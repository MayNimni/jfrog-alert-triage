# Reflection

## Assumptions

1. **code-scan timestamps are wrong, not old.** `reported_ts` decodes to September 2025, exactly a year before every other alert and ticket. I keep the raw value, convert it, and flag `TIMESTAMP_SUSPECT` rather than dropping the alert. No decision depends on time, so the flag informs a reviewer but changes nothing.
2. **cloud-posture `first_seen` is UTC.** It has no time zone.
3. **`fix_available` means a fixed version exists, not that it's deployed.** It is passed to the agent as a fact and never lowers severity by itself.
4. **A note is a claim.** "Upgraded in prod per SEC-4055" can't be checked (SEC-4055 isn't in the data), so severity and SLA stay. The model can recommend lower, and a human approves.
5. **A ticket missing an identity field is only a partial match.** `SEC-4110` has a repo and rule but no file, so linking to it needs human confirmation.
6. **Alerts arrive in file order, one at a time.** Tickets created earlier in a run are visible to later alerts, which is how the five S3 alerts collapse into one ticket.
7. **Co-owned and unknown services still get a ticket.** Policy §3 says flag for manual routing, not block. A public S3 bucket shouldn't wait on an ownership question. The ticket is created, flagged, and every listed team is notified.
8. **Unknown tier gets the strictest SLA column.** Failing toward urgency is cheaper than failing toward silence.

## How I'd evaluate correctness and catch hallucination

**What's in place now.** The LLM never produces a fact the pipeline relies on without a check. Severity, owner, and SLA are computed by code and unit-tested against hand-worked policy values. The model's answer is a typed schema. Every ticket ID it returns must appear in a tool result from the same run, and its action must fit the match type and status. A failed check becomes a visible `LLM_ERROR`, never a silent ticket. Every record carries the full tool trace, so any decision can be audited. I ran the full set three times and got the same decisions each time.

**What I'd add.**
- **A gold set.** These 24 alerts plus the bad-input fixtures, each labeled with the expected action, ticket, and human reasons. Run on every prompt or model change, scored on action accuracy and, above all, *recall of human flags*. Missing a needed flag is the costly error.
- **Repeat runs** of each alert, to measure how stable decisions are, not just whether they're right once.
- **Summary grounding.** Every CVE, file, ARN, and ticket ID in the summary must appear in the alert or a tool result. That catches invented details in the one free-text field.
- **In production,** track how often humans override each decision type. A rising override rate is the earliest sign of drift.

## What I'd change first with another week

1. The gold-set eval above, wired into CI. Without it, every prompt change is a guess.
2. A tool that checks mitigation claims against the deployed artifact (the Xray/Artifactory build actually running) instead of trusting a note.
3. Time-window grouping, plus correlation across resources (e.g. the two unencrypted queues in `notification-service`), with a confidence level that feeds `AMBIGUOUS_DUPLICATE`.
4. Real integrations: idempotent Jira create/link against the live tracker, Slack and PagerDuty notify, and a persistent store so dedup works across runs.
5. A code-level flag when a note contains instructions, so prompt injection doesn't depend on the model reporting it.

## What I'd want to know before this touched real JFrog systems or data

- **What may leave the network.** Alerts hold repo names, ARNs, file paths, and for `hardcoded-secret` possibly the secret itself. Which LLM vendors are approved for that, and what are the data-retention terms?
- **The source of truth for ownership.** How fresh is the service catalog, who settles co-owned services like `billing-worker`, and who is the security lead on-call?
- **Real scanner contracts.** Is the 2025 epoch a scanner bug or a format I misread? What other fields and values show up at real volume?
- **Tracker semantics.** What do "resolved" and "closed" mean, and who is allowed to reopen?
- **Rollout.** I'd start in shadow mode: the agent decides next to the human triager, read-only, and we compare the two before it files anything. Then come cost and rate limits at real alert volume, and audit logging for every automated action.
