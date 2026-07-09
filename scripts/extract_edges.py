#!/usr/bin/env python3
"""Extract NEW bechina/eitza/equation edges from the source text with Fable.

Goes beyond the 4,168 legacy human edges: reads each source chunk of Likutey Moharan and asks
the model for the relations explicitly stated there, as candidate occurrence records with proof
quotes. Output is a CANDIDATE layer (extractor = the model) — never merged into the human
evidence layer automatically; reviewed later like everything else.

Design for unattended, offline-tolerant, deadline-bounded operation:
  * IDEMPOTENT — one output file per chunk; existing outputs are skipped. Only writes on success,
    so a chunk that failed (offline / rate-limited) is simply retried next run — nothing to undo.
  * DEADLINE — env EXTRACT_DEADLINE (epoch seconds). No new model call starts past it.
  * OFFLINE-TOLERANT — connection/usage errors are swallowed; that chunk is left undone (not
    marked failed) so the daemon retries it once the network / quota returns.

Run:  cd ~/dev/new-sefer && MODEL=claude-fable-5 EXTRACT_DEADLINE=<epoch> \
        uv run python -u ~/dev/mapjs/scripts/extract_edges.py [conc] [max_chunks]
"""
import asyncio, json, os, sys, time
from pathlib import Path

MODEL = os.environ.get("MODEL", "claude-sonnet-5")   # v2 resume: Fable window closed 2026-07-04
DEADLINE = int(os.environ.get("EXTRACT_DEADLINE", "0")) or None
MAPJS = Path(__file__).resolve().parent.parent
NEW_SEFER = Path.home() / "dev" / "new-sefer" / "graph_poc"
OUT = MAPJS / "ontology/occurrences/ai_extracted"
MAX_RETRIES = 2                 # per chunk, per run; the daemon re-runs for more
CHUNK_CAP = 2400

from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage

SYSTEM_PROMPT = """You extract the relational structure of Likutey Moharan (Rabbi Nachman of
Breslov) for a knowledge graph. Given ONE passage of the holy text (Hebrew), report ONLY the
relations the text itself states in THIS passage. Three relation types:

- bechina (בחינה / "aspect of"): the text identifies concept X as an aspect/manifestation of
  concept Y ("X הוא בחינת Y", quoting a verse as the aspect of something).
- eitza (עצה / causal counsel): the text says X brings about / leads to / damages Y —
  BOTH the positive flow ("על ידי X זוכין ל-Y") AND the negative flow: blemish/lack
  statements ("על ידי פגם ה-X בא Z", "כשאין X..."), and direct-harm statements ("הכעס מביא ל-Z").
- equation (explicit "שהוא"/"היינו"/"זה" identity): X IS literally equated with Y.

Each eitza edge also carries its polarity and mode:
- polarity: "builds" (leads to a good/desired Y) or "harms" (causes damage/a bad Z).
- via: "presence" (X itself / doing X) or "absence" (the LACK/פגם of X).
  For harms+absence, source_he is the thing whose LACK does the damage (e.g. for
  "על ידי פגם האמונה באים חלאים": source_he=אמונה, target_he=חלאים, polarity=harms, via=absence).
- bechina/equation edges: always polarity="neutral", via="presence".

RULES:
- Extract only what is explicitly in the passage. Do not infer beyond the text. If nothing
  clear, return an empty list.
- Use the actual Hebrew concept phrases as they appear. Keep proofs verbatim from the passage.
- A concept is a noun/noun-phrase (a middah, letter, person, verse, sefirah, body part...),
  not a whole sentence.
- Direction for eitza is always cause → effect.

OUTPUT ONLY a JSON object:
{"edges": [
  {"type": "bechina|eitza|equation", "source_he": "...", "target_he": "...",
   "proof": "<verbatim Hebrew from the passage>", "explicitness": "explicit|inferred",
   "polarity": "builds|harms|neutral", "via": "presence|absence"}
]}
No prose. Empty edges list is valid."""

VALID_POLARITY = {"builds", "harms", "neutral"}
VALID_VIA = {"presence", "absence"}


