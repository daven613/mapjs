# Keywords and Classes Module

## Overview

This module provides functionality for managing keywords and classes metadata for Torah concept nodes. It solves the critical problem of **Hebrew homonyms** (same spelling, different meanings) by using **edge-level metadata** that preserves full context.

## Problem Solved

**Before:** Words like שנה (sleep vs year), אלף (letter alef vs one thousand), and חכמה (intelligence vs wisdom vs letter ches) were treated as completely separate concepts with no connections.

**After:** Each occurrence is tagged with full context (proof text, translations, connections), allowing you to correctly identify and categorize the meaning in each specific usage.

## Phase 1: Foundation ✓ COMPLETE

### What Was Implemented

#### Core Module (`keywords-classes-module.js`)
Full-featured class with comprehensive API:

- **Load/Save Metadata** - JSON-based with automatic backups
- **Extract Nodes** - Finds all 4,299 unique nodes with full context
- **Add/Remove Keywords** - Per edge occurrence (handles homonyms)
- **Add/Remove Classes** - Hierarchical categorization
- **Search by Keyword** - Fast indexed lookups
- **Search by Class** - Filter by category
- **Find Related** - Discover connections via shared keywords/classes
- **Auto-Suggest** - Keywords from English text
- **Detect Homonyms** - Found 12 in your data
- **Bulk Operations** - Apply to all occurrences of a node

#### Data Structure (`node_metadata.json`)
Edge-level metadata with:

- **15 Class Definitions** - spiritual-practice, mitzvot, emuna, prayer, torah-study, tikkun-habris, joy, tzedakah, repentance, holiness, eretz-yisrael, shabbat, wisdom, tzaddik, malchus
- **6 Keyword Definitions** - torah, prayer, faith, charity, repentance, joy
- **Hierarchical Support** - Classes can have parent classes
- **Bilingual** - Hebrew and English labels

#### Utilities

- **extract-nodes.js** - Analysis and extraction utilities
- **test-extraction.js** - Data extraction test script

## Statistics

- **4,299** unique nodes extracted
- **4,234** edges analyzed
- **8,468** total node occurrences
- **12** homonyms detected
- **15** class definitions created
- **Coverage:** Ready to tag all nodes

## Examples

### Example 1: Handling Homonyms

```javascript
const module = new KeywordsClassesModule(torahData);
await module.loadMetadata();

// שנה appears 13 times in your data
const occurrences = module.getNodeOccurrences('שנה');

// Tag first occurrence (sleep in Torah 35)
module.addKeywordToEdge('שנה', 35, 676, 'sleep');
module.addKeywordToEdge('שנה', 35, 676, 'rest');
module.addKeywordToEdge('שנה', 35, 676, 'renewal');
module.addClassToEdge('שנה', 35, 676, 'spiritual-practice');

// If שנה appears as "year" elsewhere, tag it differently
module.addKeywordToEdge('שנה', 12, 100, 'year');
module.addKeywordToEdge('שנה', 12, 100, 'time');
module.addClassToEdge('שנה', 12, 100, 'calendar');
```

### Example 2: Bulk Tagging

```javascript
// Apply keywords to all occurrences of תפילה (prayer)
module.applyToAllOccurrences('תפילה', {
    keywords: ['prayer', 'tefillah', 'davening'],
    keywords_he: ['תפילה', 'התפללות'],
    classes: ['prayer', 'spiritual-practice']
});

// Now search for all prayer-related concepts
const prayerEdges = module.findEdgesByKeyword('prayer');
console.log(`Found ${prayerEdges.length} prayer-related concepts`);
```

### Example 3: Finding Related Concepts

```javascript
// Get context for a specific edge
const context = module.getEdgeContext('תורה', 1, 0);
console.log('Hebrew:', context.nodeText);
console.log('English:', context.nodeTextEn);
console.log('Proof:', context.proof);
console.log('Connected to:', context.connectedNodeTextEn);

// Find related edges
const related = module.findRelatedEdges('תורה', 1, 0);
related.forEach(edge => {
    console.log(`${edge.nodeId} (score: ${edge.relationScore})`);
});
```

