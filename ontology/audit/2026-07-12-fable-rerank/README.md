# Fable re-rank sweep — 2026-07-12 (75-agent fleet)

Full-registry re-rank by Fable agents; fresh edge sample; stub-alias pass; coverage scan.
Synthesis report not run (session paused) — data files are complete.

- concept_rerank.json — ALL 3,586 concepts scored 0-3 + verdict.
  Scores: 802×3 / 818×2 / 1,959×1 / 7×0. Verdicts: rename 1,939 · keep 1,338 · merge 251 · demote 52 · delete 6.
- edge_verdicts_partial.json — fresh random 600 AI-only edges (seed 712):
  455 supported (76%) / 99 weak / 46 wrong; 22 polarity-inversion flags.
  Harsher than the 2026-07-10 audit's 89% supported.
- stub_aliases_partial.json — top 600 recurring p: stubs ruled:
  map-to-existing 249 · promote-to-new-concept 242 · keep-stub 99 · junk 10.
- coverage.json — missing concepts (yiush/hitchazkut/temimut/emunah-peshutah/simchah-II:24/hoda'ah —
  Part II badly under-covered) + fragmentation clusters (hitbodedut ×4, Azamra ×5, fallen-faith ×11...).
- run1_coverage_raw.json — first-run raw output.

Workflow journal (per-agent transcripts, resumable): wf_d4a432b0-99b.
