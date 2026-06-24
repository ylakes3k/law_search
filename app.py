#!/usr/bin/env python3
"""
Research App - "glass factory" web front end for the multi-source research engine.

Design goals:
- The SSE stream carries STRUCTURED events (not just status strings) so the front
  end can render the Director's reasoning live.
- Reconnection-safe: each run keeps an in-memory EVENT LOG. A reconnecting client
  replays the whole log (front end applies events idempotently), so a 20-minute run
  survives a page reload.
- Standalone: no orchestrator, only Flask + the local engine. PDF export uses the
  system Chrome headless (already on the box) so there is no new Python dependency.
"""

import os
import json
import time
import tempfile
import threading
import subprocess
from datetime import datetime
from pathlib import Path

from flask import Flask, render_template, request, jsonify, Response, send_file
import urllib.request
import engine
import catalog_search  # corpus stats for /api/config (sys.path set by `import engine`)

app = Flask(__name__)


def _unique_run_id():
    """Second-resolution id, de-duplicated so two quick starts never collide."""
    base = datetime.now().strftime("%Y%m%d_%H%M%S")
    rid, n = base, 1
    while (engine.DATA_DIR / f"run_{rid}.json").exists() or rid in active_runs:
        n += 1
        rid = f"{base}_{n}"
    return rid

# run_id -> {"events": [..], "done": bool, "lock": Lock, "run_meta": {...}}
active_runs = {}


def _new_run_state(run_id, goal, posture):
    return {
        "events": [],
        "done": False,
        "lock": threading.Lock(),
        "goal": goal,
        "posture": posture,
        "started_at": time.time(),
        "stop": threading.Event(),
    }


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/config")
def get_config():
    """The SYSTEM CONFIGURATION surface: which corpus retrieval tools are wired in + their
    live status, what's in the corpus, and the depth/stopping policy. The user SEES this."""
    sources = [
        {"key": "semantic", "name": "Semantic", "via": "BGE-M3 + Qdrant + cross-encoder rerank",
         "role": "conceptual / analogical retrieval — leading authority & fact-pattern analogies"},
        {"key": "keyword", "name": "Keyword", "via": "SQLite FTS5 (BM25)",
         "role": "exact terms of art, citations, statutory language, date-bounded sweeps"},
    ]
    # Qdrant reachable? (semantic depends on it)
    try:
        with urllib.request.urlopen("http://localhost:6401/collections", timeout=3) as r:
            cols = json.loads(r.read().decode("utf-8"))
        names = [c.get("name") for c in cols.get("result", {}).get("collections", [])]
        sources[0]["status"] = "ready" if "corpus" in names else "no 'corpus' collection"
    except Exception:
        sources[0]["status"] = "Qdrant unreachable (:6401)"
    # Catalog present?
    corpus = {}
    try:
        corpus = catalog_search.stats()
        sources[1]["status"] = "ready"
    except Exception as e:
        sources[1]["status"] = f"catalog error: {e}"
    # GPU present? (semantic reranking is much faster on GPU)
    gpu = None
    try:
        import torch
        gpu = bool(torch.cuda.is_available())
        sources[0]["status"] = sources[0].get("status", "") + (" · GPU" if gpu else " · CPU only (slow)")
    except Exception:
        pass
    return jsonify({
        "sources": sources,
        "corpus": {
            "total": corpus.get("total"),
            "full_text": corpus.get("full_text"),
            "transport": corpus.get("transport"),
            "by_juris": corpus.get("by_juris"),
            "top_courts": corpus.get("top_courts"),
        },
        "gpu": gpu,
        "policy": {
            "summary": ("A fixed 3-call pipeline — no loop. The model frames the request and "
                        "plans the ENTIRE query battery up front (call 1); every planned query "
                        "is run locally over the corpus and the top-ranked documents are read in "
                        "full; one batch extraction pulls every citation-bound proposition "
                        "(call 2); one synthesis writes the deliverable (call 3)."),
            "postures": {
                "quick": "Tight plan; fewer targeted queries; lean coverage for a focused question.",
                "deep": "Thorough plan; full query battery across statute, case law, contractual practice, jurisdiction and both parties' positions.",
            },
            "safety_ceiling": engine.HARD_CEILING,
            "safety_note": (f"Retrieval reads the top {engine.REVIEW_FULLTEXT_CAP} documents in full "
                            "(by retrieval score); the rest are weighed as snippets. There is no "
                            "convergent loop — the optional completeness gate is off by default."),
            "stop_control": "A user can press STOP / WRAP UP NOW to interrupt retrieval and force synthesis from what's gathered.",
        },
    })


@app.route("/api/start", methods=["POST"])
def start_research():
    data = request.json or {}
    goal = data.get("goal", "").strip()
    posture = data.get("posture", "deep")
    if posture not in ("quick", "deep"):
        posture = "deep"
    if not goal:
        return jsonify({"error": "Goal is required"}), 400

    run_id = _unique_run_id()
    state = _new_run_state(run_id, goal, posture)
    active_runs[run_id] = state

    def append_event(ev):
        ev = dict(ev)
        ev["t"] = time.time() - state["started_at"]
        with state["lock"]:
            state["events"].append(ev)

    def run_in_background():
        try:
            engine.run_research(
                goal=goal,
                posture=posture,
                run_id=run_id,
                on_status=lambda m: append_event({"type": "status", "message": m}),
                on_event=append_event,
                should_stop=state["stop"].is_set,
            )
        except Exception as e:  # noqa: BLE001
            append_event({"type": "run_error", "error": str(e)})
        finally:
            append_event({"type": "done"})
            with state["lock"]:
                state["done"] = True

    threading.Thread(target=run_in_background, daemon=True).start()
    return jsonify({"run_id": run_id, "posture": posture})


