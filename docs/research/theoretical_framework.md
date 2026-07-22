# AGERE Theoretical Framework: AI-Driven Autonomous SAR Navigation

## 1. Introduction and Rationale

The AGERE autonomous navigation stack is designed to elevate drone capabilities in Search and Rescue (SAR) operations from mere automated flight to intelligent, autonomous decision-making. As established in the project's design rationale, the PX4 flight controller is highly proficient at state estimation, flight control, and general reflexes. However, it lacks the capacity for high-level reasoning and strategic decision-making. 

The integration of an Artificial Intelligence (AI) reasoning stack above the PX4 layer is therefore justified to handle complex, dynamic tasks. This framework synthesizes state-of-the-art research to address the five core requirements identified for the AGERE project: localized search strategy development, search area prioritization, live rescue accounting, hold protocol logic, and optimized path planning.

## 2. Theoretical Models and Methods

The AGERE framework leverages a hybrid approach, combining Deep Reinforcement Learning (DRL) with advanced mapping and swarm intelligence techniques to achieve robust autonomous navigation.

### 2.1 Deep Reinforcement Learning for Path Planning

Relying solely on traditional coverage algorithms (like the lawnmower pattern) is sub-optimal for time-critical SAR missions. Recent research demonstrates that DRL can significantly reduce search times. Specifically, models utilizing continuous Probability Distribution Maps (PDMs) allow the AI policy to learn optimal flight paths that maximize the probability of finding a missing person quickly [1]. 

To implement this, the AGERE "driver seat" will utilize a Twin Delayed Deep Deterministic Policy Gradient (TD3) controller. This controller is trained using an Artificial Potential Field (APF) reward structure, which blends attractive potentials (towards high-probability search zones) and repulsive potentials (away from obstacles or known empty zones). This approach accelerates convergence and yields smoother, safer trajectories compared to distance-only baselines [2].

### 2.2 Strategic Mapping and Terrain Analysis

A critical component of the AGERE framework is the separation of strategic mapping from immediate path execution. The system will incorporate a dedicated mapping module to build a strategic map of the terrain. 

For complex and GPS-denied environments, the drone will rely on Simultaneous Localization and Mapping (SLAM) integrating LiDAR and visual odometry. LiDAR is particularly crucial for terrain following, allowing the drone to maintain a consistent altitude over rugged topography and penetrate dense forest canopies to map the actual ground surface [4]. This real-time data feeds into the PDM, dynamically updating the search strategy based on newly discovered terrain features.

### 2.3 Search Area Prioritization and Decision Logic

Search area prioritization is not static; it requires continuous statistical and logical optimization. The AGERE framework will utilize an Adaptive Reinforcement Learning-Driven Jellyfish Search Optimizer (RL-JSO). This hybrid model uses a Dueling Double Deep Q-Network (DQN) to adaptively select between exploration (searching new areas) and exploitation (focusing on high-probability zones) phases [3]. 

This adaptive phase switching is vital for maintaining swarm coordination and safety under adversarial conditions, such as GPS jamming or communication loss. By replacing deterministic time-control rules with a learned policy, the drone can dynamically adjust its search prioritization based on the immediate environmental context and the evolving PDM.

## 3. Addressing AGERE Core Requirements

The synthesized theoretical models directly address the five core reasons for the AI stack:

| AGERE Requirement | Theoretical Solution |
| :--- | :--- |
| **1. Localized Search Strategy** | SLAM and LiDAR integration for real-time terrain mapping, feeding into a dynamic Probability Distribution Map (PDM). |
| **2. Search Area Prioritization** | RL-JSO (Jellyfish Search Optimizer) driven by a Dueling Double DQN to adaptively manage exploration vs. exploitation based on the PDM. |
| **3. Live Rescue Accounting** | Integration of semantic perception models (e.g., thermal and visual object detection) to identify targets and update the strategic map. |
| **4. Hold Protocol & Edge Cases** | Implementation of the Ground-Link-Loss Decision Framework and Work Index Energy Model (from Architecture v2.0) to handle communication drops and battery constraints safely. |
| **5. Optimised Path Planning** | TD3 controller with Artificial Potential Field (APF) rewards for continuous, smooth, and obstacle-aware trajectory generation. |

## References

[1] Ewers, J. H., Anderson, D., & Thomson, D. (2025). Deep reinforcement learning for time-critical wilderness search and rescue using drones. *Frontiers in Robotics and AI*. https://pmc.ncbi.nlm.nih.gov/articles/PMC11831046/
[2] Hickling, T., Hogan, M., Tammam, A., & Aouf, N. (2025). Deep Reinforcement Learning based Autonomous Decision-Making for Cooperative UAVs: A Search and Rescue Real World Application. *arXiv preprint arXiv:2502.20326*. https://arxiv.org/abs/2502.20326
[3] Alotaibi, N., & BinSaeedan, W. (2026). Adaptive Reinforcement Learning-Driven Jellyfish Search Optimizer for Cooperative Multi-UAV Path Planning Under Dynamic and Adversarial Conditions. *Drones*, 10(5), 394. https://www.mdpi.com/2504-446X/10/5/394
[4] AAI Drones. (n.d.). Navigating the Unseen: Drone Techniques for Complex Terrain Search in SAR. https://aai-drones.com/navigating-the-unseen-drone-techniques-for-complex-terrain-search-in-sar/
