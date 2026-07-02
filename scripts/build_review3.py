#!/usr/bin/env python3
"""Round-3 review page: ONLY the proposed connections (multi-form merges), full context.

Per Shmuel: never show separations for confirmation — separate is the silent default.
Each row = one group of forms Claude proposes to be ONE concept, with the same context
depth as round 1: per usage the location, relation, partner concept, proof quote, and
an on-demand full-paragraph button (/chunk). Everything pre-approved (green); he hits
✗ to break a connection. Excludes everything already decided in his r1 review
(sections Questions+Likely are locked in decisions_shmuel_r1.json).

Sources of proposals:
  - rejects_refigured.json boxes with >=2 forms (new groups formed from his ✗ forms)
  - round-1 adjudication boxes with >=2 distinct forms in the un-reviewed (typography) clusters
Writes ontology/registry/review_app.html (served at localhost:8777).
"""
import json, html as H
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent


def main():
    occs = [json.loads(l) for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()]
    by_form = {}
    for o in occs:
        for side, other in (("source", "target"), ("target", "source")):
            f = o[f"{side}_surface"]
            if f:
                a = o["anchor"]
                by_form.setdefault(f, []).append({
                    "type": o["type"], "partner": o[f"{other}_surface"],
                    "proof": o.get("proof") or "",
                    "where": f"{a.get('book')}:{a.get('torah')}",
                    "book": a.get("book"), "keys": (a.get("chunks") or [])[:1]})

    proposals = []   # {id, he, en, why, forms:[...]}

    r1 = json.loads((MAPJS / "ontology/registry/decisions_shmuel_r1.json").read_text())
    rejected = {tuple(k.split("::", 1)) for k, v in r1.items() if v == "reject"}

    refig = json.loads((MAPJS / "ontology/registry/rejects_refigured.json").read_text())
    refig.pop("_comment", None)
    for cid, r in refig.items():
        for b in r["boxes"]:
            # only NEW pairings: groups joining >=2 of his ✗ forms; anything he already
            # approved together in round 1 is settled and must not reappear
            own = [f for f in set(b["forms"]) if (cid, f) in rejected]
            if len(own) >= 2:
                proposals.append({"id": f"{cid}::{b['he']}", "he": b["he"], "en": b["en"],
                                   "why": "Grouping forms you marked ✗ — I read their sources; "
                                          "they name the same thing.",
                                   "forms": sorted(set(b["forms"]))})

    for f in sorted((MAPJS / "ontology/registry/adjudications").glob("cl_*.json")):
        d = json.loads(f.read_text())
        cons = d.get("concepts", [])
        if d["cluster_id"] in refig or sum(len(c["members"]) for c in cons) < 2:
            continue
        tiers = {m["tier"] for c in cons for m in c["members"]}
        flags = {fl for c in cons for fl in (c.get("flags") or [])}
        if "question" in tiers or "likely" in tiers or "archetype-question" in flags \
           or "local-equation" in flags:
            continue          # sections 1+2 — already reviewed and locked
        for c in cons:
            forms = sorted(set(m["form"] for m in c["members"]))
            if len({" ".join(f.split()) for f in forms}) < 2:
                continue      # whitespace-only variants: auto-same, not worth review
            if len(forms) >= 2:
                proposals.append({"id": f"{d['cluster_id']}::{c['canonical_he']}",
                                   "he": c["canonical_he"], "en": c["gloss_en"],
                                   "why": "Variants of the same word (quotes/spelling/spacing).",
                                   "forms": forms})

    def ctx_html(form):
        rows = []
        for u in by_form.get(form, []):
            btns = " ".join(f'<button class="loadp" data-book="{H.escape(u["book"] or "")}" '
                            f'data-key="{H.escape(k)}">show full paragraph {H.escape(k)}</button>'
                            for k in u["keys"])
            rows.append(f'''<div class="ctx">
              <div class="ctxhead"><b>{H.escape(u["where"])}</b> · relation: <b>{H.escape(u["type"])}</b>
               · connected to: <span class="heb">{H.escape(u["partner"] or "")}</span></div>
              <div class="proof heb">{H.escape(u["proof"])}</div>{btns}</div>''')
        return "".join(rows)

    rows = []
    for p in proposals:
        forms_html = "".join(
            f'''<details class="fdet"><summary><span class="frm heb">{H.escape(f)}</span>
                <span class="cnt">{len(by_form.get(f, []))} usage(s) — click for sources</span></summary>
                {ctx_html(f)}</details>''' for f in p["forms"])
        rows.append(f'''<div class="row" data-k="merge:{H.escape(p["id"])}">
          <div class="head"><b class="heb bhe">{H.escape(p["he"])}</b>
            <span class="gloss">{H.escape(p["en"])}</span>
            <span class="act"><button data-v="approve">✓ connect</button><button data-v="reject">✗ keep separate</button></span></div>
          <div class="why">{H.escape(p["why"])}</div>
          {forms_html}</div>''')

    page = f'''<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>Merge Review — Proposed Connections</title><style>
 body{{margin:0;font:15px/1.55 system-ui,sans-serif;background:#f7f5f0;color:#1c1917}}
 header{{position:sticky;top:0;background:#fff;border-bottom:1px solid #e7e2d9;padding:10px 22px;display:flex;gap:16px;align-items:center;z-index:5}}
 main{{max-width:960px;margin:18px auto 60px;padding:0 16px}}
 .row{{background:#fff;border:1px solid #e7e2d9;border-radius:12px;margin:14px 0;padding:14px 18px}}
 .row.rej{{outline:2px solid #b91c1c}}
 .head{{display:flex;gap:14px;align-items:baseline;flex-wrap:wrap}}
 .heb{{direction:rtl;unicode-bidi:isolate;font-family:serif}}
 .bhe{{font-size:1.5em}}
 .gloss{{flex:1;color:#1e3a8a;background:#eef4ff;border-radius:6px;padding:4px 10px;font-size:14px}}
 .act button{{border:1px solid #e7e2d9;background:#fafaf9;border-radius:8px;padding:5px 12px;cursor:pointer;font-size:13px;margin:0 2px}}
 .act .on-approve{{background:#15803d;color:#fff}} .act .on-reject{{background:#b91c1c;color:#fff}}
 .why{{font-size:13px;color:#78716c;margin:6px 0}}
 .fdet{{border-top:1px dashed #e7e2d9;padding:8px 0 2px;margin-top:6px}}
 .fdet summary{{cursor:pointer;list-style:none;display:flex;gap:12px;align-items:baseline}}
 .frm{{background:#f1efe9;border-radius:6px;padding:2px 10px;font-size:1.2em;font-weight:600}}
 .cnt{{color:#1d4ed8;font-size:12.5px}}
 .ctx{{border:1px solid #e7e2d9;border-radius:8px;padding:9px 13px;margin:7px 0;background:#fdfcfa}}
 .ctxhead{{font-size:12px;color:#78716c;margin-bottom:5px}} .ctxhead b{{color:#1c1917}}
 .proof{{background:#fffbeb;border-radius:6px;padding:6px 10px;margin:5px 0;font-size:1.1em}}
 .loadp{{border:1px solid #e7e2d9;background:#fff;border-radius:6px;padding:3px 10px;font-size:12.5px;cursor:pointer;color:#1d4ed8}}
 .para{{max-height:320px;overflow-y:auto;border-top:1px dotted #e7e2d9;margin-top:7px;padding-top:7px}}
 .para .he{{direction:rtl;text-align:right;font-size:1.15em;font-family:serif}}
 .para .en{{color:#78716c;font-size:.92em;margin-bottom:7px}}
 #stat{{margin-left:auto;font-size:13px;color:#78716c}}
</style></head><body>
<header><b>Proposed Connections</b>
 <span style="font-size:13px;color:#78716c">Every group below = forms I say are ONE concept. All green by default;
 open a form to see its sources; hit ✗ to keep it separate. Nothing you already decided appears here.</span>
 <span id="stat">…</span></header>
<main>{''.join(rows)}</main>
<script>
let dec={{}};
const isHeb=s=>((s.match(/[א-ת]/g)||[]).length >= (s.trim().length*0.3||1));
function paraHtml(t){{return t.split('\\n').map(l=>!l.trim()?'':
  (isHeb(l)?`<div class="he">${{esc(l)}}</div>`:`<div class="en">${{esc(l)}}</div>`)).join('');}}
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}}[c]));
function paint(){{
  document.querySelectorAll('.row').forEach(r=>{{
    const v=dec[r.dataset.k]||'approve';
    r.classList.toggle('rej',v==='reject');
    r.querySelectorAll('.act button').forEach(b=>b.className=(b.dataset.v===v)?'on-'+b.dataset.v:'');
  }});
  const all=[...document.querySelectorAll('.row')].map(r=>dec[r.dataset.k]||'approve');
  document.getElementById('stat').textContent=(all.filter(v=>v==='reject').length)+' broken of '+all.length+' proposed';
}}
let t=null; function save(){{clearTimeout(t);t=setTimeout(async()=>{{
  try{{const cur=await(await fetch('/decisions')).json(); Object.assign(cur,dec);
      await fetch('/save',{{method:'POST',headers:{{'content-type':'application/json'}},body:JSON.stringify(cur)}});
      document.getElementById('stat').textContent+=' · saved ✓';}}catch(e){{}} }},400);}}
document.querySelectorAll('.act button').forEach(b=>b.addEventListener('click',ev=>{{
  ev.preventDefault(); dec[b.closest('.row').dataset.k]=b.dataset.v; paint(); save(); }}));
document.querySelectorAll('.loadp').forEach(b=>b.addEventListener('click',async ev=>{{
  ev.preventDefault(); if(b.dataset.done)return; b.textContent='loading…';
  try{{const j=await(await fetch(`/chunk?book=${{b.dataset.book}}&key=${{b.dataset.key}}`)).json();
    const d=document.createElement('div'); d.className='para'; d.innerHTML=paraHtml(j.text);
    b.after(d); b.dataset.done='1'; b.textContent='¶ '+b.dataset.key;
  }}catch(e){{b.textContent='load failed';}} }}));
(async()=>{{try{{const cur=await(await fetch('/decisions')).json();
  for(const k in cur) if(k.startsWith('merge:')) dec[k]=cur[k];}}catch(e){{}}
  document.querySelectorAll('.row').forEach(r=>{{if(!(r.dataset.k in dec))dec[r.dataset.k]='approve';}});
  paint(); save();}})();
</script></body></html>'''
    dest = MAPJS / "ontology/registry/review_app.html"
    dest.write_text(page)
    print(f"{dest}\nproposed connections: {len(proposals)}")


if __name__ == "__main__":
    main()
