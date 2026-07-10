#!/usr/bin/env python3
"""make_trace.py — validate a story-trace "interpretation bundle" and install it for the explorer.

A bundle is the JSON that the explorer's "Story trace" mode renders: a sequence of story
beats, a set of projectable segments (each mapping picked concepts onto a Likutey Moharan
teaching with attested proof-quotes), optional bridges / unknown-slot resolutions, and the
narrative prose. `scripts/segment_project.py` plus narration fields produce it; the canonical
example is the Lost Princess (ontology/graph/story_trace.json).

Usage:
    python3 scripts/make_trace.py BUNDLE.json                 # validate + install
    cat BUNDLE.json | python3 scripts/make_trace.py -         # read from stdin
    python3 scripts/make_trace.py BUNDLE.json --slug my-story  # explicit slug
    python3 scripts/make_trace.py BUNDLE.json --check          # validate only, do not write
    python3 scripts/make_trace.py BUNDLE.json --url-only       # print a self-contained #b= URL, no file written

On success it writes ontology/graph/traces/<slug>.json and prints the deep-link URL
    http://localhost:8890/explorer.html?trace=<slug>&t=<epoch>
so a CLI session can hand a reviewer a clickable, proof-backed interpretation. With --url-only it
instead prints a fully self-contained URL that carries the whole bundle in the #b= hash (no file):
    http://localhost:8890/explorer.html#b=<base64url(deflate(bundle-json))>

The validation rules are derived from what explorer.html's story-trace renderer actually
consumes (renderTraceList / selectTraceSegment / showTraceOverview / showUnknownDetail and the
live projection it recomputes from segment ids), plus the bundle's provenance contract: every
concept id must resolve against the graph, and every projection hop must carry a proof quote and
a source reference. See specs/trace_bundle_v1.md.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

GRAPH_DIR = Path(__file__).resolve().parent.parent / "ontology" / "graph"
NODES_PATH = GRAPH_DIR / "nodes.json"
TRACES_DIR = GRAPH_DIR / "traces"
DEFAULT_PORT = 8890

REF_RE = re.compile(r"^[IVXLCDM]+:\d+[a-z]?$")   # e.g. I:10, II:40, I:280


def load_node_ids():
    """Set of every concept id in the graph — the explorer resolves trace ids against this
    (nodes.json and explorer_data.json carry the identical id set)."""
    with open(NODES_PATH, encoding="utf-8") as f:
        nodes = json.load(f)
    return {n["id"] for n in nodes}


class Validator:
    def __init__(self, node_ids):
        self.node_ids = node_ids
        self.errors = []
        self.warnings = []

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")

    def _resolves(self, where, cid, label="id"):
        if not isinstance(cid, str) or not cid:
            self.err(where, f"{label} missing or not a string (got {cid!r})")
            return False
        if cid not in self.node_ids:
            self.err(where, f"{label} '{cid}' does not resolve against ontology/graph/nodes.json")
            return False
        return True

    def _hop(self, where, hop, require_kind):
        """A projection hop must name real endpoints and carry a proof quote + source ref —
        that is the whole promise of the bundle: every step is attested, never invented."""
        if not isinstance(hop, dict):
            self.err(where, "hop is not an object")
            return
        self._resolves(where, hop.get("from"), "hop.from")
        self._resolves(where, hop.get("to"), "hop.to")
        proof = hop.get("proof")
        if not isinstance(proof, str) or not proof.strip():
            self.err(where, "hop.proof missing or empty (each hop must carry its source quote)")
        ref = hop.get("ref")
        if not isinstance(ref, list) or not ref:
            self.err(where, "hop.ref missing or empty (each hop must cite at least one teaching)")
        else:
            for r in ref:
                if not (isinstance(r, str) and REF_RE.match(r)):
                    self.warn(where, f"hop.ref entry {r!r} is not a 'I:10'-style reference")
        if require_kind and hop.get("kind") not in ("cause", "reframe"):
            self.warn(where, f"hop.kind {hop.get('kind')!r} is not 'cause' or 'reframe'")

    def _project(self, where, proj, n_ids, n_beats):
        if not isinstance(proj, dict):
            self.err(where, "project block missing or not an object")
            return
        # home: KEY must be present; value may be null (cross-Torah) or a 'I:10'-style ref
        if "home" not in proj:
            self.err(where, "project.home key missing (use null for a cross-Torah projection)")
        else:
            home = proj["home"]
            if home is not None and not (isinstance(home, str) and REF_RE.match(home)):
                self.warn(where, f"project.home {home!r} is neither null nor a 'I:10'-style ref")
        cost = proj.get("cost")
        if not isinstance(cost, (int, float)):
            self.err(where, f"project.cost missing or not a number (got {cost!r})")
        # chain: the causal spine anchors — non-empty, each entry an id that resolves
        chain = proj.get("chain")
        if not isinstance(chain, list) or not chain:
            self.err(where, "project.chain missing or empty")
        else:
            for ci, c in enumerate(chain):
                cid = c.get("id") if isinstance(c, dict) else c
                self._resolves(f"{where}.chain[{ci}]", cid, "chain id")
        # mappings: one per picked concept, pick+anchor resolve, hops attested
        mappings = proj.get("mappings")
        if not isinstance(mappings, list) or not mappings:
            self.err(where, "project.mappings missing or empty")
        else:
            if n_ids is not None and len(mappings) != n_ids:
                self.warn(where, f"project.mappings has {len(mappings)} entries but segment lists {n_ids} ids")
            for mi, m in enumerate(mappings):
                mw = f"{where}.mappings[{mi}]"
                if not isinstance(m, dict):
                    self.err(mw, "mapping is not an object")
                    continue
                self._resolves(mw, m.get("pick"), "mapping.pick")
                self._resolves(mw, m.get("anchor"), "mapping.anchor")
                if not isinstance(m.get("pcost"), (int, float)):
                    self.err(mw, f"mapping.pcost missing or not a number (got {m.get('pcost')!r})")
                kind = m.get("kind")
                hops = m.get("hops", [])
                if not isinstance(hops, list):
                    self.err(mw, "mapping.hops is not a list")
                elif hops:
                    for hi, h in enumerate(hops):
                        self._hop(f"{mw}.hops[{hi}]", h, require_kind=False)
                elif kind not in ("self", "shared"):
                    # only a same-concept ('self') or semantic-fallback ('shared') mapping may be hopless
                    self.err(mw, f"mapping has no hops but kind={kind!r} (only 'self'/'shared' may be hopless)")
        # links: causal hops joining consecutive anchors
        links = proj.get("links")
        if not isinstance(links, list):
            self.err(where, "project.links missing or not a list")
        else:
            if chain and isinstance(chain, list) and len(links) != max(0, len(chain) - 1):
                self.warn(where, f"project.links has {len(links)} entries; expected {max(0, len(chain) - 1)} for a {len(chain)}-anchor chain")
            for li, l in enumerate(links):
                lw = f"{where}.links[{li}]"
                if not isinstance(l, dict):
                    self.err(lw, "link is not an object")
                    continue
                if not isinstance(l.get("cost"), (int, float)):
                    self.err(lw, f"link.cost missing or not a number (got {l.get('cost')!r})")
                hops = l.get("hops")
                if not isinstance(hops, list) or not hops:
                    self.err(lw, "link.hops missing or empty (a link must trace at least one hop)")
                else:
                    for hi, h in enumerate(hops):
                        self._hop(f"{lw}.hops[{hi}]", h, require_kind=True)

    def validate(self, b):
        if not isinstance(b, dict):
            self.err("bundle", "top-level JSON is not an object")
            return
        # ---- required top-level keys ----
        for key in ("input", "sequence", "segments", "narrative", "narrative_by_segment"):
            if key not in b:
                self.err("bundle", f"required top-level key '{key}' is missing")

        # ---- input ----
        inp = b.get("input")
        if not isinstance(inp, dict):
            self.err("input", "missing or not an object")
        else:
            if not (isinstance(inp.get("title"), str) and inp["title"].strip()):
                self.err("input", "input.title missing or empty (it titles the trace and seeds the slug)")
            for opt in ("type", "text_summary"):
                if opt in inp and not isinstance(inp[opt], str):
                    self.warn("input", f"input.{opt} present but not a string")

        # ---- sequence ----
        seq = b.get("sequence")
        n_beats = 0
        if not isinstance(seq, list):
            self.err("sequence", "missing or not a list")
        else:
            n_beats = len(seq)
            for i, s in enumerate(seq):
                sw = f"sequence[{i}]"
                if not isinstance(s, dict):
                    self.err(sw, "beat is not an object")
                    continue
                status = s.get("status")
                if status == "known":
                    self._resolves(sw, s.get("id"), "known-beat id")
                elif status not in ("unknown", None) and not isinstance(status, str):
                    self.warn(sw, f"beat.status {status!r} is unusual (expected 'known'/'unknown')")

        # ---- segments ----
        segs = b.get("segments")
        n_segs = 0
        if not isinstance(segs, list) or not segs:
            self.err("segments", "missing or empty (need at least one projectable segment)")
        else:
            n_segs = len(segs)
            for i, seg in enumerate(segs):
                sw = f"segments[{i}]"
                if not isinstance(seg, dict):
                    self.err(sw, "segment is not an object")
                    continue
                slots = seg.get("slots")
                if not isinstance(slots, list):
                    self.err(sw, "segment.slots missing or not a list (renderer maps beats to segments by slot)")
                else:
                    for sl in slots:
                        if not (isinstance(sl, int) and 0 <= sl < n_beats):
                            self.err(sw, f"slot {sl!r} is not a valid index into sequence (0..{n_beats - 1})")
                ids = seg.get("ids")
                if not isinstance(ids, list) or not ids:
                    self.err(sw, "segment.ids missing or empty (the concepts the projection is recomputed from)")
                else:
                    for cid in ids:
                        self._resolves(sw, cid, "segment id")
                    if len(ids) < 2:
                        self.warn(sw, "segment has a single concept — no causal chain will form")
                self._project(f"{sw}.project", seg.get("project"), len(ids) if isinstance(ids, list) else None, n_beats)

        # ---- narrative + per-segment narrative ----
        if "narrative" in b and not (isinstance(b["narrative"], str) and b["narrative"].strip()):
            self.err("narrative", "present but empty (the overview elaboration must be non-empty)")
        nbs = b.get("narrative_by_segment")
        if not isinstance(nbs, list):
            self.err("narrative_by_segment", "missing or not a list")
        else:
            if n_segs and len(nbs) != n_segs:
                self.err("narrative_by_segment", f"has {len(nbs)} entries but there are {n_segs} segments (must align 1:1)")
            for i, note in enumerate(nbs):
                if not (isinstance(note, str) and note.strip()):
                    self.err(f"narrative_by_segment[{i}]", "empty (each segment needs a narrative note)")

        # ---- optional: process_notes ----
        if "process_notes" in b and not isinstance(b["process_notes"], str):
            self.warn("process_notes", "present but not a string")

        # ---- optional: bridges ----
        bridges = b.get("bridges")
        if bridges is not None:
            if not isinstance(bridges, list):
                self.err("bridges", "present but not a list")
            else:
                for i, br in enumerate(bridges):
                    bw = f"bridges[{i}]"
                    if not isinstance(br, dict):
                        self.err(bw, "bridge is not an object")
                        continue
                    if not (isinstance(br.get("note"), str) and br["note"].strip()):
                        self.err(bw, "bridge.note missing or empty")
                    if not isinstance(br.get("penalty"), (int, float)):
                        self.err(bw, f"bridge.penalty missing or not a number (got {br.get('penalty')!r})")

        # ---- optional: unknown_resolutions ----
        unk = b.get("unknown_resolutions")
        if unk is not None:
            if not isinstance(unk, list):
                self.err("unknown_resolutions", "present but not a list")
            else:
                for i, u in enumerate(unk):
                    uw = f"unknown_resolutions[{i}]"
                    if not isinstance(u, dict):
                        self.err(uw, "entry is not an object")
                        continue
                    self._resolves(uw, u.get("anchor"), "anchor")
                    if u.get("direction") not in ("prior", "next"):
                        self.err(uw, f"direction {u.get('direction')!r} must be 'prior' or 'next'")
                    cands = u.get("candidates")
                    if not isinstance(cands, list):
                        self.err(uw, "candidates missing or not a list")
                    else:
                        for ci, c in enumerate(cands):
                            cw = f"{uw}.candidates[{ci}]"
                            if not isinstance(c, dict):
                                self.err(cw, "candidate is not an object")
                                continue
                            self._resolves(cw, c.get("id"), "candidate id")


def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return s or None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Validate a story-trace bundle and install it for the explorer.")
    ap.add_argument("bundle", help="path to the bundle JSON, or '-' for stdin")
    ap.add_argument("--slug", help="install slug (default: derived from input.title)")
    ap.add_argument("--check", action="store_true", help="validate only; do not write or print a URL")
    ap.add_argument("--url-only", action="store_true",
                    help="print a SELF-CONTAINED URL with the whole bundle in the #b= hash (no traces/ file written)")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"port for the printed URL (default {DEFAULT_PORT})")
    args = ap.parse_args(argv)

    # ---- read ----
    try:
        raw = sys.stdin.read() if args.bundle == "-" else Path(args.bundle).read_text(encoding="utf-8")
    except OSError as e:
        print(f"error: cannot read bundle: {e}", file=sys.stderr)
        return 2
    try:
        bundle = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"error: bundle is not valid JSON: {e}", file=sys.stderr)
        return 2

    # ---- validate ----
    try:
        node_ids = load_node_ids()
    except OSError as e:
        print(f"error: cannot load {NODES_PATH}: {e}", file=sys.stderr)
        return 2
    v = Validator(node_ids)
    v.validate(bundle)

    for w in v.warnings:
        print(f"warning  {w}", file=sys.stderr)
    if v.errors:
        print(f"\nINVALID — {len(v.errors)} error(s):", file=sys.stderr)
        for e in v.errors:
            print(f"  error  {e}", file=sys.stderr)
        return 1

    title = (bundle.get("input") or {}).get("title", "")
    print(f"valid — {len(bundle.get('segments', []))} segment(s), "
          f"{len(bundle.get('sequence', []))} beat(s)"
          + (f", {len(v.warnings)} warning(s)" if v.warnings else "")
          + f"  [{title}]", file=sys.stderr)

    if args.check:
        return 0

    # ---- self-contained URL: embed the whole bundle in the #b= hash ----
    # deflate (zlib, RFC 1950 — matches the explorer's DecompressionStream('deflate')) then
    # url-safe base64 (no padding). The explorer decodes #b= on load exactly like ?trace=.
    if args.url_only:
        import zlib, base64
        raw = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        b64 = base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii").rstrip("=")
        url = f"http://localhost:{args.port}/explorer.html#b={b64}"
        if len(url) > 30000:
            print(f"warning  self-contained URL is {len(url)} chars (> ~30k) — some browsers/tools may truncate it; "
                  f"prefer the file form (drop --url-only) for a bundle this large", file=sys.stderr)
        print(url)
        return 0

    # ---- resolve slug + write ----
    slug = slugify(args.slug) if args.slug else slugify(title)
    if not slug:
        print("error: could not derive a slug — pass --slug", file=sys.stderr)
        return 2
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    out = TRACES_DIR / f"{slug}.json"
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out}", file=sys.stderr)

    url = f"http://localhost:{args.port}/explorer.html?trace={slug}&t={int(time.time())}"
    print(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
