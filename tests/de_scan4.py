"""Findet DEUTSCH AUSSEHENDEN Text ausserhalb von t() - in ALLEN Modulen.

WARUM ES DIESEN VIERTEN SCANNER GIBT (Sitzung 17):
de_scan3 meldete 0, waehrend auf der englischen Oberflaeche die ganze
Bestandszeile im Bauplan deutsch war, der CCP-Hinweis in den Einstellungen
und jede Fehlermeldung aus esi.py/hubs.py/scanner.py. Zwei blinde Flecken:
  1. de_scan3 prueft nur eve_trader/ui/ - Fehlermeldungen entstehen aber in
     den Hintergrund-Modulen und werden erst spaeter angezeigt.
  2. de_scan3 folgt einem Text bis zu einem ANZEIGE-Aufruf. Texte, die ueber
     `parts.append(...)`, eigene Helfer (`_flash_tip`, `_run(label=...)`)
     oder `raise RuntimeError(...)` laufen, erreicht er nie.

DIESER HIER FRAGT ANDERSHERUM: sieht der Text deutsch aus (Umlaut oder ein
eindeutig deutsches Wort)? Und lief er durch t()/_txt()? Wohin er danach
fliesst, spielt keine Rolle. Das findet anderes als de_scan3 - beide
zusammen sind die Pruefung, keiner allein.

AUSGENOMMEN: Docstrings, nackte Zeichenketten-Anweisungen, sprache.py (dort
steht der Katalog), und Bereiche zwischen `# de_scan4: aus` und
`# de_scan4: an` (auch de_scan2/de_scan3-Marker gelten). Jeder Marker
braucht eine Begruendung daneben.

AUFRUF:  python de_scan4.py            -> Fundstellen je Datei
         python de_scan4.py --kurz     -> nur die Zaehlung
"""
import ast
import os as _os_wurzel
_os_wurzel.chdir(_os_wurzel.path.dirname(_os_wurzel.path.dirname(_os_wurzel.path.abspath(__file__))))   # Projektwurzel (tests\ -> ..)
import glob
import re
import sys

WORTE = re.compile(
    r"\b(nicht|nichts|und|der|die|das|dem|den|noch|kein|keine|fehlt|fehlen|"
    r"Fehler|geladen|laden|bitte|zuerst|wird|werden|wurde|ist|oder|mit|ohne|"
    r"fuer|gebaut|kaufen|bauen|Bestand|jetzt|schon|nur|aber|auch|bereits|"
    r"frisch|fertig|fertigen|gedeckt|teilweise|laut|Stand|vor|Stk|Seite|Zeile|"
    r"alle|alles|eingefroren|mitgerechnet|abliefern|Reservierung\w*|Einkauf\w*|"
    r"Zwischenprodukt\w*|erneut|gesperrt|gekauft|Kauf|Bau|Menge|Preis|Kosten|"
    # Sitzung 17 (Nutzer fand "1. Treibstoff", "2. Reaktionen", "4.
    # Komponenten", "5. Endprodukt" im Bauplan-Reiter - KEIN Scanner meldete
    # sie): die Namen der Bau-Stufen und Kategorien gehoeren in die Liste.
    r"Treibstoff|Endprodukt|Komponente\w*|Reaktion\w*|Mineralien|Rohstoffe|"
    r"H\u00fcllen|Mond-Materialien|Stufe|Bauplan|Blaupause\w*|"
    r"Stufe|Kopien|besorgen|genug|unbekannt|verf\u00fcgbar|eingeloggt)\b")
