# Architecture

`main.py` runs the steps below for one alert at a time, in file order.
Blue = code (fixed rules, tested). Orange = LLM (judgment only). Red = a human decides.

```mermaid
flowchart TD
    IN[/"data/alerts.json · 24 sample alerts<br/>or --alerts data/bad_alerts.json"/]

    N["<b>normalize.py</b> · code<br/>one adapter per scanner<br/>severity from policy §1 · time to UTC · data flags<br/>Xray: fix_available passed on as a fact"]
    INV(["Human review<br/>INVALID_INPUT, no LLM call"])

    AG["<b>agent.py</b> · LLM<br/>Google ADK + Gemini<br/>decides the action, writes summary + why"]
    JB["Judgment branches<br/>open match → link<br/>resolved match → reopen + RECURRENCE<br/>partial match → link + AMBIGUOUS_DUPLICATE<br/>no match → create<br/>'already fixed' note → keep severity + UNVERIFIED_MITIGATION"]

    T["<b>tools.py</b> · code<br/>lookup_owner(repo)<br/>find_matching_tickets(alert_id)"]
    S[("<b>store.py</b> · code<br/>ticket store for this run<br/>seeded from historical_tickets.json")]
    CAT[("data/service_catalog.json")]

    R["<b>routing.py</b> · code<br/>who gets the ticket (policy §3)<br/>teams · Slack · on-call · tier from the catalog"]
    RB["Routing branches<br/>one owner → auto<br/>co-owned → notify all teams + CO_OWNED<br/>not in catalog → security lead + NOT_IN_CATALOG"]

    G["<b>guardrails.py</b> · code<br/>checks the model's answer against the facts<br/>SLA from severity + tier (policy §2)"]
    GB["Rule branches<br/>ticket ID not returned by a tool → reject<br/>action doesn't fit the match → reject<br/>(create on exact · reopen on open · link to resolved)<br/>missed reason → code adds it<br/>(partial → AMBIGUOUS_DUPLICATE · resolved → RECURRENCE)<br/>lower priority → PRIORITY_DOWNGRADE"]
    ERR(["Human review<br/>LLM_ERROR"])

    M["<b>main.py</b> · code<br/>writes the decision to the store<br/>one record per ticket"]
    OUT[/"output/results.json<br/>or output/bad_alerts_results.json"/]
    HUM(["Human review<br/>needs_human = true, with reasons"])

    IN --> N
    N -- "unknown source, missing field, bad value" --> INV
    N -- "NormalizedAlert" --> AG
    N -- "NormalizedAlert" --> R
    R -- "lookup_owner" --> CAT
    R -.- RB
    R -- "teams, tier" --> M
    AG <-- "tool calls" --> T
    T --> S
    T --> CAT
    AG -.- JB
    AG -- "AgentDecision (no team field)" --> G
    G -.- GB
    G -- "answer fails a check" --> ERR
    G --> M
    M --> OUT
    OUT -- "any human reason" --> HUM

    classDef code fill:#dbeafe,stroke:#2563eb,color:#0f172a
    classDef llm fill:#ffedd5,stroke:#c2410c,color:#0f172a
    classDef human fill:#fee2e2,stroke:#b91c1c,color:#0f172a
    classDef data fill:#f1f5f9,stroke:#64748b,color:#0f172a
    classDef note fill:#ffffff,stroke:#94a3b8,stroke-dasharray:4 3,color:#0f172a
    class N,T,S,R,G,M code
    class AG llm
    class INV,HUM,ERR human
    class IN,CAT,OUT data
    class JB,RB,GB note
```

**The rule:** the model proposes, code enforces. The model never outputs a team, every ticket ID it returns must have come from a tool call in the same run, and its action must fit what the tool found.

**Routing runs without the model.** `routing.py` reads the owner and tier from the service catalog before the agent runs, so the model has no say in who gets the ticket.

**Severity vs. tier.** Severity (Sev-0 to Sev-3) is how bad the finding is. It comes from the scanner's score, normalized by `normalize.py`, and the model may recommend changing it. Tier (P0 to P3) is how critical the service is. It comes from `criticality_tier` in the service catalog and nothing in the pipeline changes it. The SLA is set by both. A service missing from the catalog has no tier and gets the strictest SLA column (P0/P1).
