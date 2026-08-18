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
            record=sim_config.record,
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

    def apply_velocity_kick(self, delta_velocity: np.ndarray) -> None:
        """Instantaneously add `delta_velocity` (m/s, world frame) to the
        drone's current linear velocity — for simulating a mid-episode
        disturbance (Stage 3 criterion 3, docs/hover-model-plan.md).

        Uses PyBullet's resetBaseVelocity, which is a direct kinematic
        override rather than something routed through the physics solver
        (confirmed against PyBullet's own docs/forum discussion) —
        appropriate here since the drone isn't in contact with anything,
        and it gives a clean, well-defined kick that isn't sensitive to
        internal physics-substep timing the way apply_impulse_force()
        below is (see that method's docstring). Prefer this method unless
        you specifically want the literal applyExternalForce mechanism the
        plan doc names as an example.

        Only linearVelocity is passed to resetBaseVelocity — confirmed
        each of linearVelocity/angularVelocity is an independently
        optional parameter, not "pass both or the other resets to zero,"
        so this leaves current angular velocity (yaw/tilt rate) untouched.
        """
        import pybullet as p

        current = self.get_state().velocity
        new_velocity = np.asarray(current, dtype=np.float64) + np.asarray(delta_velocity, dtype=np.float64)
        p.resetBaseVelocity(
            self._aviary.DRONE_IDS[0],
            linearVelocity=new_velocity.tolist(),
            physicsClientId=self._aviary.CLIENT,
        )

    def apply_impulse_force(self, force: np.ndarray) -> None:
        """Apply a one-shot external force (Newtons, world frame) at the
        drone's current position, via PyBullet's applyExternalForce — the
        mechanism docs/hover-model-plan.md names directly as an example
        for Stage 3 criterion 3.

        Real caveat, confirmed against PyBullet's own docs: "After each
        simulation step, the external forces are cleared to zero."
        HoverAviary.step() (called from apply_action() below) runs several
        physics substeps internally per control step (pyb_freq/ctrl_freq
        of them) that this class has no hook into — so a single call here
        only actually acts on the FIRST physics substep of the next
        apply_action() call, not the whole control step. That's a
        legitimate model of a literal impulse (a brief force) rather than
        a sustained push, but the "brief" part is a consequence of this
        constraint, not a tunable choice. For a kick whose magnitude
        doesn't depend on substep timing, prefer apply_velocity_kick()
        above; this method exists because the plan doc names
        applyExternalForce specifically.
        """
        import pybullet as p

        state = self.get_state()
        p.applyExternalForce(
            objectUniqueId=self._aviary.DRONE_IDS[0],
            linkIndex=-1,
            forceObj=np.asarray(force, dtype=np.float64).tolist(),
            posObj=state.position.tolist(),
            flags=p.WORLD_FRAME,
            physicsClientId=self._aviary.CLIENT,
        )

    def draw_target_marker(self, position: np.ndarray, color: tuple = (0.2, 0.9, 0.2, 0.5), radius: float = 0.05):
        """Draw a visual-only sphere at `position` (GUI mode only — no
        physical effect on the sim). Purely for presentations/demos.

        color/radius are parameterized (not hardcoded) so callers with
        multiple markers to distinguish — e.g. a waypoint route showing
        passed/current/upcoming stops — can vary appearance per call without
        needing a second method. Defaults match the original single-target
        hover marker exactly, so HoverGymEnv/hover_demo.py callers are
        unaffected by this change."""
        import pybullet as p

        if not self.sim_config.gui:
            return
        visual_shape = p.createVisualShape(
            p.GEOM_SPHERE, radius=radius, rgbaColor=list(color),
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
