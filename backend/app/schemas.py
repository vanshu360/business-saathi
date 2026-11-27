"""Request validation models. Anything not matching these is rejected with a 422 error."""
import re
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator

Unit = Literal["kg", "g", "l", "ml", "piece", "packet"]
OrderStatus = Literal["draft", "confirmed", "pending", "processing", "completed", "cancelled"]

_TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return " ".join(value.split())


def normalise_phone(value: Optional[str]) -> Optional[str]:
    """Accepts 10-digit Indian mobile numbers, with optional +91/0 prefix and spaces."""
    if value is None or not value.strip():
        return None
    digits = re.sub(r"[\s\-()]", "", value)
    if digits.startswith("+91"):
        digits = digits[3:]
    elif digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise ValueError("Phone number must be a 10-digit Indian mobile number")
    return digits


class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    default_unit: Unit
    price: Optional[float] = Field(default=None, ge=0)
    aliases: list[str] = Field(default_factory=list, max_length=30)

    _clean_name = field_validator("name")(lambda cls, v: clean_text(v))

    @field_validator("aliases")
    @classmethod
    def _clean_aliases(cls, values: list[str]) -> list[str]:
        seen, result = set(), []
        for v in values:
            v = clean_text(v) or ""
            if v and v.lower() not in seen and len(v) <= 64:
                seen.add(v.lower())
                result.append(v)
        return result


class AliasIn(BaseModel):
    alias: str = Field(min_length=1, max_length=64)
    language_code: Optional[str] = Field(default=None, max_length=10)


class CustomerIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    phone: Optional[str] = None
    notes: str = Field(default="", max_length=500)

    _clean_name = field_validator("name")(lambda cls, v: clean_text(v))
    _phone = field_validator("phone")(lambda cls, v: normalise_phone(v))


class OrderItemIn(BaseModel):
    product_id: Optional[int] = None
    product_name_spoken: str = Field(default="", max_length=120)
    product_name: str = Field(min_length=1, max_length=120)
    quantity: Optional[float] = Field(default=None, gt=0, le=100000)
    unit: Optional[Unit] = None
    needs_review: bool = False
    review_reason: str = Field(default="", max_length=200)

    _clean_name = field_validator("product_name")(lambda cls, v: clean_text(v))


class OrderFields(BaseModel):
    customer_id: Optional[int] = None
    customer_name: Optional[str] = Field(default=None, max_length=80)
    customer_phone: Optional[str] = None
    delivery_date: Optional[date] = None
    delivery_time: Optional[str] = None
    delivery_time_text: str = Field(default="", max_length=80)
    special_instructions: str = Field(default="", max_length=1000)
    items: list[OrderItemIn] = Field(default_factory=list, max_length=100)

    _clean_customer = field_validator("customer_name")(lambda cls, v: clean_text(v) or None)
    _phone = field_validator("customer_phone")(lambda cls, v: normalise_phone(v))

    @field_validator("delivery_time")
    @classmethod
    def _check_time(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        if not _TIME_RE.match(v):
            raise ValueError("Delivery time must be HH:MM in 24-hour format")
        return v


class OrderCreate(OrderFields):
    status: Literal["draft", "confirmed"] = "draft"
    source: Literal["voice", "manual"] = "manual"
    transcription_id: Optional[int] = None
    idempotency_key: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9\-_]+$")


class OrderUpdate(OrderFields):
    pass


class StatusChange(BaseModel):
    status: OrderStatus
