"""Findet ANZEIGETEXTE, die nicht durch t() laufen - ohne Sprach-Raten.

WARUM ES DIESEN DRITTEN SCANNER GIBT (Sitzung 16):
de_scan.py prueft nur direkte Qt-Aufrufe. de_scan2.py fragt "sieht das
deutsch aus?" und braucht dafuer Umlaute oder Woerter aus einer Liste -
"Neu berechnen" hat weder das eine noch das andere. Beide standen auf 0,
waehrend rund 250 deutsche Texte in der Oberflaeche standen.

DIESER HIER FRAGT NICHT NACH SPRACHE. Er fragt:
    Landet diese Textkonstante in einem ANZEIGE-Aufruf?
    Und wurde sie unterwegs durch t() geschickt?
Beides ist am Syntaxbaum ablesbar, nicht zu erraten. Sprache spielt keine
Rolle - ein englischer Text ohne t() ist genauso ein Treffer, denn er
bleibt in der deutschen Fassung englisch.

VERFAHREN: von jeder Konstante nach OBEN laufen (f-String, Verkettung,
.join/.format, Liste/Tupel) bis ein Aufruf kommt. Ist es t()/_txt() -
uebersetzt. Ist es ein Anzeige-Aufruf - Treffer. Sonst weiter hoch.

MARKER: `# de_scan3: aus` ... `# de_scan3: an` blendet Zeilen aus (fuer
Schluessel, die nie angezeigt werden). `# de_scan2: aus/an` gilt mit.

AUFRUF:  python de_scan3.py            -> Fundstellen je Datei
         python de_scan3.py --kurz     -> nur die Zaehlung
"""
import ast
import os as _os_wurzel
_os_wurzel.chdir(_os_wurzel.path.dirname(_os_wurzel.path.dirname(_os_wurzel.path.abspath(__file__))))   # Projektwurzel (tests\ -> ..)
import glob
import sys

UEBERSETZER = {"t", "_txt", "_txtf"}

# Methoden und Klassen, deren Text ein Mensch liest.
ANZEIGE_METHODEN = {
    "setText", "setToolTip", "addItem", "addAction", "setWindowTitle",
    "showMessage", "setPlaceholderText", "setHeaderLabels", "setHeaderLabel",
    "setHorizontalHeaderLabels", "setVerticalHeaderLabels", "addTab",
    "setTabText", "information", "warning", "critical", "question", "about",
    "setLabelText", "setInformativeText", "addButton", "setStatusTip",
    "setTitle", "setFormat", "setPrefix", "setSuffix", "setItemText",
    "setLabel", "setEditText", "setDetailedText", "getItem", "getText",
    "setHtml", "setPlainText", "setWhatsThis", "insertItem", "setSectionText",
    # EIGENE ANZEIGE-HELFER (Sitzung 17, Nutzer-Screenshots): ihre Texte fielen
    # durchs Raster - "Gewinn (netto)" (kpi_card), "STRATEGIE" und
    # "CAPITAL-SCHIFFE" (_collapsible), die Kacheln (_box), Formularzeilen.
    "_collapsible", "kpi_card", "_box", "addRow",
}
ANZEIGE_KLASSEN = {
    "QLabel", "QPushButton", "QCheckBox", "QRadioButton", "QGroupBox",
    "QAction", "QMessageBox", "QTreeWidgetItem", "QTableWidgetItem",
    "QListWidgetItem", "_QCheckBox", "QMenu", "QToolButton", "QLineEdit",
    "QInputDialog", "QProgressDialog", "QTabWidget", "NumericItem",
}
# Aufrufe, deren ERSTES Argument ein Schluessel/Index ist, kein Anzeigetext.
SCHLUESSEL_ERSTES = {"setLabel", "setItemText", "setTabText", "insertItem",
                     "setSectionText"}
# Variablennamen, die auf Anzeigetext hindeuten.
ANZEIGE_NAMEN = ("txt", "text", "label", "lbl", "title", "titel", "tip",
                 "msg", "hint", "status", "caption", "head", "note",
                 "warn", "info", "summary", "reason", "grund")
