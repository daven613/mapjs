# The Conceptual Framework of the Torah Map

> This document defines the data model, relationship types, and structural concepts used to represent Rebbe Nachman's teachings in graph form. It serves as the reference for all future classification, enrichment, and traversal work.

---

## 1. The Two Fundamental Relationship Types

Rebbe Nachman's teachings operate on two fundamentally different axes. Every connection in the dataset must be understood as belonging to one of these two types.

---

### 1.1 Bechina (בְּחִינָה) — Parallel Aspects / Shared Nature

**What it is:** A bechina states that two concepts share the same essential nature, quality, or dimension. They are different expressions of the same underlying reality. The relationship is **symmetric** — neither is the cause of the other; they are two faces of the same thing.

**How Rebbe Nachman states it:** Explicitly, using language like:
- "X הוא בחינת Y" — X is an aspect of Y
- "X נקרא Y" — X is called Y
- "X כנ"ל" — X is as said above (equating it to a prior concept)

**Key property:** Reversible. If Jacob is a bechina of sekhel, then sekhel is also present in Jacob. Neither produces the other — they illuminate the same idea from different angles.

**Examples from Torah #1:**
- חכמה (wisdom) is a bechina of the letter חי"ת (because חי"ת = חיות = vitality, and wisdom is the life-force of all things)
- יעקב is a bechina of the one who attaches himself to the sekhel
- מלכות is a bechina of the letter נו"ן (poor, receiving, the moon)

**Use in the map:** Bechina edges are the backbone of the graph. They show the conceptual topology — which ideas are structurally identical across different domains (body, soul, letters, personalities, natural phenomena).

---

### 1.2 Eitza (עֵיצָה) — Cause and Effect / Flow

**What it is:** An eitza describes how one concept *produces*, *enables*, or *leads to* another. It is the **directional** dimension of the teaching — the flow from one idea to the next. This is not two faces of the same thing; this is one thing causing or generating another.

**How Rebbe Nachman states it:** Often framed as advice or consequence:
- "על ידי X בא Y" — through X comes Y
- "X מביא ל-Y" — X brings Y
- "כדי להשיג Y צריך X" — to achieve Y one needs X
- The teaching's *practical conclusion* — what you should do and what will follow

**Key property:** Directional, asymmetric. X → Y does not imply Y → X. One thing flows into the next.

**Examples from Torah #1:**
- חן (grace) → חקיקה (engraving): having grace engraves a place in the listener's heart — grace *produces* the engraving, it is not the same as it
- חכמה (wisdom) → תפלה (prayer): attaching to wisdom enables prayer to be accepted
- Torah (the vav/staff) → overcoming the yetzer hara: Torah *causes* the yetzer's madness to be defeated

**Use in the map:** Eitza edges show the *narrative flow* of the teaching — the chain of cause and consequence that gives each Torah its argument and practical guidance.

---

## 2. The Critical Distinction

| | Bechina | Eitza |
|---|---|---|
| Question | "What IS this, at its core?" | "What does this LEAD TO or PRODUCE?" |
| Direction | Symmetric — both directions | Asymmetric — one direction |
| Nature | Parallel / same essence | Sequential / cause-and-effect |
| In the teaching | "X is a bechina of Y" | "through X you get Y" / "X therefore Y" |
| Graph type | Undirected conceptual equivalence | Directed causal flow |

**The test:** Ask: *does one produce the other, or are they both expressions of the same thing?*
- חן and מלכות — both aspects of the same receptive quality → **bechina**
- חן and חקיקה — grace *produces* the engraving in the heart → **eitza** (cause and effect)

---

## 3. Packages (חֲבִילָה, pl. חֲבִילוֹת) — Thematic Clusters

### 3.1 What a Package Is

A package is a named collection of concepts within a single Torah that all share a **common denominator** — they form a thematic family, illuminate the same domain, and are connected primarily through **bechina** (parallel) relationships.

### 3.2 Key Rules

1. **Torah-specific** — each Torah's packages are entirely independent. Even if two Torahs both discuss wisdom, each Torah's wisdom package stands on its own. The *same concept* (node) can belong to different packages in different Torahs without conflict.
2. **Built on bechinas only** — packages are formed from bechina-connected nodes, not eitza edges. Cause-and-effect flows *between* packages, not within them.
3. **Every node belongs to exactly one package** per Torah in which it appears.
4. **Named after the dominant concept** — the most connected / most central node gives the package its name.

### 3.3 What Packages Are NOT

