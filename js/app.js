// Main application logic
// Data is loaded from torah1.js and torah2.js files

func_hide('button_english');

// Run on load
func_show_status('Loading...');
func_change_query_type(document.getElementById('select_query_type').value);

// Hide keyboard shortcuts
func_toggle_keyboard_shortcuts()

// Neo4j cypher get topics with advice
var arr_topics_advice = [];

//arr_topics_advice = autofill_advice(torah1);
arr_topics_advice = get_autofill_data(torah1, ["eitza"], ["node2_id"])

// Delete duplacates arr_topics_advice
var seen = {};
arr_topics_advice = arr_topics_advice.filter(
    function (item) {
        return seen.hasOwnProperty(item) ? false : (seen[item] = true);
    }
);
// Sort
arr_topics_advice.sort();
// Add to autocomplete
$("#input_topic_advice").autocomplete({
    source: arr_topics_advice,
    minLength: 0,
    // show overlay to prevent sigma from acting on mouse hover and closing the live search dropdown
    open: function (event, ui) { func_show('overlay'); },
    close: function (event, ui) { func_hide('overlay'); },
});
//.bind('focus', function(){ $(this).autocomplete("search"); } );

// Neo4j cypher get topics with effects
var arr_topics_effects = [];

arr_topics_effects = get_autofill_data(torah1, ["eitza"], ["node1_id"])

// Dedup arr_topics_effects
var seen = {};
arr_topics_effects = arr_topics_effects.filter(
    function (item) {
        return seen.hasOwnProperty(item) ? false : (seen[item] = true);
    }
);
// Sort
arr_topics_effects.sort();
// Add to autocomplete
$("#input_topic_effects").autocomplete({
    source: arr_topics_effects,
    minLength: 0,
    // show overlay to prevent sigma from acting on mouse hover and closing the live search dropdown
    open: function (event, ui) { func_show('overlay'); },
    close: function (event, ui) { func_hide('overlay'); },
});


// Neo4j cypher get topics with bechinos
var arr_topics_bechinos = [];
arr_topics_bechinos = get_autofill_data(torah1, ["bechina"], ["node1_id", "node2_id"])
// Dedup arr_topics_bechinos
var seen = {};

// Sort
arr_topics_bechinos.sort();
// Add to autocomplete
$("#input_topic_bechinos").autocomplete({
    source: arr_topics_bechinos,
    minLength: 0,
    // show overlay to prevent sigma from acting on mouse hover and closing the live search dropdown
    open: function (event, ui) { func_show('overlay'); },
    close: function (event, ui) { func_hide('overlay'); },
});

// Neo4j cypher get topics
var arr_topics = [];
arr_topics = get_autofill_data(torah1, ["bechina", "eitza"], ["node1_id", "node2_id"])
// Sort
arr_topics.sort();
// Add to autocompletes
$("#input_topic_1").autocomplete({
    source: arr_topics,
    minLength: 0,
    // show overlay to prevent sigma from acting on mouse hover and closing the live search dropdown
    open: function (event, ui) { func_show('overlay'); },
    close: function (event, ui) { func_hide('overlay'); },
});
$("#input_topic_2").autocomplete({
    source: arr_topics,
    minLength: 0,
    // show overlay to prevent sigma from acting on mouse hover and closing the live search dropdown
    open: function (event, ui) { func_show('overlay'); },
    close: function (event, ui) { func_hide('overlay'); },
});

