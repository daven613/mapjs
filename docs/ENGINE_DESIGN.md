# The Projection Engine — Technical Design

> Companion to [VISION.md](VISION.md) (why) and [framework.md](framework.md) (data model of the
> existing dataset). This document names the fields of knowledge this project actually belongs to,
> makes the key architectural decisions, and lays out the build phases.
> Written 2026-07-02.

---

## 1. What this is, in established terms

You asked "is this ontology?" — partially. The project spans four established fields, and knowing
which part belongs to which field tells you which tools to borrow:

| Your concept | Established name | Field |
|---|---|---|
| The concept vocabulary + relation types (bechina, eitza) + rules about them | **Ontology** (specifically the *schema*/TBox) | Knowledge representation |
| The actual extracted facts ("chochma is a bechina of chet", "grace → engraving") | **Knowledge graph** (instances/ABox) | Same |
| Pulling those facts out of the text automatically | **Information extraction** (relation extraction with provenance) | NLP |
| "Everything is connected; find the connection and weight it" | **Weighted path search / graph proximity** | Graph theory |
| The causal skeleton of a Torah as a reusable pattern | **Motif / template** | Graph mining |
| Projecting a Torah onto a dream, a name, a law, physics | **Analogical mapping** — structure-preserving correspondence between two relational graphs | Cognitive science / AI |
| "Map my dream onto the Torahs" via an AI query | **GraphRAG** (retrieval over a knowledge graph + LLM) | Modern LLM engineering |

Two important framings:

