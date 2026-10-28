"""Turn the results files into one HTML page: a ticket queue you can click through.

Usage:
    python report.py    # reads output/*results.json, writes output/report.html

main.py also calls write_report() at the end of every run.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"
DATA_DIR = Path(__file__).parent / "data"
META_FILE = OUTPUT_DIR / "run_meta.json"  # model + time of the last run, written by main.py
RUNS = [  # (tab label, results file, alerts file, one-line description)
    ("Sample alerts", "results.json", "alerts.json", "The 24 alerts from the exercise, in file order."),
    ("Bad & adversarial input", "bad_alerts_results.json", "bad_alerts.json",
     "Malformed alerts the normalizer must reject, plus one valid alert whose note tries to give the agent orders."),
]


def scanner_notes(alerts_file: str) -> dict:
    """alert id -> the free-text note the scanner attached, so the report can show it next to the agent's answer."""
    path = DATA_DIR / alerts_file
    if not path.exists():
        return {}
    notes = {}
    for raw in json.loads(path.read_text()).get("alerts", []):
        note = raw.get("mitigation_note") or raw.get("note")
        alert_id = raw.get("scan_id") or raw.get("finding_id")
        if note and alert_id:
            notes[alert_id] = note
    return notes


def save_meta(model: str) -> None:
    """Called by main.py so the report can say which model made the decisions and when."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    META_FILE.write_text(json.dumps({
        "model": model,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }, indent=2))


def write_report() -> Path:
    runs = []
    for label, filename, alerts_file, about in RUNS:
        path = OUTPUT_DIR / filename
        if path.exists():
            runs.append({"label": label, "file": filename, "about": about,
                         "notes": scanner_notes(alerts_file), "records": json.loads(path.read_text())})
    meta = json.loads(META_FILE.read_text()) if META_FILE.exists() else {}
    # "</" inside a <script> block would end it early, so escape it.
    data = json.dumps({"runs": runs, "meta": meta}).replace("</", "<\\/")
    report = OUTPUT_DIR / "report.html"
    report.write_text(TEMPLATE.replace("__DATA__", data))
    return report


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Alert Triage</title>
<meta name="description" content="The ticket queue built by the alert triage agent: every decision, why it was made, and the tool calls behind it.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root {
  --bg: #f6f8fd; --side-bg: #eef5ff; --panel: #ffffff; --ink: #18233a; --muted: #5d6b82; --faint: #8d99ad; --line: #e3e9f2; --hair: #eef2f7; --hover: #f6f9ff;
  --accent: #2563eb; --accent-bg: #e3edff; --shadow: 0 1px 3px rgba(37, 99, 235, .06);
  --sev0: #d62d2d; --sev0-bg: #ffeaea; --sev1: #e26a00; --sev1-bg: #fff1e0; --sev2: #b58a00; --sev2-bg: #fff8d6; --sev3: #5d6b82; --sev3-bg: #edf1f6;
  --review: #c25e00; --review-bg: #fff3e3; --auto: #13895b; --auto-bg: #e2f7ec; --rej: #5d6b82; --rej-bg: #edf1f6;
  --sans: "IBM Plex Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; --mono: "IBM Plex Mono", ui-monospace, Menlo, monospace;
  --side: 224px; --drawer: 600px;
  color-scheme: light;
}
* { box-sizing: border-box; }
html, body { height: 100%; }
body { margin: 0; background: var(--bg); color: var(--ink); font: 400 14px/1.55 var(--sans); -webkit-font-smoothing: antialiased; }
a { color: var(--accent); text-decoration: none; } a:hover { text-decoration: underline; }
button { font: inherit; color: inherit; cursor: pointer; background: none; border: 0; padding: 0; }
code, pre, .mono { font-family: var(--mono); font-size: 12px; }
code { background: var(--hair); padding: 1px 5px; border-radius: 4px; }
pre { background: var(--hair); border-radius: 6px; padding: 12px; overflow-x: auto; margin: 8px 0 0; line-height: 1.5; font-size: 11.5px; }
:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.muted { color: var(--muted); } .faint { color: var(--faint); }

/* Shell */
.app { display: grid; grid-template-columns: var(--side) minmax(0, 1fr); min-height: 100vh; }
.side { background: var(--side-bg); border-right: 1px solid #dce6f7; padding: 18px 14px; display: flex; flex-direction: column; gap: 22px; position: sticky; top: 0; height: 100vh; }
.brand { display: flex; align-items: center; gap: 10px; padding: 4px 8px; font-weight: 600; font-size: 14px; }
.brand i { width: 22px; height: 22px; border-radius: 6px; background: var(--accent); display: grid; place-items: center; color: #fff; font: 600 11px/1 var(--mono); }
.brand span { color: var(--muted); font-weight: 400; font-size: 12px; display: block; }
.nav { display: flex; flex-direction: column; gap: 2px; }
.nav .h { font-size: 11px; font-weight: 500; color: var(--faint); text-transform: uppercase; letter-spacing: .06em; padding: 10px 8px 4px; }
.nav button { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; text-align: left; padding: 7px 8px; border-radius: 6px; color: var(--muted); font-weight: 500; }
.nav button:hover { background: rgba(255,255,255,.7); color: var(--ink); }
.nav button.on { background: var(--panel); color: var(--accent); box-shadow: 0 1px 2px rgba(20, 30, 50, .08); }
.nav button .cnt { font-size: 11.5px; color: var(--faint); font-variant-numeric: tabular-nums; }
.nav button.on .cnt { color: var(--accent); }
.side-meta { margin-top: auto; font-size: 12px; color: var(--muted); padding: 0 8px; display: grid; gap: 4px; }
.side-meta b { color: var(--ink); font-weight: 500; }

.main { min-width: 0; }
.topbar { display: flex; align-items: center; justify-content: space-between; gap: 16px; padding: 18px 28px 0; }
.topbar h1 { font-size: 20px; font-weight: 600; margin: 0; letter-spacing: -.01em; }
.topbar p { margin: 2px 0 0; color: var(--muted); }
.content { padding: 20px 28px 48px; display: grid; gap: 16px; }

/* Cards */
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; box-shadow: var(--shadow); }
.card .ch { padding: 14px 18px 0; display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
.card .ch h2 { font-size: 13.5px; font-weight: 600; margin: 0; }
.card .ch p { margin: 0; color: var(--muted); font-size: 12.5px; }
.card .cb { padding: 14px 18px 18px; }
.kpis { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 16px; }
.kpi { padding: 14px 18px; display: flex; flex-direction: column; gap: 2px; text-align: left; }
.kpi:is(button):hover { border-color: #c9c9ce; }
.kpi .l { color: var(--muted); font-size: 12.5px; font-weight: 500; }
.kpi .v { font-size: 26px; font-weight: 500; letter-spacing: -.02em; line-height: 1.2; font-variant-numeric: tabular-nums; }
.kpi .v small { font-size: 13px; font-weight: 400; color: var(--muted); margin-left: 4px; }
.kpi .s { color: var(--muted); font-size: 12px; margin-top: 4px; }
.two { display: grid; grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr); gap: 16px; align-items: start; }

/* Pipeline */
.pipe { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 0; position: relative; }
.pipe::before { content: ""; position: absolute; left: 10%; right: 10%; top: 13px; height: 1px; background: var(--line); }
.step { padding: 0 12px; position: relative; text-align: center; }
.step .dot { width: 26px; height: 26px; border-radius: 50%; margin: 0 auto 10px; display: grid; place-items: center; font: 500 11px/1 var(--mono); background: var(--panel); border: 1px solid var(--line); color: var(--muted); position: relative; }
.step.model .dot { background: var(--accent); color: #fff; border-color: var(--accent); }
.step b { display: block; font-weight: 600; font-size: 13px; }
.step em { display: block; font-style: normal; font-size: 11px; color: var(--faint); margin-bottom: 4px; text-transform: uppercase; letter-spacing: .05em; }
.step.model em { color: var(--accent); }
.step span { display: block; color: var(--muted); font-size: 12px; line-height: 1.45; }

/* Reasons */
.rlist { display: grid; gap: 0; }
.rrow { display: grid; grid-template-columns: 200px 36px minmax(0, 1fr); gap: 12px; align-items: baseline; padding: 9px 0; border-top: 1px solid var(--hair); text-align: left; width: 100%; }
.rrow:first-child { border-top: 0; padding-top: 0; }
.rrow:hover code { color: var(--accent); }
.rrow .n { font-weight: 600; font-variant-numeric: tabular-nums; text-align: right; }
.rrow .w { color: var(--muted); font-size: 12.5px; }
.cases { display: grid; gap: 0; }
.case { display: grid; grid-template-columns: 110px minmax(0, 1fr); gap: 12px; padding: 10px 0; border-top: 1px solid var(--hair); text-align: left; width: 100%; align-items: start; }
.case:first-child { border-top: 0; padding-top: 0; }
.case:hover .t { color: var(--accent); }
.case .t { font: 500 12.5px/1.5 var(--mono); }
.case .d b { font-weight: 600; display: block; font-size: 13px; }
.case .d span { color: var(--muted); font-size: 12.5px; }

/* Chips */
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 1px 9px; border-radius: 999px; font-size: 12px; font-weight: 500; white-space: nowrap; line-height: 1.7; }
.chip.plain::before { display: none; }
.chip::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; opacity: .8; flex: none; }
.Sev-0 { color: var(--sev0); background: var(--sev0-bg); } .Sev-1 { color: var(--sev1); background: var(--sev1-bg); }
.Sev-2 { color: var(--sev2); background: var(--sev2-bg); } .Sev-3 { color: var(--sev3); background: var(--sev3-bg); }
.review { color: var(--review); background: var(--review-bg); } .autof { color: var(--auto); background: var(--auto-bg); } .rej { color: var(--rej); background: var(--rej-bg); }

/* Toolbar + table */
.toolbar { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; padding: 12px 18px; border-bottom: 1px solid var(--line); }
.toolbar .sep { width: 1px; height: 18px; background: var(--line); margin: 0 6px; }
.f { padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight: 500; color: var(--muted); border: 1px solid var(--line); display: inline-flex; gap: 5px; align-items: center; }
.f:hover { color: var(--ink); }
.f.on { background: var(--accent-bg); color: var(--accent); border-color: transparent; }
.f .cnt { font-size: 11px; opacity: .7; font-variant-numeric: tabular-nums; }
.f.sev.on { background: var(--c-bg); color: var(--c); border-color: transparent; }
select.f { -webkit-appearance: none; appearance: none; background: var(--panel); border-color: var(--line); color: var(--muted); }
.search { margin-left: auto; }
.search input { font: inherit; font-size: 13px; padding: 5px 12px; border: 1px solid var(--line); border-radius: 999px; background: var(--panel); width: 260px; color: var(--ink); }
.search input::placeholder { color: var(--faint); }
.showing { padding: 8px 18px; color: var(--faint); font-size: 12px; border-bottom: 1px solid var(--hair); }
.showing button { color: var(--accent); }
table { width: 100%; border-collapse: collapse; }
th { text-align: left; font-size: 11.5px; font-weight: 500; color: var(--faint); text-transform: uppercase; letter-spacing: .06em; background: #f8fafd; padding: 11px 12px; border-bottom: 1px solid var(--line); white-space: nowrap; }
th:first-child, td:first-child { padding-left: 18px; } th:last-child, td:last-child { padding-right: 18px; }
td { padding: 11px 12px; border-bottom: 1px solid var(--hair); vertical-align: top; }
tr.r { cursor: pointer; } tr.r:hover td { background: var(--hover); } tr.r.on td { background: var(--hover); box-shadow: inset 3px 0 0 var(--accent); }
tr.r.on td:not(:first-child) { box-shadow: none; }
tr:last-child td { border-bottom: 0; }
td .tid { font: 500 12.5px/1.5 var(--mono); }
td:first-child { white-space: nowrap; } td .sla { white-space: nowrap; }
td .sub { color: var(--muted); font-size: 12px; display: flex; gap: 8px; white-space: nowrap; }
td .sub .g { color: var(--accent); }
td .fnd { max-width: 60ch; }
td .repo { color: var(--muted); font-size: 12px; display: block; }
td .act span { display: block; color: var(--muted); font-size: 12px; }
td .sla span { display: block; color: var(--muted); font-size: 12px; }
.empty { padding: 32px 18px; color: var(--muted); text-align: center; }

/* Drawer */
.scrim { position: fixed; inset: 0; background: rgba(24, 24, 27, .25); opacity: 0; pointer-events: none; transition: opacity .15s; z-index: 20; }
.drawer { position: fixed; top: 0; right: 0; bottom: 0; width: min(var(--drawer), 100vw); background: var(--panel); border-left: 1px solid var(--line); transform: translateX(100%); transition: transform .18s ease; z-index: 21; display: flex; flex-direction: column; box-shadow: -8px 0 24px rgba(0,0,0,.06); }
body.open .scrim { opacity: 1; pointer-events: auto; } body.open .drawer { transform: none; }
.dh { padding: 16px 22px 14px; border-bottom: 1px solid var(--line); display: flex; align-items: flex-start; gap: 12px; }
.dh .ids { flex: 1; min-width: 0; }
.dh .tid { font: 600 15px/1.3 var(--mono); }
.dh .chips { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.dh .x { width: 30px; height: 30px; border-radius: 6px; display: grid; place-items: center; color: var(--muted); font-size: 18px; line-height: 1; }
.dh .x:hover { background: var(--hover); color: var(--ink); }
.db { overflow-y: auto; padding: 4px 22px 32px; }
.sec { padding: 16px 0; border-bottom: 1px solid var(--hair); }
.sec:last-child { border-bottom: 0; }
.sec h3 { margin: 0 0 8px; font-size: 11.5px; font-weight: 500; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }
.sec h3 small { text-transform: none; letter-spacing: 0; color: var(--faint); font-weight: 400; margin-left: 6px; }
.sec p { margin: 0; }
.dec { font-size: 14.5px; font-weight: 500; margin-bottom: 4px; }
.dec code { font-size: 13px; }
.why { color: var(--muted); }
.kv { display: grid; grid-template-columns: 96px minmax(0, 1fr); gap: 7px 12px; font-size: 13px; }
.kv > div:nth-child(odd) { color: var(--muted); }
.rs { margin: 0; padding: 0; list-style: none; display: grid; gap: 8px; }
.rs li { display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 10px; align-items: baseline; font-size: 13px; }
.rs li span { color: var(--muted); }
.note { border: 1px solid var(--line); border-left: 3px solid var(--sev1); background: #fffaf3; padding: 8px 12px; border-radius: 6px; margin: 8px 0; font-size: 12.5px; }
.note b { font-weight: 600; }
.note.bad { border-left-color: var(--sev0); background: #fff5f5; }
.note.info { border-left-color: var(--accent); background: #f2f6ff; }
.run { padding: 12px 0; border-top: 1px solid var(--hair); }
.run:first-of-type { border-top: 0; }
.run .rh { display: flex; gap: 10px; align-items: baseline; margin-bottom: 8px; font-size: 12.5px; color: var(--muted); }
.run .rh .mono { color: var(--ink); font-weight: 500; }
.steps { margin: 0; padding: 0; list-style: none; counter-reset: s; display: grid; gap: 6px; }
.steps li { display: grid; grid-template-columns: 20px minmax(0, 1fr); gap: 8px; font-size: 13px; }
.steps li::before { counter-increment: s; content: counter(s); width: 18px; height: 18px; border-radius: 50%; background: var(--hair); color: var(--muted); font: 500 10.5px/18px var(--mono); text-align: center; margin-top: 2px; }
.steps li.final::before { content: "→"; background: var(--accent); color: #fff; }
.steps .call { font: 500 12px/1.6 var(--mono); }
.steps .res { color: var(--muted); display: block; }
.steps .res b { color: var(--ink); font-weight: 500; }
details.raw summary { cursor: pointer; color: var(--accent); font-size: 12px; margin-top: 6px; width: fit-content; }

@media (max-width: 1100px) { .kpis { grid-template-columns: repeat(2, minmax(0, 1fr)); } .two { grid-template-columns: 1fr; } }
@media (max-width: 860px) {
  .app { grid-template-columns: 1fr; }
  .side { position: static; height: auto; flex-direction: row; align-items: center; flex-wrap: wrap; gap: 8px 16px; padding: 12px 16px; border-right: 0; border-bottom: 1px solid var(--line); }
  .nav { flex-direction: row; gap: 4px; } .nav .h { display: none; } .side-meta { display: none; }
  .topbar, .content { padding-left: 16px; padding-right: 16px; }
  .pipe { grid-template-columns: 1fr; gap: 12px; } .pipe::before { display: none; } .step { text-align: left; display: grid; grid-template-columns: 26px 1fr; gap: 12px; } .step .dot { margin: 0; }
  .rrow { grid-template-columns: 1fr 36px; } .rrow .w { grid-column: 1 / -1; }
  .case { grid-template-columns: 1fr; }
  th.o, td.o { display: none; } .search { margin-left: 0; width: 100%; } .search input { width: 100%; }
  .kv, .rs li { grid-template-columns: 1fr; gap: 2px; }
}
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<div class="app">
  <aside class="side">
    <div class="brand"><i>AT</i><div>Alert Triage<span>take-home exercise</span></div></div>
    <nav class="nav" id="nav" aria-label="Pages"></nav>
    <div class="side-meta" id="meta"></div>
  </aside>
  <section class="main">
    <div class="topbar" id="topbar"></div>
    <div class="content" id="content"></div>
  </section>
</div>
<div class="scrim" id="scrim"></div>
<aside class="drawer" id="drawer" aria-label="Ticket detail"></aside>
<script>
const DATA = __DATA__;
const RUNS = DATA.runs, META = DATA.meta || {};

const REASONS = {
  CO_OWNED: "The service has more than one owning team. All are notified, none is picked.",
  NOT_IN_CATALOG: "The service isn't in the catalog. Routed to the security lead, strictest SLA.",
  AMBIGUOUS_DUPLICATE: "Only a partial match to an existing ticket. A human confirms it's the same finding.",
  RECURRENCE: "Matches a resolved ticket, which was reopened instead of silently deduplicated.",
  UNVERIFIED_MITIGATION: "A note claims a fix, but nothing verifies it. Severity and SLA stay.",
  PRIORITY_DOWNGRADE: "The model recommends a lower priority. A human approves; the SLA stays.",
  ARN_UNPARSEABLE: "Malformed resource ID, so the duplicate check was skipped.",
  LLM_ERROR: "The model failed, or its answer failed a guardrail check. Nothing was applied.",
  AGENT_UNSURE: "The model asked for review without a reason.",
  INVALID_INPUT: "The alert can't be normalized. No LLM call was made.",
};
const FLAGS = { TIMESTAMP_SUSPECT: "the scanner's timestamp is a year off the feed; kept, not dropped", ARN_UNPARSEABLE: "resource ARN has too few parts to match on" };
const SOURCES = { xr: "Xray", cs: "Code scan", cp: "Cloud posture" };
const SOURCE_NAMES = { "xray-scan": "Xray", "code-scan": "Code scan", "cloud-posture": "Cloud posture" };
const SEVS = ["Sev-0", "Sev-1", "Sev-2", "Sev-3"];
const SEV_VAR = { "Sev-0": "sev0", "Sev-1": "sev1", "Sev-2": "sev2", "Sev-3": "sev3" };
const PAGES = [["overview", "Overview"], ["queue", "Queue"], ["bad", "Bad input"]];

let page = "overview", status = "all", sevs = new Set(), reason = null, query = "", sort = "human", openKey = null;

const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const isInvalid = r => !!(r.human_reasons && r.human_reasons.includes("INVALID_INPUT"));
const rowId = (r, i) => r.ticket_id || "invalid-" + i;
const rawId = r => (r.raw_alert && (r.raw_alert.scan_id || r.raw_alert.finding_id)) || "(no id)";
const sourceOf = id => SOURCES[String(id).slice(0, 2)] || "Unknown";
const repoOf = r => { for (const t of r.trace || []) for (const c of t.tool_calls || []) if (c.tool === "lookup_owner" && c.args && c.args.repo) return c.args.repo; return null; };
const plural = (n, w) => `${n} ${w}${n === 1 ? "" : "s"}`;
const count = (list, fn) => list.reduce((m, x) => { const k = fn(x); if (k != null) m[k] = (m[k] || 0) + 1; return m; }, {});
const runFor = p => RUNS[p === "bad" ? 1 : 0] || RUNS[0];
const sourcesOf = r => { const seen = []; for (const a of r.alert_ids || []) { const s = sourceOf(a); if (!seen.includes(s)) seen.push(s); } return seen; };
const sevIdx = r => SEVS.indexOf(r.severity) < 0 ? 9 : SEVS.indexOf(r.severity);

function stats(run) {
  const tickets = run.records.filter(r => !isInvalid(r)), invalid = run.records.filter(isInvalid);
  const alerts = tickets.reduce((n, r) => n + r.alert_ids.length, 0);
  const human = tickets.filter(r => r.needs_human);
  return { tickets, invalid, alerts, human, auto: tickets.filter(r => !r.needs_human),
    grouped: tickets.filter(r => r.alert_ids.length > 1).length, actions: count(tickets, r => r.action),
    reasons: Object.entries(count(human.flatMap(r => r.human_reasons), x => x)).sort((a, b) => b[1] - a[1]),
    bySev: count(tickets, r => r.severity), bySource: count(tickets.flatMap(r => r.alert_ids.map(sourceOf)), s => s) };
}

/* ---------- shell ---------- */
function renderShell() {
  const s0 = stats(RUNS[0]), s1 = RUNS[1] ? stats(RUNS[1]) : null;
  const counts = { overview: "", queue: s0.tickets.length, bad: s1 ? s1.invalid.length + s1.tickets.length : "" };
  document.getElementById("nav").innerHTML = `<div class="h">Pages</div>` + PAGES.filter(([k]) => k !== "bad" || RUNS[1]).map(([k, label]) =>
    `<button class="${page === k ? "on" : ""}" data-page="${k}">${label}<span class="cnt">${counts[k]}</span></button>`).join("");
  document.getElementById("meta").innerHTML = `<div>Model <b>${esc(META.model || "gemini")}</b></div><div>Run <b>${esc(META.generated_at || "—")}</b></div>
    <div><a href="https://github.com/MayNimni/jfrog-alert-triage">Source on GitHub ↗</a></div>`;
}

/* ---------- overview ---------- */
function renderOverview() {
  const run = RUNS[0], s = stats(run);
  document.getElementById("topbar").innerHTML = `<div><h1>Overview</h1><p>What the agent did with the ${s.alerts} sample alerts, and where it asked for a person.</p></div>`;
  const kpi = (l, v, sub, act) => `<${act ? `button data-go="${act}"` : "div"} class="card kpi"><span class="l">${l}</span><span class="v">${v}</span><span class="s">${sub}</span></${act ? "button" : "div"}>`;
  const kpis = `<div class="kpis">
    ${kpi("Alerts in", s.alerts, Object.entries(s.bySource).map(([k, n]) => `${n} ${k}`).join(" · "))}
    ${kpi("Tickets out", s.tickets.length, `${s.alerts - s.tickets.length} alerts merged into ${plural(s.grouped, "existing ticket")}`, "queue")}
    ${kpi("Need a person", `${s.human.length}<small>of ${s.tickets.length}</small>`, "each with a named reason", "queue:human")}
    ${kpi("Filed automatically", `${s.auto.length}<small>of ${s.tickets.length}</small>`, "clean match or create, owner known", "queue:auto")}
  </div>`;
  const pipe = `<div class="card"><div class="ch"><h2>How a decision is made</h2><p>The model proposes. Code decides the facts and checks the answer.</p></div><div class="cb"><div class="pipe">
    <div class="step"><div class="dot">1</div><em>code</em><b>Normalize</b><span>Three scanner formats become one shape. Severity from the policy table.</span></div>
    <div class="step"><div class="dot">2</div><em>code</em><b>Route</b><span>Owner, Slack, on-call and tier from the catalog. Co-owned or unknown is flagged.</span></div>
    <div class="step model"><div class="dot">3</div><em>model</em><b>Agent decides</b><span>Create, link, reopen or review, plus the summary. Only tool results count as facts.</span></div>
    <div class="step"><div class="dot">4</div><em>code</em><b>Guardrails</b><span>Rejects ticket IDs no tool returned and actions that don't fit the match. Sets the SLA.</span></div>
    <div class="step"><div class="dot">5</div><em>code</em><b>Ticket store</b><span>Every decision is written back, so later alerts see it. That is the dedup.</span></div>
  </div></div></div>`;
  const reasons = `<div class="card"><div class="ch"><h2>Why a person must look</h2><p>${s.human.length} tickets · click to open the queue</p></div><div class="cb"><div class="rlist">
    ${s.reasons.map(([k, n]) => `<button class="rrow" data-go="queue:reason:${esc(k)}"><code>${esc(k)}</code><span class="n">${n}</span><span class="w">${esc(REASONS[k] || "")}</span></button>`).join("")}
  </div></div></div>`;
  const cases = highlightCases().map(c => `<button class="case" data-open="${esc(c.key)}"><span class="t">${esc(c.id)}</span><span class="d"><b>${esc(c.title)}</b><span>${esc(c.text)}</span></span></button>`).join("");
  const worth = `<div class="card"><div class="ch"><h2>Cases worth opening</h2><p>The hard ones from the exercise</p></div><div class="cb"><div class="cases">${cases}</div></div></div>`;
  document.getElementById("content").innerHTML = kpis + pipe + `<div class="two">${reasons}${worth}</div>`;
}

function highlightCases() {
  const out = [], run = RUNS[0];
  const add = (r, title, text, runIdx = 0) => { if (r && out.length < 5) out.push({ key: `${runIdx}:${r.ticket_id}`, id: (runIdx ? "Bad input · " : "") + r.ticket_id, title, text }); };
  const recs = run.records.filter(r => !isInvalid(r));
  add(recs.find(r => r.action === "reopen"), "Recurrence, not a duplicate", "A resolved ticket matched. The agent reopened it, and the four alerts that followed were linked to it instead of filed again.");
  add(recs.find(r => r.human_reasons.includes("UNVERIFIED_MITIGATION")), "A note claims it's fixed", "The scanner note says production was upgraded. Severity and SLA stay; the model may only recommend lower.");
  add(recs.find(r => r.human_reasons.includes("AMBIGUOUS_DUPLICATE")), "Partial match", "The old ticket has no file, so the identity key is incomplete. Linked, and a person confirms.");
  add(recs.find(r => r.human_reasons.includes("CO_OWNED")), "Two owning teams", "Policy says never pick one. Both are notified; the ticket waits for manual routing.");
  if (RUNS[1]) add(RUNS[1].records.find(r => !isInvalid(r) && /instruction/i.test(r.summary || "")), "Instructions hidden in a note", "The note told the agent to downgrade and close. It was treated as data, and the summary says so.", 1);
  return out;
}

/* ---------- queue ---------- */
function matches(r) {
  if (status === "invalid") { if (!isInvalid(r)) return false; }
  else if (status === "human") { if (isInvalid(r) || !r.needs_human) return false; }
  else if (status === "auto") { if (isInvalid(r) || r.needs_human) return false; }
  if (sevs.size && !sevs.has(r.severity)) return false;
  if (reason && !(r.human_reasons || []).includes(reason)) return false;
  if (query) {
    const hay = [r.ticket_id, r.summary, r.problem, repoOf(r), ...(r.alert_ids || []), ...(r.routing ? r.routing.teams : []), ...(r.human_reasons || []), rawId(r)].join(" ").toLowerCase();
    if (!hay.includes(query)) return false;
  }
  return true;
}
function sorted(records) {
  return records.map((r, i) => ({ r, id: rowId(r, i) })).sort((a, b) =>
    isInvalid(a.r) - isInvalid(b.r) ||
    (sort === "human" ? (b.r.needs_human - a.r.needs_human || sevIdx(a.r) - sevIdx(b.r)) : (sevIdx(a.r) - sevIdx(b.r) || b.r.needs_human - a.r.needs_human)));
}

function renderQueue() {
  const run = runFor(page), s = stats(run);
  const title = page === "bad" ? "Bad input" : "Queue";
  const sub = page === "bad" ? run.about : `${s.tickets.length} tickets from ${s.alerts} alerts. Click a row to see the decision and the trace.`;
  document.getElementById("topbar").innerHTML = `<div><h1>${title}</h1><p>${esc(sub)}</p></div>`;

  const statuses = [["all", "All", run.records.length], ["human", "Needs a person", s.human.length], ["auto", "Automatic", s.auto.length]];
  if (s.invalid.length) statuses.push(["invalid", "Rejected", s.invalid.length]);
  let tb = statuses.map(([k, l, n]) => `<button class="f ${status === k ? "on" : ""}" data-status="${k}">${l}<span class="cnt">${n}</span></button>`).join("");
  tb += `<span class="sep"></span>` + SEVS.map(x => `<button class="f sev ${sevs.has(x) ? "on" : ""}" data-sev="${x}" style="--c:var(--${SEV_VAR[x]});--c-bg:var(--${SEV_VAR[x]}-bg)">${x}<span class="cnt">${s.bySev[x] || 0}</span></button>`).join("");
  if (reason) tb += `<span class="sep"></span><button class="f on" data-reason="${esc(reason)}">${esc(reason)} ×</button>`;
  tb += `<span class="sep"></span><select class="f" id="sort"><option value="human" ${sort === "human" ? "selected" : ""}>Needs a person first</option><option value="sev" ${sort === "sev" ? "selected" : ""}>By severity</option></select>`;
  tb += `<div class="search"><input id="q" type="search" placeholder="Search ticket, alert, repo, team" value="${esc(query)}" aria-label="Search"></div>`;

  const all = sorted(run.records), shown = all.filter(({ r }) => matches(r));
  const active = status !== "all" || sevs.size || reason || query;
  const showing = active ? `<div class="showing">Showing ${shown.length} of ${all.length} · <button id="clear">Clear filters</button></div>` : "";
  const rows = shown.map(({ r, id }) => isInvalid(r) ? invalidRow(r, id) : ticketRow(r, id)).join("");
  document.getElementById("content").innerHTML = `<div class="card"><div class="toolbar">${tb}</div>${showing}
    <table><thead><tr><th>Ticket</th><th>Severity</th><th>Finding</th><th class="o">Action → owner</th><th class="o">SLA</th><th>Status</th></tr></thead>
    <tbody>${rows || `<tr><td colspan="6" class="empty">Nothing matches these filters.</td></tr>`}</tbody></table></div>`;
  const q = document.getElementById("q");
  if (document.activeElement === document.body && query) { q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
}

function ticketRow(r, id) {
  const key = `${page === "bad" ? 1 : 0}:${id}`;
  const n = r.alert_ids.length, repo = repoOf(r);
  const to = !r.routing.teams.length ? "security lead on-call" : r.routing.mode === "auto" ? r.routing.teams.join(", ") : r.routing.teams.join(" + ") + " (person picks)";
  const act = { create: "New ticket", link: `Link to ${r.ticket_id}`, reopen: `Reopen ${r.ticket_id}`, manual_review: "Manual review" }[r.action] || r.action;
  return `<tr class="r ${openKey === key ? "on" : ""}" data-open="${esc(key)}">
    <td><div class="tid">${esc(r.ticket_id)}</div><div class="sub"><span>${esc(sourcesOf(r).join(" + "))}</span>${n > 1 ? `<span class="g">${n} alerts</span>` : `<span>${esc(r.alert_ids[0])}</span>`}</div></td>
    <td><span class="chip ${esc(r.severity)}">${esc(r.severity)}</span></td>
    <td><div class="fnd">${esc(r.summary || "(no summary)")}${repo ? `<span class="repo">${esc(repo)}${r.routing.tier ? " · tier " + esc(r.routing.tier) : ""}</span>` : ""}</div></td>
    <td class="o"><div class="act">${esc(act)}<span>→ ${esc(to)}</span></div></td>
    <td class="o"><div class="sla">${esc(r.sla)}<span>${r.routing.tier ? "tier " + esc(r.routing.tier) : "no tier, strictest"}</span></div></td>
    <td>${r.needs_human ? `<span class="chip review">Needs a person</span>` : `<span class="chip autof">Auto-filed</span>`}</td></tr>`;
}
function invalidRow(r, id) {
  const key = `${page === "bad" ? 1 : 0}:${id}`, src = SOURCE_NAMES[r.raw_alert && r.raw_alert.source] || (r.raw_alert && r.raw_alert.source) || "unknown";
  return `<tr class="r ${openKey === key ? "on" : ""}" data-open="${esc(key)}">
    <td><div class="tid">${esc(rawId(r))}</div><div class="sub"><span>${esc(src)}</span></div></td><td><span class="faint">—</span></td>
    <td><div class="fnd">Rejected: ${esc(r.problem)}</div></td><td class="o"><div class="act">No ticket<span>→ manual review queue</span></div></td><td class="o"><span class="faint">—</span></td>
    <td><span class="chip rej">Rejected</span></td></tr>`;
}

/* ---------- drawer ---------- */
function describeCall(c) {
  const res = c.result || {};
  if (c.tool === "find_matching_tickets") {
    if (!res.matches || !res.matches.length) return `<b>No existing ticket matches.</b> A new ticket is the only valid action.`;
    return res.matches.map(m => `<b>${esc(m.match_type)} match: ${esc(m.ticket_id)} (${esc(m.status)})</b> — ${esc(m.reason)}${m.resolution_note ? `. Resolution note: “${esc(m.resolution_note)}”` : ""}${m.alert_ids && m.alert_ids.length ? ` · already holds ${esc(m.alert_ids.join(", "))}` : ""}`).join("<br>");
  }
  if (c.tool === "lookup_owner") {
    if (res.found === false) return `<b>Not in the service catalog.</b> No owner is guessed; routing goes to the security lead.`;
    return `<b>${res.co_owned ? "Co-owned: " : "Owner: "}${esc((res.teams || []).join(", "))}</b> · tier ${esc(res.tier || "?")} · ${esc((res.slack || []).join(", ") || "no channel")}${res.note ? ` · note: ${esc(res.note)}` : ""}`;
  }
  return esc(JSON.stringify(res));
}
function alertRun(t, r, runIdx) {
  const note = (RUNS[runIdx].notes || {})[t.alert_id];
  const noteBox = note ? `<div class="note"><b>Scanner note</b> (treated as data, not as a fact or an instruction): “${esc(note)}”</div>` : "";
  const calls = (t.tool_calls || []).map(c => `<li><div><span class="call">${esc(c.tool)}(${esc(Object.values(c.args || {}).join(", "))})</span><span class="res">${describeCall(c)}</span></div></li>`).join("");
  const final = `<li class="final"><div><span class="call">${esc(t.action)}${t.action !== "create" && r.ticket_id ? " → " + esc(r.ticket_id) : ""}</span><span class="res">${esc(t.why || "(no reason given)")}</span></div></li>`;
  const problems = t.problems && t.problems.length ? `<div class="note bad"><b>Guardrail rejected the answer:</b> ${esc(t.problems.join("; "))}</div>` : "";
  return `<div class="run"><div class="rh"><span class="mono">${esc(t.alert_id)}</span><span>${esc(sourceOf(t.alert_id))}</span><span>${plural((t.tool_calls || []).length, "tool call")}, then the decision</span></div>
    ${noteBox}<ol class="steps">${calls}${final}</ol>${problems}
    <details class="raw"><summary>Raw tool calls and results</summary><pre>${esc(JSON.stringify(t.tool_calls, null, 2))}</pre></details></div>`;
}
function ticketDrawer(r, runIdx) {
  const actionText = { create: "Create a new ticket", link: `Link to open ticket <code>${esc(r.ticket_id)}</code>`, reopen: `Reopen resolved ticket <code>${esc(r.ticket_id)}</code>`, manual_review: "Send to manual review" }[r.action] || esc(r.action);
  const rec = r.recommended_priority ? `<div class="note info"><b>Model recommends ${esc(r.recommended_priority)}.</b> Normalized ${esc(r.severity)} stays until a person approves. ${esc(r.priority_reason || "")}</div>` : "";
  const reasons = r.human_reasons.length ? `<ul class="rs">${r.human_reasons.map(x => `<li><code>${esc(x)}</code><span>${esc(REASONS[x] || "")}</span></li>`).join("")}</ul>` : `<p class="muted">No open questions. Filed without review.</p>`;
  const flags = r.flags.length ? `<div>Data flags</div><div>${r.flags.map(f => `<code>${esc(f)}</code> <span class="muted">${esc(FLAGS[f] || "")}</span>`).join("<br>")}</div>` : "";
  const assignee = r.routing.mode === "auto" ? r.routing.teams.join(", ") : "unassigned until a person routes it";
  const slack = r.routing.slack.length ? r.routing.slack.join(", ") : "security lead (no team channel)";
  const labels = r.human_reasons.length ? r.human_reasons.concat("needs-human").join(", ") : "none";
  return `<div class="dh"><div class="ids"><div class="tid">${esc(r.ticket_id)}</div><div class="muted">${esc(r.summary || "")}</div>
      <div class="chips"><span class="chip ${esc(r.severity)}">${esc(r.severity)}</span>${r.needs_human ? `<span class="chip review">Needs a person</span>` : `<span class="chip autof">Auto-filed</span>`}<span class="chip rej plain">${esc(r.sla)}</span></div></div>
      <button class="x" data-close aria-label="Close">×</button></div>
    <div class="db">
      <div class="sec"><h3>Decision<small>by the model, checked by code</small></h3><p class="dec">${actionText}</p><p class="why">${esc((r.trace[0] && r.trace[0].why) || "")}</p>${rec}</div>
      <div class="sec"><h3>Needs a person because</h3>${reasons}</div>
      <div class="sec"><h3>Ticket fields<small>by code</small></h3><div class="kv">
        <div>Severity</div><div><span class="chip ${esc(r.severity)}">${esc(r.severity)}</span> <span class="muted">from ${esc([...new Set(r.raw_scores)].join(", "))}</span></div>
        <div>SLA</div><div>${esc(r.sla)} <span class="muted">(${r.routing.tier ? "tier " + esc(r.routing.tier) : "tier unknown, strictest column"})</span></div>
        <div>Owner</div><div>${esc(r.routing.teams.join(", ") || "none in catalog → security lead")}${r.routing.mode !== "auto" && r.routing.teams.length ? ` <span class="muted">(manual routing)</span>` : ""}</div>
        <div>Slack</div><div>${esc(r.routing.slack.join(", ") || "—")}</div>
        <div>On-call</div><div>${esc(r.routing.on_call.join(", ") || "—")}</div>
        <div>Alerts</div><div>${r.alert_ids.map((a, i) => `<code>${esc(a)}</code> <span class="muted">${esc(r.raw_scores[i])}</span>`).join("<br>")}</div>${flags}</div></div>
      <div class="sec"><h3>Agent trace<small>one run per alert, ${plural(r.trace.length, "run")}</small></h3>${r.trace.map(t => alertRun(t, r, runIdx)).join("")}</div>
      <div class="sec"><h3>If this were wired to real systems<small>planned mapping, not built</small></h3><div class="kv">
        <div>Jira</div><div>${{ create: "Create a new ticket", link: `Add the alert to <code>${esc(r.ticket_id)}</code> as a comment, no new ticket`, reopen: `Reopen <code>${esc(r.ticket_id)}</code> and add the alert`, manual_review: "No ticket yet. Goes to the manual review queue" }[r.action] || esc(r.action)}</div>
        <div>Fields</div><div>Priority ${esc(r.severity)} · due in ${esc(r.sla)} · assignee: ${esc(assignee)} · labels: ${esc(labels)}</div>
        <div>Slack</div><div>Post the summary to ${esc(slack)}</div>
        <div>On-call</div><div>${esc(r.routing.on_call.join(", ") || "no rotation listed")}</div></div></div>
    </div>`;
}
function invalidDrawer(r) {
  return `<div class="dh"><div class="ids"><div class="tid">${esc(rawId(r))}</div><div class="muted">Rejected by the normalizer. No model call was made.</div><div class="chips"><span class="chip rej">Rejected</span></div></div><button class="x" data-close aria-label="Close">×</button></div>
    <div class="db"><div class="sec"><h3>Why</h3><p>${esc(r.problem)}</p><p class="muted" style="margin-top:6px">In production this goes to the manual review queue with the reason above.</p></div>
    <div class="sec"><h3>Raw alert</h3><pre>${esc(JSON.stringify(r.raw_alert, null, 2))}</pre></div></div>`;
}
function renderDrawer() {
  const d = document.getElementById("drawer");
  if (!openKey) { document.body.classList.remove("open"); return; }
  const [ri, id] = openKey.split(/:(.*)/s); const run = RUNS[+ri]; if (!run) { openKey = null; return renderDrawer(); }
  const rec = run.records.map((r, i) => ({ r, id: rowId(r, i) })).find(x => x.id === id);
  if (!rec) { openKey = null; return renderDrawer(); }
  d.innerHTML = isInvalid(rec.r) ? invalidDrawer(rec.r) : ticketDrawer(rec.r, +ri);
  d.scrollTop = 0; document.body.classList.add("open");
}

/* ---------- routing ---------- */
function render() {
  renderShell();
  if (page === "overview") renderOverview(); else renderQueue();
  renderDrawer();
  const url = new URL(location.href);
  const [ri, oid] = openKey ? openKey.split(/:(.*)/s) : [null, null];
  url.hash = oid ? (ri === "1" ? "bad" : "queue") + "/" + oid : page;
  history.replaceState(null, "", url);
}
function go(spec) {
  const [p, kind, val] = spec.split(":");
  page = p; status = "all"; sevs.clear(); reason = null; query = "";
  if (kind === "human" || kind === "auto") status = kind;
  if (kind === "reason") reason = val;
}
document.addEventListener("click", e => {
  const t = e.target;
  if (t.closest("details, pre, a, select, input")) return;
  const pg = t.closest("[data-page]"), goTo = t.closest("[data-go]"), op = t.closest("[data-open]"), st = t.closest("[data-status]"), sv = t.closest("[data-sev]"),
    rs = t.closest("[data-reason]"), clear = t.closest("#clear"), close = t.closest("[data-close]") || (t.id === "scrim" ? t : null);
  if (pg) { go(pg.dataset.page); openKey = null; }
  else if (goTo) { go(goTo.dataset.go); openKey = null; }
  else if (op) { openKey = openKey === op.dataset.open ? null : op.dataset.open; }
  else if (close) { openKey = null; }
  else if (st) { status = st.dataset.status; if (status === "auto") reason = null; }
  else if (sv) { sevs.has(sv.dataset.sev) ? sevs.delete(sv.dataset.sev) : sevs.add(sv.dataset.sev); }
  else if (rs) { reason = null; }
  else if (clear) { status = "all"; sevs.clear(); reason = null; query = ""; }
  else return;
  render();
});
document.addEventListener("change", e => { if (e.target.id === "sort") { sort = e.target.value; render(); } });
document.addEventListener("input", e => { if (e.target.id === "q") { query = e.target.value.trim().toLowerCase(); render(); } });
document.addEventListener("keydown", e => { if (e.key === "Escape" && openKey) { openKey = null; render(); } });

// #queue/SEC-3987 opens the queue with that ticket; #overview, #queue, #bad pick a page.
{
  const h = decodeURIComponent(location.hash.slice(1)), [p, id] = h.split("/");
  if (PAGES.some(([k]) => k === p)) page = p;
  if (id) {
    const ri = page === "bad" ? 1 : 0, run = RUNS[ri];
    if (run && run.records.some((r, i) => rowId(r, i) === id)) { openKey = `${ri}:${id}`; if (page === "overview") page = "queue"; }
  }
  if (page === "queue") sort = "human";
}
if (RUNS.length) render();
else document.getElementById("content").innerHTML = '<div class="card"><div class="empty">No results yet. Run python main.py first.</div></div>';
</script>
</body>
</html>
"""


if __name__ == "__main__":
    print(f"Written to {write_report()}")
