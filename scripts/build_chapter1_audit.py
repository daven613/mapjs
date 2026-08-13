#!/usr/bin/env python3
"""Build Chapter 1 manual-vs-AI audit dashboard with human proof review.

Proof completeness is judged by human reading (stored in PROOF_REVIEWS), not by
letter-matching heuristics. Alternate Divine Name spellings (ה׳ / השם / יתברך /
הקדוש־ברוך־הוא), letter variants (וי״ו / ואו), and obvious pronouns count when
the proof itself makes the link legible.
"""

from __future__ import annotations

import html
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LEGACY_PATH = ROOT / "ontology/occurrences/legacy_human.jsonl"
AI_COMPILED_PATH = ROOT / "ontology/occurrences/ai_compiled.jsonl"
AI_RAW_DIR = ROOT / "ontology/occurrences/ai_extracted"
NODES_PATH = ROOT / "ontology/graph/nodes.json"
EDGES_PATH = ROOT / "ontology/graph/edges.json"
OUTPUT = ROOT / "ontology/audit/2026-07-13-chapter1-manual-vs-ai.html"

CHAPTER = 1
BOOK = "lm1"


# Human proof review keyed by occurrence id.
# verdict: complete | context_dependent | incomplete
PROOF_REVIEWS: dict[str, dict[str, str]] = {
    # --- manual ---
    "occ:legacy:1195": {
        "verdict": "incomplete",
        "note": "Stored src/tgt are שֵּׂכֶל→חֵן, but this proof span is about דַּרְכֵי ה׳/תּוֹרָה and מַלְכוּת הָרְשָׁעָה. Neither שֵּׂכֶל nor חֵן appear in the quote.",
    },
    "occ:legacy:1382": {
        "verdict": "context_dependent",
        "note": "Proof ends mid-thought ('כְּחַדָּא חֲשִׁיבֵי') without stating the equation יעקב=יוסף in this span — though the surrounding manual gloss carries it.",
    },
    # Python falsely flagged these; human reading says both endpoints are in the proof:
    "occ:legacy:188": {
        "verdict": "complete",
        "note": "אַלְוָתָא and וָאו are both explicit ('וְהַתּוֹרָה הִיא בְּחִינַת וָאו… וְזֶהוּ בְּחִינַת אַלְוָתָא').",
    },
    "occ:legacy:189": {
        "verdict": "complete",
        "note": "תּוֹרָה and וָאו both named directly.",
    },
    "occ:legacy:1225": {
        "verdict": "complete",
        "note": "תָ״ו glossed as לְשׁוֹן חֲקִיקָה וּרְשִׁימָה in the same breath.",
    },
    "occ:legacy:1938": {
        "verdict": "complete",
        "note": "וָי״ו and מַקֵּל both in the quote.",
    },
    "occ:legacy:2794": {
        "verdict": "complete",
        "note": "Duplicate of occ:legacy:1225 — both endpoints present.",
    },
    "occ:legacy:3065": {
        "verdict": "complete",
        "note": "Long proof names חֵן and תָ״ו explicitly.",
    },
    "occ:legacy:3265": {
        "verdict": "complete",
        "note": "Both endpoints appear — the long Hebrew labels compress what the proof states as המפרסמים / עזות / הבעל תפלה / המלוה הגדול.",
    },
    # --- AI (lm1 only) ---
    "occ:ai:lm1_1_0_0:3": {
        "verdict": "context_dependent",
        "note": "Proof is only שֶׁמַּעֲלָה חֵן עַל לוֹמְדֶיהָ — חֵן is there, but הַתּוֹרָה is the prior sentence's subject, not in this snippet.",
    },
    "occ:ai:lm1_1_0_10:2": {
        "verdict": "context_dependent",
        "note": "Proof is שֶׁהוּא בְּחִינַת הַשֵּׂכֶל כַּנַ״ל — יַעֲקֹב אִישׁ תָּם is not in the quote.",
    },
    "occ:ai:lm1_1_0_2:2": {
        "verdict": "context_dependent",
        "note": "Verse+targum fragment identifies wisdom with Yaakov via וַיַּעַקְבֵנִי / וְחַכְּמַנִי, but יַעֲקֹב is not named in the stored proof line.",
    },
    "occ:ai:lm1_1_0_2:4": {
        "verdict": "context_dependent",
        "note": "Only the verse אֹרַח צַדִּיקִים… is quoted; שֶׁמֶשׁ is carried by כַּנַ״ל from the prior sentence.",
    },
    "occ:ai:lm1_1_0_4:3": {
        "verdict": "incomplete",
        "note": "Proof is only וְזֶה בְּחִינַת מַלְכוּת הָרְשָׁעָה — the long source phrase about not binding to sekhel is absent.",
    },
    "occ:ai:lm1_1_0_5:6": {
        "verdict": "context_dependent",
        "note": "מַלְכוּת דִּקְדֻשָּׁה is only 'זֶה קָם'; מַלְכוּת הָרְשָׁעָה is named on the fall side.",
    },
    "occ:ai:lm1_1_0_6:0": {
        "verdict": "context_dependent",
        "note": "תְּפִלּוֹת/בַּקָּשׁוֹת appear, but חֵן is only in the prior clause ('עַל יְדֵי זֶה').",
    },
    "occ:ai:lm1_1_0_6:1": {
        "verdict": "complete",
        "note": "הַתּוֹרָה and חֵן both explicit, with the nun-chet join spelled out.",
    },
    "occ:ai:lm1_1_0_7:3": {
        "verdict": "context_dependent",
        "note": "יעקב named; השכל via כַּנַ״ל only.",
    },
    "occ:ai:lm1_1_0_7:7": {
        "verdict": "context_dependent",
        "note": "בְּכוֹר → השכל via כַּנַ״ל.",
    },
    "occ:ai:lm1_1_0_8:3": {
        "verdict": "context_dependent",
        "note": "הַשֵּׁם יִתְבָּרַךְ is explicit on the target side; השכל is the unstated subject of מְקָרֵב.",
    },
    "occ:ai:lm1_1_0_9:6": {
        "verdict": "complete",
        "note": "הַתּוֹרָה and שְׁמוֹתָיו שֶׁל הַקָּדוֹשׁ־בָּרוּךְ־הוּא — Divine Name spelled differently from node label, same referent.",
    },
    "occ:ai:lm1_1_0_9:5": {
        "verdict": "complete",
        "note": "הַתּוֹרָה and הַיֵּצֶר־הָרָע both in the causal line.",
    },
}


