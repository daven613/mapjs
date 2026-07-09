# v2 Merge Policy — folding `ai_extracted/` into the canonical graph (2026-07-09)

Decided before coding, per the merge-session brief. Governs `scripts/compile_graph.py`.

## Inputs

- `ontology/occurrences/legacy_human.jsonl` — 4,148 curated human occurrences (unchanged).
- `ontology/occurrences/ai_extracted/*.json` — 3,880 chunk files (157 schema-1, 3,723
  schema-2), 16,007 candidate edges with verbatim proofs.
- `ontology/registry/concepts_final.json` — 3,588 canonical concepts (identity = gloss).

## Relation types

Exactly the pre-existing vocabulary: `eitza` (directed cause→effect), `bechina`
(undirected parallel), `equation` (explicit identity; traversal-wise an aspect edge —
already supported by tmap and the explorer, just previously unpopulated). **No new
relation types**; polarity/via are edge *attributes*, never types.

## Polarity / via (first-class on every edge)

- Schema-2 eitza edges: as extracted (`builds|harms|neutral` × `presence|absence`).
- Schema-1 (v1) eitza edges lacking the fields: default `builds`/`presence` (per
  `specs/extraction_v2.md` §Compatibility).
- ALL bechina/equation edges: coerced to `neutral`/`presence` (aspects are
  polarity-free; the spec keeps lack-parallels-lack as a query-time inference).
  Coercions of a non-default extracted value are counted and reported.
- Legacy human eitza edges: `builds`/`presence` (the human layer was curated as the
  good-flow map). Legacy bechina: `neutral`/`presence`.

## Edge identity & conflicting attestations (the design fork)

Edges aggregate by **(source, target, type, polarity, via)**. Weight = number of
attesting occurrences; every edge keeps all proof occurrence ids.

Consequence: if the text attests both "X brings Y" and "X damages Y", they live as two
SEPARATE edges between the same pair, each with its own polarity and proofs. Nothing is
averaged, voted on, or discarded — both readings stay queryable and provable.

*Recommendation implemented; alternative considered and rejected:* a single
(s,t,type) edge carrying a polarity→proofs map would keep the edge count closer to v1
but makes every consumer (tmap traversal, explorer rendering, path costs) branch on an
inner structure, and a single `polarity` field would have to lie for mixed edges. The
parallel-edges shape keeps polarity a plain field everywhere. If Shmuel prefers the
merged shape, the compile step is deterministic and re-runnable — flipping the policy
is a one-line key change, no data loss.

## Endpoint resolution (surface → canonical concept)

Deterministic lexical ladder only — **no gloss-similarity at merge time** (that stays a
flagged last-resort inside projection queries, per the standing rule; the A4 incident —
"פגם האמונה" substring-matching "אמונה" — is exactly the corruption class this avoids):

1. **exact**: NFC, strip niqqud+te'amim, maqaf→space, normalize gershayim/geresh,
   collapse non-letter chars; match against every concept form + canonical_he.
2. **article**: same, after stripping a leading ה from each word (התורה → תורה).
3. **skeleton**: plene/defective folding (drop י/ו) — accepted ONLY when the skeleton
   maps to exactly one concept across the whole registry (ambiguous skeletons are
   dropped from the index, so דבור/דיבור resolves only if no other concept collides).
4. **skeleton+article**: 2 then 3.

At EVERY rung, a key owned by more than one concept (homograph splits like שדי) is
treated as unresolved rather than silently awarding a winner. Ladder rung per endpoint
is counted and reported in stats.

## Unresolved endpoints

- One endpoint resolved, the other not → the unresolved surface becomes a **statement
  node** (`kind: "statement"`, id `p:NNNN`, deduped by normalized surface, provenance
  `ai`). Same mechanism the legacy compile already uses for proposition targets;
  statement nodes are excluded from search/match pools but traversable and provable.
  This is what keeps the harms/absence (פגם) layer alive: only 105/482 harms+absence
  edges resolve on both sides, 340/482 with one side.
- **Neither** endpoint resolved → the edge is NOT stored (counted + reported as
  `skipped_islands`). Rationale: a proposition→proposition edge touching zero canonical
  concepts adds no query value and floods the map; the chunk files remain the source of
  truth, and the compile is re-runnable if the policy changes (e.g. after an alias pass
  maps recurring unresolved forms onto concepts).
- Self-loops after resolution (source==target) are dropped and counted.

## Provenance

Each stored AI edge occurrence gets id `occ:ai:<book>_<chunk>:<idx>` written to
`ontology/occurrences/ai_compiled.jsonl` (proof, anchor book/torah, type, polarity,
via, explicitness, extractor). `build_explorer_data.py` reads it alongside
`legacy_human.jsonl` for proof text and torah refs. Attested only — the merge stores no
inferred edges; `diagnose` keeps inferring at query time.

## Known follow-up (not in this merge)

~982 unresolved normalized forms recur ≥3× (דיבור, שמירת הברית, מצח הנחש, …). A
verified alias pass (LLM judges each form against candidate concept glosses) would lift
both-side resolution well above the current ~26%; recommended as a separate reviewed
step, since lexical-only aliasing is exactly the corruption vector this policy exists
to block.

---

## Merge results (executed 2026-07-09, this policy as implemented)

Before (2026-07-03 graph): 4,215 nodes (3,588 concepts + 627 statements), 3,939 edges
(bechina 2,114 / eitza 1,825), no polarity data.

After: **9,018 nodes** (3,588 concepts + 627 legacy statements + 4,803 AI
phrase-statements) and **12,328 edges** — bechina 5,346 / eitza 5,106 / equation 1,876.

Polarity (edges): builds 4,132 · harms 974 · neutral 7,222.
Via (edges): presence 12,000 · absence 328.
Attestations by polarity/via: builds/presence 4,646 · harms/presence 705 ·
harms/absence 337 · builds/absence 11 · neutral/presence 8,821.

AI layer: 16,007 candidate edges in 3,880 chunks → 10,372 merged; 5,627 skipped as
islands (neither endpoint resolved); 8 self-loops dropped; 0 invalid polarity/via;
0 non-eitza polarity coercions needed. 764 chunks had empty extractions; 1,187 chunks
total contributed 0 merged edges. Resolution ladder (endpoint occurrences):
exact 11,755 · article 1,080 · skeleton 1,479 · skeleton+article 61 · unresolved 17,639.

Verification: `test_tmap.py` 70 passed / 1 skipped; `tmap selftest` ok (33 checks);
question battery 13/13 (A5 sleep~RH healed by the merge; A6 anger-cascade now attested
with harms labels); 5/5 harms/absence spot-checks surface via `advice --polarity harms`
with verbatim proofs; explorer headless projection harness 40/40 pick-sets (all stages
map non-silently, chains distinct, every referenced node resolvable and placed), zero
console errors on cache-busted load.
