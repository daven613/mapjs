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

## Enhanced Data Structure

### Current Node Structure (Edges)
```javascript
{
    "id": 1.0,
    "node1_id": "תורה",
    "node2_id": "להסתכל בהשכל",
    "node1_text": "תּוֹרָה",
    "node2_text": "לִזְכּוֹת לְהִסְתַּכֵּל",
    "node1_text_en": "Torah",
    "node2_text_en": "To be able to look",
    "proof": "וְזֶהוּ...",
    "reference": 1,
    "type": "eitza"
}
```

### NEW: Node Metadata Structure
We will create a separate `node_metadata.json` file to store keywords and classes:

```javascript
{
    "nodes": {
        "תורה": {
            "keywords": ["torah", "study", "learning"],
            "keywords_he": ["תורה", "לימוד"],
            "classes": ["spiritual-practice", "mitzvot"],
            "aliases": ["התורה", "תורתינו"],
            "color": "#4CAF50",  // Optional: visual theming
            "icon": "📖",         // Optional: emoji icon
            "description": "Torah study and learning",
            "last_modified": "2025-10-21T10:30:00Z"
        },
        "תפילה": {
            "keywords": ["prayer", "tefillah", "davening"],
            "keywords_he": ["תפילה", "תפלה"],
            "classes": ["spiritual-practice", "daily-service"],
            "aliases": ["התפילה"],
            "description": "Prayer and connection to Hashem"
        }
        // ... more nodes
    },
    "class_definitions": {
        "spiritual-practice": {
            "label": "Spiritual Practice",
            "label_he": "עבודה רוחנית",
            "description": "Practices for spiritual growth",
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
        this.torahData = torahData;
        this.metadata = null;
        this.metadataPath = metadataPath;
        this.nodeIndex = new Map(); // node_id -> metadata
        this.keywordIndex = new Map(); // keyword -> Set(node_ids)
        this.classIndex = new Map(); // class -> Set(node_ids)
    }

    // Load metadata from JSON
    async loadMetadata() { }

    // Save metadata to JSON
    async saveMetadata() { }

    // Get metadata for a specific node
    getNodeMetadata(nodeId) { }

    // Update metadata for a node
    updateNodeMetadata(nodeId, updates) { }

    // Add keyword to a node
    addKeyword(nodeId, keyword) { }

    // Remove keyword from a node
    removeKeyword(nodeId, keyword) { }

    // Add class to a node
    addClass(nodeId, className) { }

    // Remove class from a node
    removeClass(nodeId, className) { }

    // Find all nodes with a keyword
    findNodesByKeyword(keyword) { }

    // Find all nodes in a class
    findNodesByClass(className) { }

    // Find related nodes (shared keywords/classes)
    findRelatedNodes(nodeId, options = {}) { }

    // Auto-suggest keywords for a node based on text
    suggestKeywords(nodeId) { }

    // Build search indices
    buildIndices() { }

    // Get all unique nodes from torah data
    extractAllNodes() { }
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

### Metadata Editor Modal

```
┌─────────────────────────────────────────────────────────┐
│  Edit Node: תּוֹרָה (Torah)                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Node ID: תורה                                           │
│  Hebrew: תּוֹרָה                                          │
│  English: Torah                                          │
│                                                          │
│  Keywords (English):                                     │
│  ┌────────────────────────────────────────────────┐     │
│  │ [torah] [study] [learning] [+Add]              │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  Keywords (Hebrew):                                      │
│  ┌────────────────────────────────────────────────┐     │
│  │ [תורה] [לימוד] [+Add]                          │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  Classes:                                                │
│  ┌────────────────────────────────────────────────┐     │
│  │ [spiritual-practice] [mitzvot] [+Add]          │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  Aliases (will map to this node):                       │
│  ┌────────────────────────────────────────────────┐     │
│  │ [התורה] [תורתינו] [+Add]                       │     │
│  └────────────────────────────────────────────────┘     │
│                                                          │
│  Auto-suggest:                                           │
│  [ Generate Keywords ] [ Suggest Classes ]              │
│                                                          │
│  Related Nodes (sharing keywords):                       │
│  • תלמוד (Talmud) - shared: study, learning              │
│  • מצווה (Mitzvah) - shared: mitzvot                     │
│                                                          │
│  [Save] [Cancel] [Save & Next]                          │
└─────────────────────────────────────────────────────────┘
```

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

### Example 1: Torah Node
```json
{
    "nodes": {
        "תורה": {
            "keywords": ["torah", "study", "learning", "wisdom", "teaching"],
            "keywords_he": ["תורה", "לימוד", "חכמה"],
            "classes": ["spiritual-practice", "mitzvot", "wisdom-path"],
            "aliases": ["התורה", "תורתינו", "תורת ה'"],
            "description": "Torah study is the foundation of spiritual growth",
            "last_modified": "2025-10-21T10:30:00Z"
        }
    }
}
```

### Example 2: Prayer Node
```json
{
    "nodes": {
        "תפילה": {
            "keywords": ["prayer", "tefillah", "davening", "connection", "communication"],
            "keywords_he": ["תפילה", "תפלה", "התפללות"],
            "classes": ["spiritual-practice", "daily-service", "connection"],
            "aliases": ["התפילה", "תפלתינו"],
            "description": "Prayer creates a direct connection with Hashem",
            "last_modified": "2025-10-21T10:31:00Z"
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
