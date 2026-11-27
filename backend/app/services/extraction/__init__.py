"""Order extraction. Rule-based by default; another Extractor can be plugged in later."""
from datetime import datetime
from typing import Optional
from zoneinfo import ZoneInfo

from ...repositories import products as product_repo
from .base import CatalogueEntry, ExtractionResult, Extractor
from .rules import RuleBasedExtractor

_EXTRACTORS: dict[str, Extractor] = {RuleBasedExtractor.name: RuleBasedExtractor()}
DEFAULT_EXTRACTOR = RuleBasedExtractor.name


def load_catalogue(conn, shop_id: int) -> list[CatalogueEntry]:
    return [
        CatalogueEntry(p["id"], p["name"], p["default_unit"], [a["alias"] for a in p["aliases"]])
        for p in product_repo.list_products(conn, shop_id)
    ]


def keyterms(conn, shop_id: int, limit: int = 50) -> list[str]:
    """Product names for Sarvam keyterm prompting (max 50 terms, 64 chars each)."""
    terms: list[str] = []
    for entry in load_catalogue(conn, shop_id):
        for term in [entry.name, *entry.terms]:
            if term not in terms and len(term) <= 64:
                terms.append(term)
    return terms[:limit]


def extract_order(conn, shop_id: int, timezone: str, original: str,
                  roman: Optional[str] = None, english: Optional[str] = None,
                  extractor: str = DEFAULT_EXTRACTOR) -> ExtractionResult:
    today = datetime.now(ZoneInfo(timezone)).date().isoformat()
    return _EXTRACTORS[extractor].extract(original, roman, english, load_catalogue(conn, shop_id), today)
