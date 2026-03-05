/**
 * Torah Map Explorer - Main Application Logic
 * Manages graph visualization, UI state, and user interactions
 */

// ===== Global State =====
var searchEngine = null;
var sigmaInstance = null;
var currentMode = 'explore';
var currentLanguage = 'hebrew';
var searchHistory = [];
var selectedNodeId = null;

// ===== Mode Descriptions =====
var modeDescriptions = {
    explore:  'Find everything connected to a topic - all aspects and advice links.',
    advice:   'Discover what advice relates to this topic (incoming eitza connections).',
    effects:  'See what this topic leads to or causes (outgoing eitza connections).',
    aspects:  'Explore deeper aspects and meanings of a topic (bechina connections).',
    torah:    'Browse all connections found in a specific Torah from Likutay Halachos.',
    path:     'Trace the chain of connections from one concept to another.',
    common:   'Find what two topics share in common - their overlapping connections.',
    multi:    'Combine keyword, type, and Torah number filters for precise searches.'
};

var modeDescriptionsHeb = {
    explore:  '\u05de\u05e6\u05d0 \u05d0\u05ea \u05db\u05dc \u05de\u05d4 \u05e9\u05e7\u05e9\u05d5\u05e8 \u05dc\u05e0\u05d5\u05e9\u05d0 - \u05db\u05dc \u05d4\u05d1\u05d7\u05d9\u05e0\u05d5\u05ea \u05d5\u05e7\u05e9\u05e8\u05d9 \u05d4\u05e2\u05e6\u05d5\u05ea.',
    advice:   '\u05d2\u05dc\u05d4 \u05d0\u05d9\u05d6\u05d5 \u05e2\u05e6\u05d4 \u05e7\u05e9\u05d5\u05e8\u05d4 \u05dc\u05e0\u05d5\u05e9\u05d0 \u05d4\u05d6\u05d4 (\u05d7\u05d9\u05d1\u05d5\u05e8\u05d9 \u05e2\u05e6\u05d4 \u05e0\u05db\u05e0\u05e1\u05d9\u05dd).',
    effects:  '\u05e8\u05d0\u05d4 \u05dc\u05de\u05d4 \u05d4\u05e0\u05d5\u05e9\u05d0 \u05d4\u05d6\u05d4 \u05de\u05d5\u05d1\u05d9\u05dc \u05d0\u05d5 \u05d2\u05d5\u05e8\u05dd (\u05d7\u05d9\u05d1\u05d5\u05e8\u05d9 \u05e2\u05e6\u05d4 \u05d9\u05d5\u05e6\u05d0\u05d9\u05dd).',
    aspects:  '\u05d7\u05e7\u05d5\u05e8 \u05d1\u05d7\u05d9\u05e0\u05d5\u05ea \u05e2\u05de\u05d5\u05e7\u05d5\u05ea \u05d9\u05d5\u05ea\u05e8 \u05e9\u05dc \u05e0\u05d5\u05e9\u05d0 (\u05d7\u05d9\u05d1\u05d5\u05e8\u05d9 \u05d1\u05d7\u05d9\u05e0\u05d4).',
    torah:    '\u05e2\u05d9\u05d9\u05df \u05d1\u05db\u05dc \u05d4\u05d7\u05d9\u05d1\u05d5\u05e8\u05d9\u05dd \u05d4\u05e0\u05de\u05e6\u05d0\u05d9\u05dd \u05d1\u05ea\u05d5\u05e8\u05d4 \u05de\u05e1\u05d5\u05d9\u05de\u05ea \u05de\u05dc\u05d9\u05e7\u05d5\u05d8\u05d9 \u05d4\u05dc\u05db\u05d5\u05ea.',
    path:     '\u05e2\u05e7\u05d5\u05d1 \u05d0\u05d7\u05e8 \u05e9\u05e8\u05e9\u05e8\u05ea \u05d4\u05d7\u05d9\u05d1\u05d5\u05e8\u05d9\u05dd \u05de\u05de\u05d5\u05e9\u05d2 \u05d0\u05d7\u05d3 \u05dc\u05de\u05e9\u05e0\u05d4\u05d5.',
    common:   '\u05de\u05e6\u05d0 \u05d0\u05ea \u05de\u05d4 \u05e9\u05e9\u05e0\u05d9 \u05e0\u05d5\u05e9\u05d0\u05d9\u05dd \u05d7\u05d5\u05dc\u05e7\u05d9\u05dd - \u05d4\u05d7\u05d9\u05d1\u05d5\u05e8\u05d9\u05dd \u05d4\u05d7\u05d5\u05e4\u05e4\u05d9\u05dd \u05e9\u05dc\u05d4\u05dd.',
    multi:    '\u05e9\u05dc\u05d1 \u05de\u05d9\u05dc\u05ea \u05de\u05e4\u05ea\u05d7, \u05e1\u05d5\u05d2 \u05d5\u05de\u05e1\u05e4\u05e8 \u05ea\u05d5\u05e8\u05d4 \u05dc\u05d7\u05d9\u05e4\u05d5\u05e9 \u05de\u05d3\u05d5\u05d9\u05e7.'
};

