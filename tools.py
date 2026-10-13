"""The two tools the agent can call. Plain functions: ADK reads the docstrings as tool descriptions."""

import json
from pathlib import Path

import store
from models import NormalizedAlert

CATALOG_PATH = Path(__file__).parent / "data" / "service_catalog.json"

# alert_id -> NormalizedAlert. Filled by main.py before the run.
ALERTS: dict[str, NormalizedAlert] = {}


def as_list(value) -> list:
    """The catalog mixes "x", ["x", "y"] and null. Always return a list."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def lookup_owner(repo: str) -> dict:
    """Look up who owns a repo in the service catalog.

    Returns the owning teams, Slack channels, on-call rotations and criticality tier.
    co_owned is True when more than one team is listed. found is False when the
    repo is not in the catalog at all.
    """
    with open(CATALOG_PATH) as f:
        services = json.load(f)["services"]
    for service in services:
        if service["repo"] == repo:
            teams = as_list(service["team"])
            return {
                "found": True,
                "teams": teams,
                "slack": as_list(service["slack_channel"]),
                "on_call": as_list(service["on_call"]),
                "tier": service.get("criticality_tier"),
                "co_owned": len(teams) > 1,
                "note": service.get("note"),
            }
    return {"found": False, "reason": "not in service catalog"}


def find_matching_tickets(alert_id: str) -> dict:
    """Find existing tickets about the same finding as this alert.

    Each match has a match_type: "exact" (same finding) or "partial" (likely the
    same, but a field is missing), the ticket status ("open" or "resolved"),
    a resolution_note if any, and the alert_ids already linked to it.
    An empty list means no ticket exists for this finding yet.
    """
    alert = ALERTS.get(alert_id)
    if alert is None:
        return {"error": f"unknown alert_id {alert_id!r}"}
    return {"alert_id": alert_id, "matches": store.find_matches(alert)}
