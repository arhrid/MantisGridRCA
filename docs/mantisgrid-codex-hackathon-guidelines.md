# MantisGrid Hackathon Codex Guidelines

## Purpose

This guide describes how Codex should work during the MantisGrid hackathon. It complements the Track 1 and Track 2 POR docs.

The goal is to keep Codex focused, incremental, testable, and aligned with the current Plan of Record while leaving clear checkpoints for human review.

## Always Read First

Before starting implementation work, Codex should read:

- `mantisgrid-track1-rca-por.md`
- `mantisgrid-track2-cluster-efficiency-por.md`
- `mantisgrid-hackathon-implementation-plan.md`

The POR docs describe what we are building and why. The implementation plan describes the current phase, status, and next checkpoint.

## Start-of-Hackathon Update Intake

At the start of the hackathon, and before beginning implementation, Codex should explicitly ask the humans for the latest event updates, instructions, files, API docs, credentials guidance, judging criteria, and any verbal clarifications.

New hackathon-provided information may override assumptions in the POR docs and implementation plan.

Codex should treat the current docs as the best-known plan, not immutable truth. When new official event details conflict with earlier assumptions, Codex should:

- Call out the conflict.
- Ask whether the new information should supersede the earlier assumption if the answer is not obvious.
- Update the affected POR docs.
- Update the implementation plan.
- Adjust the current phase scope if needed.

Examples of assumptions that may change:

- Direct API access vs required MCP usage.
- Available telemetry types.
- API authentication model.
- External LLM policy.
- Eval data format.
- Judging criteria.
- Track-specific deliverables.
- Required runtime or packaging format.

Codex should not begin coding from stale assumptions if fresh event instructions are available.

## Working Rhythm

Codex should work one phase at a time.

Default loop:

```text
Read POR docs and implementation plan
  |
  +-- Confirm current phase
  |
  +-- Implement the scoped phase
  |
  +-- Run tests / smoke checks / manual validation
  |
  +-- Update implementation plan
  |
  +-- Summarize changes, risks, and next steps
  |
  +-- Stop for human review
```

At the end of each phase, Codex should:

- Update the implementation plan with status.
- Record what changed.
- Record validation performed.
- Record known risks, blockers, and assumptions.
- Suggest a commit message.
- Wait for human review before starting the next phase unless explicitly told to continue.

Codex should not commit or push unless explicitly asked.

## Implementation Defaults

Default architecture:

- Mac laptop host.
- Local Python runtime on the Mac laptop. Add Docker packaging only if later required by the hackathon or useful for handoff.
- Python backend.
- Direct MantisGrid API access as the default data path.
- Optional MCP adapter only if useful or required.
- DuckDB or Polars for local caching and query.
- Streamlit as the default UI.
- Cloud LLM behind a provider-independent interface when needed.

Avoid starting with:

- Native Mac apps.
- Cloud deployment.
- Kubernetes deployment.
- Complex distributed services.
- Model training or fine-tuning.
- Automated remediation.
- Broad refactors not required by the current phase.

## LLM and Tooling Rules

The cloud LLM should not directly call MantisGrid APIs or telemetry tools.

Codex should preserve this control model:

```text
LLM proposes
  |
Python backend validates
  |
Python backend executes
  |
Python backend summarizes
  |
LLM reasons over bounded results
```

Backend must own:

- API credentials.
- Tool execution.
- Data retrieval.
- Validation.
- Budgets.
- Evidence IDs.
- Trace logging.
- Final persisted outputs.

LLM outputs should use structured contracts wherever possible:

- Track 1: RCA state updates, tool requests, final RCA answer.
- Track 2: AnalysisIntent, DataRequest, ViewSpec, DashboardSpec, CandidateFindingSpec.

## Track 1 Operating Rules

Track 1 is an RCA investigation system.

Prioritize:

- One incident end-to-end early.
- Detailed trace logging.
- LLM-stepped RCA workflow.
- Constrained telemetry tools.
- Eval harness.
- Batch eval/tuning loop.
- Clear symptom-vs-root-cause distinction.
- Evidence-backed final answers.

