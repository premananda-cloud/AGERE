# Research Findings: Autonomous SAR Drone Methods

## 1. Reinforcement Learning (RL) for Path Planning
- **Algorithm Performance**: Deep Reinforcement Learning (DRL) outperforms traditional benchmark algorithms (like Local Hill Climbing or Zig-Zag) by over 100% in search time [1].
- **A Priori Data**: Successful models use **Probability Distribution Maps (PDM)** derived from prior info (last seen location, fitness, age). Continuous PDMs are preferred over image-based ones to avoid noisy rewards [1].
- **Continuous Action Space**: Using cubature-based calculations allows for continuous action spaces, enabling more nuanced and efficient flight patterns compared to discrete grids [1].
- **Advanced Controllers**: Twin Delayed Deep Deterministic Policy Gradient (TD3) combined with Artificial Potential Field (APF) rewards (attractive/repulsive potentials) accelerates convergence and yields safer trajectories [2].

## 2. Terrain Mapping & Strategic Analysis
- **SLAM for GPS-Denied**: Simultaneous Localization and Mapping (SLAM) using LiDAR and cameras is essential for "urban canyons," forests, and indoor environments [4].
- **Terrain Following**: LiDAR is critical for maintaining consistent altitude above varying topography and penetrating dense vegetation to map the actual ground [4].
- **Hybrid Optimizers**: RL-JSO (Jellyfish Search Optimizer) uses a Dueling Double DQN to adaptively switch between exploration/exploitation phases, maintaining 100% collision-free rates even in adversarial conditions (wind, jamming) [3].

## 3. SAR Decision Frameworks
- **Search Prioritization**: AI algorithms analyze historical data, topography, and weather *pre-mission* to determine priority areas [4].
- **Cooperative Swarms**: Graph Attention Networks (GAT) can be used for real-time task allocation among multiple UAVs with minimal on-board compute [2].
- **Work Index / Energy Management**: Continuous re-evaluation of energy (flight-minutes remaining) vs. mission requirements is a key architectural safety layer.

## References
[1] Ewers, J. H., et al. (2025). "Deep reinforcement learning for time-critical wilderness search and rescue using drones." PMC11831046.
[2] Hickling, T., et al. (2025). "Deep Reinforcement Learning based Autonomous Decision-Making for Cooperative UAVs." arXiv:2502.20326.
[3] Alotaibi, N., et al. (2026). "Adaptive Reinforcement Learning-Driven Jellyfish Search Optimizer." MDPI Drones.
[4] AAI Drones. "Drone Techniques for Complex Terrain Search in SAR."
