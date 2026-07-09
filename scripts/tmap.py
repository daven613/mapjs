#!/usr/bin/env python3
"""tmap — CLI for the Torah Map (Likutey Moharan) concept graph.

Stdlib-only Python 3 port of the algorithms in ontology/graph/explorer.html
(scoreOne/matchList/wireAc search, hopCost/causalPath/aspectPath/aspectDist,
sharedTerms/glossSim/parallels, project). See specs/api_v1.md for the spec
this implements.
"""
from __future__ import annotations

import argparse
import datetime
import heapq
import itertools
import json
import math
import re
import sys
import time
from pathlib import Path

DEFAULT_DATA_PATH = Path(__file__).resolve().parent.parent / "ontology/graph/explorer_data.json"
USER_PACKETS_PATH = Path(__file__).resolve().parent.parent / "ontology/packets/user_packets.jsonl"

TOKEN_RE = re.compile(r"[a-z]{3,}|[א-ת]{2,}")

# v1.4: pattern notation shown in every search command's --help (spec ~262-264).
PATTERN_HELP = (
    "PATTERN NOTATION (v1.4):\n"
    "  (A) -[bechina*0..N]- (X) -[eitza+]-> (Y) -[bechina*0..N]- (B)\n"
    "  i.e. zero-or-more undirected bechina/equation aspect-hops, then one-or-\n"
    "  more forward eitza cause-hops, then zero-or-more more bechina/equation hops."
)
WHY_PATTERN_HELP = PATTERN_HELP + (
    "\n--pre N / --post N bound the bechina-hop run before the first eitza hop /\n"
    "  after the last eitza hop (default: unlimited)."
)


# --------------------------------------------------------------------------
# Graph: load + index (port of the `fetch(...).then(...)` block + buildTokenIndex,
# explorer.html ~lines 132-160).
# --------------------------------------------------------------------------
class Graph:
    def __init__(self, nodes, edges, torahs=None):
        self.nodes = nodes
        self.edges = edges
        self.torahs = torahs or []
        self.by_id = {}
        self.adj = {}
        self.concepts_in = {}
        self.tokx = {}
        self.ctxx = {}
        self.idf = {}
        self._build()

    def _build(self):
        for n in self.nodes:
            self.by_id[n["id"]] = n
            self.adj[n["id"]] = {"all": [], "bechina": [], "eitza_out": [], "eitza_in": []}

        for e in self.edges:
            s, t = e.get("s"), e.get("t")
            if s not in self.adj or t not in self.adj:
                continue
            self.adj[s]["all"].append({"o": t, "ty": e.get("ty"), "dir": "out", "e": e})
            self.adj[t]["all"].append({"o": s, "ty": e.get("ty"), "dir": "in", "e": e})
            if e.get("ty") == "bechina":
                self.adj[s]["bechina"].append(t)
                self.adj[t]["bechina"].append(s)
            elif e.get("ty") == "eitza":
                self.adj[s]["eitza_out"].append(t)
                self.adj[t]["eitza_in"].append(s)

        # ---- token index (buildTokenIndex, explorer.html ~148-160) ----
        proof_by = {}
        for e in self.edges:
            p = e.get("p")
            if p:
                proof_by.setdefault(e.get("s"), []).append(p)
                proof_by.setdefault(e.get("t"), []).append(p)

        df = {}
        for n in self.nodes:
            nid = n["id"]
            # order-preserving "sets" (dict-as-ordered-set), to mirror JS Set insertion-order
            # iteration exactly — this matters downstream wherever ties are broken by first-seen
            # order (e.g. shared_terms sort stability).
            st = dict.fromkeys(tokens(n.get("gloss")) + tokens(n.get("he")))
            ct = {}
            for p in proof_by.get(nid, []):
                for w in tokens(p):
                    if w not in st:
                        ct[w] = None
            self.tokx[nid] = st
            self.ctxx[nid] = ct
            for w in st:
                df[w] = df.get(w, 0) + 1
            for w in ct:
                df[w] = df.get(w, 0) + 1
            for r in n.get("refs") or []:
                self.concepts_in.setdefault(r, []).append(nid)

        N = len(self.nodes)
        for w, c in df.items():
            self.idf[w] = math.log(N / c) if c else 0.0


def load_data(path=None) -> Graph:
    p = Path(path) if path else DEFAULT_DATA_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    return Graph(data.get("nodes") or [], data.get("edges") or [], data.get("torahs") or [])


# --------------------------------------------------------------------------
# tokens / score_one / match  (explorer.html ~146, ~163, ~169)
# --------------------------------------------------------------------------
def tokens(s):
    return TOKEN_RE.findall((s or "").lower())


def score_one(g: Graph, q: dict, cid: str) -> float:
    st = g.tokx.get(cid) or set()
    ct = g.ctxx.get(cid) or set()
    s = 0.0
    for w, cnt in q.items():
        wt = (g.idf.get(w, 0.5)) * (1 + math.log(cnt))
        if w in st:
            s += wt
        elif w in ct:
            s += 0.35 * wt
    deg = (g.by_id.get(cid) or {}).get("deg") or 0
    return s / (1 + math.log(1 + deg) * 0.15)


def match(g: Graph, text: str, topn: int, pool=None):
    qt = tokens(text)
    if not qt:
        return []
    q = {}
    for w in qt:
        q[w] = q.get(w, 0) + 1
    ids = pool if pool is not None else [n["id"] for n in g.nodes if n.get("kind") != "statement"]
    scored = [(cid, score_one(g, q, cid)) for cid in ids]
    scored = [x for x in scored if x[1] > 0]
    scored.sort(key=lambda x: -x[1])
    return scored[:topn]


# --------------------------------------------------------------------------
# search — autocomplete ranking (wireAc, explorer.html ~245-258)
# --------------------------------------------------------------------------
def search(g: Graph, query: str, topn: int = 10):
    q = (query or "").strip().lower()
    if not q:
        return []
    wb = re.compile(r"\b" + re.escape(q))
    out = []
    for n in g.nodes:
        if n.get("kind") == "statement":
            continue
        he = (n.get("he") or "").lower()
        gl = (n.get("gloss") or "").lower()
        if he == q:
            s = 100
        elif he.startswith(q):
            s = 82
        elif q in he:
            s = 64
        elif gl.startswith(q):
            s = 54
        elif wb.search(gl):
            s = 42
        elif q in gl:
            s = 22
        else:
            continue
        s += min(15, (n.get("deg") or 0) / 40)
        out.append((n, s))
    out.sort(key=lambda x: -x[1])
    return out[:topn]


# --------------------------------------------------------------------------
# hop_cost / causal_path  (explorer.html ~315-341)
# --------------------------------------------------------------------------
def hop_cost(e, home):
    ref = e.get("ref") or []
    if home is not None and home in ref:
        return 0.12
    return 1.6 if e.get("ty") == "eitza" else 2.0


