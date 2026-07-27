# Configuration

This directory will hold tracked configuration that is safe to version:

- environment templates
- Docker-related config
- simulator launch parameters
- experiment manifests
- paths and mount conventions
- stable lab defaults in `lab.env.example`

Guidelines:

- Keep secrets out of git.
- Keep machine-specific overrides separate from shared defaults.
- Prefer small, explicit config files over hidden shell state.

Planned substructure:

```text
config/
├── lab.env.example
├── environment/
├── isaac/
├── sensors/
└── experiments/
```
