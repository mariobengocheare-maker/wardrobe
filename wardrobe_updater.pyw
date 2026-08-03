"""
Wardrobe Updater — one-click self-update, no console/commands needed.

Double-click the "Wardrobe Updater" desktop icon (created once via
"Create Wardrobe Updater Desktop Icon.vbs") to download the latest
Wardrobe from GitHub, install it over this folder, and clean up after
itself:
  - stops Wardrobe if it's currently running (no more hunting it down in
    Task Manager first)
  - downloads + installs the new files
  - deletes the downloaded zip and extracted folder automatically —
    nothing left to Ctrl+A/Ctrl+V by hand or clean up yourself
  - never touches your real wardrobe data — `wardrobe.db` lives outside
    this folder entirely (%APPDATA%\\WardrobeApp\\wardrobe.db), so an
    update can never come near it, by design

Safe to re-run any time. If the download or install fails partway,
nothing gets overwritten and you're left exactly where you started.

Mirrors urto_updater.pyw (URTO's own one-click updater) — keep them in
sync if the approach ever changes.
"""

import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path

REPO_ZIP_URL = "https://codeload.github.com/mariobengocheare-maker/wardrobe/zip/refs/heads/claude/wardrobe-v1-code-66xtsm"
INSTALL_DIR = Path(__file__).resolve().parent
BACKUP_ROOT = INSTALL_DIR / "_update_backups"
MAX_BACKUPS = 5

# Nothing in this project folder actually holds real user data — wardrobe.db
# lives outside it entirely (see db.py) — but node_modules/package-lock.json
# are local dev-only clutter that isn't part of the repo anyway (gitignored,
# never in the downloaded zip), so there's nothing to overwrite there either
# way. Kept as an explicit list for the same belt-and-suspenders reason
# URTO's updater has one.
NEVER_TOUCH = {"_update_backups", "node_modules"}

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def kill_running_app(log):
    """Stops any already-running `app.py` from THIS folder so its files
    aren't locked when we overwrite them — no manual Task Manager step.
    Matched on the full path to this folder's app.py, not just the bare
    filename — Mario also runs URTO, which has its own unrelated app.py,
    and a name-only match would risk killing that instead if both happen
    to be running at once."""
    log("Stopping Wardrobe if it's currently running...")
    target = str(INSTALL_DIR / "app.py").replace("'", "''")
    ps_cmd = (
        f"Get-CimInstance Win32_Process | "
        f"Where-Object {{ $_.CommandLine -like '*{target}*' }} | "
        f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            capture_output=True, timeout=15, creationflags=NO_WINDOW,
        )
    except Exception:
        pass  # best-effort — if nothing was running, this is a harmless no-op
    time.sleep(1)


def backup_current_install(log):
    """Copies the current code aside before overwriting, as a rollback
    safety net — capped at MAX_BACKUPS."""
    log("Backing up current version...")
    BACKUP_ROOT.mkdir(exist_ok=True)
    dest = BACKUP_ROOT / time.strftime("%Y%m%d_%H%M%S")
    dest.mkdir()
    for item in INSTALL_DIR.iterdir():
        if item.name in NEVER_TOUCH or item.name.startswith("."):
            continue
        try:
            if item.is_dir():
                shutil.copytree(item, dest / item.name)
            else:
                shutil.copy2(item, dest / item.name)
        except Exception:
            pass  # best-effort backup; never let this block the real update
    for old in sorted(BACKUP_ROOT.iterdir())[:-MAX_BACKUPS]:
        shutil.rmtree(old, ignore_errors=True)


