# Fable re-rank sweep — 2026-07-12 (76-agent fleet, complete)

Full-registry re-rank by Fable agents; fresh edge sample; stub-alias pass; coverage scan; synthesis.
Workflow wf_d4a432b0-99b; per-agent transcripts in the session workflow journal.

- SYNTHESIS.md — the fleet's own report: headline numbers, failure themes, priorities.
- concept_rerank.json — ALL 3,586 concepts scored 0-3 + verdict + proposed fix.
  Scores: 802 x3 / 818 x2 / 1,959 x1 / 7 x0. Verdicts: rename 1,939 / keep 1,338 / merge 251 / demote 52 / delete 6.
- edge_verdicts.json — fresh random 600 AI-only edges (seed 712, batches in scratchpad/rerank):
  455 supported (75.8%) / 99 weak / 46 wrong; 22 polarity flags. The 2026-07-10 "89% supported" does NOT replicate.
- stub_aliases.json — top 600 recurring p: stubs ruled: map 249 / new-concept 242 / keep-stub 99 / junk 10.
- coverage.json — missing concepts (yiush, hitchazkut, temimut u-peshitut, Chanukah, mikveh, LM II eitzot...)
  and fragmentation clusters (hitgalut ha-ratzon x9, clapping x7, makifim x6, fallen faith x11...).
- run1_coverage_raw.json — first (partial) run raw output.

Next actions implied: registry rename/merge pass from concept_rerank.json -> alias pass from stub_aliases.json ->
seed missing concepts (esp. LM II) -> delete/fix wrong edges -> recompile graph.
