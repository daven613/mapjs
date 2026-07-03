#!/usr/bin/env python3
"""Validate the projection premise: do single Torahs contain multi-step eitza (cause->effect)
chains A->B->C we can project a user's narrative onto? Find example chains to test against."""
import json, collections
from pathlib import Path

G = Path(__file__).resolve().parent.parent / "ontology/graph"
d = json.loads((G / "explorer_data.json").read_text())
byId = {n["id"]: n for n in d["nodes"]}

# eitza edges grouped by Torah ref they occur in (directed s->t = cause->effect)
by_torah = collections.defaultdict(list)   # ref -> [(s,t,edge)]
for e in d["edges"]:
    if e["ty"] != "eitza":
        continue
    for r in e.get("ref", []):
        by_torah[r].append((e["s"], e["t"], e))

# find directed chains length>=2 (A->B->C) fully inside one Torah
chains = []
for r, es in by_torah.items():
    out = collections.defaultdict(list)
    for s, t, e in es:
        out[s].append(t)
    # DFS for simple paths up to length 4
    def dfs(node, path):
        if len(path) >= 3:
            chains.append((r, list(path)))
        if len(path) >= 4:
            return
        for nxt in out.get(node, []):
            if nxt not in path:
                dfs(nxt, path + [nxt])
    for start in list(out.keys()):
        dfs(start, [start])

# rank Torahs by richest causal structure
torah_rank = collections.Counter()
for r, es in by_torah.items():
    torah_rank[r] = len(es)

print("=== eitza edges per Torah (top 12) ===")
for r, n in torah_rank.most_common(12):
    concepts = len({x for s, t, e in by_torah[r] for x in (s, t)})
    print(f"  LM {r:8s}  {n} causal edges, {concepts} concepts")

print(f"\n=== {len(chains)} same-Torah A->B->C(+) chains found ===")
seen_r = set()
for r, path in sorted(chains, key=lambda c: -len(c[1])):
    if r in seen_r:
        continue
    seen_r.add(r)
    labels = " → ".join((byId[p]["he"] or p) for p in path)
    glosses = " / ".join((byId[p]["gloss"] or "")[:32] for p in path)
    print(f"  LM {r}: {labels}")
    print(f"        {glosses}")
    if len(seen_r) >= 10:
        break
