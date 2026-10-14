"""Turn the results files into one HTML page: a ticket queue you can click through.

Usage:
    python report.py    # reads output/*results.json, writes output/report.html

main.py also calls write_report() at the end of every run.
"""

import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
RUNS = [  # (tab label, results file)
    ("Sample alerts", "results.json"),
    ("Bad input test", "bad_alerts_results.json"),
]


def write_report() -> Path:
    runs = []
    for label, filename in RUNS:
        path = OUTPUT_DIR / filename
        if path.exists():
            runs.append({"label": label, "file": filename, "records": json.loads(path.read_text())})
    # "</" inside a <script> block would end it early, so escape it.
    data = json.dumps(runs).replace("</", "<\\/")
    report = OUTPUT_DIR / "report.html"
    report.write_text(TEMPLATE.replace("__DATA__", data))
    return report


TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alert Triage Results</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
/* Layout: one bright, light-only column; a pale sky band holds the title and run switch, white list below. */
:root {
  --bg: #ffffff; --band: #eef5ff; --panel: #ffffff; --text: #18233a; --muted: #5d6b82; --faint: #8d99ad;
  --line: #e3e9f2; --line-soft: #eef2f7; --accent: #2563eb; --accent-soft: #e3edff;
  --row-hover: #f6f9ff; --code-bg: #f2f6fc;
  --sev0: #d62d2d; --sev0-bg: #ffeaea; --sev1: #e26a00; --sev1-bg: #fff1e0;
  --sev2: #b58a00; --sev2-bg: #fff8d6; --sev3: #5d6b82; --sev3-bg: #edf1f6;
  --human: #c25e00; --human-bg: #fff3e3; --auto: #13895b; --auto-bg: #e2f7ec;
  --sans: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
  color-scheme: light;
}
* { box-sizing: border-box; }
body { margin: 0; color: var(--text);
  background: linear-gradient(var(--band) 0 236px, var(--bg) 236px);
  font: 400 14px/1.6 var(--sans); -webkit-font-smoothing: antialiased; }
main { max-width: 1120px; margin: 0 auto; padding: 40px 16px 64px; }
h1 { font-size: 20px; font-weight: 600; letter-spacing: -.01em; margin: 0 0 4px; text-wrap: balance; }
.sub { color: var(--muted); margin: 0 0 28px; }

.tabs { display: inline-flex; gap: 2px; padding: 3px; margin-bottom: 24px;
  background: #dce8fb; border-radius: 10px; flex-wrap: wrap; }
.tabs button.chip { border: 0; background: transparent; color: var(--muted); padding: 5px 14px; border-radius: 8px; }
.tabs button.chip.on { background: var(--panel); color: var(--text); box-shadow: 0 1px 2px rgba(20, 30, 50, .08); }
.filters { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 14px; }
button.chip { border: 1px solid var(--line); background: transparent; color: var(--muted);
  padding: 4px 12px; border-radius: 999px; cursor: pointer; font: 500 13px/1.5 var(--sans);
  transition: background .15s, color .15s, border-color .15s; }
button.chip:hover { color: var(--text); }
.filters button.chip.on { background: var(--accent-soft); border-color: transparent; color: var(--accent); }
button.chip:focus-visible, .row:focus-visible, summary:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; margin: 0 0 28px; }
.stat { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px;
  box-shadow: 0 1px 3px rgba(37, 99, 235, .06); }
.stat b { display: block; font-size: 22px; font-weight: 500; font-variant-numeric: tabular-nums; }
.stat span { color: var(--muted); font-size: 12.5px; }

.table { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; overflow: hidden;
  box-shadow: 0 4px 16px rgba(37, 99, 235, .05); }
.row { display: grid; grid-template-columns: 110px 72px minmax(0, 1fr) 220px 112px; gap: 16px; align-items: center;
  padding: 13px 18px; border-top: 1px solid var(--line-soft); cursor: pointer; transition: background .12s; }
.row.head { cursor: default; border-top: 0; color: var(--faint); background: #f8fafd; font-size: 11.5px; font-weight: 500;
  text-transform: uppercase; letter-spacing: .06em; padding-block: 11px; }
