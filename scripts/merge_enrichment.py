#!/usr/bin/env python3
"""Fold the Fable enrichment back into the concept layer and finalize concept IDs.

Inputs:
  ontology/registry/concepts.json        (from apply_decisions.py; tmp ids, some gloss-less)
  ontology/registry/sweep/*.json         sense-consistency verdicts + refined glosses (>=2 occ)
  ontology/registry/glosses/batch_*.json glosses for single-occurrence concepts
  ontology/registry/decisions.json       form: homograph splits Shmuel already approved

Actions:
  1. Attach the best gloss to every concept (sweep gloss > batch gloss > existing).
  2. Apply Shmuel-APPROVED homograph splits (form: reject vocalization -> its own concept),
     partitioning occurrences by their per-occurrence display vocalization.
  3. Collect sweep-DISCOVERED outliers into flagged_for_review.json — NOT applied
     (recommend-then-confirm: these are proposals for Shmuel, per the protocol).
  4. Assign stable c:<english-slug> ids, deduped.

Output:
  ontology/registry/concepts_final.json
  ontology/registry/flagged_for_review.json
"""
import json, glob, re, unicodedata, collections
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
REG = MAPJS / "ontology/registry"
nf = lambda s: re.sub(r"\s+", " ", (s or "").strip())
CANT = re.compile(r"[֑-ֽֿ֯]")
KEEP = re.compile(r"[^ְ-ׇּׁׂא-ת]")
vocal = lambda w: KEEP.sub("", CANT.sub("", unicodedata.normalize("NFC", w or "")))

concepts = json.loads((REG / "concepts.json").read_text())
by_tmp = {c["tmp_id"]: c for c in concepts}
occ_by_id = {json.loads(l)["id"]: json.loads(l)
             for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()}

# ---- 1. glosses ------------------------------------------------------------
sweep = {}
for f in glob.glob(str(REG / "sweep/*.json")):
    d = json.loads(Path(f).read_text())
    if not d.get("_failed"):
        sweep[d["tmp_id"]] = d
batch_gloss = {}
for f in glob.glob(str(REG / "glosses/batch_*.json")):
    d = json.loads(Path(f).read_text())
    if not d.get("_failed"):
        batch_gloss.update(d)

for c in concepts:
    g = None
    if c["tmp_id"] in sweep:
        g = sweep[c["tmp_id"]].get("gloss_en")
    if not g:
        g = batch_gloss.get(c["tmp_id"])
    if not g:
        g = c.get("gloss_en")
    c["gloss_en"] = g

# ---- 2. approved homograph splits -----------------------------------------
# form: decisions -> {surface: {vocalized: approve|reject}}
splits = collections.defaultdict(dict)
for k, v in json.loads((REG / "decisions.json").read_text()).items():
    if k.startswith("form:"):
        surf, voc = k[len("form:"):].split("::", 1)
        splits[nf(surf)][vocal(voc)] = v

new_concepts = []
for c in list(concepts):
    split_forms = [f for f in c["forms"] if f in splits and
                   any(val == "reject" for val in splits[f].values())]
    if not split_forms:
        continue
    # partition this concept's occurrences by the display vocalization of the split form
    keep_occ, moved = [], collections.defaultdict(list)
    for oid in c["occ_ids"]:
        o = occ_by_id.get(oid)
        disp = ""
        for side in ("source", "target"):
            if nf(o.get(f"{side}_surface", "")) in split_forms:
                disp = vocal(o.get(f"{side}_display", ""))
                break
        # is this display a rejected vocalization of any split form?
        rejected_here = None
        for f in split_forms:
            if disp in splits[f] and splits[f][disp] == "reject":
                rejected_here = disp
                break
        if rejected_here:
            moved[rejected_here].append(oid)
        else:
            keep_occ.append(oid)
    c["occ_ids"] = keep_occ
    for voc, oids in moved.items():
        nc = {"tmp_id": c["tmp_id"] + ":split:" + voc, "canonical_he": voc,
              "gloss_en": None, "forms": c["forms"], "occ_ids": oids,
              "provenance": {"source": "homograph_split", "from": c["tmp_id"], "voc": voc}}
        # borrow the split concept's gloss from a sweep outlier note if present
        sw = sweep.get(c["tmp_id"], {})
        for o in sw.get("outliers", []):
            if vocal(o.get("actual_sense_he", "")) == voc:
                nc["gloss_en"] = o.get("actual_gloss_en")
        new_concepts.append(nc)
concepts += new_concepts

# ---- 3. sweep-discovered outliers -> review queue (NOT applied) -------------
flagged = []
approved_split_forms = set(splits.keys())
for tmp, d in sweep.items():
    if d.get("consistent", True):
        continue
    c = by_tmp.get(tmp, {})
    # skip outliers already handled by an approved split of this concept's forms
    if any(f in approved_split_forms for f in c.get("forms", [])):
        continue
    flagged.append({"tmp_id": tmp, "canonical_he": d.get("canonical_he"),
                    "gloss_en": d.get("gloss_en"), "confidence": d.get("confidence"),
                    "outliers": d.get("outliers", [])})

# ---- 4. stable english-slug ids -------------------------------------------
def base_slug(c):
    g = c.get("gloss_en") or ""
    m = re.match(r"\s*([a-zA-Z][a-zA-Z'-]*)", g)          # leading transliteration if any
    if m and len(m.group(1)) > 2:
        return m.group(1).lower().strip("'-")
    words = re.findall(r"[a-zA-Z]+", g.lower())
    stop = {"the", "a", "an", "of", "in", "as", "to", "and", "or", "its", "his"}
    words = [w for w in words if w not in stop]
    if words:
        return "-".join(words[:2])
    return "he-" + re.sub(r"[^\w]", "", c["canonical_he"])[:10]

seen = collections.Counter()
for c in concepts:
    b = base_slug(c)
    seen[b] += 1
    c["id"] = f"c:{b}" if seen[b] == 1 else f"c:{b}-{seen[b]}"

(REG / "concepts_final.json").write_text(json.dumps(concepts, ensure_ascii=False, indent=1))
(REG / "flagged_for_review.json").write_text(json.dumps(flagged, ensure_ascii=False, indent=1))

print(f"concepts (incl. splits): {len(concepts)}")
print(f"  homograph-split concepts added: {len(new_concepts)}")
print(f"  still gloss-less: {sum(1 for c in concepts if not c['gloss_en'])}")
print(f"sweep verdicts loaded: {len(sweep)}  | batch glosses: {len(batch_gloss)}")
print(f"NEW outliers flagged for Shmuel (not applied): {len(flagged)}")
