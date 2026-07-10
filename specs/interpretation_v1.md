# Interpretation v1 — from a news item (or story) to a clear, attested map reading

**Purpose.** A repeatable pipeline that takes a real-world item — a news flash, a story,
an event — and produces (a) a short, plain-language interpretation showing that *this is
the pattern Rebbe Nachman taught*, and (b) an interpretation bundle the explorer renders
clickable with sources (`specs/trace_bundle_v1.md`, `scripts/make_trace.py`).

**Audience for the output:** an ordinary reader with no Breslov background. The test of
success is not that the mapping is deep; it is that the reader *nods*.

**Where this runs.** In Claude Code (a session following this spec + the `torah-map`
skill), with `tmap.py` / `segment_project.py` as the deterministic layer. Nothing here
requires interactive input, so the same procedure could later sit behind an API — but no
API is implemented or planned now.

**The one law (inherited, non-negotiable):** the causal spine is attested edges only.
The LLM does language work at the two ends — distilling the input, narrating the output —
and NEVER supplies a connecting step in the middle. "No chain found" is a real,
publishable answer.

---

## Pipeline

### Stage 0 — Intake
Record: title, source URL, date, 3–6 sentence neutral summary (`input.text_summary`).
Genre-tag it (`news`, `story`, `dream`, `question`) — genre rules from the skill apply.

### Stage 1 — Distill the dynamics (LLM work)
- Extract the **causal arc as 3–6 universal dynamics**, ordered in time:
  *public shame → rage → escalation → collapse*. Dynamics, not actors: strip names,
  parties, sides. If the item has several arcs, take the one with the strongest
  **emotional center** — the thing an ordinary reader actually feels reading it.
  That center is the relatability anchor; protect it through every later stage.
- Phrase each dynamic in the item's own images when possible (a flood, a debt, a
  betrayal) — the map is symbol-rich and prefers the text's own symbol.
- News guardrails: never judge real persons; the mapping is an analogy about a
  *pattern*, and the narration will say so.

### Stage 2 — Resolve to concepts
For each dynamic: `tmap search` / `match`, read glosses, shortlist 2–3 candidate ids.
Beware homograph slugs. Prefer the concept whose gloss a layperson would recognize.
- **Substring pollution (item B, 2026-07-10):** Hebrew search matches substrings — צלם
  returning only אֶצְלָם homographs. If a search yields only substring hits, DROP that
  framing of the dynamic rather than force the nearest hit; rephrase the dynamic and
  search again.
- **The entry step may stay story-side.** For technology/novelty stories the map will
  not attest the mechanism (e.g. AI-tool → falsehood). That is fine: the division
  "the story supplies the cause, the map owns the consequences" is an explicit, labeled
  feature of the bundle — not a weakness to hide. Label such steps `story-supplied`.

### Stage 3 — Query the map
**Split the arc at its hinge first** (discovered on item A, 2026-07-10): most real
stories are a *descent* (problem unfolding) then an *ascent* (response/remedy), hinged
at a turning point. The map attests these separately — descent through `harms`/`absence`
polarity edges, ascent through `builds` eitza chains — and projecting *across* the hinge
fails legitimately (a remedy is not caused by its problem). Query each side on its own;
the hinge itself is the person's free choice, and the narration says so.

**Descent discovery shortcut (item C, 2026-07-10):** ask what the map says damages X,
where X is what the reader feels was lost — a polarity-filtered scan of `harms` edges
touching the story's *outcome* concept finds the descent in one step, faster and more
faithful than starting from the actors' actions.

**Missing-concept honesty (item C, 2026-07-10):** when the story's central image has no
concept in the map (e.g. מיצר/strait, צינור/channel), say so in process_notes and log it
as an extraction candidate — never cast a neighboring gloss in its role. A tempting
near-miss (II:4 "charity widens all openings" — openings into divine service, not
parnassah) was correctly rejected on faithfulness.

