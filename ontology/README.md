# ontology/ — the layered knowledge-graph store

Data model per [../docs/ENGINE_DESIGN.md](../docs/ENGINE_DESIGN.md). Four layers, plain JSON.
The text layer itself lives in the sibling repo (`~/dev/new-sefer/graph_poc/<book>/reading.json`)
and is referenced by chunk key (e.g. `lm1` + `23_1_4` = Torah 23, section 1, subsection 4).

```
occurrences/   evidence layer — one record per statement in the text; append-only, never edited
  _legacy_raw.json     verbatim dump of the pre-AI dataset (data/torahData.js)
  legacy_human.jsonl   the 4,168 hand-extracted edges as occurrence records (extractor: human-2019)
  import_report.json   anchoring stats + flagged (un-anchorable) edges
registry/      concept layer — canonical concepts, aliases, domains, polarity (Phase 1)
graph/         compiled graph — canonical nodes + weighted typed edges (derived, rebuildable)
skeletons/     per-Torah eitza chains / causal motifs (Phase 3)
```

## Occurrence record

```jsonc
{
  "id": "occ:legacy:3265",
  "type": "eitza",                    // bechina | eitza (legacy 'cause' folded into eitza)
  "legacy_type": "cause",             // original label, preserved
  "source_surface": "…", "target_surface": "…",   // raw strings as extracted — NOT canonical ids
  "proof": "…verbatim quote…",
  "explicitness": "explicit",
  "anchor": {
    "book": "lm2", "torah": 1, "chunks": ["1_2_0"],  // new-sefer chunk keys the proof spans
    "match": "full",                  // how the proof was located (see below)
    "legacy_reference": 1001          // original reference; >=1000 means LM II (ref-1000)
  },
  "extractor": "human-2019", "confidence": 1.0
}
```

`anchor.match` methods: `full`/`prefix80`/`prefix40` — exact normalized substring;
`windows` — k-mer voting (proof wording drifts from our edition but its fragments land in the
right chunks); `relocated+*` — proof was not in the torah its reference claimed, but was found
unambiguously elsewhere (caught real off-by-one reference errors, e.g. 34→33, 177→178);
`not_found` — flagged in import_report.json, kept unanchored rather than guessed.

Matching is niqqud/punctuation-insensitive (text normalized to bare Hebrew consonants).

Import stats (2026-07-02): 4,130/4,168 anchored (99.1%) — 3,177 exact/prefix, 948 windows,
5 relocated; 34 not found + 4 without usable reference.

Rebuild any time: `python3 scripts/import_legacy.py` (idempotent).
