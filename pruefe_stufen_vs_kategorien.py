"""DIAGNOSE (Sitzung 14): Liegen die Kategorie-Haken sauber auf den
Rezeptstufen - oder mischen sie?

HINTERGRUND. Der Runplaner bildet seine Stufen aus der ECHTEN Rezeptkette
(`industry.reaction_stage_map`): Stufe 1 = das Produkt wird selbst wieder in
einer Reaktion verbraucht, Stufe 2 = es geht direkt in den Schiffbau. Die
Fertigungstiefe dagegen schaltet SDE-KATEGORIEN. Der Nutzer beobachtet, dass
"Ab Composite-Reaktionen" die Intermediate-Stufe im Runplaner nicht
verschwinden laesst - sie schrumpft nur.

DIESES SKRIPT BEANTWORTET GENAU EINE FRAGE: enthaelt eine Kategorie Items aus
MEHREREN Rezeptstufen? Wenn ja, kann kein Kategorie-Haken je "ab Stufe X
baue ich selbst" halten, und der Umbau auf Stufen ist begruendet statt
vermutet. Wenn nein, reicht eine kleine Korrektur der Tiefen-Zusammenstellung.

ES AENDERT NICHTS. Nur lesen, nur Ausgabe auf den Bildschirm.

AUFRUF (im Projektordner, derselbe Ordner wie main.py):
    python pruefe_stufen_vs_kategorien.py

Die Ausgabe hier hereinkopieren - sie enthaelt keine Kontodaten, nur
Item-Namen, Gruppen und Stufen.
"""
import sys
import traceback
from collections import defaultdict


