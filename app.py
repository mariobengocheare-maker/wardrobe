"""Wardrobe tracker — Flask backend.

Run with:  python app.py
Then open: http://localhost:5050
"""

from flask import Flask, jsonify, render_template, request

import db
import imageproc

app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


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
    app.run(host="127.0.0.1", port=5050, debug=True)
