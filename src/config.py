"""
Central configuration for AGERE's RL tasks (hover/stabilize, waypoint
navigation + landing).

No PX4/MAVSDK config here — AGERE is PyBullet + Gymnasium only. Anything
PX4-related lives in AGERE_sims, a separate repo entirely.
"""

from dataclasses import dataclass, field


@dataclass
class SimConfig:
    """Low-level PyBullet simulation settings — owned by environments/,
    read by DroneSim. No RL concepts here (no reward, no episode length)."""

    pyb_freq: int = 240   # PyBullet physics step rate (Hz)
    ctrl_freq: int = 30   # How often the sim accepts a new action (Hz);
                           # must evenly divide pyb_freq
    gui: bool = False     # True to render the PyBullet window locally


@dataclass
class HoverTaskConfig:
    """RL task definition for hover/stabilize — owned by training/, read by
    the Gymnasium wrapper. Reward, episode length, and termination bounds
    are RL design choices, not physics facts, so they live here rather
    than in SimConfig."""

    target_position: tuple = (0.0, 0.0, 1.0)   # meters, world frame
    episode_len_sec: float = 8.0

    # Reset randomization around target_position. Non-zero on purpose:
    # a fixed start teaches "memorize one trajectory," randomized start
    # teaches "stabilize from anywhere nearby."
    reset_position_jitter: float = 0.3
    reset_yaw_jitter_deg: float = 15.0

    # Truncation bounds (episode ends as failure if exceeded)
    max_xy_distance: float = 1.5     # meters from origin, x or y
    max_altitude: float = 2.0        # meters
    max_tilt_rad: float = 0.4        # roll or pitch, radians (~23 degrees)

    # Reward shaping weights
    position_error_weight: float = 1.0
    velocity_penalty_weight: float = 0.05
    action_smoothness_weight: float = 0.01
    survival_bonus: float = 0.01


@dataclass
class WaypointTaskConfig:
    """RL task definition for waypoint navigation + landing. Mirrors
    HoverTaskConfig's structure — same reset randomization, truncation
    bounds, and reward-shaping pattern — but adds a waypoint sequence and
    a distinct landing phase. See
    training/gym_wrapper/waypoint_gym_wrapper.py for how these fields are
    used."""

    waypoints: tuple = (
        (1.0, 0.0, 1.0),
        (1.0, 1.0, 1.5),
        (0.0, 1.5, 1.5),
        (-1.0, 1.0, 1.0),
        (0.0, 0.0, 0.5),
    )   # meters, world frame, visited in order

    waypoint_reach_radius: float = 0.15   # meters — within this = "reached," advance to next
    episode_len_sec: float = 20.0          # longer than hover's 8s — more ground to cover

    # Reset randomization — same idea as hover: don't memorize one exact
    # start, learn to reach waypoint 1 from a nearby range of starts.
    reset_position_jitter: float = 0.2
    reset_yaw_jitter_deg: float = 15.0

    # Truncation bounds — wider than hover's since the route itself
    # covers more xy space; these should comfortably contain all waypoints
    # plus some margin, not hug them tightly.
    max_xy_distance: float = 3.0
    max_altitude: float = 2.5
    max_tilt_rad: float = 0.4

    # Landing phase — begins once the final waypoint is reached.
    landing_target_altitude: float = 0.05   # near-ground, not exactly 0 (avoids
                                              # divide-by-zero / degenerate reward near contact)
    landing_max_velocity: float = 0.15      # m/s — vertical speed at touchdown to count as "soft"
    landing_hold_time_sec: float = 2.0      # must stay down + stable for this long to count as success

    # Reward shaping weights — same pattern as hover, plus one new term
    position_error_weight: float = 1.0
    velocity_penalty_weight: float = 0.05
    action_smoothness_weight: float = 0.01
    survival_bonus: float = 0.01
    waypoint_bonus: float = 5.0             # one-time bonus on reaching each waypoint —
                                              # needed so reward doesn't just reward "closer,"
                                              # it explicitly rewards "arrived and advanced"
    landing_velocity_penalty_weight: float = 0.3   # only active during landing phase — much
                                                     # heavier than the general velocity penalty,
                                                     # specifically to punish crashing into the ground fast


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
    """task defaults to HoverTaskConfig for backward compatibility —
    hover_train.py/hover_evaluate.py/hover_demo.py calling ProjectConfig()
    with no args are unaffected. waypoint_train.py (and its evaluate/demo
    siblings) explicitly pass task=WaypointTaskConfig() instead."""

    sim: SimConfig = field(default_factory=SimConfig)
    task: HoverTaskConfig | WaypointTaskConfig = field(default_factory=HoverTaskConfig)
    ppo: PPOConfig = field(default_factory=PPOConfig)