def causal_path(g: Graph, a, b, home, strict, exclude_edges=None, mode="strict",
                 user_packet_adj=None, pre_bound=None, post_bound=None):
    """Cheapest a->b path with >=1 forward causal (eitza) hop.
    Returns (cost, node_ids, hops) or (None, None, None).

    `exclude_edges` (v1.3, additive): optional set of `id(edge_dict)` values to
    skip entirely — used by `k_causal_chains` (the `why -k` alternatives rerun)
    to find the next-best chain over a distinct hop-edge set. Unused (None) by
    every pre-existing caller, so behavior is unchanged when omitted.

    v1.4 additions (specs/api_v1.md ~250-264) — all optional / default-off, so
    every pre-v1.4 caller (mode="strict", no bounds, no packets) is
    byte-identical to before (AP4):

    `mode`:
      - "strict" (default): unchanged hop_cost(e,home) + 0.15 reframe surcharge.
      - "loose": bechina/equation ("reframe") hops cost 0.15 if their edge's
        ref set shares a torah with the immediately-preceding hop AND that
        preceding hop was itself reframe/user-packet-typed, else 0.9; eitza
        ("cause") hops cost a flat 1.0. This approximates packet-contraction
        (near-free movement within one torah's identification-chain) while
        still emitting one printable hop per edge.
      - "loose_all": everything "loose" does, PLUS traversal may use synthetic
        user-packet co-membership edges (`user_packet_adj`, built by
        `build_user_packet_adjacency`) as an extra bechina-like move, flat
        cost 0.3, kind "user-packet" — always carries by/note downstream, an
        evidence class kept visibly distinct from attested graph data.

    Documented simplification (spec ~253 invites one): "shares a torah with an
    ADJACENT bechina hop" is read as backward-looking only — "the hop
    immediately preceding this one in the walk" — since a forward Dijkstra
    cannot know the future. The state key gains `last_fp`: the frozenset of
    refs of the most recent reframe/user-packet hop, reset to None the instant
    a cause (eitza) hop is taken. This keeps the state space close to the
    strict (node, caused) graph's size (last_fp is almost always 1-2 refs)
    while staying exact for the backward-looking rule actually implemented.

    `pre_bound`/`post_bound` (why --pre/--post): max bechina/reframe hops
    before the first eitza hop / after the last one. `pre` is enforced by
    pruning — once violated with caused==0 it can never be cured, so the
    transition is simply refused — via a `lead` counter frozen the instant
    caused flips to 1. `post` is only checked at arrival — a violation can
    still be cured later by another eitza hop, which resets the `trail`
    counter to 0. Both counters are added to the state key ONLY when a bound
    is actually given, so the unlimited default keeps the pre-v1.4 state size.
    """
    if a == b:
        return 0, [a], []

    loose = mode in ("loose", "loose_all")
    bounded = pre_bound is not None or post_bound is not None
    extra0 = (0, 0) if bounded else ()

    counter = itertools.count()
    start_key = (a, 0, None) + extra0
    dist = {start_key: 0}
    prev = {}
    h = [(0, next(counter), a, 0, None) + extra0]
    guard = 0

    while h and guard < 40000:
        guard += 1
        item = heapq.heappop(h)
        c = item[0]
        node, caused, fp = item[2], item[3], item[4]
        if bounded:
            lead, trail = item[5], item[6]
            key = (node, caused, fp, lead, trail)
        else:
            lead = trail = 0
            key = (node, caused, fp)
        if c > dist.get(key, 1e9):
            continue

        if node == b and caused and (post_bound is None or trail <= post_bound):
            hops = []
            k = key
            while k in prev:
                p = prev[k]
                hops.insert(0, {"from": p["from"], "to": p["node"], "e": p["e"],
                                 "kind": p["kind"], "hc": p["hc"]})
                k = p["pk"]
            return c, [a] + [hh["to"] for hh in hops], hops

        neighbors = g.adj.get(node, {}).get("all", [])
        if mode == "loose_all" and user_packet_adj:
            extra = user_packet_adj.get(node)
            if extra:
                neighbors = list(neighbors) + [
                    {"o": other, "ty": "user-packet", "dir": "out", "e": synth}
                    for other, synth in extra
                ]

        for x in neighbors:
            ety = x["ty"]
            if x["dir"] != "out" and ety == "eitza":
                continue  # eitza only forward (cause -> effect)
            if strict and ety != "user-packet" and strict not in (x["e"].get("ref") or []):
                continue
            if exclude_edges and id(x["e"]) in exclude_edges:
                continue

            if ety == "eitza":
                kind = "cause"
            elif ety == "user-packet":
                kind = "user-packet"
            else:
                kind = "reframe"
            nc = 1 if (caused or kind == "cause") else 0

            if not loose:
                hc = hop_cost(x["e"], home) + (0.15 if kind == "reframe" else 0)
                nfp = None
            elif kind == "cause":
                hc = 1.0
                nfp = None
            elif kind == "user-packet":
                hc = 0.3
                nfp = frozenset(x["e"].get("ref") or [])
            else:  # loose bechina/equation ("reframe")
                ref_set = frozenset(x["e"].get("ref") or [])
                hc = 0.15 if (fp is not None and fp & ref_set) else 0.9
                nfp = ref_set

            if bounded:
                if kind == "cause":
                    n_lead, n_trail = lead, 0
                else:
                    n_lead = lead if caused else lead + 1
                    n_trail = trail + 1 if caused else trail
                    if not caused and pre_bound is not None and n_lead > pre_bound:
                        continue  # permanent --pre violation: prune
                nk_extra = (n_lead, n_trail)
            else:
                nk_extra = ()

            nk = (x["o"], nc, nfp) + nk_extra
            if c + hc < dist.get(nk, 1e9):
                dist[nk] = c + hc
                prev[nk] = {"from": node, "pk": key, "node": x["o"], "e": x["e"],
                            "kind": kind, "hc": hc}
                heapq.heappush(h, (c + hc, next(counter), x["o"], nc, nfp) + nk_extra)

    return None, None, None


def k_causal_chains(g: Graph, a, b, k=1, mode="strict", user_packet_adj=None,
                     pre_bound=None, post_bound=None):
    """v1.3 `why -k`: top-k causal_path(a,b,None,None) chains, cost asc, distinct
    hop-sequences. k=1 is exactly causal_path's optimum. For k>1, uses the
    spec-sanctioned "edge-penalty rerun" approach: after each chain is found,
    exclude every edge it used and rerun causal_path over what remains — since
    each rerun's edge set is disjoint from every earlier chain's, hop-sequences
    are guaranteed distinct, and cost is guaranteed non-decreasing (excluding
    edges can only raise, never lower, the achievable minimum).
    `mode`/`user_packet_adj`/`pre_bound`/`post_bound` (v1.4, additive, all
    default to strict/off): threaded straight through to `causal_path`.
    Returns a list (len <= k) of {"cost", "nodes", "hops"} dicts."""
    chains = []
    exclude = set()
    while len(chains) < k:
        cost, nodes, hops = causal_path(g, a, b, None, None, exclude_edges=exclude,
                                         mode=mode, user_packet_adj=user_packet_adj,
                                         pre_bound=pre_bound, post_bound=post_bound)
        if cost is None:
            break
        chains.append({"cost": cost, "nodes": nodes, "hops": hops})
        if not hops:
            break  # a==b (no edges to exclude) -- would repeat forever otherwise
        for hh in hops:
            exclude.add(id(hh["e"]))
    return chains


# --------------------------------------------------------------------------
# aspect_dist / aspect_path  (explorer.html ~344-384)
# --------------------------------------------------------------------------
def aspect_dist(g: Graph, x):
    counter = itertools.count()
    dist = {x: 0}
    h = [(0, next(counter), x)]
    guard = 0
    while h and guard < 60000:
        guard += 1
        c, _, node = heapq.heappop(h)
        if c > dist.get(node, 1e9):
            continue
        for e in g.adj.get(node, {}).get("all", []):
            if e["ty"] != "bechina":
                continue
            nc = c + 1
            if nc < dist.get(e["o"], 1e9):
                dist[e["o"]] = nc
                heapq.heappush(h, (nc, next(counter), e["o"]))
    return dist


def aspect_path(g: Graph, a, b, home):
    if a == b:
        return []
    counter = itertools.count()
    dist = {a: 0}
    prev = {}
    h = [(0, next(counter), a)]
    guard = 0
    while h and guard < 30000:
        guard += 1
        c, _, node = heapq.heappop(h)
        if c > dist.get(node, 1e9):
            continue
        if node == b:
            hops = []
            k = b
            while k in prev:
                hops.insert(0, prev[k])
                k = prev[k]["from"]
            return hops
        for x in g.adj.get(node, {}).get("all", []):
            if x["ty"] != "bechina":
                continue
            w = 0.12 if (home is not None and home in (x["e"].get("ref") or [])) else 1.2
            nc = c + w
            if nc < dist.get(x["o"], 1e9):
                dist[x["o"]] = nc
                prev[x["o"]] = {"from": node, "to": x["o"], "e": x["e"]}
                heapq.heappush(h, (nc, next(counter), x["o"]))
    return None


# --------------------------------------------------------------------------
# shared_terms / gloss_sim / parallels  (explorer.html ~361-372)
# --------------------------------------------------------------------------
def shared_terms(g: Graph, x, a, topn=8):
    sx = g.tokx.get(x) or set()
    sa = g.tokx.get(a) or set()
    ov = [(w, g.idf.get(w, 0.5)) for w in sx if w in sa and len(w) > 1]
    ov.sort(key=lambda p: -p[1])
    return [w for w, _ in ov[:topn]]


def gloss_sim(g: Graph, x, a):
    n = g.by_id.get(x) or {}
    text = (n.get("gloss") or "") + " " + (n.get("he") or "")
    q = {}
    for w in tokens(text):
        q[w] = q.get(w, 0) + 1
    return score_one(g, q, a)


def parallels(g: Graph, x, pool, topn=6):
    scored = []
    bech = set(g.adj.get(x, {}).get("bechina", []))
    for a in pool:
        s = 0.0
        if a == x:
            s += 5
        if a in bech:
            s += 2
        s += 0.5 * gloss_sim(g, x, a)
        if s > 0:
            scored.append((a, s))
    scored.sort(key=lambda p: -p[1])
    return scored[:topn]


