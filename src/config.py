"""
Central configuration for the hover/stabilize RL task.

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
    """RL task definition — owned by training/, read by the Gymnasium
    wrapper. Reward, episode length, and termination bounds are RL design
    choices, not physics facts, so they live here rather than in
    SimConfig."""

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
    sim: SimConfig = field(default_factory=SimConfig)
    task: HoverTaskConfig = field(default_factory=HoverTaskConfig)
    ppo: PPOConfig = field(default_factory=PPOConfig)
