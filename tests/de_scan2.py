"""Zweitsuche nach deutschen Anzeigetexten - AST-basiert, als Ergaenzung zu
de_scan.py.

WARUM ES DAS GIBT (Sitzung 16): de_scan.py prueft nur direkte Qt-Aufrufe
(setText, setToolTip, QMessageBox ...). Als er auf 0 stand, fand eine
AST-Suche noch ~420 Kandidaten: Datenlisten (die Lade-Tipps), Dicts fuer
_set_header_tips({...}), Trend-Bezeichner, Kategorie-Beschreibungen. Alles
sichtbar, nichts davon ein Qt-Aufruf.

WAS GEZAEHLT WIRD: jede String-Konstante in den UI-Modulen, die NICHT als
Argument von t()/_txt()/_txtf() steht, kein Docstring ist, nicht in einen
Log-/Format-/Stil-Aufruf geht, und entweder einen Umlaut oder mindestens
zwei deutsche Funktionswoerter enthaelt.

DAS IST EINE HEURISTIK. Sie findet auch Fehltreffer (SDE-Gruppennamen,
Kommentare in Strings). Aber sie ist eine bessere Untergrenze als de_scan.py.

AUFRUF:  python de_scan2.py            -> Zaehlung je Datei + Fundstellen
         python de_scan2.py --kurz     -> nur die Zaehlung
"""
import ast
import os as _os_wurzel
_os_wurzel.chdir(_os_wurzel.path.dirname(_os_wurzel.path.dirname(_os_wurzel.path.abspath(__file__))))   # Projektwurzel (tests\ -> ..)
import glob
import re
import sys
from collections import Counter

# WORTLISTE BEWUSST GROSSZUEGIG (Sitzung 16): eine zu kleine Liste laesst
# Texte durch, und ein Scanner, der 0 meldet, sieht aus wie ein Beweis.
# "Items aus dem Portfolio" hatte mit der alten Liste nur EINEN Treffer
# ("aus") und fiel unter die Schwelle von zwei.
WOERTER = re.compile(
    r"\b(der|die|das|und|nicht|f\u00fcr|mit|von|wird|werden|bitte|keine?|"
    r"zuerst|oder|beim|dieser|diese|noch|schon|nur|auch|wenn|dann|erst|kein|"
    r"sind|ist|wurde|kann|soll|muss|zum|zur|im|am|aus|an|ein|eine|einen|"
    r"sich|sie|wir|du|dein|deine|dass|sonst|dort|hier|jetzt|immer|nie|"
    r"hat|haben|dem|den|des|als|bei|nach|vor|\u00fcber|unter|ohne|gegen|"
    r"durch|um|damit|weil|aber|sondern|schlecht|gut|mehr|weniger|alle|"
    r"alles|jede|jeder|jedes|man|es|liegt|steht|gibt|geht|macht|zeigt)\b",
    re.I)
UML = re.compile(r"[\u00e4\u00f6\u00fc\u00df\u00c4\u00d6\u00dc]")
UEBERSETZER = ("t", "_txt", "_txtf")
IGNORIER_AUFRUFE = {
    "_log_exception", "_log_step", "log", "warning", "info", "debug", "error",
    "exception", "print", "setObjectName", "setStyleSheet", "setProperty",
    "get", "setdefault", "startswith", "endswith", "replace", "split", "join",
    "format", "strftime", "encode", "decode", "compile", "match", "search",
    "sub", "findall", "setWhatsThis", "setAccessibleName"}
# "%" IST RAUS (Sitzung 16): "% \u00fcber Normal" ist ein Spaltenname, kein
# Format-String. Wer CSS-Prozente ausschliessen will, nimmt den Marker.
PRAEFIX_IGNORIEREN = ("Q", "color:", "font", "background", "border",
                      "padding", "margin", "{", "<", "http", "esi-",
                      "#", "rgb", "qproperty")


AUS_MARKER = "# de_scan2: aus"
AN_MARKER = "# de_scan2: an"


def _ausgeblendet(src):
    """Zeilennummern zwischen `# de_scan2: aus` und `# de_scan2: an`.

    WOFUER: deutsche DICT-SCHLUESSEL, die nie angezeigt werden (z. B. die
    (Schluessel, Beschriftung)-Paare der Kosten-Aufschluesselung). Sie
    sind keine Uebersetzungsluecke, wuerden aber die Ratsche (aa271) auf
    einem falschen Sockel festhalten. Der Marker ist AUSDRUECKLICH und
    steht neben der Stelle - wer ihn setzt, sagt damit: das sieht niemand.
    """
    aus, zeilen = False, set()
    for nr, zeile in enumerate(src.splitlines(), 1):
        if AUS_MARKER in zeile:
            aus = True
        elif AN_MARKER in zeile:
            aus = False
        elif aus:
            zeilen.add(nr)
    return zeilen


def scanne(pfad):
    src = open(pfad, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    versteckt = _ausgeblendet(src)
    ok, weg = set(), set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            name = (n.func.id if isinstance(n.func, ast.Name)
                    else n.func.attr if isinstance(n.func, ast.Attribute)
                    else None)
            if name in UEBERSETZER:
                for a in n.args:
                    if isinstance(a, ast.Constant):
                        ok.add(id(a))
                    if isinstance(a, ast.JoinedStr):
                        for v in a.values:
                            if isinstance(v, ast.Constant):
                                ok.add(id(v))
            elif name in IGNORIER_AUFRUFE:
                for a in n.args:
                    if isinstance(a, ast.Constant):
                        weg.add(id(a))
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant):
            weg.add(id(n.value))            # Docstring / nackter String
    raus = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
            continue
        if id(n) in ok or id(n) in weg or n.lineno in versteckt:
            continue
        s = n.value
        # MINDESTLAENGE 3, NICHT 8 (Sitzung 16, nach einer Gegenzaehlung des
        # Nutzers: "wie viele deutsche Texte gibt's noch?"). Mit 8 fielen
        # "Huellen", "Spaeter", "\u00f7 Stueck" durch das Raster - der Scanner
        # meldete 0, obwohl ~20 sichtbare deutsche Texte dastanden. Eine
        # Untergrenze, die zu hoch liegt, ist schlimmer als keine: sie sieht
        # aus wie ein Beweis.
        if len(s) < 3 or s.lstrip().startswith(PRAEFIX_IGNORIEREN):
            continue
        if UML.search(s) or len(WOERTER.findall(s)) >= 2:
            raus.append((n.lineno, s[:80].replace("\n", " ")))
    return raus


def main():
    kurz = "--kurz" in sys.argv
    dateien = sorted(glob.glob("eve_trader/ui/*.py")) + ["eve_trader/__main__.py"]
    gesamt = 0
    for f in dateien:
        treffer = scanne(f)
        gesamt += len(treffer)
        print(f"== {f}: {len(treffer)}")
        if not kurz:
            for ln, s in treffer:
                print(f"   {ln:>6}  {s}")
    print(f"GESAMT {gesamt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
