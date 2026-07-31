"""
PPO policy construction.

This is the only file that knows we're using PPO specifically. Swapping to
SAC (or anything else in SB3) later means writing a sibling
`build_sac(env, config)` function with the same signature and pointing the
training script at it — the env and action space don't change at all.
"""

from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor

from src.config import PPOConfig


def build_ppo(env, ppo_config: PPOConfig, tensorboard_log: str | None = None) -> PPO:
    monitored_env = Monitor(env)
    model = PPO(
        policy="MlpPolicy",
        env=monitored_env,
        learning_rate=ppo_config.learning_rate,
        n_steps=ppo_config.n_steps,
        batch_size=ppo_config.batch_size,
        n_epochs=ppo_config.n_epochs,
        gamma=ppo_config.gamma,
        gae_lambda=ppo_config.gae_lambda,
        clip_range=ppo_config.clip_range,
        ent_coef=ppo_config.ent_coef,
        policy_kwargs={"net_arch": ppo_config.net_arch},
        tensorboard_log=tensorboard_log,
        verbose=1,
        device = 'cpu'
    )
    return model
