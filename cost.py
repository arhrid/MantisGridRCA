#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

PRICES = {
    "zai-org/GLM-4.7-Flash": (0.065, 0.40),
    "zai-org/GLM-5.3-Flash": (0.15, 0.50),
    "zai-org/GLM-4.6": (0.55, 2.20),
    "zai-org/GLM-4.7": (0.55, 2.20),
    "zai-org/GLM-5": (0.95, 3.15),
    "zai-org/GLM-5.1": (1.30, 4.30),
    "zai-org/GLM-5.2": (1.40, 4.40),
}


def main() -> None:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "out/dev/usage.jsonl")
    total = 0.0
    cases = 0
    by_model: dict[str, float] = {}
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        cases += 1
        rec = json.loads(line)
        case_cost = 0.0
        for model, usage in rec.get("models", {}).items():
            pin, pout = PRICES.get(model, (0.0, 0.0))
            cost = usage.get("prompt_tokens", 0) * pin / 1_000_000 + usage.get("completion_tokens", 0) * pout / 1_000_000
            by_model[model] = by_model.get(model, 0.0) + cost
            case_cost += cost
        total += case_cost
        print(f"row {rec.get('row_id')}: ${case_cost:.4f}  {rec.get('wall_s', 0)}s")
    print(f"\n{cases} cases: ${total:.4f} total, ${total / max(cases, 1):.4f}/case")
    for model, cost in sorted(by_model.items()):
        print(f"{model}: ${cost:.4f}")


if __name__ == "__main__":
    main()