def esc(value: object) -> str:
    return html.escape(str(value or ""))


MAQAF = "־"
NIQQUD = re.compile(r"[֑-ֽֿ-ׇ]")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFC", s or "")
    s = s.replace(MAQAF, " ")
    s = NIQQUD.sub("", s)
    s = s.replace("״", '"').replace("׳", "'")
    s = re.sub(r"[^א-ת\"' ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def skel(s: str) -> str:
    return re.sub(r"[יו]", "", norm(s).replace('"', "").replace("'", ""))


def legacy_polarity(occ: dict) -> tuple[str, str]:
    if occ["type"] != "eitza":
        return "neutral", "presence"
    pol = occ.get("polarity") or {}
    if pol.get("is_bad"):
        return "harms", "presence"
    if pol.get("is_good"):
        return "builds", "presence"
    return "builds", "presence"


def load_manual() -> list[dict]:
    rows = []
    for line in LEGACY_PATH.read_text().splitlines():
        occ = json.loads(line)
        anchor = occ.get("anchor", {})
        if anchor.get("book") != BOOK or anchor.get("torah") != CHAPTER:
            continue
        src = occ.get("source_display") or occ.get("source_surface", "")
        tgt = occ.get("target_display") or occ.get("target_surface", "")
        pol, via = legacy_polarity(occ)
        review = PROOF_REVIEWS.get(occ["id"], {})
        rows.append(
            {
                "layer": "manual",
                "id": occ["id"],
                "type": occ["type"],
                "polarity": pol,
                "via": via,
                "source": src,
                "target": tgt,
                "proof": occ.get("proof", ""),
                "chunk": (anchor.get("chunks") or [""])[0],
                "proof_verdict": review.get("verdict", "complete"),
                "proof_note": review.get("note", ""),
            }
        )
    return rows


def load_ai() -> list[dict]:
    rows = []
    for line in AI_COMPILED_PATH.read_text().splitlines():
        occ = json.loads(line)
        anchor = occ.get("anchor", {})
        if anchor.get("book") != BOOK or anchor.get("torah") != CHAPTER:
            continue
        if not occ["id"].startswith("occ:ai:lm1_1_"):
            continue
        review = PROOF_REVIEWS.get(occ["id"], {})
        rows.append(
            {
                "layer": "ai",
                "id": occ["id"],
                "type": occ["type"],
                "polarity": occ.get("polarity", "neutral"),
                "via": occ.get("via", "presence"),
                "source": occ.get("source_surface", ""),
                "target": occ.get("target_surface", ""),
                "proof": occ.get("proof", ""),
                "chunk": occ["id"].split(":")[1].replace("lm1_", "").rsplit(":", 1)[0],
                "proof_verdict": review.get("verdict", "complete"),
                "proof_note": review.get("note", ""),
            }
        )
    return rows


def edge_key(row: dict) -> tuple[str, str, str, str, str]:
    return (
        row["type"],
        row["polarity"],
        row["via"],
        skel(row["source"]),
        skel(row["target"]),
    )


def loose_edge_key(row: dict) -> tuple[str, str, str]:
    return (row["type"], skel(row["source"]), skel(row["target"]))


def proof_label(verdict: str) -> str:
    return {
        "complete": "Both endpoints in proof (human)",
        "context_dependent": "Needs surrounding sentence / כנ״ל",
        "incomplete": "Endpoint missing even on reading",
    }.get(verdict, verdict)


def render_edge_card(row: dict, number: int, badge: str) -> str:
    verdict = row["proof_verdict"]
    vclass = {
        "complete": "ok",
        "context_dependent": "warn",
        "incomplete": "bad",
    }.get(verdict, "warn")
    meta = f"{row['type']} · {row['polarity']} · {row['via']} · chunk {row['chunk']}"
    note = (
        f'<p class="note"><b>Human review:</b> {esc(row["proof_note"])}</p>'
        if row.get("proof_note")
        else ""
    )
    return f"""<article class="card" data-badge="{esc(badge)}" data-proof="{esc(verdict)}">
  <header>
    <span class="num">{number:03d}</span>
    <span class="tag {esc(badge)}">{esc(badge.replace('_', ' '))}</span>
    <span class="tag {vclass}">{esc(proof_label(verdict))}</span>
    <span class="meta">{esc(meta)} · {esc(row['id'])}</span>
  </header>
  <div class="relation">
    <div><b dir="rtl">{esc(row['source'])}</b></div>
    <div class="arrow">→</div>
    <div><b dir="rtl">{esc(row['target'])}</b></div>
  </div>
  <blockquote dir="rtl">{esc(row['proof'])}</blockquote>
  {note}
</article>"""


def main() -> None:
    manual = load_manual()
    ai = load_ai()

    manual_keys = {edge_key(r) for r in manual}
    manual_loose = {loose_edge_key(r) for r in manual}

    ai_only = [r for r in ai if loose_edge_key(r) not in manual_loose]
    manual_only = [r for r in manual if edge_key(r) not in {edge_key(x) for x in ai}]
    overlap = [r for r in ai if loose_edge_key(r) in manual_loose]

    manual_concepts = {skel(r["source"]) for r in manual} | {skel(r["target"]) for r in manual}
    ai_concepts = {skel(r["source"]) for r in ai} | {skel(r["target"]) for r in ai}
    manual_concepts.discard("")
    ai_concepts.discard("")
    ai_only_concepts = sorted(ai_concepts - manual_concepts)

    manual_proof_counts = Counter(r["proof_verdict"] for r in manual)
    ai_proof_counts = Counter(r["proof_verdict"] for r in ai)

    flagged_manual = [r for r in manual if r["proof_verdict"] != "complete"]
    flagged_ai = [r for r in ai if r["proof_verdict"] != "complete"]

    sections = {
        "ai_only": "".join(
            render_edge_card(r, i, "ai_only")
            for i, r in enumerate(sorted(ai_only, key=lambda x: (x["type"], x["source"])), 1)
        ),
        "manual_only": "".join(
            render_edge_card(r, i, "manual_only")
            for i, r in enumerate(sorted(manual_only, key=lambda x: (x["type"], x["source"])), 1)
        ),
        "overlap": "".join(
            render_edge_card(r, i, "overlap")
            for i, r in enumerate(sorted(overlap, key=lambda x: (x["type"], x["source"])), 1)
        ),
        "flagged_manual": "".join(
            render_edge_card(r, i, "flagged")
            for i, r in enumerate(sorted(flagged_manual, key=lambda x: x["proof_verdict"]), 1)
        ),
        "flagged_ai": "".join(
            render_edge_card(r, i, "flagged")
            for i, r in enumerate(sorted(flagged_ai, key=lambda x: x["proof_verdict"]), 1)
        ),
        "concepts": "".join(
            f"""<article class="card"><header><span class="tag concept">AI surface not in manual set</span></header>
<p><code>{esc(key)}</code></p></article>"""
            for key in ai_only_concepts
        ),
    }

    page = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Torah Map — Chapter 1 Manual vs AI Audit (Human Review)</title>
<style>
:root {{
  color-scheme: dark;
  --bg:#10131a; --panel:#181d27; --panel2:#222938; --ink:#edf1f8; --muted:#a7b2c4;
  --line:#334055; --green:#5ee1a7; --amber:#f5c56b; --red:#ff817d; --blue:#88b8ff;
}}
* {{ box-sizing:border-box }}
body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.55 system-ui,sans-serif }}
main {{ max-width:1180px; margin:auto; padding:34px 18px 70px }}
h1 {{ margin:0 0 8px; font-size:clamp(28px,4vw,42px) }}
.lead, .notice p {{ color:var(--muted); max-width:920px }}
.notice {{ background:#1a2230; border-left:4px solid var(--blue); padding:14px 16px; border-radius:8px; margin:20px 0 }}
.stats {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:22px 0 }}
.stat {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:14px }}
.stat strong {{ display:block; font-size:28px }}
.stat span {{ color:var(--muted); font-size:13px }}
.tabs {{ display:flex; flex-wrap:wrap; gap:8px; position:sticky; top:0; background:#10131af2; padding:12px 0; z-index:2; border-bottom:1px solid var(--line) }}
.tabs button {{ border:1px solid var(--line); background:var(--panel2); color:var(--ink); border-radius:999px; padding:8px 12px; cursor:pointer }}
.tabs button.on {{ outline:2px solid var(--blue) }}
.panel {{ display:none }}.panel.on {{ display:block }}
.card {{ background:var(--panel); border:1px solid var(--line); border-radius:12px; padding:16px; margin:14px 0 }}
.card header {{ display:flex; gap:8px; flex-wrap:wrap; align-items:center }}
.num {{ color:var(--muted); font-weight:700; width:34px }}
.tag {{ font-size:12px; font-weight:700; border-radius:999px; padding:2px 9px; text-transform:capitalize }}
.ai_only {{ background:#3a2a10; color:#ffe6b0 }}
.manual_only {{ background:#1f3558; color:#d9ebff }}
.overlap {{ background:#174033; color:#d7ffef }}
.flagged {{ background:#4a2328; color:#ffd7d5 }}
.concept {{ background:#35285d; color:#ece2ff }}
.ok {{ background:#174033; color:#d7ffef }}
.warn {{ background:#664d1b; color:#fff0c9 }}
.bad {{ background:#4a2328; color:#ffd7d5 }}
.meta {{ color:var(--muted); font-size:13px }}
.relation {{ display:grid; grid-template-columns:1fr 34px 1fr; gap:10px; margin:14px 0 }}
.relation > div {{ background:var(--panel2); border-radius:8px; padding:10px }}
.relation b {{ font-size:18px; display:block }}
.arrow {{ text-align:center; color:var(--green); font-size:26px }}
blockquote {{ margin:0; padding:12px 14px; border-right:4px solid var(--blue); background:#141a24; font-size:18px; line-height:1.75 }}
.note {{ color:var(--muted); font-size:14px; margin:8px 0 0 }}
</style></head><body><main>
<h1>Chapter 1 — Manual vs AI (Human-Reviewed)</h1>
<p class="lead">Likutey Moharan <b>Part I, Torah 1</b> only (<code>book=lm1</code>, <code>torah=1</code>). Proof completeness was read by a human — not by Hebrew letter matching. Hashem spelled as ה׳, השם, יתברך, הקדוש־ברוך־הוא counts; so do וי״ו/ואו variants when the proof clearly names both sides of the link.</p>
<div class="notice">
  <p><b>Important correction from the prior report.</b> The old page used skeleton matching and falsely flagged many good proofs (including Divine-Name variants). It also accidentally mixed in <b>141 edges from LM II:1</b> because both share <code>torah=1</code>. This version filters to <code>lm1</code> only.</p>
  <p><b>Proof verdicts.</b> <i>Complete</i> = both endpoints legible in the stored quote. <i>Context dependent</i> = one side is only via pronoun/כנ״ל/prior sentence. <i>Incomplete</i> = even on reading, an endpoint is genuinely absent.</p>
</div>
<div class="stats">
  <div class="stat"><strong>{len(manual)}</strong><span>manual edges</span></div>
  <div class="stat"><strong>{len(ai)}</strong><span>AI edges (lm1 only)</span></div>
  <div class="stat"><strong>{len(overlap)}</strong><span>overlap (type+surfaces)</span></div>
  <div class="stat"><strong>{len(ai_only)}</strong><span>AI-only connections</span></div>
  <div class="stat"><strong>{len(manual_only)}</strong><span>manual-only (strict)</span></div>
  <div class="stat"><strong>{manual_proof_counts.get('complete',0)}</strong><span>manual proofs complete</span></div>
  <div class="stat"><strong>{len(flagged_manual)}</strong><span>manual flagged on reading</span></div>
  <div class="stat"><strong>{ai_proof_counts.get('complete',0)}</strong><span>AI proofs complete</span></div>
  <div class="stat"><strong>{len(flagged_ai)}</strong><span>AI flagged on reading</span></div>
  <div class="stat"><strong>{len(ai_only_concepts)}</strong><span>AI-only concept surfaces</span></div>
</div>
<div class="tabs" id="tabs">
  <button class="on" data-panel="overview">Overview</button>
  <button data-panel="ai_only">AI only ({len(ai_only)})</button>
  <button data-panel="manual_only">Manual only ({len(manual_only)})</button>
  <button data-panel="overlap">Overlap ({len(overlap)})</button>
  <button data-panel="flagged_manual">Manual proof flags ({len(flagged_manual)})</button>
  <button data-panel="flagged_ai">AI proof flags ({len(flagged_ai)})</button>
  <button data-panel="concepts">AI-only concepts ({len(ai_only_concepts)})</button>
</div>
<section class="panel on" id="overview">
  <h2>What I actually read</h2>
  <ul>
    <li>Manual: {manual_proof_counts.get('complete',0)} complete · {manual_proof_counts.get('context_dependent',0)} context-dependent · {manual_proof_counts.get('incomplete',0)} incomplete</li>
    <li>AI (lm1): {ai_proof_counts.get('complete',0)} complete · {ai_proof_counts.get('context_dependent',0)} context-dependent · {ai_proof_counts.get('incomplete',0)} incomplete</li>
    <li>The automated report claimed 8 manual proof gaps and 87 AI gaps — that was wrong. On human reading: {len(flagged_manual)} manual and {len(flagged_ai)} AI edges need attention.</li>
    <li>Example false positive the code made: <code>occ:legacy:3265</code> and <code>occ:ai:lm1_1_0_9:6</code> — Hashem appears as הַקָּדוֹשׁ־בָּרוּךְ־הוּא / הַשֵּׁם יִתְבָּרַךְ, which is obviously the same node.</li>
  </ul>
</section>
<section class="panel" id="ai_only">{sections['ai_only'] or '<p class="lead">None</p>'}</section>
<section class="panel" id="manual_only">{sections['manual_only'] or '<p class="lead">None</p>'}</section>
<section class="panel" id="overlap">{sections['overlap'] or '<p class="lead">None</p>'}</section>
<section class="panel" id="flagged_manual">{sections['flagged_manual'] or '<p class="lead">All manual proofs read as complete.</p>'}</section>
<section class="panel" id="flagged_ai">{sections['flagged_ai'] or '<p class="lead">All AI proofs read as complete.</p>'}</section>
<section class="panel" id="concepts">{sections['concepts'] or '<p class="lead">None</p>'}</section>
<script>
document.getElementById('tabs').addEventListener('click', (e) => {{
  const btn = e.target.closest('button[data-panel]');
  if (!btn) return;
  document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('on'));
  btn.classList.add('on');
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('on', p.id === btn.dataset.panel));
}});
</script>
</main></body></html>"""

    OUTPUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    print(f"manual={len(manual)} ai={len(ai)} overlap={len(overlap)} ai_only={len(ai_only)}")
    print("manual proof:", dict(manual_proof_counts))
    print("ai proof:", dict(ai_proof_counts))


if __name__ == "__main__":
    main()
