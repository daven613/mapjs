#!/usr/bin/env python3
"""Apply the reviewed canonicalization decisions -> concept registry (nodes).

Deterministic assembly. Sources of truth, in precedence order (later overrides earlier):
  1. adjudications/*.json      base grouping of each multi-member cluster into concepts + glosses
  2. rejects_refigured.json    Shmuel's final re-placement of the forms he marked reject in round 1
  3. user_rulings.json         Shmuel's explicit standing rulings (outrank everything)
  4. decisions.json            per-item approve/reject across rounds (merge:/refig:/form:/cl::form)

Output:
  ontology/registry/concepts.json   the concept layer (nodes), each with provenance
  ontology/registry/apply_audit.json  assignment audit (orphans, collisions, split-needed)

Nothing here calls an LLM. Glosses for singletons are left null (filled by the enrichment
workflow) and every concept with >=2 occurrences is marked for the sense-consistency sweep.
"""
import json, glob, os, re, collections
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
REG = MAPJS / "ontology/registry"
OCC = MAPJS / "ontology/occurrences/legacy_human.jsonl"


def load(p, default=None):
    p = Path(p)
    return json.loads(p.read_text()) if p.exists() else default


def nf(s):
    """Normalize a surface form: collapse whitespace (some cluster members carry stray
    leading spaces that the occurrence surfaces do not)."""
    return re.sub(r"\s+", " ", (s or "").strip())


# ---- load inputs -----------------------------------------------------------
clusters_doc = load(REG / "clusters_candidates.json")
clusters = clusters_doc["clusters"]
statement_forms = set(nf(s) for s in clusters_doc["statements"])
by_cluster = {c["id"]: c for c in clusters}
multi = {c["id"]: c for c in clusters if len(c.get("members", [])) > 1}
singles = {c["id"]: c for c in clusters if len(c.get("members", [])) == 1}

adj = {}
for f in glob.glob(str(REG / "adjudications/*.json")):
    d = json.load(open(f))
    adj[d["cluster_id"]] = d

refig = load(REG / "rejects_refigured.json", {})
rulings = load(REG / "user_rulings.json", {})
decisions = load(REG / "decisions.json", {})

# occurrences indexed by surface form and by id
occ_by_form = collections.defaultdict(list)   # form -> [occ_id]
occ_rec = {}
disp_by_form_occ = {}                          # (form, occ_id, side) -> vocalized display
with open(OCC) as fh:
    for line in fh:
        o = json.loads(line)
        occ_rec[o["id"]] = o
        for side in ("source", "target"):
            form = nf(o.get(f"{side}_surface", ""))
            if form:
                occ_by_form[form].append(o["id"])
                disp_by_form_occ[(form, o["id"], side)] = o.get(f"{side}_display", form)

# homograph splits from decisions: form -> {vocalized: approve|reject}
form_splits = collections.defaultdict(dict)
for k, v in decisions.items():
    if k.startswith("form:"):
        body = k[len("form:"):]
        surf, voc = body.split("::", 1)
        form_splits[nf(surf)][voc] = v

r1_rejects = {(k.split("::", 1)[0], nf(k.split("::", 1)[1])) for k, v in decisions.items()
              if "::" in k and not k.startswith(("merge:", "refig:", "form:")) and v == "reject"}


def slug(he, gloss=""):
    """Provisional English slug from gloss (preferred) or transliteration placeholder.
    Real English slugs are assigned/deduped in the enrichment workflow."""
    base = ""
    if gloss:
        # first few english words of the gloss
        words = re.findall(r"[a-zA-Z]+", gloss.lower())
        base = "-".join(words[:3])
    if not base:
        base = "he-" + re.sub(r"[^\w]", "", he)[:12]
    return base


# ---- build concepts --------------------------------------------------------
concepts = []          # each: {tmp_id, canonical_he, gloss_en, forms:[], occ_ids:[], provenance:{}}
form_to_concept = {}   # form -> tmp_id  (for edge compile later); may be overridden by split
audit = {"orphans": [], "collisions": [], "split_needed": [], "notes": []}
cid_counter = [0]


def new_concept(he, gloss, forms, provenance):
    cid_counter[0] += 1
    tmp = f"tmp:{cid_counter[0]:04d}"
    forms = [nf(f) for f in forms if nf(f)]
    occ_ids = sorted({oid for f in forms for oid in occ_by_form.get(f, [])})
    c = {"tmp_id": tmp, "canonical_he": he, "gloss_en": gloss,
         "forms": sorted(set(forms)), "occ_ids": occ_ids, "provenance": provenance}
    concepts.append(c)
    for f in forms:
        if f in form_to_concept:
            audit["collisions"].append({"form": f, "a": form_to_concept[f], "b": tmp})
        form_to_concept[f] = tmp
    return c


