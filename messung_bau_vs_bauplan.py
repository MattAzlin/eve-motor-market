"""MESSUNG: Warum bewertet der Bau-Scanner ein Item anders als der Bauplan?

Der Scanner (Tab "Bauen") rechnet mit `industry.build_cost()` - pro Stueck,
schnell, ueber hunderte Items. Der Bauplan-Dialog rechnet mit
`industry.production_plan()` - fuer eine konkrete Menge, mit EVE-genauer
Rundung. Beide meinen dieselbe Groesse ("was kostet mich ein Stueck?"), und
genau deshalb muessen Abweichungen erklaerbar sein.

Dieses Skript stellt beide Rechnungen fuer DASSELBE Item nebeneinander,
aufgeschluesselt nach Material / Job / Invention / Bestand, und faehrt danach
eine Ablation: es schaltet EINE Annahme nach der anderen um und zeigt, welche
Zeile die Luecke schliesst. Die Zeile, in der die beiden auseinandergehen, ist
die Antwort - nicht die Vermutung davor (Arbeitsregel 5).

WICHTIG - warum das Skript das Hauptfenster baut, statt die Optionen selbst
zusammenzustellen: es ruft `_bau_scan_build_opts()` und
`_bau_scan_build_opts_esi()` auf, also EXAKT die Methoden, mit denen auch der
Scan seine `build_opts` baut. Eine Nachbildung waere eine zweite Wahrheit und
wuerde am Ende die Nachbildung messen statt den Scanner (Arbeitsregel 9).

AUFRUF (im Projektverzeichnis):
    QT_QPA_PLATFORM=offscreen python3 messung_bau_vs_bauplan.py "Flycatcher"
    QT_QPA_PLATFORM=offscreen python3 messung_bau_vs_bauplan.py 22464 --menge 10

Ohne Argument werden ein paar T2-Items aus dem aktuellen Markt-Snapshot
genommen. Voraussetzung: SDE geladen und einmal "Markt-Scan" gelaufen (das
Skript liest denselben Snapshot wie der Bauen-Tab, es holt keine Preise neu).
"""
import argparse
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication            # noqa: E402

_app = QApplication.instance() or QApplication([])

from eve_trader import industry, store                # noqa: E402
from eve_trader.ui.main_window import MainWindow, isk  # noqa: E402

_POSTEN = (("mat_market", "Material (Marktpreis)"),
           ("mat_adjusted", "Material (Adjusted-Rueckfall)"),
           ("job", "Jobkosten"),
           ("inv", "Invention"),
           ("stock", "Bestand"))


def _scanner_sicht(type_id, price_fn, recipes, opts):
    """build_cost() + seine eigene Aufschluesselung (parts_memo) - PRO STUECK."""
    parts = {}
    c = industry.build_cost(type_id, price_fn, recipes, opts, {}, parts_memo=parts)
    p = dict(parts.get(type_id) or {})
    p["stock"] = 0.0            # build_cost kennt keinen Bestand
    return c, p


def _plan_sicht(type_id, menge, price_fn, recipes, opts):
    """production_plan() fuer `menge` Stueck, auf ein Stueck heruntergerechnet.
    mat_cost enthaelt beide Preisquellen; mat_cost_adjusted ist der Teil, der
    nur am Adjusted-Price haengt - dieselbe Trennung wie in build_cost."""
    plan = industry.production_plan(type_id, menge, price_fn, recipes, opts)
    n = float(menge or 1)
    adj = float(plan.get("mat_cost_adjusted", 0.0) or 0.0)
    return float(plan.get("total_cost", 0.0) or 0.0) / n, {
        "mat_market": (float(plan.get("mat_cost", 0.0) or 0.0) - adj) / n,
        "mat_adjusted": adj / n,
        "job": float(plan.get("job_cost", 0.0) or 0.0) / n,
        "inv": float(plan.get("inv_cost", 0.0) or 0.0) / n,
        "stock": float(plan.get("stock_cost", 0.0) or 0.0) / n,
    }


def _zeile(label, a, b):
    d = (b or 0) - (a or 0)
    mark = "   <<<" if abs(d) > 0.005 * max(abs(a or 0), abs(b or 0), 1) else ""
    return (f"  {label:30} {isk(a, suffix=False):>18} {isk(b, suffix=False):>18}"
            f" {isk(d, suffix=False):>18}{mark}")


