@echo off
REM ============================================================
REM  EVE Trade Ledger - quick launch for testing (no EXE build)
REM  First run: sets up a venv and installs deps (1-2 min, once).
REM  Every run after: starts in a couple of seconds.
REM ============================================================
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [Erststart] Richte Umgebung ein, das dauert einmalig 1-2 Minuten...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo Starte EVE Trade Ledger...
python main.py
