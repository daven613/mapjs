#!/usr/bin/env python3
"""Bundle the compiled graph into one compact JSON the explorer loads (self-contained, offline).

nodes: id, he (canonical Hebrew), gloss, kind, deg (degree)
edges: s, t, ty (bechina|eitza|equation), w (weight), p (one sample proof, trimmed)
"""
import json, collections
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
G = MAPJS / "ontology/graph"
nodes = json.loads((G / "nodes.json").read_text())
edges = json.loads((G / "edges.json").read_text())
occ = {json.loads(l)["id"]: json.loads(l)
       for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()}

deg = collections.Counter()
for e in edges:
    deg[e["source"]] += 1
    deg[e["target"]] += 1

out_nodes = []
for n in nodes:
    out_nodes.append({"id": n["id"], "he": n.get("canonical_he") or n.get("text_he") or "",
                      "gloss": n.get("gloss_en"), "kind": n.get("kind", "concept"),
                      "deg": deg.get(n["id"], 0)})

out_edges = []
for e in edges:
    proof = ""
    for oid in e.get("proofs", [])[:1]:
        o = occ.get(oid)
        if o:
            proof = (o.get("proof") or "")[:220]
    out_edges.append({"s": e["source"], "t": e["target"], "ty": e["type"],
                      "w": e["weight"], "p": proof})

bundle = {"nodes": out_nodes, "edges": out_edges,
          "stats": {"nodes": len(out_nodes), "edges": len(out_edges)}}
(G / "explorer_data.json").write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")))
print(f"bundled {len(out_nodes)} nodes, {len(out_edges)} edges -> {(G/'explorer_data.json').stat().st_size//1024} KB")
