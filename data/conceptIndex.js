// Concept Index - Maps canonical concepts to their variants
// This enables semantic search: searching for "תורה" will also find "לימוד תורה", "דברי תורה", etc.

const conceptIndex = {
    // =============== MITZVOT & SPIRITUAL PRACTICES ===============

    "תורה": {
        canonical: "תורה",
        variants: [
            "התורה",
            "תורת ה'",
            "לימוד תורה",
            "תלמוד תורה",
            "עסק התורה",
            "דברי תורה",
            "דרושי התורה",
            "באורי התורה",
            "אותיות התורה",
            "בתורה"
        ],
        category: "מצוות",
        subcategory: "תורה ומצוות",
        description: "Torah and Torah study"
    },

    "תפלה": {
        canonical: "תפלה",
        variants: [
            "התפלה",
            "תפלה לשמה",
            "בעל תפלה",
            "תפלות",
            "להתפלל"
        ],
        category: "מצוות",
        subcategory: "עבודה",
        description: "Prayer"
    },

    "צדקה": {
        canonical: "צדקה",
        variants: [
            "הצדקה",
            "נתינת צדקה",
            "מעשי צדקה"
        ],
        category: "מצוות",
        subcategory: "מעשים טובים",
        description: "Charity and righteousness"
    },

    "תשובה": {
        canonical: "תשובה",
        variants: [
            "התשובה",
            "בעל תשובה",
            "עשיית תשובה"
        ],
        category: "מצוות",
        subcategory: "עבודה",
        description: "Repentance"
    },

    "תקון הברית": {
        canonical: "תקון הברית",
        variants: [
            "שמירת הברית",
            "קדשת הברית",
            "ברית קדש"
        ],
        category: "מצוות",
        subcategory: "קדשה",
        description: "Guarding the covenant"
    },

    "שבת": {
        canonical: "שבת",
        variants: [
            "השבת",
            "יום השבת",
            "שבת קדש",
            "קדשת השבת"
        ],
        category: "מצוות",
        subcategory: "זמנים",
        description: "Sabbath"
    },

    "תפלין": {
        canonical: "תפלין",
        variants: [
            "התפלין",
            "הנחת תפלין",
            "תפילין"
        ],
        category: "מצוות",
        subcategory: "תורה ומצוות",
        description: "Tefillin"
    },

    "תענית": {
        canonical: "תענית",
        variants: [
            "התענית",
            "תעניות",
            "צום"
        ],
        category: "מצוות",
        subcategory: "עבודה",
        description: "Fasting"
    },

    // =============== MIDDOT (CHARACTER TRAITS) ===============

    "אמונה": {
        canonical: "אמונה",
        variants: [
            "האמונה",
            "אמונה שלמה",
            "בעל אמונה"
        ],
        category: "מדות",
        subcategory: "עיקרים",
        description: "Faith and belief"
    },

    "יראה": {
        canonical: "יראה",
        variants: [
            "היראה",
            "יראת שמים",
            "יראת ה'",
            "פחד",
            "מורא"
        ],
        category: "מדות",
        subcategory: "עבודה",
        description: "Fear and awe of God"
    },

    "אהבה": {
        canonical: "אהבה",
        variants: [
            "האהבה",
            "אהבת ה'",
            "אהבה רבה"
        ],
        category: "מדות",
        subcategory: "עבודה",
        description: "Love of God"
    },

    "שמחה": {
        canonical: "שמחה",
        variants: [
            "השמחה",
            "שמחה גדולה",
            "לשמח"
        ],
        category: "מדות",
        subcategory: "עבודה",
        description: "Joy and happiness"
    },

    "אמת": {
        canonical: "אמת",
        variants: [
            "האמת",
            "דרך האמת",
            "אנשי אמת"
        ],
        category: "מדות",
        subcategory: "מידות טובות",
        description: "Truth"
    },

    "שלום": {
        canonical: "שלום",
        variants: [
            "השלום",
            "דרכי שלום",
            "שלום בית"
        ],
        category: "מדות",
        subcategory: "מידות טובות",
        description: "Peace"
    },

    "ענווה": {
        canonical: "ענווה",
        variants: [
            "הענווה",
            "שפלות",
            "שפל רוח"
        ],
        category: "מדות",
        subcategory: "מידות טובות",
        description: "Humility"
    },

    "כבוד": {
        canonical: "כבוד",
        variants: [
            "הכבוד",
            "גאוה",
            "גדלות"
        ],
        category: "מדות",
        subcategory: "מידות רעות",
        description: "Honor and pride"
    },

    "בושה": {
        canonical: "בושה",
        variants: [
            "הבושה",
            "בוש",
            "כלימה"
        ],
        category: "מדות",
        subcategory: "רגשות",
        description: "Shame and embarrassment"
    },

    // =============== SEFIROT & SPIRITUAL CONCEPTS ===============

    "חכמה": {
        canonical: "חכמה",
        variants: [
            "החכמה",
            "שכל",
            "השכל",
            "חכמה עילאה"
        ],
        category: "ספירות",
        subcategory: "מוחין",
        description: "Wisdom and intellect"
    },

    "בינה": {
        canonical: "בינה",
        variants: [
            "הבינה",
            "תבונה",
            "התבונה"
        ],
        category: "ספירות",
        subcategory: "מוחין",
        description: "Understanding"
    },

    "דעת": {
        canonical: "דעת",
        variants: [
            "הדעת",
            "ידיעה",
            "מוחין"
        ],
        category: "ספירות",
        subcategory: "מוחין",
        description: "Knowledge and consciousness"
    },

    "חסד": {
        canonical: "חסד",
        variants: [
            "החסד",
            "חסדים",
            "גמילות חסדים"
        ],
        category: "ספירות",
        subcategory: "מידות",
        description: "Kindness and loving-kindness"
    },

    "דין": {
        canonical: "דין",
        variants: [
            "הדין",
            "דינים",
            "משפט",
            "המתקת הדינים"
        ],
        category: "ספירות",
        subcategory: "מידות",
        description: "Judgment and justice"
    },

    "מלכות": {
        canonical: "מלכות",
        variants: [
            "המלכות",
            "מלכות דקדשה",
            "מלכות שמים",
            "מלכותא דשמיא"
        ],
        category: "ספירות",
        subcategory: "מלכות",
        description: "Kingship and sovereignty"
    },

    // =============== BIBLICAL FIGURES ===============

    "משה": {
        canonical: "משה",
        variants: [
            "משה רבינו",
            "משה רבנו"
        ],
        category: "אישים",
        subcategory: "אבות",
        description: "Moses"
    },

    "אברהם": {
        canonical: "אברהם",
        variants: [
            "אברהם אבינו",
            "אברהם אוהבי"
        ],
        category: "אישים",
        subcategory: "אבות",
        description: "Abraham"
    },

    "יעקב": {
        canonical: "יעקב",
        variants: [
            "יעקב אבינו",
            "ישראל",
            "איש תם"
        ],
        category: "אישים",
        subcategory: "אבות",
        description: "Jacob"
    },

    "יוסף": {
        canonical: "יוסף",
        variants: [
            "יוסף הצדיק",
            "יוסף הצדק"
        ],
        category: "אישים",
        subcategory: "שבטים",
        description: "Joseph"
    },

    "צדיק": {
        canonical: "צדיק",
        variants: [
            "הצדיק",
            "צדיקים",
            "צדיק אמת",
            "צדיק האמת"
        ],
        category: "אישים",
        subcategory: "מדרגות",
        description: "Righteous person"
    },

    // =============== PLACES & CONCEPTS ===============

    "ארץ ישראל": {
        canonical: "ארץ ישראל",
        variants: [
            "הארץ",
            "ארץ הקדושה",
            "ארץ הקודש"
        ],
        category: "מקומות",
        subcategory: "קדשה",
        description: "Land of Israel"
    },

    "ממון": {
        canonical: "ממון",
        variants: [
            "הממון",
            "כסף",
            "פרנסה",
            "עשירות"
        ],
        category: "גשמיות",
        subcategory: "פרנסה",
        description: "Money and livelihood"
    }
};

// Helper function to find all variants of a concept
function getConceptVariants(searchTerm) {
    // First, check if it's a canonical term
    if (conceptIndex[searchTerm]) {
        return [conceptIndex[searchTerm].canonical, ...conceptIndex[searchTerm].variants];
    }

    // Otherwise, search through all concepts to see if it's a variant
    for (const [canonical, data] of Object.entries(conceptIndex)) {
        if (data.variants.includes(searchTerm)) {
            return [canonical, ...data.variants];
        }
    }

    // If not found, return just the search term
    return [searchTerm];
}

// Helper function to get concept category
function getConceptCategory(term) {
    if (conceptIndex[term]) {
        return conceptIndex[term].category;
    }

    for (const [canonical, data] of Object.entries(conceptIndex)) {
        if (data.variants.includes(term)) {
            return data.category;
        }
    }

    return null;
}

// Helper function to get all concepts in a category
function getConceptsByCategory(category) {
    return Object.entries(conceptIndex)
        .filter(([_, data]) => data.category === category)
        .map(([canonical, _]) => canonical);
}
