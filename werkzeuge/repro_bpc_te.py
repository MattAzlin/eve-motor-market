"""REPRO: 'Eigene BPC' anhaken, dann TE verstellen -> App schliesst sich.

Baut den Bauplan-Dialog offscreen mit einem erfundenen (T2) Endprodukt, hakt
die Checkbox an und verstellt danach den TE-Spinner - genau die vom Nutzer
gemeldete Reihenfolge. Ein harter Absturz zeigt sich hier als Rueckgabecode
-11 (Segfault) bzw. als RuntimeError 'C++ object already deleted'.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
_HOME = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".smoke_home")   # Projektwurzel
os.makedirs(_HOME, exist_ok=True)
for _k in ("HOME", "APPDATA", "USERPROFILE"):
    os.environ[_k] = _HOME

from PySide6.QtWidgets import QApplication, QCheckBox, QSpinBox   # noqa: E402

_app = QApplication.instance() or QApplication([])

from eve_trader import industry as I                              # noqa: E402
from eve_trader.ui.main_window import MainWindow                  # noqa: E402


class _Recipes:
    product_to_bp = {100: (900, I.MANUFACTURING, 1), 200: (901, I.MANUFACTURING, 1)}
    bp_materials = {(900, I.MANUFACTURING): [(200, 4), (300, 10)],
                    (901, I.MANUFACTURING): [(300, 8)]}
    activity_time = {(900, I.MANUFACTURING): 600, (901, I.MANUFACTURING): 300}
    activity_max_runs = {(900, I.MANUFACTURING): 0, (901, I.MANUFACTURING): 0}
    reaction_products = set()
    invention_for_bpc = {900: (899, 10, 0.34, [(300, 2)])}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return True


PRICES = {100: 5000.0, 200: 100.0, 300: 20.0, 899: 1000.0}

win = MainWindow()
win._bd_pricemap = dict(PRICES)
win._bd_recipes = _Recipes()
win._bd_opts = {"me": 0, "te": 0, "job_pct": 0, "build_reactions": False,
                "tree_depth": 4, "invention": True}
win._bd_type = 100
win._bd_qty = 10
_plan = I.production_plan(100, 10, PRICES.get, _Recipes(), dict(win._bd_opts))
_tree = I.build_tree(100, PRICES.get, _Recipes(), dict(win._bd_opts))
_res = {"tree": _tree, "names": {100: "Testship-T2", 200: "Testmat"},
        "sell": 6000.0, "sell_is_contract": False, "plan": _plan}
win._show_build_detail(100, "Testship-T2", _res)
dlg = getattr(win, "_bd_dialog", None)
assert dlg is not None, "Dialog wurde nicht gebaut"

cbs = [c for c in dlg.findChildren(QCheckBox) if "Eigene BPC" in c.text()]
print(f"Checkbox 'Eigene BPC' gefunden: {len(cbs)}")
assert cbs, "Checkbox nicht im Fenster (nie ins Layout gehaengt?)"
cb = cbs[0]

sps = [s for s in dlg.findChildren(QSpinBox) if s.suffix() == " %"]
print(f"Prozent-Spinner im Fenster: {len(sps)}")

print(">>> Checkbox anhaken (loest _bd_full_rebuild aus) ...")
cb.setChecked(True)
_app.processEvents()          # deleteLater() der alten Karten wirklich ausfuehren
print("    Rebuild ueberstanden.")

# Nach dem Rebuild neu suchen - die Widgets koennten woanders haengen.
sps2 = [s for s in dlg.findChildren(QSpinBox) if s.suffix() == " %"]
print(f"    Prozent-Spinner danach: {len(sps2)}")
for s in sps2:
    print(f"    - Tooltip: {s.toolTip()[:60]!r}")

te = [s for s in sps2 if "Zeit-Effizienz" in s.toolTip()]
print(f">>> TE-Spinner gefunden: {len(te)}")
if not te:
    print("!!! TE-Spinner ist nach dem Umschalten NICHT MEHR im Fenster.")
    print("    Er wurde mit der alten Karte geloescht - jede weitere")
    print("    Benutzung trifft ein totes C++-Objekt.")
    sys.exit(2)

print(f">>> TE-Spinner aktiv? {te[0].isEnabled()}")
print(">>> TE verstellen (nur setValue - loest KEIN editingFinished aus) ...")
te[0].setValue(12)
_app.processEvents()
print("    ueberstanden.")

# SO BEDIENT ES DER NUTZER: hineinklicken, Wert aendern, wieder hinausklicken.
# Der Fokuswechsel loest editingFinished aus - und DAS haengt am Rebuild.
print(">>> jetzt mit echtem Fokuswechsel (editingFinished) ...")
te[0].setFocus()
_app.processEvents()
te[0].setValue(15)
_app.processEvents()
te[0].clearFocus()            # <- hier feuert editingFinished
_app.processEvents()
print("    ueberstanden.")
sys.exit(0)
