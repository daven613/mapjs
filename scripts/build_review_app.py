#!/usr/bin/env python3
"""Build the HTML merge-review app (ontology/registry/review_app.html).

Shows every proposed concept with its English definition front and center, each member form
with FULL paragraph context (the interlinear Hebrew+English chunk where each proof lives),
and click-to-decide buttons. Decisions autosave through review_server.py to decisions.json.

Sections: 1 REAL QUESTIONS (archetype/question/local-equation) · 2 LIKELY · 3 TYPOGRAPHY
(pre-checked) — per Shmuel's 2026-07-02 rulings in docs/CANONICALIZATION.md.
"""
import json, re, unicodedata
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
NEW_SEFER = Path.home() / "dev" / "new-sefer" / "graph_poc"
STRIPN = re.compile(r"[֑-ׇ]")
LETTERS = re.compile(r"[^א-ת]+")

lonly = lambda s: LETTERS.sub("", STRIPN.sub("", unicodedata.normalize("NFC", s or "")))


def load_chunks():
    texts = {}
    for book in ("lm1", "lm2"):
        data = json.loads((NEW_SEFER / book / "reading.json").read_text())
        for t in data["torahs"]:
            for sec in t["sections"]:
                for sub in sec["subsections"]:
                    texts[(book, sub["key"])] = sub["text"]
    return texts


def main():
    chunks = load_chunks()
    occs = [json.loads(l) for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()]
    by_form = {}
    for o in occs:
        for side, other in (("source", "target"), ("target", "source")):
            f = o[f"{side}_surface"]
            if f:
                by_form.setdefault(f, []).append({
                    "occ": o["id"], "type": o["type"], "partner": o[f"{other}_surface"],
                    "proof": o.get("proof") or "", "anchor": o["anchor"]})

    def contexts(form, cap=4):
        out = []
        for u in by_form.get(form, [])[:cap]:
            a = u["anchor"]
            paras = []
            for k in (a.get("chunks") or [])[:2]:
                txt = chunks.get((a["book"], k))
                if txt:
                    paras.append({"key": k, "text": txt})
            out.append({"type": u["type"], "partner": u["partner"], "proof": u["proof"],
                        "where": f"{a.get('book')}:{a.get('torah')}", "paras": paras})
        return out

    # verifications (full-context pass) and user rulings
    vers = {}
    vdir = MAPJS / "ontology/registry/verifications"
    if vdir.is_dir():
        for f in vdir.glob("*.json"):
            d = json.loads(f.read_text())
            if not d.get("_failed"):
                vers[d["id"]] = d
    rul_path = MAPJS / "ontology/registry/user_rulings.json"
    rulings = json.loads(rul_path.read_text()) if rul_path.exists() else {}

    cards = []
    for f in sorted((MAPJS / "ontology/registry/adjudications").glob("cl_*.json")):
        d = json.loads(f.read_text())
        ver = vers.get(f"card:{d['cluster_id']}")
        rec = {}
        if ver:
            for c in ver.get("concepts", []):
                for m in c.get("members", []):
                    rec[m["form"]] = m.get("recommend")
        ruling = rulings.get(d["cluster_id"])
        for ci, c in enumerate(d.get("concepts", [])):
            if len(c["members"]) < 2 and not c.get("flags"):
                continue
            tiers = {m["tier"] for m in c["members"][1:]}
            flags = c.get("flags") or []
            if "question" in tiers or "archetype-question" in flags or "local-equation" in flags:
                section = 1
            elif "likely" in tiers:
                section = 2
            else:
                section = 3
            cards.append({
                "id": f"{d['cluster_id']}#{ci}", "section": section,
                "canonical_he": c["canonical_he"], "gloss": c["gloss_en"], "flags": flags,
                "notes": d.get("notes", ""),
                "rec": ({"verdict": ver.get("verdict"), "confidence": ver.get("confidence"),
                          "reason": ver.get("reason_for_human", "")} if ver else None),
                "ruling": ruling,
                "members": [{**m, "recommend": (None if ruling and ruling.get("keep_round1")
                                                 else rec.get(m["form"])),
                             "contexts": contexts(m["form"])} for m in c["members"]],
            })

    # homograph verifications become their own question cards, one member per sense
    occ_ctx = {}
    for form, us in by_form.items():
        for u in us:
            occ_ctx.setdefault((form, u["occ"]), u)
    for vid, ver in vers.items():
        if ver.get("kind") != "homograph":
            continue
        form = vid.split(":", 1)[1]
        members = []
        for c in ver.get("concepts", []):
            mem_ctx = []
            for oid in (c.get("occ_ids") or [])[:4]:
                u = occ_ctx.get((form, oid))
                if u:
                    a = u["anchor"]
                    paras = [{"key": k, "text": chunks[(a["book"], k)]}
                             for k in (a.get("chunks") or [])[:1] if (a["book"], k) in chunks]
                    mem_ctx.append({"type": u["type"], "partner": u["partner"], "proof": u["proof"],
                                     "where": f"{a.get('book')}:{a.get('torah')}", "paras": paras})
            members.append({"form": c["canonical_he"], "tier": "question",
                            "recommend": "approve",
                            "note": f"{c['gloss_en']} — {len(c.get('occ_ids') or [])} occurrence(s)",
                            "contexts": mem_ctx})
        if len(members) < 2:
            continue          # verifier says one word (inflection noise) — no decision needed
        cards.append({
            "id": vid, "section": 1,
            "canonical_he": form, "gloss": "HOMOGRAPH — one written form, several words. "
                                            "Approve each sense split below.",
            "flags": ["homograph"], "notes": "",
            "rec": {"verdict": ver.get("verdict"), "confidence": ver.get("confidence"),
                     "reason": ver.get("reason_for_human", "")},
            "ruling": None, "members": members,
        })
    cards.sort(key=lambda c: c["section"])

    html = (MAPJS / "scripts/review_app_template.html").read_text()
    html = html.replace("/*__DATA__*/", json.dumps(cards, ensure_ascii=False))
    dest = MAPJS / "ontology/registry/review_app.html"
    dest.write_text(html)
    n = [sum(1 for c in cards if c["section"] == s) for s in (1, 2, 3)]
    print(f"{dest}\ncards: {len(cards)} (questions {n[0]}, likely {n[1]}, typography {n[2]})")


if __name__ == "__main__":
    main()
