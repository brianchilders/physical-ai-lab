# Expected Results

The OpenUSD foundations lab should produce:

- a human-readable `output/openusd_foundations.usda` in the isolated NVMe runtime output directory
- a binary `output/openusd_foundations.usd` in the isolated NVMe runtime output directory
- a printed hierarchy matching `expected-hierarchy.txt`
- successful validation of:
  - default prim `/World`
  - stage up-axis
  - meters-per-unit
  - required prim paths
  - prim types
  - transforms
  - cube, sphere, and cylinder display colors
  - reopening both USDA and USD files

Expected console markers include:

- `OPENUSD: SimulationApp initialized`
- `OPENUSD: stage created`
- `OPENUSD: default prim set to /World`
- `OPENUSD: geometry created`
- `OPENUSD: transforms applied`
- `OPENUSD: USDA saved`
- `OPENUSD: USD saved`
- `OPENUSD: validation passed`
- `OPENUSD: 10 frames completed`
- `OPENUSD: requesting immediate shutdown`

Expected behavior:

- the script exits with code `0`
- no external assets are downloaded
- no GUI is launched
- no unrelated simulator components are started
- the generated files remain ignored unless explicitly inspected

Phase status:

- Phase 4A complete
- Phase 4B complete
- Phase 4 overall complete