- Not cause-and-effect chains (those are eitza connections *between* packages)
- Not cross-Torah super-categories (each Torah's packages are local to that Torah)
- Not label inconsistencies (those are alias fixes)

### 3.4 Package Polarity: Good, Evil, and Neutral

**This is a fundamental structural feature of Rebbe Nachman's teachings.**

Every concept the Rebbe discusses exists within a cosmic polarity of good and evil. His teachings are predominantly about the positive — holiness, wisdom, prayer, the soul — but the evil side is always present as the counterforce. Packages must therefore be marked with their polarity:

| Polarity | Description | Examples |
|----------|-------------|---------|
| `good` | Concepts belonging to the domain of holiness, the positive teaching | חכמה, מלכות דקדושה, תפלה, יעקב |
| `evil` | Concepts belonging to the domain of the negative, the opposing force | יצר הרע, מלכות דסטרא אחרא, עשו, שגעון |
| `neutral` | Concepts that are objects or structures which can appear in both domains, depending on context | letters of the alphabet, body parts, natural phenomena used as metaphors |

**The same concept can appear in both a good package and an evil package within the same Torah.** This is not a contradiction — it reflects a deep structural feature of the teachings: the same reality can be filled with holiness or with evil, depending on its orientation.

**Example from Torah #1:**
- מלכות (kingship) appears in Package 2 (מלכות וחן) as **holy malkhut** — the moon receiving light from the sun of wisdom → `good`
- מלכות (kingship) appears in Package 3 (יצר הרע ומלכות הרשעה) as **evil malkhut** (sitra achra's moon) → `evil`
- The same letter נו"ן, the same concept of "a kingdom that receives" — but one is oriented toward God and one toward the sitra achra. These are two separate package memberships, in two separate packages, with opposite polarities.

**Why this matters for traversal:** When navigating the graph, knowing a package's polarity allows you to understand whether you are moving through the positive dimension or the negative dimension of the teaching. A path from a good package to an evil package through a shared node reveals the *point of fracture* — the concept that can tip either way.

---

## 4. The Good/Evil Mirror Structure

One of the most consistent structural patterns in Rebbe Nachman's teachings is that **the positive teaching always has an exact evil mirror**. For nearly every cluster of good concepts, there is a corresponding cluster of evil concepts with the same structure:

| Good package | Evil mirror |
|-------------|-------------|
| חכמה (wisdom of holiness) | חכמת הרע (evil wisdom, the "old foolish king" who mimics wisdom) |
| מלכות דקדושה (holy kingdom) | מלכות דסטרא אחרא (evil kingdom) |
| יעקב (the one who grasps sekhel) | עשו (the one who despises sekhel) |
| לבנה (the moon receiving holy light) | לבנה דסטרא אחרא (the moon aligned with evil) |

This mirror structure means that when classifying packages, you should actively look for the evil counterpart of every good package. If you find a Torah discussing wisdom, look for what it says about evil wisdom. If it discusses prayer, look for what opposes prayer.

---

## 5. Edge Types Summary

| Type | Hebrew | What it represents | Direction |
|------|--------|--------------------|-----------|
| `bechina` | בְּחִינָה | Parallel aspects — same essential nature | Undirected |
| `eitza` | עֵיצָה | Cause-and-effect — one thing produces another | Directed |

---

## 6. Torah #1 — Worked Example

Torah #1 contains **5 packages** across **49 nodes** from **48 bechina edges**. Their structure maps exactly to the Torah's four-part argument, with the good/evil polarity clearly visible:

| # | Package | Polarity | Nodes | Dominant Node |
|---|---------|----------|-------|---------------|
| 1 | חָכְמָה וְיַעֲקֹב — Wisdom and Jacob | good | 13 | חכמה (8 connections) |
| 2 | מַלְכוּת וְחֵן — Kingship and Grace | good | 14 | מלכות (9 connections) |
| 3 | יֵצֶר הָרָע וּמַלְכוּת הָרְשָׁעָה — Evil Inclination and Wicked Kingdom | evil | 13 | יצר הרע / מלכות הרשעה |
| 4 | תּוֹרָה וָמַקֵּל — Torah and the Staff | good | 6 | תורה (6 connections) |
| 5 | אוֹת תָּ"ו וְהַחֲקִיקָה — The Letter Tav and the Engraving | good | 3 | אות ת"ו |

**The Torah's argument in four moves:**
```
Pursue this →          It produces →    This opposes it →   This defeats it
[Pkg 1: good]          [Pkg 2: good]    [Pkg 3: evil]       [Pkg 4: good]
חכמה / יעקב    →eitza→  מלכות / חן  →eitza→  יצר הרע       →eitza→  תורה / מקל
                              ↓ eitza
                         [Pkg 5: good]
                         אות ת"ו / חקיקה
```

**The good/evil mirror in Torah #1:**
- Package 1 (חכמה) mirrors Package 3's "מלך זקן וכסיל" — the old foolish king who is the anti-wisdom
- Package 2 (מלכות דקדושה) mirrors Package 3's מלכות הרשעה — same structure, opposite orientation
- Package 2's לבנה (the good moon) mirrors Package 3's לבנה דסטרא אחרא (the evil moon)

---

## 7. Cross-Torah Traversal

Because packages are Torah-specific, concepts that appear in multiple Torahs act as **bridges**:

- `חכמה` in Torah #1's Package 1 and `חכמה` in Torah #7's Package X are the *same node*
- Traversal: Node A (Torah #1 Package 1) → via bechina/eitza → `חכמה` → enter Torah #7 Package X → traverse from there

This means the entire dataset forms one large traversable network, with individual Torahs as distinct thematic islands connected through shared conceptual nodes. The richer a concept is (appears in many Torahs), the more central a bridge it becomes across the full graph.

**Polarity is preserved across traversal:** Moving from a good package in one Torah through a shared node into an evil package in another Torah is meaningful — that shared node is a concept that exists on the boundary between the two poles.

---

## 8. Classification Guidelines

When classifying new content, always ask:

**1. Bechina or Eitza?**
Test: does one *produce* the other, or are they both *expressions of the same thing?*

**2. Which package does this node belong to?**
Ask: what is its essential nature/domain? Which cluster of concepts shares that nature in *this Torah*?

**3. Good, evil, or neutral?**
Is this concept aligned with holiness, with the opposing force, or is it an object/structure that can serve either?

**4. Is there an evil mirror?**
For every good package you identify, actively look for its evil counterpart in the same Torah.

**5. Is this a label inconsistency (alias)?**
Is this a different name for a concept that already exists in the dataset?

---

*Document created: 2026-03-02*
*Based on analysis of Torah #1 (Likutay Moharan) and the existing dataset of ~4,200 edges.*
