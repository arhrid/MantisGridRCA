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

Run three configurations. The point is not just to get a score; it is to understand what each layer is buying us.

#### Config A: `agents.heuristic`

Command:

```bash
LIMIT=10 AGENT=agents.heuristic scripts/run_official_local.sh
```

What it is:

- A no-LLM baseline.
- Reads only metrics.
- Uses robust z-scores to find the loudest anomalous component.
- Guesses the root-cause reason from KPI-name keywords.
- Costs $0 in model calls.

Why we run it:

- It tells us the minimum bar.
- If our LLM agent cannot beat this, our model calls are not adding value.
- It helps identify cases where simple metric spikes are enough.

Expected weakness:

- Often picks the loudest symptom, not the root cause.
- Does not inspect logs.
- Does not inspect traces.
- Weak for network faults and causality.

#### Config B: `agents.routed`

Command:

```bash
LIMIT=10 AGENT=agents.routed scripts/run_official_local.sh
```

What it is:

- The official starter's example LLM agent.
- Still starts from the heuristic candidate ranking.
- Uses a cheap GLM model for simple reading/formatting.
- Uses a stronger GLM model to choose from ranked candidates.
- Falls back if a model is busy or returns an invalid answer.

Why we run it:

- It proves Featherless, model routing, token accounting, and fallback behavior work.
- It is the official example of the required routed-vs-single-model idea.
- It gives us a comparison between "heuristic only" and "heuristic plus LLM choice."

Expected weakness:

- The candidate packet is still metric-heavy.
- It does not deeply use logs or traces.
- The LLM can only choose from candidates it is shown.
- If the heuristic ranking misses the true cause, the LLM may never see the right answer.

#### Config C: `agents.mantis`

Command:

```bash
LIMIT=10 AGENT=agents.mantis scripts/run_official_local.sh
```

What it is:

- Our planned simple real agent.
- Python first reduces telemetry into a compact evidence packet.
- The packet should include metric anomalies, service-level symptoms, and targeted log/trace signals where available.
- One LLM decision call chooses the answer from grounded candidates.
- Python validates and formats the final prediction.
- Evidence is written from deterministic data, not invented prose.

Why we run it:

- This tests our actual hypothesis: better telemetry summaries should beat the starter.
- It separates "better evidence" from "more model calls."
- It gives us the agent we can tune under time pressure.

Expected weakness:

- First version may still miss deep trace causality.
- It may be weak on multi-failure windows.
- It may need better candidate generation before prompt tuning helps.

#### Optional Config D: Single-Model Ablation

After `agents.mantis` exists, run it with routing disabled or pinned to one model.

Example shape:

```bash
LIMIT=10 RCA_MODEL=zai-org/GLM-5.2 AGENT=agents.mantis scripts/run_official_local.sh
```

Why we run it:

- The scoring docs expect a routed-vs-single-model comparison.
- This tells us whether routing actually saves money or time without hurting score.
- If routing does not help, that is still a valid finding for the report.

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

### 5. Automated Run -> Validate -> Tweak Loop

Use the same 10-case slice while tuning. Change one thing at a time.

Default loop:

1. Run `agents.mantis` with a unique `RUN_NAME` and `OUT`.
2. Validate mechanics:
   - `predictions.csv` exists.
   - Each row has a non-empty prediction.
   - Each row has an evidence file.
   - Prediction object count matches expected failure count.
   - Reasons are legal strings.
3. Score with the same evaluator logic as `starter/score.py`.
4. Classify every non-perfect case:
   - `candidate_missing`: expected component not visible in evidence.
   - `candidate_present_model_wrong`: expected component visible, model chose another.
   - `reason_wrong`: component is right, reason is wrong.
   - `time_wrong`: component/reason may be right, timestamp is wrong.
   - `count_or_format_wrong`: object count or prediction format broke scoring.
   - `model_failure`: fallback used because the model failed or key was missing.
   - `unknown`: needs manual inspection.
5. Pick exactly one tweak based on the largest failure class.
6. Rerun the same slice and compare score, time, and token/cost.
7. Keep the tweak only if it improves score or evidence quality without unacceptable cost/time.

Initial automation commands:

```bash
RUN_NAME=mantis-10-a LIMIT=10 AGENT=agents.mantis OUT=/tmp/rca-mantis-10-a scripts/run_official_local.sh
scripts/eval_track1.py --out /tmp/rca-mantis-10-a --queries /Users/benchong/Work/Hackathon/hackathon-2026-official/track-1/data/Market-cloudbed-1/dev/query_dev.csv
```

Tuning rules:

- If `candidate_missing` dominates, improve Python candidate generation.
- If `candidate_present_model_wrong` dominates, improve the compact decision prompt.
- If `reason_wrong` dominates, improve KPI/log/trace-to-reason hints.
- If `time_wrong` dominates, improve first-anomaly timestamp logic.
- If `model_failure` dominates, adjust model list, retry behavior, or fallback.
- If `count_or_format_wrong` appears, fix Python validation before any prompt work.

Do not run all 70 repeatedly until the 10-case loop shows improvement. Move to `LIMIT=20` after a useful gain on `LIMIT=10`.

Current observation after the first `mantis` loop:

- `agents.mantis` currently matches the heuristic score on the first 10 cases.
- The LLM is reachable when the run has network access, but model choice alone did not improve the first two cases.
- The useful immediate signal is failure classification:
  - `candidate_present_model_wrong` means the right answer is visible but not selected.
  - `time_wrong` means candidate choice may be acceptable but timestamp logic needs work.
- Prompt-only tuning reduced output tokens but did not fix row 0.

Next tuning step:

1. Treat model choice as an explicit knob.
   - Use `RCA_MODEL=zai-org/GLM-4.7-Flash` for a cheap single-model run.
   - Use `RCA_MODEL=zai-org/GLM-5.2` for a strong single-model run.
   - Compare score, wall-clock, prompt tokens, and completion tokens on the same `LIMIT=2` or `LIMIT=10` slice.
2. If model choice does not move score, stop spending time on model selection and improve evidence generation.
3. The likely evidence-generation improvement is targeted trace/service relationship summary, because metric-only evidence tends to pick loud symptoms rather than causal components.

## Tweak Log

Track every scoring/cost tweak here so we do not re-test the same idea without a new reason.

### Tweak 1: Local run wrapper and clean output

- Change: added `scripts/run_official_local.sh` to run the official starter locally, load `.env.local`, clean `OUT` by default, print predictions beside `scoring_points`, and print a score summary.
- Result: made fast local iteration possible without Docker.
- Keep: yes.
- Notes: every run clobbers `OUT` unless `CLEAN_OUT=0`.

### Tweak 2: Single-call `agents.mantis`

- Change: created `agents.mantis` as a small wrapper around the official heuristic candidate generation plus one bounded LLM decision call.
- Result: valid official output shape, deterministic evidence files, and no extra evidence-prose LLM call.
- Keep: yes.
- Notes: if the LLM is unavailable, it falls back to `agents.heuristic`.

### Tweak 3: Service-level symptom summary

- Change: added compact `metric_service.csv` summaries for latency ratio and success-rate drop.
- Result: useful context for matching symptomatic services to candidate pods.
- Keep: yes.
- Notes: this helps candidate selection, but service symptoms alone do not prove root cause.

### Tweak 4: Prompt tightening

- Change: instructed the LLM to pick only from shown candidates, use only legal reason strings, prefer root causes over downstream symptoms, and avoid choosing nodes only because aggregate TCP/network counters are large.
- Result: reduced sloppy output and token use, but did not fix row 0.
- Keep: yes.
- Notes: prompt-only changes are not enough if the evidence packet is weak.

### Tweak 5: Model knob

- Change: added `RCA_MODEL` and `MANTIS_MODELS` so we can compare Featherless models without code changes.
- Result: `RCA_MODEL=zai-org/GLM-4.7-Flash` on the first two cases produced the same score and failure classes as the stronger-model run, at lower expected cost.
- Keep: yes.
- Notes: model choice alone is not the main bottleneck so far.

### Tweak 6: Optional trace summary

- Change: added compact `trace_span.csv` p95/error summaries behind `MANTIS_TRACE_SUMMARY=1`.
- Result: first row-0 test did not improve the answer and added noticeable runtime/prompt overhead.
- Keep: behind flag only.
- Notes: use it selectively for network/latency-looking cases rather than the default run.

### Tweak 7: `reason_quality` and `evidence_score`

- Change: labelled candidates as direct KPI matches vs fallback reasons and adjusted ranking with service matches.
- Result: made candidate packets more honest but did not change first two answers.
- Keep: yes.
- Notes: helped expose that the model was seeing weak/ambiguous reason evidence.

### Tweak 8: Reason-evidence extractor

- Change: added candidate-level `reason_evidence` with one strongest KPI per legal reason family, source labels (`candidate_metric`, `host_node_metric`), and a weak `inferred_storage` hint for pod filesystem usage metrics.
- Result: local no-network smoke test passes. Evidence now surfaces `shippingservice-1` with `container read I/O load` support. LLM-backed `LIMIT=10` scored `0.200`, with `1 / 10` fully solved.
- Keep: yes, but it did not move the 10-case score by itself.
- Notes: this is the current active experiment. It is generic and does not hard-code a scenario answer.