def download_and_extract(log, tmp_dir: Path) -> Path:
    log("Downloading the latest version...")
    zip_path = tmp_dir / "update.zip"
    urllib.request.urlretrieve(REPO_ZIP_URL, zip_path)

    log("Checking the download...")
    with zipfile.ZipFile(zip_path) as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"Downloaded file looks corrupted ({bad}). Try again.")
        extract_dir = tmp_dir / "extracted"
        zf.extractall(extract_dir)

    # The zip always contains exactly one top-level folder, e.g.
    # "wardrobe-claude-wardrobe-v1-code-66xtsm".
    subdirs = [p for p in extract_dir.iterdir() if p.is_dir()]
    if len(subdirs) != 1:
        raise RuntimeError("Unexpected download structure — nothing was changed.")
    return subdirs[0]


def install_update(log, source_dir: Path):
    log("Installing new files...")
    for item in source_dir.iterdir():
        if item.name in NEVER_TOUCH:
            continue
        dest = INSTALL_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, dest, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest)


def record_install_time(log):
    # Written fresh on every successful update with THIS PC's own clock —
    # app.py's version footer reads it back instead of a hand-typed
    # timestamp, which used to drift out of sync with reality.
    try:
        (INSTALL_DIR / "install_time.txt").write_text(datetime.now().isoformat(), encoding="utf-8")
    except Exception:
        pass  # footer just falls back to app.py's own file time; never block the update over this


def install_requirements(log):
    # Best-effort: only matters if a future version adds a new dependency.
    # Never blocks the update if pip isn't reachable or errors out.
    req = INSTALL_DIR / "requirements.txt"
    if not req.exists():
        return
    log("Checking dependencies...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-q", "-r", str(req)],
            capture_output=True, timeout=120, creationflags=NO_WINDOW,
        )
    except Exception:
        pass


def run_update(log) -> bool:
    try:
        kill_running_app(log)
        backup_current_install(log)
        with tempfile.TemporaryDirectory(prefix="wardrobe_update_") as tmp:
            source_dir = download_and_extract(log, Path(tmp))
            install_update(log, source_dir)
        # TemporaryDirectory cleans up the zip/extracted files on exit —
        # nothing left behind to manage by hand.
        record_install_time(log)
        install_requirements(log)
        log("")
        log("Done! Wardrobe is up to date.")
        return True
    except Exception as e:
        log("")
        log(f"Update failed: {e}")
        log("Nothing was changed — you're still on your previous version.")
        return False


def launch_wardrobe():
    # This updater itself runs under pythonw.exe (a .pyw double-click), so
    # sys.executable here already IS pythonw — same no-console launch
    # launch_desktop.pyw already knows how to do (including "already running").
    subprocess.Popen([sys.executable, str(INSTALL_DIR / "launch_desktop.pyw")], cwd=str(INSTALL_DIR))


def main():
    root = tk.Tk()
    root.title("Wardrobe Updater")
    root.geometry("540x380")
    root.configure(bg="#1c1813")

    tk.Label(root, text="Wardrobe Updater", font=("Segoe UI", 16, "bold"),
              fg="#a8863f", bg="#1c1813").pack(pady=(16, 4))

    text = tk.Text(root, height=14, width=64, bg="#211b12", fg="#f4ecd9",
                   insertbackground="#f4ecd9", relief="flat", state="disabled")
    text.pack(padx=16, pady=8)

    def log(msg):
        text.configure(state="normal")
        text.insert("end", msg + "\n")
        text.see("end")
        text.configure(state="disabled")
        text.update()

    btn_frame = tk.Frame(root, bg="#1c1813")
    btn_frame.pack(pady=(4, 16))

    launch_btn = tk.Button(btn_frame, text="Launch Wardrobe Now", state="disabled",
                            command=lambda: (launch_wardrobe(), root.destroy()))
    launch_btn.grid(row=0, column=0, padx=6)
    tk.Button(btn_frame, text="Close", command=root.destroy).grid(row=0, column=1, padx=6)

    def worker():
        ok = run_update(log)
        if ok:
            launch_btn.configure(state="normal")

    log("Starting update...")
    threading.Thread(target=worker, daemon=True).start()
    root.mainloop()


if __name__ == "__main__":
    main()
