# Backseat Driver Model
## AI-Supervised Autonomous Control System for PX4 Drones

---

### Document Version: 2.0
### Date: July 13, 2026
### Project: Agere Autonomous Navigation Stack

---

## 1. Executive Summary

The Backseat Driver Model establishes a formal architectural framework for integrating Artificial Intelligence with the PX4 flight control system. This document outlines the separation of responsibilities, communication protocols, and system boundaries that enable safe, intelligent autonomous drone operations.

The core philosophy positions PX4 as the reliable, real-time **executor** (frontline soldiers) while AI systems function as the strategic **advisor** (battalion commander), providing high-level reasoning and mission planning without compromising flight safety.

**Version 2.0 additions:** this revision formalizes the Tactical/Middleware layer, which was previously a single row in a table. It now includes a concrete decision framework for ground-station communication loss during search-and-rescue-style operations, and a Work Index energy-margin model governing when the vehicle must abandon a task and preserve itself and its ability to be located. These are specified as architecture and decision *logic* (states, thresholds, rules) — implementation (code, tuned constants) is a follow-on phase and intentionally out of scope here.

---

## 2. System Architecture Overview

### 2.1 The Chain of Command

The architecture follows a strict hierarchical separation with clearly defined responsibilities:

| Layer | Component | Responsibility | Hardware |
|-------|-----------|----------------|----------|
| **Strategic** | AI Advisor | High-level reasoning, mission planning, semantic perception | Companion Computer (NVIDIA Jetson, Raspberry Pi, etc.) |
| **Tactical** | Middleware | Command translation, safety enforcement, constraint checking, **comms-loss decision logic, energy-margin arbitration** | Companion Computer |
| **Execution** | PX4 Flight Stack | Low-level control, stabilization, sensor fusion, failsafes | Flight Controller (Pixhawk, etc.) |

### 2.2 Communication Bridge

All data exchange between the AI layer and PX4 occurs through the **uXRCE-DDS** (ROS 2) bridge:

```
AI/ROS2 Node → uXRCE-DDS Agent → uXRCE-DDS Client → PX4 uORB → Flight Control
```

This bidirectional channel supports:
- **Downlink**: Telemetry data (position, velocity, attitude, battery, status)
- **Uplink**: High-level commands (setpoints, vehicle commands, mode changes)

### 2.3 Communication Link Taxonomy

Not all "loss of signal" is the same failure, and each has a different correct response. This architecture distinguishes three independent links:

| Link | Path | Loss Behavior Owner | Typical Cause |
|------|------|---------------------|---------------|
| **Ground link** | Ground station ↔ Companion computer | Tactical layer (Section 4) | Radio range, terrain occlusion, jamming |
| **Onboard heartbeat** | Companion computer ↔ PX4 (`OffboardControlMode`) | PX4 failsafe (`COM_OF_LOSS_T`), unchanged from v1.0 | Software crash, cable/serial fault |
| **Positioning signal** | GPS/GNSS ↔ EKF | PX4 EKF fallback / vision odometry | GPS denial, urban canyon, indoor |

This document's new sections (4, 6.4) address **ground link loss** specifically, since this is the case where the vehicle retains full onboard authority and autonomy but loses human oversight — the highest-value case for AI decision-making, and the focus of the current design effort.

---

## 3. PX4 Capabilities Assessment

### 3.1 Data Handling Capabilities

| Parameter | Capability |
|-----------|------------|
| **Sensor Data Rate** | 50 Hz to 1 kHz |
| **Control Loop Frequency** | 200 Hz typical |
| **Internal Messaging** | uORB bus with sub-millisecond latency |
| **State Estimation** | Extended Kalman Filter (EKF) fusing multiple sensors |

### 3.2 Supported Control Modes

| Mode | Description | AI Usage |
|------|-------------|----------|
| **Offboard Mode** | Accepts external setpoints from companion computer | **Primary mode** for AI control |
| **Position Control** | Internal PX4 loop tracking position setpoints | AI sends waypoints |
| **Velocity Control** | Internal PX4 loop tracking velocity setpoints | AI sends velocity vectors |
| **Altitude Control** | Internal PX4 loop tracking altitude | AI can specify altitude |

