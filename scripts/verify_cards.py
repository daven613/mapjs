#!/usr/bin/env python3
"""Full-context verification pass (docs/CANONICALIZATION.md — "nothing mechanical goes unchecked").

One Opus agent per item, where an item is either:
  - a review card (proposed concept group from round-1 adjudication), or
  - a homograph-candidate form (multiple vocalizations found in the proofs).

Unlike round 1 (which saw <=3 trimmed proofs per form), each agent here sees EVERY occurrence
of every member form: its vocalization in the proof, the relation and partner concept, and the
full paragraph (chunk) text. Output is a RECOMMENDATION for the human — approve/reject per
member, per-occurrence sense assignments when one written form covers several words/senses,
an English reason, and a confidence level. Nothing is applied.

Outputs: ontology/registry/verifications/<item>.json   (resumable; skips non-failed existing)

Run:
  cd ~/dev/new-sefer && uv run python -u ~/dev/mapjs/scripts/verify_cards.py [concurrency] [max_items]
"""
import asyncio, json, os, re, sys, unicodedata
from pathlib import Path
from collections import defaultdict

MODEL = os.environ.get("MODEL", "claude-opus-4-8")
MAPJS = Path(__file__).resolve().parent.parent
NEW_SEFER = Path.home() / "dev" / "new-sefer" / "graph_poc"
OUT = MAPJS / "ontology/registry/verifications"
MAX_RETRIES = 3
CHUNK_CAP = 1800          # chars of paragraph context per occurrence
FULL_CTX_MAX = 12         # occurrences with full paragraphs; beyond that, proof-only

from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage

CANT = re.compile(r"[֑-ֽֿ֯]")
KEEP = re.compile(r"[^ְ-ׇּׁׂא-ת]")
skeleton = lambda w: re.sub(r"[^א-ת]", "", unicodedata.normalize("NFC", w))
vocal = lambda w: KEEP.sub("", CANT.sub("", unicodedata.normalize("NFC", w)))

SYSTEM_PROMPT = """You are the verification layer for concept canonicalization in a knowledge
graph of Likutey Moharan. A first pass proposed concept groupings from limited context; you now
see EVERY occurrence with full paragraph context, and your job is to produce a final
RECOMMENDATION for the human reviewer (Shmuel — expert in the text, short on time). He will
confirm or veto; write your reason so he can judge it in seconds.

RULES (binding, from the project protocol):
- Under-merge beats over-merge. Uncertain -> keep separate.
- One written (consonantal) form may be several different WORDS (homographs: מִדְבָּר desert vs
  מְדַבֵּר speaker; מִטָּה bed vs מַטֶּה staff). The vocalization shown for each occurrence is
  authoritative evidence. Inflection/pausal/plene variation of the SAME word is NOT a homograph
  (בֵּן/בֶּן, אֶרֶץ/אָרֶץ, משֶׁה/מֹשֶׁה = same concept).
- The definite article can mark the archetype (הצדיק) vs generic (צדיק) — split when usage shows it.
- Explicit textual equations ("שהוא") are equation edges, never merges.
- Every concept needs an English gloss precise enough to serve as its identity (semantic IDs).

OUTPUT: ONLY a JSON object:
{
  "id": "<item id, echo it>",
  "verdict": "confirm" | "revise",
  "concepts": [
    {"canonical_he": "...", "gloss_en": "...",
     "members": [{"form": "<exact surface form>", "recommend": "approve|reject"}],
     "occ_ids": ["occ:..."]}   // which occurrences belong to THIS concept (critical for homographs)
  ],
  "reason_for_human": "<2-3 plain-English sentences: what you checked and why this is right>",
  "confidence": "high" | "medium" | "low"
}
"confirm" = round-1 grouping stands. "revise" = you changed it (split/merged/reassigned) — the
concepts array is the corrected proposal either way. Every occurrence id shown to you must appear
in exactly one concept's occ_ids."""


def load_chunks():
    texts = {}
    for book in ("lm1", "lm2"):
        data = json.loads((NEW_SEFER / book / "reading.json").read_text())
        for t in data["torahs"]:
            for sec in t["sections"]:
                for sub in sec["subsections"]:
                    texts[(book, sub["key"])] = sub["text"]
    return texts


