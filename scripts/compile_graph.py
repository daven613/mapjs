#!/usr/bin/env python3
"""Compile the graph: nodes = canonical concepts, edges = typed weighted relations.

Reads concepts_final.json (post-enrichment). Each legacy occurrence is an edge between the
concept on its source side and the concept (or statement) on its target side. Edges are
aggregated by (source, target, type); weight = number of occurrences; every edge keeps its
proof occurrence ids for provenance.

Homograph splits are respected: a form whose occurrences were partitioned across concepts is
resolved per-occurrence (via the occ_ids each concept actually owns), so the שָׂדַי 'field'
occurrence lands on its own node, not on שַׁדַּי the Divine Name.

Output:
  ontology/graph/nodes.json
  ontology/graph/edges.json
  ontology/graph/stats.json
"""
import json, re, collections
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
REG = MAPJS / "ontology/registry"
GRAPH = MAPJS / "ontology/graph"
nf = lambda s: re.sub(r"\s+", " ", (s or "").strip())

concepts = json.loads((REG / "concepts_final.json").read_text())
occ_by_id = {json.loads(l)["id"]: json.loads(l)
             for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()}
statement_forms = set(nf(s) for s in json.loads((REG / "clusters_candidates.json").read_text())["statements"])

# precise resolver: (surface_form, occ_id) -> concept id, using the occ_ids each concept owns
resolve = {}
for c in concepts:
    fset = set(c["forms"])
    for oid in c["occ_ids"]:
        o = occ_by_id.get(oid)
        if not o:
            continue
        for side in ("source", "target"):
            if nf(o.get(f"{side}_surface", "")) in fset:
                resolve[(nf(o[f"{side}_surface"]), oid)] = c["id"]

# nodes
nodes = []
for c in concepts:
    nodes.append({"id": c["id"], "canonical_he": c["canonical_he"], "gloss_en": c["gloss_en"],
                  "forms": c["forms"], "n_occ": len(c["occ_ids"]),
                  "provenance": c.get("provenance", {})})
node_ids = {n["id"] for n in nodes}

# statement nodes (targets that are propositions, not concepts)
stmt_nodes = {}
def stmt_id(form):
    if form not in stmt_nodes:
        stmt_nodes[form] = f"s:{len(stmt_nodes)+1:04d}"
    return stmt_nodes[form]

# edges
edges = collections.defaultdict(lambda: {"weight": 0, "proofs": []})
unresolved = 0
for oid, o in occ_by_id.items():
    sform, tform = nf(o.get("source_surface", "")), nf(o.get("target_surface", ""))
    src = resolve.get((sform, oid))
    if not src and sform in statement_forms:
        src = stmt_id(sform)
    tgt = resolve.get((tform, oid))
    if not tgt and tform in statement_forms:
        tgt = stmt_id(tform)
    if not src or not tgt:
        unresolved += 1
        continue
    key = (src, tgt, o["type"])
    edges[key]["weight"] += 1
    edges[key]["proofs"].append(oid)

edge_list = [{"source": s, "target": t, "type": ty, "weight": e["weight"], "proofs": e["proofs"]}
             for (s, t, ty), e in edges.items()]

# append statement nodes to node list
for form, sid in stmt_nodes.items():
    nodes.append({"id": sid, "kind": "statement", "text_he": form,
                  "gloss_en": None, "forms": [form], "n_occ": 0})

GRAPH.mkdir(parents=True, exist_ok=True)
(GRAPH / "nodes.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=1))
(GRAPH / "edges.json").write_text(json.dumps(edge_list, ensure_ascii=False, indent=1))

by_type = collections.Counter(e["type"] for e in edge_list)
stats = {"concept_nodes": len(node_ids), "statement_nodes": len(stmt_nodes),
         "edges": len(edge_list), "edges_by_type": dict(by_type),
         "total_occurrences": len(occ_by_id), "unresolved_occurrences": unresolved,
         "top_hubs": [{"id": nid, "degree": deg} for nid, deg in
                      collections.Counter([e["source"] for e in edge_list] +
                                          [e["target"] for e in edge_list]).most_common(15)]}
(GRAPH / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))

print(json.dumps(stats, ensure_ascii=False, indent=1))
