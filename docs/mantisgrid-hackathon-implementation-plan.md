# MantisGrid Hackathon Implementation Plan

## Purpose

This is the living implementation plan for the MantisGrid hackathon work. Codex should update this document at the end of each phase to capture status, validation, risks, and changes to the Plan of Record.

This document is intentionally operational. The Track 1 and Track 2 POR docs explain the strategy.

## Current Status

Status: planning.

No implementation has started yet.

Current docs:

- `mantisgrid-track1-rca-por.md`
- `mantisgrid-track2-cluster-efficiency-por.md`
- `mantisgrid-codex-hackathon-guidelines.md`
- `mantisgrid-hackathon-implementation-plan.md`

Important:

At the start of the hackathon, Codex should ask the humans for the latest event updates before beginning implementation. New official details may override assumptions captured in the POR docs and this implementation plan.

## Working Agreements

- Work one phase at a time.
- Keep each phase small enough for human review.
- Prefer working vertical slices over broad scaffolding.
- Update this plan after each phase.
- Do not commit or push unless explicitly asked.
- At phase boundaries, provide validation results, known risks, and suggested commit message.

## Phase Status Legend

- `not_started`
- `in_progress`
- `blocked`
- `ready_for_review`
- `complete`

## Shared Foundation Phases

### Phase S0: Confirm Inputs and Environment

Status: `not_started`

Objective:

Confirm hackathon-provided updates, assets, API instructions, credentials, local runtime requirements, judging criteria, eval data, and whether MCP is required or optional.

Deliverables:

- Captured start-of-hackathon update notes.
- Inventory of available datasets, APIs, docs, and sample eval data.
- Confirmed local setup requirements.
- List of assumptions that changed from the POR docs.
- Updated open questions in Track 1 and Track 2 POR docs.

Acceptance criteria:

- Humans have provided latest event instructions or confirmed there are none.
- We know how data will be accessed.
- We know whether direct API access is possible.
- We know whether MCP is required.
- We know whether external LLM APIs are allowed.
- We know whether judging criteria or deliverables changed.

Validation:

- Human confirms event instructions.
- Basic API or dataset access is verified if available.
- POR docs and this implementation plan are updated for any changed assumptions.

Human review checkpoint:

- Decide Track 1, Track 2, or both for first implementation slice.

### Phase S1: Project Skeleton and Local Runtime

Status: `not_started`

Objective:

Create a reproducible local Python project skeleton with dependencies, config handling, and a simple smoke test. Do not start with Docker unless later hackathon instructions require it.

Deliverables:

- Python package structure
- Dependency file
- Config directory
- Simple smoke test
- Optional Docker packaging note only if required later

Acceptance criteria:

- Local environment installs successfully.
- Basic command runs on the host.
- Project has clear entry points for Track 1 and/or Track 2.

Validation:

- Install local dependencies.
- Run smoke command.

Suggested commit message:

`Shared: add local Python project skeleton`

## Track 1 Phases: Root Cause Analysis

### Phase T1-1: Data/API Client and Incident Loader

Status: `not_started`

Objective:

Build the first usable data access layer for Track 1.

Deliverables:

- Direct MantisGrid API client or file-backed stub.
- Incident loader.
- Typed data objects or schemas for incidents.
- Optional local cache setup.

Acceptance criteria:

- Can list incidents.
- Can load one incident by ID.
- Can retrieve enough metadata to start RCA.

Validation:

- Run command to list incidents.
- Run command to load one incident and print normalized metadata.

Suggested commit message:

`Track 1: add incident loader and data client`

### Phase T1-2: RCA State and Trace Logging

Status: `not_started`

Objective:

Create canonical RCA state and detailed trace logging before adding complex LLM behavior.

Deliverables:

- RCA state schema.
- Trace event schema.
- JSON/JSONL trace writer.
- Run ID and incident ID tracking.

Acceptance criteria:

- A dummy RCA run produces a valid trace.
- Trace captures steps, state snapshots, and placeholder decisions.

Validation:

- Run dummy workflow.
- Inspect trace file.

Suggested commit message:

`Track 1: add RCA state and trace logging`

### Phase T1-3: Telemetry Tool Interface

Status: `not_started`

Objective:

Implement constrained telemetry tools behind validated Python interfaces.

