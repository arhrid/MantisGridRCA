# Eval

Run at least two configurations before submission:

```bash
make validate
make dev AGENT=agents.telemetry_routed OUT=out/routed
make score OUT=out/routed
make cost OUT=out/routed

RCA_MODEL=zai-org/GLM-5.2 make dev AGENT=agents.telemetry_routed OUT=out/single-glm52
make score OUT=out/single-glm52
make cost OUT=out/single-glm52

python scripts/compare_runs.py \
  --queries data/Market-cloudbed-1/dev/query_dev.csv \
  --out out/routed out/single-glm52 \
  --report out/comparison.md
```

Record strict/partial accuracy, dollars per case, wall time per case, and the major failure groups in `REPORT.md`.

Recommended comparison set:

- Deterministic no-key run: verifies baseline output mechanics and zero-dollar fallback.
- Routed Featherless run: default `agents.telemetry_routed`, cheap-first only for dominant single-candidate cases.
- Single-model ablation: set `RCA_MODEL=zai-org/GLM-5.2` to measure whether routing saves cost or wall-clock without losing score.
