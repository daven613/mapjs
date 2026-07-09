#!/usr/bin/env python3
"""Bundle the compiled graph into one compact JSON the explorer loads (self-contained, offline).

nodes: id, he (canonical Hebrew), gloss, kind, deg (degree)
edges: s, t, ty (bechina|eitza|equation), w (weight), p (one sample proof, trimmed),
       pol (builds|harms|neutral), via (presence|absence), ref (torah refs)

Proof/ref lookups span both evidence layers: legacy_human.jsonl and ai_compiled.jsonl
(the latter written by compile_graph.py from the merged ai_extracted chunks).
"""
import json, collections
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
G = MAPJS / "ontology/graph"
nodes = json.loads((G / "nodes.json").read_text())
edges = json.loads((G / "edges.json").read_text())
occ = {}
for src in ("legacy_human.jsonl", "ai_compiled.jsonl"):
    p = MAPJS / "ontology/occurrences" / src
    if p.exists():
        for l in p.open():
            o = json.loads(l)
            occ[o["id"]] = o

deg = collections.Counter()
for e in edges:
    deg[e["source"]] += 1
    deg[e["target"]] += 1

out_nodes = []
for n in nodes:
    out_nodes.append({"id": n["id"], "he": n.get("canonical_he") or n.get("text_he") or "",
                      "gloss": n.get("gloss_en"), "kind": n.get("kind", "concept"),
                      "deg": deg.get(n["id"], 0)})

def ref_of(o):
    a = o.get("anchor", {})
    b = {"lm1": "I", "lm2": "II"}.get(a.get("book"), a.get("book"))
    t = a.get("torah")
    return f"{b}:{t}" if t is not None else None

node_refs = collections.defaultdict(set)
out_edges = []
for e in edges:
    proof = ""
    refs = set()
    for oid in e.get("proofs", []):
        o = occ.get(oid)
        if not o:
            continue
        if not proof:
            proof = (o.get("proof") or "")[:240]
        r = ref_of(o)
        if r:
            refs.add(r)
            node_refs[e["source"]].add(r)
            node_refs[e["target"]].add(r)
    out_edges.append({"s": e["source"], "t": e["target"], "ty": e["type"],
                      "w": e["weight"], "p": proof, "ref": sorted(refs),
                      "pol": e.get("polarity", "neutral"), "via": e.get("via", "presence")})

def refsort(r):
    b, t = r.split(":"); return (0 if b == "I" else 1, int(t))
for n in out_nodes:
    n["refs"] = sorted(node_refs.get(n["id"], []), key=refsort)

all_torahs = sorted({r for rs in node_refs.values() for r in rs}, key=refsort)
bundle = {"nodes": out_nodes, "edges": out_edges, "torahs": all_torahs,
          "stats": {"nodes": len(out_nodes), "edges": len(out_edges)}}
(G / "explorer_data.json").write_text(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")))
print(f"bundled {len(out_nodes)} nodes, {len(out_edges)} edges -> {(G/'explorer_data.json').stat().st_size//1024} KB")
