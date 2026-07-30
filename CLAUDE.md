# Wardrobe — Closet & Fit Studio

Solo-user local tool for tracking a personal wardrobe. Flask + vanilla
HTML/CSS/JS — **no build step, no npm install, no React/Tailwind/TypeScript**.
Runs as `python app.py` on **port 5050** (see port note below), opened at
`http://localhost:5050` on the user's own Windows PC. Has its own
Desktop-icon launcher (see below) that opens with **no console window at
all** — same approach as URTO.

**⚠️ Port note:** this app used to default to port 5000, same as the
user's other local app, **URTO** (`mariobengocheare-maker/urto-git`).
Since both are separate Flask dev servers that can be running at once,
sharing a port meant whichever app started first "won" it, so clicking to
open Wardrobe while URTO was already running just showed URTO instead.
Moved Wardrobe to 5050 to fix this. **Do not move it back to 5000** or
reuse any other port URTO (or any future local app like this) might use.

## Current status

Working tree clean; every commit pushed to `origin/claude/wardrobe-v1-code-66xtsm`.
No known open bug. Version shown in the app's own footer — see build order
below for the version-history convention (mirrors URTO's).

Build order, roughly (see `git log` for exact commits):
1. Initial Wardrobe app: items/collections/outfits, Fit Maker temperature-overlap logic.
2. Moved off port 5000 (collided with URTO) to 5050 — see port note above.
3. Replaced `Start Wardrobe.bat` with `launch_desktop.pyw` (no console window at all, mirrors URTO's launcher) + `Create Wardrobe Desktop Icon.vbs`.
4. Added a visible app version + last-updated timestamp, same convention as URTO: `APP_VERSION`/`APP_VERSION_DATE` constants at the top of `app.py`, rendered in a footer at the bottom of the page. **Bump both by hand on every future shipped change**, timestamp in **Eastern time** — current: v1.2.3, updated Jul 30, 2026 5:30 PM EST.
5. Added a one-click **"Wardrobe Updater"** desktop icon (`wardrobe_updater.pyw` + `Create Wardrobe Updater Desktop Icon.vbs`), mirroring URTO's own updater built the same day: double-click it and it downloads the latest branch ZIP, stops any running `app.py` itself (matched on the full path to *this* folder's `app.py`, not just the bare filename — the user's other app, URTO, also has a file called `app.py`, and a name-only match risked killing the wrong one if both were running at once), installs the new files, and cleans up the temp zip/extraction automatically. `wardrobe.db` was never at risk either way — it lives outside the project folder entirely (`%APPDATA%\WardrobeApp\wardrobe.db`), so an update can't reach it regardless. Verified the core download → install logic end-to-end against the real GitHub zip. **Bootstrap note**: since the updater doesn't exist on the user's PC until installed once, that first install still needs the old manual ZIP method — every update after that goes through the icon.

**Known repo quirk (not yet fixed, flagged for a future session):** `node_modules/` (Playwright test tooling, 100+ MB) is currently tracked in git despite being listed in `.gitignore` — almost certainly committed before the ignore rule was added, and `.gitignore` doesn't retroactively untrack already-tracked files. Not a functional problem today (`wardrobe_updater.pyw`'s `NEVER_TOUCH` list explicitly skips `node_modules` on install, so it's harmless), but worth a proper `git rm -r --cached node_modules` cleanup commit at some point to stop shipping it in every ZIP download. Don't remove the `NEVER_TOUCH` entry for `node_modules` without doing that cleanup first, or updates will start overwriting/downloading it again.

## User context (read this first)

- **The user is not a developer.** Give explicit, numbered, Windows-specific
  steps for anything involving files, the command line, or GitHub. Don't
  assume familiarity with terminals or git.
- **Standing rule: no feature should ever require the user to open a console/terminal and paste commands.** One-off tasks get a UI flow (or, like updates, a double-click icon) instead — same rule established on URTO, applies equally here.
- **Update flow: the "Wardrobe Updater" desktop icon, not a manual ZIP** (see build order #5 above). Still give the ZIP download link after every push as a manual fallback, purely in case the updater itself ever needs fixing.
- **The user iterates by screenshot** — treat screenshots of the running app
  as ground truth over assumptions.
- **Always test before claiming done.** Render the app headless and screenshot
  it (Playwright + `/opt/pw-browsers/chromium`) rather than eyeballing code.

## Architecture

- `app.py` — Flask app, all routes (items, collections, outfits). Port 5050 (see port note above).
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
- `launch_desktop.pyw` — Windows double-click entry point. Checks if the server's already up on `127.0.0.1:5050`; if not, spawns `app.py` detached/hidden via `sys.executable` (which is `pythonw.exe` when this `.pyw` itself was launched that way — no console window at any point), waits for it to come up, then opens the browser. Re-launching while already running just opens another browser tab instead of a second server. **Replaced `Start Wardrobe.bat`** (removed) — a `.bat` always runs in a visible terminal window and its `start /min python app.py` still left a real (just-minimized) console around for the server; `.pyw` via `pythonw.exe` has no console at all, for the launcher or the server it spawns. Mirrors URTO's launcher — keep them in sync if the approach changes.
- `Create Wardrobe Desktop Icon.vbs` — one-time setup the user double-clicks to add a "Wardrobe" Desktop shortcut pointing at `launch_desktop.pyw`, with `wardrobe.ico` as its icon. Resolves its own folder via `WScript.ScriptFullName` so it works regardless of where the project folder lives. Re-run it to repoint an old shortcut that still targets the removed `.bat`.
- `wardrobe.ico` — the desktop shortcut's icon. Committed, ships with every update.
- `wardrobe_updater.pyw` — one-click self-updater (see build order #5). Downloads the latest branch ZIP from GitHub, stops any running `app.py` (PowerShell one-liner matched on the full path to *this* folder's `app.py`, never by bare name — the user's other app, URTO, has its own unrelated `app.py`), backs up the current code into `_update_backups/` (capped at 5, oldest pruned), installs the new files, then deletes the temp zip/extraction itself — nothing left to clean up by hand. A small Tkinter status window shows progress and offers a "Launch Wardrobe Now" button when done. Mirrors `urto_updater.pyw` — keep them in sync if the approach changes.
- `Create Wardrobe Updater Desktop Icon.vbs` — one-time setup double-clicked to create the "Wardrobe Updater" Desktop shortcut, mirroring `Create Wardrobe Desktop Icon.vbs`.

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
