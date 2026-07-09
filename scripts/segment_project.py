#!/usr/bin/env python3
"""segment_project — split a long causal sequence into contiguous, single-teaching
projections, and resolve unknown ("?") slots at the ends of a chain.

`tmap.py project` maps a 2-6 concept chain onto the single Torah (teaching) that
fits it best, paying a real but small cost for any hop it must take outside that
teaching. It does not, by itself, decide to CUT a longer sequence into several
teaching-local pieces — that's what this module adds, as a thin layer on top of
tmap's Graph/project (no changes to tmap.py itself).

Algorithm (`segment_chain`): standard DP over cut points. Every candidate segment
[i,j) with 2 <= j-i <= 6 (project()'s own arity limit) is priced by calling
tmap's project() on ids[i:j]; splitting into segment k+1 after segment k adds a
flat BRIDGE_PENALTY (a knob — default 2.5, a bit above the observed cross-teaching
hop cost of ~1.6-2.0, so splitting only wins when it materially tightens the fit
in each half). dp[j] = min cost to cover ids[0:j]; backpointers reconstruct the
chosen cut points. This always considers "no split at all" (i=0..n if n<=6) as
one of its candidates, so segmentation never does worse than a single project()
call unless splitting is genuinely cheaper.

Unknown-slot resolution (`resolve_unknown`): once a segment's home teaching is
known, an unresolved end of the user's chain ("? -> X" or "X -> ?") is filled by
querying tmap's own attested edges — advice (eitza_in) for a missing prior cause,
effects (eitza_out) for a missing next effect — ranked with in-home matches
first. This never invents a connection; it only surfaces what the graph already
attests near that anchor, same discipline as tmap.py's `diagnose`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tmap  # noqa: E402

DEFAULT_BRIDGE_PENALTY = 2.5
MIN_SEG, MAX_SEG = 2, 6


def _segment_cost(g, ids, cache):
    key = tuple(ids)
    if key in cache:
        return cache[key]
    res = tmap.project(g, list(ids), k=1)
    cache[key] = res
    return res


def segment_chain(g, ids, bridge_penalty=DEFAULT_BRIDGE_PENALTY):
    """DP-segment `ids` (an ordered concept-id sequence, len >= 2) into
    contiguous 2-6-length pieces, each independently projected, minimizing
    total (sum of segment project costs) + bridge_penalty * (num_segments - 1).
    Returns {"segments": [...], "bridges": [...], "total_cost": float} or
    raises TmapError if no valid segmentation exists (e.g. a stretch of >6
    ids none of whose 2-6 sub-windows is projectable)."""
    n = len(ids)
    if n < 2:
        raise tmap.TmapError("segment_chain requires >=2 concept ids")

    cache = {}
    INF = float("inf")
    dp = [INF] * (n + 1)
    dp[0] = 0.0
    back = [None] * (n + 1)  # back[j] = (i, project_result)

    for j in range(1, n + 1):
        for length in range(MIN_SEG, MAX_SEG + 1):
            i = j - length
            if i < 0 or dp[i] == INF:
                continue
            res = _segment_cost(g, ids[i:j], cache)
            if res is None:
                continue
            if i == 0:
                bridge = 0.0
            else:
                prev_home = back[i][1]["home"] if back[i] else None
                # a split forced purely by project()'s 2-6 arity cap, where both
                # halves land in the SAME teaching anyway, isn't a real cross-teaching
                # jump — only charge the bridge penalty when the homes actually differ.
                bridge = 0.0 if prev_home == res["home"] else bridge_penalty
            cand = dp[i] + res["cost"] + bridge
            if cand < dp[j]:
                dp[j] = cand
                back[j] = (i, res)

    if dp[n] == INF:
        raise tmap.TmapError(
            f"no valid segmentation found for {n} concepts (no 2-6-length window projects)"
        )

    # reconstruct
    cuts = []
    j = n
    while j > 0:
        i, res = back[j]
        cuts.append((i, j, res))
        j = i
    cuts.reverse()

    segments = []
    for idx, (i, j, res) in enumerate(cuts):
        segments.append({
            "segment_index": idx,
            "slots": list(range(i, j)),
            "ids": list(ids[i:j]),
            "project": tmap._project_result_json(g, res),
        })

    bridges = []
    for k in range(len(segments) - 1):
        a_seg, b_seg = segments[k], segments[k + 1]
        a_last, b_first = a_seg["ids"][-1], b_seg["ids"][0]
        same_home = a_seg["project"]["home"] == b_seg["project"]["home"]
        bridges.append({
            "from_segment": k, "to_segment": k + 1,
            "from_id": a_last, "to_id": b_first,
            "penalty": 0.0 if same_home else bridge_penalty,
            "note": (
                f"both halves land in LM {a_seg['project']['home']} — split only by the "
                "2-6 concept limit on a single projection call, not a real teaching change"
                if same_home else
                f"segment {k} closes in LM {a_seg['project']['home']}, "
                f"segment {k + 1} opens a new teaching (LM {b_seg['project']['home']}) "
                "— a real jump between teachings, not a graph-attested hop"
            ),
        })

    return {"segments": segments, "bridges": bridges, "total_cost": dp[n]}


def resolve_unknown(g, home, anchor_id, direction, topn=5):
    """Fill a '?' slot adjacent to `anchor_id` inside teaching `home`.
    direction: "prior" (what could cause anchor_id — eitza_in) or
               "next" (what anchor_id leads to — eitza_out).
    Ranks in-home candidates first (cost 0), then out-of-home (flagged),
    never inventing an edge the graph doesn't attest."""
    tmap.require_node(g, anchor_id)
    ty_dir = ("eitza", "in") if direction == "prior" else ("eitza", "out")
    rows = tmap.rows_for(g, anchor_id, *ty_dir)
    for r in rows:
        r["in_home"] = bool(home) and home in (r.get("ref") or [])
    rows.sort(key=lambda r: (not r["in_home"]))
    return {
        "ok": True, "anchor": anchor_id, "home": home, "direction": direction,
        "candidates": rows[:topn],
        "note": "ranked in-home first; these are attested eitza edges near the anchor, not invented",
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def main(argv=None):
    p = argparse.ArgumentParser(prog="segment_project")
    p.add_argument("--data", default=None)
    p.add_argument("--pretty", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("segment", help="segment a long chain into contiguous single-teaching projections")
    sp.add_argument("ids", nargs="+")
    sp.add_argument("--bridge-penalty", type=float, default=DEFAULT_BRIDGE_PENALTY)

    sp = sub.add_parser("resolve", help="resolve an unknown ('?') slot adjacent to an anchor")
    sp.add_argument("home", help="teaching ref the segment landed in, e.g. I:22 (or 'none')")
    sp.add_argument("anchor_id")
    sp.add_argument("direction", choices=["prior", "next"])
    sp.add_argument("-n", type=int, default=5)

    args = p.parse_args(argv)
    indent = 2 if args.pretty else None
    g = tmap.load_data(args.data)

    try:
        if args.command == "segment":
            out = segment_chain(g, args.ids, bridge_penalty=args.bridge_penalty)
        else:
            home = None if args.home.lower() == "none" else args.home
            out = resolve_unknown(g, home, args.anchor_id, args.direction, topn=args.n)
    except tmap.TmapError as ex:
        print(json.dumps({"ok": False, "error": str(ex)}, ensure_ascii=False, indent=indent))
        return 1

    print(json.dumps(out, ensure_ascii=False, indent=indent))
    return 0


if __name__ == "__main__":
    sys.exit(main())
