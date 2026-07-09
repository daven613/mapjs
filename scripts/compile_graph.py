#!/usr/bin/env python3
"""Compile the graph: nodes = canonical concepts, edges = typed weighted relations.

Two evidence layers (see specs/MERGE_POLICY.md for the v2 merge policy):

1. LEGACY HUMAN — legacy_human.jsonl occurrences, resolved per-occurrence via the
   occ_ids each concept owns (homograph splits respected: the שָׂדַי 'field' occurrence
   lands on its own node, not on שַׁדַּי the Divine Name).
2. AI EXTRACTED (v2) — every chunk in ontology/occurrences/ai_extracted/, resolved by a
   deterministic lexical ladder (exact → article → unambiguous plene skeleton), with
   polarity/via carried as first-class edge attributes. Surfaces that resolve to no
   concept become statement nodes when the edge's other side resolved; edges touching
   no concept at all are skipped (counted). No gloss-similarity, no inferred edges.

Edges aggregate by (source, target, type, polarity, via); weight = attestations; every
edge keeps its proof occurrence ids. AI proofs are written to ai_compiled.jsonl so
downstream consumers (build_explorer_data.py) can look them up like legacy occurrences.

Output:
  ontology/graph/nodes.json
  ontology/graph/edges.json
  ontology/graph/stats.json
  ontology/occurrences/ai_compiled.jsonl
"""
import json, re, collections, unicodedata
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
REG = MAPJS / "ontology/registry"
GRAPH = MAPJS / "ontology/graph"
OCC = MAPJS / "ontology/occurrences"
nf = lambda s: re.sub(r"\s+", " ", (s or "").strip())

VALID_POLARITY = {"builds", "harms", "neutral"}
VALID_VIA = {"presence", "absence"}

# ---- normalization ladder (MERGE_POLICY.md §Endpoint resolution) ----
MAQAF = "־"
NIQQUD = re.compile(r"[֑-ֽֿ-ׇ]")   # niqqud + te'amim, NOT maqaf

