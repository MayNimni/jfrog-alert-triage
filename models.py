"""Data shapes shared by every step of the pipeline."""

from typing import Literal

from pydantic import BaseModel

Severity = Literal["Sev-0", "Sev-1", "Sev-2", "Sev-3"]
Source = Literal["xray-scan", "code-scan", "cloud-posture"]


class NormalizedAlert(BaseModel):
    """One alert from any scanner, in one common shape."""

    alert_id: str
    source: Source
    repo: str

    # How bad it is, and why (policy §1)
    normalized_severity: Severity
    severity_reason: str  # e.g. "cvss 7.5 >= 7.0 -> Sev-1 (policy §1)"
    raw_score: str  # what the scanner said, e.g. "cvss 7.5"

    # When it was found
    detected_at: str  # ISO UTC, e.g. "2026-09-19T09:15:00Z"
    raw_time: str  # the original value, kept for review

    # Data-quality notes that don't stop processing, e.g. "TIMESTAMP_SUSPECT"
    flags: list[str] = []

    # Free text from the scanner. A claim, not a fact.
    note: str | None = None

    # Extra context from Xray, passed to the agent as facts
    package_type: str | None = None  # e.g. "maven", "npm"
    fix_available: bool | None = None  # a fixed version exists. It does not mean the fix is deployed.

    # Identity fields, used later to match existing tickets
    finding_key: str  # display only: a readable summary of the fields below
    component: str | None = None  # xray
    cve: str | None = None  # xray
    rule: str | None = None  # code-scan
    file: str | None = None  # code-scan
    resource_arn: str | None = None  # cloud-posture
    finding_type: str | None = None  # cloud-posture


class AgentDecision(BaseModel):
    """The only thing the model returns. There is no team field: routing is done by code."""

    action: Literal["create", "link", "reopen", "manual_review"]
    linked_ticket_id: str | None = None  # required for link and reopen
    judgment_reasons: list[Literal["AMBIGUOUS_DUPLICATE", "UNVERIFIED_MITIGATION", "RECURRENCE"]] = []
    recommended_priority: Severity | None = None  # only if it differs from the normalized severity
    priority_reason: str | None = None  # required when recommended_priority is set
    summary: str  # what is wrong
    why: str  # why this action
