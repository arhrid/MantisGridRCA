# MantisGrid Hackathon Track 1: Root Cause Analysis POR

## Purpose

This document captures the current Plan of Record (POR) for MantisGrid Hackathon Track 1: Root Cause Analysis. It separates confirmed hackathon facts from proposed implementation choices so the plan can evolve cleanly as final event instructions, API details, datasets, and judging criteria become available.

The working objective is to build a focused, accurate, and efficient RCA system that investigates real cluster incidents using telemetry evidence and produces a root-cause hypothesis with supporting evidence.

## Confirmed Hackathon Facts

Based on the MantisGrid event materials and discussion so far:

- Track 1 is Infrastructure Root Cause Analysis.
- Participants receive 12 GB of real telemetry.
- The telemetry includes metrics, traces, and logs.
- Participants receive 70 cases with answers included.
- The challenge is to build an accurate and efficient agent that finds the root cause of real failures.
- The event provides labeled answers for evaluation.
- The slide describes a starter pack that already runs end to end.
- The slide describes 7 GLM models available through a provided Featherless key.
- No model training is needed.
- The track is aligned with agent frameworks, evaluation, and distributed-system debugging.
- Published-agent baseline context: the best published agent referenced on the slide solves 18 of 70 cases.

## Additional Working Information

Based on discussion so far:

- MantisGrid APIs are expected to be available for accessing hackathon data or insights.
- MCP support may be available or required, but the current plan is to run the project locally without Docker.
- The MCP server may be available as one interface to the data, but it does not need to be the default path if the MantisGrid APIs can be called directly.
- Direct API access should be the default design assumption; MCP should remain an optional adapter unless final instructions require it.
- The Track 1 screenshot emphasizes model routing and explainability. This should shape the implementation toward routed model selection, evidence discipline, and transparent reasoning traces.
- The slide states that the telemetry will not fit in model context and should be queried through tools rather than pasted into prompts.

These details should be confirmed against final event instructions, especially the exact API surface, authentication model, rate limits, and whether MCP is required, optional, or mainly provided as a convenience layer.

## Slide-Captured Requirements

The Track 1 challenge slide adds the following concrete deliverables and success signals:

- Create an agent that names the incident time, failed component, and cause.
- Provide evidence for every answer.
- Produce benchmarks comparing routed model use against a single-model baseline.
- Query telemetry instead of trying to fit raw telemetry into context.
- Use model routing where it saves tokens or improves investigation quality.
- Be honest about uncertainty; a reasoned negative result is better than a vague claim.
- Focus on routing and explainability.

## Product Signals From MantisGrid

MantisGrid's public website and blog framing are useful context for shaping the RCA solution, even though they are not hackathon-specific requirements.

Relevant signals:

- MantisGrid positions itself as an AI-native autonomous reliability platform for AI infrastructure and workloads across cloud, edge, GPUs, and accelerators.
- The product framing emphasizes uptime, performance, utilization, and cost efficiency.
- The platform is described as collecting logs, telemetry, and configuration data to build a real-time graph of infrastructure.
- MantisGrid emphasizes correlating signals across every layer of the stack to identify root causes that affect business goals.
- Public examples focus on GPU failures, orchestration issues, latency spikes, noisy alerts, configuration drift, driver instability, memory pressure, network bottlenecks, node degradation, and container runtime anomalies.
- The company repeatedly distinguishes true root-cause analysis from dashboards, alert summaries, and simple log summarization.

Design implications:

- The system should feel like a distributed-systems investigator, not a log summarizer.
- The RCA loop should correlate metrics, logs, traces, cluster state, workload context, resource health, and dependency context.
- The internal data model should preserve a lightweight reliability graph mindset: clusters, nodes, workloads, services, jobs, GPUs or accelerators, incidents, metrics, logs, traces, and dependency edges where available.
- Final answers should distinguish observed symptoms from the likely root cause.
- Evaluation should track correctness and investigation efficiency, reflecting the product emphasis on MTTR reduction.
- Recommendations should be concrete and operational, even if automated remediation is outside the initial build.

Useful public references:

- https://mantisgrid.ai/
- https://mantisgrid.ai/blog/aws
- https://mantisgrid.ai/blog/ai-sre-sunglasses
- https://mantisgrid.ai/blog/k8s-reliability-for-ai
- https://www.mantisgrid.ai/blog/DesignpartnershipRockfishdata

## Core Thesis

Track 1 is primarily an agent-plus-tools-plus-evaluation problem rather than a UI, model-training, or infrastructure-deployment problem.

The strongest solution shape is:

**Incident -> affected entities -> dependency context -> constrained telemetry tools -> routed hypothesis loop -> evidence-backed RCA -> evaluation**

The infrastructure should stay simple and local:

**Mac laptop -> local Python RCA backend -> direct MantisGrid APIs and/or local telemetry cache -> Streamlit browser UI**

with optional cloud LLM inference through a provider-independent interface.

## Architecture Summary

```text
Mac laptop host
  |
  +-- Local Python runtime
        |
        +-- Python RCA backend / orchestrator
        |     |
        |     +-- RCA workflow state machine
        |     +-- Provider-independent LLM interface
        |     +-- Tool dispatcher and validators
        |     +-- Direct MantisGrid API client
        |     +-- Optional MCP adapter
        |
        +-- Local telemetry storage / cache
        |     |
        |     +-- DuckDB or Polars
        |     +-- Cached or materialized metrics/logs/traces/incidents
        |
        +-- Streamlit localhost UI
        |
        +-- Evaluation harness
              |
              +-- Gold incident set
              +-- Accuracy and efficiency scoring
```

Important boundary:

**The cloud LLM should not directly call MantisGrid APIs or telemetry tools.** The local Python backend should call the APIs directly on the host, optionally through MCP if useful or required, then pass only bounded prompts, tool results, and summarized evidence to the LLM.

## Terminology: Agent vs. LLM

When this document says "agent" or "local agent," it means a software orchestration construct running in the local Python runtime. It is not assumed to be a local LLM.

The local Python RCA backend is the orchestrator. It owns:

- Control flow.
- Tool selection and execution.
- API calls.
- State management.
- Evidence shaping.
- Evaluation logging.
- UI-facing investigation traces.

The LLM is the reasoning engine. It can be a cloud LLM called through a provider-independent interface. A local model remains a possible future option, but it is not part of the initial POR.

## Runtime Environment

### Host

Use the Mac laptop as the primary host.

Rationale:

- The event appears designed for laptop-based participation.
- The datasets and/or API access can be handled locally.
- No model training is required.
- Local execution reduces setup risk during the hackathon.
- The system remains demoable without cloud deployment.

### Runtime

Use a local Python runtime for the hackathon. Add Docker packaging only if later event instructions require it.

Rationale:

- Keeps setup reproducible.
- Avoids dependency drift across machines.
- Makes the system easier to hand off, demo, or rerun.
- Provides enough isolation without introducing Kubernetes or cloud deployment complexity.

### Implementation Language

Use Python.

Rationale:

- Strong fit for telemetry analysis, data processing, LLM orchestration, and quick UI work.
- Good support for DuckDB, Polars, Pandas, OpenTelemetry-related data formats, Streamlit, and evaluation scripts.
- Faster iteration during a short hackathon than a native app or heavier service stack.

## Data and API Layer

Use direct MantisGrid API access as the default data path. Treat MCP as an optional adapter unless final instructions require it.

Use local storage and query through DuckDB or Polars where useful:

- DuckDB if the data is tabular, query-heavy, or naturally represented as Parquet/CSV tables.
- Polars if the fastest path is dataframe-first exploration and transformation.
- Both can coexist if useful, but the POR should start simple.

Expected data objects:

- Incident definitions.
- Gold labels or expected root causes.
- Metrics.
- Logs.
- Traces.
- Cluster, node, service, pod, workload, job, GPU, accelerator, or resource metadata if provided.
- Topology, dependency, configuration, deployment, scheduling, or change data if exposed.

The ingestion path should support:

- Static files available to the local Python runtime.
- API-backed retrieval through a direct Python API client.
- Optional API-backed retrieval through MCP if that interface is useful or required.

The local layer can act as a cache, index, or materialized query layer so repeated evaluation runs are faster and more reproducible.

## LLM Strategy

