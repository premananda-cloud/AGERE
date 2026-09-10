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
envelope, let it do its job, then get it back down, the same way you'd
deliver a player onto the field before the game starts rather than have
them appear mid-play.

How it works, mechanically:
    HoverGymEnv._obs_from_state() recomputes pos_error from
    self.task.target_position EVERY step, not once at reset. The policy
    only ever sees pos_error/velocity/attitude-error -- it has no idea,
    and doesn't need to know, whether pos_error is nonzero because the
    DRONE moved or because the TARGET moved. So a target that ramps
    smoothly from ground level up to hover altitude, holds, then ramps
    back down produces a takeoff/hover/landing flight out of a policy
    that only ever trained against a fixed target -- no retraining, no
    separate takeoff/landing controller, one continuous episode.

Deliberately different from hover_demo.py in three ways:
    - ONE reset(), ever. No mid-flight resets or episode restarts --
      "continuous, can't jump" was the point.
    - No disturbance of any kind (no --stage, no --force-type). Clean
      baseline flight only -- this is about the transfer/tracking
      behavior itself, not recovery.
    - The target moves. hover_demo.py's target is fixed for the whole
      episode; here it's a 3-phase ramp (see _target_altitude() below).

Ramp shape is an ease-in/ease-out (smoothstep), not linear, so the
target's climb/descent RATE goes to zero at the start and end of each
ramp instead of snapping instantly to a constant speed -- a smoother
setpoint tends to produce a smoother tracked flight, given
action_smoothness_weight already discourages jerky commands in what the
policy learned.

Usage:
    # Defaults: ground (0.1m) -> hover (1.0m) -> ground, ~0.12 m/s ramps,
    # 6s hover hold, watched live in real time.
    python -m src.training.demo.sim_transfer_test_demo

    # Slower / gentler:
    python -m src.training.demo.sim_transfer_test_demo \\
        --climb-rate 0.08 --descend-rate 0.08 --hover-duration 8

    # Higher hover altitude, longer hold, record a video:
    python -m src.training.demo.sim_transfer_test_demo \\
        --hover-altitude 1.5 --hover-duration 10 --record

    # Headless (fast, for CI-style sanity checks rather than watching):
    python -m src.training.demo.sim_transfer_test_demo --headless