// ===== Initialization =====
$(document).ready(function() {
    if (typeof torah1 === 'undefined') {
        showToast('Error: Torah data not loaded');
        return;
    }

    // Initialize search engine
    searchEngine = new TorahSearchEngine(torah1);

    // Display stats
    var stats = searchEngine.getStats();
    $('#statTopics').text(stats.totalTopics);
    $('#statConnections').text(stats.totalConnections);
    $('#statTorahs').text(stats.torahCount);
    $('#wsTopics').text(stats.totalTopics);
    $('#wsConnections').text(stats.totalConnections);
    $('#wsTorahs').text(stats.torahCount);

    // Setup autocomplete on all inputs
    var acOptions = {
        source: function(request, response) {
            var suggestions = searchEngine.getSuggestions(request.term, 20);
            response(suggestions);
        },
        minLength: 2
    };

    $('#inputTopic, #inputTopicA, #inputTopicB, #filterKeyword').autocomplete(acOptions);

    // Populate Torah dropdowns
    searchEngine.allTorahNumbers.forEach(function(num) {
        var opt = '<option value="' + num + '">' + num + '</option>';
        $('#selectTorah').append(opt);
        $('#filterTorah').append(opt);
    });

    // Initialize Sigma
    initSigma();

    // Set initial mode
    selectMode('explore');

    // Keyboard shortcuts
    $(document).on('keydown', function(e) {
        if (e.key === 'Enter' && $(e.target).is('input')) {
            runSearch();
        }
    });
});

// ===== Sigma.js Setup =====
function initSigma() {
    try {
        sigmaInstance = new sigma({
            renderer: {
                container: document.getElementById('graph-container'),
                type: 'canvas'
            }
        });

        sigmaInstance.settings({
            minNodeSize: 2,
            maxNodeSize: 14,
            minEdgeSize: 0.5,
            maxEdgeSize: 2.5,
            enableEdgeHovering: true,
            edgeHoverSizeRatio: 2,
            defaultNodeColor: '#3b82f6',
            defaultEdgeColor: '#94a3b8',
            labelThreshold: 5,
            labelSize: 'fixed',
            defaultLabelSize: 13,
            labelColor: 'node',
            drawEdges: true,
            drawEdgeLabels: false,
            edgesPowRatio: 0.8,
            edgesArrowSize: 8,
            minArrowSize: 5,
            zoomMin: 0.02,
            zoomMax: 10,
            mouseZoomDuration: 300,
            doubleClickZoomDuration: 300
        });

        // Enable drag
        sigma.plugins.dragNodes(sigmaInstance, sigmaInstance.renderers[0]);

        // Edge click -> show details
        sigmaInstance.bind('clickEdge', function(e) {
            var edge = e.data.edge;
            showEdgeDetails(edge);
        });

        // Node click -> show details + highlight
        sigmaInstance.bind('clickNode', function(e) {
            var node = e.data.node;
            selectedNodeId = node.id;
            showNodeDetails(node.id);
        });

        // Stage click -> clear selection
        sigmaInstance.bind('clickStage', function() {
            selectedNodeId = null;
        });

        // Double-click node -> expand neighborhood
        sigmaInstance.bind('doubleClickNode', function(e) {
            var node = e.data.node;
            doExpandNode(node.id);
        });

    } catch(err) {
        console.error('Sigma init error:', err);
    }
}