UMLAUT = re.compile("[\u00e4\u00f6\u00fc\u00c4\u00d6\u00dc\u00df]")
UEBERSETZER = {"t", "_txt", "_txtf"}
# ZWEI ZUSATZREGELN (Sitzung 17, Nutzer-Screenshot: "Lade Ziel-Orderbuch ...
# (ganze Region, kann dauern)" im Ladebild - kein Wort davon stand in WORTE):
#  A) was an einen STATUS-RUECKRUF oder an label=/err_prefix= geht, ist
#     Anzeigetext - egal in welcher Sprache (auch Englisch ohne t() bliebe
#     in der deutschen Fassung englisch);
#  B) ein Text mit Ellipse "\u2026" ist fast immer ein Ladetext.
STATUS_RUFE = {"status", "progress", "_set_loading", "set_status"}
#  D) (Sitzung 22) WAS NUR INS PROTOKOLL GEHT, IST KEIN ANZEIGETEXT:
#     `_log_exception(wo, text)` schreibt ausschliesslich in fehler.log
#     (nachgesehen in main_window.py, nicht vermutet). Seine Beschriftungen
#     standen bisher einzeln unter `# de_scan4: aus`-Markern - jede neue
#     Fehlerbehandlung brauchte einen weiteren. de_scan5 und de_scan6 kennen
#     die Regel schon; hier zieht sie nach.
NUR_PROTOKOLL = {"_log_exception"}
#  C) (Sitzung 17, Nutzer-Screenshots "Gewinn (netto)", "Ziel-Marge",
#     "Lohnende Produktion") - kein Wort davon stand in WORTE, und die Texte
#     gehen an eigene Helfer (kpi_card, _collapsible, Formularlisten). Die
#     beste Liste deutscher Anzeigetexte ist der KATALOG SELBST: wer im Code
#     woertlich eine DEUTSCHE Uebersetzung schreibt, hat das t() vergessen.
def _deutsche_katalogtexte():
    try:
        import sys as _s, os as _o
        _s.path.insert(0, _o.path.dirname(_o.path.dirname(_o.path.abspath(__file__))))
        from eve_trader.sprache import KATALOG
    except Exception:
        return set()
    out = set()
    for en, de in KATALOG.get("de", {}).items():
        d = (de or "").strip()
        if d and d != (en or "").strip() and len(d) >= 3:
            out.add(d)
    return out


_DE_TEXTE = _deutsche_katalogtexte()
ANZEIGE_KW = {"label", "err_prefix"}


def _ausgeblendet(src):
    aus, zeilen = False, set()
    for nr, z in enumerate(src.splitlines(), 1):
        if any(f"de_scan{i}: aus" in z for i in (2, 3, 4)):
            aus = True
        elif any(f"de_scan{i}: an" in z for i in (2, 3, 4)):
            aus = False
        elif aus:
            zeilen.add(nr)
    return zeilen


# WOERTER IN GROSSBUCHSTABEN (Sitzung 17, Nutzer-Screenshot "BAUEN \u00b7 20
# Runs"): WORTE unterscheidet Gross/klein, "BAUEN" traf "bauen" nicht. NUR
# ganz grosse Woerter werden klein verglichen - sonst loesten englische Texte
# mit "plan"/"stand" Fehlalarme aus.
_WORTE_KLEIN = {w.lower() for w in re.findall(r"[A-Za-z\u00e4\u00f6\u00fc]{2,}",
                                             WORTE.pattern) if w not in ("b", "w")}
_GROSS = re.compile(r"\b[A-Z\u00c4\u00d6\u00dc]{3,}\b")


def _sieht_deutsch_aus(s):
    if UMLAUT.search(s) or WORTE.search(s):
        return True
    return any(w.lower() in _WORTE_KLEIN for w in _GROSS.findall(s))


def scan_datei(pfad):
    src = open(pfad, encoding="utf-8").read()
    tree = ast.parse(src)
    aus = _ausgeblendet(src)
    eltern = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            eltern[c] = n
    stumm = set()     # Docstrings und nackte Zeichenketten-Anweisungen
    for n in ast.walk(tree):
        if isinstance(n, ast.Expr) and isinstance(getattr(n, "value", None), ast.Constant):
            stumm.add(n.value)
    # Regel A: Konstanten, die in einen Status-Rueckruf / label= fliessen
    regel_a = set()
    protokoll = set()          # Regel D: Argumente von _log_exception
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            f = n.func
            name = f.id if isinstance(f, ast.Name) else getattr(f, "attr", "")
            ziele = [n.args[0]] if (name in STATUS_RUFE and n.args) else []
            ziele += [kw.value for kw in n.keywords if kw.arg in ANZEIGE_KW]
            for z in ziele:
                for c in ast.walk(z):
                    if isinstance(c, ast.Constant) and isinstance(c.value, str):
                        regel_a.add(c)
            if name in NUR_PROTOKOLL:
                for a in n.args:
                    for c in ast.walk(a):
                        if isinstance(c, ast.Constant) \
                           and isinstance(c.value, str):
                            protokoll.add(c)
    treffer = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Constant) and isinstance(n.value, str)):
            continue
        if n in stumm or n in protokoll or n.lineno in aus \
           or len(n.value.strip()) < 3:
            continue
        if not any(ch.isalpha() for ch in n.value):
            continue
        if not (_sieht_deutsch_aus(n.value) or n in regel_a
                or "\u2026" in n.value or n.value.strip() in _DE_TEXTE):
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
            treffer.append((n.lineno, n.value.replace("\n", " ")[:80]))
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
            for nr, s in sorted(t):
                print(f"   {nr:6}  {s}")
    print(f"GESAMT {gesamt}")


if __name__ == "__main__":
    main()
