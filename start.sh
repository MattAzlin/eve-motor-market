#!/bin/bash
# SITZUNGSSTART in EINEM Befehl:  bash start.sh
# Installiert die Abhaengigkeiten und faehrt die Pflicht-Pruefungen.
# SOLL-Ergebnis steht am Ende - weicht etwas ab, ERST das klaeren, dann bauen.
# (Eingerichtet in Sitzung 7, Zahlen zuletzt GEMESSEN am 17.09.2026.)
set -u
cd "$(dirname "$0")"

echo "== 1/6 Abhaengigkeiten =="
python3 -c "import PySide6, pyflakes" 2>/dev/null || \
    pip install --break-system-packages --quiet -r requirements.txt pyflakes

echo "== 2/6 aa-Suite (SOLL 3941/3941) =="
timeout 280 python3 test_bestand_herkunft.py | tail -3

echo "== 3/6 b-Suite (SOLL 1307/1307, endet nach wenigen Sekunden) =="
QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD" timeout 120 \
    python3 test_bauplan_aufbau.py 2>/dev/null | tail -1

echo "== 4/6 Lint (SOLL 0 Befunde) =="
python3 lint_order.py $(find eve_trader -name "*.py") main.py | tail -1

echo "== 5/6 pyflakes (SOLL keine 'undefined name') =="
python3 -m pyflakes eve_trader/ main.py | grep -c "undefined name"

echo "== 6/6 Rotprobe-Anwendbarkeit (SOLL 1006/1006) =="
python3 rotprobe.py --check

echo ""
echo "SOLL: aa 3941 | b 1307 | Lint 0 | pyflakes 0 | Mutationen 1006/1006 anwendbar."
echo "      de_scan 0 | de_scan2 0 | de_scan3 0 | de_scan4 0 | de_scan5 0 | de_scan6 0."
echo "Vor jeder Veroeffentlichung beim Nutzer: python pruefe.py"
echo ""
echo "PRUEFEN IN BLOECKEN (Nutzer, Sitzung 17): Aenderungen sammeln, am Ende"
echo "des Blocks pruefen. Zwischendurch hoechstens die aa-Suite; b-Suite nur"
echo "bei Oberflaechen-Aenderungen. Neue Mutationen gebuendelt fahren:"
echo "    python3 rotprobe.py <von> <bis>       # ~25 s je Mutation im Container"
echo "Ein Werkzeug-Aufruf bricht nach 300 s ab - also Bloecke von ~10."
echo "AUSNAHME: alles, was Material oder ISK kosten kann, sofort pruefen."