# --------------------------------------------------------------------------
# project  (explorer.html ~386-425, enriched per spec step 7 / runProject ~428-450)
# --------------------------------------------------------------------------
def _project_raw(g: Graph, concept_ids):
    dists = [aspect_dist(g, x) for x in concept_ids]
    cover = {}
    for idx, x in enumerate(concept_ids):
        seen = {}  # order-preserving set (mirrors JS Set insertion order — matters for cover tie-break)
        d = dists[idx]
        for a, dv in d.items():
            if dv <= 6:
                for r in (g.by_id.get(a) or {}).get("refs") or []:
                    seen[r] = None
        for r in seen:
            cover[r] = cover.get(r, 0) + 1

    min_cover = min(2, len(concept_ids))
    homes = [r for r in cover if cover[r] >= min_cover]
    homes.sort(key=lambda r: -cover[r])
    homes = homes[:24]

    home_locs = []  # one best-per-home optimum each (v1.2: source for -k alternatives)
    for home in homes:
        pool = g.concepts_in.get(home) or []
        if not pool:
            continue
        candk = []
        for idx, x in enumerate(concept_ids):
            d = dists[idx]
            # No parallels()/gloss_sim() fallback here on purpose: an anchor candidate must be
            # reached by a real bechina/equation edge (aspect_dist), never by text-similarity —
            # the map's own connections are only the ones the text attests, never invented from
            # a regex/vocabulary-overlap guess. A home with no real candidate for some picked
            # concept is simply not a valid projection target (candk[i] stays empty below, and
            # the whole home is skipped by the `any(not c for c in candk)` check).
            cand = [(a, 0 if a == x else 0.2 * d[a]) for a in pool if d.get(a, 99) <= 6]
            cand.sort(key=lambda p: p[1])
            candk.append(cand[:6])
        if any(not c for c in candk):
            continue

        loc = [None]

        def dfs(i, used, chain, links, pcosts, cost):
            if loc[0] and cost >= loc[0]["cost"]:
                return
            if i == len(concept_ids):
                loc[0] = {"cost": cost, "home": home, "chain": list(chain),
                          "links": list(links), "pcosts": list(pcosts)}
                return
            for cid, pcost in candk[i]:
                if cid in used:
                    continue
                if i == 0:
                    dfs(1, {cid}, [cid], [], [pcost], pcost)
                else:
                    pc, nodes, hops = causal_path(g, chain[-1], cid, home, home)
                    if pc is None:
                        continue
                    u = set(used)
                    u.add(cid)
                    dfs(i + 1, u, chain + [cid], links + [{"cost": pc, "nodes": nodes, "hops": hops}],
                        pcosts + [pcost], cost + pcost + pc)

        dfs(0, set(), [], [], [], 0)
        if loc[0]:
            home_locs.append(loc[0])

    home_locs.sort(key=lambda r: r["cost"])

    if home_locs:
        alternatives_raw = home_locs
    else:
        chain = list(concept_ids)
        links = []
        cost = 0
        ok = True
        for i in range(len(chain) - 1):
            pc, nodes, hops = causal_path(g, chain[i], chain[i + 1], None, None)
            if pc is None:
                ok = False
                break
            cost += pc + 2
            links.append({"cost": pc + 2, "nodes": nodes, "hops": hops})
        if ok:
            fallback = {"cost": cost, "home": None, "chain": chain, "links": links,
                        "pcosts": [0] * len(chain)}
            alternatives_raw = [fallback]
        else:
            alternatives_raw = []

    if not alternatives_raw:
        return None

    best = dict(alternatives_raw[0])
    best["alternatives_raw"] = alternatives_raw  # v1.2: per-home optima, cost asc
    return best


def _project_enrich(g: Graph, concept_ids, raw):
    """Per-stage mapping enrichment (spec step 7) for one raw projection result
    (cost, home, chain, links, pcosts) — shared by project()'s primary result
    and its v1.2 top-k `alternatives` (one raw result per candidate home).
    Returns {cost, home, chain, links, mappings}.
    mappings[i] = {pick, anchor, pcost, kind, hops, shared_terms} for concept_ids[i]."""
    chain = raw["chain"]
    home = raw["home"]
    pcosts = raw.get("pcosts") or [0] * len(concept_ids)

    mappings = []
    for i, pick in enumerate(concept_ids):
        anchor = chain[i]
        if pick == anchor:
            kind = "self"
            hops = []
        else:
            hops = aspect_path(g, pick, anchor, home)
            if hops:
                kind = "aspect"
            else:
                kind = "shared"
                hops = []
        mapping = {
            "pick": pick,
            "anchor": anchor,
            "pcost": pcosts[i] if i < len(pcosts) else 0,
            "kind": kind,
            "hops": hops,
        }
        mapping["shared_terms"] = shared_terms(g, pick, anchor, 8) if kind == "shared" else []
        mappings.append(mapping)

    return {
        "cost": raw["cost"],
        "home": home,
        "chain": chain,
        "links": raw["links"],
        "mappings": mappings,
    }


def project(g: Graph, concept_ids, k: int = 1):
    """Full projection: best causal-chain home + per-stage mapping enrichment.

    Returns dict {cost, home, chain, links, mappings, alternatives} or None if
    no projection found. The top-level (cost/home/chain/links/mappings) fields
    are always == alternatives[0] (v1.2: `alternatives` = top-k DISTINCT-home
    results by cost, k=1 default keeps every pre-v1.2 field byte-identical).
    """
    raw = _project_raw(g, concept_ids)
    if raw is None:
        return None

    alt_raws = raw.get("alternatives_raw") or [raw]
    k_eff = max(1, k)
    alternatives = [_project_enrich(g, concept_ids, r) for r in alt_raws[:k_eff]]

    result = dict(alternatives[0])
    result["alternatives"] = alternatives
    return result


# --------------------------------------------------------------------------
# diagnose  (v1.1 addendum, specs/api_v1.md ~136-173)
#
# The graph only attests the GOOD flow (X strengthens Y, via eitza edges).
# diagnose() derives candidate DEFICIENCIES at query time by inverting those
# attested edges near a concept: "if h -> c is attested (h builds c), then a
# lack of h is a plausible weakener of c." Nothing is stored; every inferred
# item carries the full derivation (aspect hops + the one real eitza edge it
# inverts) so it can be verified against the data (AD2).
# --------------------------------------------------------------------------
def diagnose(g: Graph, concept_id, depth=2, topn=12):
    """Contexts = concept_id plus concepts within aspect-distance <= depth
    (via aspect_dist/aspect_path). For each context c, attested helpers are
    eitza_in edges of c; inferred deficiencies are those edges inverted
    (lack_of helper weakens c), ranked by (dist asc, edge weight desc)."""
    dmap = aspect_dist(g, concept_id)
    context_ids = [cid for cid in dmap if dmap[cid] <= depth]
    context_ids.sort(key=lambda cid: dmap[cid])
    context_ids = context_ids[:topn]

    contexts = []
    for cid in context_ids:
        d = dmap[cid]
        if cid == concept_id:
            path_hops = []
        else:
            hops = aspect_path(g, concept_id, cid, None) or []
            path_hops = [
                {"from": h["from"], "to": h["to"],
                 "proof": h["e"].get("p") or "", "ref": h["e"].get("ref") or []}
                for h in hops
            ]
        n = g.by_id.get(cid) or {}
        contexts.append({
            "id": cid, "he": n.get("he", ""), "gloss": n.get("gloss", ""),
            "dist": d, "path": path_hops,
        })

    attested_helpers = []
    inferred = []
    for ctx in contexts:
        cid = ctx["id"]
        d = ctx["dist"]
        for x in g.adj.get(cid, {}).get("all", []):
            if x["ty"] != "eitza" or x["dir"] != "in":
                continue  # only eitza_in: what leads TO this context
            # v1.5: only BUILDS edges may be inverted. Inverting a harms edge
            # ("Z damages c") into "lack of Z weakens c" would assert the exact
            # opposite of the text.
            if (x["e"].get("pol") or "builds") != "builds":
                continue
            e = x["e"]
            helper_id = x["o"]
            hn = g.by_id.get(helper_id) or {}
            he, gloss = hn.get("he", ""), hn.get("gloss", "")
            proof, ref = e.get("p") or "", e.get("ref") or []
            attested_helpers.append({
                "of": cid, "helper": helper_id, "he": he, "gloss": gloss,
                "proof": proof, "ref": ref,
            })
            derivation = list(ctx["path"]) + [
                {"from": helper_id, "to": cid, "proof": proof, "ref": ref}
            ]
            inferred.append({
                "lack_of": helper_id, "he": he, "gloss": gloss, "weakens": cid,
                "dist": d, "derivation": derivation, "status": "inferred",
                "_w": e.get("w") or 1,
            })

    inferred.sort(key=lambda item: (item["dist"], -item["_w"]))
    for item in inferred:
        item.pop("_w", None)

    concept_n = g.by_id.get(concept_id) or {}
    return {
        "ok": True,
        "concept": {
            "id": concept_id, "he": concept_n.get("he", ""),
            "gloss": concept_n.get("gloss", ""), "refs": concept_n.get("refs") or [],
        },
        "contexts": contexts,
        "attested_helpers": attested_helpers,
        "inferred_deficiencies": inferred,
        "note": "inferred items are query-time inversions of attested builds-edges, not text",
    }


