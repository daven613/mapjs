#!/usr/bin/env python3
"""Prototype + test the STRUCTURAL PROJECTION algorithm before porting to the UI.

Goal (Shmuel's spec): given an ordered narrative of stages (free text each), find the
best mapping onto a cause->effect (eitza) chain in the text, where:
  - each stage maps to a concept by PARALLEL (semantic similarity), not by a causal edge;
  - consecutive mapped concepts are linked by CAUSATION (forward eitza), possibly via cheap
    reframing (bechina) hops;
  - staying inside ONE Torah is almost free; crossing Torahs is weighty; fewer/lighter hops win.

Test: feed a PARAPHRASE of LM I:7's chain (Joseph -> Truth -> Faith -> Redemption) and check
the algorithm recovers those four concepts, connected, inside Torah I:7.
"""
import json, math, heapq, collections, re
from pathlib import Path

G = Path(__file__).resolve().parent.parent / "ontology/graph"
d = json.loads((G / "explorer_data.json").read_text())
NODES = d["nodes"]; EDGES = d["edges"]
byId = {n["id"]: n for n in NODES}

# ---- token index (parallel matching) --------------------------------------
# Own gloss + Hebrew (full weight) plus the concept's OWN edge proofs (partial). No neighbour
# glosses — those turn hubs into text sponges that match everything. IDF discounts common words.
def toks(s): return re.findall(r"[a-z]{3,}|[א-ת]{2,}", (s or "").lower())
deg = {n["id"]: n.get("deg", 0) for n in NODES}
proof_txt = collections.defaultdict(list)
for e in EDGES:
    if e.get("p"):
        proof_txt[e["s"]].append(e["p"]); proof_txt[e["t"]].append(e["p"])
df = collections.Counter(); selftok = {}; ctxtok = {}
for n in NODES:
    st = set(toks(n.get("gloss")) + toks(n.get("he")))
    ct = set(); [ct.update(toks(x)) for x in proof_txt.get(n["id"], [])]
    ct -= st
    selftok[n["id"]] = st; ctxtok[n["id"]] = ct
    for w in st | ct: df[w] += 1
N = len(NODES)
idf = {w: math.log(N / c) for w, c in df.items()}
def score_one(q, cid):
    st, ct = selftok[cid], ctxtok[cid]; s = 0.0
    for w, c in q.items():
        wt = idf.get(w, .5) * (1 + math.log(c))
        if w in st: s += wt
        elif w in ct: s += 0.35 * wt
    # gentle prior against mega-hubs so they need real evidence, not sheer connectivity
    return s / (1 + math.log(1 + deg.get(cid, 0)) * 0.15)
def match_scores(text, topn=10, pool=None):
    q = collections.Counter(toks(text))
    if not q: return []
    ids = pool if pool is not None else [n["id"] for n in NODES if n.get("kind") != "statement"]
    scored = [(cid, score_one(q, cid)) for cid in ids]
    scored = [x for x in scored if x[1] > 0]
    scored.sort(key=lambda x: -x[1])
    return scored[:topn]

# ---- adjacency (directed causal + undirected reframe) ----------------------
adj = collections.defaultdict(list)   # u -> [(v, edge, kind)] kind: 'cause'|'reframe'
for e in EDGES:
    if e["ty"] == "eitza":
        adj[e["s"]].append((e["t"], e, "cause"))          # cause -> effect (forward only)
    elif e["ty"] == "bechina":
        adj[e["s"]].append((e["t"], e, "reframe"))
        adj[e["t"]].append((e["s"], e, "reframe"))

def hop_cost(edge, home):
    same = home in (edge.get("ref") or [])
    if same: return 0.12                                   # inside the chapter: almost free
    return 1.6 if edge["ty"] == "eitza" else 2.0           # jumping chapters is weighty

def causal_path(a, b, home, strict=None, maxset=6000):
    """Cheapest a->b path that includes >=1 forward causal (eitza) hop.
    If strict is a Torah ref, only edges occurring in that Torah may be used (stay in-chapter).
    Returns (cost, node_list)."""
    if a == b: return 0.0, [a]
    start = (a, 0); dist = {start: 0}; prev = {}
    pq = [(0, start)]; settled = 0
    while pq and settled < maxset:
        c, st = heapq.heappop(pq)
        if c > dist.get(st, 1e9): continue
        node, caused = st; settled += 1
        if node == b and caused:
            path = [st]
            while path[-1] in prev: path.append(prev[path[-1]])
            path.reverse()
            return c, [p[0] for p in path]
        for v, edge, kind in adj.get(node, []):
            if strict is not None and strict not in (edge.get("ref") or []): continue
            nc2 = caused or (kind == "cause")
            ncost = c + hop_cost(edge, home) + (0.15 if kind == "reframe" else 0.0)
            nst = (v, 1 if nc2 else 0)
            if ncost < dist.get(nst, 1e9):
                dist[nst] = ncost; prev[nst] = st
                heapq.heappush(pq, (ncost, nst))
    return None, None

