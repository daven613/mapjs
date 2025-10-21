// Extract all unique node occurrences from torah data
// This script analyzes torah1.js and torah2.js to find all edges and create
// a comprehensive map of node occurrences with full context

function extractNodeOccurrences(torahData) {
    const nodeOccurrences = new Map(); // node_id -> Array of edge occurrences
    const edgeKeys = new Set(); // Track unique edge keys
    const homonymCandidates = new Map(); // node_id -> Set of English translations

    torahData.forEach((edge, edgeIndex) => {
        // Process node1
        processNode(edge, 'node1', edgeIndex, nodeOccurrences, edgeKeys, homonymCandidates);

        // Process node2
        processNode(edge, 'node2', edgeIndex, nodeOccurrences, edgeKeys, homonymCandidates);
    });

    return {
        nodeOccurrences,
        edgeKeys: Array.from(edgeKeys),
        homonymCandidates: detectHomonyms(homonymCandidates),
        totalNodes: nodeOccurrences.size,
        totalEdges: torahData.length
    };
}

function processNode(edge, nodePrefix, edgeIndex, nodeOccurrences, edgeKeys, homonymCandidates) {
    const nodeId = edge[`${nodePrefix}_id`];
    const nodeText = edge[`${nodePrefix}_text`];
    const nodeTextEn = edge[`${nodePrefix}_text_en`];
    const reference = edge.reference;

    if (!nodeId) return; // Skip if no node_id

    // Create edge key: "node_id:reference:index"
    const edgeKey = `${nodeId}:${reference}:${edgeIndex}`;
    edgeKeys.add(edgeKey);

    // Create occurrence object with full context
    const occurrence = {
        edgeKey,
        nodeId,
        nodeText,
        nodeTextEn,
        reference,
        edgeIndex,
        edgeId: edge.id,
        type: edge.type,

        // Connected node info (the other node in this edge)
        connectedNodeId: edge[nodePrefix === 'node1' ? 'node2_id' : 'node1_id'],
        connectedNodeText: edge[nodePrefix === 'node1' ? 'node2_text' : 'node1_text'],
        connectedNodeTextEn: edge[nodePrefix === 'node1' ? 'node2_text_en' : 'node1_text_en'],

        // Context
        proof: edge.proof,
        is_good: edge.is_good,
        is_bad: edge.is_bad,

        // Position in edge
        position: nodePrefix // 'node1' or 'node2'
    };

    // Add to node occurrences map
    if (!nodeOccurrences.has(nodeId)) {
        nodeOccurrences.set(nodeId, []);
    }
    nodeOccurrences.get(nodeId).push(occurrence);

    // Track potential homonyms
    if (nodeTextEn) {
        if (!homonymCandidates.has(nodeId)) {
            homonymCandidates.set(nodeId, new Set());
        }
        homonymCandidates.get(nodeId).add(nodeTextEn.toLowerCase().trim());
    }
}

function detectHomonyms(homonymCandidates) {
    const homonyms = [];

    homonymCandidates.forEach((englishTranslations, nodeId) => {
        // If same node_id has multiple different English translations, it's likely a homonym
        if (englishTranslations.size > 1) {
            homonyms.push({
                nodeId,
                translations: Array.from(englishTranslations),
                count: englishTranslations.size
            });
        }
    });

    // Sort by number of different translations (most ambiguous first)
    return homonyms.sort((a, b) => b.count - a.count);
}

function generateStatistics(extractionResult) {
    const { nodeOccurrences, totalEdges, homonymCandidates } = extractionResult;

    // Calculate occurrence distribution
    const occurrenceCounts = new Map();
    nodeOccurrences.forEach((occurrences, nodeId) => {
        const count = occurrences.length;
        occurrenceCounts.set(count, (occurrenceCounts.get(count) || 0) + 1);
    });

    // Find most frequent nodes
    const nodeFrequency = Array.from(nodeOccurrences.entries())
        .map(([nodeId, occurrences]) => ({
            nodeId,
            count: occurrences.length,
            firstOccurrence: occurrences[0]
        }))
        .sort((a, b) => b.count - a.count);

    return {
        totalNodes: nodeOccurrences.size,
        totalEdges,
        totalOccurrences: nodeFrequency.reduce((sum, item) => sum + item.count, 0),
        homonymCount: homonymCandidates.length,
        topNodes: nodeFrequency.slice(0, 20),
        occurrenceDistribution: Object.fromEntries(
            Array.from(occurrenceCounts.entries()).sort((a, b) => a[0] - b[0])
        )
    };
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        extractNodeOccurrences,
        generateStatistics,
        detectHomonyms
    };
}