# --------------------------------------------------------------------------
# packets  (v1.4 addendum, specs/api_v1.md ~236-275)
#
# A packet is PURE query-time closure: within one torah ref, the connected
# components of that torah's bechina+equation edges (Rebbe Nachman chaining
# identifications within a single teaching — hop-count inside a torah is
# sentence-order, not conceptual distance). Nothing new is stored; a "packet"
# is just a union-find pass over the already-attested edges, computed lazily
# per ref on request.
#
# A USER packet is a wholly separate evidence class: Shmuel's own annotation
# ({torah, members, note, by, date}), persisted append-only to
# ontology/packets/user_packets.jsonl, and NEVER silently merged into the
# attested graph — it only participates in traversal via `why --loose=all`,
# where every hop it contributes is labeled kind:"user-packet" plus by/note.
# --------------------------------------------------------------------------
def torah_bechina_components(g: Graph, ref):
    """Connected components of `ref`'s bechina+equation edges (union-find).
    Only components with >=2 members are returned (a lone node with no
    bechina/equation edge in this torah isn't a chained "packet"). Sorted by
    size desc, ties broken by smallest member id for determinism; members
    within a component are sorted by id."""
    parent = {}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry

    for e in g.edges:
        if e.get("ty") not in ("bechina", "equation"):
            continue
        if ref not in (e.get("ref") or []):
            continue
        s, t = e.get("s"), e.get("t")
        if s not in g.by_id or t not in g.by_id:
            continue
        parent.setdefault(s, s)
        parent.setdefault(t, t)
        union(s, t)

    comps = {}
    for nid in parent:
        comps.setdefault(find(nid), []).append(nid)

    result = [sorted(members) for members in comps.values() if len(members) >= 2]
    result.sort(key=lambda m: (-len(m), m[0]))
    return result


def packets_of(g: Graph, nid):
    """Every (torah, packet) containing `nid` — one entry per torah ref where
    `nid` has >=1 bechina/equation edge and lands in a real (size>=2)
    component there (spec: `packets --of ID`)."""
    refs = set()
    for x in g.adj.get(nid, {}).get("all", []):
        if x["ty"] not in ("bechina", "equation"):
            continue
        for r in x["e"].get("ref") or []:
            refs.add(r)

    out = []
    for ref in sorted(refs):
        for comp in torah_bechina_components(g, ref):
            if nid in comp:
                out.append({"torah": ref, "packet": [
                    {"id": cid, "he": (g.by_id.get(cid) or {}).get("he", "")} for cid in comp
                ]})
                break
    return out


def load_user_packets(path=None):
    """Read ontology/packets/user_packets.jsonl (one JSON object per line);
    [] if the file doesn't exist yet (spec: "created if absent")."""
    p = Path(path) if path else USER_PACKETS_PATH
    if not p.exists():
        return []
    entries = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        entries.append(json.loads(line))
    return entries


def append_user_packet(entry, path=None):
    """Append one user-packet entry, creating ontology/packets/ if needed."""
    p = Path(path) if path else USER_PACKETS_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def build_user_packet_adjacency(entries):
    """Turn user-packet entries into a `node -> [(other_id, synthetic_edge), ...]`
    adjacency map for `causal_path(mode="loose_all")`. Every unordered member
    pair within one entry shares a SINGLE synthetic edge dict object (built
    once here, reused — not rebuilt per lookup) so `id(edge)`-based exclusion
    (the `why -k` rerun trick) stays stable across repeated causal_path calls
    within the same command. The synthetic edge always carries `_by`/`_note`
    so downstream hop JSON can label it kind:"user-packet" with by/note,
    never mistaken for attested graph data."""
    adj = {}
    for entry in entries:
        members = list(dict.fromkeys(entry.get("members") or []))
        torah = entry.get("torah")
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                m1, m2 = members[i], members[j]
                synth = {
                    "s": m1, "t": m2, "ty": "user-packet", "w": 1, "p": "",
                    "ref": [torah] if torah else [],
                    "_by": entry.get("by") or "", "_note": entry.get("note") or "",
                }
                adj.setdefault(m1, []).append((m2, synth))
                adj.setdefault(m2, []).append((m1, synth))
    return adj


# --------------------------------------------------------------------------
# CLI helpers
# --------------------------------------------------------------------------
def node_summary(g: Graph, nid):
    n = g.by_id.get(nid) or {}
    return {
        "id": n.get("id", nid),
        "he": n.get("he", ""),
        "gloss": n.get("gloss", ""),
        "kind": n.get("kind", ""),
        "deg": n.get("deg", 0),
        "refs": n.get("refs") or [],
    }


def _row(g: Graph, other_id, e):
    o = g.by_id.get(other_id) or {}
    return {
        "id": other_id,
        "he": o.get("he", ""),
        "gloss": o.get("gloss", ""),
        "proof": e.get("p") or "",
        "ref": e.get("ref") or [],
        "polarity": e.get("pol") or "neutral",
        "via": e.get("via") or "presence",
    }


def rows_for(g: Graph, nid, ty, dir_filter=None, polarity=None):
    """v1.5: `polarity` filters eitza rows by their pol field ('all'/None = no
    filter). Pre-v2-merge data had only builds eitza edges, so polarity='builds'
    reproduces the pre-merge result set exactly."""
    out = []
    for x in g.adj.get(nid, {}).get("all", []):
        if x["ty"] != ty:
            continue
        if dir_filter is not None and x["dir"] != dir_filter:
            continue
        if polarity and polarity != "all" and ty == "eitza" \
                and (x["e"].get("pol") or "builds") != polarity:
            continue
        out.append(_row(g, x["o"], x["e"]))
    return out


class TmapError(Exception):
    pass


def require_node(g: Graph, nid):
    if nid not in g.by_id:
        raise TmapError(f"unknown concept id: {nid!r}")
    return g.by_id[nid]


# ---- commands ----
def cmd_search(g: Graph, args):
    res = search(g, args.query, args.n)
    return {"ok": True, "results": [
        {**node_summary(g, n["id"]), "score": s} for n, s in res
    ]}


def cmd_match(g: Graph, args):
    res = match(g, args.text, args.n)
    return {"ok": True, "results": [
        {"id": cid, "he": (g.by_id.get(cid) or {}).get("he", ""),
         "gloss": (g.by_id.get(cid) or {}).get("gloss", ""), "score": s}
        for cid, s in res
    ]}


def cmd_concept(g: Graph, args):
    require_node(g, args.id)
    out = node_summary(g, args.id)
    out["aspects"] = rows_for(g, args.id, "bechina")
    out["causes"] = rows_for(g, args.id, "eitza", "in")
    out["effects"] = rows_for(g, args.id, "eitza", "out")
    return {"ok": True, **out}


def cmd_aspects(g: Graph, args):
    require_node(g, args.id)
    return {"ok": True, "results": rows_for(g, args.id, "bechina")}


def cmd_advice(g: Graph, args):
    """v1.5: advice means COUNSEL to attain the concept, so it defaults to
    polarity=builds (a harms-in edge — "Z damages X" — is not advice; ask for
    it explicitly with --polarity harms/all)."""
    require_node(g, args.id)
    pol = getattr(args, "polarity", None) or "builds"
    return {"ok": True, "polarity_filter": pol,
            "results": rows_for(g, args.id, "eitza", "in", polarity=pol)}


def cmd_effects(g: Graph, args):
    """v1.5: effects means everything the concept leads to — good and bad —
    so it defaults to polarity=all with each row labeled; filter with
    --polarity builds/harms."""
    require_node(g, args.id)
    pol = getattr(args, "polarity", None) or "all"
    return {"ok": True, "polarity_filter": pol,
            "results": rows_for(g, args.id, "eitza", "out", polarity=pol)}