Initial tools:

- `get_incident`
- `get_affected_entities`
- `cluster_summary`
- `query_metrics`
- `search_logs`
- `get_traces`
- `compare_peer_entities`
- `get_resource_health`

Deliverables:

- Tool schemas.
- Tool dispatcher.
- Argument validation.
- Stub or real implementations.
- Tool result summaries.

Acceptance criteria:

- Tools can be called from Python.
- Invalid tool calls are rejected.
- Tool results are summarized and trace logged.

Validation:

- Unit or smoke tests for valid/invalid tool calls.

Suggested commit message:

`Track 1: add constrained telemetry tool interface`

### Phase T1-4: LLM-Stepped RCA Workflow Skeleton

Status: `not_started`

Objective:

Implement the stateful RCA loop with structured LLM steps, initially using a mock LLM if needed.

Deliverables:

- Prompt templates.
- LLM provider abstraction.
- Manual JSON tool request loop.
- Workflow steps for intake, hypothesis generation, tool planning, evidence interpretation, hypothesis update, and final answer.

Acceptance criteria:

- One incident can run through the full workflow.
- Tool requests are backend-validated.
- Final answer is structured.
- Full trace is produced.

Validation:

- Run one incident end-to-end.
- Inspect final answer and trace.

Suggested commit message:

`Track 1: add LLM-stepped RCA workflow skeleton`

### Phase T1-5: Eval Harness and Batch Runner

Status: `not_started`

Objective:

Add the evaluation loop so tuning can begin.

Deliverables:

- Gold label loader.
- Batch eval runner.
- Scoring module.
- Summary CSV or JSON.
- Failure-mode field.

Acceptance criteria:

- Can run all public eval incidents.
- Each run saves a trace.
- Aggregate score and per-incident result are produced.

Validation:

- Run batch eval on available sample incidents.
- Inspect summary output.

Suggested commit message:

`Track 1: add batch RCA eval harness`

### Phase T1-6: RCA Tuning Loop

Status: `not_started`

Objective:

Use eval data to improve the RCA loop.

Deliverables:

- Config files for experiment variants.
- Failure-mode tracking.
- Prompt/tool/budget tuning.
- Best-known config.

Acceptance criteria:

- At least one baseline run and one improved run are recorded.
- Changes are tied to observed failure modes.
- Tuning table or summary captures what changed and why.

Validation:

- Compare eval summaries before and after tuning.

Suggested commit message:

`Track 1: tune RCA workflow with eval data`

### Phase T1-7: Track 1 Streamlit UI

Status: `not_started`

Objective:

Build the human-facing Track 1 demo UI.

Deliverables:

- Incident selector.
- Run RCA action.
- Investigation trace view.
- Tool call/evidence view.
- Final answer view.
- Batch eval action if practical.

Acceptance criteria:

- Human can run one incident from the UI.
- Human can inspect evidence and final RCA.

Validation:

- Manual UI smoke test.

Suggested commit message:

`Track 1: add RCA Streamlit demo UI`

## Track 2 Phases: Cluster Efficiency

### Phase T2-1: Track 2 Data Model and Cache

Status: `not_started`

Objective:

Build the data layer for cluster efficiency analysis.

Deliverables:

- Direct MantisGrid API client reuse or extension.
- Local cache tables.
- Derived table definitions.
- Metric and entity catalogs.

Acceptance criteria:

- Can load representative cluster data.
- Can query derived metrics for nodes, workloads, costs, and utilization where available.

Validation:

- Run data load command.
- Print derived summary tables.

Suggested commit message:

`Track 2: add efficiency data model and cache`

### Phase T2-2: Deterministic Finding Engine

Status: `not_started`

Objective:

Generate named efficiency findings from deterministic rules.

Deliverables:

- Finding schema.
- Rules for initial utilization/cost findings.
- Evidence IDs.
- Recommendation templates.
- Finding trace records.

Acceptance criteria:

- System produces top findings from available data.
- Each finding has evidence, affected entities, impact, confidence, and recommendation.

Validation:

- Run findings command.
- Inspect finding JSON.

Suggested commit message:

`Track 2: add deterministic efficiency findings`

### Phase T2-3: Baseline Streamlit Dashboard

Status: `not_started`

Objective:

Build the static baseline dashboard.

