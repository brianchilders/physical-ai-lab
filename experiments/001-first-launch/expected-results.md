# Expected Results

Expected smoke-test output includes:

- `SMOKE: python runtime started`
- `SMOKE: SimulationApp initialized`
- `SMOKE: stage API imported`
- `SMOKE: empty stage created`
- `SMOKE: frame 1/10` through `SMOKE: frame 10/10`
- `SMOKE: simulation loop complete`
- `SMOKE: peak gpu memory observed: 1572 MiB`
- `SMOKE: requesting immediate shutdown`

Expected behavior:

- the final successful smoke-test rerun exits with code `0`
- no assets are downloaded
- no GUI is launched
- no ROS 2 components are started
- the existing headless service remains healthy
- the original graceful-close attempt is preserved as a known shutdown issue in the experiment summary