Use a provider-independent LLM abstraction. The LLM is a reasoning dependency behind the local Python RCA backend; it is not the same thing as the agent.

Initial mode:

- Cloud LLM API for inference.

Design requirements:

- The rest of the system should not depend directly on one provider's SDK or response format.
- The cloud LLM should receive only the minimum context needed to reason.
- API credentials and unrestricted telemetry access should stay inside the local Python runtime.

Rationale:

- Cloud inference is the fastest path to strong reasoning quality.
- Provider independence preserves the ability to switch models or run a local model later.
- Local compute and data remain the default; only inference is cloud-optional.

## LLM-Stepped RCA Workflow

The RCA process should not be implemented as a one-shot prompt. It should be a stateful workflow controlled by the Python RCA backend.

The Python backend steps the LLM through the RCA process with narrow prompts, captures the structured output from each step, updates canonical investigation state, and funnels the relevant state into the next step.

The intended loop is:

```text
Incident context
  |
  +-- Step 1: Incident intake prompt
  |       -> summarize incident, affected entities, initial symptoms
  |
  +-- Step 2: Routed hypothesis generation prompt
  |       -> candidate root causes, expected confirming/refuting evidence
  |
  +-- Step 3: Tool planning prompt
  |       -> requested telemetry/API queries
  |
  +-- Python backend executes approved tools
  |       -> metrics, logs, traces, resource health, topology, changes
  |
  +-- Step 4: Routed evidence interpretation prompt
  |       -> evidence for/against each hypothesis
  |
  +-- Step 5: Hypothesis update prompt
  |       -> ranked candidates, confidence, continue/stop decision
  |
  +-- Repeat planning/execution/evidence/update loop within budget
  |
  +-- Step 6: Final RCA prompt
          -> root cause, evidence chain, confidence, blast radius, next action
```

The Python backend owns:

- Workflow step selection.
- Model routing decisions.
- Prompt construction.
- Structured output validation.
- Tool execution.
- Tool result summarization.
- Round, tool-call, latency, and token budgets.
- Investigation trace logging.
- Final answer persistence.

The LLM contributes:

- Incident interpretation.
- Hypothesis generation.
- Next-evidence recommendations.
- Evidence interpretation.
- Confidence updates.
- Final root-cause explanation.

## Model Routing and Benchmarking

The slide explicitly asks for benchmarks comparing routed model use against a single-model baseline. Treat routing as part of the core system design, not only a cost optimization.

Initial routing strategy:

- Use cheaper or faster models for intake, summarization, and broad hypothesis generation.
- Use stronger models for final evidence synthesis, difficult hypothesis arbitration, and low-confidence cases.
- Keep a single-model baseline configuration that can run the same incidents for comparison.
- Record per-step model choice, latency, token usage, tool-call count, and final score in the trace.
- Evaluate whether routing improves cost, latency, or accuracy without reducing explainability.

The provided Featherless key and 7 GLM models should be treated as the first expected model pool, subject to final event credentials and SDK details.

## Investigation State

The backend should maintain a compact canonical state object for each incident session.

Example state fields:

- `incident_id`
- `incident_window`
- `affected_entities`
- `observed_symptoms`
- `candidate_root_causes`
- `evidence_for`
- `evidence_against`
- `tools_called`
- `next_queries`
- `remaining_questions`
- `confidence`
- `stop_or_continue`
- `stop_reason`

The working state should preserve:

- Observed symptoms.
- Affected entities.
- Candidate root causes.
- Evidence supporting each candidate.
- Evidence against each candidate.
- Remaining questions.
- Confidence level.

This matters because the solution should explain not only what changed, but why one signal is likely causal while another is likely downstream.

## Detailed Trace Logging

The Python RCA backend should log every meaningful step of the investigation. Detailed traces are required for debugging, eval tuning, failure analysis, reproducibility, and judge-facing explainability.

Each incident run should produce a complete trace artifact.

Trace goals:

- Reconstruct exactly what happened during an RCA run.
- Compare different configs or prompt versions.
- Identify where a miss occurred.
- Support failure-mode classification.
- Show judges the evidence chain behind an answer.
- Measure efficiency, latency, tool usage, and token usage.
- Preserve enough detail to improve prompts, tools, summaries, and stopping criteria.