def main():
    try:
        from eve_trader import industry
    except Exception:
        print("FEHLER: eve_trader nicht importierbar. Liegt dieses Skript im "
              "Projektordner (neben main.py)?")
        traceback.print_exc()
        return 1

    print("=" * 70)
    print("STUFEN vs. KATEGORIEN")
    print("=" * 70)

    try:
        recipes = industry.Recipes()
    except Exception:
        print("FEHLER: Rezepte nicht ladbar (industry.db leer?). Im Tool "
              "einmal die SDE laden, dann erneut versuchen.")
        traceback.print_exc()
        return 1

    stage_map = industry.reaction_stage_map(recipes)
    print(f"Reaktionsprodukte gesamt: {len(stage_map)}")
    if not stage_map:
        print("Keine Reaktionsprodukte gefunden - hier ist nichts zu messen.")
        return 1

    catmap = industry.item_category_map() or {}
    # GRUPPENNAMEN AUS DER SDE, nicht aus dem Markt-Scan. `_category_key`
    # entscheidet an Namensbestandteilen wie "Hybrid Polymer" oder
    # "Composite"; `item_category_map` liefert nur group_IDs. Genau diese
    # Luecke hat im Tool schon einmal dazu gefuehrt, dass ein Item (Ferrogel)
    # mit leerem Gruppennamen in die generische Auffang-Kategorie fiel und
    # still gekauft wurde. Dieselbe Quelle wie der Rueckfall dort.
    try:
        groups = industry.group_names(list(stage_map.keys())) or {}
    except Exception:
        groups = {}
        print("WARNUNG: Gruppennamen nicht ladbar - das Ergebnis unten waere "
              "wertlos, weil die Kategorie an den Namen haengt.")
        traceback.print_exc()
        return 1
    # Namen sind nur Beiwerk fuer die Beispiel-Zeilen; fehlen sie, steht dort
    # die Type-ID. Das Ergebnis haengt NICHT daran.
    try:
        from eve_trader import store as _store
        names = _store.cached_names(list(stage_map.keys())) or {}
    except Exception:
        names = {}

    # KEIN IMPORT VON MainWindow: der zieht Qt und pyqtgraph nach, die auf
    # einem System ohne die Tool-Umgebung nicht installiert sind. Stattdessen
    # wird `_category_key` als QUELLTEXT aus main_window.py geholt und hier
    # ausgefuehrt. Das ist KEINE zweite Fassung der Logik - es ist derselbe
    # Code, nur ohne Oberflaeche drumherum. Eine nachgebaute Kopie waere
    # genau die zweite Wahrheit, die dieses Skript gerade untersucht.
    import ast
    import os
    _mw_pfad = os.path.join("eve_trader", "ui", "main_window.py")
    try:
        _baum = ast.parse(open(_mw_pfad, encoding="utf-8").read())
    except Exception:
        print(f"FEHLER: {_mw_pfad} nicht lesbar. Liegt das Skript im "
              f"Projektordner?")
        traceback.print_exc()
        return 1

    _ns = {"industry": industry}
    _fn_node = None
    _depth_node = None
    for _kl in ast.walk(_baum):
        if isinstance(_kl, ast.FunctionDef) and _kl.name == "_category_key":
            _fn_node = _kl
        if isinstance(_kl, ast.Assign):
            for _z in _kl.targets:
                if getattr(_z, "id", "") == "_DEPTH_LEVELS":
                    _depth_node = _kl
    if _fn_node is None:
        print("FEHLER: _category_key nicht in main_window.py gefunden.")
        return 1
    try:
        exec(compile(ast.Module(body=[_fn_node], type_ignores=[]),
                     "<category_key>", "exec"), _ns)
        _roh = _ns["_category_key"]
    except Exception:
        print("FEHLER: _category_key nicht ausfuehrbar.")
        traceback.print_exc()
        return 1

    class _Huelle:
        """Minimales `self`: die Funktion benutzt daraus nur einen Zwischen-
        speicher fuer Gruppennamen."""
        _sde_group_name_cache = {}

    _huelle = _Huelle()

    def _cat_key(tid, grp, is_react, cat, meta):
        return _roh(_huelle, tid, grp, is_react, cat, meta)

    # Kategorie -> {Stufe: [Beispielnamen]}
    treffer = defaultdict(lambda: defaultdict(list))
    ohne_key = []
    for tid, stufe in stage_map.items():
        info = catmap.get(tid)
        cat = info[0] if info else None
        meta = info[2] if info and len(info) > 2 else None
        grp = groups.get(tid) or ""
        try:
            key = _cat_key(tid, grp or "", True, cat, meta)
        except Exception:
            ohne_key.append(tid)
            continue
        treffer[key][stufe].append(names.get(tid) or f"#{tid}")

    print()
    print(f"{'KATEGORIE-SCHLUESSEL':<28} {'St1':>5} {'St2':>5}   BEFUND")
    print("-" * 70)
    gemischt = []
    for key in sorted(treffer):
        s1 = len(treffer[key].get(1, []))
        s2 = len(treffer[key].get(2, []))
        if s1 and s2:
            befund = "<<< MISCHT BEIDE STUFEN"
            gemischt.append(key)
        elif s1:
            befund = "nur Stufe 1"
        else:
            befund = "nur Stufe 2"
        print(f"{key:<28} {s1:>5} {s2:>5}   {befund}")

    print()
    if gemischt:
        print("ERGEBNIS: Es MISCHT. Diese Kategorien enthalten Items aus BEIDEN")
        print("Rezeptstufen - ein Kategorie-Haken kann dort nicht 'ab Stufe X'")
        print("bedeuten:")
        for key in gemischt:
            print(f"\n  {key}")
            for stufe in (1, 2):
                bsp = treffer[key].get(stufe, [])
                if bsp:
                    print(f"    Stufe {stufe} ({len(bsp)}): "
                          + ", ".join(sorted(bsp)[:6])
                          + (" ..." if len(bsp) > 6 else ""))
    else:
        print("ERGEBNIS: Jede Kategorie liegt VOLLSTAENDIG auf EINER Stufe.")
        print("Dann reicht es, die Zusammenstellung der Fertigungstiefe zu")
        print("korrigieren - der groessere Umbau auf Stufen ist nicht noetig.")

    if ohne_key:
        print(f"\nHINWEIS: {len(ohne_key)} Item(s) ohne Kategorie-Schluessel "
              f"(z.B. {ohne_key[:5]}) - konnten nicht zugeordnet werden.")

    # Die Zusammenstellung, um die es konkret geht: was nimmt "Ab Composite"
    # heraus, und welche Stufen bleiben dadurch trotzdem drin?
    try:
        exec(compile(ast.Module(body=[_depth_node], type_ignores=[]),
                     "<depth>", "exec"), _ns)
        stufen = {k: keys for k, _lbl, keys, _tip in _ns["_DEPTH_LEVELS"]}
        ab_comp = stufen.get("ab_composite") or set()
        print()
        print("=" * 70)
        print("WAS 'AB COMPOSITE-REAKTIONEN' ANGEHAKT LAESST")
        print("=" * 70)
        for key in sorted(treffer):
            if key in ab_comp:
                s1 = len(treffer[key].get(1, []))
                if s1:
                    print(f"  {key:<28} enthaelt {s1} Item(s) der STUFE 1 "
                          f"-> bleiben im Runplaner stehen")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