def norm(s):
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace(MAQAF, " ")
    s = NIQQUD.sub("", s)
    s = s.replace("״", '"').replace("׳", "'")
    s = re.sub(r"[^א-ת\"' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

def skel(s):
    return re.sub(r"[יו]", "", norm(s).replace('"', "").replace("'", ""))

def strip_article(s):
    return " ".join(w[1:] if w.startswith("ה") and len(w) > 2 else w for w in s.split())


concepts = json.loads((REG / "concepts_final.json").read_text())
occ_by_id = {json.loads(l)["id"]: json.loads(l)
             for l in (OCC / "legacy_human.jsonl").open()}
statement_forms = set(nf(s) for s in json.loads((REG / "clusters_candidates.json").read_text())["statements"])

# precise legacy resolver: (surface_form, occ_id) -> concept id, via the occ_ids each concept owns
resolve_legacy = {}
for c in concepts:
    fset = set(c["forms"])
    for oid in c["occ_ids"]:
        o = occ_by_id.get(oid)
        if not o:
            continue
        for side in ("source", "target"):
            if nf(o.get(f"{side}_surface", "")) in fset:
                resolve_legacy[(nf(o[f"{side}_surface"]), oid)] = c["id"]

# lexical ladder indexes for the AI layer — every rung is unambiguous-only:
# a key owned by >1 concept resolves nothing (homograph safety).
def build_index(keyfn):
    idx, ambiguous = {}, set()
    for c in concepts:
        for f in c["forms"] + [c["canonical_he"]]:
            k = keyfn(f)
            if not k:
                continue
            if k in idx and idx[k] != c["id"]:
                ambiguous.add(k)
            else:
                idx[k] = c["id"]
    for k in ambiguous:
        del idx[k]
    return idx

exact_idx = build_index(norm)
skel_idx = build_index(skel)

def resolve_surface(surface):
    """-> (concept_id or None, ladder_rung)"""
    n = norm(surface)
    if not n:
        return None, "empty"
    if n in exact_idx:
        return exact_idx[n], "exact"
    a = strip_article(n)
    if a in exact_idx:
        return exact_idx[a], "article"
    k = skel(surface)
    if k in skel_idx:
        return skel_idx[k], "skel"
    ka = re.sub(r"[יו]", "", a.replace('"', "").replace("'", ""))
    if ka in skel_idx:
        return skel_idx[ka], "skel_article"
    return None, "unresolved"

# nodes
nodes = []
for c in concepts:
    nodes.append({"id": c["id"], "canonical_he": c["canonical_he"], "gloss_en": c["gloss_en"],
                  "forms": c["forms"], "n_occ": len(c["occ_ids"]),
                  "provenance": c.get("provenance", {})})
node_ids = {n["id"] for n in nodes}

# statement nodes (targets that are propositions, not concepts) — legacy s: pool
stmt_nodes = {}
def stmt_id(form):
    if form not in stmt_nodes:
        stmt_nodes[form] = f"s:{len(stmt_nodes)+1:04d}"
    return stmt_nodes[form]

# AI phrase-statement nodes — p: pool, deduped by normalized surface
phrase_nodes = {}   # norm_form -> {"id", "text_he"}
def phrase_id(surface):
    key = norm(surface)
    if key not in phrase_nodes:
        phrase_nodes[key] = {"id": f"p:{len(phrase_nodes)+1:04d}", "text_he": nf(surface)}
    return phrase_nodes[key]["id"]

# edges keyed by (source, target, type, polarity, via)
edges = collections.defaultdict(lambda: {"weight": 0, "proofs": []})

def add_edge(src, tgt, ty, pol, via, proof_id):
    key = (src, tgt, ty, pol, via)
    edges[key]["weight"] += 1
    edges[key]["proofs"].append(proof_id)

# ---- layer 1: legacy human occurrences ----
unresolved_legacy = 0
for oid, o in occ_by_id.items():
    sform, tform = nf(o.get("source_surface", "")), nf(o.get("target_surface", ""))
    src = resolve_legacy.get((sform, oid))
    if not src and sform in statement_forms:
        src = stmt_id(sform)
    tgt = resolve_legacy.get((tform, oid))
    if not tgt and tform in statement_forms:
        tgt = stmt_id(tform)
    if not src or not tgt:
        unresolved_legacy += 1
        continue
    ty = o["type"]
    pol, via = ("builds", "presence") if ty == "eitza" else ("neutral", "presence")
    add_edge(src, tgt, ty, pol, via, oid)

# ---- layer 2: AI-extracted chunks (schema 1 + 2) ----
ai_stats = collections.Counter()
ladder = collections.Counter()
ai_occ_records = []
chunks_zero_contrib = 0
chunk_files = sorted((OCC / "ai_extracted").glob("*.json"))
for fn in chunk_files:
    d = json.loads(fn.read_text())
    book, torah = d.get("book"), d.get("torah")
    contributed = 0
    if not d.get("edges"):
        ai_stats["chunks_empty_extraction"] += 1
    for i, e in enumerate(d.get("edges", [])):
        ty = e.get("type")
        if ty not in ("bechina", "eitza", "equation"):
            ai_stats["bad_type"] += 1
            continue
        pol = e.get("polarity") or ("builds" if ty == "eitza" else "neutral")
        via = e.get("via") or "presence"
        if pol not in VALID_POLARITY or via not in VALID_VIA:
            ai_stats["bad_polarity_via"] += 1
            continue
        if ty != "eitza" and (pol, via) != ("neutral", "presence"):
            ai_stats["coerced_non_eitza"] += 1
            pol, via = "neutral", "presence"
        ai_stats["candidate"] += 1

        rs, hs = resolve_surface(e.get("source_he", ""))
        rt, ht = resolve_surface(e.get("target_he", ""))
        ladder[f"src_{hs}"] += 1
        ladder[f"tgt_{ht}"] += 1

        if not rs and not rt:
            ai_stats["skipped_islands"] += 1
            continue
        # unresolved side -> legacy statement form if it matches one, else p: phrase node
        if not rs:
            sform = nf(e.get("source_he", ""))
            rs = stmt_id(sform) if sform in statement_forms else phrase_id(sform)
            ai_stats["phrase_endpoint"] += 1
        if not rt:
            tform = nf(e.get("target_he", ""))
            rt = stmt_id(tform) if tform in statement_forms else phrase_id(tform)
            ai_stats["phrase_endpoint"] += 1
        if rs == rt:
            ai_stats["self_loops_dropped"] += 1
            continue

        oid = f"occ:ai:{fn.stem}:{i}"
        ai_occ_records.append({
            "id": oid, "type": ty, "polarity": pol, "via": via,
            "source_surface": nf(e.get("source_he", "")), "target_surface": nf(e.get("target_he", "")),
            "proof": nf(e.get("proof", "")), "explicitness": e.get("explicitness", "explicit"),
            "extractor": d.get("extractor", "ai"), "schema": d.get("schema", 1),
            "anchor": {"book": book, "torah": torah},
        })
        add_edge(rs, rt, ty, pol, via, oid)
        ai_stats["merged"] += 1
        contributed += 1
    if contributed == 0:
        chunks_zero_contrib += 1

edge_list = [{"source": s, "target": t, "type": ty, "polarity": pol, "via": via,
              "weight": e["weight"], "proofs": e["proofs"]}
             for (s, t, ty, pol, via), e in edges.items()]

# append statement + phrase nodes to node list
for form, sid in stmt_nodes.items():
    nodes.append({"id": sid, "kind": "statement", "text_he": form,
                  "gloss_en": None, "forms": [form], "n_occ": 0})
for rec in phrase_nodes.values():
    nodes.append({"id": rec["id"], "kind": "statement", "text_he": rec["text_he"],
                  "gloss_en": None, "forms": [rec["text_he"]], "n_occ": 0, "src": "ai"})

GRAPH.mkdir(parents=True, exist_ok=True)
(GRAPH / "nodes.json").write_text(json.dumps(nodes, ensure_ascii=False, indent=1))
(GRAPH / "edges.json").write_text(json.dumps(edge_list, ensure_ascii=False, indent=1))
with (OCC / "ai_compiled.jsonl").open("w") as f:
    for rec in ai_occ_records:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

by_type = collections.Counter(e["type"] for e in edge_list)
by_polarity = collections.Counter(e["polarity"] for e in edge_list)
by_via = collections.Counter(e["via"] for e in edge_list)
by_pol_via_w = collections.Counter()
for e in edge_list:
    by_pol_via_w[f"{e['polarity']}/{e['via']}"] += e["weight"]
stats = {"concept_nodes": len(node_ids), "statement_nodes": len(stmt_nodes),
         "phrase_nodes": len(phrase_nodes),
         "nodes_total": len(nodes),
         "edges": len(edge_list), "edges_by_type": dict(by_type),
         "edges_by_polarity": dict(by_polarity), "edges_by_via": dict(by_via),
         "attestations_by_polarity_via": dict(by_pol_via_w),
         "legacy_occurrences": len(occ_by_id), "legacy_unresolved": unresolved_legacy,
         "ai_chunks": len(chunk_files), "ai_chunks_zero_contribution": chunks_zero_contrib,
         "ai": dict(ai_stats), "ai_resolution_ladder": dict(ladder),
         "top_hubs": [{"id": nid, "degree": deg} for nid, deg in
                      collections.Counter([e["source"] for e in edge_list] +
                                          [e["target"] for e in edge_list]).most_common(15)]}
(GRAPH / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1))

print(json.dumps(stats, ensure_ascii=False, indent=1))
