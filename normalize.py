"""Turn raw alerts from three scanners into one NormalizedAlert shape."""

import json
from datetime import datetime, timezone
from pathlib import Path

from models import NormalizedAlert

# Policy §1 severity tables, highest first.
CVSS_THRESHOLDS = [(9.0, "Sev-0"), (7.0, "Sev-1"), (4.0, "Sev-2"), (0.0, "Sev-3")]
RISK_THRESHOLDS = [(85, "Sev-0"), (60, "Sev-1"), (30, "Sev-2"), (0, "Sev-3")]
LABEL_TO_SEVERITY = {"Critical": "Sev-0", "High": "Sev-1", "Medium": "Sev-2", "Low": "Sev-3"}

# A time this far before the feed was captured is probably wrong (README assumption 1).
FEED_CAPTURED_AT = datetime(2026, 9, 20, tzinfo=timezone.utc)
SUSPECT_AFTER_DAYS = 90


class InvalidAlert(Exception):
    """The alert can't be normalized. It goes to a human as INVALID_INPUT."""


def load_alerts(path: Path) -> list[dict]:
    with open(path) as f:
        return json.load(f)["alerts"]


# --- Severity ---

def severity_from_score(score: float, thresholds: list, scale: str, max_score: float) -> tuple[str, str]:
    """Return (severity, reason). Checks the highest threshold first, so no value falls in a gap."""
    if not isinstance(score, (int, float)) or not 0 <= score <= max_score:
        raise InvalidAlert(f"{scale} score {score!r} is not a number between 0 and {max_score}")
    for minimum, severity in thresholds:
        if score >= minimum:
            return severity, f"{scale} {score} >= {minimum} -> {severity} (policy §1)"


def severity_from_label(label: str) -> tuple[str, str]:
    if label not in LABEL_TO_SEVERITY:
        raise InvalidAlert(f"unknown severity label {label!r}")
    severity = LABEL_TO_SEVERITY[label]
    return severity, f"label {label} -> {severity} (policy §1)"


# --- Time ---

def to_iso_utc(moment: datetime) -> str:
    """One format for every scanner: 2026-09-19T09:15:00Z."""
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_suspect_time(detected_at: str) -> bool:
    age = FEED_CAPTURED_AT - datetime.fromisoformat(detected_at)
    return age.days > SUSPECT_AFTER_DAYS


# --- One adapter per scanner ---

def normalize_xray(raw: dict) -> NormalizedAlert:
    severity, reason = severity_from_score(raw["cvss_score"], CVSS_THRESHOLDS, "cvss", 10)
    return NormalizedAlert(
        alert_id=raw["scan_id"],
        source="xray-scan",
        repo=raw["repo"],
        normalized_severity=severity,
        severity_reason=reason,
        raw_score=f"cvss {raw['cvss_score']}",
        detected_at=to_iso_utc(datetime.fromisoformat(raw["detected_at"])),
        raw_time=raw["detected_at"],
        note=raw.get("mitigation_note"),
        package_type=raw.get("package_type"),  # optional: useful context, not needed to triage
        fix_available=raw.get("fix_available"),
        finding_key=f"{raw['repo']} | {raw['component']} | {raw['cve']}",
        component=raw["component"],
        cve=raw["cve"],
    )


def normalize_code_scan(raw: dict) -> NormalizedAlert:
    severity, reason = severity_from_label(raw["severity_label"])
    return NormalizedAlert(
        alert_id=raw["finding_id"],
        source="code-scan",
        repo=raw["repo"],
        normalized_severity=severity,
        severity_reason=reason,
        raw_score=f"label {raw['severity_label']}",
        detected_at=to_iso_utc(datetime.fromtimestamp(raw["reported_ts"], timezone.utc)),
        raw_time=str(raw["reported_ts"]),
        finding_key=f"{raw['repo']} | {raw['rule']} | {raw['file']}",
        rule=raw["rule"],
        file=raw["file"],
    )


def normalize_cloud(raw: dict) -> NormalizedAlert:
    severity, reason = severity_from_score(raw["risk_score"], RISK_THRESHOLDS, "risk", 100)
    # No time zone in the data, so we read it as UTC (README assumption 3).
    seen = datetime.strptime(raw["first_seen"], "%d/%m/%Y %H:%M").replace(tzinfo=timezone.utc)
    # A real ARN has at least 5 ":"-separated parts. Otherwise we keep it but flag it.
    flags = ["ARN_UNPARSEABLE"] if len(raw["resource_arn"].split(":")) < 5 else []
    return NormalizedAlert(
        alert_id=raw["finding_id"],
        source="cloud-posture",
        repo=raw["repo"],
        normalized_severity=severity,
        severity_reason=reason,
        raw_score=f"risk {raw['risk_score']}",
        detected_at=to_iso_utc(seen),
        raw_time=raw["first_seen"],
        flags=flags,
        finding_key=f"{raw['resource_arn']} | {raw['finding_type']}",
        resource_arn=raw["resource_arn"],
        finding_type=raw["finding_type"],
    )


# --- Entry point ---

def normalize(raw: dict) -> NormalizedAlert:
    """Pick the adapter by source. Any bad input raises InvalidAlert, never a crash."""
    source = raw.get("source")
    try:
        if source == "xray-scan":
            alert = normalize_xray(raw)
        elif source == "code-scan":
            alert = normalize_code_scan(raw)
        elif source == "cloud-posture":
            alert = normalize_cloud(raw)
        else:
            raise InvalidAlert(f"unknown source {source!r}")
    except KeyError as missing:
        raise InvalidAlert(f"missing field {missing}")
    except (ValueError, TypeError, AttributeError) as bad:
        raise InvalidAlert(f"bad value: {bad}")

    if is_suspect_time(alert.detected_at):
        alert.flags.append("TIMESTAMP_SUSPECT")
    return alert


if __name__ == "__main__":
    raw_alerts = load_alerts(Path(__file__).parent / "data" / "alerts.json")
    shown_sources = set()
    normalized_count = 0
    for raw in raw_alerts:
        try:
            alert = normalize(raw)
        except InvalidAlert as reason:
            print(f"INVALID_INPUT: {reason}")
            continue
        normalized_count += 1
        if alert.source not in shown_sources:
            shown_sources.add(alert.source)
            print(alert.model_dump_json(indent=2, exclude_none=True))
    print(f"{normalized_count}/{len(raw_alerts)} normalized")
