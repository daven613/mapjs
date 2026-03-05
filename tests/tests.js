/**
 * Torah Map Explorer - Test Suite
 * Tests the TorahSearchEngine search algorithms
 * Can run in Node.js (node tests/tests.js) or browser (tests/test.html)
 */

// ===== Minimal Test Framework =====
var testResults = { passed: 0, failed: 0, errors: [] };

function assert(condition, message) {
    if (condition) {
        testResults.passed++;
    } else {
        testResults.failed++;
        testResults.errors.push('FAIL: ' + message);
        if (typeof console !== 'undefined') console.error('FAIL: ' + message);
    }
}

function assertEqual(actual, expected, message) {
    if (actual === expected) {
        testResults.passed++;
    } else {
        testResults.failed++;
        var detail = message + ' (expected ' + expected + ', got ' + actual + ')';
        testResults.errors.push('FAIL: ' + detail);
        if (typeof console !== 'undefined') console.error('FAIL: ' + detail);
    }
}

function assertGreater(actual, threshold, message) {
    assert(actual > threshold, message + ' (expected > ' + threshold + ', got ' + actual + ')');
}

function assertArrayIncludes(arr, item, message) {
    assert(arr.indexOf(item) !== -1, message + ' (item "' + item + '" not found in array)');
}

function test(name, fn) {
    try {
        fn();
        if (typeof console !== 'undefined') console.log('  PASS: ' + name);
    } catch(e) {
        testResults.failed++;
        testResults.errors.push('ERROR in "' + name + '": ' + e.message);
        if (typeof console !== 'undefined') console.error('  ERROR: ' + name + ' - ' + e.message);
    }
}

// ===== Test Data =====
var testData = [
    { id: 1, node1_id: 'topic_a', node2_id: 'topic_b', node1_text: 'Topic A', node2_text: 'Topic B', node1_text_en: 'Topic A EN', node2_text_en: 'Topic B EN', proof: 'Proof text 1', reference: 10, type: 'bechina', is_good: null, is_bad: null },
    { id: 2, node1_id: 'topic_a', node2_id: 'topic_c', node1_text: 'Topic A', node2_text: 'Topic C', node1_text_en: 'Topic A EN', node2_text_en: 'Topic C EN', proof: 'Proof text 2', reference: 10, type: 'bechina', is_good: null, is_bad: null },
    { id: 3, node1_id: 'topic_b', node2_id: 'topic_d', node1_text: 'Topic B', node2_text: 'Topic D', node1_text_en: 'Topic B EN', node2_text_en: 'Topic D EN', proof: 'Proof text 3', reference: 20, type: 'eitza', is_good: null, is_bad: null },
    { id: 4, node1_id: 'topic_c', node2_id: 'topic_e', node1_text: 'Topic C', node2_text: 'Topic E', node1_text_en: 'Topic C EN', node2_text_en: 'Topic E EN', proof: 'Proof text 4', reference: 20, type: 'eitza', is_good: null, is_bad: null },
    { id: 5, node1_id: 'topic_d', node2_id: 'topic_e', node1_text: 'Topic D', node2_text: 'Topic E', node1_text_en: 'Topic D EN', node2_text_en: 'Topic E EN', proof: 'Proof text 5', reference: 30, type: 'bechina', is_good: null, is_bad: null },
    { id: 6, node1_id: 'topic_f', node2_id: 'topic_g', node1_text: 'Topic F', node2_text: 'Topic G', node1_text_en: 'Topic F EN', node2_text_en: 'Topic G EN', proof: 'Proof text 6', reference: 30, type: 'eitza', is_good: null, is_bad: null },
    { id: 7, node1_id: 'topic_a', node2_id: 'topic_f', node1_text: 'Topic A', node2_text: 'Topic F', node1_text_en: 'Topic A EN', node2_text_en: 'Topic F EN', proof: 'Proof text 7', reference: 40, type: 'bechina', is_good: null, is_bad: null },
    { id: 8, node1_id: 'special_node', node2_id: 'topic_a', node1_text: 'Special', node2_text: 'Topic A', node1_text_en: 'Special EN', node2_text_en: 'Topic A EN', proof: 'Special proof', reference: 50, type: 'eitza', is_good: null, is_bad: null },
];