// Neo4j cypher get torahs
var arr_torahs = [];
arr_torahs = get_autofill_data(torah1, ["bechina", "eitza"], ['reference'])
// Sort
arr_torahs.sort(function (a, b) { return a - b });
// Add to select
arr_torahs.forEach(
    function (torah) {
        var z = document.createElement("option");
        z.setAttribute("value", torah);
        var t = document.createTextNode(torah);
        z.appendChild(t);
        document.getElementById("select_torah").appendChild(z);
    }
);
//Instantiate sigma
var init_sigma = new sigma({
    renderer: {
        container: document.getElementById('graph-container'),
        type: 'canvas'
    },
    settings: {
        doubleClickEnabled: false,
        //			autoCurveSortByDirection: true,
        //			mouseEnabled: false,
        enableHovering: true,
        minNodeSize: 1.0,
        maxNodeSize: 15.0,
        labelAlignment: 'center',
        labelThreshold: 2,
        labelSize: 'fixed',
        defaultLabelSize: 13,
        defaultLabelColor: '#000000',
        minEdgeSize: 0.5,
        maxEdgeSize: 1.8,
        enableEdgeHovering: true,
        //			defaultEdgeHoverColor: '#000',
        //			edgeHoverColor: 'edge',
        edgeHoverSizeRatio: 1,
        edgeHoverExtremities: true,
        animationsTime: 1500,
        drawEdgeLabels: true,
        autoCurveRatio: 2,
        // 			dragNodeStickiness: 0.01,
        // 			minArrowSize: 15,
        // 			drawEdges: true,
        // 			sideMargin: 2,
        // 			scalingMode: 'outside',
        // 			animationsTime: 1000,
        // 			defaultEdgeLabelSize: 12,
        // 			edgeLabelSize: 'fixed',
        // 			edgeLabelThreshold: 2.0,
    }
});
var activeState = sigma.plugins.activeState(init_sigma);
var dragListener = sigma.plugins.dragNodes(init_sigma, init_sigma.renderers[0], activeState);
//var select = sigma.plugins.select(init_sigma, activeState);
//var keyboard = sigma.plugins.keyboard(init_sigma, init_sigma.renderers[0]);
//select.bindKeyboard(keyboard);
// Bind the events
init_sigma.bind('clickNode doubleClickNode rightClickNode', function (e) {
    //console.log(e.type, e.data.node.label, e.data.captor);
    if (e.type == "clickNode") {
        func_hide("div_connection_info")
    }
});

init_sigma.bind('clickEdge doubleClickEdge rightClickEdge', function (e) {
    //console.log(e.type, e.data.edge, e.data.captor);
    if (e.type == "clickEdge") {
        document.getElementById("txt_from_node").innerHTML = e.data.edge.node1_text;
        document.getElementById("txt_to_node").innerHTML = e.data.edge.node2_text;
        document.getElementById("txt_proof").innerHTML = e.data.edge.proof;
        document.getElementById("txt_reference").innerHTML = e.data.edge.reference;
        func_show("div_connection_info")
    }
});

init_sigma.bind('clickStage doubleClickStage rightClickStage', function (e) {
    //console.log(e.type, e.data.captor);
    if (e.type == "clickStage") {
        func_hide("div_connection_info");
    }
});

// 	init_sigma.bind('hovers', function(e) {
// 		console.log(e.type, e.data.captor, e.data);
// 	});

var kbd = sigma.plugins.keyboard(init_sigma, init_sigma.renderers[0], {
    zoomingRatio: 1.3
});

func_hide('div_status');

// ------- Functions --------
function func_center(id) {
    var e = document.getElementById(id);
    half_height = document.getElementById(id).offsetHeight / 2;
    e.style.top = '-moz-calc(50% - ' + half_height + 'px)';
    e.style.top = '-webkit-calc(50% - ' + half_height + 'px)';
    e.style.top = 'calc(50% - ' + half_height + 'px)';
    half_width = document.getElementById(id).offsetWidth / 2;
    e.style.left = '-moz-calc(50% - ' + half_width + 'px)';
    e.style.left = '-webkit-calc(50% - ' + half_width + 'px)';
    e.style.left = 'calc(50% - ' + half_width + 'px)';
}

function func_show(id) {
    var e = document.getElementById(id);
    e.style.display = 'block';
}

function func_hide(id) {
    var e = document.getElementById(id);
    e.style.display = 'none';
}

function func_show_hide(id) {
    var e = document.getElementById(id);
    e.style.display = (e.style.display == 'block') ? 'none' : 'block';
}

function func_escape_chars(string) {
    return string.toString().replace(/"/g, '\\"').replace(/'/g, "\\'");
}

function func_show_status(text) {
    document.getElementById('div_status').innerHTML = text;
    func_show('div_status');
    func_center('div_status');
}

function func_toggle_cypher_query() {
    var e = document.getElementById('div_cypher_query');
    if (e.style.display != 'none') {
        e.style.display = 'none';
        document.getElementById('button_toggle_cypher_query').innerHTML = lang_show_cypher_box;
    } else {
        e.style.display = '';
        document.getElementById('button_toggle_cypher_query').innerHTML = 'X';
    }
}

function func_toggle_keyboard_shortcuts() {
    var e = document.getElementById('div_keyboard_shortcuts');
    if (e.style.display != 'none') {
        e.style.display = 'none';
        document.getElementById('button_toggle_keyboard_shortcuts').innerHTML = '&#708;';
    } else {
        e.style.display = '';
        document.getElementById('button_toggle_keyboard_shortcuts').innerHTML = 'X';
    }
}