// ===== Search Mode Selection =====
function selectMode(mode) {
    currentMode = mode;

    // Update mode cards
    $('.mode-card').removeClass('active');
    $('.mode-card[data-mode="' + mode + '"]').addClass('active');

    // Update description
    var desc = currentLanguage === 'hebrew' ? modeDescriptionsHeb[mode] : modeDescriptions[mode];
    $('#modeDescription').text(desc || '');

    // Show correct input group
    $('#inputSingleTopic, #inputTorahGroup, #inputTwoTopics, #inputMultiFilter').addClass('hidden');

    if (mode === 'explore' || mode === 'advice' || mode === 'effects' || mode === 'aspects') {
        $('#inputSingleTopic').removeClass('hidden');
    } else if (mode === 'torah') {
        $('#inputTorahGroup').removeClass('hidden');
    } else if (mode === 'path' || mode === 'common') {
        $('#inputTwoTopics').removeClass('hidden');
        // Show depth selectors per mode
        document.getElementById('pathDepthSpacer').style.display = mode === 'path' ? 'block' : 'none';
        document.getElementById('pathDepthGroup').style.display = mode === 'path' ? 'block' : 'none';
        document.getElementById('commonDepthSpacer').style.display = mode === 'common' ? 'block' : 'none';
        document.getElementById('commonDepthGroup').style.display = mode === 'common' ? 'block' : 'none';
    } else if (mode === 'multi') {
        $('#inputMultiFilter').removeClass('hidden');
    }
}

// ===== Run Search =====
function runSearch() {
    if (!searchEngine || !sigmaInstance) return;

    var btn = $('#runSearchBtn');
    btn.addClass('loading');

    // Short delay so the UI updates before heavy computation
    setTimeout(function() {
        doSearch();
        btn.removeClass('loading');
    }, 50);
}

