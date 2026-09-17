from __future__ import annotations

import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from llm import LLM  # noqa: E402
from run import Solution, format_prediction  # noqa: E402


MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}

REASONS = [
    "container CPU load",
    "container memory load",
    "container network latency",
    "container network packet corruption",
    "container network packet retransmission",
    "container packet loss",
    "container process termination",
    "container read I/O load",
    "container write I/O load",
    "node CPU load",
    "node CPU spike",
    "node disk read I/O consumption",
    "node disk space consumption",
    "node disk write I/O consumption",
    "node memory consumption",
]

NODE_REASONS = {
    "cpu": "node CPU load",
    "spike": "node CPU spike",
    "memory": "node memory consumption",
    "read": "node disk read I/O consumption",
    "write": "node disk write I/O consumption",
    "space": "node disk space consumption",
}
POD_REASONS = {
    "cpu": "container CPU load",
    "memory": "container memory load",
    "latency": "container network latency",
    "loss": "container packet loss",
    "retrans": "container network packet retransmission",
    "corrupt": "container network packet corruption",
    "kill": "container process termination",
    "read": "container read I/O load",
    "write": "container write I/O load",
}

CHEAP = ["zai-org/GLM-4.7-Flash", "zai-org/GLM-5.3-Flash"]
STRONG = ["zai-org/GLM-5.2", "zai-org/GLM-5.1"]
_DAY_CACHE: dict[tuple[str, str], pd.DataFrame] = {}


@dataclass
class Candidate:
    component: str
    reason: str
    when: datetime
    score: float
    source: str
    facts: list[str] = field(default_factory=list)


def _models(tier: list[str]) -> list[str]:
    return [os.environ["RCA_MODEL"]] if os.environ.get("RCA_MODEL") else tier


def _llm_tier(n: int, cands: list[Candidate]) -> tuple[list[str], str]:
    if os.environ.get("RCA_MODEL"):
        return _models(STRONG), "single-model override"
    if n > 1 or len(cands) < 2:
        return STRONG, "strong: multi-failure or sparse candidate set"
    top, second = cands[0].score, max(cands[1].score, 1.0)
    if top >= 150 and top / second >= 2.5:
        return CHEAP + STRONG, "routed cheap-first: one dominant candidate"
    return STRONG, "strong: ambiguous candidate ranking"


def parse_window(instruction: str) -> tuple[datetime, datetime] | None:
    m = re.search(
        r"(\w+)\s+(\d{1,2}),?\s+(\d{4}).{0,60}?(\d{1,2}):(\d{2})"
        r"\s*(?:to|-|and|until)\s*.{0,60}?(\d{1,2}):(\d{2})",
        instruction,
        re.I | re.S,
    )
    if not m:
        return None
    mon, day, year, h1, m1, h2, m2 = m.groups()
    if mon.lower() not in MONTHS:
        return None
    base = datetime(int(year), MONTHS[mon.lower()], int(day), tzinfo=timezone.utc)
    lo = base + timedelta(hours=int(h1), minutes=int(m1))
    hi = base + timedelta(hours=int(h2), minutes=int(m2))
    if hi <= lo:
        hi += timedelta(days=1)
    return lo, hi


def failure_count(instruction: str) -> int:
    t = instruction.lower()
    for word, n in (("one failure", 1), ("a single failure", 1), ("two failures", 2),
                    ("three failures", 3), ("four failures", 4)):
        if word in t:
            return n
    m = re.search(r"experienced\s+(\d+)\s+failures?", t)
    return int(m.group(1)) if m else 1


def component_of(cmdb_id: str) -> str:
    s = str(cmdb_id)
    if ".destination." in s:
        return s.split(".destination.", 1)[0]
    return s.split(".", 1)[1] if "." in s else s


def reason_for(kpi: str, component: str) -> str | None:
    k = str(kpi).lower()
    table = NODE_REASONS if component.startswith("node-") else POD_REASONS
    if any(x in k for x in ("terminate", "killed", "oom", "restart")):
        return table.get("kill")
    if any(x in k for x in ("packet_loss", "drop", "dropped")):
        return table.get("loss")
    if "retrans" in k:
        return table.get("retrans")
    if "corrupt" in k:
        return table.get("corrupt")
    if any(x in k for x in ("disk_read", "read_bytes", "diskio_read", "read_io")):
        return table.get("read")
    if any(x in k for x in ("disk_write", "write_bytes", "diskio_write", "write_io")):
        return table.get("write")
    if any(x in k for x in ("disk_space", "fs_usage", "filesystem", "disk_usage")):
        return table.get("space")
    if any(x in k for x in ("memory", "mem_", "pgfault", "rss")):
        return table.get("memory")
    if "cpu" in k:
        return table.get("cpu")
    if any(x in k for x in ("latency", "rtt", "delay", "network", "net_", "tcp", "rx", "tx")):
        return table.get("latency")
    return None


