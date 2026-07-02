#!/usr/bin/env python3
"""Phase 1 step 2 (docs/CANONICALIZATION.md): AI adjudication of candidate clusters.

One cluster per agent call. The agent sees every member form with its usage counts, torah
locations, and proof quotes, and must SPLIT the cluster into distinct concepts and tier each
proposed merge (obvious/likely/question). It merges nothing itself — output is proposals only,
written one file per cluster to ontology/registry/adjudications/<cluster_id>.json.

Resumable: existing non-failed outputs are skipped.

Run (uses new-sefer's venv for claude_agent_sdk, session auth — never an API key):
  cd ~/dev/new-sefer && uv run python ~/dev/mapjs/scripts/adjudicate_clusters.py [concurrency] [max_clusters]
"""
import asyncio, json, os, sys, time
from pathlib import Path

MODEL = os.environ.get("MODEL", "claude-opus-4-8")
MAPJS = Path(__file__).resolve().parent.parent
OUT_DIR = MAPJS / "ontology/registry/adjudications"
MAX_RETRIES = 3

from claude_agent_sdk import query
from claude_agent_sdk.types import ClaudeAgentOptions, ResultMessage

SYSTEM_PROMPT = """You are adjudicating candidate concept clusters for a knowledge graph of
Rabbi Nachman of Breslov's Likutey Moharan. A mechanical pass grouped surface forms (Hebrew
phrases used as graph nodes) that MIGHT name the same concept. Your job: split each cluster
into its truly distinct concepts and tier each grouping. You are the safeguard — a wrong merge
silently corrupts the whole graph.

BINDING RULES (from the project's canonicalization protocol):
1. UNDER-MERGE BEATS OVER-MERGE. When in doubt, keep forms as separate concepts.
2. The definite article can change the concept: הצדיק ("THE tzaddik") often means the archetype
   (the tzaddik of the generation), while צדיק can be any righteous person. Same for החכם/חכם
   etc. If both readings are plausible across the cited usages, put the forms in SEPARATE
   concepts and flag "archetype-question" — never silently merge these.
3. Merges that hold only in one Torah's context ("the chacham = the tzaddik in Torah N") are
   NOT identity — keep separate and note it.
4. Different possessed/construct heads are different concepts (שמו של הקב"ה ≠ חמתו של הקב"ה).
   An action/state about X is not X (בנין בית המקדש ≠ בית המקדש; תקון כח המדמה ≠ כח המדמה).
5. Pure orthographic variants ARE the same concept: niqqud, quotation marks around the same
   words, trailing spaces, plene/defective spelling, a verse quoted with/without gershayim.
6. Read the proof quotes — context is king. Judge from usage, not from the strings alone.

TIERS for each member you place under a concept:
- "obvious": orthographic/typographic variant, zero semantic risk.
- "likely": strong evidence of same referent in these usages (say why in note).
- "question": plausible but genuinely uncertain — the human will decide. Default when unsure.
The FIRST member of a concept (its representative) always gets tier "obvious".

OUTPUT: ONLY a JSON object, no prose, no code fences:
{
  "cluster_id": "<id>",
  "concepts": [
    {
      "canonical_he": "<best canonical Hebrew form, unvocalized>",
      "gloss_en": "<short English gloss; state the distinction if a near-twin exists>",
      "members": [
        {"form": "<exact surface form>", "tier": "obvious|likely|question", "note": "<why, brief>"}
      ],
      "flags": []   // e.g. "archetype-question", "verse-quote", "local-equation"
    }
  ],
  "notes": "<anything the human reviewer must know, or empty>"
}
Every input member form must appear in exactly one concept, verbatim."""


def cluster_prompt(c):
    lines = [f"Cluster {c['id']} — {c['size']} candidate forms. Mechanical signals: {', '.join(c['signals'])}.", ""]
    for m in c["members"]:
        lines.append(f"FORM: {m['form']}")
        lines.append(f"  used {m['count']}x in torahs: {', '.join(m['torahs'][:8]) or 'unknown'}")
        for p in m["proofs"]:
            lines.append(f"  proof: {p}")
        lines.append("")
    lines.append("Adjudicate per the rules. Output only the JSON object.")
    return "\n".join(lines)


async def one_call(prompt):
    try:
        async for msg in query(prompt=prompt, options=ClaudeAgentOptions(
                system_prompt=SYSTEM_PROMPT, model=MODEL, tools=[], max_turns=1,
                permission_mode="dontAsk", cwd=str(MAPJS))):
            if isinstance(msg, ResultMessage):
                if msg.is_error:
                    return None, f"error: {msg.result}"
                return msg.result, None
    except Exception as exc:
        return None, str(exc)
    return None, "no result"


import re, unicodedata
_NIQQUD = re.compile(r"[֑-ׇ]")

def _fkey(s):
    return _NIQQUD.sub("", unicodedata.normalize("NFC", s or "")).strip()


def parse_result(text, cluster):
    t = text.strip()
    if t.startswith("```"):
        t = t.split("```")[1]
        t = t[4:] if t.startswith("json") else t
    obj = json.loads(t)
    # match members back to exact input surface forms: exact niqqud-stripped key first,
    # then a letters-only key (agents normalize quotes/geresh) against still-unmatched inputs
    _loose = lambda s: re.sub(r"[^א-ת]+", "", _fkey(s))
    unmatched = {m["form"] for m in cluster["members"]}
    exact = {_fkey(f): f for f in unmatched}
    for c in obj["concepts"]:
        for m in c["members"]:
            f = exact.get(_fkey(m["form"]))
            if f not in unmatched:
                cands = [x for x in unmatched if _loose(x) == _loose(m["form"])]
                if not cands:
                    raise ValueError(f"unknown member: {m['form']!r}")
                # >1 candidate means the inputs themselves differ only typographically —
                # interchangeable, so any assignment is correct
                f = cands[0]
            unmatched.discard(f)
            m["form"] = f
    if unmatched:
        raise ValueError(f"missing members: {sorted(unmatched)}")
    return obj


async def adjudicate(sem, cluster):
    out = OUT_DIR / f"{cluster['id'].replace(':', '_')}.json"
    if out.exists() and "_failed" not in out.read_text()[:20]:
        return cluster["id"], "skip"
    async with sem:
        last = ""
        for attempt in range(MAX_RETRIES):
            text, err = await one_call(cluster_prompt(cluster))
            if text:
                try:
                    obj = parse_result(text, cluster)
                    obj["model"] = MODEL
                    out.write_text(json.dumps(obj, ensure_ascii=False, indent=1))
                    return cluster["id"], f"ok ({len(obj['concepts'])} concepts)"
                except Exception as pe:
                    last = f"parse: {pe}"
            else:
                last = err or "?"
            await asyncio.sleep(4 * (attempt + 1))
        out.write_text(json.dumps({"_failed": True, "cluster_id": cluster["id"], "err": last[:300]}))
        return cluster["id"], f"FAIL {last[:120]}"


async def main():
    conc = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    cap = int(sys.argv[2]) if len(sys.argv) > 2 else None
    data = json.loads((MAPJS / "ontology/registry/clusters_candidates.json").read_text())
    clusters = [c for c in data["clusters"] if c["size"] > 1]
    if cap:
        clusters = clusters[:cap]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(conc)
    t0 = time.time()
    done = 0
    for coro in asyncio.as_completed([adjudicate(sem, c) for c in clusters]):
        cid, status = await coro
        done += 1
        print(f"[{done}/{len(clusters)}] {cid}: {status}", flush=True)
    print(f"finished in {time.time()-t0:.0f}s")


if __name__ == "__main__":
    asyncio.run(main())
