# Keywords and Classes Module Design Document

## Executive Summary

This document outlines the design for a Keywords and Classes module to enhance the Torah concept mapping system. The module will allow connecting related concepts (like "תורה" and "התורה") through shared keywords and organizing nodes into semantic classes.

## Problem Statement

Currently, similar concepts are treated as completely separate entities:
- "תורה" (torah) and "התורה" (hatorah) have no connection
- No way to find all concepts related to a theme (e.g., all Torah-related concepts)
- No hierarchical organization or categorization of concepts
- Difficult to perform semantic searches across related terms

## Solution Overview

### 1. Add Keywords System
**Keywords** are normalized, canonical terms that represent the essence of concepts:
- Extract core meaning from variations (התורה → torah, תורה → torah)
- Enable semantic grouping and search
- Create implicit connections between related concepts
- Support multiple keywords per node

### 2. Add Classes System
**Classes** are categories or taxonomies for organizing concepts:
- Spiritual states (e.g., "emuna", "prayer", "holiness")
- Practical guidance (e.g., "livelihood", "health", "relationships")
- Torah topics (e.g., "shabbat", "kashrut", "holidays")
- Support hierarchical classification

## Handling Homonyms: The Critical Challenge

**The Problem:** The same Hebrew word can have completely different meanings:
- **שנה** = "sleep" (sheina) OR "year" (shana)
- **אלף** = "letter alef" OR "one thousand" (elef)
- Words with different vowel marks (nikud) are written the same without vowels

**The Solution:** Use the rich contextual data already in your torah1.js and torah2.js files:
- **node1_text / node2_text** - Hebrew with vowel marks (שֵׁנָה vs שָׁנָה)
- **node1_text_en / node2_text_en** - English translations disambiguate meaning
- **proof** - The source text provides deep context
- **Connected nodes** - What this concept relates to
- **Reference number** - Torah source provides additional context

## Enhanced Data Structure

### Current Node Structure (Edges)
```javascript
{
    "id": 1.0,
    "node1_id": "שנה",              // Ambiguous: could be sleep or year
    "node2_id": "חדוש השכל",
    "node1_text": "שֵׁנָה",          // ✓ With vowels: this is "sleep"
    "node2_text": "וְחִדּוּשׁ הַשֵּׂכֶל",
    "node1_text_en": "Sleep",       // ✓ English confirms: sleep, not year
    "node2_text_en": "Renewal of intellect",
    "proof": "וְחִדּוּשׁ הַשֵּׂכֶל...הוּא עַל־יְדֵי שֵׁנָה...",  // ✓ Context!
    "reference": 35,
    "type": "eitza"
}
```

### NEW: Context-Aware Node Metadata Structure

We will create a separate `node_metadata.json` file to store keywords and classes.

**Two storage approaches to handle homonyms:**

#### Approach 1: Edge-Level Metadata (RECOMMENDED)
Store metadata per edge occurrence, using the edge ID or combination of node_id + reference:

```javascript
{
    "edge_metadata": {
        // Key: edge ID or "node_id:reference" for precision
        "שנה:35": {
            "node_id": "שנה",
            "reference": 35,
            "meaning": "sleep",  // Disambiguate the meaning
            "keywords": ["sleep", "rest", "renewal"],
            "keywords_he": ["שינה", "מנוחה"],
            "classes": ["physical-needs", "spiritual-rest"]
        },
        "שנה:12": {  // If שנה appeared as "year" in reference 12
            "node_id": "שנה",
            "reference": 12,
            "meaning": "year",
            "keywords": ["year", "time", "cycle"],
            "keywords_he": ["שנה", "זמן"],
            "classes": ["time", "calendar"]
        }
    }
}
```

#### Approach 2: Node-Level with Sense Variants (Alternative)
Store at node level but include multiple "senses" for homonyms:

```javascript
{
    "nodes": {
        "שנה": {
            "senses": [
                {
                    "sense_id": "sleep",
                    "meaning": "Sleep, rest",
                    "hebrew_form": "שֵׁנָה",
                    "keywords": ["sleep", "rest", "renewal"],
                    "keywords_he": ["שינה", "מנוחה"],
                    "classes": ["physical-needs", "spiritual-rest"],
                    "references": [35, 54],  // Where this meaning appears
                    "context": "Physical sleep as spiritual renewal"
                },
                {
                    "sense_id": "year",
                    "meaning": "Year, annual cycle",
                    "hebrew_form": "שָׁנָה",
                    "keywords": ["year", "time", "cycle"],
                    "keywords_he": ["שנה", "זמן"],
                    "classes": ["time", "calendar"],
                    "references": [12, 18],  // Where this meaning appears
                    "context": "Annual cycle and time periods"
                }
            ]
        },
        "תורה": {  // Simple case: no homonyms
            "keywords": ["torah", "study", "learning"],
            "keywords_he": ["תורה", "לימוד"],
            "classes": ["spiritual-practice", "mitzvot"],
            "aliases": ["התורה", "תורתינו"],
            "description": "Torah study and learning",
            "last_modified": "2025-10-21T10:30:00Z"
        }
    },
    "class_definitions": {
        "spiritual-practice": {
            "label": "Spiritual Practice",
            "label_he": "עבודה רוחנית",
            "description": "Practices for spiritual development",
            "parent": null,
            "color": "#9C27B0"
        },
        "mitzvot": {
            "label": "Mitzvot",
            "label_he": "מצוות",
            "description": "Torah commandments",
            "parent": "spiritual-practice",
            "color": "#2196F3"
        }
        // ... more classes
    },
    "keyword_definitions": {
        "torah": {
            "label": "Torah",
            "label_he": "תורה",
            "description": "Torah study, learning, and wisdom",
            "related_keywords": ["study", "learning", "wisdom"]
        }
        // ... more keywords
    }
}
```

### Recommendation: Which Approach to Use?

**Use Approach 1 (Edge-Level Metadata)** for maximum precision:

**Pros:**
- ✓ Each occurrence can be tagged independently with full context
- ✓ Simple key structure: `"node_id:reference"` or edge ID
- ✓ Editor can show the exact proof text and connections for that occurrence
- ✓ No risk of mixing different meanings
- ✓ Easy to browse: "שנה in Torah 35" vs "שנה in Torah 54"

**Cons:**
- More entries in the metadata file (one per edge occurrence)
- Need to aggregate when searching by keyword

**Use Approach 2 (Senses)** only if:
- You want a more compact metadata file
- You're willing to manually group occurrences by meaning

**Recommended:** Start with Approach 1 (edge-level). It matches your data structure perfectly and gives you the most control when tagging with the full context visible.

## Module Architecture

### File Structure
```
/home/user/mapjs/
├── data/
│   ├── torah1.js                    (existing)
│   ├── torah2.js                    (existing)
│   └── node_metadata.json           (NEW)
├── js/
│   ├── modules/
│   │   ├── keywords-classes-module.js    (NEW - main module)
│   │   ├── metadata-loader.js            (NEW - load/save metadata)
│   │   └── metadata-editor.js            (NEW - UI for editing)
│   └── enhanced-search.js                (NEW - keyword-aware search)
└── docs/
    └── KEYWORDS_AND_CLASSES_DESIGN.md    (this document)
```

### Core Module: keywords-classes-module.js

