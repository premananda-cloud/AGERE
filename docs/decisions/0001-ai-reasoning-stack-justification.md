# ADR 0001: Justification for an AI Reasoning Stack Above PX4

## Status
Accepted — 2026-07-21

## Context

PX4 is highly capable at what it's designed for: state estimation, flight
control, and general reflexes. It is not designed for reasoning or
high-level decision-making. Before adding an AI layer on top of it, that
addition needs to be justified rather than assumed — extra complexity on a
safety-critical system is a cost, not a default.

Five gaps were identified that PX4 alone does not address, all of which
matter specifically for autonomous Search and Rescue (SAR) missions:

1. **Localized search strategy development** — processing GPS and other
   sensor/terrain data to build a strategic map for pre-planning and
   context, not just moment-to-moment navigation.
2. **Search area prioritization** — statistical and logical optimization of
   *where* to search next, not just how to fly there.
3. **Live rescue accounting** — tracking what has been found, confirmed, or
   ruled out during an active mission.
4. **Hold protocol, logic, and edge-case handling** — deciding what to do
   when a mission hits an ambiguous or unplanned situation (e.g. candidate
   detected, link lost, energy low).
5. **Optimized path planning** — finding the most effective path given (1)
   and (2), not merely a collision-free one.

A reinforcement-learning (RL) model alone was considered but judged
sub-optimal on its own: RL is well suited to (5) — finding the most
effective path — but is not, by itself, a complete answer to (1)–(4). It
needs a strategic map, a prioritization signal, and a decision framework to
act on.

## Decision

Adopt a layered "Backseat Driver" architecture:

- **PX4 remains the sole real-time executor** of flight control,
  stabilization, and failsafes. This is not renegotiated by anything above.
- **An AI advisor layer is added above PX4**, responsible for the five
  items above, communicating via the uXRCE-DDS / ROS 2 bridge rather than
  by replacing any PX4 control logic.
- **RL (TD3 + APF reward) is used specifically for path planning (item 5)**,
  trained in simulation on a continuous Probability Distribution Map (PDM)
  rather than raw image input, to avoid noisy reward signals.
- **A separate optimizer (RL-JSO / Dueling Double DQN)** handles search area
  prioritization (item 2), adaptively switching between exploration and
  exploitation as the PDM updates.
- **Whether the strategic terrain map is a separate module or integrated
  into the path-planning model is left open** for now. Its outputs are
  planning context, not ground truth — it informs the AI advisor's
  reasoning but is not authoritative over PX4's own state estimation.

## Consequences

- Requires a robust, low-latency communication bridge (uXRCE-DDS) between
  the companion computer and PX4, since the split only works if telemetry
  and setpoints flow reliably in both directions.
- Introduces non-deterministic, compute-heavy AI processes that must be
  architecturally isolated from PX4's deterministic, safety-certifiable
  core — if the AI advisor crashes or misbehaves, PX4 must continue to fly
  safely regardless.
- Items 3 and 4 (live rescue accounting, hold protocol/edge cases) still
  need their own explicit decision logic — see the Ground-Link-Loss
  Decision Framework and Work Index energy model in
  `docs/architecture/analysis-backseat-driver.md`, which formalize (4).
- The open question on mapping-module architecture (integrated vs.
  separate) should be revisited once SLAM integration begins, and this ADR
  updated or superseded at that point.

## References
- Original notes: `docs/decisions/raw/design-rational-original.md`
- `docs/architecture/analysis-backseat-driver.md`
- `docs/research/theoretical-framework.md`