**Projection = structure mapping.** The single most important theoretical anchor: what Rabbi
Nachman does when he projects a causal chain onto a verse, a law, or a story is exactly what
cognitive science calls **analogy as structure mapping** (Gentner's Structure-Mapping theory,
and its computational form, the Structure-Mapping Engine). An analogy is a mapping between two
domains that preserves *relations*, not surface features: A:B :: C:D because the *relationship*
A→B matches the relationship C→D. A Torah's eitza chain is the "base domain"; a dream / name /
law / news story is the "target domain"; a projection is a correspondence between them that
preserves the causal order. Bechina edges are what license the node correspondences ("this dream
element *is the aspect of* that Torah concept"). This is the formal skeleton of your entire
project, and it means the projection engine is a **graph alignment scorer**, not a mystical
black box.

**Deliberately NOT: OWL/RDF/formal reasoners.** Classic ontology tooling (OWL, description
logic, triple stores, Protégé) is built for *deductive* reasoning — subsumption, consistency
checking. What you need is *analogical* reasoning — alignment and similarity. OWL buys you almost
nothing here and costs enormous ceremony. Verdict: **use ontology as a discipline (controlled
vocabulary, typed relations, canonical IDs), not as a technology stack.** A labeled property
graph in plain files is the right substrate.

---

## 2. Data model

Four layers, each a plain-JSON artifact (consistent with the new-sefer sidecar philosophy —
files, not databases, until scale forces otherwise).

### 2.1 Text layer (exists — in new-sefer)
The chunked source: Torah → Section → Subsection → chunk, with stable anchors (`reading.json`).
Everything above anchors into this. Hebrew + English both available.

### 2.2 Occurrence layer (extraction output)
One record per *statement in the text*. Never merged, never edited — this is the evidence.

```json
{
  "id": "occ:lm1:6:3:2:007",
  "anchor": {"book": "lm1", "torah": 6, "chunk": "6_3_2", "char_span": [412, 498]},
  "type": "bechina | eitza",
  "source_surface": "חן",          // exactly as written there
  "target_surface": "חקיקה",
  "proof": "…the verbatim quote…",
  "explicitness": "explicit | inferred",   // did he SAY it, or is it implied by context
  "cue": "על ידי זה",                        // the trigger phrase matched
  "extractor": "human-2019 | claude-2026",   // provenance of the extraction itself
  "confidence": 0.97
}
```

Your existing 4,168 edges import directly into this layer with `extractor: human-2019` — they
already have proof quotes and references. They become the **gold set** (§5).

### 2.3 Concept layer (canonicalization output)
The registry that fixes the 4,299-nodes-for-4,168-edges fragmentation problem.

```json
{
  "id": "c:chochma",
  "canonical_he": "חכמה",
  "canonical_en": "wisdom",
  "aliases": ["חכמה עילאה", "שכל", "the sekhel", "חכמות"],
  "domain": "middah | letter | person | verse | halacha | body | nature | ...",
  "polarity_default": "good | evil | neutral",
  "embedding": "→ stored in a parallel vectors file",
  "occurrences": ["occ:...", "occ:..."]
}
```

Rules: an alias merge must be *justified* (either the text equates them via an explicit bechina,
or a reviewed judgment call — track which). When in doubt, keep separate and connect with a
bechina edge; over-merging destroys information, under-merging just costs one hop.

### 2.4 Graph layer (derived, rebuildable)
Compiled from occurrences + registry: nodes = canonical concepts; edges = typed, weighted,
carrying their occurrence list. Plus the per-Torah artifacts:

- **Skeleton**: each Torah's eitza chain as an ordered graph (the motif) — including the
  macro-edge/micro-path structure ("A→B because A→C→D→X→B" stores A→B as a summary edge
  *refined by* the sub-path).
- **Packages** with polarity and mirror pairs (per framework.md).

Storage: JSON files + NetworkX (Python) for analysis; SQLite if lookup speed ever matters;
Sigma.js (already in this repo) for visualization. **Neo4j is not needed** at this scale
(~10⁴–10⁵ edges) and adds operational drag.

---

## 3. The weighting model (connection calculator)

Formalizing the principles from VISION.md §5.3. Weight = strength in [0,1]; cost = −log(strength)
so path costs add and shortest-path algorithms apply directly.

Edge strength = product of factors:

| Factor | Values (initial guesses — tune against gold data, §5) |
|---|---|
| Explicitness | explicit statement 1.0 · inferred 0.6 |
| Relation type | equation ~1.0 (traversal cost ≈ 0 — "which is", literal identity statements) · bechina 1.0 · eitza 1.0 (same base; different queries) · inferred-by-us (our common-sense equivalences) lower, marked as ours |
| Locality of use *in a query path* | same chunk 1.0 · same Torah 0.8 · cross-Torah bridge 0.5 |
| Multiplicity | stated once 1.0 · restated in k places 1−(1−s)ᵏ (repetition strengthens) |

Path strength = product of edge strengths (i.e., costs add). Connection score between two
concepts = strength of best path, optionally summed over top-k disjoint paths ("connected many
ways" beats "connected once").

**Ordered-sequence bonus** (the name-letters case): when a query is a *sequence* ⟨q₁…qₙ⟩, score a
candidate Torah by aligning the sequence against the Torah's skeleton (order-preserving
alignment, gaps penalized — Smith–Waterman over concepts instead of DNA bases). All items
explicitly present, in order, in one chapter ⇒ near-max score, exactly matching your intuition
that this is "the highest weight possible."

---

## 4. The projection engine

Pipeline for "map X onto the Torahs" where X = dream, name, news article, science concept, life
situation:

1. **Decompose** (LLM): extract from X its entities and its causal/sequential structure — the
   same bechina/eitza shapes, in the target domain. Output: a small query graph.
2. **Bridge** (embeddings + registry): for each query entity, find candidate Torah concepts —
   via alias registry, multilingual embeddings, and letter/gematria expanders for name-type
   queries (each letter → its known concept aspects, from the graph itself).
3. **Align** (structure mapping): for each candidate Torah skeleton, find the best
   order-preserving correspondence between the query graph and the skeleton; score with §3.
4. **Rank & prove**: return top mappings, each rendered as: the correspondence table (your X ↔
   his concept), the weight breakdown, and — crucially — the **proof quotes** at every step.
   The output must read like the experience: "this is exactly what he says in Torah N, here."

Steps 2–3 are classic candidate-generation + verification; step 1 and the final rendering are
where the LLM lives. The graph keeps the LLM honest (no hallucinated connections — every edge
must exist in the data), and the LLM gives the graph reach into arbitrary domains.

---

## 5. The two gold datasets (the project's secret weapons)

1. **The manual 4,168 edges** → evaluation set for extraction. Run AI extraction over the same
   Torahs; measure recall (does it find what you found?) and review precision on a sample (are
   its new edges real?). Iterate on the prompt until recall on your edges is ≥95%, then trust it
   to run exhaustively. This converts years of pre-AI labor into the thing AI work always
   lacks: ground truth.

2. **Likutey Halachos** → evaluation set for *projection*. Reb Noson's book is thousands of
   worked, authoritative projections of LM Torahs onto the halachic dimension — and new-sefer has
   it fully translated and chunked. Extract (Torah skeleton → halacha mapping) pairs from LH;
   then the projection engine is good exactly to the degree that, given the halacha side alone,
   it re-discovers which Torah Reb Noson mapped it to and how the correspondence runs. **This is
   the benchmark that makes "projection quality" measurable at all.** No other team on earth has
   this dataset.

---

## 6. Build phases

**Phase 0 — Consolidate (small, do first)**
- Import torahData.js into the occurrence format (§2.2); fix the `cause`/`eitza ` type variants;
  map `reference` values onto new-sefer anchors.
- Stand up the repo structure for the layers (occurrences/, registry/, graph/, skeletons/).

**Phase 1 — Canonicalize**
- Cluster the 4,299 surface forms (normalize niqqud/quotes → embed → cluster → LLM adjudicates
  each cluster with proof texts → human spot-review). Output: concept registry + alias table.
- First payoff visible immediately in the existing Sigma visualizer: the graph *connects*.

**Phase 2 — Exhaustive extraction (LLM, one-chunk-per-agent, same pipeline discipline as the
translation work — SDK script + usage guard)**
- Prompted with framework.md definitions + few-shot from gold edges; validated per §5.1.
- Cover LM I+II fully; emit occurrences with anchors, cues, explicitness, confidence.

**Phase 3 — Skeletons + calculator**
- Per-Torah eitza skeletons (with macro/micro refinement); package + polarity assignment
  (framework.md rules); the weighted path/alignment scorer as a Python library with a CLI:
  `connect <concept> <concept>`, `match-sequence <a,b,c,...>`.

**Phase 4 — Projection engine + LH benchmark**
- Extract the LH projection pairs; build the decompose→bridge→align→prove pipeline; tune weights
  against the benchmark.

**Phase 5 — The product surface**
- Query UI (natural-language box → engine → proof-annotated answer), graph explorer (upgrade
  mapjs), and the generative direction: propose *new* projections onto a chosen domain and rank
  them for human review — light in the darkness, on demand.

Each phase produces something usable on its own; nothing gambles on the far rungs.

---

## 7. Risks & disciplines

- **Over-merging in canonicalization** silently corrupts everything downstream — keep merges
  justified and reversible (registry edits, never occurrence edits).
- **LLM-invented edges**: extraction must quote its proof span verbatim; a validator rejects any
  occurrence whose proof isn't found at its anchor. (Same trick as the translation verifiers.)
- **Weight-tuning by vibes**: only tune against the LH benchmark and the gold edges, or the
  numbers mean nothing.
- **Scope creep toward the far horizon**: the future-sight rung is a direction, not a milestone;
  ship the calculator and the projection engine first.