def _read_metrics(dataset: Path, date: str) -> pd.DataFrame:
    key = (str(dataset), date)
    if key in _DAY_CACHE:
        return _DAY_CACHE[key]
    frames = []
    metric_dir = dataset / "telemetry" / date / "metric"
    for name in ("metric_container", "metric_node", "metric_service", "metric_mesh"):
        f = metric_dir / f"{name}.csv"
        if not f.exists():
            continue
        if name == "metric_service":
            df = pd.read_csv(f)
            melted = df.melt(id_vars=["service", "timestamp"], var_name="kpi_name", value_name="value")
            melted = melted.rename(columns={"service": "cmdb_id"})
            melted["source"] = name
            frames.append(melted[["timestamp", "cmdb_id", "kpi_name", "value", "source"]])
        else:
            df = pd.read_csv(f, usecols=["timestamp", "cmdb_id", "kpi_name", "value"])
            df["source"] = name
            frames.append(df)
    out = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(
        columns=["timestamp", "cmdb_id", "kpi_name", "value", "source"])
    _DAY_CACHE[key] = out
    return out


def metric_candidates(dataset: Path, lo: datetime, hi: datetime) -> list[Candidate]:
    day = _read_metrics(dataset, lo.strftime("%Y_%m_%d"))
    if day.empty:
        return []
    lo_s, hi_s = lo.timestamp(), hi.timestamp()
    inw = day[(day.timestamp >= lo_s) & (day.timestamp < hi_s)]
    out = day[(day.timestamp < lo_s) | (day.timestamp >= hi_s)]
    if inw.empty or out.empty:
        return []
    base = out.groupby(["cmdb_id", "kpi_name"]).value.agg(
        med="median", mad=lambda s: (s - s.median()).abs().median())
    peak = inw.groupby(["cmdb_id", "kpi_name"]).value.agg(["max", "min", "mean"])
    j = peak.join(base, how="inner").reset_index()
    j = j[j.mad > 0].copy()
    if j.empty:
        return []
    j["z"] = np.maximum((j["max"] - j.med).abs(), (j["min"] - j.med).abs()) / (1.4826 * j.mad)
    j["component"] = j.cmdb_id.map(component_of)
    j = j.sort_values("z", ascending=False)
    candidates: list[Candidate] = []
    for comp, sub in j.groupby("component", sort=False):
        picked = None
        reason = None
        for row in sub.itertuples(index=False):
            reason = reason_for(row.kpi_name, comp)
            if reason:
                picked = row
                break
        if picked is None:
            picked = sub.iloc[0]
            reason = "node CPU load" if comp.startswith("node-") else "container CPU load"
        series = inw[(inw.cmdb_id == picked.cmdb_id) & (inw.kpi_name == picked.kpi_name)]
        when = lo
        if not series.empty:
            idx = (series.value - picked.med).abs().idxmax()
            when = datetime.fromtimestamp(float(series.loc[idx, "timestamp"]), tz=timezone.utc)
        facts = [
            f"{picked.source}/{picked.cmdb_id}/{picked.kpi_name}: robust z={float(picked.z):.1f}, "
            f"baseline median={float(picked.med):.4g}, in-window min={float(picked.min):.4g}, "
            f"max={float(picked.max):.4g}",
        ]
        candidates.append(Candidate(comp, reason or "container CPU load", when, float(picked.z), "metrics", facts))
    return sorted(candidates, key=lambda c: c.score, reverse=True)


