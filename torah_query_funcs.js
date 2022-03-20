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
    // torah_data = torah_data1.concat(torah_data2)
    return create_sigma_graph_from_torah_edges(torah_data);
}
function query_connected(str_topic, torah_edges) {
    var torah_data = [];
    torah_data1 = find_matches("eitza", "node1_id", str_topic, torah_edges);
    torah_data2 = find_matches("eitza", "node2_id", str_topic, torah_edges);
    torah_data3 = find_matches("bechina", "node1_id", str_topic, torah_edges);
    torah_data4 = find_matches("bechina", "node2_id", str_topic, torah_edges);
    torah_data = [...torah_data1, ...torah_data2, ...torah_data3, ...torah_data4];
    return create_sigma_graph_from_torah_edges(torah_data);
}
function query_connect_two(str_depth, str_topic1, str_topic2, torah1) {
    var found = [];
    for (edge of torah1) {
        if ((edge.node1_id == str_topic1 && edge.type == "bechina") ||
            (edge.node2_id == str_topic1 && edge.type == "bechina")) {
            found.push(edge);
        }
    }
}