Each trace should include:

- Run ID.
- Incident ID.
- Config ID and config values.
- Model/provider information.
- Prompt template names or hashes.
- Workflow step names.
- Prompt inputs or compact prompt payloads.
- Raw LLM outputs where appropriate.
- Parsed and validated structured LLM outputs.
- Tool-call requests proposed by the LLM.
- Tool-call validation decisions.
- Executed tool calls and arguments.
- Tool execution status, latency, and errors.
- Raw result references or evidence IDs.
- Backend-shaped tool summaries.
- Investigation state before and after each step.
- Candidate hypotheses per round.
- Evidence for and against each hypothesis.
- Stop/continue decisions and stop reason.
- Final RCA answer.
- Gold answer, when running in evaluation mode.
- Score, failure mode, and evaluator notes.

Trace format:

- Use structured JSON or JSONL for machine-readable traces.
- Keep human-readable summaries for Streamlit display.
- Avoid logging secrets, raw credentials, or unrestricted telemetry dumps.
- Store references or compact excerpts for large raw results.

Suggested trace file shape:

```json
{
  "run_id": "baseline_20260916_103000",
  "incident_id": "incident_001",
  "config_id": "baseline.yaml",
  "model": "provider/model-name",
  "steps": [
    {
      "step": "incident_intake",
      "prompt_template": "incident_intake_v1",
      "input_state": {},
      "llm_output": {},
      "parsed_output": {},
      "state_after": {}
    },
    {
      "step": "tool_execution",
      "requested_tool": "query_metrics",
      "validated": true,
      "arguments": {},
      "latency_ms": 842,
      "result_summary": {},
      "evidence_ids": []
    }
  ],
  "final_answer": {},
  "eval": {
    "gold_answer": {},
    "score": null,
    "failure_mode": null
  }
}
```

The trace log should be treated as a first-class output of the RCA loop, not a debug afterthought.

## Root-Cause Taxonomy

Prepare for likely root-cause categories suggested by MantisGrid's public positioning and the Track 1 challenge:

- GPU or accelerator fault.
- GPU driver or hardware instability.
- Node degradation.
- Memory pressure.
- Network bottleneck or latency spike.
- Container runtime anomaly.
- Kubernetes scheduling or orchestration issue.
- Configuration drift.
- Dependency cascade.
- Training job or inference workload failure.
- Resource saturation or over-provisioning.

The taxonomy should guide hypothesis generation, tool choice, and final answer normalization without forcing the model into a category when evidence does not support it.

## Practical Tool-Calling Model

For a cloud LLM session, the cloud LLM does not directly interact with telemetry tools or MantisGrid APIs.

The tool model is:

**LLM suggests. Python backend validates and executes.**

Practical loop:

```text
1. Python backend sends current investigation state to the cloud LLM.

2. LLM returns a structured proposed tool call.

3. Python backend validates the tool call:
   - allowed tool name
   - valid argument schema
   - bounded time range
   - incident-scoped entity access
   - budget limits
   - result-size limits

4. Python backend executes the tool:
   - direct MantisGrid API call, or
   - local DuckDB / Polars query, or
   - optional MCP call if useful

5. Python backend receives raw result.

6. Python backend shapes and summarizes result.

7. Python backend appends the result summary to investigation state.

8. Python backend sends the updated state to the next LLM step.
```

Example LLM-proposed tool request:

```json
{
  "action": "call_tool",
  "tool_name": "query_metrics",
  "arguments": {
    "entity_id": "node-17",
    "metric": "gpu_memory_errors",
    "start": "2026-09-16T10:00:00Z",
    "end": "2026-09-16T10:30:00Z"
  },
  "reason": "Check whether the affected node shows GPU memory errors during the incident window."
}
```

Example backend-shaped tool result:

```json
{
  "tool_name": "query_metrics",
  "summary": "node-17 shows a sharp spike in GPU memory errors during the incident window, while peer nodes remain flat.",
  "time_window": "2026-09-16T10:00:00Z/2026-09-16T10:30:00Z",
  "evidence_ids": ["metric:gpu_memory_errors:node-17:10_00_10_30"],
  "key_observations": [
    "Affected node error rate increased 9x over baseline.",
    "Peer nodes did not show the same error pattern.",
    "Spike begins 4 minutes before workload failure."
  ]
}
```