"""

import argparse
import glob
import shutil
import subprocess
import time
from dataclasses import replace

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


def _smoothstep(frac: float) -> float:
    """Ease-in/ease-out over frac in [0,1]: zero slope at both ends. Used
    for every ramp so the target's own velocity doesn't jump discontinuously
    at phase boundaries -- see module docstring."""
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
    """Three-phase altitude ramp: ground -> hover (takeoff), hold (hover),
    hover -> ground (landing), then hold at ground (settle) so you can watch
    it stabilize on the ground before the script ends. x/y stay fixed
    throughout -- only altitude ramps."""

    def __init__(self, ground_z, hover_z, xy, climb_rate, descend_rate,
                 hover_duration, settle_duration):
        self.ground_z = ground_z
        self.hover_z = hover_z
        self.xy = xy
        span = hover_z - ground_z
        # Guarded in main() before this is constructed, but zero-guard here
        # too so this class is safe to reuse/import elsewhere.
        self.takeoff_duration = span / climb_rate if climb_rate > 0 else 0.0
        self.landing_duration = span / descend_rate if descend_rate > 0 else 0.0
        self.hover_duration = hover_duration
        self.settle_duration = settle_duration

        self.t_takeoff_end = self.takeoff_duration
        self.t_hover_end = self.t_takeoff_end + self.hover_duration
        self.t_landing_end = self.t_hover_end + self.landing_duration
        self.t_settle_end = self.t_landing_end + self.settle_duration

    @property
    def total_duration(self) -> float:
        return self.t_settle_end

    def phase_at(self, t_sec: float) -> str:
        if t_sec <= self.t_takeoff_end:
            return "takeoff"
        if t_sec <= self.t_hover_end:
            return "hover"
        if t_sec <= self.t_landing_end:
            return "landing"
        return "settle"

    def target_at(self, t_sec: float) -> tuple:
        """(x, y, z) target for this instant -- this is the only thing this
        script feeds back into the policy; everything else is untouched."""
        if t_sec <= self.t_takeoff_end:
            frac = t_sec / self.takeoff_duration if self.takeoff_duration > 0 else 1.0
            z = self.ground_z + _smoothstep(frac) * (self.hover_z - self.ground_z)
        elif t_sec <= self.t_hover_end:
            z = self.hover_z
        elif t_sec <= self.t_landing_end:
            frac = (t_sec - self.t_hover_end) / self.landing_duration if self.landing_duration > 0 else 1.0
            z = self.hover_z - _smoothstep(frac) * (self.hover_z - self.ground_z)
        else:
            z = self.ground_z
        return (self.xy[0], self.xy[1], z)


_PHASE_MARKER_COLOR = {
    "takeoff": (0.0, 0.8, 0.8, 0.7),   # teal
    "hover": (0.2, 0.9, 0.2, 0.7),     # green -- matches hover_demo.py's target marker
    "landing": (1.0, 0.65, 0.0, 0.7),  # amber
    "settle": (0.5, 0.5, 0.5, 0.7),    # grey
}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--model", type=str, default=DEFAULT_MODEL,
                         help=f"Defaults to {DEFAULT_MODEL} -- the promoted disturbance-robustness champion.")
    parser.add_argument("--ground-z", type=float, default=ENV_MIN_ALTITUDE,
                         help=f"Target altitude for takeoff start / landing end. Values below "
                              f"{ENV_MIN_ALTITUDE} are clamped by HoverGymEnv.reset() itself, so "
                              f"this can't actually go lower regardless of what's passed.")
    parser.add_argument("--hover-altitude", type=float, default=1.0,
                         help="Target altitude during the hover phase (matches HoverTaskConfig's "
                              "default target_position z, i.e. what the policy was actually trained at).")
    parser.add_argument("--xy", type=float, nargs=2, default=(0.0, 0.0), metavar=("X", "Y"),
                         help="Fixed x,y target for the whole flight -- only altitude ramps.")
    parser.add_argument("--climb-rate", type=float, default=0.12,
                         help="m/s -- how fast the TARGET climbs during takeoff. Slower = gentler "
                              "liftoff. Not a hard drone speed limit, just the setpoint's own pace.")
    parser.add_argument("--descend-rate", type=float, default=0.12,
                         help="m/s -- how fast the TARGET descends during landing.")
    parser.add_argument("--hover-duration", type=float, default=6.0,
                         help="Seconds to hold at --hover-altitude before beginning descent.")
    parser.add_argument("--settle-duration", type=float, default=2.0,
                         help="Seconds to hold at --ground-z after landing, so you can watch it "
                              "stabilize on the ground before the script ends.")
    parser.add_argument("--seed", type=int, default=0, help="Seeds the single reset() call.")
    parser.add_argument("--record", action="store_true",
                         help="Same as hover_demo.py's --record -- saves video via gym-pybullet-"
                              "drones' built-in recorder, output in ./results/ (not configurable).")
    parser.add_argument("--headless", action="store_true",
                         help="No GUI, no real-time pacing -- runs as fast as the sim allows and "
                              "records PNG frames. Implies --record.")
    args = parser.parse_args()

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

    profile = FlightProfile(
        ground_z=ground_z,
        hover_z=args.hover_altitude,
        xy=tuple(args.xy),
        climb_rate=args.climb_rate,
        descend_rate=args.descend_rate,
        hover_duration=args.hover_duration,
        settle_duration=args.settle_duration,
    )

    print(f"Flight profile: ground {ground_z:.2f}m -> hover {args.hover_altitude:.2f}m "
          f"(takeoff {profile.takeoff_duration:.1f}s) -> hold {args.hover_duration:.1f}s -> "
          f"ground {ground_z:.2f}m (landing {profile.landing_duration:.1f}s) -> "
          f"settle {args.settle_duration:.1f}s")
    print(f"Total duration: {profile.total_duration:.1f}s\n")

    # --- Build a config sized for this specific flight -------------------
    # episode_len_sec must be set BEFORE HoverGymEnv() is constructed --
    # it's read once in __init__ to compute _max_steps. Oversized with a
    # margin so the env's own timeout truncation never fires mid-sequence;
    # this script drives its own step budget and stops itself.
    # jitter set to 0 for a clean, deterministic ground start -- start
    # position becomes exactly target_position (see reset()'s formula) at
    # zero jitter, so the very first observation has ~zero pos_error rather
    # than an arbitrary offset.
    task = HoverTaskConfig(
        target_position=(args.xy[0], args.xy[1], ground_z),  # only used for the initial reset() spawn
        episode_len_sec=profile.total_duration + 2.0,
        reset_position_jitter=0.0,
        reset_yaw_jitter_deg=0.0,
        disturbance_enabled=False,  # explicit, even though this is already the default
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
    env.sim.draw_target_marker(profile.target_at(0.0), color=_PHASE_MARKER_COLOR["takeoff"], radius=0.06)

    max_tilt_seen = 0.0
    max_speed_seen = 0.0
    current_phase = None
    start_time = time.time()
    crashed = False

    try:
        for step_i in range(total_steps):
            t_sec = step_i / ctrl_freq
            target = profile.target_at(t_sec)
            env.task.target_position = target  # the only thing driving takeoff/hover/land

            phase = profile.phase_at(t_sec)
            if phase != current_phase:
                current_phase = phase
                print(f"--- {phase} (t={t_sec:.1f}s, target z={target[2]:.2f}m) ---")
                env.sim.draw_target_marker(target, color=_PHASE_MARKER_COLOR[phase], radius=0.05)
            elif step_i % ctrl_freq == 0:  # once per sim-second, a breadcrumb of the ramp path
                env.sim.draw_target_marker(target, color=_PHASE_MARKER_COLOR[phase], radius=0.03)

            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            if not args.headless:
                sync(step_i, start_time, timestep)

            max_tilt_seen = max(max_tilt_seen, float(max(abs(obs[6]), abs(obs[7]))))
            max_speed_seen = max(max_speed_seen, float(np.linalg.norm(obs[3:6])))

            if step_i % ctrl_freq == 0:
                print(f"  t={t_sec:5.1f}s | target z={target[2]:.2f}m | "
                      f"pos error {info['position_error_norm']:.3f} m")

            if truncated and info.get("is_crash"):
                crashed = True
                print(f"\n!! Flight ended early: {info['truncation_reason']} at t={t_sec:.1f}s "
                      f"(phase={phase}). This is a genuine loss of control under the smooth "
                      f"profile, not something to wave off -- worth reproducing with a slower "
                      f"--climb-rate/--descend-rate before trusting this transfer.")
                break

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        env.close()

    if not crashed:
        print(f"\nFlight complete: ground -> hover -> ground, {profile.total_duration:.1f}s, "
              f"no crash.")
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
