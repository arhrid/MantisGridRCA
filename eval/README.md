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
```

Record strict/partial accuracy, dollars per case, wall time per case, and the major failure groups in `REPORT.md`.