Then per side: `segment_project.segment_chain` over the ordered ids (arcs >6 or
poorly-fitting arcs get segmented into teaching-local pieces with explicit bridges). Ask
for alternatives (`-k 3`). If fit is poor, swap in shortlist alternates and retry — that
is legitimate; inventing a hop is not. Unknown end-slots ("? → X") resolve only through
`resolve_unknown` (attested advice/effects near the anchor).

**When a multi-concept arc won't project, find the broken leg first** (trace-plumber
correction, 2026-07-10): `project()` failing on the full arc doesn't mean no pair
projects — sub-pairs often project fine (nekudot-tovot→niggunim-2 does, at cost 0.12).
Bisect: project consecutive pairs/triples to locate the leg that breaks, then decide —
trim the arc, hinge-split, or go to torah+chain for that leg only.

**When `project`/`why` return nothing but the reading feels present in one teaching:**
read the teaching itself (`torah REF`) — much causal flow is attested on
statement-node (`s:`/`p:`) edges that concept-level traversal skips. Those edges carry
proofs + refs and are fully legitimate hops for the bundle. Verify every sequence you
assemble this way with `tmap chain` before publishing — `"attested": true` per junction
or it doesn't go in the spine. The reliable discovery loop is: `advice`/`effects` on the
arc's resolution concept → find the home teaching → `torah REF` → assemble → `chain`.

### Stage 4 — Explainability selection  ← the v1 addition
Score every candidate reading; publish the best **explainable** one, not the best-fitting
one. Rubric (score each 0–2; publish threshold ≥ 7/10, hard gates regardless of score):

| Axis | 2 | 0 |
|---|---|---|
| **Fit** | single home teaching, cost < ~2 | multi-bridge, cost > ~6 |
| **Simplicity** | 1 segment, chain of 3–5 | 3+ segments or chain > 6 |
| **Directness** | picks map `self` or one `aspect` hop | mappings mostly `shared` |
| **Familiarity** | anchors are everyday concepts (joy, prayer, truth, money, shame) | anchors are technical kabbalistic terms |
| **One-breath test** | the load-bearing move states in one plain sentence a stranger nods at | needs a paragraph of setup |

Hard gates:
- **THE ONE-EDGE RULE (v1.2 — Shmuel's calibration, 2026-07-10, overrides everything
  below for news):** the default public product is a SINGLE attested edge, both
  endpoints everyday-literal, which the news event *instantiates* (is a live case of) —
  the Hormuz descent ("anger damages livelihood", one hop, fight→money lost) was the
  only pilot reading Shmuel found clear; every multi-hop, hinged, or figurative reading
  — including individually-verified ones — read to him as "making stuff up."
  Multi-hop chains and figurative edges are STUDY MODE: keep them in bundles and
  process notes, but a public narrative may carry at most one hop, literally read.
  Work from `interpretations_work/clear-laws-catalog.md` (the mined single-edge law
  inventory) — match event → law, not story → chain. If no law fits literally, publish
  nothing rather than a stretch.