function doSearch() {
    // Stop and clean up any existing layout
    stopLayout();
    sigmaInstance.graph.clear();
    sigmaInstance.refresh();
    resetCamera();

    var results, highlightNodes = {};
    var searchLabel = '';

    switch (currentMode) {
        case 'explore': {
            var topic = $('#inputTopic').val().trim();
            if (!topic) { showToast('Please enter a topic'); return; }
            results = searchEngine.explore(topic);
            searchLabel = topic;
            break;
        }
        case 'advice': {
            var topic = $('#inputTopic').val().trim();
            if (!topic) { showToast('Please enter a topic'); return; }
            results = searchEngine.getAdvice(topic);
            searchLabel = topic;
            break;
        }
        case 'effects': {
            var topic = $('#inputTopic').val().trim();
            if (!topic) { showToast('Please enter a topic'); return; }
            results = searchEngine.getEffects(topic);
            searchLabel = topic;
            break;
        }
        case 'aspects': {
            var topic = $('#inputTopic').val().trim();
            if (!topic) { showToast('Please enter a topic'); return; }
            results = searchEngine.getAspects(topic);
            searchLabel = topic;
            break;
        }
        case 'torah': {
            var num = parseInt($('#selectTorah').val());
            if (isNaN(num)) { showToast('Please select a Torah number'); return; }
            results = searchEngine.searchByTorah(num);
            searchLabel = 'Torah #' + num;
            break;
        }
        case 'path': {
            var a = $('#inputTopicA').val().trim();
            var b = $('#inputTopicB').val().trim();
            if (!a || !b) { showToast('Please enter both start and end topics'); return; }
            var pathDepth = parseInt($('#pathDepth').val()) || 7;
            var pathResult = searchEngine.findPath(a, b, pathDepth);
            if (!pathResult || pathResult.edges.length === 0) {
                showToast('No path found between these topics');
                return;
            }
            results = pathResult.edges;
            highlightNodes = { startNodes: pathResult.startNodes, endNodes: pathResult.endNodes };
            searchLabel = a + ' \u2192 ' + b;
            break;
        }
        case 'common': {
            var a = $('#inputTopicA').val().trim();
            var b = $('#inputTopicB').val().trim();
            if (!a || !b) { showToast('Please enter both topics'); return; }
            var depth = parseInt($('#commonDepth').val()) || 2;
            var commonResult = searchEngine.findCommonGround(a, b, depth);
            if (!commonResult || commonResult.edges.length === 0) {
                showToast('No common connections found (try increasing depth)');
                return;
            }
            results = commonResult.edges;
            searchLabel = a + ' & ' + b + ' (depth ' + depth + ')';
            break;
        }
        case 'multi': {
            var filters = {
                keyword: $('#filterKeyword').val().trim(),
                type: $('#filterType').val(),
                torahNum: $('#filterTorah').val()
            };
            if (!filters.keyword && filters.type === 'all' && !filters.torahNum) {
                showToast('Please set at least one filter');
                return;
            }
            results = searchEngine.multiFilter(filters);
            var parts = [];
            if (filters.keyword) parts.push(filters.keyword);
            if (filters.type !== 'all') parts.push(filters.type);
            if (filters.torahNum) parts.push('Torah #' + filters.torahNum);
            searchLabel = parts.join(', ');
            break;
        }
    }

    if (!results || results.length === 0) {
        showToast('No results found');
        return;
    }

    // Hide welcome screen
    $('#welcomeScreen').addClass('hidden');

    // Build graph
    buildGraph(results, highlightNodes);

    // Show results summary
    var nodeCount = sigmaInstance.graph.nodes().length;
    var edgeCount = sigmaInstance.graph.edges().length;
    $('#resultsStats').html(
        '<strong>' + nodeCount + '</strong> nodes and <strong>' + edgeCount + '</strong> connections found.'
    );
    $('#resultsSummary').removeClass('hidden');

    showToast(nodeCount + ' nodes, ' + edgeCount + ' connections');

    // Add to history
    addToHistory(currentMode, searchLabel, nodeCount, edgeCount);
}

