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
from collections import defaultdict
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
    reason_for,
    solve as heuristic_solve,
)

STRONG = ["zai-org/GLM-5.2", "zai-org/GLM-5.1"]
CANDIDATES = 12
KPIS_EACH = 4
REASON_EVIDENCE_EACH = 6
LEGAL_BACKFILL = 10


def _model(tier: list[str]) -> list[str]:
    if os.environ.get("MANTIS_MODELS"):
        return [m.strip() for m in os.environ["MANTIS_MODELS"].split(",") if m.strip()]
    return [os.environ["RCA_MODEL"]] if os.environ.get("RCA_MODEL") else tier


def _json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    return json.loads(match.group(0)) if match else {}


def _component_service(component: str) -> str:
    if component.startswith("node-"):
        return component
    return re.sub(r"-\d+$", "", component)


def _host_node(row: pd.Series) -> str | None:
    cmdb_id = str(row.get("cmdb_id", ""))
    match = re.match(r"(node-\d+)\.", cmdb_id)
    return match.group(1) if match else None


def _reason_hint(kpi: str, component: str) -> tuple[str | None, str]:
    reason = reason_for(kpi, component)
    if reason:
        return reason, "direct"
    lowered = kpi.lower()
    if component.startswith("node-") and ("system.mem" in lowered or ".mem." in lowered):
        return "node memory consumption", "direct"
    if component.startswith("node-") and any(
        part in lowered for part in ("system.io.r_", "system.io.read", "disk_read")
    ):
        return "node disk read I/O consumption", "direct"
    if component.startswith("node-") and any(
        part in lowered for part in ("system.io.w_", "system.io.write", "disk_write")
    ):
        return "node disk write I/O consumption", "direct"
    if not component.startswith("node-") and any(
        part in lowered for part in ("fs_usage", "filesystem", "disk_usage")
    ):
        return "container read I/O load", "inferred_storage"
    return None, ""