Deliverables:

- Overview page.
- Utilization view.
- Performance view if data supports it.
- Reliability view if data supports it.
- Cost view if data supports it.
- Findings view.

Acceptance criteria:

- Dashboard shows top findings and key charts.
- User can drill from finding to evidence.

Validation:

- Manual UI smoke test.

Suggested commit message:

`Track 2: add baseline efficiency dashboard`

### Phase T2-4: Dynamic Dashboard Spec and Renderer

Status: `not_started`

Objective:

Implement structured dynamic dashboard specs and safe rendering.

Deliverables:

- `AnalysisIntent`
- `DataRequest`
- `ViewSpec`
- `DashboardSpec`
- spec validator
- supported view renderer
- safe rejection/fallback behavior

Acceptance criteria:

- A sample DashboardSpec renders a valid dashboard section.
- Invalid specs are rejected safely.

Validation:

- Test valid and invalid specs.
- Render sample bar chart/table/finding card.

Suggested commit message:

`Track 2: add dynamic dashboard spec renderer`

### Phase T2-5: LLM-Guided Dynamic Workspace

Status: `not_started`

Objective:

Allow a user question to become a validated dashboard spec.

Deliverables:

- Prompt for dynamic dashboard specs.
- LLM provider integration or mock.
- Validation loop.
- Streamlit input and rendered dynamic views.
- Trace logs for dynamic requests.

Acceptance criteria:

- User can ask a supported question.
- System renders a validated chart/table/card.
- Invalid generated specs produce useful fallback.

Validation:

- Try several supported questions.
- Inspect trace logs.

Suggested commit message:

`Track 2: add LLM-guided dynamic dashboard workspace`

### Phase T2-6: LLM-Assisted Inefficiency Discovery

Status: `not_started`

Objective:

Use the LLM to propose candidate inefficiencies from bounded summaries, then validate candidates before promoting them to findings.

Deliverables:

- `CandidateFindingSpec`
- Discovery prompt.
- Candidate validation logic.
- Candidate-to-finding promotion.
- Discovery trace logs.

Acceptance criteria:

- System proposes candidate inefficiencies.
- Backend validates or rejects candidates.
- Validated candidates appear as ranked findings.

Validation:

- Run discovery on sample summaries.
- Inspect accepted/rejected candidates.

Suggested commit message:

`Track 2: add LLM-assisted inefficiency discovery`

### Phase T2-7: Track 2 Tuning and Demo Polish

Status: `not_started`

Objective:

Tune thresholds, ranking, dynamic specs, and discovery prompts for judge-facing usefulness.

Deliverables:

- Tuned finding thresholds.
- Tuned ranking.
- Clean top findings.
- Demo-ready dynamic questions.
- Known limitations documented.

Acceptance criteria:

- Dashboard tells a clear story.
- Top findings are evidence-backed and actionable.
- Dynamic workspace handles expected demo questions.

Validation:

- Manual demo rehearsal.

Suggested commit message:

`Track 2: tune efficiency dashboard for demo`

## Cross-Track Demo and Finalization

### Phase F1: Demo Script and Final Smoke Test

Status: `not_started`

Objective:

Prepare final hackathon demo flow and verify both selected tracks work.

Deliverables:

- Demo script.
- Known limitations.
- Final smoke-test checklist.
- Final run outputs or screenshots if useful.

Acceptance criteria:

- Human can run the demo without improvising core flow.
- Key claims are supported by visible evidence or traces.

Validation:

- Run through demo at least once.

Suggested commit message:

`Final: add demo script and smoke-test notes`

## Phase Update Template

Codex should use this template when updating a phase.

```text
### Phase X: Name

Status: ready_for_review

Objective:

...

Completed:

- ...

Validation:

- ...

Files changed:

- ...

Known risks:

- ...

POR changes:

- ...

Suggested commit message:

...

Next recommended phase:

...
```

## Open Coordination Questions

- Which track should be implemented first if time is limited?
- Will the event provide sample API credentials before the hackathon begins?
- Will public eval data be large enough to support Track 1 tuning?
- Will Track 2 have labels/expected findings, or will judging be qualitative?
- Are external LLM APIs allowed during judging?
- Is Streamlit acceptable for the final demo, or should Track 2 move to React/FastAPI if time allows?