def _polarity_ok(e, polarity):
    """v1.5 traversal filter: restricts eitza edges to one polarity; neutral
    aspect edges (bechina/equation) always pass."""
    if not polarity or polarity == "all":
        return True
    if e.get("ty") != "eitza":
        return True
    return (e.get("pol") or "builds") == polarity


def _shortest_path_search(g: Graph, a, b, blocked_nodes=None, blocked_edges=None, polarity=None):
    """Weighted shortest path (cost = 1/max(1,e.w)), any edge type, undirected.
    Port of runPath (~562). Extended with optional `blocked_nodes` (ids that may
    not appear in the path, other than the start) and `blocked_edges` (edge
    identities, via id(edge_dict), that may not be traversed) so it can serve
    as the spur-search primitive for Yen's k-shortest-paths (v1.2 -k).
    Returns {"cost", "nodes", "hops":[{"from","to","e"}]} or None."""
    if a == b:
        return {"cost": 0, "nodes": [a], "hops": []}

    blocked_nodes = blocked_nodes or ()
    blocked_edges = blocked_edges or ()

    counter = itertools.count()
    dist = {a: 0}
    prev = {}
    h = [(0, next(counter), a)]
    while h:
        c, _, node = heapq.heappop(h)
        if c > dist.get(node, 1e9):
            continue
        if node == b:
            break
        for x in g.adj.get(node, {}).get("all", []):
            e = x["e"]
            if x["o"] in blocked_nodes or id(e) in blocked_edges:
                continue
            if not _polarity_ok(e, polarity):
                continue
            nc = c + 1 / max(1, e.get("w") or 1)
            if nc < dist.get(x["o"], 1e9):
                dist[x["o"]] = nc
                prev[x["o"]] = {"from": node, "e": e}
                heapq.heappush(h, (nc, next(counter), x["o"]))

    if b not in dist:
        return None

    nodes, hops, cur = [b], [], b
    while cur != a:
        p = prev.get(cur)
        if p is None:
            return None
        hops.insert(0, {"from": p["from"], "to": cur, "e": p["e"]})
        cur = p["from"]
        nodes.insert(0, cur)
    return {"cost": dist[b], "nodes": nodes, "hops": hops}


def _path_steps(hops):
    return [{"from": h["from"], "to": h["to"], "ty": h["e"].get("ty"),
              "proof": h["e"].get("p") or "", "ref": h["e"].get("ref") or [],
              "polarity": h["e"].get("pol") or "neutral", "via": h["e"].get("via") or "presence"}
             for h in hops]


def k_shortest_paths(g: Graph, a, b, k=1, polarity=None):
    """Yen's algorithm for k shortest LOOPLESS paths a->b over the same weighting
    as `_shortest_path_search` (v1.2 addendum). Returns a cost-ascending list of
    {"cost", "nodes", "hops"} dicts, length <= k, no duplicate node-sequences.
    The first entry is exactly the plain-Dijkstra best path (backward compatible)."""
    if a == b:
        return [{"cost": 0, "nodes": [a], "hops": []}]

    first = _shortest_path_search(g, a, b, polarity=polarity)
    if first is None:
        return []

    A = [first]
    seen = {tuple(first["nodes"])}
    B = []

    while len(A) < k:
        prev = A[-1]
        prev_nodes, prev_hops = prev["nodes"], prev["hops"]
        for i in range(len(prev_nodes) - 1):
            spur_node = prev_nodes[i]
            root_nodes = prev_nodes[: i + 1]
            root_hops = prev_hops[:i]
            root_cost = sum(1 / max(1, hh["e"].get("w") or 1) for hh in root_hops)

            blocked_edges = set()
            for p in A:
                if len(p["nodes"]) > i + 1 and p["nodes"][: i + 1] == root_nodes:
                    blocked_edges.add(id(p["hops"][i]["e"]))
            blocked_nodes = set(root_nodes[:-1])  # everything on the root path except the spur node

            spur = _shortest_path_search(g, spur_node, b, blocked_nodes=blocked_nodes,
                                         blocked_edges=blocked_edges, polarity=polarity)
            if spur is None:
                continue

            total_nodes = root_nodes[:-1] + spur["nodes"]
            key = tuple(total_nodes)
            if key in seen or len(set(total_nodes)) != len(total_nodes):
                continue
            total_hops = root_hops + spur["hops"]
            total_cost = root_cost + spur["cost"]
            B.append({"cost": total_cost, "nodes": total_nodes, "hops": total_hops})

        if not B:
            break
        B.sort(key=lambda p: p["cost"])
        nxt = None
        for cand in B:
            if tuple(cand["nodes"]) not in seen:
                nxt = cand
                break
        if nxt is None:
            break
        seen.add(tuple(nxt["nodes"]))
        A.append(nxt)
        B = [p for p in B if tuple(p["nodes"]) != tuple(nxt["nodes"])]

    return A[:k]


def cmd_path(g: Graph, args):
    """Weighted shortest path (cost = 1/max(1,e.w)), any edge type, undirected.
    `steps`/`length` (best path) are unchanged (v1 contract); `-k` (v1.2) adds
    `alternatives`: [{cost, steps}] via Yen's k-shortest loopless paths."""
    a, b = args.a, args.b
    require_node(g, a)
    require_node(g, b)
    k = max(1, getattr(args, "k", 1) or 1)
    pol = getattr(args, "polarity", None) or "all"

    paths = k_shortest_paths(g, a, b, k, polarity=pol)
    if not paths:
        return {"ok": False, "error": f"no path found between {a} and {b}"
                + (f" (polarity={pol})" if pol != "all" else "")}

    best = paths[0]
    steps = _path_steps(best["hops"])
    alternatives = [{"cost": p["cost"], "steps": _path_steps(p["hops"])} for p in paths]
    return {"ok": True, "steps": steps, "length": len(steps), "alternatives": alternatives}


def cmd_common(g: Graph, args):
    a, b = args.a, args.b
    require_node(g, a)
    require_node(g, b)
    na = g.adj.get(a, {}).get("all", [])
    nb = g.adj.get(b, {}).get("all", [])
    set_b = {x["o"] for x in nb}
    common_ids = []
    seen = set()
    for x in na:
        if x["o"] in set_b and x["o"] not in seen:
            seen.add(x["o"])
            common_ids.append(x["o"])

    def edge_to(lst, other):
        for x in lst:
            if x["o"] == other:
                return x
        return None

    shared = []
    for cid in common_ids:
        o = g.by_id.get(cid) or {}
        xa = edge_to(na, cid)
        xb = edge_to(nb, cid)
        shared.append({
            "id": cid, "he": o.get("he", ""), "gloss": o.get("gloss", ""),
            "via_a": {"ty": xa["e"].get("ty"), "proof": xa["e"].get("p") or ""} if xa else None,
            "via_b": {"ty": xb["e"].get("ty"), "proof": xb["e"].get("p") or ""} if xb else None,
        })
    return {"ok": True, "shared": shared}


def cmd_torah(g: Graph, args):
    ref = args.ref
    es = [e for e in g.edges if ref in (e.get("ref") or [])]
    ns = []
    seen = set()
    for e in es:
        for nid in (e.get("s"), e.get("t")):
            if nid not in seen:
                seen.add(nid)
                ns.append(nid)
    concepts = [node_summary(g, nid) for nid in ns if nid in g.by_id]
    concepts.sort(key=lambda n: -(n.get("deg") or 0))
    edges = [{"s": e.get("s"), "t": e.get("t"), "ty": e.get("ty"), "proof": e.get("p") or ""} for e in es]
    return {"ok": True, "ref": ref, "concepts": concepts, "edges": edges}


def _project_hop_json_causal(h):
    e = h["e"]
    return {"from": h["from"], "to": h["to"], "kind": h["kind"], "hc": h["hc"],
            "proof": e.get("p") or "", "ref": e.get("ref") or [],
            "polarity": e.get("pol") or "neutral", "via": e.get("via") or "presence"}


def _project_hop_json_aspect(h):
    e = h["e"]
    return {"from": h["from"], "to": h["to"], "proof": e.get("p") or "", "ref": e.get("ref") or []}