@app.route("/api/stop/<run_id>", methods=["POST"])
def stop_run(run_id):
    """User STOP / WRAP UP NOW: end a live run and force synthesis from what's gathered."""
    state = active_runs.get(run_id)
    if not state:
        return jsonify({"error": "Run not active"}), 404
    state["stop"].set()
    return jsonify({"ok": True, "run_id": run_id})


@app.route("/api/stream/<run_id>")
def stream_events(run_id):
    """
    Replay the full structured event log, then stream new events live. Replaying
    from 0 makes reconnection trivial: the front end seeds from persisted JSON and
    applies streamed events idempotently (keyed by pass), so overlap is harmless.
    """
    def generate():
        # Case 1: a live (or just-finished) run we have an event log for.
        state = active_runs.get(run_id)
        if state is not None:
            idx = 0
            while True:
                with state["lock"]:
                    events = state["events"][idx:]
                    done = state["done"]
                    idx = len(state["events"])
                for ev in events:
                    yield f"data: {json.dumps(ev)}\n\n"
                if done and not events:
                    break
                if not events:
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
                    time.sleep(0.4)
            return
        # Case 2: no live log (process restarted, or opened a historical run).
        # Reconstruct terminal events from the persisted file so the page still fills.
        try:
            run = engine.ResearchRun.load(run_id)
            yield f"data: {json.dumps({'type': 'reconstructed', 'status': run.status})}\n\n"
            if run.synthesis:
                yield f"data: {json.dumps({'type': 'synthesis_complete', 'synthesis': run.synthesis})}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except FileNotFoundError:
            yield f"data: {json.dumps({'type': 'error', 'message': 'run not found'})}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/runs")
def list_runs():
    return jsonify(engine.ResearchRun.list_all())


@app.route("/api/runs/<run_id>")
def get_run(run_id):
    try:
        run = engine.ResearchRun.load(run_id)
        d = run.to_dict()
        d["live"] = run_id in active_runs and not active_runs[run_id]["done"]
        return jsonify(d)
    except FileNotFoundError:
        return jsonify({"error": "Run not found"}), 404


@app.route("/api/runs/<run_id>/report/markdown")
def get_report_markdown(run_id):
    try:
        run = engine.ResearchRun.load(run_id)
        return Response(engine.generate_report_markdown(run), mimetype="text/markdown",
                        headers={"Content-Disposition": f"attachment; filename=research_{run_id}.md"})
    except FileNotFoundError:
        return jsonify({"error": "Run not found"}), 404


@app.route("/api/runs/<run_id>/report/html")
def get_report_html(run_id):
    try:
        run = engine.ResearchRun.load(run_id)
        return Response(engine.generate_report_html(run), mimetype="text/html",
                        headers={"Content-Disposition": f"attachment; filename=research_{run_id}.html"})
    except FileNotFoundError:
        return jsonify({"error": "Run not found"}), 404


@app.route("/api/runs/<run_id>/report/view")
def view_report_html(run_id):
    try:
        run = engine.ResearchRun.load(run_id)
        return Response(engine.generate_report_html(run), mimetype="text/html")
    except FileNotFoundError:
        return jsonify({"error": "Run not found"}), 404


def _find_chrome():
    for c in ("google-chrome", "google-chrome-stable", "chromium-browser", "chromium"):
        path = subprocess.run(["which", c], capture_output=True, text=True).stdout.strip()
        if path:
            return path
    return None


@app.route("/api/runs/<run_id>/report/pdf")
def get_report_pdf(run_id):
    """Render the HTML report to PDF using system Chrome headless (no Python dep)."""
    try:
        run = engine.ResearchRun.load(run_id)
    except FileNotFoundError:
        return jsonify({"error": "Run not found"}), 404
    chrome = _find_chrome()
    if not chrome:
        return jsonify({"error": "No Chrome/Chromium available for PDF rendering"}), 500
    html = engine.generate_report_html(run)
    with tempfile.TemporaryDirectory() as tmp:
        html_path = os.path.join(tmp, "report.html")
        pdf_path = os.path.join(tmp, "report.pdf")
        with open(html_path, "w") as f:
            f.write(html)
        subprocess.run(
            [chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
             "--no-pdf-header-footer", f"--print-to-pdf={pdf_path}", f"file://{html_path}"],
            capture_output=True, timeout=60,
        )
        if not os.path.exists(pdf_path):
            return jsonify({"error": "PDF generation failed"}), 500
        return send_file(pdf_path, mimetype="application/pdf", as_attachment=True,
                         download_name=f"research_{run_id}.pdf")


if __name__ == "__main__":
    print("Starting Legal Research Desk (glass factory)...")
    print("Open http://localhost:5080 in your browser")
    app.run(host="0.0.0.0", port=5080, debug=False, threaded=True)
