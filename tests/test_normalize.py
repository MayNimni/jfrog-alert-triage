"""Normalization checks. Expected values were worked out by hand from policy §1."""

from pathlib import Path

import pytest

from normalize import InvalidAlert, load_alerts, normalize


def test_xray_severity_time_and_fix_context():
    raw = {
        "source": "xray-scan", "scan_id": "xr-1", "repo": "checkout-api",
        "package_type": "maven", "component": "lib:1.0", "cve": "CVE-1", "cvss_score": 7.5,
        "fix_available": True, "detected_at": "2026-09-18T14:32:00Z",
    }
    alert = normalize(raw)
    assert alert.normalized_severity == "Sev-1"  # 7.5 is in the 7.0-8.9 band
    assert alert.detected_at == "2026-09-18T14:32:00Z"
    assert alert.flags == []
    assert (alert.package_type, alert.fix_available) == ("maven", True)


def test_code_scan_2025_epoch_is_flagged_suspect():
    raw = {
        "source": "code-scan", "finding_id": "cs-1", "repo": "billing-worker",
        "rule": "hardcoded-secret", "file": "a.py", "severity_label": "Critical",
        "reported_ts": 1758294600,  # 2025-09-19, a year before the feed
    }
    alert = normalize(raw)
    assert alert.normalized_severity == "Sev-0"
    assert alert.detected_at == "2025-09-19T15:10:00Z"
    assert "TIMESTAMP_SUSPECT" in alert.flags


def test_unknown_source_is_invalid_input():
    with pytest.raises(InvalidAlert, match="unknown source"):
        normalize({"source": "snyk", "id": "s-1"})


# --- Bad-input fixtures (data/bad_alerts.json) ---

BAD_ALERTS = load_alerts(Path(__file__).parent.parent / "data" / "bad_alerts.json")


def bad_alert(fixture_id):
    for raw in BAD_ALERTS:
        if fixture_id in (raw.get("scan_id"), raw.get("finding_id")):
            return raw


@pytest.mark.parametrize("fixture_id, problem", [
    ("bad-unknown-source", "unknown source 'xscan'"),
    ("bad-xray-no-scan-id", "missing field 'scan_id'"),
    ("bad-missing-repo", "missing field 'repo'"),
    ("bad-cvss-150", "cvss score 150 is not a number between 0 and 10"),
    ("bad-label-urgent", "unknown severity label 'Urgent'"),
    ("bad-missing-time", "missing field 'first_seen'"),
])
def test_every_bad_fixture_is_rejected_with_a_clear_reason(fixture_id, problem):
    with pytest.raises(InvalidAlert) as rejected:
        normalize(bad_alert(fixture_id))
    assert str(rejected.value) == problem