### 3.3 Extensibility for AI

PX4 supports AI integration through:

1. **Offboard Mode**: External control via setpoint streaming
2. **Distance Sensors**: Collision prevention using obstacle data
3. **Vision/Visual Odometry**: EKF fusion for improved state estimation
4. **Custom Flight Modes**: Experimental neural network control (v1.17+)

---

## 4. Tactical Layer: Ground-Link-Loss Decision Framework

### 4.1 Design Principle

Loss of the ground station link does **not** mean loss of vehicle authority — the drone retains full onboard sensing, computing, and control. The design question is what the AI advisor should decide **on its own**, in the absence of an operator, and how conservative that decision should be based on mission phase.

Two priorities govern every rule below, in order:
1. **Do not act irreversibly on unconfirmed information without a human.**
2. **Maximize the probability of the vehicle being found** if it cannot continue the mission — a vehicle that can still transmit its position is far more recoverable than one that has gone silent.

### 4.2 Phase-Dependent Behavior Table

| Mission Phase | Ground-Link-Loss Behavior | Rationale |
|---|---|---|
| **Preflight / Arming** | Do not arm / abort arming sequence | No reason to launch a mission that cannot be monitored from the start |
| **Transit to operational area** | Continue transit; degrade telemetry rate; keep attempting reconnection | Low-stakes navigation phase, no irreversible decisions pending |
| **Active search/task execution** | Continue autonomously, **strictly bounded** by pre-briefed geofence and the Work Index energy margin (Section 6.4) | Autonomy exists precisely so an operator dropout doesn't abort the mission — but only within pre-agreed limits |
| **Candidate/target detected** | Do **not** act on it. Loiter, log position + imagery, keep attempting reconnection. No descent, approach, or intervention. | Highest-stakes decision point. Acting on an unconfirmed detection without a human risks misidentification or unsafe action |
| **Return-to-base phase** | Continue as planned | The decision to return was already made before link loss; nothing changes |
| **Energy-critical (any phase)** | Overrides all rules above — see Section 6.4 | Physical constraints take precedence over mission logic unconditionally |

### 4.3 Timeout Ladder (Reconnection Sensitivity)

A single "connected / disconnected" threshold is too crude — very short dropouts are normal RF behavior, not a real loss event. A graduated response is required:

| Dropout Duration | Response |
|---|---|
| **< 10 s** | Ignore. No behavior change. Treated as normal link noise. |
| **10 s – 2 min** | Enter degraded autonomous mode: increase reconnection attempt rate, reduce telemetry/logging rate to conserve link budget, continue current phase behavior from Section 4.2 |
| **> 2 min** | Escalate: re-evaluate current phase decision (e.g., abandon further search expansion, transition toward return or hold per Section 4.2 and 6.4) |

*Note: the exact thresholds above are a starting proposal, not tuned values — they should be calibrated against the actual radio hardware's real-world dropout distribution during field testing before being treated as final.*

### 4.4 Preconditions This Framework Depends On

Allowing "continue mission on ground-link loss" is only safe if the following are true and enforced elsewhere in the system:
- A **geofence** is defined and enforced by PX4/middleware before the mission starts.
- A **time and energy budget** for the mission is defined before launch (feeds directly into Section 6.4).
- Target/candidate detections carry a **confidence score** from the perception pipeline, and the loiter-and-hold rule in 4.2 should trigger even at *medium* confidence — the cost of an unnecessary loiter is low; the cost of unauthorized action on a false positive is high.

---

## 5. AI Integration Patterns

### 5.1 Supported AI Functions on Top of PX4

