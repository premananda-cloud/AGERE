"""
sim_transfer_test_demo.py

A slow, continuous takeoff -> hover -> land flight of the trained hover
policy, entirely within this repo's own PyBullet sim (AGERE stays
PyBullet + Gymnasium only, per README/Architecture.md -- this is NOT a
PX4/Gazebo test, that's AGERE_sims' job later).

What this is for: hover_demo.py demonstrates disturbance recovery from a
policy that's already hovering. This script demonstrates something the
policy was never explicitly trained to do -- fly a full ground-to-hover-
to-ground profile -- using no new logic on top of it. The "delivery"
idea: get the drone from the ground into the policy's trained operating
envelope, let it do its job, then get it back down.

Mechanism (unchanged from the first version): HoverGymEnv._obs_from_state()
recomputes pos_error from self.task.target_position EVERY step, not once
at reset. The policy only sees pos_error/velocity/attitude-error -- it
doesn't know or care whether pos_error is nonzero because the DRONE moved
or because the TARGET moved. A target that ramps smoothly from ground
level up to hover altitude, holds, then ramps back down produces a
takeoff/hover/landing flight with no retraining and no separate takeoff/
landing controller -- one continuous episode, one reset().

REVISION (v2): the first version used one uniform ease-in/ease-out ramp
across the WHOLE altitude range for each of takeoff/landing. That's wrong
in one specific way -- confirmed against config.py's HoverTaskConfig:

    target_position z default = 1.0, reset_position_jitter default = 0.3

Every training episode starts within 0.3m of z=1.0, i.e. roughly z in
[0.7, 1.3]. The policy has effectively ZERO experience flying below
~0.7m -- no ground effect, no near-ground turbulence, nothing. A uniform
ease-in/ease-out ramp is actively counterproductive here: smoothstep's
velocity is SLOWEST exactly at the start (near the ground, the untrained
band) and fastest through the middle -- the opposite of what you want.
Slowing the whole ramp down (as tried: 0.12 -> 0.08 m/s) only makes this
worse by increasing dwell time in the untrained band, which is almost
certainly why the slower run strayed from the marker while the faster
default didn't.

Fix: split each of takeoff/landing into two segments instead of one:
    - TRANSIT (ground <-> the edge of the trained jitter band): fast,
      minimizes time spent somewhere the policy has never flown.
    - APPROACH (jitter-band edge <-> hover altitude): slow and gentle,
      exactly as before -- this band is squarely inside what training
      covered, and its span is (by construction) the same distance the
      policy always had to close from a fresh reset, so a slow ramp
      through it looks like a smooth version of exactly the correction
      it trained on, not something novel.

Usage:
    # Defaults: transit fast through the untrained low band, gentle
    # approach into hover, 6s hold, watched live in real time.
    python -m src.training.demo.sim_transfer_test_demo

    # Even gentler final approach (transit rate untouched -- this is the
    # segment that's already known to work):
    python -m src.training.demo.sim_transfer_test_demo --climb-rate 0.08 --descend-rate 0.08

    # Faster transit through the untrained low band (spend even less time
    # there), longer hold once at altitude:
    python -m src.training.demo.sim_transfer_test_demo --transit-rate 0.4 --hover-duration 10

    # Record a video:
    python -m src.training.demo.sim_transfer_test_demo --record
"""

import argparse
import glob
import shutil
import subprocess
import time

import numpy as np
from stable_baselines3 import PPO
from gym_pybullet_drones.utils.utils import sync

from src.config import ProjectConfig, HoverTaskConfig
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv

DEFAULT_MODEL = "model/model_weights/hover_champion.zip"

# HoverGymEnv.reset() clips spawn altitude to max(z, 0.1) ("never spawn
# below ground") -- so 0.1m is the real floor regardless of what's asked
# for. Made an explicit constant (not just a CLI default) so the clamp is
# visible here rather than silently overriding a lower --ground-z later.
ENV_MIN_ALTITUDE = 0.1

# Pulled from HoverTaskConfig's own defaults rather than hardcoded, so if
# the training config's jitter or target altitude ever changes, this
# script's idea of "the trained band" stays correct automatically.
_TRAINED_DEFAULTS = HoverTaskConfig()
_TRAINED_JITTER = _TRAINED_DEFAULTS.reset_position_jitter       # 0.3 by default
_TRAINED_TARGET_Z = _TRAINED_DEFAULTS.target_position[2]        # 1.0 by default


def _smoothstep(frac: float) -> float:
    """Ease-in/ease-out over frac in [0,1]: zero slope at both ends."""
    frac = max(0.0, min(1.0, frac))
    return frac * frac * (3.0 - 2.0 * frac)


