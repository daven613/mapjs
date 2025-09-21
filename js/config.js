// Configuration file - all settings in one place
// The app uses torah1.js and torah2.js for data instead of Neo4j

var config = {
    // Language settings
    language: {
        default: 'hebrew',
        current: 'hebrew'
    },

    // UI settings
    ui: {
        animationDuration: 800,
        animationEasing: 'quadraticInOut',
        layoutIterations: 500
    },

    // Graph settings
    graph: {
        minNodeSize: 1.0,
        maxNodeSize: 15.0,
        minEdgeSize: 0.5,
        maxEdgeSize: 1.8,
        labelThreshold: 2,
        defaultLabelSize: 13,
        animationsTime: 1500
    },

    // Colors
    colors: {
        defaultNode: '#6cbef4',
        selectedNode: '#f5963e',
        bechinaEdge: '#4acfc8',
        eitzaEdge: '#cf4ac8',
        edgeHover: '#000000'
    }
};

// Global variables for language strings
var lang_select_topic = "";
var lang_select_topic_1 = "";
var lang_select_depth = "";
var lang_select_depth_1 = "";
var lang_show_cypher_box = "";

// Note: Neo4j variables removed - data comes from torah1.js and torah2.js files