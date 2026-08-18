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

    # Disturbance demo (added 2026-08-16), same config source as hover_train.py/
    # hover_evaluate.py's --stage flag:
    python -m src.training.demo.hover_demo --stage 1a

    # Manual magnitude override, no --stage needed — useful for calibrating a
    # NEW magnitude level visually before committing it to config.py's
    # HOVER_STAGE_PRESETS (per theory-log.md 2026-08-16-3: Level 1's 0.1-0.3 m/s
    # range turned out to be too weak to see anything happen; try higher):
    python -m src.training.demo.hover_demo --kick-min 0.4 --kick-max 0.6

Draws an orange marker at the drone's position the instant a kick fires
(distinct from the green target marker), and prints whether/how fast the
policy recovered — this is a visual sanity check on the same recovery
tracking hover_evaluate.py reports numerically, not a separate mechanism.
"""

import argparse
import glob
import shutil
import subprocess
import time
from dataclasses import replace

from stable_baselines3 import PPO
from gym_pybullet_drones.utils.utils import sync

from src.config import ProjectConfig, HOVER_STAGE_PRESETS
from src.paths import hover_stabilize_model_path
from src.training.gym_wrapper.hover_gym_wrapper import HoverGymEnv


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
        help="Apply a Stage 1 sub-stage's disturbance config (config.py's HOVER_STAGE_PRESETS, "
             "same presets hover_train.py/hover_evaluate.py use)."
    )
    parser.add_argument(
        "--kick-min", type=float, default=None,
        help="Manual override: minimum kick magnitude, m/s. Enables disturbance even without "
             "--stage. Combine with --kick-max. Useful for visually calibrating a new magnitude "
             "level before committing it to a config preset."
    )
    parser.add_argument(
        "--kick-max", type=float, default=None,
        help="Manual override: maximum kick magnitude, m/s. See --kick-min."
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

    config = ProjectConfig()
    config.sim.gui = not args.headless  # demo defaults to a window; --headless turns it off
    config.sim.record = args.record or args.headless

    if args.stage:
        config.task = replace(config.task, **HOVER_STAGE_PRESETS[args.stage])
        print(f"Applied stage preset '{args.stage}': {HOVER_STAGE_PRESETS[args.stage]}")
    if args.kick_min is not None or args.kick_max is not None:
        overrides = {"disturbance_enabled": True}
        if args.kick_min is not None:
            overrides["disturbance_kick_min_mps"] = args.kick_min
        if args.kick_max is not None:
            overrides["disturbance_kick_max_mps"] = args.kick_max
        config.task = replace(config.task, **overrides)
        print(f"Manual kick magnitude override: {config.task.disturbance_kick_min_mps}-"
              f"{config.task.disturbance_kick_max_mps} m/s")
    if config.task.disturbance_enabled:
        print(f"Disturbance ON — kicks between step {config.task.disturbance_kick_step_min}-"
              f"{config.task.disturbance_kick_step_max}, recovery threshold "
              f"{config.task.recovery_threshold_m}m held {config.task.recovery_hold_steps} steps.\n")

    if config.sim.record:
        print(f"Recording ON — {'headless PNG frames' if args.headless else 'live GUI + direct .mp4'}, "
              f"output in ./results/ (relative to cwd, not configurable — see --record help).\n")

    env = HoverGymEnv(config)
    model = PPO.load(model_path, device="cpu")

    timestep = 1.0 / config.sim.ctrl_freq
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
            kicked_this_episode = False

            while not (terminated or truncated):
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                if not args.headless:
                    sync(step_i, start_time, timestep)  # paces to real time so it's watchable
                step_i += 1

                # Fires exactly once, the same step hover_gym_wrapper.py applies the
                # kick — draw a marker at the drone's current position so viewers can
                # see WHERE/WHEN it happened, distinct from the green target marker.
                if info.get("kicked") and not kicked_this_episode:
                    kicked_this_episode = True
                    kick_pos = env.sim.get_state().position
                    env.sim.draw_target_marker(kick_pos, color=(1.0, 0.35, 0.0, 0.85), radius=0.07)
                    print(f"  >> kick applied at step {step_i}")

            reason = info.get("truncation_reason", "n/a")
            recovery_note = ""
            if kicked_this_episode:
                if info.get("is_crash"):
                    recovery_note = " | kicked, CRASHED"
                elif info.get("recovered"):
                    recovery_note = f" | kicked, recovered in {info.get('recovery_time_steps')} steps"
                else:
                    recovery_note = " | kicked, did NOT recover in budget"
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
