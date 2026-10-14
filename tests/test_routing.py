"""Routing rules from policy §3. No LLM calls."""

import routing
from normalize import normalize


def cloud_alert(repo):
    return normalize({
        "source": "cloud-posture", "finding_id": "cp-1", "repo": repo,
        "resource_arn": "arn:aws:s3:::some-bucket", "finding_type": "public-read-acl",
        "risk_score": 88, "first_seen": "19/09/2026 09:15",
    })


def test_unknown_service_goes_to_a_human_not_a_guessed_team():
    result = routing.route(cloud_alert("legacy-reporting"))
    assert result["mode"] == "manual"
    assert result["teams"] == []
    assert result["human_reasons"] == ["NOT_IN_CATALOG"]


def test_co_owned_service_notifies_both_teams_but_picks_neither():
    result = routing.route(cloud_alert("billing-worker"))
    assert result["mode"] == "manual"
    assert result["slack"] == ["#payments-platform", "#data-platform"]
    assert result["human_reasons"] == ["CO_OWNED"]
