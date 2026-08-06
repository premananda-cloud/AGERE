"""
WaypointGymEnv: the Gymnasium environment for waypoint navigation +
landing.

Mirrors HoverGymEnv's split (Gymnasium concerns here, pure physics in
DroneSim) — see hover_gym_wrapper.py and docs/code-structure.md. Two
things are genuinely different from hover, not just cosmetic:

1. There's a moving target. "Target" for observation/reward purposes is
   the current waypoint's position while the route is in progress, and
   switches to a fixed landing target (xy of the final waypoint, low
   altitude) once the route completes. self._current_target() is the
   single place that decides which.

2. This task has a real endpoint. Hover always ends via truncation
   (timeout/out_of_bounds/tilt) — there's no "done, succeeded" state,
   just "still going" or "failed/timed out." Waypoint nav can actually
   finish: reach every waypoint, then hold a soft landing for
   landing_hold_time_sec, and the episode TERMINATES (not truncates) as
   a success. This is why `terminated` is no longer hardcoded False here
   the way it is in hover_gym_wrapper.py.
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from src.actions.velocity_action import ACTION_DIM, normalize_action
from src.config import ProjectConfig
from src.environments.drone_sim import DroneSim


class WaypointGymEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: ProjectConfig | None = None):
        super().__init__()
        self.config = config or ProjectConfig()
        self.task = self.config.task

        self.sim = DroneSim(self.config.sim)

        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32
        )
        # 10 floats: pos_error (3), velocity (3), roll/pitch/yaw_error (3),
        # landing_phase flag (1). The flag is new vs. hover's 9 — nav and
        # landing genuinely call for different behavior (converge-and-hold
        # near a waypoint vs. controlled descent-and-stop), so the policy
        # gets an explicit signal for which regime it's in rather than
        # having to infer it indirectly from position/velocity alone.
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(10,), dtype=np.float32
        )

        self._waypoints = [np.asarray(wp, dtype=np.float32) for wp in self.task.waypoints]
        self._step_count = 0
        self._max_steps = int(self.task.episode_len_sec * self.config.sim.ctrl_freq)
        self._target_yaw_rad = 0.0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)

        self._waypoint_idx = 0          # index into self._waypoints of the
                                          # current target; == len(waypoints)
                                          # once the route is complete
        self._in_landing = False
        self._landing_hold_steps = 0     # consecutive steps meeting the
                                          # soft-landing condition

    # ------------------------------------------------------------------
    def _landing_target(self) -> np.ndarray:
        """xy of the final waypoint, at the configured landing altitude."""
        last_wp = self._waypoints[-1]
        return np.array([last_wp[0], last_wp[1], self.task.landing_target_altitude], dtype=np.float32)

    def _current_target(self) -> np.ndarray:
        if self._in_landing:
            return self._landing_target()
        return self._waypoints[self._waypoint_idx]

    def _obs_from_state(self, state) -> np.ndarray:
        pos_error = self._current_target() - state.position
        yaw_error = self._target_yaw_rad - state.orientation_rpy[2]
        yaw_error = (yaw_error + np.pi) % (2 * np.pi) - np.pi  # wrap to [-pi, pi]
        return np.concatenate(
            [
                pos_error,
                state.velocity,
                np.array([state.orientation_rpy[0], state.orientation_rpy[1], yaw_error], dtype=np.float32),
                np.array([1.0 if self._in_landing else 0.0], dtype=np.float32),
            ]
        ).astype(np.float32)

    def _advance_waypoint_if_reached(self, obs: np.ndarray) -> float:
        """Checks distance to the current waypoint; advances the index and
        returns a one-time bonus if reached. Returns 0.0 otherwise (and
        always 0.0 once in the landing phase — this only governs the
        waypoint-following part of the route).

        Called once per step, before reward is computed, so the bonus
        lands in the same step the waypoint was reached rather than one
        step later.
        """
        if self._in_landing:
            return 0.0

        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        if pos_error_norm > self.task.waypoint_reach_radius:
            return 0.0

        self._waypoint_idx += 1
        if self._waypoint_idx >= len(self._waypoints):
            self._in_landing = True
            self._landing_hold_steps = 0
        return self.task.waypoint_bonus

    def _compute_reward(self, obs: np.ndarray, action: np.ndarray, waypoint_bonus: float) -> float:
        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        vel_norm = float(np.linalg.norm(obs[3:6]))
        action_delta = float(np.linalg.norm(action - self._prev_action))

        # Landing phase uses a heavier velocity penalty (per config docstring:
        # specifically to punish crashing into the ground fast) in place of
        # the general one — not in addition to it, since both terms penalize
        # the same vel_norm and stacking them would double-count.
        vel_weight = (
            self.task.landing_velocity_penalty_weight if self._in_landing
            else self.task.velocity_penalty_weight
        )

        return (
            -self.task.position_error_weight * pos_error_norm
            - vel_weight * vel_norm
            - self.task.action_smoothness_weight * action_delta
            + self.task.survival_bonus
            + waypoint_bonus
        )

    def _check_landing(self, state) -> bool:
        """Updates the landing hold-timer and returns True on a completed
        (successful) soft landing. Only called while self._in_landing.

        Contact is modeled as altitude at-or-below landing_target_altitude
        (see config.py's note on why that's not exactly 0) — a deliberate
        altitude+velocity simplification rather than real PyBullet contact
        detection; flagged in the handoff as fine for a demo, worth
        revisiting for more precision later.
        """
        vel_norm = float(np.linalg.norm(state.velocity))
        touched_down = state.position[2] <= self.task.landing_target_altitude

        if not touched_down:
            self._landing_hold_steps = 0
            return False

        if vel_norm > self.task.landing_max_velocity:
            # Ground contact at unsafe speed — handled as a hard_landing
            # truncation by the caller, not treated as a hold-timer reset;
            # the caller checks this same condition separately.
            return False

        self._landing_hold_steps += 1
        hold_steps_needed = int(round(self.task.landing_hold_time_sec * self.config.sim.ctrl_freq))
        return self._landing_hold_steps >= hold_steps_needed

    def _truncation_reason(self, state) -> str | None:
        """Same out_of_bounds/tilt/timeout pattern as hover_gym_wrapper.py,
        plus hard_landing: fast ground contact during the landing phase.
        Does NOT check for successful landing — that's a termination
        (see step()), handled separately since it's a success, not a
        failure/timeout end.
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
        if self._in_landing:
            vel_norm = float(np.linalg.norm(state.velocity))
            touched_down = state.position[2] <= self.task.landing_target_altitude
            if touched_down and vel_norm > self.task.landing_max_velocity:
                return "hard_landing"
        if self._step_count >= self._max_steps:
            return "timeout"
        return None

    # ------------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        first_wp = self._waypoints[0]
        jitter = self.task.reset_position_jitter
        start_position = first_wp + self.np_random.uniform(-jitter, jitter, size=3)
        start_position[2] = max(start_position[2], 0.1)  # never spawn below ground

        yaw_jitter_rad = np.deg2rad(self.task.reset_yaw_jitter_deg)
        self._target_yaw_rad = 0.0
        start_yaw = self.np_random.uniform(-yaw_jitter_rad, yaw_jitter_rad)

        state = self.sim.reset_episode(start_position, start_yaw)

        self._step_count = 0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)
        self._waypoint_idx = 0
        self._in_landing = False
        self._landing_hold_steps = 0

        obs = self._obs_from_state(state)
        info = {
            "start_position": start_position.copy(),
            "start_yaw_rad": float(start_yaw),
        }
        return obs, info

    def step(self, action: np.ndarray):
        command = normalize_action(action)
        state = self.sim.apply_action(command)

        obs = self._obs_from_state(state)
        waypoint_bonus = self._advance_waypoint_if_reached(obs)
        # Re-derive obs if this step just flipped into landing: pos_error
        # in obs above was computed against the *pre-advance* target, which
        # would be one step stale (still the just-reached waypoint, not the
        # landing target) for the very step the route completes.
        if self._in_landing and waypoint_bonus > 0.0:
            obs = self._obs_from_state(state)

        reward = self._compute_reward(obs, action, waypoint_bonus)

        self._step_count += 1

        success = self._in_landing and self._check_landing(state)
        reason = None if success else self._truncation_reason(state)
        terminated = success
        truncated = (not success) and (reason is not None)

        info = {
            "position_error_norm": float(np.linalg.norm(obs[0:3])),
            "waypoints_reached": min(self._waypoint_idx, len(self._waypoints)),
            "success": success,
        }
        if truncated:
            info["truncation_reason"] = reason
            info["is_crash"] = reason in ("out_of_bounds", "tilt", "hard_landing")

        self._prev_action = np.asarray(action, dtype=np.float32)
        return obs, reward, terminated, truncated, info

    def close(self):
        self.sim.close()
