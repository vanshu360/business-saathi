"""Rule-based extractor: reads the original transcript; Roman and English are cross-checks only.

Anything it is not sure about is flagged for review instead of guessed.
"""
import re
import unicodedata
from datetime import date, timedelta
from typing import Optional

from .base import CatalogueEntry, ExtractedItem, ExtractionResult
from .vocabulary import (AM_PM, CLOCK_MARKERS, DATE_WORDS, DATIVE_MARKERS, HONORIFICS,
                         NUMBER_WORDS, PART_OF_DAY, PURPOSE_PAIRS, SEPARATORS, STOPWORDS,
                         UNIT_LOOKUP, UNSUPPORTED_UNITS, VERBS_BEFORE_DO,
                         HALF_BEFORE, HALF_WORDS)

DEVANAGARI_DIGITS = str.maketrans("०१२३४५६७८९", "0123456789")
PHONE_RE = re.compile(r"(?:\+?91[\s-]?)?([6-9](?:[\s-]?\d){9})(?!\d)")
CLOCK_RE = re.compile(r"^(\d{1,2})(?::(\d{2}))?$")
NUMBER_RE = re.compile(r"^\d+(?:\.\d+)?$")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "").translate(DEVANAGARI_DIGITS).lower()
    text = re.sub(r"\b([ap])\.\s?m\b\.?", r"\1m", text)
    text = re.sub(r"(?<=\d)(?=[^\d\s.:,])|(?<=[^\d\s.:,])(?=\d)", " ", text)
    text = re.sub(r"(?<!\d)[.:](?!\d)|[;।!?\"()\[\]]", " , ", text)
    text = re.sub(r",", " , ", text)
    return text


def _number(tok: str) -> Optional[float]:
    if NUMBER_RE.match(tok):
        return float(tok)
    value = NUMBER_WORDS.get(tok)
    return float(value) if value is not None and float(value).is_integer() else None


def _join_halves(tokens: list[str]) -> list[str]:
    """"one and a half" / "do aur aadha" / "saadhe teen" become one number, not two items."""
    out, i = [], 0
    while i < len(tokens):
        n = _number(tokens[i])
        if tokens[i] in HALF_BEFORE and i + 1 < len(tokens) and _number(tokens[i + 1]) is not None:
            out.append(f"{_number(tokens[i + 1]) + 0.5:g}")
            i += 2
            continue
        if n is not None and i + 2 < len(tokens) and tokens[i + 1] in ("and", "aur", "और"):
            j = i + 3 if tokens[i + 2] == "a" and i + 3 < len(tokens) else i + 2
            if tokens[j] in HALF_WORDS:
                out.append(f"{n + 0.5:g}")
                i = j + 1
                continue
        out.append(tokens[i])
        i += 1
    return out


def tokenize(text: str) -> list[str]:
    return _join_halves([t.strip("'") for t in normalise(text).split() if t.strip("'")])


class Matcher:
    """Finds catalogue terms (single or multi-word) at a token position."""

    def __init__(self, catalogue: list[CatalogueEntry]):
        self.terms: list[tuple[list[str], CatalogueEntry]] = []
        for entry in catalogue:
            for term in {entry.name, *entry.terms}:
                words = tokenize(term)
                if words:
                    self.terms.append((words, entry))
        self.terms.sort(key=lambda t: -len(t[0]))

    @staticmethod
    def _same(token: str, word: str) -> bool:
        return token == word or token in (word + "s", word + "es")

    def match(self, tokens: list[str], i: int) -> Optional[tuple[int, CatalogueEntry]]:
        for words, entry in self.terms:
            n = len(words)
            if all(i + k < len(tokens) and self._same(tokens[i + k], w) for k, w in enumerate(words)):
                return n, entry
        return None

    def is_term_word(self, token: str) -> bool:
        return any(self._same(token, w) for words, _ in self.terms for w in words)


class _Draft:
    def __init__(self):
        self.quantity: Optional[float] = None
        self.unit: Optional[str] = None
        self.bad_unit: Optional[str] = None
        self.entry: Optional[CatalogueEntry] = None
        self.spoken: list[str] = []
        self.unknown: list[str] = []

    def empty(self) -> bool:
        return self.quantity is None and self.unit is None and self.entry is None and not self.bad_unit

    def to_item(self) -> Optional[ExtractedItem]:
        if self.empty():
            return None
        spoken = " ".join(self.unknown + self.spoken).strip()
        if self.entry:
            item = ExtractedItem(product_name=self.entry.name, product_name_spoken=spoken,
                                 product_id=self.entry.product_id)
            if self.unknown:
                item.flag(f"Check the exact product: \"{spoken}\"")
        elif self.unknown:
            item = ExtractedItem(product_name=spoken, product_name_spoken=spoken)
            item.flag("Not in the product list, please check the name")
        else:
            item = ExtractedItem(product_name="", product_name_spoken="")
            item.flag("Product not clear")
        item.quantity, item.unit = self.quantity, self.unit
        if self.quantity is None:
            item.flag("Quantity not spoken")
        if self.bad_unit:
            item.flag(f"Unit \"{self.bad_unit}\" is not supported, please choose a unit")
        elif self.unit is None and self.quantity is not None:
            item.flag("Unit not spoken")
        return item