def vergleiche(name, type_id, menge, price_fn, recipes, opts):
    sc, sp = _scanner_sicht(type_id, price_fn, recipes, opts)
    pc, pp = _plan_sicht(type_id, menge, price_fn, recipes, opts)
    print(f"\n=== {name}  (type_id {type_id}, Menge {menge}) ===")
    if sc is None:
        print("  Scanner: KEINE Baukosten berechenbar (build_cost -> None).")
        print("  -> Das ist bereits die Antwort: ein Material ist weder bau-")
        print("     noch bepreisbar. Der Plan behilft sich stattdessen mit Kauf.")
    print(f"  {'Posten je Stueck':30} {'Scanner':>18} {'Bauplan':>18} {'Differenz':>18}")
    for key, label in _POSTEN:
        print(_zeile(label, sp.get(key, 0.0) if sc is not None else 0.0,
                     pp.get(key, 0.0)))
    print(_zeile("SUMME", sc, pc))
    if sp.get("inv_saved"):
        print(f"  Hinweis: {isk(sp['inv_saved'])}/Stk Invention wurden NICHT "
              f"berechnet (eigene BPCs).")
    return sc, pc


def ablation(name, type_id, menge, price_fn, recipes, opts):
    """Eine Annahme nach der anderen umschalten - welche schliesst die Luecke?"""
    basis_s, basis_p = _scanner_sicht(type_id, price_fn, recipes, opts)[0], \
        _plan_sicht(type_id, menge, price_fn, recipes, opts)[0]
    if basis_s is None or not basis_p:
        return
    print(f"\n--- Ablation {name}: was aendert die Luecke von "
          f"{isk(basis_p - basis_s)}? ---")
    varianten = [
        ("ohne eigene BPCs", dict(opts, inv_owned_runs={}, inv_manual_override={})),
        ("ohne Invention ueberhaupt", dict(opts, invention=False)),
        ("ohne Adjusted-Rueckfall", dict(opts, adjusted_prices={})),
        ("ohne Rig-ME-Maps", dict(opts, me_map={}, me_map_reaction={},
                                  rig_me_map={})),
        ("Reaktionen kaufen statt bauen", dict(opts, build_reactions=False)),
    ]
    for label, o in varianten:
        s = _scanner_sicht(type_id, price_fn, recipes, o)[0]
        p = _plan_sicht(type_id, menge, price_fn, recipes, o)[0]
        if s is None or not p:
            print(f"  {label:32} nicht berechenbar")
            continue
        print(f"  {label:32} Scanner {isk(s, suffix=False):>16}   "
              f"Bauplan {isk(p, suffix=False):>16}   Luecke "
              f"{isk(p - s, suffix=False):>16}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("item", nargs="*", help="Item-Name oder type_id")
    ap.add_argument("--menge", type=int, default=10)
    args = ap.parse_args()

    if not industry.sde_ready():
        print("SDE fehlt - erst im Tool die Blaupausendaten laden.")
        return 1
    snapshot = store.get_snapshot()
    if not snapshot:
        print("Kein Markt-Snapshot - erst einmal 'Markt-Scan' laufen lassen.")
        return 1
    price_map = {s["type_id"]: s["sell_min"] for s in snapshot if s["sell_min"] > 0}

    win = MainWindow()
    recipes = industry.Recipes()
    # EXAKT die Optionen des Scans - beide Haelften, wie in compute_build().
    opts = win._bau_scan_build_opts(recipes)
    win._bau_scan_build_opts_esi(opts, recipes)
    print(f"Scan-Optionen: ME {opts.get('me'):.2f} % · Reaktions-ME "
          f"{opts.get('me_reaction'):.2f} % · eigene BPCs für "
          f"{len(opts.get('inv_owned_runs') or {})} Blaupausen · "
          f"{len(opts.get('adjusted_prices') or {})} Adjusted Prices")

    ziele = []
    for a in args.item:
        tid = int(a) if a.isdigit() else industry.type_id_for_name(a)
        if not tid:
            print(f"Unbekanntes Item: {a}")
            continue
        ziele.append((a, tid))
    if not ziele:
        namen = store.cached_names([t for t in list(price_map)[:400]])
        for tid in list(price_map):
            bp = recipes.product_to_bp.get(tid)
            if bp and recipes.invention_for_bpc.get(bp[0]):
                ziele.append((namen.get(tid, f"#{tid}"), tid))
            if len(ziele) >= 5:
                break

    for name, tid in ziele:
        vergleiche(name, tid, args.menge, price_map.get, recipes, opts)
        ablation(name, tid, args.menge, price_map.get, recipes, opts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