def _project_result_json(g: Graph, result):
    """Convert one enriched project() result (ids only) to full CLI JSON shape
    (chain of full node summaries, JSON-safe hops). Shared by the primary
    result and each v1.2 `alternatives` entry."""
    chain_full = [node_summary(g, cid) for cid in result["chain"]]
    links = [{"cost": l["cost"], "hops": [_project_hop_json_causal(h) for h in (l.get("hops") or [])]}
              for l in result["links"]]
    mappings = [{
        "pick": m["pick"], "anchor": m["anchor"], "kind": m["kind"], "pcost": m["pcost"],
        "hops": [_project_hop_json_aspect(h) for h in (m.get("hops") or [])],
        "shared_terms": m.get("shared_terms") or [],
    } for m in result["mappings"]]
    return {"cost": result["cost"], "home": result["home"], "chain": chain_full,
            "mappings": mappings, "links": links}


def _resolve_project_stage(g: Graph, raw_id):
    """v1.4: a project stage may be `re:PATTERN` (spec ~261), expanding over
    he+gloss (case-insensitive, cap 40 -- same rule as why's --from/--to).
    Multiple matches must collapse to ONE concrete anchor for project()'s
    existing single-id-per-stage pipeline; documented simplification: pick
    the highest-`deg` match (a proxy for "most attested/central" reading),
    since the spec doesn't prescribe a selection rule and no acceptance test
    (AP1-5) exercises this path. The full candidate set is still reported
    (never a silent choice)."""
    if not raw_id.startswith("re:"):
        return raw_id, None
    pattern = raw_id[3:]
    matched, warn, total = _endpoint_matches(g, pattern)
    if not matched:
        raise TmapError(f"no concepts matched project stage pattern: {pattern!r}")
    matched_sorted = sorted(matched, key=lambda cid: -((g.by_id.get(cid) or {}).get("deg") or 0))
    chosen = matched_sorted[0]
    info = {
        "pattern": pattern, "chosen": chosen,
        "matched": [{"id": cid, "he": (g.by_id.get(cid) or {}).get("he", "")} for cid in matched],
    }
    if warn:
        info["warning"] = f"matched {total} concepts; capped at 40"
    return chosen, info


def cmd_project(g: Graph, args):
    raw_ids = args.ids
    if not (2 <= len(raw_ids) <= 6):
        raise TmapError("project requires 2-6 concept ids")

    ids, resolved = [], []
    for raw in raw_ids:
        cid, info = _resolve_project_stage(g, raw)
        ids.append(cid)
        if info:
            resolved.append(info)
    for nid in ids:
        require_node(g, nid)

    k = max(1, getattr(args, "k", 1) or 1)
    res = project(g, ids, k=k)
    if res is None:
        return {"ok": False, "error": "no projection found for those concepts"}

    primary = _project_result_json(g, res)
    alternatives = [_project_result_json(g, alt) for alt in res["alternatives"]]

    out = {"ok": True, **primary, "alternatives": alternatives}
    if resolved:
        out["resolved_stages"] = resolved
    return out


def cmd_diagnose(g: Graph, args):
    require_node(g, args.id)
    return diagnose(g, args.id, depth=args.depth, topn=args.n)


# --------------------------------------------------------------------------
# why / chain  (v1.3 addendum: typed causal query + mechanical verifier)
# --------------------------------------------------------------------------
def _why_hop_json(g: Graph, h):
    e = h["e"]
    out = {
        "from": h["from"], "to": h["to"],
        "he_from": (g.by_id.get(h["from"]) or {}).get("he", ""),
        "he_to": (g.by_id.get(h["to"]) or {}).get("he", ""),
        "kind": h["kind"], "hc": h["hc"],
        "proof": e.get("p") or "", "ref": e.get("ref") or [],
        "polarity": e.get("pol") or "neutral", "via": e.get("via") or "presence",
    }
    if h["kind"] == "user-packet":  # v1.4: ALWAYS visibly labeled (spec ~256-257)
        out["by"] = e.get("_by") or ""
        out["note"] = e.get("_note") or ""
    return out


# ---- v1.4: set endpoints (`why --from REGEX --to REGEX`), spec ~258-261 ----
def _endpoint_matches(g: Graph, pattern):
    """Expand a regex over he+gloss (case-insensitive) to a node-id list,
    excluding statement nodes (consistent with search()/match()). Capped at
    40; returns (matched_ids[:40], warn: bool, total_matched)."""
    rx = re.compile(pattern, re.I)
    matched = []
    for n in g.nodes:
        if n.get("kind") == "statement":
            continue
        text = (n.get("he") or "") + " " + (n.get("gloss") or "")
        if rx.search(text):
            matched.append(n["id"])
    return matched[:40], len(matched) > 40, len(matched)


def _resolve_endpoints(g: Graph, single_id, pattern, label):
    """One side of `why`'s endpoints: either a single concrete id (positional,
    validated via require_node) or a regex-expanded set (--from/--to).
    Returns (ids, warn, total_matched)."""
    if single_id:
        require_node(g, single_id)
        return [single_id], False, 1
    if pattern:
        matched, warn, total = _endpoint_matches(g, pattern)
        if not matched:
            raise TmapError(f"no concepts matched --{label} pattern: {pattern!r}")
        return matched, warn, total
    raise TmapError(f"why requires {label.upper()} (positional id, or --{label} PATTERN)")


def _causal_chains_multi(g, froms, tos, k, mode, user_packet_adj, pre_bound, post_bound):
    """Set-endpoint `why`: run k_causal_chains over every (from,to) pair, then
    take the global cost-ascending, distinct-hop-sequence top-k. Correct
    (not just a heuristic): if a chain C is in the TRUE global top-k, then
    fewer than k chains anywhere beat it, so in particular fewer than k
    chains from C's own (from,to) pair beat it — i.e. C is already within
    that pair's own top-k. So merging each pair's own top-k always contains
    every globally-top-k chain. With singleton from/to sets (the pre-v1.4
    case) this is exactly one pair, i.e. exactly k_causal_chains(a,b,k)."""
    seen = set()
    pool = []
    for f in froms:
        for t in tos:
            for c in k_causal_chains(g, f, t, k, mode=mode, user_packet_adj=user_packet_adj,
                                      pre_bound=pre_bound, post_bound=post_bound):
                seq = tuple((h["from"], h["to"], h["kind"]) for h in c["hops"])
                if seq in seen:
                    continue
                seen.add(seq)
                pool.append(c)
    pool.sort(key=lambda c: c["cost"])
    return pool[:k]


def cmd_why(g: Graph, args):
    """`why A B [-k 3]`: thin exposure of causal_path(A,B,home=None,strict=None)
    (spec ~204-218). No chain is a normal, non-error answer: {ok:true, chains:[]}
    means "the map cannot attest this".

    v1.4 additions: `--loose`/`--loose=all` swap the traversal cost model
    (see causal_path's docstring); `--from`/`--to` REGEX expand to node sets
    (capped at 40, reported as matched_from/matched_to); `--pre`/`--post`
    bound bechina-hop runs before the first / after the last eitza hop.

    Endpoint resolution: `ids` is a variadic positional ([], [A], or [A, B]).
    Whichever side has a --from/--to PATTERN does NOT consume a positional;
    the remaining positional(s), in order, fill whichever side(s) lack a
    PATTERN. This is what lets a single positional pair with the OTHER
    side's PATTERN (spec ~258-261: "and positional ids still fine")."""
    from_re = getattr(args, "from_re", None)
    to_re = getattr(args, "to_re", None)
    positionals = list(args.ids or [])
    a = None if from_re else (positionals.pop(0) if positionals else None)
    b = None if to_re else (positionals.pop(0) if positionals else None)
    if positionals:
        raise TmapError(f"why: too many positional ids: {positionals!r}")

    froms, warn_from, total_from = _resolve_endpoints(g, a, from_re, "from")
    tos, warn_to, total_to = _resolve_endpoints(g, b, to_re, "to")
    k = max(1, getattr(args, "k", 1) or 1)

    loose_arg = getattr(args, "loose", None)
    mode = "strict" if loose_arg is None else ("loose_all" if loose_arg == "all" else "loose")

    user_packet_adj = None
    if mode == "loose_all":
        entries = load_user_packets(getattr(args, "packets_path", None))
        user_packet_adj = build_user_packet_adjacency(entries)

    pre_bound = getattr(args, "pre", None)
    post_bound = getattr(args, "post", None)

    raw = _causal_chains_multi(g, froms, tos, k, mode, user_packet_adj, pre_bound, post_bound)
    chains = [{"cost": c["cost"], "hops": [_why_hop_json(g, h) for h in c["hops"]]} for c in raw]

    def _mrow(nid):
        n = g.by_id.get(nid) or {}
        return {"id": nid, "he": n.get("he", "")}

    result = {
        "ok": True, "chains": chains,
        "matched_from": [_mrow(i) for i in froms],
        "matched_to": [_mrow(i) for i in tos],
    }
    if warn_from:
        result["warning_from"] = f"--from matched {total_from} concepts; capped at 40"
    if warn_to:
        result["warning_to"] = f"--to matched {total_to} concepts; capped at 40"
    return result