Track 1 core loop:

```text
Incident
  -> affected entities
  -> dependency context
  -> hypotheses
  -> tool planning
  -> backend tool execution
  -> evidence interpretation
  -> hypothesis update
  -> final RCA answer
  -> eval scoring
```

Codex should never let the LLM see gold labels during an RCA run. Gold labels are used only by the eval harness after the run.

## Track 2 Operating Rules

Track 2 is a cluster efficiency and dynamic dashboarding system.

Track 2 has three intelligence layers:

1. Deterministic baseline dashboard.
2. LLM-guided dynamic dashboarding.
3. LLM-assisted inefficiency discovery.

Prioritize:

- Derived analytics and named findings, not just charts.
- Evidence-backed finding cards.
- Business impact next to technical evidence.
- Dynamic dashboard specs validated by the backend.
- Candidate inefficiency findings validated before promotion.
- Traceability from every finding back to data.

The LLM should emit specs, not UI code.

## Evaluation and Tuning Rules

Evaluation and tuning are central, not optional polish.

For Track 1:

- Run the RCA workflow against gold incidents.
- Save full traces.
- Score against gold labels.
- Classify failure modes.
- Tune prompts, tool policy, summaries, schemas, and budgets.
- Rerun the full eval set after each meaningful change.

For Track 2:

- If labels or expected findings exist, score against them.
- If not, tune against evidence quality, actionability, duplicate suppression, and dashboard usefulness.
- Track failed dynamic specs and invalid candidate findings.

Failure-driven tuning rule:

Make the smallest targeted change that explains a failure, then rerun the full relevant eval set.

## Logging and Traceability Rules

Detailed logs are required.

Track 1 should log every RCA step:

- prompts or prompt hashes
- LLM outputs
- parsed structured outputs
- tool requests
- validation decisions
- tool calls
- tool summaries
- state before/after each step
- hypotheses
- stop reason
- final answer
- eval score

Track 2 should log:

- generated findings
- evidence IDs
- source tables or API calls
- thresholds and scoring rules
- dynamic dashboard specs
- validation errors
- executed data requests
- rendered views
- LLM-assisted candidate findings
- promotion/rejection decisions

Do not log secrets, credentials, or unrestricted raw telemetry dumps.

## Phase Discipline

Each phase should have:

- Objective.
- Scope.
- Deliverables.
- Acceptance criteria.
- Validation steps.
- Known risks.
- Human review checkpoint.

Codex should prefer a working vertical slice over broad scaffolding.

If a phase is too large, Codex should split it into smaller phases and update the implementation plan.

## Human Review Handoff

At each handoff, Codex should provide:

- What changed.
- How it was validated.
- Where to look.
- Known limitations.
- Suggested commit message.
- Next recommended phase.

Commit message format:

```text
Track N: concise phase summary
```

Examples:

- `Track 1: add RCA state and trace logging`
- `Track 1: add batch eval runner`
- `Track 2: add dynamic dashboard spec validator`
- `Track 2: add inefficiency discovery candidates`

## Decision Rules Under Time Pressure

When time is short:

- Prefer direct API access over MCP unless MCP is required.
- Prefer Streamlit over React unless UI polish becomes a judged differentiator.
- Prefer deterministic rules before LLM flourish.
- Prefer traceability over cleverness.
- Prefer one working incident or dashboard slice over broad incomplete architecture.
- Prefer configs and schemas that can be tuned quickly.
- Prefer simple validation and visible evidence over opaque automation.

## Final Demo Bias

The final demo should make it obvious that the system is not just charts or chat.

Track 1 demo message:

> The system investigates incidents with a repeatable RCA loop, controlled tools, evidence, and eval traces.

Track 2 demo message:

> The system finds cluster inefficiencies, explains the evidence, and lets users ask dynamic follow-up questions that become validated dashboard views.