.row:not(.head):hover { background: var(--row-hover); }
.row > div { min-width: 0; overflow-wrap: anywhere; }
.row .id { font: 500 12.5px/1.4 var(--mono); color: var(--muted); }
.row .prod { font-size: 13px; line-height: 1.45; }

.badge { display: inline-flex; align-items: center; gap: 6px; padding: 1px 9px; border-radius: 999px;
  font-size: 12px; font-weight: 500; white-space: nowrap; }
.badge::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: .8; }
.Sev-0 { color: var(--sev0); background: var(--sev0-bg); } .Sev-1 { color: var(--sev1); background: var(--sev1-bg); }
.Sev-2 { color: var(--sev2); background: var(--sev2-bg); } .Sev-3 { color: var(--sev3); background: var(--sev3-bg); }
.human { color: var(--human); background: var(--human-bg); } .auto { color: var(--auto); background: var(--auto-bg); }
.muted { color: var(--muted); }

.detail { padding: 6px 18px 24px 144px; background: var(--row-hover); border-top: 1px solid var(--line-soft); }
.detail h3 { font-size: 11.5px; font-weight: 500; color: var(--faint); text-transform: uppercase; letter-spacing: .06em; margin: 20px 0 6px; }
.detail p { margin: 0; max-width: 72ch; }
.reasons { margin: 0; padding-left: 18px; }
.reasons li { margin-bottom: 4px; }
.kv { display: grid; grid-template-columns: 120px minmax(0, 1fr); gap: 6px 16px; }
.kv div:nth-child(odd) { color: var(--muted); }
code, pre { font-family: var(--mono); font-size: 12px; }
code { background: var(--code-bg); padding: 1px 5px; border-radius: 4px; }
pre code, pre { background: var(--code-bg); }
pre { border: 1px solid var(--line-soft); border-radius: 8px; padding: 12px; overflow-x: auto; margin: 8px 0 0; }
details { padding: 4px 0; }
details summary { cursor: pointer; color: var(--accent); }
@media (max-width: 760px) {
  .row { grid-template-columns: minmax(0, 1fr) auto; }
  .row .prod, .row .sla { display: none; }
  .row.head { display: none; }
  .detail { padding-left: 18px; }
  .kv { grid-template-columns: 1fr; gap: 2px; }
  .kv div:nth-child(even) { margin-bottom: 8px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<main>
  <h1>Alert Triage Results</h1>
  <p class="sub">Each row is one ticket. Click a row to see why the agent decided what it did.</p>
  <div class="tabs" id="tabs"></div>
  <div class="stats" id="stats"></div>
  <div class="filters" id="filters"></div>
  <div class="table" id="table"></div>
</main>
<script>
const RUNS = __DATA__;

const REASONS = {
  CO_OWNED: "Service has more than one owning team. All are notified, none is picked.",
  NOT_IN_CATALOG: "Service isn't in the catalog. Routed to the security lead.",
  AMBIGUOUS_DUPLICATE: "Only a partial match to an existing ticket. A human confirms it's the same finding.",
  RECURRENCE: "Matches a resolved ticket, which was reopened.",
  UNVERIFIED_MITIGATION: "A note claims a fix, but nothing verifies it.",
  PRIORITY_DOWNGRADE: "The model recommends a lower priority. A human approves; the SLA stays.",
  ARN_UNPARSEABLE: "Malformed resource ID, so the duplicate check was skipped.",
  LLM_ERROR: "The model failed, or its answer failed a guardrail check.",
  AGENT_UNSURE: "The model asked for review without a reason.",
  INVALID_INPUT: "The alert can't be normalized. No LLM call was made.",
};
const SEV_ORDER = { "Sev-0": 0, "Sev-1": 1, "Sev-2": 2, "Sev-3": 3 };

let runIndex = 0, filter = "all", openId = null;

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const isInvalid = r => r.human_reasons && r.human_reasons.includes("INVALID_INPUT");
const rowId = (r, i) => r.ticket_id || "invalid-" + i;
const rawId = r => (r.raw_alert && (r.raw_alert.scan_id || r.raw_alert.finding_id)) || "(no id)";

function sorted(records) {
  return records.map((r, i) => ({ r, id: rowId(r, i) })).sort((a, b) =>
    isInvalid(a.r) - isInvalid(b.r) || b.r.needs_human - a.r.needs_human ||
    (SEV_ORDER[a.r.severity] ?? 9) - (SEV_ORDER[b.r.severity] ?? 9));
}

function render() {
  const run = RUNS[runIndex];
  document.getElementById("tabs").innerHTML = RUNS.map((x, i) =>
    `<button class="chip ${i === runIndex ? "on" : ""}" data-run="${i}">${esc(x.label)}</button>`).join("");

  const tickets = run.records.filter(r => !isInvalid(r));
  const invalid = run.records.filter(isInvalid);
  const alerts = tickets.reduce((n, r) => n + r.alert_ids.length, 0) + invalid.length;
  const human = tickets.filter(r => r.needs_human).length;
  document.getElementById("stats").innerHTML = [
    [alerts, "alerts in"], [tickets.length, "tickets out"], [human, "need a human"],
    [tickets.length - human, "fully automatic"], [invalid.length, "invalid input"],
  ].filter(([n, label]) => n || label !== "invalid input").map(([n, label]) => `<div class="stat"><b>${n}</b><span>${label}</span></div>`).join("");

  const filters = [["all", "All"], ["human", "Needs human"], ["auto", "Automatic"]];
  if (invalid.length) filters.push(["invalid", "Invalid input"]);
  document.getElementById("filters").innerHTML = filters.map(([key, label]) =>
    `<button class="chip ${key === filter ? "on" : ""}" data-filter="${key}">${label}</button>`).join("");

  const shown = sorted(run.records).filter(({ r }) =>
    filter === "all" || (filter === "invalid" ? isInvalid(r) :
      !isInvalid(r) && (filter === "human" ? r.needs_human : !r.needs_human)));

  let html = `<div class="row head"><div>Ticket</div><div>Sev</div><div>Summary</div><div class="prod">In production</div><div>Status</div></div>`;
  for (const { r, id } of shown) {
    html += isInvalid(r) ? invalidRow(r, id) : ticketRow(r, id);
    if (id === openId) html += isInvalid(r) ? invalidDetail(r) : ticketDetail(r);
  }
  if (!shown.length) html += `<div class="row"><div class="muted">Nothing here.</div></div>`;
  document.getElementById("table").innerHTML = html;
}

// Short form of production() for the table: the Jira action, then who it's routed to.
function productionCell(r) {
  const jira = {
    create: "New Jira ticket",
    link: `Comment on ${r.ticket_id}`,
    reopen: `Reopen ${r.ticket_id}`,
    manual_review: "Manual review queue",
  }[r.action] || r.action;
  const to = !r.routing.teams.length ? "security lead"
    : r.routing.mode === "auto" ? r.routing.teams.join(", ")
    : r.routing.teams.join(" + ") + ", human picks owner";
  return `${esc(jira)}<br><span class="muted">→ ${esc(to)}</span>`;
}

function ticketRow(r, id) {
  const status = r.needs_human ? `<span class="badge human">needs human</span>` : `<span class="badge auto">automatic</span>`;
  return `<div class="row" data-id="${esc(id)}">
    <div class="id">${esc(r.ticket_id)}</div>
    <div><span class="badge ${esc(r.severity)}">${esc(r.severity)}</span></div>
    <div>${esc(r.summary || "(no summary)")}</div>
    <div class="prod">${productionCell(r)}</div>
    <div>${status}</div></div>`;
}

function invalidRow(r, id) {
  return `<div class="row" data-id="${esc(id)}">
    <div class="id">${esc(rawId(r))}</div><div>—</div>
    <div>${esc(r.problem)}</div><div class="prod">Manual review queue<br><span class="muted">→ no ticket</span></div>
    <div><span class="badge human">invalid input</span></div></div>`;
}

function ticketDetail(r) {
  const reasons = r.human_reasons.length
    ? `<ul class="reasons">${r.human_reasons.map(x => `<li><code>${esc(x)}</code> ${esc(REASONS[x] || "")}</li>`).join("")}</ul>`
    : `<p class="muted">None. Filed automatically.</p>`;
  const rec = r.recommended_priority
    ? `<div>Recommended</div><div><span class="badge ${esc(r.recommended_priority)}">${esc(r.recommended_priority)}</span> ${esc(r.priority_reason)}</div>` : "";
  const traces = r.trace.map(t => `<details><summary>${esc(t.alert_id)}: ${esc(t.action)}</summary>
    <p><b>Why:</b> ${esc(t.why || "")}</p>
    ${t.problems.length ? `<p><b>Guardrail problems:</b> ${esc(t.problems.join("; "))}</p>` : ""}
    <pre>${esc(JSON.stringify(t.tool_calls, null, 2))}</pre></details>`).join("");
  return `<div class="detail">
    <h3>What's wrong</h3><p>${esc(r.summary || "(no summary)")}</p>
    <h3>Needs a human because</h3>${reasons}
    <h3>Ticket</h3><div class="kv">
      <div>Action</div><div><code>${esc(r.action)}</code></div>
      <div>Alerts</div><div>${r.alert_ids.map((a, i) => `<code>${esc(a)}</code> <span class="muted">(${esc(r.raw_scores[i])})</span>`).join(", ")}</div>
      <div>Severity</div><div><span class="badge ${esc(r.severity)}">${esc(r.severity)}</span></div>
      ${rec}
      <div>SLA</div><div>${esc(r.sla)}</div>
      <div>Teams</div><div>${esc(r.routing.teams.join(", ") || "none (not in catalog)")}</div>
      <div>Slack</div><div>${esc(r.routing.slack.join(", ") || "—")}</div>
      <div>On-call</div><div>${esc(r.routing.on_call.join(", ") || "—")}</div>
      <div>Tier</div><div>${esc(r.routing.tier || "unknown")}</div>
      ${r.flags.length ? `<div>Data flags</div><div>${r.flags.map(f => `<code>${esc(f)}</code>`).join(" ")}</div>` : ""}
    </div>
    <h3>In production <span class="muted">(not built: the planned mapping)</span></h3>${production(r)}
    <h3>Agent trace (tool calls and results)</h3>${traces}</div>`;
}

function production(r) {
  const jira = {
    create: `Create a new ticket`,
    link: `Add the alert to <code>${esc(r.ticket_id)}</code> as a comment, no new ticket`,
    reopen: `Reopen <code>${esc(r.ticket_id)}</code> and add the alert`,
    manual_review: `No ticket yet. Goes to the manual review queue`,
  }[r.action] || esc(r.action);
  const assignee = r.routing.mode === "auto" ? r.routing.teams.join(", ") : "unassigned until a human routes it";
  const slack = r.routing.slack.length ? r.routing.slack.join(", ") : "security lead (no team channel)";
  const labels = r.human_reasons.length ? r.human_reasons.concat("needs-human").join(", ") : "none";
  return `<div class="kv">
    <div>Jira</div><div>${jira}</div>
    <div>Jira fields</div><div>Priority ${esc(r.severity)} · due in ${esc(r.sla)} · assignee: ${esc(assignee)} · labels: ${esc(labels)}</div>
    <div>Slack</div><div>Post the summary to ${esc(slack)}</div>
    <div>On-call</div><div>${esc(r.routing.on_call.join(", ") || "no rotation listed")}</div>
  </div>`;
}

function invalidDetail(r) {
  return `<div class="detail"><h3>Rejected because</h3><p>${esc(r.problem)}</p>
    <h3>In production <span class="muted">(not built: the planned mapping)</span></h3>
    <p>No ticket. Goes to the manual review queue with the reason above.</p>
    <h3>Raw alert</h3><pre>${esc(JSON.stringify(r.raw_alert, null, 2))}</pre></div>`;
}

document.addEventListener("click", e => {
  const run = e.target.closest("[data-run]"), f = e.target.closest("[data-filter]"), row = e.target.closest(".row[data-id]");
  if (run) { runIndex = +run.dataset.run; filter = "all"; openId = null; }
  else if (f) { filter = f.dataset.filter; }
  else if (row) { openId = openId === row.dataset.id ? null : row.dataset.id; }
  else return;
  render();
});

if (RUNS.length) render();
else document.getElementById("table").innerHTML = '<div class="row"><div>No results yet. Run python main.py first.</div></div>';
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print(f"Written to {write_report()}")
