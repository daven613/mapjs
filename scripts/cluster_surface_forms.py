#!/usr/bin/env python3
"""Phase 1 step 1 (docs/CANONICALIZATION.md): mechanical candidate clustering.

Groups the surface forms from the occurrence layer into CANDIDATE clusters for AI+human
adjudication. This script merges nothing — it only proposes groupings with the mechanical
signal that linked them, so the adjudicator (and Shmuel) can judge each with context.

Signals used (candidate links only):
  identical     — same string after niqqud/punctuation normalization
  he-prefix     — differ only by leading ה (definite article) — NEVER auto-merged (archetype risk)
  clitic        — differ only by leading ו/ש/ב/ל/כ/מ clitics
  plural        — differ only by ים/ות suffix
  token-overlap — multi-word forms sharing most tokens

Forms that are whole clauses (long, many tokens) are routed to a separate `statements` list —
they are not concept names; the AI pass must extract the underlying concept instead.

Output: ontology/registry/clusters_candidates.json
"""
import json, re, unicodedata
from pathlib import Path
from collections import defaultdict

MAPJS = Path(__file__).resolve().parent.parent
STRIP = re.compile(r"[֑-ׇ]")
PUNCT = re.compile(r"[\"'״׳׳״.,:;!?()\[\]{}*\-–—]")
SPACES = re.compile(r"\s+")
CLITICS = "ושבלכמ"


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = STRIP.sub("", s)
    s = PUNCT.sub(" ", s)
    return SPACES.sub(" ", s).strip()


def strip_he(s: str) -> str:
    toks = [t[1:] if len(t) > 2 and t[0] == "ה" else t for t in s.split()]
    return " ".join(toks)


def strip_clitic(s: str) -> str:
    t = s.split()
    if t and len(t[0]) > 2 and t[0][0] in CLITICS:
        t[0] = t[0][1:]
    return " ".join(t)


def strip_plural(s: str) -> str:
    toks = []
    for t in s.split():
        if len(t) > 4 and (t.endswith("ים") or t.endswith("ות")):
            t = t[:-2]
        toks.append(t)
    return " ".join(toks)


def main():
    occs = [json.loads(l) for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()]

    # surface form -> usage info
    forms = defaultdict(lambda: {"count": 0, "occ_ids": [], "torahs": set(), "proofs": []})
    for o in occs:
        for side in ("source", "target"):
            f = o[f"{side}_surface"]
            if not f:
                continue
            e = forms[f]
            e["count"] += 1
            e["occ_ids"].append(o["id"])
            a = o.get("anchor") or {}
            if a.get("torah") is not None:
                e["torahs"].add(f"{a['book']}:{a['torah']}")
            if len(e["proofs"]) < 3 and o.get("proof"):
                e["proofs"].append(o["proof"][:220])

    # split off clause-like forms
    statements, concepts = [], {}
    for f, e in forms.items():
        n = norm(f)
        if len(n) > 45 or len(n.split()) > 7:
            statements.append(f)
        else:
            concepts[f] = n

    # union-find over candidate links
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    def union(x, y):
        parent[find(y)] = find(x)

    links = defaultdict(set)   # (a,b) -> {signals}
    def link(a, b, sig):
        if a != b:
            key = tuple(sorted((a, b)))
            links[key].add(sig)
            union(a, b)

    # index by each transform; forms sharing a transform key are candidates
    for sig, fn in (("identical", lambda n: n),
                    ("he-prefix", strip_he),
                    ("clitic", strip_clitic),
                    ("plural", strip_plural),
                    ("he+clitic+plural", lambda n: strip_plural(strip_he(strip_clitic(n))))):
        idx = defaultdict(list)
        for f, n in concepts.items():
            k = fn(n)
            if k:
                idx[k].append(f)
        for group in idx.values():
            for other in group[1:]:
                link(group[0], other, sig)

    # token-overlap for multi-word forms (blocking by shared token)
    tok_idx = defaultdict(list)
    multi = {f: set(n.split()) for f, n in concepts.items() if len(n.split()) >= 2}
    for f, toks in multi.items():
        for t in toks:
            if len(t) > 2:
                tok_idx[t].append(f)
    for bucket in tok_idx.values():
        if len(bucket) > 40:      # ultra-common token (e.g. בחינת) — not a useful signal
            continue
        for i, a in enumerate(bucket):
            for b in bucket[i + 1:]:
                ta, tb = multi[a], multi[b]
                j = len(ta & tb) / len(ta | tb)
                if j >= 0.6:
                    link(a, b, "token-overlap")

    # build clusters
    clusters = defaultdict(list)
    for f in concepts:
        clusters[find(f)].append(f)
    out_clusters = []
    for members in clusters.values():
        members.sort(key=lambda f: -forms[f]["count"])
        pair_sigs = sorted({s for a in members for b in members
                            for s in links.get(tuple(sorted((a, b))), ())})
        out_clusters.append({
            "id": f"cl:{len(out_clusters):04d}",
            "size": len(members),
            "signals": pair_sigs,
            "members": [{
                "form": f, "count": forms[f]["count"],
                "torahs": sorted(forms[f]["torahs"]),
                "proofs": forms[f]["proofs"],
            } for f in members],
        })
    out_clusters.sort(key=lambda c: -c["size"])

    dest = MAPJS / "ontology/registry/clusters_candidates.json"
    dest.write_text(json.dumps({
        "generated": "cluster_surface_forms.py",
        "n_forms_total": len(forms),
        "n_concept_forms": len(concepts),
        "n_statement_forms": len(statements),
        "clusters": out_clusters,
        "statements": sorted(statements, key=lambda f: -forms[f]["count"]),
    }, ensure_ascii=False, indent=1))

    sizes = defaultdict(int)
    for c in out_clusters:
        sizes[1 if c["size"] == 1 else (2 if c["size"] == 2 else ("3-5" if c["size"] <= 5 else "6+"))] += 1
    print(f"forms: {len(forms)} total = {len(concepts)} concept-like + {len(statements)} statements")
    print(f"clusters: {len(out_clusters)}  sizes: {dict(sizes)}")
    print(f"multi-member clusters needing adjudication: {sum(1 for c in out_clusters if c['size'] > 1)}")


if __name__ == "__main__":
    main()
