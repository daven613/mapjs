# Torah Map Sweep — Synthesis (75-agent, 2026-07-12)

## 1. Headline numbers vs. the prior "89% supported" claim

- **Edges (fresh n=600): 455 supported = 75.8%**, 99 weak (16.5%), 46 wrong (7.7%). The 89% figure does not replicate; real support is ~76%, and 7 of the 455 "supported" also carry dubious polarity, so fully-clean edges ≈ 74.7%.
- Extrapolated to 12,328 live edges: **~950 wrong, ~2,040 weak.**
- **Concepts (n=3,586 scored): 54.8% score ≤1** (7 broken + 1,959 poor); only 45.2% score 2–3. The node layer is in worse shape than the edge layer.

## 2. Top themes among bad concepts

1. **Gloss-fragment slugs** — id built from a side detail, citation, or disambiguation note instead of the Hebrew term (c:noun-instruction=תורה, c:berakhot-5=יסורין, c:heb-aram=מים, c:holy-day-rest=שבת). Largest bucket by far.
2. **Id/content swaps and canonical-id squatting** — the most dangerous class: c:emunah holds ארץ ישראל, c:rosh-hashanah holds שופר, c:sitra-achra ↔ c:azut-ha-guf are crossed, c:aravah ↔ c:hoshana-rabba are crossed, the entire c:shabbat-N family holds non-Shabbat content, c:tikkun-haklali holds ה' חסדים וה' גבורות (three-way rotation). Slug-keyed queries silently hit the wrong concept.
3. **Homograph misreadings** — c:will-see-will absorbing 57 occurrences of יראה=fear; חיות read as creatures not chiyut; גשמים read as gashmiyut; איה the bird vs אַיֵּה; דלות read as letter dalet.
4. **Numbered-suffix duplicates** — -2/-3 nodes duplicating base concepts (tikkun-haklali-2, machashavah-2, etzah-2, peh-2, anachah-2).
5. **Verse/predication fragments as nodes** — p:1467 הַשֵּׁנִי, c:clause (יש לו שמחת יום טוב), c:ve-lo-chasakhta.

Edge failures mirror this: of 46 wrong, ~15 are surface-form homograph misresolutions, ~12 endpoint misresolutions to mismatched nodes, and ~14 polarity inversions — mostly tikkun/shemirah/hachna'ah encoded as *producing* the evil (tzitzit builds→נאוף, Elul kavanot builds→פגם הברית, ger מכניע ע"ז encoded builds→ע"ז). There is also no settled convention for "beneficial destruction" (subduing kelipot tagged harms in one edge, builds in a parallel one — i=470 vs 465).

## 3. Strongest missing-concept and fragmentation findings

**Missing (high confidence — multiple agents independently):**
- **יאוש** and **התחזקות** — zero hits each. The flagship LM II:78 dictum and the entire hitchazkut pillar have no nodes; fall→hitchazkut→return chains are inexpressible (ירידה also absent).
- **תמימות ופשיטות** (LM II:19), **לעשות מהתורות תפלות** (LM II:25), **גשר צר מאד / לא להתפחד** (LM II:48), **הודאה** (LM II:2) — first-order Breslov eitzot, all absent.
- **חנוכה** — zero hits while every other festival has nodes; carries first-class eitzot in LM II:2, II:7.
- **מקוה** base node (only hyper-specific composites exist), **אתרוג/הדס** (half the four species), **ברית הלשון** (the LM I:19 middle term).
- **The two kefirot of LM I:64** — the unanswerable chalal-hapanui heresy is missing, collapsing two *opposite* eitzot (answer vs. silence) into one node.
- Kabbalistic ladder gaps: אריך אנפין, נוקבא, כנסת ישראל, עלמא דאתגליא (its pair is registered), עולמות אצילות/בריאה, י"ג מדות הרחמים.

**Worst fragmentation:**
- **התגלות הרצון (LM II:4): 9 nodes** for one teaching — worst cluster found.
- **Clapping in prayer (LM I:44-46): ~7 nodes**; tefillah be-koach: 5; hitbodedut: 3; Azamra: 4; simchah shel mitzvah: 5+ (with c:yirah and c:viduy-devarim-2 squatting on its content).
- **Makifim (LM I:21):** 6+ content nodes plus three squatted ids (c:makifin=רצועה, c:makifin-2=חפה, c:makifim=emptied brain).
- Systematic Hebrew/Aramaic and plene/defective doubling: מחין/מוחין, עתיק/עתיקא/עתיק יומין, מחין דגדלות/גדלות המחין (and katnut ditto), יחוד/זווגא דקוב"ה ושכינתה, עשרה מיני נגונא/נגינה. A dedup rule for these variants would kill dozens of splits mechanically.

## 4. Implication for the planned alias pass (~982 unresolved forms)

Stub triage (n=600): **map 41.5% / new-concept 40.3% / keep-stub 16.5% / junk 1.7%**. The planned pass assumed unresolved forms mostly alias to existing nodes — **that's true for only ~4 in 10**. Nearly as many are genuinely missing concepts (consistent with the coverage gaps above). Run the alias pass as **two tracks**: an alias-map track and a node-creation track; and do it *after* the id-swap fixes, or ~hundreds of aliases will be attached to squatted/mismatched ids and inherit the corruption.

## 5. Prioritized to-do

1. **Un-squat the crossed/squatted ids first** (blocks everything else): shabbat-N family, rosh-hashanah↔head-year, emunah↔emunah-2, sitra-achra↔azut-ha-guf, aravah↔hoshana-rabba, tikkun-haklali rotation, makifin family, chametz, sukkah, terumah. Small list, highest corruption per node.
2. **Batch-rename the ~120 score≤1 slugs** per the fix column — mechanical, fixes are already specified.
3. **Merge pass on the named fragmentation clusters** — start with hitgalut-ratzon (9), clapping (7), simchat-mitzvah, makifim, hitbodedut, Azamra, mochin gadlut/katnut, tzimtzum/chalal, Atik; adopt a standing rule folding Aramaic/Hebrew and plene/defective variants into forms, not nodes.
4. **Polarity convention + flip pass**: decide once how "beneficial destruction" (מכניע/מבטל קליפות) is encoded, document it, then flip the ~14 confirmed inverted edges and sweep all builds/harms edges whose target is an evil-node with a tikkun/shemirah source verb (נתתקן, שמירה מ־, מכניע, נפסק).
5. **Homograph re-resolution sweep** on the recurring offenders: יראה, איה, חיות, גאוה הנ"ל, תמיד, כסיל, שמות, הליכה/הלכה, כתובה/כתיבה, דמים/דומם, נעור, עשירית/עשירות.
6. **Add the missing core nodes**: יאוש, התחזקות, ירידה, תמימות ופשיטות, גשר צר, הודאה, תורות→תפלות, חנוכה, מקוה, אתרוג/הדס, ברית הלשון, the two-kefirot split, plus the kabbalistic pair-completions (עלמא דאתגליא, נוקבא, כנסת ישראל).
7. **Then run the alias pass**, split into map vs. new-concept tracks per §4; route the 10 junk stubs to deletion and re-sample the 99 keep-stubs at the end.