"""
Live PyBullet demo of the trained hover/stabilize policy, for machines
with Intel integrated graphics and no dedicated GPU. Same episode loop
and real-time pacing as demo.py — the only difference is how the PyBullet
GUI window gets opened, since Bullet's default OpenGL3 renderer is a
common source of black-screen/crash failures on Mesa's Intel iGPU
drivers. If you have a dedicated GPU, use demo.py instead.

IMPORTANT: the Mesa env vars below must be set *before* pybullet /
gym_pybullet_drones get imported anywhere in the process (including
transitively via src.training.gym_wrapper) — Mesa reads them when the GL
context is first created, not on every connect() call. That's why this
file parses args with only argparse/os imported, sets the env vars, and
imports everything else afterward, instead of importing normally at the
top like demo.py does.

Usage:
    python -m src.training.demo_intel
    python -m src.training.demo_intel --model hover_stabilize_ppo.zip
    python -m src.training.demo_intel --episodes 5
    python -m src.training.demo_intel --gl-version-override 3.3
    python -m src.training.demo_intel --software-render

If the GUI window doesn't open, opens but stays black, or PyBullet
crashes/segfaults on connect, try in this order:
  1. Run as-is first — some Intel iGPUs with recent Mesa work unmodified.
  2. --gl-version-override 3.3 — forces an explicit, older, broadly-
     supported GL context. Helps when the failure is a GLSL/context-
     version mismatch rather than a total connect failure. If that's not
     enough on its own, Mesa also reads MESA_GLSL_VERSION_OVERRIDE (e.g.
     `MESA_GLSL_VERSION_OVERRIDE=330 python -m src.training.demo_intel
     --gl-version-override 3.3`) — not auto-set here since the correct
     value isn't a fixed formula across GL versions.
  3. --software-render — forces Mesa's llvmpipe software rasterizer.
     Slowest option but should always at least run. Expect the real-time
     pacing (sync()) to fall behind — treat this as "does it run at all,"
     not a smooth watchable demo.

Note: a driver-level failure can segfault the process outright rather
than raising a catchable Python exception — the try/except around env
creation below is best-effort (catches connection errors PyBullet raises
cleanly) but won't save you from a hard crash. If it segfaults instead of
printing the message below, go straight to trying the flags above.

None of this affects the trained model or its numbers — only whether/how
the visualization window renders. If nothing here gets the GUI working,
evaluate.py runs headless (no GUI) and still gives you real position-
error/crash-rate numbers regardless of graphics support.
"""

import argparse
import os


def _configure_gl_environment(software_render: bool, gl_version_override: str | None) -> None:
    if software_render:
        os.environ["LIBGL_ALWAYS_SOFTWARE"] = "1"
        print(
            "[demo_intel] Forcing Mesa software rendering (LIBGL_ALWAYS_SOFTWARE=1). "
            "This will be slow — real-time pacing may fall behind."
        )
    if gl_version_override:
        os.environ["MESA_GL_VERSION_OVERRIDE"] = gl_version_override
        print(f"[demo_intel] Overriding Mesa GL version to {gl_version_override}.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--model", type=str, default=None,
        help="Defaults to model/hover_stabilize/hover_stabilize_ppo.zip (see src/paths.py)"
    )
    parser.add_argument("--episodes", type=int, default=None, help="Loop forever if not set")
    parser.add_argument(
        "--software-render", action="store_true",
        help="Force Mesa's llvmpipe software rasterizer. Use if the GUI window "
             "crashes, stays black, or fails to open on hardware GL. Slow but reliable."
    )
    parser.add_argument(
        "--gl-version-override", type=str, default=None,
        help="Force a specific Mesa GL version (e.g. '3.3'). Try this before "
             "--software-render if the failure looks like a GLSL/context-version "
             "mismatch rather than a total connect failure."
    )
    args = parser.parse_args()

    # Must happen before any pybullet-importing module is imported below —
    # see module docstring.
    _configure_gl_environment(args.software_render, args.gl_version_override)

    import time
    from stable_baselines3 import PPO
    from gym_pybullet_drones.utils.utils import sync

    from src.config import ProjectConfig
    from src.paths import hover_stabilize_model_path
    from src.training.gym_wrapper import HoverGymEnv

    model_path = args.model or str(hover_stabilize_model_path())

    config = ProjectConfig()
    config.sim.gui = True  # demo always shows the window, no --gui flag needed

    try:
        env = HoverGymEnv(config)
    except Exception:
        print(
            "\n[demo_intel] Failed to open the PyBullet GUI window. This is almost\n"
            "always a Mesa/OpenGL compatibility issue on integrated graphics, not a\n"
            "problem with the trained model. Things to try, in order:\n"
            "  1. python -m src.training.demo_intel --gl-version-override 3.3\n"
            "  2. python -m src.training.demo_intel --software-render\n"
            "If neither works, evaluate.py runs headless (no GUI) and still gives\n"
            "you real position-error/crash-rate numbers regardless of graphics support.\n"
        )
        raise

    model = PPO.load(model_path)

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

            while not (terminated or truncated):
                action, _ = model.predict(obs, deterministic=True)
                obs, reward, terminated, truncated, info = env.step(action)
                sync(step_i, start_time, timestep)  # paces to real time so it's watchable
                step_i += 1

            reason = info.get("truncation_reason", "n/a")
            print(f"episode {episode} ended: {reason} | final pos error: {info['position_error_norm']:.3f} m")

    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        env.close()


if __name__ == "__main__":
    main()
