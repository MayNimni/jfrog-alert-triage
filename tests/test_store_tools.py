"""Store and tool checks against the real data files. Expected results were worked out by hand."""

from pathlib import Path

import pytest

import store
import tools
from normalize import load_alerts, normalize

DATA = Path(__file__).parent.parent / "data"


@pytest.fixture(autouse=True)
def fresh_run():
    """Every test starts like a new run: historical tickets loaded, all alerts normalized."""
    store.load_store(DATA / "historical_tickets.json")
    tools.ALERTS.clear()
    for raw in load_alerts(DATA / "alerts.json"):
        alert = normalize(raw)
        tools.ALERTS[alert.alert_id] = alert


def only_match(alert_id):
    matches = tools.find_matching_tickets(alert_id)["matches"]
    assert len(matches) == 1
    return matches[0]


def test_jackson_matches_open_ticket_exactly():
    match = only_match("xr-88213")
    assert (match["ticket_id"], match["status"], match["match_type"]) == ("SEC-4102", "open", "exact")


def test_tls_alert_is_only_a_partial_match():
    match = only_match("cs-51301")
    assert (match["ticket_id"], match["match_type"]) == ("SEC-4110", "partial")


def test_reopened_s3_ticket_is_seen_as_open_by_the_next_alert():
    assert only_match("cp-77010")["status"] == "resolved"
    store.reopen("SEC-3987", "cp-77010")
    match = only_match("cp-77011")
    assert match["status"] == "open"
    assert match["alert_ids"] == ["cp-77010"]


def test_different_bucket_does_not_match():
    assert tools.find_matching_tickets("cp-77168")["matches"] == []


def test_owner_lookup_flags_co_owned_and_unknown_services():
    assert tools.lookup_owner("billing-worker")["co_owned"] is True
    assert tools.lookup_owner("legacy-reporting")["found"] is False
