# Wardrobe — Closet & Fit Studio

A local, single-user app to track your wardrobe, build looks with the
**Fit Maker**, and save **Collections** of outfits. Flask + vanilla
HTML/CSS/JS — no build step, no npm, no framework.

## Run it (Windows)

**Desktop shortcut (recommended for everyday use):** double-click
`Create Wardrobe Desktop Icon.vbs` once — it adds a "Wardrobe" icon to
your Desktop. From then on, just double-click that icon: it starts the
app with **no console window at all** and opens it in your browser
automatically. If you already have an older "Wardrobe" icon that opens a
black terminal window first, double-click the `.vbs` again to switch it
over to the instant version.

**Manual:**

1. Install Python 3 from python.org if you don't have it (check "Add
   Python to PATH" during install).
2. Open the folder in File Explorer, click the address bar, type `cmd`,
   and press Enter — a black command window opens in this folder.
3. First time only, install Flask:
   ```
   pip install -r requirements.txt
   ```
4. Start the app:
   ```
   python app.py
   ```
5. Open your browser to: http://localhost:5050

The first run creates `wardrobe.db` and seeds your starting wardrobe plus
the **Office** collection. All your data lives in that one file, on your
PC only — it's never uploaded to GitHub.

## What's inside

- **Wardrobe** — add / edit / remove pieces. Every piece can carry a
  brand, color, material, and an ideal temperature range (°F).
- **Fit Maker** — tap pieces to build a look; see them together and get an
  overlapping temperature rating for the whole fit. Save it as an outfit.
- **Collections** — group outfits, each with its own temperature rating.
  The **Office** collection ships with every combination of the slacks
  (grey, khaki) and the Ralph Lauren long-sleeve polos, rated 65–73°F.
