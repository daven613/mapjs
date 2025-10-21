/**
 * Keywords and Classes Module
 *
 * This module provides functionality for managing keywords and classes metadata
 * for Torah concept nodes. It uses edge-level metadata to handle homonyms
 * (same word, different meanings) by storing metadata per occurrence.
 */

class KeywordsClassesModule {
    constructor(torahData, metadataPath = '../../data/node_metadata.json') {
        this.torahData = torahData;  // Array of edges from torah1.js/torah2.js
        this.metadata = null;
        this.metadataPath = metadataPath;

        // Indices for fast lookups
        this.edgeIndex = new Map(); // "node_id:reference:index" -> metadata
        this.keywordIndex = new Map(); // keyword -> Set(edge_keys)
        this.classIndex = new Map(); // class -> Set(edge_keys)
        this.nodeOccurrences = new Map(); // node_id -> Array of edge objects

        // Track if metadata has been modified
        this.isDirty = false;
    }

    /**
     * Load metadata from JSON file
     */
    async loadMetadata() {
        if (typeof window !== 'undefined') {
            // Browser environment
            const response = await fetch(this.metadataPath);
            this.metadata = await response.json();
        } else {
            // Node.js environment
            const fs = require('fs');
            const path = require('path');
            const fullPath = path.resolve(__dirname, this.metadataPath);
            const content = fs.readFileSync(fullPath, 'utf8');
            this.metadata = JSON.parse(content);
        }

        this.buildIndices();
        this.isDirty = false;
        return this.metadata;
    }

