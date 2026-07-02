#!/usr/bin/env python3
"""Phase 1 step 3 (docs/CANONICALIZATION.md): compile adjudications into the human review list.

Reads ontology/registry/adjudications/*.json and produces ontology/registry/MERGE_REVIEW.md,
ordered so Shmuel's attention goes where it matters:
  1. QUESTIONS — every merge tiered `question` and every flagged concept, one by one, full context.
  2. LIKELY — compact but with reasons.
  3. OBVIOUS — bulk list of typographic merges (scan, don't study).
Approving: edit the checkbox lines ([ ] -> [x] approve, [-] reject), then the apply step
(scripts/apply_registry.py, Phase 1 step 4 — not yet written) consumes only checked items.
Nothing merges until then.
"""
import json
from pathlib import Path

MAPJS = Path(__file__).resolve().parent.parent
ADJ = MAPJS / "ontology/registry/adjudications"


def main():
    files = sorted(ADJ.glob("cl_*.json"))
    concepts_q, concepts_l, concepts_o, failed = [], [], [], []
    n_concepts = 0
    for f in files:
        d = json.loads(f.read_text())
        if d.get("_failed"):
            failed.append(d)
            continue
        for c in d["concepts"]:
            n_concepts += 1
            if len(c["members"]) < 2 and not c.get("flags"):
                continue                      # singleton concept, nothing to review
            tiers = {m["tier"] for m in c["members"][1:]}
            entry = (d["cluster_id"], c, d.get("notes", ""))
            if "question" in tiers or c.get("flags"):
                concepts_q.append(entry)
            elif "likely" in tiers:
                concepts_l.append(entry)
            elif len(c["members"]) > 1:
                concepts_o.append(entry)

    L = ["# Merge review — Phase 1 canonicalization", "",
         f"{len(files)} clusters adjudicated -> {n_concepts} proposed concepts.",
         "Mark each item: `[x]` approve · `[-]` reject (keep separate) · leave `[ ]` undecided.",
         "Nothing is applied until you mark it and we run the apply step.", ""]

    L += ["## 1. QUESTIONS & FLAGS — decide one by one", ""]
    for cid, c, notes in concepts_q:
        L.append(f"### {c['canonical_he']} — {c['gloss_en']}")
        L.append(f"({cid}{', flags: ' + ', '.join(c['flags']) if c.get('flags') else ''})")
        for m in c["members"]:
            mark = "x" if m["tier"] == "obvious" and m is c["members"][0] else " "
            L.append(f"- [{mark}] `{m['form']}` — {m['tier']}: {m.get('note','')}")
        if notes:
            L.append(f"> adjudicator: {notes}")
        L.append("")

    L += ["## 2. LIKELY — approve unless something looks off", ""]
    for cid, c, _ in concepts_l:
        members = " · ".join(f"`{m['form']}`" for m in c["members"])
        why = "; ".join(m.get("note", "") for m in c["members"][1:] if m.get("note"))[:160]
        L.append(f"- [ ] **{c['canonical_he']}** ({c['gloss_en'][:60]}): {members}")
        L.append(f"      _{why}_")
    L.append("")

    L += ["## 3. OBVIOUS — typographic variants, scan quickly", ""]
    for cid, c, _ in concepts_o:
        members = " · ".join(f"`{m['form']}`" for m in c["members"])
        L.append(f"- [x] **{c['canonical_he']}**: {members}")
    L.append("")

    if failed:
        L += ["## Failed adjudications (re-run needed)", ""]
        L += [f"- {d['cluster_id']}: {d.get('err','')[:120]}" for d in failed] + [""]

    dest = MAPJS / "ontology/registry/MERGE_REVIEW.md"
    dest.write_text("\n".join(L) + "\n")
    print(f"{dest}")
    print(f"questions/flagged: {len(concepts_q)}  likely: {len(concepts_l)}  "
          f"obvious multi-member: {len(concepts_o)}  failed: {len(failed)}")


if __name__ == "__main__":
    main()
