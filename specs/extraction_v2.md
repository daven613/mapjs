# Edge Extraction v2 — polarity & mode (the "bad flow")

## Problem
v1 extracted only the relation skeleton (bechina/eitza/equation). Likutey Moharan states
harm-flows explicitly too — פגם statements ("על ידי פגם ה-X בא Z"), and direct-damage
statements ("הכעס מזיק ל..."). Without them, the graph knows only what builds; diagnosis
of lack has to be inferred. Capture the negative flow as FIRST-CLASS attested edges.

## Schema v2 (per extracted edge)
```json
{"type": "bechina|eitza|equation",
 "source_he": "...", "target_he": "...",
 "proof": "<verbatim Hebrew>", "explicitness": "explicit|inferred",
 "polarity": "builds|harms|neutral",
 "via": "presence|absence"}
```
Record envelope gains `"schema": 2`.

### Semantics (eitza edges)
| polarity | via      | reading                                        | example pattern |
|----------|----------|------------------------------------------------|-----------------|
| builds   | presence | doing/attaining X brings good Y                | על ידי X זוכין ל-Y |
| harms    | absence  | LACK/blemish of X causes damage Z              | על ידי פגם ה-X בא Z; כשאין X... |
| harms    | presence | X itself causes damage Z                       | הכעס מביא ל-Z |
| builds   | absence  | refraining from X brings good Y                | על ידי שבירת התאוה זוכין... (when framed as absence) |

bechina/equation: `polarity: "neutral"`, `via: "presence"` (aspects are polarity-free;
the lack of X parallels the lack of its bechinot — that inference stays QUERY-TIME, in tmap).

### Direction convention (unchanged)
source → target is cause → effect for eitza. For harms/absence: source is the thing
whose LACK does the damage (source=אמונה, target=חלאים for "פגם האמונה מביא חלאים") —
so inversion queries stay trivial: the builds-graph and harms-graph share concept nodes.

## Compatibility
- The 157 v1 chunk files stay as-is. At merge time, edges lacking polarity/via default to
  `builds/presence` (correct for the overwhelming majority of v1-prompt output; the v1
  prompt only asked for positive counsel patterns anyway).
- Optional later: a cheap backfill pass re-classifying v1 edges' polarity from their proofs.

## Acceptance criteria
- AC1: extractor prompt requests and validates the two new fields; records tagged schema:2.
- AC2: a chunk containing a פגם statement yields ≥1 eitza edge with polarity=harms,via=absence
  (spot-check during review, not automated).
- AC3: invalid polarity/via values are rejected at parse time → chunk retried, never written.
- AC4: daemon resumes idempotently: v1 files skipped, only missing chunks extracted.

## Operations (resume, 2026-07-05)
- Model: claude-sonnet-5 (Fable window closed 2026-07-04 17:00).
- Concurrency 6 (box OOM'd at 14 previously). Usage-limit → long sleep (1800s), retry;
  subscription limits reset on their own.
- Backstop deadline 2026-07-08 17:00; daemon also self-terminates when remaining==0.
