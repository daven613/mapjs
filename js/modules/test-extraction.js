// Test script to extract nodes from torah data and display results
const fs = require('fs');
const path = require('path');

// Load torah data files
const torah1Path = path.join(__dirname, '../../data/torah1.js');
const torah2Path = path.join(__dirname, '../../data/torah2.js');

// Read and parse torah1.js
let torah1Content = fs.readFileSync(torah1Path, 'utf8');
const torah1 = new Function('var torah1; ' + torah1Content + '; return torah1;')();

// Read and parse torah2.js (note: the file also uses torah1 variable name)
let torah2Content = fs.readFileSync(torah2Path, 'utf8');
const torah2 = new Function('var torah1; ' + torah2Content + '; return torah1;')();

console.log('Loaded torah data:');
console.log(`  torah1: ${torah1.length} edges`);
console.log(`  torah2: ${torah2.length} edges`);
console.log(`  Total: ${torah1.length + torah2.length} edges\n`);

// Import extraction functions
const { extractNodeOccurrences, generateStatistics } = require('./extract-nodes.js');

// Extract from both datasets
console.log('Extracting from torah1...');
const result1 = extractNodeOccurrences(torah1);

console.log('Extracting from torah2...');
const result2 = extractNodeOccurrences(torah2);

// Combine results
console.log('\nCombining results...');
const combinedOccurrences = new Map();
const combinedHomonyms = [...result1.homonymCandidates, ...result2.homonymCandidates];

// Merge occurrences
result1.nodeOccurrences.forEach((occurrences, nodeId) => {
    combinedOccurrences.set(nodeId, occurrences);
});

result2.nodeOccurrences.forEach((occurrences, nodeId) => {
    if (combinedOccurrences.has(nodeId)) {
        combinedOccurrences.get(nodeId).push(...occurrences);
    } else {
        combinedOccurrences.set(nodeId, occurrences);
    }
});

const combinedResult = {
    nodeOccurrences: combinedOccurrences,
    totalEdges: torah1.length + torah2.length,
    homonymCandidates: combinedHomonyms
};

// Generate statistics
const stats = generateStatistics(combinedResult);

console.log('\n=== EXTRACTION STATISTICS ===');
console.log(`Total unique nodes: ${stats.totalNodes}`);
console.log(`Total edges: ${stats.totalEdges}`);
console.log(`Total node occurrences: ${stats.totalOccurrences}`);
console.log(`Potential homonyms detected: ${stats.homonymCount}\n`);

console.log('=== OCCURRENCE DISTRIBUTION ===');
console.log('(How many nodes appear X times)');
Object.entries(stats.occurrenceDistribution).slice(0, 10).forEach(([count, nodes]) => {
    console.log(`  ${count} occurrences: ${nodes} nodes`);
});

console.log('\n=== TOP 20 MOST FREQUENT NODES ===');
stats.topNodes.forEach((node, index) => {
    console.log(`${(index + 1).toString().padStart(2)}. ${node.nodeId} (${node.firstOccurrence.nodeTextEn}): ${node.count} occurrences`);
});

console.log('\n=== TOP 20 HOMONYM CANDIDATES ===');
console.log('(Same node_id with different English translations)');
combinedHomonyms.slice(0, 20).forEach((homonym, index) => {
    console.log(`${(index + 1).toString().padStart(2)}. ${homonym.nodeId}`);
    console.log(`    Translations: ${homonym.translations.join(', ')}`);
});

console.log('\n=== SAMPLE NODE OCCURRENCES ===');
// Show detailed info for שנה as an example
const shanaOccurrences = combinedOccurrences.get('שנה');
if (shanaOccurrences) {
    console.log(`\nNode: שנה (${shanaOccurrences.length} occurrences)`);
    shanaOccurrences.slice(0, 3).forEach((occ, index) => {
        console.log(`\n  Occurrence ${index + 1}:`);
        console.log(`    Edge Key: ${occ.edgeKey}`);
        console.log(`    Hebrew: ${occ.nodeText}`);
        console.log(`    English: ${occ.nodeTextEn}`);
        console.log(`    Reference: Torah ${occ.reference}`);
        console.log(`    Type: ${occ.type}`);
        console.log(`    Connected to: ${occ.connectedNodeTextEn}`);
        console.log(`    Proof (excerpt): ${occ.proof ? occ.proof.substring(0, 100) + '...' : 'N/A'}`);
    });
}

// Save results to file for inspection
const outputPath = path.join(__dirname, '../../data/node_extraction_results.json');
const outputData = {
    statistics: stats,
    homonyms: combinedHomonyms.slice(0, 50),
    sampleNodes: {
        'שנה': shanaOccurrences ? shanaOccurrences.slice(0, 5) : null,
        'תורה': combinedOccurrences.get('תורה') ? combinedOccurrences.get('תורה').slice(0, 5) : null,
        'תפילה': combinedOccurrences.get('תפילה') ? combinedOccurrences.get('תפילה').slice(0, 5) : null
    }
};

fs.writeFileSync(outputPath, JSON.stringify(outputData, null, 2));
console.log(`\n\nResults saved to: ${outputPath}`);
