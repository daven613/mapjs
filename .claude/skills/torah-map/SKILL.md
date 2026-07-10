---
name: torah-map
description: Query the Likutey Moharan concept graph (search, cause-effect, projection) to interpret stories and questions through Rebbe Nachman's teachings, with proof quotes. Use when the user tells a story / describes a situation and wants a Torah-map interpretation, or asks about connections, causes, effects, or parallels between concepts.
---

# Torah Map — interpreting through the concept graph

The graph: ~4,200 concepts and ~3,900 typed edges extracted from Likutey Moharan.
Edge types: **eitza** (directed cause→effect / advice), **bechina** (aspect/parallel),
**equation** (explicit identity). Every edge carries a Hebrew proof quote and teaching
ref (e.g. `I:22` = Likutey Moharan I, Torah 22).

Tool: `python3 /home/smiles/dev/mapjs/scripts/tmap.py <command> [--pretty]` — all JSON.

## Commands
- `search QUERY [-n 10]` — find concepts by Hebrew or English name/gloss (start here; you need concept ids like `c:simchah`)
- `match "free text" [-n 10]` — token-similarity match of a sentence/paragraph to concepts
- `concept ID` — a concept's gloss, teachings, aspects, causes (advice), effects
- `advice ID` — what LEADS TO it (eitza in-edges) · `effects ID` — what it leads to
- `aspects ID` — its bechina parallels
- `path A B` — shortest connection chain · `common A B` — shared ground
- `torah I:22` — everything in one teaching
- `project ID ID [ID...]` — **the flagship**: map a 2–6 concept causal sequence onto a
  parallel cause-effect chain inside ONE teaching. Returns: `home` (the teaching),
  `chain` (anchors), `mappings` (how each of your picks reaches its anchor: kind
  `self`/`aspect`/`shared`, with aspect-hop proofs), `links` (the causal hops between
  anchors, each with cost + proof), total `cost` (lower = tighter fit; same-teaching
  hop ≈ 0.12, cross-teaching ≥ 1.6).

## The general method (works for ANY input genre)
1. **You do the language work**: distill the input — story, dream, news event, halacha,
   symptom, question — into its concepts. If it has a temporal/causal arc, order them
   (X led to Y led to Z). The graph reasons over concepts, not prose; never feed it raw text
   except via `match`.
2. Resolve each concept to an id with `search`/`match` — read the glosses, beware homographs
   (ids are disambiguated slugs; e.g. שדי has two senses).
3. **Formulate ONE typed query per question.** The map contains exactly two relation
   kinds — cause-effect (eitza) and parallels (bechina) — so every natural-language
   question must be translated into a query typed accordingly. Order-in-time IS
   causation here: "why does X come before Y" means "X (or a parallel of X, even a
   parallel of a parallel) CAUSES Y (or a parallel of Y)" — that is the `why` command,
   never `torah`-co-occurrence, never your own narration.
   | question shape                        | the one query |
   |---------------------------------------|------|
   | why X before Y / X leads to Y? / order | `why A B -k 3` (bechina* → eitza+ → bechina*) |
   | a sequence of events/causes            | `project` (parallel chain in one teaching) |
   | what IS this thing                     | `concept` + `aspects` (1–2 levels) |
   | what builds it / what does it bring    | `advice` / `effects` |
   | an affliction / lack / failure         | `diagnose` (inversions, labeled inferred) |
   | how are X and Y related (no direction) | `path -k` + `common` |
   "No chain found" is a REAL ANSWER: report that the map cannot attest it, show the
   nearest attested fragments, and name the missing edge — do not bridge the gap yourself.
