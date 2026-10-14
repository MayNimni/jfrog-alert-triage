"""Guardrail checks. No LLM calls: the agent's answer is written by hand."""

from pathlib import Path

import guardrails
import store
from models import AgentDecision

DATA = Path(__file__).parent.parent / "data"


def test_a_ticket_id_no_tool_returned_is_caught_as_a_hallucination():
    store.load_store(DATA / "historical_tickets.json")
    decision = AgentDecision(action="link", linked_ticket_id="SEC-4102", summary="...", why="...")
    trace = [{"tool": "find_matching_tickets", "args": {"alert_id": "cp-1"}, "result": {"matches": []}}]
    problems = guardrails.check_decision(decision, trace)
    assert problems == ["ticket 'SEC-4102' was not returned by a tool in this run"]


# --- Does the action fit what the tools found? ---

def tool_found(ticket_id, match_type, status):
    """A trace where find_matching_tickets returned exactly one match."""
    match = {"ticket_id": ticket_id, "match_type": match_type, "status": status}
    return [{"tool": "find_matching_tickets", "args": {}, "result": {"matches": [match]}}]


def decide(action, ticket_id=None):
    return AgentDecision(action=action, linked_ticket_id=ticket_id, summary="...", why="...")


def test_create_when_an_exact_match_exists_is_rejected_as_a_duplicate():
    store.load_store(DATA / "historical_tickets.json")
    problems = guardrails.check_decision(decide("create"), tool_found("SEC-4102", "exact", "open"))
    assert problems == ["create although SEC-4102 is an exact match (a duplicate)"]


def test_reopen_on_an_open_ticket_and_link_to_a_resolved_one_are_rejected():
    store.load_store(DATA / "historical_tickets.json")
    reopen_open = guardrails.check_decision(decide("reopen", "SEC-4102"), tool_found("SEC-4102", "exact", "open"))
    link_resolved = guardrails.check_decision(decide("link", "SEC-3987"), tool_found("SEC-3987", "exact", "resolved"))
    assert reopen_open == ["reopen on SEC-4102, which is already open"]
    assert link_resolved == ["link to resolved SEC-3987 would hide a recurrence (policy §4)"]


def test_code_adds_the_human_reason_the_model_forgot():
    partial = tool_found("SEC-4110", "partial", "open")
    resolved = tool_found("SEC-3987", "exact", "resolved")
    assert guardrails.reasons_the_model_missed(decide("link", "SEC-4110"), partial) == ["AMBIGUOUS_DUPLICATE"]
    assert guardrails.reasons_the_model_missed(decide("reopen", "SEC-3987"), resolved) == ["RECURRENCE"]


def test_create_next_to_a_partial_match_goes_to_a_human():
    partial = tool_found("SEC-4110", "partial", "open")
    assert guardrails.reasons_the_model_missed(decide("create"), partial) == ["AMBIGUOUS_DUPLICATE"]
