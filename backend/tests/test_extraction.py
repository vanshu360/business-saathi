"""Rule-based extraction: reads the original transcript and flags anything unclear."""
import pytest

from app.catalogue_seed import DEFAULT_PRODUCTS
from app.services.extraction.base import CatalogueEntry
from app.services.extraction.rules import RuleBasedExtractor

CATALOGUE = [CatalogueEntry(i + 1, n, u, a) for i, (n, u, a) in enumerate(DEFAULT_PRODUCTS)]
TODAY = "2026-11-27"


def run(original, roman=None, english=None):
    return RuleBasedExtractor().extract(original, roman, english, CATALOGUE, TODAY)


def items(result):
    return [(i.product_name, i.quantity, i.unit) for i in result.items]


def test_hinglish_order_with_customer_and_delivery():
    r = run("Ramesh ji ko 2 kilo chawal, 1 kilo chini aur 1 litre doodh kal shaam 5 baje bhej dena")
    assert r.customer_name == "Ramesh"
    assert items(r) == [("Rice", 2, "kg"), ("Sugar", 1, "kg"), ("Milk", 1, "l")]
    assert not any(i.needs_review for i in r.items)
    assert r.delivery_date == "2026-11-28" and r.delivery_time == "17:00"
    assert "delivery_date" in r.uncertain_fields  # "kal" can mean yesterday or tomorrow


def test_devanagari_order_keeps_spoken_names():
    r = run("सुनीता जी के लिए ढाई किलो आटा और दो लीटर दूध, 98765 43210")
    assert r.customer_name == "सुनीता" and r.customer_phone == "9876543210"
    assert items(r) == [("Wheat flour", 2.5, "kg"), ("Milk", 2, "l")]
    assert [i.product_name_spoken for i in r.items] == ["आटा", "दूध"]


def test_english_order_and_products_without_separators():
    r = run("For Anil, 2kg rice half kg onion 2 l oil, deliver today 6 pm")
    assert r.customer_name == "Anil"
    assert items(r) == [("Rice", 2, "kg"), ("Onion", 0.5, "kg"), ("Cooking oil", 2, "l")]
    assert (r.delivery_date, r.delivery_time) == ("2026-11-27", "18:00")


def test_product_first_word_order():
    assert items(run("chawal 2 kilo chini 1 kilo")) == [("Rice", 2, "kg"), ("Sugar", 1, "kg")]


@pytest.mark.parametrize("text,reason", [
    ("chawal dena", "Quantity not spoken"),
    ("2 chawal", "Unit not spoken"),
    ("1 dozen ande", "not supported"),
    ("2 kilo kaju", "Not in the product list"),
    ("2 kilo basmati chawal", "Check the exact product"),
])
def test_unclear_items_are_flagged_not_guessed(text, reason):
    item = run(text).items[0]
    assert item.needs_review and reason in item.review_reason


def test_unknown_product_keeps_spoken_name_and_no_unit_is_invented():
    item = run("2 chawal").items[0]
    assert item.unit is None and item.quantity == 2
    kaju = run("2 kilo kaju").items[0]
    assert kaju.product_id is None and kaju.product_name == "kaju"


def test_give_verb_is_not_read_as_quantity_two():
    item = run("चावल दे दो").items[0]
    assert item.quantity is None and item.product_name_spoken == "चावल"


def test_time_without_morning_or_evening_is_flagged():
    r = run("2 kilo chawal 5 baje")
    assert r.delivery_time is None and "delivery_time" in r.uncertain_fields


def test_leftover_text_is_reported():
    r = run("2 kilo chawal aur thoda masala")
    assert r.unmatched_text == ["thoda masala"]


def test_roman_transcript_is_only_a_cross_check():
    r = run("रमेश जी को दो किलो चावल", roman="Ramesh ji ko teen kilo chawal")
    assert items(r) == [("Rice", 2, "kg")]  # original wins
    assert "Roman transcript says 3 kg" in r.items[0].review_reason


def test_roman_suggestion_for_unmatched_original_product():
    r = run("2 kilo xyz", roman="2 kilo chawal")
    assert r.items[0].product_name == "xyz" and r.items[0].suggestion == "Rice"


def test_english_translation_mismatch_is_reported():
    r = run("2 kilo chawal", english="2 kg rice and 1 litre milk")
    assert "items" in r.uncertain_fields


def test_extract_endpoint_uses_database_catalogue(client):
    client.post("/api/products", json={"name": "Semolina", "default_unit": "kg", "aliases": ["sooji"]})
    res = client.post("/api/extract", json={"original": "Meena ji ko 1 kilo sooji aur 2 packet namak"})
    assert res.status_code == 200
    body = res.json()
    assert body["customer_name"] == "Meena" and body["extractor"] == "rules-v1"
    assert [(i["product_name"], i["quantity"], i["unit"]) for i in body["items"]] == [
        ("Semolina", 1, "kg"), ("Salt", 2, "packet")]


def test_extract_endpoint_requires_text(client):
    assert client.post("/api/extract", json={"original": "  "}).status_code == 422


@pytest.mark.parametrize("text", ["one and a half kg rice", "ek aur aadha kilo chawal", "saadhe ek kilo chawal"])
def test_compound_halves_are_one_quantity(text):
    r = run(text)
    assert items(r) == [("Rice", 1.5, "kg")]
    assert not r.items[0].needs_review


def test_word_hour_with_baje_and_dotted_pm():
    r = run("2 kilo chawal kal shaam paanch baje")
    assert r.delivery_time == "17:00"
    r = run("2 kg rice tomorrow at 6 p.m.")
    assert items(r) == [("Rice", 2, "kg")] and r.delivery_time == "18:00"


def test_different_known_product_in_roman_is_flagged():
    r = run("2 किलो चावल", roman="2 kilo chini")
    assert items(r) == [("Rice", 2, "kg")]
    assert r.items[0].needs_review and "Sugar" in r.items[0].review_reason


def test_half_hours_compact_pm_and_verb_do():
    r = run("2 kilo chawal kal shaam saadhe paanch baje")
    assert items(r) == [("Rice", 2, "kg")] and r.delivery_time == "17:30"
    assert run("2 kg rice today 6p.m.").delivery_time == "18:00"
    r = run("chawal de do aur aadha kilo chini")
    assert ("Sugar", 0.5, "kg") in items(r)
    assert items(run("likh ek aur aadha kilo chawal")) == [("Rice", 1.5, "kg")]