# 1. multi-member clusters
for cid, cl in multi.items():
    a = adj.get(cid)
    all_forms = [m["form"] for m in cl["members"]]
    if cid in rulings and cid in refig:
        # explicit ruling + refigured boxes are authoritative
        for box in refig[cid]["boxes"]:
            new_concept(box["he"], box["en"], box["forms"],
                        {"cluster": cid, "source": "user_ruling+refig"})
        placed = {f for box in refig[cid]["boxes"] for f in box["forms"]}
        leftover = [f for f in all_forms if f not in placed]
        if leftover and a:
            for con in a["concepts"]:
                lf = [m["form"] for m in con["members"] if m["form"] in leftover]
                if lf:
                    new_concept(con["canonical_he"], con["gloss_en"], lf,
                                {"cluster": cid, "source": "adjudication(leftover)"})
    elif cid in refig:
        # refigured boxes replace the rejected forms; remaining adj concepts keep the rest
        placed = {f for box in refig[cid]["boxes"] for f in box["forms"]}
        for box in refig[cid]["boxes"]:
            new_concept(box["he"], box["en"], box["forms"],
                        {"cluster": cid, "source": "refig"})
        if a:
            for con in a["concepts"]:
                lf = [m["form"] for m in con["members"] if m["form"] not in placed]
                if lf:
                    new_concept(con["canonical_he"], con["gloss_en"], lf,
                                {"cluster": cid, "source": "adjudication"})
    elif a:
        # straight from adjudication concepts, dropping any r1-rejected form into its own concept
        for con in a["concepts"]:
            keep = [m["form"] for m in con["members"] if (cid, nf(m["form"])) not in r1_rejects]
            drop = [m["form"] for m in con["members"] if (cid, nf(m["form"])) in r1_rejects]
            if keep:
                new_concept(con["canonical_he"], con["gloss_en"], keep,
                            {"cluster": cid, "source": "adjudication"})
            for f in drop:
                new_concept(f, None, [f], {"cluster": cid, "source": "r1_reject_solo"})
    else:
        audit["notes"].append(f"{cid}: multi-member but no adjudication")

# 2. singletons -> own concept, gloss to be filled by workflow
for cid, cl in singles.items():
    f = cl["members"][0]["form"]
    if f in form_to_concept:
        continue  # already placed via a cluster
    new_concept(f, None, [f], {"cluster": cid, "source": "singleton"})

# 3. homograph splits: carve a form's occurrences by vocalization
for surf, votes in form_splits.items():
    rejected_vocs = [v for v, val in votes.items() if val == "reject"]
    if not rejected_vocs:
        continue
    audit["split_needed"].append({"form": surf, "reject_vocs": rejected_vocs,
                                   "note": "occurrences whose display matches a rejected vocalization "
                                           "must move to a distinct concept (done at edge-compile "
                                           "using per-occurrence display)"})

# ---- coverage check --------------------------------------------------------
concept_forms = set(nf(m["form"]) for c in clusters for m in c["members"])
covered = set(form_to_concept)
orphan_forms = concept_forms - covered - statement_forms
for f in sorted(orphan_forms):
    audit["orphans"].append(f)

# every occurrence: are both sides assigned to a concept or a statement?
unassigned_occ = 0
for oid, o in occ_rec.items():
    for side in ("source", "target"):
        form = nf(o.get(f"{side}_surface", ""))
        if form and form not in form_to_concept and form not in statement_forms:
            unassigned_occ += 1
            audit.setdefault("unassigned_forms", []).append(form)

# ---- write -----------------------------------------------------------------
(REG / "concepts.json").write_text(json.dumps(concepts, ensure_ascii=False, indent=1))
(REG / "apply_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=1))

need_sweep = sum(1 for c in concepts if len(c["occ_ids"]) >= 2)
need_gloss = sum(1 for c in concepts if not c["gloss_en"])
print(f"concepts built:            {len(concepts)}")
print(f"  from multi-member:       {sum(1 for c in concepts if c['provenance']['source'] not in ('singleton',))}")
print(f"  singletons:              {sum(1 for c in concepts if c['provenance']['source']=='singleton')}")
print(f"concept-forms covered:     {len(covered)} / {len(concept_forms)}")
print(f"orphan forms (no concept): {len(orphan_forms)}")
print(f"form/concept collisions:   {len(audit['collisions'])}")
print(f"homograph splits pending:  {len(audit['split_needed'])}")
print(f"occ sides unassigned:      {unassigned_occ}")
print(f"concepts needing gloss:    {need_gloss}")
print(f"concepts needing sweep:    {need_sweep}  (>=2 occurrences)")
