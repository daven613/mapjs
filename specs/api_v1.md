# Torah Map API v1 — `tmap` CLI (spec)

## Problem
The concept graph (Likutey Moharan: 4,215 nodes / 3,939 typed edges) is only queryable
through a browser GUI. An AI assistant (Claude skill) needs programmatic access: search,
cause-effect traversal, and structural projection — all returning JSON with proof quotes,
so the AI can interpret a user's story/question against the text and cite sources.

## Deliverables
1. `scripts/tmap.py` — stdlib-only Python 3 CLI (argparse; no third-party deps). Executable.
2. `scripts/test_tmap.py` — pytest suite (also runnable as `python3 test_tmap.py`).
3. `tmap.py selftest` — built-in invariant suite, exit 0/1 (usable without pytest).

## Data
Loads `ontology/graph/explorer_data.json` (resolve relative to the script:
`Path(__file__).resolve().parent.parent / "ontology/graph/explorer_data.json"`,
overridable with `--data PATH`).

Shape: `{nodes:[{id,he,gloss,kind,deg,refs}], edges:[{s,t,ty,w,p,ref}], torahs:[...]}`.
`ty ∈ {bechina, eitza, equation}`. `eitza` is DIRECTED cause→effect (s causes t);
`bechina` (aspect) is undirected in meaning. `p` = proof quote (Hebrew). `ref` =
list of teaching refs like `"I:22"`. `refs` on a node = teachings it appears in.

Build once at startup:
- `by_id`, and `adj[id] = {all:[(other,ty,dir,edge)], bechina:[ids], eitza_out:[ids], eitza_in:[ids]}`
  (dir = 'out' if id==e.s else 'in'; both directions get an `all` entry).
- `concepts_in[ref] = [node ids with ref in node.refs]`.
- Token index: `tokens(s) = re.findall(r"[a-z]{3,}|[א-ת]{2,}", (s or "").lower())`.
  For each node: `tokx[id]` = set(tokens(gloss)+tokens(he)); `ctxx[id]` = tokens of all
  proof strings on edges touching the node, minus tokx. `df[w]` counts nodes containing w
  (in tokx or ctxx); `idf[w] = ln(N_nodes/df[w])`.

## Algorithms (port EXACTLY from `ontology/graph/explorer.html`, the canonical source)

### score_one(q, cid)   — explorer.html `scoreOne` (~line 163)
q = dict token→count. `wt = idf.get(w,0.5) * (1+ln(q[w]))`; add wt if w in tokx[cid],
else 0.35*wt if in ctxx[cid]. Divide total by `1 + ln(1+deg)*0.15`.

### match(text, topn, pool=None) — `matchList` (~169)
Token-count the text; score all non-statement nodes (or pool); return [(cid,score)] desc, >0 only.

### search(query, topn) — autocomplete ranking (`wireAc`, ~247)
q lowercased. Per non-statement node: he==q→100; he.startswith(q)→82; q in he→64;
gloss.startswith(q)→54; regex word-boundary match in gloss→42; q in gloss→22; else skip.
Plus `min(15, deg/40)` tiebreak. Sort desc, top n.

### hop_cost(e, home) — (~306)
`0.12` if home in e.ref else (1.6 if ty=='eitza' else 2.0).

### causal_path(a, b, home, strict) — (~309)
Dijkstra over states (node, caused∈{0,1}); start (a,0). Neighbors from adj[node].all:
skip eitza with dir!='out' (forward-only); if strict, skip edges whose ref doesn't
contain strict. kind='cause' if eitza else 'reframe'; new caused = 1 if (caused or cause);
hc = hop_cost(e,home) + (0.15 if reframe). Accept b only with caused==1.
Return (cost, node_list, hops) where hop = {from,to,kind,hc,edge}; (None,None,None) if none.
a==b → (0,[a],[]). Guard ~40k pops.

### aspect_dist(x) — (~371)
Dijkstra (uniform weight 1) over bechina edges only → dict id→hop count.

### aspect_path(a, b, home) — (~335)
Dijkstra over bechina edges, weight 0.12 if home in e.ref else 1.2.
Return list of hops {from,to,edge}, [] if a==b, None if unreachable.

