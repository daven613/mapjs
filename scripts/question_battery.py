#!/usr/bin/env python3
"""Natural-English question battery for the tmap CLI.

Two parts:
  A. Everyday questions a person would actually ask (advice/effects/why/common).
  B. "Showcase" questions — multi-hop causal chains, projection, and diagnosis
     that no keyword search engine could answer.

HISTORY OF THE POLARITY RULE: pre-merge (2026-07-05, per Shmuel) this graph
was a GOOD map only — the human evidence layer traced good-building-on-good,
and the "bad map" (anger/sadness's own cascades) was a separate future layer.
The 2026-07-09 v2 merge (specs/MERGE_POLICY.md) landed that layer INTO this
graph as labeled edges: every eitza edge now carries polarity (builds|harms)
and via (presence|absence), so the bad flow is first-class and attested.
Consequence for the cases below: remedial questions still ask "what leads to
<the good thing>" (advice defaults to builds), but "what does <the bad
thing> cause" is now a REAL query — check the polarity labels on every hop.

Each case notes its EXPECTED outcome as of 2026-07-09 (post-merge). A5
flipped to found, per its pre-merge GAP note. A6 flipped from OUT OF SCOPE
to found: anger's own cascade is now attested with harms labels.

Run:  python3 scripts/question_battery.py
"""
import json, subprocess
from pathlib import Path

TMAP = ["python3", str(Path(__file__).resolve().parent / "tmap.py")]


def run(*args):
    r = subprocess.run(TMAP + list(args), capture_output=True, text=True, timeout=60)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {"raw": r.stdout[:500], "err": r.stderr[:300]}


def show_chain(ch):
    hops = ch.get("hops", [])
    if not hops:
        return "  (no hops)"
    parts = [hops[0].get("he_from", "?")]
    refs = []
    for h in hops:
        arrow = {"cause": "⟶", "aspect": "≈", "equation": "≡"}.get(h.get("kind"), "—")
        parts.append(f" {arrow} {h.get('he_to', '?')}")
        refs.append(",".join(h.get("ref", [])) or "?")
    return f"  cost {ch.get('cost')}: " + "".join(parts) + f"   [refs: {' | '.join(refs)}]"


def why(q, *args, expect_chain=True):
    print(f"\n### {q}")
    d = run("why", *args)
    ok = bool(d.get("ok") and d.get("chains"))
    if not ok:
        tag = "GAP (expected pre-merge)" if not expect_chain else "FAIL"
        print(f"  NO CHAIN FOUND — {tag}")
        return ok == expect_chain
    for ch in d["chains"][:3]:
        print(show_chain(ch))
    return ok == expect_chain


def listy(q, cmd, cid, expect_nonempty=True, tag="GAP (expected pre-merge)"):
    print(f"\n### {q}")
    d = run(cmd, cid)
    rows = d.get("results", []) if isinstance(d, dict) else d
    if not rows and isinstance(d, dict):
        rows = next((v for v in d.values() if isinstance(v, list) and v), [])
    for r in rows[:8]:
        if isinstance(r, dict):
            ref = ",".join(r.get("ref", [])) if isinstance(r.get("ref"), list) else r.get("ref", "")
            print(f"  {r.get('he', r.get('id', '?'))}  ({ref})  {(r.get('gloss') or '')[:80]}")
    if not rows:
        print(f"  (empty) — {tag if not expect_nonempty else 'FAIL'}")
    return bool(rows) == expect_nonempty


def generic(q, *args, expect_ok=True):
    print(f"\n### {q}")
    d = run(*args)
    print(json.dumps(d, ensure_ascii=False, indent=1)[:1500])
    ok = bool(d.get("ok")) if isinstance(d, dict) else False
    return ok == expect_ok


results = []

print("=" * 70)
print("PART A — everyday questions")
results.append(("A1 joy advice", listy(
    "A1. I'm feeling down. What actually leads a person to joy?", "advice", "c:simchah")))
results.append(("A2 charity effects", listy(
    "A2. What does giving charity actually cause?", "effects", "c:mitzvah-charity")))
results.append(("A3 livelihood advice", listy(
    "A3. What brings a person livelihood/money?", "advice", "c:mamon")))
results.append(("A4 melody->faith", why(
    # NOTE (fixed 2026-07-05): loose --to "אמונה" also substring-matched
    # c:kilkul-ha-emunah ("the CORRUPTION of faith") and won the cost-ranked
    # #1 slot over real faith — a genuine human-curated edge, just the wrong
    # endpoint. Pin --to to the exact id; --from stays loose (all matches
    # there are genuine melody variants, no collision).
    "A4. How does melody/music strengthen faith?", "--from", "נגון|נגינה", "c:emunah-2", "-k", "2")))
print("\n### A5. What do SLEEP and ROSH HASHANAH have in common?")
_a5 = run("common", "c:sleep-slumber-mind", "c:head-year")
print(json.dumps(_a5, ensure_ascii=False)[:300])
# Flipped 2026-07-09 per the pre-merge GAP note: the v2 merge connected them
# (shared neighbor c:emunah-2 — sleep→emunah eitza, RH~emunah bechina).
results.append(("A5 sleep~RH common [healed by v2 merge]",
                _a5.get("ok") is True and bool(_a5.get("shared"))))
results.append(("A6 anger cascade [attested harms edges, v2 merge]", listy(
    "A6. What does anger's own cascade look like? (rows are polarity-labeled harms)",
    "effects", "c:ka'as", expect_nonempty=True)))

print()
print("=" * 70)
print("PART B — showcase questions no search engine could answer")
results.append(("B1 eyes->money", why(
    "B1. Does GUARDING THE EYES affect your MONEY?", "--from", "עינים", "--to", "ממון|פרנסה", "-k", "2")))
results.append(("B2 truth->rain", why(
    "B2. Can TRUTH make it RAIN?", "--from", "אמת", "--to", "גשם", "-k", "1")))
results.append(("B3 melody->redemption", why(
    "B3. Is there a causal road from MELODY to the REDEMPTION?",
    "--from", "נגון|נגינה", "--to", "גאלה|משיח", "-k", "2")))
results.append(("B4 RH->YK loose", why(
    "B4. Rosh Hashanah -> Yom Kippur seal (loose/packet mode)",
    "--from", "ראש השנה", "--to", "כפור|חותם", "--loose", "-k", "2")))
results.append(("B5 brit->prayer", why(
    "B5. Why does the state of the covenant affect PRAYER?",
    "--from", "פגם הברית|ברית", "--to", "תפלה", "-k", "2")))
results.append(("B6 project ascent", generic(
    "B6. PROJECT my own ascent (joy->faith->redemption) onto one Torah's structure — "
    "good-only chain, never anchors on a bad concept",
    "project", "c:simchah", "c:emunah-2", "c:ge'ulah", "-k", "1")))
results.append(("B7 diagnose joy", generic(
    "B7. DIAGNOSE: I want joy — what does the map say I may be missing? "
    "(diagnoses the GOOD target, not the bad state)",
    "diagnose", "c:simchah", "-n", "6")))

print()
print("=" * 70)
n_ok = sum(1 for _, ok in results if ok)
for name, ok in results:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")
print(f"\n{n_ok}/{len(results)} as expected")
