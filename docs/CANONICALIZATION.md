# Canonicalization Protocol (Phase 1)

> Merging surface forms into canonical concepts is the most dangerous step in the whole
> pipeline: a wrong merge silently corrupts everything downstream, and unlike extraction
> errors it does not announce itself. This protocol is binding. Written with Shmuel 2026-07-02.

## The core danger: same words, different concepts

The hardest cases are not spelling variants — they are **definite vs. generic** and
**archetype vs. instance**:

- **הצדיק vs. צדיק** — "*the* tzaddik" often means the archetype (the tzaddik of the
  generation / Moshiach-level tzaddik), while "*a* tzaddik / righteous person" can mean anyone
  acting righteously. Same root word, genuinely different concepts.
- **החכם vs. חכם** — in some Torahs "the wise man" is explicitly equated with "the tzaddik"
  (same referent *in that Torah*); elsewhere "a wise man" is generic. The equation is **local
  to a chapter**, not global.
- **חכמה** in one context is the sefirah; in another, ordinary human cleverness; in another,
  the wisdom of the Other Side (חכמות חיצוניות).

**Context is king.** No merge may be decided from the surface strings alone — the decider
(human or AI) must see the proof quotes and, when needed, the surrounding chunk text.

## Rules

1. **Nothing merges automatically.** Every merge is a *proposal* until reviewed. The pipeline
   produces proposal lists; a separate, deliberate step applies approved ones.
2. **Tiered proposals.** Every proposal is classified:
   - `obvious` — spelling/niqqud/prefix variants, unambiguous ("חכמה"/"החכמה"/"חכמות" as plural
     of same use). Reviewed in bulk, but still reviewed.
   - `likely` — strong evidence (e.g. the text itself equates them via an explicit bechina),
     shown with the proof quote.
   - `question` — genuinely uncertain; presented as an open question with full context, one by
     one. Default answer is NO MERGE.
3. **Under-merge beats over-merge.** Two concepts wrongly kept separate cost one graph hop
   (and can be joined later, cheaply). Two concepts wrongly merged poison every path through
   them (and are expensive to disentangle). When in doubt: keep separate, add an explicit
   bechina edge with its evidence if the text supports one.
4. **Local equations stay local.** "The chacham = the tzaddik *in Torah N*" is recorded as a
   scoped equivalence (an edge carrying its anchor), NOT as a global registry merge. The
   registry merges only identities that hold everywhere.
5. **Every merge is justified and reversible.** A registry entry lists each alias with the
   *reason* it was accepted (`spelling`, `explicit-equation @ anchor`, `reviewed-judgment`).
   The occurrence layer is never rewritten, so any merge can be undone by editing the registry
   and recompiling the graph.
6. **Distinct-by-design concepts.** The registry explicitly supports near-twin concepts with
   clear IDs and English glosses, e.g. `c:tzaddik` (generic) vs `c:tzaddik-emet` (the archetype),
   `c:chochma` (holy wisdom) vs `c:chochmot-chitzoniot` (external wisdoms). The gloss states the
   distinction so future classification lands on the right one.
7. **Every concept gets an English gloss** (leaning on the existing LM/LH translations for the
   standard renderings), a canonical Hebrew form, and a stable ID.

## Pipeline shape

1. **Group** (mechanical): normalize niqqud/punctuation, strip definite-article prefix *as a
   candidate signal only* (the ה may be meaningful! see above), cluster by string similarity +
   embeddings. Output: candidate clusters.
2. **Adjudicate** (AI, one cluster per agent, with the proof quotes and chunk context in the
   prompt): split each cluster into proposed concepts; classify each proposed merge
   obvious/likely/question; flag definite-article and archetype cases explicitly.
3. **Review** (human, in the review UI or a markdown checklist): approve/reject/split.
   `question` items are never bulk-approved.
4. **Apply + compile**: write the registry, recompile the graph. Report what changed.

Nothing in steps 1–2 touches saved state; only step 4 writes, and only from approved items.
