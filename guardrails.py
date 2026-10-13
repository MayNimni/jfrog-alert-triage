"""Code enforces what the model must not decide: routing, SLA, and checks on the model's answer."""

import store
from models import AgentDecision, NormalizedAlert
from tools import lookup_owner

# Policy §3 names this role, but no data file lists it. A placeholder until we know who it is.
SECURITY_LEAD_ON_CALL = "security-lead-oncall"

# Policy §2: SLA by normalized severity and service tier.
SLA = {
    "Sev-0": {"P0/P1": "4 business hours", "P2/P3": "1 business day"},
    "Sev-1": {"P0/P1": "1 business day", "P2/P3": "3 business days"},
    "Sev-2": {"P0/P1": "3 business days", "P2/P3": "1 week"},
    "Sev-3": {"P0/P1": "1 week", "P2/P3": "best effort"},
}

SEVERITY_ORDER = ["Sev-0", "Sev-1", "Sev-2", "Sev-3"]  # most urgent first


# --- Routing (policy §3) ---

def route(alert: NormalizedAlert) -> dict:
    """Who gets the ticket. Never guesses: co-owned or unknown services go to a human."""
    owner = lookup_owner(alert.repo)

    if not owner["found"]:
        return {
            "mode": "manual",
            "teams": [],
            "slack": [],
            "on_call": [SECURITY_LEAD_ON_CALL],
            "tier": None,
            "human_reasons": ["NOT_IN_CATALOG"],
        }

    routing = {
        "mode": "auto",
        "teams": owner["teams"],
        "slack": owner["slack"],
        "on_call": owner["on_call"],
        "tier": owner["tier"],
        "human_reasons": [],
    }
    if owner["co_owned"]:
        # Notify every listed team, but don't pick one.
        routing["mode"] = "manual"
        routing["human_reasons"] = ["CO_OWNED"]
    return routing


def sla_label(severity: str, tier: str | None) -> str:
    """The SLA as a label. An unknown tier gets the strictest column, to fail safe."""
    column = "P2/P3" if tier in ("P2", "P3") else "P0/P1"
    return SLA[severity][column]


# --- Checks on the model's answer ---

def matches_returned_by_tools(trace: list[dict]) -> list[dict]:
    """Every ticket match that find_matching_tickets returned in this run."""
    matches = []
    for entry in trace:
        if entry["tool"] == "find_matching_tickets" and entry["result"]:
            matches += entry["result"].get("matches", [])
    return matches


def match_for_ticket(ticket_id: str | None, trace: list[dict]) -> dict | None:
    for match in matches_returned_by_tools(trace):
        if match["ticket_id"] == ticket_id:
            return match
    return None


def check_decision(decision: AgentDecision, trace: list[dict]) -> list[str]:
    """Problems that make the model's answer untrustworthy. Empty list = the answer passes."""
    problems = []
    tools_called = [entry["tool"] for entry in trace]
    ticket_id = decision.linked_ticket_id

    if "find_matching_tickets" not in tools_called:
        problems.append("the agent never checked for existing tickets")

    if decision.action in ("link", "reopen"):
        match = match_for_ticket(ticket_id, trace)
        if ticket_id not in store.TICKETS:
            problems.append(f"ticket {ticket_id!r} does not exist")
        elif match is None:
            problems.append(f"ticket {ticket_id!r} was not returned by a tool in this run")
        elif decision.action == "reopen" and match["status"] == "open":
            problems.append(f"reopen on {ticket_id}, which is already open")
        elif decision.action == "link" and match["status"] == "resolved":
            problems.append(f"link to resolved {ticket_id} would hide a recurrence (policy §4)")

    if decision.action == "create":
        for match in matches_returned_by_tools(trace):
            if match["match_type"] == "exact":
                problems.append(f"create although {match['ticket_id']} is an exact match (a duplicate)")

    if decision.recommended_priority and not decision.priority_reason:
        problems.append("recommended_priority has no priority_reason")

    return problems


def reasons_the_model_missed(decision: AgentDecision, trace: list[dict]) -> list[str]:
    """Human reasons the tool results call for, but the model left out. Code adds them."""
    match = match_for_ticket(decision.linked_ticket_id, trace)
    if match is None:
        return []
    missed = []
    if match["match_type"] == "partial" and "AMBIGUOUS_DUPLICATE" not in decision.judgment_reasons:
        missed.append("AMBIGUOUS_DUPLICATE")
    if match["status"] == "resolved" and "RECURRENCE" not in decision.judgment_reasons:
        missed.append("RECURRENCE")
    return missed


def most_urgent(severity_a: str, severity_b: str) -> str:
    if SEVERITY_ORDER.index(severity_a) <= SEVERITY_ORDER.index(severity_b):
        return severity_a
    return severity_b


def is_downgrade(decision: AgentDecision, alert: NormalizedAlert) -> bool:
    """True when the model recommends a less urgent priority than the normalized severity."""
    if decision.recommended_priority is None:
        return False
    return SEVERITY_ORDER.index(decision.recommended_priority) > SEVERITY_ORDER.index(alert.normalized_severity)
