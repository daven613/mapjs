#!/usr/bin/env python3
"""Sense-consistency sweep — the guardrail from docs/CANONICALIZATION.md.

For every concept that has >=2 occurrences, one agent reads the concept's gloss and EVERY
occurrence (vocalized proof + relation + partner + paragraph) and answers: does every
occurrence really mean THIS sense? A single occurrence that means something else (a שָׂדַי
'field' sitting in the שַׁדַּי 'Divine Name' bin) is flagged as an outlier with the sense it
actually belongs to. Because identity = the gloss, each occurrence is judged against the
definition, never by majority vote — so 1-in-10 and 10-in-10 mismatches both surface.

Also (re)writes a precise English gloss for the concept — the identity anchor. Concepts that
arrived without a gloss (singletons, r1 solo-rejects) get one here.

Input:  ontology/registry/concepts.json      (from apply_decisions.py)
Output: ontology/registry/sweep/<tmp_id>.json (resumable; skips existing non-failed)

Run (Fable, from new-sefer for the SDK venv):
  cd ~/dev/new-sefer && MODEL=claude-fable-5 uv run python -u ~/dev/mapjs/scripts/sweep_concepts.py [conc] [cap]
"""
import asyncio, json, os, re, sys, unicodedata
from pathlib import Path

MODEL = os.environ.get("MODEL", "claude-fable-5")
MAPJS = Path(__file__).resolve().parent.parent
NEW_SEFER = Path.home() / "dev" / "new-sefer" / "graph_poc"
OUT = MAPJS / "ontology/registry/sweep"
MAX_RETRIES = 3
CHUNK_CAP = 1600
FULL_CTX_MAX = 12

from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage

CANT = re.compile(r"[֑-ֽֿ֯]")
KEEP = re.compile(r"[^ְ-ׇּׁׂא-ת]")
skeleton = lambda w: re.sub(r"[^א-ת]", "", unicodedata.normalize("NFC", w))
vocal = lambda w: KEEP.sub("", CANT.sub("", unicodedata.normalize("NFC", w)))
nf = lambda s: re.sub(r"\s+", " ", (s or "").strip())

SYSTEM_PROMPT = """You are the sense-consistency guardrail for a knowledge graph of Likutey
Moharan (Rabbi Nachman of Breslov). A concept is a single MEANING, identified by its English
gloss. You are given one concept — its Hebrew form(s), its current gloss, and every occurrence
where its form appears (each with the vocalization found in the proof, the relation, the partner
concept, and paragraph context). Two jobs:

1. GLOSS. Write a precise English gloss that pins this concept's identity — specific enough that
   a different word sharing the same letters could never match it. If a gloss is given, refine it.

2. CONSISTENCY. Decide whether EVERY occurrence really carries this one sense. Judge each
   occurrence against the gloss, never by majority. Flag any occurrence that is actually a
   different word/sense (a homograph — מִדְבָּר desert vs מְדַבֵּר speaker; שָׂדַי field vs
   שַׁדַּי the Divine Name; מִטָּה bed vs מַטֶּה staff) or a plain mis-assignment. Inflection,
   pausal, or plene spelling variation of the SAME word is NOT an outlier (בֵּן/בֶּן, אֶרֶץ/אָרֶץ,
   משֶׁה/מֹשֶׁה). When unsure, flag it (under-merge beats silent over-merge).

OUTPUT ONLY a JSON object:
{
  "tmp_id": "<echo>",
  "gloss_en": "<precise identity gloss>",
  "consistent": true | false,
  "outliers": [
    {"occ": "occ:...", "actual_sense_he": "<the vocalized word it really is>",
     "actual_gloss_en": "<what that occurrence actually means>", "reason": "<short>"}
  ],
  "confidence": "high" | "medium" | "low"
}
consistent=true means outliers is []. Every flagged occ must be one shown to you."""


def load_chunks():
    texts = {}
    for book in ("lm1", "lm2"):
        data = json.loads((NEW_SEFER / book / "reading.json").read_text())
        for t in data["torahs"]:
            for sec in t["sections"]:
                for sub in sec["subsections"]:
                    texts[(book, sub["key"])] = sub["text"]
    return texts


