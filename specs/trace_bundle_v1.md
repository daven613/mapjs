# Trace bundle v1 — the story-trace "interpretation bundle" format

A **trace bundle** is the JSON the explorer's *Story trace* mode renders: a story (or news
item, or any narrative) segmented into beats, each segment projected onto a Likutey Moharan
teaching as a chain of concepts joined by attested cause→effect and aspect hops, plus the prose
narrative that walks a reader through it. It is the hand-off artifact from a CLI interpretation
session to the visual explorer: the session writes a bundle, `scripts/make_trace.py` validates
and installs it under `ontology/graph/traces/<slug>.json`, and the explorer renders it clickable
at `explorer.html?trace=<slug>`.

The canonical example is the **Lost Princess** (`ontology/graph/story_trace.json`, also installed
as `ontology/graph/traces/lost-princess.json`). `scripts/segment_project.py` produces the
structural core; the narration fields are added on top.

This document is the contract `scripts/make_trace.py` enforces. Rules are derived from two things:
what `explorer.html`'s renderer actually consumes (`renderTraceList` / `selectTraceSegment` /
`showTraceOverview` / `showUnknownDetail`, and the projection it **recomputes live** from each
segment's `ids`), and the bundle's provenance promise — every concept id resolves against the
graph and every projection hop carries a proof quote and a source reference.

## How the explorer uses a bundle (why the rules are what they are)

- The left rail lists the **sequence** (beats, colored by segment), the **segments**, any
  **bridges** and **unresolved slots**, and a link to the full narrative.
- Selecting a segment calls `runProjectFor(segment.ids)` — the explorer **re-runs the projection
  from scratch** against the live graph. So a segment's stored `project` block is provenance and
  audit, not the render source; but `project.home` and `project.cost` *are* read directly for the
  segment list, and every id the projection touches must exist in the graph or the live recompute
  throws. That is why id-resolution is a hard error and the stored proofs are required.
- The overview shows `input.title` / `input.type` / `input.text_summary`, `process_notes`, and
  `narrative`. Selecting segment *i* also shows `narrative_by_segment[i]`.

## Top-level fields

| field | required | type | notes |
|---|---|---|---|
| `input` | yes | object | see below |
| `sequence` | yes | array | story beats, in order |
| `segments` | yes | array (≥1) | projectable segments |
| `narrative` | yes | non-empty string | the overview elaboration prose |
| `narrative_by_segment` | yes | array | one non-empty string per segment, aligned 1:1 |
| `bridges` | optional | array | jumps between segments that cross teachings |
| `unknown_resolutions` | optional | array | ranked candidates for unfilled story slots |
| `process_notes` | optional | string | how the interpretation was built |

### `input`

| field | required | type |
|---|---|---|
| `title` | yes | non-empty string (also seeds the install slug) |
| `type` | optional | string |
| `text_summary` | optional | string |

Example:

```json
"input": {
  "title": "The Lost Princess (Ma'aseh Me'Aveidat Bat Melech) — first of Rebbe Nachman's Sipurei Ma'asiyot",
  "type": "story",
  "text_summary": "A king had six sons and one daughter…"
}
```

### `sequence` — story beats

Array of beats in narrative order. Each beat:

| field | required | type | notes |
|---|---|---|---|
| `status` | recommended | `"known"` / `"unknown"` | a `known` beat is anchored to a concept |
| `id` | required **iff** `status=="known"` | string | must resolve against `ontology/graph/nodes.json` |
| `slot` | recommended | int | the beat's index |
| `he` / `phrase` | optional | string | display label (renderer falls back to `id`) |

```json
{"slot": 0, "status": "known", "id": "c:king-sovereign-ruler", "he": "מלך", "phrase": "a king had a beloved, only daughter"}
```

### `segments` — projectable units (≥1)

Each segment groups consecutive beats and carries the projection of their concepts onto one
teaching. Each segment:

| field | required | type | notes |
|---|---|---|---|
| `slots` | yes | array of int | indices into `sequence` (each `0 ≤ slot < len(sequence)`) |
| `ids` | yes | array (≥1) | concept ids the projection is recomputed from; each resolves against the graph. `<2` is allowed but warns (no causal chain forms) |
| `project` | yes | object | see below |
| `segment_index` | optional | int | |

#### `segment.project`

| field | required | type | notes |
|---|---|---|---|
| `home` | key required; value nullable | string ref (`"I:10"`) or `null` | `null` = cross-Torah projection |
| `cost` | yes | number | total projection weight (read for the segment list) |
| `chain` | yes | array (≥1) | the causal-spine anchors; each entry's `id` resolves |
| `mappings` | yes | array | one per picked concept; warns if count ≠ `len(ids)` |
| `links` | yes | array | causal hops joining consecutive anchors; warns if count ≠ `len(chain)-1` |