DURCHREICHEND = {"join", "format", "lstrip", "rstrip", "strip", "upper",
                 "lower", "replace", "center", "ljust", "rjust"}


def _ausgeblendet(src):
    aus, zeilen = False, set()
    for nr, zeile in enumerate(src.splitlines(), 1):
        if "de_scan3: aus" in zeile or "de_scan2: aus" in zeile:
            aus = True
        elif "de_scan3: an" in zeile or "de_scan2: an" in zeile:
            aus = False
        elif aus:
            zeilen.add(nr)
    return zeilen


def _eltern(tree):
    m = {}
    for n in ast.walk(tree):
        for k in ast.iter_child_nodes(n):
            m[k] = n
    return m


def _urteil(node, eltern):
    """'uebersetzt' | 'anzeige' | None - was passiert mit dieser Konstante?"""
    kind, cur = node, eltern.get(node)
    tiefe = 0
    while cur is not None and tiefe < 25:
        tiefe += 1
        if isinstance(cur, ast.Call):
            f = cur.func
            name = (f.id if isinstance(f, ast.Name)
                    else f.attr if isinstance(f, ast.Attribute) else None)
            if name in UEBERSETZER:
                return "uebersetzt"
            if name in ANZEIGE_METHODEN or name in ANZEIGE_KLASSEN:
                # ERSTES ARGUMENT IST MANCHMAL EIN SCHLUESSEL, kein Text:
                # setLabel("bottom", text), setItemText(index, text),
                # setText(spalte, text) bei QTreeWidgetItem. Nur dort, wo das
                # erste Argument NICHT der Text ist, wird es uebersprungen -
                # sonst wuerde jeder Knopf durchs Raster fallen.
                if name in SCHLUESSEL_ERSTES and cur.args and cur.args[0] is kind:
                    return None
                return "anzeige"
            if name in DURCHREICHEND:
                kind, cur = cur, eltern.get(cur)
                continue
            return None                      # anderer Aufruf: nicht sichtbar
        if isinstance(cur, (ast.JoinedStr, ast.BinOp, ast.List, ast.Tuple,
                            ast.IfExp, ast.Starred, ast.keyword)):
            kind, cur = cur, eltern.get(cur)
            continue
        # ZUWEISUNG AN EINE ANZEIGE-VARIABLE (Nutzer-Befund Sitzung 16:
        # "da ist noch deutscher Text in Rot"). `status_txt = "genug"` geht
        # erst in eine Variable und von dort in die Tabelle - der Weg nach
        # oben endete bisher hier, und die Zeile fiel durchs Raster.
        # Am NAMEN erkannt, nicht am Datenfluss: eine echte Verfolgung waere
        # ein eigenes Programm. Der Name ist ein guter Hinweis, mehr nicht -
        # deshalb steht hier eine Liste, die man erweitern darf.
        if isinstance(cur, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            ziele = (cur.targets if isinstance(cur, ast.Assign)
                     else [cur.target])
            namen = []
            for z in ziele:
                for nn in ast.walk(z):
                    if isinstance(nn, ast.Name):
                        namen.append(nn.id.lower())
            if any(any(w in nm for w in ANZEIGE_NAMEN) for nm in namen):
                return "anzeige"
            return None
        return None
    return None


_TAG = __import__("re").compile(r"<[^>]*>")
# NUR ECHTE CSS-EIGENSCHAFTEN (Sitzung 17, Nutzer-Screenshots): die alte
# Fassung `[A-Za-z-]+\s*:\s*[^;]*` hielt JEDE Beschriftung mit Doppelpunkt
# fuer CSS ("Zeitraum:", "Typ:", "Suche:", "Kategorie:") - sie fielen seit
# Sitzung 16 alle durchs Raster, waehrend der Scanner 0 meldete.
_CSS_TEIL = __import__("re").compile(
    r"\b(?:color|background(?:-color)?|font-(?:size|weight|family|style)|"
    r"border(?:-(?:radius|left|right|top|bottom|color|width))?|padding(?:-\w+)?|"
    r"margin(?:-\w+)?|text-(?:align|decoration|transform)|letter-spacing|"
    r"white-space|(?:max|min)-(?:width|height)|width|height|line-height|opacity|"
    r"display|vertical-align|qproperty-\w+|selection-\w+(?:-\w+)?)"
    r"\s*:\s*[^;\"'<]*;?")


# WOERTER, DIE IN BEIDEN SPRACHEN GLEICH HEISSEN: EVE-Vokabular ("Runs",
# "Blueprint", "Hub") und Einheiten ("ISK", "m\u00b3"). Sie zu uebersetzen
# waere falsch - im Spiel heissen sie so. Steht ein Text NUR aus solchen
# Woertern, Zahlen und Zeichen, ist er kein Uebersetzungsfall.
SPRACHNEUTRAL = {
    "isk", "m", "m3", "run", "runs", "blueprint", "blueprints", "bpc", "bpo",
    "hub", "esi", "sde", "me", "te", "t1", "t2", "t3", "eve", "jita", "plex",
    "item", "items", "id", "ok", "stk", "structures", "all", "none",
    "tech", "sell",
}


def _sprachneutral(s):
    import re as _re
    woerter = _re.findall(r"[A-Za-z\u00c0-\u024f]{2,}", s)
    return bool(woerter) and all(w.lower() in SPRACHNEUTRAL for w in woerter)


def _schluesselwort(s):
    """True bei internen Schluesseln wie "under", "relist", "npc", "__add__".

    Sie stehen als userData in addItem(label, data) oder als Modus-Kennung
    im Code - ein Mensch sieht sie nie. Merkmal: EIN Wort, klein
    geschrieben, ohne Leerzeichen. Deutsche Anzeigetexte sehen anders aus
    (Substantive gross, Saetze mit Leerzeichen), englische Beschriftungen
    beginnen mit einem Grossbuchstaben.
    """
    import re as _re
    k = s.strip()
    return bool(_re.fullmatch(r"_{0,2}[a-z][a-z0-9_]*_{0,2}", k))


def _nur_markup(s):
    """True, wenn nichts uebrig bleibt, das ein Mensch liest.

    HTML-Bruchstuecke aus f-Strings (`'<span style="color:'`, `'</b>  \u00b7  '`)
    landen sonst als Treffer - sie sind aber Aufbau, kein Text. Tags und
    CSS-Eigenschaften rausrechnen; bleibt kein Buchstaben-Wort uebrig, ist es
    Markup.
    """
    import re as _re
    rest = s
    # angebrochene Tags an den Raendern: '<span style="color:'  /  ';">Text'
    rest = _re.sub(r"<[^>]*$", "", rest)
    rest = _re.sub(r"^[^<]*?>", "", rest, count=1) if ">" in rest.split("<")[0] else rest
    rest = _re.sub(r"&[a-z]+;|&#\d+;", " ", rest)   # &nbsp; &amp; &#183; ...
    rest = _TAG.sub("", rest)
    rest = _CSS_TEIL.sub("", rest)
    return not _re.search(r"[A-Za-z\u00c0-\u024f]{2}", rest)


def scanne(pfad):
    src = open(pfad, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    versteckt = _ausgeblendet(src)
    eltern = _eltern(tree)
    raus = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
            continue
        if n.lineno in versteckt:
            continue
        s = n.value
        if not s.strip() or len(s.strip()) < 2:
            continue
        if _nur_markup(s) or _sprachneutral(s) or _schluesselwort(s):
            continue
        if _urteil(n, eltern) == "anzeige":
            raus.append((n.lineno, s[:78].replace("\n", " ")))
    return sorted(set(raus))


def main():
    kurz = "--kurz" in sys.argv
    dateien = sorted(glob.glob("eve_trader/ui/*.py")) + ["eve_trader/__main__.py"]
    gesamt = 0
    for f in dateien:
        tr = scanne(f)
        gesamt += len(tr)
        print(f"== {f}: {len(tr)}")
        if not kurz:
            for ln, s in tr:
                print(f"   {ln:>6}  {s}")
    print(f"GESAMT {gesamt}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
