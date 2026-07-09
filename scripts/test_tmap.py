#!/usr/bin/env python3
"""
Pytest suite for scripts/tmap.py, written PURELY from specs/api_v1.md.

tmap.py does not exist yet when this file is authored: these tests are the
executable spec. They are expected to fail/skip until tmap.py is implemented,
and to pass once it faithfully implements specs/api_v1.md.

Run with:
    pytest scripts/test_tmap.py -v
or directly (pytest not required, falls back to a tiny built-in runner):
    python3 scripts/test_tmap.py

Coverage map (see final report emitted by the calling harness):
    AC1 load/adjacency symmetry     -> test_ac1_*
    AC2 search quality               -> test_ac2_*
    AC3 project on the spec triple   -> test_ac3_*
    AC4 project on other triples     -> test_ac4_*
    AC5 causal_path forward-only     -> test_ac5_*, test_causal_path_*
    AC6 CLI ok/error surface         -> test_ac6_*
    AC7 proof fields / UTF-8         -> test_ac7_*
    unit: tokens/score_one/hop_cost/causal_path/aspect_path on synthetic graphs
    CLI surface: search/concept/aspects/advice/effects/path/common/torah/match/
                 project/selftest, unknown-id -> exit 1
"""

import copy
import json
import math
import subprocess
import sys
import tempfile
import time
import types
from pathlib import Path

# ---------------------------------------------------------------------------
# pytest / fallback shim
# ---------------------------------------------------------------------------
try:
    import pytest
    _HAVE_PYTEST = True
except ImportError:  # pragma: no cover - only exercised when pytest is absent
    _HAVE_PYTEST = False

    class _Skipped(Exception):
        pass

    class _Approx:
        def __init__(self, value, rel=1e-6, abs=1e-9):
            self.value = value
            self.rel = rel
            self.abs = abs

        def __eq__(self, other):
            try:
                return math.isclose(other, self.value, rel_tol=self.rel, abs_tol=self.abs)
            except TypeError:
                return other == self.value

        def __repr__(self):
            return "approx(%r)" % (self.value,)

    class _RaisesCtx:
        def __init__(self, exc_type):
            self.exc_type = exc_type

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            if exc_type is None:
                raise AssertionError("expected %r to be raised" % (self.exc_type,))
            return issubclass(exc_type, self.exc_type)

    class _Mark:
        @staticmethod
        def skipif(cond, reason=""):
            def deco(fn):
                if cond:
                    def wrapper(*a, **k):
                        raise _Skipped(reason)
                    wrapper.__name__ = getattr(fn, "__name__", "test")
                    return wrapper
                return fn
            return deco

        @staticmethod
        def parametrize(*a, **k):
            def deco(fn):
                return fn
            return deco

    class _FallbackPytest:
        Skipped = _Skipped
        mark = _Mark()

        @staticmethod
        def skip(reason=""):
            raise _Skipped(reason)

        @staticmethod
        def fail(reason=""):
            raise AssertionError(reason)

        @staticmethod
        def approx(value, rel=1e-6, abs=1e-9):
            return _Approx(value, rel, abs)

        @staticmethod
        def raises(exc_type):
            return _RaisesCtx(exc_type)

    pytest = _FallbackPytest()


# ---------------------------------------------------------------------------
# Paths / module under test
# ---------------------------------------------------------------------------
SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent
TMAP_PY = SCRIPTS_DIR / "tmap.py"
REAL_DATA = REPO_ROOT / "ontology" / "graph" / "explorer_data.json"

sys.path.insert(0, str(SCRIPTS_DIR))

try:
    import tmap  # noqa: E402  (module under test; may not exist yet)
    TMAP_IMPORTABLE = True
    TMAP_IMPORT_ERROR = None
except Exception as _e:  # ImportError or any error raised at import time
    tmap = None
    TMAP_IMPORTABLE = False
    TMAP_IMPORT_ERROR = repr(_e)

needs_tmap_import = pytest.mark.skipif(
    not TMAP_IMPORTABLE,
    reason="scripts/tmap.py is not importable yet (%s)" % (TMAP_IMPORT_ERROR,),
)
needs_real_data = pytest.mark.skipif(
    not REAL_DATA.exists(),
    reason="ontology/graph/explorer_data.json not found at %s" % (REAL_DATA,),
)


# ---------------------------------------------------------------------------
# Generic duck-typing helpers (per task instructions: be tolerant of
# reasonable signature differences, e.g. project(graph, ids) vs project(ids))
# ---------------------------------------------------------------------------
def flex_call(fn, arg_variants):
    """Try each positional-args tuple in `arg_variants` against `fn`; return
    the result of the first one that doesn't raise TypeError. Non-TypeError
    exceptions propagate immediately (they indicate a real bug, not a
    signature mismatch)."""
    last = None
    for args in arg_variants:
        try:
            return fn(*args)
        except TypeError as e:
            last = e
            continue
    raise last


def call_hop_cost(edge_dict, home):
    """hop_cost(e, home) per spec. Tolerate edges represented as dicts (the
    documented JSON shape) or as simple attribute-bearing objects."""
    try:
        return tmap.hop_cost(edge_dict, home)
    except (AttributeError, TypeError):
        ns = types.SimpleNamespace(**edge_dict)
        return tmap.hop_cost(ns, home)


_LOADER_NAMES = [
    "load_data", "load_graph", "build_graph", "load", "build",
    "init", "setup", "load_json", "from_dict", "make_graph",
]


def try_load_synthetic(data):
    """Best-effort: get tmap's internal state (by_id/tokx/ctxx/idf/adj/...)
    to reflect `data` instead of whatever it loaded at import/CLI time.

    Returns a truthy graph handle to try passing explicitly to algorithm
    functions (if the loader returned one), True as a generic "loaded into
    globals" sentinel, or False if no known loader entrypoint worked -- in
    which case the calling test should pytest.skip() rather than fail, since
    the module's internal wiring differs from what this harness guessed.
    """
    if tmap is None:
        return False
    n_expected = len(data["nodes"])

    def _looks_loaded():
        by_id = getattr(tmap, "by_id", None)
        return isinstance(by_id, dict) and len(by_id) == n_expected

    # 1) in-memory dict argument
    for name in _LOADER_NAMES:
        fn = getattr(tmap, name, None)
        if not callable(fn):
            continue
        try:
            result = fn(copy.deepcopy(data))
        except Exception:
            continue
        if _looks_loaded():
            return result if result is not None else True
        if result is not None and hasattr(result, "by_id"):
            try:
                if len(result.by_id) == n_expected:
                    return result
            except Exception:
                pass

    # 2) path-based loaders
    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, tf, ensure_ascii=False)
    tf.close()
    for name in _LOADER_NAMES:
        fn = getattr(tmap, name, None)
        if not callable(fn):
            continue
        for arg in (tf.name, Path(tf.name)):
            try:
                result = fn(arg)
            except Exception:
                continue
            if _looks_loaded():
                return result if result is not None else True
            if result is not None and hasattr(result, "by_id"):
                try:
                    if len(result.by_id) == n_expected:
                        return result
                except Exception:
                    pass
    return False


def call_algo(fn, positional_args, graph):
    """Call an algorithm function tolerating either a global-state design
    (positional_args only, per the literal signatures in the spec, e.g.
    causal_path(a,b,home,strict)) or an explicit-graph design
    (graph prepended/appended)."""
    variants = [tuple(positional_args)]
    if graph not in (None, False, True):
        variants.append((graph,) + tuple(positional_args))
        variants.append(tuple(positional_args) + (graph,))
    return flex_call(fn, variants)


def call_project(ids, graph=None):
    """project(concept_ids) per spec, but the task brief explicitly flags
    this one as ambiguous: try project(ids) and project(graph, ids)."""
    variants = [(ids,)]
    if graph not in (None, False, True):
        variants.append((graph, ids))
        variants.append((ids, graph))
    return flex_call(tmap.project, variants)


# ---------------------------------------------------------------------------
# CLI helpers
# ---------------------------------------------------------------------------
def run_cli(args, data_path=None, timeout=30):
    cmd = [sys.executable, str(TMAP_PY)] + list(args)
    if data_path is not None:
        cmd += ["--data", str(data_path)]
    return subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", timeout=timeout
    )