// ===== Graph Building =====
function buildGraph(edges, highlightNodes) {
    highlightNodes = highlightNodes || {};
    var nodes = {};
    var degrees = {};

    // Create nodes from edges
    edges.forEach(function(edge) {
        if (edge.node1_id && !nodes[edge.node1_id]) {
            nodes[edge.node1_id] = {
                id: edge.node1_id,
                label: currentLanguage === 'hebrew' ? (edge.node1_text || edge.node1_id) : (edge.node1_text_en || edge.node1_id),
                x: 0, y: 0, size: 1,
                color: '#3b82f6'
            };
        }
        if (edge.node2_id && !nodes[edge.node2_id]) {
            nodes[edge.node2_id] = {
                id: edge.node2_id,
                label: currentLanguage === 'hebrew' ? (edge.node2_text || edge.node2_id) : (edge.node2_text_en || edge.node2_id),
                x: 0, y: 0, size: 1,
                color: '#3b82f6'
            };
        }
    });

    // Layout nodes on circle
    var nodeIds = Object.keys(nodes);
    nodeIds.forEach(function(id, i) {
        var angle = (2 * Math.PI * i) / nodeIds.length;
        nodes[id].x = Math.cos(angle) * 10;
        nodes[id].y = Math.sin(angle) * 10;
    });

    // Add nodes
    Object.values(nodes).forEach(function(node) {
        sigmaInstance.graph.addNode(node);
    });

    // Add edges
    edges.forEach(function(edge, idx) {
        if (!edge.node1_id || !edge.node2_id) return;
        try {
            var isEitza = edge.type === 'eitza';
            sigmaInstance.graph.addEdge({
                id: 'e' + idx,
                source: edge.node1_id,
                target: edge.node2_id,
                type: isEitza ? 'arrow' : 'line',
                color: isEitza ? '#a855f7' : '#06b6d4',
                size: isEitza ? 1.5 : 1,
                // Store data for details panel
                node1_text: edge.node1_text,
                node2_text: edge.node2_text,
                node1_text_en: edge.node1_text_en,
                node2_text_en: edge.node2_text_en,
                proof: edge.proof,
                reference: edge.reference,
                edgeType: edge.type
            });
            degrees[edge.node1_id] = (degrees[edge.node1_id] || 0) + 1;
            degrees[edge.node2_id] = (degrees[edge.node2_id] || 0) + 1;
        } catch(e) {
            // duplicate edge
        }
    });

    // Scale node size by degree
    Object.keys(degrees).forEach(function(id) {
        var node = sigmaInstance.graph.nodes(id);
        if (node) {
            node.size = 2 + Math.sqrt(degrees[id]) * 1.5;
        }
    });

    // Highlight start/end nodes for path search
    if (highlightNodes.startNodes) {
        highlightNodes.startNodes.forEach(function(nodeId) {
            var n = sigmaInstance.graph.nodes(nodeId);
            if (n) {
                n.color = '#22c55e';
                n.size = Math.max(n.size, 12);
            }
        });
    }
    if (highlightNodes.endNodes) {
        highlightNodes.endNodes.forEach(function(nodeId) {
            var n = sigmaInstance.graph.nodes(nodeId);
            if (n) {
                n.color = '#ef4444';
                n.size = Math.max(n.size, 12);
            }
        });
    }

    sigmaInstance.refresh();

    // Run force layout
    if (sigmaInstance.startForceAtlas2) {
        var useBarnesHut = sigmaInstance.graph.nodes().length > 50;
        sigmaInstance.startForceAtlas2({
            worker: true,
            barnesHutOptimize: useBarnesHut,
            barnesHutTheta: 0.8,
            gravity: 0.8,
            scalingRatio: 20,
            slowDown: 5,
            strongGravityMode: true
        });

        var duration = Math.min(5000, 1000 + edges.length * 15);
        setTimeout(function() {
            stopLayout();
            fitToScreen();
        }, duration);
    } else {
        fitToScreen();
    }
}

// ===== Expand Node Neighborhood =====
function expandNode() {
    if (!selectedNodeId || !searchEngine) return;
    doExpandNode(selectedNodeId);
}