Implementation layers:

```text
LLM-facing tool schema
  |
  +-- Python tool dispatcher
        |
        +-- Tool implementation backend
              |
              +-- MantisGrid API
              +-- DuckDB / Polars local cache
              +-- Optional MCP adapter
```

This design keeps the important control points local:

- API credentials stay inside the local Python runtime.
- The LLM never receives unrestricted API access.
- The backend can reject invalid or overly broad tool calls.
- The backend can cap time windows, call counts, latency, token usage, and result size.
- Tool results can be cached for repeatable evaluation.
- Every tool call and result summary can be logged for scoring and debugging.
- Direct API, local cache, or MCP implementations can be swapped behind the same tool schema.

Initial preference: use a provider-independent manual JSON tool loop unless provider-native tool calling becomes materially easier or more reliable. This keeps the RCA harness portable and easier to debug during the hackathon.

## Constrained Telemetry Tools

Expose a small set of controlled tools to the LLM-facing workflow. The tools should return structured, bounded results rather than dumping raw telemetry into the prompt.

Initial tool set:

- `list_incidents`: list available incidents and labels, depending on evaluation mode.
- `get_incident`: fetch metadata for one incident.
- `get_affected_entities`: identify the initial cluster, workload, service, node, pod, job, or GPU entities tied to an incident.
- `get_dependency_context`: retrieve upstream, downstream, peer, or placement relationships for affected entities when available.
- `cluster_summary`: summarize the affected cluster around the incident window.
- `query_metrics`: retrieve metrics over a bounded time window and dimension set.
- `search_logs`: search logs by time range, service, node, severity, keyword, or pattern.
- `get_traces`: retrieve traces or trace summaries for affected services/time windows.
- `compare_nodes`: compare nodes, pods, services, or workloads against peers or baseline.
- `compare_peer_entities`: compare an affected entity against peer nodes, pods, workloads, services, jobs, or accelerators.
- `get_resource_health`: retrieve resource-level health signals, especially node, GPU, accelerator, memory, network, storage, or runtime health where available.
- `get_recent_changes`: retrieve recent configuration, deployment, scheduling, or topology changes if the dataset/API exposes them.

Tool constraints:

- Require incident-scoped or time-bounded queries.
- Limit result size.
- Validate entity IDs, metric names, time ranges, and query scope.
- Return structured summaries with links or IDs back to raw records when possible.
- Track tool-call count, latency, result size, and token footprint for evaluation.

## Cloud vs. Local Boundary

Keep data and compute local by default:

- Telemetry data or cached telemetry views stay on the laptop.
- Query execution and API access run inside the local Python runtime.
- UI runs locally.
- Evaluation runs locally.

Use cloud services only where they materially help:

- LLM inference can initially use a cloud API.
- Provider choice should remain replaceable.
- The system should degrade gracefully if cloud inference changes or is unavailable.

The cloud LLM should receive only the minimum context needed to reason:

- Incident metadata.
- Current investigation state.
- Tool result summaries.
- Small supporting excerpts.
- Structured evidence tables or aggregates.

The cloud LLM should not receive unrestricted raw telemetry dumps, API credentials, or direct network access to MantisGrid services.

## User Interface

Use Streamlit running on localhost in the browser.

The UI should support:

- Selecting an incident.
- Running the RCA workflow.
- Viewing the investigation trace.
- Inspecting tool calls and returned evidence summaries.
- Viewing candidate hypotheses and confidence over time.
- Viewing the final root-cause hypothesis.
- Comparing the prediction to the known answer in evaluation mode.
- Running a batch evaluation against gold incidents.

Preferred answer display:

- Root cause.
- Primary evidence.
- Secondary evidence.
- Affected entities and blast radius.
- Why this is likely the cause rather than a symptom.
- Ruled-out alternatives.
- Confidence.
- Recommended next action.

Rationale:

- Streamlit is fast enough for a hackathon demo.
- Browser UI avoids native Mac app complexity.
- The UI can remain thin while the RCA workflow and evaluation harness carry the core value.

## Evaluation Harness

