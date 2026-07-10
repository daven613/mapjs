# Provenance toggle — vetted vs. speculative edges

The concept graph mixes two evidence layers. **Legacy** edges were hand-authored/reviewed
(`ontology/occurrences/legacy_human.jsonl`); **AI** edges were extracted automatically by the
LLM pipeline (`occ:ai:*` occurrences) and have **not** been hand-reviewed. The explorer's
provenance toggle lets a reader see and browse that split — an AI-vs-vetted lens over the whole
map — so the AI's concept links can be judged rather than trusted blind.

## Classification (per edge, one flag)

An edge is **vetted** iff at least one of its `proofs` occurrence ids contains `legacy`;
otherwise it rests only on AI-extracted occurrences and is **speculative**. This is computed
once at build time in `scripts/build_explorer_data.py` and emitted as a compact per-edge field:

    prov: "v"   # vetted   — has ≥1 legacy_human proof
    prov: "a"   # speculative — AI-extracted proofs only

As of the current graph: **3,939 vetted / 8,389 speculative / 12,328 total**.

`explorer_data.json` only carries one trimmed sample proof per edge (not the full `proofs`
array), so provenance can't be re-derived in the page — the `prov` flag is the single source of
truth the explorer reads.

## Explorer behaviour (`ontology/graph/explorer.html`)

- **3-state control** next to the mode buttons: **All** (default) / **Vetted only** /
  **Speculative only**, with a count readout (`3,939 vetted / 12,328 total`, plus what the
  active filter is showing).
- Switching the filter rebuilds the adjacency index (`buildAdj()`) from the passing edges, so
  **every graph traversal honours it automatically**: explore / aspects / advice / effects /
  path / common / project (all read `adj`), plus the direct-`EDGES` scans in torah / common.
  The current view is then re-run (`refreshView()`).
- **Canvas**: `redraw()` skips any edge failing `edgePasses()` (a filtered-out edge is never
  drawn). In **All** view, speculative edges render faded (½ alpha) and dashed, so vetted spine
  reads through the AI noise.
- **Detail panels**: speculative edges get an `AI` tag on their proof blocks (explore, path,
  and projection hop rows).
- **URL**: the filter persists as `&prov=vetted|ai` (omitted for `all`), composing with every
  mode's existing URL-state params and round-tripping through a fresh load / back-forward.
- Synthesized edges with no `prov` (story-trace stored provenance) are always shown, so a
  filter never hides an attested, hop-by-hop-verified chain.

## Rebuild

    python3 scripts/build_explorer_data.py     # re-emits explorer_data.json with prov flags
