# Enrich Packages with Cause/Effect Nodes

Assign cause/effect (eitza and cause-type) nodes to existing bechina-based packages for a specific Torah.

## Argument format

`$ARGUMENTS` is either:
- A plain number (e.g. `42`) → **Likutay Moharan Volume 1 (LM1)**
- A prefixed number (e.g. `lm2/42`) → **Likutay Moharan Tinyana Volume 2 (LM2)**

Parse the argument at the start:
- If `$ARGUMENTS` starts with `lm2/`, set **VOLUME = lm2** and **NUM = the number after the slash**
- Otherwise, set **VOLUME = lm1** and **NUM = $ARGUMENTS**

For LM2, the reference number in torahData.js is `1000 + NUM` (e.g. lm2/5 → reference 1005).

All path and filename references below use VOLUME and NUM.

## What you are doing

You are enriching existing bechina-based packages by assigning cause/effect nodes that are NOT yet in any package. Each unassigned node gets placed into the package that matches its **essential nature** — not simply the package of whatever it connects to via cause/effect.

Read `/home/user/mapjs/docs/framework.md` first for the full conceptual framework.

## Input files

- **Edge data**: `/home/user/mapjs/data/torahData.js`
  - **IMPORTANT**: This file is ~6MB. Do NOT read it directly. Instead, run a Node.js script to extract just the edges you need:
    ```
    node -e '
    const fs = require("fs");
    let d = fs.readFileSync("/home/user/mapjs/data/torahData.js","utf8");
    d = d.replace("const torahData = ","module.exports = ");
    fs.writeFileSync("/tmp/_td.js", d);
    const td = require("/tmp/_td.js");
    const ref = REF_NUM;
    const edges = td.filter(e => e.reference === ref && (e.type === "eitza" || e.type === "cause"));
    fs.writeFileSync("/tmp/torah_REF_NUM_ce_edges.json", JSON.stringify(edges, null, 2));
    console.log("Extracted " + edges.length + " edges");
    '
    ```
    Replace REF_NUM with the actual reference number. Then read `/tmp/torah_REF_NUM_ce_edges.json`.
  - Filter: `reference === REF_NUM` AND (`type === 'eitza'` OR `type === 'cause'`)
  - REF_NUM = NUM for LM1, 1000+NUM for LM2
  - Each edge has: `id`, `node1_id`, `node2_id`, `node1_text`, `node2_text`, `proof`, `type`, `is_good`, `is_bad`
- **Existing packages**: `/home/user/mapjs/data/review/torah_NUM_packages.json` (LM1) or `/home/user/mapjs/data/review/lm2/torah_NUM_packages.json` (LM2)
  - Also check `torah_NUM_additions.json` in the same directory for additional nodes already assigned
- **Torah source text**: `/home/user/mapjs/data/torah_texts/VOLUME/torah_NUM.txt`
  - Read the full text to understand context and the nature of each concept

## Algorithm

### Step 1 — Collect all nodes already in packages

From the existing `torah_NUM_packages.json`, gather every node from every package's `"nodes"` array into a set called `ASSIGNED_NODES`.

Also check `torah_NUM_additions.json` — any nodes listed there should also be added to `ASSIGNED_NODES` (they were identified in gap analysis).

### Step 2 — Extract cause/effect edges

From `torahData.js`, collect all edges where `reference === REF_NUM` AND (`type === 'eitza'` OR `type === 'cause'`).

### Step 3 — Identify unassigned nodes

For each cause/effect edge, check both `node1_id` and `node2_id`:
- If a node is already in `ASSIGNED_NODES`, skip it — it already has a home.
- If a node is NOT in `ASSIGNED_NODES`, it needs assignment.

Collect the set of all unique unassigned nodes. De-duplicate — a node may appear in multiple edges but only needs one assignment.

### Step 4 — Read the Torah source text

Read the full Torah text file. Use this along with the `proof` field on each edge to understand the essential nature of each unassigned concept.

### Step 5 — Assign each unassigned node to a package

