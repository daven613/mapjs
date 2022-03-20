function find_matches(edge_type, edge_property, edge_value, edges_arr) {
    next_arr = [];
    for (edge of edges_arr) {
        if (edge.type == edge_type && edge[edge_property] == edge_value) {
            next_arr.push(edge);
        }
    }
    return next_arr
}


function find_matches_regex(edge_type, edge_property, edge_value, edges_arr) {
    next_arr = [];
    if (edge_value == "") {
        return next_arr;
    }
    var edge_reg = new RegExp(edge_value)
    for (edge of edges_arr) {
        if (edge.type == edge_type && edge_reg.test(edge[edge_property])) {
            //edge[edge_property].includes(edge_value)){ //edge[edge_property] == edge_value){
            next_arr.push(edge);
        }
    }
    return next_arr
}

function remove_array_doubles(array) {
    return [...new Set(array)]
}

function get_autofill_data(full_arr, type_to_search, atrabutes_to_search) {
    var atuofill_data = [];
    for (arr of full_arr) {  //loop through all data
        for (typ of type_to_search) {
            if (arr.type == typ) {
                for (atr of atrabutes_to_search) {
                    atuofill_data.push(arr[atr]);
                }
            }
        }
    }
    atuofill_data = remove_array_doubles(atuofill_data)

    return atuofill_data.slice(0,200);
}
// input torah object and return sigma object
function create_sigma_graph_from_torah_edges(torah_data) {
    var sigma_object = {
        nodes: [],
        edges: []
    };
    sigma_object.edges = parse_edges_from_torah(torah_data);
    sigma_object.nodes = parse_nodes_from_torah(torah_data);
    return sigma_object;
}

//convert torah edge to sigma edge
function parse_edge_from_torah(edge, edge_id) {
    var new_edge = {};
    new_edge["id"] = edge_id;
    new_edge["source"] = edge["node1_id"];
    new_edge["target"] = edge["node2_id"];
    var hebrewTrue = document.getElementById('button_english')
    if (hebrewTrue.style.display == "block") {
        new_edge["node1_text"] = edge["node1_text"];
        new_edge["node2_text"] = edge["node2_text"];
    } else {
        new_edge["node1_text"] = edge["node1_text_en"];
        new_edge["node2_text"] = edge["node2_text_en"];
    }
    new_edge["proof"] = edge["proof"];
    new_edge["reference"] = edge["reference"];
    new_edge["type"] = edge["type"];
    new_edge["is_good"] = edge["is_good"];
    new_edge["is_bad"] = edge["is_bad"];
    return new_edge;
}



function parse_nodes_from_torah(edges) {
    var new_nodes = {};
    var no_doub = new Set(); // set for removing doubles form array
    var new_node_list = [];
    for (edge of edges) {
        var hebrewTrue = document.getElementById('button_english')
        if (hebrewTrue.style.display == "block") {
            new_nodes[edge["node1_id"]] = edge["node1_text"];
            new_nodes[edge["node2_id"]] = edge["node2_text"];
        } else {
            new_nodes[edge["node1_id"]] = edge["node1_text_en"];
            new_nodes[edge["node2_id"]] = edge["node2_text_en"];
        }
    }
    new_node_list = Object.keys(new_nodes)
        .map(key => ({
            id: (key),
            label: new_nodes[key],
            color: "rgb(55,155,51)",
            x: Math.random(),
            y: Math.random(),
            size: 4.39528751373291
        }));

    return new_node_list;
}


//loop through all torah edges and return list of sigma edges
function parse_edges_from_torah(edges) {
    var new_edges = [];
    for ([edge_id, edge] of edges.entries()) {
        new_edges.push(parse_edge_from_torah(edge, edge_id));
    }
    return new_edges;
}
