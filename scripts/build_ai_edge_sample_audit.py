#!/usr/bin/env python3
"""Build a self-contained, manually annotated sample audit of AI-only edges."""

from __future__ import annotations

import html
import json
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
EXPLORER_DATA = ROOT / "ontology/graph/explorer_data.json"
RAW_DIR = ROOT / "ontology/occurrences/ai_extracted"
OUTPUT = ROOT / "ontology/audit/2026-07-12-independent-ai-edge-sample.html"

QUOTAS = {
    ("bechina", "neutral", "presence"): 5,
    ("equation", "neutral", "presence"): 5,
    ("eitza", "builds", "presence"): 8,
    ("eitza", "harms", "presence"): 6,
    ("eitza", "harms", "absence"): 6,
}

# This is the manual review, made explicit rather than inferred by the report builder.
# Keys are source extraction file + zero-based edge position.
REVIEWS = {
    "lm2_9_0_2.json:3": (
        "supported", "partial",
        "The proof explicitly says that some wicked people are an aspect of the erev rav. The stored source gloss is stale/misleading (it mentions ashes), and the target has no English gloss.",
        "Keep the edge; repair the source gloss and add a target gloss.",
    ),
    "lm1_31_9_2.json:2": (
        "supported", "clear",
        "The phrase explicitly identifies the revelation of פני ה׳ with פנים. This is a narrow but real bechina link.",
        "Keep.",
    ),
    "lm1_277_23_0.json:0": (
        "weak", "unclear",
        "The quote only introduces the verse phrase as a bechina; it does not say in the quoted span that the whole phrase is an aspect of the abstract node צדק. The source is a verse fragment, not a legible concept label.",
        "Keep only with a longer proof that states the intended correspondence, or demote to review.",
    ),
    "lm1_59_0_1.json:1": (
        "supported", "partial",
        "והיכל, זה בחינת הכבוד is an explicit aspect statement. The source is understandable in Hebrew but has no explanatory gloss.",
        "Keep; add a gloss for היכל in this usage.",
    ),
    "lm1_234_6_0.json:2": (
        "supported", "partial",
        "The proof directly says that mochin d'katnut are an aspect of dinim. The technical terms are valid, though the target is not glossed.",
        "Keep; gloss the target.",
    ),
    "lm1_286_3_0.json:3": (
        "supported", "clear",
        "The quote defines mishpat as the judgments and laws of the Torah. Equation is appropriate.",
        "Keep.",
    ),
    "lm1_62_5_2.json:2": (
        "supported", "partial",
        "The proof explicitly gives the letter-play: Pharaoh is the letters of oref/backwards. The target needs a user-facing gloss.",
        "Keep; gloss the wordplay target.",
    ),
    "lm1_38_3_0.json:5": (
        "weak", "clear",
        "The proof is only שהם הגבורות (they are the gevurot). It does not name the five mouth articulation points, so the antecedent is outside the displayed proof.",
        "Extend the proof to include the antecedent, then keep as an equation.",
    ),
    "lm1_280_2_0.json:0": (
        "supported", "clear",
        "The sentence says that all business dealings are Torah. It directly supports the stored equation.",
        "Keep.",
    ),
    "lm1_14_5_5.json:1": (
        "supported", "unclear",
        "The text explicitly glosses מרבעתא as a term for zivug. The relation is supported, but the source is opaque Aramaic and has no gloss for a reader.",
        "Keep; add a concise English explanation of מרבעתא.",
    ),
    "lm1_31_9_33.json:2": (
        "wrong", "partial",
        "The proof says charity cancels/removes a delay on the road. The stored builds edge reads as charity producing the delay, so the target direction/polarity is wrong for this schema.",
        "Replace with a representation for removing/preventing the delay, or omit until that semantics is modeled.",
    ),
    "lm1_56_9_3.json:6": (
        "weak", "unclear",
        "מזה (from this) leaves the source outside the quote. The stored source, lifting the heart to the hands, is not textually visible in the proof.",
        "Extend the proof to name the source; otherwise flag as context-dependent.",
    ),
    "lm1_23_5_17.json:1": (
        "supported", "partial",
        "The proof directly says that the essential flow of abundance is drawn from truth. The target is a raw Hebrew phrase without a gloss.",
        "Keep; gloss shefa.",
    ),
    "lm1_9_2_4.json:1": (
        "supported", "partial",
        "The proof explicitly says that through his prayer he influenced vitality to all three parts of the world. The output is clear in Hebrew but stored as an unglossed phrase node.",
        "Keep; give the phrase node an English gloss or consolidate it into a named concept.",
    ),
    "lm1_18_2_4.json:5": (
        "weak", "partial",
        "The proof says he crowns them with kingship and leadership, but does not name the source concept atarah. The relation relies on unquoted context/root-word interpretation.",
        "Use a proof that names atarah, or classify it as a contextual inference.",
    ),
    "lm1_66_1_8.json:3": (
        "weak", "unclear",
        "The proof says that he will perform more deeds and charities than his teacher, but the source פי שנים is absent from the displayed quote.",
        "Extend the proof to include the double-portion clause.",
    ),
    "lm1_32_2_0.json:7": (
        "supported", "clear",
        "על ידי שמחת הלב מרקדין directly states that joy of the heart brings dancing.",
        "Keep.",
    ),
    "lm1_69_0_13.json:4": (
        "supported", "partial",
        "The sentence directly says that branches make fruit. It is clear literally, though this node's fuller symbolic meaning is not visible in the endpoint label.",
        "Keep; improve the contextual gloss if this is a symbolic branch concept.",
    ),
    "lm1_74_0_12.json:2": (
        "supported", "clear",
        "The proof says that the din comes from mochin d'katnut. This supports a harms/presence causal edge.",
        "Keep.",
    ),
    "lm1_7_4_0.json:5": (
        "wrong", "clear",
        "ציצית מכסה על עריות says tzitzit protects/covers against forbidden relations; it does not say tzitzit produces or damages them. The harms/presence encoding reverses the ordinary reading.",
        "Do not store this as a harms edge from tzitzit to arayot; model prevention explicitly or retain it only as quoted evidence.",
    ),
    "lm1_72_0_0.json:2": (
        "supported", "clear",
        "The proof says the evil inclination intensifies and the person loses all desire. It supports a harmful effect, though a loss-of-desire endpoint would make the negative effect more explicit.",
        "Keep, but consider naming the target as loss of cheshek rather than cheshek itself.",
    ),
    "lm1_95_2_0.json:2": (
        "weak", "partial",
        "The proof describes people opening their mouths and insulting him. It supports a concrete act of verbal contempt, but the generic node פה overgeneralizes that act into 'mouth causes contempt.'",
        "Use an endpoint/source such as insulting speech, or retain only with a more precise concept label.",
    ),
    "lm1_38_2_1.json:7": (
        "weak", "clear",
        "ולעורר דין is an infinitive fragment ('to arouse judgment') and does not name קץ כל בשר. The source is supplied by omitted context.",
        "Extend the quote to include the source clause.",
    ),
    "lm1_23_5_6.json:2": (
        "weak", "clear",
        "The quote says that his days are consumed pursuing luxuries, but it does not mention lust for money. The asserted source is outside the proof span.",
        "Extend the proof to include the money-lust antecedent.",
    ),
    "lm1_60_6_1.json:4": (
        "supported", "clear",
        "The proof explicitly says that when eating is not holy, one loses one's face, namely intellect. It matches harms/absence exactly.",
        "Keep.",
    ),
    "lm1_24_8_4.json:3": (
        "supported", "partial",
        "The proof explicitly says that without the restraining force, the mochin would be entirely annulled. The source is a technical phrase node without a helpful gloss.",
        "Keep; add a plain-language gloss for the restraining force.",
    ),
    "lm1_31_9_7.json:6": (
        "supported", "clear",
        "Without vowel points, the letters are like a golem with no motion or life. This directly matches harms/absence.",
        "Keep.",
    ),
    "lm1_152_1_0.json:1": (
        "weak", "partial",
        "The quote says 'then they cannot enter/approach their root,' but does not name emunah or its lack. The causal attribution depends on prior context.",
        "Extend the proof to include the faith clause.",
    ),
    "lm1_18_2_2.json:6": (
        "supported", "partial",
        "The proof explicitly relates wrath and concealment to the diminution of faith, matching a harms/absence edge. The target is a bundled phrase without an English gloss.",
        "Keep; gloss or split the bundled effect if queries need the two outcomes separately.",
    ),
    "lm1_67_8_4.json:3": (
        "supported", "partial",
        "The proof says that the nefesh became weary through separation from kavod. It supports the absence relation, but the node id c:kingship is misleading for a Hebrew label of kavod.",
        "Keep the claim; rename/alias the node id so it does not read as a different concept.",
    ),
}


