function query_advice(str_topic, torah_edges) {
    torah_data = find_matches_regex("eitza", "node2_id", str_topic, torah_edges);
    return create_sigma_graph_from_torah_edges(torah_data);
}

function query_effects(str_topic, torah_edges) {
    torah_data = find_matches_regex("eitza", "node1_id", str_topic, torah_edges);
    return create_sigma_graph_from_torah_edges(torah_data);
}

function query_by_torah(str_topic, torah_edges) {
    var torah_data1 = [];
    torah_data1 = find_matches("eitza", "reference", str_topic, torah_edges);
    torah_data2 = find_matches("bechina", "reference", str_topic, torah_edges);
    torah_data = [...torah_data1, ...torah_data2];
    return create_sigma_graph_from_torah_edges(torah_data);
}

function query_bechinos(str_topic, torah_edges) {
    torah_data = find_matches_regex("bechina", "node1_id", str_topic, torah_edges);
    torah_data2 = find_matches_regex("bechina", "node2_id", str_topic, torah_edges);
    torah_data = [...torah_data, ...torah_data2];
    return create_sigma_graph_from_torah_edges(torah_data);
}

function query_connected(str_topic, torah_edges) {
    var torah_data = [];
    torah_data1 = find_matches_regex("eitza", "node1_id", str_topic, torah_edges);
    torah_data2 = find_matches_regex("eitza", "node2_id", str_topic, torah_edges);
    torah_data3 = find_matches_regex("bechina", "node1_id", str_topic, torah_edges);
    torah_data4 = find_matches_regex("bechina", "node2_id", str_topic, torah_edges);
    torah_data = [...torah_data1, ...torah_data2, ...torah_data3, ...torah_data4];
    return create_sigma_graph_from_torah_edges(torah_data);
}

function query_connect_two(str_depth, str_topic1, str_topic2, torah_edges) {
    // Simple implementation - find direct connections between two topics
    var found = [];
    for (edge of torah_edges) {
        if ((edge.node1_id == str_topic1 && edge.node2_id == str_topic2) ||
            (edge.node2_id == str_topic1 && edge.node1_id == str_topic2)) {
            found.push(edge);
        }
    }
    return create_sigma_graph_from_torah_edges(found);
}

function query_likutay(str_depth1, str_depth2, str_topic1, str_topic2, torah_edges) {
    // Find connections through advice relationships
    var found = [];
    var topic1_edges = [];
    var topic2_edges = [];

    // Find edges connected to topic1
    for (edge of torah_edges) {
        if (edge.node1_id == str_topic1 || edge.node2_id == str_topic1) {
            topic1_edges.push(edge);
        }
        if (edge.node1_id == str_topic2 || edge.node2_id == str_topic2) {
            topic2_edges.push(edge);
        }
    }

    // Combine relevant edges (simplified version)
    found = [...topic1_edges, ...topic2_edges];

    // Remove duplicates based on edge properties
    var seen = {};
    found = found.filter(function(edge) {
        var key = edge.node1_id + "-" + edge.node2_id + "-" + edge.type;
        return seen.hasOwnProperty(key) ? false : (seen[key] = true);
    });

    return create_sigma_graph_from_torah_edges(found);
}