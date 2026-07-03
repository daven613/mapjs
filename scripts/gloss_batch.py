#!/usr/bin/env python3
"""Gloss the single-occurrence concepts — the identity anchor for forms that appear once.

These have exactly one occurrence, so there is no consistency question (that is the sweep's job
for multi-occurrence concepts). Each just needs a precise English gloss. Batched ~40 concepts per
agent for efficiency.

Input:  ontology/registry/concepts.json
Output: ontology/registry/glosses/batch_<n>.json  {tmp_id: gloss_en}   (resumable per batch)

Run (Fable, from new-sefer for the SDK venv):
  cd ~/dev/new-sefer && MODEL=claude-fable-5 uv run python -u ~/dev/mapjs/scripts/gloss_batch.py [conc] [batchsize]
"""
import asyncio, json, os, re, sys
from pathlib import Path

MODEL = os.environ.get("MODEL", "claude-fable-5")
MAPJS = Path(__file__).resolve().parent.parent
NEW_SEFER = Path.home() / "dev" / "new-sefer" / "graph_poc"
OUT = MAPJS / "ontology/registry/glosses"
MAX_RETRIES = 3
nf = lambda s: re.sub(r"\s+", " ", (s or "").strip())

from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage

SYSTEM_PROMPT = """You gloss concepts for a knowledge graph of Likutey Moharan (Rabbi Nachman of
Breslov). Each item is a Hebrew form that appears once, with its proof quote and paragraph. Write
a precise English gloss that pins the concept's identity — specific enough that a different word
sharing the same Hebrew letters could never be mistaken for it. Name what it IS (a middah, a
letter-symbol, a person, a verse, a body part, a kabbalistic term, an action, a state...), not
just a translation. Keep each to one line.

OUTPUT ONLY a JSON object mapping each tmp_id to its gloss string:
{"tmp:1234": "erekh apayim — patience/forbearance as a spiritual quality ...", "tmp:1235": "..."}
Include every tmp_id shown. No other text."""


def load_chunks():
    texts = {}
    for book in ("lm1", "lm2"):
        data = json.loads((NEW_SEFER / book / "reading.json").read_text())
        for t in data["torahs"]:
            for sec in t["sections"]:
                for sub in sec["subsections"]:
                    texts[(book, sub["key"])] = sub["text"]
    return texts


def batch_prompt(batch, occ_by_id, chunks):
    L = ["Gloss each concept below.\n"]
    for c in batch:
        oid = c["occ_ids"][0] if c["occ_ids"] else None
        o = occ_by_id.get(oid) if oid else None
        proof = (o.get("proof") if o else "") or ""
        para = ""
        if o:
            a = o["anchor"]
            for k in (a.get("chunks") or [])[:1]:
                para = (chunks.get((a.get("book"), k)) or "")[:900]
        L.append(f"{c['tmp_id']}  form={c['canonical_he']}")
        if proof:
            L.append(f"  proof: {proof[:300]}")
        if para:
            L.append(f"  paragraph: {para}")
        L.append("")
    L.append("Output only the JSON object mapping tmp_id -> gloss.")
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


async def do_batch(sem, n, batch, occ_by_id, chunks):
    fn = OUT / f"batch_{n:04d}.json"
    if fn.exists() and "_failed" not in fn.read_text()[:20]:
        return n, "skip"
    async with sem:
        last = ""
        for attempt in range(MAX_RETRIES):
            text, err = await one_call(batch_prompt(batch, occ_by_id, chunks))
            if text:
                try:
                    t = text.strip()
                    if t.startswith("```"):
                        t = t.split("```")[1]
                        t = t[4:] if t.startswith("json") else t
                    obj = json.loads(t)
                    # keep only the tmp_ids we asked for
                    ids = {c["tmp_id"] for c in batch}
                    obj = {k: v for k, v in obj.items() if k in ids}
                    fn.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
                    return n, f"{len(obj)}/{len(batch)} glossed"
                except Exception as pe:
                    last = f"parse: {pe}"
            else:
                last = err or "?"
            await asyncio.sleep(4 * (attempt + 1))
        fn.write_text(json.dumps({"_failed": True, "err": last[:300]}))
        return n, f"FAIL {last[:80]}"


async def main():
    conc = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    bs = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    concepts = json.loads((MAPJS / "ontology/registry/concepts.json").read_text())
    occ_by_id = {json.loads(l)["id"]: json.loads(l)
                 for l in (MAPJS / "ontology/occurrences/legacy_human.jsonl").open()}
    chunks = load_chunks()
    todo = [c for c in concepts if len(c["occ_ids"]) < 2 and not c["gloss_en"]]
    batches = [todo[i:i + bs] for i in range(0, len(todo), bs)]
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"{len(todo)} concepts in {len(batches)} batches, model={MODEL}, conc={conc}", flush=True)
    sem = asyncio.Semaphore(conc)
    done = 0
    for coro in asyncio.as_completed(
            [do_batch(sem, i, b, occ_by_id, chunks) for i, b in enumerate(batches)]):
        n, status = await coro
        done += 1
        print(f"[{done}/{len(batches)}] batch {n}: {status}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
