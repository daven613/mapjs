function create_adjacency_object(torah1) {
    var adj_list = init_adjacency_object(torah1);
    for (edge of torah1) {
        if (edge.type == "bechina") {
            adj_list[edge.node1_id][edge.type].push(edge.node2_id);
            adj_list[edge.node2_id][edge.type].push(edge.node1_id);
        }
        if (edge.type == "eitza") {
            adj_list[edge.node1_id]["child_eitza"].push(edge.node2_id);
            adj_list[edge.node2_id]["parent_eitza"].push(edge.node1_id);
        }

    }
    return adj_list;
}
function init_adjacency_object(torah1) {
    var adj_list = {};

    //initialize nodes in adj_list 
    for (edge of torah1) {
        if (!adj_list.hasOwnProperty(edge.node1_id)) {
            adj_list[edge.node1_id] = {
                "bechina": [],
                "parent_eitza": [],
                "child_eitza": []
            };
        }
        if (!adj_list.hasOwnProperty(edge.node2_id)) {
            adj_list[edge.node2_id] = {
                "bechina": [],
                "parent_eitza": [],
                "child_eitza": []
            };

        }
    }
    return adj_list;
}