def validate_edges(edges):
    """Schema-v2 gate: bad enum values reject the whole chunk (retried later), per spec AC3."""
    for e in edges:
        if e.get("type") not in ("bechina", "eitza", "equation"):
            raise ValueError(f"bad type: {e.get('type')}")
        # tolerate omitted polarity/via on non-eitza by filling the spec defaults
        if e.get("type") != "eitza":
            e.setdefault("polarity", "neutral"); e.setdefault("via", "presence")
        if e.get("polarity") not in VALID_POLARITY or e.get("via") not in VALID_VIA:
            raise ValueError(f"bad polarity/via: {e.get('polarity')}/{e.get('via')}")
    return edges


def load_chunks():
    out = []
    for book in ("lm1", "lm2"):
        p = NEW_SEFER / book / "reading.json"
        if not p.exists():
            continue
        data = json.loads(p.read_text())
        for t in data["torahs"]:
            for sec in t["sections"]:
                for sub in sec["subsections"]:
                    out.append({"book": book, "torah": t.get("torah"),
                                "key": sub["key"], "text": sub["text"]})
    return out


def prompt(ch):
    return (f"Passage {ch['book']} torah {ch['torah']} chunk {ch['key']}:\n\n"
            f"{ch['text'][:CHUNK_CAP]}\n\nExtract the relations. Output only the JSON object.")


async def one_call(p):
    try:
        async for msg in query(prompt=p, options=ClaudeAgentOptions(
                system_prompt=SYSTEM_PROMPT, model=MODEL, tools=[], max_turns=1,
                permission_mode="dontAsk", cwd=str(MAPJS))):
            if isinstance(msg, ResultMessage):
                return (None, f"error: {msg.result}") if msg.is_error else (msg.result, None)
    except Exception as exc:
        return None, str(exc)
    return None, "no result"


def past_deadline():
    return DEADLINE and time.time() >= DEADLINE


async def do_chunk(sem, ch):
    fn = OUT / f"{ch['book']}_{ch['key']}.json"
    if fn.exists():
        return ch["key"], "skip"
    if past_deadline():
        return ch["key"], "deadline"
    async with sem:
        if past_deadline():
            return ch["key"], "deadline"
        for attempt in range(MAX_RETRIES):
            text, err = await one_call(prompt(ch))
            if text:
                try:
                    t = text.strip()
                    if t.startswith("```"):
                        t = t.split("```")[1]
                        t = t[4:] if t.startswith("json") else t
                    obj = json.loads(t)
                    edges = validate_edges(obj.get("edges", []))
                    rec = {"book": ch["book"], "torah": ch["torah"], "chunk": ch["key"],
                           "model": MODEL, "extractor": f"ai:{MODEL}", "schema": 2,
                           "edges": edges}
                    tmp = fn.with_suffix(".tmp")
                    tmp.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
                    tmp.rename(fn)          # atomic — a partial write can never be seen as done
                    return ch["key"], f"{len(edges)} edges"
                except Exception as pe:
                    err = f"parse: {pe}"
            # failure (network / usage / parse): do NOT write — leave undone for a later run
            await asyncio.sleep(3 * (attempt + 1))
        return ch["key"], f"defer ({(err or '?')[:60]})"


async def main():
    conc = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else None
    OUT.mkdir(parents=True, exist_ok=True)
    all_chunks = load_chunks()
    todo = [c for c in all_chunks if not (OUT / f"{c['book']}_{c['key']}.json").exists()]
    chunks = todo[:cap] if cap else todo
    print(f"{len(chunks)} chunks this pass ({len(all_chunks)-len(todo)}/{len(all_chunks)} done, "
          f"{len(todo)} remaining), model={MODEL}, conc={conc}, "
          f"deadline={'set' if DEADLINE else 'none'}", flush=True)
    if past_deadline():
        print("PAST DEADLINE — nothing to do.", flush=True)
        return
    sem = asyncio.Semaphore(conc)
    done = defer = 0
    for coro in asyncio.as_completed([do_chunk(sem, c) for c in chunks]):
        key, status = await coro
        done += 1
        if status.startswith("defer") or status == "deadline":
            defer += 1
        if done % 25 == 0 or status not in ("skip",):
            print(f"[{done}/{len(chunks)}] {key}: {status}", flush=True)
    print(f"RUN DONE. deferred/blocked this run: {defer}", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
