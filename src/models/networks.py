"""
Custom network architectures live here.

Right now the hover task is small (9-dim observation) so SB3's default MLP
extractor is plenty — there's no custom feature extractor yet. This file
exists as the deliberate extension point: if you later add richer
observations (e.g. depth images, LiDAR scans for obstacle avoidance), a
custom `BaseFeaturesExtractor` subclass goes here and gets passed into
policy_kwargs in src/policies/ppo_policy.py, without touching the env or
training script.
"""

# Example shape for later:
#
# from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
# import torch.nn as nn
#
# class CustomExtractor(BaseFeaturesExtractor):
#     def __init__(self, observation_space, features_dim=64):
#         super().__init__(observation_space, features_dim)
#         self.net = nn.Sequential(...)
#
#     def forward(self, observations):
#         return self.net(observations)
