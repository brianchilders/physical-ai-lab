# Roadmap

## Phase 1

Status: complete

Goal:

- define the Physical AI lab foundation
- organize the repository
- establish documentation
- document storage and workflow conventions

Deliverables:

- improved README
- vision, architecture, storage, workflow, and roadmap docs
- placeholder directories for future work
- explicit `/mnt/nvme` storage plan

## Phase 2

Goal:

- prepare Isaac Sim deployment infrastructure in a clean, reproducible Docker-based workflow

Deliverables:

- simulator container boundary
- launch instructions
- validation checklist
- storage preparation
- runtime notes

## Phase 3

Goal:

- create the first reproducible simulation and experiment loop

Deliverables:

- sample scenes
- asset handling conventions
- experiment templates
- logging and results capture

## Phase 4

Status: complete

Goal:

- introduce OpenUSD foundations in a controlled, documented way

Deliverables:

- stage authoring lab
- prim and hierarchy inspection
- text and binary USD save/reopen examples
- stage validation helpers

Next milestone:

- Phase 4C / Phase 5: USD layers, references, and composition to prepare for future real-world environment ingestion such as OVER USDZ captures

## Phase 5

Status: complete

Goal:

- introduce USD composition foundations in a controlled, documented way

Deliverables:

- reusable USD assets
- reference composition lab
- payload load and unload validation
- sublayer ordering and layer-strength validation
- wrapper-stage override validation
- source-layer immutability checks
- future OVER/USDZ-ready composition pattern

Validation results:

- asset creation complete
- composition creation complete
- independent inspection complete
- source and runtime hashes verified
- wrapper-stage teardown workaround scoped to the disposable read-only inspector only

## Phase 6

Status: complete

Goal:

- introduce physics foundations in a controlled, documented way

Deliverables:

- physics scene authoring and explicit gravity setup
- static ground collider and dynamic rigid bodies
- explicit physics materials, collision schemas, and mass properties
- fixed-step contact reporting and rebound detection
- two-run reproducibility comparison with bounded tolerances
- environment preparation for downstream robot and sensor work

Validation results:

- scene authoring complete
- controlled simulation complete
- independent formal inspection complete
- cross-run reproducibility comparison complete
- teardown containment scoped to the disposable one-shot authoring and inspection containers only

## Phase 7

Status: complete

Interactive Studio is the Phase 7 development environment.

Goal:

- introduce an interactive Isaac Sim development environment in a controlled, documented way

Deliverables:

- persistent interactive development container workflow
- WebRTC-oriented simulator access notes
- separation from one-shot production containers
- iterative scene-debug-edit loop guidance
- explicit host-IP requirement for remote streaming
- read-only Shared Assets mounting
- writable Interactive Workspace separation
- initial Windows WebRTC connection and interactive save acceptance validated
- lifecycle recreation and reconnect persistence validated
- Hub Workstation Cache downloaded as a persistent package but intentionally deferred

Validation results:

- repository scaffold complete
- storage and ownership validation complete
- persistent container launch complete
- Windows WebRTC connection complete
- interactive scene authoring complete
- workspace persistence complete
- lifecycle recreation complete
- Windows reconnect and scene reopen complete
- Phase 7 overall complete

## Phase 8

Goal:

- introduce sensors in a controlled, documented way

Deliverables:

- camera, depth, and range sensor foundations
- sensor configuration and calibration notes
- data capture and export conventions

## Phase 9

Goal:

- introduce Isaac Lab in a controlled, documented way

Deliverables:

- Isaac Lab workspace preparation
- task and environment organization
- training and evaluation harness notes

## Phase 10

Goal:

- prepare real-world environment capture workflows in a controlled, documented way

Deliverables:

- OVER capture planning
- Insta360 capture workflow notes
- USDZ wrapper-stage compatibility
- real-world environment composition guidance

## Phase 11

Goal:

- introduce robot training in a controlled, documented way

Deliverables:

- training loop documentation
- evaluation conventions
- experiment tracking and replay guidance