Build evaluation as a first-class component, not an afterthought.

The harness should run the RCA workflow against gold incidents and record:

- Predicted root cause.
- Expected root cause.
- Match score or classification result.
- Supporting evidence returned.
- Number of tool calls.
- Runtime per incident.
- Time to first plausible root-cause hypothesis.
- Number of hypotheses considered.
- Whether the final answer distinguishes root cause from symptoms.
- Whether the answer includes an operational next action.
- Token usage, if available.
- Failure mode notes.

Primary evaluation goals:

- Accuracy: did the system identify the correct root cause?
- Efficiency: how many calls, how much time, and how much inference did it need?
- Explainability: did the answer include evidence that a human judge can inspect?
- Operational usefulness: did the answer help reduce MTTR by pointing to the affected entity, causal mechanism, blast radius, and next action?
- Routing value: did routed model selection improve accuracy, latency, cost, or token usage relative to a single-model baseline?
- Honesty under uncertainty: did the system clearly explain when evidence was insufficient instead of making a vague unsupported claim?

Evaluation artifacts to persist:

- Prompt templates or prompt hashes.
- Model/provider configuration.
- Tool calls and validated arguments.
- Tool result summaries.
- Intermediate hypotheses.
- Detailed per-incident trace logs.
- Final answer.
- Gold answer.
- Scores.
- Latency, token usage, and tool-call counts.

## Using Eval Data To Tune The RCA Loop

The provided eval data should be treated as the main feedback mechanism for improving the RCA system. This is not model fine-tuning. It is RCA harness tuning: prompts, tool policy, workflow steps, budgets, state updates, result summaries, scoring, and final answer normalization.

Likely judging model:

- Public or sample gold incidents are available during development.
- A private or held-out set is used during judging.
- The system should generalize to the private set rather than overfitting to known public incidents.

Core development loop:

```text
Run RCA workflow on gold incidents
  |
  +-- Save full traces
  |
  +-- Score final answers against gold labels
  |
  +-- Inspect misses and categorize failure modes
  |
  +-- Adjust prompts, tools, budgets, summaries, or schemas
  |
  +-- Re-run the eval set
  |
  +-- Keep changes that improve accuracy, evidence quality, or efficiency
```

Each eval case should be treated as a test case:

```text
incident_id
input metadata
telemetry/API access
expected root cause
expected category, entity, or evidence if provided
```

The RCA workflow should produce comparable fields:

```text
predicted root cause
predicted category
predicted affected entity
causal mechanism
evidence chain
confidence
tool calls
runtime
token usage
```

Important rule:

**The LLM should never see the gold answer during an RCA run.** Gold labels are used only afterward by the evaluation harness for scoring and analysis.

Recommended configurable knobs:

- `model`
- `temperature`
- `max_rounds`
- `max_tool_calls`
- `initial_strategy`
- `confidence_threshold`
- `hypothesis_count`
- `evidence_summary_size`
- `allowed_tools`
- `final_answer_schema`
- `stop_policy`

Useful experiment variants:

- Baseline workflow.
- Topology-first workflow.
- Metrics-first workflow.
- Logs-first workflow.
- More investigation rounds.
- Stricter root-cause taxonomy.
- Required peer comparison before final answer.
- Required final self-check before submission.
- Different evidence summary sizes.

Failure modes to track:

- `missed_entity`: picked the wrong node, workload, service, job, or resource.
- `symptom_as_cause`: reported a symptom instead of the underlying cause.
- `missing_tool`: failed because a key telemetry source was never queried.
- `bad_summary`: tool result summary hid or distorted the key clue.
- `stopped_early`: stopped before enough evidence was collected.
- `overexplored`: used too many calls, too much time, or too many tokens.
- `format_mismatch`: answer may be right but does not match the expected scoring format.
- `taxonomy_gap`: gold root cause does not fit the current taxonomy.
- `weak_evidence`: final answer has insufficient supporting evidence.

Suggested run artifact layout:

```text
configs/
  baseline.yaml
  topology_first.yaml
  metrics_first.yaml
  strict_taxonomy.yaml

runs/
  baseline_YYYYMMDD_HHMMSS/
    config.yaml
    summary.csv
    incident_001_trace.json
    incident_002_trace.json
    ...
```