### Tweak 9: Sliceable local runner

- Change: added `START_ROW` to `scripts/run_official_local.sh` so we can run holdout slices without editing official query files.
- Result: pending.
- Keep: yes.
- Notes: use `START_ROW=10 LIMIT=10` for rows 11-20 after a candidate-generation tweak.

### Tweak 10: Legal-signal candidate backfill

- Change: expanded `agents.mantis` candidate generation with a backfill pass over components that have strong KPI evidence for a legal reason class.
- Change: added node-specific shorthand mappings for `system.mem.*` and `system.io.*` metrics so node memory/disk candidates are not hidden by noisy pod/network symptoms.
- Result: local no-LLM smoke checks now put previously missing `node-1` in row 3 evidence and `node-2` in row 8 evidence.
- Keep: pending LLM-backed `LIMIT=10` validation.
- Notes: this is generic candidate coverage logic; it does not key off row ids, expected answers, or scenario labels.

### Tweak 11: Dataset timezone fix

- Change: parse instruction windows as UTC+8, matching the dataset/scoring convention, and format occurrence times back in UTC+8.
- Result: rows after 16:00 local time no longer fail with `No samples inside the window`; row 12 smoke test now produces a real prediction.
- Keep: yes.
- Notes: this changes all time windows, so rerun rows 1-10 and rows 11-20 before comparing further prompt/model tweaks.

### Current Read

- `mantis-reason-10` on rows 1-10 scored `0.200`, `1 / 10` fully solved, `234.6s` total runtime, `67,169` prompt tokens, and `5,000` completion tokens.
- `mantis-backfill-10` on rows 1-10 also scored `0.200`, but moved `candidate_missing` from `4` to `0`, so true components are now visible and the remaining issue is mostly choice/ranking.
- The rows 11-20 holdout initially scored `0.000`, but rows 12-19 were invalid because the parser treated UTC+8 instruction times as UTC. Do not use that holdout score for model-quality conclusions.

Next execution target:

1. Rerun rows 1-10 to check whether `candidate_missing` drops after the legal-signal backfill.
2. Then run rows 11-20 as a holdout slice so we do not overfit the first 10 rows.
3. If candidate coverage improves but score does not, inspect whether the failure moved to `candidate_present_model_wrong`, `reason_wrong`, or `time_wrong`.

Current reason-evidence slice:

- Added candidate-level `reason_evidence` to `agents.mantis`.
- The extractor keeps one strongest KPI per legal reason family instead of letting repeated noisy network counters fill the evidence packet.
- Evidence is labelled by source:
  - `candidate_metric`: metric belongs directly to the candidate component.
  - `host_node_metric`: metric belongs to the node hosting a pod candidate, useful but weaker than direct candidate evidence.
- Added a weak `inferred_storage` hint for pod filesystem usage metrics such as `container_fs_usage_MB.*`, because this dataset may expose storage pressure without explicit container read/write byte counters.
- The prompt now tells the LLM to use `reason_evidence`, prefer direct candidate metrics over host-node support, and treat inferred storage as weaker than direct read/write counters.
- Local no-network smoke test passes and evidence now surfaces `shippingservice-1` with `container read I/O load` support, but the fallback prediction remains the old heuristic because the LLM call is unavailable in sandboxed local validation.

Next validation step:

```bash
LIMIT=10 RUN_NAME=mantis-reason-10 AGENT=agents.mantis RCA_MODEL=zai-org/GLM-4.7-Flash OUT=/tmp/rca-mantis-reason-10 scripts/run_official_local.sh
scripts/eval_track1.py --out /tmp/rca-mantis-reason-10 --queries /Users/benchong/Work/Hackathon/hackathon-2026-official/track-1/data/Market-cloudbed-1/dev/query_dev.csv
```

Holdout command after the next candidate-generation tweak:

```bash
START_ROW=10 LIMIT=10 RUN_NAME=mantis-holdout-11-20 AGENT=agents.mantis RCA_MODEL=zai-org/GLM-4.7-Flash OUT=/tmp/rca-mantis-holdout-11-20 scripts/run_official_local.sh
scripts/eval_track1.py --out /tmp/rca-mantis-holdout-11-20 --queries /tmp/rca-mantis-holdout-11-20/queries.csv
```

This sends bounded telemetry-derived summaries to Featherless. Get team approval for that data flow before using it in the judged workflow.

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