def trace_candidates(dataset: Path, lo: datetime, hi: datetime) -> list[Candidate]:
    f = dataset / "telemetry" / lo.strftime("%Y_%m_%d") / "trace" / "trace_span.csv"
    if not f.exists():
        return []
    lo_ms, hi_ms = int(lo.timestamp() * 1000), int(hi.timestamp() * 1000)
    frames = []
    usecols = ["timestamp", "cmdb_id", "span_id", "trace_id", "duration", "status_code", "parent_span"]
    try:
        for chunk in pd.read_csv(f, usecols=usecols, chunksize=250_000):
            w = chunk[(chunk.timestamp >= lo_ms) & (chunk.timestamp < hi_ms)]
            if not w.empty:
                frames.append(w)
    except ValueError:
        return []
    if not frames:
        return []
    df = pd.concat(frames, ignore_index=True)
    df["component"] = df.cmdb_id.map(component_of)
    df["duration"] = pd.to_numeric(df.duration, errors="coerce").fillna(0)
    df["bad"] = ~df.status_code.astype(str).str.lower().isin(("0", "ok", "nan", "none", ""))
    g = df.groupby("component").agg(
        spans=("span_id", "count"),
        p95_ms=("duration", lambda s: float(np.percentile(s, 95))),
        max_ms=("duration", "max"),
        errors=("bad", "sum"),
        first_ms=("timestamp", "min"),
    )
    candidates = []
    for comp, row in g.sort_values(["errors", "p95_ms"], ascending=False).head(12).iterrows():
        if row.spans < 5:
            continue
        score = float(row.p95_ms) / 100.0 + float(row.errors) * 5.0
        when = datetime.fromtimestamp(float(row.first_ms) / 1000.0, tz=timezone.utc)
        reason = "container network latency"
        if row.errors > max(3, row.spans * 0.02):
            reason = "container packet loss"
        facts = [
            f"trace_span.csv: {int(row.spans)} spans in window, p95 duration={row.p95_ms:.1f}ms, "
            f"max={row.max_ms:.1f}ms, non-OK spans={int(row.errors)}",
        ]
        candidates.append(Candidate(comp, reason, when, score, "traces", facts))
    return candidates


def log_candidates(dataset: Path, lo: datetime, hi: datetime) -> list[Candidate]:
    log_dir = dataset / "telemetry" / lo.strftime("%Y_%m_%d") / "log"
    lo_s, hi_s = lo.timestamp(), hi.timestamp()
    hits: dict[str, list[str]] = {}
    for name in ("log_service", "log_proxy"):
        f = log_dir / f"{name}.csv"
        if not f.exists():
            continue
        try:
            for chunk in pd.read_csv(f, chunksize=250_000):
                if "timestamp" not in chunk or "cmdb_id" not in chunk:
                    continue
                chunk["timestamp"] = pd.to_numeric(chunk["timestamp"], errors="coerce")
                w = chunk[(chunk.timestamp >= lo_s) & (chunk.timestamp < hi_s)]
                if w.empty:
                    continue
                text_cols = [c for c in ("log_name", "value") if c in w]
                if not text_cols:
                    continue
                text = w[text_cols].astype(str).agg(" ".join, axis=1).str.lower()
                mask = text.str.contains("kill|killed|oom|restart|terminate|error|exception|timeout", regex=True, na=False)
                for r in w[mask].head(200).itertuples(index=False):
                    comp = component_of(getattr(r, "cmdb_id"))
                    hits.setdefault(comp, []).append(f"{name}: {getattr(r, 'log_name', '')} {str(getattr(r, 'value', ''))[:120]}")
        except Exception:
            continue
    out = []
    for comp, rows in hits.items():
        reason = "container process termination" if any(re.search("kill|oom|restart|terminate", x, re.I) for x in rows) else "container network latency"
        out.append(Candidate(comp, reason, lo, 50 + len(rows), "logs", rows[:4]))
    return out


def merge_candidates(cands: list[Candidate]) -> list[Candidate]:
    merged: dict[tuple[str, str], Candidate] = {}
    for c in cands:
        key = (c.component, c.reason)
        prev = merged.get(key)
        if prev is None:
            merged[key] = c
        else:
            prev.score += c.score * 0.5
            prev.facts.extend(c.facts)
            if c.when < prev.when:
                prev.when = c.when
    return sorted(merged.values(), key=lambda x: x.score, reverse=True)


