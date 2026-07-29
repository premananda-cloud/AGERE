"""
HoverStabilizeEnv: a Gymnasium environment where the agent learns to hold
station at a target point in local NED coordinates.

Observation (9 floats, all relative — not absolute — so the policy
generalizes to any hover target):
    [pos_error_n, pos_error_e, pos_error_d,   # target - current position
     vx, vy, vz,                              # current velocity
     roll_deg, pitch_deg, yaw_error_deg]       # attitude / yaw error

Action (4 floats, normalized [-1, 1], scaled by VelocityActionSpace):
    [vx, vy, vz, yaw_rate]
"""

import time

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from src.actions.velocity_action import VelocityActionSpace
from src.config import ProjectConfig
from src.environments.px4_interface import PX4Interface


def _wrap_deg(angle: float) -> float:
    """Wrap an angle in degrees to [-180, 180]."""
    return (angle + 180.0) % 360.0 - 180.0


class HoverStabilizeEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, config: ProjectConfig | None = None):
        super().__init__()
        self.config = config or ProjectConfig()
        self.task = self.config.task

        self.action_helper = VelocityActionSpace(self.config.action_limits)
        self.action_space = self.action_helper.space
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(9,), dtype=np.float32
        )

        self.px4 = PX4Interface(self.config.control)
        self._connected = False

        self._step_count = 0
        self._target_yaw_deg = 0.0
        self._prev_action = np.zeros(4, dtype=np.float32)

    # ------------------------------------------------------------------
    def _ensure_connected(self):
        if not self._connected:
            self.px4.connect()
            self._connected = True

    def _get_obs(self) -> np.ndarray:
        state = self.px4.get_state()
        tgt_n, tgt_e, tgt_d = self.task.target_position
        pos_error = np.array(
            [tgt_n - state.north, tgt_e - state.east, tgt_d - state.down],
            dtype=np.float32,
        )
        velocity = np.array([state.vx, state.vy, state.vz], dtype=np.float32)
        yaw_error = _wrap_deg(self._target_yaw_deg - state.yaw_deg)
        attitude = np.array(
            [state.roll_deg, state.pitch_deg, yaw_error], dtype=np.float32
        )
        return np.concatenate([pos_error, velocity, attitude])

    def _compute_reward(self, obs: np.ndarray, action: np.ndarray) -> float:
        pos_error = obs[0:3]
        velocity = obs[3:6]
        roll, pitch, _ = obs[6], obs[7], obs[8]

        pos_error_norm = float(np.linalg.norm(pos_error))
        vel_norm = float(np.linalg.norm(velocity))
        angular_proxy = abs(roll) + abs(pitch)  # cheap proxy for angular rate
        action_delta = float(np.linalg.norm(action - self._prev_action))

        reward = (
            -self.task.position_error_weight * pos_error_norm
            - self.task.velocity_penalty_weight * vel_norm
            - self.task.angular_rate_penalty_weight * angular_proxy
            - self.task.action_smoothness_weight * action_delta
            + self.task.survival_bonus
        )
        return reward

    def _is_terminated(self, obs: np.ndarray) -> bool:
        pos_error_norm = float(np.linalg.norm(obs[0:3]))
        roll, pitch = abs(obs[6]), abs(obs[7])
        if pos_error_norm > self.task.max_position_error:
            return True
        if roll > self.task.max_tilt_deg or pitch > self.task.max_tilt_deg:
            return True
        return False

    # ------------------------------------------------------------------
    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        self._ensure_connected()

        # NOTE: true per-episode re-randomized start position requires
        # either respawning in Gazebo (SITL-only trick, not available on
        # real hardware) or flying to a jittered start point before the
        # episode begins. For the first working version we land/re-arm/
        # takeoff and treat the takeoff point plus small settle time as
        # "close enough to randomized" via natural drift. Revisit once
        # this loop is confirmed working end to end.
        self.px4.arm_and_takeoff(altitude_m=abs(self.task.target_position[2]))
        time.sleep(1.0)  # let telemetry populate

        self._target_yaw_deg = self.np_random.uniform(
            -self.task.reset_yaw_jitter_deg, self.task.reset_yaw_jitter_deg
        )
        self._step_count = 0
        self._prev_action = np.zeros(4, dtype=np.float32)

        obs = self._get_obs()
        return obs, {}

    def step(self, action: np.ndarray):
        setpoint = self.action_helper.scale(action)
        self.px4.send_velocity_body(
            setpoint.vx, setpoint.vy, setpoint.vz, setpoint.yaw_rate_deg
        )
        time.sleep(self.config.control.control_dt)

        obs = self._get_obs()
        reward = self._compute_reward(obs, action)
        terminated = self._is_terminated(obs)

        self._step_count += 1
        truncated = self._step_count >= self.task.max_episode_steps

        self._prev_action = np.asarray(action, dtype=np.float32)
        return obs, reward, terminated, truncated, {}

    def close(self):
        if self._connected:
            self.px4.land_and_disarm()
