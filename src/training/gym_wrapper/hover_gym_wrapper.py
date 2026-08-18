"""
HoverGymEnv: the Gymnasium environment for the hover/stabilize task.

This is where Gymnasium lives — action_space, observation_space, reward,
episode termination/truncation. It wraps DroneSim (pure PyBullet, no RL
concepts) and adds everything RL-specific on top. See docs/code-structure.md
for the reasoning behind this split.
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from src.actions.velocity_action import ACTION_DIM, normalize_action
from src.config import ProjectConfig
from src.environments.drone_sim import DroneSim


class HoverGymEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: ProjectConfig | None = None):
        super().__init__()
        self.config = config or ProjectConfig()
        self.task = self.config.task

        self.sim = DroneSim(self.config.sim)

        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32
        )
        # 9 floats: pos_error (3), velocity (3), roll/pitch/yaw_error (3).
        # Relative pos_error and yaw_error (not absolute position/yaw) so
        # the policy generalizes to any target rather than memorizing one.
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(9,), dtype=np.float32
        )

        self._step_count = 0
        self._max_steps = int(self.task.episode_len_sec * self.config.sim.ctrl_freq)
        self._target_yaw_rad = 0.0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)

        # --- Disturbance (Stage 1, 2026-08-16) -----------------------------
        # Per-episode kick schedule and recovery-tracking state. All reset in
        # reset(); see that method for the sampling logic and step() for
        # when kicks actually fire and how recovery is measured. Kept as
        # plain instance state (not a separate class) since HoverGymEnv
        # already owns all other per-episode state the same way
        # (_step_count, _prev_action).
        self._pending_kick_steps: list[int] = []
        self._last_kick_step: int | None = None
        self._recovery_hold_counter = 0
        self._recovery_achieved = False
        self._recovery_time_steps: int | None = None
        self._any_kick_fired = False

    def _sample_kick_schedule(self) -> list[int]:
        """Sample this episode's kick step(s), respecting the configured
        step window and minimum spacing between kicks. Returns a sorted
        list of control-step indices at which a kick will fire — empty if
        disturbance is disabled for this task config.

        Only called from reset(); step() just consumes this list in order.
        """
        if not getattr(self.task, "disturbance_enabled", False):
            return []

        n = self.task.disturbance_kicks_per_episode
        lo, hi = self.task.disturbance_kick_step_min, self.task.disturbance_kick_step_max
        # Clamp the window to fit inside this episode -- a longer-episode
        # config (Stage 1 sub-stages 1d+) may reuse the same window values
        # unmodified; this guards against a misconfigured window exceeding
        # _max_steps rather than silently sampling an invalid step.
        hi = min(hi, self._max_steps - 1)
        if lo >= hi:
            return []

        min_spacing = self.task.disturbance_min_kick_spacing_steps
        steps: list[int] = []
        attempts = 0
        while len(steps) < n and attempts < 100:
            attempts += 1
            candidate = int(self.np_random.integers(lo, hi + 1))
            if all(abs(candidate - s) >= min_spacing for s in steps):
                steps.append(candidate)
        return sorted(steps)

    # ------------------------------------------------------------------
    def _obs_from_state(self, state) -> np.ndarray:
        pos_error = np.asarray(self.task.target_position, dtype=np.float32) - state.position
        yaw_error = self._target_yaw_rad - state.orientation_rpy[2]
        # wrap to [-pi, pi]
        yaw_error = (yaw_error + np.pi) % (2 * np.pi) - np.pi
        return np.concatenate(
            [
                pos_error,
                state.velocity,
                np.array([state.orientation_rpy[0], state.orientation_rpy[1], yaw_error], dtype=np.float32),
            ]
        ).astype(np.float32)

    def _compute_reward(self, obs: np.ndarray, action: np.ndarray) -> float:
        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        vel_norm = float(np.linalg.norm(obs[3:6]))
        action_delta = float(np.linalg.norm(action - self._prev_action))

        return (
            -self.task.position_error_weight * pos_error_norm
            - self.task.velocity_penalty_weight * vel_norm
            - self.task.action_smoothness_weight * action_delta
            + self.task.survival_bonus
        )

    def _truncation_reason(self, obs: np.ndarray, state) -> str | None:
        """Returns why an episode ended, or None if it's still going.

        Distinguishing "crash" (out_of_bounds/tilt) from "timeout" matters
        for evaluation — see docs/hover-model-plan.md Stage 2, which
        requires <10% crash rate specifically, not just "episode ended."
        """
        x, y = state.position[0], state.position[1]
        roll, pitch = state.orientation_rpy[0], state.orientation_rpy[1]
        if (
            abs(x) > self.task.max_xy_distance
            or abs(y) > self.task.max_xy_distance
            or state.position[2] > self.task.max_altitude
        ):
            return "out_of_bounds"
        if abs(roll) > self.task.max_tilt_rad or abs(pitch) > self.task.max_tilt_rad:
            return "tilt"
        if self._step_count >= self._max_steps:
            return "timeout"
        return None

    # ------------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        jitter = self.task.reset_position_jitter
        start_position = np.asarray(self.task.target_position, dtype=np.float32) + self.np_random.uniform(
            -jitter, jitter, size=3
        )
        start_position[2] = max(start_position[2], 0.1)  # never spawn below ground

        yaw_jitter_rad = np.deg2rad(self.task.reset_yaw_jitter_deg)
        self._target_yaw_rad = 0.0
        start_yaw = self.np_random.uniform(-yaw_jitter_rad, yaw_jitter_rad)

        state = self.sim.reset_episode(start_position, start_yaw)

        self._step_count = 0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)

        # Disturbance state, per-episode -- sampled AFTER super().reset()
        # seeds self.np_random, so this respects the same seed as the rest
        # of the episode's randomization (position/yaw jitter above).
        self._pending_kick_steps = self._sample_kick_schedule()
        self._last_kick_step = None
        self._recovery_hold_counter = 0
        self._recovery_achieved = False
        self._recovery_time_steps = None
        self._any_kick_fired = False

        obs = self._obs_from_state(state)
        # Exposed so callers (evaluate.py's tail diagnostics, in particular)
        # can correlate final outcome with the randomized start condition,
        # rather than only ever seeing the post-jitter obs.
        info = {
            "start_position": start_position.copy(),
            "start_yaw_rad": float(start_yaw),
        }
        return obs, info

    def step(self, action: np.ndarray):
        command = normalize_action(action)
        state = self.sim.apply_action(command)

        obs = self._obs_from_state(state)
        reward = self._compute_reward(obs, action)

        self._step_count += 1

        # --- Disturbance: fire a scheduled kick, if this is the step for one ---
        # Applied AFTER apply_action() advances physics for this step, so the
        # kick's effect is visible starting next step's observation -- matches
        # apply_velocity_kick()'s own semantics (instantaneous velocity add,
        # not routed through this step's control command).
        if self._pending_kick_steps and self._step_count == self._pending_kick_steps[0]:
            direction = self.np_random.normal(size=3)
            norm = np.linalg.norm(direction)
            direction = direction / norm if norm > 1e-6 else np.array([1.0, 0.0, 0.0])
            magnitude = self.np_random.uniform(
                self.task.disturbance_kick_min_mps, self.task.disturbance_kick_max_mps
            )
            self.sim.apply_velocity_kick(direction * magnitude)
            self._pending_kick_steps.pop(0)
            self._last_kick_step = self._step_count
            self._any_kick_fired = True
            # A new kick resets the recovery streak -- if a second kick lands
            # before the first's hold window completed, recovery is judged
            # against the MOST RECENT kick only (multi-kick sub-stages 1e/1f).
            self._recovery_hold_counter = 0
            self._recovery_achieved = False

        # --- Recovery tracking, relative to the most recent kick ---------
        if self._last_kick_step is not None and not self._recovery_achieved:
            pos_error_norm = float(np.linalg.norm(obs[0:3]))
            if pos_error_norm < self.task.recovery_threshold_m:
                self._recovery_hold_counter += 1
                if self._recovery_hold_counter >= self.task.recovery_hold_steps:
                    self._recovery_achieved = True
                    # Steps from kick to the START of the sustained-recovery
                    # window, not to when the hold finished -- this is the
                    # number that actually reflects "how fast did it recover,"
                    # per the plan doc's per-trial logging spec.
                    self._recovery_time_steps = (
                        self._step_count - self._recovery_hold_counter + 1 - self._last_kick_step
                    )
            else:
                self._recovery_hold_counter = 0  # violation resets the streak, same
                                                   # non-momentary-touch pattern as
                                                   # landing_hold_time_sec elsewhere

        reason = self._truncation_reason(obs, state)
        truncated = reason is not None
        terminated = False  # this task has no early-success condition; it
        # ends via truncation (out of bounds / tilt / timeout) only

        info = {}
        if truncated:
            info["truncation_reason"] = reason
            info["is_crash"] = reason in ("out_of_bounds", "tilt")
        info["position_error_norm"] = float(np.linalg.norm(obs[0:3]))

        # Disturbance summary info, only meaningful (and only populated) once
        # the episode has actually seen a kick -- evaluate.py should check
        # "kicked" before reading "recovered"/"recovery_time_steps".
        if self._any_kick_fired:
            info["kicked"] = True
            info["recovered"] = self._recovery_achieved
            info["recovery_time_steps"] = self._recovery_time_steps

        self._prev_action = np.asarray(action, dtype=np.float32)
        return obs, reward, terminated, truncated, info

    def close(self):
        self.sim.close()
