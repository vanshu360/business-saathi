"""Speech languages. 'documented' = listed by Sarvam for Saaras v4 (docs checked 27-11-2026).
'tested' = verified by us with a real recording. Update TESTED_CODES only after a real test."""

SAARAS_V4_LANGUAGES = [
    ("en-IN", "English"), ("as-IN", "Assamese"), ("bn-IN", "Bengali"), ("brx-IN", "Bodo"),
    ("doi-IN", "Dogri"), ("gu-IN", "Gujarati"), ("hi-IN", "Hindi"), ("kn-IN", "Kannada"),
    ("ks-IN", "Kashmiri"), ("kok-IN", "Konkani"), ("mai-IN", "Maithili"),
    ("ml-IN", "Malayalam"), ("mni-IN", "Manipuri"), ("mr-IN", "Marathi"), ("ne-IN", "Nepali"),
    ("od-IN", "Odia"), ("pa-IN", "Punjabi"), ("sa-IN", "Sanskrit"), ("sat-IN", "Santali"),
    ("sd-IN", "Sindhi"), ("ta-IN", "Tamil"), ("te-IN", "Telugu"), ("ur-IN", "Urdu"),
]

TESTED_CODES: set[str] = set()

AUTO_DETECT = "unknown"
VALID_CODES = {code for code, _ in SAARAS_V4_LANGUAGES} | {AUTO_DETECT}


def language_list() -> list[dict]:
    items = [{
        "code": AUTO_DETECT,
        "name": "Detect automatically",
        "status": "documented",
    }]
    for code, name in SAARAS_V4_LANGUAGES:
        items.append({
            "code": code,
            "name": name,
            "status": "tested" if code in TESTED_CODES else "documented",
        })
    return items
