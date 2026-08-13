# GOAL: Merge all 3,880 v2-extracted edge chunks into the Torah Map graph (polarity/via as first-class data), rebuild the explorer + tmap layer, and prove it with the test suite and headless harness.

**Model fit: this NEEDS Fable** for the merge semantics, dedup/conflict decisions, and query-layer design — precision graph work where subtle mistakes silently corrupt the map. The bulk mechanics (running batch scripts, re-running eval batteries) are plain Python and cheap; no need to delegate LLM work, but use Sonnet subagents if you spawn any bulk verification/writing agents.

## Context (verified 2026-07-09)

- The extraction daemon FINISHED: all **3,880** chunk files sit in `ontology/occurrences/ai_extracted/` (daemon done + disarmed 2026-07-05; STOP flag present — leave it, the daemon is intentionally dead).
- The current graph is STALE relative to that: `ontology/graph/edges.json` (3,939 edges) was last built **2026-07-03**, and `scripts/compile_graph.py` contains **no reference to `ai_extracted` or `polarity`** — so the v2 merge has NOT happened. That is this session's job.
- Schema v2 spec: `specs/extraction_v2.md` — every edge carries `polarity: builds|harms|neutral` and `via: presence|absence` (this makes the "bad flow" / פגם statements first-class attested edges). The **157 v1-era chunks default to `builds`/`presence` at merge time**.
- Query layer: `scripts/tmap.py` (stdlib CLI: search/match/concept/aspects/advice/effects/path/common/torah/project/diagnose/selftest), spec `specs/api_v1.md`, tests `scripts/test_tmap.py` (currently green — must stay green). Claude skill at `.claude/skills/torah-map/`.
- Explorer: `ontology/graph/explorer.html`, served by `scripts/serve_explorer.sh` (port 8890, sends `Cache-Control: no-store`). Its flagship "Project chain" mode consumes `explorer_data.json` built by `scripts/build_explorer_data.py`.

## Task order

1. **Understand the merge surface.** Read `specs/extraction_v2.md`, one or two `ai_extracted/*.json` chunks, and `compile_graph.py`. Decide the dedup/merge policy: same (source,target,type) edges accumulate weight + proof occurrences; polarity/via conflicts on the same edge must be RESOLVED explicitly (e.g. keep separate edges per polarity, or record both with proofs) — write the chosen policy into the spec or a MERGE_POLICY note before coding it.
2. **Upgrade `compile_graph.py`** (or add a merge step) to fold in all 3,880 chunks + legacy edges, emitting polarity/via on every edge (v1 chunks → builds/presence). Only ATTESTED edges are stored — **never store inferred edges** (the `diagnose` command infers at query time; that stays query-time).
3. **Rebuild everything downstream:** graph JSONs, `explorer_data.json`, stats.
4. **Update `tmap.py`** minimally: it must not break, `selftest` must pass, and at minimum expose polarity in output where edges are shown; a `--polarity` filter on advice/effects/path is the natural small addition (spec it in `specs/api_v1.md` if added).
5. **Verify (mandatory, in this order):**
   - `python3 scripts/test_tmap.py` green + `tmap selftest` passes.
   - Report before/after: node count, edge count, polarity distribution (builds/harms/neutral), via distribution, how many chunks contributed 0 edges.
   - Spot-check 5 known harms/absence edges from raw chunks and confirm they surface correctly via `tmap` queries.
   - Explorer: serve it, load with a **cache-buster `?t=N`** (browser cache previously cost hours; check `typeof aspectDist==='function'` to confirm fresh code), and run the **headless in-page projection harness** over many sample pick-sets (assert result exists, every stage maps non-silently, chain distinct, every referenced node placed) — not one eyeballed example.
   - Verify every chain you present with `tmap chain` — "no chain found" is a real answer; never splice steps the map doesn't attest.

## Hard rules

- The map holds exactly TWO relations: `eitza` (cause→effect) and `bechina` (parallels). Don't invent relation types during merge.
- Gloss-similarity remains a flagged last-resort fallback in projection — don't let merged data change that hierarchy.
- Commit in logical steps with clear messages. If the merge policy raises a real design fork (e.g. how to store conflicting polarity attestations for the same edge pair), present the options to Shmuel with a recommendation rather than guessing.

## Definition of done

- [ ] All 3,880 chunks merged; counts + polarity distribution reported.
- [ ] test_tmap.py + selftest green; explorer harness passes on fresh (cache-busted) code.
- [ ] Docs updated: `specs/api_v1.md` (if tmap changed) and a dated MERGE note recording the policy and the numbers.
- [ ] Tell Shmuel to hard-reload the explorer once (Ctrl+Shift+R).
