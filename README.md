# AGERE — AI-Driven Autonomous SAR Navigation Stack

AGERE adds an AI reasoning layer on top of the PX4 flight stack so that
drones can make high-level Search and Rescue (SAR) decisions — where to
search, when to hold, when to abort — while PX4 remains solely responsible
for real-time flight control and failsafes. This "Backseat Driver" split
keeps flight safety independent of the AI's non-deterministic reasoning.

## Documentation map

| Area | Path | What's there |
|---|---|---|
| **Architecture** | [`docs/architecture/overview.md`](docs/architecture/overview.md) | Core spec: layers, comms protocol, ground-link-loss framework, Work Index energy model |
| | [`docs/architecture/analysis-backseat-driver.md`](docs/architecture/analysis-backseat-driver.md) | Full analysis report of the architecture above |
| | [`docs/architecture/diagrams/diagrams.md`](docs/architecture/diagrams/diagrams.md) | Mermaid source for all diagrams (source of truth — regenerate the PNG from this, don't hand-edit the image) |
| **Research** | [`docs/research/theoretical-framework.md`](docs/research/theoretical-framework.md) | DRL / TD3 / APF / RL-JSO theory backing the design |
| | [`docs/research/findings-sar-methods.md`](docs/research/findings-sar-methods.md) | Literature survey of autonomous SAR drone methods |
| **Planning** | [`docs/planning/implementation-pipeline.md`](docs/planning/implementation-pipeline.md) | Phased build plan: sim → HIL → tethered → supervised → autonomous |
| | [`docs/planning/rd-record.md`](docs/planning/rd-record.md) | R&D log |
| **Decisions** | [`docs/decisions/`](docs/decisions/) | ADRs — one file per significant design decision, numbered in order |
| **Devlog** | [`docs/devlog/`](docs/devlog/) | Dated working notes (`YYYY-MM-DD.md`) |
| **Presentations** | [`docs/presentations/`](docs/presentations/) | Slide decks (.pptx) |
| **Source layout** | [`src/README.md`](src/README.md) | What each module in `src/` does |

## Quick start

```bash
git clone <repo-url>
cd AGERE
conda env create -f environment.yml
conda activate agere
```

See [`docs/planning/implementation-pipeline.md`](docs/planning/implementation-pipeline.md)
for the current build phase and next steps.

## Project status

Early-stage: architecture and decision logic are specified
(`docs/architecture/`, `docs/decisions/`); implementation is proceeding
phase-by-phase per the pipeline document, starting with PX4/ROS 2 SITL
integration before any AI/RL components are trained.

## License

See [`LICENSE`](LICENSE).
