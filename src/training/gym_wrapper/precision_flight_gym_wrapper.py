"""
PrecisionFlightGymEnv: takeoff -> hover -> land, trained as ONE episode,
ONE policy (added 2026-08-11 -- see docs/decisions/devlog/2026_08_11.md
for why waypoint nav was paused in favor of this task).

Observation/action spaces are identical to HoverGymEnv's (9 floats / 4
floats) -- deliberately, so a hover_stabilize checkpoint can warm-start
this the same way hover_stabilize warm-started waypoint_nav_ppo. What
transfers: "hold station, don't move too fast." What's new here: the
target the policy is chasing moves through three phases within one
episode, switched by simple deterministic rules (see
PrecisionFlightTaskConfig's docstring) -- NOT anything the policy itself
decides. The policy never sees which phase it's in as an explicit input
(same design choice WaypointGymEnv made about its landing_phase flag, for
the same reason: PPO.load() rebuilds the input layer from the saved obs
shape, so a phase-flag dimension would break warm-starting from hover).

Phase transitions (all deterministic, no learning involved):
  TAKEOFF -> HOVER:   pos_error to hover_target < takeoff_arrival_radius
  HOVER   -> LANDING: hover phase has been held for hover_hold_duration_sec
  LANDING -> success (terminated=True): altitude + velocity within landing
                      thresholds, held continuously for landing_hold_time_sec

Disturbance injection (2026-08-11's "edge cases" goal) happens only during
the HOVER phase, via DroneSim.apply_velocity_kick() -- already existed,
built for Stage 3's disturbance criterion, not added here. Not applied
during takeoff/landing: getting kicked mid-climb or mid-descent is a
meaningfully different (harder, less-motivated-by-the-actual-goal)
problem than recovering from a kick while already holding station, and
conflating the two in one training signal risks muddying both. Revisit
if takeoff/landing robustness specifically becomes a goal later.
"""

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from src.actions.velocity_action import ACTION_DIM, normalize_action
from src.config import ProjectConfig
from src.environments.drone_sim import DroneSim

PHASE_TAKEOFF = "takeoff"
PHASE_HOVER = "hover"
PHASE_LANDING = "landing"


class PrecisionFlightGymEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: ProjectConfig | None = None):
        super().__init__()
        self.config = config or ProjectConfig()
        self.task = self.config.task

        self.sim = DroneSim(self.config.sim)

        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(ACTION_DIM,), dtype=np.float32
        )
        # Same 9-float shape as HoverGymEnv, deliberately -- see module
        # docstring for why (warm-start compatibility).
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(9,), dtype=np.float32
        )

        self._step_count = 0
        self._max_steps = int(self.task.episode_len_sec * self.config.sim.ctrl_freq)
        self._dt = 1.0 / self.config.sim.ctrl_freq
        self._target_yaw_rad = 0.0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)

        self._phase = PHASE_TAKEOFF
        self._hover_elapsed = 0.0
        self._landing_hold_elapsed = 0.0

    # ------------------------------------------------------------------
    def _current_target(self) -> np.ndarray:
        if self._phase == PHASE_LANDING:
            return np.asarray(self.task.ground_position, dtype=np.float32)
        # TAKEOFF and HOVER both chase the same point -- takeoff is just
        # "hasn't arrived at the hover target yet."
        return np.asarray(self.task.hover_target, dtype=np.float32)

    def _obs_from_state(self, state) -> np.ndarray:
        target = self._current_target()
        pos_error = target - state.position
        yaw_error = self._target_yaw_rad - state.orientation_rpy[2]
        yaw_error = (yaw_error + np.pi) % (2 * np.pi) - np.pi
        return np.concatenate(
            [
                pos_error,
                state.velocity,
                np.array([state.orientation_rpy[0], state.orientation_rpy[1], yaw_error], dtype=np.float32),
            ]
        ).astype(np.float32)

    def _maybe_apply_disturbance(self):
        if not self.task.disturbance_enabled or self._phase != PHASE_HOVER:
            return
        if self.np_random.random() < self.task.disturbance_prob_per_step:
            direction = self.np_random.normal(size=3)
            norm = np.linalg.norm(direction)
            if norm < 1e-6:
                return
            direction = direction / norm
            magnitude = self.np_random.uniform(*self.task.disturbance_kick_range)
            self.sim.apply_velocity_kick(direction * magnitude)

    def _advance_phase(self, obs: np.ndarray, state) -> None:
        """Deterministic phase supervisor -- see module docstring. Runs
        once per step, after the action has been applied and the new
        state/obs are known."""
        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        vel_norm = float(np.linalg.norm(state.velocity))

        if self._phase == PHASE_TAKEOFF:
            if pos_error_norm < self.task.takeoff_arrival_radius:
                self._phase = PHASE_HOVER

        elif self._phase == PHASE_HOVER:
            self._hover_elapsed += self._dt
            if self._hover_elapsed >= self.task.hover_hold_duration_sec:
                self._phase = PHASE_LANDING

        elif self._phase == PHASE_LANDING:
            altitude = float(state.position[2])
            soft_and_low = (
                altitude <= self.task.landing_target_altitude
                and vel_norm <= self.task.landing_max_velocity
            )
            if soft_and_low:
                self._landing_hold_elapsed += self._dt
            else:
                self._landing_hold_elapsed = 0.0  # reset -- must be continuous, not cumulative

    def _compute_reward(self, obs: np.ndarray, action: np.ndarray, state) -> float:
        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        vel_norm = float(np.linalg.norm(obs[3:6]))
        action_delta = float(np.linalg.norm(action - self._prev_action))

        # Landing phase swaps in a heavier, landing-specific velocity
        # penalty in place of the general one -- same pattern
        # WaypointTaskConfig uses, see that config's docstring for why
        # (REPLACES, not additive).
        if self._phase == PHASE_LANDING:
            velocity_term = self.task.landing_velocity_penalty_weight * vel_norm
        else:
            velocity_term = self.task.velocity_penalty_weight * vel_norm

        reward = (
            -self.task.position_error_weight * pos_error_norm
            - velocity_term
            - self.task.action_smoothness_weight * action_delta
            + self.task.survival_bonus
        )

        if self._phase == PHASE_HOVER and pos_error_norm < self.task.hover_precision_radius:
            reward += self.task.precision_bonus

        return reward

    def _truncation_reason(self, state) -> str | None:
        x, y = state.position[0], state.position[1]
        altitude = state.position[2]
        roll, pitch = state.orientation_rpy[0], state.orientation_rpy[1]
        vel_norm = float(np.linalg.norm(state.velocity))

        if abs(x) > self.task.max_xy_distance or abs(y) > self.task.max_xy_distance or altitude > self.task.max_altitude:
            return "out_of_bounds"
        if abs(roll) > self.task.max_tilt_rad or abs(pitch) > self.task.max_tilt_rad:
            return "tilt"
        # Hard landing: touched near-ground altitude too fast, in ANY
        # phase -- not just while already in the landing phase, since a
        # crash during takeoff or a disturbance-induced fall during hover
        # is just as much a hard landing as one during the landing phase
        # itself. Threshold is a first-pass guess (3x the soft-landing
        # velocity threshold) -- not validated against any real run yet.
        if altitude <= self.task.landing_target_altitude and vel_norm > (self.task.landing_max_velocity * 3):
            return "hard_landing"
        if self._step_count >= self._max_steps:
            return "timeout"
        return None

    def _landing_success(self) -> bool:
        return (
            self._phase == PHASE_LANDING
            and self._landing_hold_elapsed >= self.task.landing_hold_time_sec
        )

    # ------------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)

        jitter = self.task.reset_position_jitter
        start_position = np.asarray(self.task.ground_position, dtype=np.float32) + self.np_random.uniform(
            -jitter, jitter, size=3
        )
        start_position[2] = max(start_position[2], 0.02)  # never spawn below ground

        yaw_jitter_rad = np.deg2rad(self.task.reset_yaw_jitter_deg)
        self._target_yaw_rad = 0.0
        start_yaw = self.np_random.uniform(-yaw_jitter_rad, yaw_jitter_rad)

        state = self.sim.reset_episode(start_position, start_yaw)

        self._step_count = 0
        self._prev_action = np.zeros(ACTION_DIM, dtype=np.float32)
        self._phase = PHASE_TAKEOFF
        self._hover_elapsed = 0.0
        self._landing_hold_elapsed = 0.0

        obs = self._obs_from_state(state)
        info = {
            "start_position": start_position.copy(),
            "start_yaw_rad": float(start_yaw),
            "phase": self._phase,
        }
        return obs, info

    def step(self, action: np.ndarray):
        command = normalize_action(action)
        state = self.sim.apply_action(command)

        self._maybe_apply_disturbance()

        obs = self._obs_from_state(state)
        reward = self._compute_reward(obs, action, state)

        self._step_count += 1
        self._advance_phase(obs, state)

        success = self._landing_success()
        terminated = success   # this task DOES have an early-success condition, unlike HoverGymEnv
        reason = self._truncation_reason(state)
        truncated = (reason is not None) and not terminated

        info = {
            "phase": self._phase,
            "position_error_norm": float(np.linalg.norm(obs[0:3])),
            "success": success,
            "hover_elapsed": self._hover_elapsed,
        }
        if truncated:
            info["truncation_reason"] = reason
            info["is_crash"] = reason in ("out_of_bounds", "tilt", "hard_landing")

        self._prev_action = np.asarray(action, dtype=np.float32)
        return obs, reward, terminated, truncated, info

    def close(self):
        self.sim.close()
