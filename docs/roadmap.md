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

Goal:

- introduce ROS 2 in a controlled, documented way

Deliverables:

- ROS 2 workspace layout
- message and topic conventions
- simulator-to-ROS bridge documentation

## Phase 6

Goal:

- integrate DGX Spark as a remote inference and compute node

Deliverables:

- service architecture
- model serving conventions
- network and authentication documentation
- distributed workflow notes