**`mappings[i]`** — how pick *i* maps onto its anchor:

| field | required | type | notes |
|---|---|---|---|
| `pick` | yes | resolvable id | the source concept |
| `anchor` | yes | resolvable id | the in-teaching concept it maps onto |
| `pcost` | yes | number | mapping cost |
| `kind` | recommended | `"aspect"` / `"self"` / `"shared"` | |
| `hops` | yes (array) | array of hop | may be **empty only** when `kind` is `"self"` or `"shared"` |
| `shared_terms` | optional | array | shown when a `shared` (semantic) mapping has no graph path |

**`links[i]`** — a causal path between two anchors:

| field | required | type |
|---|---|---|
| `cost` | yes | number |
| `hops` | yes | non-empty array of hop |

**hop** (in both `mappings[].hops` and `links[].hops`) — the atom of provenance:

| field | required | type | notes |
|---|---|---|---|
| `from` | yes | resolvable id | |
| `to` | yes | resolvable id | |
| `proof` | yes | non-empty string | the source quote that attests this step |
| `ref` | yes | non-empty array | source teaching(s), `"I:10"`-style (non-matching entries warn) |
| `kind` | required in `links` hops | `"cause"` / `"reframe"` | warns otherwise |
| `hc` | optional | number | hop cost |

```json
{"from": "c:like-moses-joseph", "to": "c:emunah-2", "kind": "cause", "hc": 0.12,
 "proof": "נִמְצָא, שֶׁעַל־יְדֵי הַצַּדִּיק … וְנִתְרַבֶּה הָאֱמוּנָה …", "ref": ["I:10"]}
```

### `bridges` (optional)

A real jump between teachings where the graph has no attested hop. Each:

| field | required | type |
|---|---|---|
| `note` | yes | non-empty string |
| `penalty` | yes | number |
| `from_segment` / `to_segment` / `from_id` / `to_id` | optional | |

### `unknown_resolutions` (optional)

Ranked, attested candidates for a story slot the interpretation could not fill. Each:

| field | required | type | notes |
|---|---|---|---|
| `anchor` | yes | resolvable id | the known neighbor |
| `direction` | yes | `"prior"` / `"next"` | what precedes / follows the anchor |
| `candidates` | yes | array | each candidate has a resolvable `id` (and typically `he`, `gloss`, `ref`, `proof`, `in_home`) |
| `home` / `note` / `slot` / `label` | optional | | |

### `narrative_by_segment` and `narrative`

`narrative_by_segment` is an array with exactly one entry per segment (aligned 1:1); each entry is
a non-empty string shown when that segment is selected. `narrative` is the non-empty overview
prose. Both may contain `\n` (rendered as line breaks).

## Validation summary (`scripts/make_trace.py`)

Errors (exit 1) — the bundle will not render or breaks the provenance promise:

- a required top-level key, or `input.title`, is missing/empty;
- any `known` sequence beat, any `segment.ids` entry, any `chain`/`mapping`/`hop`/candidate id, or
  any `unknown_resolutions.anchor` does **not** resolve against `ontology/graph/nodes.json`;
- a `segment.slots` entry is out of range, or `slots`/`ids`/`project` is missing;
- `project.cost` / `mapping.pcost` / `link.cost` is not a number, or `project.home` key is absent;
- a hop lacks a non-empty `proof` or a non-empty `ref`; a `links` hop has no hops; a hopless
  mapping whose `kind` is not `self`/`shared`;
- `narrative_by_segment` length ≠ segment count, or any per-segment note (or `narrative`) is empty;
- a `bridge` lacks `note`/`penalty`.

Warnings (still valid) — count mismatches (`mappings` vs `ids`, `links` vs `chain-1`), a
single-concept segment, a `ref` entry that is not `"I:10"`-shaped, a non-`cause`/`reframe` link
hop kind, or an odd `home`/`status` value.

## Producing and installing

```
python3 scripts/make_trace.py BUNDLE.json                # validate + install, print URL
python3 scripts/make_trace.py BUNDLE.json --check        # validate only
python3 scripts/make_trace.py BUNDLE.json --slug my-story # explicit slug
cat BUNDLE.json | python3 scripts/make_trace.py -        # from stdin
```

The install slug comes from `--slug` or is derived from `input.title` (lowercased, non-alphanumeric
runs → `-`). The printed URL is the canonical deep-link:

```
http://localhost:8890/explorer.html?trace=<slug>&t=<epoch>
```

`<slug>` is re-sanitized in the browser to `[a-z0-9_-]`, so it can never escape the `traces/`
directory. The `&t=<epoch>` cache-buster is belt-and-suspenders atop the server's no-store headers
(`scripts/serve_explorer.sh`).
