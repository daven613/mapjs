# Judge feedback — item C

Scores: {'clarity': 8, 'faithfulness': 8, 'relatability': 6} | Verdicts: {'clarity': 'publish-with-fixes', 'faithfulness': 'publish-with-fixes', 'relatability': 'publish-with-fixes'}

## Issues
- [clarity] The teaching paragraph stacks three separate citations (I:66, I:14, I:9) in quick succession — as an ordinary reader I lose track of which quote is which and just skim past the parenthetical numbers.
- [clarity] The Hebrew text (כַּעַס מַזִּיק לְפַרְנָסָה) breaks the reading flow for someone with zero background — I can't parse it, so my eye just jumps it, which is fine, but it adds visual clutter to an already dense paragraph.
- [clarity] "the pattern suggests" is a slightly wobbly hedge right after a strong opening line — reads like the writer is stepping back from their own claim mid-sentence.
- [clarity] 'He would say' at the end assumes I'm still tracking that 'he' = Rebbe Nachman two sentences after the name was last used; a tiny stumble on a re-read but not on a fast first read.
- [faithfulness] The narrative sentence 'he teaches the reverse chain just as plainly, step by step: "through peace, one merits prayer" (I:14) — quarrel makes real prayer impossible, peace restores it — and "as one sustains..."' embeds an unquoted writer's gloss ('quarrel makes real prayer impossible, peace restores it') inside a construction ('he teaches... step by step') that implies it too comes from the text, when only the two quoted clauses are sourced.
- [faithfulness] 'Rebbe Nachman's counsel is exact: make peace where you actually live — at home, with a partner, a rival' overclaims precision — the attested spine only establishes shalom→tefillah→parnasah in general; the specific applications ('at home, with a partner, a rival') are the writer's extrapolation dressed as exact counsel.
- [faithfulness] 'Peace opens prayer; prayer opens the channel everything else flows through' uses 'channel' as if it were Rebbe Nachman's own image, but the process notes admit the strait/channel (מיצר/צינור) concept has NO node in the map at all — this is a purely writer-supplied bridge to the news hook, stated in the narrative without the hedge the very next sentence ('he would say') supplies.
- [faithfulness] The direct single-hop query c:shalom→c:parnasah-livelihood-material returns attested:false/incomplete — the file never claims this as one hop (correctly routes through tefillah-2), but a careless reader skimming just 'shalom...parnasah' claims could be misled if they tried the naive query; worth a one-line note in Process notes clarifying the direct edge doesn't exist.
- [relatability] The pivot from an active shooting war with real casualties to 'make peace with a partner, a rival' reads as a stretch — it risks feeling tone-deaf, like using a war as a springboard for a self-help note rather than sitting with the stakes.
- [relatability] Hedging language ('the pattern suggests, in a sea lane') breaks the narrative momentum and reads as academic disclaimer-speak rather than storytelling — a phone-scrolling reader will feel the writer flinching.
- [relatability] The three-part 'The story. / The teaching. / The takeaway.' scaffolding is functional but formulaic — it signals 'devotional content' before the reader even gets to the good line, which caps how far this travels outside an already-interested audience.
- [relatability] The takeaway ('make peace where you actually live... and the channel begins to widen from there') is true but generic — it could be advice for almost any hardship story; it doesn't feel earned specifically by THIS week's strait/oil story.

## Fixes (apply these)
- [clarity] Drop the three inline citation numbers (I:66, I:14, I:9) from the flowing prose, or move them to a single parenthetical at the end of the paragraph, so the reader isn't asked to file three source-tags while following one idea.
- [clarity] Cut or shorten the Hebrew original — keep the English translation only, since the Hebrew adds nothing for this audience and lengthens an already word-dense middle paragraph.
- [clarity] Replace 'the pattern suggests' with a flatter, more confident phrase like 'and, this reading proposes, in a sea lane' to keep the momentum of the sentence.
- [faithfulness] Rewrite the I:14/I:9 paragraph so the writer's connective gloss is set off (em-dash + explicit 'that is,' or a parenthetical) instead of sitting inside 'he teaches...step by step,' which currently reads as if the connective clause is also being taught.
- [faithfulness] Soften 'Rebbe Nachman's counsel is exact' to something like 'the pattern suggests' or 'applying it plainly might mean' before the household/partner/rival specifics, since those specifics aren't in any cited proof text.
- [faithfulness] Add one clause to the Process notes flagging that 'channel' in the takeaway is a writer-supplied bridge image (no map concept exists for מיצר/צינור), matching the honesty already shown for the missing-concept observation earlier in that section.
- [relatability] Cut or tighten 'the pattern suggests, in a sea lane' — let the analogy stand without the hedge; the guardrail note already covers the disclaimer job elsewhere.
- [relatability] Add one concrete, physical action to the takeaway (a specific thing to say or do today, not just 'make peace') so it's a task, not a mood.
- [relatability] Acknowledge the real-world stakes for one clause before pivoting inward — e.g. 'people are genuinely afraid and paying more for gas' — so the turn to personal peace doesn't feel like changing the subject.

## Failed verifications / framing flags
- c:shalom → c:parnasah-livelihood-material (direct single-hop chain query) returned {"ok": true, "complete": false, "attested": false} — not a problem for the file since it never claims this as a direct hop (it correctly uses the two-hop I:14→I:9 bridge via tefillah-2, which IS attested), but flagging since a naive re-run of just the endpoints looks unattested.
- Narrative clause 'quarrel makes real prayer impossible, peace restores it' — unlabeled writer paraphrase presented inside an 'he teaches...step by step' construction; reads as attested when it is not itself sourced to any proof text.
- Narrative clause 'Rebbe Nachman's counsel is exact: make peace where you actually live — at home, with a partner, a rival' — the specific applications are writer-supplied, not present in the I:66/I:14/I:9 proofs, but framed with the word 'exact.'

## Best lines (keep these)
- [clarity] "You do not control that strait. But everyone has one narrow channel their own livelihood flows through, and anger is what chokes it."
- [faithfulness] "The strait, he would say, was never only made of water." — the one place the writer's extension is honestly flagged as imagined ('he would say') rather than presented as a direct teaching.
- [relatability] "The strait, he would say, was never only made of water."