The hackathon workflow should prioritize getting this loop running early:

1. Load incidents.
2. Run one incident end-to-end.
3. Save the trace.
4. Score the result.
5. Batch-run all public eval incidents.
6. Inspect failures.
7. Tune prompts, tool policies, budgets, and schemas.
8. Re-run and compare.

The final system should support a single-command or single-button evaluation run, for example:

```text
python -m rca_agent.eval.run --config configs/best.yaml
```

or a Streamlit "Run Evaluation" action.

Success criteria during tuning:

- Improve root-cause accuracy.
- Preserve or improve affected-entity accuracy.
- Improve evidence quality.
- Reduce symptom-as-cause failures.
- Keep tool calls and runtime within reasonable bounds.
- Avoid incident-specific hacks that would fail on private eval data.

### Practical Tuning Guidelines Under Time Pressure

During the hackathon, tuning should be failure-driven rather than random prompt tweaking.

For each failed or weak eval case, inspect:

- Gold answer.
- Our final answer.
- Intermediate hypotheses.
- Tool calls.
- Tool outputs and summaries.
- Stop reason.
- Confidence.
- Runtime, tool count, and token count.

Then ask:

- Did we look at the right entity?
- Did we ask the right telemetry question?
- Did we collect the right evidence?
- Did the tool summary preserve the important clue?
- Did the LLM interpret the evidence correctly?
- Did we stop too early?
- Did we produce an answer that is right but hard to score?

Use this failure-to-change mapping:

| Failure observed | Likely issue | What to change |
| --- | --- | --- |
| Model had the right evidence but chose the wrong cause | Reasoning prompt too weak | Update evidence interpretation or final RCA prompt |
| Model never collected the key evidence | Bad tool policy or initial strategy | Change tool order, require a tool, or add a conditional rule |
| Needed evidence cannot be retrieved | Missing tool capability | Add or expose a new tool |
| Raw data had the clue but summary hid it | Tool summarizer too lossy | Preserve exact codes, timestamps, entities, counts, and anomalies |
| Model forgot an important fact from earlier rounds | State schema too weak | Add explicit state fields |
| Model stopped with weak evidence | Stop policy too permissive | Require stronger evidence or more independent sources |
| Model used too many calls or too much time | Budget too loose or query policy too broad | Tighten budgets, query scope, or stopping rules |
| Answer seems right but scores poorly | Final schema or normalizer mismatch | Tighten final answer schema or add synonym/category mapping |
| Model reports a symptom as the cause | Cause-vs-symptom reasoning weak | Strengthen prompts and require temporal/locality evidence |

Smallest-change rule:

Make the smallest targeted change that explains the failure. Then rerun the full eval set, not just the incident that failed.

Examples:

- Bad reasoning -> adjust prompt.
- Missing evidence -> adjust tool strategy.
- Missing capability -> add a tool.
- Hidden clue -> improve tool summary.
- Forgotten clue -> improve state schema.
- Premature answer -> adjust stopping rule.
- Good answer, bad score -> adjust final schema or normalizer.

Example failure: missed GPU driver instability.

```text
Gold: node-17 GPU driver instability caused job failures.
Our answer: workload crash loop due to application errors.
Trace: searched workload logs repeatedly; never checked node/GPU health.
Failure mode: missing_tool / bad_initial_strategy.
Change: require get_resource_health for affected GPU workloads.
Validation: rerun all eval incidents and check aggregate score, not only this case.
```

Example failure: symptom reported as cause.

```text
Gold: network bottleneck on node pool caused downstream latency.
Our answer: service latency spike.
Trace: network retransmits and peer comparison were present, but final answer chose the downstream symptom.
Failure mode: symptom_as_cause / weak evidence interpretation.
Change: update evidence interpretation prompt to prefer causes that precede symptoms in time and localized infrastructure anomalies over widespread downstream errors.
Validation: rerun all eval incidents and check that the change does not over-bias toward infrastructure causes.
```

Maintain a tuning table:

```text
incident_id
gold_category
predicted_category
gold_entity
predicted_entity
score
failure_mode
suspected_loop_issue
change_to_try
result_after_change
```