function doExpandNode(nodeId) {
    var edges = searchEngine.getNeighborhood(nodeId, 1);
    if (edges.length === 0) {
        showToast('No additional connections found');
        return;
    }

    // Hide welcome screen
    $('#welcomeScreen').addClass('hidden');

    var addedNodes = 0;
    var addedEdges = 0;

    edges.forEach(function(edge, idx) {
        // Add nodes if new
        [
            { id: edge.node1_id, text: edge.node1_text, textEn: edge.node1_text_en },
            { id: edge.node2_id, text: edge.node2_text, textEn: edge.node2_text_en }
        ].forEach(function(n) {
            if (!n.id) return;
            try {
                var existing = sigmaInstance.graph.nodes(n.id);
                if (!existing) {
                    // Position near the expanded node
                    var source = sigmaInstance.graph.nodes(nodeId);
                    var sx = source ? source.x : 0;
                    var sy = source ? source.y : 0;
                    sigmaInstance.graph.addNode({
                        id: n.id,
                        label: currentLanguage === 'hebrew' ? (n.text || n.id) : (n.textEn || n.id),
                        x: sx + (Math.random() - 0.5) * 4,
                        y: sy + (Math.random() - 0.5) * 4,
                        size: 3,
                        color: '#3b82f6'
                    });
                    addedNodes++;
                }
            } catch(e) {}
        });

        // Add edge if new
        try {
            var edgeId = 'expand_' + edge.node1_id + '_' + edge.node2_id + '_' + edge.type;
            var isEitza = edge.type === 'eitza';
            sigmaInstance.graph.addEdge({
                id: edgeId,
                source: edge.node1_id,
                target: edge.node2_id,
                type: isEitza ? 'arrow' : 'line',
                color: isEitza ? '#a855f7' : '#06b6d4',
                size: isEitza ? 1.5 : 1,
                node1_text: edge.node1_text,
                node2_text: edge.node2_text,
                node1_text_en: edge.node1_text_en,
                node2_text_en: edge.node2_text_en,
                proof: edge.proof,
                reference: edge.reference,
                edgeType: edge.type
            });
            addedEdges++;
        } catch(e) {
            // duplicate
        }
    });

    // Highlight expanded node
    var expandedNode = sigmaInstance.graph.nodes(nodeId);
    if (expandedNode) {
        expandedNode.color = '#f59e0b';
        expandedNode.size = Math.max(expandedNode.size, 10);
    }

    sigmaInstance.refresh();

    // Brief layout to settle new nodes
    if (sigmaInstance.startForceAtlas2) {
        stopLayout();
        sigmaInstance.startForceAtlas2({
            worker: true,
            barnesHutOptimize: true,
            gravity: 1,
            scalingRatio: 15,
            slowDown: 8,
            strongGravityMode: true
        });
        setTimeout(function() {
            stopLayout();
        }, 2000);
    }

    if (addedNodes > 0 || addedEdges > 0) {
        showToast('Added ' + addedNodes + ' nodes, ' + addedEdges + ' connections');
        // Update summary
        var totalNodes = sigmaInstance.graph.nodes().length;
        var totalEdges = sigmaInstance.graph.edges().length;
        $('#resultsStats').html(
            '<strong>' + totalNodes + '</strong> nodes and <strong>' + totalEdges + '</strong> connections on graph.'
        );
        $('#resultsSummary').removeClass('hidden');
    } else {
        showToast('All connections already shown');
    }
}

function searchFromNode() {
    if (!selectedNodeId) return;
    $('#inputTopic').val(selectedNodeId);
    selectMode('explore');
    switchTab('search');
    runSearch();
}

// ===== Show Details =====
function showNodeDetails(nodeId) {
    var details = searchEngine.getNodeDetails(nodeId);
    if (!details) return;

    // Switch to details tab
    switchTab('details');

    // Hide placeholders, show node panel
    $('#detailsPlaceholder').addClass('hidden');
    $('#edgeDetailsPanel').addClass('hidden');
    $('#nodeDetailsPanel').removeClass('hidden');

    // Populate
    $('#nodeTitle').text(currentLanguage === 'hebrew' ? (details.text || details.id) : (details.textEn || details.id));
    $('#nodeSubtitle').text(details.id);
    $('#nodeConnCount').text(details.totalConnections);
    $('#nodeAspectCount').text(details.aspects);
    $('#nodeAdviceCount').text(details.adviceGiven + details.adviceReceived);

    // Torah references
    var tagHtml = '';
    details.torahReferences.forEach(function(ref) {
        tagHtml += '<span class="tag">' + ref + '</span>';
    });
    $('#nodeTorahList').html(tagHtml || '<span style="color:var(--color-text-muted);font-size:12px;">None</span>');
}

