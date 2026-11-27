"""Built-in grocery word list, added once on first start. Used for extraction and Sarvam keyterms."""
from .database import utc_now

DEFAULT_PRODUCTS = [
    ("Rice", "kg", ["chawal", "chaval", "chawul", "चावल", "rice"]),
    ("Wheat flour", "kg", ["atta", "aata", "aataa", "आटा", "gehun ka atta"]),
    ("Sugar", "kg", ["chini", "cheeni", "shakkar", "चीनी", "शक्कर", "sugar"]),
    ("Salt", "packet", ["namak", "नमक", "salt"]),
    ("Milk", "l", ["doodh", "dudh", "दूध", "milk"]),
    ("Cooking oil", "l", ["tel", "तेल", "oil", "sarson ka tel", "सरसों का तेल"]),
    ("Tea", "packet", ["chai patti", "chaipatti", "chai", "चाय पत्ती", "चायपत्ती", "चाय", "tea"]),
    ("Biscuits", "packet", ["biscuit", "biskut", "बिस्कुट"]),
    ("Toor dal", "kg", ["dal", "daal", "arhar dal", "toor dal", "दाल", "अरहर दाल"]),
    ("Onion", "kg", ["pyaz", "pyaaz", "kanda", "प्याज", "प्याज़", "onion"]),
    ("Potato", "kg", ["aloo", "alu", "आलू", "potato"]),
    ("Tomato", "kg", ["tamatar", "टमाटर", "tomato"]),
    ("Bread", "packet", ["bread", "ब्रेड", "double roti"]),
    ("Eggs", "piece", ["anda", "ande", "अंडा", "अंडे", "egg"]),
    ("Ghee", "kg", ["ghee", "घी"]),
    ("Curd", "kg", ["dahi", "दही", "curd"]),
    ("Soap", "piece", ["sabun", "साबुन", "soap"]),
]


def seed_catalogue(conn, shop_id: int) -> None:
    if conn.execute("SELECT 1 FROM products WHERE shop_id = ? LIMIT 1", (shop_id,)).fetchone():
        return
    now = utc_now()
    for name, unit, aliases in DEFAULT_PRODUCTS:
        cur = conn.execute(
            "INSERT INTO products (shop_id, name, default_unit, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (shop_id, name, unit, now, now),
        )
        conn.executemany(
            "INSERT OR IGNORE INTO product_aliases (product_id, alias) VALUES (?, ?)",
            [(cur.lastrowid, a) for a in aliases],
        )