def _extract_json(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    return json.loads(m.group(0)) if m else {}


def llm_refine(instruction: str, lo: datetime, hi: datetime, n: int, cands: list[Candidate]) -> tuple[list[Candidate], dict, dict]:
    if not os.environ.get("FEATHERLESS_API_KEY"):
        return cands[:n], {}, {}
    llm = LLM()
    models, routing_note = _llm_tier(n, cands)
    brief = []
    for i, c in enumerate(cands[:14], 1):
        brief.append(
            f"{i}. component={c.component}; reason={c.reason}; time={c.when:%Y-%m-%d %H:%M:%S}; "
            f"score={c.score:.1f}; source={c.source}; facts={' | '.join(c.facts[:2])}"
        )
    prompt = (
        f"Pick the {n} most likely root-cause failure(s) for this OpenRCA microservice incident. "
        f"Window: {lo:%Y-%m-%d %H:%M:%S} to {hi:%Y-%m-%d %H:%M:%S} UTC+8 timestamps as written. "
        "Prefer causes that move first and explain downstream symptoms. Network faults may only be visible in traces. "
        "Use only listed components and exactly one legal reason. "
        "Node components may only use node reasons; non-node components may only use container reasons. "
        "A very large node TCP/network metric is often traffic from affected services, not a legal node root-cause reason. "
        "Do not invent components, times, reasons, telemetry, or confidence.\n\n"
        f"Question:\n{instruction}\n\nLegal reasons:\n{json.dumps(REASONS)}\n\nCandidates:\n" + "\n".join(brief) +
        '\n\nReply JSON only: {"answers":[{"component":"...","reason":"..."}],'
        '"confidence":"low|medium|high","why":"short explanation","ruled_out":[{"component":"...","why":"..."}]}'
    )
    try:
        raw = llm.ask(models, prompt, max_tokens=700)
        data = _extract_json(raw)
    except Exception as e:
        return cands[:n], {"confidence": "low", "why": f"LLM refinement failed: {type(e).__name__}: {e}"}, llm.usage
    data["routing"] = routing_note
    by_component = {c.component: c for c in cands}
    picked = []
    for item in data.get("answers", []):
        comp = item.get("component")
        reason = item.get("reason")
        if comp in by_component:
            base = by_component[comp]
            if reason in REASONS and (comp.startswith("node-") == reason.startswith("node")):
                base = Candidate(base.component, reason, base.when, base.score, base.source, base.facts)
            picked.append(base)
    for c in cands:
        if len(picked) >= n:
            break
        if c.component not in {p.component for p in picked}:
            picked.append(c)
    return picked[:n], data, llm.usage


def evidence(instruction: str, lo: datetime, hi: datetime, answers: list[Candidate], candidates: list[Candidate], llm_note: dict) -> str:
    lines = [
        "## Answer",
        "",
    ]
    for i, c in enumerate(answers, 1):
        lines.append(f"{i}. {c.component} / {c.reason} / {c.when:%Y-%m-%d %H:%M:%S}")
    confidence = llm_note.get("confidence") or ("medium" if answers and answers[0].score > 100 else "low")
    lines += [
        "",
        "## Confidence",
        "",
        f"{confidence.capitalize()}. {llm_note.get('why', 'Ranked by telemetry anomalies in the requested window; uncertainty remains because correlated symptoms can outrank causes.')}",
        "",
        "## Evidence",
        "",
    ]
    for c in answers:
        lines.append(f"- `{c.component}` at `{c.when:%Y-%m-%d %H:%M:%S}`: `{c.reason}` from {c.source}, score {c.score:.1f}.")
        for fact in c.facts[:5]:
            lines.append(f"  - {fact}")
    lines += [
        "",
        "## Ruled out",
        "",
    ]
    answer_components = {c.component for c in answers}
    for c in candidates[:10]:
        if c.component not in answer_components:
            lines.append(f"- `{c.component}`: candidate evidence was weaker or later ({c.source}, score {c.score:.1f}, guessed reason `{c.reason}`).")
    lines += [
        "",
        "## Method",
        "",
        f"- Parsed the instruction window as `{lo:%Y-%m-%d %H:%M:%S}` to `{hi:%Y-%m-%d %H:%M:%S}` using the dataset's UTC+8 answer convention and preserved the requested failure count.",
        "- Metrics/log timestamps were treated as seconds; trace timestamps were treated as milliseconds.",
        f"- Model routing: {llm_note.get('routing', 'no Featherless call; deterministic candidate ranking only')}.",
        "- Predictions always include a best guess; doubts stay in this evidence file.",
    ]
    return "\n".join(lines) + "\n"


def solve(instruction: str, dataset_dir: Path, ctx: dict) -> Solution:
    win = parse_window(instruction)
    n = failure_count(instruction)
    if not win:
        answers = [{"datetime": "2022-03-20 00:00:00", "component": "frontend-0", "reason": "container CPU load"} for _ in range(n)]
        return Solution(format_prediction(answers), "## Answer\n\nCould not parse the incident window; emitted a fallback guess.\n")
    lo, hi = win
    cands = merge_candidates(
        metric_candidates(dataset_dir, lo, hi)
        + trace_candidates(dataset_dir, lo, hi)
        + log_candidates(dataset_dir, lo, hi)
    )
    if not cands:
        cands = [Candidate("frontend-0", "container network latency", lo, 0.0, "fallback", ["No telemetry rows were readable in the requested window."])]
    answers, note, usage = llm_refine(instruction, lo, hi, n, cands)
    payload = [
        {"datetime": c.when.strftime("%Y-%m-%d %H:%M:%S"), "component": c.component, "reason": c.reason}
        for c in answers
    ]
    return Solution(format_prediction(payload), evidence(instruction, lo, hi, answers, cands, note), usage)
