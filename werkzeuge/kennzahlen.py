"""Kennzahlen: wie viele Zeilen haben wir, und wie viele davon laufen je?

Zaehlt AST-basiert, nicht per grep. Fuer jede def/class im ausgelieferten
Code wird gefragt: wird der Name IRGENDWO sonst benutzt?
  - im Anwendungscode          -> LEBT
  - nur in Tests/Werkzeugen    -> tot zur Laufzeit, aber von Pruefungen FESTGENAGELT
  - nirgends                   -> TOT (Loeschkandidat)
Zusaetzlich wird in ALLEN String-Literalen gesucht (getattr/Qt-Signalnamen),
damit dynamisch gerufene Methoden nicht faelschlich als tot gelten.
"""
import ast
import collections
import pathlib
import sys

WURZEL = pathlib.Path(__file__).parent.parent   # Projektwurzel
ANWENDUNG = sorted(
    [p for p in (WURZEL / "eve_trader").rglob("*.py") if "__pycache__" not in str(p)]
) + [WURZEL / "main.py"]
DRUMHERUM = sorted(
    list((WURZEL / "tests").glob("test_*.py")) + list((WURZEL / "werkzeuge").glob("messung_*.py"))
    + [WURZEL / "rotprobe.py", WURZEL / "lint_order.py", WURZEL / "repro_bpc_te.py"]
)


def _spanne(knoten):
    """Zeilenbereich inkl. Dekoratoren."""
    start = knoten.lineno
    for d in getattr(knoten, "decorator_list", []):
        start = min(start, d.lineno)
    return start, knoten.end_lineno


def _baeume(dateien):
    for p in dateien:
        if not p.exists():
            continue
        try:
            yield p, ast.parse(p.read_text(encoding="utf-8"), filename=str(p))
        except SyntaxError as e:
            print(f"  !! {p.name}: {e}", file=sys.stderr)


def sammle_defs(dateien):
    """(name, datei, zeilen, verschachtelt?) je Funktion/Methode."""
    treffer = []
    for p, baum in _baeume(dateien):
        eltern = {}
        for k in ast.walk(baum):
            for kind in ast.iter_child_nodes(k):
                eltern[kind] = k
        for k in ast.walk(baum):
            if not isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            a, b = _spanne(k)
            # verschachtelt = liegt in einer anderen Funktion (Closure)
            e, tief = eltern.get(k), False
            while e is not None:
                if isinstance(e, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    tief = True
                    break
                e = eltern.get(e)
            treffer.append((k.name, p, a, b, b - a + 1, tief))
    return treffer


def sammle_benutzungen(dateien, def_zeilen):
    """Zaehlt Namensverwendungen, OHNE die def-Zeile selbst."""
    zaehler = collections.Counter()
    for p, baum in _baeume(dateien):
        for k in ast.walk(baum):
            if isinstance(k, ast.Name):
                zaehler[k.id] += 1
            elif isinstance(k, ast.Attribute):
                zaehler[k.attr] += 1
            elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                # getattr("...")/Qt-Namen: jedes Wort im String zaehlt mit
                for wort in k.value.replace("(", " ").replace(".", " ").split():
                    if wort.isidentifier():
                        zaehler[wort] += 1
            elif isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                pass  # def-Zeile selbst ist keine Benutzung
    return zaehler


def main():
    defs_app = sammle_defs(ANWENDUNG)
    benutzt_app = sammle_benutzungen(ANWENDUNG, None)
    benutzt_test = sammle_benutzungen(DRUMHERUM, None)

    gesamt_zeilen = sum(
        len(p.read_text(encoding="utf-8").splitlines()) for p in ANWENDUNG if p.exists()
    )

    lebt, nur_test, tot = [], [], []
    for name, p, a, b, n, tief in defs_app:
        if benutzt_app.get(name, 0) > 0:
            lebt.append((name, p, a, b, n, tief))
        elif benutzt_test.get(name, 0) > 0:
            nur_test.append((name, p, a, b, n, tief))
        else:
            tot.append((name, p, a, b, n, tief))

    def summe(liste):
        return sum(x[4] for x in liste)

    print(f"AUSGELIEFERTER CODE: {gesamt_zeilen:,} Zeilen in {len(ANWENDUNG)} Dateien")
    print(f"  davon in Funktionen/Methoden: {summe(defs_app):,} "
          f"({len(defs_app)} Stueck)")
    print()
    print(f"  LEBT (irgendwo im App-Code gerufen)   : {len(lebt):4d} Def / "
          f"{summe(lebt):6,} Zeilen")
    print(f"  NUR VON TESTS festgenagelt            : {len(nur_test):4d} Def / "
          f"{summe(nur_test):6,} Zeilen")
    print(f"  TOT (nirgends erwaehnt)               : {len(tot):4d} Def / "
          f"{summe(tot):6,} Zeilen")
    print()

    for titel, liste in (("TOT - LOESCHKANDIDATEN", tot),
                         ("NUR VON TESTS FESTGENAGELT", nur_test)):
        if not liste:
            continue
        print(f"=== {titel} ({len(liste)}) ===")
        for name, p, a, b, n, tief in sorted(liste, key=lambda x: -x[4]):
            marke = " [Closure]" if tief else ""
            print(f"  {n:5d} Z  {p.name}:{a}-{b}  {name}{marke}")
        print()

    print("=== GROESSTE LEBENDE FUNKTIONEN (Zerlegungs-Kandidaten) ===")
    for name, p, a, b, n, tief in sorted(lebt, key=lambda x: -x[4])[:15]:
        print(f"  {n:5d} Z  {p.name}:{a}-{b}  {name}")


if __name__ == "__main__":
    main()
