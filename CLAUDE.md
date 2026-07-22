# Wardrobe — Closet & Fit Studio

Solo-user local tool for tracking a personal wardrobe. Flask + vanilla
HTML/CSS/JS — **no build step, no npm install, no React/Tailwind/TypeScript**.
Runs as `python app.py`, opened at `http://localhost:5000` on the user's own
Windows PC.

## User context (read this first)

- **The user is not a developer.** Give explicit, numbered, Windows-specific
  steps for anything involving files, the command line, or GitHub. Don't
  assume familiarity with terminals or git.
- **Preferred update flow: ZIP download, not `git pull`.** Download the repo
  ZIP from GitHub → extract → replace files in the project folder → rerun
  `python app.py`. Offer the GitHub link after every push.
- **The user iterates by screenshot** — treat screenshots of the running app
  as ground truth over assumptions.
- **Always test before claiming done.** Render the app headless and screenshot
  it (Playwright + `/opt/pw-browsers/chromium`) rather than eyeballing code.

## Architecture

- `app.py` — Flask app, all routes (items, collections, outfits). Port 5000.
- `db.py` — SQLite data layer. Auto-creates the schema and, on first run only
  (empty DB), seeds the starting wardrobe and the "Office" collection.
- `templates/index.html` — the entire frontend. One file, three tabs:
  **Wardrobe**, **Fit Maker**, **Collections**. Vanilla JS, no framework.
- `wardrobe.db` — SQLite DB, **gitignored**, and lives OUTSIDE the project
  folder (in `%APPDATA%\WardrobeApp\wardrobe.db`, resolved in `db.py`) —
  never commit it. This is deliberate: the user re-downloads the app as a
  fresh ZIP into a new folder for every update, and a fixed, code-independent
  location means every item, photo, and collection survives that
  automatically. Don't move the DB back inside the project folder.
- `static/theme.mp3` — home-page theme song, **committed** (not gitignored).
  The user uploaded this once and never wants to re-upload it, so it ships
  with the repo like any other asset.

## Features (all working, verified)

1. **Wardrobe** — add / edit / remove pieces. Each piece: name, category,
   color (+ swatch hex), brand, material, ideal temperature range (°F), notes.
2. **Fit Maker** — tap pieces to build a look; shows the selected pieces
   together and computes the fit's shared temperature range as the *overlap*
   of the pieces' ranges (highest low → lowest high). Save a look as an outfit,
   optionally straight into a collection.
3. **Collections** — named groups of outfits, each with its own temperature
   rating. Deleting a collection cascades to its outfits; deleting an item
   cascades out of any outfits it was in (SQLite `ON DELETE CASCADE`,
   `PRAGMA foreign_keys = ON` in `db.py`).

## Data model

`items`, `collections`, `outfits`, `outfit_items` (join). An outfit belongs to
at most one collection (`outfits.collection_id`, nullable) and links any number
of items through `outfit_items`. The seeded "Office" collection is every
combination of the two slacks × the four Ralph Lauren long-sleeve polos
(8 outfits), rated 65–73°F.

## Don't do this

- Don't introduce React/Tailwind/shadcn/TypeScript or any build step — the
  whole point is that the user can download a ZIP, replace files, and rerun.
  Keep it single-file-vanilla + Flask.
- Don't commit `wardrobe.db` — it holds real personal data and is gitignored.
- Don't fetch frontend deps from a CDN if this runs in the Claude sandbox
  (CDNs are blocked there); vendor from `registry.npmjs.org` tarballs instead.
