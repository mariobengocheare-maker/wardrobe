"""Wardrobe tracker — Flask backend.

Run with:  python app.py
Then open: http://localhost:5050
"""

import os
import threading
import time

from flask import Flask, jsonify, render_template, request

import db
import imageproc

app = Flask(__name__)

# The desktop launcher starts this server detached, with no window — so
# nothing closes it automatically when you're done. The frontend pings
# /api/heartbeat every few seconds while a tab is open and fires
# /api/shutdown the instant one closes; the watchdog thread below is the
# fallback for anything that skips that (a crash, force-closing the
# browser, the PC sleeping) — if no heartbeat arrives for a while, it shuts
# the server down on its own so nothing lingers in Task Manager.
_last_heartbeat = {"t": None}
HEARTBEAT_TIMEOUT = 20


@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    _last_heartbeat["t"] = time.time()
    return jsonify({"ok": True})


@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    threading.Timer(0.2, lambda: os._exit(0)).start()
    return jsonify({"ok": True})


def _watchdog():
    while True:
        time.sleep(5)
        t = _last_heartbeat["t"]
        if t is not None and (time.time() - t) > HEARTBEAT_TIMEOUT:
            os._exit(0)


# Bump these two together whenever a change is shipped, so it's obvious at
# a glance which build is running. Always give the timestamp in Eastern
# time (matches the same convention URTO's own version footer uses).
APP_VERSION = "1.2.3"
APP_VERSION_DATE = "Jul 30, 2026 5:30 PM EST"


@app.route("/")
def index():
    return render_template("index.html", app_version=APP_VERSION, app_version_date=APP_VERSION_DATE)


# --- Image standardisation ----------------------------------------------

@app.route("/api/process-image", methods=["POST"])
def process_image():
    """Knock out the background and fit the photo to a standard canvas."""
    data = request.get_json(force=True)
    src = data.get("image", "")
    remove_bg = data.get("remove_bg", True)
    try:
        out = imageproc.standardize(src, remove_bg=remove_bg)
        return jsonify({"image": out, "ok": True})
    except Exception as exc:  # never block a save on a bad photo
        return jsonify({"image": src, "ok": False, "error": str(exc)})


# --- Items ---------------------------------------------------------------

@app.route("/api/items", methods=["GET"])
def get_items():
    return jsonify(db.list_items())


@app.route("/api/items", methods=["POST"])
def create_item():
    new_id = db.add_item(request.get_json(force=True))
    return jsonify({"id": new_id}), 201


@app.route("/api/items/<int:item_id>", methods=["PUT"])
def edit_item(item_id):
    db.update_item(item_id, request.get_json(force=True))
    return jsonify({"ok": True})


@app.route("/api/items/<int:item_id>", methods=["DELETE"])
def remove_item(item_id):
    db.delete_item(item_id)
    return jsonify({"ok": True})


# --- Temperature classes --------------------------------------------------

@app.route("/api/temp-classes", methods=["GET"])
def get_temp_classes():
    return jsonify(db.list_temp_classes())


@app.route("/api/temp-classes", methods=["POST"])
def create_temp_class():
    new_id = db.add_temp_class(request.get_json(force=True))
    return jsonify({"id": new_id}), 201


@app.route("/api/temp-classes/<int:class_id>", methods=["DELETE"])
def remove_temp_class(class_id):
    db.delete_temp_class(class_id)
    return jsonify({"ok": True})


# --- Price notes (by brand + category) ------------------------------------

@app.route("/api/price-notes", methods=["GET"])
def get_price_notes():
    return jsonify(db.list_price_notes())


@app.route("/api/price-notes", methods=["POST"])
def save_price_note():
    data = request.get_json(force=True)
    db.set_price_note(
        data.get("brand", "").strip(), data.get("category", "").strip(), data.get("note", "").strip()
    )
    return jsonify({"ok": True})


# --- Brands ----------------------------------------------------------------

@app.route("/api/brands", methods=["GET"])
def get_brands():
    return jsonify(db.list_brands())


@app.route("/api/brands", methods=["POST"])
def create_brand():
    data = request.get_json(force=True)
    db.add_brand(data.get("name", ""))
    return jsonify({"ok": True})


# --- Categories (styles) ----------------------------------------------

@app.route("/api/categories", methods=["GET"])
def get_categories():
    return jsonify(db.list_categories())


@app.route("/api/categories", methods=["POST"])
def create_category():
    data = request.get_json(force=True)
    db.add_category(data.get("name", ""), data.get("piece_type", "Top"))
    return jsonify({"ok": True})


@app.route("/api/category-temp-defaults", methods=["GET"])
def get_category_temp_defaults():
    return jsonify(db.list_category_temp_defaults())


@app.route("/api/category-brand-defaults", methods=["GET"])
def get_category_brand_defaults():
    return jsonify(db.list_category_brand_defaults())


@app.route("/api/category-material-defaults", methods=["GET"])
def get_category_material_defaults():
    return jsonify(db.list_category_material_defaults())


# --- Materials ---------------------------------------------------------

@app.route("/api/materials", methods=["GET"])
def get_materials():
    return jsonify(db.list_materials())


@app.route("/api/materials", methods=["POST"])
def create_material():
    data = request.get_json(force=True)
    db.add_material(data.get("name", ""))
    return jsonify({"ok": True})


# --- Collections ---------------------------------------------------------

@app.route("/api/collections", methods=["GET"])
def get_collections():
    return jsonify(db.list_collections())


@app.route("/api/collections", methods=["POST"])
def create_collection():
    new_id = db.add_collection(request.get_json(force=True))
    return jsonify({"id": new_id}), 201


@app.route("/api/collections/<int:coll_id>", methods=["PUT"])
def edit_collection(coll_id):
    db.update_collection(coll_id, request.get_json(force=True))
    return jsonify({"ok": True})


@app.route("/api/collections/<int:coll_id>", methods=["DELETE"])
def remove_collection(coll_id):
    db.delete_collection(coll_id)
    return jsonify({"ok": True})


# --- Outfits -------------------------------------------------------------

@app.route("/api/outfits", methods=["POST"])
def create_outfit():
    new_id = db.add_outfit(request.get_json(force=True))
    return jsonify({"id": new_id}), 201


@app.route("/api/outfits/<int:outfit_id>", methods=["DELETE"])
def remove_outfit(outfit_id):
    db.delete_outfit(outfit_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    db.init_db()
    threading.Thread(target=_watchdog, daemon=True).start()
    # use_reloader=False: with it on, Flask's debug reloader runs a second
    # "monitor" process that doesn't serve requests but would run its own
    # copy of the watchdog above with no heartbeats ever reaching it — it'd
    # shut itself down on a timer regardless of whether you're using the
    # app, taking the real server with it. Not needed anyway: the desktop
    # launcher always starts this fresh from freshly-downloaded files.
    app.run(host="127.0.0.1", port=5050, debug=True, use_reloader=False)
