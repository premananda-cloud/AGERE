"""
Velocity action definition.

Defines what the 4 numbers a policy outputs mean as a physical command:
a 3D direction vector plus a speed magnitude, matching the convention
gym-pybullet-drones' own VEL action type expects internally (direction,
magnitude — not vx/vy/vz/yaw_rate independently; see the "no yaw control"
note below).

This module intentionally does NOT import gymnasium. Whether an action
space is a `Box`, its shape, its bounds as a Gym object — that's a
Gymnasium concern and lives in the training-side wrapper
(src/training/gym_wrapper.py), not here. This file only defines what a raw
action array *means*, independent of any RL framework.

KNOWN LIMITATION (inherited from gym-pybullet-drones, not introduced here):
this action type has no yaw-rate control — the underlying PID controller
holds whatever yaw the drone currently has. Fine for pure position-hold.
"""

from dataclasses import dataclass

import numpy as np


@dataclass
class VelocityCommand:
    """A direction + speed command, ready to hand to DroneSim.apply_action()."""

    direction: np.ndarray  # unit vector, shape (3,)
    speed: float           # fraction of the sim's max speed, in [0, 1]


ACTION_DIM = 4  # [dir_x, dir_y, dir_z, speed] — matches gym-pybullet-drones' VEL convention


def normalize_action(raw_action: np.ndarray) -> VelocityCommand:
    """Turn a raw 4-vector (as produced by a policy) into a VelocityCommand.

    raw_action[0:3] is treated as a direction (normalized to a unit vector
    here; doesn't need to arrive pre-normalized). raw_action[3] is clipped
    to [0, 1] and treated as speed magnitude.
    """
    raw_action = np.asarray(raw_action, dtype=np.float32)
    direction = raw_action[0:3]
    norm = np.linalg.norm(direction)
    if norm > 1e-6:
        direction = direction / norm
    else:
        direction = np.zeros(3, dtype=np.float32)

    speed = float(np.clip(raw_action[3], 0.0, 1.0))
    return VelocityCommand(direction=direction, speed=speed)
