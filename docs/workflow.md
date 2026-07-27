# Development Workflow

The workflow is built around reproducibility and small steps.

## Default Loop

1. Write or update the relevant documentation first.
2. Define the target directory layout and storage path.
3. Add config or scaffolding only after the shape of the system is documented.
4. Keep changes small and reviewable.
5. Record what was validated and what remains open.

## Phase 2 Loop

1. Run `./prepare-storage.sh` to create the canonical Isaac storage tree.
2. Run `./validate-workstation.sh` to confirm host readiness.
3. Review the launch wrappers before any manual container run.
4. Keep the image tag, storage contract, and docs in sync.
5. Do not automate pulls, logins, or workstation changes in the repository.

## Experiment Flow

1. Create an experiment note in `experiments/`.
2. Define the input assets, data location, and runtime assumptions.
3. Run the experiment with an explicit configuration.
4. Store outputs and logs under `/mnt/nvme/isaac/logs/` and `/mnt/nvme/isaac/datasets/` as appropriate.
5. Summarize the result in the experiment note or a notebook.

## Notebook Flow

Use `notebooks/` for analysis, exploration, and decision-making support.

- keep notebooks tied to a specific experiment or question
- avoid notebook-only knowledge when it should become documentation
- extract durable findings into `docs/`

## Change Policy

- no destructive actions without asking
- no committing or pushing unless explicitly instructed
- no ROS 2 setup in Phase 1
- no Isaac Sim installation in Phase 1
- no Isaac Sim installation during Phase 2 repository preparation

## Documentation Standard

Each non-trivial change should leave behind:

- what changed
- why it changed
- what depends on it
- what comes next