def form_usages(occ_by_id, occ_ids, chunks, forms):
    fset = set(forms)
    out = []
    for oid in occ_ids:
        o = occ_by_id.get(oid)
        if not o:
            continue
        for side, other in (("source", "target"), ("target", "source")):
            if nf(o.get(f"{side}_surface", "")) not in fset:
                continue
            proof = o.get("proof") or ""
            disp = o.get(f"{side}_display") or ""
            a = o["anchor"]
            out.append({"occ": oid, "type": o["type"], "partner": o[f"{other}_surface"],
                        "where": f"{a.get('book')}:{a.get('torah')}", "voc": disp,
                        "proof": proof, "chunks": a.get("chunks") or [], "book": a.get("book")})
            break
    return out


def concept_prompt(c, occ_by_id, chunks):
    L = [f"CONCEPT tmp_id: {c['tmp_id']}",
         f"Hebrew form(s): {', '.join(c['forms'])}",
         f"Current gloss: {c['gloss_en'] or '(none — write one)'}",
         f"Canonical Hebrew: {c['canonical_he']}", ""]
    us = form_usages(occ_by_id, c["occ_ids"], chunks, c["forms"])
    L.append(f"=== {len(us)} OCCURRENCE(S) ===")
    full = len(us) <= FULL_CTX_MAX
    for u in us:
        L.append(f"[{u['occ']}] @ {u['where']} relation={u['type']} partner={u['partner']}"
                 + (f" vocalized={u['voc']}" if u["voc"] else ""))
        L.append(f"  proof: {u['proof'][:400]}")
        if full:
            for k in u["chunks"][:1]:
                txt = chunks.get((u["book"], k))
                if txt:
                    L.append(f"  paragraph ({k}): {txt[:CHUNK_CAP]}")
        L.append("")
    L.append("Output only the JSON object.")
    return "\n".join(L)


async def one_call(prompt):
    try:
        async for msg in query(prompt=prompt, options=ClaudeAgentOptions(
                system_prompt=SYSTEM_PROMPT, model=MODEL, tools=[], max_turns=1,
                permission_mode="dontAsk", cwd=str(MAPJS))):
            if isinstance(msg, ResultMessage):
                return (None, f"error: {msg.result}") if msg.is_error else (msg.result, None)
    except Exception as exc:
        return None, str(exc)
    return None, "no result"


async def sweep(sem, c, occ_by_id, chunks):
    fn = OUT / (c["tmp_id"].replace(":", "_") + ".json")
    if fn.exists() and "_failed" not in fn.read_text()[:20]:
        return c["tmp_id"], "skip"
    async with sem:
        last = ""
        for attempt in range(MAX_RETRIES):
            text, err = await one_call(concept_prompt(c, occ_by_id, chunks))
            if text:
                try:
                    t = text.strip()
                    if t.startswith("```"):
                        t = t.split("```")[1]
                        t = t[4:] if t.startswith("json") else t
                    obj = json.loads(t)
                    obj["tmp_id"] = c["tmp_id"]
                    obj["canonical_he"] = c["canonical_he"]
                    obj["model"] = MODEL
                    fn.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
                    flag = "" if obj.get("consistent", True) else f" ⚠ {len(obj.get('outliers',[]))} outlier(s)"
                    return c["tmp_id"], f"{obj.get('confidence')}{flag}"
                except Exception as pe:
                    last = f"parse: {pe}"
            else:
                last = err or "?"
            await asyncio.sleep(4 * (attempt + 1))
        fn.write_text(json.dumps({"_failed": True, "tmp_id": c["tmp_id"], "err": last[:300]}))
        return c["tmp_id"], f"FAIL {last[:100]}"


async def main():
    conc = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else None
    concepts = json.loads((MAPJS / "ontology/registry/concepts.json").read_text())
    occ_by_id = {json.loads(l)["id"]: json.loads(l)
                 for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()}
    chunks = load_chunks()

    todo = [c for c in concepts if len(c["occ_ids"]) >= 2]
    if cap:
        todo = todo[:cap]
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{len(todo)} concepts to sweep (>=2 occ), model={MODEL}, conc={conc}", flush=True)
    sem = asyncio.Semaphore(conc)
    done = flagged = 0
    for coro in asyncio.as_completed([sweep(sem, c, occ_by_id, chunks) for c in todo]):
        cid, status = await coro
        done += 1
        if "⚠" in status:
            flagged += 1
        print(f"[{done}/{len(todo)}] {cid}: {status}", flush=True)
    print(f"DONE. {flagged} concept(s) flagged with outliers.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