| Function | Description | Communication Method |
|----------|-------------|---------------------|
| **Natural Language Command** | LLM interprets speech/text → structured flight commands | `TrajectorySetpoint` |
| **Computer Vision Navigation** | Detection models find obstacles/targets → path adjustment | `TrajectorySetpoint` |
| **RL-based Path Planning** | RL agent learns optimal routes in simulation → real deployment | `TrajectorySetpoint` |
| **Mission Orchestration** | FSM/Behavior Tree managing complex multi-phase missions, including Section 4's decision framework | `VehicleCommand` |
| **Semantic Perception** | Understanding scene context, including detection confidence scoring for Section 4.2 | Internal AI processing |

### 5.2 Command Types from AI to PX4

| Command Type | ROS 2 Topic | Description |
|--------------|-------------|-------------|
| **Setpoint Stream** | `/fmu/in/trajectory_setpoint` | Continuous position/velocity/acceleration targets |
| **Heartbeat Signal** | `/fmu/in/offboard_control_mode` | Proves AI is alive; required for Offboard Mode |
| **Vehicle Commands** | `/fmu/in/vehicle_command` | Arm, disarm, takeoff, land, mode changes |
| **Obstacle Data** | `/fmu/in/obstacle_distance` | Collision prevention information |

---

## 6. Data Flow, Sensor Integration & Energy Management

### 6.1 Sensor Data Pipeline (LiDAR example)

```
LiDAR Sensor → Companion Computer → ROS 2 Node → uXRCE-DDS → PX4 EKF
```

### 6.2 PX4 Consumer Modules

| Module | Function |
|--------|----------|
| **Collision Prevention** | Slows/stops drone to avoid obstacles |
| **EKF Fusion** | Improves position/velocity estimates without GPS |
| **Offboard Control** | Enables AI to use sensor data for path planning |

### 6.3 Failsafe Chain (Onboard Heartbeat Loss)

This is unchanged from v1.0 and governs companion-computer ↔ PX4 link loss, distinct from ground-link loss (Section 4):

```
AI Freezes → Heartbeat stops → PX4 detects loss →
Auto-transition to Position Hold → Execute failsafe landing
```

### 6.4 Work Index: Energy-Margin Decision Model

**Purpose:** determine, continuously through the mission, whether the vehicle has enough remaining energy to complete its current task *and* return or land safely — and if not, what to do about it. This model governs the "energy-critical" override referenced in Section 4.2.

**Unit:** flight-minutes remaining (derived from battery state + current power draw model). Energy (Wh) is an equally valid unit if a power-draw model is easier to maintain in those terms; the two convert 1:1 given a draw-rate model.

**Terms:**

| Term | Definition |
|---|---|
| `W_total` | Estimated flight-minutes remaining at current battery state and power draw |
| `W_op` | Estimated minutes required to complete the *remaining* planned task from current position |
| `W_return(t)` | Minutes required to fly directly back to base **from current position**, re-evaluated continuously (not fixed at mission start — it changes as the vehicle moves through the operational area) |
| `W_landing_maneuver` | Minutes of powered flight needed to execute a controlled landing |
| `W_beacon_reserve` | Minutes of low-power beacon transmission (GPS + comms, no flight) to sustain after landing, so the vehicle remains locatable |
| `W_land_safe` | `W_landing_maneuver + W_beacon_reserve` — the floor below which the vehicle must stop flying regardless of anything else |

**Priority ordering this model encodes:** a vehicle that is still flying and transmitting is easier to locate than one that has landed; a vehicle that has landed while still able to beacon is far easier to locate than one whose battery died mid-flight or immediately on landing. The decision rule below is built to preserve this ordering.

**Decision rule (re-evaluated at a fixed interval, e.g. every 15–30s or every waypoint):**

```
IF W_total >= W_op + W_return(t) + W_reserve:
    CONTINUE current task

ELSE IF W_total > W_land_safe:
    ABORT further task expansion
    HEAD TOWARD base or a pre-mapped safe landing zone
    (do not wait until forced down at an arbitrary location)

ELSE:  # W_total <= W_land_safe
    LAND IMMEDIATELY, in place
    Do NOT attempt to reach base — do not gamble remaining
    flight-minutes on a return that may not complete
    Enter beacon mode: halt flight systems, sustain GPS +
    comms transmission for as long as possible
```