For each unassigned node, determine which existing package it belongs to **by its essential nature**:

- **The key question**: "What IS this concept, at its core? Which thematic domain does it belong to?"
- **Do NOT** simply assign it to the package of whatever it connects to via the eitza/cause edge. The connection tells you there is a causal relationship, but the node's *nature* determines its package.
- Example: If `לימוד תורה` (learning Torah) causes `חכמה` (wisdom), and חכמה is in the Wisdom package — `לימוד תורה` should go in a Torah package if one exists, because its essential nature is Torah, not wisdom. It *produces* wisdom but it *is* Torah.
- Consider the polarity: is this a good-domain, evil-domain, or neutral concept?
- If a node genuinely doesn't fit any existing package, flag it as unassigned with a reason.
- If multiple unassigned nodes form a coherent new thematic cluster, propose a new package.

### Step 6 — Handle edge cases

- **Node appears in multiple edges**: Assign it once. Use all its edges as context for understanding its nature.
- **Both sides of an edge are unassigned**: Both need assignment. They may go to different packages.
- **No existing packages file**: If `torah_NUM_packages.json` doesn't exist, report this and stop — we need bechina packages first.
- **Zero cause/effect edges**: Write an output file noting zero edges found.

## Output directory

- **LM1**: `/home/user/mapjs/data/review/`
- **LM2**: `/home/user/mapjs/data/review/lm2/`

## Output file: `torah_NUM_cause_effect.json`

```json
{
  "meta": {
    "source": "Torah #NUM (Likutay Moharan VOLUME)",
    "volume": "VOLUME",
    "type": "cause_effect_package_assignment",
    "generated": "YYYY-MM-DD",
    "based_on": "torah_NUM_packages.json"
  },
  "assignments": [
    {
      "node_id": "concept_id",
      "node_text": "vowelized Hebrew text",
      "edge_type": "eitza|cause",
      "edge_ids": [123, 456],
      "connected_to": ["node_it_connects_to_1", "node_it_connects_to_2"],
      "package_id": 1,
      "package_label": "Hebrew Package Label",
      "package_label_en": "English Package Label",
      "polarity": "good|evil|neutral",
      "reason": "Why this node's essential nature places it in this package, not just because of its causal connection"
    }
  ],
  "new_packages": [
    {
      "id": "new_1",
      "label": "Hebrew label",
      "label_en": "English label",
      "polarity": "good|evil|neutral",
      "reason": "Why these nodes form a new thematic cluster",
      "nodes": ["node1", "node2"]
    }
  ],
  "unassigned_nodes": [
    {
      "node_id": "concept_id",
      "node_text": "vowelized Hebrew",
      "edge_ids": [789],
      "reason": "Why this node doesn't fit any existing package"
    }
  ],
  "stats": {
    "total_cause_eitza_edges": 0,
    "unique_unassigned_nodes": 0,
    "nodes_assigned_to_existing": 0,
    "nodes_in_new_packages": 0,
    "nodes_unassigned": 0,
    "nodes_already_in_bechina_packages": 0
  }
}
```

## Quality checks before writing

- Every unassigned node from Step 3 appears exactly once in either `assignments`, `new_packages`, or `unassigned_nodes`
- No node that was already in a bechina package appears in `assignments`
- Every assignment has a reason explaining the node's **essential nature**, not just its causal connection
- Polarity is assigned to every node
- The `connected_to` field accurately lists what the node connects to via cause/effect edges
- Stats numbers are consistent (unique_unassigned_nodes = nodes_assigned_to_existing + nodes_in_new_packages + nodes_unassigned)

## Notes

- Torah text files use nikud (vowel marks) — node_ids in torahData.js may use simplified spelling; match by root/consonants
- The `proof` field on each edge is your best evidence for understanding a concept's nature
- Some edges have `is_bad: 1` confirming evil polarity
- For `eitza` edges: `node1_id` is the cause, `node2_id` is the effect
- For `cause` edges: `node1_id` is the cause, `node2_id` is the effect
- Do NOT modify any existing package files — this is additive only
