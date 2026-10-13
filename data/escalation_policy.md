# Alert Triage & Escalation Policy (v3) — Reference Copy

Synthetic reference document for the take-home exercise. This is the kind of
internal policy an agent like the one you're building would need to encode
and apply consistently — not a spec for the code itself.

## 1. Normalized severity

Each scanner reports severity on its own scale. Triage runs on one normalized
scale, **Sev-0 (highest) through Sev-3 (lowest)**:

| Normalized | Xray `cvss_score` | Code-scan `severity_label` | Cloud-posture `risk_score` |
|---|---|---|---|
| Sev-0 | 9.0 – 10.0 | Critical | 85 – 100 |
| Sev-1 | 7.0 – 8.9 | High | 60 – 84 |
| Sev-2 | 4.0 – 6.9 | Medium | 30 – 59 |
| Sev-3 | 0.0 – 3.9 | Low | 0 – 29 |

Normalized severity is a starting point, not a verdict. A finding with an
available, deployed fix, or one already tracked as resolved, should generally
be treated as lower urgency than the raw score implies — use judgment, and
say so in the ticket rather than silently overriding the score.

## 2. Ticket SLA by tier

| Normalized severity | Service tier P0/P1 | Service tier P2/P3 |
|---|---|---|
| Sev-0 | 4 business hours | 1 business day |
| Sev-1 | 1 business day | 3 business days |
| Sev-2 | 3 business days | 1 week |
| Sev-3 | 1 week | Best effort |

## 3. Routing

- Route to the owning team's Slack channel and on-call rotation from the
  service catalog.
- If a service has more than one listed owning team, **do not pick one** —
  flag the ticket for manual routing and notify both channels.
- If a service isn't in the catalog at all, **do not guess an owner** — flag
  for manual routing to the on-call security lead.

## 4. Duplicate and recurrence handling

- If an open ticket already exists for the same underlying finding
  (same component + CVE, same rule + file, or same resource + finding type),
  link the new detection to it instead of opening a new one.
- If a matching ticket exists but is marked **resolved**, treat the new
  detection as a possible recurrence, not a duplicate — reopening or
  escalating is usually more appropriate than silent dedup, especially if
  the resolution note flags the fix as fragile or automation-reverted.
- Multiple raw alerts that describe the same incident (same resource or
  component, same finding type, detected within a short window) should be
  grouped into a single ticket, not filed individually.

## 5. What counts as "manual review required"

Route to manual review (rather than fully automated ticket creation) whenever
confidence is genuinely low — co-owned or unregistered services, ambiguous
duplicate matches, or a finding type the policy above doesn't clearly cover.
An automated system that is wrong silently is worse than one that asks for
help visibly.
