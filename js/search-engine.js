/**
 * Torah Search Engine - Advanced search algorithms for Torah concept connections
 * Pure logic module - no DOM dependencies, fully testable
 */
var TorahSearchEngine = (function() {

    function TorahSearchEngine(data) {
        this.data = data || [];
        this.adjacency = {};
        this.edgeMap = {};
        this.allTopics = [];
        this.allTorahNumbers = [];
        this._buildIndices();
    }

    // Build all lookup indices from raw data
    TorahSearchEngine.prototype._buildIndices = function() {
        var topicSet = new Set();
        var torahSet = new Set();
        var self = this;

        this.data.forEach(function(edge) {
            if (edge.node1_id) topicSet.add(edge.node1_id);
            if (edge.node2_id) topicSet.add(edge.node2_id);
            if (edge.reference) torahSet.add(edge.reference);

            // Build adjacency list
            if (!self.adjacency[edge.node1_id]) {
                self.adjacency[edge.node1_id] = { bechina: [], parent_eitza: [], child_eitza: [] };
            }
            if (!self.adjacency[edge.node2_id]) {
                self.adjacency[edge.node2_id] = { bechina: [], parent_eitza: [], child_eitza: [] };
            }

            if (edge.type === 'bechina') {
                self.adjacency[edge.node1_id].bechina.push(edge.node2_id);
                self.adjacency[edge.node2_id].bechina.push(edge.node1_id);
            } else if (edge.type === 'eitza') {
                self.adjacency[edge.node1_id].child_eitza.push(edge.node2_id);
                self.adjacency[edge.node2_id].parent_eitza.push(edge.node1_id);
            }

            // Edge map for quick lookup
            var key = edge.node1_id + '||' + edge.node2_id + '||' + edge.type;
            self.edgeMap[key] = edge;
            if (edge.type === 'bechina') {
                self.edgeMap[edge.node2_id + '||' + edge.node1_id + '||bechina'] = edge;
            }
        });

        this.allTopics = Array.from(topicSet).sort();
        this.allTorahNumbers = Array.from(torahSet).sort(function(a, b) { return a - b; });
    };

    // Dataset statistics
    TorahSearchEngine.prototype.getStats = function() {
        var bechinaCount = 0;
        var eitzaCount = 0;
        this.data.forEach(function(e) {
            if (e.type === 'bechina') bechinaCount++;
            else if (e.type === 'eitza') eitzaCount++;
        });

        return {
            totalTopics: this.allTopics.length,
            totalConnections: this.data.length,
            bechinaCount: bechinaCount,
            eitzaCount: eitzaCount,
            torahCount: this.allTorahNumbers.length
        };
    };

    // Fuzzy matching for search
    TorahSearchEngine.prototype.fuzzyMatch = function(query, target) {
        if (!query || !target) return { score: 0, match: false };
        var q = query.trim().toLowerCase();
        var t = target.toLowerCase();

        if (t.includes(q)) return { score: 1.0, match: true };

        var words = q.split(/\s+/);
        var matched = words.filter(function(w) { return t.includes(w); });
        if (matched.length === words.length) return { score: 0.9, match: true };
        if (matched.length > 0) return { score: 0.5 * matched.length / words.length, match: true };

        return { score: 0, match: false };
    };

    // Autocomplete suggestions with fuzzy ranking
    TorahSearchEngine.prototype.getSuggestions = function(query, limit) {
        if (!query || query.length < 1) return [];
        limit = limit || 20;
        var self = this;
        var matches = [];

        this.allTopics.forEach(function(topic) {
            var result = self.fuzzyMatch(query, topic);
            if (result.match) {
                matches.push({ topic: topic, score: result.score });
            }
        });

        matches.sort(function(a, b) { return b.score - a.score; });
        return matches.slice(0, limit).map(function(m) { return m.topic; });
    };

    // 1. Explore - Find everything connected to a topic
    TorahSearchEngine.prototype.explore = function(topic, limit) {
        if (!topic) return [];
        limit = limit || 200;
        var results = [];

        this.data.forEach(function(edge) {
            if ((edge.node1_id && edge.node1_id.includes(topic)) ||
                (edge.node2_id && edge.node2_id.includes(topic))) {
                results.push(edge);
            }
        });

        return results.slice(0, limit);
    };

    // 2. Get Advice - What advice relates to this topic?
    TorahSearchEngine.prototype.getAdvice = function(topic, limit) {
        if (!topic) return [];
        limit = limit || 200;
        var results = [];

        this.data.forEach(function(edge) {
            if (edge.type === 'eitza' && edge.node2_id && edge.node2_id.includes(topic)) {
                results.push(edge);
            }
        });

        return results.slice(0, limit);
    };

    // 3. Get Effects - What does this topic lead to?
    TorahSearchEngine.prototype.getEffects = function(topic, limit) {
        if (!topic) return [];
        limit = limit || 200;
        var results = [];

        this.data.forEach(function(edge) {
            if (edge.type === 'eitza' && edge.node1_id && edge.node1_id.includes(topic)) {
                results.push(edge);
            }
        });

        return results.slice(0, limit);
    };

    // 4. Get Aspects (Bechinos) - Deeper aspects of a topic
    TorahSearchEngine.prototype.getAspects = function(topic, limit) {
        if (!topic) return [];
        limit = limit || 200;
        var results = [];

        this.data.forEach(function(edge) {
            if (edge.type === 'bechina' &&
                ((edge.node1_id && edge.node1_id.includes(topic)) ||
                 (edge.node2_id && edge.node2_id.includes(topic)))) {
                results.push(edge);
            }
        });

        return results.slice(0, limit);
    };

    // 5. Search by Torah number
    TorahSearchEngine.prototype.searchByTorah = function(torahNum) {
        if (torahNum === null || torahNum === undefined) return [];
        return this.data.filter(function(edge) {
            return edge.reference === torahNum;
        });
    };

    // 6. Find Path - Trace cause-effect connections between concepts
    TorahSearchEngine.prototype.findPath = function(startSearch, endSearch, maxDepth) {
        if (!startSearch || !endSearch) return { edges: [], paths: [], startNodes: [], endNodes: [] };
        maxDepth = maxDepth || 5;

        var adjList = this.adjacency;
        var edgeMap = this.edgeMap;

        var startNodes = Object.keys(adjList).filter(function(id) {
            return id.includes(startSearch);
        });
        var endNodeSet = new Set(Object.keys(adjList).filter(function(id) {
            return id.includes(endSearch);
        }));

        if (startNodes.length === 0 || endNodeSet.size === 0) {
            return { edges: [], paths: [], startNodes: [], endNodes: [] };
        }

        var allPaths = [];
        var actualStartNodes = new Set();
        var actualEndNodes = new Set();

        // Phase 1: BFS from start nodes through bechina edges to find cause nodes
        var queue = [];
        var globalVisited = new Set();
        var causeNodes = [];

        startNodes.forEach(function(startNode) {
            queue.push({
                node: startNode,
                path: [startNode],
                depth: 0,
                visited: new Set([startNode]),
                startNode: startNode
            });
        });

        while (queue.length > 0) {
            var current = queue.shift();
            var visitKey = current.startNode + '::' + current.node + '::' + current.depth;
            if (globalVisited.has(visitKey)) continue;
            globalVisited.add(visitKey);

            if (adjList[current.node] && adjList[current.node].child_eitza.length > 0) {
                causeNodes.push({
                    node: current.node,
                    pathFromStart: current.path,
                    visitedNodes: current.visited,
                    originalStart: current.startNode
                });
            }

            if (current.depth < maxDepth && adjList[current.node] && adjList[current.node].bechina) {
                adjList[current.node].bechina.forEach(function(neighbor) {
                    if (!current.visited.has(neighbor)) {
                        var newVisited = new Set(current.visited);
                        newVisited.add(neighbor);
                        queue.push({
                            node: neighbor,
                            path: current.path.concat([neighbor]),
                            depth: current.depth + 1,
                            visited: newVisited,
                            startNode: current.startNode
                        });
                    }
                });
            }
        }

        if (causeNodes.length === 0) {
            return { edges: [], paths: [], startNodes: [], endNodes: [] };
        }

        if (causeNodes.length > 100) causeNodes = causeNodes.slice(0, 100);

        // Phase 2: Follow eitza edges, then BFS to end node
        causeNodes.forEach(function(causeInfo) {
            if (allPaths.length >= 20) return;

            adjList[causeInfo.node].child_eitza.forEach(function(effectNode) {
                if (causeInfo.visitedNodes.has(effectNode)) return;
                if (allPaths.length >= 20) return;

                var queue2 = [{
                    node: effectNode,
                    path: [effectNode],
                    depth: 0,
                    visited: new Set([effectNode])
                }];
                var visited2 = new Map();

                while (queue2.length > 0) {
                    var c = queue2.shift();
                    if (visited2.has(c.node) && visited2.get(c.node) < c.depth) continue;
                    visited2.set(c.node, c.depth);

                    if (endNodeSet.has(c.node)) {
                        var fullPath = causeInfo.pathFromStart.concat([effectNode]).concat(c.path.slice(1));
                        allPaths.push({
                            path: fullPath,
                            causeNode: causeInfo.node,
                            effectNode: effectNode,
                            startNode: causeInfo.originalStart,
                            endNode: c.node,
                            length: fullPath.length - 1
                        });
                        actualStartNodes.add(causeInfo.originalStart);
                        actualEndNodes.add(c.node);
                        continue;
                    }

                    if (c.depth < maxDepth && adjList[c.node] && adjList[c.node].bechina) {
                        adjList[c.node].bechina.forEach(function(neighbor) {
                            if (!c.visited.has(neighbor) && !causeInfo.visitedNodes.has(neighbor)) {
                                var nv = new Set(c.visited);
                                nv.add(neighbor);
                                queue2.push({
                                    node: neighbor,
                                    path: c.path.concat([neighbor]),
                                    depth: c.depth + 1,
                                    visited: nv
                                });
                            }
                        });
                    }
                }
            });
        });

        allPaths.sort(function(a, b) { return a.length - b.length; });
        allPaths = allPaths.slice(0, 20);

        // Convert paths to edges
        var resultEdges = [];
        var edgeSet = new Set();

        allPaths.forEach(function(pathInfo) {
            for (var i = 0; i < pathInfo.path.length - 1; i++) {
                var from = pathInfo.path[i];
                var to = pathInfo.path[i + 1];
                var type = (from === pathInfo.causeNode && to === pathInfo.effectNode) ? 'eitza' : 'bechina';

                var edge = edgeMap[from + '||' + to + '||' + type] || edgeMap[to + '||' + from + '||' + type];
                if (edge) {
                    var eid = edge.node1_id + '-' + edge.node2_id + '-' + edge.type;
                    if (!edgeSet.has(eid)) {
                        edgeSet.add(eid);
                        resultEdges.push(edge);
                    }
                }
            }
        });

        return {
            edges: resultEdges,
            paths: allPaths,
            startNodes: Array.from(actualStartNodes),
            endNodes: Array.from(actualEndNodes)
        };
    };

    // 7. Common Ground - Find shared connections between two topics via BFS
    // depth controls how many hops from each topic to explore (default 2)
    TorahSearchEngine.prototype.findCommonGround = function(topic1, topic2, depth) {
        if (!topic1 || !topic2) return { edges: [], commonNodes: [], topic1Connections: 0, topic2Connections: 0, depth: 0 };
        depth = (depth !== undefined && depth !== null) ? depth : 2;

        var self = this;

        // BFS to collect all reachable nodes and their edges up to given depth
        function bfsCollect(searchTerm, maxDepth) {
            // Find seed nodes matching the search term
            var seeds = [];
            self.data.forEach(function(edge) {
                if (edge.node1_id && edge.node1_id.includes(searchTerm) && seeds.indexOf(edge.node1_id) === -1) seeds.push(edge.node1_id);
                if (edge.node2_id && edge.node2_id.includes(searchTerm) && seeds.indexOf(edge.node2_id) === -1) seeds.push(edge.node2_id);
            });

            var visited = new Set(seeds);
            var queue = [];
            var collectedEdges = [];
            var edgeSet = new Set();

            seeds.forEach(function(s) { queue.push({ node: s, d: 0 }); });

            while (queue.length > 0) {
                var current = queue.shift();
                if (current.d >= maxDepth) continue;

                self.data.forEach(function(edge) {
                    var isSource = edge.node1_id === current.node;
                    var isTarget = edge.node2_id === current.node;
                    if (!isSource && !isTarget) return;

                    var key = edge.node1_id + '-' + edge.node2_id + '-' + edge.type;
                    if (!edgeSet.has(key)) {
                        edgeSet.add(key);
                        collectedEdges.push(edge);
                    }

                    var neighbor = isSource ? edge.node2_id : edge.node1_id;
                    if (!visited.has(neighbor)) {
                        visited.add(neighbor);
                        queue.push({ node: neighbor, d: current.d + 1 });
                    }
                });
            }

            return { nodes: visited, edges: collectedEdges };
        }

        var result1 = bfsCollect(topic1, depth);
        var result2 = bfsCollect(topic2, depth);

        // Find common nodes (intersection of reachable sets)
        var commonNodes = [];
        result1.nodes.forEach(function(node) {
            if (result2.nodes.has(node)) commonNodes.push(node);
        });

        // Collect edges that connect through common nodes
        var resultEdges = [];
        var edgeSet = new Set();
        var commonNodeSet = new Set(commonNodes);

        result1.edges.concat(result2.edges).forEach(function(edge) {
            if (commonNodeSet.has(edge.node1_id) || commonNodeSet.has(edge.node2_id)) {
                var key = edge.node1_id + '-' + edge.node2_id + '-' + edge.type;
                if (!edgeSet.has(key)) {
                    edgeSet.add(key);
                    resultEdges.push(edge);
                }
            }
        });

        return {
            edges: resultEdges,
            commonNodes: commonNodes,
            topic1Connections: result1.edges.length,
            topic2Connections: result2.edges.length,
            depth: depth
        };
    };

    // 8. Multi-filter search - Combine keyword, type, and Torah number
    TorahSearchEngine.prototype.multiFilter = function(filters) {
        var keyword = (filters.keyword || '').trim();
        var type = filters.type || 'all';
        var torahNum = filters.torahNum !== undefined && filters.torahNum !== null && filters.torahNum !== '' ? Number(filters.torahNum) : null;
        var limit = filters.limit || 200;

        var results = this.data.filter(function(edge) {
            if (type !== 'all' && edge.type !== type) return false;

            if (torahNum !== null && !isNaN(torahNum) && edge.reference !== torahNum) return false;

            if (keyword) {
                var found = false;
                if (edge.node1_id && edge.node1_id.includes(keyword)) found = true;
                if (!found && edge.node2_id && edge.node2_id.includes(keyword)) found = true;
                if (!found && edge.proof && edge.proof.includes(keyword)) found = true;
                if (!found && edge.node1_text && edge.node1_text.includes(keyword)) found = true;
                if (!found && edge.node2_text && edge.node2_text.includes(keyword)) found = true;
                if (!found && edge.node1_text_en && edge.node1_text_en.includes(keyword)) found = true;
                if (!found && edge.node2_text_en && edge.node2_text_en.includes(keyword)) found = true;
                if (!found) return false;
            }

            return true;
        });

        return results.slice(0, limit);
    };

    // Get neighborhood edges for expanding a node on the graph
    TorahSearchEngine.prototype.getNeighborhood = function(nodeId, depth) {
        if (!nodeId) return [];
        depth = depth || 1;

        var visited = new Set([nodeId]);
        var queue = [{ node: nodeId, d: 0 }];
        var edgesFound = [];
        var edgeSet = new Set();
        var self = this;

        while (queue.length > 0) {
            var current = queue.shift();
            if (current.d >= depth) continue;

            self.data.forEach(function(edge) {
                if (edge.node1_id === current.node || edge.node2_id === current.node) {
                    var key = edge.node1_id + '-' + edge.node2_id + '-' + edge.type;
                    if (!edgeSet.has(key)) {
                        edgeSet.add(key);
                        edgesFound.push(edge);
                    }

                    var neighbor = (edge.node1_id === current.node) ? edge.node2_id : edge.node1_id;
                    if (!visited.has(neighbor)) {
                        visited.add(neighbor);
                        queue.push({ node: neighbor, d: current.d + 1 });
                    }
                }
            });
        }

        return edgesFound;
    };

    // Get detailed info about a node
    TorahSearchEngine.prototype.getNodeDetails = function(nodeId) {
        var adj = this.adjacency[nodeId];
        if (!adj) return null;

        var references = new Set();
        var nodeText = '';
        var nodeTextEn = '';
        var self = this;

        this.data.forEach(function(edge) {
            if (edge.node1_id === nodeId) {
                if (edge.reference) references.add(edge.reference);
                if (!nodeText && edge.node1_text) nodeText = edge.node1_text;
                if (!nodeTextEn && edge.node1_text_en) nodeTextEn = edge.node1_text_en;
            }
            if (edge.node2_id === nodeId) {
                if (edge.reference) references.add(edge.reference);
                if (!nodeText && edge.node2_text) nodeText = edge.node2_text;
                if (!nodeTextEn && edge.node2_text_en) nodeTextEn = edge.node2_text_en;
            }
        });

        return {
            id: nodeId,
            text: nodeText,
            textEn: nodeTextEn,
            totalConnections: adj.bechina.length + adj.parent_eitza.length + adj.child_eitza.length,
            aspects: adj.bechina.length,
            adviceGiven: adj.child_eitza.length,
            adviceReceived: adj.parent_eitza.length,
            bechinaNeighbors: adj.bechina.slice(),
            eitzaChildren: adj.child_eitza.slice(),
            eitzaParents: adj.parent_eitza.slice(),
            torahReferences: Array.from(references).sort(function(a, b) { return a - b; })
        };
    };

    // ===== Package Search Methods =====

    // Initialize package data (called separately after loading packageData.js)
    TorahSearchEngine.prototype.loadPackages = function(packages) {
        this.packages = packages || [];
        // Build index by torah_ref for quick lookup
        this.packagesByTorah = {};
        var self = this;
        this.packages.forEach(function(pkg) {
            var ref = pkg.torah_ref;
            if (!self.packagesByTorah[ref]) self.packagesByTorah[ref] = [];
            self.packagesByTorah[ref].push(pkg);
        });
    };

    // Search packages by keyword (matches label, label_en, nodes, reason)
    TorahSearchEngine.prototype.searchPackages = function(query, limit) {
        if (!query || !this.packages) return [];
        limit = limit || 50;
        var q = query.trim().toLowerCase();
        var results = [];

        this.packages.forEach(function(pkg) {
            var score = 0;

            // Match Hebrew label
            if (pkg.label && pkg.label.toLowerCase().includes(q)) score = 1.0;
            // Match English label
            if (!score && pkg.label_en && pkg.label_en.toLowerCase().includes(q)) score = 1.0;
            // Match dominant node
            if (!score && pkg.dominant_node && pkg.dominant_node.toLowerCase().includes(q)) score = 0.95;
            // Match any node in the package
            if (!score && pkg.nodes) {
                for (var i = 0; i < pkg.nodes.length; i++) {
                    if (pkg.nodes[i].toLowerCase().includes(q)) {
                        score = 0.8;
                        break;
                    }
                }
            }
            // Match reason text
            if (!score && pkg.reason && pkg.reason.toLowerCase().includes(q)) score = 0.5;

            if (score > 0) {
                results.push({ package: pkg, score: score });
            }
        });

        results.sort(function(a, b) { return b.score - a.score; });
        return results.slice(0, limit).map(function(r) { return r.package; });
    };

    // Get packages by Torah number
    TorahSearchEngine.prototype.getPackagesByTorah = function(torahNum) {
        if (!this.packagesByTorah) return [];
        return this.packagesByTorah[torahNum] || [];
    };

    // Get edges for a package's nodes (to visualize the cluster on the graph)
    TorahSearchEngine.prototype.getPackageEdges = function(pkg) {
        if (!pkg || !pkg.nodes || !pkg.torah_ref) return [];
        var nodeSet = new Set(pkg.nodes);
        var torahRef = pkg.torah_ref;

        return this.data.filter(function(edge) {
            return edge.reference === torahRef &&
                   nodeSet.has(edge.node1_id) && nodeSet.has(edge.node2_id);
        });
    };

    // Get package stats
    TorahSearchEngine.prototype.getPackageStats = function() {
        if (!this.packages) return { totalPackages: 0, torahsWithPackages: 0 };
        return {
            totalPackages: this.packages.length,
            torahsWithPackages: Object.keys(this.packagesByTorah || {}).length
        };
    };

    return TorahSearchEngine;
})();

if (typeof module !== 'undefined' && module.exports) {
    module.exports = TorahSearchEngine;
}
