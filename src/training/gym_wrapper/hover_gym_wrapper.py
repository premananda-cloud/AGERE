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
        reason = self._truncation_reason(obs, state)
        truncated = reason is not None
        terminated = False  # this task has no early-success condition; it
        # ends via truncation (out of bounds / tilt / timeout) only

        info = {}
        if truncated:
            info["truncation_reason"] = reason
            info["is_crash"] = reason in ("out_of_bounds", "tilt")
        info["position_error_norm"] = float(np.linalg.norm(obs[0:3]))

        self._prev_action = np.asarray(action, dtype=np.float32)
        return obs, reward, terminated, truncated, info

    def close(self):
        self.sim.close()
