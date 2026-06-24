# Law Search — Legal Research Desk (web front end)

The **"glass factory"** web front end for the Legal Research Desk: a Flask app that
streams a legal-research run live in the browser as it moves through a fixed
**3-call pipeline** — *plan → retrieve → review → synthesize*.

> This repository is the **web layer only** (`app.py` + the single-page UI). It serves
> and renders the interface; it does **not** include the retrieval engine or the legal
> corpus, which run alongside it. On its own the UI loads, but starting a run needs the
> backend wired in (see *Backend dependency* below).

## What it does

The user states a legal question or contract-review request. The backend then runs a
deterministic three-model-call pipeline (no convergent loop):

1. **Plan** — frame the request (intent · subject · constraints · deliverable) and plan
   the *entire* retrieval query battery up front.
2. **Retrieve** — run every planned query locally over the corpus (semantic + keyword),
   dedupe, and read the top-ranked documents in full. *No model calls.*
3. **Review** — one batch extraction of every citation-bound proposition.
4. **Synthesize** — one call writes the deliverable (a legal memo, clause table, etc.).

The browser opens a Server-Sent-Events stream and renders each stage as it happens:
the frame, the plan spine, a **Plan → Retrieve → Review → Synthesize** pipeline tracker,
the corpus queries with hit counts, the extracted claims with provenance, and the final
rendered report. The event log is reconnection-safe — reloading mid-run replays it.

## Layout

```
app.py                 Flask server: SSE streaming, run control, report export (MD/HTML/PDF)
templates/index.html   The single-page UI (vanilla JS, no build step)
static/marked.min.js   Inlined Markdown renderer (offline + PDF-safe)
```

## Endpoints

| Route | Purpose |
|-------|---------|
| `GET /` | The single-page app |
| `GET /api/config` | Live system health — retrieval sources, corpus stats, GPU, pipeline policy |
| `POST /api/start` · `POST /api/stop/<id>` | Start a run (goal + quick/deep) · interrupt and force synthesis |
| `GET /api/stream/<id>` | Live SSE event stream (replay-from-zero on reconnect) |
| `GET /api/runs` · `GET /api/runs/<id>` | List / load past runs |
| `GET /api/runs/<id>/report/{markdown,html,view,pdf}` | Export the report (PDF via headless Chrome) |

## Running

```bash
pip install flask
python app.py            # serves on http://localhost:5080
```

### Backend dependency

`app.py` imports a retrieval `engine` module and a `catalog_search` module (the corpus
layer), which are **not** part of this repository. Without them the UI still loads and
`/api/config` reports the backend as unreachable, but a run cannot start. Point the import
path at your engine + corpus to make it fully functional.

## License

No license specified — all rights reserved by the author unless stated otherwise.