```javascript
class KeywordsClassesModule {
    constructor(torahData, metadataPath) {
        this.torahData = torahData;  // Array of edges from torah1.js/torah2.js
        this.metadata = null;
        this.metadataPath = metadataPath;
        this.edgeIndex = new Map(); // "node_id:reference" -> metadata
        this.keywordIndex = new Map(); // keyword -> Set(edge_keys)
        this.classIndex = new Map(); // class -> Set(edge_keys)
        this.nodeOccurrences = new Map(); // node_id -> Array of edge objects
    }

    // Load metadata from JSON
    async loadMetadata() { }

    // Save metadata to JSON
    async saveMetadata() { }

    // Get all edges (occurrences) for a node_id
    getNodeOccurrences(nodeId) {
        // Returns array of edges where node appears
        // Each edge includes: id, node1_id, node2_id, proof, reference, etc.
    }

    // Get metadata for specific edge occurrence
    getEdgeMetadata(nodeId, reference) {
        // Key: "nodeId:reference"
        // Returns: { keywords, classes, meaning, etc. }
    }

    // Update metadata for a specific edge
    updateEdgeMetadata(nodeId, reference, updates) {
        // Updates keywords/classes for this specific occurrence
    }

    // Get contextual data for editing (includes proof, connections, etc.)
    getEdgeContext(nodeId, reference) {
        // Returns full edge data + current metadata
        // Used to display context in editor
    }

    // Add keyword to a specific edge
    addKeywordToEdge(nodeId, reference, keyword) { }

    // Remove keyword from a specific edge
    removeKeywordFromEdge(nodeId, reference, keyword) { }

    // Add class to a specific edge
    addClassToEdge(nodeId, reference, className) { }

    // Remove class from a specific edge
    removeClassFromEdge(nodeId, reference, className) { }

    // Find all edges with a keyword
    findEdgesByKeyword(keyword) {
        // Returns edges (with full context) that have this keyword
    }

    // Find all edges in a class
    findEdgesByClass(className) {
        // Returns edges (with full context) in this class
    }

    // Find related edges (shared keywords/classes)
    findRelatedEdges(nodeId, reference, options = {}) {
        // Find edges with shared keywords or classes
    }

    // Auto-suggest keywords based on proof text and English translation
    suggestKeywords(nodeId, reference) {
        // Extract keywords from node_text_en and proof
        // Use simple NLP or keyword extraction
    }

    // Detect homonyms (same node_id, different meanings)
    detectHomonyms() {
        // Find node_ids that appear with different English translations
        // Flag for manual review
    }

    // Build search indices
    buildIndices() {
        // Build keyword and class indices
        // Build node occurrence map
    }

    // Extract all unique nodes and their occurrences
    extractAllNodes() {
        // Create map of node_id -> array of occurrences
        // Each occurrence includes full edge data for context
    }

    // Apply metadata to all occurrences of a node
    applyToAllOccurrences(nodeId, metadata) {
        // Bulk apply keywords/classes to all edges with this node_id
    }
}
```

## Implementation Plan

### Phase 1: Foundation (Week 1)
1. **Create metadata structure**
   - Define `node_metadata.json` schema
   - Create initial empty metadata file
   - Extract all unique nodes from torah1.js and torah2.js

2. **Build core module**
   - Implement `KeywordsClassesModule` class
   - Add load/save functionality
   - Create indexing system

3. **Define initial classes**
   - Identify 10-15 core classes from existing data
   - Create class hierarchy
   - Document class definitions

### Phase 2: Editor UI (Week 2)
1. **Create metadata editor interface**
   - Search/select node to edit
   - Add/remove keywords
   - Add/remove classes
   - View related nodes
   - Preview changes

2. **Implement bulk operations**
   - Apply keyword to multiple nodes
   - Apply class to multiple nodes
   - Import/export metadata

3. **Add validation**
   - Prevent duplicate keywords
   - Validate class hierarchy
   - Check for conflicts

### Phase 3: Integration (Week 3)
1. **Enhanced search functionality**
   - Search by keyword
   - Filter by class
   - "Related concepts" query
   - Fuzzy matching (torah ≈ hatorah)

2. **Visual enhancements**
   - Color-code nodes by class
   - Show keyword badges
   - Highlight related nodes

3. **Query extensions**
   - Add "Get by Keyword" query type
   - Add "Get by Class" query type
   - Enhance existing queries with keyword matching

