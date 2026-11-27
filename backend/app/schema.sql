-- Business Saathi database schema (SQLite).
-- Every business table has shop_id so shops can be separated later.

CREATE TABLE IF NOT EXISTS shops (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    shop_id     INTEGER NOT NULL REFERENCES shops(id),
    key         TEXT NOT NULL,
    value       TEXT NOT NULL,
    PRIMARY KEY (shop_id, key)
);

CREATE TABLE IF NOT EXISTS customers (
    id          INTEGER PRIMARY KEY,
    shop_id     INTEGER NOT NULL REFERENCES shops(id),
    name        TEXT NOT NULL,
    phone       TEXT,
    notes       TEXT NOT NULL DEFAULT '',
    is_demo     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_customers_shop_phone ON customers(shop_id, phone);
CREATE INDEX IF NOT EXISTS idx_customers_shop_name ON customers(shop_id, name);

CREATE TABLE IF NOT EXISTS products (
    id            INTEGER PRIMARY KEY,
    shop_id       INTEGER NOT NULL REFERENCES shops(id),
    name          TEXT NOT NULL,
    default_unit  TEXT NOT NULL CHECK (default_unit IN ('kg','g','l','ml','piece','packet')),
    price         REAL CHECK (price IS NULL OR price >= 0),
    is_active     INTEGER NOT NULL DEFAULT 1,
    is_demo       INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_products_shop_name ON products(shop_id, name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS product_aliases (
    id             INTEGER PRIMARY KEY,
    product_id     INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    alias          TEXT NOT NULL,
    language_code  TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_alias_unique ON product_aliases(product_id, alias COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS transcriptions (
    id                    INTEGER PRIMARY KEY,
    shop_id               INTEGER NOT NULL REFERENCES shops(id),
    audio_sha256          TEXT,
    audio_path            TEXT,
    audio_mime            TEXT,
    audio_delete_after    TEXT,
    duration_seconds      REAL,
    api_type              TEXT CHECK (api_type IN ('rest','batch')),
    language_requested    TEXT NOT NULL,
    language_detected     TEXT,
    language_probability  REAL,
    original_mode         TEXT NOT NULL DEFAULT 'transcribe',
    original_text         TEXT,
    original_status       TEXT NOT NULL DEFAULT 'pending',
    original_error        TEXT,
    roman_text            TEXT,
    roman_status          TEXT NOT NULL DEFAULT 'pending',
    roman_error           TEXT,
    english_text          TEXT,
    english_status        TEXT NOT NULL DEFAULT 'pending',
    english_error         TEXT,
    request_count         INTEGER NOT NULL DEFAULT 0,
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_transcriptions_sha ON transcriptions(shop_id, audio_sha256);

CREATE TABLE IF NOT EXISTS orders (
    id                    INTEGER PRIMARY KEY,
    shop_id               INTEGER NOT NULL REFERENCES shops(id),
    order_number          TEXT NOT NULL UNIQUE,
    customer_id           INTEGER REFERENCES customers(id),
    status                TEXT NOT NULL CHECK (status IN
                            ('draft','confirmed','pending','processing','completed','cancelled')),
    source                TEXT NOT NULL CHECK (source IN ('voice','manual')),
    delivery_date         TEXT,
    delivery_time         TEXT,
    delivery_time_text    TEXT NOT NULL DEFAULT '',
    special_instructions  TEXT NOT NULL DEFAULT '',
    transcription_id      INTEGER REFERENCES transcriptions(id),
    idempotency_key       TEXT NOT NULL,
    is_demo               INTEGER NOT NULL DEFAULT 0,
    confirmed_at          TEXT,
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_idempotency ON orders(shop_id, idempotency_key);
CREATE INDEX IF NOT EXISTS idx_orders_shop_status ON orders(shop_id, status);
CREATE INDEX IF NOT EXISTS idx_orders_shop_created ON orders(shop_id, created_at);

CREATE TABLE IF NOT EXISTS order_items (
    id                   INTEGER PRIMARY KEY,
    order_id             INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    position             INTEGER NOT NULL DEFAULT 0,
    product_id           INTEGER REFERENCES products(id),
    product_name_spoken  TEXT NOT NULL DEFAULT '',
    product_name         TEXT NOT NULL,
    quantity             REAL CHECK (quantity IS NULL OR quantity > 0),
    unit                 TEXT CHECK (unit IS NULL OR unit IN ('kg','g','l','ml','piece','packet')),
    needs_review         INTEGER NOT NULL DEFAULT 0,
    review_reason        TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);

CREATE TABLE IF NOT EXISTS order_history (
    id          INTEGER PRIMARY KEY,
    order_id    INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    changed_at  TEXT NOT NULL,
    field       TEXT NOT NULL,
    old_value   TEXT,
    new_value   TEXT
);
CREATE INDEX IF NOT EXISTS idx_order_history_order ON order_history(order_id);