concepts_in = collections.defaultdict(list)      # torah -> [concept ids present]
for n in NODES:
    for r in n.get("refs", []): concepts_in[r].append(n["id"])

def project(stages, home_try=12):
    # global candidates per stage (to discover which Torahs are worth trying as "home")
    gcand = [match_scores(s, 12) for s in stages]
    if any(not c for c in gcand): return None
    cover = collections.Counter()
    for c in gcand:
        for r in {r for cid, _ in c for r in byId[cid].get("refs", [])}: cover[r] += 1
    homes = [r for r, cnt in cover.most_common(home_try) if cnt >= 2]  # host >=2 stages

    best = None
    for home in homes:
        pool = concepts_in.get(home, [])
        # top-k in-chapter candidates per stage
        candk = [match_scores(s, 6, pool=pool) for s in stages]
        if any(not c for c in candk): continue
        maxs = max(sc for c in candk for _, sc in c) or 1
        semc = [{cid: (1 - sc / maxs) for cid, sc in c} for c in candk]
        # DFS assignment: distinct concepts, consecutive linked by an in-chapter causal path
        bestHome = [None]
        def dfs(i, used, chain, links, cost):
            if bestHome[0] and cost >= bestHome[0]["cost"]: return
            if i == len(stages):
                bestHome[0] = {"cost": cost, "home": home, "chain": list(chain),
                               "links": list(links)}; return
            for cid, _ in candk[i]:
                if cid in used: continue
                if i == 0:
                    dfs(1, used | {cid}, [cid], [], semc[0][cid])
                else:
                    pc, nodes = causal_path(chain[-1], cid, home, strict=home)
                    if pc is None: continue
                    dfs(i + 1, used | {cid}, chain + [cid], links + [(pc, nodes)],
                        cost + semc[i][cid] + pc)
        dfs(0, set(), [], [], 0.0)
        if bestHome[0] and (best is None or bestHome[0]["cost"] < best["cost"]):
            best = bestHome[0]
    # cross-Torah fallback: use global best matches, connect with Torah-jump penalties
    if best is None:
        chosen = [c[0][0] for c in gcand]
        total = 0.0; links = []; ok = True
        for i in range(len(chosen) - 1):
            cost, nodes = causal_path(chosen[i], chosen[i + 1], None)
            if cost is None: ok = False; break
            total += cost + 2.0; links.append((cost, nodes))   # +2 per cross-chapter link
        if ok: best = {"cost": total, "home": None, "chain": chosen, "links": links, "scores": None}
    return best

def show(stages, res):
    print("STAGES:")
    for s in stages: print("   •", s)
    if not res: print("  -> no projection found"); return
    print(f"\nBEST PROJECTION  (home Torah: {res['home'] or 'mixed/cross-Torah'}, weight {res['cost']:.2f})")
    for i, cid in enumerate(res["chain"]):
        n = byId[cid]
        print(f"  stage {i+1} → {n['he']}  [{cid}]  refs={n.get('refs')[:5]}")
        print(f"            {(n.get('gloss') or '')[:70]}")
        if i < len(res["links"]):
            cost, nodes = res["links"][i]
            hebs = " → ".join(byId[x]["he"] for x in nodes)
            print(f"       link↓ (cost {cost:.2f}): {hebs}")

if __name__ == "__main__":
    tests = [
        ("paraphrase of I:7 (Joseph→Truth→Faith→Redemption)", [
            "a righteous man betrayed and sold by his brothers who stayed pure and rose to power in exile",
            "speaking with complete honesty and integrity, never falsehood",
            "wholehearted belief and trust in God and his providence",
            "the final national deliverance of Israel and the coming of the messiah"]),
        ("joy chain (I:22 territory)", [
            "great joy and gladness of the heart",
            "holy boldness and brazenness in serving God",
            "faith and trust in the creator",
            "being able to accept criticism and moral rebuke from teachers"]),
        ("fasting/eating chain (I:47 territory)", [
            "fasting and afflicting the body",
            "breaking and subduing the craving to eat",
            "the divine attribute of truth",
            "being rescued from poverty and destitution"]),
    ]
    for i, (label, stages) in enumerate(tests):
        print("=" * 78); print("TEST:", label)
        show(stages, project(stages)); print()

