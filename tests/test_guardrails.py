"""Guardrail checks. No LLM calls: the agent's answer is written by hand."""

from pathlib import Path

import guardrails
import store
from models import AgentDecision
from normalize import normalize

DATA = Path(__file__).parent.parent / "data"


def cloud_alert(repo):
    return normalize({
        "source": "cloud-posture", "finding_id": "cp-1", "repo": repo,
        "resource_arn": "arn:aws:s3:::some-bucket", "finding_type": "public-read-acl",
        "risk_score": 88, "first_seen": "19/09/2026 09:15",
    })


def test_unknown_service_goes_to_a_human_not_a_guessed_team():
    routing = guardrails.route(cloud_alert("legacy-reporting"))
    assert routing["mode"] == "manual"
    assert routing["teams"] == []
    assert routing["human_reasons"] == ["NOT_IN_CATALOG"]


def test_co_owned_service_notifies_both_teams_but_picks_neither():
    routing = guardrails.route(cloud_alert("billing-worker"))
    assert routing["mode"] == "manual"
    assert routing["slack"] == ["#payments-platform", "#data-platform"]
    assert routing["human_reasons"] == ["CO_OWNED"]


def test_a_ticket_id_no_tool_returned_is_caught_as_a_hallucination():
    store.load_store(DATA / "historical_tickets.json")
    decision = AgentDecision(action="link", linked_ticket_id="SEC-4102", summary="...", why="...")
    trace = [{"tool": "find_matching_tickets", "args": {"alert_id": "cp-1"}, "result": {"matches": []}}]
    problems = guardrails.check_decision(decision, trace)
    assert problems == ["ticket 'SEC-4102' was not returned by a tool in this run"]