function func_change_query_type(value) {
    switch (value) {
        case "advice":
            func_show('div_select_topic_advice');
            func_hide('div_select_topic_effects');
            func_hide('div_select_topic_bechinos');
            //func_hide('div_select_topic');
            func_hide('div_select_topic_1');
            func_hide('div_select_topic_2');
            func_hide('div_select_torah');
            func_hide('div_select_depth_1');
            func_hide('div_select_depth_2');
            func_hide('div_raw_query');
            break;
        case "effects":
            func_hide('div_select_topic_advice');
            func_show('div_select_topic_effects');
            func_hide('div_select_topic_bechinos');
            //func_hide('div_select_topic');
            func_hide('div_select_topic_1');
            func_hide('div_select_topic_2');
            func_hide('div_select_torah');
            func_hide('div_select_depth_1');
            func_hide('div_select_depth_2');
            func_hide('div_raw_query');
            break;
        case "by_torah":
            func_hide('div_select_topic_advice');
            func_hide('div_select_topic_effects');
            func_hide('div_select_topic_bechinos');
            //func_hide('div_select_topic');
            func_hide('div_select_topic_1');
            func_hide('div_select_topic_2');
            func_show('div_select_torah');
            func_hide('div_select_depth_1');
            func_hide('div_select_depth_2');
            func_hide('div_raw_query');
            break;
        case "bechinos":
            func_hide('div_select_topic_advice');
            func_hide('div_select_topic_effects');
            func_show('div_select_topic_bechinos');
            //func_hide('div_select_topic');
            func_hide('div_select_topic_1');
            func_hide('div_select_topic_2');
            func_hide('div_select_torah');
            func_hide('div_select_depth_1');
            func_hide('div_select_depth_2');
            func_hide('div_raw_query');
            break;
        case "connected":
            func_hide('div_select_topic_advice');
            func_hide('div_select_topic_effects');
            func_hide('div_select_topic_bechinos');
            //func_show('div_select_topic');
            func_show('div_select_topic_1');
            document.getElementById("label_select_topic_1").innerHTML = lang_select_topic;
            func_hide('div_select_topic_2');
            func_hide('div_select_torah');
            func_hide('div_select_depth_1');
            func_hide('div_select_depth_2');
            func_hide('div_raw_query');
            break;
        case "connect_two":
            func_hide('div_select_topic_advice');
            func_hide('div_select_topic_effects');
            func_hide('div_select_topic_bechinos');
            func_show('div_select_topic_1');
            document.getElementById("label_select_topic_1").innerHTML = lang_select_topic_1;
            func_show('div_select_topic_2');
            func_hide('div_select_torah');
            func_show('div_select_depth_1');
            document.getElementById("label_select_depth_1").innerHTML = lang_select_depth;
            func_hide('div_select_depth_2');
            func_hide('div_raw_query');
            break;
        case "likutay":
            func_hide('div_select_topic_advice');
            func_hide('div_select_topic_effects');
            func_hide('div_select_topic_bechinos');
            func_show('div_select_topic_1');
            document.getElementById("label_select_topic_1").innerHTML = lang_select_topic_1;
            func_show('div_select_topic_2');
            func_hide('div_select_torah');
            func_show('div_select_depth_1');
            document.getElementById("label_select_depth_1").innerHTML = lang_select_depth_1;
            func_show('div_select_depth_2');
            func_hide('div_raw_query');
            break;
        case "query":
            func_hide('div_select_topic_advice');
            func_hide('div_select_topic_effects');
            func_hide('div_select_topic_bechinos');
            func_hide('div_select_topic_1');
            func_hide('div_select_topic_2');
            func_hide('div_select_torah');
            func_hide('div_select_depth_1');
            func_hide('div_select_depth_2');
            func_show('div_raw_query');
            break;
    }
}