### shared_terms(x, a, topn=8)
tokx[x] ∩ tokx[a], len(w)>1, ranked by idf desc → list of terms.

### gloss_sim(x, a) / parallels(x, pool, topn=6) — (~333)
gloss_sim: token counts of (x.gloss+' '+x.he) scored via score_one against a.
parallels score: +5 if a==x; +2 if a in adj[x].bechina; +0.5*gloss_sim. Keep >0, top n.

### project(concept_ids) — (~386, the aspect-reachable version)
1. dists = [aspect_dist(x) for x in picks].
2. cover[ref] += 1 for each ref of every concept with dist<=6 per pick (count picks covering ref once each).
3. homes = refs with cover >= min(2, len(picks)), sorted by cover desc, top 24.
4. Per home: pool=concepts_in[home]; candidates per pick =
   `[(a, 0 if a==x else 0.2*d[a]) for a in pool if d.get(a,99)<=6]`;
   if empty → fallback `[(a, 1.2+0.1*k) for k,(a,_) in enumerate(parallels(x,pool,4))]`;
   sort by cost, keep 6.
5. DFS over stages choosing DISTINCT anchors; stage 0 cost=pcost; later stages add
   causal_path(prev_anchor, cid, home, strict=home) — skip if None; prune when
   running cost >= best-so-far. Track (cost, home, chain, links, pcosts);
   links[i] = {cost, nodes, hops}.
6. Best across homes. If none: cross-Torah fallback — chain=picks,
   links via causal_path(a,b,home=None,strict=None) with +2 penalty each; None if any link missing.
7. Enrich result per stage i: mapping = {pick, anchor, pcost, kind, hops, shared_terms}
   where kind = 'self' if pick==anchor else ('aspect' if aspect_path(pick,anchor,home) non-empty
   else 'shared'); hops = that aspect_path (with edge proofs); shared_terms only when kind='shared'.

## CLI

`tmap.py <command> [args] [--data PATH] [--pretty] [-n N]`
All output JSON on stdout (dict with a top-level `"ok": true/false`). Errors →
`{"ok":false,"error":"..."}` + exit 1. `--pretty` = indent 2, ensure_ascii=False (always ensure_ascii=False).

- `search QUERY [-n 10]` → `{ok, results:[{id,he,gloss,kind,deg,refs,score}]}`
- `concept ID` → node fields + `{aspects:[...], causes:[...], effects:[...]}` each
  `[{id,he,gloss,proof,ref}]` (proof = edge.p, ref = edge.ref)
- `aspects ID` / `advice ID` (eitza_in: what leads TO it) / `effects ID` (eitza_out) → same row shape
- `path A B` → weighted shortest path, cost 1/max(1,e.w), ANY edge type, undirected —
  port of `runPath` (~444): `{ok, steps:[{from,to,ty,proof,ref}], length}`
- `common A B` → `{ok, shared:[{id,he,gloss,via_a:{ty,proof}, via_b:{ty,proof}}]}`
- `torah REF` → `{ok, ref, concepts:[...], edges:[{s,t,ty,proof}]}` (edges whose ref includes REF)
- `match TEXT [-n 10]` → `{ok, results:[{id,he,gloss,score}]}` (free text → closest concepts)
- `project ID ID [ID...]` → `{ok, cost, home, chain:[{id,he,gloss}],
   mappings:[{pick,anchor,kind,pcost,hops:[{from,to,proof,ref}],shared_terms}],
   links:[{cost, hops:[{from,to,kind,hc,proof,ref}]}]}`
  (2–6 ids; validate all exist)
- `selftest` → run invariants below, print report JSON, exit 0/1.