- **Opposites-gate:** a reading whose key move equates opposites ("X and not-X are
  really the same") is beautiful and usually unpublishable. Allowed ONLY if it passes
  the one-breath test cleanly; otherwise take a runner-up reading. Beauty ≠ clarity.
- **Shared-only gate:** reject any reading where every mapping is `shared` — that is
  co-occurrence dressed as connection.
- **Anchor gate:** the emotional center of Stage 1 must map to a `self` or single-hop
  anchor. If the reading loses the emotional center, it will not land — reject.

If nothing passes: publish the honest miss — "the map doesn't force this one" — with the
nearest attested fragments and the named missing edge. That is a valid, trust-building
output.

### Stage 5 — Narration (two registers, never mixed)
**Public narrative** (`narrative`, `narrative_by_segment`) — ≤ 250 words total, three parts:
1. **The story** — retell the arc in 2–3 sentences, universal terms, no names needed.
2. **The teaching** — "Rebbe Nachman teaches (Likutey Moharan I:7) …" — walk the SAME
   arc through the teaching, one sentence per causal hop, each load-bearing sentence
   carrying its ref; quote 1–2 *short* Hebrew proofs with translation (not every proof —
   the bundle holds the rest, one click away).
3. **The takeaway** — one concrete eitza the reader can act on, drawn from an attested
   advice edge of the arc's resolution concept.

**Look for polarity pairs (item B, 2026-07-10):** when one edge exists as BOTH
harms/presence and builds/absence (e.g. sheker→hashgachah: falsehood drives away His
watching; guarding from falsehood brings it back), the problem and the remedy are the
same sentence read twice — the clearest possible takeaway structure. Interpreters
should check the resolution concept's edges for these pairs deliberately.

Style rules: newspaper-column register; no map jargon in public text (never "cost",
"bechina", "node", "edge", "projection", "segment"); any Hebrew term gets a ≤5-word
gloss; analogy framing explicit ("the pattern here is the same pattern as…"); epistemics
humanized — attested = "Rebbe Nachman says", aspect-derived = "which he identifies
with…", resolved unknown = "the teaching suggests the missing step is…", your framing =
"to my eye". Never pronounce on real persons.

**v1.1 narration rules (judge-panel calibration, 9 judges, 2026-07-10 — scores were
7–8/10 with the SAME failure modes across all three pilots):**
1. **Citations out of the flow.** No inline book codes ("Likutey Moharan I:282") in the
   public text — say "a teaching called Azamra" and put refs in ONE end-of-paragraph
   parenthetical at most. Full sourcing is the bundle URL's job; that's why it exists.
2. **No Hebrew script in the public flow.** English translation only; the Hebrew lives
   in the bundle's proof cards, one click away.
3. **Identify Rebbe Nachman once**, ~5 words ("the 18th-century Hasidic teacher").
4. **Gloss vs. attested, audibly separated.** The writer's connective analysis must
   sound like the writer's ("that is —", "to my eye") and NEVER sit inside an "he
   teaches, step by step" construction. Precision words ("exact", "precisely") are
   reserved for chain-verified content only.
5. **Takeaway = one physical action a person could do today**, earned by THIS story —
   not an aphorism, not generic advice that fits any hardship.
6. **Honor real stakes before pivoting inward** (one clause: "people are afraid and
   paying more for gas") — otherwise the turn to the personal reads tone-deaf.
7. **Structure invisible.** Keep the story→teaching→takeaway shape but drop the visible
   scaffold labels — they signal "devotional content" and cap how far the piece travels.
8. **Vary attribution.** "He says" once, maybe twice; let imperatives stand alone.
9. **One more beat of human stakes in the hook** before the turn to the teaching.

**Process notes** (`process_notes`) — the analyst register: ids, costs, alternatives
considered and why rejected (one line each), gates applied. This is for us and for the
explorer's detail view, not for the reader.

### Stage 6 — Emit
Assemble trace_bundle_v1 (segment output + input + both narrations), then:
`python3 scripts/make_trace.py bundle.json --slug <slug>` → validates, installs to
`ontology/graph/traces/`, prints the explorer URL. The URL is the deliverable.

---

## Checklist (tick before publishing)
- [ ] Arc is dynamics-only; emotional center named in one phrase
- [ ] Every spine hop is an attested edge with proof + ref (no LLM bridging)
- [ ] Explainability ≥ 7/10; all three hard gates passed (or honest-miss issued)
- [ ] Public narrative ≤ 250 words, 3-part, jargon-free, refs on load-bearing sentences
- [ ] Alternatives noted in process_notes (what was rejected and why)
- [ ] Bundle validates; URL renders; proofs clickable

## Known v1 limits
- Rubric weights are first-guess — calibrate through judge rounds (clarity /
  faithfulness / relatability) and revise this file with dated notes.
- Familiarity axis is judgment, not a list; consider a `familiar: true` node tag later.
- Hebrew-first readers may want an inverted register (Hebrew quote first) — v2 question.
