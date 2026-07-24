@echo off
cd /d "%~dp0"
start "Wardrobe Server" /min python app.py

rem Wait for the server to actually answer on its own port (up to ~15s)
rem instead of guessing a fixed delay - a fixed sleep either opens the
rem browser too early on a slow PC, or (the bug this replaced) opens it
rem regardless of whether OUR server actually started, which showed
rem whatever else was already running on a shared port instead of Wardrobe.
set tries=0
:waitloop
powershell -NoProfile -Command "try { (New-Object Net.Sockets.TcpClient).Connect('127.0.0.1',5050); exit 0 } catch { exit 1 }" >nul 2>&1
if %errorlevel%==0 goto ready
set /a tries+=1
if %tries% GEQ 30 goto ready
timeout /t 1 /nobreak >nul
goto waitloop

:ready
start "" "http://localhost:5050"
exit
