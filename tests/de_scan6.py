"""Findet Anzeigetexte, die ueber eine VARIABLE in die Anzeige wandern.

WARUM ES DIESEN SECHSTEN SCANNER GIBT (Sitzung 22):
Die beiden vom Nutzer gemeldeten Texte ("% Erfolg", "bei N parallel")
hatten dieselbe Bauform: die Konstante steht nicht im Anzeige-Aufruf,
sondern wird erst einer lokalen Variable zugewiesen, und DIE landet
spaeter in `setText(...)`.

    _dauer = f'bei {n} parallel'          # <- hier steht der Text
    ...
    self._inv_split_lbl.setText(... + _dauer)   # <- hier wird er sichtbar

de_scan3 laeuft von der Konstante nach OBEN und endet an der Zuweisung -
es sei denn, der Variablenname klingt nach Anzeige ("txt", "label", ...).
"_dauer" und "_rest" tun das nicht, also fielen beide durchs Raster.

DIESER HIER GEHT DEN WEG ANDERSHERUM, je Funktion:
  1. Welche NAMEN tauchen in dieser Funktion in einem Anzeige-Aufruf auf?
  2. Welche Textkonstanten fliessen in die Zuweisung genau dieser Namen?
  3. Lief so eine Konstante NICHT durch t()/_txt()? -> Treffer.

Das ist bewusst eine Naeherung: es genuegt, dass derselbe Name in
derselben Funktion einmal angezeigt wird. Eine echte Datenflussanalyse
waere ein eigenes Programm - und gaebe hier keinen besseren Befund.

SPRACHE SPIELT KEINE ROLLE (wie bei de_scan3): ein englischer Text ohne
t() ist genauso ein Treffer, denn er bliebe in der deutschen Fassung
englisch. Genau so lag " Runs Reserve" zwei Sitzungen lang im Code.

AUSGENOMMEN: Markup, sprachneutrales EVE-Vokabular ("Runs", "Blueprint",
"Hub", "ISK"), interne Schluessel (ein kleingeschriebenes Wort) und
Bereiche zwischen `# de_scan6: aus` und `# de_scan6: an` (die Marker von
de_scan2/3 gelten mit). Jeder Marker braucht eine Begruendung daneben.

AUFRUF:  python de_scan6.py            -> Fundstellen je Datei
         python de_scan6.py --kurz     -> nur die Zaehlung
"""
import ast
import os as _os_wurzel
_os_wurzel.chdir(_os_wurzel.path.dirname(_os_wurzel.path.dirname(_os_wurzel.path.abspath(__file__))))   # Projektwurzel (tests\ -> ..)
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import de_scan3 as _d3                                       # noqa: E402

# EIGENE ANZEIGE-HELFER, die de_scan3 (noch) nicht kennt. Alle drei sind
# nachgesehen, nicht vermutet: _flash_tip zeigt ein Tooltip an der Maus,
# _copied_popup ist sein Alias, _dv_label beschriftet das Decryptor-
# Dropdown, _kv_rows baut die Zeilen der Kosten-Tooltips.
HELFER = {"_flash_tip", "_copied_popup", "_dv_label", "_kv_rows"}
SENKEN = _d3.ANZEIGE_METHODEN | _d3.ANZEIGE_KLASSEN | HELFER

# WOERTER, DIE IN BEIDEN SPRACHEN GLEICH HEISSEN - zusaetzlich zu
# de_scan3.SPRACHNEUTRAL. Jedes einzeln nachgesehen: "Auto", "Container",
# "Plan", "Char", "Rig" heissen im deutschen EVE genauso, "Daytrade" und
# "Swing" sind die Namen der Handelsarten im Programm selbst.
ZUSAETZLICH_NEUTRAL = {"auto", "container", "plan", "char", "rig",
                       "daytrade", "swing", "token", "scope", "error",
                       "limit", "csv"}


def _sprachneutral(s):
    import re
    woerter = re.findall(r"[A-Za-zÀ-ɏ]{2,}", s)
    erlaubt = _d3.SPRACHNEUTRAL | ZUSAETZLICH_NEUTRAL
    return bool(woerter) and all(w.lower() in erlaubt for w in woerter)


