"""
Live PyBullet demo of the trained hover/stabilize policy — for showing to
other people, not for evaluation (see evaluate/hover_evaluate.py for that).

Runs continuously, looping episodes, at real-time speed so it's watchable.
Draws a green marker at the target position so viewers can see what the
drone is trying to hold station at.

On Intel integrated graphics with no dedicated GPU, this may fail to open
the GUI window or render a black screen. (demo_intel.py used to carry a
Mesa/OpenGL-compatibility variant of this script for that case; it's been
removed — if that problem resurfaces, re-add a variant here rather than
assuming one still exists elsewhere.)

Usage:
    python -m src.training.demo.hover_demo
    python -m src.training.demo.hover_demo --model hover_stabilize_ppo.zip
    python -m src.training.demo.hover_demo --episodes 5   # stop after N episodes instead of looping forever

    # 3-type/5-level disturbance demo (2026-08-25 redesign — see
    # docs/architecture/hover-disturbance-3x5-design.md), same config
    # source as hover_train.py/hover_evaluate.py's --stage flag. Random
    # type+level each episode, same as training/eval:
    python -m src.training.demo.hover_demo --stage disturbance_3x5 \\
        --model model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2.zip

    # Force a SPECIFIC type/level instead of waiting for a random draw to
    # land on it — e.g. to reproduce the late-episode instability pattern
    # flagged in training-log.md (2026-08-25: several kick episodes recover
    # cleanly, then crash again many steps later with no new disturbance
    # event). Level/magnitude/onset still randomize per episode unless also
    # forced, so you still see natural variety within the forced type:
    python -m src.training.demo.hover_demo --stage disturbance_3x5 \\
        --model model/model_weights/hover_stabilize_ppo_seed0_disturbance_3x5_tiltfix2.zip \\
        --force-type kick --force-level 4

    # Fully pinned (exact magnitude, exact onset step) for the most
    # reproducible repro of one specific case:
    python -m src.training.demo.hover_demo --stage disturbance_3x5 \\
        --force-type kick --force-level 4 --force-magnitude 1.3 --force-onset-step 90

Draws a marker at the drone's position the instant a disturbance event
fires (color varies by type — orange=kick, purple=torque, blue=wind),
distinct from the green target marker. Once recovery is achieved, this
also watches for tilt climbing back past half the crash threshold
afterward with NO new disturbance event — the live signature of the
late-episode instability pattern — and prints a flag the moment it
happens, rather than only being visible after the fact in an eval log.
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

from src.config import ProjectConfig, HOVER_STAGE_PRESETS, DISTURBANCE_TYPES
from src.paths import hover_stabilize_model_path
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv

# Marker color per disturbance type, so viewers can tell which fired without
# reading the console. Distinct from the green target marker either way.
_TYPE_MARKER_COLOR = {
    "kick": (1.0, 0.35, 0.0, 0.85),    # orange
    "torque": (0.6, 0.0, 0.9, 0.85),   # purple
    "wind": (0.0, 0.5, 1.0, 0.85),     # blue
}

# Renewed-instability watch: fraction of max_tilt_rad that, if crossed AFTER
# recovery was already achieved with no new disturbance event, gets flagged
# live. 0.5 chosen to catch it building up well before it would actually
# reach the (sustained-hold) crash threshold, giving a visible early warning
# rather than only knowing right as/after it truncates.
_RENEWED_INSTABILITY_TILT_FRACTION = 0.5


def _stitch_pngs_to_mp4(frame_dir: str, ctrl_freq: int) -> str | None:
    """Stitch a directory of frame_N.png (headless recording output) into an
    mp4 via ffmpeg. Returns the output path, or None if ffmpeg isn't
    available -- in that case the PNGs are left in place and the caller
    should tell the person how to stitch them manually later."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", type=str, default=None,
        help="Defaults to model/hover_stabilize/hover_stabilize_ppo.zip (see src/paths.py)"
    )
    parser.add_argument("--episodes", type=int, default=None, help="Loop forever if not set")
    parser.add_argument(
        "--stage", type=str, default=None, choices=sorted(HOVER_STAGE_PRESETS.keys()),
        help="Apply a stage's disturbance config (config.py's HOVER_STAGE_PRESETS, same presets "
             "hover_train.py/hover_evaluate.py use). REQUIRED to see disturbance at all unless "
             "--force-type is given instead (--force-type implies disturbance regardless of stage)."
    )
    parser.add_argument(
        "--force-type", type=str, default=None, choices=sorted(DISTURBANCE_TYPES.keys()),
        help="Force every episode's disturbance to this type instead of random type selection "
             "(level/magnitude/onset still randomize unless also forced -- see --force-level etc). "
             "Enables disturbance even without --stage. Useful for reliably reproducing a specific "
             "case, e.g. the late-episode instability pattern seen in kick episodes."
    )
    parser.add_argument(
        "--force-level", type=int, default=None, choices=[1, 2, 3, 4, 5],
        help="Force the disturbance level (1-5). Requires --force-type. Magnitude still randomizes "
             "within that level's range unless --force-magnitude is also given."
    )
    parser.add_argument(
        "--force-magnitude", type=float, default=None,
        help="Force the exact disturbance magnitude (units depend on --force-type: m/s for kick, "
             "rad/s for torque, N for wind). Requires --force-type. Overrides --force-level's range "
             "sampling, though --force-level is still used if given (e.g. for eval-report labeling)."
    )
    parser.add_argument(
        "--force-onset-step", type=int, default=None,
        help="Force the exact control step the disturbance fires (or, for wind, starts). Requires "
             "--force-type. Otherwise sampled within the normal window each episode."
    )
    parser.add_argument(
        "--record", action="store_true",
        help="Save video output via gym-pybullet-drones' built-in recorder. With GUI on "
             "(default), produces a real .mp4 directly -- window still opens, but you don't "
             "need to watch it live. Output always lands in ./results/ (not configurable, "
             "confirmed against gym-pybullet-drones source -- HoverAviary never exposes "
             "output_folder). Combine with --headless for no window at all."
    )
    parser.add_argument(
        "--headless", action="store_true",
        help="No GUI window at all. Implies --record (a headless run with nothing displayed "
             "and nothing recorded would produce no output). Saves per-step PNG frames to "
             "./results/recording_<timestamp>/, then stitches them into an .mp4 via ffmpeg if "
             "it's on PATH -- if not, the PNGs are left in place and this prints the manual "
             "ffmpeg command instead of failing silently. Also skips real-time pacing (no "
             "point pacing a run nobody's watching live), so this finishes much faster than "
             "the episode's actual duration."
    )
    args = parser.parse_args()
    model_path = args.model or str(hover_stabilize_model_path())

    if args.force_level is not None and args.force_type is None:
        parser.error("--force-level requires --force-type")
    if args.force_magnitude is not None and args.force_type is None:
        parser.error("--force-magnitude requires --force-type")
    if args.force_onset_step is not None and args.force_type is None:
        parser.error("--force-onset-step requires --force-type")

    config = ProjectConfig()
    config.sim.gui = not args.headless  # demo defaults to a window; --headless turns it off
    config.sim.record = args.record or args.headless

    if args.stage:
        config.task = replace(config.task, **HOVER_STAGE_PRESETS[args.stage])
        print(f"Applied stage preset '{args.stage}': {HOVER_STAGE_PRESETS[args.stage]}")

    forced_disturbance = None
    if args.force_type:
        forced_disturbance = {"type": args.force_type}
        if args.force_level is not None:
            forced_disturbance["level"] = args.force_level
        if args.force_magnitude is not None:
            forced_disturbance["magnitude"] = args.force_magnitude
        if args.force_onset_step is not None:
            forced_disturbance["onset_step"] = args.force_onset_step
        # Forcing implies disturbance regardless of --stage/config.task.disturbance_enabled --
        # _sample_disturbance_event() checks self._forced_disturbance BEFORE the enabled flag
        # (see hover_gym_wrapper.py), so this is enough on its own.
        print(f"Forced disturbance: {forced_disturbance} "
              f"(unset fields still randomize per episode, same range as normal sampling)")
    elif not config.task.disturbance_enabled:
        print("No --stage or --force-type given -- this will be a plain, undisturbed hover demo.\n")

    if config.sim.record:
        print(f"Recording ON — {'headless PNG frames' if args.headless else 'live GUI + direct .mp4'}, "
              f"output in ./results/ (relative to cwd, not configurable — see --record help).\n")

    env = HoverGymEnv(config, forced_disturbance=forced_disturbance)
    model = PPO.load(model_path, device="cpu")

    timestep = 1.0 / config.sim.ctrl_freq
    max_tilt_rad = config.task.max_tilt_rad
    episode = 0

    try:
        while args.episodes is None or episode < args.episodes:
            episode += 1
            obs, _ = env.reset()
            env.sim.draw_target_marker(config.task.target_position)

            print(f"\n--- episode {episode} ---")
            start_time = time.time()
            terminated = truncated = False
            step_i = 0
            disturbance_marked = False
            recovery_seen = False  # info["recovered"] has been True at least once this episode
            renewed_instability_flagged = False  # printed the live warning already this episode

            while not (terminated or truncated):
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                if not args.headless:
                    sync(step_i, start_time, timestep)  # paces to real time so it's watchable
                step_i += 1

                # Fires the first step a disturbance event is visible in info --
                # draw a marker at the drone's current position, colored by type,
                # distinct from the green target marker.
                if info.get("disturbance_fired") and not disturbance_marked:
                    disturbance_marked = True
                    dtype = info["disturbance_type"]
                    dpos = env.sim.get_state().position
                    color = _TYPE_MARKER_COLOR.get(dtype, (1.0, 1.0, 1.0, 0.85))
                    env.sim.draw_target_marker(dpos, color=color, radius=0.07)
                    unit = DISTURBANCE_TYPES[dtype].unit
                    print(f"  >> {dtype} L{info['disturbance_level']} "
                          f"({info['disturbance_magnitude']:.3f}{unit}) applied at step {step_i}")

                if info.get("recovered"):
                    recovery_seen = True

                # Live renewed-instability watch (2026-08-25): once recovery has
                # already been achieved once, tilt climbing back past half the
                # crash threshold with no NEW disturbance event is exactly the
                # pattern flagged in training-log.md -- flag it the moment it
                # happens instead of only being inferable after the episode ends.
                if recovery_seen and not renewed_instability_flagged:
                    tilt_now = max(abs(obs[6]), abs(obs[7]))
                    if tilt_now > _RENEWED_INSTABILITY_TILT_FRACTION * max_tilt_rad:
                        renewed_instability_flagged = True
                        print(f"  !! renewed instability at step {step_i}: tilt "
                              f"{np.degrees(tilt_now):.1f} deg after prior recovery, "
                              f"no new disturbance event")

            reason = info.get("truncation_reason", "n/a")
            recovery_note = ""
            if disturbance_marked:
                if info.get("is_crash"):
                    recovery_note = " | disturbed, CRASHED"
                    if renewed_instability_flagged:
                        recovery_note += " (after an earlier recovery -- late-instability pattern)"
                elif info.get("recovered"):
                    recovery_note = f" | disturbed, recovered in {info.get('recovery_time_steps')} steps"
                    if "wind_steady_state_error_mean" in info:
                        recovery_note += f", steady-state err {info['wind_steady_state_error_mean']:.3f}m"
                else:
                    recovery_note = " | disturbed, did NOT recover in budget"
            print(f"episode {episode} ended: {reason} | final pos error: {info['position_error_norm']:.3f} m{recovery_note}")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        env.close()
        if args.headless and config.sim.record:
            # BaseAviary calls _startVideoRecording() on every reset(), not just once --
            # confirmed against source (2026-08-16) -- so multi-episode runs produce a NEW
            # timestamped results/recording_.../ folder per episode, not one combined
            # folder. Stitch the most recent one (this run's last episode); earlier
            # episodes' folders are still on disk if --episodes > 1, just not auto-stitched.
            frame_dirs = sorted(glob.glob("results/recording_*/"))
            if not frame_dirs:
                print("No frame directory found -- recording may not have started correctly.")
            else:
                latest = frame_dirs[-1]
                print(f"\nStitching {latest} ...")
                out = _stitch_pngs_to_mp4(latest, config.sim.ctrl_freq)
                if out:
                    print(f"Video saved: {out}")
                else:
                    print(f"ffmpeg not found on PATH -- frames left in {latest}. Stitch manually with:\n"
                          f"  ffmpeg -framerate {config.sim.ctrl_freq} -i {latest}frame_%d.png "
                          f"-pix_fmt yuv420p {latest.rstrip('/')}.mp4")
                if len(frame_dirs) > 1:
                    print(f"Note: {len(frame_dirs) - 1} earlier episode(s) also recorded to "
                          f"separate results/recording_*/ folders, not auto-stitched.")


if __name__ == "__main__":
    main()
