"""First MantisGrid RCA agent.

This is intentionally small. Python builds a compact evidence packet; one GLM
call may choose from grounded candidates; Python validates and formats output.
If the model is unavailable, the agent falls back to the free heuristic answer.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm import LLM  # noqa: E402
from run import Solution, format_prediction  # noqa: E402
from agents.heuristic import (  # noqa: E402
    NODE_REASONS,
    POD_REASONS,
    Analysis,
    analyse,
    answer_for,
    solve as heuristic_solve,
)

STRONG = ["zai-org/GLM-5.2", "zai-org/GLM-5.1"]
CANDIDATES = 12
KPIS_EACH = 4


def _model(tier: list[str]) -> list[str]:
    return [os.environ["RCA_MODEL"]] if os.environ.get("RCA_MODEL") else tier


def _json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0)) if match else {}


def _component_service(component: str) -> str:
    if component.startswith("node-"):
        return component
    return re.sub(r"-\d+$", "", component)


def _candidate_rows(a: Analysis, service_rows: list[dict]) -> list[dict]:
    rows = []
    components = list(a.ranked.head(8).index)
    service_matches: list[list[str]] = []
    for service_row in service_rows[:5]:
        service = service_row["service"].replace("-grpc", "")
        matches = [c for c in a.ranked.index if _component_service(c) == service]
        service_matches.append(matches[:2])

    for matches in service_matches:
        if matches and matches[0] not in components:
            components.append(matches[0])

    for matches in service_matches:
        for component in matches[1:]:
            if component not in components:
                components.append(component)
            if len(components) >= CANDIDATES:
                break
        if len(components) >= CANDIDATES:
            break

    for rank, component in enumerate(components[:CANDIDATES], 1):
        z = a.ranked[component]
        kpis = a.j[a.j.component == component].head(KPIS_EACH)
        heuristic = answer_for(a, component)
        rows.append({
            "rank": rank,
            "component": component,
            "service": _component_service(component),
            "peak_z": round(float(z), 1),
            "heuristic_reason": heuristic["reason"],
            "heuristic_time": heuristic["datetime"],
            "top_kpis": [
                {"kpi": str(k.kpi_name), "z": round(float(k.z), 1)}
                for k in kpis.itertuples()
            ],
        })
    return rows


def _service_summary(a: Analysis, dataset_dir: Path) -> list[dict]:
    path = dataset_dir / "telemetry" / a.lo.strftime("%Y_%m_%d") / "metric" / "metric_service.csv"
    if not path.exists():
        return []
    lo_s, hi_s = a.lo.timestamp(), a.hi.timestamp()
    try:
        df = pd.read_csv(path)
    except Exception:
        return []
    inw = df[(df.timestamp >= lo_s) & (df.timestamp < hi_s)]
    out = df[(df.timestamp < lo_s) | (df.timestamp >= hi_s)]
    if inw.empty or out.empty:
        return []

    rows = []
    base = out.groupby("service").agg(
        mrt_base=("mrt", "median"),
        sr_base=("sr", "median"),
        count_base=("count", "median"),
    )
    cur = inw.groupby("service").agg(
        mrt_window=("mrt", "max"),
        sr_window=("sr", "min"),
        count_window=("count", "max"),
    )
    joined = cur.join(base, how="inner").reset_index()
    joined["latency_ratio"] = joined.mrt_window / joined.mrt_base.replace(0, pd.NA)
    joined["success_drop"] = joined.sr_base - joined.sr_window
    joined = joined.sort_values(["latency_ratio", "success_drop"], ascending=False)
    for row in joined.head(8).itertuples(index=False):
        rows.append({
            "service": str(row.service),
            "mrt_window": round(float(row.mrt_window), 3),
            "mrt_base": round(float(row.mrt_base), 3),
            "latency_ratio": round(float(row.latency_ratio), 2) if pd.notna(row.latency_ratio) else None,
            "sr_window": round(float(row.sr_window), 3),
            "sr_base": round(float(row.sr_base), 3),
            "success_drop": round(float(row.success_drop), 3),
        })
    return rows


def _decide_with_llm(a: Analysis, candidates: list[dict], service_rows: list[dict]) -> tuple[list[dict], dict, dict]:
    llm = LLM()
    legal = sorted(set(NODE_REASONS.values()) | set(POD_REASONS.values()))
    prompt = {
        "task": "Root cause analysis over microservice telemetry",
        "window": {
            "start": a.lo.strftime("%Y-%m-%d %H:%M:%S"),
            "end": a.hi.strftime("%Y-%m-%d %H:%M:%S"),
            "timezone_note": "timestamps in predictions must use the dataset's UTC+8 convention",
        },
        "failure_count": a.n,
        "legal_reasons": legal,
        "candidate_components": candidates,
        "service_symptoms": service_rows,
        "instructions": [
            "Choose exactly failure_count answers.",
            "Pick components only from candidate_components.component.",
            "Pick reasons exactly from legal_reasons.",
            "Prefer root causes over downstream symptoms.",
            "Reply with JSON only.",
        ],
        "response_schema": {
            "answers": [{"component": "...", "reason": "..."}],
            "confidence": "low|medium|high",
            "why": "brief reasoning",
            "ruled_out": [{"component": "...", "why": "..."}],
        },
    }
    text = llm.ask(_model(STRONG), json.dumps(prompt, indent=2))
    decision = _json(text)
    answers = _validated_answers(a, decision.get("answers") or [])
    return answers, decision, llm.usage


def _validated_answers(a: Analysis, picks: list[dict]) -> list[dict]:
    fallback = [answer_for(a, c) for c in a.ranked.head(a.n).index]
    legal = set(NODE_REASONS.values()) | set(POD_REASONS.values())
    answers = []
    for i in range(a.n):
        pick = picks[i] if i < len(picks) and isinstance(picks[i], dict) else {}
        component = pick.get("component")
        reason = pick.get("reason")
        if component not in a.ranked.index:
            answers.append(fallback[i])
            continue
        answer = answer_for(a, component)
        if reason in legal:
            answer["reason"] = reason
        answers.append(answer)
    return answers


def _evidence(
    a: Analysis,
    answers: list[dict],
    candidates: list[dict],
    service_rows: list[dict],
    decision: dict,
    notes: list[str],
    usage: dict,
) -> str:
    lines = ["## Answer", ""]
    for i, answer in enumerate(answers, 1):
        lines.append(
            f"{i}. `{answer['component']}` / `{answer['reason']}` / `{answer['datetime']}`"
        )
    lines += ["", "## Confidence", ""]
    confidence = decision.get("confidence", "low")
    why = decision.get("why") or "First slice: confidence is conservative until logs/traces are added."
    lines.append(f"{confidence.capitalize()}. {why}")

    lines += ["", "## Evidence", "", "Top metric candidates:"]
    for row in candidates:
        kpis = ", ".join(f"{k['kpi']} z={k['z']}" for k in row["top_kpis"][:3])
        lines.append(
            f"- `{row['component']}`: peak z={row['peak_z']}; "
            f"heuristic reason `{row['heuristic_reason']}` at {row['heuristic_time']}; {kpis}"
        )
    if service_rows:
        lines += ["", "Service-level symptoms:"]
        for row in service_rows[:5]:
            lines.append(
                f"- `{row['service']}`: mrt {row['mrt_window']} vs baseline {row['mrt_base']} "
                f"(ratio {row['latency_ratio']}), success {row['sr_window']} vs {row['sr_base']}"
            )

    lines += ["", "## Ruled out", ""]
    ruled = decision.get("ruled_out") or []
    if ruled:
        for item in ruled[:5]:
            lines.append(f"- `{item.get('component', 'unknown')}`: {item.get('why', '')}")
    else:
        for row in candidates[len(answers): min(len(candidates), len(answers) + 5)]:
            lines.append(f"- `{row['component']}`: lower-ranked metric candidate in this first slice.")

    lines += ["", "## Limitations", ""]
    lines.append("- This first slice uses metrics and service-level symptoms.")
    lines.append("- It does not yet deeply inspect traces or proxy logs.")
    lines.append("- The model only sees compact summaries, not raw telemetry.")
    for note in notes:
        lines.append(f"- {note}")
    if usage:
        lines += ["", "## Model usage", ""]
        for model, counts in usage.items():
            lines.append(
                f"- `{model}`: {counts.get('calls', 0)} call(s), "
                f"{counts.get('prompt_tokens', 0):,} input / "
                f"{counts.get('completion_tokens', 0):,} output tokens"
            )
    return "\n".join(lines) + "\n"


def solve(instruction: str, dataset_dir: Path, ctx: dict) -> Solution:
    a = analyse(instruction, dataset_dir)
    if not isinstance(a, Analysis):
        return a

    service_rows = _service_summary(a, Path(dataset_dir))
    candidates = _candidate_rows(a, service_rows)
    notes: list[str] = []
    decision: dict = {}
    usage: dict = {}

    try:
        answers, decision, usage = _decide_with_llm(a, candidates, service_rows)
    except Exception as exc:
        notes.append(f"LLM decision failed or was unavailable: {type(exc).__name__}: {exc}")
        answers = [answer_for(a, c) for c in a.ranked.head(a.n).index]

    evidence = _evidence(a, answers, candidates, service_rows, decision, notes, usage)
    return Solution(prediction=format_prediction(answers), evidence=evidence, usage=usage)
