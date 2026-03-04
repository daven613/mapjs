# Analyze Torah Packages

Analyze a Torah from Likutay Moharan to identify its thematic concept packages (חֲבִילוֹת).

## Argument format

`$ARGUMENTS` is either:
- A plain number (e.g. `42`) → **Likutay Moharan Volume 1 (LM1)**
- A prefixed number (e.g. `lm2/42`) → **Likutay Moharan Tinyana Volume 2 (LM2)**

Parse the argument at the start:
- If `$ARGUMENTS` starts with `lm2/`, set **VOLUME = lm2** and **NUM = the number after the slash**
- Otherwise, set **VOLUME = lm1** and **NUM = $ARGUMENTS**

All path and filename references below use VOLUME and NUM.

## What you are doing

You are a researcher analyzing a specific Torah from Likutay Moharan (Rebbe Nachman of Breslov). Your job is to identify the **concept packages** — thematic clusters of concepts connected by bechina (parallel/shared-nature) relationships.

Read `/Users/shmuel/dev/mapjs/docs/framework.md` first for the full conceptual framework before doing anything else.

## Input files

- **Edge data**: `/Users/shmuel/dev/mapjs/data/torahData.js`
  - Filter: `reference === NUM` AND `type === 'bechina'` AND `volume === 'VOLUME'` (if volume field exists) — or just `reference === NUM` AND `type === 'bechina'` if no volume field
  - Each edge has: `id`, `node1_id`, `node2_id`, `node1_text`, `node2_text`, `proof`, `is_good`, `is_bad`
- **Torah source text**: `/Users/shmuel/dev/mapjs/data/torah_texts/VOLUME/torah_NUM.txt`
  - Read the full text to understand the Torah's argument and themes

## Output directory

- **LM1**: `/Users/shmuel/dev/mapjs/data/review/`
- **LM2**: `/Users/shmuel/dev/mapjs/data/review/lm2/`

Create the output directory if it does not exist.

## Algorithm

### Step 1 — Extract the bechina subgraph
From `torahData.js`, collect all edges where `reference === NUM` AND `type === 'bechina'`. List every unique node and every edge.

### Step 2 — Find connected components
Build an adjacency graph from those edges. Find all connected components (sets of nodes reachable from each other through bechina edges). List each component with its nodes and their degrees (number of bechina edges).

### Step 3 — Name and characterize each component
For each component (starting with the largest):
- Identify the **dominant node** (highest degree count)
- Identify the **polarity**: `good`, `evil`, or `neutral`
  - `good` = domain of holiness, the positive teaching
  - `evil` = domain of opposition, the negative force
  - `neutral` = structural objects (letters, body parts, phenomena) used as metaphors in both domains
- Write a **reason** explaining what binds these nodes together as one thematic family
- Look for the **good/evil mirror structure**: for every good package, find its evil counterpart

### Step 4 — Propose package merges for small components
Components with 1–2 nodes are usually isolated pairs. For each:
- Read the `proof` text on their edge
- Determine which larger component they thematically belong to
- Document the merge reason
- **Critical rule**: merge based on SHARED NATURE (bechina), not cause-and-effect (eitza). If concept A *produces* concept B, that is eitza (they belong to different packages). If A and B are *two expressions of the same thing*, that is bechina (they belong together).

### Step 5 — Gap analysis
After finalizing packages:
1. Check every node in the bechina edges — are all nodes assigned to a package? List any orphaned nodes.
2. Read the Torah source text carefully. For every concept the Rebbe explicitly calls a "בְּחִינַת" (bechina) — is it in the dataset? If not, flag it as a missing node.
3. For each gap: suggest which package it belongs to and provide the source quote.

### Step 6 — New package check
Ask: are there 3+ concepts connected by explicit bechina language in the source text that form an **independent domain** not covered by the existing packages? If yes, propose a new package. If not, state NO_NEW_PACKAGES with reasoning.

## Output files

Write three JSON files to the output directory for this volume.

### File 1: `torah_NUM_packages.json`
```json
{
  "meta": {
    "source": "Torah #NUM (Likutay Moharan VOLUME)",
    "volume": "VOLUME",
    "type": "package_proposals",
    "generated": "YYYY-MM-DD",
    "algorithm": "connected_components_bechina_only"
  },
  "packages": [
    {
      "id": 1,
      "torah_ref": NUM,
      "volume": "VOLUME",
      "label": "Hebrew label",
      "label_en": "English label",
      "polarity": "good|evil|neutral",
      "reason": "Why these nodes share the same essential nature",
      "dominant_node": "node_id of most-connected node",
      "nodes": ["node_id1", "node_id2", ...],
      "node_degrees": { "node_id": degree_count },
      "merge_notes": [
        {
          "merged_nodes": ["nodeA", "nodeB"],
          "reason": "Why this small component was merged here"
        }
      ]
    }
  ],
  "stats": {
    "total_bechina_edges": N,
    "total_nodes": N,
    "total_packages": N,
    "raw_connected_components": N
  }
}
```

### File 2: `torah_NUM_additions.json`
```json
{
  "meta": {
    "source": "Torah #NUM (Likutay Moharan VOLUME)",
    "volume": "VOLUME",
    "type": "package_gap_analysis",
    "generated": "YYYY-MM-DD"
  },
  "additions": [
    {
      "package_id": N,
      "node_id": "concept_id",
      "node_text": "Hebrew text",
      "polarity": "good|evil|neutral",
      "reason": "Why this concept belongs here",
      "source_quote": "Direct quote from torah text with bechina language",
      "in_dataset_already": false
    }
  ],
  "unassigned_dataset_nodes": [
    {
      "node_id": "node_id",
      "suggested_package_id": N,
      "reason": "Why this orphaned node belongs in that package"
    }
  ],
  "analysis_notes": {
    "total_bechina_edges": N,
    "nodes_in_dataset_not_in_packages": ["node1", "node2"],
    "concepts_in_source_text_not_in_dataset": ["concept1"]
  }
}
```

### File 3: `torah_NUM_new_packages.json`
```json
{
  "meta": {
    "source": "Torah #NUM (Likutay Moharan VOLUME)",
    "volume": "VOLUME",
    "type": "new_package_proposals",
    "generated": "YYYY-MM-DD"
  },
  "verdict": "NO_NEW_PACKAGES | NEW_PACKAGES_PROPOSED",
  "new_packages": [],
  "observations": "Detailed analysis of why the existing packages are complete or why new ones are needed"
}
```

## Quality checks before writing

- **Both sides of every edge must be explicitly defined.** Whenever you identify a bechina relationship between A and B, both A and B must be named Hebrew concepts with their own node entries. Whenever you identify an eitza (cause→effect) relationship, both the cause node and the effect node must be named. Never record a half-edge where only one side is specified.
- Every bechina-connected node in the dataset appears in exactly one package
- No eitza (cause-effect) connections are used to group nodes into the same package
- Polarity is assigned to every package
- The good/evil mirror is documented where it exists
- All merge decisions have written reasoning
- The source text has been read and checked for missing concepts

## Notes

- Torah text files use nikud (vowel marks) — the node_ids in torahData.js may use simplified spelling without nikud; match by root/consonants
- Some edges have `is_bad: 1` which confirms evil polarity for those nodes
- The `proof` field on each edge contains a direct quote from the source text — use these as primary evidence
- Package labels should be in Hebrew (with nikud) + English translation
- Do NOT modify `analysis_progress.json` or `lm2_analysis_progress.json`
