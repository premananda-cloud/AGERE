"""
Velocity-setpoint action space.

The policy network always outputs normalized actions in [-1, 1] — this is
good practice for training stability regardless of the underlying physical
units. This module is the *only* place that knows how to turn that into a
real (vx, vy, vz, yaw_rate) command, and the only place that would need to
change if you switch to position setpoints later.
"""

from dataclasses import dataclass

import numpy as np
from gymnasium import spaces

from src.config import ActionLimits


@dataclass
class VelocitySetpoint:
    vx: float          # m/s, body-frame forward
    vy: float          # m/s, body-frame right
    vz: float          # m/s, body-frame down (positive = descending)
    yaw_rate_deg: float  # deg/s


class VelocityActionSpace:
    """Wraps a Gymnasium Box space and the scaling logic to go with it."""

    def __init__(self, limits: ActionLimits):
        self.limits = limits
        # 4 actions: vx, vy, vz, yaw_rate — all normalized to [-1, 1]
        self.space = spaces.Box(
            low=-1.0, high=1.0, shape=(4,), dtype=np.float32
        )

    def scale(self, raw_action: np.ndarray) -> VelocitySetpoint:
        """Map a normalized action from the policy to a real setpoint."""
        action = np.clip(raw_action, -1.0, 1.0)
        vx = float(action[0]) * self.limits.max_horizontal_speed
        vy = float(action[1]) * self.limits.max_horizontal_speed
        vz = float(action[2]) * self.limits.max_vertical_speed
        yaw_rate = float(action[3]) * self.limits.max_yaw_rate_deg
        return VelocitySetpoint(vx=vx, vy=vy, vz=vz, yaw_rate_deg=yaw_rate)

    def sample(self) -> np.ndarray:
        return self.space.sample()
