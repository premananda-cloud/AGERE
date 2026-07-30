"""
Central configuration for the hover/stabilize RL task.

Keep every tunable constant here. Nothing downstream (env, action space,
policy, training script) should hardcode a number that belongs in this file —
that's what makes it cheap to swap tasks, algorithms, or control modes later.
"""

from dataclasses import dataclass, field


@dataclass
class ControlConfig:
    """MAVSDK connection + control-loop timing."""

    # Matches the udpin://<host>:<port> fix from the 2026-07-23 session —
    # explicit "listen" mode, since PX4's onboard MAVLink instance connects
    # *to* us on this port.
    connection_url: str = "udpin://0.0.0.0:14540"

    # RL step rate. MAVSDK's UDP round-trip can't sustain PX4's 200 Hz
    # internal loop, so we step at a much lower rate and let PX4's own
    # controller handle the gap. Start conservative; raise once stable.
    control_hz: float = 15.0

    @property
    def control_dt(self) -> float:
        return 1.0 / self.control_hz


@dataclass
class ActionLimits:
    """Velocity-setpoint action space bounds (body frame)."""

    max_horizontal_speed: float = 2.0   # m/s, vx / vy
    max_vertical_speed: float = 1.0     # m/s, vz (kept lower than horizontal —
                                         # vertical overshoot is the fastest way
                                         # to bounce off the ground or ceiling
                                         # of the geofence during early training)
    max_yaw_rate_deg: float = 45.0      # deg/s


@dataclass
class PyBulletHoverConfig:
    """Task + sim settings for the active gym-pybullet-drones hover track.

    Mirrors HoverTaskConfig's intent but adapted to what
    gym_pybullet_drones.envs.HoverAviary actually exposes. This is the
    config the training script uses right now; HoverTaskConfig (below)
    is for the parked PX4/MAVSDK path.
    """

    # Sim rates. pyb_freq is PyBullet's physics step rate; ctrl_freq is how
    # often the RL agent gets a step (must evenly divide pyb_freq).
    pyb_freq: int = 240
    ctrl_freq: int = 30

    gui: bool = False   # set True locally to watch training; False for
                         # headless/server runs

    # Action/observation type strings, matching gym_pybullet_drones.utils.enums.
    # "vel"  -> velocity direction+magnitude, PID-controlled internally,
    #           no yaw-rate control (framework limitation, see README).
    # "kin"  -> 12-dim kinematic observation (pos, rpy, vel, ang vel).
    action_type: str = "vel"
    observation_type: str = "kin"

    target_position: tuple = (0.0, 0.0, 1.0)   # meters, world frame
    episode_len_sec: float = 8.0

    # Reset randomization around target_position — same rationale as the
    # PX4 config: fixed start teaches "memorize one trajectory", randomized
    # start teaches "stabilize from anywhere nearby".
    reset_position_jitter: float = 0.3
    reset_yaw_jitter_deg: float = 15.0

    # Truncation bounds (episode ends as failure if exceeded)
    max_xy_distance: float = 1.5     # meters from origin, x or y
    max_altitude: float = 2.0        # meters
    max_tilt_rad: float = 0.4        # roll or pitch, radians (~23 degrees)

    # Reward shaping weights (used if you override HoverAviary's default
    # reward — see src/environments/pybullet/hover_env.py)
    position_error_weight: float = 1.0
    velocity_penalty_weight: float = 0.05
    action_smoothness_weight: float = 0.01
    survival_bonus: float = 0.01


@dataclass
class HoverTaskConfig:
    """PARKED (PX4/MAVSDK path). Episode / task definition for
    hover-and-stabilize against PX4 SITL. Not used by the active
    training script — see PyBulletHoverConfig above."""

    # Target is expressed relative to the takeoff point, in local NED-ish
    # (north, east, down-negative-up) meters.
    target_position: tuple = (0.0, 0.0, -3.0)  # 3 m above takeoff point

    # How far from the target a reset may randomly place the drone.
    # Non-zero on purpose: a fixed start teaches "memorize one trajectory",
    # randomized start teaches "stabilize from anywhere nearby".
    reset_position_jitter: float = 1.0   # meters, per axis
    reset_yaw_jitter_deg: float = 30.0

    max_episode_steps: int = 300         # at 15 Hz this is 20 s per episode

    # Termination bounds (episode ends as failure if exceeded)
    max_position_error: float = 8.0      # meters from target -> geofence-ish bound
    max_tilt_deg: float = 45.0           # roll or pitch -> about to lose control

    # Reward shaping weights
    position_error_weight: float = 1.0
    velocity_penalty_weight: float = 0.05
    angular_rate_penalty_weight: float = 0.02
    action_smoothness_weight: float = 0.01
    survival_bonus: float = 0.01


@dataclass
class PPOConfig:
    """Hyperparameters passed to stable-baselines3 PPO."""

    learning_rate: float = 3e-4
    n_steps: int = 2048
    batch_size: int = 64
    n_epochs: int = 10
    gamma: float = 0.99
    gae_lambda: float = 0.95
    clip_range: float = 0.2
    ent_coef: float = 0.01
    net_arch: dict = field(default_factory=lambda: {"pi": [64, 64], "vf": [64, 64]})
    total_timesteps: int = 200_000


@dataclass
class ProjectConfig:
    # Active track
    pybullet_task: PyBulletHoverConfig = field(default_factory=PyBulletHoverConfig)
    ppo: PPOConfig = field(default_factory=PPOConfig)

    # Parked (PX4/MAVSDK transplant phase)
    control: ControlConfig = field(default_factory=ControlConfig)
    action_limits: ActionLimits = field(default_factory=ActionLimits)
    task: HoverTaskConfig = field(default_factory=HoverTaskConfig)
