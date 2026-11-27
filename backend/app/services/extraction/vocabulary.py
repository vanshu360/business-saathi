"""Words the rule-based extractor understands (Hindi in Roman and Devanagari script, and English)."""

NUMBER_WORDS = {
    "ek": 1, "एक": 1, "one": 1, "do": 2, "दो": 2, "two": 2, "teen": 3, "तीन": 3, "three": 3,
    "char": 4, "chaar": 4, "चार": 4, "four": 4, "paanch": 5, "panch": 5, "पांच": 5, "पाँच": 5,
    "five": 5, "chhe": 6, "chah": 6, "chhah": 6, "छह": 6, "छः": 6, "six": 6, "saat": 7,
    "सात": 7, "seven": 7, "aath": 8, "आठ": 8, "eight": 8, "nau": 9, "नौ": 9, "nine": 9,
    "das": 10, "दस": 10, "ten": 10, "barah": 12, "बारह": 12, "twelve": 12, "bees": 20,
    "बीस": 20, "twenty": 20, "aadha": 0.5, "adha": 0.5, "आधा": 0.5, "half": 0.5,
    "sava": 1.25, "सवा": 1.25, "dedh": 1.5, "derh": 1.5, "डेढ़": 1.5, "डेढ": 1.5,
    "dhai": 2.5, "dhaai": 2.5, "ढाई": 2.5,
}

UNIT_WORDS = {
    "kg": ["kilo", "kilos", "kg", "kgs", "kilogram", "kilograms", "किलो", "केजी"],
    "g": ["gram", "grams", "gm", "gms", "g", "ग्राम"],
    "l": ["litre", "litres", "liter", "liters", "ltr", "l", "लीटर"],
    "ml": ["ml", "millilitre", "milliliter", "मिलीलीटर", "एमएल"],
    "packet": ["packet", "packets", "pack", "packs", "pkt", "paket", "पैकेट", "पाकेट"],
    "piece": ["piece", "pieces", "pc", "pcs", "nag", "नग", "पीस"],
}
UNIT_LOOKUP = {word: unit for unit, words in UNIT_WORDS.items() for word in words}

# Containers we cannot convert to kg/l/packet/piece without guessing.
UNSUPPORTED_UNITS = {"dozen", "darjan", "दर्जन", "dabba", "डब्बा", "box", "bottle", "botal",
                     "बोतल", "bori", "बोरी", "bag"}

HALF_WORDS = {"half", "aadha", "adha", "आधा"}
HALF_BEFORE = {"saadhe", "sadhe", "saade", "साढ़े", "साढे"}

SEPARATORS = {",", "aur", "और", "and", "&", "phir", "fir", "फिर", "plus", "also", "तथा"}

HONORIFICS = {"ji", "जी", "bhai", "भाई", "bhaiya", "भैया", "sahab", "साहब", "didi", "दीदी",
              "aunty", "uncle", "madam", "sir"}
DATIVE_MARKERS = {"ko", "को"}
PURPOSE_PAIRS = {("ke", "liye"), ("के", "लिए"), ("ke", "lie")}

DATE_WORDS = {
    "aaj": ("today", 0, False), "आज": ("today", 0, False), "today": ("today", 0, False),
    "kal": ("tomorrow", 1, True), "कल": ("tomorrow", 1, True),
    "tomorrow": ("tomorrow", 1, False),
    "parso": ("day after tomorrow", 2, True), "परसों": ("day after tomorrow", 2, True),
}
PART_OF_DAY = {
    "subah": "morning", "सुबह": "morning", "morning": "morning",
    "dopahar": "afternoon", "दोपहर": "afternoon", "afternoon": "afternoon",
    "shaam": "evening", "sham": "evening", "शाम": "evening", "evening": "evening",
    "raat": "night", "रात": "night", "night": "night",
}
CLOCK_MARKERS = {"baje", "बजे", "o'clock", "oclock"}
AM_PM = {"am": "am", "a.m": "am", "pm": "pm", "p.m": "pm"}

STOPWORDS = {
    # Hindi (Roman)
    "hai", "hain", "he", "dena", "de", "dijiye", "dijie", "dedo", "chahiye", "chaiye", "wala",
    "wali", "wale", "vala", "ka", "ki", "ke", "se", "me", "mein", "main", "bhi", "aap", "please",
    "plz", "likh", "likhna", "likho", "likhiye", "karna", "kar", "kardo", "kardena", "bhejna",
    "bhej", "bhejo", "bhejiye", "order", "delivery", "deliver", "ghar", "pe", "par", "tak", "to",
    "toh", "na", "liye", "lie", "ko", "jaldi", "abhi", "bhaiya", "haan", "achha", "theek",
    "thik", "sath", "saath", "chahie", "lena", "lijiye", "pahuncha", "pahunchana", "ek",
    # Hindi (Devanagari)
    "है", "हैं", "देना", "दे", "दीजिए", "दीजिये", "चाहिए", "वाला", "वाली", "वाले", "का", "की",
    "के", "से", "में", "भी", "आप", "लिख", "लिखना", "लिखो", "कर", "करना", "भेज", "भेजना",
    "भेजो", "डिलीवरी", "घर", "पर", "तक", "तो", "लिए", "को", "जल्दी", "अभी", "ऑर्डर",
    "पहुंचा", "पहुँचा", "देना।", "दो।",
    # English
    "the", "a", "an", "of", "give", "send", "need", "needs", "want", "wants", "i", "we", "with",
    "is", "are", "by", "at", "in", "on", "my", "me", "add", "write", "note", "it", "them",
    "this", "that", "for", "has", "have", "be", "will", "should", "deliver", "delivered",
    "customer", "name", "pls", "kindly", "some", "number", "phone", "mobile", "नंबर", "नाम",
}
VERBS_BEFORE_DO = {"de", "kar", "likh", "bhej", "dikha", "rakh", "दे", "कर", "लिख", "भेज", "रख"}
