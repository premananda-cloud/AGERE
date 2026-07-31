"""
DroneSim: the PyBullet simulation layer. No RL concepts here — no reward,
no episode termination, no Gymnasium spaces. Just physics: reset to a
start state, apply a command, read state back.

Built on top of gym-pybullet-drones' HoverAviary as the physics engine.
Honest note on a real constraint: HoverAviary (and everything under it —
BaseRLAviary, BaseAviary) is itself built as a `gymnasium.Env` subclass
internally, since that's how the gym-pybullet-drones package is designed
from the ground up. This class does not re-expose that — no
action_space/observation_space attributes, no gym step()/reset() contract
on DroneSim itself — callers only see plain methods below. But it's worth
knowing the underlying library does depend on gymnasium; this wrapper
draws the "no Gymnasium" line at OUR module boundary, not by avoiding the
third-party dependency entirely. A from-scratch PyBullet physics
implementation would remove that dependency completely but is a much
larger rewrite than today's cleanup — not done here.
"""

from dataclasses import dataclass

import numpy as np
from gym_pybullet_drones.envs.HoverAviary import HoverAviary
from gym_pybullet_drones.utils.enums import ActionType, ObservationType, DroneModel, Physics

from src.actions.velocity_action import VelocityCommand
from src.config import SimConfig


@dataclass
class DroneState:
    position: np.ndarray          # (3,) x, y, z — world frame
    orientation_rpy: np.ndarray    # (3,) roll, pitch, yaw — radians
    velocity: np.ndarray           # (3,) vx, vy, vz
    angular_velocity: np.ndarray   # (3,) wx, wy, wz


class DroneSim:
    """Wraps gym-pybullet-drones' HoverAviary as a plain physics engine."""

    def __init__(self, sim_config: SimConfig):
        self.sim_config = sim_config
        self._aviary = HoverAviary(
            drone_model=DroneModel.CF2X,
            physics=Physics.PYB,
            pyb_freq=sim_config.pyb_freq,
            ctrl_freq=sim_config.ctrl_freq,
            gui=sim_config.gui,
            record=False,
            obs=ObservationType.KIN,
            act=ActionType.VEL,
        )

    def reset_episode(self, start_position: np.ndarray, start_yaw_rad: float) -> DroneState:
        """Reset the sim with the drone starting at a given position/yaw.

        Mutates INIT_XYZS/INIT_RPYS before calling the underlying reset() —
        confirmed against BaseAviary source that _housekeeping() reads
        these fresh on every reset(), so this gives true per-episode
        start randomization rather than always respawning at a fixed point.
        """
        start_position = np.asarray(start_position, dtype=np.float32)
        self._aviary.INIT_XYZS = start_position.reshape(1, 3)
        self._aviary.INIT_RPYS = np.array([[0.0, 0.0, start_yaw_rad]], dtype=np.float32)
        self._aviary.reset()
        return self.get_state()

    def apply_action(self, command: VelocityCommand) -> DroneState:
        """Advance the sim by one control step using a direction+speed command."""
        raw_action = np.array(
            [[command.direction[0], command.direction[1], command.direction[2], command.speed]],
            dtype=np.float32,
        )
        # The underlying HoverAviary.step() has a gym-shaped 5-tuple return
        # (obs, reward, terminated, truncated, info) — we deliberately
        # ignore all of it except the side effect of advancing physics.
        # Reward/termination are computed independently in the training-side
        # Gymnasium wrapper, using get_state() below, not this library's
        # built-in values.
        self._aviary.step(raw_action)
        return self.get_state()

    def get_state(self) -> DroneState:
        state = self._aviary._getDroneStateVector(0)
        return DroneState(
            position=state[0:3],
            orientation_rpy=state[7:10],
            velocity=state[10:13],
            angular_velocity=state[13:16],
        )

    def draw_target_marker(self, position: np.ndarray):
        """Draw a visual-only sphere at `position` (GUI mode only — no
        physical effect on the sim). Purely for presentations/demos so a
        viewer can see what the drone is trying to hold station at, since
        gym-pybullet-drones' GUI doesn't show the target by default."""
        import pybullet as p

        if not self.sim_config.gui:
            return
        visual_shape = p.createVisualShape(
            p.GEOM_SPHERE, radius=0.05, rgbaColor=[0.2, 0.9, 0.2, 0.5],
            physicsClientId=self._aviary.CLIENT,
        )
        p.createMultiBody(
            baseMass=0,
            baseVisualShapeIndex=visual_shape,
            basePosition=position,
            physicsClientId=self._aviary.CLIENT,
        )

    def close(self):
        self._aviary.close()
