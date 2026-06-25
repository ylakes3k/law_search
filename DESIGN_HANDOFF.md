# Design Hand-off — Legal Research Desk (front end)

**Read this first.** You're getting the web front end of a legal-research tool with **no live
backend**. That's fine — this document gives you (1) the whole system in plain language,
(2) every screen and every region broken down, (3) the exact content that belongs in each
slot, and (4) a complete set of **realistic placeholder content** you can hard-code so the UI
looks alive while you design. Anywhere you see a 🧩 **PLACEHOLDER**, that's copy you can paste
straight into the markup to fill the region.

The current UI lives in **`templates/index.html`** (a single file: markup + CSS + vanilla JS,
no build step) and **`static/marked.min.js`** (renders Markdown). `app.py` is the server that
feeds it — you don't need it to design, but this doc explains what it *would* send.

---

## Contents

1. [What this product is (1 minute)](#1-what-this-product-is)
2. [The pipeline the UI visualizes](#2-the-pipeline-the-ui-visualizes)
3. [File & layout map](#3-file--layout-map)
4. [The four screens](#4-the-four-screens)
5. [Screen-by-screen anatomy + placeholder content](#5-screen-by-screen-anatomy)
6. [The data model (full mock fixture)](#6-the-data-model--full-mock-fixture)
7. [Live states & animation (how it streams)](#7-live-states--animation)
8. [Visual language (colors, tags, badges, labels)](#8-visual-language)
9. [How to run it in "demo mode" with no backend](#9-demo-mode-no-backend)
10. [What we'd love you to improve](#10-designer-todo)

---

## 1. What this product is

A lawyer types a legal question or contract-review request. The system researches it against a
large corpus of Canadian/US transportation-law documents (case law, statutes, regulations,
tribunal decisions) and writes a finished **deliverable** — usually a legal memo.

The signature idea is the **"glass factory"**: the user watches the work happen live. Nothing is
a black box. As the system frames the request, plans its research, pulls documents, extracts
legal propositions, and writes the memo, each step streams into the page in real time. A page
reload mid-run replays everything, so a long run survives a refresh.

**Tone of the product:** a senior lawyer's workspace — precise, calm, authoritative, dark-themed,
information-dense but legible. Not playful, not consumer-y. Think Bloomberg terminal meets a
clean legal memo.

---

## 2. The pipeline the UI visualizes

The backend runs a fixed **3-call pipeline** (three calls to the AI model, no looping). The whole
UI is organized around these four stages, in order:

```
   PLAN            RETRIEVE             REVIEW            SYNTHESIZE
 (1 model call)   (no model calls)   (1 model call)    (1 model call)
 frame + plan  →  run every query  →  extract every  →  write the
 the entire       over the corpus,    citation-bound     deliverable
 research up       dedupe, read top    legal claim       (the memo)
 front             docs in full
```

Everything the user sees maps onto these stages. The **Pipeline tracker** (a 4-node progress bar)
is the spine of the live view. Keep that plan → retrieve → review → synthesize order sacred — it's
the product's mental model.

---

## 3. File & layout map

```
app.py                 Backend server (not needed for design). Sends the live data.
templates/index.html   THE UI you're designing. Markup + CSS + JS in one file.
static/marked.min.js   Markdown → HTML renderer (used for the final report + analysis blocks).
```

**Page shell** (always present):

```
┌────────────┬──────────────────────────────────────────────┐
│            │                                              │
│  SIDEBAR   │                 MAIN AREA                    │
│  (aside)   │   (one of four screens shown at a time)      │
│            │                                              │
│  • brand   │                                              │
│  • nav     │                                              │
│  • current │                                              │
│    run chip│                                              │
└────────────┴──────────────────────────────────────────────┘
```

- **Sidebar** (`<aside>`): logo/brand, three nav items (Investigate / Runs / Sources & Settings),
  and a "Current run" chip that appears while a run is active (click to jump back to it).
- **Main area** (`<main>`): shows exactly one of the four screens below.

---

## 4. The four screens

| Screen | DOM id | What it's for |
|--------|--------|---------------|
| **Investigate** | `#view-investigate` | The landing/command screen. Enter a goal, pick a posture, start a run. Also shows system config. |
| **Run** | `#view-run` | The live "glass factory" + the final report. This is the heart of the product. |
| **Runs** | `#view-runs` | History list of past runs. |
| **Sources & Settings** | `#view-settings` | What the system is and the rules it follows. |

Most of your design effort belongs in **Investigate** and **Run**.

---

## 5. Screen-by-screen anatomy

For each region: **what it is**, the **DOM hook** (so you know where content lands), the **states**
it can be in, and 🧩 **placeholder content** to fill it.

### 5.1 Sidebar (`<aside>`)

- **Brand** — mark "L" + "Legal Research Desk" + subtitle.
  🧩 Title: `Legal Research Desk` · Subtitle: `legal corpus · 3-call pipeline`
- **Nav items** — `Investigate` (✦), `Runs` (◷), `Sources & Settings` (⚙). One is "active" at a time.
- **Current-run chip** (`#currentchip`, hidden until a run starts) — a live dot + truncated goal.
  🧩 Label: `Current run` · Goal: `Carrier liability for misdelivery to the wrong consignee…`

### 5.2 Investigate screen (`#view-investigate`)

- **Page heading + subtitle**
  🧩 H1: `New investigation`
  🧩 Sub: *"State a legal question or contract-review request. The model frames it, plans the entire
  research effort, retrieves the whole query battery over the legal corpus, then extracts
  citation-bound propositions and writes the deliverable — **three model calls, no loop**:
  plan → retrieve → review → synthesize."*

- **Goal input** (`<textarea id="goal">`) — the main input.
  🧩 Placeholder: *"e.g. When a motor carrier delivers cargo to the wrong consignee, what is its
  liability and can it rely on the $4.41/kg cap under O. Reg. 643/05 if no value was declared on the
  bill of lading? Provide a legal memo."*

- **Posture toggle** (`#postureSeg`) — two segmented buttons.
  🧩 **⚡ Quick** — *"tight plan · fewer targeted queries"*
  🧩 **🔬 Deep** — *"thorough plan · full query battery across every dimension"* (default = on)
  🧩 Label hint: *"nudges plan breadth & how many corpus queries get planned up front"*

- **Start button** (`#startbtn`) 🧩 `Start investigation →`

- **System configuration card** (`#configCard`) — shows the retrieval sources + the depth policy.
  See §5.6 for its content (same component is reused on the Settings screen).

### 5.3 Run screen (`#view-run`) — the main event

This screen is built top-to-bottom as: **Run header → Frame → Plan → Pipeline tracker → Retrieval &
extraction → Report.** Each maps to a pipeline stage. Walk through them in order.

#### (a) Run header (`.runhead`, sticky)

A goal line + a row of status "pills" + a Stop button.

- **Goal** (`#rh-goal`) 🧩 *"Under Canadian law, when a motor carrier delivers cargo to the wrong
  consignee, what is its liability and can it rely on the $4.41/kg cap under O. Reg. 643/05…"*
- **Pills:**
  - **Stage** (`#rh-stage`) — current stage with a spinner while live. 🧩 values cycle through:
    `Framing & planning` → `Retrieving corpus` → `Reading sources in full` → `Extracting claims`
    → `Writing deliverable` → `Complete`
  - **Posture** (`#rh-posture`) 🧩 `deep`
  - **Queries** (`#rh-pass`) 🧩 `21 queries`
  - **Plan** (`#rh-plan`) 🧩 `plan 8/8`
  - **Elapsed** (`#rh-elapsed`) 🧩 `7m 20s`
  - **Sources** (`#rh-sources`) 🧩 two tags: `Semantic` `Keyword`
- **Stop button** (`#stopbtn`) 🧩 `■ Stop / wrap up now` (hidden once the run is done)

#### (b) Frame card (`#framebox`) — "read this first; veto if it's a misread"

The system's reconstruction of what the user actually wants. Four labeled rows.

- 🧩 **Intent:** *"Assess a motor carrier's exposure for delivering cargo to the wrong consignee and
  determine whether the statutory liability cap still applies; produce a predictive legal memo."*
- 🧩 **Subject:** *"Trucking (motor carrier) · carrier–shipper relationship · liability for misdelivery
  to the wrong consignee, and survival of the O. Reg. 643/05 $4.41/kg limitation where no value was
  declared on the bill of lading."*
- 🧩 **Constraints** (rendered as chips, each prefixed "filter:"):
  `Ontario (provincial regime)` · `mode: road / motor carrier` · `doc types: case law + regulation`
  · `contract carrier under Uniform Conditions` · `no value declared → cap in play`
  · `domestic shipment (Carmack not engaged)`
- 🧩 **Deliverable:** *"Legal memo — Question Presented → Short Answer → Discussion (IRAC) →
  Conclusion → Qualifications & Limitations."*

*Loading state* 🧩 `reconstructing intent…`

#### (c) Plan spine (`#planbox`) — the research plan

A progress header + a list of plan items. Each item is one component of the deliverable.

- **Header:** title `Plan`, a progress bar, and a count 🧩 `8 of 8 answered`
- **"Now pursuing" line** (only while running) 🧩 `▸ now pursuing: the $4.41/kg cap analysis`
- **Plan items** — each: a check mark (✓ answered / ○ open), an id (`p1`), the question, an optional
  "why" line, an optional "discovered gap" tag, and an "answered · pass 1" note.
  🧩 sample items:
  - `p1` ✓ **Does delivery to the wrong consignee constitute misdelivery/conversion that breaches the
    contract of carriage?** — *why: primary law (case law) → Discussion §A*
  - `p2` ✓ **Does the $4.41/kg cap under O. Reg. 643/05, Sched. 1 s. 9 apply where no value was
    declared on the bill of lading?** — *why: primary law (regulation + case) → Discussion §B*
  - `p3` ✓ **Can a limitation clause survive a fundamental breach / deviation such as misdelivery
    (the Tercon framework)?** — *why: enforceability → Discussion §C*
  - `p4` ✓ **Is the shipment provincial or extra-provincial, and which Uniform Conditions govern?**
  - `p5` ✓ **What counts as a "declared value" — does an invoice suffice, or must it be on the face
    of the bill?**
  - `p6` ✓ **Who has title to sue the carrier — shipper, consignee, or owner?**
  - `p7` ✓ **What common-carrier defences (act of God, inherent vice, shipper's default) apply?**
  - `p8` ✓ *(discovered gap)* **On a cross-border shipment, would Carmack or provincial law govern,
    and how would the cap differ?**

*Loading state* 🧩 `drafting plan…`

> Note the **"discovered gap"** tag (amber): the plan can grow during a run. Design a clear "this was
> added mid-research" treatment.

#### (d) Pipeline tracker (`#pipeline`) — THE signature component

A horizontal 4-node tracker. Each node = one pipeline stage, with a sublabel that fills in as the
stage produces results. Nodes move through three states: **future** (grey, shows its number),
**active** (pulsing, brand color), **done** (green ✓).

🧩 Four nodes, left to right:

| # | Label | Sublabel (placeholder) |
|---|-------|------------------------|
| 1 | **Plan** | `8 components` |
| 2 | **Retrieve** | `21 queries · 14 read full` |
| 3 | **Review** | `30 claims` |
| 4 | **Synthesize** | `deliverable ready` |

This is the most important thing to make beautiful. It's the product's heartbeat.

#### (e) Retrieval & extraction (`#timeline`)

A single expandable card (the run now has exactly one "pass"). Header + body.

- **Header:** a number badge (`1`, becomes ✓ when done), a title, and a count badge.
  🧩 Title: `Retrieval & extraction` · Badge: `21 queries · 30 claims ▾`
- **Body, in order:**

  **i. Retrieval summary line** (a highlighted one-liner)
  🧩 *"Planned **21** corpus queries → **173** results retrieved → top **14** read in full → one batch
  extraction"*

  **ii. Retrieval — corpus queries (`N`)** — a list of every query that ran. Each row: a **source tag**
  (Semantic = indigo, Keyword = teal), the query text, an optional "why", and a result count.
  🧩 sample rows:
  - `Semantic` — *"motor carrier delivers freight to the wrong consignee; misdelivery liability of a
    common carrier as bailee"* — why: *leading authority on misdelivery* — **8 results**
  - `Keyword` — *"misdelivery AND (\"bill of lading\" OR consignee OR \"wrong party\")"* — **8 results**
  - `Semantic` — *"Ontario Uniform Conditions of Carriage limitation of liability $4.41 per kilogram"*
    — **8 results**
  - `Keyword` — *"\"2016 ONCA 339\" OR (\"National Refrigeration\" AND Celadon)"* — **1 result**
  - `Keyword` — *"\"2010 SCC 4\" OR Tercon"* — **8 results**
  - `Semantic` — *"limitation clause survives fundamental breach; unconscionability; public policy"* —
    **8 results**
  - `Keyword` — *"\"declared value\" AND (\"bill of lading\" OR invoice OR cap OR limitation)"* —
    **6 results**
  - `Semantic` — *"cross-border shipment governing law; Carmack Amendment; Canada-origin full actual
    loss"* — **8 results**

  *(A failed/zero query renders red:* 🧩 `FAILED: 0 results` *— design this state too.)*

  **iii. Findings — claims (`N`) · `M` from full reads** — the extracted legal propositions. Each is a
  card with a **left border colored by confidence** (high = amber, medium = blue, low = grey), the
  claim text, a confidence badge, a "📄 full read" or "snippet" badge, and a source link.
  🧩 sample claims:
  - **[HIGH · 📄 full read]** *"In McGraw-Edison (Canada) Ltd v Direct Winters Transport Ltd, 1968
    CanLII 418 (ON SC), a carrier that delivered goods to the wrong party was held liable; misdelivery
    is a fundamental breach of the contract of carriage."* — ↗ canlii.org
  - **[HIGH · 📄 full read]** *"O. Reg. 643/05, Sched. 1, s. 9 caps a motor carrier's liability at
    $4.41/kg unless a higher value is declared by the consignor on the face of the bill of lading."* —
    ↗ ontario.ca
  - **[HIGH · 📄 full read]** *"In Tercon Contractors Ltd v British Columbia, 2010 SCC 4, the Court set
    a three-step test for exclusion clauses: (1) does the clause apply as a matter of interpretation;
    (2) was it unconscionable at formation; (3) should it be denied effect on public-policy grounds."*
    — ↗ canlii.org
  - **[HIGH · snippet]** *"The doctrine of fundamental breach no longer automatically voids a
    limitation clause; Tercon replaced it (2010 SCC 4 at paras 62–64) — the clause is tested on its
    terms and on public policy."* — ↗ canlii.org
  - **[MEDIUM · 📄 full read]** *"In National Refrigeration … v Celadon, 2016 ONCA 339, the $4.41/kg cap
    applied where the shipper failed to declare a value on the bill; an invoice value did not displace
    the cap."* — ↗ canlii.org
  - **[MEDIUM · snippet]** *"Consolidated Fastfrate Inc v Western Canada Council of Teamsters, 2009 SCC
    53 — a freight forwarder that contracts out interprovincial carriage is provincially regulated."* —
    ↗ canlii.org
  - **[LOW · snippet]** *"Some lower-court commentary suggests 'deviation' (gross route or handling
    departure) may still oust a limitation clause, but this is unsettled post-Tercon."* — ↗ canlii.org

  **iv. Threads opened** — leads the system noticed but treats as secondary (prefixed ⌥).
  🧩 *"Whether the pre-Tercon 'deviation' doctrine survives in cargo cases — worth a dedicated query."*
  🧩 *"Released-value vs declared-value distinction under US Carmack for cross-border lanes."*

  **v. Contradictions** — conflicting authority the system flagged (prefixed ⚠).
  🧩 *"One trial-level source treats misdelivery as automatically ousting the cap (deviation); the
  ONCA in Celadon holds the cap survives absent a Tercon ground. The appellate authority controls."*

  **vi. Reviewer analysis** — a short prose synthesis of this extraction (rendered as Markdown).
  🧩 *"The retrieved authority is internally consistent on liability: misdelivery is a clear breach and
  the carrier is liable as a near-insurer. The live question is the cap. The regulation and Celadon
  point the same way — the $4.41/kg cap holds where no value was declared — while Tercon supplies the
  only route to defeat it. The corpus is thin on verbatim regulatory text, flagged below."*

#### (f) Report (`#synth-slot`) — the deliverable

Appears when the run finishes. A stats strip, export buttons, and the rendered memo.

- **Section label** 🧩 `Report`
- **Summary strip** (stat tiles) 🧩 `21 corpus queries` · `8/8 plan answered` · `14 read in full`
  · `30 claims` · `2 sources` · `stopped: full plan retrieved & reviewed in one pass`
- **Export bar** 🧩 `⬇ Markdown` · `⬇ HTML` · `⬇ PDF` · `↗ Standalone`
- **Rendered memo** (Markdown → HTML). 🧩 use this sample as the body:

  > # MEMORANDUM OF LAW
  >
  > **RE:** Carrier liability for misdelivery to the wrong consignee, and survival of the $4.41/kg cap
  > under O. Reg. 643/05 where no value was declared on the bill of lading
  > **JURISDICTION:** Ontario (provincial regime under the *Highway Traffic Act*)
  >
  > ## Short Answer / Bottom Line
  > **Liability: Clearly established.** A motor carrier that delivers cargo to the wrong consignee is
  > liable to the shipper/owner; misdelivery is a fundamental breach of the contract of carriage, and
  > the standard bailee defences do not answer an affirmative misdelivery.
  > **The cap: Likely survives.** Absent a declared value on the face of the bill, O. Reg. 643/05 caps
  > liability at $4.41/kg, and post-*Tercon* the cap is not automatically defeated by the breach…
  >
  > ## Discussion
  > **A. The carrier is liable for misdelivery.** …
  > **B. The $4.41/kg cap applies where no value was declared.** …
  > **C. Whether the cap can be defeated — the *Tercon* framework.** …
  >
  > ## Qualifications & Limitations
  > This memo addresses Ontario domestic carriage. For cross-border (Canada–US) shipments, Carmack
  > may apply to US-origin freight…

*Loading state* 🧩 `Writing the deliverable from the extracted propositions…`

### 5.4 Runs screen (`#view-runs`)

A list of past runs. Each row: the goal, the sources used, the stop reason, posture + plan coverage,
date, and a status pill.
🧩 sample row: **"Carrier liability for misdelivery to the wrong consignee…"** · `Keyword · Semantic ·
pipeline` · right side: `deep · plan 8/8` · `2026-06-24` · status `completed`.
🧩 Empty state: *"No runs yet. Start one from Investigate."*

### 5.5 Sources & Settings (`#view-settings`)

Reuses the config card (§5.6).
🧩 Sub: *"The parts of the system and the rules it follows. Nothing here is hidden — this is exactly
how the pipeline works."*

### 5.6 Config card (used on Investigate + Settings) (`#configCard` / `#settingsCard`)

Two parts: the **sources** and the **policy**.

- **Sources** — two tiles:
  - 🧩 **Semantic** (tag indigo) — role: *"conceptual / analogical retrieval — leading authority &
    fact-pattern analogies"* — status: `ready · GPU` — via *"BGE-M3 + Qdrant + cross-encoder rerank"*
  - 🧩 **Keyword** (tag teal) — role: *"exact terms of art, citations, statutory language, date-bounded
    sweeps"* — status: `ready` — via *"SQLite FTS5 (BM25)"*
  - Status colors: green = ready, amber = degraded/fallback, red = unreachable.
    🧩 error example: `Qdrant unreachable (:6401)`
- **Policy block** 🧩:
  - Summary: *"A fixed 3-call pipeline — no loop. The model frames the request and plans the ENTIRE
    query battery up front (call 1); every planned query is run locally over the corpus and the
    top-ranked documents are read in full; one batch extraction pulls every citation-bound proposition
    (call 2); one synthesis writes the deliverable (call 3)."*
  - **Quick:** *"Tight plan; fewer targeted queries; lean coverage for a focused question."*
  - **Deep:** *"Thorough plan; full query battery across statute, case law, contractual practice,
    jurisdiction and both parties' positions."*
  - ⛑ note: *"Retrieval reads the top 14 documents in full (by retrieval score); the rest are weighed
    as snippets. There is no convergent loop."*
  - stop control: *"A user can press STOP / WRAP UP NOW to interrupt retrieval and force synthesis."*

---

## 6. The data model — full mock fixture

Hard-code this object to drive the whole Run screen without a backend. Field names match what the
backend actually sends, so if you keep them, swapping in real data later is trivial.

```json
{
  "id": "20260624_182817",
  "goal": "Under Canadian law, when a motor carrier delivers cargo to the wrong consignee, what is its liability and can it rely on the $4.41/kg cap under O. Reg. 643/05 if no value was declared on the bill of lading? Provide a legal memo.",
  "posture": "deep",
  "status": "completed",
  "stop_reason": "pipeline_complete",
  "frame": {
    "intent": "Assess a motor carrier's exposure for delivering cargo to the wrong consignee and whether the statutory liability cap still applies; produce a predictive legal memo.",
    "subject": "Trucking (motor carrier) · carrier–shipper relationship · liability for misdelivery to the wrong consignee, and survival of the O. Reg. 643/05 $4.41/kg limitation where no value was declared on the bill of lading.",
    "constraints": [
      "Ontario (provincial regime)",
      "mode: road / motor carrier",
      "doc types: case law + regulation",
      "contract carrier under provincial Uniform Conditions",
      "no value declared on the bill → cap in play",
      "domestic shipment (Carmack not engaged)"
    ],
    "deliverable": "Legal memo — Question Presented → Short Answer → Discussion (IRAC) → Conclusion → Qualifications & Limitations."
  },
  "plan": [
    {"id":"p1","question":"Does delivery to the wrong consignee constitute misdelivery/conversion that breaches the contract of carriage?","why":"primary law (case law) → Discussion §A","status":"answered","answered_pass":1,"origin":"initial"},
    {"id":"p2","question":"Does the $4.41/kg cap under O. Reg. 643/05, Sched. 1 s. 9 apply where no value was declared on the bill of lading?","why":"regulation + case → Discussion §B","status":"answered","answered_pass":1,"origin":"initial"},
    {"id":"p3","question":"Can a limitation clause survive a fundamental breach / deviation such as misdelivery (the Tercon framework)?","why":"enforceability → Discussion §C","status":"answered","answered_pass":1,"origin":"initial"},
    {"id":"p4","question":"Is the shipment provincial or extra-provincial, and which Uniform Conditions govern?","why":"governing regime → Discussion §A","status":"answered","answered_pass":1,"origin":"initial"},
    {"id":"p5","question":"What counts as a 'declared value' — does an invoice suffice, or must it be on the face of the bill?","why":"declared-value test → Discussion §B","status":"answered","answered_pass":1,"origin":"initial"},
    {"id":"p6","question":"Who has title to sue the carrier — shipper, consignee, or owner?","why":"standing → Discussion §D","status":"answered","answered_pass":1,"origin":"initial"},
    {"id":"p7","question":"What common-carrier defences (act of God, inherent vice, shipper's default) are available?","why":"defences → Discussion §A","status":"answered","answered_pass":1,"origin":"initial"},
    {"id":"p8","question":"On a cross-border shipment, would Carmack or provincial law govern, and how would the cap differ?","why":"cross-border → Qualifications","status":"answered","answered_pass":1,"origin":"discovered"}
  ],
  "passes": [
    {
      "pass_num": 1,
      "director_question": "misdelivery liability and the O. Reg. 643/05 cap",
      "searches": [
        {"source":"semantic","query":"motor carrier delivers freight to the wrong consignee; misdelivery liability of a common carrier as bailee","why":"leading authority on misdelivery","result_count":8,"error":null},
        {"source":"keyword","query":"misdelivery AND (\"bill of lading\" OR consignee OR \"wrong party\")","why":"exact-term sweep","result_count":8,"error":null},
        {"source":"semantic","query":"Ontario Uniform Conditions of Carriage limitation of liability $4.41 per kilogram","why":"the statutory cap","result_count":8,"error":null},
        {"source":"keyword","query":"\"2016 ONCA 339\" OR (\"National Refrigeration\" AND Celadon)","why":"the leading cap case","result_count":1,"error":null},
        {"source":"keyword","query":"\"2010 SCC 4\" OR Tercon","why":"the exclusion-clause framework","result_count":8,"error":null},
        {"source":"semantic","query":"limitation clause survives fundamental breach; unconscionability; public policy","why":"enforceability","result_count":8,"error":null},
        {"source":"keyword","query":"\"declared value\" AND (\"bill of lading\" OR invoice OR cap OR limitation)","why":"declared-value test","result_count":6,"error":null},
        {"source":"semantic","query":"cross-border shipment governing law; Carmack Amendment; Canada-origin full actual loss","why":"cross-border qualifier","result_count":8,"error":null}
      ],
      "read_urls": [
        "https://www.canlii.org/en/on/onsc/doc/1968/1968canlii418/1968canlii418",
        "https://www.canlii.org/en/ca/scc/doc/2010/2010scc4/2010scc4",
        "https://www.canlii.org/en/on/onca/doc/2016/2016onca339/2016onca339"
      ],
      "extracted_claims": [
        {"claim":"In McGraw-Edison (Canada) Ltd v Direct Winters Transport Ltd, 1968 CanLII 418 (ON SC), a carrier that delivered goods to the wrong party was held liable; misdelivery is a fundamental breach of the contract of carriage.","source_title":"1968 CanLII 418 (ON SC)","source_url":"https://www.canlii.org/en/on/onsc/doc/1968/1968canlii418/1968canlii418","confidence":"high","from_full_read":true},
        {"claim":"O. Reg. 643/05, Sched. 1, s. 9 caps a motor carrier's liability at $4.41/kg unless a higher value is declared by the consignor on the face of the bill of lading.","source_title":"O Reg 643/05, Sched 1, s 9","source_url":"https://www.ontario.ca/laws/regulation/050643","confidence":"high","from_full_read":true},
        {"claim":"In Tercon Contractors Ltd v British Columbia, 2010 SCC 4, the Court set a three-step test for exclusion clauses: (1) does the clause apply on interpretation; (2) was it unconscionable at formation; (3) should it be denied effect on public-policy grounds.","source_title":"2010 SCC 4","source_url":"https://www.canlii.org/en/ca/scc/doc/2010/2010scc4/2010scc4","confidence":"high","from_full_read":true},
        {"claim":"The doctrine of fundamental breach no longer automatically voids a limitation clause; Tercon replaced it (2010 SCC 4 at paras 62-64).","source_title":"2010 SCC 4","source_url":"https://www.canlii.org/en/ca/scc/doc/2010/2010scc4/2010scc4","confidence":"high","from_full_read":false},
        {"claim":"In National Refrigeration … v Celadon, 2016 ONCA 339, the $4.41/kg cap applied where the shipper failed to declare a value on the bill; an invoice value did not displace the cap.","source_title":"2016 ONCA 339","source_url":"https://www.canlii.org/en/on/onca/doc/2016/2016onca339/2016onca339","confidence":"medium","from_full_read":true},
        {"claim":"Consolidated Fastfrate Inc v Western Canada Council of Teamsters, 2009 SCC 53 — a freight forwarder that contracts out interprovincial carriage is provincially regulated.","source_title":"2009 SCC 53","source_url":"https://www.canlii.org/en/ca/scc/doc/2009/2009scc53/2009scc53","confidence":"medium","from_full_read":false},
        {"claim":"Some lower-court commentary suggests 'deviation' (gross route or handling departure) may still oust a limitation clause, but this is unsettled post-Tercon.","source_title":"commentary","source_url":"https://www.canlii.org/en/commentary","confidence":"low","from_full_read":false}
      ],
      "threads_identified": [
        {"thread":"Whether the pre-Tercon 'deviation' doctrine survives in cargo cases — worth a dedicated query.","why":"could change the cap analysis","suggested_source":"keyword"},
        {"thread":"Released-value vs declared-value distinction under US Carmack for cross-border lanes.","why":"affects the cross-border qualifier","suggested_source":"semantic"}
      ],
      "contradictions": [
        "One trial-level source treats misdelivery as automatically ousting the cap (deviation); the ONCA in Celadon holds the cap survives absent a Tercon ground. The appellate authority controls."
      ],
      "reviewer_analysis": "The retrieved authority is internally consistent on liability: misdelivery is a clear breach and the carrier is liable as a near-insurer. The live question is the cap. The regulation and Celadon point the same way — the $4.41/kg cap holds where no value was declared — while Tercon supplies the only route to defeat it."
    }
  ],
  "synthesis": "# MEMORANDUM OF LAW\n\n**RE:** Carrier liability for misdelivery to the wrong consignee, and survival of the $4.41/kg cap under O. Reg. 643/05 where no value was declared on the bill of lading\n\n## Short Answer / Bottom Line\n**Liability: Clearly established.** A motor carrier that delivers cargo to the wrong consignee is liable to the shipper/owner…\n\n## Discussion\n**A. The carrier is liable for misdelivery.** …\n**B. The $4.41/kg cap applies where no value was declared.** …\n**C. Whether the cap can be defeated — the Tercon framework.** …\n\n## Qualifications & Limitations\nThis memo addresses Ontario domestic carriage…"
}
```

**Field → UI mapping cheat-sheet:**

| Field | Renders in |
|-------|-----------|
| `goal` | Run header goal, sidebar chip |
| `frame.*` | Frame card (§5.3b) |
| `plan[]` | Plan spine (§5.3c) — `status:"answered"` drives the ✓; `origin:"discovered"` drives the amber tag |
| `passes[0].searches[]` | Pipeline "Retrieve" sublabel + Retrieval query list (§5.3e-ii); `source` drives the tag color |
| `passes[0].read_urls[]` | "read full" counts (pipeline node + summary line) |
| `passes[0].extracted_claims[]` | Claims list (§5.3e-iii); `confidence` drives border/badge color; `from_full_read` drives 📄/snippet |
| `passes[0].threads_identified[]` | Threads (§5.3e-iv) |
| `passes[0].contradictions[]` | Contradictions (§5.3e-v) |
| `passes[0].reviewer_analysis` | Reviewer analysis (§5.3e-vi) — render as Markdown |
| `synthesis` | The report body (§5.3f) — render as Markdown |
| `stop_reason` | Report "stopped:" tile + header pill color |

---

## 7. Live states & animation

In production the page streams events and re-renders. You don't have to wire this, but design the
**states** so it feels alive. The run moves through these stages (this is the `stage` value that
drives the header pill and the Pipeline tracker's active node):

```
starting → planning → framed → planned → searching → reading → reviewing → synthesizing → done
   │           │         │         │          │          │          │            │          │
   └─ Plan node active ──┴─────────┘   └── Retrieve node active ──┘   Review     Synthesize  all ✓
```

Each region has three visual states to design:

- **Empty / loading** — e.g. Frame `reconstructing intent…`, Plan `drafting plan…`, Pipeline nodes grey.
- **Active** — the current pipeline node pulses; the header shows a spinner + stage label; queries
  stream in one by one; claims appear as they're extracted.
- **Done** — node turns green ✓; the Report appears; the Stop button disappears; the stage pill turns
  green ("Complete").

There's also a **user-stop** path: the user can hit "Stop / wrap up now" mid-run, which jumps to
synthesis. Design the "wrapping up early" treatment (amber, not green).

---

## 8. Visual language

The current theme is dark. Key tokens (CSS variables already in `index.html`):

| Token | Value | Used for |
|-------|-------|----------|
| `--bg` | `#0b0d12` | page background |
| `--surface` / `--surface2/3` | `#12151c` … | cards, insets |
| `--ink` / `--muted` / `--faint` | `#eef1f7` / `#9aa4b5` / `#677082` | text hierarchy |
| `--brand` / `--brand2` | `#7c8cff` / `#5563e6` | primary, **Semantic source** |
| `--drill` | `#2dd4a7` (teal) | **Keyword source**, progress |
| `--done` | `#34d399` | completed / answered |
| `--warn` | `#f5b545` | discovered gaps, early stop, **high-confidence** |
| `--err` | `#f0616d` | failures, errors |
| `--med` / `--lo` | `#54b6f0` / `#7c8aa0` | medium / low confidence |

**Source tags** (important — these are the two retrieval engines):
- **Semantic** → indigo (`--brand2`). Natural-language conceptual search.
- **Keyword** → teal (`--drill`). Exact-term / citation search.

**Confidence badges** on claims:
- **high** → amber · **medium** → blue · **low** → grey. The claim card's left border matches.

**Read badges** on claims: `📄 full read` (green) vs `snippet` (grey) — whether the system read the
whole document or just a search snippet.

**Stage labels** (header pill): `Framing & planning`, `Plan ready`, `Retrieving corpus`,
`Reading sources in full`, `Extracting claims`, `Writing deliverable`, `Complete`.

**Stop-reason labels** (report tile): `full plan retrieved & reviewed in one pass`
(`pipeline_complete`, green) · `you wrapped it up early` (`user`, amber).

---

## 9. Demo mode (no backend)

You have two easy ways to design against realistic content with no server:

**Option A — paste content directly into the markup.** Every region in §5 has placeholder copy.
Drop it into the corresponding element in `index.html` and style away. Fastest for pure visual work.

**Option B — feed the fixture to the existing render functions.** The JS in `index.html` already has
all the rendering logic. To light up the whole Run screen from the §6 fixture, you can seed it:

```js
// at the end of the <script>, for design/demo only:
STATE = blankState("demo", "Carrier liability for misdelivery…", "deep");
seedFromPersisted(FIXTURE);   // FIXTURE = the JSON object from §6
showView("run");
renderAll();
```

`seedFromPersisted()` already exists and maps the fixture fields onto `STATE`; `renderAll()` paints
every region. This gives you the real components populated with real-looking content, which you can
then restyle. (Drop the `EventSource` connection in `openRun()` so it doesn't try to reach a server.)

---

## 10. Designer TODO

Where the UI most wants your help:

1. **The Pipeline tracker** (§5.3d) is the signature element — make the plan → retrieve → review →
   synthesize progression feel like a living process. It's currently functional but plain.
2. **Empty / loading / active / done states** for every region (§7) — these are sparse right now.
3. **The Report** (§5.3f) is the product's payoff (a finished legal memo). It deserves
   document-grade typography — margins, a real memo letterhead feel, readable tables.
4. **The claim cards** (§5.3e-iii) carry the substance — confidence, provenance, full-read vs snippet.
   Make the hierarchy scannable at a glance.
5. **Mobile / narrow** — the layout collapses below 860px; the sidebar and the 4-node tracker need a
   considered small-screen treatment.
6. **Frame card as a "veto" surface** (§5.3b) — it's where the user catches a misread of their
   request. Consider making it feel editable/confirmable.

Everything you need to populate the UI is in §5 (per-region copy) and §6 (one complete fixture).
Match the field names if you keep any data wiring, and the real backend will slot in unchanged.