function showEdgeDetails(edge) {
    switchTab('details');

    $('#detailsPlaceholder').addClass('hidden');
    $('#nodeDetailsPanel').addClass('hidden');
    $('#edgeDetailsPanel').removeClass('hidden');

    var isEitza = edge.edgeType === 'eitza';
    var badge = $('#edgeTypeBadge');
    badge.text(isEitza ? 'Advice (Eitza)' : 'Aspect (Bechina)');
    badge.removeClass('bechina eitza').addClass(isEitza ? 'eitza' : 'bechina');

    if (currentLanguage === 'hebrew') {
        $('#edgeFrom').text(edge.node1_text || '');
        $('#edgeTo').text(edge.node2_text || '');
    } else {
        $('#edgeFrom').text(edge.node1_text_en || edge.node1_text || '');
        $('#edgeTo').text(edge.node2_text_en || edge.node2_text || '');
    }
    $('#edgeProof').text(edge.proof || '');
    $('#edgeRef').text(edge.reference || '');
}

// ===== Tab Switching =====
function switchTab(tabName) {
    $('.sidebar-tab').removeClass('active');
    $('.sidebar-tab[data-tab="' + tabName + '"]').addClass('active');
    $('.tab-content').removeClass('active');
    $('#tab-' + tabName).addClass('active');
}

// ===== Search History =====
function addToHistory(mode, label, nodeCount, edgeCount) {
    var entry = {
        mode: mode,
        label: label,
        nodes: nodeCount,
        edges: edgeCount,
        time: new Date()
    };
    searchHistory.unshift(entry);
    if (searchHistory.length > 50) searchHistory.pop();

    renderHistory();
}

function renderHistory() {
    if (searchHistory.length === 0) {
        $('#historyEmpty').show();
        return;
    }
    $('#historyEmpty').hide();

    var html = '';
    searchHistory.forEach(function(entry, idx) {
        html += '<div class="history-item" onclick="replaySearch(' + idx + ')">' +
            '<div class="history-mode">' + escapeHtml(entry.mode) + '</div>' +
            '<div class="history-query">' + escapeHtml(entry.label) + '</div>' +
            '<div class="history-result">' + entry.nodes + ' nodes, ' + entry.edges + ' connections</div>' +
            '</div>';
    });
    $('#historyList').html(html);
}

function replaySearch(idx) {
    var entry = searchHistory[idx];
    if (!entry) return;

    selectMode(entry.mode);
    switchTab('search');

    // Fill in the search fields based on mode
    if (entry.mode === 'explore' || entry.mode === 'advice' || entry.mode === 'effects' || entry.mode === 'aspects') {
        $('#inputTopic').val(entry.label);
    } else if (entry.mode === 'torah') {
        var num = entry.label.replace('Torah #', '');
        $('#selectTorah').val(num);
    } else if (entry.mode === 'path') {
        var parts = entry.label.split(' \u2192 ');
        if (parts.length === 2) {
            $('#inputTopicA').val(parts[0]);
            $('#inputTopicB').val(parts[1]);
        }
    } else if (entry.mode === 'common') {
        var parts = entry.label.split(' & ');
        if (parts.length === 2) {
            $('#inputTopicA').val(parts[0]);
            $('#inputTopicB').val(parts[1]);
        }
    }

    runSearch();
}

// ===== Language Toggle =====
function toggleLanguage() {
    currentLanguage = currentLanguage === 'hebrew' ? 'english' : 'hebrew';
    $('#langLabel').text(currentLanguage === 'hebrew' ? 'EN' : '\u05e2\u05d1');

    // Update mode description
    var desc = currentLanguage === 'hebrew' ? modeDescriptionsHeb[currentMode] : modeDescriptions[currentMode];
    $('#modeDescription').text(desc || '');

    // Re-render node labels if graph has nodes
    if (sigmaInstance && sigmaInstance.graph.nodes().length > 0) {
        showToast('Language switched. Run search again to update labels.');
    }
}

