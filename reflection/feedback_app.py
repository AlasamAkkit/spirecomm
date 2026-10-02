"""Local browser UI for C2 trajectory-level human feedback.

Usage from project root:
    python reflection/feedback_app.py --output-dir reflection/condition_c2_outputs

Then open:
    http://127.0.0.1:8765

No third-party web framework is required.
"""

from __future__ import annotations

import argparse
import html
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

STATUS_PENDING = "PENDING"
STATUS_FINALIZED = "FINALIZED"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, document: dict) -> None:
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(temp, path)


def safe_packet_files(output_dir: Path):
    return sorted(output_dir.glob("run_*_feedback_review.json"))


def load_packet(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def page_shell(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif; }}
body {{ margin: 0; background: #111827; color: #e5e7eb; }}
a {{ color: #93c5fd; text-decoration: none; }}
.container {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 60px; }}
.card {{ background: #1f2937; border: 1px solid #374151; border-radius: 14px; padding: 18px; margin: 14px 0; }}
.grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(170px,1fr)); gap: 10px; }}
.metric {{ background:#111827; border-radius:10px; padding:12px; }}
.metric b {{ display:block; font-size:20px; margin-top:4px; }}
.badge {{ display:inline-block; border-radius:999px; padding:4px 9px; font-size:12px; background:#374151; margin-right:6px; }}
.pending {{ background:#92400e; }} .final {{ background:#065f46; }}
.event {{ border-left: 4px solid #f59e0b; padding: 10px 14px; margin:10px 0; background:#111827; border-radius:8px; }}
.timeline {{ border-left:2px solid #4b5563; margin-left:10px; padding-left:18px; }}
.timeline-item {{ margin: 12px 0; }}
small, .muted {{ color:#9ca3af; }}
textarea {{ width:100%; min-height:210px; padding:14px; box-sizing:border-box; border-radius:10px; border:1px solid #4b5563; background:#111827; color:#f3f4f6; font:inherit; line-height:1.45; }}
button {{ padding:11px 18px; border-radius:10px; border:0; cursor:pointer; font-weight:700; margin-right:8px; }}
.primary {{ background:#2563eb; color:white; }} .secondary {{ background:#374151; color:white; }}
pre {{ white-space:pre-wrap; overflow-wrap:anywhere; background:#111827; padding:14px; border-radius:10px; }}
details {{ margin:10px 0; }} summary {{ cursor:pointer; font-weight:650; }}
.lesson {{ background:#111827; border-radius:10px; padding:12px; margin:10px 0; }}
.warning {{ background:#451a03; border:1px solid #92400e; padding:12px; border-radius:10px; }}
.success {{ background:#052e16; border:1px solid #166534; padding:12px; border-radius:10px; }}
</style>
</head>
<body><div class="container">{body}</div></body></html>"""


def render_index(output_dir: Path) -> str:
    rows = []
    for path in safe_packet_files(output_dir):
        try:
            packet = load_packet(path)
        except Exception as exc:
            rows.append(f'<div class="card">{html.escape(path.name)} — error: {html.escape(str(exc))}</div>')
            continue
        status = packet.get("status", "?")
        summary = packet.get("run_summary") or {}
        cls = "final" if status == STATUS_FINALIZED else "pending"
        rows.append(
            '<div class="card">'
            f'<span class="badge {cls}">{html.escape(status)}</span>'
            f'<b>Run {packet.get("source_run")}</b> — {html.escape(str(summary.get("result")))} '
            f'Act {html.escape(str(summary.get("act")))} Floor {html.escape(str(summary.get("floor")))}'
            f'<div style="margin-top:10px"><a href="/review?file={quote(path.name)}">Open review →</a></div>'
            '</div>'
        )
    if not rows:
        rows = ['<div class="card muted">No feedback packets yet. Finish a C2 run and refresh this page.</div>']
    body = (
        '<h1>C2 Human Feedback</h1>'
        '<p class="muted">Review the run trajectory. Either approve the initial reflection exactly as-is, '
        'or write your own teaching in natural language. Your teaching will be stored verbatim; the LLM may '
        'only tag it for retrieval and may not rewrite its strategic content.</p>'
        + ''.join(rows)
    )
    return page_shell("C2 Human Feedback", body)


def fmt_value(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def render_review(path: Path, packet: dict, saved: bool = False) -> str:
    summary = packet.get("run_summary") or {}
    metrics = [
        ("Result", summary.get("result")),
        ("Act / Floor", f'{summary.get("act")} / {summary.get("floor")}'),
        ("Score", summary.get("score")),
        ("HP", f'{summary.get("current_hp")}/{summary.get("max_hp")}'),
        ("Deck size", summary.get("final_deck_size")),
        ("Keys", summary.get("final_keys")),
    ]
    metric_html = ''.join(
        f'<div class="metric"><small>{html.escape(label)}</small><b>{html.escape(fmt_value(value))}</b></div>'
        for label, value in metrics
    )

    key_events = packet.get("key_events") or []
    if key_events:
        events_html = ''.join(
            '<div class="event">'
            f'<b>{html.escape(str(e.get("title")))}</b> '
            f'<span class="muted">Act {html.escape(str(e.get("act")))} Floor {html.escape(str(e.get("floor")))}</span>'
            f'<div>{html.escape(str(e.get("detail")))}</div>'
            '</div>'
            for e in key_events
        )
    else:
        events_html = '<p class="muted">No automatic review candidates were flagged.</p>'

    timeline_html = []
    for t in packet.get("strategic_timeline") or []:
        alts = t.get("alternatives") or []
        alt_html = '<br>'.join(html.escape(str(x)) for x in alts)
        timeline_html.append(
            '<div class="timeline-item">'
            f'<b>Act {html.escape(str(t.get("act")))} Floor {html.escape(str(t.get("floor")))}</b> '
            f'<span class="badge">{html.escape(str(t.get("decision_type")))}</span><br>'
            f'HP {html.escape(str(t.get("hp")))}/{html.escape(str(t.get("max_hp")))} · '
            f'Gold {html.escape(str(t.get("gold")))}<br>'
            f'<b>Selected:</b> {html.escape(str(t.get("selected_action")))}'
            + (f'<details><summary>Alternatives</summary><div class="muted">{alt_html}</div></details>' if alts else '')
            + '</div>'
        )

    reflection = packet.get("initial_reflection") or {}
    lessons_html = []
    for i, lesson in enumerate(reflection.get("lessons") or [], start=1):
        lessons_html.append(
            '<div class="lesson">'
            f'<b>{i}. [{html.escape(str(lesson.get("category")))}] {html.escape(str(lesson.get("title")))}</b><br>'
            f'<span class="muted">When: {html.escape(str(lesson.get("situation")))}</span><br>'
            f'{html.escape(str(lesson.get("lesson")))}'
            '</div>'
        )

    trajectory_text = ""
    try:
        trajectory_path = Path(str(packet.get("trajectory_file") or ""))
        if trajectory_path.exists():
            trajectory_text = trajectory_path.read_text(encoding="utf-8")
    except Exception:
        trajectory_text = ""

    feedback = str(packet.get("human_feedback") or "")
    status = packet.get("status")
    finalized = status == STATUS_FINALIZED
    save_banner = '<div class="success">Review finalized. The controller can now store the approved reflection or authoritative teaching and continue.</div>' if saved else ''

    review_decision = str(packet.get("review_decision") or "")
    if finalized:
        if review_decision == "APPROVE_INITIAL":
            form_html = (
                '<div class="success"><b>Initial reflection approved as-is.</b></div>'
                '<p class="muted">Its original lessons are stored unchanged.</p>'
            )
        else:
            form_html = (
                '<div class="success"><b>Authoritative human teaching finalized.</b></div>'
                '<p class="muted">The text below is the exact strategic guidance stored for future runs.</p>'
                f'<pre>{html.escape(feedback)}</pre>'
            )
    else:
        form_html = f"""
<div class="warning">
<b>Choose one:</b><br>
1. If the initial reflection is already correct, approve it unchanged.<br>
2. Otherwise, write your own teaching naturally. <b>Your wording is authoritative and will be stored verbatim.</b>
The LLM is allowed only to assign retrieval metadata such as category and applies_to; it may not rewrite your strategy.
</div>
<form method="post" action="/submit?file={quote(path.name)}">
<textarea id="feedback" name="feedback" placeholder="Write exactly what you want the agent to remember. Example: 39/56 HP is fine here. The real mistake was taking Bites without Blood Vial. Do not take Bites unless you have Blood Vial.">{html.escape(feedback)}</textarea>
<div style="margin-top:10px">
<button type="submit" name="review_decision" value="APPROVE_INITIAL" class="secondary" formnovalidate onclick="return confirm('Approve the initial reflection exactly as-is?');">Approve initial reflection as-is</button>
<button type="submit" name="review_decision" value="HUMAN_TEACHING" class="primary" onclick="return confirm('Store your teaching verbatim and finalize this review?');">Store my teaching verbatim</button>
</div>
</form>
"""

    body = f"""
<a href="/">← All runs</a>
<h1>Run {html.escape(str(packet.get('source_run')))} Review</h1>
{save_banner}
<div class="grid">{metric_html}</div>
<div class="card"><h2>Potentially important events</h2><p class="muted">These are review candidates, not labels of mistakes.</p>{events_html}</div>
<div class="card"><h2>Strategic timeline</h2><div class="timeline">{''.join(timeline_html) or '<span class="muted">No strategic actions found.</span>'}</div></div>
<details class="card"><summary>Full compact trajectory</summary><pre>{html.escape(trajectory_text) if trajectory_text else 'Trajectory file not available.'}</pre></details>
<div class="card"><h2>LLM initial reflection</h2><p>{html.escape(str(reflection.get('summary') or ''))}</p>{''.join(lessons_html)}</div>
<div class="card"><h2>Your trajectory feedback</h2>{form_html}</div>
<details class="card"><summary>Files / metadata</summary><pre>{html.escape(json.dumps({k: packet.get(k) for k in ['source_run_id','trajectory_file','initial_reflection_file','review_version','review_decision','status']}, indent=2))}</pre></details>
"""
    return page_shell(f"Run {packet.get('source_run')} Review", body)


class FeedbackHandler(BaseHTTPRequestHandler):
    output_dir: Path = Path(".")

    def log_message(self, format, *args):
        # Keep terminal output concise.
        return

    def send_html(self, body: str, status: int = 200):
        payload = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def resolve_packet(self, filename: str) -> Path:
        # Only allow a basename matching our generated packet pattern.
        name = Path(filename).name
        if name != filename or not name.startswith("run_") or not name.endswith("_feedback_review.json"):
            raise ValueError("Invalid packet filename")
        path = self.output_dir / name
        if not path.exists():
            raise FileNotFoundError(name)
        return path

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self.send_html(render_index(self.output_dir))
            return
        if parsed.path == "/review":
            try:
                filename = parse_qs(parsed.query).get("file", [""])[0]
                path = self.resolve_packet(filename)
                packet = load_packet(path)
                saved = parse_qs(parsed.query).get("saved", ["0"])[0] == "1"
                self.send_html(render_review(path, packet, saved=saved))
            except Exception as exc:
                self.send_html(page_shell("Error", f'<h1>Error</h1><pre>{html.escape(str(exc))}</pre>'), 400)
            return
        self.send_html(page_shell("Not found", "<h1>Not found</h1>"), 404)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/submit":
            self.send_html(page_shell("Not found", "<h1>Not found</h1>"), 404)
            return
        try:
            filename = parse_qs(parsed.query).get("file", [""])[0]
            path = self.resolve_packet(filename)
            length = int(self.headers.get("Content-Length", "0"))
            if length > 200_000:
                raise ValueError("Feedback payload is unexpectedly large.")
            form = parse_qs(self.rfile.read(length).decode("utf-8"))
            feedback = str(form.get("feedback", [""])[0]).strip()
            review_decision = str(
                form.get("review_decision", [""])[0]
            ).strip().upper()
            if review_decision not in {"APPROVE_INITIAL", "HUMAN_TEACHING"}:
                raise ValueError("Choose either approve-initial or human-teaching mode.")
            if review_decision == "HUMAN_TEACHING" and not feedback:
                raise ValueError("Human teaching cannot be empty.")
            if review_decision == "APPROVE_INITIAL":
                feedback = ""

            packet = load_packet(path)
            if packet.get("status") == STATUS_FINALIZED:
                raise ValueError("This review has already been finalized.")
            packet["review_decision"] = review_decision
            packet["human_feedback"] = feedback
            packet["status"] = STATUS_FINALIZED
            packet["finalized_at"] = utc_now_iso()
            atomic_write_json(path, packet)

            self.send_response(303)
            self.send_header("Location", f"/review?file={quote(path.name)}&saved=1")
            self.end_headers()
        except Exception as exc:
            self.send_html(page_shell("Error", f'<h1>Error</h1><pre>{html.escape(str(exc))}</pre>'), 400)


def main():
    parser = argparse.ArgumentParser(description="Local browser UI for C2 trajectory feedback")
    parser.add_argument("--output-dir", default="reflection/condition_c2_outputs")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    FeedbackHandler.output_dir = output_dir

    server = ThreadingHTTPServer((args.host, args.port), FeedbackHandler)
    print(f"C2 feedback UI: http://{args.host}:{args.port}")
    print(f"Watching: {output_dir}")
    print("Keep this terminal open while running Condition C2.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
