#!/usr/bin/env python3
"""Round-2 review page: Claude's final boxing, built for skimming.

Section A: Shmuel's ✗ forms, re-placed by Claude (rejects_refigured.json — hand judgment).
Section B: the 103 'typography' clusters, re-figured with one clear rule-line each.
Section C: homograph splits confirmed by Shmuel's ✗ marks (settled, read-only).

Default = accepted; he flags exceptions. Writes ontology/registry/review_app.html
(served at localhost:8777). Decisions keyed refig:<cluster_id>, merged into decisions.json.
"""
import json, re, unicodedata, html as H
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
lonly = lambda s: re.sub(r"[^א-ת]", "", unicodedata.normalize("NFC", s or ""))


def main():
    occs = [json.loads(l) for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()]
    counts = {}
    for o in occs:
        for side in ("source", "target"):
            f = o[f"{side}_surface"]
            if f:
                counts[f] = counts.get(f, 0) + 1

    refig = json.loads((MAPJS / "ontology/registry/rejects_refigured.json").read_text())
    refig.pop("_comment", None)

    # typography clusters = same section-3 logic as before
    typo = []
    for f in sorted((MAPJS / "ontology/registry/adjudications").glob("cl_*.json")):
        d = json.loads(f.read_text())
        cons = d.get("concepts", [])
        if sum(len(c["members"]) for c in cons) < 2 or d["cluster_id"] in refig:
            continue
        tiers = {m["tier"] for c in cons for m in c["members"]}
        flags = {fl for c in cons for fl in (c.get("flags") or [])}
        if "question" in tiers or "archetype-question" in flags or "local-equation" in flags \
           or "likely" in tiers:
            continue
        boxes = [{"he": c["canonical_he"], "en": c["gloss_en"].split("—")[0].split("(")[0].strip()[:80],
                  "forms": sorted(set(m["form"] for m in c["members"]),
                                   key=lambda x: -counts.get(x, 0))} for c in cons]
        if len(boxes) == 1:
            why = "Same word — the variants differ only in quotes/spelling/spacing."
        else:
            keys = [lonly(b["he"]) for b in boxes]
            nested = any(a != b and (a in b or b in a) for a in keys for b in keys)
            why = ("Base concept vs qualified/action form — kept separate (your rule: the thing "
                   "≠ an action or qualifier on it)." if nested
                   else "Different words that merely share letters — never one concept.")
        typo.append({"id": d["cluster_id"], "boxes": boxes, "why": why})

    homs = []
    vdir = MAPJS / "ontology/registry/verifications"
    for f in sorted(vdir.glob("form_*.json")):
        d = json.loads(f.read_text())
        if d.get("_failed") or len(d.get("concepts", [])) < 2:
            continue
        homs.append({"form": d["id"].split(":", 1)[1],
                     "senses": [{"he": c["canonical_he"], "en": c["gloss_en"][:70],
                                  "n": len(c.get("occ_ids") or [])} for c in d["concepts"]]})

    def box_html(b, forms_counts=True):
        forms = " ".join(f'<span class="frm heb">{H.escape(x)}'
                         + (f'<span class="cnt">×{counts.get(x,1)}</span>' if forms_counts else '')
                         + '</span>' for x in b["forms"])
        return (f'<div class="box">{forms}<span class="arrow">→</span>'
                f'<b class="heb bhe">{H.escape(b["he"])}</b>'
                f'<span class="ben">{H.escape(b["en"])}</span></div>')

    rowsA = []
    for cid, r in refig.items():
        rowsA.append(f'''<div class="row" data-k="refig:{H.escape(cid)}">
          <div class="boxes">{''.join(box_html(b) for b in r["boxes"])}</div>
          <div class="why">{H.escape(r.get("why",""))}</div>
          <div class="act"><button data-v="approve">✓</button><button data-v="reject">✗</button></div>
        </div>''')

    rowsB = []
    for t in typo:
        rowsB.append(f'''<div class="row" data-k="refig:{H.escape(t["id"])}">
          <div class="boxes">{''.join(box_html(b) for b in t["boxes"])}</div>
          <div class="why">{H.escape(t["why"])}</div>
          <div class="act"><button data-v="approve">✓</button><button data-v="reject">✗</button></div>
        </div>''')

    rowsC = []
    for h in homs:
        senses = " · ".join(f'<b class="heb">{H.escape(s["he"])}</b> {H.escape(s["en"])} (×{s["n"]})'
                            for s in h["senses"])
        rowsC.append(f'<div class="rowc"><span class="heb bhe">{H.escape(h["form"])}</span> — {senses}</div>')

    page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Merge Review — Round 2 (final boxing)</title><style>
 body{{margin:0;font:15px/1.5 system-ui,sans-serif;background:#f7f5f0;color:#1c1917}}
 header{{position:sticky;top:0;background:#fff;border-bottom:1px solid #e7e2d9;padding:10px 22px;display:flex;gap:16px;align-items:center;z-index:5}}
 main{{max-width:1050px;margin:18px auto 60px;padding:0 16px}}
 h2{{font-size:16px;margin:26px 0 6px}}
 .note{{font-size:13.5px;color:#78716c;margin:0 0 10px}}
 .row{{background:#fff;border:1px solid #e7e2d9;border-radius:10px;margin:8px 0;padding:10px 14px;display:flex;gap:12px;align-items:flex-start}}
 .row.rej{{outline:2px solid #b91c1c}}
 .boxes{{flex:1}}
 .box{{margin:3px 0;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}}
 .heb{{direction:rtl;unicode-bidi:isolate;font-family:serif}}
 .frm{{background:#f1efe9;border-radius:6px;padding:1px 8px;font-size:1.1em}}
 .cnt{{color:#78716c;font-size:.75em;margin-inline-start:3px}}
 .arrow{{color:#a8a29e}}
 .bhe{{font-size:1.15em}}
 .ben{{color:#57534e;font-size:.92em}}
 .why{{flex-basis:270px;flex-shrink:0;font-size:12.5px;color:#78716c;border-inline-start:3px solid #e7e2d9;padding-inline-start:10px}}
 .act button{{border:1px solid #e7e2d9;background:#fafaf9;border-radius:8px;padding:4px 11px;cursor:pointer;margin:0 2px}}
 .act .on-approve{{background:#15803d;color:#fff}} .act .on-reject{{background:#b91c1c;color:#fff}}
 .rowc{{background:#fff;border:1px solid #e7e2d9;border-radius:10px;margin:6px 0;padding:8px 14px;font-size:14px}}
 #stat{{margin-left:auto;font-size:13px;color:#78716c}}
</style></head><body>
<header><b>Merge Review — Round 2</b>
 <span style="font-size:13px;color:#78716c">Everything is pre-accepted (✓). Skim; hit ✗ only where I'm wrong.</span>
 <span id="stat">…</span></header>
<main>
<h2>A. Your ✗ forms — my re-placement ({len(rowsA)} groups)</h2>
<div class="note">Each line: the forms → the concept box I put them in. Rejects that belong together are grouped.</div>
{''.join(rowsA)}
<h2>B. Typography clusters — final boxing ({len(rowsB)} groups)</h2>
<div class="note">One rule-line each. Boxes on separate lines = separate concepts.</div>
{''.join(rowsB)}
<h2>C. Homographs — settled by your ✗ (read-only)</h2>
{''.join(rowsC)}
</main>
<script>
let dec={{}};
function paint(){{
  document.querySelectorAll('.row').forEach(r=>{{
    const v=dec[r.dataset.k]||'approve';
    r.classList.toggle('rej',v==='reject');
    r.querySelectorAll('button').forEach(b=>b.className=(b.dataset.v===v)?'on-'+v:'');
  }});
  const all=[...document.querySelectorAll('.row')].map(r=>dec[r.dataset.k]||'approve');
  document.getElementById('stat').textContent=all.filter(v=>v==='reject').length+' flagged of '+all.length;
}}
let t=null; function save(){{clearTimeout(t);t=setTimeout(async()=>{{
  try{{const cur=await(await fetch('/decisions')).json();
      Object.assign(cur,dec);
      await fetch('/save',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify(cur)}});
      document.getElementById('stat').textContent+=' · saved ✓';}}catch(e){{}}
}},400);}}
document.querySelectorAll('.row .act button').forEach(b=>b.addEventListener('click',()=>{{
  dec[b.closest('.row').dataset.k]=b.dataset.v; paint(); save();
}}));
(async()=>{{try{{const cur=await(await fetch('/decisions')).json();
  for(const k in cur) if(k.startsWith('refig:')) dec[k]=cur[k];}}catch(e){{}}
  document.querySelectorAll('.row').forEach(r=>{{if(!(r.dataset.k in dec))dec[r.dataset.k]='approve';}});
  paint(); save();}})();
</script></body></html>'''
    dest = MAPJS / "ontology/registry/review_app.html"
    dest.write_text(page)
    print(f"{dest}\nA: {len(rowsA)} re-placements  B: {len(rowsB)} typography  C: {len(rowsC)} homographs")


if __name__ == "__main__":
    main()
