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


PARENS = re.compile(r"\([^)]*\)")


def norm(s: str) -> str:
    """Reduce Hebrew text to bare consonant stream: immune to niqqud, punctuation, quotes, spacing."""
    s = unicodedata.normalize("NFC", s or "")
    s = STRIP.sub("", s)
    return NONLETTER.sub("", s)


def norm_noparens(s: str) -> str:
    """Like norm(), but first drops parenthesized spans (source citations, footnote letters) —
    the legacy proof quotes and our edition often differ only in these."""
    return norm(PARENS.sub(" ", s or ""))


def hebrew_lines(interlinear: str) -> str:
    """The chunk text alternates Hebrew/English lines; keep the Hebrew-majority lines."""
    out = []
    for line in interlinear.splitlines():
        letters = len(HEBREW.findall(line))
        if letters and letters >= len(line.strip()) * 0.3:
            out.append(line)
    return "\n".join(out)


def load_book(book: str):
    """-> {torah_number: [(chunk_key, chunk_id, norm_hebrew, norm_noparens_hebrew), ...]}"""
    data = json.loads((NEW_SEFER / book / "reading.json").read_text())
    torahs = {}
    for t in data["torahs"]:
        chunks = []
        for sec in t["sections"]:
            for sub in sec["subsections"]:
                heb = hebrew_lines(sub["text"])
                chunks.append((sub["key"], sub["id"], norm(heb), norm_noparens(heb)))
        torahs[t["torah"]] = chunks
    return torahs


def build_stream(chunks, col=2):
    stream, offsets = "", []          # offsets[i] = start position of chunk i in stream
    for c in chunks:
        offsets.append(len(stream))
        stream += c[col]
    return stream, offsets


def find_anchor_one(chunks, proof_n, col):
    """Locate normalized proof in the torah's concatenated chunk stream (one normalization).
    Exact/prefix match first; then window voting (the human's proof quotes sometimes splice
    phrases or drift from our edition, but their k-mers still land in the right chunks).
    Returns (chunk_keys_spanned, method) or (None, reason)."""
    stream, offsets = build_stream(chunks, col)
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


def find_anchor(chunks, proof_raw):
    """Try plain normalization, then parenthesis-stripped normalization (proof quotes and our
    edition often differ only in inline citations like (תהלים כ"ה) or footnote letters)."""
    res, method = find_anchor_one(chunks, norm(proof_raw), 2)
    if res is not None:
        return res, method
    res, method = find_anchor_one(chunks, norm_noparens(proof_raw), 3)
    if res is not None:
        return res, method + "-noparens"
    return None, method


def main():
    raw = json.loads((MAPJS / "ontology/occurrences/_legacy_raw.json").read_text())
    books = {"lm1": load_book("lm1"), "lm2": load_book("lm2")}
    streams = {(b, t): build_stream(chunks)[0]
               for b, ts in books.items() for t, chunks in ts.items()}
    streams_np = {(b, t): build_stream(chunks, 3)[0]
                  for b, ts in books.items() for t, chunks in ts.items()}
    overrides_path = MAPJS / "ontology/occurrences/anchor_overrides.json"
    overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}

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

        proof_raw = e.get("proof", "")
        anchor_chunks, method = (None, "no_reference")
        if book:
            anchor_chunks, method = find_anchor(books[book][torah], proof_raw)
        if anchor_chunks is None:
            # proof absent from the assigned torah (or no reference): try to relocate globally,
            # but only accept an unambiguous hit
            for pn, pool in ((norm(proof_raw), streams), (norm_noparens(proof_raw), streams_np)):
                if len(pn) < 25:
                    continue
                probe = pn[len(pn) // 2 - 15: len(pn) // 2 + 15]
                hits = [bt for bt, s in pool.items() if probe in s]
                if len(hits) == 1:
                    book, torah = hits[0]
                    anchor_chunks, method = find_anchor(books[book][torah], proof_raw)
                    if anchor_chunks:
                        method = "relocated+" + method
                        break
        if anchor_chunks is None and book:
            # last resort: trust the torah-level reference, leave chunk resolution open
            anchor_chunks, method = [], "torah_only"

        occ_id = f"occ:legacy:{eid}"
        anchor = {"book": book, "torah": torah, "chunks": anchor_chunks,
                  "match": method, "legacy_reference": e.get("reference")}
        if occ_id in overrides:
            anchor = {**overrides[occ_id], "match": "override",
                      "legacy_reference": e.get("reference")}
        occ = {
            "id": occ_id,
            "type": etype,
            "legacy_type": legacy_type,
            "source_surface": e["node1_id"],
            "target_surface": e["node2_id"],
            "source_display": e.get("node1_text"),
            "target_display": e.get("node2_text"),
            "proof": e.get("proof"),
            "explicitness": "explicit",
            "anchor": anchor,
            "polarity": {"is_good": e.get("is_good"), "is_bad": e.get("is_bad")},
            "extractor": "human-2019",
            "confidence": 1.0,
        }
        out.append(occ)
        m = occ["anchor"]["match"]
        report["by_method"][m] = report["by_method"].get(m, 0) + 1
        if occ["anchor"].get("chunks") or occ["anchor"].get("locus"):
            report["anchored"] += 1
        elif m == "torah_only":
            report.setdefault("torah_only", 0)
            report["torah_only"] += 1
        else:
            report["flagged"].append({"id": occ["id"], "reference": e.get("reference"),
                                       "reason": m, "proof_head": (e.get("proof") or "")[:80]})

    dest = MAPJS / "ontology/occurrences/legacy_human.jsonl"
    dest.write_text("\n".join(json.dumps(o, ensure_ascii=False) for o in out) + "\n")
    (MAPJS / "ontology/occurrences/import_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=1))
    print(f"wrote {len(out)} occurrences -> {dest}")
    print(f"anchored {report['anchored']}/{report['total']}  methods={report['by_method']}")


if __name__ == "__main__":
    sys.exit(main())