    /**
     * Save metadata to JSON file
     */
    async saveMetadata() {
        if (!this.metadata) {
            throw new Error('No metadata to save. Call loadMetadata() first.');
        }

        // Update statistics
        this.updateStatistics();

        // Update last modified timestamp
        this.metadata._last_updated = new Date().toISOString();

        const jsonContent = JSON.stringify(this.metadata, null, 2);

        if (typeof window !== 'undefined') {
            // Browser - offer download
            const blob = new Blob([jsonContent], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'node_metadata.json';
            a.click();
            URL.revokeObjectURL(url);
        } else {
            // Node.js - write to file
            const fs = require('fs');
            const path = require('path');
            const fullPath = path.resolve(__dirname, this.metadataPath);

            // Create backup before saving
            if (fs.existsSync(fullPath)) {
                const backupPath = fullPath.replace('.json', `.backup.${Date.now()}.json`);
                fs.copyFileSync(fullPath, backupPath);
            }

            fs.writeFileSync(fullPath, jsonContent, 'utf8');
        }

        this.isDirty = false;
        return true;
    }

    /**
     * Get all edges (occurrences) for a node_id
     */
    getNodeOccurrences(nodeId) {
        if (!this.nodeOccurrences.has(nodeId)) {
            // Build occurrences from torah data
            this.extractAllNodes();
        }
        return this.nodeOccurrences.get(nodeId) || [];
    }

    /**
     * Get metadata for specific edge occurrence
     */
    getEdgeMetadata(nodeId, reference, edgeIndex = null) {
        // Try with edge index if provided
        if (edgeIndex !== null) {
            const key = `${nodeId}:${reference}:${edgeIndex}`;
            return this.metadata.edge_metadata[key] || null;
        }

        // Search for any edge with matching node_id and reference
        const keyPrefix = `${nodeId}:${reference}:`;
        for (const key in this.metadata.edge_metadata) {
            if (key.startsWith(keyPrefix)) {
                return this.metadata.edge_metadata[key];
            }
        }

        return null;
    }

    /**
     * Get contextual data for editing (includes proof, connections, etc.)
     */
    getEdgeContext(nodeId, reference, edgeIndex = null) {
        const occurrences = this.getNodeOccurrences(nodeId);

        // Find the specific edge
        let edge = null;
        if (edgeIndex !== null) {
            edge = occurrences.find(occ =>
                occ.reference === reference && occ.edgeIndex === edgeIndex
            );
        } else {
            edge = occurrences.find(occ => occ.reference === reference);
        }

        if (!edge) {
            return null;
        }

        // Get metadata for this edge
        const edgeKey = edge.edgeKey || `${nodeId}:${reference}:${edge.edgeIndex}`;
        const metadata = this.metadata.edge_metadata[edgeKey] || {};

        return {
            ...edge,
            metadata: metadata,
            edgeKey: edgeKey
        };
    }

    /**
     * Update metadata for a specific edge
     */
    updateEdgeMetadata(nodeId, reference, edgeIndex, updates) {
        const edgeKey = `${nodeId}:${reference}:${edgeIndex}`;

        if (!this.metadata.edge_metadata[edgeKey]) {
            this.metadata.edge_metadata[edgeKey] = {
                node_id: nodeId,
                reference: reference,
                edge_index: edgeIndex,
                keywords: [],
                keywords_he: [],
                classes: [],
                last_modified: new Date().toISOString()
            };
        }

        // Apply updates
        Object.assign(this.metadata.edge_metadata[edgeKey], updates);
        this.metadata.edge_metadata[edgeKey].last_modified = new Date().toISOString();

        // Rebuild indices
        this.buildIndices();
        this.isDirty = true;

        return this.metadata.edge_metadata[edgeKey];
    }

    /**
     * Add keyword to a specific edge
     */
    addKeywordToEdge(nodeId, reference, edgeIndex, keyword) {
        const edgeKey = `${nodeId}:${reference}:${edgeIndex}`;
        const metadata = this.metadata.edge_metadata[edgeKey] || {};

        if (!metadata.keywords) {
            metadata.keywords = [];
        }

        keyword = keyword.toLowerCase().trim();

        if (!metadata.keywords.includes(keyword)) {
            metadata.keywords.push(keyword);
            this.updateEdgeMetadata(nodeId, reference, edgeIndex, metadata);
            return true;
        }

        return false;
    }

    /**
     * Remove keyword from a specific edge
     */
    removeKeywordFromEdge(nodeId, reference, edgeIndex, keyword) {
        const edgeKey = `${nodeId}:${reference}:${edgeIndex}`;
        const metadata = this.metadata.edge_metadata[edgeKey];

        if (!metadata || !metadata.keywords) {
            return false;
        }

        keyword = keyword.toLowerCase().trim();
        const index = metadata.keywords.indexOf(keyword);

        if (index !== -1) {
            metadata.keywords.splice(index, 1);
            this.updateEdgeMetadata(nodeId, reference, edgeIndex, metadata);
            return true;
        }

        return false;
    }

    /**
     * Add class to a specific edge
     */
    addClassToEdge(nodeId, reference, edgeIndex, className) {
        const edgeKey = `${nodeId}:${reference}:${edgeIndex}`;
        const metadata = this.metadata.edge_metadata[edgeKey] || {};

        if (!metadata.classes) {
            metadata.classes = [];
        }

        className = className.toLowerCase().trim();

        if (!metadata.classes.includes(className)) {
            metadata.classes.push(className);
            this.updateEdgeMetadata(nodeId, reference, edgeIndex, metadata);
            return true;
        }

        return false;
    }

    /**
     * Remove class from a specific edge
     */
    removeClassFromEdge(nodeId, reference, edgeIndex, className) {
        const edgeKey = `${nodeId}:${reference}:${edgeIndex}`;
        const metadata = this.metadata.edge_metadata[edgeKey];

        if (!metadata || !metadata.classes) {
            return false;
        }

        className = className.toLowerCase().trim();
        const index = metadata.classes.indexOf(className);

        if (index !== -1) {
            metadata.classes.splice(index, 1);
            this.updateEdgeMetadata(nodeId, reference, edgeIndex, metadata);
            return true;
        }

        return false;
    }

    /**
     * Find all edges with a keyword
     */
    findEdgesByKeyword(keyword) {
        keyword = keyword.toLowerCase().trim();
        const edgeKeys = this.keywordIndex.get(keyword) || new Set();

        return Array.from(edgeKeys).map(edgeKey => {
            const metadata = this.metadata.edge_metadata[edgeKey];
            const [nodeId, reference, edgeIndex] = edgeKey.split(':');
            return this.getEdgeContext(nodeId, parseInt(reference), parseInt(edgeIndex));
        }).filter(edge => edge !== null);
    }

    /**
     * Find all edges in a class
     */
    findEdgesByClass(className) {
        className = className.toLowerCase().trim();
        const edgeKeys = this.classIndex.get(className) || new Set();

        return Array.from(edgeKeys).map(edgeKey => {
            const metadata = this.metadata.edge_metadata[edgeKey];
            const [nodeId, reference, edgeIndex] = edgeKey.split(':');
            return this.getEdgeContext(nodeId, parseInt(reference), parseInt(edgeIndex));
        }).filter(edge => edge !== null);
    }

    /**
     * Find related edges (shared keywords/classes)
     */
    findRelatedEdges(nodeId, reference, edgeIndex, options = {}) {
        const edge = this.getEdgeContext(nodeId, reference, edgeIndex);
        if (!edge || !edge.metadata) {
            return [];
        }

        const relatedEdges = new Map(); // edgeKey -> score
        const keywords = edge.metadata.keywords || [];
        const classes = edge.metadata.classes || [];

        // Find edges with shared keywords
        keywords.forEach(keyword => {
            const edges = this.findEdgesByKeyword(keyword);
            edges.forEach(relatedEdge => {
                if (relatedEdge.edgeKey === edge.edgeKey) return; // Skip self

                const score = relatedEdges.get(relatedEdge.edgeKey) || 0;
                relatedEdges.set(relatedEdge.edgeKey, score + 1);
            });
        });

        // Find edges with shared classes
        classes.forEach(className => {
            const edges = this.findEdgesByClass(className);
            edges.forEach(relatedEdge => {
                if (relatedEdge.edgeKey === edge.edgeKey) return; // Skip self

                const score = relatedEdges.get(relatedEdge.edgeKey) || 0;
                relatedEdges.set(relatedEdge.edgeKey, score + 2); // Classes weighted higher
            });
        });

        // Convert to array and sort by score
        return Array.from(relatedEdges.entries())
            .map(([edgeKey, score]) => {
                const [nodeId, reference, edgeIndex] = edgeKey.split(':');
                const context = this.getEdgeContext(nodeId, parseInt(reference), parseInt(edgeIndex));
                return { ...context, relationScore: score };
            })
            .sort((a, b) => b.relationScore - a.relationScore);
    }

    /**
     * Auto-suggest keywords based on proof text and English translation
     */
    suggestKeywords(nodeId, reference, edgeIndex) {
        const edge = this.getEdgeContext(nodeId, reference, edgeIndex);
        if (!edge) {
            return [];
        }

        const suggestions = new Set();

        // Extract from English text
        if (edge.nodeTextEn) {
            const words = edge.nodeTextEn.toLowerCase()
                .split(/[\s,.-]+/)
                .filter(word => word.length > 3);
            words.forEach(word => suggestions.add(word));
        }

        // Extract from connected node English
        if (edge.connectedNodeTextEn) {
            const words = edge.connectedNodeTextEn.toLowerCase()
                .split(/[\s,.-]+/)
                .filter(word => word.length > 3);
            words.slice(0, 3).forEach(word => suggestions.add(word));
        }

        return Array.from(suggestions).slice(0, 10);
    }

    /**
     * Detect homonyms (same node_id, different meanings)
     */
    detectHomonyms() {
        const homonymMap = new Map(); // node_id -> Set of English translations

        this.torahData.forEach(edge => {
            // Check node1
            if (edge.node1_id && edge.node1_text_en) {
                if (!homonymMap.has(edge.node1_id)) {
                    homonymMap.set(edge.node1_id, new Set());
                }
                homonymMap.get(edge.node1_id).add(edge.node1_text_en.toLowerCase().trim());
            }

            // Check node2
            if (edge.node2_id && edge.node2_text_en) {
                if (!homonymMap.has(edge.node2_id)) {
                    homonymMap.set(edge.node2_id, new Set());
                }
                homonymMap.get(edge.node2_id).add(edge.node2_text_en.toLowerCase().trim());
            }
        });

        // Return only nodes with multiple translations
        const homonyms = [];
        homonymMap.forEach((translations, nodeId) => {
            if (translations.size > 1) {
                homonyms.push({
                    nodeId,
                    translations: Array.from(translations),
                    count: translations.size
                });
            }
        });

        return homonyms.sort((a, b) => b.count - a.count);
    }

    /**
     * Build search indices
     */
    buildIndices() {
        if (!this.metadata || !this.metadata.edge_metadata) {
            return;
        }

        this.edgeIndex.clear();
        this.keywordIndex.clear();
        this.classIndex.clear();

        Object.entries(this.metadata.edge_metadata).forEach(([edgeKey, metadata]) => {
            this.edgeIndex.set(edgeKey, metadata);

            // Index keywords
            if (metadata.keywords) {
                metadata.keywords.forEach(keyword => {
                    if (!this.keywordIndex.has(keyword)) {
                        this.keywordIndex.set(keyword, new Set());
                    }
                    this.keywordIndex.get(keyword).add(edgeKey);
                });
            }

            // Index classes
            if (metadata.classes) {
                metadata.classes.forEach(className => {
                    if (!this.classIndex.has(className)) {
                        this.classIndex.set(className, new Set());
                    }
                    this.classIndex.get(className).add(edgeKey);
                });
            }
        });
    }

    /**
     * Extract all unique nodes and their occurrences
     */
    extractAllNodes() {
        this.nodeOccurrences.clear();

        this.torahData.forEach((edge, edgeIndex) => {
            // Process node1
            this.processNode(edge, 'node1', edgeIndex);

            // Process node2
            this.processNode(edge, 'node2', edgeIndex);
        });

        return this.nodeOccurrences;
    }

    /**
     * Helper to process a single node in an edge
     */
    processNode(edge, nodePrefix, edgeIndex) {
        const nodeId = edge[`${nodePrefix}_id`];
        if (!nodeId) return;

        const occurrence = {
            edgeKey: `${nodeId}:${edge.reference}:${edgeIndex}`,
            nodeId,
            nodeText: edge[`${nodePrefix}_text`],
            nodeTextEn: edge[`${nodePrefix}_text_en`],
            reference: edge.reference,
            edgeIndex,
            edgeId: edge.id,
            type: edge.type,
            connectedNodeId: edge[nodePrefix === 'node1' ? 'node2_id' : 'node1_id'],
            connectedNodeText: edge[nodePrefix === 'node1' ? 'node2_text' : 'node1_text'],
            connectedNodeTextEn: edge[nodePrefix === 'node1' ? 'node2_text_en' : 'node1_text_en'],
            proof: edge.proof,
            is_good: edge.is_good,
            is_bad: edge.is_bad,
            position: nodePrefix
        };

        if (!this.nodeOccurrences.has(nodeId)) {
            this.nodeOccurrences.set(nodeId, []);
        }
        this.nodeOccurrences.get(nodeId).push(occurrence);
    }

    /**
     * Apply metadata to all occurrences of a node
     */
    applyToAllOccurrences(nodeId, metadata) {
        const occurrences = this.getNodeOccurrences(nodeId);

        occurrences.forEach(occ => {
            this.updateEdgeMetadata(nodeId, occ.reference, occ.edgeIndex, metadata);
        });

        return occurrences.length;
    }

    /**
     * Update statistics in metadata
     */
    updateStatistics() {
        if (!this.metadata || !this.metadata.statistics) {
            return;
        }

        const taggedEdges = Object.keys(this.metadata.edge_metadata).length;
        const totalEdges = this.torahData.length;

        this.metadata.statistics.tagged_edges = taggedEdges;
        this.metadata.statistics.coverage_percentage =
            totalEdges > 0 ? ((taggedEdges / totalEdges) * 100).toFixed(2) : 0;
    }

    /**
     * Get all class definitions
     */
    getClassDefinitions() {
        return this.metadata ? this.metadata.class_definitions : {};
    }

    /**
     * Get all keyword definitions
     */
    getKeywordDefinitions() {
        return this.metadata ? this.metadata.keyword_definitions : {};
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = KeywordsClassesModule;
}