## Acceptance criteria (each mechanically checked by tests + selftest)
- AC1 load: 4215 nodes, 3939 edges parse; adj symmetric (every edge appears in both endpoints' `all`).
- AC2 search("joy") top-3 contains `c:simchah`; search("אמונה") top-1 he == "ארץ ישראל" or id startswith c:emunah.
- AC3 project(["c:tefillah-2","c:simchah","c:emet"]) → ok, home=="I:22", chain distinct,
  every mapping kind ∈ {self,aspect,shared} and (kind=='aspect' → hops non-empty),
  every link has ≥1 hop with kind=='cause', and when home set every hop's ref contains home.
- AC4 project on ≥3 other varied triples (e.g. ta'anit/emunah/divine; mamon/mitzvah-charity/simchah;
  teshuvah-ish ids found via search) → ok, same structural invariants; each call < 5s.
- AC5 causal_path forward-only: no returned causal hop traverses an eitza edge backwards
  (hop.from must equal edge.s when kind=='cause').
- AC6 path/common/torah/match/concept each return ok on known-good inputs; unknown id →
  ok:false, exit 1, helpful message.
- AC7 every proof field is a string (possibly empty) — never null crashes; JSON is valid UTF-8 Hebrew.

## Test plan
- `test_tmap.py`: import tmap as a module (expose functions, don't only hide in __main__);
  unit-test tokens/score_one/hop_cost/causal_path/aspect_path on tiny synthetic graphs
  + the ACs above against the real data file (skip gracefully if data missing).
- `selftest` command: ACs 1–5 against real data, timing included.

## Out of scope (v1)
HTTP server, MCP server, GUI changes, write operations, sub-paragraph anchoring.

---

# v1.1 addendum — `diagnose` (inferred deficiency analysis)

## Problem
The graph attests the GOOD flow (X strengthens Y). Users ask about lacks/afflictions
("pain in the kidneys"). Derive candidate deficiencies at QUERY TIME by inverting attested
advice edges and walking near aspects — never storing inferred edges, always labeling them.

## Command
`diagnose ID [--depth 2] [-n 12]`   (depth = max aspect-distance to walk, 1..3, default 2)

## Algorithm
1. Validate ID. `contexts` = [(ID, dist=0, path=[])] + every concept within aspect-distance
   <= depth of ID (via `aspect_dist`), each with its connecting aspect-hop path
   (via `aspect_path(ID, c, home=None)`, hops carry proofs). Sort by dist asc, cap at n.
2. For each context concept c: attested helpers = eitza_in edges of c (what leads TO c),
   each {helper_id, he, gloss, proof, ref}.
3. Inferred deficiencies: for every (helper h → context c), emit
   {lack_of: h, weakens: c, dist, status: "inferred",
    derivation: [aspect hops ID..c with proofs] + [attested eitza h→c with proof],
    basis: "inversion of attested eitza"}.
   Rank by (dist asc, edge weight desc). NEVER emit a deficiency without an underlying
   attested eitza edge — the inversion may not fabricate connectivity.
4. Output:
   {ok, concept:{id,he,gloss,refs},
    contexts:[{id,he,gloss,dist,path:[{from,to,proof,ref}]}],
    attested_helpers:[{of,helper,he,gloss,proof,ref}],
    inferred_deficiencies:[{lack_of,he,gloss,weakens,dist,derivation:[...],status}],
    note: "inferred items are query-time inversions of attested builds-edges, not text"}

## Acceptance criteria
- AD1 `diagnose c:trust` (kidneys): contexts include c:bitachon-trust-reliance at dist 1
  with the I:60 proof; attested_helpers include c:seichel (of bitachon, I:225);
  inferred_deficiencies include lack_of c:seichel with a 2-step derivation, status "inferred".
- AD2 Every inferred_deficiency's derivation ends in a real eitza edge present in the data
  (verifiable s->t match); no deficiency exists without one.
- AD3 depth respected: with --depth 1 no context has dist>1. Unknown id -> ok:false, exit 1.
- AD4 synthetic-graph unit test: inversion emits exactly the eitza_in set, nothing more.
- AD5 every proof is a string; output valid UTF-8 Hebrew; runs < 5s on real data.

---

# v1.2 addendum — top-K alternatives (`-k`)

## Problem
`path` and `project` return only the optimum. Questions have many valid answers; the
runner-ups are often as illuminating (different teachings = different readings).

## Spec
- `path A B [-k 5]`: Yen-style k-shortest LOOPLESS paths over the same weighting
  (1/max(1,w), any edge type). Output keeps `steps` (= best path, backward compatible)
  and adds `alternatives: [{cost, steps:[...]}]` (k entries incl. the best, cost asc,
  no duplicate node-sequences). k=1 default → alternatives has 1 entry.
- `project ID... [-k 3]`: the home-search already scores per-home optima; return
  `alternatives: [{cost, home, chain, mappings, links}]` = top-k DISTINCT homes by cost
  (full enriched structure each). Primary fields stay as today (= alternatives[0]).
- `diagnose`/`advice`/`effects`/etc. already return lists — unchanged.

## Acceptance criteria
- AK1 path A B -k 3 on a known multi-path pair returns ≤3 distinct paths, costs
  non-decreasing, first == old behavior.
- AK2 project with -k 3 returns ≤3 alternatives with distinct homes, costs non-decreasing,
  alternatives[0] identical to the primary result; every alternative passes the same
  structural invariants as AC3 (distinct chain, ≥1 cause hop per link, home-restricted).
- AK3 default k=1 keeps all existing outputs byte-compatible (old tests untouched, green).
- AK4 all existing tests still pass.

---

# v1.3 addendum — `why` (typed causal query) and `chain` (verifier)

## Problem
Temporal/order/why questions ("why does X come before Y", "what does X lead to")
are CAUSAL queries: X —(bechina*)→ —(eitza+)→ —(bechina*)→ Y. The engine exists
(causal_path, used inside project) but is not exposed; the `path` command (undirected,
type-blind) is the wrong tool and invites narration over data. Also: chains presented
to the user must be mechanically verifiable — no unattested junctions.

## `why A B [-k 3]`
Runs causal_path(A, B, home=None, strict=None). Output:
{ok, chains:[{cost, hops:[{from,to,he_from,he_to,kind:"cause"|"reframe",hc,proof,ref}]}]}
- chains sorted by cost asc, up to k, distinct hop-sequences (k>1 via edge-penalty reruns
  or Yen on the (node,caused) state graph — implementer's choice, must be exact for k=1).
- No chain → {ok:true, chains:[]} (NOT an error: "the map cannot attest this" is an answer).

## `chain ID ID ID...` (≥2 ids)
For each adjacent pair report the best attesting edge or its absence:
{ok, complete:bool, junctions:[{from,to,attested:bool,ty,direction:"forward"|"reverse"|"undirected",proof,ref}]}
- eitza counts forward only (from==edge.s); bechina/equation are undirected.
- complete = every junction attested. Unknown id → ok:false exit 1.

## Acceptance criteria
- AW1 why c:head-year c:phylacteries → 1 chain, 2 cause-hops (תקון המחין middle), proofs present.
- AW2 why c:head-year c:day-atonement → ok:true, chains:[] on current data
  (regression: after the v2 merge heals II:5, flip this test to expect ≥1 chain).
- AW3 chain c:head-year c:sleep c:phylacteries → complete:true, both junctions forward eitza.
- AW4 chain c:head-year c:day-atonement → complete:false, junction attested:false.
- AW5 all existing tests stay green; -k respects distinctness + non-decreasing cost.

---

# v1.4 addendum — packets, loose mode, set-endpoints, pattern notation

## Concepts
A **packet** = within ONE torah ref, a connected component of that torah's bechina+equation
edges. Rebbe Nachman chains identifications within a teaching; hop-count inside a torah is
sentence-order, not distance. Packets are pure query-time closure of attested edges — no new data.
A **user packet entry** = Shmuel's own understanding: {torah, members:[concept ids], note, by, date}
in ontology/packets/user_packets.jsonl (created if absent). Separate evidence class, never silent.

## Commands / changes
1. `packets REF` → {ok, ref, packets:[[{id,he}...]]} (components sorted by size desc).
   `packets --of ID` → every (torah, packet) containing ID.
2. `packet add REF ID [ID...] --note "..."` → append a user-packet entry (merges into the
   torah's packet universe only in loose=all mode). `packet list` → dump user entries.
3. `why A B [--loose | --loose=all] [-k]`:
   - strict (default): current behavior.
   - --loose: traversal cost model changes — bechina hop whose edge shares a torah with an
     adjacent bechina hop in the walk: 0.15; other bechina: 0.9; eitza: 1.0. (Approximates
     packet-contraction while keeping per-edge derivations printable.)
   - --loose=all: additionally, user-packet co-membership acts as a zero-proof bechina edge
     with cost 0.3, kind "user-packet"; output hop carries {kind:"user-packet", by, note} —
     ALWAYS visibly labeled.
4. Set endpoints: `why --from REGEX --to REGEX` (and positional ids still fine). Expand each
   regex over he+gloss (case-insensitive) to a node set (cap 40, warn if more); virtual
   source/target connected at cost 0; result reports WHICH concrete endpoints matched.
   Same for `project` stage inputs: a stage may be `re:PATTERN`.
5. Pattern documentation: every search command's --help gains a PATTERN line in the notation
   (A) -[bechina*0..N]- (X) -[eitza+]-> (Y) -[bechina*0..N]- (B); `--pre N --post N` bound
   the parallel runs on each side of why (default unlimited).

## Acceptance
- AP1 packets I:1 includes a component containing both מלכות and חן nodes (c:chokhmah-tata'ah, c:chen-2 or equiv).
- AP2 why --from 'ראש השנה' --to 'חותם' (loose) finds ≥1 chain on CURRENT data (the gmar-node
  route via II:5 eitza fragments is reachable when the target set includes the gmar node);
  if genuinely none, the test asserts the empty result and documents why.
- AP3 packet add + why --loose=all: adding user packet (II:8: c:head-year + a malchut node)
  changes the RH→c:sekhel-2 result to include a hop labeled kind:"user-packet"; removing the
  file restores prior behavior. Tests must clean up the file.
- AP4 strict mode outputs byte-identical to v1.3 (all existing tests green).
- AP5 --from expansion caps at 40 nodes and reports matched endpoint counts.

## v1.5 addendum — polarity/via as first-class edge data (2026-07-09 v2 merge)

Data: the 2026-07-09 merge (specs/MERGE_POLICY.md) folded the 3,880 `ai_extracted/`
chunks into the graph. New bundle shape: every edge additionally carries
`pol ∈ {builds, harms, neutral}` and `via ∈ {presence, absence}`; edges aggregate by
(s,t,ty,pol,via), so the same concept pair may carry parallel edges of different
polarity, each with its own proofs. Counts: 9,018 nodes (3,588 concepts, 627 legacy
statements, 4,803 AI phrase-statements — `kind:"statement"`, excluded from search/match
pools as before) / 12,328 edges. bechina/equation edges are always neutral/presence.

Surface changes (all additive):
1. Every JSON shape that shows an edge (concept/aspects/advice/effects rows, path steps,
   why/chain/project hops, chain junctions) gains `polarity` and `via` fields.
2. `advice ID [--polarity builds|harms|neutral|all]` — DEFAULT `builds`: advice means
   counsel to attain the concept; pre-merge data was all-builds, so the default
   reproduces pre-merge results exactly. `--polarity harms` answers the new question
   "what does the text say DAMAGES this?" (incl. via=absence פגם edges). Output carries
   `polarity_filter` echoing the filter applied.
3. `effects ID [--polarity ...]` — DEFAULT `all` (effects means everything the concept
   leads to, good and bad; rows are labeled).
4. `path A B [--polarity builds|harms|all]` — DEFAULT `all`; the filter restricts
   traversed eitza edges to one polarity; neutral aspect edges always pass.
5. `diagnose`: query-time inversion now inverts ONLY builds-edges (inverting "Z damages
   c" into "lack of Z weakens c" would assert the opposite of the text). Attested
   harms/absence edges surface directly through `advice --polarity harms` instead.
6. `why`/`chain`/`project`: traversal unchanged (mixed polarity permitted); every hop is
   labeled, so a chain crossing a harms edge is visible as such.

Acceptance:
- AV1: `advice c:simchah` returns only polarity=builds rows; `advice X --polarity harms`
  returns only harms rows, each with a verbatim proof.
- AV2: selftest AC1 counts = 9,018 / 12,328; whole suite green on merged data.
- AV3: a known harms/absence edge from a raw chunk (e.g. פגם statements) is queryable via
  advice --polarity harms / effects, with matching proof text.
