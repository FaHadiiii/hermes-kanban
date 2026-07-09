#!/usr/bin/env python3
"""Generate a static, light, read-only preview of Hermes Kanban boards.

Scans every board DB under ~/.hermes/kanban/boards/*/kanban.db and emits:
  - public/index.html        : portfolio landing (links to each board page)
  - public/<board>.html      : per-board Kanban preview (attention-aware)

Reads tasks from each board SQLite DB (read-only, fixed queries only),
escapes all DB-derived text, and emits self-contained HTML files.
"""

import hashlib
import html
import os
import sqlite3
import time
from datetime import datetime, timezone

# Minimal static inline script (no DB input, no eval) that sets the initial
# theme from localStorage or OS preference, then wires the toggle button.
# Runs in <head>: theme is applied immediately (no FOUC); the click handler is
# attached on DOMContentLoaded because #theme-toggle lives later in <body>.
# Kept as a module-level constant so the embedded bytes and the reported
# sha256 (for Caddy CSP: script-src 'sha256-...') are always identical.
# MUST stay free of any interpolated/foreign data.
THEME_SCRIPT = (
    "const d=document.documentElement;const s=localStorage.getItem('kanban-theme');"
    "d.dataset.theme=s||(matchMedia('(prefers-color-scheme:dark)').matches?'dark':'light');"
    "document.addEventListener('DOMContentLoaded',function(){"
    "var b=document.getElementById('theme-toggle');"
    "if(b){b.onclick=function(){"
    "var n=d.dataset.theme==='dark'?'light':'dark';d.dataset.theme=n;"
    "localStorage.setItem('kanban-theme',n);}};});"
)

# --- Paths ---------------------------------------------------------------
APP_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(os.path.dirname(APP_DIR), "public")
BOARDS_ROOT = "/home/ubuntu/.hermes/kanban/boards"

# --- Spec constants ------------------------------------------------------
STATUS_ORDER = ["triage", "todo", "scheduled", "ready", "running", "blocked", "done"]
ASSIGNEE_ORDER = ["ayo", "leha", "jusoh", "zali"]

# Pill semantic classes per status (from design spec).
STATUS_PILL_CLASS = {
    "triage": "pill-neutral",
    "todo": "pill-neutral",
    "scheduled": "pill-warning",
    "ready": "pill-warning",
    "running": "pill-accent",
    "blocked": "pill-danger",
    "done": "pill-success",
}

# Fixed set of columns we try to read; tolerate missing ones (e.g. updated_at).
FALLBACK_COLUMNS = {
    "id": "''",
    "title": "''",
    "assignee": "''",
    "status": "''",
    "priority": "0",
    "created_at": "NULL",
    "updated_at": "NULL",
}

# A task is "stale" when (now - created_at) > STALE_DAYS and status != done.
STALE_DAYS = 3

# Where the portfolio links send you. Each board page is emitted as
# public/<board>.html and is served at /<board>.html.
BOARD_URL_TMPL = "{board_id}.html"


# --- DB helpers ----------------------------------------------------------
def get_connection(db_path):
    return sqlite3.connect("file:" + db_path + "?mode=ro", uri=True)


def available_columns(cur):
    """Return set of column names that actually exist on the tasks table."""
    cur.execute("PRAGMA table_info(tasks)")
    return {row[1] for row in cur.fetchall()}


def build_query(cols):
    selects = []
    for c in ["id", "title", "assignee", "status", "priority", "created_at", "updated_at"]:
        if c in cols:
            selects.append(c)
        else:
            selects.append(FALLBACK_COLUMNS[c] + " AS " + c)
    # Always include last_heartbeat_at if present (used as last-sync fallback).
    if "last_heartbeat_at" in cols:
        selects.append("last_heartbeat_at")
    return "SELECT " + ", ".join(selects) + " FROM tasks ORDER BY created_at ASC"


