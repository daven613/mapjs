# Plan: Add Cause/Effect Nodes to Packages

## The Problem

Currently, packages only contain **bechina** nodes (parallel/shared-nature concepts). But the **other side** of cause/effect edges — the nodes that aren't already in a bechina package — should also become **full members** of a package.

For example, if there's an eitza edge `לימוד תורה → חכמה`, `חכמה` is already in the Wisdom package (from bechina analysis). We need to assign `לימוד תורה` — the node that has no package yet — to an appropriate package **by its essential nature** (in this case, perhaps a Torah package, not the Wisdom package it merely connects to).

## Current State

- ~200+ Torahs have existing `torah_N_packages.json` files (bechina-only)
- 206 Torahs have cause/eitza edges in `torahData.js`
- 1,894 total cause/eitza edges (1,698 eitza + 196 cause)
- No cause/effect package assignment exists yet

## Approach: New Slash Command + Parallel Agents

### Step 1: Create a new slash command `.claude/commands/enrich-packages.md`

This command takes a Torah number (like `analyze-torah`), and for that Torah:

1. **Reads** the existing `torah_N_packages.json` to get current bechina-based packages and their node lists
2. **Extracts** all `eitza` and `cause` edges from `torahData.js` where `reference === N`
3. **Collects only the "unassigned" nodes** — for each edge, checks which side (node1 or node2) is NOT already in a bechina package. Only those unassigned nodes need placement. (If both sides are already in packages, the edge is skipped. If neither side is in a package, both need assignment.)
4. **Reads** the Torah source text for context
5. **For each unassigned cause/effect node**, uses AI judgment to determine which package it belongs to **by its essential nature** (not by which package the other end of the edge belongs to)
   - If a node doesn't fit any existing package, proposes a new package or flags it as unassigned
6. **Writes** output to a new file: `torah_N_cause_effect.json`

### Step 2: Output File Format

Each Torah gets a new file `torah_N_cause_effect.json`:

```json
{
  "meta": {
    "source": "Torah #N (Likutay Moharan Vol. X)",
    "type": "cause_effect_package_assignment",
    "generated": "YYYY-MM-DD",
    "based_on": "torah_N_packages.json"
  },
  "assignments": [
    {
      "node_id": "לימוד תורה",
      "node_text": "לִמּוּד תּוֹרָה",
      "edge_type": "eitza",
      "edge_id": 123,
      "connected_to": "חכמה",
      "direction": "cause",
      "package_id": 1,
      "package_label": "חָכְמָה וְיַעֲקֹב",
      "polarity": "good",
      "reason": "Learning Torah is essentially a wisdom-domain activity..."
    }
  ],
  "new_packages": [],
  "unassigned_nodes": [],
  "stats": {
    "total_cause_eitza_edges": N,
    "total_new_nodes_assigned": N,
    "nodes_already_in_packages": N
  }
}
```

### Step 3: Test Batch (5 Torahs)

Run the command on 5 Torahs with good cause/eitza coverage and existing packages:

1. **Torah 1** — the worked example in framework.md, 6 edges, very well documented
2. **Torah 5** — 57 cause/eitza edges, rich test case
3. **Torah 4** — 42 edges
4. **Torah 7** — 39 edges
5. **Torah 14** — 39 edges

We run these as **5 parallel agents**, each invoking the new slash command on one Torah.

### Step 4: Review Results

After the test batch:
- Check that assignments make sense (nodes assigned by nature, not just connection)
- Verify the JSON format is consistent
- Decide if we need to adjust the command before scaling to all ~200 Torahs

### Step 5: Scale Up

Once validated, run remaining Torahs in parallel batches of ~10 agents at a time.

## Implementation Order

1. Create `.claude/commands/enrich-packages.md` (the slash command definition)
2. Run test batch of 5 Torahs in parallel using agents
3. Review output files
4. Iterate on command if needed
5. Scale to remaining Torahs
