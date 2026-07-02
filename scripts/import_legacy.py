#!/usr/bin/env python3
"""Phase 0 importer: legacy torahData.js edges -> occurrence records (ENGINE_DESIGN.md §2.2).

- Normalizes the legacy `type` variants (cause / 'eitza ' -> eitza; original kept in legacy_type).
- Resolves `reference` -> (book, torah): ref >= 1000 => lm2 torah (ref-1000), else lm1 torah ref.
- Anchors every edge to the new-sefer chunk layer by locating its verbatim `proof` quote
  (niqqud/punctuation-insensitive) in the torah's Hebrew text. An edge whose proof cannot be
  found anywhere in its assigned torah is flagged, never guessed.

Output: ontology/occurrences/legacy_human.jsonl  (one occurrence per line)
        ontology/occurrences/import_report.json  (match stats + flagged edges)

Idempotent: pure function of inputs, safe to re-run.
"""
import json, re, unicodedata, sys
from pathlib import Path
from bisect import bisect_right

MAPJS = Path(__file__).resolve().parent.parent
NEW_SEFER = Path.home() / "dev" / "new-sefer" / "graph_poc"

HEBREW = re.compile(r"[֐-ת]")
STRIP = re.compile(r"[֑-ׇ]")            # niqqud + te'amim
NONLETTER = re.compile(r"[^א-ת]+")       # keep only Hebrew letters


def norm(s: str) -> str:
    """Reduce Hebrew text to bare consonant stream: immune to niqqud, punctuation, quotes, spacing."""
    s = unicodedata.normalize("NFC", s or "")
    s = STRIP.sub("", s)
    return NONLETTER.sub("", s)


def hebrew_lines(interlinear: str) -> str:
    """The chunk text alternates Hebrew/English lines; keep the Hebrew-majority lines."""
    out = []
    for line in interlinear.splitlines():
        letters = len(HEBREW.findall(line))
        if letters and letters >= len(line.strip()) * 0.3:
            out.append(line)
    return "\n".join(out)


def load_book(book: str):
    """-> {torah_number: [(chunk_key, chunk_id, norm_hebrew), ...]}"""
    data = json.loads((NEW_SEFER / book / "reading.json").read_text())
    torahs = {}
    for t in data["torahs"]:
        chunks = []
        for sec in t["sections"]:
            for sub in sec["subsections"]:
                chunks.append((sub["key"], sub["id"], norm(hebrew_lines(sub["text"]))))
        torahs[t["torah"]] = chunks
    return torahs


def build_stream(chunks):
    stream, offsets = "", []          # offsets[i] = start position of chunk i in stream
    for _, _, h in chunks:
        offsets.append(len(stream))
        stream += h
    return stream, offsets


def find_anchor(chunks, proof_n):
    """Locate normalized proof in the torah's concatenated chunk stream.
    Exact/prefix match first; then window voting (the human's proof quotes sometimes splice
    phrases or drift from our edition, but their k-mers still land in the right chunks).
    Returns (chunk_keys_spanned, method) or (None, reason)."""
    stream, offsets = build_stream(chunks)
    if not proof_n:
        return None, "empty_proof"
    for probe, method in ((proof_n, "full"), (proof_n[:80], "prefix80"), (proof_n[:40], "prefix40")):
        if len(probe) < 12:
            continue
        pos = stream.find(probe)
        if pos < 0:
            continue
        first = bisect_right(offsets, pos) - 1
        last = bisect_right(offsets, pos + len(proof_n if method == "full" else probe) - 1) - 1
        return [chunks[i][0] for i in range(first, min(last, len(chunks) - 1) + 1)], method

    # window voting: slide k-mers over the proof, map each hit to a chunk, take the hit span
    k = min(24, max(12, len(proof_n) // 2))
    hit_chunks = []
    for i in range(0, max(1, len(proof_n) - k + 1), max(1, k // 3)):
        w = proof_n[i:i + k]
        pos = stream.find(w)
        if pos >= 0:
            hit_chunks.append(bisect_right(offsets, pos) - 1)
    if hit_chunks:
        first, last = min(hit_chunks), max(hit_chunks)
        if last - first > 4:          # scattered hits: keep only the densest chunk
            best = max(set(hit_chunks), key=hit_chunks.count)
            first = last = best
        return [chunks[i][0] for i in range(first, last + 1)], "windows"
    return None, "not_found"


def main():
    raw = json.loads((MAPJS / "ontology/occurrences/_legacy_raw.json").read_text())
    books = {"lm1": load_book("lm1"), "lm2": load_book("lm2")}
    streams = {(b, t): build_stream(chunks)[0]
               for b, ts in books.items() for t, chunks in ts.items()}

    out, report = [], {"total": len(raw), "anchored": 0, "by_method": {}, "flagged": []}
    for i, e in enumerate(raw):
        eid = int(e["id"]) if e.get("id") is not None else f"noid_{i}"
        legacy_type = (e.get("type") or "").strip()
        etype = "eitza" if legacy_type in ("cause", "eitza") else legacy_type  # bechina stays
        ref = e.get("reference")
        book, torah = (None, None)
        if isinstance(ref, (int, float)) and ref:
            ref = int(ref)
            book, torah = ("lm2", ref - 1000) if ref >= 1000 else ("lm1", ref)
            if torah not in books.get(book, {}):
                book, torah = None, None

        proof_n = norm(e.get("proof", ""))
        anchor_chunks, method = (None, "no_reference")
        if book:
            anchor_chunks, method = find_anchor(books[book][torah], proof_n)
        if anchor_chunks is None and len(proof_n) >= 25:
            # proof absent from the assigned torah (or no reference): try to relocate globally,
            # but only accept an unambiguous hit
            probe = proof_n[len(proof_n) // 2 - 15: len(proof_n) // 2 + 15]
            hits = [(b, t) for b, ts in books.items() for t, _ in ts.items()
                    if probe in streams[(b, t)]]
            if len(hits) == 1:
                book, torah = hits[0]
                anchor_chunks, method = find_anchor(books[book][torah], proof_n)
                if anchor_chunks:
                    method = "relocated+" + method

        occ = {
            "id": f"occ:legacy:{eid}",
            "type": etype,
            "legacy_type": legacy_type,
            "source_surface": e["node1_id"],
            "target_surface": e["node2_id"],
            "source_display": e.get("node1_text"),
            "target_display": e.get("node2_text"),
            "proof": e.get("proof"),
            "explicitness": "explicit",
            "anchor": {"book": book, "torah": torah, "chunks": anchor_chunks,
                        "match": method, "legacy_reference": e.get("reference")},
            "polarity": {"is_good": e.get("is_good"), "is_bad": e.get("is_bad")},
            "extractor": "human-2019",
            "confidence": 1.0,
        }
        out.append(occ)
        report["by_method"][method] = report["by_method"].get(method, 0) + 1
        if anchor_chunks:
            report["anchored"] += 1
        else:
            report["flagged"].append({"id": occ["id"], "reference": e.get("reference"),
                                       "reason": method, "proof_head": (e.get("proof") or "")[:80]})

    dest = MAPJS / "ontology/occurrences/legacy_human.jsonl"
    dest.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n")
    (MAPJS / "ontology/occurrences/import_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1))
    print(f"wrote {len(out)} occurrences -> {dest}")
    print(f"anchored {report['anchored']}/{report['total']}  methods={report['by_method']}")


if __name__ == "__main__":
    sys.exit(main())