def _stitch_pngs_to_mp4(frame_dir: str, ctrl_freq: int) -> str | None:
    """Same as hover_demo.py's helper -- duplicated rather than imported so
    this script has no dependency on hover_demo.py's internals."""
    if shutil.which("ffmpeg") is None:
        return None
    out_path = frame_dir.rstrip("/") + ".mp4"
    cmd = [
        "ffmpeg", "-y", "-framerate", str(ctrl_freq),
        "-i", f"{frame_dir}frame_%d.png",
        "-pix_fmt", "yuv420p", out_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg stitching failed:\n{result.stderr[-500:]}")
        return None
    return out_path


class FlightProfile:
    """Six-phase altitude timeline:

        ground --[transit, fast]--> band edge --[approach, slow]--> hover
        hover --[approach, slow]--> band edge --[transit, fast]--> ground
        ground --[settle]--> (hold, watch it stabilize)

    x/y stay fixed throughout -- only altitude moves. Each individual
    segment is itself eased (smoothstep) so there's no velocity
    discontinuity at segment boundaries either, just a different PACE
    per segment.
    """

    def __init__(self, ground_z, hover_z, xy, transit_rate, climb_rate,
                 descend_rate, hover_duration, settle_duration,
                 band_edge_z):
        self.ground_z = ground_z
        self.hover_z = hover_z
        self.xy = xy
        self.band_edge_z = band_edge_z  # top of the "transit" segment / bottom of "approach"

        transit_span = band_edge_z - ground_z     # untrained low band
        approach_span = hover_z - band_edge_z      # trained jitter band

        self.takeoff_transit_dur = transit_span / transit_rate if transit_rate > 0 and transit_span > 0 else 0.0
        self.takeoff_approach_dur = approach_span / climb_rate if climb_rate > 0 and approach_span > 0 else 0.0
        self.landing_approach_dur = approach_span / descend_rate if descend_rate > 0 and approach_span > 0 else 0.0
        self.landing_transit_dur = transit_span / transit_rate if transit_rate > 0 and transit_span > 0 else 0.0
        self.hover_duration = hover_duration
        self.settle_duration = settle_duration

        self.t0 = 0.0
        self.t1 = self.t0 + self.takeoff_transit_dur    # end of takeoff_transit
        self.t2 = self.t1 + self.takeoff_approach_dur   # end of takeoff_approach / start of hover
        self.t3 = self.t2 + self.hover_duration          # end of hover
        self.t4 = self.t3 + self.landing_approach_dur    # end of landing_approach
        self.t5 = self.t4 + self.landing_transit_dur     # end of landing_transit
        self.t6 = self.t5 + self.settle_duration         # end of settle

    @property
    def total_duration(self) -> float:
        return self.t6

    @property
    def takeoff_duration(self) -> float:
        return self.takeoff_transit_dur + self.takeoff_approach_dur

    @property
    def landing_duration(self) -> float:
        return self.landing_approach_dur + self.landing_transit_dur

    def phase_at(self, t: float) -> str:
        if t <= self.t1:
            return "takeoff_transit"
        if t <= self.t2:
            return "takeoff_approach"
        if t <= self.t3:
            return "hover"
        if t <= self.t4:
            return "landing_approach"
        if t <= self.t5:
            return "landing_transit"
        return "settle"

    def target_at(self, t: float) -> tuple:
        if t <= self.t1:
            frac = t / self.takeoff_transit_dur if self.takeoff_transit_dur > 0 else 1.0
            z = self.ground_z + _smoothstep(frac) * (self.band_edge_z - self.ground_z)
        elif t <= self.t2:
            frac = (t - self.t1) / self.takeoff_approach_dur if self.takeoff_approach_dur > 0 else 1.0
            z = self.band_edge_z + _smoothstep(frac) * (self.hover_z - self.band_edge_z)
        elif t <= self.t3:
            z = self.hover_z
        elif t <= self.t4:
            frac = (t - self.t3) / self.landing_approach_dur if self.landing_approach_dur > 0 else 1.0
            z = self.hover_z - _smoothstep(frac) * (self.hover_z - self.band_edge_z)
        elif t <= self.t5:
            frac = (t - self.t4) / self.landing_transit_dur if self.landing_transit_dur > 0 else 1.0
            z = self.band_edge_z - _smoothstep(frac) * (self.band_edge_z - self.ground_z)
        else:
            z = self.ground_z
        return (self.xy[0], self.xy[1], z)


_PHASE_MARKER_COLOR = {
    "takeoff_transit": (0.0, 0.55, 0.95, 0.7),   # blue -- quick pass through the untrained band
    "takeoff_approach": (0.0, 0.85, 0.75, 0.7),  # teal -- gentle, inside the trained band
    "hover": (0.2, 0.9, 0.2, 0.7),                # green -- matches hover_demo.py's target marker
    "landing_approach": (1.0, 0.75, 0.0, 0.7),   # amber -- gentle, inside the trained band
    "landing_transit": (0.9, 0.3, 0.0, 0.7),      # red-orange -- quick pass through the untrained band
    "settle": (0.5, 0.5, 0.5, 0.7),               # grey
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                         help=f"Defaults to {DEFAULT_MODEL} -- the promoted disturbance-robustness champion.")
    parser.add_argument("--ground-z", type=float, default=ENV_MIN_ALTITUDE,
                         help=f"Target altitude for takeoff start / landing end. Values below "
                              f"{ENV_MIN_ALTITUDE} are clamped by HoverGymEnv.reset() itself.")
    parser.add_argument("--hover-altitude", type=float, default=_TRAINED_TARGET_Z,
                         help=f"Target altitude during the hover phase. Defaults to {_TRAINED_TARGET_Z} -- "
                              f"exactly what the policy was trained at.")
    parser.add_argument("--xy", type=float, nargs=2, default=(0.0, 0.0), metavar=("X", "Y"),
                         help="Fixed x,y target for the whole flight -- only altitude ramps.")
    parser.add_argument("--transit-rate", type=float, default=0.30,
                         help="m/s -- speed through the UNTRAINED low-altitude band (ground to "
                              "hover-altitude minus the training jitter distance). Faster is safer "
                              "here, not gentler -- this band is out-of-distribution for the policy, "
                              "so minimizing time spent in it matters more than a slow, pretty ramp.")
    parser.add_argument("--climb-rate", type=float, default=0.12,
                         help="m/s -- speed for the final APPROACH into hover altitude, i.e. only "
                              "within the training jitter band. This is the segment that's safe to "
                              "take slow -- it's squarely inside what the policy actually trained on.")
    parser.add_argument("--descend-rate", type=float, default=0.12,
                         help="m/s -- mirror of --climb-rate for the initial descent out of hover, "
                              "before the low-altitude transit segment.")
    parser.add_argument("--jitter-margin", type=float, default=_TRAINED_JITTER,
                         help=f"Distance below --hover-altitude considered 'the trained band' -- "
                              f"defaults to HoverTaskConfig's own reset_position_jitter "
                              f"({_TRAINED_JITTER}). Only override this if you've changed that "
                              f"training config and this script wasn't updated to match.")
    parser.add_argument("--hover-duration", type=float, default=6.0,
                         help="Seconds to hold at --hover-altitude before beginning descent.")
    parser.add_argument("--settle-duration", type=float, default=2.0,
                         help="Seconds to hold at --ground-z after landing.")
    parser.add_argument("--seed", type=int, default=0, help="Seeds the single reset() call.")
    parser.add_argument("--record", action="store_true", help="Same as hover_demo.py's --record.")
    parser.add_argument("--headless", action="store_true",
                         help="No GUI, no real-time pacing. Implies --record.")
    args = parser.parse_args()

    if args.transit_rate <= 0:
        parser.error("--transit-rate must be > 0")
    if args.climb_rate <= 0:
        parser.error("--climb-rate must be > 0")
    if args.descend_rate <= 0:
        parser.error("--descend-rate must be > 0")
    if args.hover_altitude <= args.ground_z:
        parser.error("--hover-altitude must be above --ground-z")

    ground_z = max(args.ground_z, ENV_MIN_ALTITUDE)
    if args.ground_z < ENV_MIN_ALTITUDE:
        print(f"Note: --ground-z {args.ground_z} is below the env's own {ENV_MIN_ALTITUDE}m spawn "
              f"floor -- using {ENV_MIN_ALTITUDE}m instead.")

    band_edge_z = max(ground_z, args.hover_altitude - args.jitter_margin)
    if band_edge_z <= ground_z:
        print(f"Note: --hover-altitude is within --jitter-margin of --ground-z -- the whole climb/"
              f"descent is inside the trained band, no separate low-altitude transit segment needed.")

    profile = FlightProfile(
        ground_z=ground_z,
        hover_z=args.hover_altitude,
        xy=tuple(args.xy),
        transit_rate=args.transit_rate,
        climb_rate=args.climb_rate,
        descend_rate=args.descend_rate,
        hover_duration=args.hover_duration,
        settle_duration=args.settle_duration,
        band_edge_z=band_edge_z,
    )

    print(f"Trained altitude band: z in [{band_edge_z:.2f}, {args.hover_altitude:.2f}]m "
          f"(hover target {_TRAINED_TARGET_Z}m +/- jitter {args.jitter_margin}m during training)")
    print(f"Takeoff: ground {ground_z:.2f}m --[transit {profile.takeoff_transit_dur:.1f}s]--> "
          f"{band_edge_z:.2f}m --[approach {profile.takeoff_approach_dur:.1f}s]--> "
          f"{args.hover_altitude:.2f}m")
    print(f"Hold:    {args.hover_duration:.1f}s at {args.hover_altitude:.2f}m")
    print(f"Landing: {args.hover_altitude:.2f}m --[approach {profile.landing_approach_dur:.1f}s]--> "
          f"{band_edge_z:.2f}m --[transit {profile.landing_transit_dur:.1f}s]--> {ground_z:.2f}m")
    print(f"Settle:  {args.settle_duration:.1f}s at {ground_z:.2f}m")
    print(f"Total duration: {profile.total_duration:.1f}s\n")

    task = HoverTaskConfig(
        target_position=(args.xy[0], args.xy[1], ground_z),
        episode_len_sec=profile.total_duration + 2.0,
        reset_position_jitter=0.0,
        reset_yaw_jitter_deg=0.0,
        disturbance_enabled=False,
    )
    config = ProjectConfig(task=task)
    config.sim.gui = not args.headless
    config.sim.record = args.record or args.headless

    if config.sim.record:
        print(f"Recording ON -- output in ./results/ (relative to cwd, not configurable).\n")

    env = HoverGymEnv(config)
    model = PPO.load(args.model, device="cpu")

    ctrl_freq = config.sim.ctrl_freq
    timestep = 1.0 / ctrl_freq
    total_steps = int(profile.total_duration * ctrl_freq)

    obs, _ = env.reset(seed=args.seed)
    env.sim.draw_target_marker(profile.target_at(0.0), color=_PHASE_MARKER_COLOR["takeoff_transit"], radius=0.06)

    max_tilt_seen = 0.0
    max_speed_seen = 0.0
    current_phase = None
    start_time = time.time()
    crashed = False

    try:
        for step_i in range(total_steps):
            t_sec = step_i / ctrl_freq
            target = profile.target_at(t_sec)
            env.task.target_position = target

            phase = profile.phase_at(t_sec)
            if phase != current_phase:
                current_phase = phase
                print(f"--- {phase} (t={t_sec:.1f}s, target z={target[2]:.2f}m) ---")
                env.sim.draw_target_marker(target, color=_PHASE_MARKER_COLOR[phase], radius=0.05)
            elif step_i % ctrl_freq == 0:
                env.sim.draw_target_marker(target, color=_PHASE_MARKER_COLOR[phase], radius=0.03)

            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            if not args.headless:
                sync(step_i, start_time, timestep)

            max_tilt_seen = max(max_tilt_seen, float(max(abs(obs[6]), abs(obs[7]))))
            max_speed_seen = max(max_speed_seen, float(np.linalg.norm(obs[3:6])))

            if step_i % ctrl_freq == 0:
                print(f"  t={t_sec:5.1f}s | phase={phase:<17s} | target z={target[2]:.2f}m | "
                      f"pos error {info['position_error_norm']:.3f} m")

            if truncated and info.get("is_crash"):
                crashed = True
                print(f"\n!! Flight ended early: {info['truncation_reason']} at t={t_sec:.1f}s "
                      f"(phase={phase}). Reproduce with a faster --transit-rate before trusting "
                      f"this profile -- if it's still happening in the transit segments, that's the "
                      f"untrained low-altitude band; if it's in the approach/hover segments, that's "
                      f"a different problem worth investigating on its own.")
                break

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        env.close()

    if not crashed:
        print(f"\nFlight complete: ground -> hover -> ground, {profile.total_duration:.1f}s, no crash.")
        print(f"Max tilt observed:  {np.degrees(max_tilt_seen):.1f} deg")
        print(f"Max speed observed: {max_speed_seen:.2f} m/s")

    if args.headless and config.sim.record:
        frame_dirs = sorted(glob.glob("results/recording_*/"))
        if not frame_dirs:
            print("No frame directory found -- recording may not have started correctly.")
        else:
            latest = frame_dirs[-1]
            print(f"\nStitching {latest} ...")
            out = _stitch_pngs_to_mp4(latest, ctrl_freq)
            if out:
                print(f"Video saved: {out}")
            else:
                print(f"ffmpeg not found on PATH -- frames left in {latest}. Stitch manually with:\n"
                      f"  ffmpeg -framerate {ctrl_freq} -i {latest}frame_%d.png "
                      f"-pix_fmt yuv420p {latest.rstrip('/')}.mp4")


if __name__ == "__main__":
    main()