function func_run_query() {
    init_sigma.graph.clear();
    init_sigma.refresh();
    func_show_status('Running Query...'); //מחפש
    switch (document.getElementById("select_query_type").value) {
        case "advice":
            var str_topic = func_escape_chars(document.getElementById("input_topic_advice").value);
            var gr = query_advice(str_topic, torah1);
            break;
        case "effects":
            var str_topic = func_escape_chars(document.getElementById("input_topic_effects").value);
            var gr = query_effects(str_topic, torah1);
            break;
        case "by_torah":
            var str_torah = func_escape_chars(document.getElementById("select_torah").value);
            var gr = query_by_torah(str_torah, torah1);
            break;
        case "bechinos":
            var str_topic = func_escape_chars(document.getElementById("input_topic_bechinos").value);
            var gr = query_bechinos(str_topic, torah1);
            break;
        case "connected":
            var str_topic = func_escape_chars(document.getElementById("input_topic_1").value);
            var gr = query_connected(str_topic, torah1);
            break;
        case "connect_two":
            var str_topic1 = func_escape_chars(document.getElementById("input_topic_1").value);
            var str_topic2 = func_escape_chars(document.getElementById("input_topic_2").value);
            var str_depth = func_escape_chars(document.getElementById("select_depth_1").value);
            var gr = query_connect_two(str_depth,str_topic1,str_topic2, torah1);
            break;
        case "likutay":
            var str_topic1 = func_escape_chars(document.getElementById("input_topic_1").value);
            var str_topic2 = func_escape_chars(document.getElementById("input_topic_2").value);
            var str_depth1 = func_escape_chars(document.getElementById("select_depth_1").value);
            var str_depth2 = func_escape_chars(document.getElementById("select_depth_2").value);
            var gr = query_likutay(str_depth1,str_depth1,str_topic1,str_topic2, torah1);
            break;
        case "query":
            // Raw query mode - no longer uses Neo4j
            break;
    }

    document.getElementById("txt_raw_query").value = "Query mode (Neo4j no longer used)"

    //gr = create_sigma_graph_from_torah_edges(torah1);
    adj_list = create_adjacency_object(torah1)
    init_sigma.graph.read(gr)
    func_customize_graph(init_sigma);
}

function func_customize_graph(s, e) {

    if (e) {
        func_show_status(e[0]['message']);
    } else if (s) {
        // Auto-curve parallel edges:
        sigma.canvas.edges.autoCurve(s);

        s.graph.nodes().forEach(function (node) {
            //node.label = node.neo4j_data['name'];
            node.color = '#6cbef4';
            //node.border_color = '#000';
            //node.border_size = 1.0;
            //node.size = 25.0;
            //node.fixed = false;
            switch (document.getElementById("select_query_type").value) {
                case "advice":
                    var str_topic = func_escape_chars(document.getElementById("input_topic_advice").value);
                    if (node.label == str_topic) {
                        node.color = '#f5963e';
                    }
                    break;
                case "effects":
                    var str_topic = func_escape_chars(document.getElementById("input_topic_effects").value);
                    if (node.label == str_topic) {
                        node.color = '#f5963e';
                    }
                    break;
                case "by_torah":
                    var str_torah = func_escape_chars(document.getElementById("select_torah").value);
                    if (node.label == str_torah) {
                        node.color = '#f5963e';
                    }
                    break;
                case "bechinos":
                    var str_topic = func_escape_chars(document.getElementById("input_topic_bechinos").value);
                    if (node.label == str_topic) {
                        node.color = '#f5963e';
                    }
                    break;
                case "connected":
                    var str_topic = func_escape_chars(document.getElementById("input_topic_1").value);
                    if (node.label == str_topic) {
                        node.color = '#f5963e';
                    }
                    break;
                case "connect_two":
                    var str_topic1 = func_escape_chars(document.getElementById("input_topic_1").value);
                    var str_topic2 = func_escape_chars(document.getElementById("input_topic_2").value);
                    if (node.label == str_topic1) {
                        node.color = '#f5963e';
                    }
                    if (node.label == str_topic2) {
                        node.color = '#f5963e';
                    }
                    break;
                case "likutay":
                    var str_topic1 = func_escape_chars(document.getElementById("input_topic_1").value);
                    var str_topic2 = func_escape_chars(document.getElementById("input_topic_2").value);
                    if (node.label == str_topic1) {
                        node.color = '#f5963e';
                    }
                    if (node.label == str_topic2) {
                        node.color = '#f5963e';
                    }
                    break;
                case "query":
                    break;
            }
        });

        s.graph.edges().forEach(function (edge) {
            var hebrewTrue = document.getElementById('button_english')
            if (edge.type == 'bechina' || edge.cc_prev_type == 'bechina') {
                edge.color = '#4acfc8';
                edge.size = 2.1;
                edge.type = 'curve';
                if (hebrewTrue.style.display == "block") {
                    edge.label = 'בחינה';
                } else {
                    edge.label = 'Aspect';
                }
            }
            if (edge.type == 'eitza' || edge.cc_prev_type == 'eitza') {
                //edge.color = '#FF6C7C';
                edge.color = '#cf4ac8';
                edge.size = 6.1;
                edge.type = 'curvedArrow';
                if (hebrewTrue.style.display == "block") {
                    edge.label = 'עצה';
                } else {
                    edge.label = 'Advice';
                }
            }
            edge.hover_color = '#000000';
            //edge.label = edge.neo4j_type;
        });

        var cam = s.camera;
        sigma.misc.animation.camera(cam, {
            ratio: 1.3
        });

        s.refresh();
        console.log('Number of nodes :' + s.graph.nodes().length);
        console.log('Number of edges :' + s.graph.edges().length);

        // Configure the Fruchterman-Reingold algorithm:
        var frListener = sigma.layouts.fruchtermanReingold.configure(s, {
            iterations: 500,
            easing: 'quadraticInOut',
            duration: 800
        });

        // Bind the events:
        frListener.bind('start stop interpolate', function (e) {
            console.log(e.type);
            if (e.type == 'stop') {
                func_hide('div_status');
            }
        });

        // Start the Fruchterman-Reingold algorithm:
        sigma.layouts.fruchtermanReingold.start(s);

    } else {
        func_show_status('Unspecified Error');
    }
}
function funk_turn_hebrew() {
    lang_select_topic = "בחר נושא"//"Select Topic: "
    lang_select_topic_1 = "בחר נושא 1"//"Select Topic 1: "
    lang_select_depth = "בחר עומק"//"Select Depth: "
    lang_select_depth_1 = "בחר עומק 1"//"Select Depth 1: "
    lang_show_cypher_box = "גלה חלון חיפוש"//'Show Cypher Query Box &#709;'
    $(div_cypher_query).css("direction", "rtl");//direction: rtl;
    $(select_query_type).css("margin-right", "10px");//direction: rtl;

    //set all text to hebrew
    $(button_search).html("חפש")
    $(option_advice).html("קבל עצה")
    $(option_effects).html("קבל נמשך (מסובב)")
    $(option_by_torah).html("חפש לפי תורה")
    $(option_bechinos).html("בחינות")
    $(option_connected).html("קבל כל הנושאים הקשורים")
    $(option_connect_two).html("קשר ב' בחינות")
    $(option_likutay).html("חידושים בסיגנון לקוטי הלכות")
    $(option_query).html("חפש עם קוד")

    //$(label_select_topic).html("בחר נושא")
    $(label_select_topic_advice).html("בחר נושא")
    $(label_select_topic_bechinos).html("בחר נושא")
    $(label_select_topic_effects).html("בחר נושא")
    $(label_select_topic_2).html("בחר נושא 2")
    $(label_select_topic_1).html("בחר נושא 1")
    $(label_select_torah_num).html("מספר תורה")
    $(label_select_depth_2).html("בחר עומק 2")
    func_show('button_english');
    func_hide('button_hebrew');
    if (init_sigma.graph.nodes().length > 0) {
        func_run_query()
    }
}