// ===== Sidebar Toggle =====
function toggleSidebar() {
    $('#sidebar').toggleClass('collapsed');

    // Resize sigma after animation
    setTimeout(function() {
        if (sigmaInstance) sigmaInstance.refresh();
    }, 350);
}

// ===== Graph Controls =====
function zoomIn() {
    if (!sigmaInstance) return;
    var camera = sigmaInstance.camera;
    camera.goTo({ ratio: camera.ratio / 1.5 });
}

function zoomOut() {
    if (!sigmaInstance) return;
    var camera = sigmaInstance.camera;
    camera.goTo({ ratio: camera.ratio * 1.5 });
}

function fitToScreen() {
    if (!sigmaInstance) return;
    var nodes = sigmaInstance.graph.nodes();
    if (!nodes.length) return;

    var bounds = nodes.reduce(function(acc, node) {
        acc.minX = Math.min(acc.minX, node.x);
        acc.maxX = Math.max(acc.maxX, node.x);
        acc.minY = Math.min(acc.minY, node.y);
        acc.maxY = Math.max(acc.maxY, node.y);
        return acc;
    }, { minX: Infinity, maxX: -Infinity, minY: Infinity, maxY: -Infinity });

    var renderer = sigmaInstance.renderers[0];
    var width = renderer.width || renderer.container.offsetWidth;
    var height = renderer.height || renderer.container.offsetHeight;
    if (!width || !height) return;

    var sizeX = bounds.maxX - bounds.minX;
    var sizeY = bounds.maxY - bounds.minY;
    var paddingX = width * 0.35;
    var paddingY = height * 0.35;
    var ratioX = sizeX ? (sizeX + paddingX) / width : 1;
    var ratioY = sizeY ? (sizeY + paddingY) / height : 1;
    var ratio = Math.max(ratioX, ratioY);

    var target = {
        x: (bounds.minX + bounds.maxX) / 2,
        y: (bounds.minY + bounds.maxY) / 2,
        ratio: ratio || 1
    };

    if (sigma.misc && sigma.misc.animation && typeof sigma.misc.animation.camera === 'function') {
        sigma.misc.animation.camera(sigmaInstance.camera, target, { duration: 400 });
    } else {
        sigmaInstance.camera.goTo(target);
    }
    sigmaInstance.refresh();
}

function resetCamera() {
    if (!sigmaInstance) return;
    sigmaInstance.camera.goTo({ x: 0, y: 0, angle: 0, ratio: 1 });
}

function clearGraph() {
    if (!sigmaInstance) return;
    stopLayout();
    sigmaInstance.graph.clear();
    sigmaInstance.refresh();
    resetCamera();
    $('#resultsSummary').addClass('hidden');
    $('#welcomeScreen').removeClass('hidden');

    // Reset details
    $('#detailsPlaceholder').removeClass('hidden');
    $('#nodeDetailsPanel').addClass('hidden');
    $('#edgeDetailsPanel').addClass('hidden');
    selectedNodeId = null;
}

// ===== Helpers =====
function stopLayout() {
    if (sigmaInstance && sigmaInstance.isForceAtlas2Running && sigmaInstance.isForceAtlas2Running()) {
        sigmaInstance.stopForceAtlas2();
    }
    if (sigmaInstance && sigmaInstance.killForceAtlas2) {
        sigmaInstance.killForceAtlas2();
    }
}

function showToast(msg) {
    var toast = $('#statusToast');
    toast.text(msg).removeClass('hidden');
    clearTimeout(showToast._timer);
    showToast._timer = setTimeout(function() {
        toast.addClass('hidden');
    }, 3000);
}

function escapeHtml(str) {
    var div = document.createElement('div');
    div.appendChild(document.createTextNode(str));
    return div.innerHTML;
}
