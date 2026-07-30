"""SQLite data layer for the wardrobe app.

Single-user, local. Auto-creates the schema and seeds Mario's starting
wardrobe + the "Office" collection on first run.
"""

import os
import re
import shutil
import sqlite3
from itertools import product

# The database lives in a fixed spot in the user's profile — NOT inside the
# project folder. That way, re-downloading the app into a brand new folder
# (a fresh "WARDROBE 1.4" extract, say) still finds the same wardrobe data;
# nothing looks wiped just because the code moved.
_OLD_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wardrobe.db")


def _data_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "WardrobeApp")
    os.makedirs(d, exist_ok=True)
    return d


DB_PATH = os.path.join(_data_dir(), "wardrobe.db")

# One-time migration for anyone upgrading from a version that kept the
# database next to the code: adopt that existing database instead of
# starting over.
if not os.path.exists(DB_PATH) and os.path.exists(_OLD_DB_PATH):
    shutil.move(_OLD_DB_PATH, DB_PATH)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    category    TEXT NOT NULL DEFAULT '',
    piece_type  TEXT NOT NULL DEFAULT '',
    color       TEXT NOT NULL DEFAULT '',
    color_hex   TEXT NOT NULL DEFAULT '',
    brand       TEXT NOT NULL DEFAULT '',
    material    TEXT NOT NULL DEFAULT '',
    image_url   TEXT NOT NULL DEFAULT '',
    temp_min    INTEGER,
    temp_max    INTEGER,
    notes       TEXT NOT NULL DEFAULT '',
    pending_purchase INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS collections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    temp_min    INTEGER,
    temp_max    INTEGER,
    notes       TEXT NOT NULL DEFAULT '',
    sort_order  INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS outfits (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL DEFAULT '',
    collection_id INTEGER,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (collection_id) REFERENCES collections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS outfit_items (
    outfit_id INTEGER NOT NULL,
    item_id   INTEGER NOT NULL,
    PRIMARY KEY (outfit_id, item_id),
    FOREIGN KEY (outfit_id) REFERENCES outfits(id) ON DELETE CASCADE,
    FOREIGN KEY (item_id)   REFERENCES items(id)   ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS temp_classes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    icon        TEXT NOT NULL DEFAULT '🌡️',
    temp_min    INTEGER NOT NULL,
    temp_max    INTEGER NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS price_notes (
    brand       TEXT NOT NULL DEFAULT '',
    category    TEXT NOT NULL DEFAULT '',
    note        TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (brand, category)
);

CREATE TABLE IF NOT EXISTS brands (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS materials (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL UNIQUE,
    piece_type  TEXT NOT NULL DEFAULT 'Top'
);

CREATE TABLE IF NOT EXISTS category_temp_defaults (
    category      TEXT PRIMARY KEY,
    temp_class_id INTEGER,
    FOREIGN KEY (temp_class_id) REFERENCES temp_classes(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS category_brand_defaults (
    category    TEXT PRIMARY KEY,
    brand       TEXT
);

CREATE TABLE IF NOT EXISTS category_material_defaults (
    category    TEXT PRIMARY KEY,
    material    TEXT
);
"""


def init_db():
    conn = get_conn()
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.commit()
    # Seed only if the wardrobe is empty.
    if conn.execute("SELECT COUNT(*) AS c FROM items").fetchone()["c"] == 0:
        _seed(conn)
    if conn.execute("SELECT COUNT(*) AS c FROM temp_classes").fetchone()["c"] == 0:
        _seed_temp_classes(conn)
    if conn.execute("SELECT COUNT(*) AS c FROM brands").fetchone()["c"] == 0:
        _seed_brands(conn)
    if conn.execute("SELECT COUNT(*) AS c FROM price_notes").fetchone()["c"] == 0:
        _seed_price_notes(conn)
    if conn.execute("SELECT COUNT(*) AS c FROM categories").fetchone()["c"] == 0:
        _seed_categories(conn)
    if conn.execute("SELECT COUNT(*) AS c FROM category_temp_defaults").fetchone()["c"] == 0:
        _seed_category_temp_defaults(conn)
    if conn.execute("SELECT COUNT(*) AS c FROM materials").fetchone()["c"] == 0:
        _seed_materials(conn)
    conn.close()


def _migrate(conn):
    """Add newer columns to wardrobes created before they existed."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(items)")}
    if "piece_type" not in cols:
        conn.execute("ALTER TABLE items ADD COLUMN piece_type TEXT NOT NULL DEFAULT ''")
    if "image_url" not in cols:
        conn.execute("ALTER TABLE items ADD COLUMN image_url TEXT NOT NULL DEFAULT ''")
    if "pending_purchase" not in cols:
        conn.execute("ALTER TABLE items ADD COLUMN pending_purchase INTEGER NOT NULL DEFAULT 0")
    cat_cols = {r["name"] for r in conn.execute("PRAGMA table_info(categories)")}
    if "piece_type" not in cat_cols:
        conn.execute("ALTER TABLE categories ADD COLUMN piece_type TEXT NOT NULL DEFAULT 'Top'")
        # Best-effort classify any pre-existing rows using the same keyword
        # heuristic the rest of the app already uses to guess Top vs Bottom.
        bottom_re = re.compile(r"(pant|slack|trouser|jean|chino|short|skirt|legging)", re.I)
        for row in conn.execute("SELECT id, name FROM categories").fetchall():
            if bottom_re.search(row["name"] or ""):
                conn.execute("UPDATE categories SET piece_type = 'Bottom' WHERE id = ?", (row["id"],))
    coll_cols = {r["name"] for r in conn.execute("PRAGMA table_info(collections)")}
    if "sort_order" not in coll_cols:
        conn.execute("ALTER TABLE collections ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0")
        for idx, row in enumerate(conn.execute("SELECT id FROM collections ORDER BY created_at").fetchall()):
            conn.execute("UPDATE collections SET sort_order = ? WHERE id = ?", (idx, row["id"]))
        # Pinned to the top by default, per an explicit one-off ask — still
        # fully re-orderable afterward via drag-and-drop like anything else.
        conn.execute("UPDATE collections SET sort_order = -1 WHERE lower(name) = 'outdoor daytime chic'")
    conn.commit()


# --- Seed data -----------------------------------------------------------

# Starting wardrobe. color_hex is an approximate swatch for the UI.
SEED_ITEMS = [
    # name, category, piece_type, color, color_hex, brand, material,
    #   temp_min, temp_max, notes
    ("Grey Slacks", "Slacks", "Bottom", "Grey", "#8a8d91", "", "", 60, 78, ""),
    ("Khaki Slacks", "Slacks", "Bottom", "Khaki", "#c3a877", "", "", 62, 82, ""),
    ("Long Sleeve Polo — Dark Green", "Long Sleeve Polo", "Top", "Dark Green",
     "#1f4d34", "Ralph Lauren", "", 60, 74, ""),
    ("Long Sleeve Polo — Light Green", "Long Sleeve Polo", "Top", "Light Green",
     "#5a8f5f", "Ralph Lauren", "", 60, 74, ""),
    ("Long Sleeve Polo — Cream", "Long Sleeve Polo", "Top", "Cream",
     "#efe6cf", "Ralph Lauren", "", 60, 74, ""),
    ("Long Sleeve Polo — Blue", "Long Sleeve Polo", "Top", "Blue",
     "#3a6ea5", "Ralph Lauren", "", 60, 74, ""),
    ("Quarter Zip — Light Red", "Quarter Zip", "Top", "Light Red",
     "#d1595c", "Ralph Lauren", "", 55, 70, ""),
    ("Long Sleeve Polo Shirt — Dark Wine Red", "Long Sleeve Polo", "Top",
     "Dark Wine Red", "#6e2233", "J.Crew", "", 58, 72, ""),
]

# Names of the four Ralph Lauren long-sleeve polos that belong in "Office".
OFFICE_SHIRT_NAMES = [
    "Long Sleeve Polo — Dark Green",
    "Long Sleeve Polo — Light Green",
    "Long Sleeve Polo — Cream",
    "Long Sleeve Polo — Blue",
]
OFFICE_PANT_NAMES = ["Grey Slacks", "Khaki Slacks"]


def _seed(conn):
    ids = {}
    for row in SEED_ITEMS:
        cur = conn.execute(
            """INSERT INTO items
               (name, category, piece_type, color, color_hex, brand, material,
                temp_min, temp_max, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            row,
        )
        ids[row[0]] = cur.lastrowid

    # "Office" collection: every pants x every RL long-sleeve polo.
    cur = conn.execute(
        "INSERT INTO collections (name, temp_min, temp_max) VALUES (?, ?, ?)",
        ("Office", 65, 73),
    )
    coll_id = cur.lastrowid

    for pant, shirt in product(OFFICE_PANT_NAMES, OFFICE_SHIRT_NAMES):
        pant_id, shirt_id = ids[pant], ids[shirt]
        # Nice readable outfit name, e.g. "Grey Slacks + Dark Green Polo"
        shirt_color = shirt.split("—")[-1].strip()
        pant_short = pant.replace(" Slacks", "")
        oname = f"{pant_short} + {shirt_color}"
        oc = conn.execute(
            "INSERT INTO outfits (name, collection_id) VALUES (?, ?)",
            (oname, coll_id),
        )
        oid = oc.lastrowid
        conn.executemany(
            "INSERT INTO outfit_items (outfit_id, item_id) VALUES (?, ?)",
            [(oid, pant_id), (oid, shirt_id)],
        )

    conn.commit()


# name, icon, temp_min, temp_max
DEFAULT_TEMP_CLASSES = [
    ("Cool", "❄️", 60, 73),
    ("Versatile", "🌤️", 65, 82),
    ("Hot", "🌡️", 74, 89),
]


def _seed_temp_classes(conn):
    conn.executemany(
        "INSERT INTO temp_classes (name, icon, temp_min, temp_max, sort_order) VALUES (?, ?, ?, ?, ?)",
        [(name, icon, lo, hi, i) for i, (name, icon, lo, hi) in enumerate(DEFAULT_TEMP_CLASSES)],
    )
    conn.commit()


DEFAULT_BRANDS = ["Ralph Lauren", "J.Crew"]
DEFAULT_MATERIALS = ["Cotton", "Pima Cotton", "Wool", "Polyester", "Linen"]

# brand, category, note
DEFAULT_PRICE_NOTES = [
    ("Ralph Lauren", "Long Sleeve Polo", "Ralph Lauren Long Sleeve Polos go for $10-15 on average on Depop."),
]


def _seed_brands(conn):
    conn.executemany("INSERT OR IGNORE INTO brands (name) VALUES (?)", [(b,) for b in DEFAULT_BRANDS])
    conn.commit()


def _seed_materials(conn):
    conn.executemany("INSERT OR IGNORE INTO materials (name) VALUES (?)", [(m,) for m in DEFAULT_MATERIALS])
    conn.commit()


def _seed_price_notes(conn):
    conn.executemany(
        "INSERT OR IGNORE INTO price_notes (brand, category, note) VALUES (?, ?, ?)",
        DEFAULT_PRICE_NOTES,
    )
    conn.commit()


# name, piece_type
DEFAULT_CATEGORIES = [
    ("Long Sleeve Polo", "Top"),
    ("Polo", "Top"),
    ("Quarter Zip", "Top"),
    ("Slacks", "Bottom"),
    ("Shorts", "Bottom"),
]

# category -> temp class name, only where we have a confident starting guess.
# Anything else is learned automatically: whenever an item is saved with a
# category and a temp range that matches one of the classes, that pairing is
# remembered here so the next piece of that same style suggests it too.
DEFAULT_CATEGORY_TEMP_DEFAULTS = {
    "Quarter Zip": "Cool",
}


def _seed_categories(conn):
    conn.executemany(
        "INSERT OR IGNORE INTO categories (name, piece_type) VALUES (?, ?)", DEFAULT_CATEGORIES
    )
    conn.commit()


def _seed_category_temp_defaults(conn):
    for category, class_name in DEFAULT_CATEGORY_TEMP_DEFAULTS.items():
        row = conn.execute("SELECT id FROM temp_classes WHERE name = ?", (class_name,)).fetchone()
        if row:
            conn.execute(
                "INSERT OR IGNORE INTO category_temp_defaults (category, temp_class_id) VALUES (?, ?)",
                (category, row["id"]),
            )
    conn.commit()


# --- Item queries --------------------------------------------------------

def list_items():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM items ORDER BY category, name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _learn_category_temp(conn, category, temp_min, temp_max):
    """Remember which temp class goes with a category, so picking that
    category next time can suggest the same temp automatically."""
    if not category or temp_min is None or temp_max is None:
        return
    row = conn.execute(
        "SELECT id FROM temp_classes WHERE temp_min = ? AND temp_max = ?",
        (temp_min, temp_max),
    ).fetchone()
    if row:
        conn.execute(
            """INSERT INTO category_temp_defaults (category, temp_class_id) VALUES (?, ?)
               ON CONFLICT(category) DO UPDATE SET temp_class_id = excluded.temp_class_id""",
            (category, row["id"]),
        )


def _learn_category_brand(conn, category, brand):
    if not category or not brand:
        return
    conn.execute(
        """INSERT INTO category_brand_defaults (category, brand) VALUES (?, ?)
           ON CONFLICT(category) DO UPDATE SET brand = excluded.brand""",
        (category, brand),
    )


def _learn_category_material(conn, category, material):
    if not category or not material:
        return
    conn.execute(
        """INSERT INTO category_material_defaults (category, material) VALUES (?, ?)
           ON CONFLICT(category) DO UPDATE SET material = excluded.material""",
        (category, material),
    )


def _learn_from_item(conn, category, brand, material, temp_min, temp_max):
    _learn_category_temp(conn, category, temp_min, temp_max)
    _learn_category_brand(conn, category, brand)
    _learn_category_material(conn, category, material)


def add_item(data):
    conn = get_conn()
    category = data.get("category", "").strip()
    brand = data.get("brand", "").strip()
    material = data.get("material", "").strip()
    temp_min, temp_max = _int_or_none(data.get("temp_min")), _int_or_none(data.get("temp_max"))
    cur = conn.execute(
        """INSERT INTO items
           (name, category, piece_type, color, color_hex, brand, material,
            image_url, temp_min, temp_max, notes, pending_purchase)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            data.get("name", "").strip(),
            category,
            data.get("piece_type", "").strip(),
            data.get("color", "").strip(),
            data.get("color_hex", "").strip(),
            brand,
            material,
            (data.get("image_url") or "").strip(),
            temp_min,
            temp_max,
            data.get("notes", "").strip(),
            1 if data.get("pending_purchase") else 0,
        ),
    )
    _learn_from_item(conn, category, brand, material, temp_min, temp_max)
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def update_item(item_id, data):
    conn = get_conn()
    category = data.get("category", "").strip()
    brand = data.get("brand", "").strip()
    material = data.get("material", "").strip()
    temp_min, temp_max = _int_or_none(data.get("temp_min")), _int_or_none(data.get("temp_max"))
    conn.execute(
        """UPDATE items SET
             name = ?, category = ?, piece_type = ?, color = ?, color_hex = ?,
             brand = ?, material = ?, image_url = ?, temp_min = ?, temp_max = ?,
             notes = ?, pending_purchase = ?
           WHERE id = ?""",
        (
            data.get("name", "").strip(),
            category,
            data.get("piece_type", "").strip(),
            data.get("color", "").strip(),
            data.get("color_hex", "").strip(),
            brand,
            material,
            (data.get("image_url") or "").strip(),
            temp_min,
            temp_max,
            data.get("notes", "").strip(),
            1 if data.get("pending_purchase") else 0,
            item_id,
        ),
    )
    _learn_from_item(conn, category, brand, material, temp_min, temp_max)
    conn.commit()
    conn.close()


def delete_item(item_id):
    conn = get_conn()
    conn.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()


# --- Collection / outfit queries -----------------------------------------

def list_collections():
    conn = get_conn()
    colls = [dict(r) for r in conn.execute(
        "SELECT * FROM collections ORDER BY sort_order, created_at").fetchall()]
    for c in colls:
        c["outfits"] = _outfits_for_collection(conn, c["id"])
    conn.close()
    return colls


def _outfits_for_collection(conn, coll_id):
    outfits = [dict(r) for r in conn.execute(
        "SELECT * FROM outfits WHERE collection_id = ? ORDER BY id",
        (coll_id,)).fetchall()]
    for o in outfits:
        o["items"] = [dict(r) for r in conn.execute(
            """SELECT i.* FROM items i
               JOIN outfit_items oi ON oi.item_id = i.id
               WHERE oi.outfit_id = ?
               ORDER BY i.category""",
            (o["id"],)).fetchall()]
    return outfits


def add_collection(data):
    conn = get_conn()
    next_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) + 1 AS n FROM collections").fetchone()["n"]
    cur = conn.execute(
        "INSERT INTO collections (name, temp_min, temp_max, notes, sort_order) VALUES (?, ?, ?, ?, ?)",
        (
            data.get("name", "").strip(),
            _int_or_none(data.get("temp_min")),
            _int_or_none(data.get("temp_max")),
            data.get("notes", "").strip(),
            next_order,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def reorder_collections(order):
    """order: list of collection ids in the desired display order."""
    conn = get_conn()
    for idx, coll_id in enumerate(order):
        conn.execute("UPDATE collections SET sort_order = ? WHERE id = ?", (idx, coll_id))
    conn.commit()
    conn.close()


def update_collection(coll_id, data):
    conn = get_conn()
    conn.execute(
        "UPDATE collections SET name = ?, temp_min = ?, temp_max = ?, notes = ? WHERE id = ?",
        (
            data.get("name", "").strip(),
            _int_or_none(data.get("temp_min")),
            _int_or_none(data.get("temp_max")),
            data.get("notes", "").strip(),
            coll_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_collection(coll_id):
    conn = get_conn()
    conn.execute("DELETE FROM collections WHERE id = ?", (coll_id,))
    conn.commit()
    conn.close()


def add_outfit(data):
    """Create an outfit from a list of item ids, optionally in a collection."""
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO outfits (name, collection_id) VALUES (?, ?)",
        (data.get("name", "").strip(), _int_or_none(data.get("collection_id"))),
    )
    oid = cur.lastrowid
    item_ids = data.get("item_ids", []) or []
    conn.executemany(
        "INSERT OR IGNORE INTO outfit_items (outfit_id, item_id) VALUES (?, ?)",
        [(oid, int(i)) for i in item_ids],
    )
    conn.commit()
    conn.close()
    return oid


def delete_outfit(outfit_id):
    conn = get_conn()
    conn.execute("DELETE FROM outfits WHERE id = ?", (outfit_id,))
    conn.commit()
    conn.close()


# --- Temperature classes ---------------------------------------------------

def list_temp_classes():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM temp_classes ORDER BY sort_order, temp_min").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_temp_class(data):
    conn = get_conn()
    max_order = conn.execute(
        "SELECT COALESCE(MAX(sort_order), -1) AS m FROM temp_classes").fetchone()["m"]
    cur = conn.execute(
        "INSERT INTO temp_classes (name, icon, temp_min, temp_max, sort_order) VALUES (?, ?, ?, ?, ?)",
        (
            data.get("name", "").strip() or "Custom",
            (data.get("icon", "").strip() or "🌡️"),
            _int_or_none(data.get("temp_min")) or 0,
            _int_or_none(data.get("temp_max")) or 0,
            max_order + 1,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def delete_temp_class(class_id):
    conn = get_conn()
    conn.execute("DELETE FROM temp_classes WHERE id = ?", (class_id,))
    conn.commit()
    conn.close()


# --- Price notes (by brand + category) -------------------------------------

def list_price_notes():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM price_notes").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def set_price_note(brand, category, note):
    conn = get_conn()
    conn.execute(
        """INSERT INTO price_notes (brand, category, note) VALUES (?, ?, ?)
           ON CONFLICT(brand, category) DO UPDATE SET note = excluded.note""",
        (brand, category, note),
    )
    conn.commit()
    conn.close()


# --- Brands ------------------------------------------------------------

def list_brands():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM brands ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_brand(name):
    conn = get_conn()
    name = (name or "").strip()
    if name:
        conn.execute("INSERT OR IGNORE INTO brands (name) VALUES (?)", (name,))
        conn.commit()
    conn.close()


# --- Categories (styles) ----------------------------------------------

def list_categories():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM categories ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_category(name, piece_type):
    conn = get_conn()
    name = (name or "").strip()
    if name:
        conn.execute(
            "INSERT OR IGNORE INTO categories (name, piece_type) VALUES (?, ?)",
            (name, piece_type if piece_type in ("Top", "Bottom") else "Top"),
        )
        conn.commit()
    conn.close()


def list_category_temp_defaults():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM category_temp_defaults").fetchall()
    conn.close()
    return {r["category"]: r["temp_class_id"] for r in rows}


def list_category_brand_defaults():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM category_brand_defaults").fetchall()
    conn.close()
    return {r["category"]: r["brand"] for r in rows}


def list_category_material_defaults():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM category_material_defaults").fetchall()
    conn.close()
    return {r["category"]: r["material"] for r in rows}


# --- Materials ----------------------------------------------------------

def list_materials():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM materials ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_material(name):
    conn = get_conn()
    name = (name or "").strip()
    if name:
        conn.execute("INSERT OR IGNORE INTO materials (name) VALUES (?)", (name,))
        conn.commit()
    conn.close()


def _int_or_none(v):
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except (ValueError, TypeError):
        return None