def form_usages(occs, chunks, form):
    """every occurrence of a surface form, with vocalization + paragraph context"""
    out = []
    ftoks = [skeleton(t) for t in form.split() if skeleton(t)]
    for o in occs:
        for side, other in (("source", "target"), ("target", "source")):
            if o[f"{side}_surface"] != form:
                continue
            proof = o.get("proof") or ""
            voc = None
            pwords = [(skeleton(w), vocal(w)) for w in proof.split()]
            for i in range(len(pwords) - len(ftoks) + 1):
                if ftoks and [pwords[i + j][0] for j in range(len(ftoks))] == ftoks:
                    voc = " ".join(pwords[i + j][1] for j in range(len(ftoks)))
                    break
            a = o["anchor"]
            out.append({"occ": o["id"], "type": o["type"], "partner": o[f"{other}_surface"],
                        "where": f"{a.get('book')}:{a.get('torah')}", "voc": voc,
                        "proof": proof, "chunks": a.get("chunks") or [], "book": a.get("book")})
    return out


def item_prompt(item, occs, chunks):
    L = [f"ITEM ID: {item['id']}"]
    if item["kind"] == "card":
        L.append("Round-1 proposal (verify or revise):")
        for c in item["concepts"]:
            L.append(f"  CONCEPT: {c['canonical_he']} — {c['gloss_en']}")
            for m in c["members"]:
                L.append(f"    member: {m['form']} (tier {m['tier']})")
        forms = [m["form"] for c in item["concepts"] for m in c["members"]]
    else:
        L.append("Homograph-candidate form (multiple vocalizations in proofs). Decide: one word "
                 "with inflection variants, or several distinct words? Assign every occurrence.")
        forms = [item["form"]]
    L.append("")
    for f in forms:
        us = form_usages(occs, chunks, f)
        L.append(f"=== ALL USAGES OF: {f}  ({len(us)} occurrences) ===")
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


async def verify(sem, item, occs, chunks):
    fn = OUT / (item["id"].replace(":", "_").replace("#", "_").replace("/", "_") + ".json")
    if fn.exists() and "_failed" not in fn.read_text()[:20]:
        return item["id"], "skip"
    async with sem:
        last = ""
        for attempt in range(MAX_RETRIES):
            text, err = await one_call(item_prompt(item, occs, chunks))
            if text:
                try:
                    t = text.strip()
                    if t.startswith("```"):
                        t = t.split("```")[1]
                        t = t[4:] if t.startswith("json") else t
                    obj = json.loads(t)
                    obj["id"] = item["id"]
                    obj["kind"] = item["kind"]
                    obj["model"] = MODEL
                    fn.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
                    return item["id"], f"{obj.get('verdict')} ({obj.get('confidence')})"
                except Exception as pe:
                    last = f"parse: {pe}"
            else:
                last = err or "?"
            await asyncio.sleep(4 * (attempt + 1))
        fn.write_text(json.dumps({"_failed": True, "id": item["id"], "err": last[:300]}))
        return item["id"], f"FAIL {last[:100]}"


async def main():
    conc = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else None
    occs = [json.loads(l) for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()]
    chunks = load_chunks()

    items = []
    for f in sorted((MAPJS / "ontology/registry/adjudications").glob("cl_*.json")):
        d = json.loads(f.read_text())
        cs = [c for c in d.get("concepts", []) if len(c["members"]) > 1 or c.get("flags")]
        if cs:
            items.append({"id": f"card:{d['cluster_id']}", "kind": "card", "concepts": cs})
    for h in json.loads((MAPJS / "ontology/registry/homograph_candidates.json").read_text()):
        items.append({"id": f"form:{h['form']}", "kind": "homograph", "form": h["form"]})
    if cap:
        items = items[:cap]
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{len(items)} items to verify")
    sem = asyncio.Semaphore(conc)
    done = 0
    for coro in asyncio.as_completed([verify(sem, it, occs, chunks) for it in items]):
        iid, status = await coro
        done += 1
        print(f"[{done}/{len(items)}] {iid}: {status}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