# ============ concept-INPUT projection (Shmuel's clarification) ============
# The user picks concepts X,Y,Z (not free text). We map that sequence onto a parallel causal
# chain A->B->C: each Ai is PARALLEL to Xi (Ai==Xi, or a bechina-aspect of Xi, or gloss-akin),
# and A->B->C are causally (eitza) linked, ideally all inside one Torah.
bech = collections.defaultdict(set)
for e in EDGES:
    if e["ty"] == "bechina":
        bech[e["s"]].add(e["t"]); bech[e["t"]].add(e["s"])

def gloss_sim(x, a):
    q = collections.Counter(toks((byId[x].get("gloss") or "") + " " + (byId[x].get("he") or "")))
    return score_one(q, a)

def parallels(x, pool, topn=6):
    scored = []
    for a in pool:
        s = 0.0
        if a == x: s += 5.0
        if a in bech[x]: s += 2.0
        s += 0.5 * gloss_sim(x, a)
        if s > 0: scored.append((a, s))
    scored.sort(key=lambda z: -z[1])
    return scored[:topn]

def project_concepts(concept_ids, home_try=16):
    cover = collections.Counter()
    for x in concept_ids:
        cands = set(byId[x].get("refs", []))
        for nb in bech[x]:
            cands |= set(byId[nb].get("refs", []))
        for r in cands: cover[r] += 1
    homes = [r for r, c in cover.most_common(home_try) if c >= 2]
    best = None
    for home in homes:
        pool = concepts_in.get(home, [])
        if not pool: continue
        candk = [parallels(x, pool, 6) for x in concept_ids]
        if any(not c for c in candk): continue
        maxs = max(sc for c in candk for _, sc in c) or 1
        semc = [{cid: (1 - sc / maxs) for cid, sc in c} for c in candk]
        loc = [None]
        def dfs(i, used, chain, links, cost):
            if loc[0] and cost >= loc[0]["cost"]: return
            if i == len(concept_ids):
                loc[0] = {"cost": cost, "home": home, "chain": chain[:], "links": links[:]}; return
            for cid, _ in candk[i]:
                if cid in used: continue
                if i == 0: dfs(1, used | {cid}, [cid], [], semc[0][cid])
                else:
                    pc, nodes = causal_path(chain[-1], cid, home, strict=home)
                    if pc is None: continue
                    dfs(i+1, used | {cid}, chain+[cid], links+[(pc, nodes)], cost+semc[i][cid]+pc)
        dfs(0, set(), [], [], 0.0)
        if loc[0] and (best is None or loc[0]["cost"] < best["cost"]): best = loc[0]
    return best

def find(he):
    for n in NODES:
        if n["he"] == he: return n["id"]
    for n in NODES:
        if he in (n["he"] or ""): return n["id"]
    return None

if __name__ == "__main__":
    print("\n\n########## CONCEPT-INPUT PROJECTION ##########")
    # pick the exact I:7 concepts as X,Y,Z,W -> should recover the chain trivially
    for label, hes in [
        ("exact I:7 concepts: Joseph, Truth, Faith, Redemption", ["יוסף","אמת","אמונה","גאולה"]),
        ("user example: prayer, faith, redemption", ["תפלה","אמונה","גאולה"]),
        ("fasting, truth, poverty", ["תענית","אמת","נצולין מדלות ועניות"]),
    ]:
        ids = [find(h) for h in hes]
        print("=" * 70); print("PICKED:", " → ".join(f"{h}({i})" for h, i in zip(hes, ids)))
        if any(x is None for x in ids): print("  (a concept not found)"); continue
        r = project_concepts(ids)
        if not r: print("  no projection"); continue
        print(f"  home LM {r['home']}, weight {r['cost']:.2f}")
        for k, cid in enumerate(r["chain"]):
            print(f"    X{k+1}={byId[ids[k]]['he']}  →  A{k+1}={byId[cid]['he']}")
            if k < len(r["links"]): print("        causes:", " → ".join(byId[x]["he"] for x in r["links"][k][1]))
