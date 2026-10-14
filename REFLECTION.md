# Reflection

## Assumptions

1. **Times.** code-scan timestamps decode to 2025, a year off. I flag them `TIMESTAMP_SUSPECT` rather than drop them. cloud-posture times have no zone, so I read them as UTC.
2. **A note or `fix_available` is a claim, not a fact.** Severity and SLA stay; the model can recommend lower, and a human approves.
3. **A ticket missing an identity field is only a partial match.** `SEC-4110` has no file, so a human confirms the link.
4. **Co-owned and unknown services still get a ticket**, flagged for manual routing. A public S3 bucket shouldn't wait on an ownership question.
5. **Unknown tier gets the strictest SLA.** Failing toward urgency beats failing toward silence.

## How I'd evaluate correctness and catch hallucination

**In place now.**
- **Code decides the facts.** Severity, owner, and SLA come from code, not the model, and are unit-tested.
- **Code checks the model.** A ticket ID no tool returned, or an action that doesn't fit what the tools found, is rejected and sent to a human (`LLM_ERROR`).
- **Everything is traceable.** Each record keeps every tool call and result.

**What I'd add: watch, learn, fix.**
- **Watch.** Log every run and whether a human changed the decision (ADK's `BigQueryAgentAnalyticsPlugin` for a dashboard, `adk web` for one run).
- **Learn.** Every mistake a human catches becomes a test case. Over time this is the golden set.
- **Fix.** Change the prompt or code, then rerun the golden set with `adk eval` before shipping.
- **Check the summary**, the only free text the model writes, with ADK's `hallucinations_v1` metric.

## What I'd change first with another week

1. The golden set and `adk eval`, run on every change.
2. A tool that checks a mitigation claim against the deployed artifact, instead of trusting the note.
3. Time-window grouping and correlation across resources.
4. Real integrations: Jira, Slack, PagerDuty, and a persistent store so dedup works across runs.

## What I'd want to know before this touched real JFrog systems or data

- **Data and security.** What leaves the network, where it goes, and who approves it. A `hardcoded-secret` finding may hold the secret itself.
- **Sources of truth.** What the system trusts (catalog, scanners) and how fresh it is.
- **Contracts.** What exactly comes in, and what each ticket status means.
- **Gradual rollout.** Shadow first, then a small share, then everything.
- **Stop button and rollback.** How to turn it off fast and undo what it filed.
- **Least privilege.** It can do only what it needs.
- **Ownership and measurement.** Who owns it after launch, what we measure, cost, and logs.