def _reason_evidence_for_rows(rows: pd.DataFrame, component: str, source: str) -> list[dict]:
    evidence = []
    for row in rows.head(40).itertuples(index=False):
        reason, hint = _reason_hint(str(row.kpi_name), component)
        if not reason:
            continue
        evidence.append({
            "reason": reason,
            "kpi": str(row.kpi_name),
            "z": round(float(row.z), 1),
            "source": source,
            "hint": hint,
        })
    evidence.sort(key=lambda item: item["z"], reverse=True)
    seen = set()
    unique = []
    for item in evidence:
        key = (item["reason"], item["source"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= REASON_EVIDENCE_EACH:
            break
    return unique


def _reason_evidence(a: Analysis, component: str, kpis: pd.DataFrame) -> tuple[list[dict], str]:
    direct = _reason_evidence_for_rows(kpis, component, "candidate_metric")
    if component.startswith("node-"):
        return direct, "direct_kpi_match" if direct else "fallback_reason"

    hosts = {
        host
        for host in (_host_node(row) for _, row in kpis.head(20).iterrows())
        if host and host in a.ranked.index
    }
    host_evidence: list[dict] = []
    for host in sorted(hosts):
        host_rows = a.j[a.j.component == host]
        host_evidence.extend(_reason_evidence_for_rows(host_rows, host, "host_node_metric")[:3])
    combined = direct + host_evidence
    if direct:
        quality = "direct_kpi_match"
    elif host_evidence:
        quality = "host_node_support_only"
    else:
        quality = "fallback_reason"
    return combined[:REASON_EVIDENCE_EACH], quality


def _candidate_rows(a: Analysis, service_rows: list[dict]) -> list[dict]:
    rows = []
    components = list(a.ranked.head(8).index)
    symptomatic_services = {row["service"].replace("-grpc", "") for row in service_rows[:5]}
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

    legal_rows = []
    for row in a.j.itertuples(index=False):
        reason, hint = _reason_hint(str(row.kpi_name), str(row.component))
        if not reason:
            continue
        legal_rows.append({
            "component": str(row.component),
            "reason": reason,
            "hint": hint,
            "z": float(row.z),
        })
    legal_scores: dict[str, float] = {}
    for row in legal_rows:
        multiplier = 0.5 if row["hint"] == "inferred_storage" else 1.0
        legal_scores[row["component"]] = max(
            legal_scores.get(row["component"], 0.0),
            row["z"] * multiplier,
        )
    for component, _ in sorted(legal_scores.items(), key=lambda item: item[1], reverse=True):
        if component not in components:
            components.append(component)
        if len(components) >= CANDIDATES + LEGAL_BACKFILL:
            break
    for component, _ in sorted(
        ((component, score) for component, score in legal_scores.items() if component.startswith("node-")),
        key=lambda item: item[1],
        reverse=True,
    ):
        if component not in components:
            components.append(component)

    selected = components[:CANDIDATES + LEGAL_BACKFILL]
    for component in components[CANDIDATES + LEGAL_BACKFILL:]:
        if component.startswith("node-") and component not in selected:
            selected.append(component)

    for rank, component in enumerate(selected, 1):
        z = a.ranked[component]
        component_kpis = a.j[a.j.component == component]
        kpis = component_kpis.head(KPIS_EACH)
        heuristic = answer_for(a, component)
        reason_evidence, reason_quality = _reason_evidence(a, component, component_kpis)
        service_match = _component_service(component) in symptomatic_services
        evidence_score = float(z)
        if reason_quality == "fallback_reason":
            evidence_score *= 0.2
        elif reason_quality == "host_node_support_only":
            evidence_score *= 0.5
        if reason_evidence:
            evidence_score += min(max(item["z"] for item in reason_evidence), 100.0) * 0.5
        if service_match:
            evidence_score += 75.0
        rows.append({
            "rank": rank,
            "component": component,
            "service": _component_service(component),
            "peak_z": round(float(z), 1),
            "evidence_score": round(evidence_score, 1),
            "service_match": service_match,
            "heuristic_reason": heuristic["reason"],
            "reason_quality": reason_quality,
            "reason_evidence": reason_evidence,
            "heuristic_time": heuristic["datetime"],
            "top_kpis": [
                {"kpi": str(k.kpi_name), "z": round(float(k.z), 1)}
                for k in kpis.itertuples()
            ],
        })
    rows.sort(key=lambda row: row["evidence_score"], reverse=True)
    for rank, row in enumerate(rows, 1):
        row["rank"] = rank
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


def _trace_summary(a: Analysis, dataset_dir: Path, candidates: list[dict]) -> list[dict]:
    path = dataset_dir / "telemetry" / a.lo.strftime("%Y_%m_%d") / "trace" / "trace_span.csv"
    if not path.exists():
        return []

    candidate_components = {row["component"] for row in candidates}
    if not candidate_components:
        return []

    lo_ms, hi_ms = int(a.lo.timestamp() * 1000), int(a.hi.timestamp() * 1000)
    stats = defaultdict(lambda: {"in": [], "out": [], "errors": 0, "first_error_ms": None})
    usecols = ["timestamp", "cmdb_id", "duration", "status_code", "operation_name"]

    try:
        chunks = pd.read_csv(path, usecols=usecols, chunksize=250_000)
        for chunk in chunks:
            chunk = chunk[chunk.cmdb_id.isin(candidate_components)]
            if chunk.empty:
                continue
            chunk["timestamp"] = pd.to_numeric(chunk["timestamp"], errors="coerce")
            chunk["duration"] = pd.to_numeric(chunk["duration"], errors="coerce")
            chunk = chunk.dropna(subset=["timestamp", "duration"])
            in_window = chunk[(chunk.timestamp >= lo_ms) & (chunk.timestamp < hi_ms)]
            out_window = chunk[(chunk.timestamp < lo_ms) | (chunk.timestamp >= hi_ms)]
            for comp, values in in_window.groupby("cmdb_id").duration:
                stats[comp]["in"].extend(values.tolist())
            for comp, values in out_window.groupby("cmdb_id").duration:
                stats[comp]["out"].extend(values.sample(min(len(values), 2000), random_state=1).tolist())
            errors = in_window[in_window.status_code.astype(str).str.lower().ne("0")]
            errors = errors[errors.status_code.astype(str).str.lower().ne("ok")]
            for comp, group in errors.groupby("cmdb_id"):
                stats[comp]["errors"] += len(group)
                first = int(group.timestamp.min())
                current = stats[comp]["first_error_ms"]
                stats[comp]["first_error_ms"] = first if current is None else min(current, first)
    except Exception:
        return []

    rows = []
    for comp, s in stats.items():
        if not s["in"]:
            continue
        in_series = pd.Series(s["in"])
        out_series = pd.Series(s["out"]) if s["out"] else pd.Series(dtype=float)
        p95 = float(in_series.quantile(0.95))
        baseline = float(out_series.quantile(0.95)) if len(out_series) else None
        ratio = round(p95 / baseline, 2) if baseline and baseline > 0 else None
        first_error = None
        if s["first_error_ms"] is not None:
            first_error = pd.to_datetime(s["first_error_ms"], unit="ms").strftime("%Y-%m-%d %H:%M:%S")
        rows.append({
            "component": comp,
            "span_count": len(s["in"]),
            "p95_duration_window": round(p95, 1),
            "p95_duration_baseline": round(baseline, 1) if baseline else None,
            "p95_ratio": ratio,
            "error_spans": s["errors"],
            "first_error_time": first_error,
        })

    rows.sort(key=lambda row: (row["p95_ratio"] or 0, row["error_spans"], row["span_count"]), reverse=True)
    return rows[:8]


def _decide_with_llm(
    a: Analysis,
    candidates: list[dict],
    service_rows: list[dict],
    trace_rows: list[dict],
) -> tuple[list[dict], dict, dict]:
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
        "trace_symptoms": trace_rows,
        "instructions": [
            "Choose exactly failure_count answers.",
            "Pick components only from candidate_components.component.",
            "Pick reasons exactly from legal_reasons.",
            "Prefer root causes over downstream symptoms.",
            "Do not choose a node only because aggregate TCP/network counters are huge; node network counters often reflect downstream traffic.",
            "When a pod/service candidate appears in both candidate_components and service_symptoms, consider it seriously even if its peak_z is lower than a node.",
            "When a candidate also has trace_symptoms with high p95_ratio or errors, use that as causal evidence.",
            "Treat candidate_components.reason_quality=fallback_reason as weak evidence; it means the top KPI did not map cleanly to the proposed reason.",
            "Use candidate_components.reason_evidence to select the legal reason; candidate_metric evidence is stronger than host_node_metric evidence.",
            "Reason evidence with hint=inferred_storage is weaker than direct keyword evidence, but it can support container read/write I/O when the dataset exposes filesystem usage instead of read/write counters.",
            "host_node_metric evidence can explain a pod through its host, but should not override direct candidate_metric evidence.",
            "For service-level symptoms, prefer the matching pod candidate over unrelated noisy peers unless there is direct node resource evidence.",
            "Keep the JSON compact: no prose outside JSON and no long explanations.",
            "Reply with JSON only.",
        ],
        "response_schema": {
            "answers": [{"component": "...", "reason": "..."}],
            "confidence": "low|medium|high",
            "why": "brief reasoning",
            "ruled_out": [{"component": "...", "why": "..."}],
        },
    }
    text = llm.ask(_model(STRONG), json.dumps(prompt, indent=2), max_tokens=500)
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
    trace_rows: list[dict],
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
        reasons = ", ".join(
            f"{r['reason']} via {r['source']}:{r['kpi']} z={r['z']}"
            for r in row.get("reason_evidence", [])[:3]
        ) or "no mapped reason-specific KPI"
        lines.append(
            f"- `{row['component']}`: evidence score={row['evidence_score']}, peak z={row['peak_z']}; "
            f"heuristic reason `{row['heuristic_reason']}` ({row['reason_quality']}) "
            f"at {row['heuristic_time']}; service_match={row['service_match']}; {kpis}; reasons: {reasons}"
        )
    if service_rows:
        lines += ["", "Service-level symptoms:"]
        for row in service_rows[:5]:
            lines.append(
                f"- `{row['service']}`: mrt {row['mrt_window']} vs baseline {row['mrt_base']} "
                f"(ratio {row['latency_ratio']}), success {row['sr_window']} vs {row['sr_base']}"
            )
    if trace_rows:
        lines += ["", "Trace symptoms:"]
        for row in trace_rows[:8]:
            lines.append(
                f"- `{row['component']}`: {row['span_count']} spans, p95 duration "
                f"{row['p95_duration_window']} vs baseline {row['p95_duration_baseline']} "
                f"(ratio {row['p95_ratio']}), error spans {row['error_spans']}"
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
    trace_rows = []
    if os.environ.get("MANTIS_TRACE_SUMMARY") == "1":
        trace_rows = _trace_summary(a, Path(dataset_dir), candidates)
    notes: list[str] = []
    decision: dict = {}
    usage: dict = {}

    try:
        answers, decision, usage = _decide_with_llm(a, candidates, service_rows, trace_rows)
    except Exception as exc:
        notes.append(f"LLM decision failed or was unavailable: {type(exc).__name__}: {exc}")
        answers = [answer_for(a, c) for c in a.ranked.head(a.n).index]

    evidence = _evidence(a, answers, candidates, service_rows, trace_rows, decision, notes, usage)
    return Solution(prediction=format_prediction(answers), evidence=evidence, usage=usage)
