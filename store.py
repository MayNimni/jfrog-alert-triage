"""The in-memory ticket tracker: our mini Jira for one run.

Seeded from historical_tickets.json. Every ticket the agent creates, links or
reopens is written here, so a repeat alert later in the same run finds it.
"""

import json
from pathlib import Path

from models import NormalizedAlert

# ticket_id -> ticket dict. Reset by load_store() at the start of every run.
TICKETS: dict[str, dict] = {}


def load_store(path: Path) -> None:
    TICKETS.clear()
    with open(path) as f:
        for ticket in json.load(f)["tickets"]:
            ticket["alert_ids"] = []
            TICKETS[ticket["ticket_id"]] = ticket


# --- Matching (policy §4: same component + CVE, same rule + file, same resource + finding type) ---

def match_type(alert: NormalizedAlert, ticket: dict) -> tuple[str, str] | None:
    """Return (match_type, reason) if the ticket is about the same finding, else None."""
    if ticket["source"] != alert.source:
        return None

    if alert.source == "xray-scan":
        if (ticket.get("repo"), ticket.get("component"), ticket.get("cve")) == (alert.repo, alert.component, alert.cve):
            return "exact", "same repo + component + CVE"

    elif alert.source == "code-scan":
        if (ticket.get("repo"), ticket.get("rule")) == (alert.repo, alert.rule):
            if ticket.get("file") == alert.file:
                return "exact", "same repo + rule + file"
            if ticket.get("file") is None:
                return "partial", "same repo + rule, but the ticket has no file"

    elif alert.source == "cloud-posture":
        if (ticket.get("resource_arn"), ticket.get("finding_type")) == (alert.resource_arn, alert.finding_type):
            return "exact", "same resource ARN + finding type"

    return None


def find_matches(alert: NormalizedAlert) -> list[dict]:
    """All tickets about the same finding, with how sure the match is."""
    if "ARN_UNPARSEABLE" in alert.flags:
        return []  # a broken ARN can't be trusted as an identity

    matches = []
    for ticket in TICKETS.values():
        found = match_type(alert, ticket)
        if found is None:
            continue
        kind, reason = found
        matches.append({
            "ticket_id": ticket["ticket_id"],
            "status": ticket["status"],
            "match_type": kind,
            "reason": reason,
            "resolution_note": ticket.get("resolution_note"),
            "alert_ids": list(ticket["alert_ids"]),  # a copy, so later links don't rewrite this answer
        })
    return matches


# --- Writes ---

def create_ticket(alert: NormalizedAlert) -> str:
    new_count = sum(1 for ticket_id in TICKETS if ticket_id.startswith("NEW-"))
    ticket_id = f"NEW-{new_count + 1:03d}"
    TICKETS[ticket_id] = {
        "ticket_id": ticket_id,
        "source": alert.source,
        "repo": alert.repo,
        "component": alert.component,
        "cve": alert.cve,
        "rule": alert.rule,
        "file": alert.file,
        "resource_arn": alert.resource_arn,
        "finding_type": alert.finding_type,
        "status": "open",
        "created_at": alert.detected_at,
        "alert_ids": [alert.alert_id],
    }
    return ticket_id


def link(ticket_id: str, alert_id: str) -> None:
    TICKETS[ticket_id]["alert_ids"].append(alert_id)


def reopen(ticket_id: str, alert_id: str) -> None:
    """Mark a resolved ticket open again, so the next repeat alert links instead of reopening twice."""
    TICKETS[ticket_id]["status"] = "open"
    TICKETS[ticket_id]["alert_ids"].append(alert_id)
