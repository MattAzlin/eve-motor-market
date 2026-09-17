"""Findet deutschen Anzeigetext ausserhalb von t() - VOKABULAR AUS DEM KATALOG.

WARUM ES DIESEN FUENFTEN SCANNER GIBT (Sitzung 22):
Der Nutzer meldete zwei deutsche Texte auf der englischen Oberflaeche
("% Erfolg" und "bei N parallel", beide in mw_bauplan_tabs.py). Alle vier
bestehenden Scanner meldeten dabei GESAMT 0. Die Nachschau fand nicht zwei
Stellen, sondern rund fuenfzig - darunter jedes "kopiert ✓", "Bester
Gewinn:", "Baukosten gesamt" und "Materialkosten (…% ME)".

DIE ZWEI LUECKEN, die das erklaeren:
  1. de_scan und de_scan3 folgen einem Text bis zu einem ANZEIGE-Aufruf.
     Texte, die ueber einen eigenen Helfer laufen - `_flash_tip(...)`,
     `parts.append(...)`, `addItem(_dv_label(...))` - erreichen sie nie.
  2. de_scan4 fragt "sieht das deutsch aus?" gegen eine HANDGEPFLEGTE
     Wortliste. "Erfolg", "kopiert", "Baukosten", "Materialkosten" und
     "bei" standen nicht drin. Eine Liste, die jemand pflegen muss, ist
     genau so vollstaendig wie die letzte Sitzung, in der jemand daran
     gedacht hat.

DIESER HIER PFLEGT SEIN VOKABULAR SELBST. Es ist der KATALOG:
alle Woerter aus den deutschen Uebersetzungen, MINUS alle Woerter aus den
englischen Schluesseln. Was uebrig bleibt, ist ein Wort, das in dieser
Anwendung nur auf Deutsch vorkommt - steht es im Quelltext ausserhalb von
t(), ist es ein vergessenes t(). Wer einen deutschen Text ergaenzt,
erweitert damit automatisch auch das Vokabular des Scanners.

NICHT GEMELDET (sonst schlaegt er Alarm, wo nichts ist):
  * was durch t()/_txt()/_txtf() laeuft,
  * Docstrings und nackte Zeichenketten-Anweisungen,
  * sprache.py (dort steht der Katalog selbst),
  * Zeichenketten in SCHLUESSEL-STELLUNG (dict-Schluessel, `x["..."]`,
    `.get("...")`) und alles mit Unterstrich - das adressiert Daten,
    es steht nicht auf dem Schirm,
  * ein einzelnes KLEINGESCHRIEBENES Wort ohne Leerzeichen ringsum
    ("spanne", "manuell", "mond"): in diesem Projekt sind das interne
    Werte. ACHTUNG, die Abgrenzung ist knapp: "bei " mit Leerzeichen ist
    ein Anzeigetext und wird gemeldet, "bei" allein nicht,
  * SQL-Anweisungen (ALTER TABLE …; "Alter" ist deutsch, ALTER nicht),
  * Argumente von `_log_exception` (die landen in fehler.log, nicht auf
    dem Schirm - nachgesehen in main_window.py),
  * Platzhalternamen und Markup: "{tief}" und "<path fill=…>" sind Code,
  * Bereiche zwischen `# de_scan5: aus` und `# de_scan5: an` (auch die
    Marker von de_scan2/3/4 gelten). Jeder Marker braucht eine
    Begruendung daneben.

AUFRUF:  python de_scan5.py            -> Fundstellen je Datei
         python de_scan5.py --kurz     -> nur die Zaehlung
"""
import ast
import glob
import os
import re
import sys

WORT = re.compile(r"[A-Za-zÄÖÜäöüß]{3,}")
PLATZHALTER = re.compile(r"\{[^{}]*\}")
MARKUP = re.compile(r"<[^<>]*>")
SQL = re.compile(r"^\s*(select|insert|update|delete|alter|create|drop|pragma|"
                 r"with|replace|begin|commit|attach|vacuum|index)\b", re.I)
# Ein einzelnes kleingeschriebenes Wort OHNE Leerzeichen ringsum - in
# diesem Projekt ein interner Wert ("spanne", "manuell", "bauplan"), kein
# Anzeigetext. Anzeigetexte tragen fast immer ein Leerzeichen, eine
# Satzzeichen-Umgebung oder einen Grossbuchstaben.
INTERNER_WERT = re.compile(r"^[a-zäöüß][a-z0-9äöüß.\-]*$")
UEBERSETZER = {"t", "_txt", "_txtf"}
# Schreibt NUR in fehler.log (nachgesehen: main_window._log_exception).
NUR_PROTOKOLL = {"_log_exception"}
# Erstes Argument dieser Aufrufe ist ein SCHLUESSEL, kein Text.
SCHLUESSEL_RUFE = {"get", "setdefault", "pop"}


