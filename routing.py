"""Who gets the ticket (policy §3). Code decides this, never the model."""

from models import NormalizedAlert
from tools import lookup_owner

# Policy §3 names this role, but no data file lists it. A placeholder until we know who it is.
SECURITY_LEAD_ON_CALL = "security-lead-oncall"


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