### Example 4: Auto-Suggestion

```javascript
// Get keyword suggestions based on English text and proof
const suggestions = module.suggestKeywords('תורה', 1, 0);
console.log('Suggested keywords:', suggestions);
// Output: ["torah", "able", "intellect", "everything", ...]
```

## Data Structure Design

### Edge-Level Metadata (Recommended Approach)

Each edge occurrence has independent metadata:

```json
{
  "edge_metadata": {
    "שנה:35:676": {
      "node_id": "שנה",
      "reference": 35,
      "edge_index": 676,
      "keywords": ["sleep", "rest", "renewal"],
      "keywords_he": ["שינה", "מנוחה"],
      "classes": ["spiritual-practice", "physical-needs"],
      "last_modified": "2025-10-21T..."
    }
  }
}
```

**Why Edge-Level?**
- ✓ Full context for each occurrence (proof text, translations, connections)
- ✓ No confusion between different meanings
- ✓ Easy to browse: "שנה in Torah 35" vs "שנה in Torah 54"
- ✓ Simple key structure: `"node_id:reference:edgeIndex"`

## Detected Homonyms

The module detected these homonyms in your data:

1. **חכמה** - intelligence, the hebrew letter ches, wisdom
2. **תורה** - torah, dealing with torah
3. **בכור** - first born (son), the first born son
4. **חן** - grace and importance, grace
5. **אות חי"ת** - beast, the hebrew letter ches
6. **מקל** - alusa, sticks and names of hashem, stick
7. And 6 more...

These need manual review with full context to tag correctly!

## Next Steps: Phase 2 - Editor UI

The foundation is complete and tested. Next phase will add:

1. **Metadata Editor Interface**
   - Search/select node to edit
   - Browse all occurrences with full context
   - Add/remove keywords and classes
   - View proof text and connections
   - Navigate between occurrences
   - Preview related nodes

2. **Bulk Operations UI**
   - Apply keyword to multiple nodes
   - Apply class to multiple nodes
   - Import/export metadata
   - Review homonyms

3. **Validation**
   - Prevent duplicate keywords
   - Validate class hierarchy
   - Check for conflicts

## Testing

All core functionality is tested and working:

```bash
node js/modules/test-extraction.js
# Shows: 4,299 nodes, 12 homonyms, statistics

# Quick test
node -e "const KC = require('./js/modules/keywords-classes-module.js'); ..."
```

## Files Created

```
/home/user/mapjs/
├── data/
│   ├── node_metadata.json              # Metadata storage
│   └── node_extraction_results.json    # Analysis results
├── js/modules/
│   ├── keywords-classes-module.js      # Core module (600+ lines)
│   ├── extract-nodes.js                # Extraction utilities
│   └── test-extraction.js              # Test script
└── docs/
    └── KEYWORDS_AND_CLASSES_DESIGN.md  # Full design document
```

## Usage

```javascript
// Load the module
const KeywordsClassesModule = require('./js/modules/keywords-classes-module.js');

// Initialize with your Torah data
const module = new KeywordsClassesModule(torahData);

// Load existing metadata
await module.loadMetadata();

// Extract all nodes
module.extractAllNodes();

// Work with the data
const occurrences = module.getNodeOccurrences('תורה');
module.addKeywordToEdge('תורה', 1, 0, 'torah');
module.addClassToEdge('תורה', 1, 0, 'torah-study');

// Save changes
await module.saveMetadata();
```

## API Reference

See the comprehensive design document at:
`/home/user/mapjs/docs/KEYWORDS_AND_CLASSES_DESIGN.md`

## Status

- [x] Phase 1: Foundation - **COMPLETE**
- [ ] Phase 2: Editor UI - Ready to start
- [ ] Phase 3: Integration - Pending
- [ ] Phase 4: Auto-tagging - Pending

---

**Created:** 2025-10-21
**Status:** Phase 1 Complete and Tested
**Ready for:** UI Development
