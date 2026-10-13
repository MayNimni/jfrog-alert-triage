"""Run the triage pipeline: normalize -> agent -> guardrails -> one record per ticket.

Usage:
    python main.py                                # all alerts in data/alerts.json
    python main.py cp-77010 cp-77011              # only these alerts (fewer LLM calls)
    python main.py --alerts data/bad_alerts.json  # another alerts file
"""

import argparse
import json
from pathlib import Path

import guardrails
import store
import tools
from agent import AgentError, run_agent
from models import NormalizedAlert
from normalize import InvalidAlert, load_alerts, normalize

DATA = Path(__file__).parent / "data"
DEFAULT_ALERTS = DATA / "alerts.json"
OUTPUT_DIR = Path(__file__).parent / "output"


def output_path(alerts_path: Path) -> Path:
    """results.json for the main alerts file, <name>_results.json for any other, so nothing is overwritten."""
    if alerts_path.resolve() == DEFAULT_ALERTS.resolve():
        return OUTPUT_DIR / "results.json"
    return OUTPUT_DIR / f"{alerts_path.stem}_results.json"


def apply_to_store(action: str, linked_ticket_id: str | None, alert: NormalizedAlert) -> str:
    """Write the decision into the ticket store. Returns the ticket the alert ended up on."""
    if action == "link":
        store.link(linked_ticket_id, alert.alert_id)
        return linked_ticket_id
    if action == "reopen":
        store.reopen(linked_ticket_id, alert.alert_id)
        return linked_ticket_id
    if action == "create":
        return store.create_ticket(alert)
    # manual_review: no automated ticket (policy §5). A human gets a review item instead.
    return f"REVIEW-{alert.alert_id}"


def triage(alert: NormalizedAlert) -> dict:
    """Decide what happens to one alert, and return everything the output record needs."""
    routing = guardrails.route(alert)
    human_reasons = routing.pop("human_reasons")  # routing keeps only who and where

    try:
        decision, trace = run_agent(alert)
        problems = guardrails.check_decision(decision, trace)
    except AgentError as error:
        decision, trace, problems = None, [], [str(error)]

    if problems:
        action, linked_ticket_id = "manual_review", None
        human_reasons.append("LLM_ERROR")
    else:
        action, linked_ticket_id = decision.action, decision.linked_ticket_id
        human_reasons += decision.judgment_reasons
        human_reasons += guardrails.reasons_the_model_missed(decision, trace)
        if action == "manual_review" and not human_reasons:
            human_reasons.append("AGENT_UNSURE")  # the model asked for review without saying why
        if guardrails.is_downgrade(decision, alert):
            human_reasons.append("PRIORITY_DOWNGRADE")  # a human approves; the SLA stays on normalized severity

    ticket_id = apply_to_store(action, linked_ticket_id, alert)
    return {
        "ticket_id": ticket_id,
        "action": action,
        "routing": routing,
        "human_reasons": human_reasons,
        "decision": decision,
        "trace": {"alert_id": alert.alert_id, "action": action, "problems": problems,
                  "why": decision.why if decision else None, "tool_calls": trace},
    }


def add_to_records(records: dict, alert: NormalizedAlert, result: dict) -> None:
    """One record per ticket. A linked alert joins the record of the ticket it was linked to."""
    ticket_id = result["ticket_id"]
    if ticket_id not in records:
        decision = result["decision"]
        records[ticket_id] = {
            "ticket_id": ticket_id,
            "action": result["action"],
            "alert_ids": [],
            "severity": alert.normalized_severity,
            "raw_scores": [],
            "routing": result["routing"],
            "sla": None,
            "needs_human": False,
            "human_reasons": [],
            "summary": decision.summary if decision else None,
            "recommended_priority": decision.recommended_priority if decision else None,
            "priority_reason": decision.priority_reason if decision else None,
            "flags": [],
            "trace": [],
        }

    record = records[ticket_id]
    record["alert_ids"].append(alert.alert_id)
    record["raw_scores"].append(alert.raw_score)
    record["severity"] = guardrails.most_urgent(record["severity"], alert.normalized_severity)
    record["sla"] = guardrails.sla_label(record["severity"], record["routing"]["tier"])
    for reason in result["human_reasons"]:
        if reason not in record["human_reasons"]:
            record["human_reasons"].append(reason)
    for flag in alert.flags:
        if flag not in record["flags"]:
            record["flags"].append(flag)
    record["needs_human"] = bool(record["human_reasons"])
    record["trace"].append(result["trace"])


def main(alerts_path: Path, only_alert_ids: list[str]) -> None:
    store.load_store(DATA / "historical_tickets.json")
    records = {}
    invalid = []
    alerts = []

    for raw in load_alerts(alerts_path):
        try:
            alert = normalize(raw)
        except InvalidAlert as reason:
            invalid.append({"action": "manual_review", "needs_human": True,
                            "human_reasons": ["INVALID_INPUT"], "problem": str(reason), "raw_alert": raw})
            raw_id = raw.get("scan_id") or raw.get("finding_id") or "(no id)"
            print(f"{raw_id}: INVALID_INPUT  {reason}")
            continue
        tools.ALERTS[alert.alert_id] = alert
        if not only_alert_ids or alert.alert_id in only_alert_ids:
            alerts.append(alert)

    for alert in alerts:  # one at a time, in file order
        result = triage(alert)
        add_to_records(records, alert, result)
        print(f"{alert.alert_id}: {result['action']} -> {result['ticket_id']}  {result['human_reasons']}")

    output = output_path(alerts_path)
    output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(list(records.values()) + invalid, indent=2))
    print(f"\n{len(alerts)} alerts -> {len(records)} tickets, {len(invalid)} invalid. Written to {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Triage security alerts into tickets.")
    parser.add_argument("alert_ids", nargs="*", help="only run these alert ids (default: all)")
    parser.add_argument("--alerts", type=Path, default=DEFAULT_ALERTS, help="alerts file (default: data/alerts.json)")
    args = parser.parse_args()
    main(args.alerts, args.alert_ids)
