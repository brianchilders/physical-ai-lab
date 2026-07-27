# AGENTS.md

This repository is documentation-first and reproducibility-first.

Future coding agents should:

- prefer documentation before implementation
- prefer Docker-first workflows where practical
- avoid destructive operations unless explicitly approved
- never commit without approval
- never push without approval
- keep experiments reproducible and traceable
- keep large assets, datasets, and logs outside git
- prefer small iterative milestones over broad unreviewed changes
- preserve the canonical `/mnt/nvme/isaac/` storage layout
- keep Isaac Sim work isolated from unrelated repository concerns

When working on simulator or deployment changes:

- treat current official NVIDIA Isaac Sim documentation as the source of truth
- do not hardcode stale image names or launch assumptions
- do not install software unless explicitly asked to do so
- do not pull large images unless the user explicitly approves it