Where `W_reserve` is a general safety buffer (wind, cell degradation, one failed approach attempt) applied above and beyond the hard `W_land_safe` floor.

**Open design points, deliberately left for the next design pass:**
- Landing-site selection logic when `W_land_safe` triggers away from base (flat terrain detection, avoiding people/water/hazards) — not yet specified.
- Whether flight and beacon/comms power should eventually be separated onto independent batteries, removing `W_beacon_reserve` as a carve-out of the flight pack entirely. Noted as a future hardware-level direction; out of scope for the current software architecture pass and intentionally deferred.
- Exact numeric values for `W_reserve`, `W_land_safe`, and the reconnection timeout ladder (Section 4.3) — these require field calibration against real hardware, not architectural specification.

### 6.5 Safety Philosophy

The architecture deliberately separates:
- **AI**: Non-deterministic, compute-heavy, experimental
- **PX4**: Hard real-time, deterministic, safety-certifiable

**Even if AI crashes completely, PX4 continues flying safely.** The Work Index and ground-link decision frameworks above are additional layers of *judgment* on top of this base guarantee — they do not replace it.

---

## 7. Recommended Hardware Architecture

| Component | Purpose | Example Hardware |
|-----------|---------|------------------|
| **Flight Controller** | Run PX4 real-time stack | Pixhawk, Holybro, CUAV |
| **Companion Computer** | Run ROS 2, AI models, perception | NVIDIA Jetson, Raspberry Pi 4, VOXL |
| **Communication Link** | uXRCE-DDS bridge | USB/UART/Serial connection |

---

## 8. Development Workflow

### 8.1 Recommended Tools

| Tool | Purpose |
|------|---------|
| **ROS 2 Humble** | Robotics middleware |
| **PX4-Autopilot** | Flight control stack |
| **Gazebo/Gz** | Simulation environment |
| **uXRCE-DDS Agent** | ROS 2 ↔ PX4 bridge |
| **SITL** | Software-in-the-loop testing |

### 8.2 Typical Testing Pipeline

1. **Simulation Only**: Test AI logic with SITL and Gazebo, including injected ground-link dropouts and battery drain scenarios to validate Sections 4 and 6.4
2. **HIL Testing**: Hardware-in-the-loop with real flight controller
3. **Tethered Flight**: Real drone with physical safety tether
4. **Supervised Flight**: AI active, human pilot ready to override
5. **Autonomous Flight**: Full AI control within safe envelope

---

## 9. Research vs. Production Considerations

| Aspect | Research | Production |
|--------|----------|------------|
| **AI Integration** | Can experiment with replacing control logic | Must keep AI strictly on top |
| **Safety Margin** | Accept some risk in controlled tests | Must be safety-certified |
| **Code Quality** | Focus on rapid iteration | Focus on robustness and redundancy |
| **Testing** | Primarily simulation | Extensive real-world validation |

---

## 10. Next Steps

1. **Establish Baseline**: Run PX4 SITL with ROS 2 communication working
2. **Data Understanding**: Document and verify all PX4 ↔ ROS 2 topics
3. **MVP Integration**: Implement simple "advisor" that sends setpoints
4. **Formalize Decision Logic**: Turn Sections 4 and 6.4 into an explicit FSM/behavior tree with tuned constants (deferred — "long game," per project direction)
5. **AI Training**: Begin RL or LLM development in simulation
6. **Safety Testing**: Validate failsafe mechanisms, including ground-link-loss and energy-margin scenarios from Sections 4 and 6.4

---

## 11. References

- PX4 Offboard Control Documentation
- uXRCE-DDS Protocol Specifications
- ROS 2 Drone Integration Guides
- Companion Computer Architecture Recommendations

---

*This document serves as the formal specification for the Agere project's Backseat Driver AI integration model. All architectural decisions should be evaluated against the principles outlined above. Version 2.0 adds the ground-link-loss decision framework and Work Index energy model as architectural specification only; implementation, tuning, and the deferred landing-site-selection and dual-battery questions are follow-on work.*
