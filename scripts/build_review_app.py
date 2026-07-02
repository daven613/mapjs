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

    def contexts(form, occ_filter=None):
        out = []
        for u in by_form.get(form, []):
            if occ_filter is not None and u["occ"] not in occ_filter:
                continue
            a = u["anchor"]
            out.append({"type": u["type"], "partner": u["partner"], "proof": u["proof"],
                        "where": f"{a.get('book')}:{a.get('torah')}",
                        "book": a.get("book"), "keys": (a.get("chunks") or [])[:2]})
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
        concepts = d.get("concepts", [])
        if sum(len(c["members"]) for c in concepts) < 2:
            continue                        # single form, nothing to group or split
        ver = vers.get(f"card:{d['cluster_id']}")
        rec = {}
        if ver:
            for c in ver.get("concepts", []):
                for m in c.get("members", []):
                    rec[m["form"]] = m.get("recommend")
        ruling = rulings.get(d["cluster_id"])
        tiers = {m["tier"] for c in concepts for m in c["members"]}
        flags = sorted({fl for c in concepts for fl in (c.get("flags") or [])})
        if "question" in tiers or "archetype-question" in flags or "local-equation" in flags:
            section = 1
        elif "likely" in tiers:
            section = 2
        else:
            section = 3
        rep = max((m for c in concepts for m in c["members"]),
                  key=lambda m: len(by_form.get(m["form"], [])))
        cards.append({
            "id": d["cluster_id"], "section": section, "title_he": rep["form"],
            "flags": flags, "notes": d.get("notes", ""),
            "rec": ({"verdict": ver.get("verdict"), "confidence": ver.get("confidence"),
                      "reason": ver.get("reason_for_human", "")} if ver else None),
            "ruling": ruling,
            "concepts": [{
                "canonical_he": c["canonical_he"], "gloss": c["gloss_en"],
                "flags": c.get("flags") or [],
                "members": [{**m,
                             "recommend": (None if ruling and ruling.get("keep_round1")
                                            else rec.get(m["form"])),
                             "n_usages": len(by_form.get(m["form"], [])),
                             "contexts": contexts(m["form"])} for m in c["members"]],
            } for c in concepts],
        })

    # homograph verifications: one card per form, one "member" per sense,
    # contexts filtered to the occurrences the verifier assigned to that sense
    for vid, ver in vers.items():
        if ver.get("kind") != "homograph":
            continue
        form = vid.split(":", 1)[1]
        senses = ver.get("concepts", [])
        if len(senses) < 2:
            continue                        # one word, inflection noise — no decision
        cards.append({
            "id": vid, "section": 1, "title_he": form,
            "flags": ["homograph"], "notes": "",
            "rec": {"verdict": ver.get("verdict"), "confidence": ver.get("confidence"),
                     "reason": ver.get("reason_for_human", "")},
            "ruling": None,
            "concepts": [{
                "canonical_he": c["canonical_he"], "gloss": c["gloss_en"], "flags": [],
                "members": [{"form": c["canonical_he"], "tier": "question",
                             "recommend": "approve",
                             "note": f"written {form}; {len(c.get('occ_ids') or [])} occurrence(s)",
                             "n_usages": len(c.get("occ_ids") or []),
                             "contexts": contexts(form, occ_filter=set(c.get("occ_ids") or []))}],
            } for c in senses],
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