def _nur_deutsche_woerter():
    """Woerter, die in dieser Anwendung nur auf DEUTSCH vorkommen.

    Aus dem Katalog, nicht aus einer Handliste: deutsche Uebersetzungen
    liefern die Kandidaten, die englischen Schluessel ziehen alles ab, was
    auch englisch ist ("Portfolio", "Standard", "Total", "parallel")."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from eve_trader.sprache import KATALOG
    deutsch, englisch = set(), set()
    for en, de in KATALOG.get("de", {}).items():
        for w in WORT.findall(en or ""):
            englisch.add(w.lower())
        for w in WORT.findall(de or ""):
            deutsch.add(w.lower())
    return deutsch - englisch


_NUR_DEUTSCH = _nur_deutsche_woerter()


def deutsche_woerter(s):
    """Welche NUR-deutschen Woerter stehen in diesem Text? Platzhalter und
    Markup fliegen vorher raus - "{tief}" ist ein Variablenname und
    "<path stroke=…>" ist Code, keins von beidem steht auf dem Schirm."""
    rein = MARKUP.sub(" ", PLATZHALTER.sub(" ", s or ""))
    return sorted({w for w in WORT.findall(rein) if w.lower() in _NUR_DEUTSCH})


def _ausgeblendet(src):
    aus, zeilen = False, set()
    for nr, z in enumerate(src.splitlines(), 1):
        if any(f"de_scan{i}: aus" in z for i in (2, 3, 4, 5)):
            aus = True
        elif any(f"de_scan{i}: an" in z for i in (2, 3, 4, 5)):
            aus = False
        elif aus:
            zeilen.add(nr)
    return zeilen


def scan_datei(pfad):
    src = open(pfad, encoding="utf-8").read()
    tree = ast.parse(src)
    aus = _ausgeblendet(src)
    eltern = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            eltern[c] = n
    stumm = set()          # Docstrings und nackte Zeichenketten-Anweisungen
    for n in ast.walk(tree):
        if isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None),
                                                  ast.Constant):
            stumm.add(n.value)
    protokoll = set()      # Argumente von _log_exception
    schluessel = set()     # Zeichenketten in Schluessel-Stellung
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
            if name in NUR_PROTOKOLL:
                for a in n.args:
                    for c in ast.walk(a):
                        if isinstance(c, ast.Constant) \
                           and isinstance(c.value, str):
                            protokoll.add(c)
            if name in SCHLUESSEL_RUFE and n.args \
               and isinstance(n.args[0], ast.Constant):
                schluessel.add(n.args[0])
        if isinstance(n, ast.Dict):
            for k in n.keys:
                if isinstance(k, ast.Constant):
                    schluessel.add(k)
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant):
            schluessel.add(n.slice)
    treffer = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
            continue
        if n in stumm or n in protokoll or n in schluessel or n.lineno in aus:
            continue
        s = n.value
        if SQL.search(s) or "_" in s or INTERNER_WERT.match(s):
            continue
        gefunden = deutsche_woerter(s)
        if not gefunden:
            continue
        k, uebersetzt = n, False
        while k in eltern:
            k = eltern[k]
            if isinstance(k, ast.Call):
                f = k.func
                name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
                if name in UEBERSETZER:
                    uebersetzt = True
                    break
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef, ast.Module)):
                break
        if not uebersetzt:
            treffer.append((n.lineno, ",".join(gefunden),
                            s.replace("\n", " ")[:70]))
    return treffer


def main():
    kurz = "--kurz" in sys.argv
    gesamt = 0
    for pfad in sorted(glob.glob("eve_trader/**/*.py", recursive=True)):
        pfad = pfad.replace("\\", "/")          # Windows: glob liefert "\"
        if pfad.endswith("sprache.py"):
            continue
        t = scan_datei(pfad)
        gesamt += len(t)
        if t and not kurz:
            print(f"== {pfad}: {len(t)}")
            for nr, woerter, s in sorted(t):
                print(f"   {nr:6}  [{woerter}]  {s}")
    print(f"GESAMT {gesamt}")


if __name__ == "__main__":
    main()