### Phase 4: Auto-tagging & Polish (Week 4)
1. **Implement auto-suggestion**
   - NLP-based keyword extraction
   - Suggest classes based on existing patterns
   - Bulk auto-tag with review

2. **Documentation & training**
   - User guide for adding keywords/classes
   - Best practices document
   - Example workflows

## User Interface Design

### Metadata Editor Modal (WITH CONTEXT)

The editor MUST show all contextual information from the original data to help disambiguate homonyms (words with multiple meanings):

```
┌───────────────────────────────────────────────────────────────────┐
│  Edit Node: שנה (Occurrences: 4)                          [1/4]   │
├───────────────────────────────────────────────────────────────────┤
│  Context from Torah Data:                                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Node ID: שנה                                                 │ │
│  │ Hebrew Text: שֵׁנָה                                           │ │
│  │ English: Sleep                                               │ │
│  │                                                              │ │
│  │ Connected to: חדוש השכל, הינו חדוש הנשמה                     │ │
│  │    (Renewal of intellect, renewal of the soul)              │ │
│  │                                                              │ │
│  │ Proof Text (excerpt):                                        │ │
│  │ "וְחִדּוּשׁ הַשֵּׂכֶל...הוּא עַל־יְדֵי שֵׁנָה, כַּמּוּבָא        │ │
│  │  בַּזֹּהַר הַקָּדוֹשׁ...כִּי כְּשֶׁהַמֹּחִין מִתְיַגְּעִים,        │ │
│  │  אָז עַל־יְדֵי הַשֵּׁנָה הֵם מִתְחַדְּשִׁים"                     │ │
│  │                                                              │ │
│  │ Reference: Torah 35                                          │
│  │ Type: eitza (advice)                                         │ │
│  │                                                              │ │
│  │ [< Prev Occurrence] [Next Occurrence >]                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Keywords (English):                                              │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [sleep] [rest] [renewal] [+Add]                              │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Keywords (Hebrew):                                               │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [שינה] [מנוחה] [+Add]                                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Classes:                                                         │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ [physical-needs] [renewal] [spiritual-rest] [+Add]          │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ⚠ Disambiguation Note:                                          │
│  This node appears 4 times in the data. Review each occurrence   │
│  to ensure consistent tagging, or add occurrence-specific notes. │
│                                                                   │
│  Occurrence Notes:                                                │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │ Occ 1 (Torah 35): Sleep as spiritual renewal                │ │
│  │ Occ 2 (Torah 35): Sleep connecting to faith                 │ │
│  │ Occ 3 (Torah 54): Sleep attaching thought to world to come  │ │
│  │ Occ 4 (Torah 35): Sleep as business dealings in faith       │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  Other nodes with this ID:                                        │
│  • שנה (year) - NOT FOUND IN CURRENT DATA                        │
│                                                                   │
│  [Apply to All Occurrences] [Apply to This Only]                │
│  [Save] [Cancel] [Save & Next Node]                             │
└───────────────────────────────────────────────────────────────────┘
```

**Key Features for Context-Aware Editing:**

1. **Show ALL contextual data:**
   - node1_text / node2_text (Hebrew with vowel marks)
   - node1_text_en / node2_text_en (English translations)
   - proof (source text - critical for understanding meaning!)
   - reference (Torah number)
   - Connected nodes (what this connects to)
   - Relationship type (eitza/bechina/cause)

2. **Browse all occurrences:**
   - If node_id appears multiple times, show counter: [1/4]
   - Navigate between occurrences: [< Prev | Next >]
   - See if different occurrences need different keywords

3. **Disambiguation support:**
   - Warning when same node_id has multiple meanings
   - Option to add occurrence-specific notes
   - Ability to apply keywords to all or individual occurrences

4. **Context panel:**
   - Always visible while editing
   - Shows proof text (the most important context!)
   - Shows relationships (what connects to what)

### Enhanced Search Interface

Add new query types to existing dropdown:

```
Query Type: [Get by Keyword ▼]
            - Get Advice
            - Get Effects
            - Search by Torah
            - Get Bechinos
            - Get All Connected Topics
            - Connect Two Bechinos
            - Likutay Halachos Style
            ─────────────────────────
            - Get by Keyword        (NEW)
            - Get by Class          (NEW)
            - Related Concepts      (NEW)

Search: [torah________________________] 🔍

Options: ☑ Include aliases
         ☑ Fuzzy matching
         ☐ Exact keyword only

Results: 47 nodes found
```

## Example Use Cases

### Use Case 1: Connect "Torah" Variations
**Problem:** User searches for "torah" but misses "hatorah" results

**Solution:**
1. Add keyword "torah" to both "תורה" and "התורה" nodes
2. Search by keyword "torah" returns both
3. Visual indicator shows they share keywords

### Use Case 2: Find All Prayer-Related Concepts
**Problem:** Want to see all concepts related to prayer

**Solution:**
1. Tag all prayer nodes with class "prayer"
2. Query "Get by Class: prayer" returns all
3. Can visualize prayer-related subgraph

### Use Case 3: Discover Related Topics
**Problem:** Exploring "emuna" and want related concepts

**Solution:**
1. Click "Find Related" on "emuna" node
2. System finds nodes sharing keywords: "faith", "trust", "belief"
3. System finds nodes in same classes: "spiritual-states", "foundations"
4. Display scored list of related concepts

## Technical Considerations

### 1. Performance
- **Indexing:** Build keyword and class indices on load for O(1) lookups
- **Caching:** Cache frequently accessed metadata
- **Lazy loading:** Only load full metadata when editor is opened

### 2. Data Integrity
- **Validation:** Ensure keywords are lowercase, normalized
- **Conflict resolution:** Handle node_id collisions
- **Backup:** Auto-backup metadata before saves

### 3. Language Support
- **Hebrew normalization:** Handle different Hebrew spellings
- **Bilingual keywords:** Support both Hebrew and English keywords
- **Translation mapping:** Link Hebrew and English keyword pairs

### 4. Scalability
- **Current scale:** ~4,200 edges, ~800 unique nodes
- **Future scale:** System should handle 10,000+ nodes
- **File size:** Keep metadata JSON under 1MB

## Migration Strategy

### Initial Population
```javascript
// Script to create initial metadata from existing data
function generateInitialMetadata(torahData) {
    const metadata = { nodes: {}, class_definitions: {}, keyword_definitions: {} };

    // Extract all unique nodes
    const uniqueNodes = extractUniqueNodes(torahData);

    // For each node, create basic metadata
    uniqueNodes.forEach(node => {
        metadata.nodes[node.id] = {
            keywords: extractKeywordsFromText(node.text_en),
            keywords_he: extractKeywordsFromText(node.text),
            classes: inferClassFromReferences(node),
            aliases: [],
            description: `Auto-generated from ${node.text_en}`,
            last_modified: new Date().toISOString()
        };
    });

    return metadata;
}
```

### Manual Review Process
1. Generate initial metadata automatically
2. Review top 50 most-connected nodes
3. Manually refine keywords and classes
4. Establish keyword/class naming conventions
5. Bulk-apply patterns to remaining nodes

## Success Metrics

1. **Coverage:** 80%+ of nodes have at least 1 keyword and 1 class
2. **Connectivity:** Average 5+ nodes per keyword
3. **Usability:** Users can find related concepts in 2 clicks or less
4. **Accuracy:** 90%+ of suggested keywords are relevant

## Next Steps

1. **Review this document** with stakeholders
2. **Approve data structure** for node_metadata.json
3. **Define initial class taxonomy** (10-15 core classes)
4. **Implement Phase 1** (foundation module)
5. **Create proof-of-concept** editor UI
6. **Test with sample data** (100 nodes)
7. **Iterate based on feedback**

## Questions for Discussion

