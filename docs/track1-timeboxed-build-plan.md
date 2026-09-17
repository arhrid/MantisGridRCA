# Track 1 Time-Boxed Build Plan

## Goal

Build a small, reliable RCA command-line agent that beats the starter heuristic, produces defensible evidence, and gives us a credible routed-vs-baseline evaluation story.

The judged Track 1 artifact is not a UI. It is a headless command:

```bash
python run.py --dataset /data --queries /data/query.csv --out /out
```

Required outputs:

- `predictions.csv`
- `evidence/<row_id>.md`
- `usage.jsonl`

## Constraints

- Keep the official `run.py` contract intact.
- Do not build a broad framework.
- Do not build a GUI.
- Do not paste raw telemetry into an LLM prompt.
- Avoid full `log_proxy.csv` and deep trace processing until there is time; those files are large.
- Always emit a best guess, but be honest in evidence.
- Treat cost and wall-clock as product requirements, not polish.

## Scoring Priorities

Based on official scoring docs, prioritize:

1. Correct output mechanics.
   - Correct failure count.
   - Exact key order.
   - Exact legal component and reason strings.
   - Timestamp format and UTC+8 interpretation.
2. Evidence and explainability.
   - Worth more than raw accuracy.
   - Must cite concrete telemetry and ruled-out alternatives.
3. Evaluation quality.
   - Compare heuristic, routed starter, and our agent.
   - Report score, time, estimated cost, and failure modes.
4. Cost efficiency.
   - Python reduces data first.
   - LLM receives only compact candidate summaries.
   - Limit calls per case.

## Near-Term Scope

### 1. Harden Local Harness

Owner: anyone.

Deliverables:

- Local run script clears output by default, with opt-out if needed.
- Local run prints prediction vs `scoring_points`.
- Local run can score quickly.
- Commands for `LIMIT=N`, agent selection, and output path are documented.

Acceptance:

- `LIMIT=2 AGENT=agents.heuristic scripts/run_official_local.sh` runs cleanly.
- `LIMIT=2 AGENT=agents.routed scripts/run_official_local.sh` runs cleanly with `FEATHERLESS_API_KEY`.
- Stale outputs do not confuse results.

### 2. Build One Simple Real Agent

Create `agents/mantis.py` in the official starter-style agent shape.

Do not invent a large framework. Start from starter patterns:

- Use `Solution`.
- Use `format_prediction()`.
- Reuse heuristic parsing and metric analysis where helpful.
- Add only the minimum extra telemetry summarization needed.

Initial agent flow:

1. Parse query window and failure count.
2. Build deterministic evidence packet:
   - Top container metric anomalies.
   - Top node metric anomalies.
   - Service-level latency/success-rate anomalies from `metric_service.csv`.
   - Optional targeted service-log counts from `log_service.csv`.
3. Rank candidate root-cause components.
4. Send one compact LLM decision prompt.
5. Validate model output in Python.
6. Write deterministic evidence Markdown.

Acceptance:

- Runs with `LIMIT=10`.
- Produces valid `predictions.csv`.
- Produces useful `evidence/*.md`.
- Does not require UI or manual steps.

### 3. Keep Prompting Cheap

First version:

- One LLM decision call per case.
- No LLM call for evidence prose unless needed.
- Python templates the evidence.

Routing policy, first pass:

- Use a strong model only for the final compact decision.
- Try cheaper model experiments after the candidate packet is good.
- Keep deterministic fallback from heuristic if the model fails.

Future routing, if time:

- Cheap model for easy cases or formatting.
- Strong model only when top candidates are close, multi-failure cases appear, or network-like evidence is suspected.

### 4. Evaluate Quickly

Run three configurations:

```bash
LIMIT=10 AGENT=agents.heuristic scripts/run_official_local.sh
LIMIT=10 AGENT=agents.routed scripts/run_official_local.sh
LIMIT=10 AGENT=agents.mantis scripts/run_official_local.sh
```

Then score each output with `starter/score.py`.

Record:

- Mean score.
- Fully solved count.
- Score by task.
- Score by difficulty.
- Wall-clock seconds per case.
- Cost estimate where LLM usage exists.
- Obvious failure modes.

Acceptance:

- We know whether `agents.mantis` beats the heuristic.
- We can explain why it wins or fails.
- We have a defensible next tuning target.

## Evidence Template

Each `evidence/<row_id>.md` should include:

```markdown
## Answer

<component> / <reason> / <time if required>

## Confidence

Low|Medium|High. One or two sentences.

## Evidence

- Metric evidence...
- Service-level evidence...
- Log or trace evidence if inspected...

## Ruled out

- Candidate A: why less likely.
- Candidate B: why less likely.

## Limitations

- What was not inspected.
- Why this may be wrong.
```

## What To Avoid

- Spending time on UI.
- Sending raw CSV chunks to the model.
- Deep parsing `log_proxy.csv` before simpler signals are exhausted.
- Multi-agent orchestration.
- Refactoring starter code before we have a better score.
- Optimizing prompts before improving candidate evidence.

## Recommended First Implementation Slice

1. Add fresh-output cleanup to `scripts/run_official_local.sh`.
2. Copy `starter/agents/routed.py` into a new `agents/mantis.py` once starter files are copied into this repo.
3. Remove extra LLM calls so `mantis.py` has one decision call and deterministic evidence.
4. Add `metric_service.csv` summary to the candidate packet.
5. Run `LIMIT=10`, score, inspect failures.
6. Tune only the most common failure class.

## Success Definition

Good enough for this hackathon means:

- Valid official output shape.
- Better than heuristic baseline.
- Honest evidence for every answer.
- Clear cost/time comparison.
- A report that says what worked, what failed, and why.