def _best_junction(g: Graph, a, b):
    """Best attesting edge for one `chain` adjacent pair a->b (spec ~220-224):
    forward eitza (a==e.s) > undirected bechina/equation > (unattested) reverse
    eitza. eitza attests forward only (cause->effect); a reverse-only eitza edge
    is surfaced with attested:false plus a `note` explaining why it doesn't
    count, so the caller can see exactly what the map DOES say even when it
    doesn't attest the asked-for direction."""
    candidates = [x for x in g.adj.get(a, {}).get("all", []) if x["o"] == b]

    forward_eitza = next((x for x in candidates if x["ty"] == "eitza" and x["dir"] == "out"), None)
    if forward_eitza is not None:
        e = forward_eitza["e"]
        return {"from": a, "to": b, "attested": True, "ty": e.get("ty"), "direction": "forward",
                "polarity": e.get("pol") or "builds", "via": e.get("via") or "presence",
                "proof": e.get("p") or "", "ref": e.get("ref") or []}

    undirected = next((x for x in candidates if x["ty"] in ("bechina", "equation")), None)
    if undirected is not None:
        e = undirected["e"]
        return {"from": a, "to": b, "attested": True, "ty": e.get("ty"), "direction": "undirected",
                "polarity": e.get("pol") or "neutral", "via": e.get("via") or "presence",
                "proof": e.get("p") or "", "ref": e.get("ref") or []}

    reverse_eitza = next((x for x in candidates if x["ty"] == "eitza" and x["dir"] == "in"), None)
    if reverse_eitza is not None:
        e = reverse_eitza["e"]
        return {"from": a, "to": b, "attested": False, "ty": e.get("ty"), "direction": "reverse",
                "polarity": e.get("pol") or "builds", "via": e.get("via") or "presence",
                "proof": e.get("p") or "", "ref": e.get("ref") or [],
                "note": f"eitza only attests forward (cause->effect); the attested direction is {b}->{a}"}

    return {"from": a, "to": b, "attested": False, "ty": None, "direction": None, "proof": "", "ref": []}


def cmd_chain(g: Graph, args):
    """`chain ID ID ID...` (>=2 ids): mechanical junction-by-junction verifier
    (spec ~220-224). complete = every adjacent-pair junction is attested."""
    ids = args.ids
    if len(ids) < 2:
        raise TmapError("chain requires >=2 concept ids")
    for nid in ids:
        require_node(g, nid)

    junctions = [_best_junction(g, ids[i], ids[i + 1]) for i in range(len(ids) - 1)]
    complete = all(j["attested"] for j in junctions)
    return {"ok": True, "complete": complete, "junctions": junctions}


# --------------------------------------------------------------------------
# packets / packet  (v1.4 addendum, spec ~245-249)
# --------------------------------------------------------------------------
def cmd_packets(g: Graph, args):
    """`packets REF` -> components; `packets --of ID` -> every (torah,packet)
    containing ID."""
    of_id = getattr(args, "of_id", None)
    if of_id:
        require_node(g, of_id)
        return {"ok": True, "of": of_id, "packets": packets_of(g, of_id)}

    ref = args.ref
    if not ref:
        raise TmapError("packets requires REF or --of ID")
    comps = torah_bechina_components(g, ref)
    packets_out = [
        [{"id": cid, "he": (g.by_id.get(cid) or {}).get("he", "")} for cid in comp]
        for comp in comps
    ]
    return {"ok": True, "ref": ref, "packets": packets_out}


def cmd_packet_add(g: Graph, args):
    """`packet add REF ID [ID...] --note "..."`: append a user-packet entry.
    Separate evidence class (spec ~242-243): never silently merged into the
    attested graph; only used by `why --loose=all`, always visibly labeled."""
    for nid in args.ids:
        require_node(g, nid)
    entry = {
        "torah": args.ref,
        "members": args.ids,
        "note": args.note or "",
        "by": args.by,
        "date": datetime.date.today().isoformat(),
    }
    append_user_packet(entry, path=getattr(args, "packets_path", None))
    return {"ok": True, "added": entry}


def cmd_packet_list(g: Graph, args):
    """`packet list`: dump user-packet entries as-is."""
    entries = load_user_packets(getattr(args, "packets_path", None))
    return {"ok": True, "entries": entries}


# --------------------------------------------------------------------------
# selftest — ACs 1-5 against real data
# --------------------------------------------------------------------------
def _check(checks, name, ok, detail=""):
    checks.append({"name": name, "ok": bool(ok), "detail": detail})


def _walk_causal_hops(res):
    for l in res["links"]:
        for h in l.get("hops") or []:
            yield h


def _validate_project_result(res, concept_ids, checks, label):
    ok_all = True

    if res is None:
        _check(checks, f"{label}: ok", False, "no projection found")
        return False
    _check(checks, f"{label}: ok", True)

    chain = res["chain"]
    distinct = len(set(chain)) == len(chain)
    _check(checks, f"{label}: chain distinct", distinct, str(chain))
    ok_all &= distinct

    kinds_ok = all(m["kind"] in ("self", "aspect", "shared") for m in res["mappings"])
    _check(checks, f"{label}: mapping kinds valid", kinds_ok)
    ok_all &= kinds_ok

    aspect_hops_ok = all((m["kind"] != "aspect") or len(m["hops"]) > 0 for m in res["mappings"])
    _check(checks, f"{label}: aspect kind => hops non-empty", aspect_hops_ok)
    ok_all &= aspect_hops_ok

    links_have_cause = all(
        any(h["kind"] == "cause" for h in (l.get("hops") or [])) for l in res["links"]
    ) if res["links"] else True
    _check(checks, f"{label}: every link has >=1 cause hop", links_have_cause)
    ok_all &= links_have_cause

    if res["home"]:
        refs_ok = all(res["home"] in (h["e"].get("ref") or []) for h in _walk_causal_hops(res))
        _check(checks, f"{label}: every causal hop ref contains home", refs_ok)
        ok_all &= refs_ok

    return ok_all


def selftest(g: Graph):
    checks = []
    t0 = time.time()

    # AC1 (counts updated for the 2026-07-09 v2 merge: 3,588 concepts + 627
    # legacy statements + 4,803 AI phrase-statements; 12,328 polarity-tagged edges)
    n_nodes, n_edges = len(g.nodes), len(g.edges)
    _check(checks, "AC1: node/edge counts", n_nodes == 9018 and n_edges == 12328,
           f"nodes={n_nodes} edges={n_edges}")
    sym_ok = True
    for e in g.edges:
        s, t = e.get("s"), e.get("t")
        if s not in g.adj or t not in g.adj:
            continue
        has_out = any(x["o"] == t and x["e"] is e for x in g.adj[s]["all"])
        has_in = any(x["o"] == s and x["e"] is e for x in g.adj[t]["all"])
        if not (has_out and has_in):
            sym_ok = False
            break
    _check(checks, "AC1: adj symmetric", sym_ok)

    # AC2
    joy = search(g, "joy", 3)
    joy_ids = [n["id"] for n, _ in joy]
    _check(checks, "AC2: search(joy) top-3 has c:simchah", "c:simchah" in joy_ids, str(joy_ids))
    emunah = search(g, "אמונה", 1)
    emunah_ok = bool(emunah) and (
        emunah[0][0].get("he") == "ארץ ישראל" or emunah[0][0].get("id", "").startswith("c:emunah")
    )
    _check(checks, "AC2: search(אמונה) top-1", emunah_ok,
           str(emunah[0][0].get("id") if emunah else None))

    # AC3
    ac3_ids = ["c:tefillah-2", "c:simchah", "c:emet"]
    if all(i in g.by_id for i in ac3_ids):
        res3 = project(g, ac3_ids)
        home_ok = bool(res3) and res3["home"] == "I:22"
        _check(checks, "AC3: home == I:22", home_ok, str(res3["home"]) if res3 else "None")
        _validate_project_result(res3, ac3_ids, checks, "AC3")
    else:
        _check(checks, "AC3: ids present", False, str(ac3_ids))

    # AC4 — varied triples
    candidates = [
        ["c:emunah", "c:divine", "c:mamon"],
        ["c:mamon", "c:mitzvah-charity", "c:simchah"],
        ["c:teshuvah", "c:emunah", "c:tefillah"],
    ]
    for i, ids in enumerate(candidates):
        ids = [i2 for i2 in ids if i2 in g.by_id]
        if len(ids) < 2:
            _check(checks, f"AC4[{i}]: ids present", False, str(ids))
            continue
        t1 = time.time()
        res4 = project(g, ids)
        elapsed = time.time() - t1
        _validate_project_result(res4, ids, checks, f"AC4[{i}]")
        _check(checks, f"AC4[{i}]: elapsed < 5s", elapsed < 5, f"{elapsed:.2f}s")

    # AC5 — forward-only causal hops, checked directly on causal_path/project internals
    ac5_ok = True
    ac5_detail = ""
    for ids in [ac3_ids] + candidates:
        ids = [i2 for i2 in ids if i2 in g.by_id]
        if len(ids) < 2:
            continue
        raw = _project_raw(g, ids)
        if raw is None:
            continue
        for l in raw["links"]:
            for h in l.get("hops") or []:
                if h["kind"] == "cause" and h["from"] != h["e"].get("s"):
                    ac5_ok = False
                    ac5_detail = f"hop {h['from']}->{h['to']} kind=cause but edge.s={h['e'].get('s')}"
    _check(checks, "AC5: forward-only eitza traversal", ac5_ok, ac5_detail)

    ok = all(c["ok"] for c in checks)
    elapsed_ms = int((time.time() - t0) * 1000)
    return {"ok": ok, "checks": checks, "elapsed_ms": elapsed_ms}