def cli_json(args, data_path=None, timeout=30):
    """Run the CLI and parse stdout as JSON, failing loudly (with stdout and
    stderr in the message) if the process didn't emit parseable JSON."""
    proc = run_cli(args, data_path=data_path, timeout=timeout)
    try:
        parsed = json.loads(proc.stdout)
    except Exception as e:
        raise AssertionError(
            "CLI %r did not emit valid JSON (rc=%s): %s\nSTDOUT:\n%s\nSTDERR:\n%s"
            % (args, proc.returncode, e, proc.stdout, proc.stderr)
        )
    return proc, parsed


def write_json(tmp_path, name, data):
    p = tmp_path / name
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def _hop_edge(h):
    """Extract the edge dict out of a causal_path/aspect_path hop, tolerating
    either the spec-prose key name "edge" or an implementation abbreviation
    like "e", and either a dict or an attribute-bearing object."""
    v = h.get("edge", h.get("e"))
    if v is None:
        return None
    if isinstance(v, dict):
        return v
    return {
        "s": getattr(v, "s", None), "t": getattr(v, "t", None),
        "ty": getattr(v, "ty", None), "ref": getattr(v, "ref", None),
        "p": getattr(v, "p", None),
    }


def assert_all_proofs_are_strings(obj):
    """AC7: every proof field is a string (possibly empty), never null."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("proof", "p"):
                assert isinstance(v, str), (
                    "proof field %r is not a string: %r" % (k, v)
                )
            else:
                assert_all_proofs_are_strings(v)
    elif isinstance(obj, list):
        for item in obj:
            assert_all_proofs_are_strings(item)


# ---------------------------------------------------------------------------
# Synthetic data: small graph for tokens/score_one/hop_cost/causal_path/
# aspect_path unit tests.
#
#   eitza (directed, cause->effect): a -> b -> c
#   bechina (undirected aspect):     a - c ,  c - d
#
# Proof strings are deliberately distinct per edge so ctxx (context tokens)
# differs per node, exercising both the tokx-hit and ctxx-hit branches of
# score_one.
# ---------------------------------------------------------------------------
def _node(id_, he, gloss, kind="concept", deg=0, refs=None):
    return {"id": id_, "he": he, "gloss": gloss, "kind": kind, "deg": deg,
            "refs": refs or []}


def _edge(s, t, ty, ref, p="", w=1):
    return {"s": s, "t": t, "ty": ty, "w": w, "p": p, "ref": ref}


SMALL_GRAPH = {
    "nodes": [
        _node("c:a", "א", "joy and light", deg=2, refs=["I:1"]),
        _node("c:b", "ב", "sorrow and dark", deg=1, refs=["I:1", "I:2"]),
        _node("c:c", "ג", "faith bridge", deg=3, refs=["I:2"]),
        _node("c:d", "ד", "unrelated node", deg=0, refs=["I:3"]),
    ],
    "edges": [
        _edge("c:a", "c:b", "eitza", ["I:1"], p="the flame word"),
        _edge("c:b", "c:c", "eitza", ["I:2"], p="the bridge quote"),
        _edge("c:a", "c:c", "bechina", ["I:1"], p="the anchor here"),
        _edge("c:c", "c:d", "bechina", ["I:3"], p="the final note"),
    ],
    "torahs": [],
}

# Deterministic, hand-verified expected score_one() values for SMALL_GRAPH
# (idf computed with N_nodes=4, per specs/api_v1.md's own df/idf formula).
EXPECTED_SCORES = {
    ("joy", "c:a"): 1.190164894348924,
    ("joy", "c:b"): 0.0,
    ("and2", "c:a"): 1.0075621676341528,   # q={'and':2}
    ("and2", "c:b"): 1.0630705421264541,   # q={'and':2}
    ("bridge", "c:c"): 0.5738238627740007,
    ("bridge", "c:b"): 0.21975330556981412,  # ctxx-branch (0.35x) hit
    ("the", "c:a"): 0.0,  # idf==0 because 'the' occurs on every node -> no signal
}


# A variant of SMALL_GRAPH with one fully isolated node (no edges at all),
# used solely for genuine-unreachability tests. Kept as a separate graph so
# it doesn't perturb N_nodes/idf in the score_one expectations above.
ISOLATED_GRAPH = {
    "nodes": SMALL_GRAPH["nodes"] + [
        _node("c:iso", "בודד", "a fully isolated node with no edges", deg=0, refs=["Z:1"]),
    ],
    "edges": list(SMALL_GRAPH["edges"]),
    "torahs": [],
}


# ---------------------------------------------------------------------------
# Synthetic data: dedicated deterministic graph for project() invariants.
#
# 3 picks (x1,x2,x3) all share ref "H:1" and nothing else; a forward eitza
# chain x1->x2->x3 also tagged "H:1" gives project() a single unambiguous
# home, self-mapping for every pick (no bechina edges => aspect_dist only
# reaches each node itself), and a fully causal (kind='cause') link chain.
# Hand-derived expected total cost: 0 (pcosts) + 0.12 + 0.12 = 0.24.
# ---------------------------------------------------------------------------
PROJECT_GRAPH = {
    "nodes": [
        _node("c:x1", "א1", "project pick one", deg=1, refs=["H:1"]),
        _node("c:x2", "א2", "project pick two", deg=1, refs=["H:1"]),
        _node("c:x3", "א3", "project pick three", deg=1, refs=["H:1"]),
    ],
    "edges": [
        _edge("c:x1", "c:x2", "eitza", ["H:1"], p="x1 causes x2"),
        _edge("c:x2", "c:x3", "eitza", ["H:1"], p="x2 causes x3"),
    ],
    "torahs": [],
}


# ---------------------------------------------------------------------------
# Synthetic data: v1.3 `why -k` alternatives.
#
# Two node-disjoint, equal-cost (1.6+1.6=3.2 each, home=None) forward-eitza
# routes wa->wd: via wb and via wc. Exactly 2 distinct causal chains exist,
# so k=3 must still return only 2, with non-decreasing (here: equal) cost and
# distinct hop-sequences.
# ---------------------------------------------------------------------------
WHY_GRAPH = {
    "nodes": [
        _node("c:wa", "א", "why start", deg=1, refs=["W:1"]),
        _node("c:wb", "ב", "route via b", deg=1, refs=["W:1"]),
        _node("c:wc", "ג", "route via c", deg=1, refs=["W:1"]),
        _node("c:wd", "ד", "why end", deg=1, refs=["W:1"]),
    ],
    "edges": [
        _edge("c:wa", "c:wb", "eitza", ["W:1"], p="a causes b"),
        _edge("c:wb", "c:wd", "eitza", ["W:1"], p="b causes d"),
        _edge("c:wa", "c:wc", "eitza", ["W:1"], p="a causes c"),
        _edge("c:wc", "c:wd", "eitza", ["W:1"], p="c causes d"),
    ],
    "torahs": [],
}


# ===========================================================================
# Unit tests: tokens()
# ===========================================================================
@needs_tmap_import
def test_tokens_ascii_min_length_three():
    assert tmap.tokens("Joy and Light") == ["joy", "and", "light"]


@needs_tmap_import
def test_tokens_lowercases():
    assert tmap.tokens("JOY") == ["joy"]


@needs_tmap_import
def test_tokens_ascii_too_short_excluded():
    # 'ab' and 'is' are below the 3-letter ascii threshold
    assert tmap.tokens("ab is on cat") == ["cat"]


@needs_tmap_import
def test_tokens_hebrew_min_length_two():
    assert tmap.tokens("אב") == ["אב"]  # 'אב' (2 chars) kept


@needs_tmap_import
def test_tokens_hebrew_single_char_excluded():
    assert tmap.tokens("א") == []  # single Hebrew char excluded


@needs_tmap_import
def test_tokens_none_safe():
    assert tmap.tokens(None) == []


@needs_tmap_import
def test_tokens_empty_string():
    assert tmap.tokens("") == []


@needs_tmap_import
def test_tokens_mixed_hebrew_english():
    out = tmap.tokens("emunah אמונה faith")
    assert "emunah" in out
    assert "faith" in out
    assert "אמונה" in out


# ===========================================================================
# Unit tests: hop_cost(e, home)
# ===========================================================================
@needs_tmap_import
def test_hop_cost_home_match_is_cheap():
    e = _edge("c:a", "c:b", "eitza", ["I:22"])
    assert call_hop_cost(e, "I:22") == pytest.approx(0.12)


@needs_tmap_import
def test_hop_cost_home_match_beats_edge_type():
    # even a bechina edge is 0.12 when home matches its ref
    e = _edge("c:a", "c:b", "bechina", ["I:22"])
    assert call_hop_cost(e, "I:22") == pytest.approx(0.12)


@needs_tmap_import
def test_hop_cost_eitza_default():
    e = _edge("c:a", "c:b", "eitza", ["I:1"])
    assert call_hop_cost(e, "I:99") == pytest.approx(1.6)
    assert call_hop_cost(e, None) == pytest.approx(1.6)


@needs_tmap_import
def test_hop_cost_bechina_default():
    e = _edge("c:a", "c:b", "bechina", ["I:1"])
    assert call_hop_cost(e, "I:99") == pytest.approx(2.0)
    assert call_hop_cost(e, None) == pytest.approx(2.0)


@needs_tmap_import
def test_hop_cost_home_absent_from_multi_ref():
    e = _edge("c:a", "c:b", "eitza", ["I:1", "I:2", "I:3"])
    assert call_hop_cost(e, "I:2") == pytest.approx(0.12)
    assert call_hop_cost(e, "I:9") == pytest.approx(1.6)


# ===========================================================================
# Unit tests: score_one(q, cid) on SMALL_GRAPH (best-effort in-process load)
# ===========================================================================
@needs_tmap_import
def test_score_one_synthetic_values():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip(
            "no discoverable graph-loading entrypoint on tmap for a synthetic "
            "graph (tried: %s); score_one needs tokx/ctxx/idf/deg built from "
            "a loaded graph" % (", ".join(_LOADER_NAMES),)
        )
    got_joy_a = call_algo(tmap.score_one, ({"joy": 1}, "c:a"), graph)
    got_joy_b = call_algo(tmap.score_one, ({"joy": 1}, "c:b"), graph)
    got_and_a = call_algo(tmap.score_one, ({"and": 2}, "c:a"), graph)
    got_and_b = call_algo(tmap.score_one, ({"and": 2}, "c:b"), graph)
    got_bridge_c = call_algo(tmap.score_one, ({"bridge": 1}, "c:c"), graph)
    got_bridge_b = call_algo(tmap.score_one, ({"bridge": 1}, "c:b"), graph)
    got_the_a = call_algo(tmap.score_one, ({"the": 1}, "c:a"), graph)

    assert got_joy_a == pytest.approx(EXPECTED_SCORES[("joy", "c:a")])
    assert got_joy_b == pytest.approx(EXPECTED_SCORES[("joy", "c:b")])
    assert got_and_a == pytest.approx(EXPECTED_SCORES[("and2", "c:a")])
    assert got_and_b == pytest.approx(EXPECTED_SCORES[("and2", "c:b")])
    assert got_bridge_c == pytest.approx(EXPECTED_SCORES[("bridge", "c:c")])
    assert got_bridge_b == pytest.approx(EXPECTED_SCORES[("bridge", "c:b")])
    # 'the' appears on every synthetic node -> idf==0 -> zero signal
    assert got_the_a == pytest.approx(0.0, abs=1e-9)
    # score_one must never go negative and a real hit must outscore no-hit
    assert got_joy_a > got_joy_b


# ===========================================================================
# Unit tests: causal_path(a, b, home, strict) on SMALL_GRAPH
# ===========================================================================
@needs_tmap_import
def test_causal_path_same_node_trivial():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for causal_path unit test")
    cost, nodes, hops = call_algo(tmap.causal_path, ("c:a", "c:a", None, None), graph)
    assert cost == 0
    assert nodes == ["c:a"]
    assert hops == []


@needs_tmap_import
def test_causal_path_forward_chain_found():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for causal_path unit test")
    cost, nodes, hops = call_algo(tmap.causal_path, ("c:a", "c:c", None, None), graph)
    assert nodes == ["c:a", "c:b", "c:c"]
    assert len(hops) == 2
    assert cost == pytest.approx(1.6 + 1.6)
    for h in hops:
        assert h["kind"] == "cause"
        # forward-only invariant: a causal hop must follow the eitza edge's
        # own direction (from == edge.s). Tolerate the hop's edge being
        # stored under either "edge" or "e".
        e = _hop_edge(h)
        assert e is not None, "hop has no edge/e reference: %r" % (h,)
        assert h["from"] == e["s"]
        assert h["to"] == e["t"]


@needs_tmap_import
def test_causal_path_home_discount_applied():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for causal_path unit test")
    cost, nodes, hops = call_algo(tmap.causal_path, ("c:a", "c:c", "I:1", None), graph)
    # a->b has ref I:1 (home match, 0.12); b->c has ref I:2 only (no match, 1.6)
    assert cost == pytest.approx(0.12 + 1.6)


@needs_tmap_import
def test_causal_path_strict_filters_out_of_ref_edges():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for causal_path unit test")
    # with strict='I:2', the only a->b edge (ref=[I:1]) is filtered out, so
    # 'a' has no viable causal exit at all.
    cost, nodes, hops = call_algo(tmap.causal_path, ("c:a", "c:c", None, "I:2"), graph)
    assert (cost, nodes, hops) == (None, None, None)


@needs_tmap_import
def test_causal_path_unreachable_returns_none_triple():
    graph = try_load_synthetic(ISOLATED_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for causal_path unit test")
    # 'c:iso' has no edges at all -> genuinely unreachable in either direction.
    result = call_algo(tmap.causal_path, ("c:iso", "c:a", None, None), graph)
    assert result == (None, None, None)
    result2 = call_algo(tmap.causal_path, ("c:a", "c:iso", None, None), graph)
    assert result2 == (None, None, None)


# The known-good forward eitza edges in SMALL_GRAPH, as (from, to) pairs --
# used to positively assert the forward-only invariant below (a causal hop
# may only ever traverse an eitza edge in its own s->t direction; it must
# never appear "backwards" as (t, s)).
_SMALL_GRAPH_FORWARD_EITZA_PAIRS = {("c:a", "c:b"), ("c:b", "c:c")}


@needs_tmap_import
def test_causal_path_never_traverses_eitza_backwards():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for causal_path unit test")
    # 'd' only touches bechina (reframe) edges directly; to satisfy
    # caused==1 it must eventually route through the real a->b->c eitza
    # chain (possibly winding through reframe hops first/after). Wherever a
    # 'cause' hop appears, it must be one of the forward eitza pairs, never
    # the reverse (b,a) or (c,b).
    result = call_algo(tmap.causal_path, ("c:d", "c:a", None, None), graph)
    cost, nodes, hops = result
    if hops is None:
        return  # also a valid, spec-compliant outcome (unreachable)
    assert cost >= 0
    assert nodes[0] == "c:d" and nodes[-1] == "c:a"
    cause_hops = [h for h in hops if h["kind"] == "cause"]
    assert cause_hops, "reaching a target requires caused==1, i.e. >=1 cause hop"
    for h in cause_hops:
        pair = (h["from"], h["to"])
        assert pair in _SMALL_GRAPH_FORWARD_EITZA_PAIRS, (
            "cause hop %r is not a forward eitza traversal (backwards eitza "
            "hop detected)" % (pair,)
        )


@needs_tmap_import
def test_causal_path_requires_at_least_one_cause_hop():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for causal_path unit test")
    # c:a and c:c are also connected by a *direct bechina* edge, but a pure
    # reframe path must NOT satisfy causal_path -- it must go via the eitza
    # chain (a->b->c), never claim victory via the 1-hop bechina shortcut
    # alone, unless a genuine 'cause' hop is present in the returned path.
    cost, nodes, hops = call_algo(tmap.causal_path, ("c:a", "c:c", None, None), graph)
    assert any(h["kind"] == "cause" for h in hops)


# ===========================================================================
# Unit tests: aspect_path(a, b, home) on SMALL_GRAPH
# ===========================================================================
@needs_tmap_import
def test_aspect_path_same_node_trivial():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for aspect_path unit test")
    hops = call_algo(tmap.aspect_path, ("c:a", "c:a", None), graph)
    assert hops == []


@needs_tmap_import
def test_aspect_path_direct_bechina_edge():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for aspect_path unit test")
    hops = call_algo(tmap.aspect_path, ("c:a", "c:c", None), graph)
    assert len(hops) == 1
    assert hops[0]["from"] in ("c:a", "c:c")
    assert hops[0]["to"] in ("c:a", "c:c")
    assert {hops[0]["from"], hops[0]["to"]} == {"c:a", "c:c"}


@needs_tmap_import
def test_aspect_path_multi_hop_via_bechina_only():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for aspect_path unit test")
    hops = call_algo(tmap.aspect_path, ("c:a", "c:d", None), graph)
    assert hops is not None
    visited = {"c:a"}
    for h in hops:
        assert h["from"] in visited
        visited.add(h["to"])
    assert "c:d" in visited


@needs_tmap_import
def test_aspect_path_unreachable_returns_none():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for aspect_path unit test")
    # 'b' has no bechina edges at all in SMALL_GRAPH
    hops = call_algo(tmap.aspect_path, ("c:a", "c:b", None), graph)
    assert hops is None


@needs_tmap_import
def test_aspect_path_home_discount():
    graph = try_load_synthetic(SMALL_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for aspect_path unit test")
    hops_home = call_algo(tmap.aspect_path, ("c:a", "c:c", "I:1"), graph)
    # direct edge a-c has ref I:1 -> weight 0.12 when home='I:1'
    assert len(hops_home) == 1


# ===========================================================================
# Project synthetic invariants (deterministic, hand-verified) -- CLI-level,
# so this passes regardless of tmap's internal Python API shape.
# ===========================================================================
def test_project_synthetic_full_invariants(tmp_path):
    data_path = write_json(tmp_path, "project_synth.json", PROJECT_GRAPH)
    proc, out = cli_json(["project", "c:x1", "c:x2", "c:x3"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True, out
    assert out["home"] == "H:1"
    chain_ids = [c["id"] for c in out["chain"]]
    assert len(set(chain_ids)) == len(chain_ids) == 3  # distinct chain
    assert set(chain_ids) == {"c:x1", "c:x2", "c:x3"}
    assert out["cost"] == pytest.approx(0.24, abs=1e-6)
    for m in out["mappings"]:
        assert m["kind"] in ("self", "aspect", "shared")
        assert m["kind"] == "self"  # by construction: no bechina edges exist
    assert len(out["links"]) == 2
    for link in out["links"]:
        kinds = [h["kind"] for h in link["hops"]]
        assert "cause" in kinds
        for h in link["hops"]:
            assert "H:1" in h["ref"]
            assert isinstance(h["proof"], str)


def test_project_synthetic_in_process_if_available(tmp_path):
    if not TMAP_IMPORTABLE:
        pytest.skip("tmap not importable")
    graph = try_load_synthetic(PROJECT_GRAPH)
    if graph is False:
        pytest.skip("no discoverable graph-loading entrypoint for project() unit test")
    result = call_project(["c:x1", "c:x2", "c:x3"], graph)
    assert result is not None


# ===========================================================================
# CLI surface tests on synthetic data (guaranteed by the spec's argparse
# contract regardless of internal Python API shape)
# ===========================================================================
def test_cli_search_synthetic(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, out = cli_json(["search", "joy"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert isinstance(out["results"], list)
    if out["results"]:
        r = out["results"][0]
        for key in ("id", "he", "gloss", "kind", "deg", "refs", "score"):
            assert key in r


def test_cli_concept_synthetic_shape(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, out = cli_json(["concept", "c:a"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    for key in ("aspects", "causes", "effects"):
        assert key in out
        assert isinstance(out[key], list)
        for row in out[key]:
            for k in ("id", "he", "gloss", "proof", "ref"):
                assert k in row
            assert isinstance(row["proof"], str)


def test_cli_aspects_advice_effects_synthetic(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc_a, out_a = cli_json(["aspects", "c:a"], data_path=data_path)
    assert out_a["ok"] is True
    # c:a's only bechina neighbor is c:c
    ids = [r["id"] for r in out_a.get("results", out_a.get("aspects", []))]
    assert "c:c" in ids

    # advice ID = eitza_in (what leads TO it): b has c:a leading to it
    proc_adv, out_adv = cli_json(["advice", "c:b"], data_path=data_path)
    assert out_adv["ok"] is True

    # effects ID = eitza_out (id causes these): a causes b
    proc_eff, out_eff = cli_json(["effects", "c:a"], data_path=data_path)
    assert out_eff["ok"] is True


def test_cli_path_synthetic(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, out = cli_json(["path", "c:a", "c:d"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert "steps" in out and "length" in out
    for step in out["steps"]:
        for k in ("from", "to", "ty", "proof", "ref"):
            assert k in step
        assert isinstance(step["proof"], str)


def test_cli_match_synthetic(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, out = cli_json(["match", "a feeling of great joy"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert isinstance(out["results"], list)
    for r in out["results"]:
        for k in ("id", "he", "gloss", "score"):
            assert k in r


def test_cli_torah_synthetic(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, out = cli_json(["torah", "I:1"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert out["ref"] == "I:1"
    assert "concepts" in out and "edges" in out
    assert_all_proofs_are_strings(out)


def test_cli_common_synthetic(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, out = cli_json(["common", "c:a", "c:c"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert "shared" in out
    for row in out["shared"]:
        for k in ("id", "he", "gloss", "via_a", "via_b"):
            assert k in row


def test_cli_unknown_id_synthetic(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc = run_cli(["concept", "c:definitely-not-a-real-id"], data_path=data_path)
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert out["ok"] is False
    assert isinstance(out.get("error"), str) and out["error"]


def test_cli_project_bad_id_fails(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc = run_cli(["project", "c:a", "c:no-such-id"], data_path=data_path)
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert out["ok"] is False


def test_cli_pretty_flag_indents(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc_plain = run_cli(["search", "joy"], data_path=data_path)
    proc_pretty = run_cli(["search", "joy", "--pretty"], data_path=data_path)
    assert json.loads(proc_plain.stdout) == json.loads(proc_pretty.stdout)
    assert "\n  " in proc_pretty.stdout or "\n    " in proc_pretty.stdout


def test_cli_hebrew_not_escaped(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, _ = cli_json(["concept", "c:a"], data_path=data_path)
    assert "\\u05" not in proc.stdout  # ensure_ascii=False: raw UTF-8, not escapes
    assert "א" in proc.stdout  # the Hebrew 'he' field value appears literally


# ===========================================================================
# AC1: load + adjacency symmetry (real data)
# ===========================================================================
@needs_real_data
def test_ac1_node_and_edge_counts():
    # counts updated 2026-07-09 for the v2 ai_extracted merge (specs/MERGE_POLICY.md):
    # 3,588 concepts + 627 legacy statements + 4,803 AI phrase-statements;
    # 12,328 edges keyed by (s,t,type,polarity,via)
    raw = json.loads(REAL_DATA.read_text(encoding="utf-8"))
    assert len(raw["nodes"]) == 9018
    assert len(raw["edges"]) == 12328


@needs_real_data
def test_ac1_adjacency_symmetric_via_concept_cli():
    """adj symmetric: every edge appears in both endpoints' `all` list.
    Verified through the public CLI surface (concept command) rather than
    reaching into internals, using a sample of real edges."""
    raw = json.loads(REAL_DATA.read_text(encoding="utf-8"))
    import random
    random.seed(1234)
    sample = random.sample(raw["edges"], 25)
    for e in sample:
        s, t, ty = e["s"], e["t"], e["ty"]
        _, out_s = cli_json(["concept", s], data_path=REAL_DATA)
        _, out_t = cli_json(["concept", t], data_path=REAL_DATA)
        assert out_s["ok"] and out_t["ok"]
        if ty == "bechina":
            s_aspect_ids = {r["id"] for r in out_s["aspects"]}
            t_aspect_ids = {r["id"] for r in out_t["aspects"]}
            assert t in s_aspect_ids, "bechina edge %s-%s missing from %s's aspects" % (s, t, s)
            assert s in t_aspect_ids, "bechina edge %s-%s missing from %s's aspects" % (s, t, t)
        elif ty == "eitza":
            s_effect_ids = {r["id"] for r in out_s["effects"]}
            t_cause_ids = {r["id"] for r in out_t["causes"]}
            assert t in s_effect_ids, "eitza edge %s->%s missing from %s's effects" % (s, t, s)
            assert s in t_cause_ids, "eitza edge %s->%s missing from %s's causes" % (s, t, t)


@needs_real_data
@needs_tmap_import
def test_ac1_adjacency_symmetric_in_process_if_available():
    graph = try_load_synthetic(SMALL_GRAPH)  # cheap sanity that loader works at all
    if graph is False:
        pytest.skip("no discoverable in-process loader; covered via CLI test instead")
    raw = json.loads(REAL_DATA.read_text(encoding="utf-8"))
    real_graph = try_load_synthetic(raw)  # will only "succeed" (len match) for real data
    if real_graph is False:
        pytest.skip("loader worked for synthetic data but not for real data shape")
    by_id = getattr(tmap, "by_id", None)
    adj = getattr(tmap, "adj", None)
    if by_id is None or adj is None:
        pytest.skip("tmap.by_id / tmap.adj not exposed as module globals")
    assert len(by_id) == 9018
    for e in raw["edges"][:200]:
        s, t = e["s"], e["t"]
        s_all_others = {other for (other, _ty, _dir, _edge) in adj[s]["all"]}
        t_all_others = {other for (other, _ty, _dir, _edge) in adj[t]["all"]}
        assert t in s_all_others
        assert s in t_all_others


# ===========================================================================
# AC2: search quality (real data)
# ===========================================================================
@needs_real_data
def test_ac2_search_joy_top3_contains_simchah():
    _, out = cli_json(["search", "joy", "-n", "10"], data_path=REAL_DATA)
    assert out["ok"] is True
    top3_ids = [r["id"] for r in out["results"][:3]]
    assert "c:simchah" in top3_ids


@needs_real_data
def test_ac2_search_emunah_hebrew_top1():
    _, out = cli_json(["search", "אמונה", "-n", "5"], data_path=REAL_DATA)
    assert out["ok"] is True
    assert out["results"], "expected at least one search result for אמונה"
    top1 = out["results"][0]
    assert top1["he"] == "ארץ ישראל" or top1["id"].startswith("c:emunah")


# ===========================================================================
# AC3: project(["c:tefillah-2","c:simchah","c:emet"]) invariants (real data)
# ===========================================================================
def _assert_project_structural_invariants(out, expect_home=None):
    assert out["ok"] is True, out
    chain_ids = [c["id"] for c in out["chain"]]
    assert len(set(chain_ids)) == len(chain_ids), "chain must be distinct concepts"
    home = out.get("home")
    if expect_home is not None:
        assert home == expect_home
    for m in out["mappings"]:
        assert m["kind"] in ("self", "aspect", "shared")
        if m["kind"] == "aspect":
            assert m.get("hops"), "aspect mapping must carry non-empty hops"
    for link in out["links"]:
        kinds = [h["kind"] for h in link["hops"]]
        assert "cause" in kinds, "every link must contain at least one cause hop"
        for h in link["hops"]:
            assert isinstance(h.get("proof", ""), str)
            if home:
                assert home in h.get("ref", []), (
                    "hop ref %r does not contain home %r" % (h.get("ref"), home)
                )
    assert_all_proofs_are_strings(out)


@needs_real_data
def test_ac3_project_tefillah_simchah_emet():
    proc, out = cli_json(
        ["project", "c:tefillah-2", "c:simchah", "c:emet"], data_path=REAL_DATA, timeout=30
    )
    assert proc.returncode == 0, proc.stderr
    _assert_project_structural_invariants(out, expect_home="I:22")


# ===========================================================================
# AC4: project on >=3 other varied triples, ids found via search (real data)
# ===========================================================================
def _search_top_id(term, fallback):
    proc, out = cli_json(["search", term, "-n", "5"], data_path=REAL_DATA)
    if out.get("ok") and out.get("results"):
        return out["results"][0]["id"]
    return fallback


@needs_real_data
def test_ac4_project_varied_triples_under_5s_each():
    triples = [
        [
            _search_top_id("fasting", "c:ta'anit"),
            _search_top_id("faith", "c:emunah"),
            _search_top_id("divine providence", "c:hashgachah"),
        ],
        [
            _search_top_id("money", "c:shevirat-ta'avat-mamon"),
            _search_top_id("charity", "c:charity-intellect"),
            _search_top_id("simcha", "c:simchah"),
        ],
        [
            _search_top_id("repentance", "c:return-repentance-repenting"),
            "c:tefillah-2",
            "c:emet",
        ],
    ]
    for ids in triples:
        ids = list(dict.fromkeys(ids))  # de-dup while preserving order
        assert len(ids) >= 2, "need at least 2 distinct ids for project()"
        start = time.monotonic()
        proc, out = cli_json(["project"] + ids, data_path=REAL_DATA, timeout=10)
        elapsed = time.monotonic() - start
        assert elapsed < 5.0, "project(%r) took %.2fs (must be < 5s)" % (ids, elapsed)
        # AC4 is about TIMING, not guaranteed success: ids are resolved live via search(),
        # which can drift onto obscure/narrow nodes with no real textual connection to the
        # others. project() must never fabricate one (no bechina/eitza edge -> no home is the
        # only honest answer), so a clean {"ok": false} is a valid, well-formed outcome here,
        # not a test failure — only a crash (non-JSON / unexpected returncode) is.
        assert proc.returncode in (0, 1), "project(%r) crashed: %s" % (ids, proc.stderr)
        assert isinstance(out, dict) and "ok" in out, "project(%r) malformed output: %r" % (ids, out)
        if out["ok"]:
            _assert_project_structural_invariants(out)
        else:
            assert out.get("error"), "project(%r) ok:false with no error message" % (ids,)


# ===========================================================================
# AC5: causal_path forward-only (real data, checked through project() links
# and directly via the CLI-visible cause hops)
# ===========================================================================
@needs_real_data
def test_ac5_no_backward_eitza_in_project_links():
    proc, out = cli_json(
        ["project", "c:tefillah-2", "c:simchah", "c:emet"], data_path=REAL_DATA, timeout=30
    )
    assert out["ok"] is True
    raw = json.loads(REAL_DATA.read_text(encoding="utf-8"))
    edges_by_st = {}
    for e in raw["edges"]:
        edges_by_st.setdefault((e["s"], e["t"]), []).append(e)
    for link in out["links"]:
        for h in link["hops"]:
            if h["kind"] == "cause":
                # the hop must follow an eitza edge in its own s->t direction
                assert (h["from"], h["to"]) in edges_by_st, (
                    "cause hop %s->%s does not correspond to a forward eitza edge.s->edge.t"
                    % (h["from"], h["to"])
                )
                matching = [e for e in edges_by_st[(h["from"], h["to"])] if e["ty"] == "eitza"]
                assert matching, "cause hop %s->%s has no matching eitza edge" % (h["from"], h["to"])


# ===========================================================================
# AC6: CLI ok/error surface on known-good + unknown inputs (real data)
# ===========================================================================
@needs_real_data
def test_ac6_known_good_calls_return_ok():
    proc, out = cli_json(["path", "c:tefillah-2", "c:emunah-2"], data_path=REAL_DATA)
    assert proc.returncode == 0
    assert out["ok"] is True
    assert "steps" in out and "length" in out

    proc, out = cli_json(["common", "c:ahavah-2", "c:tefillah-2"], data_path=REAL_DATA)
    assert proc.returncode == 0
    assert out["ok"] is True
    shared_ids = {r["id"] for r in out["shared"]}
    assert "c:avraham" in shared_ids

    proc, out = cli_json(["torah", "I:22"], data_path=REAL_DATA)
    assert proc.returncode == 0
    assert out["ok"] is True
    assert out["concepts"]

    proc, out = cli_json(["match", "joy and gratitude before prayer"], data_path=REAL_DATA)
    assert proc.returncode == 0
    assert out["ok"] is True

    proc, out = cli_json(["concept", "c:simchah"], data_path=REAL_DATA)
    assert proc.returncode == 0
    assert out["ok"] is True


@needs_real_data
def test_ac6_unknown_id_error_exit_1():
    for args in (
        ["concept", "c:this-id-does-not-exist-anywhere"],
        ["aspects", "c:this-id-does-not-exist-anywhere"],
        ["path", "c:this-id-does-not-exist-anywhere", "c:simchah"],
        ["project", "c:this-id-does-not-exist-anywhere", "c:simchah"],
    ):
        proc = run_cli(args, data_path=REAL_DATA)
        assert proc.returncode == 1, "expected exit 1 for %r, got %s" % (args, proc.returncode)
        out = json.loads(proc.stdout)
        assert out["ok"] is False
        assert isinstance(out.get("error"), str) and out["error"].strip()


# ===========================================================================
# AC7: proof fields always strings; valid UTF-8 Hebrew JSON (real data)
# ===========================================================================
@needs_real_data
def test_ac7_proof_fields_are_strings_across_commands():
    _, out1 = cli_json(["concept", "c:simchah"], data_path=REAL_DATA)
    assert_all_proofs_are_strings(out1)

    _, out2 = cli_json(["path", "c:tefillah-2", "c:emunah-2"], data_path=REAL_DATA)
    assert_all_proofs_are_strings(out2)

    _, out3 = cli_json(["torah", "I:22"], data_path=REAL_DATA)
    assert_all_proofs_are_strings(out3)

    _, out4 = cli_json(["common", "c:ahavah-2", "c:tefillah-2"], data_path=REAL_DATA)
    assert_all_proofs_are_strings(out4)

    _, out5 = cli_json(
        ["project", "c:tefillah-2", "c:simchah", "c:emet"], data_path=REAL_DATA, timeout=30
    )
    assert_all_proofs_are_strings(out5)


@needs_real_data
def test_ac7_json_is_valid_utf8_hebrew():
    proc = run_cli(["concept", "c:simchah"], data_path=REAL_DATA)
    raw_bytes = proc.stdout.encode("utf-8")
    decoded = raw_bytes.decode("utf-8")  # must not raise
    parsed = json.loads(decoded)
    assert parsed["ok"] is True
    assert "שמחה" in proc.stdout or any(
        "א" <= ch <= "ת" for ch in proc.stdout
    )
    assert "\\u05" not in proc.stdout  # ensure_ascii=False, not escaped


# ===========================================================================
# diagnose() v1.1 addendum: AD1-AD5 (specs/api_v1.md ~136-173)
# ===========================================================================
def test_cli_diagnose_synthetic_shape(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, out = cli_json(["diagnose", "c:c"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    for key in ("concept", "contexts", "attested_helpers", "inferred_deficiencies", "note"):
        assert key in out
    assert out["note"] == (
        "inferred items are query-time inversions of attested builds-edges, not text"
    )
    for c in out["contexts"]:
        for k in ("id", "he", "gloss", "dist", "path"):
            assert k in c
    for h in out["attested_helpers"]:
        for k in ("of", "helper", "he", "gloss", "proof", "ref"):
            assert k in h
    for d in out["inferred_deficiencies"]:
        for k in ("lack_of", "he", "gloss", "weakens", "dist", "derivation", "status"):
            assert k in d
        assert d["status"] == "inferred"


# AD1 pinned facts (verified directly against ontology/graph/explorer_data.json):
# c:trust (כליות, kidneys) has exactly one bechina edge, to
# c:bitachon-trust-reliance, ref ["I:60"]; c:bitachon-trust-reliance has an
# eitza_in edge from c:seichel, ref ["I:225"].
@needs_real_data
def test_ad1_diagnose_c_trust_kidneys():
    proc, out = cli_json(["diagnose", "c:trust", "--pretty"], data_path=REAL_DATA)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True

    ctx_by_id = {c["id"]: c for c in out["contexts"]}
    assert "c:bitachon-trust-reliance" in ctx_by_id
    bitachon_ctx = ctx_by_id["c:bitachon-trust-reliance"]
    assert bitachon_ctx["dist"] == 1
    assert any("I:60" in (h.get("ref") or []) for h in bitachon_ctx["path"])

    seichel_helpers = [
        h for h in out["attested_helpers"]
        if h["of"] == "c:bitachon-trust-reliance" and h["helper"] == "c:seichel"
    ]
    assert seichel_helpers, out["attested_helpers"]
    assert "I:225" in (seichel_helpers[0].get("ref") or [])

    seichel_deficiencies = [
        d for d in out["inferred_deficiencies"]
        if d["lack_of"] == "c:seichel" and d["weakens"] == "c:bitachon-trust-reliance"
    ]
    assert seichel_deficiencies, out["inferred_deficiencies"]
    d0 = seichel_deficiencies[0]
    assert d0["status"] == "inferred"
    assert len(d0["derivation"]) == 2  # aspect hop c:trust->bitachon, then eitza c:seichel->bitachon
    assert d0["derivation"][-1]["from"] == "c:seichel"
    assert d0["derivation"][-1]["to"] == "c:bitachon-trust-reliance"
    assert "I:225" in (d0["derivation"][-1].get("ref") or [])


# AD2: every inferred_deficiency's derivation ends in a real eitza edge
# present in the data (verifiable s->t match) -- no deficiency without one.
@needs_real_data
def test_ad2_every_derivation_ends_in_real_eitza_edge():
    proc, out = cli_json(["diagnose", "c:trust", "--depth", "2", "-n", "12"], data_path=REAL_DATA)
    assert out["ok"] is True
    raw = json.loads(REAL_DATA.read_text(encoding="utf-8"))
    eitza_pairs = {(e["s"], e["t"]) for e in raw["edges"] if e["ty"] == "eitza"}
    assert out["inferred_deficiencies"], "expected at least one inferred deficiency for c:trust"
    for d in out["inferred_deficiencies"]:
        assert d["derivation"], d
        last = d["derivation"][-1]
        assert (last["from"], last["to"]) == (d["lack_of"], d["weakens"])
        assert (last["from"], last["to"]) in eitza_pairs, (
            "inferred deficiency %r has no matching attested eitza edge" % (d,)
        )


# AD3: depth is respected, and an unknown id fails cleanly.
@needs_real_data
def test_ad3_depth_respected_real_data():
    proc, out = cli_json(["diagnose", "c:trust", "--depth", "1"], data_path=REAL_DATA)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert all(c["dist"] <= 1 for c in out["contexts"])


def test_ad3_unknown_id_exit_1(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc = run_cli(["diagnose", "c:this-id-does-not-exist"], data_path=data_path)
    assert proc.returncode == 1
    out = json.loads(proc.stdout)
    assert out["ok"] is False
    assert isinstance(out.get("error"), str) and out["error"]


# AD4: synthetic-graph unit test -- inversion emits exactly the eitza_in
# set, nothing more. On SMALL_GRAPH, diagnosing c:c (bechina neighbors
# c:a and c:d at dist 1, no further bechina reach) the only eitza_in edge
# among {c:c, c:a, c:d} is b->c, so exactly one attested helper / inferred
# deficiency may appear, and no others may be fabricated.
def test_ad4_synthetic_inversion_exactly_eitza_in_set(tmp_path):
    data_path = write_json(tmp_path, "small.json", SMALL_GRAPH)
    proc, out = cli_json(["diagnose", "c:c", "--depth", "2", "-n", "12"], data_path=data_path)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True

    ctx_ids = {c["id"] for c in out["contexts"]}
    assert ctx_ids == {"c:c", "c:a", "c:d"}

    helper_pairs = {(h["of"], h["helper"]) for h in out["attested_helpers"]}
    assert helper_pairs == {("c:c", "c:b")}

    deficiency_pairs = {(d["lack_of"], d["weakens"]) for d in out["inferred_deficiencies"]}
    assert deficiency_pairs == {("c:b", "c:c")}
    assert len(out["inferred_deficiencies"]) == 1
    d0 = out["inferred_deficiencies"][0]
    assert d0["status"] == "inferred"
    assert d0["dist"] == 0


# AD5: every proof is a string, output is valid UTF-8 Hebrew, and diagnose
# runs fast on real data.
@needs_real_data
def test_ad5_proofs_strings_utf8_and_fast():
    start = time.monotonic()
    proc = run_cli(["diagnose", "c:trust", "--pretty"], data_path=REAL_DATA)
    elapsed = time.monotonic() - start
    assert elapsed < 5.0, "diagnose(c:trust) took %.2fs (must be < 5s)" % elapsed
    out = json.loads(proc.stdout)
    assert out["ok"] is True
    assert_all_proofs_are_strings(out)
    assert "\\u05" not in proc.stdout  # ensure_ascii=False, not escaped
    assert "שכל" in proc.stdout or any("א" <= ch <= "ת" for ch in proc.stdout)


# ===========================================================================
# v1.2 addendum: top-K alternatives (-k), specs/api_v1.md ~177-200
# ===========================================================================
@needs_real_data
def test_ak1_path_k3_known_multi_path_pair():
    """AK1: path A B -k 3 on a known multi-path pair (c:simchah -> c:emet)
    returns <=3 distinct-node-sequence paths, costs non-decreasing, and the
    first alternative == the old (k=1) best-path behavior byte-for-byte."""
    proc1, out1 = cli_json(["path", "c:simchah", "c:emet"], data_path=REAL_DATA)
    assert proc1.returncode == 0, proc1.stderr
    assert out1["ok"] is True

    proc3, out3 = cli_json(["path", "c:simchah", "c:emet", "-k", "3"], data_path=REAL_DATA)
    assert proc3.returncode == 0, proc3.stderr
    assert out3["ok"] is True

    # k=1 fields (steps/length) are untouched by -k
    assert out3["steps"] == out1["steps"]
    assert out3["length"] == out1["length"]

    alts = out3["alternatives"]
    assert 1 <= len(alts) <= 3
    # first alternative == old (k=1) behavior
    assert alts[0]["steps"] == out1["steps"]

    costs = [a["cost"] for a in alts]
    assert costs == sorted(costs), "alternative costs must be non-decreasing"

    node_seqs = []
    for a in alts:
        seq = [a["steps"][0]["from"]] + [s["to"] for s in a["steps"]] if a["steps"] else ["c:simchah"]
        node_seqs.append(tuple(seq))
    assert len(set(node_seqs)) == len(node_seqs), "alternatives must have distinct node-sequences"

    for a in alts:
        for step in a["steps"]:
            for k in ("from", "to", "ty", "proof", "ref"):
                assert k in step
            assert isinstance(step["proof"], str)


@needs_real_data
def test_ak2_project_k3_tefillah_simchah_emet():
    """AK2: project ID... -k 3 returns <=3 alternatives with distinct homes,
    costs non-decreasing, alternatives[0] identical to the primary result
    (primary home is I:22), and every alternative passes the same AC3
    structural invariants."""
    ids = ["c:tefillah-2", "c:simchah", "c:emet"]
    proc, out = cli_json(["project"] + ids + ["-k", "3"], data_path=REAL_DATA, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert out["home"] == "I:22"

    alts = out["alternatives"]
    assert 1 <= len(alts) <= 3

    homes = [a["home"] for a in alts]
    assert len(set(homes)) == len(homes), "alternatives must have distinct homes"

    costs = [a["cost"] for a in alts]
    assert costs == sorted(costs), "alternative costs must be non-decreasing"

    # primary fields (cost/home/chain/mappings/links) == alternatives[0]
    primary = {k: out[k] for k in ("cost", "home", "chain", "mappings", "links")}
    assert primary == alts[0]

    for a in alts:
        _assert_project_structural_invariants({**a, "ok": True})


# ===========================================================================
# v1.3 addendum: `why` (typed causal query) and `chain` (verifier),
# specs/api_v1.md ~204-232
# ===========================================================================
@needs_real_data
def test_aw1_why_head_year_phylacteries_two_cause_hops():
    """AW1: why c:head-year c:phylacteries -> 1 chain, 2 cause-hops
    (via c:sleep, he=='תקון המחין'), proofs present."""
    proc, out = cli_json(["why", "c:head-year", "c:phylacteries"], data_path=REAL_DATA)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert len(out["chains"]) == 1

    hops = out["chains"][0]["hops"]
    assert len(hops) == 2
    assert all(h["kind"] == "cause" for h in hops)
    assert hops[0]["from"] == "c:head-year"
    assert hops[-1]["to"] == "c:phylacteries"
    # the middle node connecting both hops is c:sleep == תקון המחין
    assert hops[0]["to"] == hops[1]["from"] == "c:sleep"
    assert hops[0]["he_to"] == "תקון המחין"
    for h in hops:
        for key in ("from", "to", "he_from", "he_to", "kind", "hc", "proof", "ref"):
            assert key in h
        assert isinstance(h["proof"], str) and h["proof"]


@needs_real_data
def test_aw2_why_head_year_day_atonement_chain_exists_post_merge():
    """AW2 (flipped 2026-07-09, per this test's own pre-merge TODO note): the
    v2 ai_extracted merge connected these. Verified attested via `tmap chain`:
    head-year ≈ hashgachah (bechina II:8) -> echad (eitza I:51, "על ידי
    ההשגחה כולו אחד") ≈ day-atonement (bechina I:179, "ולו אחד בהם – זה יום
    הכפורים"). Spec ~228-229 called this a forward-looking regression flag."""
    proc, out = cli_json(["why", "c:head-year", "c:day-atonement"], data_path=REAL_DATA)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert len(out["chains"]) >= 1
    hops = out["chains"][0]["hops"]
    assert any(h["kind"] == "cause" for h in hops)
    for h in hops:
        assert isinstance(h["proof"], str) and h["proof"]
        assert h.get("polarity") in ("builds", "harms", "neutral")


@needs_real_data
def test_aw3_chain_head_year_sleep_phylacteries_complete():
    """AW3: chain c:head-year c:sleep c:phylacteries -> complete:true, both
    junctions forward eitza."""
    proc, out = cli_json(["chain", "c:head-year", "c:sleep", "c:phylacteries"], data_path=REAL_DATA)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert out["complete"] is True
    assert len(out["junctions"]) == 2
    for j in out["junctions"]:
        assert j["attested"] is True
        assert j["ty"] == "eitza"
        assert j["direction"] == "forward"
        assert isinstance(j["proof"], str) and j["proof"]


@needs_real_data
def test_aw4_chain_head_year_day_atonement_incomplete():
    """AW4: chain c:head-year c:day-atonement -> complete:false, junction
    attested:false (no edge at all between them on current data)."""
    proc, out = cli_json(["chain", "c:head-year", "c:day-atonement"], data_path=REAL_DATA)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert out["complete"] is False
    assert len(out["junctions"]) == 1
    j = out["junctions"][0]
    assert j["from"] == "c:head-year"
    assert j["to"] == "c:day-atonement"
    assert j["attested"] is False


def test_aw5_why_k_alternatives_distinct_and_nondecreasing(tmp_path):
    """AW5: why A B -k N respects distinctness (no duplicate hop-sequences)
    and non-decreasing cost, on a synthetic graph with exactly 2 node-disjoint
    equal-cost causal routes wa->wd. k=1 default is unaffected by -k wiring."""
    data_path = write_json(tmp_path, "why_graph.json", WHY_GRAPH)

    proc1, out1 = cli_json(["why", "c:wa", "c:wd"], data_path=data_path)
    assert proc1.returncode == 0, proc1.stderr
    assert out1["ok"] is True
    assert len(out1["chains"]) == 1  # k=1 default

    proc3, out3 = cli_json(["why", "c:wa", "c:wd", "-k", "3"], data_path=data_path)
    assert proc3.returncode == 0, proc3.stderr
    assert out3["ok"] is True

    chains = out3["chains"]
    # exactly 2 distinct causal routes exist in WHY_GRAPH -- -k 3 can't invent a 3rd
    assert len(chains) == 2
    assert chains[0] == out1["chains"][0]  # k=1 behavior unchanged by -k

    costs = [c["cost"] for c in chains]
    assert costs == sorted(costs), "chain costs must be non-decreasing"

    hop_seqs = [tuple((h["from"], h["to"]) for h in c["hops"]) for c in chains]
    assert len(set(hop_seqs)) == len(hop_seqs), "chains must have distinct hop-sequences"

    # a bogus/unknown id still fails cleanly (exit 1, ok:false) through the new commands
    proc_bad = run_cli(["why", "c:wa", "c:nope"], data_path=data_path)
    assert proc_bad.returncode == 1
    assert json.loads(proc_bad.stdout)["ok"] is False
    proc_bad2 = run_cli(["chain", "c:wa", "c:nope"], data_path=data_path)
    assert proc_bad2.returncode == 1
    assert json.loads(proc_bad2.stdout)["ok"] is False


# ===========================================================================
# v1.4 addendum: packets, loose mode, set-endpoints, pattern notation
# specs/api_v1.md ~236-275
# ===========================================================================
USER_PACKETS_FILE = REPO_ROOT / "ontology" / "packets" / "user_packets.jsonl"


@needs_real_data
def test_ap1_packets_i1_includes_malchut_chen_component():
    """AP1: packets I:1 includes a component containing both the מלכות node
    (c:chokhmah-tata'ah) and the חן node (c:chen)."""
    proc, out = cli_json(["packets", "I:1"], data_path=REAL_DATA)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert out["ref"] == "I:1"

    found = False
    for comp in out["packets"]:
        ids = {row["id"] for row in comp}
        if "c:chokhmah-tata'ah" in ids and "c:chen" in ids:
            found = True
            # sanity: both members carry their Hebrew label
            he_by_id = {row["id"]: row["he"] for row in comp}
            assert he_by_id["c:chokhmah-tata'ah"] == "מלכות"
            assert he_by_id["c:chen"] == "חן"
            break
    assert found, "no I:1 packet contains both c:chokhmah-tata'ah and c:chen"

    # every component is a real chain (size >= 2), sorted by size desc
    sizes = [len(c) for c in out["packets"]]
    assert all(s >= 2 for s in sizes)
    assert sizes == sorted(sizes, reverse=True)


@needs_real_data
def test_ap2_why_set_endpoints_rosh_hashanah_to_chotam_loose():
    """AP2: why --from 'ראש השנה' --to 'חותם' --loose finds >=1 chain on
    CURRENT data (spec ~268-270). If this ever regresses to zero, that's
    itself news about the data, not a silent pass -- so we assert the
    concrete >=1 expectation rather than "either is fine"."""
    proc, out = cli_json(
        ["why", "--from", "ראש השנה", "--to", "חותם", "--loose", "-k", "2"],
        data_path=REAL_DATA,
    )
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert len(out["matched_from"]) >= 1
    assert len(out["matched_to"]) >= 1
    assert any(row["id"] == "c:head-year" for row in out["matched_from"])
    assert len(out["chains"]) >= 1

    chain = out["chains"][0]
    assert chain["hops"], "expected a non-trivial chain"
    # the resolved endpoints are real matched concepts, not the raw patterns
    from_ids = {row["id"] for row in out["matched_from"]}
    to_ids = {row["id"] for row in out["matched_to"]}
    assert chain["hops"][0]["from"] in from_ids
    assert chain["hops"][-1]["to"] in to_ids
    for c in out["chains"]:
        for h in c["hops"]:
            assert isinstance(h["proof"], str)


@needs_real_data
def test_ap3_packet_add_loose_all_user_packet_hop_then_cleanup():
    """AP3: packet add (II:8: c:head-year + a malchut node) then
    why --loose=all c:head-year c:sekhel-2 includes a hop labeled
    kind:"user-packet"; removing the file restores the prior (non-labeled)
    result. MUST clean up the real user_packets.jsonl file in `finally`."""
    assert not USER_PACKETS_FILE.exists(), (
        "stale ontology/packets/user_packets.jsonl from a previous run -- "
        "refusing to overwrite; remove it manually and rerun"
    )
    try:
        # baseline: before any user packet exists, --loose=all == plain --loose
        proc_before, out_before = cli_json(
            ["why", "c:head-year", "c:sekhel-2", "--loose=all", "-k", "1"],
            data_path=REAL_DATA,
        )
        assert proc_before.returncode == 0, proc_before.stderr
        before_kinds = {h["kind"] for c in out_before["chains"] for h in c["hops"]}
        assert "user-packet" not in before_kinds

        proc_add, out_add = cli_json(
            ["packet", "add", "II:8", "c:head-year", "c:chokhmah-tata'ah",
             "--note", "test packet (AP3)", "--by", "pytest"],
            data_path=REAL_DATA,
        )
        assert proc_add.returncode == 0, proc_add.stderr
        assert out_add["ok"] is True
        assert USER_PACKETS_FILE.exists()

        proc_list, out_list = cli_json(["packet", "list"], data_path=REAL_DATA)
        assert proc_list.returncode == 0, proc_list.stderr
        assert any(e.get("members") == ["c:head-year", "c:chokhmah-tata'ah"]
                   for e in out_list["entries"])

        proc_after, out_after = cli_json(
            ["why", "c:head-year", "c:sekhel-2", "--loose=all", "-k", "1"],
            data_path=REAL_DATA,
        )
        assert proc_after.returncode == 0, proc_after.stderr
        assert out_after["ok"] is True
        assert len(out_after["chains"]) >= 1
        top = out_after["chains"][0]
        up_hops = [h for h in top["hops"] if h["kind"] == "user-packet"]
        assert up_hops, "expected the ranked-#1 chain to use the new user-packet hop"
        for h in up_hops:
            assert h["by"] == "pytest"
            assert h["note"] == "test packet (AP3)"
        # a plain --loose (not =all) run must NOT see the user-packet hop
        proc_loose, out_loose = cli_json(
            ["why", "c:head-year", "c:sekhel-2", "--loose", "-k", "1"],
            data_path=REAL_DATA,
        )
        loose_kinds = {h["kind"] for c in out_loose["chains"] for h in c["hops"]}
        assert "user-packet" not in loose_kinds
    finally:
        if USER_PACKETS_FILE.exists():
            USER_PACKETS_FILE.unlink()

    # after cleanup, behavior is restored to the pre-packet baseline
    proc_restored, out_restored = cli_json(
        ["why", "c:head-year", "c:sekhel-2", "--loose=all", "-k", "1"],
        data_path=REAL_DATA,
    )
    assert proc_restored.returncode == 0, proc_restored.stderr
    assert out_restored["chains"] == out_before["chains"]


@needs_real_data
def test_ap4_strict_mode_unaffected_by_v14_wiring():
    """AP4: strict mode (no --loose, no set endpoints) stays exactly the
    v1.3 behavior -- re-check AW1's own assertion (2 forward cause-hops via
    c:sleep) still holds byte-for-byte after the v1.4 causal_path rewrite."""
    proc, out = cli_json(["why", "c:head-year", "c:phylacteries"], data_path=REAL_DATA)
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert len(out["chains"]) == 1
    hops = out["chains"][0]["hops"]
    assert len(hops) == 2
    assert all(h["kind"] == "cause" for h in hops)
    assert hops[0]["to"] == hops[1]["from"] == "c:sleep"
    # new v1.4 keys are additive, never present with meaningful content when unused
    assert out["matched_from"] == [{"id": "c:head-year", "he": "ראש השנה"}]
    assert "warning_from" not in out
    assert "warning_to" not in out


@needs_real_data
def test_ap5_from_expansion_caps_at_40_and_reports_matched_counts():
    """AP5: --from expansion caps at 40 nodes and reports matched endpoint
    counts. 'תפלה' matches >40 non-statement concepts on the real data."""
    proc, out = cli_json(
        ["why", "--from", "תפלה", "c:sekhel-2", "-k", "1"],
        data_path=REAL_DATA,
    )
    assert proc.returncode == 0, proc.stderr
    assert out["ok"] is True
    assert len(out["matched_from"]) == 40
    assert "warning_from" in out
    assert "40" in out["warning_from"]
    assert "warning_to" not in out


# ===========================================================================
# selftest command (real data): AC1-5 self-report, exit 0
# ===========================================================================
@needs_real_data
def test_selftest_command_exits_zero_with_json_report():
    proc = run_cli(["selftest"], data_path=REAL_DATA, timeout=60)
    try:
        report = json.loads(proc.stdout)
    except Exception:
        report = None
    assert proc.returncode == 0, (
        "tmap.py selftest failed (rc=%s)\nSTDOUT:\n%s\nSTDERR:\n%s"
        % (proc.returncode, proc.stdout, proc.stderr)
    )
    assert isinstance(report, dict)


# ===========================================================================
# __main__: runnable standalone via `python3 test_tmap.py`
# ===========================================================================
def _plain_fallback_runner():
    """Minimal test runner used only when pytest itself is not installed.
    Supports plain no-fixture tests and the tmp_path fixture (backed by a
    real temp directory, which duck-types fine since it's just a Path)."""
    import inspect
    import traceback

    mod = sys.modules[__name__]
    tests = sorted(
        (name, obj) for name, obj in vars(mod).items()
        if name.startswith("test_") and callable(obj)
    )
    passed = failed = skipped = 0
    for name, fn in tests:
        sig = inspect.signature(fn)
        kwargs = {}
        runnable = True
        for pname in sig.parameters:
            if pname == "tmp_path":
                kwargs["tmp_path"] = Path(tempfile.mkdtemp(prefix="tmap_test_"))
            else:
                runnable = False
        if not runnable:
            print("SKIP  %s (needs an unsupported fixture without pytest)" % name)
            skipped += 1
            continue
        try:
            fn(**kwargs)
        except _Skipped as e:
            print("SKIP  %s: %s" % (name, e))
            skipped += 1
        except AssertionError as e:
            print("FAIL  %s: %s" % (name, e))
            failed += 1
        except Exception as e:
            print("ERROR %s: %s" % (name, e))
            traceback.print_exc()
            failed += 1
        else:
            print("PASS  %s" % name)
            passed += 1
    print("\n%d passed, %d failed, %d skipped" % (passed, failed, skipped))
    return 1 if failed else 0


if __name__ == "__main__":
    if _HAVE_PYTEST:
        raise SystemExit(pytest.main([__file__, "-v"]))
    else:
        raise SystemExit(_plain_fallback_runner())
