# The Torah Map — Vision Document

> This is the canonical statement of what this project is, where it came from, and where it is going.
> It captures the author's (Shmuel's) own understanding and personal experience, as dictated 2026-07-02,
> so it never needs to be re-explained from scratch. The technical counterpart is [ENGINE_DESIGN.md](ENGINE_DESIGN.md);
> the data-model reference is [framework.md](framework.md).

---

## 1. The Core Discovery

Rabbi Nachman's Torahs (the teachings of Likutey Moharan) are intensely **structural**. Two
structures account for roughly 90–98% of the entire book's architecture:

### 1.1 Cause-and-effect chains (eitza / עצה)

Each Torah leads through a long — often very long — string of causes and effects.
The chain is *usually* linear but frequently branches. Characteristic patterns:

- **Compression then expansion**: he first states the short form ("the beginning leads to the
  end"), then unpacks it explicitly ("because the beginning leads to stage 2, and stage 2 to
  stage 3, and that leads to the end").
- **Granular detours**: "A leads to B, because A leads to C, and C leads to D, and D leads to X,
  and X leads to B" — the macro-edge A→B is *explained by* a micro-path A→C→D→X→B.
- Signature phrases: "על ידי זה" (through this), "through X you come to Y" — this is what was
  keyword-hunted in the original pre-AI pass.

### 1.2 Parallel concepts (bechina / בחינה)

As the causal chain unfolds, he simultaneously shows how the *same* sequence or concept
**projects into many different dimensions**: the same structure appears as

- a passage in the Torah (the same sequence of words),
- a law of the Torah (the same concepts embodied in halacha),
- a story of a tzaddik (first he did this, then this happened — same sequence as events),
- psychological states, physical phenomena, letters, body parts, and so on.

Signature phrases: "בחינת", "זה בחינת", "נקרא" — the special "this is the concept/aspect of that"
vocabulary.

Other structural elements exist (principles, definitions, etc.) and may be extracted later,
but these two relations ARE the skeleton of the book.

---

## 2. Rabbi Nachman's Own Claims (why this is more than an indexing project)

Rabbi Nachman states explicitly that his Torah is like the **root of all Torah** — everything is
somehow rooted in what he is saying. His teachings are the root; everything else (Torah passages,
laws, stories, the world itself) are **real projections** of the concepts he understood and taught.

Even more strongly: **any single teaching is a microcosm** — you can see how it projects onto any
aspect of the whole Torah, and possibly onto the whole world and everything in it. This is
precisely the study his student Reb Noson undertook in **Likutey Halachos**: showing, law by law,
how the teachings project into the halachic dimension of Torah. (That book — which we have now
fully translated in the sibling `new-sefer` project — is therefore a massive corpus of *worked
examples of projection*.)

He also indicates that the future can be seen through these sequences: if A happened and then B
happened, you can know C is coming — the same microcosm principle applied along the time axis.

**The framing**: this is the science of the world's mechanism. Every projection is a *dimension*.
The Torahs describe the root process; the dimensions (scripture, law, stories of tzaddikim,
psychology, physics, current events, a person's life, a dream, a name) are where the same process
re-appears. Studying the map of projections is studying how the dimensions relate to each other.

---

## 3. Personal Experience (what motivates this)

- While studying, Shmuel has repeatedly projected teachings himself — onto physics, onto
  understandings of the universe, onto sciences of different sorts — and found it revealing.
- As a Jew, there is particular joy in **finding light in the darkness**: opening a science
  article or a news story and seeing "that's exactly what Rabbi Nachman explained in Torah X."
- The experience is that once you hold the structure, the recognition is almost **mechanical** —
  it *should* be easy, it should be computable. That is the engine this project wants to build.

---

## 4. The Pre-AI Work (what already exists)

Before AI tools existed, Shmuel went through the entire book — quickly but carefully — and:

- searched for every occurrence of the "concept" vocabulary (בחינת etc.) and the causal
  vocabulary ("על ידי זה", "through this you come to…"),
- highlighted the matches in a word processor and manually extracted the relationships,
- built the **mapjs** project (this repo): a Sigma.js graph visualizer over an edge dataset.

Current dataset (data/torahData.js, measured 2026-07-02):

| Metric | Value |
|---|---|
| Edges | 4,168 (2,273 bechina; 1,894 eitza/cause; 1 typo'd type) |
| Unique node IDs | 4,299 |
| Torah references covered | 256 distinct reference values |
| Provenance | every edge carries a `proof` quote from the source text |

The **node/edge ratio (~1.03 nodes per edge)** is the tell-tale of the biggest gap: node IDs are
raw surface strings, so the same concept appears under many spellings/phrasings and the graph is
far more fragmented than the reality it models. Canonicalization (alias resolution) is the first
big unlock.

The conceptual data model — bechina vs. eitza, packages (חבילות), good/evil polarity and the
mirror structure, cross-Torah bridges — is fully worked out in [framework.md](framework.md) with
Torah #1 as the worked example.

Meanwhile, the sibling `new-sefer` project has produced: full verified interlinear English of
Likutey Halachos (7,280 chunks), Likutey Moharan I+II chunked to fine paragraph level with a
4-level hierarchy (Torah → Section → Subsection → chunk) and stable anchors, and translations of
the wider Breslov corpus in progress. **That chunk/anchor layer is the substrate the graph should
attach to.**

---

## 5. The Goal Ladder (from indexing to the engine)

Each rung builds on the previous. This is the roadmap in vision terms; the technical version is
in ENGINE_DESIGN.md.

1. **Exhaustive extraction** — redo the pre-AI keyword pass with AI: every bechina and eitza in
   Likutey Moharan (later: the whole Breslov corpus), each anchored to its exact source chunk
   with its proof quote. The 4,168 hand-made edges become the *gold standard* to validate the AI
   extraction against.
2. **Canonical concept graph** — resolve aliases into canonical concepts, keep every occurrence
   linked to its place in the text, preserve packages and polarity. Now "everything is connected
   to everything" becomes literally navigable.
3. **The connection calculator** — given any two concepts, find the connection and **weight** it.
   Weighting principles (Shmuel's own, to be formalized):
   - Everything is connected; the question is never *whether* but *how strongly and by what path*.
   - Crossing from one Torah/chapter to another **costs** weight; staying inside one chapter is
     stronger.
   - Within a chapter: directly-linked concepts are stronger than concepts connected only through
     intermediaries.
   - The maximum possible weight: one chapter explicitly mentions the exact items, in order,
     connected in sequence — everything explicit, everything local.
   - Different relation types and contexts may carry different base weights.
4. **The projection engine** — the crown. Take an arbitrary input — a dream, the letters of a
   name, a news article, a physics concept, a life situation — decompose it into its concepts and
   its causal sequence, and find where and how it maps onto the Torahs:
   - *Example*: the letters of a name map onto a chapter because the chapter teaches A→B→C→D and
     each letter is the aspect of the corresponding stage — in order. That chapter is connected
     to that name, at very high weight if the letters are explicitly mentioned in sequence.
   - The engine finds mappings, ranks them by the weighting scheme, and shows the proof texts —
     the same experience of "that's exactly what he said," made mechanical.
5. **New projections & the far horizon** — generate projections onto domains never yet mapped
   (new sciences, current events), the way Reb Noson generated the halachic dimension. And the
   extreme, imaginative end: the time axis — given an unfolding sequence (A happened, then B),
   locate the chain and see what C is. Whether or not that rung is ever reached, it defines the
   direction: this is a study of the mechanism of the world.

---

## 6. Guiding Principles

- **Provenance always** — every assertion in the graph carries its proof quote and exact anchor.
  The engine must be able to *show its work* in the Rebbe's own words.
- **The author's structure is sacred** — extraction captures what the text says; interpretation
  layers (weights, projections) sit above it and are marked as ours. (Same principle as the
  subsection work in new-sefer: never confuse our scaffolding with the author's.)
- **Gold data before scale** — the manual 4,168 edges and Likutey Halachos's worked projections
  are ground truth. Every automated stage is validated against human-made truth before it runs
  exhaustively.
- **Translation was the precursor** — the new-sefer translation effort exists (in part) to make
  this analysis possible in both languages and to future users.
