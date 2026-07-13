documentation file  to record your  and understanding.

# ROS 2 & PX4 Development Documentation
**Author:** Premananda  
**Date:** 2026-07-13  
**Project:** AGERE
**Platform:** Debian  
**Repository:** https://github.com/premananda-cloud/AGERE

---

## 📚 Table of Contents
1. [What is ROS 2?](#1-what-is-ros-2)
2. [What is SITL?](#2-what-is-sitl-software-in-the-loop)
3. [Autopilot Systems: PX4 vs ArduPilot](#3-autopilot-systems-px4-vs-ardupilot)
4. [Why PX4 for Academic Research?](#4-why-px4-for-academic-research)
5. [Development Environment Setup](#5-development-environment-setup)
6. [Key Tools & Commands](#6-key-tools--commands)
7. [Next Steps](#7-next-steps)

---

## 1. What is ROS 2?

### Definition
**ROS 2** (Robot Operating System 2) is a open-source middleware framework for robotic application development. Despite its name, it's **NOT** an operating system—it's a set of libraries and tools that handle the "plumbing" of robot software.

### Core Concepts
| Concept | Description | Drone Analogy |
|---------|-------------|---------------|
| **Node** | Independent executable program | Camera driver, flight controller interface, path planner |
| **Topic** | Named bus for streaming data | `/drone/imu` (IMU data), `/drone/gps` (GPS position) |
| **Publisher** | Node that sends data to a topic | Camera node publishing video frames |
| **Subscriber** | Node that receives data from a topic | Object detection node subscribing to camera feed |
| **Service** | Request/response communication | `takeoff` service, `land` service |
| **Action** | Long-running task with feedback | `fly_to_waypoint` action with progress updates |

### ROS 2 vs ROS 1 (Legacy)
| Feature | ROS 1 | ROS 2 |
|---------|-------|-------|
| **Communication** | Central ROS Master | Decentralized with DDS |
| **Real-time** | Limited | Native support |
| **Platforms** | Linux-only | Linux, Windows, macOS, RTOS |
| **Security** | None | Built-in DDS-Security |
| **Support Status** | EOL (May 2025) | Active development |

### Key ROS 2 Commands
```bash
# List all running nodes
ros2 node list

# List all topics (data streams)
ros2 topic list

# View data on a topic in real-time
ros2 topic echo /drone/pose

# Publish a message to a topic
ros2 topic pub /drone/command geometry_msgs/msg/Twist "{linear: {x: 1.0}}"

# Call a service
ros2 service call /drone/takeoff std_srvs/srv/Empty

# Run a node from a package
ros2 run package_name node_name

# Launch multiple nodes
ros2 launch package_name launch_file.launch.py
```

---

## 2. What is SITL (Software-In-The-Loop)?

### Definition
**SITL** is a simulation mode where the actual flight controller software (PX4 firmware) runs natively on your computer, simulating a real drone. The autopilot processes virtual sensor data and sends virtual actuator commands, exactly as it would on physical hardware.

### Why SITL for Development?

| Advantage | Explanation |
|-----------|-------------|
| **Safety** | Test aggressive maneuvers without crashing physical drones |
| **Speed** | Run simulations faster than real-time (RTF > 1) |
| **Repeatability** | Identical test conditions every time |
| **Cost** | No hardware costs during development phase |
| **Debugging** | Full access to logs, variables, and memory |
| **Multi-vehicle** | Simulate swarms of 10+ drones on one computer |

### SITL Architecture
```
┌─────────────────────────────────────────────────────────┐
│                    YOUR COMPUTER (Debian)               │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌──────────────┐    ┌──────────────┐                   │
│  │  ROS 2 Nodes │    │   Gazebo     │  ◄─── 3D Visual   │
│  │  (Your Code) │    │   Simulator  │      Feedback     │   
│  └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                           │
│         ▼                   ▼                           │
│  ┌──────────────────────────────────┐                   │
│  │    PX4 Autopilot (SITL Mode)     │                   │
│  │  - Processes virtual sensor data │                   │
│  │  - Runs control algorithms       │                   │
│  │  - Simulates physics             │                   │
│  └──────────────────────────────────┘                   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Autopilot Systems: PX4 vs ArduPilot

### Comparison Table

| Feature | PX4 | ArduPilot |
|---------|-----|-----------|
| **Primary Language** | C++ | C++ |
| **Licensing** | BSD 3-Clause | GPLv3 |
| **Community** | Strong academic/research | Strong hobbyist/commercial |
| **Ecosystem** | ROS 2 integration | ROS 2 integration |
| **Flight Modes** | ~15 modes | ~30+ modes |
| **Hardware Support** | Limited (mainstream FCs) | Extensive (400+ boards) |
| **Real-time** | NuttX RTOS | NuttX/ChibiOS |
| **Code Quality** | Clean, modular | Large, historic codebase |
| **Documentation** | Excellent for developers | Good for users |
| **Research Usage** | MIT, ETH Zurich, UPenn | OpenUAV, more commercial |

### When to Choose PX4

✅ **Academic/Research** - Clean codebase makes modification easier  
✅ **ROS 2 Integration** - Official PX4-ROS 2 bridge maintained  
✅ **Control Algorithms** - Easy to replace with custom controllers  
✅ **Modular Architecture** - Clear separation of modules  
✅ **Startup Usage** - Many research labs use PX4 as base  

### When to Choose ArduPilot

✅ **Commercial Projects** - Mature, battle-tested  
✅ **Hardware Variety** - Supports more flight controllers  
✅ **Advanced Features** - More flight modes out-of-the-box  
✅ **Hobbyist Community** - Larger user base for support  

---

## 4. Why PX4 for Academic Research?

### 1. Academic Adoption
- MIT's Aerospace Controls Lab
- ETH Zurich's Flying Machine Arena
- UPenn's GRASP Lab
- TU Delft MAVLab
- Numerous papers published annually using PX4

### 2. Clean, Modular Architecture
```
PX4 Architecture:
├── drivers/          # Hardware drivers (sensors, GPS, etc.)
├── modules/          # Core modules (commander, navigator, etc.)
│   ├── commander/    # High-level state machine
│   ├── navigator/    # Path planning & navigation
│   ├── mc_pos_control/ # Multicopter position control
│   └── mc_att_control/ # Multicopter attitude control
├── lib/              # Libraries (matrix, math, etc.)
└── platforms/        # OS abstraction layer
```

### 3. Easy to Modify/Replace
- Each controller (attitude, position) can be replaced with custom implementation
- New flight modes can be added without touching core code
- Custom estimators can be plugged in (EKF, UKF, etc.)

### 4. Research-Ready Features
| Feature | Use Case |
|---------|----------|
| **Offboard Mode** | External control from ROS 2 |
| **MAVLink Protocol** | Telemetry & control via ground stations |
| **uXRCE-DDS Bridge** | Native ROS 2 communication |
| **Parameter System** | Tune algorithms without recompiling |
| **Logging** | Full flight logs for post-analysis |

### 5. Community & Support
- Active development (weekly releases)
- Academic-focused mailing lists
- Research-oriented GitHub issues
- Conference workshops (IROS, ICRA)

### 6. Simulation Support
- Gazebo (physics + visualization)
- AirSim (Unreal Engine based)
- jMAVSim (lightweight)
- Custom simulation via SITL

---

## 5. Development Environment Setup

### Repository Structure
```
aerial-autonomy-stack/
├── aerial_autonomy_stack/     # Main ROS 2 packages
│   ├── offboard_control/      # Custom offboard control
│   ├── swarm_control/         # Multi-drone coordination
│   └── perception/            # Vision & sensor processing
├── autopilot/                 # Autopilot source
│   ├── PX4-Autopilot/         # PX4 firmware (cloned)
│   └── Tools/                 # PX4 build tools
├── tools_and_docs/            # Helper scripts
│   ├── sim_run.sh            # Launch simulation
│   ├── docker/               # Docker configurations
│   └── docs/                 # Documentation
├── docker-compose.yaml       # Multi-container setup
└── .env.example              # Environment variables
```

### System Requirements
| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **RAM** | 8 GB | 16+ GB |
| **Storage** | 20 GB | 50+ GB |
| **CPU** | 4 cores | 8+ cores |
| **GPU** | Not required | For vision-based simulation |
| **Network** | Internet for setup | Optional after setup |

### Installation Steps (Already Done)
```bash
# Clone the repository (COMPLETED)
git clone https://github.com/JacopoPan/aerial-autonomy-stack.git
cd aerial-autonomy-stack

# Next steps (to be done):
# 1. Install Docker (if not present)
# 2. Build Docker container
# 3. Run first simulation
```

---

## 6. Key Tools & Commands

### Essential Tools

| Tool | Purpose | Example Usage |
|------|---------|---------------|
| **Docker** | Containerization | `docker compose up -d` |
| **colcon** | ROS 2 build system | `colcon build --packages-select offboard_control` |
| **Gazebo** | 3D simulation | Run with `sim_run.sh` |
| **rviz2** | ROS visualization | `rviz2 -d config.rviz` |
| **QGroundControl** | Ground Control Station | Monitor telemetry manually |
| **MAVLink Router** | Route MAVLink messages | Between PX4 and ROS 2 |

### Important ROS 2 Packages for PX4

| Package | Purpose |
|---------|---------|
| `px4_msgs` | ROS 2 message definitions for PX4 |
| `px4_ros_com` | DDS bridge between ROS 2 and PX4 |
| `mavros` | MAVLink to ROS 2 bridge (alternative) |
| `mavlink` | MAVLink protocol implementation |

### Useful PX4 Commands
```bash
# Build PX4 firmware
make px4_sitl gazebo

# Run PX4 SITL
make px4_sitl gazebo_iris

# List all available models
make px4_sitl gazebo --list
```

---

## 7. Next Steps

### Immediate Tasks
1. **Docker Setup** (today)
   ```bash
   cd aerial-autonomy-stack
   docker compose up -d --build
   ```

2. **First Simulation** (today)
   ```bash
   NUM_QUADS=1 WORLD=swiss_town RTF=3.0 ./tools_and_docs/sim_run.sh
   ```

3. **Verify ROS 2 Communication** (today)
   ```bash
   # Inside Docker container
   ros2 topic list
   ros2 topic echo /fmu/out/vehicle_status
   ```

4. **Test Offboard Control** (next session)
   - Write a simple Python node to arm and takeoff
   - Send position setpoints

### Week 1 Goals
- [ ] Understand PX4 architecture
- [ ] Write first custom controller
- [ ] Implement simple waypoint navigation
- [ ] Record and analyze flight logs

### Month 1 Goals (AGERE Project)
- [ ] Define specific research objectives
- [ ] Implement custom control algorithm
- [ ] Test in SITL environment
- [ ] Deploy on physical drone (if available)

### Learning Resources
- [PX4 Developer Guide](https://docs.px4.io/main/en/development/development.html)
- [ROS 2 Documentation](https://docs.ros.org/en/humble/)
- [Aerial Autonomy Stack Docs](https://github.com/JacopoPan/aerial-autonomy-stack/tree/main/tools_and_docs)
- [PX4-ROS 2 Bridge Tutorial](https://docs.px4.io/main/en/ros/ros2_comm.html)

---

## 📝 Notes & Observations

### Setup Notes
```bash
# Current setup status
Repository cloned: /home/premananda/projects/aerial-autonomy-stack
Branch: main
Latest commit: [date TBD]

# System info
OS: Debian
User: premananda
Project: AGERE
```

### Questions for Future Investigation
1. How to customize PX4 control parameters for our specific drone?
2. What is the best way to integrate custom perception algorithms?
3. How to handle communication delays in offboard control?
4. What are the safety considerations when transitioning to real hardware?

---

**Last Updated:** 2026-07-13  
**Next Review:** After first successful simulation run
```

This documentation gives you a solid foundation to understand your tools and justify your PX4 choice. You can save this as `README.md` or `docs/development_setup.md` in your project directory. 

Now that you have the repo cloned, want me to help you with the next step - running your first simulation and verifying everything works?