4. **Ask for runner-ups**: `path A B -k 5` and `project ... -k 3` return `alternatives`
   (distinct routes / distinct teachings, cost-ascending). Real questions have several
   valid answers — present the best reading first, then offer the alternates ("through a
   different teaching this reads as…"). Don't show all K raw; curate the 2–3 that differ
   meaningfully.
5. **When two concepts share a teaching, query the teaching**: if `concept` shows both
   sides appearing in the same ref, `torah REF` and read its causal spine — "why" answers
   usually live in one Torah's internal flow, not in a cross-teaching shortest path
   (e.g. Rosh Hashanah/Yom Kippur both in II:5: RH ⇒ tikkun of the mochin ⇒ tefillin ⇒
   YK = the COMPLETION of the seal — the ordering answer was the spine itself).
6. Interpret in plain words, **quoting proofs** with refs for every load-bearing link.
   Keep the epistemics visible: attested edge ≠ aspect-derived ≠ inferred inversion ≠
   your own framing. Projection `cost` = fit quality; if it looks forced (high cost, many
   `shared` mappings), try alternate ids, fewer/more stages, or the -k alternatives, and compare.

## Genre notes
- **Story / dream**: dreams are usually a *sequence* → `project`. Isolated dream symbols →
  `search` each symbol, then `aspects` to open its meanings; offer 2–3 candidate readings
  rather than one forced one. Rebbe Nachman's world is symbol-rich — prefer the concept the
  text itself uses (a lion is אריה, not "power").
- **News event**: extract the *dynamics* (pride → downfall; strife → exile), not the
  personalities. Interpret the pattern through the teaching; do not pronounce judgment on
  real people, and say the mapping is an analogy.
- **Halacha / minhag**: the practice is usually itself a concept (tefillin, netilat yadayim,
  candle-lighting). `concept` + `advice`/`effects` give Rebbe Nachman's ta'am — what the
  practice builds and reaches. Flag that this is his homiletic layer, not the halachic reasoning.
- **Affliction / lack** ("pain in my kidneys"): see the diagnose workflow below.

## Workflow: interpreting an affliction / lack ("I have pain in my kidneys")
1. `search` the afflicted thing (organ, situation, middah) → concept id
   (e.g. כליות → `c:trust`, "the kidneys… seat of bitachon").
2. `diagnose ID --depth 2` — returns three layers, keep them straight:
   - `contexts`: the concept's near aspects (graph-attested, with proofs) — the
     "different approaches" to what this thing IS spiritually;
   - `attested_helpers`: what the text says strengthens each context (attested);
   - `inferred_deficiencies`: the inversion — lack of each helper as candidate root,
     each with its full derivation chain. These are marked `inferred`: the darshanic
     move (X strengthens Y ⟹ lack of X weakens Y) is traditional and Rebbe Nachman
     often makes it explicitly, but here it is OUR inference — say so.
3. Present: what the kidneys ARE (quote the bechina proofs), what builds them (quote),
   and therefore what to examine (the inferred lacks, clearly labeled as inference),
   ordered by closeness (dist). Suggest the remedy side too: the attested helpers ARE
   the eitzot.
4. This is a spiritual lens; it accompanies, never replaces, medical care — say this
   briefly when the topic is bodily.

## Workflow: answering a question
- "What leads to X?" → `search` → `advice ID` (quote proofs).
- "What does X bring about?" → `effects ID`.
- "How are X and Y connected?" → `path A B`, and `common A B` for shared ground.
- "What does Torah N teach?" → `torah I:N`, summarize its causal spine.

## Workflow: interpreting a news item / story → a shareable map link
The full crystallized pipeline lives in `specs/interpretation_v1.md` — READ IT before
running this workflow; it carries field-tested rules this summary compresses. The loop:
1. **Distill** the item into 3–6 universal dynamics ordered in time; name the emotional
   center (what an ordinary reader feels). Dynamics, not actors; never judge real people.
2. **Split at the hinge**: descent (what went wrong — query `harms` edges touching the
   OUTCOME concept, i.e. what the reader feels was lost) and ascent (the remedy — eitza
   `builds` chains). The hinge is the person's free choice; the map attests each side
   separately, never across.
3. **Resolve** ids (`search`/`match`; substring-polluted results → rephrase, don't force).
   **Query** (`project`, bisect broken arcs, `torah REF` + assemble when flow rides
   statement nodes). **Verify every spine hop with `chain`** — attested:true or it's out.
4. **Gate for explainability** (spec Stage 4): familiar anchors, ≤1 aspect hop, no
   opposites move unless it passes the one-breath test, emotional center preserved.
   Look for polarity pairs (same edge harms/presence + builds/absence) — problem and
   remedy in one sentence. Nothing passes → publish the honest miss.
5. **Narrate in two registers** (spec Stage 5 + v1.1 rules): public text ≤250 words,
   no inline book codes, no Hebrew script in the flow, writer's gloss audibly the
   writer's, one concrete do-today takeaway earned by THIS story, real stakes honored
   before any inward pivot. Analyst detail goes in process_notes.
6. **Emit the bundle**: shape per `specs/trace_bundle_v1.md`, then
   `python3 scripts/make_trace.py <bundle.json> --slug <slug>` → validates, installs,
   prints `http://localhost:8890/explorer.html?trace=<slug>&t=<epoch>`. THE URL IS THE
   DELIVERABLE — the explorer renders the reading clickable with every proof.
Worked pilots (read one before your first run): `interpretations_work/item-a-*.md`
(chain-based single home), `item-b-*.md` (polarity pair), `item-c-*.md` (hinge bridge +
multi-teaching ascent), each with its judge feedback file alongside.

## Discipline (hard rules)
- **Never invent connections**: if the graph lacks an edge, say so — absence is data.
  Node NAMES and glosses are identity, not connectivity: two nodes whose Hebrew looks
  equivalent are NOT connected unless an edge says so.
- **Verify every chain before presenting it**: run `chain ID ID ID...`; any junction
  with `attested:false` must be shown to the user as a GAP, never smoothed over.
- **Context, not interpretation**: your ceiling is choosing among the map's answers and
  giving context that makes the attested relations understandable. The reasoning must
  live in the edges; if a conclusion needs a step no edge attests, the conclusion is
  not available — offer the fragments instead.
- Always cite refs (`LM I·22`) with quotes, so the user can check the source.
- Hebrew output: quote proofs in the original; translate the gist yourself.
