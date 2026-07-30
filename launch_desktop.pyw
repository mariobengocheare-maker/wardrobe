"""
Double-click entry point for Wardrobe on Windows — starts the Flask server
silently in the background (no console window at all, since .pyw files run
under pythonw.exe) and opens it in your default browser.

Replaces the old Start Wardrobe.bat, which always ran in a visible terminal
window (that's inherent to .bat files) and started the server via plain
python.exe, which keeps its own console window around too (just minimized).
This launches everything through pythonw.exe instead, so no terminal ever
appears — same approach as URTO's launch_desktop.pyw.

If Wardrobe is already running (e.g. you double-clicked the icon twice, or
a previous session is still up), this just opens the browser tab instead of
starting a second server — UNLESS that running server is on an older
version than the code sitting in this folder (e.g. it was left running from
before an update), in which case it's stopped and restarted so the icon
always opens what's actually on disk, not a stale in-memory copy.
"""

import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
HOST, PORT = "127.0.0.1", 5050
URL = f"http://{HOST}:{PORT}"

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def is_up():
    try:
        with socket.create_connection((HOST, PORT), timeout=0.5):
            return True
    except OSError:
        return False


def local_version():
    try:
        with open(os.path.join(HERE, "app.py"), encoding="utf-8") as f:
            text = f.read()
        m = re.search(r'APP_VERSION\s*=\s*"([^"]+)"', text)
        return m.group(1) if m else None
    except Exception:
        return None


def running_version():
    try:
        with urllib.request.urlopen(f"{URL}/api/version", timeout=1.5) as resp:
            return json.loads(resp.read())["version"]
    except Exception:
        return None  # old server predating /api/version, or a hiccup


def stop_stale_server():
    # Same technique wardrobe_updater.pyw uses: match on the full path to
    # THIS folder's app.py, never by bare name — URTO has its own unrelated
    # app.py, and a name-only match risked killing that instead if both
    # happen to be running at once.
    target = os.path.join(HERE, "app.py").replace("'", "''")
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
        pass
    for _ in range(20):
        if not is_up():
            break
        time.sleep(0.25)


def start_server():
    # sys.executable here is pythonw.exe (since this .pyw was launched that
    # way), so the spawned app.py inherits the same "no console window"
    # behavior. DETACHED_PROCESS + CREATE_NO_WINDOW keep it running after
    # this launcher script exits, with no window ever appearing.
    creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | NO_WINDOW
    subprocess.Popen(
        [sys.executable, os.path.join(HERE, "app.py")],
        cwd=HERE,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )


def wait_until_up():
    for _ in range(30):
        if is_up():
            return
        time.sleep(0.5)


def main():
    if is_up():
        running, local = running_version(), local_version()
        if running is not None and local is not None and running != local:
            stop_stale_server()
            start_server()
            wait_until_up()
    else:
        start_server()
        wait_until_up()
    webbrowser.open(URL)


if __name__ == "__main__":
    main()
