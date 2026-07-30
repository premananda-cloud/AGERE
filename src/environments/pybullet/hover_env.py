"""
Active hover/stabilize training environment — built on top of
gym-pybullet-drones' HoverAviary rather than reimplementing physics.

This is the intentional "leverage the framework" choice: HoverAviary
already gives correct PyBullet dynamics, a working KIN observation space,
and (via ActionType.VEL) velocity-setpoint actions with an internal PID
controller — which is most of what we hand-built against MAVSDK in the
parked PX4 track. What this subclass adds on top:

  1. Config-driven target position / episode length / reward weights,
     instead of HoverAviary's hardcoded values, so PyBulletHoverConfig is
     the single source of truth (matches the rest of this project).
  2. Reward shaping closer to what we designed for the PX4 track (position
     error + velocity penalty + smoothness), instead of HoverAviary's
     default `max(0, 2 - ||pos_error||**4)`.
  3. True per-episode start-position randomization (HoverAviary doesn't
     randomize its own reset by default).

KNOWN LIMITATION (framework, not us): ActionType.VEL provides direction +
magnitude velocity control with NO yaw-rate command — BaseRLAviary's VEL
handler always passes `target_rpy=[0, 0, current_yaw]`, i.e. "hold whatever
yaw you're currently at." Real yaw stabilization would need ActionType.PID
(3D position deltas) or a custom action type. Left as-is for the first
working version since position hold, not yaw, is the primary hover goal —
revisit if yaw drift turns out to matter.
"""

import numpy as np

from gym_pybullet_drones.envs.HoverAviary import HoverAviary
from gym_pybullet_drones.utils.enums import ActionType, ObservationType, DroneModel, Physics

from src.config import PyBulletHoverConfig


_ACTION_TYPE_MAP = {
    "rpm": ActionType.RPM,
    "pid": ActionType.PID,
    "vel": ActionType.VEL,
    "one_d_rpm": ActionType.ONE_D_RPM,
    "one_d_pid": ActionType.ONE_D_PID,
}

_OBSERVATION_TYPE_MAP = {
    "kin": ObservationType.KIN,
    "rgb": ObservationType.RGB,
    "dep": ObservationType.DEP,
    "all": ObservationType.ALL,
}


class ConfigurableHoverAviary(HoverAviary):
    """HoverAviary with target/reward/episode params pulled from config,
    and true per-episode start-position randomization."""

    def __init__(self, task_config: PyBulletHoverConfig | None = None):
        self.task_config = task_config or PyBulletHoverConfig()

        act = _ACTION_TYPE_MAP[self.task_config.action_type]
        obs = _OBSERVATION_TYPE_MAP[self.task_config.observation_type]

        super().__init__(
            drone_model=DroneModel.CF2X,
            physics=Physics.PYB,
            pyb_freq=self.task_config.pyb_freq,
            ctrl_freq=self.task_config.ctrl_freq,
            gui=self.task_config.gui,
            record=False,
            obs=obs,
            act=act,
        )

        # Override HoverAviary's hardcoded defaults with config values.
        self.TARGET_POS = np.array(self.task_config.target_position)
        self.EPISODE_LEN_SEC = self.task_config.episode_len_sec
        self._prev_action = np.zeros(4, dtype=np.float32)

    # ------------------------------------------------------------------
    def reset(self, seed=None, options=None):
        # Randomize start position around the target before the parent's
        # reset() calls _housekeeping(), which reads INIT_XYZS/INIT_RPYS
        # fresh every episode (confirmed in BaseAviary source).
        rng = np.random.default_rng(seed)
        jitter = self.task_config.reset_position_jitter
        start_xyz = np.array(self.task_config.target_position) + rng.uniform(
            -jitter, jitter, size=3
        )
        start_xyz[2] = max(start_xyz[2], 0.1)  # never spawn below the ground plane

        yaw_jitter_rad = np.deg2rad(self.task_config.reset_yaw_jitter_deg)
        start_yaw = rng.uniform(-yaw_jitter_rad, yaw_jitter_rad)

        self.INIT_XYZS = start_xyz.reshape(1, 3)
        self.INIT_RPYS = np.array([[0.0, 0.0, start_yaw]])

        self._prev_action = np.zeros(4, dtype=np.float32)
        return super().reset(seed=seed, options=options)

    # ------------------------------------------------------------------
    def _computeReward(self):
        cfg = self.task_config
        state = self._getDroneStateVector(0)

        pos_error = np.linalg.norm(self.TARGET_POS - state[0:3])
        velocity = np.linalg.norm(state[10:13])
        # action_buffer[-1] is this env's most recent action (per-drone);
        # BaseRLAviary maintains this buffer for observation stacking, so
        # we reuse it rather than tracking our own copy.
        last_action = self.action_buffer[-1][0] if self.action_buffer else np.zeros(4)
        smoothness_penalty = np.linalg.norm(last_action - self._prev_action)
        self._prev_action = last_action

        reward = (
            -cfg.position_error_weight * pos_error
            - cfg.velocity_penalty_weight * velocity
            - cfg.action_smoothness_weight * smoothness_penalty
            + cfg.survival_bonus
        )
        return reward

    def _computeTerminated(self):
        # Match HoverAviary's near-exact-target early-stop behavior.
        state = self._getDroneStateVector(0)
        return bool(np.linalg.norm(self.TARGET_POS - state[0:3]) < 0.0001)

    def _computeTruncated(self):
        cfg = self.task_config
        state = self._getDroneStateVector(0)
        out_of_bounds = (
            abs(state[0]) > cfg.max_xy_distance
            or abs(state[1]) > cfg.max_xy_distance
            or state[2] > cfg.max_altitude
        )
        too_tilted = abs(state[7]) > cfg.max_tilt_rad or abs(state[8]) > cfg.max_tilt_rad
        timed_out = self.step_counter / self.PYB_FREQ > cfg.episode_len_sec
        return bool(out_of_bounds or too_tilted or timed_out)