class RuleBasedExtractor:
    name = "rules-v1"

    def extract(self, original: str, roman: Optional[str], english: Optional[str],
                catalogue: list[CatalogueEntry], today: str) -> ExtractionResult:
        matcher = Matcher(catalogue)
        result = self._parse(original, matcher, today)
        if roman:
            self._cross_check(result, self._parse(roman, matcher, today), "Roman")
        if english:
            other = self._parse(english, matcher, today)
            known = lambda items: sum(1 for i in items if i.product_id)
            if known(other.items) > known(result.items):
                result.uncertain_fields["items"] = (
                    f"The English translation mentions {known(other.items)} known products but "
                    f"only {known(result.items)} were found in the original. Please check.")
        result.extractor = self.name
        return result

    # ---- parsing one transcript -------------------------------------------------
    def _parse(self, text: str, matcher: Matcher, today: str) -> ExtractionResult:
        result = ExtractionResult()
        text = unicodedata.normalize("NFC", text or "").translate(DEVANAGARI_DIGITS)
        phone = PHONE_RE.search(text)
        if phone:
            result.customer_phone = re.sub(r"\D", "", phone.group(1))
            text = text[:phone.start()] + " , " + text[phone.end():]
        tokens = tokenize(text)
        tokens = self._take_customer(tokens, matcher, result)
        tokens = self._take_delivery(tokens, result, today)
        self._take_items(tokens, matcher, result)
        return result

    def _name_like(self, token: str, matcher: Matcher) -> bool:
        return (all(unicodedata.category(c)[0] in "LM" for c in token) and token not in STOPWORDS and token not in NUMBER_WORDS
                and token not in UNIT_LOOKUP and token not in SEPARATORS
                and token not in DATE_WORDS and token not in PART_OF_DAY
                and token not in HONORIFICS and not matcher.is_term_word(token))

    def _take_customer(self, tokens, matcher, result) -> list[str]:
        candidates = []
        for i, tok in enumerate(tokens):
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            if tok in HONORIFICS:
                strong, end = True, i + 1
                if nxt in DATIVE_MARKERS:
                    end += 1
                elif (nxt, tokens[i + 2] if i + 2 < len(tokens) else "") in PURPOSE_PAIRS:
                    end += 2
            elif tok in DATIVE_MARKERS:
                strong, end = False, i + 1
            elif (tok, nxt) in PURPOSE_PAIRS:
                strong, end = False, i + 2
            elif tok in ("for", "customer") and i + 1 < len(tokens):
                names = [t for t in tokens[i + 1:i + 3]]
                names = names[:1] if len(names) < 2 or not self._name_like(names[1], matcher) else names
                if names and self._name_like(names[0], matcher):
                    candidates.append((False, i, i + 1 + len(names), names))
                continue
            else:
                continue
            start = i
            while start > 0 and i - start < 2 and self._name_like(tokens[start - 1], matcher):
                start -= 1
            if start < i:
                candidates.append((strong, start, end, tokens[start:i]))
        if not candidates:
            return tokens
        strong, start, end, names = sorted(candidates, key=lambda c: (not c[0], c[1]))[0]
        result.customer_name = " ".join(n.title() if n.isascii() else n for n in names)
        if not strong:
            result.uncertain_fields["customer_name"] = "Customer name detected without \"ji\", please check"
        return tokens[:start] + [","] + tokens[end:]

    def _take_delivery(self, tokens, result, today) -> list[str]:
        keep, parts = [], []
        hour = minute = None
        meridiem = part = None
        i = 0
        while i < len(tokens):
            tok, nxt = tokens[i], tokens[i + 1] if i + 1 < len(tokens) else ""
            clock = CLOCK_RE.match(tok)
            if not clock and nxt in CLOCK_MARKERS and _number(tok) is not None:
                clock = CLOCK_RE.match(f"{_number(tok):g}")
            if tok in DATE_WORDS:
                label, offset, ambiguous = DATE_WORDS[tok]
                result.delivery_date = (date.fromisoformat(today) + timedelta(days=offset)).isoformat()
                parts.append(label)
                if ambiguous:
                    result.uncertain_fields["delivery_date"] = f"\"{tok}\" was read as {label}, please confirm"
            elif tok in PART_OF_DAY:
                part = PART_OF_DAY[tok]
                parts.append(part)
            elif clock and (nxt in CLOCK_MARKERS or nxt in AM_PM) and int(clock.group(1)) <= 12:
                hour, minute = int(clock.group(1)), int(clock.group(2) or 0)
                if nxt in AM_PM:
                    meridiem = AM_PM[nxt]
                parts.append(f"{tok} {nxt}")
                i += 1
            else:
                keep.append(tok)
            i += 1
        result.delivery_time_text = " ".join(parts)
        if hour is not None:
            if meridiem == "pm" or (meridiem is None and part in ("evening", "night")
                                    or part == "afternoon" and hour < 7):
                hour = hour % 12 + 12
            elif meridiem == "am" or part == "morning":
                hour = hour % 12
            else:
                result.uncertain_fields["delivery_time"] = "Time spoken without morning/evening, please confirm"
                return keep
            result.delivery_time = f"{hour:02d}:{minute:02d}"
        return keep

    def _take_items(self, tokens, matcher, result) -> None:
        draft, loose = _Draft(), []

        def finish():
            nonlocal draft
            item = draft.to_item()
            if item:
                result.items.append(item)
            elif draft.unknown:
                loose.extend(draft.unknown)
            draft = _Draft()

        def flush_loose():
            if loose:
                result.unmatched_text.append(" ".join(loose))
                loose.clear()

        i = 0
        while i < len(tokens):
            tok = tokens[i]
            nxt = tokens[i + 1] if i + 1 < len(tokens) else ""
            prev = tokens[i - 1] if i > 0 else ""
            if tok in SEPARATORS:
                finish()
                flush_loose()
                i += 1
                continue
            hit = matcher.match(tokens, i)
            number = float(tok) if NUMBER_RE.match(tok) else None
            if number is None and tok in NUMBER_WORDS and prev not in VERBS_BEFORE_DO and (
                    nxt in UNIT_LOOKUP or nxt in UNSUPPORTED_UNITS or matcher.match(tokens, i + 1)):
                number = float(NUMBER_WORDS[tok])
            if number is not None:
                if draft.quantity is not None or draft.entry is not None and draft.unit is not None:
                    finish()
                draft.quantity = number
            elif tok in UNIT_LOOKUP and draft.unit is None:
                draft.unit = UNIT_LOOKUP[tok]
            elif tok in UNSUPPORTED_UNITS:
                draft.bad_unit = tok
            elif hit:
                if draft.entry is not None:
                    finish()
                draft.entry = hit[1]
                draft.spoken = tokens[i:i + hit[0]]
                i += hit[0]
                continue
            elif tok not in STOPWORDS and tok not in NUMBER_WORDS:
                if draft.entry is not None and draft.quantity is not None:
                    finish()
                draft.unknown.append(tok)
            i += 1
        finish()
        flush_loose()

    # ---- cross-checking with the Roman transcript ------------------------------
    def _cross_check(self, result: ExtractionResult, other: ExtractionResult, label: str) -> None:
        if not result.items and other.items:
            for item in other.items:
                item.flag(f"Found only in the {label} transcript, please check")
            result.items = other.items
        elif len(result.items) == len(other.items):
            for mine, theirs in zip(result.items, other.items):
                if mine.product_id is None and theirs.product_id is not None:
                    mine.suggestion = theirs.product_name
                    mine.flag(f"{label} transcript suggests \"{theirs.product_name}\"")
                elif mine.product_id and theirs.product_id and mine.product_id != theirs.product_id:
                    mine.flag(f"{label} transcript says \"{theirs.product_name}\", please check the product")
                if (mine.quantity, mine.unit) != (theirs.quantity, theirs.unit) and theirs.quantity is not None:
                    mine.flag(f"{label} transcript says {theirs.quantity:g} {theirs.unit or ''}".strip())
        elif other.items:
            result.uncertain_fields["items"] = (
                f"The {label} transcript has {len(other.items)} items but the original has "
                f"{len(result.items)}. Please check.")
        for key in ("customer_name", "customer_phone"):
            if getattr(result, key) is None and getattr(other, key):
                setattr(result, key, getattr(other, key))
                result.uncertain_fields[key] = f"Taken from the {label} transcript, please check"