function funk_turn_english() {
    lang_select_topic = "Select Topic:"//"Select Topic: "
    lang_select_topic_1 = "Select Topic 1:"//"Select Topic 1: "
    lang_select_depth = "Select Depth:"//"Select Depth: "
    lang_select_depth_1 = "Select Depth 1:"//"Select Depth 1: "
    lang_show_cypher_box = "Show Cypher Query Box &#709;"//'Show Cypher Query Box &#709;'
    $(div_cypher_query).css("direction", "ltr");//direction: rtl;
    $(select_query_type).css("margin-left", "10px");//direction: rtl;

    //set all text to hebrew
    $(button_search).html("Run Search")
    $(option_advice).html("Get Advice")
    $(option_effects).html("Get Effects")
    $(option_by_torah).html("Search By Torah")
    $(option_bechinos).html("Get Bechinos")
    $(option_connected).html("Get All Connected Topics")
    $(option_connect_two).html("Connect Two Bechinos")
    $(option_likutay).html("Likutay Halachos Style")
    $(option_query).html("Raw Query")

    //$(label_select_topic).html("בחר נושא")
    $(label_select_topic_advice).html("Select Topic:")
    $(label_select_topic_bechinos).html("Select Topic:")
    $(label_select_topic_effects).html("Select Topic:")
    $(label_select_topic_2).html("Select Topic 2:")
    $(label_select_topic_1).html("Select Topic 1:")
    $(label_select_torah_num).html("Select Torah #:")
    $(label_select_depth_2).html("Select Depth 2:")
    func_show('button_hebrew');
    func_hide('button_english');
    if (init_sigma.graph.nodes().length > 0) {
        func_run_query()
    }
}