The tuning table is the hackathon control panel. It keeps iteration grounded in observed failures and helps avoid overfitting to one dramatic incident.

## Explicit Non-Goals for the Initial Build

Do not start with:

- A native Mac application.
- A cloud-hosted production deployment.
- Kubernetes deployment.
- A complex distributed backend.
- Model training or fine-tuning.
- A broad general-purpose agent framework unless the dataset forces it.
- A polished enterprise dashboard as the primary deliverable.
- Automated remediation.

Rationale:

- These options add setup and demo risk without directly improving the core Track 1 scoring problem.
- The hackathon value is in the RCA reasoning loop, tool design, and evaluation quality.

## Extension Path to Track 2

The Track 1 architecture should preserve a path toward Track 2: Cluster Efficiency.

Shared foundations:

- Direct MantisGrid API client.
- Optional MCP adapter.
- Local telemetry ingestion and caching.
- DuckDB or Polars query layer.
- Cluster summary utilities.
- Metrics aggregation.
- Streamlit UI shell.
- Evidence views and dashboard components.

Possible Track 2 extensions:

- Add cost, performance, and uptime views.
- Build cluster behavior dashboards.
- Surface inefficiencies across nodes, services, or workloads.
- Translate telemetry findings into business impact.
- Reuse the RCA tool layer as an insight layer for dashboard explanations.

The Track 1 build should avoid choices that make Track 2 harder, but Track 2 should not dilute the initial RCA focus.

## Suggested Repository Shape

```text
mantisgrid-rca/
  README.md
  data/
    raw/
    processed/
  src/
    app.py
    rca_agent/
      loop.py
      llm.py
      mantisgrid_client.py
      prompts.py
      tools.py
      telemetry_store.py
      schemas.py
      state.py
      trace.py
    eval/
      run_eval.py
      scoring.py
      reports.py
  notebooks/
  tests/
```

This is a proposed shape only. The actual structure should adapt once the provided dataset format and API surface are known.

## Open Questions

- What exact file formats will MantisGrid provide for metrics, logs, traces, incidents, and labels?
- What MantisGrid API endpoints and objects are available?
- Are APIs the primary telemetry access path, or are static files also provided?
- Is MCP required, optional, or mainly a convenience layer?
- What MCP transport is used: stdio, HTTP, SSE, or another mechanism?
- How should API credentials be supplied to the local runtime?
- Are there API rate limits or query budgets that should be included in the efficiency score?
- Are incident labels visible during development, hidden during scoring, or split into train/test sets?
- What is the expected answer format for root cause?
- Will judging prioritize exact root-cause classification, natural-language explanation, evidence quality, latency, cost, or a combination?
- Are external LLM APIs allowed during judging?
- Are there limits on internet access, API keys, or cloud inference during the hackathon?
- Is the 12 GB telemetry delivered as one archive, multiple files, or API-backed records?
- Are traces OpenTelemetry-compatible or in a custom format?
- Is topology, dependency, configuration, deployment, or scheduling-change data available?

## Near-Term Build Sequence

1. Confirm dataset format, API surface, authentication model, rate limits, and evaluation rules.
2. Create the local Python project skeleton.
3. Build the direct MantisGrid API client.
4. Implement optional MCP adapter only if required or clearly useful.
5. Load or cache incidents and telemetry into DuckDB or Polars where useful.
6. Define the investigation state schema and trace logging format.
7. Build read-only telemetry tools over direct APIs and/or local cache.
8. Implement the LLM-stepped RCA workflow.
9. Add provider-independent LLM calls using manual JSON tool requests initially.
10. Build a minimal Streamlit UI for single-incident investigation.
11. Add batch evaluation against gold incidents.
12. Iterate on prompts, tool summaries, budgets, caching, and stopping criteria.
13. Preserve reusable telemetry and dashboard components for Track 2.

## Current Decision

The Plan of Record is to build a local Python RCA system with a Streamlit UI, direct API-backed telemetry access, optional MCP support, optional local caching and querying, constrained telemetry tools, cloud LLM inference through a replaceable interface, an LLM-stepped RCA workflow, and a first-class evaluation harness.

This keeps the project centered on the Track 1 scoring problem: an accurate and efficient root-cause investigation system over real cluster telemetry.