# --- Formatting helpers --------------------------------------------------
def fmt_ts(value):
    """Format an epoch (int/str) or None into 'YYYY-MM-DD HH:MM'. Empty if none."""
    if value is None:
        return ""
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return ""
    if iv <= 0:
        return ""
    try:
        return datetime.fromtimestamp(iv, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return ""


def prio_label(value):
    """Map integer priority (0..3) to P0..P3."""
    try:
        p = int(value)
    except (TypeError, ValueError):
        p = 0
    if p < 0:
        p = 0
    if p > 3:
        p = 3
    return "P" + str(p)


def initial_of(name):
    if not name:
        return "?"
    return name[0].upper()


def esc(value):
    """XSS-safe escape of any DB-derived text."""
    return html.escape("" if value is None else str(value))


def age_days(value):
    """Return float age in days for an epoch created_at, or None if unknown."""
    if value is None:
        return None
    try:
        iv = int(value)
    except (TypeError, ValueError):
        return None
    if iv <= 0:
        return None
    return (time.time() - iv) / 86400.0


# --- Reading a board -----------------------------------------------------
def read_board(db_path, board_id):
    """Return (tasks, per_status, per_assignee, last_synced, blocked, stale)."""
    con = get_connection(db_path)
    cur = con.cursor()
    cols = available_columns(cur)
    query = build_query(cols)
    cur.execute(query)  # fixed query, no user input
    rows = cur.fetchall()
    con.close()

    tasks = []
    per_status = {s: 0 for s in STATUS_ORDER}
    per_assignee = {a: 0 for a in ASSIGNEE_ORDER}
    last_synced = 0
    blocked = 0
    stale = 0

    for r in rows:
        rec = dict(zip(
            ["id", "title", "assignee", "status", "priority", "created_at", "updated_at"]
            + (["last_heartbeat_at"] if "last_heartbeat_at" in cols else []),
            r,
        ))
        status = (rec.get("status") or "").strip().lower()
        assignee = (rec.get("assignee") or "").strip().lower()
        rec["_status"] = status
        rec["_assignee"] = assignee
        rec["_id"] = rec.get("id") or ""
        rec["_title"] = rec.get("title") or "(untitled)"
        rec["_priority_label"] = prio_label(rec.get("priority"))
        rec["_created_fmt"] = fmt_ts(rec.get("created_at"))

        # Attention flags (generator-side, per DESIGN_SPEC part B).
        rec["_blocked"] = (status == "blocked")
        a = age_days(rec.get("created_at"))
        rec["_stale"] = bool(a is not None and a > STALE_DAYS and status != "done")
        rec["_age_days"] = int(a) if a is not None else None
        if rec["_blocked"]:
            blocked += 1
        if rec["_stale"]:
            stale += 1

        # last sync: prefer updated_at, else last_heartbeat, else created_at
        sync_candidate = rec.get("updated_at") or rec.get("last_heartbeat_at") or rec.get("created_at")
        try:
            sc = int(sync_candidate) if sync_candidate else 0
        except (TypeError, ValueError):
            sc = 0
        if sc > last_synced:
            last_synced = sc

        tasks.append(rec)
        if status in per_status:
            per_status[status] += 1
        else:
            per_status[status] = per_status.get(status, 0) + 1
        if assignee in per_assignee:
            per_assignee[assignee] += 1
        elif assignee:
            per_assignee[assignee] = per_assignee.get(assignee, 0) + 1

    return tasks, per_status, per_assignee, last_synced, blocked, stale


def scan_boards():
    """Return a list of (board_id, db_path) for every board DB found."""
    found = []
    if not os.path.isdir(BOARDS_ROOT):
        return found
    for name in sorted(os.listdir(BOARDS_ROOT)):
        db = os.path.join(BOARDS_ROOT, name, "kanban.db")
        if os.path.isfile(db):
            found.append((name, db))
    return found


# --- Per-board rendering -------------------------------------------------
def render_task_card(t):
    cls = STATUS_PILL_CLASS.get(t["_status"], "pill-neutral")
    card_cls = "task-card"
    if t["_blocked"]:
        card_cls += " is-blocked"
    if t["_stale"]:
        card_cls += " is-stale"

    stale_badge = ""
    if t["_stale"]:
        n = t["_age_days"] if t["_age_days"] is not None else "?"
        stale_badge = (
            '<span class="stale-badge" title="' + esc("Age {} days, not done".format(n)) + '">'
            + esc("{}d".format(n)) + "</span>"
        )

    return (
        '<article class="' + card_cls + '">'
        '<div class="task-card-row1">'
        '<span class="task-title">' + esc(t["_title"]) + "</span>"
        '<span class="pill ' + cls + '">' + esc(t["_status"].upper()) + "</span>"
        "</div>"
        '<div class="task-card-row2">'
        '<span class="mono-id">' + esc(t["_id"]) + "</span>"
        '<span class="avatar" title="' + esc(t["_assignee"]) + '">'
        + esc(initial_of(t["_assignee"])) + "</span>"
        '<span class="assignee-name">' + esc(t["_assignee"]) + "</span>"
        "</div>"
        '<div class="task-card-row3">'
        '<span class="mono-tag">' + esc(t["_priority_label"]) + "</span>"
        '<span class="mono-ts">' + esc(t["_created_fmt"]) + "</span>"
        + stale_badge
        + "</div>"
        "</article>"
    )


def render_board_page(board_id, db_path):
    (tasks, per_status, per_assignee, last_synced, blocked, stale) = read_board(db_path, board_id)
    total = len(tasks)
    last_synced_fmt = fmt_ts(last_synced) if last_synced else "—"

    # Columns
    columns_html = []
    for s in STATUS_ORDER:
        cls = STATUS_PILL_CLASS.get(s, "pill-neutral")
        cards = [t for t in tasks if t["_status"] == s]
        cards_html = []
        if not cards:
            cards_html.append('<div class="empty-well">— EMPTY —</div>')
        else:
            cards_html = [render_task_card(t) for t in cards]
        count = per_status.get(s, 0)
        columns_html.append(
            '<section class="status-column">'
            '<header class="col-header">'
            '<span class="mono-token">[ ' + esc(s.upper()) + " ]</span>"
            '<span class="count-chip mono">' + esc("{:02d}".format(count)) + "</span>"
            "</header>"
            '<div class="col-body">' + "".join(cards_html) + "</div>"
            "</section>"
        )

    # Summary stat cards: 5 meaningful metrics (TOTAL, DONE, RUNNING, BLOCKED, STALE)
    summary_cards = [
        '<div class="stat-card">'
        '<span class="stat-label mono">' + esc("TOTAL") + "</span>"
        '<span class="stat-count">' + esc(str(total)) + "</span>"
        '<span class="stat-legend mono neutral-dot">' + esc("{:02d}".format(total)) + "</span>"
        "</div>",
        '<div class="stat-card">'
        '<span class="stat-label mono">' + esc("DONE") + "</span>"
        '<span class="stat-count">' + esc(str(per_status.get("done", 0))) + "</span>"
        '<span class="stat-legend mono success-dot">' + esc("{:02d}".format(per_status.get("done", 0))) + "</span>"
        "</div>",
        '<div class="stat-card">'
        '<span class="stat-label mono">' + esc("RUNNING") + "</span>"
        '<span class="stat-count">' + esc(str(per_status.get("running", 0))) + "</span>"
        '<span class="stat-legend mono accent-dot">' + esc("{:02d}".format(per_status.get("running", 0))) + "</span>"
        "</div>",
        '<div class="stat-card">'
        '<span class="stat-label mono">' + esc("BLOCKED") + "</span>"
        '<span class="stat-count">' + esc(str(blocked)) + "</span>"
        '<span class="stat-legend mono danger-dot">' + esc("{:02d}".format(blocked)) + "</span>"
        "</div>",
        '<div class="stat-card">'
        '<span class="stat-label mono">' + esc("STALE") + "</span>"
        '<span class="stat-count">' + esc(str(stale)) + "</span>"
        '<span class="stat-legend mono warning-dot">' + esc("{:02d}".format(stale)) + "</span>"
        "</div>",
    ]

    # Attention rail (B1): show only when something needs attention.
    attention_rail = ""
    attention_total = blocked + stale
    if attention_total > 0:
        attention_rail = (
            '<section class="attention-rail" aria-label="Tasks needing attention">'
            '<span class="attention-rail-title mono">NEEDS ATTENTION</span>'
        )
        if blocked > 0:
            attention_rail += (
                '<span class="attention-chip attention-chip--blocked" title="Blocked tasks">'
                '⚠ <span class="attention-n mono">' + esc(str(blocked)) + "</span> BLOCKED"
                "</span>"
            )
        if stale > 0:
            attention_rail += (
                '<span class="attention-chip attention-chip--stale" '
                'title="Stale tasks (age &gt; 3d, not done)">'
                '⏱ <span class="attention-n mono">' + esc(str(stale)) + "</span> STALE"
                "</span>"
            )
        attention_rail += (
            '<span class="attention-total mono">' + esc(str(attention_total)) + " TOTAL</span>"
            "</section>"
        )

    return page_shell(
        esc(board_id) + " · Kanban Preview",
        (
            '<header class="topbar">'
            '<div class="topbar-left">'
            '<a class="back-link mono" href="index.html" title="All boards">← BOARDS</a>'
            '<h1 class="board-name">' + esc(board_id) + "</h1>"
            "</div>"
            '<div class="topbar-right"><span class="live-dot"></span><span>LIVE</span>'
            '<button id="theme-toggle" class="theme-toggle" type="button" aria-label="Toggle color theme">'
            'THEME <span class="ico"></span></button>'
            '<span class="mono-refresh">&#8984;R refresh</span></div>'
            "</header>"
            '<p class="eyebrow">BOARD &middot; ' + esc(board_id) + "</p>"
            + attention_rail
            + '<div class="summary-bar">'
            + "".join(summary_cards)
            + "</div>"
            '<div class="columns">' + "".join(columns_html) + "</div>"
            '<footer class="footerline">'
            "<span>TOTAL <b>" + esc(str(total)) + "</b></span>"
            "<span>LAST SYNC <b>" + esc(last_synced_fmt) + "</b></span>"
            "<span>BOARD <b>" + esc(board_id) + "</b></span>"
            "</footer>"
        ),
    )


# --- Portfolio rendering -------------------------------------------------
def render_portfolio_page(boards_meta, last_synced):
    cards = []
    for meta in boards_meta:
        bid = meta["board_id"]
        total = meta["total"]
        done = per_status_val(meta["per_status"], "done")
        blocked = meta["blocked"]
        pct = int(round(done / total * 100)) if total else 0
        cards.append(
            '<a class="board-card" href="' + esc(BOARD_URL_TMPL.format(board_id=bid)) + '">'
            '<div class="board-card-top">'
            '<span class="board-name">' + esc(bid) + "</span>"
            '<span class="board-blocked mono" title="Blocked tasks">'
            '⚠ <span class="board-blocked-n">' + esc(str(blocked)) + "</span>"
            "</span>"
            "</div>"
            '<div class="board-progress">'
            '<div class="board-progress-bar">'
            '<span class="board-progress-fill" style="width:' + esc(str(pct)) + '%"></span>'
            "</div>"
            '<span class="board-progress-label mono">' + esc("{} / {}".format(done, total)) + "</span>"
            "</div>"
            '<div class="board-meta mono">'
            '<span class="pill pill-success">DONE ' + esc(str(done)) + "</span>"
            '<span class="pill pill-danger">BLOCKED ' + esc(str(blocked)) + "</span>"
            "</div>"
            "</a>"
        )

    last_synced_fmt = fmt_ts(last_synced) if last_synced else "—"
    n_boards = len(boards_meta)

    return page_shell(
        "Hermes · Kanban Portfolio",
        (
            '<header class="page-head">'
            "<div>"
            '<p class="eyebrow mono">HERMES &middot; KANBAN PORTFOLIO</p>'
            '<h1 class="h1">Boards</h1>'
            "</div>"
            '<button id="theme-toggle" class="theme-toggle" type="button" aria-label="Toggle color theme">'
            '<span class="ico"></span></button>'
            "</header>"
            '<section class="portfolio-grid" aria-label="All boards">'
            + "".join(cards)
            + "</section>"
            '<footer class="footerline mono">'
            "<span>" + esc("{} BOARDS".format(n_boards)) + "</span>"
            "<span>LAST SYNC " + esc(last_synced_fmt) + "</span>"
            "</footer>"
        ),
    )


def per_status_val(per_status, status):
    return per_status.get(status, 0)


# --- Shared CSS + HTML shell --------------------------------------------
CSS = """
    :root{
      --bg-base:#FAFAF9; --bg-panel:#FFFFFF; --bg-muted:#F2F1EE;
      --border:#E5E3DE; --text-1:#18181B; --text-2:#6B6B6B; --text-3:#A3A29D;
      --accent:#FF5A1F; --accent-hover:#E64A15;
      --success:#16A34A; --warning:#B45309; --danger:#DC2626;
      --mono:'JetBrains Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
      --sans:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;
    }
    /* ===== Explicit dark (user toggled / persisted) ===== */
    [data-theme="dark"]{
      --bg-base:#141312;
      --bg-panel:#1F1D1A;
      --bg-muted:#26231F;
      --border:#2E2B27;
      --text-1:#EDEAE4;
      --text-2:#A8A39B;
      --text-3:#9CA3AF;
      --accent:#FF5A1F;
      --accent-hover:#E64A15;
      --success:#16A34A;
      --warning:#B45309;
      --danger:#DC2626;
      --pill-neutral-bg:#26231F;  --pill-neutral-fg:#A8A39B;
      --pill-warning-bg:#2E2410;  --pill-warning-fg:#F5C264;
      --pill-accent-bg:#2A1A12;   --pill-accent-fg:#FF8A5C;
      --pill-danger-bg:#2A1414;   --pill-danger-fg:#F4A0A0;
      --pill-success-bg:#14261A;  --pill-success-fg:#7FE0A4;
      .pill-neutral{background:var(--pill-neutral-bg);color:var(--pill-neutral-fg);}
      .pill-warning{background:var(--pill-warning-bg);color:var(--pill-warning-fg);}
      .pill-accent {background:var(--pill-accent-bg); color:var(--pill-accent-fg);}
      .pill-danger {background:var(--pill-danger-bg); color:var(--pill-danger-fg);}
      .pill-success{background:var(--pill-success-bg);color:var(--pill-success-fg);}
      /* SECTION-D attention overrides (dark) */
      .attention-chip--blocked{background:var(--pill-danger-bg);color:var(--pill-danger-fg);}
      .attention-chip--stale{background:var(--pill-warning-bg);color:var(--pill-warning-fg);}
      .stale-badge{background:var(--pill-warning-bg);color:var(--pill-warning-fg);}
      .task-card.is-blocked{border-color:var(--pill-danger-fg);}
    }
    /* ===== OS preference is the default when user hasn't chosen ===== */
    @media (prefers-color-scheme: dark){
      :root:not([data-theme="light"]){
        --bg-base:#141312;
        --bg-panel:#1F1D1A;
        --bg-muted:#26231F;
        --border:#2E2B27;
        --text-1:#EDEAE4;
        --text-2:#A8A39B;
        --text-3:#9CA3AF;
        --accent:#FF5A1F;
        --accent-hover:#E64A15;
        --success:#16A34A;
        --warning:#B45309;
        --danger:#DC2626;
        --pill-neutral-bg:#26231F;  --pill-neutral-fg:#A8A39B;
        --pill-warning-bg:#2E2410;  --pill-warning-fg:#F5C264;
        --pill-accent-bg:#2A1A12;   --pill-accent-fg:#FF8A5C;
        --pill-danger-bg:#2A1414;   --pill-danger-fg:#F4A0A0;
        --pill-success-bg:#14261A;  --pill-success-fg:#7FE0A4;
        .pill-neutral{background:var(--pill-neutral-bg);color:var(--pill-neutral-fg);}
        .pill-warning{background:var(--pill-warning-bg);color:var(--pill-warning-fg);}
        .pill-accent {background:var(--pill-accent-bg); color:var(--pill-accent-fg);}
        .pill-danger {background:var(--pill-danger-bg); color:var(--pill-danger-fg);}
        .pill-success{background:var(--pill-success-bg);color:var(--pill-success-fg);}
        /* SECTION-D attention overrides (dark, OS preference) */
        .attention-chip--blocked{background:var(--pill-danger-bg);color:var(--pill-danger-fg);}
        .attention-chip--stale{background:var(--pill-warning-bg);color:var(--pill-warning-fg);}
        .stale-badge{background:var(--pill-warning-bg);color:var(--pill-warning-fg);}
        .task-card.is-blocked{border-color:var(--pill-danger-fg);}
      }
      :root:not([data-theme="light"]) .theme-toggle .ico::before{content:"\\2636";}
    }
    .theme-toggle .ico::before{content:"\\2600";}
    [data-theme="dark"] .theme-toggle .ico::before{content:"\\2636";}
    *{box-sizing:border-box}
    html,body{margin:0;padding:0;overflow-x:hidden}
    body{
      background-color:var(--bg-base);
      font-family:var(--sans);
      color:var(--text-1);
      font-size:14px;
      line-height:1.5;
      -webkit-font-smoothing:antialiased;
    }
    .container{max-width:1280px;margin:0 auto;padding:24px 24px 48px}
    header.topbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:24px}
    .topbar-left{display:flex;align-items:center;gap:14px}
    .back-link{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--text-3);text-decoration:none;letter-spacing:.04em}
    .back-link:hover{color:var(--text-1)}
    .board-name{font-size:1.5rem;font-weight:700;letter-spacing:-0.01em;margin:0}
    .topbar-right{display:flex;align-items:center;gap:12px;color:var(--text-2);font-size:12px}
    .live-dot{width:8px;height:8px;border-radius:9999px;background:var(--accent);display:inline-block;box-shadow:0 0 0 3px rgba(255,90,31,.18)}
    .mono-refresh{font-family:var(--mono);font-size:12px;color:var(--text-3);border:1px solid var(--border);border-radius:6px;padding:4px 8px;background:var(--bg-panel)}
    .theme-toggle{display:inline-flex;align-items:center;justify-content:center;gap:6px;font-family:var(--mono);font-size:12px;font-weight:600;color:var(--text-2);background:var(--bg-panel);border:1px solid var(--border);border-radius:6px;min-height:44px;min-width:44px;padding:8px 14px;cursor:pointer;line-height:1;transition:border-color .15s ease,background-color .15s ease,color .15s ease}
    .theme-toggle:hover{border-color:var(--text-3);color:var(--text-1)}
    @media (prefers-reduced-motion:reduce){.theme-toggle{transition:none}}
    .eyebrow{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.08em;color:var(--text-3);text-transform:uppercase;margin:0 0 8px}
    .summary-bar{background:var(--bg-panel);border:1px solid var(--border);border-radius:8px;padding:16px;display:flex;flex-wrap:wrap;gap:12px;box-shadow:0 1px 2px rgba(24,24,27,.04)}
    .stat-card{background:var(--bg-base);border:1px solid var(--border);border-radius:6px;padding:12px;min-width:104px;flex:1 1 104px;display:flex;flex-direction:column;gap:4px}
    .stat-label{font-size:11px;font-weight:600;letter-spacing:.08em;color:var(--text-3);text-transform:uppercase}
    .stat-count{font-family:var(--sans);font-weight:700;font-size:30px;line-height:1;color:var(--text-1)}
    .stat-legend{font-size:11px;color:var(--text-3);display:flex;align-items:center;gap:6px}
    .columns{display:flex;gap:16px;margin-top:24px;overflow-x:auto;padding-bottom:8px}
    .status-column{background:var(--bg-panel);border:1px solid var(--border);border-radius:8px;padding:16px;min-width:240px;flex:0 0 240px}
    .col-header{display:flex;align-items:center;justify-content:space-between;padding-bottom:8px;border-bottom:1px solid var(--border);margin-bottom:12px}
    .mono-token{font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.08em;color:var(--text-2);text-transform:uppercase}
    .count-chip{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--text-2);background:var(--bg-muted);border-radius:9999px;padding:2px 8px}
    .col-body{display:flex;flex-direction:column;gap:12px;min-height:48px}
    .task-card{background:var(--bg-panel);border:1px solid var(--border);border-radius:6px;padding:12px;display:flex;flex-direction:column;gap:8px;transition:border-color .15s ease,background-color .15s ease}
    .task-card:hover{border-color:var(--text-3);background:var(--bg-muted)}
    .task-card-row1{display:flex;align-items:flex-start;justify-content:space-between;gap:8px}
    .task-title{font-weight:600;color:var(--text-1);font-size:14px;flex:1 1 auto;min-width:0;overflow-wrap:anywhere}
    .task-card-row2{display:flex;align-items:center;gap:8px}
    .task-card-row3{display:flex;align-items:center;gap:10px}
    .mono-id{font-family:var(--mono);font-size:12px;color:var(--text-3)}
    .mono-tag{font-family:var(--mono);font-size:12px;font-weight:600;color:var(--text-2)}
    .mono-ts{font-family:var(--mono);font-size:12px;color:var(--text-3)}
    .assignee-name{font-family:var(--sans);font-size:12px;color:var(--text-2)}
    .avatar{width:20px;height:20px;border-radius:9999px;background:var(--bg-muted);border:1px solid var(--border);display:inline-flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:11px;font-weight:600;color:var(--text-2);text-transform:uppercase}
    .avatar.sm{width:16px;height:16px;font-size:10px}
    .pill{font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.06em;border-radius:9999px;padding:3px 10px;text-transform:uppercase;white-space:nowrap}
    .pill-neutral{background:var(--bg-muted);color:var(--text-2)}
    .pill-warning{background:#FEF3C7;color:#B45309}
    .pill-accent{background:#FFEDE6;color:#E64A15}
    .pill-danger{background:#FEE2E2;color:#DC2626}
    .pill-success{background:#DCFCE7;color:#16A34A}
    .empty-well{background:var(--bg-muted);border:1px dashed var(--border);border-radius:6px;padding:16px;text-align:center;font-family:var(--mono);font-size:12px;color:var(--text-3);letter-spacing:.08em}
    .success-dot{color:var(--success)} .warning-dot{color:var(--warning)} .danger-dot{color:var(--danger)} .accent-dot{color:var(--accent)} .neutral-dot{color:var(--text-3)}
    footer.footerline{margin-top:24px;font-family:var(--mono);font-size:12px;color:var(--text-3);display:flex;gap:16px;flex-wrap:wrap}
    footer.footerline b{color:var(--text-2);font-weight:600}

    /* ===== Attention rail (B1) ===== */
    .attention-rail{
      display:flex;align-items:center;gap:10px;flex-wrap:wrap;
      background:var(--bg-panel);
      border:1px solid var(--border);
      border-radius:8px;
      padding:12px 16px;
      margin-top:16px;
    }
    .attention-rail-title{
      font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.08em;
      color:var(--text-3);text-transform:uppercase;
    }
    .attention-chip{
      display:inline-flex;align-items:center;gap:6px;
      font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.04em;
      border-radius:9999px;padding:4px 10px;
    }
    .attention-chip--blocked{background:#FEE2E2;color:var(--danger);}
    .attention-chip--stale{background:#FEF3C7;color:#B45309;}
    .attention-n{font-weight:700;}
    .attention-total{
      margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--text-2);
    }
    /* Blocked task card — red left border, float to top of column (B2) */
    .task-card.is-blocked{
      order:-1;                                   /* floats above siblings in col-body */
      box-shadow:inset 3px 0 0 var(--danger);     /* inset = no layout shift */
      border-color:var(--danger);
    }
    .task-card.is-blocked:hover{
      box-shadow:inset 3px 0 0 var(--danger);     /* keep border on hover */
    }
    /* Stale badge (B3) */
    .stale-badge{
      font-family:var(--mono);font-size:11px;font-weight:600;letter-spacing:.04em;
      color:#B45309;background:#FEF3C7;border-radius:9999px;padding:2px 8px;
      white-space:nowrap;margin-left:auto;
    }

    /* ===== Portfolio landing (PART A) ===== */
    .page-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:8px}
    .h1{font-family:var(--sans);font-size:1.75rem;font-weight:700;letter-spacing:-0.01em;margin:0;color:var(--text-1)}
    .portfolio-grid{
      display:grid;
      grid-template-columns:repeat(auto-fill,minmax(260px,1fr));
      gap:16px;
      margin-top:24px;
    }
    .board-card{
      display:block;text-decoration:none;
      background:var(--bg-panel);
      border:1px solid var(--border);
      border-radius:8px;
      padding:16px;
      transition:border-color .15s ease,background-color .15s ease,transform .15s ease;
    }
    .board-card:hover{
      border-color:var(--text-3);
      background:var(--bg-muted);
      transform:translateY(-1px);
    }
    .board-card-top{
      display:flex;align-items:center;justify-content:space-between;gap:8px;
    }
    .board-name{
      font-family:var(--sans);font-weight:600;font-size:1rem;color:var(--text-1);
    }
    .board-blocked{
      display:inline-flex;align-items:center;gap:4px;
      font-family:var(--mono);font-size:12px;font-weight:600;color:var(--text-2);
    }
    .board-blocked-n{color:var(--danger);}
    .board-progress{margin-top:14px;display:flex;align-items:center;gap:10px;}
    .board-progress-bar{
      flex:1;height:6px;border-radius:9999px;background:var(--bg-muted);overflow:hidden;
    }
    .board-progress-fill{
      display:block;height:100%;border-radius:9999px;background:var(--accent);
    }
    .board-progress-label{
      font-family:var(--mono);font-size:12px;color:var(--text-3);white-space:nowrap;
    }
    .board-meta{margin-top:12px;display:flex;gap:6px;flex-wrap:wrap;}

    /* ===== Mobile-first polish (<768px): stack columns, touch targets ===== */
    @media (max-width:768px){
      body{background-attachment:scroll}
      .container{padding:16px 16px 40px}
      header.topbar{flex-wrap:wrap;row-gap:12px;margin-bottom:16px}
      .board-name{font-size:1.25rem;flex:1 1 auto}
      .topbar-right{gap:8px;flex-wrap:wrap}
      .summary-bar{gap:8px;padding:12px}
      .stat-card{flex:1 1 calc(50% - 4px);min-width:0}
      .stat-count{font-size:26px}
      .columns{flex-direction:column;overflow-x:visible;gap:12px;margin-top:16px}
      .status-column{min-width:0;flex:1 1 auto;width:100%}
      .col-body{gap:10px}
      .task-card{padding:14px;gap:10px}
      .task-title{overflow-wrap:anywhere}
      .mono-refresh{display:none}
      .portfolio-grid{grid-template-columns:1fr;gap:12px;margin-top:16px}
      .board-card{padding:14px}
      .board-progress-label{font-size:11px}
    }
    @media (min-width:769px) and (max-width:1024px){
      .stat-card{flex:1 1 calc(25% - 9px);min-width:0}
    }
    @media (max-width:380px){
      .portfolio-grid{gap:10px}
      .board-name{font-size:1.1rem}
      .board-progress-label{font-size:10px}
    }
    @media (prefers-reduced-motion:reduce){*{transition:none!important}}
    """

def page_shell(title, body):
    """Build a full HTML document. Uses concatenation (not str.format) because
    the shared CSS contains literal curly braces."""
    return (
        "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<script>" + THEME_SCRIPT + "</script>\n"
        "<title>" + title + "</title>\n<style>" + CSS + "</style>\n</head>\n<body>\n"
        '<div class="container">\n' + body + "\n</div>\n</body>\n</html>\n"
    )


# --- Output --------------------------------------------------------------
def ensure_public():
    if not os.path.isdir(PUBLIC_DIR):
        os.makedirs(PUBLIC_DIR, exist_ok=True)


def generate_all():
    ensure_public()
    boards = scan_boards()
    boards_meta = []
    max_last_synced = 0

    for board_id, db_path in boards:
        (tasks, per_status, per_assignee, last_synced, blocked, stale) = read_board(db_path, board_id)
        boards_meta.append({
            "board_id": board_id,
            "db_path": db_path,
            "total": len(tasks),
            "per_status": per_status,
            "per_assignee": per_assignee,
            "blocked": blocked,
            "stale": stale,
        })
        if last_synced > max_last_synced:
            max_last_synced = last_synced

        # Per-board page.
        out_board = os.path.join(PUBLIC_DIR, "{}.html".format(board_id))
        with open(out_board, "w", encoding="utf-8") as f:
            f.write(render_board_page(board_id, db_path))

    # Portfolio page.
    out_index = os.path.join(PUBLIC_DIR, "index.html")
    with open(out_index, "w", encoding="utf-8") as f:
        f.write(render_portfolio_page(boards_meta, max_last_synced))

    return boards_meta


if __name__ == "__main__":
    meta = generate_all()
    script_sha256 = hashlib.sha256(THEME_SCRIPT.encode("utf-8")).hexdigest()
    print("Generated portfolio:", os.path.join(PUBLIC_DIR, "index.html"))
    print("Boards:", ", ".join(m["board_id"] for m in meta) or "(none)")
    for m in meta:
        print("  {board_id}: total={total} blocked={blocked} stale={stale} -> {board_id}.html".format(**m))
    print("inline script sha256 (Caddy CSP whitelist):", script_sha256)