// ===== Run Tests =====
function runAllTests() {
    if (typeof console !== 'undefined') console.log('Torah Map Explorer - Test Suite\n');

    // Load the engine
    var TorahSearchEngineCtor;
    if (typeof TorahSearchEngine !== 'undefined') {
        TorahSearchEngineCtor = TorahSearchEngine;
    } else if (typeof require !== 'undefined') {
        TorahSearchEngineCtor = require('../js/search-engine.js');
    } else {
        if (typeof console !== 'undefined') console.error('TorahSearchEngine not found');
        return;
    }

    var engine = new TorahSearchEngineCtor(testData);

    // ===== Initialization Tests =====
    if (typeof console !== 'undefined') console.log('--- Initialization ---');

    test('Engine initializes without errors', function() {
        assert(engine !== null, 'Engine should not be null');
        assert(engine.data.length === 8, 'Engine should have 8 edges');
    });

    test('All topics are extracted', function() {
        assertEqual(engine.allTopics.length, 8, 'Should find 8 unique topics');
        assertArrayIncludes(engine.allTopics, 'topic_a', 'Should include topic_a');
        assertArrayIncludes(engine.allTopics, 'special_node', 'Should include special_node');
    });

    test('Torah numbers are extracted', function() {
        assertEqual(engine.allTorahNumbers.length, 5, 'Should find 5 unique Torah numbers');
        assertArrayIncludes(engine.allTorahNumbers, 10, 'Should include Torah 10');
        assertArrayIncludes(engine.allTorahNumbers, 50, 'Should include Torah 50');
    });

    test('Adjacency list is built correctly', function() {
        assert(engine.adjacency['topic_a'] !== undefined, 'topic_a should be in adjacency list');
        assertGreater(engine.adjacency['topic_a'].bechina.length, 0, 'topic_a should have bechina connections');
    });

    // ===== Stats Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Stats ---');

    test('getStats returns correct counts', function() {
        var stats = engine.getStats();
        assertEqual(stats.totalTopics, 8, 'Total topics should be 8');
        assertEqual(stats.totalConnections, 8, 'Total connections should be 8');
        assertEqual(stats.bechinaCount, 4, 'Bechina count should be 4');
        assertEqual(stats.eitzaCount, 4, 'Eitza count should be 4');
        assertEqual(stats.torahCount, 5, 'Torah count should be 5');
    });

    // ===== Fuzzy Match Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Fuzzy Match ---');

    test('Exact substring match works', function() {
        var result = engine.fuzzyMatch('topic_a', 'topic_a');
        assert(result.match, 'Exact match should return true');
        assertEqual(result.score, 1.0, 'Exact match should have score 1.0');
    });

    test('Partial match works', function() {
        var result = engine.fuzzyMatch('topic', 'topic_a');
        assert(result.match, 'Partial match should return true');
    });

    test('No match returns false', function() {
        var result = engine.fuzzyMatch('xyz', 'topic_a');
        assert(!result.match, 'Non-matching should return false');
    });

    test('Empty query returns false', function() {
        var result = engine.fuzzyMatch('', 'topic_a');
        assert(!result.match, 'Empty query should return false');
    });

    test('Null inputs handled', function() {
        var result = engine.fuzzyMatch(null, 'topic_a');
        assert(!result.match, 'Null query should return false');
        result = engine.fuzzyMatch('topic', null);
        assert(!result.match, 'Null target should return false');
    });

    // ===== Suggestions Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Suggestions ---');

    test('getSuggestions returns matching topics', function() {
        var suggestions = engine.getSuggestions('topic');
        assertGreater(suggestions.length, 0, 'Should find topics matching "topic"');
        assert(suggestions.length <= 20, 'Should be limited to 20');
    });

    test('getSuggestions returns empty for no match', function() {
        var suggestions = engine.getSuggestions('zzzzzzz');
        assertEqual(suggestions.length, 0, 'Should find no topics for nonsense query');
    });

    test('getSuggestions handles empty input', function() {
        var suggestions = engine.getSuggestions('');
        assertEqual(suggestions.length, 0, 'Empty input should return no suggestions');
    });

    // ===== Explore Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Explore ---');

    test('Explore finds all connections to a topic', function() {
        var results = engine.explore('topic_a');
        assertGreater(results.length, 0, 'Should find connections for topic_a');
        // topic_a appears in edges 1, 2, 7, 8
        assertEqual(results.length, 4, 'topic_a has 4 edges');
    });

    test('Explore returns empty for non-existent topic', function() {
        var results = engine.explore('nonexistent');
        assertEqual(results.length, 0, 'Should find no connections for nonexistent topic');
    });

    test('Explore handles empty input', function() {
        var results = engine.explore('');
        assertEqual(results.length, 0, 'Empty topic should return no results');
    });

    test('Explore respects limit', function() {
        var results = engine.explore('topic', 2);
        assert(results.length <= 2, 'Should respect the limit of 2');
    });

    // ===== Get Advice Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Get Advice ---');

    test('getAdvice finds eitza edges targeting a topic', function() {
        var results = engine.getAdvice('topic_a');
        // topic_a is node2_id in edge 8 (special_node -> topic_a, eitza)
        assertEqual(results.length, 1, 'topic_a receives 1 piece of advice');
        assertEqual(results[0].node1_id, 'special_node', 'Advice comes from special_node');
    });

    test('getAdvice returns empty when no advice exists', function() {
        var results = engine.getAdvice('topic_f');
        // topic_f is never node2_id of an eitza edge
        assertEqual(results.length, 0, 'topic_f receives no advice');
    });

    // ===== Get Effects Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Get Effects ---');

    test('getEffects finds eitza edges from a topic', function() {
        var results = engine.getEffects('topic_b');
        // topic_b is node1_id in edge 3 (topic_b -> topic_d, eitza)
        assertEqual(results.length, 1, 'topic_b has 1 effect');
        assertEqual(results[0].node2_id, 'topic_d', 'Effect goes to topic_d');
    });

    test('getEffects returns empty when no effects exist', function() {
        var results = engine.getEffects('topic_e');
        assertEqual(results.length, 0, 'topic_e has no outgoing effects');
    });

    // ===== Get Aspects Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Get Aspects ---');

    test('getAspects finds bechina edges for a topic', function() {
        var results = engine.getAspects('topic_a');
        // topic_a is in bechina edges 1, 2, 7
        assertEqual(results.length, 3, 'topic_a has 3 aspect connections');
    });

    test('getAspects excludes eitza edges', function() {
        var results = engine.getAspects('topic_d');
        // topic_d is in bechina edge 5 only (edge 3 is eitza)
        assertEqual(results.length, 1, 'topic_d has 1 bechina connection');
    });

    // ===== Search By Torah Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Search By Torah ---');

    test('searchByTorah finds edges by reference', function() {
        var results = engine.searchByTorah(10);
        assertEqual(results.length, 2, 'Torah 10 has 2 edges');
    });

    test('searchByTorah returns empty for non-existent Torah', function() {
        var results = engine.searchByTorah(999);
        assertEqual(results.length, 0, 'Torah 999 should have no edges');
    });

    test('searchByTorah handles null', function() {
        var results = engine.searchByTorah(null);
        assertEqual(results.length, 0, 'Null Torah number should return empty');
    });

    // ===== Find Path Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Find Path ---');

    test('findPath finds a path between connected topics', function() {
        // Path: topic_a -> (bechina) -> topic_b -> (eitza) -> topic_d -> (bechina) -> topic_e
        var result = engine.findPath('topic_a', 'topic_e');
        assertGreater(result.edges.length, 0, 'Should find a path from topic_a to topic_e');
        assertGreater(result.startNodes.length, 0, 'Should have start nodes');
        assertGreater(result.endNodes.length, 0, 'Should have end nodes');
    });

    test('findPath returns empty for unconnected topics', function() {
        var result = engine.findPath('topic_g', 'topic_a');
        // topic_g has no outgoing eitza edges, only incoming
        assertEqual(result.edges.length, 0, 'Should find no path from topic_g to topic_a');
    });

    test('findPath handles empty input', function() {
        var result = engine.findPath('', 'topic_a');
        assertEqual(result.edges.length, 0, 'Empty start should return no path');
    });

    test('findPath handles non-existent nodes', function() {
        var result = engine.findPath('nonexistent', 'also_nonexistent');
        assertEqual(result.edges.length, 0, 'Non-existent nodes should return no path');
    });

    // ===== Common Ground Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Common Ground ---');

    test('findCommonGround finds shared connections at depth 1', function() {
        // topic_b and topic_c both connect to topic_a (via bechina) at 1 hop
        var result = engine.findCommonGround('topic_b', 'topic_c', 1);
        assertGreater(result.commonNodes.length, 0, 'topic_b and topic_c should share common nodes at depth 1');
        assertArrayIncludes(result.commonNodes, 'topic_a', 'topic_a should be a common node');
    });

    test('findCommonGround defaults to depth 2', function() {
        var result = engine.findCommonGround('topic_b', 'topic_c');
        assertEqual(result.depth, 2, 'Default depth should be 2');
    });

    test('findCommonGround finds more at deeper depth', function() {
        var result1 = engine.findCommonGround('topic_b', 'topic_c', 1);
        var result3 = engine.findCommonGround('topic_b', 'topic_c', 3);
        assert(result3.commonNodes.length >= result1.commonNodes.length,
            'Depth 3 should find at least as many common nodes as depth 1 (' +
            result3.commonNodes.length + ' >= ' + result1.commonNodes.length + ')');
    });

    test('findCommonGround at depth 2+ finds indirect connections', function() {
        // topic_g and topic_e are unrelated at depth 1
        // but at depth 2+: topic_g -> topic_f -> topic_a -> topic_c -> topic_e
        // topic_g connects to topic_f (edge 6), topic_f connects to topic_a (edge 7)
        // topic_e connects to topic_d (edge 5), topic_e connects to topic_c (edge 4)
        // topic_a connects to topic_c (edge 2) and topic_b (edge 1)
        // At depth 2 from topic_g: topic_g, topic_f, topic_a
        // At depth 2 from topic_e: topic_e, topic_d, topic_c, topic_b
        // Intersection at depth 2: potentially none or some depending on graph
        // At depth 3 they should overlap more
        var resultShallow = engine.findCommonGround('topic_g', 'topic_e', 1);
        var resultDeep = engine.findCommonGround('topic_g', 'topic_e', 3);
        assert(resultDeep.commonNodes.length >= resultShallow.commonNodes.length,
            'Deeper search should find at least as many common nodes');
    });

    test('findCommonGround returns empty for unrelated topics at depth 1', function() {
        var result = engine.findCommonGround('topic_g', 'topic_e', 1);
        assertEqual(result.commonNodes.length, 0, 'Unrelated topics should have no common nodes at depth 1');
    });

    test('findCommonGround handles empty input', function() {
        var result = engine.findCommonGround('', 'topic_a');
        assertEqual(result.edges.length, 0, 'Empty input should return no results');
    });

    // ===== Multi-Filter Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Multi-Filter ---');

    test('multiFilter filters by type', function() {
        var results = engine.multiFilter({ type: 'bechina' });
        assertEqual(results.length, 4, 'Should find 4 bechina edges');
        results.forEach(function(edge) {
            assertEqual(edge.type, 'bechina', 'All results should be bechina type');
        });
    });

    test('multiFilter filters by Torah number', function() {
        var results = engine.multiFilter({ torahNum: 30 });
        assertEqual(results.length, 2, 'Torah 30 should have 2 edges');
    });

    test('multiFilter filters by keyword', function() {
        var results = engine.multiFilter({ keyword: 'special' });
        assertEqual(results.length, 1, 'Should find 1 edge containing "special"');
    });

    test('multiFilter combines filters', function() {
        var results = engine.multiFilter({ type: 'eitza', torahNum: 20 });
        assertEqual(results.length, 2, 'Should find 2 eitza edges in Torah 20');
    });

    test('multiFilter respects limit', function() {
        var results = engine.multiFilter({ type: 'bechina', limit: 2 });
        assert(results.length <= 2, 'Should respect limit of 2');
    });

    // ===== Neighborhood Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Neighborhood ---');

    test('getNeighborhood returns direct connections', function() {
        var results = engine.getNeighborhood('topic_a', 1);
        assertGreater(results.length, 0, 'topic_a should have neighbors');
        // topic_a connects to topic_b, topic_c, topic_f, and special_node
        assertEqual(results.length, 4, 'topic_a has 4 direct edges');
    });

    test('getNeighborhood at depth 2 returns more', function() {
        var results1 = engine.getNeighborhood('topic_a', 1);
        var results2 = engine.getNeighborhood('topic_a', 2);
        assert(results2.length >= results1.length, 'Depth 2 should return at least as many edges as depth 1');
    });

    test('getNeighborhood handles non-existent node', function() {
        var results = engine.getNeighborhood('nonexistent', 1);
        assertEqual(results.length, 0, 'Non-existent node should have no neighbors');
    });

    test('getNeighborhood handles empty input', function() {
        var results = engine.getNeighborhood('', 1);
        assertEqual(results.length, 0, 'Empty input should return no neighbors');
    });

    // ===== Node Details Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Node Details ---');

    test('getNodeDetails returns correct info', function() {
        var details = engine.getNodeDetails('topic_a');
        assert(details !== null, 'Should return details for topic_a');
        assertEqual(details.id, 'topic_a', 'ID should be topic_a');
        assertGreater(details.totalConnections, 0, 'Should have connections');
        assertGreater(details.torahReferences.length, 0, 'Should have Torah references');
    });

    test('getNodeDetails shows correct connection types', function() {
        var details = engine.getNodeDetails('topic_b');
        // topic_b: bechina to topic_a (and reverse), eitza child_eitza to topic_d
        assertGreater(details.aspects, 0, 'topic_b should have bechina connections');
        assertGreater(details.adviceGiven, 0, 'topic_b should have outgoing eitza');
    });

    test('getNodeDetails returns null for non-existent node', function() {
        var details = engine.getNodeDetails('nonexistent');
        assertEqual(details, null, 'Should return null for non-existent node');
    });

    test('getNodeDetails includes text fields', function() {
        var details = engine.getNodeDetails('topic_a');
        assertEqual(details.text, 'Topic A', 'Should have Hebrew text');
        assertEqual(details.textEn, 'Topic A EN', 'Should have English text');
    });

    // ===== Edge Case Tests =====
    if (typeof console !== 'undefined') console.log('\n--- Edge Cases ---');

    test('Engine handles empty dataset', function() {
        var emptyEngine = new TorahSearchEngineCtor([]);
        var stats = emptyEngine.getStats();
        assertEqual(stats.totalTopics, 0, 'Empty engine should have 0 topics');
        assertEqual(stats.totalConnections, 0, 'Empty engine should have 0 connections');
        var results = emptyEngine.explore('anything');
        assertEqual(results.length, 0, 'Explore on empty engine should return empty');
    });

    test('Engine handles single edge dataset', function() {
        var singleEngine = new TorahSearchEngineCtor([testData[0]]);
        var stats = singleEngine.getStats();
        assertEqual(stats.totalTopics, 2, 'Single edge should have 2 topics');
        assertEqual(stats.totalConnections, 1, 'Should have 1 connection');
    });

    // ===== Test with Real Data (if available) =====
    if (typeof torah1 !== 'undefined' && torah1.length > 0) {
        if (typeof console !== 'undefined') console.log('\n--- Real Data Tests ---');

        var realEngine = new TorahSearchEngineCtor(torah1);

        test('Real data loads successfully', function() {
            var stats = realEngine.getStats();
            assertGreater(stats.totalTopics, 0, 'Should have topics');
            assertGreater(stats.totalConnections, 0, 'Should have connections');
            assertGreater(stats.torahCount, 0, 'Should have Torah references');
            if (typeof console !== 'undefined') {
                console.log('    Data: ' + stats.totalTopics + ' topics, ' +
                    stats.totalConnections + ' connections, ' +
                    stats.torahCount + ' Torahs');
            }
        });

        test('Real data suggestions work', function() {
            // Use a common Hebrew letter
            var suggestions = realEngine.getSuggestions('\u05d0', 10);
            assertGreater(suggestions.length, 0, 'Should find suggestions for alef');
        });

        test('Real data searchByTorah works', function() {
            if (realEngine.allTorahNumbers.length > 0) {
                var firstTorah = realEngine.allTorahNumbers[0];
                var results = realEngine.searchByTorah(firstTorah);
                assertGreater(results.length, 0, 'Should find edges for first Torah number');
            }
        });

        test('Real data explore works', function() {
            if (realEngine.allTopics.length > 0) {
                var firstTopic = realEngine.allTopics[0];
                var results = realEngine.explore(firstTopic);
                assertGreater(results.length, 0, 'Should find connections for first topic');
            }
        });

        test('Real data multiFilter works', function() {
            var results = realEngine.multiFilter({ type: 'bechina', limit: 10 });
            assertGreater(results.length, 0, 'Should find bechina edges');
            assert(results.length <= 10, 'Should respect limit');
        });

        test('Real data getNodeDetails works', function() {
            if (realEngine.allTopics.length > 0) {
                var details = realEngine.getNodeDetails(realEngine.allTopics[0]);
                assert(details !== null, 'Should return details for first topic');
                assertGreater(details.totalConnections, 0, 'First topic should have connections');
            }
        });
    }

    // ===== Print Summary =====
    if (typeof console !== 'undefined') {
        console.log('\n============================');
        console.log('Results: ' + testResults.passed + ' passed, ' + testResults.failed + ' failed');
        if (testResults.errors.length > 0) {
            console.log('\nFailures:');
            testResults.errors.forEach(function(err) {
                console.log('  ' + err);
            });
        }
        console.log('============================');
    }

    return testResults;
}

// Auto-run in Node.js
if (typeof module !== 'undefined' && require.main === module) {
    var results = runAllTests();
    process.exit(results.failed > 0 ? 1 : 0);
}

// Auto-run in browser when loaded
if (typeof window !== 'undefined') {
    window.runAllTests = runAllTests;
}
