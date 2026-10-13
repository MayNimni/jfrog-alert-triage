"""Normalization checks. Expected values were worked out by hand from policy §1."""

import pytest

from normalize import InvalidAlert, normalize


def test_xray_severity_and_time():
    raw = {
        "source": "xray-scan", "scan_id": "xr-1", "repo": "checkout-api",
        "component": "lib:1.0", "cve": "CVE-1", "cvss_score": 7.5,
        "detected_at": "2026-09-18T14:32:00Z",
    }
    alert = normalize(raw)
    assert alert.normalized_severity == "Sev-1"  # 7.5 is in the 7.0-8.9 band
    assert alert.detected_at == "2026-09-18T14:32:00Z"
    assert alert.flags == []


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