def stable_hash(value: str) -> int:
    result = 2166136261
    for character in value:
        result ^= ord(character)
        result = (result * 16777619) & 0xFFFFFFFF
    return result


def normalize_proof(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(
        char
        for char in decomposed
        if not unicodedata.combining(char)
        and char not in " \t\n-–—.,;:'\"׳״()[]"
    )


def load_raw_edges() -> dict[tuple[str, str, str, str], list[dict]]:
    grouped: dict[tuple[str, str, str, str], list[dict]] = defaultdict(list)
    for path in sorted(RAW_DIR.glob("*.json")):
        record = json.loads(path.read_text())
        for index, edge in enumerate(record["edges"]):
            edge = {**edge, "file": path.name, "index": index, "chunk": record["chunk"]}
            key = (
                edge["type"],
                edge.get("polarity", "builds"),
                edge.get("via", "presence"),
                normalize_proof(edge["proof"]),
            )
            grouped[key].append(edge)
    return grouped


def esc(value: object) -> str:
    return html.escape(str(value or ""))


def tag(value: str) -> str:
    return f'<span class="tag {esc(value)}">{esc(value)}</span>'


def build_report() -> str:
    data = json.loads(EXPLORER_DATA.read_text())
    nodes = {node["id"]: node for node in data["nodes"]}
    raw_edges = load_raw_edges()
    selected = []

    for (edge_type, polarity, via), quota in QUOTAS.items():
        choices = [
            edge
            for edge in data["edges"]
            if edge["prov"] == "a"
            and edge["ty"] == edge_type
            and edge["pol"] == polarity
            and edge["via"] == via
        ]
        choices.sort(key=lambda edge: stable_hash("|".join((edge["s"], edge["t"], edge["p"]))))
        selected.extend(choices[:quota])

    rows = []
    for number, edge in enumerate(selected, start=1):
        key = (edge["ty"], edge["pol"], edge["via"], normalize_proof(edge["p"]))
        matches = raw_edges[key]
        raw = matches[0]
        review_key = f'{raw["file"]}:{raw["index"]}'
        verdict, clarity, finding, action = REVIEWS[review_key]
        source = nodes[edge["s"]]
        target = nodes[edge["t"]]
        rows.append(
            {
                "number": number,
                "edge": edge,
                "raw": raw,
                "source": source,
                "target": target,
                "verdict": verdict,
                "clarity": clarity,
                "finding": finding,
                "action": action,
            }
        )

    verdicts = Counter(row["verdict"] for row in rows)
    clarity = Counter(row["clarity"] for row in rows)
    cards = []
    for row in rows:
        edge = row["edge"]
        raw = row["raw"]
        source = row["source"]
        target = row["target"]
        cards.append(
            f'''<article class="card" data-verdict="{row["verdict"]}" data-clarity="{row["clarity"]}">
  <header><span class="number">{row["number"]:02}</span> {tag(row["verdict"])} {tag(row["clarity"])}
    <span class="meta">{esc(edge["ty"])} · {esc(edge["pol"])} · {esc(edge["via"])} · {esc(", ".join(edge["ref"]))}</span></header>
  <div class="relation"><div><b dir="rtl">{esc(source["he"])}</b><code>{esc(edge["s"])}</code><p>{esc(source.get("gloss") or "No English gloss stored.")}</p></div>
    <div class="arrow">→</div>
    <div><b dir="rtl">{esc(target["he"])}</b><code>{esc(edge["t"])}</code><p>{esc(target.get("gloss") or "No English gloss stored.")}</p></div></div>
  <div class="raw"><span>Extracted as</span><b dir="rtl">{esc(raw["source_he"])} → {esc(raw["target_he"])}</b></div>
  <blockquote dir="rtl">{esc(edge["p"])}</blockquote>
  <p class="finding"><b>Finding:</b> {esc(row["finding"])}</p>
  <p class="action"><b>Recommended action:</b> {esc(row["action"])}</p>
  <footer>{esc(raw["file"])} · edge {raw["index"]} · chunk {esc(raw["chunk"])}</footer>
</article>'''
        )

    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Torah Map — Independent AI Edge Sample Audit</title>
<style>
:root {{ color-scheme: dark; --bg:#12151c; --panel:#1b202a; --panel2:#242b37; --ink:#edf1f8; --muted:#a9b4c5; --line:#3b4658; --green:#5ee1a7; --amber:#f5c56b; --red:#ff817d; --blue:#88b8ff; }}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,sans-serif}} main{{max-width:1120px;margin:auto;padding:36px 20px 60px}} h1{{margin:0;font-size:clamp(27px,4vw,42px)}} h2{{margin-top:38px}} .lead{{color:var(--muted);max-width:850px;font-size:17px}} .notice{{background:#202936;border-left:4px solid var(--blue);padding:14px 16px;border-radius:6px;margin:22px 0}} .stats{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:20px 0}} .stat{{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}} .stat strong{{display:block;font-size:26px}} .filters{{position:sticky;top:0;background:#12151cf0;padding:12px 0;z-index:1;border-bottom:1px solid var(--line)}} button{{margin:3px;padding:7px 10px;border:1px solid var(--line);border-radius:999px;background:var(--panel2);color:var(--ink);cursor:pointer}} button.on{{outline:2px solid var(--blue)}} .card{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:17px;margin:14px 0}} .card header{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}} .number{{font-weight:800;color:var(--muted);width:26px}} .tag{{font-size:12px;font-weight:700;border-radius:999px;padding:2px 8px;text-transform:capitalize}} .supported{{background:#1b5c46;color:#d6ffe9}} .weak{{background:#664d1b;color:#fff0c9}} .wrong{{background:#682f32;color:#ffe0df}} .clear{{background:#214d70;color:#dceeff}} .partial{{background:#4b426c;color:#eee8ff}} .unclear{{background:#4a4a4d;color:#eee}} .meta,footer{{color:var(--muted);font-size:13px}} .relation{{display:grid;grid-template-columns:1fr 30px 1fr;gap:10px;align-items:center;margin-top:15px}} .relation>div{{background:var(--panel2);padding:10px;border-radius:8px;min-width:0}} .relation b{{font-size:18px;display:block}} code{{color:#b7d5ff;display:block;font-size:12px;overflow-wrap:anywhere}} .relation p{{color:var(--muted);font-size:13px;margin:5px 0 0}} .arrow{{font-size:28px;text-align:center;color:var(--green)}} .raw{{margin-top:12px;color:var(--muted)}} .raw span{{display:block;font-size:12px;text-transform:uppercase;letter-spacing:.06em}} blockquote{{margin:12px 0;padding:12px 16px;border-right:4px solid var(--blue);background:#171d27;font-size:18px;line-height:1.8}} .finding,.action{{margin:10px 0}} .action b{{color:var(--green)}} footer{{border-top:1px solid var(--line);padding-top:9px;margin-top:13px}} .hidden{{display:none}} @media(max-width:680px){{.stats{{grid-template-columns:1fr}}.relation{{grid-template-columns:1fr}}.arrow{{transform:rotate(90deg)}}}}
</style></head><body><main>
<h1>Independent AI Edge Sample Audit</h1>
<p class="lead">30 AI-only connections reviewed one by one against the exact stored proof quote and the current endpoint labels. This report is a small diagnostic sample, not an estimate of the full graph's accuracy.</p>
<div class="notice"><b>Review standard.</b> <i>Supported</i> means the displayed proof itself states the relation in the stored direction/type. <i>Weak</i> means it may be true in surrounding context, but the stored proof omits an endpoint, uses an unresolved pronoun, or the endpoint overgeneralizes the text. <i>Wrong</i> means the proof's plain reading contradicts the stored causal/polarity encoding. <i>Clear / partial / unclear</i> evaluates whether a reader can understand both current endpoint labels, not whether the underlying teaching is important.</div>
<div class="stats"><div class="stat"><strong>30</strong>AI-only edges</div><div class="stat"><strong>{verdicts["supported"]} supported · {verdicts["weak"]} weak · {verdicts["wrong"]} wrong</strong>proof support</div><div class="stat"><strong>{clarity["clear"]} clear · {clarity["partial"]} partial · {clarity["unclear"]} unclear</strong>endpoint clarity</div></div>
<h2>Method</h2><ul><li>Source population: 8,389 compiled edges marked AI-only in <code>ontology/graph/explorer_data.json</code>.</li><li>Sampling: deterministic FNV-1a ordering within five strata: 5 bechina, 5 equation, 8 eitza/builds/presence, 6 eitza/harms/presence, and 6 eitza/harms/absence.</li><li>Every row was matched back to its original <code>ontology/occurrences/ai_extracted/*.json</code> extraction record. No legacy proof or external interpretation was used to upgrade a weak proof.</li><li>Important limitation: a weak result is not a claim that the teaching is false—only that this stored evidence snippet cannot independently carry this graph assertion.</li></ul>
<h2>Findings</h2><div class="filters"><b>Show:</b><button class="on" data-filter="all">all 30</button><button data-filter="supported">supported</button><button data-filter="weak">weak</button><button data-filter="wrong">wrong</button><button data-filter="clear">clear nodes</button><button data-filter="partial">partial nodes</button><button data-filter="unclear">unclear nodes</button></div>
{''.join(cards)}
</main><script>
const buttons=[...document.querySelectorAll('button')], cards=[...document.querySelectorAll('.card')];
buttons.forEach(button=>button.onclick=()=>{{const filter=button.dataset.filter;buttons.forEach(item=>item.classList.toggle('on',item===button));cards.forEach(card=>card.classList.toggle('hidden',filter!=='all'&&card.dataset.verdict!==filter&&card.dataset.clarity!==filter));}});
</script></body></html>'''


if __name__ == "__main__":
    OUTPUT.write_text(build_report())
    print(OUTPUT)