1. Should keywords be automatically extracted or manually curated?
2. How many classes is optimal? (10? 50? 100?)
3. Should classes be hierarchical (tree) or flat (tags)?
4. Do we need weighted keywords (primary vs. secondary)?
5. Should the system auto-suggest related nodes during editing?
6. How to handle keyword conflicts (same word, different meanings)?

## Appendix: Example Metadata Entries

### Example 1: Homonym - שנה (Sleep vs Year)

Using Edge-Level Metadata (Approach 1 - RECOMMENDED):

```json
{
    "edge_metadata": {
        "שנה:35:1": {
            "node_id": "שנה",
            "reference": 35,
            "edge_index": 1,
            "meaning": "sleep",
            "hebrew_form": "שֵׁנָה",
            "english": "Sleep",
            "keywords": ["sleep", "rest", "renewal", "mind-renewal"],
            "keywords_he": ["שינה", "מנוחה", "חידוש"],
            "classes": ["physical-needs", "spiritual-rest", "renewal"],
            "context_note": "Sleep as means of renewing the intellect",
            "connected_to": "חדוש השכל",
            "last_modified": "2025-10-21T10:30:00Z"
        },
        "שנה:35:2": {
            "node_id": "שנה",
            "reference": 35,
            "edge_index": 2,
            "meaning": "sleep",
            "hebrew_form": "שֵׁנָה",
            "english": "Sleep",
            "keywords": ["sleep", "faith", "business-dealings"],
            "keywords_he": ["שינה", "אמונה", "משא ומתן"],
            "classes": ["physical-needs", "emuna-practice"],
            "context_note": "Sleep in context of business dealings in faith",
            "connected_to": "משא ומתן באמונה",
            "last_modified": "2025-10-21T10:32:00Z"
        }
        // If שנה appears as "year", it would be a separate entry:
        // "שנה:12:1": {
        //     "meaning": "year",
        //     "keywords": ["year", "time", "rosh-hashana"],
        //     ...
        // }
    }
}
```

### Example 2: Simple Node - תורה (No Homonyms)
```json
{
    "edge_metadata": {
        "תורה:1:1": {
            "node_id": "תורה",
            "reference": 1,
            "edge_index": 1,
            "meaning": "Torah",
            "hebrew_form": "תּוֹרָה",
            "english": "Torah",
            "keywords": ["torah", "study", "learning", "wisdom", "intellect"],
            "keywords_he": ["תורה", "לימוד", "חכמה", "שכל"],
            "classes": ["spiritual-practice", "mitzvot", "wisdom"],
            "context_note": "Torah enables seeing intellect in everything",
            "connected_to": "להסתכל בהשכל שיש בכל דבר",
            "proof_excerpt": "אַשְׁרֵי תְמִימֵי דָרֶךְ...זֶה זוֹכִין עַל-יְדֵי הַתּוֹרָה",
            "last_modified": "2025-10-21T10:35:00Z"
        }
    }
}
```

### Example Class Definitions
```json
{
    "class_definitions": {
        "spiritual-practice": {
            "label": "Spiritual Practice",
            "label_he": "עבודה רוחנית",
            "description": "Daily practices for spiritual development",
            "parent": null,
            "color": "#9C27B0"
        },
        "mitzvot": {
            "label": "Mitzvot",
            "label_he": "מצוות",
            "description": "Torah commandments and observances",
            "parent": "spiritual-practice",
            "color": "#2196F3"
        },
        "spiritual-states": {
            "label": "Spiritual States",
            "label_he": "מצבים רוחניים",
            "description": "Internal spiritual conditions and qualities",
            "parent": null,
            "color": "#FF9800"
        },
        "emuna": {
            "label": "Faith & Belief",
            "label_he": "אמונה",
            "description": "Concepts related to faith and trust in Hashem",
            "parent": "spiritual-states",
            "color": "#4CAF50"
        }
    }
}
```

---

**Document Version:** 1.0
**Created:** 2025-10-21
**Author:** Claude (AI Assistant)
**Status:** Draft for Review
