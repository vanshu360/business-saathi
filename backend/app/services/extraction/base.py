"""Extraction interface. Any extractor (rule-based today, AI-based later) returns this shape."""
from dataclasses import asdict, dataclass, field
from typing import Optional, Protocol


@dataclass
class CatalogueEntry:
    product_id: int
    name: str
    default_unit: str
    terms: list[str]


@dataclass
class ExtractedItem:
    product_name: str
    product_name_spoken: str
    product_id: Optional[int] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    needs_review: bool = False
    review_reason: str = ""
    suggestion: Optional[str] = None

    def flag(self, reason: str) -> None:
        self.needs_review = True
        self.review_reason = f"{self.review_reason}; {reason}" if self.review_reason else reason


@dataclass
class ExtractionResult:
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    delivery_date: Optional[str] = None
    delivery_time: Optional[str] = None
    delivery_time_text: str = ""
    items: list[ExtractedItem] = field(default_factory=list)
    uncertain_fields: dict[str, str] = field(default_factory=dict)
    unmatched_text: list[str] = field(default_factory=list)
    extractor: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class Extractor(Protocol):
    name: str

    def extract(self, original: str, roman: Optional[str], english: Optional[str],
                catalogue: list[CatalogueEntry], today: str) -> ExtractionResult:
        ...