def _schluesselwort(s):
    """Wie de_scan3._schluesselwort, ABER nur ohne Leerzeichen am Rand.

    de_scan3 strippt vorher - damit galt "bei " als interner Schluessel,
    und genau daran lief `f"bei {n} parallel"` durch. Ein Schluessel steht
    nie mit angehaengtem Leerzeichen im Code; ein Textfragment aus einem
    f-String fast immer.
    """
    if s != s.strip():
        return False
    return _d3._schluesselwort(s)


def _ausgeblendet(src):
    """Alle Marker gelten, nicht nur die eigenen: "das ist ein Schluessel,
    kein Anzeigetext" ist eine Aussage ueber die Stelle, nicht ueber den
    Scanner - sonst braeuchte jede Stelle fuenf Markerpaare uebereinander."""
    aus, zeilen = False, set()
    for nr, z in enumerate(src.splitlines(), 1):
        if any(f"de_scan{i}: aus" in z for i in (2, 3, 4, 5, 6)):
            aus = True
        elif any(f"de_scan{i}: an" in z for i in (2, 3, 4, 5, 6)):
            aus = False
        elif aus:
            zeilen.add(nr)
    return zeilen


def _angezeigte_namen(fn):
    """Namen, die in DIESER Funktion in einem Anzeige-Aufruf vorkommen."""
    namen = set()
    for n in ast.walk(fn):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        nm = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
        # `append` zaehlt mit: Textstuecke werden hier oft in einer Liste
        # gesammelt und erst am Ende zusammengesetzt angezeigt.
        if nm not in SENKEN and nm != "append":
            continue
        for a in list(n.args) + [k.value for k in n.keywords]:
            for c in ast.walk(a):
                if isinstance(c, ast.Name):
                    namen.add(c.id)
    return namen


def _laeuft_durch_t(knoten, eltern, grenze):
    k = eltern.get(knoten)
    while k is not None and k is not grenze:
        if isinstance(k, ast.Call):
            f = k.func
            nm = f.id if isinstance(f, ast.Name) else getattr(f, "attr", None)
            if nm in _d3.UEBERSETZER:
                return True
        k = eltern.get(k)
    return False


def scanne(pfad):
    src = open(pfad, encoding="utf-8").read()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    versteckt = _ausgeblendet(src)
    eltern = _d3._eltern(tree)
    # dict-SCHLUESSEL sind Adressierung, kein Anzeigetext ({401: "...",
    # "420_uebersprungen": ...} - der Schluessel kommt aus den Fehlercodes).
    schluessel = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Dict):
            for k in n.keys:
                if isinstance(k, ast.Constant):
                    schluessel.add(k)
        if isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant):
            schluessel.add(n.slice)
    treffer = []
    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        ziele = _angezeigte_namen(fn)
        if not ziele:
            continue
        for zuw in ast.walk(fn):
            if not isinstance(zuw, (ast.Assign, ast.AugAssign)):
                continue
            zl = zuw.targets if isinstance(zuw, ast.Assign) else [zuw.target]
            namen = {x.id for z in zl for x in ast.walk(z)
                     if isinstance(x, ast.Name)}
            if not (namen & ziele):
                continue
            for c in ast.walk(zuw.value):
                if not (isinstance(c, ast.Constant)
                        and isinstance(c.value, str)):
                    continue
                s = c.value
                if (c in schluessel or c.lineno in versteckt
                        or len(s.strip()) < 2):
                    continue
                if (_d3._nur_markup(s) or _sprachneutral(s)
                        or _schluesselwort(s)):
                    continue
                if _laeuft_durch_t(c, eltern, zuw):
                    continue
                treffer.append((c.lineno, s[:70].replace("\n", " ")))
    return sorted(set(treffer))


def main():
    kurz = "--kurz" in sys.argv
    dateien = (sorted(glob.glob("eve_trader/ui/*.py"))
               + ["eve_trader/__main__.py"])
    gesamt = 0
    for f in dateien:
        f = f.replace("\\", "/")
        tr = scanne(f)
        gesamt += len(tr)
        if tr and not kurz:
            print(f"== {f}: {len(tr)}")
            for nr, s in tr:
                print(f"   {nr:6}  {s}")
    print(f"GESAMT {gesamt}")


if __name__ == "__main__":
    main()