def cmd_selftest(g: Graph, args):
    return selftest(g)


# --------------------------------------------------------------------------
# argparse CLI
# --------------------------------------------------------------------------
def build_parser():
    # --data/--pretty/--packets-path are accepted both before and after the subcommand.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--data", default=None, help="path to explorer_data.json")
    common.add_argument("--pretty", action="store_true", help="pretty-print JSON output")
    common.add_argument("--packets-path", dest="packets_path", default=None,
                         help="path to user_packets.jsonl (default: ontology/packets/user_packets.jsonl)")

    p = argparse.ArgumentParser(prog="tmap", description="Torah Map concept-graph CLI", parents=[common])
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("search", help="autocomplete-style concept search", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("query")
    sp.add_argument("-n", type=int, default=10)
    sp.set_defaults(func=cmd_search)

    sp = sub.add_parser("match", help="free text -> closest concepts", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("text")
    sp.add_argument("-n", type=int, default=10)
    sp.set_defaults(func=cmd_match)

    sp = sub.add_parser("concept", help="full concept detail", parents=[common], epilog=PATTERN_HELP)
    sp.add_argument("id")
    sp.set_defaults(func=cmd_concept)

    sp = sub.add_parser("aspects", help="bechina neighbors of a concept", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("id")
    sp.set_defaults(func=cmd_aspects)

    sp = sub.add_parser("advice", help="eitza_in: what leads TO this concept", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("id")
    sp.add_argument("--polarity", choices=["builds", "harms", "neutral", "all"], default="builds",
                    help="v1.5: filter eitza edges by polarity (default builds — advice is counsel; "
                         "--polarity harms lists what DAMAGES the concept)")
    sp.set_defaults(func=cmd_advice)

    sp = sub.add_parser("effects", help="eitza_out: what this concept leads to", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("id")
    sp.add_argument("--polarity", choices=["builds", "harms", "neutral", "all"], default="all",
                    help="v1.5: filter eitza edges by polarity (default all, rows labeled)")
    sp.set_defaults(func=cmd_effects)

    sp = sub.add_parser("path", help="weighted shortest path between two concepts", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("a")
    sp.add_argument("b")
    sp.add_argument("-k", type=int, default=1, help="return top-k loopless alternatives (v1.2)")
    sp.add_argument("--polarity", choices=["builds", "harms", "all"], default="all",
                    help="v1.5: restrict traversed eitza edges to one polarity "
                         "(aspect edges always pass)")
    sp.set_defaults(func=cmd_path)

    sp = sub.add_parser("common", help="shared neighbors of two concepts", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("a")
    sp.add_argument("b")
    sp.set_defaults(func=cmd_common)

    sp = sub.add_parser("torah", help="everything tied to one teaching ref", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("ref")
    sp.set_defaults(func=cmd_torah)

    sp = sub.add_parser("project", help="project a concept chain onto a Torah", parents=[common],
                         epilog=PATTERN_HELP)
    sp.add_argument("ids", nargs="+", help="concept ids; a stage may be 're:PATTERN' (v1.4, cap 40 matches)")
    sp.add_argument("-k", type=int, default=1, help="return top-k distinct-home alternatives (v1.2)")
    sp.set_defaults(func=cmd_project)

    sp = sub.add_parser("diagnose", help="inferred deficiencies near a concept (query-time eitza inversion)",
                         parents=[common], epilog=PATTERN_HELP)
    sp.add_argument("id")
    sp.add_argument("--depth", type=int, default=2)
    sp.add_argument("-n", type=int, default=12)
    sp.set_defaults(func=cmd_diagnose)

    sp = sub.add_parser("why", help="typed causal query: does A cause B? (causal_path exposure)",
                         parents=[common], epilog=WHY_PATTERN_HELP,
                         formatter_class=argparse.RawDescriptionHelpFormatter)
    sp.add_argument("ids", nargs="*", default=[],
                    help="[A [B]] concept ids (or use --from/--to PATTERN; mixing one "
                         "positional id with the other side's PATTERN is fine)")
    sp.add_argument("--from", dest="from_re", default=None,
                    help="regex over he+gloss (case-insensitive) expanding to a set of start concepts, cap 40")
    sp.add_argument("--to", dest="to_re", default=None,
                    help="regex over he+gloss (case-insensitive) expanding to a set of end concepts, cap 40")
    sp.add_argument("-k", type=int, default=1, help="return top-k distinct causal chains (v1.3)")
    sp.add_argument("--loose", nargs="?", const="on", default=None, metavar="all",
                     help="loosen the traversal cost model (packet-contraction approximation); "
                          "--loose=all also allows user-packet co-membership hops (v1.4)")
    sp.add_argument("--pre", type=int, default=None,
                    help="max bechina hops before the first eitza hop (default: unlimited)")
    sp.add_argument("--post", type=int, default=None,
                    help="max bechina hops after the last eitza hop (default: unlimited)")
    sp.set_defaults(func=cmd_why)

    sp = sub.add_parser("chain", help="verify a claimed concept chain junction-by-junction",
                         parents=[common], epilog=PATTERN_HELP)
    sp.add_argument("ids", nargs="+")
    sp.set_defaults(func=cmd_chain)

    sp = sub.add_parser("packets", help="torah-scoped bechina+equation connected components (v1.4)",
                         parents=[common], epilog=PATTERN_HELP)
    sp.add_argument("ref", nargs="?", default=None, help="teaching ref, e.g. I:1")
    sp.add_argument("--of", dest="of_id", default=None, help="every (torah,packet) containing this concept id")
    sp.set_defaults(func=cmd_packets)

    sp = sub.add_parser("packet", help="user-packet entries: Shmuel's own annotations (v1.4)",
                         parents=[common], epilog=PATTERN_HELP)
    packet_sub = sp.add_subparsers(dest="packet_command", required=True)

    sp_add = packet_sub.add_parser("add", help="append a user-packet entry", parents=[common])
    sp_add.add_argument("ref", help="teaching ref this identification chain belongs to")
    sp_add.add_argument("ids", nargs="+", help="member concept ids")
    sp_add.add_argument("--note", default="", help="free-text note explaining the packet")
    sp_add.add_argument("--by", default="shmuel", help="attribution (default: shmuel)")
    sp_add.set_defaults(func=cmd_packet_add)

    sp_list = packet_sub.add_parser("list", help="dump all user-packet entries", parents=[common])
    sp_list.set_defaults(func=cmd_packet_list)

    sp = sub.add_parser("selftest", help="run built-in invariant suite", parents=[common])
    sp.set_defaults(func=cmd_selftest)

    return p


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    indent = 2 if args.pretty else None

    try:
        g = load_data(args.data)
    except Exception as ex:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"failed to load data: {ex}"}, ensure_ascii=False, indent=indent))
        return 1

    try:
        result = args.func(g, args)
    except TmapError as ex:
        print(json.dumps({"ok": False, "error": str(ex)}, ensure_ascii=False, indent=indent))
        return 1
    except Exception as ex:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": f"{type(ex).__name__}: {ex}"}, ensure_ascii=False, indent=indent))
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=indent))
    if isinstance(result, dict) and result.get("ok") is False:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
