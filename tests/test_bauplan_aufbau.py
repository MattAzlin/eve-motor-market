"""AUFBAU-TEST: baut das Hauptfenster UND den Bauplan-Dialog wirklich.

WARUM ES DIESEN TEST GIBT
-------------------------
In einer einzigen Session ging der Bauplan-Dialog ZWEIMAL nach UI-Aenderungen
nicht mehr auf - beide Male bei gruenen Logiktests und 0 Lint-Befunden:

  1. `sell = _hp` in rebuild() machte einen geerbten Namen lokal
     -> UnboundLocalError beim OEFFNEN jedes Bauplans.
  2. Das Verkaufscharakter-Dropdown wurde erzeugt, verdrahtet, betooltippt -
     und nie ins Layout gehaengt. Sichtbar war nur die Beschriftung.

Beide Fehlerklassen sind mit reiner Logikpruefung NICHT zu finden: die eine
schlaegt erst beim Ausfuehren zu, die andere sieht im Code voellig korrekt
aus. Gefunden werden sie nur, indem man den Dialog TATSAECHLICH baut und
danach nachsieht, ob die Bedienelemente auch im Fenster gelandet sind.

Ein Widget, das nie in ein Layout gehaengt wurde, hat KEINEN Parent - es
taucht in `dlg.findChildren(...)` also gar nicht erst auf. Genau darauf
stuetzen sich die Pruefungen unten.

Laeuft ohne Bildschirm (QT_QPA_PLATFORM=offscreen) und ohne ESI.
"""
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# PROJEKTWURZEL (Ordnerstruktur 18.09.2026): die Suite liegt in tests\,
# alles, was sie liest, relativ zur Wurzel (eve_trader\, pruefe.py, ...).
# Deshalb: Wurzel bestimmen, dorthin wechseln, auf den Importpfad legen.
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_ROOT)
sys.path.insert(0, _ROOT)
_HOME = os.path.join(_ROOT, ".smoke_home")
os.makedirs(_HOME, exist_ok=True)
for _k in ("HOME", "APPDATA", "USERPROFILE"):
    os.environ[_k] = _HOME

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QTabWidget, QApplication, QComboBox, QPushButton, QLabel,
                               QTableWidget, QTreeWidget, QCheckBox,
                               QPlainTextEdit, QWidget)

_app = QApplication.instance() or QApplication([])

# (b79) FEHLER.LOG-NETZ: _log_exception schreibt abgefangene Ausnahmen neben
# das Startskript (argv[0] = diese Datei). Was der Lauf dort anhaengt, wird
# am Ende gelesen - ein AttributeError in einem try/except ist sonst unsichtbar
# (18.09.2026: "'MainWindow' object has no attribute '_bd_groups'" sechsmal je
# Prueflauf, nur in fehler.log des Nutzers zu sehen).
_FLOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fehler.log")   # neben argv[0]
try:
    _FLOG_START = os.path.getsize(_FLOG)
except OSError:
    _FLOG_START = 0

from eve_trader.ui.main_window import MainWindow          # noqa: E402
from eve_trader import industry as I                      # noqa: E402

# DAS EINRICHTUNGS-FENSTER FUER JEDES HAUPTFENSTER STILLLEGEN (Sitzung 17).
# Es ist MODAL und springt an, sobald die Testumgebung wie eine
# Neuinstallation aussieht - und genau so sieht `.smoke_home` aus.
# VORHER (Sitzung 16) geschah das nur an `win` (b1). b23 baut aber zwei
# WEITERE Hauptfenster (`_w_en`, `_w_de`); deren 300-ms-Zeitgeber oeffnete
# das Fenster nach der Schlusszeile, und die Suite hing endlos - mit
# "733/733 gruen" schon auf dem Schirm. `pruefe.py` kam nie zur Aussage, und
# die Rotprobe haette je Mutation die volle Stunde Notausstieg gewartet.
# DARUM AN DER KLASSE: jedes Hauptfenster, auch ein kuenftiges, ist erfasst.
# GEPRUEFT wird das Fenster trotzdem - separat in b58, am Fenster gemessen.
def _einrichtung_still(self, *_a, **_k):
    return None


MainWindow._erste_einrichtung_pruefen = _einrichtung_still

# DIE DREI ERSTSTART-FRAGEN EBENSO (Sitzung 17, Nutzer-Screenshot Windows).
# Rezeptfrage (400 ms), "kein Charakter" (250 ms), Verlaufsfrage (4000 ms)
# pruefen einen Merker in der settings.json. UNTER WINDOWS liegt die aber
# woanders als im Container (APPDATA -> `.smoke_home\EVE Motor Market\`,
# nicht `.smoke_home/.local/share/...`) und hat einen eigenen Stand - beim
# Nutzer fehlte der Merker, die Rezeptfrage ging auf, b59 wurde rot, und
# b2w verlor mitten im Test ein Widget (Qt raeumt verzoegert Geloeschtes
# ab, solange ein modales Fenster laeuft - Vermutung, bei ihm gesehen,
# hier nicht nachstellbar). EINE PRUEFUNG, DIE JE NACH UMGEBUNG ANDERS
# AUSGEHT, PRUEFT NICHTS - also stilllegen, wie das Einrichtungsfenster.
# Die Fragen selbst pruefen aa291 (Merker) und b57 (Buehne) separat.
MainWindow._erststart_rezepte_anbieten = _einrichtung_still
MainWindow._erststart_ohne_charakter = _einrichtung_still
# Sitzung 17: die Tutorial-Erstfrage ebenso - sonst bliebe sie im Test als
# modales Fenster stehen und b59 wuerde zu Recht rot.
MainWindow._tutorial_erstfrage = _einrichtung_still
MainWindow._frage_verlauf_laden = _einrichtung_still

# NETZ, FALLS DAS STILLLEGEN DOCH EINMAL FEHLT: das Fenster vermerkt sich
# und kehrt sofort zurueck, statt zu blockieren. Aus einem endlosen Haenger
# ohne Ausgabe wird so eine BENANNTE rote Pruefung (b59). `auto=False`
# verhindert, dass der Testlauf die Download-Kette anstoesst (140 MB).
# b58 baut das Fenster selbst mit auto=False und ruft nie exec() - es
# merkt vom Netz nichts.
import eve_trader.ui.erst_einrichtung as _ee_mod          # noqa: E402
_EINRICHTUNG_UNBESTELLT = []


class _EinrichtungImTest(_ee_mod.ErstEinrichtung):
    def __init__(self, fenster, auto=True):
        if auto:
            _EINRICHTUNG_UNBESTELLT.append(type(fenster).__name__)
        super().__init__(fenster, auto=False)

    def exec(self):
        return 0


_ee_mod.ErstEinrichtung = _EinrichtungImTest

# NETZ 2: JEDES ANDERE MODALE FENSTER (Sitzung 17). Gemessen: nach dem
# Stilllegen oben hing die Suite WEITER - an `QMessageBox.warning` im
# ESI-Nachlauf des Bauplans ("No ESI access"). Ein modales Fenster ohne
# Bildschirm wartet auf einen Klick, der nie kommt.
# Die Wache sieht alle 250 ms nach: steht ein DIALOG laenger als 3 s modal
# offen, wird er vermerkt und geschlossen. b59 macht den Vermerk rot.
# Kein Test oeffnet selbst ein modales Fenster (gemessen: kein exec() in
# dieser Datei) - die Wache kann also nichts Gewolltes stoeren.
# `activeModalWidget` WIRD HIER FESTGEHALTEN: b57 taeuscht die Funktion
# zeitweise vor (liefert dann `win`). Die Wache fragt immer die echte, und
# sie fasst nur Dialoge an - nie das Hauptfenster.
import time as _time_netz                                  # noqa: E402
from PySide6.QtCore import QTimer as _QT_netz              # noqa: E402
from PySide6.QtWidgets import QDialog as _QD_netz          # noqa: E402
_modal_echt = QApplication.activeModalWidget
_MODAL_UNBESTELLT = []
_modal_seit = {}


def _modal_wache():
    _w = _modal_echt()
    if not isinstance(_w, _QD_netz):
        _modal_seit.clear()
        return
    _t0 = _modal_seit.setdefault(id(_w), _time_netz.time())
    if _time_netz.time() - _t0 >= 3.0:
        _text = getattr(_w, "text", lambda: "")()
        _MODAL_UNBESTELLT.append(f"{type(_w).__name__} '{_w.windowTitle()}': "
                                 f"{str(_text)[:80]}")
        _modal_seit.pop(id(_w), None)
        _w.done(0)


_modal_timer = _QT_netz()
_modal_timer.setInterval(250)
_modal_timer.timeout.connect(_modal_wache)
_modal_timer.start()

# Quelltext einmal einlesen: einige Pruefungen schauen auf die STRUKTUR des
# Codes (Reihenfolge von Layout-Aufrufen o.ae.), die man am fertigen Widget
# nicht mehr ablesen kann.
import glob as _glob8b
# Sitzung 8: alle UI-Dateien zusammenhaengen (nicht nur main_window.py) -
# sonst wird jede Text-Pruefung blind, sobald Code in ein Mixin wandert.
# main_window.py bleibt vorne (siehe test_bestand_herkunft.py).
_ui8b = os.path.join(_ROOT,
                     "eve_trader", "ui")
_mw8b = os.path.join(_ui8b, "main_window.py")
_src_mw = "\n".join(
    open(_d, encoding="utf-8").read()
    for _d in [_mw8b] + sorted(d for d in _glob8b.glob(os.path.join(_ui8b, "*.py"))
                               if d != _mw8b))

_ok = 0
# UEBERSETZUNG FRUEH VERFUEGBAR: mehrere Pruefungen suchen Knoepfe ueber
# ihren Text und muessen das sprachunabhaengig tun.
from eve_trader.sprache import t as _t4
from PySide6.QtWidgets import QPushButton as _QPB23

_fail = []


def check(label, cond):
    global _ok
    if cond:
        _ok += 1
    else:
        _fail.append(label)


def eq(label, got, want):
    check(f"{label}  (erhalten {got!r}, erwartet {want!r})", got == want)


def _pos_von(hay, needle, start=0):
    """Position von `needle` in `hay` - ohne die Suite abzureissen.

    WARUM ES DIESEN HELFER GIBT (Sitzung 10): im Bestand standen 71 rohe
    `.index()`-Aufrufe. Verschwindet der gesuchte Anker durch einen Umbau,
    WIRFT `.index()` - und reisst die ganze Suite mit, statt EINE rote
    Pruefung zu setzen. Genau das ist bei Schnitt 3 passiert: aa147 stuerzte
    ab, alle folgenden Pruefungen liefen nie, und die Rotprobe wertete das
    als "blind" statt als "rot".

    Hier stattdessen: fehlt der Anker, gibt es eine benannte rote Pruefung
    und die Suite laeuft weiter. Rueckgabe 0, damit ein anschliessender
    Ausschnitt definiert bleibt (er ist dann falsch - aber die zugehoerige
    Pruefung ist ja bereits rot).
    """
    _f = getattr(hay, "find", None)
    if _f is not None:
        _p = _f(needle, start)
        if _p < 0:
            check(f"ANKER FEHLT: {needle!r:.60} nicht gefunden", False)
            return 0
        return _p
    try:
        return hay.index(needle, start)
    except (ValueError, TypeError):
        check(f"ANKER FEHLT: {needle!r:.60} nicht gefunden", False)
        return 0



class _Recipes:
    """Minimalrezept: 1 Testship <- 10 Testmat."""
    product_to_bp = {100: (900, I.MANUFACTURING, 1)}
    bp_materials = {(900, I.MANUFACTURING): [(200, 10)]}
    activity_time = {(900, I.MANUFACTURING): 60}
    activity_max_runs = {(900, I.MANUFACTURING): 0}
    reaction_products = set()
    invention_for_bpc = {}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return t in self.product_to_bp


# GEMERKTE ANSICHTS-FILTER VOR DEM START LOESCHEN (18.09.2026). b46 prueft
# die VORGABEN der Blueprints-Haken; ein vorheriger Lauf kann aber ueber
# closeEvent -> _filter_merken andere Haken in die Test-Settings geschrieben
# haben (so geschehen: b76 liess "profitable only" AUS zurueck, weil die
# Settings vorher gar kein ui_filter kannten - Lauf 1 gruen, Lauf 2 b46
# rot, nur beim Nutzer, weil seine .smoke_home aelter war als b76). Das
# Merken selbst prueft b76 ueber die beiden Methoden, nicht ueber den
# Neustart - hier darf es also weg.
try:
    from eve_trader import config as _cfg0
    _s0 = _cfg0.load_settings()
    if "ui_filter" in _s0:
        _s0.pop("ui_filter", None)
        _cfg0.save_settings(_s0)
except Exception as _e0:                                 # pragma: no cover
    print(f"(Hinweis) ui_filter nicht geloescht: {type(_e0).__name__}: {_e0}")


# ---------------------------------------------------------------- (b1)
# Das HAUPTFENSTER muss sich ueberhaupt bauen lassen.
try:
    win = MainWindow()
    # Das Einrichtungs-Fenster ist oben an der KLASSE stillgelegt
    # (`_einrichtung_still`, Sitzung 17) - hier nichts mehr zu tun.
    check("b1 MainWindow laesst sich bauen", True)
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    print(f"(b) Bauplan-Aufbau: 0/1 gruen\n  FEHLER: MainWindow: {e}")
    sys.exit(1)

# ---------------------------------------------------------------- (b1b)
# BAU-KALENDER entfernt (Nutzer: "zu viel und zu unnoetig"). Die Seite wird
# nicht mehr gebaut, bleibt aber als LEERER Platzhalter im Stapel - sonst
# verschieben sich die Seiten-Indizes und "Strukturen" (4) bricht.
_btexts0 = [b.text() for b in win.findChildren(QPushButton) if b.text()]
check("b1b Kalender-Knopf ist weg",
      not any("Kalender" in b for b in _btexts0))
eq("b1b Kalender-Seite ist aus dem Stapel raus", win.b_stack.count(), 4)
eq("b1b vier Navigations-Knoepfe", len(win._bau_page_btns), 4)
_pages_ok = True
for _i in range(win.b_stack.count()):
    try:
        win.b_stack.setCurrentIndex(_i)
        _app.processEvents()
    except Exception:
        _pages_ok = False
check("b1b alle Seiten bleiben schaltbar", _pages_ok)
# Rail-Ordnung (Nutzer): "Neuer Bauplan" steht unter PRODUKTION, ueber
# "Meine Bauplaene" - unter PLANEN bleiben nur Scanner + Meine Blueprints.
_src_rail = open(os.path.join(_ROOT,
                              "eve_trader", "ui", "main_window.py"),
                 encoding="utf-8").read()
# .find() statt .index(): ein fehlender Anker soll die PRUEFUNG rot machen,
# nicht die ganze Suite abbrechen (Sitzung 9: der Symbol-Umbau nahm dem
# alten Emoji-Anker den Boden, und das ungeschuetzte .index() riss per
# ValueError ALLE Folge-Pruefungen mit).
_i_plan = _src_rail.find('header(t("PLANNING")')
_i_prod = _src_rail.find('header(t("PRODUCTION")')
# Sitzung 17: der Knopf wird an self gemerkt (das Tutorial hebt ihn hervor).
# NICHT nach dem blossen Text suchen - "New build plan" ist auch der
# FENSTERTITEL und steht weiter oben in der Datei.
_i_neu = _src_rail.find('self._bau_newplan_btn = tool_btn(')
_i_mine = _src_rail.find('b_plans = page_btn(')
check("b1b alle vier Rail-Anker sind auffindbar",
      min(_i_plan, _i_prod, _i_neu, _i_mine) >= 0)
check("b1b 'Neuer Bauplan' steht unter PRODUKTION", 0 <= _i_prod < _i_neu)
check("b1b und ueber 'Meine Bauplaene'", 0 <= _i_neu < _i_mine)
check("b1b unter PLANEN nur noch zwei Eintraege",
      _src_rail[_i_plan:_i_prod].count("page_btn(") == 2
      and "tool_btn(" not in _src_rail[_i_plan:_i_prod])
eq("b1b Strukturen ist jetzt Index 3",
   (win.b_stack.setCurrentIndex(3), win.b_stack.currentIndex())[1], 3)

# ---------------------------------------------------------------- (b2)
# Der BAUPLAN-DIALOG muss sich mit echten Plandaten bauen lassen. Genau hier
# schlug der UnboundLocalError zu - rebuild() laeuft beim Aufbau mit.
PRICES = {100: 5000.0, 200: 100.0}
win._bd_pricemap = dict(PRICES)
win._bd_recipes = _Recipes()
# MIT BESTAND: nur so laeuft der Zweig, der die Unterzeile "davon X aus
# Bestand" fuellt - genau dort entstand das streunende "python"-Fenster.
# Ohne Bestand waere (b8) blind.
win._bd_opts = {"me": 0, "te": 0, "job_pct": 0, "build_reactions": False,
                "tree_depth": 4, "stock": {200: 40}}
win._bd_type = 100
win._bd_qty = 10
_plan = I.production_plan(100, 10, PRICES.get, _Recipes(), dict(win._bd_opts))
_tree = I.build_tree(100, PRICES.get, _Recipes(), dict(win._bd_opts))
_res = {"tree": _tree, "names": {100: "Testship", 200: "Testmat"},
        "sell": 6000.0, "sell_is_contract": False, "plan": _plan}
_dlg = None
# SEIT DER SPERRE (Sitzung 13, b40) darf nur EIN Bauplan offen sein - ein
# zweites _show_build_detail bringt ein MODALES Popup und wartet auf einen
# Klick, den es im Testbetrieb nie gibt. Die Suite oeffnet unten aber rund
# zehnmal einen frischen Dialog. Deshalb: vor jedem Oeffnen den vorigen
# schliessen - so, wie der Nutzer es jetzt auch tun muss. b40 prueft die
# Sperre selbst und ruft dafuer die UNGEWICKELTE Methode.
_sbd_echt = win._show_build_detail
def _sbd_frisch(tid, name, res):
    _d = win._offener_bauplan()
    if _d is not None:
        _d.close(); _app.processEvents()
    return _sbd_echt(tid, name, res)
win._show_build_detail = _sbd_frisch
try:
    win._show_build_detail(100, "Testship", _res)
    _dlg = getattr(win, "_bd_dialog", None)
    check("b2 Bauplan-Dialog laesst sich bauen", True)
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b2 Bauplan-Dialog: {type(e).__name__}: {e}")

check("b2 Dialog ist erreichbar (_bd_dialog gesetzt)", _dlg is not None)

# ---------------------------------------------------------------- (b2f)
# EINFUEGE-FELD AUF DER VERKAUFSLISTE (Nutzer-Wunsch, Sitzung 8): Hangar-
# Liste rein, "Verkaufspreise kopieren" raus. Ein Widget ohne Layout hat
# keinen Parent und ist unsichtbar - genau so faellt so etwas still aus.
_pastebox = getattr(win, "_sell_paste", None)
check("b2f Einfuege-Feld auf der Verkaufsliste existiert", _pastebox is not None)
if _pastebox is not None:
    check("b2f Einfuege-Feld haengt in einem Layout",
          _pastebox.parentWidget() is not None)
    # SPRACHUNABHAENGIG: die Zusage ist "das Feld erklaert sich selbst",
    # nicht "es enthaelt das deutsche Wort einfuegen".
    check("b2f Einfuege-Feld erklaert sich selbst",
          len(_pastebox.placeholderText() or "") > 30)
    check("b2f Statuszeile daneben vorhanden",
          getattr(win, "_sell_paste_info", None) is not None)
check("b2f der Knopf ist verdrahtet",
      callable(getattr(win, "_sell_paste_prices", None)))

# ---------------------------------------------------------------- (b2g)
# KNOPFDRUCK WIRKLICH AUSLOESEN. b2f prueft nur, dass es die Methode GIBT -
# das hat einen echten Absturz beim Nutzer NICHT verhindert: `_run` erwartet
# ein Worker-OBJEKT, bekam aber die nackte Job-Funktion
# ("AttributeError: 'function' object has no attribute 'done'").
# "Existiert" ist eben nicht "funktioniert". Deshalb wird hier der ganze Weg
# durchlaufen: Text einfuegen -> Namen aufloesen -> Orderbuch (Attrappe) ->
# Preise rechnen -> Zwischenablage.
try:
    import eve_trader.hubs as _hubs2g
    import eve_trader.store as _store2g
    from PySide6.QtWidgets import QApplication as _QApp2g

    _orig_fetch2g = _hubs2g.fetch_hub_orders
    _orig_names2g = _store2g.name_to_type_id
    _orig_run2g = win._run
    _hubs2g.fetch_hub_orders = lambda r, s, progress=None: {
        34: {"sell_min": 1_000_000.0},      # genau auf der Zehnerpotenz
        35: {"sell_min": 0.05},             # billig: 2 Nachkommastellen noetig
    }
    _store2g.name_to_type_id = lambda: {"tritanium": 34, "pyerite": 35}
    # Ersatz-_run, der den Job SOFORT ausfuehrt. Bekommt es keinen Worker,
    # fliegt es hier genauso wie beim Nutzer - genau das soll es.
    win._run = lambda worker, done_cb, fail_cb=None, **kw: done_cb(
        worker._fn(*worker._args, **worker._kwargs))
    win._sell_paste.setPlainText("Tritanium\t5.000\nPyerite\t12\nGibtsNicht\t1")
    win._sell_paste_prices()
    _abl2g = (_QApp2g.clipboard().text() or "").splitlines()
    check("b2g Knopfdruck laeuft ohne Absturz durch", bool(_abl2g))
    eq("b2g je Eingabezeile genau eine Ausgabezeile", len(_abl2g), 3)
    eq("b2g Tick an der Zehnerpotenz stimmt", _abl2g[0], "Tritanium 999900.00")
    eq("b2g billiges Item bekommt zwei Nachkommastellen",
       _abl2g[1], "Pyerite 0.04")
    check("b2g unbekannter Name bleibt als Platzhalter stehen",
          _abl2g[2].endswith("?"))
    check("b2g Statuszeile meldet das Ergebnis",
          # Sitzung 17: uebersetzt - beide Sprachen akzeptieren.
          any(_w in (win._sell_paste_info.text() or "")
              for _w in ("kopiert", "copied")))
except Exception as _e2g:                                # pragma: no cover
    _fail.append(f"b2g Verkaufspreise kopieren: {type(_e2g).__name__}: {_e2g}")
finally:
    try:
        _hubs2g.fetch_hub_orders = _orig_fetch2g
        _store2g.name_to_type_id = _orig_names2g
        win._run = _orig_run2g
        win._sell_paste.setPlainText("")
    except Exception:
        pass

# ---------------------------------------------------------------- (b2i)
# EINKAUFSWAGEN-WERKZEUGE (Layout-Programm, Sitzung 8): sieben Knoepfe
# wurden zu Hauptaktion + Werkzeuge-Menue (Bauplan-Muster). Der Test
# DRUECKT eine Menue-Aktion und prueft, dass der dahinterliegende
# (unsichtbare) Knopf den Handler wirklich ausloest - genau die Verkabelung,
# die beim Umbau am ehesten reisst.
try:
    _pairs2i = getattr(win, "_sh_tool_pairs", None)
    check("b2i das Werkzeuge-Menue hat vier Eintraege (load/check/sugg/clear)",
          _pairs2i is not None and len(_pairs2i) == 4)
    _rufe2i = []
    _orig_load2i = win.shopping_load_prices
    win.shopping_load_prices = lambda *a, **k: _rufe2i.append("load")
    _pairs2i[0][0].trigger()
    check("b2i Menue-Aktion drueckt den Knopf, der Knopf ruft den Handler",
          _rufe2i == ["load"])
    check("b2i die vier Knoepfe sind unsichtbar, aber am Leben",
          all(not _b.isVisible() for _a, _b in _pairs2i))
    # receivers() nimmt in PySide6 nur den C++-Signaturstring - stattdessen
    # FUNKTIONAL: Klick auf die Hauptaktion muss den Kopier-Handler rufen.
    _orig_copy2i = win.shopping_copy
    win.shopping_copy = lambda *a, **k: _rufe2i.append("copy")
    # click() ist bei deaktiviertem Knopf (leere Liste) ein No-Op - das
    # Signal direkt emittieren prueft die VERKABELUNG unabhaengig davon.
    win._sh_copy_btn.clicked.emit()
    check("b2i Hauptaktion Multibuy bleibt sichtbar verkabelt",
          "copy" in _rufe2i)
    win.shopping_copy = _orig_copy2i
    # Zweite Aufraeurunde (Nutzer): Eingabezeile + Erloes-/Gewinn-Karte weg,
    # Vorschlag-Panel als Widget-Aktion im Werkzeuge-Menue - Prozentfeld und
    # "Als Menge uebernehmen" muessen FUNKTIONIEREND mitgezogen sein.
    check("b2i Eingabezeile ist aus der Ansicht (Handler lebt weiter)",
          not win.sh_name.parentWidget().isVisible()
          and callable(win.shopping_add))
    check("b2i Erloes- und Gewinn-Karte sind ausgeblendet, Kosten bleibt",
          not win.sh_t_rev_c.isVisible() and not win.sh_t_profit_c.isVisible()
          and win.sh_t_cost_c.parentWidget() is not None)
    check("b2i das Vorschlag-Panel haengt als Widget-Aktion im Menue",
          getattr(win, "_sh_sug_wa", None) is not None
          and win._sh_sug_wa in win._sh_tools_menu.actions())
    check("b2i das Prozentfeld lebt im Menue weiter (25 % Startwert)",
          win._sh_sug_share.value() == 25
          and win._sh_sug_share.parent() is not None)
    _orig_apply2i = win._apply_suggestion_qty
    win._apply_suggestion_qty = lambda *a, **k: _rufe2i.append("apply")
    win._sh_sug_apply.clicked.emit()
    check("b2i 'Als Menge uebernehmen' bleibt im Menue verkabelt",
          "apply" in _rufe2i)
    win._apply_suggestion_qty = _orig_apply2i
    # ITEM-BILDER (Nutzer: "da fehlen noch Bilder"): der Wagen muss den
    # Hintergrund-Nachtrag ANSTOSSEN - vormerken allein holt nichts. Render
    # mit einem unbekannten Item laufen lassen; danach muss der Prefetch
    # angestossen worden sein (Attrappe zaehlt den Aufruf).
    _pf2i = []
    _orig_pf2i = win._icon_prefetch_pending
    win._icon_prefetch_pending = lambda cb=None: _pf2i.append(cb) or False
    try:
        win._render_shopping()
    except Exception as _re2i:
        _fail.append(f"b2i Render nach Umbau: {type(_re2i).__name__}: {_re2i}")
    check("b2i der Wagen stoesst den Bilder-Nachtrag an (mit Re-Render-Callback)",
          len(_pf2i) == 1 and _pf2i[0] == win._render_shopping)
    win._icon_prefetch_pending = _orig_pf2i
    # Runde 3 + 4 (Umentscheidung): der Wagen mischt Strategien (Daytrade
    # = Buy-to-Sell, Swing = Sell-to-Sell) - EINE Marge-/Gewinn-Formel
    # waere fuer die Haelfte falsch. Sichtbar nur strategie-unabhaengige
    # Zahlen; Marge (6) und Gewinn (8) sind mit AUSGEBLENDET.
    check("b2i Buy-Order- und Erloes-Spalte sind ausgeblendet",
          win.sh_table.isColumnHidden(4) and win.sh_table.isColumnHidden(7))
    check("b2i Marge- und Gewinn-Spalte sind ausgeblendet (Strategie-Mix)",
          win.sh_table.isColumnHidden(6) and win.sh_table.isColumnHidden(8))
    from eve_trader.ui import theme as _th2i
    _mwsrc2i = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    _rs2i = _mwsrc2i[_pos_von(_mwsrc2i, "def _render_shopping"):]
    _rs2i = _rs2i[:_pos_von(_rs2i, "\n    def ", 10)]
    check("b2i das Auge ist weg, das rote Kreuz bleibt",
          "\U0001F441" not in _rs2i and 'rmb = QPushButton("✕")' in _rs2i)
    check("b2i Kosten-Karte rot und praesent, Gewinn-Karte WIEDER versteckt",
          ("color:" + _th2i.RED) in win.sh_t_cost.styleSheet()
          and not win.sh_t_cost_c.isHidden()
          and win.sh_t_profit_c.isHidden())
    check("b2i Bauplan-Optik: 32er-Icons, kein Gitter",
          win.sh_table.iconSize().width() == 32
          and not win.sh_table.showGrid())
except Exception as _e2i:                                # pragma: no cover
    _fail.append(f"b2i Einkaufswagen-Werkzeuge: {type(_e2i).__name__}: {_e2i}")
finally:
    try:
        win.shopping_load_prices = _orig_load2i
    except Exception:
        pass

# ---------------------------------------------------------------- (b2s)
# SIDEBAR-BREITE (Nutzer, ZWEIMAL gemeldet: "da steht nur MOTOR MARKE").
# Zweimal hatte ich eine feste Breite GERATEN (196, dann 232) - beide Male
# zu knapp. Die noetige Breite haengt an der Schrift des Zielrechners, eine
# feste Zahl kann das nicht loesen. Jetzt wird gemessen; hier FUNKTIONAL
# geprueft, dass der Schriftzug wirklich vollstaendig Platz bekommt.
# NEU GEFASST IN SITZUNG 11: der Schriftzug "MOTOR MARKET" als eigenes
# Textfeld ist ERSATZLOS entfallen - er steht jetzt im Logo-Bild selbst
# (Nutzer: "Motor Market muss nicht extra da stehen, da das schon im PNG
# drin steht"). Damit ist der zweimal gemeldete Beschnitt strukturell
# erledigt: ein Bild skaliert, eine Schrift nicht. Die Zusage lautet jetzt
# umgekehrt - das LOGO richtet sich nach der Sidebar.
try:
    _mwsrc2s = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    _sb2s = getattr(win, "_sidebar_widget", None)
    _logo2s = getattr(win, "_brand_logo", None)
    check("b2s Sidebar und Logo sind erreichbar",
          _sb2s is not None and _logo2s is not None)
    check("b2s der Schriftzug steht nicht mehr doppelt daneben",
          getattr(win, "_brand_label", None) is None)
    # ANZEIGEN, DANN MESSEN: ohne show() rechnet Qt die Anordnung nicht
    # durch, und jedes Widget meldet seine HOECHSTbreite - die Sidebar sass
    # dann scheinbar auf 420 statt auf 232, und die Pruefung fiel um, obwohl
    # im echten Fenster alles stimmte.
    win.show()
    win.resize(1280, 800)
    _app.processEvents()
    win._sidebar_breite_anpassen()
    _app.processEvents()
    _pm2s = _logo2s.pixmap()
    check(f"b2s das Logo nutzt die Sidebar-Breite "
          f"({_pm2s.width()} bei Sidebar {_sb2s.width()})",
          not _pm2s.isNull() and _pm2s.width() >= _sb2s.width() - 24)
    check("b2s es bleibt innerhalb der Sidebar (kein Ueberstand)",
          _pm2s.width() <= _sb2s.width())
    check("b2s es ist deutlich groesser als die alten 30 px",
          _pm2s.width() >= 96)
    # NACH OBEN BEGRENZT: sonst schiebt ein sehr breites Fenster das Logo
    # so gross, dass die Werkzeugliste aus dem Fenster faellt.
    _sb2s.setMinimumWidth(420)
    win._side_roll.setMinimumWidth(420)
    win.resize(1600, 900)
    _app.processEvents()
    win._sidebar_breite_anpassen()
    check(f"b2s ... aber nach oben begrenzt ({_logo2s.pixmap().width()})",
          _logo2s.pixmap().width() <= 240)
    _sb2s.setMinimumWidth(232)
    win._side_roll.setMinimumWidth(232)
    check("b2s die Breite ist NICHT fest verdrahtet",
          "sidebar.setFixedWidth(" not in _mwsrc2s)
    check("b2s die Sidebar frisst den Tab-Bereich nicht auf",
          _sb2s.maximumWidth() <= 420)
except Exception as _e2s:                                # pragma: no cover
    _fail.append(f"b2s Sidebar-Logo: {type(_e2s).__name__}: {_e2s}")

# ---------------------------------------------------------------- (b2r)
# LOGO IM TOOL (Nutzer, Sitzung 8: "finde einen geeigneten Ort fuer das
# Logo und Motor Market im Tool"). Drei Orte, FUNKTIONAL geprueft - eine
# Quelltext-Suche wuerde nicht merken, wenn das Icon leer bleibt.
try:
    from eve_trader.ui import icons as _ic2r
    from eve_trader.ui import theme as _th2r
    import os as _os2r
    _thq2r = open("eve_trader/ui/theme.py", encoding="utf-8").read()
    _thq2r = _thq2r[_pos_von(_thq2r, "QLabel#Brand"):][:400]
    check("b2r das Fenster traegt ein Symbol (Titelleiste/Taskleiste)",
          not win.windowIcon().isNull())
    check("b2r das Symbol liegt in mehreren Groessen vor (16 bis 256)",
          {s.width() for s in _ic2r.logo_icon().availableSizes()}
          >= {16, 32, 48, 256})
    # GEGEN DIE EINE QUELLE pruefen, nicht gegen einen abgetippten Namen:
    # seit Sitzung 11 heisst das Tool "EVE Motor Market", und der Name steht
    # nur noch in eve_trader/__init__.py. Eine Pruefung mit fest
    # eingetipptem Namen waere bei jeder Umbenennung rot geworden, ohne dass
    # etwas kaputt ist.
    from eve_trader import APP_NAME as _APP2r
    check("b2r der Fenstertitel nennt den Namen",
          win.windowTitle() == _APP2r)
    # Sidebar: Logo NEBEN dem Schriftzug, beide sichtbar.
    from PySide6.QtWidgets import QLabel as _QLabel2r
    _brands = [w for w in win.findChildren(_QLabel2r)
               if w.objectName() == "Brand"]
    check("b2r der Marken-Bereich sitzt in der Sidebar",
          getattr(win, "_brandbox", None) is not None)
    _mit_pix = [w for w in win.findChildren(_QLabel2r)
                if w.toolTip() == _APP2r
                and not w.pixmap().isNull()]
    check("b2r und daneben sitzt das Logo als Bild",
          bool(_mit_pix) and _mit_pix[0].pixmap().width() >= 20)
    # LOGO KOMMT SEIT SITZUNG 11 AUS EINER BILDDATEI (Nutzer-Vorlage
    # assets/logo.png, blau statt der frueheren goldenen Wabe). Die alten
    # Pruefungen schrieben GOLD fest und die gezeichnete Wabenform - beides
    # sind jetzt Eigenschaften der RUECKFALLEBENE, nicht mehr die Zusage.
    # Die Zusage lautet: es rendert ein ECHTES, farbiges Bild. Eine
    # Textsuche wuerde nicht merken, wenn die Datei fehlt und alles leer
    # oder einfarbig bleibt.
    _limg = _ic2r.logo_pixmap(64).toImage()
    _deck2r = sum(1 for y in range(64) for x in range(64)
                  if _limg.pixelColor(x, y).alpha() > 60)
    check(f"b2r das Logo rendert wirklich sichtbar ({_deck2r} Pixel)",
          _deck2r > 400)
    _toene2r = {(_limg.pixelColor(x, y).red() // 16,
                 _limg.pixelColor(x, y).green() // 16,
                 _limg.pixelColor(x, y).blue() // 16)
                for y in range(0, 64, 2) for x in range(0, 64, 2)
                if _limg.pixelColor(x, y).alpha() > 60}
    check(f"b2r ... und ist ein echtes Bild, nicht eine Flaeche "
          f"({len(_toene2r)} Toene)", len(_toene2r) >= 5)
    # ES MUSS DIE BILDDATEI SEIN, nicht die gezeichnete Rueckfallebene.
    # Gegen die Datei selbst verglichen statt gegen eine feste Farbe: so
    # haelt die Pruefung auch, wenn der Nutzer das Logo austauscht. Die
    # erste Fassung zaehlte nur Farbtoene - eine Mutation, die auf die
    # Rueckfallebene umlenkte, blieb damit blind (die zeichnet ja auch ein
    # buntes Bild).
    from PySide6.QtGui import QPixmap as _QPix2r
    _datei2r = _QPix2r(_th2r.asset_pfad("logo.png")).scaled(
        64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation).toImage()
    _gleich2r = sum(
        1 for y in range(0, 64, 4) for x in range(0, 64, 4)
        if _datei2r.pixelColor(x, y) == _limg.pixelColor(x, y))
    _proben2r = len(range(0, 64, 4)) ** 2
    check(f"b2r das angezeigte Logo IST die Bilddatei "
          f"({_gleich2r}/{_proben2r} Proben gleich)",
          _gleich2r >= _proben2r - 2)
    # RUECKFALLEBENE: fehlt die Bilddatei (jemand packt den assets-Ordner
    # nicht mit), muss trotzdem ein Logo erscheinen - lieber ein schlichtes
    # als ein leeres Fenster-Symbol.
    _alt_pfad2r = _th2r.asset_pfad("logo.png") if hasattr(_th2r, "asset_pfad") else ""
    _ic2r._cache.clear()
    _echt_exists2r = _os2r.path.exists
    try:
        _os2r.path.exists = lambda p, _e=_echt_exists2r: (
            False if p.endswith("logo.png") else _e(p))
        # GESCHUETZT AUFRUFEN: faellt die Rueckfallebene aus, gibt die
        # Funktion None zurueck - ein direktes .isNull() wuerde dann mit
        # AttributeError abbrechen und die Pruefung traege einen fremden
        # Namen (beim ersten Anlauf genau so passiert, die Mutation galt
        # als blind).
        try:
            _fallback2r = _ic2r.logo_pixmap(64)
        except Exception:
            _fallback2r = None
        check("b2r ohne Bilddatei gibt es trotzdem ein Logo",
              _fallback2r is not None and not _fallback2r.isNull()
              and _fallback2r.width() == 64)
    finally:
        _os2r.path.exists = _echt_exists2r
        _ic2r._cache.clear()
    check("b2r der Schriftzug nimmt die Logo-Farbe auf (kein zweites Signal)",
          "color: {AMBER};" in _thq2r)
    # Das Logo darf nicht leer gerendert sein.
    _img2r = _ic2r.logo_pixmap(64).toImage()
    _px2r = sum(1 for y in range(64) for x in range(64)
                if _img2r.pixelColor(x, y).alpha() > 30)
    check(f"b2r das Logo zeichnet wirklich etwas ({_px2r} Pixel)",
          _px2r > 200)
except Exception as _e2r:                                # pragma: no cover
    _fail.append(f"b2r Logo: {type(_e2r).__name__}: {_e2r}")

# ---------------------------------------------------------------- (b2q)
# SYMBOLE IM EINSATZ (Nutzer, Sitzung 8: "ja einbauen"). Erste Runde:
# Werkzeuge-Menues (Bauplan/Wagen/Verkaufsliste) und die sichtbaren
# Kopfzeilen-Knoepfe. FUNKTIONAL: die Widgets muessen ein echtes,
# nicht-leeres Icon tragen UND ihr Text darf kein Emoji mehr enthalten -
# beides zusammen, sonst haette man doppelt oder gar nichts.
try:
    def _hat_emoji2q(text):
        return any(ord(c) > 0x2100 for c in text)

    for _name2q, _b2q in (("Aktualisieren", win.refresh_btn),
                          ("Alles aktualisieren", win.global_refresh_btn),
                          ("Blueprints laden", win.bp_refresh_btn)):
        check(f"b2q Knopf {_name2q!r} traegt ein Symbol",
              not _b2q.icon().isNull())
        check(f"b2q Knopf {_name2q!r} hat kein Emoji mehr im Text",
              not _hat_emoji2q(_b2q.text()))
    for _feld2q in ("_sh_tool_pairs", "_sl_tool_pairs"):
        _paare2q = getattr(win, _feld2q, None)
        check(f"b2q {_feld2q}: jede Aktion traegt ein Symbol",
              _paare2q is not None
              and all(not a.icon().isNull() for a, _ in _paare2q))
        check(f"b2q {_feld2q}: kein Emoji mehr im Text",
              _paare2q is not None
              and not any(_hat_emoji2q(a.text()) for a, _ in _paare2q))
    # Auch die WERKZEUGE-KNOEPFE selbst pruefen, nicht nur ihre Eintraege -
    # die Rotprobe fand hier eine Luecke (Mutation am Knopf blieb gruen).
    for _tb2q in (win._sh_tools_btn, win._sl_tools_btn):
        check("b2q der Werkzeuge-Knopf traegt selbst ein Symbol",
              not _tb2q.icon().isNull())
    # RUNDE 2 (Nutzer, Screenshot der Reiter-Leiste): die GROESSTEN,
    # wichtigsten Elemente - Hauptnavigation oben, Sidebar links, oberste
    # Leiste. Emoji dort stachen am meisten heraus.
    for _k2q, _b2q in win._nav_buttons.items():
        check(f"b2q Navigation {_k2q!r} traegt ein Symbol",
              not _b2q.icon().isNull())
        check(f"b2q Navigation {_k2q!r} hat kein Zeichen mehr im Text",
              not _hat_emoji2q(_b2q.text()))
    for _n2q, _g2q in (("Struktur", win.g_struct_btn),
                       ("Markt-Scan", win.g_scan_btn),
                       ("Baurezepte laden", win.g_sde_btn)):
        check(f"b2q Kopfleiste {_n2q!r} traegt ein Symbol",
              not _g2q.icon().isNull())
        check(f"b2q Kopfleiste {_n2q!r} hat kein Emoji mehr im Text",
              not _hat_emoji2q(_g2q.text()))
    # Die Symbol-Karte darf keine Zeichen mehr enthalten, sondern nur
    # NAMEN aus icons.py - sonst waere ein Eintrag stumm.
    from eve_trader.ui import icons as _ic2q
    _fehlend2q = [k for k, v in win._NAV_ICONS.items()
                  if v not in _ic2q.verfuegbar()]
    eq("b2q jeder Navigations-Eintrag zeigt auf ein echtes Symbol",
       _fehlend2q, [])
    # Nutzer (Sitzung 8): Reiter in AMBER (eigene Farbe fuer "wo bin ich",
    # konkurriert nicht mit den Cyan-Datenakzenten); der kleine
    # Aktualisieren-Knopf OHNE Akzentfuellung.
    _shell2q = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    _nav2q = _shell2q[_pos_von(_shell2q, "#NavTab:checked"):][:260]
    check("b2q der aktive Reiter ist AMBER, nicht Cyan",
          "theme.AMBER" in _nav2q and "theme.CYAN" not in _nav2q)
    check("b2q der kleine Aktualisieren-Knopf hat keine Akzentfuellung",
          win.refresh_btn.objectName() != "Primary")
    # Drei Rahmen-Stufen (Nutzer: "standardmaessig schon einen gelben
    # Rahmen, bevor man Mouseover macht"): Ruhe gedaempft -> Hover voll ->
    # aktiv voll. Der ruhende Rahmen muss AMBER-Familie sein, nicht
    # blaugrau, sonst wirken die Reiter wieder unbeteiligt.
    _ruhe2q = _shell2q[_pos_von(_shell2q, 'f"#NavTab{{padding'):][:220]
    check("b2q ruhende Reiter haben schon einen Amber-Rahmen",
          "theme.AMBER_DIM" in _ruhe2q and "theme.BORDER" not in _ruhe2q)
    from eve_trader.ui import theme as _th2q2
    check("b2q der ruhende Rahmen ist gedaempfter als der aktive",
          _th2q2.AMBER_DIM != _th2q2.AMBER)
    _clear2q = [a for a, _ in win._sh_tool_pairs
                if a.text() == _t4("Clear list")]
    check("b2q 'Liste leeren' traegt ein Symbol (Gefahr sichtbar)",
          bool(_clear2q) and not _clear2q[0].icon().isNull())
except Exception as _e2q:                                # pragma: no cover
    _fail.append(f"b2q Symbole im Einsatz: {type(_e2q).__name__}: {_e2q}")

# ---------------------------------------------------------------- (b2p)
# ABO-RUECKBAU + KOPFLEISTE (Nutzer, Sitzung 8): "Premium kann weg und alle
# Anzeigen davon. Die Idee war ein Abo-Modell, das verwerfen wir komplett.
# Nur noch ein Donation-Button. Update-Knopf ganz oben rechts. Die vier
# Reiter sollen wie TABS aussehen, nicht wie Knoepfe."
try:
    _mw2p = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    # "Premium" bleibt EINMAL als EVE-Meta-Level stehen (Filter-Liste,
    # nichts mit Abo zu tun) - deshalb gezielt auf die Abo-Begriffe pruefen.
    check("b2p kein PREMIUM-Label und kein Credits-/Abo-Knopf mehr",
          "\u2728 PREMIUM" not in _mw2p
          and not hasattr(win, "credits_btn")
          and "Premium-Tipp" not in _mw2p
          and "Order Marks" not in _mw2p)
    check("b2p keine Schloss-Overlays mehr (alles frei ohne Abo)",
          win._lock_overlays == {})
    # Alle vier Reiter muessen erreichbar sein - ohne Freischalt-Huerde.
    for _k2p in win._paid_keys:
        win._go_tab(_k2p)
    check("b2p alle vier Reiter lassen sich oeffnen",
          win._nav_buttons["build"].isChecked())
    check("b2p Spenden-Hinweis existiert und nennt die Corporation",
          callable(win._show_donation_info)
          and "DONATION_CORP" in _mw2p)
    check("b2p Update-Knopf haengt in der Hub-Zeile ganz oben (rechts)",
          win.update_btn is not None
          and "_tb_spacer" in _mw2p
          and _mw2p.find("_tb_spacer") >= 0
          and _mw2p.find("_tb_spacer") < _mw2p.find("self.update_btn ="))
    check("b2p die Reiter tragen den eigenen Tab-Stil (#NavTab, nicht NavPaid)",
          all(win._nav_buttons[k].objectName() == "NavTab"
              for k in win._paid_keys)
          and "#NavPaid" not in _mw2p)
    check("b2p und sehen wie Reiter aus: nur oben rund, aktiver buendig",
          "border-top-left-radius:10px" in _mw2p
          and "border-top:3px solid" in _mw2p)
except Exception as _e2p:                                # pragma: no cover
    _fail.append(f"b2p Abo-Rueckbau: {type(_e2p).__name__}: {_e2p}")

# ---------------------------------------------------------------- (b2o)
# PORTFOLIO-LAYOUT (Nutzer, Sitzung 8): "schoener anordnen, mehr mit Farben
# arbeiten, weniger Informationsueberfluss. Ein Ausklappbarer, wo man
# anhaken kann welche Rows eingeblendet werden - Standard zugeklappt, darin
# angehakt Menge, Durchschnittskauf, Marge, Status, Orders." Dazu
# Werkzeuge-Menue nach Wagen-Muster und der offene Icon-Nachtrag.
try:
    _STD2o = {1, 2, 6, 7, 8}
    _acts2o = getattr(win, "_pf_col_acts", None)
    check("b2o die Spalten-Auswahl kennt alle 11 abwaehlbaren Spalten",
          _acts2o is not None and len(_acts2o) == 11 and 0 not in _acts2o)
    check("b2o Standard angehakt: Menge, \u00d8-Kauf, Marge, Status, Orders",
          {c for c, a in _acts2o.items() if a.isChecked()} == _STD2o)
    check("b2o und genau die sind sichtbar, der Rest ist versteckt",
          all(win.pf_table.isColumnHidden(c) is (c not in _STD2o)
              for c in _acts2o))
    check("b2o die Item-Spalte ist nie abwaehlbar",
          not win.pf_table.isColumnHidden(0))
    # Haken FUNKTIONAL: abwaehlen versteckt, wieder anhaken zeigt.
    _acts2o[1].setChecked(False)
    check("b2o Haken entfernen versteckt die Spalte sofort",
          win.pf_table.isColumnHidden(1))
    _acts2o[1].setChecked(True)
    check("b2o Haken setzen blendet sie wieder ein",
          not win.pf_table.isColumnHidden(1))
    # Zuschaltbare Spalte gegenprobe
    _acts2o[9].setChecked(True)
    check("b2o zuschaltbare Spalte laesst sich einblenden",
          not win.pf_table.isColumnHidden(9))
    _acts2o[9].setChecked(False)
    # Runde 3 (Nutzer): das Werkzeuge-Menue ist WEG - "brauchen wir nie".
    # Der Handler lebt weiter (die Spalte "In Sell-Order zu" ist im
    # Spalten-Menue zuschaltbar), nur der Knopf ist unsichtbar.
    check("b2o kein Werkzeuge-Menue mehr im Portfolio",
          not hasattr(win, "_pf_tool_pairs")
          and callable(win._pf_load_order_prices))
    # SITZUNG 20 (Nutzer-Entscheid): "Total Assets die Zahl in fettem Amber" -
    # die Leitzahl ist von CYAN auf AMBER gewechselt und groesser geworden.
    # Die Ordnung dahinter bleibt: gebunden AMBER, bereit GRUEN.
    # SITZUNG 20 (Nutzer-Entscheid, zweiter Anlauf): die Leitzahl ist GROSS,
    # aber in normaler Textfarbe - "doch lieber einfach weiss wie die Zahlen
    # der Wallet". Farbe bleibt den Zahlen vorbehalten, bei denen sie etwas
    # BEDEUTET: gebunden AMBER, bereit GRUEN.
    check("b2o Leitzahl gross und neutral, gebunden AMBER, bereit GRUEN",
          "26px" in win.k_wealth.styleSheet()
          and _th2i.AMBER not in win.k_wealth.styleSheet()
          and _th2i.AMBER in win.k_invested.styleSheet()
          and _th2i.GREEN in win.k_flag.styleSheet())
    _mw2o = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    # Runde 2 (Nutzer): zwei Karten in die Auswahl der Spalten-Auswahl.
    _karten2o = getattr(win, "_pf_card_acts", None)
    check("b2o Investiert + Item-Wert sind abwaehlbare Kennzahlen",
          _karten2o is not None and len(_karten2o) == 2)
    check("b2o und beide starten AUSGEBLENDET",
          not any(a.isChecked() for a in _karten2o.values())
          and win.k_invested_c.isHidden() and win.k_value_c.isHidden())
    _kact2o = _karten2o.get("Invested (held)")   # Sitzung 17: englischer Schluessel
    _kact2o.setChecked(True)
    check("b2o Haken blendet die Kennzahl-Karte wieder ein",
          not win.k_invested_c.isHidden())
    _kact2o.setChecked(False)
    # Runde 3 (Nutzer-Entscheidung): die kurzzeitige "Marge
    # (verkaufsbereit)"-Karte ist WIEDER WEG - sie rechnete korrekt, wirkte
    # aber unplausibel, sobald ein grosser Posten dominierte. Die
    # belastbare Marge lebt im Gewinne-Tab (echte Verkaeufe).
    check("b2o im Portfolio gibt es KEINE Erwartungs-Marge-Karte mehr",
          not hasattr(win, "k_margin"))
    _pr3o = _mw2o[_pos_von(_mw2o, "def _render_profit"):]
    _pr3o = _pr3o[:_pos_von(_pr3o, "\n    def ", 10)]
    check("b2o Gewinne: Marge steht als ERSTE Karte, Gebuehren sind aus",
          win.pk_margin_c.parentWidget().layout() is not None
          and win.pk_fees_c.isHidden())
    _bp3o = _mw2o[_pos_von(_mw2o, "def _build_profit_tab"):]
    _bp3o = _bp3o[:_pos_von(_bp3o, "\n    def ", 10)]
    _bp2o = _mw2o[_pos_von(_mw2o, "def _build_portfolio_tab"):]
    _bp2o = _bp2o[:_pos_von(_bp2o, "\n    def ", 10)]
    # OHNE index() pruefen: faellt der Stretch ganz weg, wuerde index()
    # eine ValueError werfen und den ganzen Block abbrechen - die Rotprobe
    # sah das als "Pruefung blieb gruen" (blind). find() liefert -1 und
    # macht die Pruefung sauber ROT.
    # Die Funktion enthaelt MEHRERE addStretch() (auch weiter unten im
    # Container-Bereich) - ein blosses "kommt danach" war blind, weil der
    # zweite Stretch die Pruefung rettete. Deshalb die exakte
    # NACHBARSCHAFT verlangen: direkt nach dem Spalten-Knopf.
    # Nutzer (Sitzung 8): Spalten-Auswahl GANZ RECHTS, der Rest links.
    # Der Stretch steht ZWISCHEN beiden - exakte Nachbarschaft pruefen, ein
    # blosses "kommt danach" waere bei mehreren Stretches blind.
    check("b2o Spalten-Auswahl sitzt ganz rechts, der Rest bleibt links",
          "head.addStretch()\n        head.addWidget(_pf_cols_btn)" in _bp2o)
    check("b2o und Aktualisieren steht weiter links davor",
          0 <= _bp2o.find("head.addWidget(self.refresh_btn)")
          < _bp2o.find("head.addStretch()\n        head.addWidget(_pf_cols_btn)"))
    check("b2o und zwar an Position 0 der Kennzahlen-Zeile",
          "for c in (self.pk_margin_c, self.pk_net_c" in _bp3o
          and "self.pk_fees_c.setVisible(False)" in _bp3o)
    check("b2o die Gewinne-Marge ist gross und vorzeichen-gefaerbt",
          "font-size:26px" in _pr3o
          and "theme.GREEN if avg_margin >= 0 else theme.RED" in _pr3o
          and 'f"{avg_margin:+.1f} %"' in _pr3o)
    check("b2o das Portfolio stoesst den Bilder-Nachtrag an",
          "self._icon_prefetch_pending(self._render_portfolio)" in _mw2o)
    # GEWINNE-Tab: Filter links (Stretch am ENDE der Kopfzeile)
    _pr2o = _mw2o[_pos_von(_mw2o, "def _build_profit_tab"):]
    _pr2o = _pr2o[:_pos_von(_pr2o, "\n    def ", 10)]
    check("b2o Gewinne: Charakter/Zeitraum links, Stretch erst danach",
          _pos_von(_pr2o, "head.addWidget(self.pr_window)")
          < _pos_von(_pr2o, "head.addStretch()"))
except Exception as _e2o:                                # pragma: no cover
    _fail.append(f"b2o Portfolio-Layout: {type(_e2o).__name__}: {_e2o}")

# ---------------------------------------------------------------- (b2n)
# VERKAUFSLISTEN-FUSSZEILE (Nutzer, Sitzung 8): "Erwarteter Gewinn und
# Erwarteter Erloes koennen raus; die Anzeige wieviele Items in der Liste
# sind, sollte erkenntlicher sein und nach LINKS." Wie beim Einkaufswagen:
# die Liste mischt Herkuenfte, eine Summe darueber ist keine verlaessliche
# Aussage - der Zaehler dagegen ist beim Gegenchecken mit dem Ingame-
# Verkaufsfenster die eigentlich nuetzliche Zahl.
try:
    check("b2n Gewinn- und Erloes-Anzeige sind aus der Ansicht",
          not win.sell_t_profit.isVisible() and not win.sell_t_rev.isVisible())
    check("b2n die Labels leben weiter (Aktualisierung schreibt ins Leere)",
          win.sell_t_profit is not None and win.sell_t_rev is not None)
    _lay2n = win.sell_t_count.parentWidget().layout()
    check("b2n der Item-Zaehler steht praesent da (fett, H2-Groesse)",
          "font-weight:800" in win.sell_t_count.styleSheet()
          and "font-size:15px" in win.sell_t_count.styleSheet())
    # LINKS heisst: im Fusszeilen-Layout VOR dem Stretch. Funktional
    # geprueft statt per Quelltext-Suche.
    _tot2n = None
    for _i2n in range(_lay2n.count() if _lay2n else 0):
        _it2n = _lay2n.itemAt(_i2n)
        _sub2n = _it2n.layout() if _it2n else None
        if _sub2n and any(_sub2n.itemAt(_j).widget() is win.sell_t_count
                          for _j in range(_sub2n.count())):
            _tot2n = _sub2n
            break
    check("b2n der Zaehler sitzt LINKS aussen (Position 0 der Fusszeile)",
          _tot2n is not None
          and _tot2n.itemAt(0).widget() is win.sell_t_count)
except Exception as _e2n:                                # pragma: no cover
    _fail.append(f"b2n Verkaufslisten-Fusszeile: {type(_e2n).__name__}: {_e2n}")

# ---------------------------------------------------------------- (b2p)
# SYMBOL-ZUSTAENDE (Nutzer, Sitzung 8: "wenn die Symbole aktiv sind, etwas
# heller, mehr ins Weiss hinein"). FUNKTIONAL geprueft: die gerenderten
# Bilder muessen sich in der Helligkeit wirklich unterscheiden - eine
# Quelltext-Suche wuerde nicht merken, wenn Qt den Zustand ignoriert.
try:
    from PySide6.QtGui import QIcon as _QI2p
    from PySide6.QtCore import QSize as _QS2p
    from eve_trader.ui import icons as _ic2p

    def _helligkeit2p(qicon, modus):
        _img = qicon.pixmap(_QS2p(32, 32), modus).toImage()
        _px = [_img.pixelColor(x, y) for y in range(32) for x in range(32)
               if _img.pixelColor(x, y).alpha() > 200]
        return sum(p.red() for p in _px) // max(1, len(_px))

    _ic = _ic2p.icon("factory", groesse=32)
    _ruhe2p = _helligkeit2p(_ic, _QI2p.Normal)
    _aktiv2p = _helligkeit2p(_ic, _QI2p.Active)
    _aus2p = _helligkeit2p(_ic, _QI2p.Disabled)
    check(f"b2p aktiv ist HELLER als Ruhe ({_aktiv2p} > {_ruhe2p})",
          _aktiv2p > _ruhe2p)
    check("b2p und der Sprung ist deutlich sichtbar (>= 25 Stufen)",
          _aktiv2p - _ruhe2p >= 25)
    check(f"b2p inaktiv ist dunkler als Ruhe ({_aus2p} < {_ruhe2p})",
          _aus2p < _ruhe2p)
    check("b2p markierte Zeilen bekommen denselben hellen Ton",
          _helligkeit2p(_ic, _QI2p.Selected) == _aktiv2p)
    # Eingefaerbte Zustands-Symbole behalten IHRE Farbe - dort ist die
    # Farbe die Aussage, die darf nicht aufgehellt werden.
    from eve_trader.ui import theme as _th2p
    _amber2p = _ic2p.icon("warning", _th2p.AMBER, 32)
    check("b2p eingefaerbte Symbole werden NICHT aufgehellt",
          _helligkeit2p(_amber2p, _QI2p.Active)
          == _helligkeit2p(_amber2p, _QI2p.Normal))
except Exception as _e2p:                                # pragma: no cover
    _fail.append(f"b2p Symbol-Zustaende: {type(_e2p).__name__}: {_e2p}")

# ---------------------------------------------------------------- (b2m)
# GRUPPEN-RUECKFALL IM KATEGORIEN-SCHLUESSEL (Nutzer-Fall Stork: Ferrogel
# stand trotz "immer bauen" auf "kaufen", die Geschwister bauten). Ursache:
# Gruppen-Karte kannte das Item nicht -> Schluessel fiel auf generisches
# "reactions" -> nie besessen. FUNKTIONAL: mit leerem Gruppennamen muss der
# Schluessel die SDE fragen und "Composite" korrekt zuordnen.
try:
    import eve_trader.industry as _ind2m
    _orig_gn2m = _ind2m.group_names
    _ind2m.group_names = lambda ids: {int(list(ids)[0]): "Composite"}
    win._sde_group_name_cache = None
    _key2m = win._category_key(16670, "", True)
    check("b2m leerer Gruppenname -> SDE-Rueckfall -> composite_reactions",
          _key2m == "composite_reactions")
    _ind2m.group_names = lambda ids: (_ for _ in ()).throw(
        AssertionError("zweiter SDE-Zugriff"))
    check("b2m der Rueckfall ist gecacht (kein zweiter SDE-Zugriff)",
          win._category_key(16670, "", True) == "composite_reactions")
    check("b2m bekannter Gruppenname geht weiter direkt",
          win._category_key(16670, "Intermediate Materials", True)
          == "intermediate_reactions")
except Exception as _e2m:                                # pragma: no cover
    _fail.append(f"b2m Gruppen-Rueckfall: {type(_e2m).__name__}: {_e2m}")
finally:
    try:
        _ind2m.group_names = _orig_gn2m
        win._sde_group_name_cache = None
    except Exception:
        pass

# ---------------------------------------------------------------- (b2j)
# VERKAUFSLISTE NACH WAGEN-MUSTER (Sitzung 8) + Nutzer-Auftrag: "ueberpruefe
# anschliessend ob alle Buttons noch funktionieren". Also: JEDER Knopf wird
# funktional ausgeloest (Attrappen zaehlen die Handler-Aufrufe); der
# Einfuege-Knopf ist schon durch b2g abgedeckt, der ihn REAL drueckt.
try:
    _rufe2j = []
    _pairs2j = getattr(win, "_sl_tool_pairs", None)
    check("b2j Werkzeuge-Menue hat drei Eintraege (laden/check/leeren)",
          _pairs2j is not None and len(_pairs2j) == 3)
    _orig2j = (win._sell_load_prices, win._sell_check_orders, win._sell_clear,
               win._sell_copy_list, win._render_sell_list)
    win._sell_load_prices = lambda *a, **k: _rufe2j.append("laden")
    win._sell_check_orders = lambda *a, **k: _rufe2j.append("check")
    win._sell_clear = lambda *a, **k: _rufe2j.append("leeren")
    win._sell_copy_list = lambda *a, **k: _rufe2j.append("kopieren")
    win._render_sell_list = lambda *a, **k: _rufe2j.append("render")
    for _a2j, _b2j in _pairs2j:
        _a2j.trigger()
    check("b2j alle drei Menue-Aktionen rufen ihre Handler",
          _rufe2j[:3] == ["laden", "check", "leeren"])
    check("b2j die drei Knoepfe sind unsichtbar, aber am Leben",
          all(not _b.isVisible() for _a, _b in _pairs2j))
    # Hauptaktion + Ziel-Preis-Zustand
    for _w2j in win._shopping_w.findChildren(type(win._sh_copy_btn)):
        pass
    _cl2j = [b for b in win.sell_table.parentWidget().parentWidget()
             .findChildren(type(win._sh_copy_btn))
             if b.text() == _t4("Copy prices → in game")]
    check("b2j Hauptaktion 'Preise -> Ingame kopieren' sichtbar verkabelt",
          bool(_cl2j) and (_cl2j[0].clicked.emit() or "kopieren" in _rufe2j))
    _tb2j = [b for b in win.sell_table.parentWidget().parentWidget()
             .findChildren(type(win._sh_copy_btn))
             if b.text() == _t4("All at target price")]
    if _tb2j:
        _vor2j = win._sell_target_mode
        _tb2j[0].toggle()
        check("b2j Ziel-Preis-Schalter kippt den Zustand und rendert neu",
              win._sell_target_mode != _vor2j and "render" in _rufe2j)
        _tb2j[0].toggle()
    else:
        _fail.append("b2j Ziel-Preis-Knopf nicht gefunden")
    (win._sell_load_prices, win._sell_check_orders, win._sell_clear,
     win._sell_copy_list, win._render_sell_list) = _orig2j
    # Layout-Zusagen
    check("b2j Erloes- und Gewinn-Spalte sind ausgeblendet",
          win.sell_table.isColumnHidden(6) and win.sell_table.isColumnHidden(7))
    check("b2j Splitter traegt links Liste, rechts das Einfuege-Feld",
          getattr(win, "_sell_split", None) is not None
          and win._sell_split.count() == 2
          and win._sell_paste in [win._sell_split.widget(1)]
          + win._sell_split.widget(1).findChildren(type(win._sell_paste)))
    check("b2j der Einfuege-Knopf steht UEBER dem Feld",
          win._sell_split.widget(1).layout().indexOf(
              win._sell_split.widget(1).findChildren(
                  type(win._sh_copy_btn))[0]) == 0)
    _mwsrc2j = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    check("b2j der Erklaertext ist raus",
          "Portfolio-Items mit Status" not in _mwsrc2j)
    check("b2j Verkaufsliste stoesst den Bilder-Nachtrag an",
          "self._icon_prefetch_pending(self._render_sell_list)" in _mwsrc2j)
except Exception as _e2j:                                # pragma: no cover
    _fail.append(f"b2j Verkaufsliste: {type(_e2j).__name__}: {_e2j}")

# ---------------------------------------------------------------- (b2k)
# ORDER-UPDATE NACH MUSTER (Sitzung 8): Kopfzeile war schon konform -
# geprueft werden Text-Entfernung, Optik, Icon-Anschluss und dass die
# Knoepfe weiter feuern (Attrappen).
try:
    _rufe2k = []
    _orig_load2k = win._load_order_mods
    _orig_tog2k = win._toggle_order_step
    win._load_order_mods = lambda *a, **k: _rufe2k.append("laden")
    win._toggle_order_step = lambda *a, **k: _rufe2k.append("modus")
    _mwsrc2k = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    check("b2k der Erklaertext ist raus, Cache-Hinweis lebt im Tooltip",
          "Deine offenen Orders am gew" not in _mwsrc2k
          # Sitzung 13: Tooltip laeuft ueber das Sprachsystem (englischer
          # Schluessel im Quelltext, deutsch im Katalog).
          and _mwsrc2k.count("EVE caches your orders for up to ~20 min") == 1)
    check("b2k Tabellen ohne Gitter, mit 32er-Icons",
          not win.buyord_table.showGrid()
          and win.buyord_table.iconSize().width() == 32
          and win.sellord_table.iconSize().width() == 32)
    check("b2k Zeilen bekommen Item-Icons (per _table_icon)",
          "_oic = self._table_icon(r[\"tid\"])" in _mwsrc2k)
    check("b2k Bilder-Nachtrag zeichnet NUR neu, laedt NICHT aus ESI",
          "self._icon_prefetch_pending(self._rerender_order_tables)"
          in _mwsrc2k
          and "self._icon_prefetch_pending(self._load_order_mods)"
          not in _mwsrc2k)
    # Neuzeichnen aus gemerkten Zeilen darf ohne Daten nicht knallen
    win._rerender_order_tables()
    check("b2k Neuzeichnen ohne Daten laeuft sauber durch", True)
    # UEBERHOLT (Nutzer, Layout-Programm: "die Farben sollen dasselbe
    # sein"): die aeltere Violett-Logik ist dem Bauplan-Schema gewichen.
    # Name = fetter Anker in NORMALFARBE (rot NUR bei Verlust/Gebuehren-
    # Fall), Warnfarbe wohnt allein in der Status-Spalte (AMBER Handlung /
    # ROT Finger weg / GRUEN top), keine Zeilen-Tinte auf den Zahlen.
    _fo2k = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    _fo2k = _fo2k.split("def _fill_order_table")[1].split("\n    def ")[0]
    check("b2k Name ist ruhiger Anker: Farbe nur im Verlust-Fall",
          "if flag and loss:\n                nm.setForeground(QColor(theme.RED))"
          in _fo2k and "#d17ae8" not in _fo2k)
    check("b2k Status traegt die Warnfarbe: AMBER Handlung, ROT Verlust",
          "st_col = (theme.RED if loss else theme.AMBER) if flag else theme.GREEN"
          in _fo2k)
    check("b2k keine Zeilen-Tinte mehr auf Deine-Order/Bester",
          "Rest der Zeile ebenfalls rot" not in _fo2k
          and "for c in (1, 2):" not in _fo2k)
except Exception as _e2k:                                # pragma: no cover
    _fail.append(f"b2k Order-Update: {type(_e2k).__name__}: {_e2k}")
finally:
    try:
        win._load_order_mods = _orig_load2k
        win._toggle_order_step = _orig_tog2k
    except Exception:
        pass

# ---------------------------------------------------------------- (b2l)
# TRADING-TABS NACH MUSTER (Sitzung 8): Feinfilter standardmaessig ZU,
# Excel-Gefuehl raus (kein Gitter, 32er-Icons, fette Namen), Bilder-
# Nachtrag ueber Merk-Wrapper (NIE ueber einen Scan/Reload).
try:
    _mwsrc2l = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    for _t2l in (win.deals_table, win.hold_table, win.rg_table):
        pass
    check("b2l alle drei Tabellen ohne Gitter und mit 32er-Icons",
          all((not _t.showGrid()) and _t.iconSize().width() == 32
              for _t in (win.deals_table, win.hold_table, win.rg_table)))
    # SEIT SITZUNG 12 uebersetzt - gezaehlt wird der ZUSTAND (expanded=False),
    # nicht der deutsche Titel. Genau die Sorte Pruefung, die bei jeder
    # Uebersetzung umfaellt, wenn man sie am Wortlaut festmacht.
    check("b2l alle drei Feinfilter starten ZUGEKLAPPT",
          _mwsrc2l.count('t("FINE FILTERS (OPTIONAL)"), ctl, expanded=False)')
          == 3)
    check("b2l die Namenszelle traegt Icon + Fett (in allen drei Fills)",
          _mwsrc2l.count('_ic0 = self._table_icon(d["type_id"])') == 3)
    # Nachtrag: Wrapper zeichnen aus GEMERKTEN Daten, kein Scan
    _rufe2l = []
    _orig_rd2l = win._render_deals
    win._render_deals = lambda d, m: _rufe2l.append(("deals", len(d), m))
    win._deals_last = ([{"x": 1}], "flip")
    win._rerender_deals()
    check("b2l Deals-Nachtrag zeichnet aus gemerkten Daten neu",
          _rufe2l == [("deals", 1, "flip")])
    win._render_deals = _orig_rd2l
    win._deals_last = None   # Attrappen-Daten nie dem echten Renderer lassen
    check("b2l ohne gemerkte Daten zeichnet der Wrapper NICHTS (kein Crash)",
          (win._rerender_hold() or True) and (win._rerender_arbitrage()
                                              or True))
    check("b2l alle drei Renderer stossen den Bilder-Nachtrag an",
          all(f"self._icon_prefetch_pending(self.{w})" in _mwsrc2l
              for w in ("_rerender_deals", "_rerender_hold",
                        "_rerender_arbitrage")))
except Exception as _e2l:                                # pragma: no cover
    _fail.append(f"b2l Trading-Tabs: {type(_e2l).__name__}: {_e2l}")

# ---------------------------------------------------------------- (b2j)
# ICON-VERHUNGERUNG (Nutzer-Fund: Order-Update ohne ein einziges Bild).
# Vorher: kam ein zweiter Tab, waehrend ein Holer lief, wurden seine
# Wuensche GELEERT und verworfen - Icons fuer die Sitzung verloren. Jetzt:
# Wuensche bleiben stehen, Rueckruf wird gemerkt, der laufende Lauf haengt
# einen Folgelauf an. Hier FUNKTIONAL durchgespielt.
try:
    _cb2j = lambda: None
    win._icon_prefetch_running = True
    win._icon_wanted = {("icon", 34, 32)}
    win._icon_prefetch_followup = None
    _ret2j = win._icon_prefetch_pending(_cb2j)
    check("b2j bei 'laeuft schon' bleiben die Wuensche STEHEN",
          _ret2j is False and ("icon", 34, 32) in win._icon_wanted)
    check("b2j und der Rueckruf des wartenden Tabs wird gemerkt",
          win._icon_prefetch_followup is _cb2j)
    # Der laufende Lauf endet -> Folgelauf muss angestossen werden. Wir
    # spielen das nach: running aus, dann den echten Lauf starten - mit
    # _run-Attrappe, die sofort 'fertig, 1 Bild' meldet.
    win._icon_prefetch_running = False
    _laeufe2j = []
    _orig_run2j2 = win._run
    win._run = (lambda w, done, fail_cb=None, **k:
                _laeufe2j.append("lauf") or done((1, 0)))
    win._icon_tried = set()
    _ret2j2 = win._icon_prefetch_pending(win._icon_prefetch_followup)
    check("b2j der Folgelauf holt die liegengebliebenen Wuensche wirklich",
          _ret2j2 is True and _laeufe2j == ["lauf"]
          and not win._icon_wanted)
    win._run = _orig_run2j2
except Exception as _e2j:                                # pragma: no cover
    _fail.append(f"b2j Icon-Verhungerung: {type(_e2j).__name__}: {_e2j}")
finally:
    try:
        win._run = _orig_run2j2
        win._icon_prefetch_running = False
        win._icon_prefetch_followup = None
    except Exception:
        pass

# ---------------------------------------------------------------- (b2h)
# "WERTE TIEFENPRUEFEN" IM UPDATES-DIALOG (Nutzer-Wunsch, Sitzung 8:
# "das ist uebersichtlicher" - der Knopf zog aus den Einstellungen in den
# Updates-Dialog um). Geprueft wird der GANZE neue Weg: Updates-Klick bei
# "alles aktuell" -> Dialog bietet die Tiefenpruefung an -> Klick darauf ->
# Bericht. Dazu der Rueckbau: in den Einstellungen darf der alte Knopf
# NICHT mehr haengen. Bericht und Netz kommen aus Attrappen.
try:
    import eve_trader.esi as _esi2h

    _orig_srv2h = _esi2h.eve_server_version
    _orig_sde2h = _esi2h.sde_last_modified
    _esi2h.eve_server_version = lambda: "3.1.4"
    _esi2h.sde_last_modified = lambda: "2026-08-01"
    win.settings["known_server_version"] = "3.1.4"
    win.settings["known_sde_modified"] = "2026-08-01"
    win.settings["sde_reload_ausstehend"] = False
except Exception as _e2h0:                               # pragma: no cover
    _fail.append(f"b2h Vorbereitung: {type(_e2h0).__name__}: {_e2h0}")
try:
    import pruefe_rezepte as _PR2h
    from PySide6.QtWidgets import QMessageBox as _QMB2h

    _orig_ber2h = _PR2h.bericht_fuer_ui
    _orig_run2h = win._run
    _orig_exec2h = _QMB2h.exec
    _orig_info2h = _QMB2h.information
    _texte2h = []
    _PR2h.bericht_fuer_ui = lambda: {
        "leer": False, "n": 231,
        "zensus": {200: 180, 400: 30, 10: 1},
        "hart": [], "verdaechtig": [], "falsch": [],
        "diff": ([((9002, 11, 102), 200, 400)], [], [], []),
        "sde_fehler": None}
    win._run = lambda worker, done_cb, fail_cb=None, **kw: done_cb(
        worker._fn(*worker._args, **worker._kwargs))
    # exec()-Attrappe: merkt sich den Text und "klickt" den Tiefenpruefen-
    # Knopf (ActionRole), falls der Dialog einen anbietet.
    def _exec2h(dlg):
        _texte2h.append(dlg.text())
        for _b in dlg.buttons():
            if "tiefenpr" in _b.text().lower():
                dlg._klick2h = _b
                _b.click()
                return 0
        dlg._klick2h = None
        return 0
    _QMB2h.exec = _exec2h
    _orig_cb2h = _QMB2h.clickedButton
    _QMB2h.clickedButton = lambda self: getattr(self, "_klick2h", None)
    _QMB2h.information = staticmethod(
        lambda *a, **k: _texte2h.append(a[2] if len(a) > 2 else ""))
    # SITZUNG 11: der Updates-Dialog gibt nur noch die Antwort - der
    # Zusatz-Knopf "Werte tiefenpruefen" ist entfallen (Nutzer: "das
    # braucht keiner zu sehen").
    win._check_for_updates()
    check("b2h der Updates-Dialog bietet nichts Zusaetzliches an",
          not any("tiefenpr" in t.lower() for t in _texte2h))
    check("b2h er sagt nur, dass alles aktuell ist",
          any("up to date" in t for t in _texte2h))
    # KURZ HEISST KURZ (Nutzer: "hauptsache es steht: auf dem neusten
    # Stand"). Frueher zaehlte der Dialog auf, WAS verglichen wurde - das
    # half niemandem, der nur weiterarbeiten will.
    _gut2h = next((t for t in _texte2h if "up to date" in t), "")
    # SPRACHUNABHAENGIG: die Zusage ist "nur die Antwort, ein Satz". Ein
    # Zeilenumbruch heisst, dass etwas drangehaengt wurde - egal in welcher
    # Sprache. Eine Zeichenzahl waere je Sprache verschieden, ein Suchwort
    # nur in einer Sprache wirksam.
    check(f"b2h die Gut-Meldung ist kurz ({len(_gut2h)} Zeichen, "
          f"{_gut2h.count(chr(10))} Umbrueche)",
          0 < len(_gut2h) <= 60 and "\n" not in _gut2h)
    check("b2h der alte Einstellungen-Knopf ist WEG (kein Doppel)",
          "rez_btn" not in _src_mw)
    # DIE PRUEFUNG SELBST GIBT ES WEITERHIN - sie ist nur nicht mehr aus
    # diesem Dialog erreichbar. Direkt gerufen muss sie weiter arbeiten.
    _texte2h.clear()
    win._check_recipes()
    _t2h = _texte2h[-1] if _texte2h else ""
    check("b2h die Tiefenpruefung selbst arbeitet weiterhin", bool(_t2h))
    # Zweisprachig (Sitzung 16): der Bericht laeuft durch t().
    check("b2h der Bericht nennt den Zensus",
          "AUSBEUTE-ZENSUS" in _t2h or "YIELD CENSUS" in _t2h)
    check("b2h eine veraltete Ausbeute wird als Problem genannt",
          ("VERALTET" in _t2h or "OUTDATED" in _t2h)
          and "200" in _t2h and "400" in _t2h)
    check("b2h und der Weg zur Loesung steht dabei",
          "Baurezepte laden" in _t2h or "Load recipes" in _t2h)
    # Offline-Fall: Zensus MUSS trotzdem kommen (Regel 6)
    _texte2h.clear()
    _PR2h.bericht_fuer_ui = lambda: {
        "leer": False, "n": 231, "zensus": {200: 180},
        "hart": [], "verdaechtig": [], "falsch": [],
        "diff": None, "sde_fehler": "URLError: kein Netz"}
    win._check_recipes()   # Handler bleibt direkt pruefbar (Offline-Fall)
    check("b2h ohne Netz kommt der Zensus trotzdem, mit klarer Ansage",
          bool(_texte2h)
          and ("NICHT M\u00d6GLICH" in _texte2h[-1]
               or "NOT POSSIBLE" in _texte2h[-1])
          and ("AUSBEUTE-ZENSUS" in _texte2h[-1]
               or "YIELD CENSUS" in _texte2h[-1]))
except Exception as _e2h:                                # pragma: no cover
    _fail.append(f"b2h Rezepte pruefen: {type(_e2h).__name__}: {_e2h}")
finally:
    try:
        _PR2h.bericht_fuer_ui = _orig_ber2h
        win._run = _orig_run2h
        _QMB2h.exec = _orig_exec2h
        _QMB2h.information = _orig_info2h
        _QMB2h.clickedButton = _orig_cb2h
        _esi2h.eve_server_version = _orig_srv2h
        _esi2h.sde_last_modified = _orig_sde2h
    except Exception:
        pass

# ---------------------------------------------------------------- (b2e)
# BESTANDS-STAND IM KOPF (Nutzer-Wunsch): "wann war die letzte erfolgreiche
# ESI-Aktualisierung, die Veraenderungen festgestellt hat". Die Rechenlogik
# dahinter prueft aa153 - hier geht es NUR darum, dass die Zeile den Schirm
# auch erreicht: mit Text, in einem Layout haengend und nicht versteckt. Ein
# Label ohne Parent existiert im Speicher und ist trotzdem unsichtbar; genau
# so faellt so eine Anzeige still aus.
_stand_lbl = getattr(win, "_bd_esi_stand_lbl", None)
check("b2e Bestands-Zeile existiert", _stand_lbl is not None)
if _stand_lbl is not None and _dlg is not None:
    check("b2e Bestands-Zeile haengt im Fenster (hat einen Parent)",
          _stand_lbl.parentWidget() is not None)
    check("b2e Bestands-Zeile ist im Dialog sichtbar",
          _stand_lbl.isVisibleTo(_dlg))
    check("b2e Bestands-Zeile ist nicht leer",
          bool(_stand_lbl.text().strip()))
    check("b2e und benennt den Bestand",
          "Bestand" in _stand_lbl.text() or "Stock" in _stand_lbl.text())
    # Ohne Vergleichsstand darf sie KEINE Aenderung behaupten.
    check("b2e ohne Abruf wird keine Aenderung behauptet",
          "letzte festgestellte" not in _stand_lbl.text())
    # SPRACHUNABHAENGIG: der Tooltip laeuft jetzt durch t(); geprueft wird
    # dass er UEBERHAUPT etwas erklaert, nicht ein deutsches Teilwort.
    check("b2e der Hinweistext erklaert den Unterschied",
          len(_stand_lbl.toolTip() or "") > 40)

if _dlg is not None:
    # ------------------------------------------------------------ (b3)
    # BEDIENELEMENTE MUESSEN IM FENSTER SEIN. Ein Widget ohne Layout hat
    # keinen Parent und taucht hier gar nicht auf - genau so ging das
    # Verkaufscharakter-Dropdown verloren.
    _combos = _dlg.findChildren(QComboBox)
    _buttons = _dlg.findChildren(QPushButton)
    _btexts = [b.text() for b in _buttons]
    _ctips = [c.toolTip() for c in _combos]

    check("b3 mindestens zwei Dropdowns in der Kopfleiste (Hub + Charakter)",
          len(_combos) >= 2)
    check("b3 Verkaufs-HUB-Dropdown vorhanden",
          any("sell the end product" in (t or "")
              or "verkaufst du das Endprodukt" in (t or "")
              for t in _ctips))
    check("b3 Verkaufs-CHARAKTER-Dropdown vorhanden (war einmal verloren)",
          any("Wer verkauft das Endprodukt" in (t or "")
              or "Who sells the final product" in (t or "")
              for t in _ctips))
    check("b3 Knopf 'Neu berechnen' vorhanden",
          any("Neu berechnen" in t or "Recalculate" in t for t in _btexts))
    check("b3 Knopf 'Werkzeuge' vorhanden",
          any("Werkzeuge" in t or "Tools" in t for t in _btexts))
    # "Zu Einkaufswagen" entfaellt - Einkauf laeuft ueber Materialien-Tab ->
    # "Einkaufsliste erstellen". Der Knopf DORT muss es dafuer geben.
    # Zweisprachig (Sitzung 16): die Beschriftung laeuft durch t().
    check("b3 Knopf 'Einkaufsliste erstellen' vorhanden",
          any("Einkaufsliste erstellen" in t or "Create shopping list" in t
              for t in _btexts))
    check("b3 Knopf 'Bauplan speichern' vorhanden",
          any("speichern" in t.lower() or "save" in t.lower() for t in _btexts))

    # ------------------------------------------------------------ (b4)
    # KPI-Karten muessen gefuellt sein (nicht nur existieren).
    _labels = [l.text() for l in _dlg.findChildren(QLabel)]
    _joined = " ".join(_labels)
    # SPRACHUNABHAENGIG (Sitzung 12): geprueft wird, dass die KARTE da ist -
    # in der Sprache, die gerade laeuft. Ein fest eingetippter deutscher
    # Titel waere seit der Umstellung auf Englisch-als-Standard rot, ohne
    # dass etwas fehlt.
    from eve_trader.sprache import t as _t4
    # Sitzung 17: alle drei Kacheln laufen durch t() - Titel in der Sprache
    # des Testfensters.
    for _cap in (_t4("Build cost / unit"), _t4("Total profit"),
                 _t4("Min. sell price / unit")):
        check(f"b4 KPI-Karte vorhanden: {_cap}", _cap in _joined)
    check("b4 KPI-Werte sind gefuellt (ISK-Betrag sichtbar)",
          any("ISK" in t for t in _labels))
    # (b4b) Ausgeduennte Leiste: diese Karten sind bewusst NICHT mehr sichtbar.
    _vis = [l.text() for l in _dlg.findChildren(QLabel) if l.isVisibleTo(_dlg)]
    for _gone in ("Gesamt", "Sell / Stk", "Rohgewinn gesamt (ohne Geb"):
        check(f"b4b ausgeblendet: {_gone}",
              not any(t.startswith(_gone) for t in _vis))

    # ------------------------------------------------------------ (b5)
    # Materialien-Tab: Tabelle mit den Herkunfts-Spalten + Einfuege-Panel.
    # Der Materialien-Tab ist ein GRUPPEN-BAUM (Kategorien einklappbar).
    _mat = [x for x in _dlg.findChildren(QTreeWidget)
            if x.columnCount() == 7 and x.headerItem()
            and x.headerItem().text(0) == _t4("Material")]
    check("b5 Materialien-Tabelle vorhanden", bool(_mat))
    if _mat:
        _hdr = [_mat[0].headerItem().text(c)
                for c in range(_mat[0].columnCount())]
        # AUCH EINE SPALTE AUS DER ERSTEN ZEILE der Kopf-Liste pruefen:
        # eine Mutation, die nur Zeile 1 ersetzt, bliebe sonst unbemerkt
        # (in dieser Sitzung schon dreimal passiert).
        check("b5 die vordere Kopfspalte ist uebersetzt",
              _t4("Category") in _hdr)
        check("b5 Spalte fuer eingefuegten Bestand existiert",
              _t4("Pasted") in _hdr)
        check("b5 Spalte 'Fehlt' vorhanden", _t4("Missing") in _hdr)
        # Gegenprobe an echten Zeilen: Fehlt = Benoetigt - Bestand, nie < 0.
        _bad = []
        _leaves = []
        for _g in range(_mat[0].topLevelItemCount()):
            _gi = _mat[0].topLevelItem(_g)
            for _c in range(_gi.childCount()):
                _leaves.append(_gi.child(_c))
        for _nd in _leaves:
            _nt = _nd.text(2).replace("'", "").strip()
            if not _nt:
                continue
            try:
                _n = int(float(_nt.replace("k", "000").replace("M", "000000")))
            except ValueError:
                continue
            _mt = _nd.text(5).strip()
            if _mt in ("\u2013", "-", ""):
                continue
            try:
                _m = int(float(_mt.replace("'", "").replace("k", "000")
                               .replace("M", "000000")))
            except ValueError:
                continue
            if _m < 0 or _m > _n:
                _bad.append((_nd.text(0), _n, _m))
        check(f"b5 'Fehlt' liegt immer zwischen 0 und Benoetigt {_bad[:2]}",
              not _bad)
        # Die Kategorie steht jetzt in den GRUPPEN-Knoten; die Spalte selbst
        # ist dadurch redundant, bleibt aber fuer die Sortierung bestehen.
        check("b5 Blatt-Knoten tragen ihre Kategorie",
              all(_nd.text(1) for _nd in _leaves) if _leaves else True)
        # KEIN Filter, der Zeilen versteckt: alle Materialien bleiben
        # sichtbar (zurueckgenommen - das war Informationsverlust).
        _grp = [_mat[0].topLevelItem(_g)
                for _g in range(_mat[0].topLevelItemCount())]
        check("b5 Kategorie-Gruppen vorhanden", bool(_grp))
        # ZUGEKLAPPT starten (Nutzer: "wegen Ueberflutung von Informationen").
        check("b5 Gruppen starten zugeklappt",
              all(not g.isExpanded() for g in _grp))
        check("b5 aber sie lassen sich aufklappen",
              all(g.childCount() > 0 for g in _grp))
        check("b5 jede Gruppe hat Kinder", all(g.childCount() > 0 for g in _grp))
        check("b5 Gruppen tragen einen Fortschrittsbalken",
              all(_mat[0].itemWidget(g, 6) is not None for g in _grp))
        check("b5 kein 'Nur offene Posten'-Filter",
              not [c for c in _dlg.findChildren(QCheckBox)
                   if "offene Posten" in c.text()])
        check("b5 nach Kategorie vorsortiert",
              _mat[0].header().sortIndicatorSection() == 1)
        # Reihenfolge muss der Kette folgen, nicht dem Alphabet.
        # Seit Sitzung 16 ist text(0) UEBERSETZT - der Schluessel haengt als
        # Daten am Knoten (Spalte 1, UserRole).
        _cats = [g.data(1, Qt.UserRole) or g.text(0) for g in _grp]
        _seen, _order = [], []
        for _c in _cats:
            if _c not in _seen:
                _seen.append(_c); _order.append(_c)
        _want_order = ["Intermediate Reactions", "Composite Reactions",
                       "Komponenten", "Mineralien / Rohstoffe"]
        _idx = [_pos_von(_want_order, _c) for _c in _order if _c in _want_order]
        check(f"b5 Kategorien in Ketten-Reihenfolge {_order}",
              _idx == sorted(_idx))
        check("b5 'Eingefuegt' ohne Einfuegung ausgeblendet",
              _mat[0].isColumnHidden(4))
        check("b5 'Benoetigt' und 'Genutzt' bleiben sichtbar",
              not _mat[0].isColumnHidden(2) and not _mat[0].isColumnHidden(5))
        # Status-Spalte muss den Rest fuellen - der Fortschrittsbalken ist ein
        # Zell-Widget und zaehlt beim Bemessen nach Inhalt nicht mit.
        from PySide6.QtWidgets import QHeaderView as _QHV5
        eq("b5 Status-Spalte streckt sich ueber die Restbreite",
           _mat[0].header().sectionResizeMode(6), _QHV5.Stretch)
        # Auch hier: keine Roh-IDs statt Itemnamen. Der Materialien-Tab liest
        # zusaetzlich `stock_used`/`surplus` - Items, die ganz aus dem Bestand
        # kommen, waren deshalb namenlos ("#16642").
        _mnums = [_nd.text(0).strip() for _nd in _leaves
                  if _nd.text(0).strip().startswith("#")
                  and _nd.text(0).strip()[1:].isdigit()]
        check(f"b5 keine Roh-IDs im Materialbaum {_mnums[:3]}", not _mnums)
        # Deckungs-Balken: jedes Material UND jede Gruppe.
        from PySide6.QtWidgets import QProgressBar as _QPB6
        _bars = [_mat[0].itemWidget(_nd, 6) for _nd in _leaves]
        _bars = [b for b in _bars if isinstance(b, _QPB6)]
        check(f"b5 jedes Material hat einen Deckungs-Balken "
              f"({len(_bars)}/{len(_leaves)})",
              not _leaves or len(_bars) == len(_leaves))
        _bad_pct = [b.value() for b in _bars if not 0 <= b.value() <= 100]
        check(f"b5 Balkenwerte liegen zwischen 0 und 100 {_bad_pct[:3]}",
              not _bad_pct)
    _pte = _dlg.findChildren(QPlainTextEdit)
    # OPTIK der Tabellen (Nutzer: "ohne Roboter-Schriftart, ohne Grid,
    # lieber Bildchen statt Zahlen links").
    # Der Materialien-Tab ist ein BAUM (kein Gitter/keine Zeilennummern-API),
    # der Blueprints-Tab weiterhin eine Tabelle.
    _bp_tbls = [x for x in _dlg.findChildren(QTableWidget)
                if x.columnCount() == 7]
    for _tb, _nm in ((_bp_tbls[0] if _bp_tbls else None, "Blueprints"),):
        if _tb is None:
            continue
        check(f"b5b {_nm}: kein Gitter", not _tb.showGrid())
        check(f"b5b {_nm}: keine Zeilennummern",
              not _tb.verticalHeader().isVisible())
        check(f"b5b {_nm}: keine Zebrastreifen", not _tb.alternatingRowColors())
        check(f"b5b {_nm}: Icon-Groesse gesetzt", _tb.iconSize().width() >= 20)
    check("b5 Einfuege-Panel vorhanden (Textfeld)", bool(_pte))
    if _pte:
        check("b5 Textfeld ist gross genug", _pte[0].minimumHeight() >= 240)
    _plabels = [l.text() for l in _dlg.findChildren(QLabel)]
    check("b5 Panel-Titel vorhanden",
          any(_t4("PASTE STOCK") in x for x in _plabels))
    check("b5 Panel erklaert WOFUER es gut ist",
          any(_t4("Paste here if ESI is not fast enough.") in x
              for x in _plabels))
    check("b5 Haekchen 'nach ESI-Aktualisierung behalten' vorhanden",
          any(_t4("Keep after ESI updates") in c.text()
              for c in _dlg.findChildren(QCheckBox)))

    # ------------------------------------------------------------ (b4c)
    # Nutzer: "alle Kleininformationen weg, nur mit Mouseover arbeiten" und
    # "mach alle Anzeigen gleichmaessig gross".
    # "Min. Verkaufspreis / Stk" ist auf Nutzerwunsch ebenfalls ausgeblendet
    # (zweite Aufraeum-Runde) - die Zahl steht jetzt im Tooltip von "Gewinn
    # gesamt", zusammen mit dem Preis, mit dem gerechnet wurde.
    _kpi_caps = (_t4("Build cost / unit"), _t4("Total profit"), _t4("Margin"))
    _widths = [l.parent().minimumWidth() for l in _dlg.findChildren(QLabel)
               if l.text() in _kpi_caps and l.isVisibleTo(_dlg)]
    eq("b4c drei sichtbare KPI-Karten", len(_widths), 3)
    check("b4c alle gleich breit", len(set(_widths)) == 1 and _widths[0] >= 200)
    check("b4c Min. Verkaufspreis ist NICHT mehr sichtbar",
          not [l for l in _dlg.findChildren(QLabel)
               if l.text() == "Min. Verkaufspreis / Stk" and l.isVisibleTo(_dlg)])
    # ...aber die Information darf nicht verloren gehen: der Tooltip von
    # "Gewinn gesamt" muss sagen, MIT WELCHEM PREIS gerechnet wurde und wo die
    # Verlustschwelle liegt. Sonst haette das Aufraeumen eine Zahl entfernt,
    # die nirgends mehr steht.
    _pf = [l for l in _dlg.findChildren(QLabel)
           if l.text() == "Gewinn gesamt"]
    _pf_tip = ""
    for _l in _pf:
        _sibs = _l.parent().findChildren(QLabel) if _l.parent() else []
        for _sv in _sibs:
            if _sv.toolTip():
                _pf_tip = _sv.toolTip()
    # DIE ZAHLEN STEHEN NICHT MEHR IM MOUSEOVER, SONDERN IN DEN AUSGEKLAPPTEN
    # DETAILS (Nutzer: "das brauchen wir ja nicht mehr, alle diese
    # Informationen stehen ja auch unten wenn man Details ausklappt").
    # Zwei Anzeigen derselben Zahlen waren genau die Quelle der Abweichungen,
    # die in dieser Sitzung gefunden wurden - deshalb bleibt EINE.
    # ------------------------------------------------------------ (b12)
    # KATEGORIEN ALS ECHTE GRUPPEN im Rezept-Baum (Nutzer: "wo sind die
    # Gruppen?"). Vorher stand die Kategorie nur als "  · Komponente" hinter
    # dem Namen. Jetzt: ein Kopfknoten je Kategorie, Items darunter.
    # Denselben Filter wie b6 benutzen - `findChildren` liefert auch den
    # Materialien-Baum, und der hat schon immer Gruppen.
    _rt12 = next((t for t in _dlg.findChildren(QTreeWidget)
                  if t.topLevelItemCount() > 0 and t.headerItem()
                  and t.headerItem().text(0) == "Item"
                  and t.headerItem().text(2) == "Aktion"), None)
    if _rt12 is not None and _rt12.topLevelItemCount():
        _r12 = _rt12.topLevelItem(0)
        _kids12 = [_r12.child(_k) for _k in range(_r12.childCount())]
        check("b12 oberste Ebene sind Kategorie-Koepfe (ohne type_id)",
              bool(_kids12) and all(
                  _k.data(0, Qt.UserRole) is None for _k in _kids12))
        check("b12 die Materialien haengen DARUNTER",
              any(_k.childCount() > 0 for _k in _kids12))
        check("b12 Kopf nennt die Anzahl",
              all("(" in _k.text(0) for _k in _kids12))
        # Ein Kopf ist kein Material - er darf nicht abhakbar sein.
        # AUFKLAPPZUSTAND (Nutzer: "so standardmaessig ausgeklappt wie im
        # Bild"): Endprodukt und Kategorie-Koepfe offen, alles darunter zu.
        check("b12 Endprodukt ist aufgeklappt", _r12.isExpanded())
        check("b12 Kategorie-Koepfe sind aufgeklappt",
              all(_k.isExpanded() for _k in _kids12))
        check("b12 die Materialien darunter sind zugeklappt",
              all(not _k.child(_i).isExpanded()
                  for _k in _kids12 for _i in range(_k.childCount())))
        check("b12 Kopfknoten sind nicht abhakbar",
              all(not (_k.flags() & Qt.ItemIsUserCheckable) for _k in _kids12))
    _sub = _src_mw[_pos_von(_src_mw, "_profit_rows = ["):]
    _sub = _sub[:_pos_von(_sub, "]")]
    for _z in ("Verkaufspreis", "Verlustschwelle", "Baukosten", "= Gewinn",
               "Marge"):
        check(f"b4c Details-Spalte nennt '{_z}'", _z in _sub)
    check("b4c kein Zahlen-Tooltip mehr an der Gewinn-Karte",
          'st_profit.setToolTip("")' in _src_mw)
    # Der Hinweis zur PREISQUELLE darf NICHT mitverschwinden - er steht in
    # keiner Spalte, und ohne ihn waere nicht erkennbar, ob die Baukosten
    # orderbuch-genau sind oder auf Flachpreisen beruhen.
    check("b4c Preisquellen-Hinweis bleibt an der Kosten-Karte",
          "st_cost.setToolTip(_cost_src_tip)" in _src_mw)


    _subs = [l.text() for l in _dlg.findChildren(QLabel)
             if l.isVisibleTo(_dlg) and l.text().startswith(
                 ("= ", "Markt unterbieten", "davon ", "VOR Geb", "\u26a0 Markt"))]
    check("b4c keine Unterzeilen mehr sichtbar", not _subs)
    _tips = " ".join(l.toolTip() for l in _dlg.findChildren(QLabel))
    check("b4c Stueckwert steht im Tooltip", "je St" in _tips or "per unit" in _tips)

    # ------------------------------------------------------------ (b4d)
    # KOMPAKTER KOPFBEREICH (Nutzer): die Zeile "ENDPRODUKT - DAS ZU BAUENDE
    # ITEM" ist weg, Titel und Kennzahlen stehen NEBENEINANDER. Das schafft
    # Hoehe fuer Tabs und Item-Liste.
    _lbl_txt = [l.text() for l in _dlg.findChildren(QLabel)]
    check("b4d Kopfzeile 'ENDPRODUKT' entfernt",
          not any("ENDPRODUKT" in x for x in _lbl_txt))
    check("b4d Titel und Kennzahlen liegen in einer Zeile",
          "_hero_row.addLayout(stats_row, 1)" in _src_mw
          and "hv.addLayout(_hero_row)" in _src_mw)
    # Statuszelle: Balken-Text darf nicht doppelt gezeichnet werden.
    # Seit (aa46) wird die Status-Zelle direkt als NumericItem mit LEEREM
    # Text angelegt - nachtraegliches Leeren ist damit unnoetig, und die
    # Spalte bleibt trotzdem sortierbar (ueber den Rang).
    check("b4d Statuszelle hat leeren Text und einen Sortier-Rang",
          'it = NumericItem("", _st_rank)' in _src_mw)
    # Die Liste ist um die Invention-Schluessel gewachsen (Datacores standen
    # sonst als "#20411" da). Geprueft wird, dass ALLE Plan-Schluessel mit
    # Mengen drin sind - nicht mehr eine feste Zeile.
    # Die Schluesselliste gibt es jetzt EINMAL (PLAN_QTY_KEYS) - vorher stand
    # sie zweimal da, und beim Nachtragen der Invention-Schluessel wurde nur
    # eine erwischt.
    check("b4d Namen auch fuer Items unterhalb der Baumtiefe",
          all(f'"{_k}"' in _src_mw[_pos_von(_src_mw, "PLAN_QTY_KEYS = ("):][:260]
              for _k in ("stock_used", "surplus", "build_runs", "buy",
                         "inv_buy", "inv_stock_used")))
    check("b4d und beide Sammelstellen nutzen dieselbe Liste",
          _src_mw.count("for _pk in self.PLAN_QTY_KEYS:") == 1
          and _src_mw.count("for _k in self.PLAN_QTY_KEYS:") == 1)

    # ------------------------------------------------------------ (b5c)
    # Die zwei WARNUNGEN, die beim Entschlacken NICHT verlorengehen duerfen.
    check("b5c Kapazitaets-Warnung sitzt im Einkaufswagen-Pfad",
          "Does not fit in one trip" in _src_mw
          and '_ti = getattr(self, "_bd_transport", None)' in _src_mw)
    check("b5c Struktur-Warnung als Popup beim Oeffnen",
          "No hangar stock is counted" in _src_mw
          and "_bd_nostruct_warned" in _src_mw)
    check("b5c Transportzeile nur noch bei Ueberschreitung sichtbar",
          "st_transport.setVisible(bool(tinfo.get(\"over_capacity\"))" in _src_mw)

    # ------------------------------------------------------------ (b5d)
    # Aufgeraeumte Anordnung: Puffer/Fracht gehoeren nach OBEN, die
    # Aktionsknoepfe nach unten links, der Details-Bereich bleibt schmal.
    # Puffer wanderte auf Nutzer-Wunsch wieder nach UNTEN zur
    # Einkaufswagen-Aktion - er wirkt ja beim Hinzufuegen zum Wagen.
    # PUFFER UND WAGEN-KNOPF SIND WEG (Nutzer: "alles ist jetzt ueber den
    # Material-Tab machbar"). Beides steckt im Einkaufsfenster, das
    # "Materialien kopieren" oeffnet - vorher gegengeprueft, dass beide Wege
    # dieselbe Appraisal liefern. Die Fusszeile traegt nur noch Speichern.
    # NICHT auf "r2.addWidget(cart)" pruefen: dieselbe Variable gibt es im
    # Multibuy-Fenster weiter unten. Entscheidend ist, dass der BAUPLAN
    # nichts mehr in den Wagen legt.
    check("b5d kein Einkaufswagen-Knopf mehr im Bauplan",
          'QPushButton("\\U0001F6D2 Zu Einkaufswagen' not in _src_mw
          and 'self._plan_to_cart({"buy": plan.get("buy", {})}, names)'
          not in _src_mw)
    check("b5d kein zweites Puffer-Feld mehr in der Fusszeile",
          "r2.addWidget(surplus_spin)" not in _src_mw)
    # Die EINSTELLUNG muss bleiben - das Fenster liest und schreibt sie.
    check("b5d Puffer-Einstellung bleibt erhalten",
          '"bau_buy_surplus"' in _src_mw)
    check("b5d statisches Hub-Label nicht mehr in der Kopfleiste",
          "ctrl.addWidget(_lhub_lbl)" not in _src_mw)
    check("b5d Hub-Label hat trotzdem einen Parent (kein Geisterfenster)",
          "_lhub_lbl.setParent(dlg)" in _src_mw)
    for _w in ("_tl", "transport_cap_spin", "_tcol", "freight_dec_cb"):
        check(f"b5d oben statt unten: {_w}", f"r2s.addWidget({_w})" in _src_mw
              or f"r2s.addLayout({_w})" in _src_mw)
    # Die Fracht-Zeile sitzt jetzt in einem EINGEKLAPPTEN Feld im Kopfbereich
    # (Nutzer: "das mit dem Frachtraum stoert mich noch").
    check("b5d Fracht-Block ist einklappbar",
          '_fr_w = QWidget(); _fr_w.setLayout(r2s)' in _src_mw
          and "Fracht & Transport" in _src_mw)
    # Heisst seit dem Umzug in die rechte Details-Spalte "Frachtkosten"
    # (Nutzer) - zugeklappt muss sie trotzdem starten.
    check("b5d und standardmaessig zugeklappt",
          '"Freight cost"), _fr_w, expanded=False' in _src_mw)
    check("b5d Struktur-Zeile nicht mehr dauerhaft sichtbar",
          "st_struct.setVisible(False)" in _src_mw)
    check("b5d Fusszeilen-Hinweis in die Tooltips verlegt",
          "hint.setVisible(False)" in _src_mw)
    check("b5d beide behalten einen Parent (kein Geisterfenster)",
          "st_struct.setParent(dlg)" in _src_mw
          and "hint.setParent(dlg)" in _src_mw)
    # "Bauplan speichern" ist in die OBERE Leiste gewandert (Nutzer), direkt
    # hinter "Neu berechnen" - und neutral gestylt, damit dort genau EINE
    # Aktion hervorgehoben bleibt. "Schliessen" entfaellt ganz (rotes X).
    check("b5d Speichern sitzt hinter 'Neu berechnen' in der Kopfleiste",
          "ctrl.insertWidget(ctrl.indexOf(recalc) + 1, save_btn)" in _src_mw)
    check("b5d Speichern ist nicht mehr hervorgehoben",
          "save_btn.setStyleSheet(_secondary_btn_css)" in _src_mw)
    check("b5d kein eigener Schliessen-Knopf mehr",
          'cl = QPushButton("Schlie\\u00dfen"); cl.clicked.connect(dlg.accept)'
          not in _src_mw)
    # Seit dem Zwei-Spalten-Umbau (Kosten links, Gewinn rechts) darf der
    # Bereich breiter sein - begrenzt bleiben MUSS er trotzdem, sonst zieht
    # er sich wieder ueber die ganze Fensterbreite ("kein Chamaeleon").
    check("b5d Details-Bereich ist breitenbegrenzt",
          "st_details_panel.setMaximumWidth(1240)" in _src_mw)

    # ------------------------------------------------------------ (b5e)
    # TAB-REIHENFOLGE (Nutzer): erst das Arbeitsmaterial, dann das
    # Nachschlagewerk. Und der Dialog startet auf Materialien.
    from PySide6.QtWidgets import QTabWidget as _QTW
    # ANGEPASST: der Invention-Tab ist nicht mehr immer da. `_Recipes` oben
    # hat KEINEN Invention-Eintrag, ist also ein T1-Endprodukt - dort gibt es
    # nichts zu erfinden, und der Tab wird bewusst entfernt (ME/TE stehen
    # stattdessen oben neben der Menge). Geprueft wird deshalb die RELATIVE
    # Reihenfolge der vorhandenen Tabs, nicht mehr eine feste Anzahl. Die
    # Vollbesetzung mit Invention deckt b9 mit einem erfundenen Endprodukt ab.
    _tabws = [x for x in _dlg.findChildren(_QTW) if x.count() >= 4]
    check("b5e Tab-Leiste des Bauplans gefunden", bool(_tabws))
    if _tabws:
        _tb = _tabws[0]
        _titles = [_tb.tabText(_i) for _i in range(_tb.count())]
        # Rezept-Struktur zuerst: dort werden die Entscheidungen getroffen,
        # die Materialliste ist das Ergebnis davon.
        # Runplaner ganz nach rechts (Nutzer): er ist der letzte Schritt.
        # REIHENFOLGE = ARBEITSABLAUF (Nutzer): "Rezept anschauen, dann
        # Invention planen, dann Blueprints checken, dann Materialien
        # einkaufen, dann ingame mit dem Runplaner arbeiten."
        # Zweisprachig (Sitzung 16): die Reitertexte laufen durch t().
        _order = [_t4("Recipe structure"), "Invention", "Blueprints",
                  _t4("Materials"), _t4("Run planner")]
        _pos_of = {}
        for _key in _order:
            for _i, _t in enumerate(_titles):
                if _key in _t:
                    _pos_of[_key] = _i
                    break
        _seen = [_pos_of[_k] for _k in _order if _k in _pos_of]
        check(f"b5e Reihenfolge stimmt  ({_titles})", _seen == sorted(_seen))
        check("b5e T1-Endprodukt hat keinen Invention-Tab", "Invention" not in _pos_of)
        for _key in (_t4("Recipe structure"), _t4("Materials"),
                     _t4("Run planner"), "Blueprints"):
            check(f"b5e {_key} vorhanden  ({_titles})", _key in _pos_of)
        eq("b5e Dialog startet auf dem ersten Tab", _tb.currentIndex(), 0)
        # NICHT nur relativ pruefen: die alte Fassung verglich die Positionen
        # der VORHANDENEN Tabs untereinander - eine vertauschte Reihenfolge
        # blieb dadurch gruen, solange sie zur erwarteten Liste passte. Hier
        # die tatsaechliche Abfolge, Tab fuer Tab.
        _ist = [_t for _t in _titles
                if any(_k in _t for _k in _order)]
        _soll = [_k for _k in _order
                 if any(_k in _t for _t in _titles)]
        check(f"b5e tatsaechliche Abfolge stimmt  ({_ist})",
              [next(_k for _k in _order if _k in _t) for _t in _ist] == _soll)

    # ------------------------------------------------------------ (b5f)
    # Blueprints-Tab: dieselben zwei Fehler wie im Materialien-Tab.
    check("b5f Status-Pille zeichnet den Item-Text nicht doppelt",
          "_bi = tbl.item(i, 6)" in _src_mw and '_bi.setText("")' in _src_mw)
    check("b5f Blueprint-Status-Spalte streckt sich",
          _src_mw.count("_bh.setSectionResizeMode(6, _QHV2.Stretch)") == 1)

    # ------------------------------------------------------------ (b5g)
    # SORTIEREN DARF DIE BALKEN NICHT VERWECHSELN. Qt sortiert die ITEMS um,
    # laesst Zell-WIDGETS aber am alten Zeilenindex stehen - danach zeigt der
    # Balken die Aussage einer FREMDEN Zeile (vom Nutzer im Screenshot
    # gesehen, nachdem die Status-Spalte sortierbar wurde).
    if _mat:
        from PySide6.QtWidgets import QProgressBar as _QPB5
        _mt = _mat[0]

        def _bar_texts():
            _out = []
            for _g in range(_mt.topLevelItemCount()):
                _gi = _mt.topLevelItem(_g)
                for _c in range(_gi.childCount()):
                    _nd = _gi.child(_c)
                    _w = _mt.itemWidget(_nd, 6)
                    if isinstance(_w, _QPB5):
                        _out.append((_nd.text(0), _w.format()))
            return _out
        _before = dict(_bar_texts())
        check("b5g Balken sind vor dem Sortieren vorhanden", bool(_before))
        _mt.sortByColumn(6, Qt.AscendingOrder)
        _app.processEvents()
        _after = dict(_bar_texts())
        check("b5g nach dem Sortieren gleich viele Balken",
              len(_after) == len(_before) and bool(_after))
        _mismatch = [k for k in _after if _before.get(k) != _after[k]]
        check(f"b5g jeder Balken gehoert noch zu SEINEM Item {_mismatch[:2]}",
              not _mismatch)
        _mt.sortByColumn(0, Qt.AscendingOrder)
        _app.processEvents()
        _after2 = dict(_bar_texts())
        check("b5g auch nach erneutem Sortieren korrekt",
              all(_before.get(k) == v for k, v in _after2.items()))
        # Gruppierung darf durch Sortieren NICHT zerfallen.
        check("b5g Gruppen bleiben nach dem Sortieren erhalten",
              _mt.topLevelItemCount() == len(_grp))
    # Einfuege-Panel: "Dauerhaft gueltig" ist standardmaessig AN.
    _perm = [c for c in _dlg.findChildren(QCheckBox)
             if _t4("Keep after ESI updates") in c.text()]
    check("b5g Haken 'nach ESI-Aktualisierung behalten' existiert", bool(_perm))
    if _perm:
        check("b5g und ist standardmaessig gesetzt", _perm[0].isChecked())

    # ------------------------------------------------------------ (b5h)
    # RECHTSKLICK -> BLACKLIST im Rezept-Baum (Nutzer-Wunsch). Loest das
    # Tippfehler-Problem an der Wurzel: kein Tippen, kein Namensabgleich.
    check("b5h Mehrfachauswahl im Rezept-Baum",
          "tw.setSelectionMode(QTreeWidget.ExtendedSelection)" in _src_mw)
    # SEIT SITZUNG 16 ENGLISCH im Quelltext, Deutsch im Katalog.
    check("b5h Kontextmenue bietet 'Auf die Blacklist'",
          "Add to blacklist" in _src_mw)
    check("b5h und das Zuruecknehmen", "Remove from blacklist" in _src_mw)
    check("b5h mehrere Items auf einmal",
          "_sel = [x for x in tw.selectedItems()" in _src_mw)
    check("b5h Textfeld wird nachgezogen",
          "def _push_blacklist_to_ui(self):" in _src_mw)

    # ------------------------------------------------------------ (b5i)
    # FERTIGUNGSTIEFE: Panel vorhanden, Stufen setzen die Kategorie-Haken.
    from PySide6.QtWidgets import QRadioButton as _QRB
    _rbs = [r for r in _dlg.findChildren(_QRB)
            if r.text() in ("Nur das Endprodukt", "Ab Komponenten",
                            "Ab Composite-Reaktionen", "Alles selbst",
                            "End product only", "From components",
                            "From composite reactions", "Everything yourself")]
    eq("b5i vier Tiefenstufen sichtbar", len(_rbs), 4)
    check("b5i genau eine ist gewaehlt",
          sum(1 for r in _rbs if r.isChecked()) == 1)
    _by_txt = {r.text(): r for r in _rbs}
    if "Nur das Endprodukt" in _by_txt:
        _by_txt["Nur das Endprodukt"].setChecked(True)
        _app.processEvents()
        _boxes = getattr(win, "_bp_own_boxes", {}) or {}
        check("b5i Stufe 1 hakt ALLE Kategorien ab",
              all(not c.isChecked() for c in _boxes.values()) if _boxes else True)
        _by_txt["Alles selbst"].setChecked(True)
        _app.processEvents()
        check("b5i Stufe 4 hakt alle wieder an",
              all(c.isChecked() for c in _boxes.values()) if _boxes else True)

    # ------------------------------------------------------------ (b6)
    # Rezept-Baum muss Zeilen haben - sonst ist der Aufbau zwar fehlerfrei,
    # aber leer (auch ein Fehlerbild).
    # EINDEUTIG identifizieren: seit der Materialien-Tab ebenfalls ein Baum
    # ist, gibt es MEHRERE QTreeWidgets. Der Rezept-Baum hat die Kopfzeile
    # "Item / Menge / Aktion" - danach suchen, nicht nach der Reihenfolge.
    _trees = [t for t in _dlg.findChildren(QTreeWidget)
              if t.topLevelItemCount() > 0 and t.headerItem()
              and t.headerItem().text(0) == "Item"
              and t.headerItem().text(2) in ("Aktion", "Action")]
    check("b6 Rezept-Baum ist gefuellt", bool(_trees))
    if _trees:
        _rt = _trees[0]
        check("b6 Spalte 'ISK/Stk' ausgeblendet", _rt.isColumnHidden(3))
        check("b6 Spalte 'Kosten' ausgeblendet", _rt.isColumnHidden(4))
        check("b6 keine Zebrastreifen mehr", not _rt.alternatingRowColors())
        # Jedes Item im Baum muss einen NAMEN haben, keine "#12345"-Nummer.
        _nums = []

        def _walk_names(_it):
            _txt = _it.text(0).strip()
            if _txt.startswith("#") and _txt[1:].isdigit():
                _nums.append(_txt)
            for _k in range(_it.childCount()):
                _walk_names(_it.child(_k))
        for _k in range(_rt.topLevelItemCount()):
            _walk_names(_rt.topLevelItem(_k))
        check(f"b6 keine Roh-IDs statt Itemnamen {_nums[:3]}", not _nums)
        # KATEGORIE-ORDNUNG auf der obersten Ebene (Nutzer: "man erkennt
        # nicht, was welcher Kategorie angehoert"). Reihenfolge folgt der
        # Bau-Logik: Komponenten -> Reaktionen -> Kauf-Material.
        _r0 = _rt.topLevelItem(0)
        _kid_txt = [_r0.child(_k).text(0) for _k in range(_r0.childCount())]
        # "Kauf-Material" ist inzwischen aufgeteilt in Mineralien /
        # Mond-Materialien / Rohstoffe (Nutzer: "die sind so vermischt").
        # Die Aussage bleibt dieselbe: jedes Item traegt eine Kategorie, und
        # die Einkaufsposten stehen hinten.
        _kaufcats = ("Mineralien", "Mond-Materialien", "Rohstoffe")
        # Seit dem Auftrag "unbekannte Gruppe darf keine Kategorie behaupten"
        # ist auch die ausdrueckliche Markierung zulaessig: ein Item ohne
        # SDE-Gruppe steht unter "noch nicht aufgeloest" statt faelschlich
        # unter "Rohstoffe" (Arbeitsregel 6). Die Aussage des Tests bleibt:
        # KEIN Kopf ohne Etikett - behauptet wird aber nichts mehr.
        _labels6 = ("Komponente", "Reaktion") + _kaufcats \
            + (MainWindow.GRUPPE_UNBEKANNT,) \
            + ("Component", "Reaction", "Minerals", "Moon materials",
               "Raw materials", "not resolved yet")
        check("b6 Kategorie steht am Item",
              all(any(c in x for c in _labels6) for x in _kid_txt)
              if _kid_txt else True)
        _rank = {"Komponente": 1, "Reaktion": 2}
        _rank.update({c: 3 for c in _kaufcats})
        _seq = [next((v for k, v in _rank.items() if k in x), 3)
                for x in _kid_txt]
        check(f"b6 nach Kategorie sortiert {_seq}", _seq == sorted(_seq))

    # ------------------------------------------------------------ (b7)
    # Der Neu-Berechnen-Knopf muss klickbar sein, ohne zu werfen. Damit
    # laeuft rebuild() ein zweites Mal - der UnboundLocalError trat genau
    # in diesem Pfad auf.
    _rec = [b for b in _buttons if "Neu berechnen" in b.text()]
    if _rec:
        try:
            _rec[0].click()
            _app.processEvents()
            check("b7 'Neu berechnen' laeuft ohne Ausnahme", True)
        except Exception as e:                            # pragma: no cover
            _fail.append(f"b7 'Neu berechnen': {type(e).__name__}: {e}")

# ---------------------------------------------------------------- (b7b)
# TOOLTIPS MUESSEN UMBRECHEN. Qt zeigt reinen Text ohne Zeilenumbruch als
# EINE Zeile - lange Erklaerungen zogen sich ueber die ganze Fensterbreite
# (Nutzer: "gigantisch und viel zu lang auf die Breite gezogen").
if _dlg is not None:
    from PySide6.QtWidgets import QWidget as _QW7
    _all_tips = [x.toolTip() for x in _dlg.findChildren(_QW7) if x.toolTip()]
    check("b7b es gibt ueberhaupt Tooltips", len(_all_tips) > 10)
    _plain = [x for x in _all_tips if not x.lstrip().startswith("<")]
    check(f"b7b alle Tooltips sind umbruchfaehig ({len(_plain)} roh)",
          not _plain)
    check("b7b Breitenbegrenzung gesetzt",
          all("max-width" in x for x in _all_tips))

# ---------------------------------------------------------------- (b7c)
# SCHRIFTART der Item-Listen (Nutzer: "etwas weniger roboterisch"). Vorher
# Consolas/monospace - das las sich wie ein Terminal.
_theme_src = open(os.path.join(_ROOT,
                               "eve_trader", "ui", "theme.py"),
                  encoding="utf-8").read()
# theme.py ist ein f-String-Template ({{ }}), deshalb kein Klammer-Regex,
# sondern ein Blick auf den Abschnitt hinter dem Selektor.
for _blk in ("QTableWidget {{", "QTreeWidget {{"):
    _i7 = _theme_src.find(_blk)
    _seg = _theme_src[_i7:_i7 + 420] if _i7 >= 0 else ""
    # NUR die font-family-Zeile pruefen: das Wort "Consolas" steht auch im
    # erklaerenden Kommentar daneben und wuerde sonst falschen Alarm geben.
    _ff = [l for l in _seg.splitlines() if "font-family" in l]
    check(f"b7c {_blk.split()[0]} nicht mehr monospace",
          bool(_ff) and all("Consolas" not in l for l in _ff))
    # Seit der Industrie-Schrift steht dort die KETTE {FONT} statt einer
    # fest verdrahteten Familie - die Zusage ist "UI-Schrift, nicht Mono".
    check(f"b7c {_blk.split()[0]} nutzt die UI-Schrift",
          bool(_ff) and any("{FONT}" in l for l in _ff))
# Absichtlich monospace geblieben: dort haengt die Lesbarkeit an
# gleichbreiten Ziffern.
check("b7c KPI-Werte bleiben monospace",
      "QLabel#KpiValue" in _theme_src
      and "{MONO}" in _theme_src[_pos_von(_theme_src, "QLabel#KpiValue"):
                                   _pos_von(_theme_src, "QLabel#KpiValue") + 120])

# ---------------------------------------------------------------- (b7c)
# ZWEITES SZENARIO: Markt UNTER dem Mindestpreis. Dieser Zweig war bisher
# ungeprueft - und genau dort stand ein `_tip.insert(...)` auf einer
# Zeichenkette statt auf der Liste. Ergebnis: JEDER Bauplan stuerzte beim
# Oeffnen ab ("AttributeError: 'str' object has no attribute 'insert'"),
# waehrend der Test gruen blieb, weil sein Verkaufspreis stets ueber den
# Kosten lag. Ein Test, der nur den guenstigen Fall kennt, prueft die Haelfte.
_res_low = dict(_res)
_res_low["sell"] = 1.0            # weit unter jedem Mindestpreis
try:
    win._show_build_detail(100, "Testship-Verlust", _res_low)
    check("b7c Bauplan baut auch bei Markt UNTER Mindestpreis", True)
    _dlg_low = getattr(win, "_bd_dialog", None)
    if _dlg_low is not None:
        _tips_low = " ".join(x.toolTip() for x in _dlg_low.findChildren(QLabel)
                             if x.toolTip())
        check("b7c Verlust-Warnung steht im Tooltip",
              "MINDESTPREIS" in _tips_low or "Verlust" in _tips_low
              or "MINIMUM PRICE" in _tips_low or "loss" in _tips_low)
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b7c Markt unter Mindestpreis: {type(e).__name__}: {e}")

# ---------------------------------------------------------------- (b7d)
# KEIN VERKAUFSPREIS UEBERHAUPT - der Capital-Fall (Nutzer "buyenne",
# 15.09.2026, Discord: Hel und Phoenix stuerzten ab, Stork und Avalanche
# nicht). Capitals haben in Jita praktisch keine Sell-Orders; sind DANN
# auch noch keine Contract-Preise geladen, ist `_sell_eff` leer.
#
# WAS DANN PASSIERTE: der ganze Gewinn-Block haengt an `if _sell_eff:` -
# dort entstehen `gross`, `prof`, `prof_raw` und `total_all`. Die rechte
# Spalte ("Verkaufserloes brutto", "= Gewinn", "Marge") liest sie danach
# BEDINGUNGSLOS. Ohne Verkaufspreis gab es sie nie:
#   UnboundLocalError: cannot access local variable 'gross'
# `marge` und `fees` waren vorbelegt - die beiden anderen wurden vergessen,
# als die Spalte dazukam. Genau darum steht hier ein Test und kein Kommentar.
_res_nosell = dict(_res)
_res_nosell["sell"] = 0.0             # kein Marktpreis (Capital in Jita)
_res_nosell["sell_is_contract"] = True
win._bd_hub_sell_price = None
win._bd_contract_sell = None          # Contract-Preise NICHT geladen
try:
    win._show_build_detail(100, "Testcapital-ohne-Preis", _res_nosell)
    check("b7d Bauplan oeffnet auch ganz OHNE Verkaufspreis", True)
    _dlg_ns = getattr(win, "_bd_dialog", None)
    check("b7d Dialog steht", _dlg_ns is not None)
    if _dlg_ns is not None:
        # GEGENPROBE ZUM NORMALFALL: ohne Preis darf dort KEINE Zahl
        # stehen - weder eine 0 noch ein erfundener Gewinn. Ein Strich ist
        # die ehrliche Antwort (Regel 3: lieber nichts behaupten).
        _txt_ns = [x.text() for x in _dlg_ns.findChildren(QLabel)]
        check("b7d ohne Preis steht kein erfundener Gewinn da",
              "\u2013" in _txt_ns or "\u2014" in _txt_ns)
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b7d ohne Verkaufspreis: {type(e).__name__}: {e}")

# ---------------------------------------------------------------- (b7e)
# DER CONTRACT-KNOPF ZEIGT SICH IM RICHTIGEN MOMENT.
# NUTZER, 15.09.2026: "der load contracts button soll ersichtlicher werden,
# nicht versteckt in Dropdowns" - und blinken wie der Markt-Scan-Knopf.
# Der richtige Moment ist genau der, in dem das Verkaufsfeld leer bleibt.
#
# NICHT AUF isVisible() PRUEFEN: in einem nie angezeigten Fenster meldet das
# IMMER False (teuer gelernte Qt-Falle). isHidden() sagt dagegen, ob das
# Widget AUSDRUECKLICH versteckt wurde - genau die Frage hier.
_ctb = getattr(win, "_bd_ct_btn", None)
check("b7e der Contract-Knopf existiert als eigener Knopf", _ctb is not None)
if _ctb is not None:
    check("b7e ohne Verkaufspreis ist er sichtbar", not _ctb.isHidden())
    _tmr_ct = getattr(_ctb, "_ct_blink_timer", None)
    check("b7e und er blinkt", _tmr_ct is not None and _tmr_ct.isActive())
    # KEIN GROESSENSPRUNG: beide Blinkzustaende tragen einen 2-px-Rahmen
    # (Nutzer-Befund Sitzung 20 am Markt-Scan-Knopf - dieselbe Falle).
    check("b7e Ruhezustand traegt schon 2 px Rahmen",
          "border:2px solid" in getattr(_ctb, "_ct_css", ""))
    win._blink_rahmen(_ctb, True, getattr(_ctb, "_ct_css", ""))
    _an_css = _ctb.styleSheet()
    win._blink_rahmen(_ctb, False, getattr(_ctb, "_ct_css", ""))
    _aus_css = _ctb.styleSheet()
    check("b7e beide Zustaende sind gleich stark gerahmt",
          _an_css.count("border:2px solid") == _aus_css.count("border:2px solid"))
    check("b7e das Grund-Aussehen bleibt beim Blinken erhalten",
          "padding:6px 12px" in _an_css and "padding:6px 12px" in _aus_css)
# MIT Verkaufspreis muss er wieder weg sein - sonst steht ein blinkender
# Knopf in jedem normalen Bauplan und faellt genau dann nicht mehr auf,
# wenn er gebraucht wird.
try:
    win._show_build_detail(100, "Testship", _res)
    _ctb2 = getattr(win, "_bd_ct_btn", None)
    check("b7e mit Verkaufspreis ist der Knopf versteckt",
          _ctb2 is not None and _ctb2.isHidden())
    _tmr2 = getattr(_ctb2, "_ct_blink_timer", None)
    check("b7e und das Blinken steht still",
          _tmr2 is None or not _tmr2.isActive())
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b7e Contract-Knopf mit Preis: {type(e).__name__}: {e}")

# ---------------------------------------------------------------- (b7f)
# DER NAME IM RUNPLANER IST KOPIERBAR UND GERAHMT.
# NUTZER, 15.09.2026: "im Runplaner steht Silicon Diborite - klickt man drauf,
# bekommt man Silicon Diborite Reaction Formula ins Clipboard", dazu ein
# kleiner Rahmen wie um die Run-Zahlen, fette Run-Zahlen, und die FARBE des
# Namens soll bleiben (gebaute Zeilen blau, nicht amber).
from PySide6.QtWidgets import QTreeWidgetItem as _TWI7f
from eve_trader.ui.mw_basis import (ROLLE_KOPIERNAME as _RKN7f,
                                    kopier_text_rect as _ktr7f)
_dlg7f = getattr(win, "_bd_dialog", None)
_sched7f = next((x for x in (_dlg7f.findChildren(QTreeWidget) if _dlg7f else [])
                 if x.columnCount() == 6), None)
check("b7f der Runplaner-Baum ist da", _sched7f is not None)
if _sched7f is not None:
    # KEINE HERVORHEBUNG MEHR (Nutzer, 15.09.2026: "die Items sollen wieder
    # normal aussehen"). Erst war es ein Rahmen, dann ein Chip - beides zu
    # laut. Die Zeile sieht aus wie jede andere; nur der Klick kopiert.
    check("b7f Spalte 0 malt NICHTS Eigenes mehr",
          _sched7f.itemDelegateForColumn(0) is None)
    # DAS KAESTCHEN BLEIBT FREI: der Rahmen (und damit die Trefferflaeche)
    # faengt rechts vom Haken an - sonst kopierte jeder Haken still mit.
    _ti7f = _TWI7f(["Silicon Diborite", "130", "", "", "", ""])
    _sched7f.addTopLevelItem(_ti7f)
    _ti7f.setData(0, _RKN7f, "Silicon Diborite Reaction Formula")
    _idx7f = _sched7f.indexFromItem(_ti7f, 0)
    _r7f = _ktr7f(_sched7f, _idx7f, _sched7f.visualRect(_idx7f))
    check("b7f die Trefferflaeche laesst das Kaestchen aus",
          _r7f is not None and _r7f.left() > _sched7f.visualRect(_idx7f).left())
    # KEIN KOPIEREN OHNE NAMEN und nicht in anderen Spalten - sonst
    # ueberschreibt jeder Klick im Baum die Zwischenablage.
    _ti_ohne7f = _TWI7f(["Leziris Lezflow", "", "", "", "", ""])
    _sched7f.addTopLevelItem(_ti_ohne7f)
    QApplication.clipboard().setText("UNBERUEHRT")
    win._sched_name_klick(_ti_ohne7f, 0)
    win._sched_name_klick(_ti7f, 3)
    check("b7f ein Klick ohne Namen kopiert nichts",
          QApplication.clipboard().text() == "UNBERUEHRT")
    _sched7f.takeTopLevelItem(_sched7f.indexOfTopLevelItem(_ti7f))
    _sched7f.takeTopLevelItem(_sched7f.indexOfTopLevelItem(_ti_ohne7f))
# DIE VERDRAHTUNG IM RUNPLANER SELBST - am Quelltext, weil der Baum ohne
# getickte Bau-Charaktere leer bleibt und die Pruefung sonst blind waere.
_src7f = open("eve_trader/ui/mw_bauplan_tabs.py", encoding="utf-8").read()
check("b7f der Formel-Name wird an der Zeile hinterlegt",
      "iit.setData(0, ROLLE_KOPIERNAME," in _src7f)
check("b7f und er kommt aus _bp_name_fuer (EINE Regel)",
      "self._bp_name_fuer(\n"
      "                                    self._bp_basisname(a.get(\"tid\"), a.get(\"name\")),"
      in _src7f)
check("b7f die Run-Zahl steht fett", "_fr.setBold(True)" in _src7f
      and "iit.setFont(1, _fr)" in _src7f)
# GAR KEIN ZEICHNEN MEHR IN mw_basis: weder Rahmen noch Chip. Waere eines
# davon zurueck, saehe die Zeile wieder anders aus als der Rest des Baums.
_src7f_b = open("eve_trader/ui/mw_basis.py", encoding="utf-8").read()
check("b7f in mw_basis wird nichts mehr in die Spalte gemalt",
      "QStyledItemDelegate" not in _src7f_b
      and "drawRoundedRect" not in _src7f_b)

# ---------------------------------------------------------------- (b7g)
# BAUPLAENE SELBER ANORDNEN (Nutzer, 15.09.2026).
# Ein Umschalter haelt die automatische Sortierung nach Fortschritt heraus,
# die Karten lassen sich mit gehaltener linker Maustaste ziehen, und die
# eigene Folge ueberlebt Schliessen UND Update (settings.json liegt im
# Nutzerordner, die .exe wird beim Update nur ersetzt).
from PySide6.QtCore import QEvent as _QEv7g, QPoint as _QP7g
from PySide6.QtGui import QWheelEvent as _QWh7g
from PySide6.QtWidgets import (QVBoxLayout as _QVB7g, QWidget as _QW7g,
                               QScrollArea as _QSA7g)
from eve_trader.ui.mw_basis import KartenSortierer as _KS7g

_halter7g = _QW7g()
_lay7g = _QVB7g(_halter7g)
_karten7g = []
for _i7g in range(3):
    _k7g = _QW7g()
    _lay7g.addWidget(_k7g)
    _karten7g.append(_k7g)
_scr7g = _QSA7g()
_pids7g = {id(_w): f"p{_n}" for _n, _w in enumerate(_karten7g)}
_gemerkt7g = []
_srt7g = _KS7g(_lay7g, _scr7g, lambda _w: _pids7g.get(id(_w)),
               lambda _o: _gemerkt7g.append(list(_o)), parent=_halter7g)
for _k7g in _karten7g:
    _srt7g.ueberwache(_k7g)       # setzt u.a. den Objektnamen fuer den Selektor
eq("b7g die Folge kommt aus dem Layout", _srt7g.reihenfolge(),
   ["p0", "p1", "p2"])
# IM RUHEZUSTAND AENDERT DER SORTIERER NICHTS. Das ist der wichtigste Test:
# die Karten tragen Knoepfe (oeffnen, loeschen), und ein dauerhaft lauernder
# Filter waere ein Risiko fuer jeden Klick darauf.
_ev7g = _QEv7g(_QEv7g.MouseButtonPress)
check("b7g ausgeschaltet schluckt er nichts",
      _srt7g.aktiv is False and _srt7g.eventFilter(_karten7g[0], _ev7g) is False)
# MAUSRAD BLEIBT MAUSRAD - ausdrueckliche Bedingung des Nutzers
# ("scrollen muss auch gehen"), auch waehrend des Anordnens.
_srt7g.aktiv = True
_wh7g = _QWh7g(_QP7g(5, 5), _QP7g(5, 5), _QP7g(0, -120), _QP7g(0, -120),
               Qt.NoButton, Qt.NoModifier, Qt.NoScrollPhase, False)
check("b7g das Mausrad wird NICHT gefiltert",
      _srt7g.eventFilter(_karten7g[0], _wh7g) is False)
# DIE KNOEPFE AUF DEN KARTEN BLEIBEN BEDIENBAR (Nutzer, 15.09.2026: "was
# bringt der Arrange-Modus, wenn er aktiviert ist und ich nichts druecken
# kann?"). Frueher schluckte der Sortierer JEDEN Druck - der Modus war damit
# nicht dauerhaft nutzbar, obwohl er genau dafuer gedacht ist.
from PySide6.QtWidgets import QPushButton as _QPB7g, QLabel as _QL7g
from PySide6.QtGui import QMouseEvent as _QME7g
from PySide6.QtCore import QPointF as _QPF7g
_knopf7g = _QPB7g("Open", _karten7g[0])
_label7g = _QL7g("Profit", _karten7g[0])


def _druck7g(ziel):
    """Ein echter Linksklick-Druck auf dieses Widget."""
    return _QME7g(_QEv7g.MouseButtonPress, _QPF7g(3, 3), _QPF7g(3, 3),
                  Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)


_srt7g._widget = None
check("b7g ein Druck auf 'Open' geht an den Knopf",
      _srt7g.eventFilter(_knopf7g, _druck7g(_knopf7g)) is False)
check("b7g und der Sortierer merkt sich dabei KEINE Karte",
      _srt7g._widget is None)
check("b7g ein Druck auf die Karte selbst greift weiterhin",
      _srt7g.eventFilter(_karten7g[0], _druck7g(_karten7g[0])) is True
      and _srt7g._widget is _karten7g[0])
_srt7g._widget = None
_srt7g._start = None
check("b7g ein Druck auf ein Label greift ebenfalls (dort wird gezogen)",
      _srt7g.eventFilter(_label7g, _druck7g(_label7g)) is True)
_srt7g._widget = None
_srt7g._start = None
_knopf7g.setParent(None)
_label7g.setParent(None)
# Umsortieren im Layout und merken - ohne echte Maus, die Bewegung selbst
# prueft b7g nicht (dafuer braeuchte es einen sichtbaren Bildschirm).
_lay7g.removeWidget(_karten7g[0])
_lay7g.insertWidget(2, _karten7g[0])
# DIE DREI ZUSTAENDE DER KARTE (Nutzer, 15.09.2026: "wenn ich mit der Maus
# ueber einen Bauplan fahre, moechte ich dass er leicht hervorgehoben wird,
# und wenn ich ihn dann drag and droppe"). Alle drei tragen 1 px Rahmen -
# sonst springt die Karte beim Wechsel, dieselbe Falle wie beim Blinken.
for _z7g, _name7g in (("ruhe", "ruhig"), ("hover", "unter der Maus"),
                      ("zieht", "in der Hand")):
    _srt7g._zeige(_karten7g[0], _z7g)
    check(f"b7g Zustand '{_name7g}' traegt 1 px Rahmen",
          "border:1px solid" in _karten7g[0].styleSheet())
    # NUR DIE KARTE, NICHT IHRE KINDER (Nutzer: "wirklich nur den
    # Gesamtrahmen vom Bauplan, nicht 'Profit' und so auch nochmal
    # umrahmt"). Ohne Selektor vererbt Qt die Regel an jedes Label darin.
    check(f"b7g Zustand '{_name7g}' trifft nur die Karte selbst",
          bool(_KS7g.OBJEKTNAME)
          and _karten7g[0].objectName() == _KS7g.OBJEKTNAME
          and _karten7g[0].styleSheet().startswith(
              "#" + _KS7g.OBJEKTNAME + "{"))
_srt7g._zeige(_karten7g[0], "hover")
_hover7g = _karten7g[0].styleSheet()
_srt7g._zeige(_karten7g[0], "zieht")
_zieht7g = _karten7g[0].styleSheet()
check("b7g nur beim Ziehen kommt eine Flaeche dazu",
      "background:" in _zieht7g and "background:" not in _hover7g)
_srt7g.alles_zuruecksetzen()
check("b7g Ausschalten raeumt die Hervorhebung weg",
      _karten7g[0].styleSheet() == "")
eq("b7g nach dem Verschieben stimmt die Folge", _srt7g.reihenfolge(),
   ["p1", "p2", "p0"])

# --- der Umschalter am Hauptfenster ---------------------------------------
check("b7g der Knopf ist da und rastet ein",
      hasattr(win, "bp_order_btn") and win.bp_order_btn.isCheckable())
_vorher7g = win.settings.get("bau_plan_manuell")
win._plan_handsortierung_umschalten(True)
check("b7g einschalten merkt sich das",
      win.settings.get("bau_plan_manuell") is True)
win._plan_reihenfolge_merken(["7", "3", "9"])
eq("b7g die Folge landet in den Einstellungen",
   win.settings.get("bau_plan_reihenfolge"), ["7", "3", "9"])
# UND DIE AUTOMATIK BLEIBT DRAUSSEN: sonst wirft der naechste ESI-Lauf die
# Handarbeit um - genau das, was der Umschalter verhindern soll.
_lay_alt7g = getattr(win, "_plan_sortier_layout", None)
_wrap_alt7g = getattr(win, "_plan_karte_wrap", None)
win._plan_sortier_layout = _lay7g
win._plan_karte_wrap = {"p0": _karten7g[0]}
win._sortiere_plan_karten({"p0": {"qty": 10, "built": 10, "pct": 100.0}})
eq("b7g die Automatik ruehrt die Handfolge nicht an",
   _srt7g.reihenfolge(), ["p1", "p2", "p0"])
_src_ord7g = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
_i_ord7g = _src_ord7g.find("def _plan_handsortierung_umschalten")
_ab_ord7g = _src_ord7g[_i_ord7g:_i_ord7g + 1800] if _i_ord7g >= 0 else ""
check("b7g der Umschalter ist auffindbar", _i_ord7g >= 0)
# EINSCHALTEN HEISST "MEINE FOLGE GILT" (Nutzer, 15.09.2026).
check("b7g einschalten setzt die eigene Folge in Kraft",
      win.settings.get("bau_plan_eigene_folge") is True
      and win._plan_eigene_folge_gilt() is True)
# AUSSCHALTEN BEENDET NUR DAS ZIEHEN (Nutzer, 15.09.2026: "die Reihenfolge
# bleibt, aber dann fuehren wir einen Knopf ein 'Nach Fortschritt
# sortieren'"). Vorher warf das Ausschalten die Handarbeit sofort um - sein
# Einwand: "da liegt kein Sinn dahinter". Auch die Warnung davor ist raus:
# sie kuendigte etwas an, das nicht mehr passiert.
win.bp_order_btn.setChecked(True)
win._plan_handsortierung_umschalten(False)
check("b7g ausschalten merkt sich das ebenfalls",
      win.settings.get("bau_plan_manuell") is False)
check("b7g aber die eigene Folge gilt weiter",
      win._plan_eigene_folge_gilt() is True)
win._sortiere_plan_karten({"p0": {"qty": 10, "built": 10, "pct": 100.0}})
eq("b7g und die Automatik ruehrt sie auch AUSGESCHALTET nicht an",
   _srt7g.reihenfolge(), ["p1", "p2", "p0"])
check("b7g es wird nicht mehr gefragt beim Ausschalten",
      "_QMB.question(" not in _ab_ord7g)
# ZURUECK ZUR AUTOMATIK NUR AUF KLICK.
check("b7g der Knopf „Nach Fortschritt sortieren“ ist da",
      hasattr(win, "bp_progress_btn"))
win._plan_nach_fortschritt_sortieren()
check("b7g er beendet die eigene Folge",
      win.settings.get("bau_plan_eigene_folge") is False
      and win._plan_eigene_folge_gilt() is False)
eq("b7g und sortiert sofort nach Fortschritt", _srt7g.reihenfolge(),
   ["p0", "p1", "p2"])
check("b7g dafuer wird der letzte Fortschritt gemerkt",
      "self._plan_letzter_fortschritt = res" in _src_ord7g)
# WER DANACH WIEDER SCHIEBT, IST WIEDER IN SEINER FOLGE - sonst muesste er
# den Anordnen-Modus aus- und wieder einschalten, nur damit sein Zug gilt.
win._plan_reihenfolge_merken(["7", "3", "9"])
check("b7g ein neuer Zug setzt die eigene Folge wieder in Kraft",
      win._plan_eigene_folge_gilt() is True)
# OHNE FORTSCHRITT NICHT STILL (Regel 6): ohne ESI-Lauf gibt es nichts zu
# sortieren - das muss der Knopf sagen, sonst sieht er kaputt aus.
_i_prog7g = _src_ord7g.find("def _plan_nach_fortschritt_sortieren")
_ab_prog7g = _src_ord7g[_i_prog7g:_i_prog7g + 1800]
check("b7g ohne Fortschritt sagt der Knopf Bescheid",
      _i_prog7g >= 0 and "self._flash_tip(" in _ab_prog7g)
# DER KNOPF ZEIGT DEN ZUSTAND (Nutzer: "blaues transparent, wie der
# Refresh-all-Button") - derselbe Objektname, also dieselbe Regel aus dem
# Stylesheet statt eines zweiten handgemalten Knopfes.
check("b7g ausgeschaltet ist der Knopf normal",
      win.bp_order_btn.objectName() != "Primary")
win._plan_order_btn_stil(True)
check("b7g eingeschaltet leuchtet er wie \u201eRefresh all\u201c",
      win.bp_order_btn.objectName() == "Primary"
      and win.global_refresh_btn.objectName() == "Primary")
win._plan_order_btn_stil(False)
eq("b7g die Handfolge bleibt trotzdem gespeichert",
   win.settings.get("bau_plan_reihenfolge"), ["7", "3", "9"])
win._plan_sortier_layout = _lay_alt7g
win._plan_karte_wrap = _wrap_alt7g
win.settings["bau_plan_manuell"] = _vorher7g
# DIE EINSTELLUNG MUSS ES GEBEN, sonst faellt sie beim ersten Speichern
# heraus und die Reihenfolge ist nach dem naechsten Start weg.
from eve_trader import config as _cfg7g
check("b7g beide Schluessel stehen in den Standardwerten",
      "bau_plan_manuell" in _cfg7g.DEFAULT_SETTINGS
      and "bau_plan_reihenfolge" in _cfg7g.DEFAULT_SETTINGS)

# ---------------------------------------------------------------- (b7h)
# CONTRACT-STAND: ALT -> DER KNOPF BLINKT. Und vor dem Scan wird gefragt.
# NUTZER, 15.09.2026: "ich moechte, dass Load contract prices wenn nicht
# aktuell ist der Button auch blinkt, sonst vergleicht man hier alte Preise
# von gestern" - dazu "ist das normal dass das fast 5 Minuten dauert? wenn
# das normal ist, sollte ein Popup kommen mit einer Warnung".
check("b7h der Capital-Contract-Knopf ist da",
      hasattr(win, "b_cap_contract_btn"))
if hasattr(win, "b_cap_contract_btn"):
    import eve_trader.store as _st7h
    _echt7h = _st7h.contract_prices_age_seconds

    def _blinkt7h():
        """Blinkt der Knopf gerade? NONE-FEST: faellt die Alterspruefung aus,
        gibt es gar keinen Timer - ein `.isActive()` darauf wuerde die ganze
        Suite mit einem AttributeError abreissen, statt EINE Pruefung rot zu
        machen (genau die Falle, die `_pos_von` in der aa-Suite abfaengt).
        Bei der Rotprobe ist das der Unterschied zwischen ROT und BLIND."""
        _t = getattr(win.b_cap_contract_btn, "_ct_blink_timer", None)
        return _t is not None and _t.isActive()
    try:
        # NIE GELADEN -> blinken. Das ist der haeufigste Fall beim ersten
        # Start, und genau dort ist der Hinweis am noetigsten.
        _st7h.contract_prices_age_seconds = lambda _r: None
        win._capital_contract_alter_pruefen()
        check("b7h ohne Stand blinkt er", _blinkt7h())
        # FRISCH -> still.
        _st7h.contract_prices_age_seconds = lambda _r: 60.0
        win._capital_contract_alter_pruefen()
        check("b7h mit frischem Stand blinkt er nicht", not _blinkt7h())
        # AELTER ALS EINEN TAG -> wieder blinken (die Grenze selbst).
        _st7h.contract_prices_age_seconds = \
            lambda _r: win._CONTRACT_ALT_SEKUNDEN + 1
        win._capital_contract_alter_pruefen()
        check("b7h ein Stand von gestern blinkt", _blinkt7h())
        # GENAU AUF DER GRENZE ist er noch gut - sonst blinkt er bei jedem,
        # der taeglich einmal scannt, staendig kurz vor dem naechsten Lauf.
        _st7h.contract_prices_age_seconds = \
            lambda _r: float(win._CONTRACT_ALT_SEKUNDEN)
        win._capital_contract_alter_pruefen()
        check("b7h auf der Grenze noch nicht", not _blinkt7h())
    finally:
        _st7h.contract_prices_age_seconds = _echt7h
    check("b7h die Grenze ist ein Tag, nicht 15 Minuten",
          win._CONTRACT_ALT_SEKUNDEN == 24 * 3600)
    # KEIN GROESSENSPRUNG beim Blinken - 2 px in BEIDEN Zustaenden.
    check("b7h der Ruhezustand traegt schon 2 px Rahmen",
          "border:2px solid" in getattr(win.b_cap_contract_btn, "_ct_css", ""))
# DIE WARNUNG STEHT VOR DEM SCAN, nicht danach - und sie nennt die Dauer.
_src7h = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
_i7h = _src7h.find("def _load_capital_contract_prices")
# GROSSZUEGIGES FENSTER: die ganze Funktion samt done()/fail() - der
# Wiederaufruf des Alters-Checks steht erst dort unten.
_ab7h = _src7h[_i7h:_i7h + 6000]
check("b7h vor dem Scan wird gefragt", "_QMB.question(" in _ab7h)
check("b7h die Frage nennt die Dauer", "SEVERAL " in _ab7h and "MINUTES" in _ab7h)
check("b7h Abbrechen bricht wirklich ab",
      "!= _QMB.Ok:\n            return" in _ab7h)
check("b7h gefragt wird VOR dem Start des Laufs",
      _ab7h.find("_QMB.question(") < _ab7h.find("self._run("))
# UND DAS BLINKEN GEHT NACH EINEM ERFOLGREICHEN SCAN AUS.
check("b7h nach dem Scan wird der Stand neu bewertet",
      "self._capital_contract_alter_pruefen()" in _ab7h)

# ---------------------------------------------------------------- (b7i)
# CAPITAL-MODUS IST BEIM START IMMER AUS.
# NUTZER, 15.09.2026: "die Gefahr ist gross, dass man vergisst da
# herauszugehen, bevor man das Tool schliesst, und dann ist man verwirrt,
# warum man keine normalen Blueprints suchen kann." Der Modus ist etwas fuer
# Fortgeschrittene und darf nie der Zustand sein, in dem man das Programm
# unbemerkt vorfindet.
check("b7i der Capital-Modus-Knopf ist da", hasattr(win, "b_cap_mode"))
if hasattr(win, "b_cap_mode"):
    check("b7i beim Start ist er AUS", not win.b_cap_mode.isChecked())
    check("b7i und die normale Trefferliste ist sichtbar",
          not win.b_table.isHidden())
# DER ZUSTAND DARF AUCH NICHT GESPEICHERT WERDEN - sonst ist er beim
# naechsten Start wieder da, ohne dass jemand ihn eingeschaltet hat.
from eve_trader import config as _cfg7i
check("b7i der Modus steht in keiner Einstellung",
      not any("cap_mode" in _k for _k in _cfg7i.DEFAULT_SETTINGS))
_src7i = open("eve_trader/ui/mw_bauplan_tabs.py", encoding="utf-8").read()
check("b7i und er wird beim Aufbau ausdruecklich ausgeschaltet",
      "self.b_cap_mode.setChecked(False)" in _src7i)

# ---------------------------------------------------------------- (b7j)
# DER HAKEN, DEN NIEMAND GESETZT HAT.
# NUTZER, 15.09.2026, mit zwei Zoom-Bildern: "Titanium Chromide Reaction
# Formula - dieser gruene Haken ist nicht von mir, den kann ich nicht
# setzen ... ich kann ihn auch nicht wegmachen."
#
# URSACHE, nachgemessen (nicht geraten): QTreeWidgetItem traegt
# Qt.ItemIsUserCheckable BEREITS in seinen Standard-Flags, und
# checkState(0) antwortet auch ohne Kaestchen brav "Unchecked". Die
# Kinder-Kaskade in _on_sched_check ("hake ich den Charakter ab, sollen
# seine Positionen mit") fragte genau diese beiden Dinge ab - und legte
# den Material-Unterzeilen damit ein Kaestchen NEU AN, statt ein
# vorhandenes umzuschalten. Beim Loesen blieb es als LEERES Kaestchen
# stehen, weil CheckStateRole dann 0 ist und nicht mehr None.
from PySide6.QtWidgets import QTreeWidget as _TW7j, QTreeWidgetItem as _TWI7j
_t7j = _TW7j(); _t7j.setColumnCount(5)
_eltern7j = _TWI7j(["Peanut Motor", "", "", "", ""])
_t7j.addTopLevelItem(_eltern7j)
_mat7j = _TWI7j(["Vanadium", "1'000", "", "", ""])
_eltern7j.addChild(_mat7j)
check("b7j eine frische Baumzeile ist von Haus aus abhakbar (deshalb "
      "reichen die Flags als Frage nicht)",
      bool(_mat7j.flags() & Qt.ItemIsUserCheckable))
check("b7j und sie meldet Unchecked, obwohl sie gar kein Kaestchen hat",
      _mat7j.checkState(0) == Qt.Unchecked
      and _mat7j.data(0, Qt.CheckStateRole) is None)
# DIE ALTE BEDINGUNG haette hier zugeschlagen, die neue nicht.
check("b7j die alte Kaskaden-Bedingung haette ein Kaestchen erfunden",
      bool(_mat7j.flags() & Qt.ItemIsUserCheckable)
      and _mat7j.checkState(0) != Qt.Checked)
check("b7j die neue Bedingung laesst die Stuecklisten-Zeile in Ruhe",
      not (_mat7j.data(0, Qt.CheckStateRole) is not None
           and _mat7j.flags() & Qt.ItemIsUserCheckable
           and _mat7j.checkState(0) != Qt.Checked))
# BEIDE RIEGEL MUESSEN IM CODE STEHEN - einer allein waere wieder eine
# einzige Stelle, an der es kippen kann.
_src7j = open("eve_trader/ui/mw_bauplan_fenster.py", encoding="utf-8").read()
check("b7j die Kaskade fragt nach dem vorhandenen Kaestchen",
      "_ch.data(0, Qt.CheckStateRole) is not None" in _src7j)
check("b7j und zwar VOR dem Umschalten",
      # BEIDE ANKER AUSDRUECKLICH PRUEFEN: find() liefert -1, wenn ein Anker
      # fehlt, und -1 < irgendwas waere still gruen (die Blindstelle aus
      # aa353). Ein fehlender Anker muss ROT werden, nicht unsichtbar.
      _src7j.find("_ch.data(0, Qt.CheckStateRole) is not None") >= 0
      and _src7j.find("_ch.setCheckState(0, _want)") >= 0
      and (_src7j.find("_ch.data(0, Qt.CheckStateRole) is not None")
           < _src7j.find("_ch.setCheckState(0, _want)")))
check("b7j die Material-Unterzeile ist gar nicht erst abhakbar",
      "mit.setFlags(mit.flags() & ~Qt.ItemIsUserCheckable)" in _src7i)
check("b7j und das steht vor dem Einhaengen",
      _src7i.find("mit.setFlags(mit.flags() & ~Qt.ItemIsUserCheckable)") >= 0
      and _src7i.find("iit.addChild(mit)") >= 0
      and (_src7i.find("mit.setFlags(mit.flags() & ~Qt.ItemIsUserCheckable)")
           < _src7i.find("iit.addChild(mit)")))
# DIE ECHTEN ZEILEN BEHALTEN IHR KAESTCHEN: der Riegel darf den Runplaner
# nicht stumm schalten. Beides steht unveraendert im Aufbau.
check("b7j die Positionszeile bleibt abhakbar",
      "iit.setFlags(iit.flags() | Qt.ItemIsUserCheckable)" in _src7i)
check("b7j die Charakterzeile bleibt abhakbar",
      "citem.setFlags(citem.flags() | Qt.ItemIsUserCheckable)" in _src7i)

# ---------------------------------------------------------------- (b7k)
# UNGESPEICHERTE EINSTELLUNGEN (Nutzer, 15.09.2026): "wenn man in
# Einstellungen etwas einstellt und nicht speichert, bekommt man keine
# Meldung, wenn man irgendwo anders im Tool klickt ... diese Warnung muss
# kommen, sobald wir versuchen ungespeichert den Einstellungs-Tab zu
# verlassen, EGAL WOHIN."
#
# GEFAHREN, NICHT NUR GELESEN: alle drei Wege werden hier wirklich
# durchlaufen. Die modale Rueckfrage steckt in `_einstellungen_frage` und
# wird dafuer stillgelegt - ein echtes Fenster wuerde die Suite haengen
# lassen (b59 bewacht dieselbe Falle).
check("b7k die Einstellungsseite ist hinterlegt",
      getattr(win, "_settings_w", None) is not None)
check("b7k und der Riegel haengt an der Navigation",
      win.tabs.vor_wechsel is not None)
_si7k = win.tabs.indexOf(win._settings_w)
check("b7k die Seite steckt wirklich im Stapel", _si7k >= 0)
# EIN ANDERES ZIEL SUCHEN - egal welches, es geht um "egal wohin".
_ziel7k = None
for _i7k in range(win.tabs.count()):
    if _i7k != _si7k:
        _ziel7k = win.tabs.widget(_i7k)
        break
check("b7k es gibt ein anderes Ziel", _ziel7k is not None)
_gefragt7k = []
_alt_frage7k = type(win)._einstellungen_frage
_antwort7k = {"wert": "zurueck"}


def _frage7k(_self):
    _gefragt7k.append(1)
    return _antwort7k["wert"]


_merk_margin7k = win.settings.get("target_margin")
_merk_stand7k = getattr(win, "_einst_stand", None)
try:
    type(win)._einstellungen_frage = _frage7k
    # --- 1. NICHTS GEAENDERT: keine Rueckfrage, Wechsel geht durch.
    win.tabs.setCurrentWidget(win._settings_w)
    win._einstellungen_stand_merken()
    check("b7k ohne Aenderung ist nichts offen",
          win._einstellungen_offen() is False)
    win.tabs.setCurrentWidget(_ziel7k)
    check("b7k und der Wechsel geht ohne Rueckfrage durch",
          win.tabs.currentWidget() is _ziel7k and not _gefragt7k)
    # --- 2. GEAENDERT + "Zurueck": der Wechsel wird verhindert.
    win.tabs.setCurrentWidget(win._settings_w)
    win.s_margin.setValue(float(win.s_margin.value()) + 3.0)
    check("b7k eine Aenderung wird erkannt",
          win._einstellungen_offen() is True)
    _antwort7k["wert"] = "zurueck"
    win.tabs.setCurrentWidget(_ziel7k)
    check("b7k dann wird gefragt", len(_gefragt7k) == 1)
    check("b7k und „Zurueck“ laesst einen auf der Seite",
          win.tabs.currentWidget() is win._settings_w)
    check("b7k die Aenderung steht noch im Feld",
          win._einstellungen_offen() is True)
    # DERSELBE RIEGEL AUCH UEBER DEN INDEX-WEG (Seitenleiste, Code-Spruenge).
    win.tabs.setCurrentIndex(win.tabs.indexOf(_ziel7k))
    check("b7k auch der Wechsel ueber den Index wird abgefangen",
          win.tabs.currentWidget() is win._settings_w)
    # --- 3. GEAENDERT + "Verwerfen": Felder zurueck, Wechsel geht durch.
    _antwort7k["wert"] = "verwerfen"
    win.tabs.setCurrentWidget(_ziel7k)
    check("b7k „Verwerfen“ laesst den Wechsel zu",
          win.tabs.currentWidget() is _ziel7k)
    check("b7k und raeumt die Felder auf",
          win._einstellungen_offen() is False)
    eq("b7k die Einstellung selbst blieb unangetastet",
       win.settings.get("target_margin"), _merk_margin7k)
    # --- 4. GEAENDERT + "Speichern": der Wert landet in den Einstellungen.
    win.tabs.setCurrentWidget(win._settings_w)
    _neu7k = float(win.s_margin.value()) + 4.0
    win.s_margin.setValue(_neu7k)
    _antwort7k["wert"] = "speichern"
    win.tabs.setCurrentWidget(_ziel7k)
    check("b7k „Speichern“ laesst den Wechsel zu",
          win.tabs.currentWidget() is _ziel7k)
    eq("b7k und schreibt den neuen Wert",
       float(win.settings.get("target_margin")), _neu7k)
    check("b7k danach ist nichts mehr offen",
          win._einstellungen_offen() is False)
    # --- 5. VON EINER ANDEREN SEITE AUS wird NIE gefragt.
    _vorher7k = len(_gefragt7k)
    win.tabs.setCurrentIndex(_si7k)
    check("b7k der Weg IN die Einstellungen fragt nicht",
          len(_gefragt7k) == _vorher7k
          and win.tabs.currentWidget() is win._settings_w)
finally:
    type(win)._einstellungen_frage = _alt_frage7k
    win.settings["target_margin"] = _merk_margin7k
    win._einstellungen_felder_zuruecksetzen()
    win._einst_stand = _merk_stand7k
    win.tabs.vor_wechsel = None
    win.tabs.setCurrentIndex(0)
    win.tabs.vor_wechsel = win._einstellungen_wechsel_pruefen
# EIN AUSFALL DARF NIE SPERREN: sitzt der Nutzer wegen eines Anzeigefehlers
# fest, ist das schlimmer als eine verlorene Einstellung.
_altv7k = win.tabs.vor_wechsel
try:
    def _kaputt7k(_a, _b):
        raise RuntimeError("Absicht")
    win.tabs.vor_wechsel = _kaputt7k
    win.tabs.setCurrentIndex(win.tabs.indexOf(_ziel7k))
    check("b7k ein Fehler im Riegel erlaubt den Wechsel",
          win.tabs.currentWidget() is _ziel7k)
finally:
    win.tabs.vor_wechsel = _altv7k
    win.tabs.setCurrentIndex(0)

# ---------------------------------------------------------------- (b7l)
# RECHTSKLICK AUF DIE OBERE LEISTE BLENDET SIE NICHT MEHR AUS.
# NUTZER, 15.09.2026, fuenf Screenshots: "wenn ich Rechtsklick auf einen
# dieser oberen Leisten-Knoepfe mache und dann da drauf klicke, schliesst
# sich diese obere Leiste - diese Rechtsklick-Option muss weg."
# Das Kaestchen im Bild ist Qts eingebautes Fenster-Menue (QMainWindow
# bietet jede Werkzeugleiste zum Ausblenden an), kein eigener Code.
check("b7l die obere Leiste ist hinterlegt",
      getattr(win, "_toolbar", None) is not None)
if getattr(win, "_toolbar", None) is not None:
    check("b7l sie reicht den Rechtsklick nicht mehr weiter",
          win._toolbar.contextMenuPolicy() == Qt.PreventContextMenu)
    check("b7l und sie ist sichtbar", not win._toolbar.isHidden())
    # DER ZWEITE WEG: Qt baut das Menue in createPopupMenu - auch beim
    # Rechtsklick NEBEN die Leiste. Ohne diesen Riegel waere der erste nur
    # die halbe Miete.
    check("b7l das Fenster bietet gar kein solches Menue mehr an",
          win.createPopupMenu() is None)
    # EIN ECHTER RECHTSKLICK DARF NICHTS OEFFNEN. Gemessen an den offenen
    # Fenstern: waere das Menue noch da, stuende danach eins mehr offen.
    from PySide6.QtGui import QContextMenuEvent as _QCME7l
    from PySide6.QtCore import QPoint as _QP7l
    from PySide6.QtWidgets import QMenu as _QMenu7l
    _vorher7l = len([_w for _w in _app.topLevelWidgets()
                     if isinstance(_w, _QMenu7l) and _w.isVisible()])
    _ev7l = _QCME7l(_QCME7l.Mouse, _QP7l(5, 5),
                    win._toolbar.mapToGlobal(_QP7l(5, 5)))
    _app.sendEvent(win._toolbar, _ev7l)
    _app.processEvents()
    _nachher7l = len([_w for _w in _app.topLevelWidgets()
                      if isinstance(_w, _QMenu7l) and _w.isVisible()])
    check("b7l ein Rechtsklick auf die Leiste oeffnet nichts",
          _nachher7l == _vorher7l)
    # DAS EIGENE KONTEXTMENUE EINES KNOPFES DARIN BLEIBT (Sitzung 21):
    # der Riegel gilt der Leiste, nicht ihren Kindern.
    check("b7l das eigene Menue des EVE-Daten-Knopfes bleibt",
          win.g_sde_btn.contextMenuPolicy() == Qt.CustomContextMenu)

# ---------------------------------------------------------------- (b7o)
# DIE BEHAELTER-LISTE FOLGT DER CHARAKTER-WAHL.
# NUTZER, 15.09.2026: "jetzt habe ich da ploetzlich Container von allen
# Charakteren anstatt nur dem gewaehlten."
# EHRLICH ZUR URSACHE: die Liste hat den Wahlschalter NIE beachtet. Nur
# fiel es nicht auf, solange kaum Behaelter erkannt wurden (aa358). Mehr
# Treffer haben einen alten Fehler sichtbar gemacht.
_alt7o = getattr(win, "_assets_struct", {})
_alt_idx7o = win.pf_char.currentIndex()
try:
    win._assets_struct = {
        111: {"hangar": {}, "containers": [{"item_id": 1, "type_id": 9,
                                            "name": "A", "contents": {34: 5}}]},
        222: {"hangar": {}, "containers": [{"item_id": 2, "type_id": 9,
                                            "name": "B", "contents": {35: 7}}]},
    }
    win.pf_char.blockSignals(True)
    win.pf_char.clear()
    win.pf_char.addItem(_t4("All"), "all")
    win.pf_char.addItem("Eins", 111)
    win.pf_char.addItem("Zwei", 222)
    win.pf_char.blockSignals(False)

    def _namen7o():
        return sorted(c["name"] for c in win._sichtbare_container())

    win.pf_char.setCurrentIndex(0)          # "Alle"
    eq("b7o bei 'Alle' stehen die Behaelter aller Charaktere da",
       _namen7o(), ["A", "B"])
    win.pf_char.setCurrentIndex(1)          # Charakter 111
    eq("b7o bei einem Charakter nur SEINE Behaelter", _namen7o(), ["A"])
    win.pf_char.setCurrentIndex(2)          # Charakter 222
    eq("b7o und beim naechsten dessen Behaelter", _namen7o(), ["B"])
    # DIESELBE REGEL WIE DIE ITEM-LISTE - sonst behauptet eine Seite zweierlei.
    _src7o = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    check("b7o die Anzeige nimmt die gefilterte Liste",
          "containers = self._sichtbare_container()" in _src7o)
    check("b7o und 'alle ausblenden' dieselbe Quelle",
          "all_ids = [c[\"item_id\"] for c in self._sichtbare_container()]"
          in _src7o)
    # UND SIE GEHT BEIM UMSCHALTEN MIT, nicht erst beim naechsten Abruf.
    check("b7o der Wahlschalter zeichnet die Liste neu",
          "self.pf_char.currentIndexChanged.connect("
          "self._container_neu_zeichnen)" in _src7o)
finally:
    win._assets_struct = _alt7o
    win.pf_char.blockSignals(True)
    win.pf_char.clear()
    win.pf_char.blockSignals(False)
    try:
        win._reload_character_combos()
    except Exception:
        pass

# ---------------------------------------------------------------- (b7n)
# WO BIN ICH? DIE RECHTE LEISTE ZEIGT ES JETZT AUCH.
# NUTZER, 15.09.2026: "im Trading-Bereich sieht man in der linken Sidebar,
# wo man sich befindet. Im Industrie-Bereich sieht man in der rechten
# Sidebar noch nicht, wo man sich befindet - kannst du das mit derselben
# Optik machen?"
from eve_trader.ui import theme as _th7
check("b7n die vier Seiten-Knoepfe der Bau-Leiste sind da",
      len(getattr(win, "_bau_page_btns", [])) == 4)
if len(getattr(win, "_bau_page_btns", [])) == 4:
    _akt7n = win._bau_rail_active_css
    _idl7n = win._bau_rail_idle_css
    # DIESELBE HANDSCHRIFT WIE LINKS: Cyan-Schrift, Cyan-Flaeche und der
    # 3 px breite Balken an der linken Kante. Der Balken ist das
    # Erkennungszeichen der linken Leiste (theme: NavItem:checked).
    check("b7n der aktive Knopf traegt den Cyan-Balken links",
          f"border-left:3px solid {_th7.CYAN}" in _akt7n)
    check("b7n und Cyan-Schrift auf ruhiger Cyan-Flaeche",
          f"color:{_th7.CYAN}" in _akt7n
          and f"background:{_th7.CYAN_FILL}" in _akt7n)
    # BEIDE ZUSTAENDE GLEICH BREIT - sonst springt der Text beim Wechseln
    # (dieselbe Falle wie beim blinkenden Rahmen).
    check("b7n der ruhige Knopf traegt denselben Balken, nur in Rahmenfarbe",
          f"border-left:3px solid {_th7.BORDER}" in _idl7n)
    # JETZT WIRKLICH DURCHKLICKEN: jede Seite genau einmal hervorgehoben.
    for _i7n in range(4):
        win._bau_nav(_i7n)
        _app.processEvents()
        _hell = [_j for _j, _b in enumerate(win._bau_page_btns)
                 if _b.styleSheet() == _akt7n]
        eq(f"b7n Seite {_i7n}: genau dieser eine Knopf leuchtet",
           _hell, [_i7n])
        eq(f"b7n Seite {_i7n}: der Stapel steht auch dort",
           win.b_stack.currentIndex(), _i7n)
    # UND BEIM AUFBAU SCHON, nicht erst nach dem ersten Klick.
    _src7n = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
    check("b7n die Hervorhebung steht schon beim Aufbau",
          "self._bau_page_btns[self.b_stack.currentIndex()].setStyleSheet("
          in _src7n)
    win._bau_nav(0)
    _app.processEvents()

# ---------------------------------------------------------------- (b7p)
# DIE TOUR GEHT MIT, WENN WAEHREND EINES SCHRITTS EIN FENSTER AUFGEHT.
# NUTZER, 16.09.2026: "wenn der Bauplan geoeffnet ist, ist das Tutorial-
# Fenster hinter dem Bauplan, weil man zuerst auf Next druecken muss."
# Schritt 7/15 wartet genau darauf, dass der Nutzer den Bauplan oeffnet -
# der geht dann VOR der Tour auf, und bis zum naechsten "Weiter" blieb sie
# dahinter. Umgehaengt wurde bisher nur beim Schrittwechsel.
from eve_trader.ui.tutorial import TutorialFenster as _TF7p
_tp7p = _TF7p(win, "trading")
try:
    # 1. ZIEL UNVERAENDERT -> NICHTS TUN. Ein Dauer-raise_() zoege das
    # Besitzerfenster mit hoch und drueckte den Bauplan nach hinten
    # (Sitzung 17, derselbe Schritt, derselbe Nutzer).
    #
    # DER MERKER MUSS AUS DEM ECHTEN WEG KOMMEN, nicht von Hand gesetzt
    # werden: im ersten Anlauf stand hier `_letztes_ziel = _zielfenster()`,
    # und die Mutation, die das Merken im Programm abklemmt, blieb
    # deshalb BLIND - der Test hatte sich seine Voraussetzung selbst
    # gebaut. Also erst einmal richtig ordnen lassen.
    _tp7p._fenster_ordnen()
    _app.processEvents()
    _gerufen7p = []
    _tp7p._fenster_ordnen = lambda: _gerufen7p.append(1)
    _tp7p._nachfuehren()
    eq("b7p ohne Fensterwechsel wird NICHT umgehaengt", _gerufen7p, [])
    # 2. ZIEL HAT GEWECHSELT -> die Tour ordnet sich neu.
    _tp7p._letztes_ziel = None
    _tp7p._nachfuehren()
    eq("b7p bei einem Fensterwechsel ordnet sie sich neu", _gerufen7p, [1])
    # 3. DER SCHRITT, DER DEN BAUPLAN OEFFNET, ZIELT DANACH AUF DEN BAUPLAN.
    # NUTZER-SCREENSHOT 16.09.2026: die Tour lag hinter dem Bauplan. Grund:
    # der Schritt hebt "New build plan" hervor - einen Knopf im
    # HAUPTFENSTER. Der ist sichtbar, also gewann er, und die Tour blieb am
    # Haupttool. Erst wenn die Bedingung erfuellt ist, gehoert sie nach
    # vorn auf den Bauplan.
    from PySide6.QtWidgets import (QDialog as _QD7p, QPushButton as _QPB7p)
    _i_open7p = [_i for _i, _st in enumerate(_tp7p.schritte)
                 if _st[4] == "bauplan_offen"]
    check("b7p es gibt einen Schritt, der auf den offenen Bauplan wartet",
          bool(_i_open7p) or _tp7p.zweig != "industry")
    _tp7i = _TF7p(win, "industry")
    _dlg7p = _QD7p(win)
    _dlg7p.resize(900, 700)
    _alt_bd7p = getattr(win, "_bd_dialog", None)
    try:
        _j7p = [_i for _i, _st in enumerate(_tp7i.schritte)
                if _st[4] == "bauplan_offen"]
        if _j7p:
            _tp7i.i = _j7p[0]
            # Ein sichtbarer Knopf im HAUPTFENSTER als Hervorhebung - genau
            # die Lage aus dem Screenshot.
            _btn7p = _QPB7p("x", win)
            _btn7p.show()
            _tp7i._hervor = [_btn7p]
            _app.processEvents()
            win._bd_dialog = None
            check("b7p solange kein Bauplan offen ist, zielt der Schritt "
                  "aufs Hauptfenster", _tp7i._zielfenster() is win)
            win._bd_dialog = _dlg7p
            _dlg7p.show()
            _app.processEvents()
            check("b7p ist der Bauplan offen, zielt er auf den Bauplan",
                  _tp7i._zielfenster() is _dlg7p)
            _btn7p.setParent(None)
    finally:
        win._bd_dialog = _alt_bd7p
        _dlg7p.close()
        _dlg7p.setParent(None)
        _tp7i.abbrechen()
        _app.processEvents()
    # 4. UND DER MERKER WIRD BEIM ORDNEN GESETZT - ohne ihn liefe Punkt 1
    # nie zu, und es waere doch wieder ein Dauer-raise_().
    _src7p = open("eve_trader/ui/tutorial.py", encoding="utf-8").read()
    check("b7p das Ordnen merkt sich sein Ziel",
          "self._letztes_ziel = _ziel" in _src7p)
finally:
    _tp7p.abbrechen()
    # WIRKLICH WEG, nicht nur versteckt: `abbrechen` ruft deleteLater(), und
    # das passiert erst, wenn Qt die aufgeschobenen Loeschungen abarbeitet.
    # Ohne das blieb ein zweites Tour-Fenster im Programm stehen - b55 zaehlt
    # Bedienelemente OHNE Symbol und meldete prompt zweimal "Back". Ein
    # Testaufbau, der Spuren hinterlaesst, macht die naechste Pruefung kaputt.
    from PySide6.QtCore import QEvent as _QEv7p
    _app.processEvents()
    _app.sendPostedEvents(None, _QEv7p.DeferredDelete)
    _app.processEvents()

# ---------------------------------------------------------------- (b7m)
# DIE TOUR VERDECKT DIE RECHTE LEISTE NICHT MEHR.
# NUTZER, 15.09.2026, mit Screenshot: "Tutorial verdeckt Production Steps,
# das Tutorialfenster muesste weiter links sein, damit man die rechte
# Sidebar komplett sehen kann." Unter den Anker zu ruecken ist richtig,
# solange er in der breiten Mitte sitzt; in der schmalen Leiste rechts
# liegt darunter genau das, worueber der Schritt gerade spricht.
# NACHGEZOGEN 16.09.2026: die Links-Regel gilt NUR im Bauplan-Fenster.
# Im Hauptfenster schob sie die Tour unter das modale "New build
# plan"-Fenster (Schritt 7/15) - dort ist unter dem Anker Platz, in der
# schmalen Bauplan-Sidebar nicht.
from eve_trader.ui.tutorial import TutorialFenster as _TF7m
from PySide6.QtWidgets import (QWidget as _QW7m, QDialog as _QD7m)
from PySide6.QtCore import QPoint as _QP7m
_tp7m = _TF7m(win, "trading")
# EIN EIGENES FENSTER als Stellvertreter fuer den Bauplan-Dialog: die Regel
# fragt ausdruecklich "ist das Fenster des Ankers NICHT das Haupttool?".
_dlg7m = _QD7m(win)
_dlg7m.resize(1200, 800)
_dlg7m.show()
try:
    _tp7m.show()
    _app.processEvents()

    def _lauf7m(anteil, wo=None):
        """Anker an dieser waagrechten Stelle des Fensters -> wohin rueckt
        die Tour? Gibt (Fensterrechteck der Tour, Anker-Ecke) zurueck."""
        _wo = wo if wo is not None else win
        _rw = _wo.frameGeometry()
        _a = _QW7m(_wo)
        _a.resize(120, 40)
        _a.move(_wo.mapFromGlobal(
            _QP7m(_rw.left() + int(_rw.width() * anteil),
                  _rw.top() + 200)))
        _a.show()
        _app.processEvents()
        _tp7m._hervor = [_a]
        _tp7m._platzieren()
        _app.processEvents()
        return _tp7m.geometry(), _a.mapToGlobal(_QP7m(0, 0)), _a

    # 1. ANKER IN DER RECHTEN LEISTE -> die Tour steht LINKS daneben.
    # BEIDE BEDINGUNGEN IN EINER PRUEFUNG, und das ist kein Schoenheitsfehler:
    # "steht links vom Anker" allein war BLIND. Ohne den Sonderfall rutscht
    # die Tour naemlich schon durch die Bildschirm-Begrenzung nach links
    # (sie passt rechts nicht mehr hin) und stuende trotzdem UNTER der
    # Leiste - also genau der gemeldete Fehler, aber mit gruener Pruefung.
    # Aufgefallen ist das in der Rotprobe: die Mutation blieb hier gruen.
    # Entscheidend ist die HOEHE.
    _g7m, _ae7m, _a7m = _lauf7m(0.90, _dlg7m)
    check("b7m bei einem Anker in der rechten Leiste steht die Tour links "
          "DANEBEN, nicht darunter",
          _g7m.right() < _ae7m.x() and _g7m.top() <= _ae7m.y() + 4)
    _a7m.setParent(None)
    # 1b. DIESELBE STELLE IM HAUPTFENSTER -> DARUNTER (Nutzer, 16.09.2026).
    # Dort geht mittig das modale "New build plan"-Fenster auf; die Tour
    # nach links zu schieben hiesse, sie genau dorthin zu setzen.
    _g7mh, _ae7mh, _a7mh = _lauf7m(0.90, win)
    check("b7m im HAUPTFENSTER bleibt es an derselben Stelle beim Platz "
          "DARUNTER", _g7mh.top() >= _ae7mh.y() + 40)
    _a7mh.setParent(None)
    # 1c. ANKER IN EINEM MODALEN FENSTER -> die Tour darf es NICHT beruehren.
    # NUTZER-SCREENSHOT 16.09.2026: "jetzt haengt es wieder hinter dem New
    # build plan Fenster". Bei Schritt 7/15 wandert der Anker in das kleine
    # modale Such-Fenster. Ein modales Fenster liegt IMMER oben - also ist
    # jede Stelle innerhalb seiner Flaeche verdeckt, egal ob links vom Anker
    # oder darunter. Deshalb wird hier am FENSTER ausgerichtet, nicht am
    # Anker, und geprueft wird das, worauf es ankommt: KEINE UEBERDECKUNG.
    _dlgmod7m = _QD7m(win)
    _dlgmod7m.setModal(True)
    _dlgmod7m.resize(400, 300)
    _dlgmod7m.move(60, 60)
    _dlgmod7m.show()
    _app.processEvents()
    try:
        _g7mm, _ae7mm, _a7mm = _lauf7m(0.90, _dlgmod7m)
        _rm7m = _dlgmod7m.frameGeometry()
        check("b7m die Tour verdeckt ein MODALES Fenster nicht",
              not _g7mm.intersects(_rm7m))
        # ... und hier ist unter dem Dialog Platz, also steht sie auch dort.
        check("b7m und steht dann unter dem modalen Fenster",
              _g7mm.top() >= _rm7m.bottom())
        _a7mm.setParent(None)
    finally:
        _dlgmod7m.close()
        _dlgmod7m.setParent(None)
        _app.processEvents()
    # 2. GEGENPROBE, ANKER IN DER MITTE -> alles bleibt wie bisher: DARUNTER.
    # Ohne sie koennte die Regel auch immer nach links rutschen und der Test
    # waere trotzdem gruen.
    _g7m2, _ae7m2, _a7m2 = _lauf7m(0.25)
    check("b7m bei einem Anker in der Mitte bleibt es beim Platz DARUNTER",
          _g7m2.top() >= _ae7m2.y() + 40)
    check("b7m und dann NICHT links daneben", _g7m2.right() > _ae7m2.x())
    _a7m2.setParent(None)
finally:
    _tp7m.abbrechen()
    _dlg7m.close()
    _dlg7m.setParent(None)
    _app.processEvents()
    _app.sendPostedEvents(None, _QEv7p.DeferredDelete)
    _app.processEvents()

# ---------------------------------------------------------------- (b7s)
# DER KNOPF IM LEEREN FENSTER TUT, WAS FEHLT. Nutzer-Befund 17.09.2026:
# "klickt man in der Mitte auf Market scan unter 'No market data', kommt
# zwar ein Ladebildschirm, aber keine Auflistung" und "bei Blueprint genauso,
# keine Wirkung". Zwei Ursachen: (1) nach dem Scan fehlte "Load deals", der
# Hinweis bot aber weiter "Market scan" an; (2) der Blaupausen-Hinweis zeigte
# auf den SDE-Download statt auf "Meine Blaupausen laden".
import eve_trader.store as _st7s
_app.processEvents()
_alt_age7s = _st7s.snapshot_age_seconds


def _box7s(tbl):
    for _w in tbl.viewport().children():
        if getattr(_w, "_knopf", None) is not None:
            return _w
    return None


try:
    _bx = _box7s(win.deals_table)
    check("b7s die Daytrade-Tabelle hat einen Leer-Hinweis mit Knopf", _bx is not None)
    if _bx is not None:
        # 1. KEIN SCAN -> "Market scan".
        _st7s.snapshot_age_seconds = lambda source=None: None
        win.deals_table._leerhinweis_stellen()
        check("b7s ohne Scan bietet der Knopf den Markt-Scan an",
              _bx._knopf.text() in ("Market scan", "Markt-Scan", "Marktscan"))
        # 2. SCAN DA -> "Load deals", und der Klick laedt die Deals.
        _st7s.snapshot_age_seconds = lambda source=None: 120.0
        win.deals_table._leerhinweis_stellen()
        check("b7s nach dem Scan bietet der Knopf 'Load deals' an",
              _bx._knopf.text() in ("Load deals", "Deals laden"))
        _gerufen7s = []
        _alt_click7s = win.deals_btn.click
        win.deals_btn.click = lambda: _gerufen7s.append("deals")
        try:
            _bx._aktion()
        finally:
            win.deals_btn.click = _alt_click7s
        eq("b7s ... und sein Klick drueckt wirklich 'Load deals'", _gerufen7s, ["deals"])
    # 3. BLAUPAUSEN: der Knopf laedt die Blaupausen der Charaktere.
    _bxb = _box7s(win.bp_table)
    check("b7s die Blaupausen-Tabelle hat einen Leer-Hinweis", _bxb is not None)
    if _bxb is not None:
        _gerufen7sb = []
        _alt_bp7s = win.bp_refresh_btn.click
        _alt_sde7s = win.g_sde_btn.click
        win.bp_refresh_btn.click = lambda: _gerufen7sb.append("bp")
        win.g_sde_btn.click = lambda: _gerufen7sb.append("sde")
        try:
            _bxb._aktion()
        finally:
            win.bp_refresh_btn.click = _alt_bp7s
            win.g_sde_btn.click = _alt_sde7s
        eq("b7s der Blaupausen-Knopf laedt MEINE Blaupausen, nicht die SDE",
           _gerufen7sb, ["bp"])
    # 4. NACH DEM SCAN werden die Hinweise neu gestellt - die Tabelle
    # aendert sich beim Scan nicht, ihre Signale feuern also nicht.
    check("b7s nach dem Scan stellt das Programm die Hinweise neu",
          "self._leerhinweise_aktualisieren()   # \"Market scan\" -> \"Load deals\""
          in _src_mw)
finally:
    _st7s.snapshot_age_seconds = _alt_age7s
    try:
        win.deals_table._leerhinweis_stellen()
    except Exception:
        pass

# ---------------------------------------------------------------- (b7q)
# CORP-HANGAR (1.0.8): Einstellungen und der Abruf im Bauplan - am ECHTEN
# Fenster, mit vorgetaeuschtem ESI. Das Netz wird komplett ersetzt; gezaehlt
# wird, wie oft der Corp-Hangar abgerufen wird. DREI Charaktere, EINE Corp:
# es muss GENAU EIN Abruf sein (CLAUDE.md: "Ungeprueft verdreifacht sich
# der Bestand, und der Plan kauft ZU WENIG").
import eve_trader.esi as _esi7q
import eve_trader.config as _cfg7q
_alt7q = {k: getattr(_esi7q, k) for k in (
    "fetch_character_corporation", "granted_scopes", "fetch_character_roles",
    "fetch_corporation_assets", "fetch_corporation_divisions",
    "fetch_corporation_blueprints", "fetch_corporation_jobs",
    "fetch_corporation_name", "container_type_ids_safe")}
_alt_save7q = _cfg7q.save_settings
_alt_set7q = {k: win.settings.get(k) for k in ("use_corp", "corp_divisions")}
_zaehler7q = {"assets": 0, "jobs": 0, "bp": 0}
_STRUCT7q = 1035466617946
try:
    _cfg7q.save_settings = lambda s: None      # Platte nicht anfassen
    # 1. STANDARD AUS - und die Oberflaeche zeigt es.
    check("b7q der Corp-Schalter steht in den Einstellungen",
          hasattr(win, "s_corp") and isinstance(win.s_corp, QComboBox))
    eq("b7q sieben Division-Kaestchen", sorted(win.s_corp_divs), [1, 2, 3, 4, 5, 6, 7])
    # 2. AUS -> der Bauplan fragt ESI GAR NICHT nach der Corp.
    win.settings["use_corp"] = False
    _r7q = win._corp_bau_daten("cid", [{"character_id": 1, "character_name": "A"}], None)
    eq("b7q Schalter aus -> kein Corp-Bestand, kein Abruf",
       (_r7q.get("aktiv"), _r7q.get("summe")), (False, {}))
    # 3. AN, aber keine Division -> nichts zaehlen, aber SAGEN warum.
    win.settings["use_corp"] = True
    win.settings["corp_divisions"] = []
    _r7q = win._corp_bau_daten("cid", [{"character_id": 1, "character_name": "A"}], None)
    eq("b7q keine Division gewaehlt -> nichts, mit Hinweis",
       (_r7q.get("keine_division"), _r7q.get("summe")), (True, {}))
    # 4. DREI CHARAKTERE, EINE CORP, alle Director: EIN Abruf, EINMAL gezaehlt.
    _chars7q = [{"character_id": 11, "character_name": "Alpha"},
                {"character_id": 12, "character_name": "Beta"},
                {"character_id": 13, "character_name": "Gamma"}]
    _corp_assets7q = [
        {"item_id": 100, "type_id": 27, "location_id": _STRUCT7q,
         "location_flag": "OfficeFolder", "quantity": 1},
        {"item_id": 1, "type_id": 34, "location_id": 100,
         "location_flag": "CorpSAG1", "quantity": 1000},
        {"item_id": 2, "type_id": 35, "location_id": 100,
         "location_flag": "CorpSAG3", "quantity": 500},
    ]

    def _f_assets7q(client_id, cid, corp_id):
        _zaehler7q["assets"] += 1
        return list(_corp_assets7q)

    def _f_jobs7q(client_id, cid, corp_id, include_delivered=False):
        _zaehler7q["jobs"] += 1
        return [{"job_id": 1, "activity_id": 1, "product_type_id": 587,
                 "runs": 2, "status": "active", "end_date": "2099-01-01T00:00:00Z"}]

    def _f_bp7q(client_id, cid, corp_id, divisions=None):
        _zaehler7q["bp"] += 1
        return [{"type_id": 999, "quantity": 1, "material_efficiency": 10,
                 "time_efficiency": 20, "runs": -1, "is_bpo": True,
                 "location_id": 100, "location_flag": "CorpSAG1",
                 "division": 1, "corporation_id": corp_id}]

    _esi7q.fetch_character_corporation = lambda cid: 900
    _esi7q.granted_scopes = lambda client_id, cid: set(_cfg7q.CORP_SCOPES)
    _esi7q.fetch_character_roles = lambda client_id, cid: {"Director", "Factory_Manager"}
    _esi7q.fetch_corporation_assets = _f_assets7q
    _esi7q.fetch_corporation_divisions = lambda c, cid, corp: {"hangar": [{"division": 1, "name": "Minerals"}]}
    _esi7q.fetch_corporation_blueprints = _f_bp7q
    _esi7q.fetch_corporation_jobs = _f_jobs7q
    _esi7q.fetch_corporation_name = lambda corp: "Test Corp"
    _esi7q.container_type_ids_safe = lambda: set()
    win.settings["corp_divisions"] = [1]
    _r7q = win._corp_bau_daten("cid", _chars7q, None)
    eq("b7q EIN Corp-Abruf fuer drei Charaktere derselben Corp",
       _zaehler7q["assets"], 1)
    eq("b7q der Bestand ist EINMAL gezaehlt, nicht dreifach",
       _r7q.get("summe"), {34: 1000})
    check("b7q Division 3 (nicht gewaehlt) bleibt draussen",
          35 not in (_r7q.get("summe") or {}))
    eq("b7q Corp-Jobs kommen unter der Corp-Nummer",
       sorted(_r7q.get("jobs") or {}), [900])
    eq("b7q EIN Job-Abruf, EIN Blaupausen-Abruf",
       (_zaehler7q["jobs"], _zaehler7q["bp"]), (1, 1))
    eq("b7q Corp-Blaupausen kommen mit", len(_r7q.get("blueprints") or []), 1)
    eq("b7q die Anzeige nennt Corp, Charakter und Division-Namen",
       [(c["name"], c["via"], c["divisions"]) for c in _r7q.get("corps")],
       [("Test Corp", "Alpha", {1: "Minerals"})])
    # 5. ORTSGRENZE wird durchgereicht: an einer fremden Struktur nichts.
    _r7q = win._corp_bau_daten("cid", _chars7q, [123])
    eq("b7q an einer anderen Struktur zaehlt die Corp nichts",
       _r7q.get("summe"), {})
    # 6. KEIN CORP-SCOPE IM TOKEN -> "neu verknuepfen" mit Namen, kein Abruf.
    _zaehler7q["assets"] = 0
    _esi7q.granted_scopes = lambda client_id, cid: set()
    _r7q = win._corp_bau_daten("cid", _chars7q, None)
    eq("b7q ohne Corp-Scope: alle drei muessen neu verknuepfen",
       _r7q.get("relink"), ["Alpha", "Beta", "Gamma"])
    eq("b7q ohne Corp-Scope: kein Abruf", _zaehler7q["assets"], 0)
    # 7. SCOPE DA, ABER KEINE DIRECTOR-ROLLE -> Corp beim Namen nennen.
    _esi7q.granted_scopes = lambda client_id, cid: set(_cfg7q.CORP_SCOPES)
    _esi7q.fetch_character_roles = lambda client_id, cid: set()
    _r7q = win._corp_bau_daten("cid", _chars7q, None)
    eq("b7q ohne Director-Rolle wird die Corp genannt, nichts gezaehlt",
       (_r7q.get("ohne_rolle"), _r7q.get("summe")), (["Test Corp"], {}))
    # 8. EIN GESCHEITERTER CORP-ABRUF reisst nichts mit: failed-Eintrag.
    _esi7q.fetch_character_roles = lambda client_id, cid: {"Director"}

    def _kaputt7q(*a, **k):
        raise RuntimeError("403")
    _esi7q.fetch_corporation_assets = _kaputt7q
    _r7q = win._corp_bau_daten("cid", _chars7q, None)
    check("b7q ein gescheiterter Abruf landet in failed, kein Absturz",
          len(_r7q.get("failed") or []) == 1 and _r7q.get("summe") == {})
    # 9. DIVISION-KAESTCHEN SPEICHERN SOFORT (wie die Berechtigungs-Schalter).
    for _n, _c in win.s_corp_divs.items():
        _c.setChecked(False)
    win.s_corp_divs[2].setChecked(True)
    eq("b7q ein Kaestchen speichert die Division sofort",
       win.settings.get("corp_divisions"), [2])
    win.s_corp_divs[5].setChecked(True)
    eq("b7q ... und ein zweites dazu", win.settings.get("corp_divisions"), [2, 5])
    check("b7q die Divisions stehen im Feldstand (Ungespeichert-Pruefung)",
          win._einstellungen_feldstand().get("corp_divs") == (2, 5))
finally:
    for k, v in _alt7q.items():
        setattr(_esi7q, k, v)
    _cfg7q.save_settings = _alt_save7q
    for k, v in _alt_set7q.items():
        if v is None:
            win.settings.pop(k, None)
        else:
            win.settings[k] = v
    for _c in win.s_corp_divs.values():
        _c.blockSignals(True)
        _c.setChecked(False)
        _c.blockSignals(False)
    # Der gespeicherte Stand muss zu den Feldern passen - sonst haelt die
    # Ungespeichert-Pruefung jeden folgenden Reiterwechsel an (b59/b78).
    win._einstellungen_stand_merken()
    _app.processEvents()

# ---------------------------------------------------------------- (b9)
# REAKTION ALS ENDPRODUKT. Der Dialog zeigte bisher auch dann ME/TE-Eingabe,
# Invention-Tab, Invention-Seitenpanel und eine Kostenzeile "Invention" - alle
# vier sind bei einer Reaktion rechnerisch wirkungslos (nicht erforschbar,
# nicht erfindbar). Sichtbare Stellschrauben, die nichts bewegen, sind
# schlimmer als fehlende: der Nutzer dreht daran und wundert sich.
# ZWEITER ZWEIG: der Test oben baut ausschliesslich ein FERTIGUNGS-Endprodukt
# (reaction_products = set()) - ohne diesen Block waere die neue Bedingung
# nie betreten worden und trotzdem alles gruen.


class _RecipesReaction:
    """Minimalrezept: 100 Reaktionsausgabe <- 10 Testmat, per REACTION."""
    product_to_bp = {100: (900, I.REACTION, 1)}
    bp_materials = {(900, I.REACTION): [(200, 10)]}
    activity_time = {(900, I.REACTION): 60}
    activity_max_runs = {(900, I.REACTION): 0}
    reaction_products = {100}
    invention_for_bpc = {}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return False


from PySide6.QtWidgets import QSpinBox, QTabWidget

_rec_rea = _RecipesReaction()
win._bd_recipes = _rec_rea
_opts_rea = {"me": 0, "te": 0, "job_pct": 0, "build_reactions": True,
             "tree_depth": 4}
win._bd_opts = dict(_opts_rea)
_plan_rea = I.production_plan(100, 10, PRICES.get, _rec_rea, dict(_opts_rea))
_tree_rea = I.build_tree(100, PRICES.get, _rec_rea, dict(_opts_rea))
_res_rea = {"tree": _tree_rea, "names": {100: "Testreaktion", 200: "Testmat"},
            "sell": 6000.0, "sell_is_contract": False, "plan": _plan_rea}
_dlg_rea = None
try:
    win._show_build_detail(100, "Testreaktion", _res_rea)
    check("b9 Bauplan laesst sich mit einer Reaktion oeffnen", True)
    _dlg_rea = getattr(win, "_bd_dialog", None)
    _tabws = _dlg_rea.findChildren(QTabWidget) if _dlg_rea is not None else []
    _titles = [w.tabText(i) for w in _tabws for i in range(w.count())]
    check("b9 Tabs ueberhaupt gefunden", bool(_titles))
    check("b9 KEIN Invention-Tab bei einer Reaktion",
          not any("Invention" in t for t in _titles))
    check("b9 Rezept-Struktur bleibt erhalten",
          any(_t4("Recipe structure") in t for t in _titles))
    check("b9 Materialien bleiben erhalten",
          any("Materialien" in t or "Materials" in t for t in _titles))
    # Die Kostenzeile "Invention" darf nicht mehr sichtbar sein.
    # Beschriftung heisst seit Sitzung 9 "Invention (\u00d8)" - sie nennt
    # jetzt ausdruecklich den ERWARTUNGSWERT, weil der Invention-Tab die
    # (hoehere) Kaufmenge zeigt und beide vorher gleich hiessen.
    _caps = [x for x in (_dlg_rea.findChildren(QLabel) if _dlg_rea else [])
             if x.text().startswith("Invention")]
    # isHidden() statt isVisible(): letzteres ist bei einem nicht gezeigten
    # Dialog IMMER False - die Pruefung waere vacuously gruen gewesen.
    check("b9 Kostenzeile 'Invention' ist ausgeblendet",
          bool(_caps) and all(x.isHidden() for x in _caps))
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b9 Reaktion als Endprodukt: {type(e).__name__}: {e}")

# T1-FALL: kein Invention-Tab (nichts zu erfinden), aber ME/TE MUESSEN
# erreichbar bleiben - sie wandern nach oben neben die Menge. Ohne das waere
# mit dem Tab das einzige Eingabefeld verschwunden (Nutzer-Frage: "wo gebe
# ich die ein?").
win._bd_recipes = _Recipes()
try:
    win._show_build_detail(100, "Testship", _res)
    _dlg_t1 = getattr(win, "_bd_dialog", None)
    _tabws_t1 = _dlg_t1.findChildren(QTabWidget) if _dlg_t1 is not None else []
    _titles_t1 = [w.tabText(i) for w in _tabws_t1 for i in range(w.count())]
    check("b9 T1 hat KEINEN Invention-Tab",
          not any("Invention" in t for t in _titles_t1))
    # Nur die MARKIERTEN Kopfzeilen-Labels zaehlen - "ME"/"TE" stehen auch an
    # den Kategorie-Chips weiter unten.
    _hdr_t1 = [x.text() for x in (_dlg_t1.findChildren(QLabel) if _dlg_t1 else [])
               if x.property("bd_role") == "endproduct_me_te" and not x.isHidden()]
    check(f"b9 T1 zeigt ME oben  ({_hdr_t1})", "ME" in _hdr_t1)
    check(f"b9 T1 zeigt TE oben  ({_hdr_t1})", "TE" in _hdr_t1)
    # UND DIE EINGABEFELDER SELBST. Die Beschriftungen allein reichen nicht:
    # `_fill_invention_tab` haengt me_spin/te_spin in die Invention-Karte um,
    # sodass beim Rokh nur noch "ME TE" ohne Felder dastand. Der alte Test
    # war gruen, obwohl die Eingabe fehlte.
    _sp_t1 = [x for x in (_dlg_t1.findChildren(QSpinBox) if _dlg_t1 else [])
              if x.property("bd_role") == "endproduct_me_te"]
    eq("b9 T1 hat BEIDE Eingabefelder", len(_sp_t1), 2)
    # ENTSCHEIDEND IST DER ORT, nicht die Existenz. `_fill_invention_tab`
    # haengt dieselben Widget-Objekte in die Invention-Karte um; sie bleiben
    # dabei Kinder des Dialogs, findChildren findet sie also weiterhin. Eine
    # blosse Existenzpruefung war deshalb in BEIDEN Faellen gruen, waehrend
    # der Nutzer oben nur "ME TE" ohne Felder sah.
    # Pruefung: Feld und seine Beschriftung muessen denselben Eltern-Container
    # haben. Wandert das Feld weg, faellt das sofort auf.
    _cap_t1 = [x for x in (_dlg_t1.findChildren(QLabel) if _dlg_t1 else [])
               if x.property("bd_role") == "endproduct_me_te"]
    _cap_par = {x.parentWidget() for x in _cap_t1}
    _sp_par = {x.parentWidget() for x in _sp_t1}
    check(f"b9 T1 ME/TE-Felder stehen beim Label im Kopf "
          f"(Label-Eltern {len(_cap_par)}, Feld-Eltern {len(_sp_par)})",
          bool(_cap_par) and _sp_par == _cap_par)
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b9 T1-Fall: {type(e).__name__}: {e}")


# GEGENPROBE T2: mit Invention-Eintrag MUSS der Tab bleiben - sonst haette die
# Bedingung einfach immer zugeschlagen. Und ME/TE gehoeren dann NICHT nach
# oben, sondern neben die Invention-Karte.
class _RecipesInvented(_Recipes):
    invention_for_bpc = {900: (899, 10, 0.34, [(300, 2)])}


win._bd_recipes = _RecipesInvented()
try:
    win._show_build_detail(100, "Testship-T2", _res)
    _dlg_t2 = getattr(win, "_bd_dialog", None)
    _tabws_t2 = _dlg_t2.findChildren(QTabWidget) if _dlg_t2 is not None else []
    _titles_t2 = [w.tabText(i) for w in _tabws_t2 for i in range(w.count())]
    check("b9 erfundenes Endprodukt behaelt den Invention-Tab",
          any("Invention" in t for t in _titles_t2))
    _hdr_t2 = [x.text() for x in (_dlg_t2.findChildren(QLabel) if _dlg_t2 else [])
               if x.property("bd_role") == "endproduct_me_te"]
    check(f"b9 T2 zeigt ME NICHT oben (kommt aus der Invention)  ({_hdr_t2})",
          not _hdr_t2)
    _sp_t2 = [x for x in (_dlg_t2.findChildren(QSpinBox) if _dlg_t2 else [])
              if x.property("bd_role") == "endproduct_me_te"]
    check("b9 T2 hat auch keine Header-Eingabefelder", not _sp_t2)
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b9 Gegenprobe T2: {type(e).__name__}: {e}")

# ---------------------------------------------------------------- (b2w)
# (Sitzung 17 hierher verschoben: hinter die T2-Gegenprobe, solange deren
#  Fenster offen ist - vorher lief b2w an Resten eines geschlossenen.)
# ZEIT-REGLER DER INVENTION-AUFTEILUNG (Nutzer, Sitzung 9: "nur einen
# Regler bedienen, der mir die Zeit anzeigt"). Funktional am offenen
# Dialog: Regler und Kopien-Feld sind EIN Wert, die Slots deckeln den
# Regler, und die Aufteilungs-Zeile traegt die Ingame-Uebersetzung.
try:
    from PySide6.QtWidgets import QSlider as _QSl2w
    _sl2w = getattr(win, "_inv_zeit", None)
    _ko2w = getattr(win, "_inv_kopien", None)
    _st2w = getattr(win, "_inv_slots", None)
    # DAS OFFENE FENSTER, KEINE RESTE (Sitzung 17, Nutzer-Screenshot Windows:
    # "QSpinBox already deleted"). Gemessen: an der alten Stelle gehoerten die
    # Felder zu einem GESCHLOSSENEN T2-Fenster, nicht zum offenen Bauplan. Ob
    # dessen Widgets noch leben, entschied die Speicherbereinigung - im
    # Container immer ja, beim Nutzer irgendwann nein. Deshalb steht b2w jetzt
    # direkt hinter der T2-Gegenprobe, und prueft das auch.
    _w2w = _st2w.window() if _st2w is not None else None
    check("b2w prueft die Felder des OFFENEN Bauplans, keine Reste",
          _w2w is not None and _w2w is getattr(win, "_bd_dialog", None)
          and _w2w.isVisible())
    check("b2w der Zeit-Regler existiert im Invention-Panel",
          isinstance(_sl2w, _QSl2w) and _ko2w is not None)
    if _sl2w is not None and _ko2w is not None and _st2w is not None:
        _st2w.setValue(10)
        # NUTZSTUFEN-SCHNAPPEN (Nutzer, Sitzung 9: "ich kann ihn hoeher
        # ziehen als er einen Nutzen hat"): nutzlose Positionen schnappen
        # auf die kleinste Kopienzahl derselben Zeitstufe. Getestet MIT der
        # Versuchszahl der Mock-Rezepte (4 - jede Interaktion schreibt sie
        # ueber _fuelle_aufteilung zurueck; ein von Hand gesetzter Wert
        # ueberlebt genau einen Klick, erster Fehlversuch dieses Tests).
        # Nutzstufen fuer 4 Versuche: {1, 2, 4}.
        _sl2w.setValue(4); _app.processEvents()
        eq("b2w Regler ziehen stellt die Kopienzahl", _ko2w.value(), 4)
        _sl2w.setValue(10); _app.processEvents()
        eq("b2w Regler ueber der Versuchszahl schnappt zurueck (10 -> 4)",
           _ko2w.value(), 4)
        _ko2w.setValue(3); _app.processEvents()
        eq("b2w getippte Plateau-Kopien schnappen (3 -> 2)",
           _ko2w.value(), 2)
        eq("b2w und der Regler folgt der geschnappten Zahl",
           _sl2w.value(), 2)
        _ko2w.setValue(4); _app.processEvents()
        eq("b2w nuetzliche Positionen bleiben unangetastet (4 = 4)",
           _sl2w.value(), 4)
        _st2w.setValue(5); _app.processEvents()
        eq("b2w weniger freie Slots deckeln den Regler",
           _sl2w.maximum(), 5)
        _txt2w = win._inv_split_lbl.text()
        check("b2w die Zeile uebersetzt in Ingame-Felder",
              "Job Runs" in _txt2w and "Runs per Copy" in _txt2w)
        # KEINE Wandzeit-Pruefung hier: die erscheint nur, wenn die Rezepte
        # eine Invention-Versuchszeit hergeben - die Mock-Daten der Suite
        # tun das nicht. Das waere ein Test der Testdaten, nicht der Zusage.
        check("b2w und zeigt die Aufteilung selbst",
              "T1-Kopie" in _txt2w or "T1 copy" in _txt2w)
        _st2w.setValue(10); _ko2w.setValue(1); _app.processEvents()
except Exception as _e2w:                                # pragma: no cover
    _fail.append(f"b2w Block geplatzt: {_e2w!r}")
    # WO GENAU? (Sitzung 17): auf Windows bricht der Block ab, im Container
    # nicht - weder mit Windows-Datenordner noch mit groesserer Schrift
    # nachstellbar. Jede Stapelzeile als EIGENE kurze Zeile, weil pruefe.py
    # Zeilen nach 110 Zeichen abschneidet.
    import traceback as _tb2w
    for _fr2w in _tb2w.extract_tb(_e2w.__traceback__)[-4:]:
        print(f"  FEHLER-ORT b2w: {_fr2w.filename.replace(chr(92), '/').rsplit('/', 1)[-1]}"
              f":{_fr2w.lineno}  {(_fr2w.line or '')[:60]}")



# ---------------------------------------------------------------- (b64)
# BAUPLAN (Nutzer, Sitzung 17): "Build or buy" und "Production depth"
# STANDARD AUSGEKLAPPT; die Endprodukt-Zeile stand als "BAUEN \u00b7 20 Runs"
# auf der englischen Oberflaeche. Am offenen T2-Bauplan gemessen.
try:
    _d64 = getattr(win, "_bd_dialog", None)
    _k64 = {}
    for _b64 in (_d64.findChildren(QPushButton) if _d64 is not None else []):
        for _titel64 in ("Build or buy?", "Production depth"):
            if (_b64.text() or "").endswith(_t4(_titel64)) and _b64.isCheckable():
                _k64[_titel64] = _b64.isChecked()
    eq("b64 Build or buy und Production depth starten AUFGEKLAPPT", _k64,
       {"Build or buy?": True, "Production depth": True})
    _baum64 = []
    for _tw64 in (_d64.findChildren(QTreeWidget) if _d64 is not None else []):
        _it64 = _tw64.invisibleRootItem()
        _stapel64 = [_it64.child(_i) for _i in range(_it64.childCount())]
        while _stapel64:
            _x64 = _stapel64.pop()
            _baum64 += [_x64.text(_c) for _c in range(_tw64.columnCount())]
            _stapel64 += [_x64.child(_i) for _i in range(_x64.childCount())]
    check(f"b64 der Baum ist gefuellt ({len(_baum64)} Zellen)", len(_baum64) > 10)
    eq("b64 kein 'BAUEN' in den Baum-Zeilen (englische Oberflaeche)",
       [_z for _z in _baum64 if "BAUEN" in (_z or "")], [])
except Exception as _e64:                                # pragma: no cover
    _fail.append(f"b64 Bauplan-Seitenleiste: {type(_e64).__name__}: {_e64}")


# ---------------------------------------------------------------- (b10)
# EIN RUN IST UNTEILBAR (Nutzer-Hinweis). Reaktionen liefern z.B. 200 Stueck
# pro Run - "Menge 1" gibt es im Spiel nicht, und die Rechnung wuerde den
# ganzen Run auf ein Stueck buchen (gemessen: 250'000 statt 1'250 ISK/Stk).
# ZWEITER ZWEIG: alle bisherigen Testrezepte liefern 1 Stueck pro Run, die
# neue Bedingung waere also nie betreten worden.


class _RecipesBatch:
    """Reaktion: 1 Run -> 200 Stueck."""
    product_to_bp = {100: (900, I.REACTION, 200)}
    bp_materials = {(900, I.REACTION): [(200, 10)]}
    activity_time = {(900, I.REACTION): 60}
    activity_max_runs = {(900, I.REACTION): 0}
    reaction_products = {100}
    invention_for_bpc = {}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return False


win._bd_recipes = _RecipesBatch()
win._bd_qty = 1
try:
    win._show_build_detail(100, "Testreaktion-Batch", _res_rea)
    _dlg_b = getattr(win, "_bd_dialog", None)
    _spins = [x for x in (_dlg_b.findChildren(QSpinBox) if _dlg_b else [])
              if x.minimum() == 200 and x.singleStep() == 200]
    check("b10 Mengenfeld kann nicht unter einen Run", bool(_spins))
    if _spins:
        _qs = _spins[0]
        eq("b10 Startwert auf ganzen Run aufgerundet", _qs.value(), 200)
        # Getippter Zwischenwert wird beim Verlassen aufgerundet.
        _qs.setValue(250)
        _qs.editingFinished.emit()
        eq("b10 Zwischenwert wird auf den naechsten Run aufgerundet",
           _qs.value(), 400)
    _hints = [x.text() for x in (_dlg_b.findChildren(QLabel) if _dlg_b else [])
              if x.property("bd_role") == "runs_hint"]
    check(f"b10 Runs stehen daneben  ({_hints})",
          any(("Run" in t or "run" in t) and "200" in t for t in _hints))
    # RUNS DIREKT EINGEBEN (Discord, Commander Hibb, 16.09.2026). Das
    # Runs-Feld ist eine zweite ANSICHT derselben Zahl: was man dort
    # eintippt, landet als Stueck im Mengenfeld - und umgekehrt. Die
    # Wahrheit bleibt Stueck (gespeicherte Plaene, Reservierung, Runplaner).
    _rs = [x for x in (_dlg_b.findChildren(QSpinBox) if _dlg_b else [])
           if x.property("bd_role") == "runs_spin"]
    _mb = [x for x in (_dlg_b.findChildren(QPushButton) if _dlg_b else [])
           if x.property("bd_role") == "qty_mode"]
    check("b10 beim Batch-Rezept gibt es ein Runs-Feld und den Umschalter",
          bool(_rs) and bool(_mb))
    if _rs and _mb and _spins:
        _qs, _r, _m = _spins[0], _rs[0], _mb[0]
        _alt_mode10 = win.settings.get("bau_qty_in_runs")
        _alt_save10 = _cfg7q.save_settings
        _cfg7q.save_settings = lambda s: None
        try:
            eq("b10 Runs-Feld zeigt die Runs des Stueckfelds (400 -> 2)",
               _r.value(), 2)
            _r.setValue(7)
            eq("b10 7 Runs -> 1'400 Stueck im Mengenfeld", _qs.value(), 1400)
            # UND DIE RECHNUNG FOLGT: Enter im Runs-Feld uebernimmt die
            # Menge in den Plan (`_bd_qty` ist das, womit rebuild rechnet).
            _r.editingFinished.emit()
            _app.processEvents()
            eq("b10 Enter im Runs-Feld -> der Plan rechnet mit 1'400",
               int(getattr(win, "_bd_qty", 0) or 0), 1400)
            _qs.setValue(1000)
            eq("b10 1'000 Stueck -> 5 Runs", _r.value(), 5)
            # Umschalten zeigt nur das eine Feld und merkt sich die Wahl.
            _m.setChecked(True)
            check("b10 im Runs-Modus ist das Stueckfeld weg, das Runs-Feld da",
                  _qs.isHidden() and not _r.isHidden())
            eq("b10 die Wahl wird gespeichert", win.settings.get("bau_qty_in_runs"), True)
            _m.setChecked(False)
            check("b10 zurueck: Stueckfeld da, Runs-Feld weg",
                  not _qs.isHidden() and _r.isHidden())
        finally:
            _cfg7q.save_settings = _alt_save10
            win.settings["bau_qty_in_runs"] = bool(_alt_mode10)
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b10 Batch-Rezept: {type(e).__name__}: {e}")

# GEGENPROBE: bei 1 Stueck pro Run bleibt das Feld frei (kein Mindestwert).
win._bd_recipes = _Recipes()
win._bd_qty = 10
try:
    win._show_build_detail(100, "Testship", _res)
    _dlg_s = getattr(win, "_bd_dialog", None)
    _spins_s = [x for x in (_dlg_s.findChildren(QSpinBox) if _dlg_s else [])
                if x.singleStep() > 1 and x.minimum() > 1]
    check("b10 Einzelstueck-Rezept behaelt die freie Mengeneingabe",
          not _spins_s)
    _hints_s = [x for x in (_dlg_s.findChildren(QLabel) if _dlg_s else [])
                if x.property("bd_role") == "runs_hint" and not x.isHidden()]
    check("b10 und keinen Runs-Hinweis", not _hints_s)
    check("b10 und keinen Runs-Umschalter (waere nur Laerm)",
          not [x for x in _dlg_s.findChildren(QPushButton)
               if x.property("bd_role") == "qty_mode"])
except Exception as e:                                   # pragma: no cover
    _fail.append(f"b10 Gegenprobe Einzelstueck: {type(e).__name__}: {e}")

# ---------------------------------------------------------------- (b8)
# KEINE STREUNENDEN FENSTER. Ein Widget ohne Parent wird durch
# setVisible(True) zu einem eigenen Top-Level-Fenster - beim Nutzer poppte so
# ein leeres "python"-Fenster mit dem Text einer KPI-Unterzeile auf, jedes
# Mal beim Oeffnen des Bauplans. Dieselbe Falle war beim Werkzeuge-Menue
# schon dokumentiert und wurde trotzdem wiederholt -> ab jetzt gemessen.
_app.processEvents()
_strays = [w for w in _app.topLevelWidgets()
           if w.isVisible() and w is not win and w is not _dlg
           and not w.windowTitle().startswith(("Bauplan", "Build plan", "Motor"))
           and w.__class__.__name__ not in ("QMenu", "QToolTip")]
check(f"b8 keine streunenden Top-Level-Fenster {[type(w).__name__ for w in _strays][:3]}",
      not _strays)
_orphan_lbls = [w for w in _app.topLevelWidgets()
                if isinstance(w, QLabel) and w.isVisible()]
check("b8 kein sichtbares Label ohne Parent", not _orphan_lbls)

# ---------------------------------------------------------------- Ergebnis
# ------------------------------------------------------------ (b11)
# Gehoert in DIESE Kette, nicht in die Logik-Tests: die Pruefung baut
# ein echtes Qt-Widget, und dafuer braucht es die QApplication, die es
# nur hier gibt.
# ---------------------------------------------------------------- (b11)
# ISK-EINGABEFELDER NAHMEN KEINE WERTE MEHR AN (Nutzer: "kann bei Frachtdienst
# nicht mehr als 10 ISK eingeben, wollte 445, springt nach Enter zurueck").
# IskGroupedSpin SCHREIBT mit Tausender-Apostroph (textFromValue), erbte aber
# den Pruefer von QSpinBox - und der kennt das Trennzeichen nicht. Die Box
# lehnte also genau das Format ab, das sie selbst anzeigt; ab 1'000 war sie
# gar nicht mehr editierbar. Dazu kam, dass valueFromText das SUFFIX nicht
# abraeumte ("445 ISK/m3" -> float() scheitert -> alten Wert behalten), und
# im Eingabefeld steht immer die volle Anzeige.
from PySide6.QtGui import QValidator as _QV98
from eve_trader.ui.main_window import IskGroupedSpin as _IGS98
_s98 = _IGS98()
_s98.setRange(0, 2_000_000_000)
_s98.setSuffix(" ISK/m\u00b3")
_s98.setValue(10)
eq("b11 Zahl mit Suffix wird angenommen",
   _s98.validate("445 ISK/m\u00b3", 3)[0], _QV98.Acceptable)
eq("b11 eigenes Anzeigeformat wird angenommen",
   _s98.validate("1'234 ISK/m\u00b3", 3)[0], _QV98.Acceptable)
eq("b11 Buchstaben weiterhin abgelehnt",
   _s98.validate("abc", 3)[0], _QV98.Invalid)
eq("b11 leeres Feld ist kein Fehler, sondern 'tippt noch'",
   _s98.validate("", 0)[0], _QV98.Intermediate)
# Der eigentliche Nutzerfall: eintippen und uebernehmen.
_s98.lineEdit().setText("445 ISK/m\u00b3")
_s98.interpretText()
eq("b11 445 kommt auch wirklich an", _s98.value(), 445)
_s98.lineEdit().setText("1'234 ISK/m\u00b3")
_s98.interpretText()
eq("b11 und Werte ueber 1000 ebenso", _s98.value(), 1234)
_s98.setValue(50000)
eq("b11 Anzeige behaelt die Tausendertrennung",
   _s98.text(), "50'000 ISK/m\u00b3")


# ---------------------------------------------------------------- (b13)
# EINFRIEREN FRIERT DEN PLAN EIN (TOP-AUFGABE): mit gesetztem plan_snapshot
# darf der Dialog-Aufbau production_plan NICHT mehr aufrufen - der Plan kommt
# aus dem Schnappschuss (Beleg: praeparierte 999 build_runs, die eine echte
# Rechnung nie ergaebe). Dazu: Menge gesperrt, Knopf sagt was los ist.
import time as _t13
win._bd_pricemap = dict(PRICES)
win._bd_recipes = _Recipes()
win._bd_opts = {"me": 0, "te": 0, "job_pct": 0, "build_reactions": False,
                "tree_depth": 4}
win._bd_type = 100
win._bd_qty = 10
_plan13 = I.production_plan(100, 10, PRICES.get, _Recipes(), dict(win._bd_opts))
_snap13 = MainWindow._plan_snapshot_pack(_plan13)
_snap13["build_runs"] = {"100": 999}      # Marker: kann nur aus dem Snapshot kommen
win._bd_frozen = {"ts": _t13.time(), "qty": 10,
                  "prices": dict(PRICES), "adjusted": {}, "stock": {},
                  "cost_idx": {}, "plan_snapshot": _snap13}
win._bd_frozen_plan_cache = None
_tree13 = I.build_tree(100, PRICES.get, _Recipes(), dict(win._bd_opts))
_res13 = {"tree": _tree13, "names": {100: "Testship", 200: "Testmat"},
          "sell": 6000.0, "sell_is_contract": False, "plan": _plan13}
_calls13 = {"n": 0}
_orig_pp13 = I.production_plan


def _pp13(*a, **kw):
    _calls13["n"] += 1
    return _orig_pp13(*a, **kw)


I.production_plan = _pp13
_dlg13 = None
try:
    win._show_build_detail(100, "Testship-Frozen", _res13)
    _dlg13 = getattr(win, "_bd_dialog", None)
    check("b13 Dialog mit eingefrorenem Plan laesst sich bauen", _dlg13 is not None)
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b13 Dialog eingefroren: {type(e).__name__}: {e}")
finally:
    I.production_plan = _orig_pp13
eq("b13 eingefroren rechnet NICHT neu (production_plan-Aufrufe)",
   _calls13["n"], 0)
_pl13 = (getattr(win, "_bd_plan_ref", None) or {}).get("plan") or {}
eq("b13 der angezeigte Plan IST der Schnappschuss (Marker + int-Key)",
   (_pl13.get("build_runs") or {}).get(100), 999)
if _dlg13 is not None:
    _btxt13 = [b.text() for b in _dlg13.findChildren(QPushButton) if b.text()]
    check("b13 Knopf sagt was los ist (Plan eingefroren + Gewinn live)",
          any(("Plan eingefroren" in t and "Gewinn live" in t)
              or ("Plan frozen" in t and "profit live" in t) for t in _btxt13))
    # Zweisprachig (Sitzung 16): der Tooltip laeuft durch t().
    _locked13 = [s for s in _dlg13.findChildren(QSpinBox)
                 if not s.isEnabled()
                 and ("Plan eingefroren" in (s.toolTip() or "")
                      or "Plan frozen" in (s.toolTip() or ""))]
    check("b13 Mengen-Spinner ist gesperrt und sagt warum", len(_locked13) == 1)
    eq("b13 gesperrte Menge ist die EINGEFRORENE Menge",
       _locked13[0].value() if _locked13 else None, 10)
# Aufraeumen, damit kein Folge-Test versehentlich eingefroren rechnet.
win._bd_frozen = None
win._bd_frozen_plan_cache = None


# ---------------------------------------------------------------- (b14)
# "UEBERNEHMEN" BEI DEN BAU-CHARAKTEREN MUSS BELIEBIG OFT GEHEN (Nutzer-
# Befund Sitzung 11: "ich kann nur 1x uebernehmen klicken, danach sind keine
# aenderungen mehr moeglich ... haken lassen sich noch setzen, aber der
# uebernehmen button ist nicht mehr anklickbar").
#
# URSACHE war NICHT der Knopf, sondern `_reload_char_roles`: es leerte das
# Panel nur ueber `it.widget()`. Die Knopfzeile haengt aber als LAYOUT
# drin (`lay.addLayout(btn_row)`), und fuer ein Unter-Layout ist
# `it.widget()` None - die drei Knoepfe wurden also nie geloescht und
# standen nach dem Neuaufbau ein ZWEITES Mal im Panel. Der alte,
# ausgegraute "Uebernehmen" blieb dort liegen, wo der neue hingehoert:
# die Haken schalteten den NEUEN frei, der Nutzer sah den ALTEN.
# AUSGELOEST wurde der Neuaufbau vom stillen `_load_char_slots(silent=True)`,
# das der Bauplan-Dialog beim Oeffnen selbst anstoesst (freie Slots aelter
# als 10 min) - die ESI-Antwort trifft also genau waehrend des Kreuzens ein.
#
# TEXTPRUEFUNG REICHT HIER NICHT: aa220 liest den Quelltext von
# _save_build_chars/_apply_build_chars und war die ganze Zeit gruen. Der
# Fehler lag zwei Funktionen weiter, in einer Zeile, die den Knopf nie
# erwaehnt. Deshalb hier ECHT geklickt.
from eve_trader import store, config                      # noqa: E402
_chars14 = [{"character_id": 1, "character_name": "Peanut Motor"},
            {"character_id": 2, "character_name": "Berry Motor"}]
_orig_lc14 = store.list_characters
_orig_save14 = config.save_settings
store.list_characters = lambda: list(_chars14)
config.save_settings = lambda s: None      # Platte nicht anfassen
try:
    win._char_roles_dirty = False
    _panel14 = win._build_char_roles_widget()
    _btn14 = win._char_roles_apply_btn
    _box14a = win._char_role_boxes[(1, "bau_build_chars")]

    def _ueber14():
        # SPRACHUNABHAENGIG: gesucht wird der UEBERSETZTE Text, nicht das
        # deutsche Teilwort "bernehmen".
        return [b for b in _panel14.findChildren(QPushButton)
                if b.text() == _t4("\u2713 Apply")]

    check("b14 frisch geoeffnet ist 'Uebernehmen' ausgegraut",
          _btn14 is not None and not _btn14.isEnabled())
    _box14a.setChecked(True)
    _app.processEvents()
    check("b14 ein Kreuz macht 'Uebernehmen' anklickbar", _btn14.isEnabled())
    _btn14.click()
    _app.processEvents()
    check("b14 nach dem Klick ist nichts mehr offen",
          not _btn14.isEnabled() and win._char_roles_dirty is False)
    # DER ENTSCHEIDENDE TEIL: jetzt trifft die ESI-Antwort ein und baut das
    # Roster neu - genau die Stelle, an der der Knopf frueher starb.
    win._reload_char_roles()
    _app.processEvents()
    eq("b14 der Neuaufbau laesst GENAU EINEN 'Uebernehmen' zurueck",
       len(_ueber14()), 1)
    _btn14b = win._char_roles_apply_btn
    check("b14 der gemerkte Knopf ist der, der im Panel steht",
          bool(_ueber14()) and _ueber14()[0] is _btn14b)
    check("b14 er ist nach dem Neuaufbau ausgegraut (nichts offen)",
          not _btn14b.isEnabled())
    # ... und ein weiteres Kreuz muss ihn WIEDER freischalten.
    _box14b = win._char_role_boxes[(2, "bau_reaction_chars")]
    _box14b.setChecked(True)
    _app.processEvents()
    check("b14 nach dem Neuaufbau schaltet ein Kreuz ihn WIEDER frei",
          _btn14b.isEnabled() and win._char_roles_dirty is True)
    _btn14b.click()
    _app.processEvents()
    check("b14 und 'Uebernehmen' laesst sich ein zweites Mal klicken",
          not _btn14b.isEnabled() and win._char_roles_dirty is False)
    # Die Auswahl darf der Neuaufbau nicht verschluckt haben.
    eq("b14 die Rolle des zweiten Charakters ist gespeichert",
       sorted(win.settings.get("bau_reaction_chars") or []), [2])
    # LEERES ROSTER: dort baut _populate_char_roles die Knopfzeile gar nicht.
    # Der gemerkte Knopf darf dann NICHT auf ein totes C++-Objekt zeigen -
    # sonst stirbt das naechste Kreuz mit RuntimeError.
    _chars14.clear()
    win._reload_char_roles()
    _app.processEvents()
    check("b14 ohne Charaktere zeigt der Merker auf nichts (statt auf Totes)",
          win._char_roles_apply_btn is None)
    _sbc_ok14 = True
    try:
        win._save_build_chars()
    except Exception:                                    # pragma: no cover
        _sbc_ok14 = False
    check("b14 ein Kreuz-Speichern stuerzt dort nicht ab", _sbc_ok14)
finally:
    store.list_characters = _orig_lc14
    config.save_settings = _orig_save14
    win._char_roles_dirty = False


# ---------------------------------------------------------------- (b14r)
# REPROCESSING-SKILLS NUR IM TOOLTIP DES CHARAKTERNAMENS (1.0.9, Nutzer
# 17.09.2026: kein Haken, keine Spalte - "den besten reprocess Charakter
# waehlen" macht spaeter der Runplaner selbst). Die Zeile erscheint NUR,
# wenn Skills geladen sind UND die SDE die Skill-IDs kennt - sonst nichts,
# und vor allem keine geratene ID.
_chars14r = [{"character_id": 1, "character_name": "Peanut Motor"},
             {"character_id": 2, "character_name": "Berry Motor"}]
_orig_lc14r = store.list_characters
_orig_save14r = config.save_settings
_orig_ids14r = I.reprocess_skill_ids
_orig_sk14r = win.settings.get("bau_char_skills")
store.list_characters = lambda: list(_chars14r)
config.save_settings = lambda s: None
try:
    def _namen14r(panel):
        return {lb.text(): lb for lb in panel.findChildren(QLabel)
                if lb.text() in ("Peanut Motor", "Berry Motor")}
    # Schluessel str wie nach JSON; Charakter 2 hat nie Skills geladen.
    win.settings["bau_char_skills"] = {"1": {"3385": 4, "3389": 3, "3380": 5}}
    I.reprocess_skill_ids = lambda: {"Reprocessing": 3385, "Reprocessing Efficiency": 3389}
    _p14r = win._build_char_roles_widget()
    _lbs = _namen14r(_p14r)
    check("b14r mit Skills und IDs steht die Zeile im Tooltip",
          _t4("Reprocessing skills: {r} / Efficiency {e}").format(r=4, e=3)
          in _lbs["Peanut Motor"].toolTip())
    check("b14r ohne geladene Skills keine Zeile",
          "Reprocessing" not in _lbs["Berry Motor"].toolTip().split("\n")[-1]
          and _lbs["Berry Motor"].toolTip().count("\n")
          == _lbs["Peanut Motor"].toolTip().count("\n") - 1)
    check("b14r eine Zeile pro Charakter, nicht doppelt",
          _lbs["Peanut Motor"].toolTip().count("Efficiency") == 1)
    I.reprocess_skill_ids = lambda: {}
    _p14r2 = win._build_char_roles_widget()
    check("b14r ohne Skill-IDs aus der SDE keine Zeile (kein Raten)",
          "Efficiency" not in _namen14r(_p14r2)["Peanut Motor"].toolTip())
    # Die Zeile ist zweisprachig hinterlegt.
    from eve_trader import sprache as _sp14r
    check("b14r die Zeile hat eine deutsche Fassung",
          "Reprocessing skills: {r} / Efficiency {e}" in _sp14r.KATALOG["de"])
finally:
    store.list_characters = _orig_lc14r
    config.save_settings = _orig_save14r
    I.reprocess_skill_ids = _orig_ids14r
    if _orig_sk14r is None:
        win.settings.pop("bau_char_skills", None)
    else:
        win.settings["bau_char_skills"] = _orig_sk14r
    win._reload_char_roles()


# ---------------------------------------------------------------- (b15)
# KLICK AUF DEN CHARAKTERNAMEN SETZT/ENTFERNT ALLE ROLLEN (Nutzer-Wunsch
# Sitzung 11: "fuege ein, wenn man auf den charakter namen klickt, dass sich
# alle hacken setzten oder entfernen von diesem charakter") - und das
# HAKEN-SETZEN muss dabei schnell bleiben (gleicher Auftrag): ein Klick darf
# NICHT vier Speichervorgaenge ausloesen.
_chars15 = [{"character_id": 7, "character_name": "Lezaar"},
            {"character_id": 8, "character_name": "Fredy"}]
_orig_lc15 = store.list_characters
_orig_save15 = config.save_settings
_orig_async15 = config.save_settings_async
_schreibt15 = {"sync": 0, "async": 0}
store.list_characters = lambda: list(_chars15)
config.save_settings = lambda s: _schreibt15.__setitem__("sync", _schreibt15["sync"] + 1)
config.save_settings_async = lambda s: _schreibt15.__setitem__(
    "async", _schreibt15["async"] + 1)
try:
    for _k15, _l15 in win._ROSTER_ROLES:
        win.settings[_k15] = []
    win._char_roles_last_saved = None
    win._char_roles_dirty = False
    _panel15 = win._build_char_roles_widget()   # Referenz halten, sonst raeumt
    _panel15.setObjectName("Roster15")          # Python das Widget weg
    _rollen15 = [k for k, _l in win._ROSTER_ROLES]
    _boxen15 = [win._char_role_boxes[(7, k)] for k in _rollen15]
    eq("b15 der Charakter hat vier Rollen-Kreuze", len(_boxen15), 4)
    check("b15 vorher steht keins davon", not any(b.isChecked() for b in _boxen15))

    win._toggle_char_alle_rollen(7)
    _app.processEvents()
    check("b15 ein Klick auf den Namen setzt ALLE vier",
          all(b.isChecked() for b in _boxen15))
    for _k15 in _rollen15:
        check(f"b15 Rolle {_k15} ist auch gespeichert",
              7 in (win.settings.get(_k15) or []))
    check("b15 der Nachbar-Charakter bleibt unangetastet",
          not any(win._char_role_boxes[(8, k)].isChecked() for k in _rollen15))
    check("b15 'Uebernehmen' wird durch den Namensklick freigeschaltet",
          win._char_roles_dirty is True
          and win._char_roles_apply_btn.isEnabled())

    win._toggle_char_alle_rollen(7)
    _app.processEvents()
    check("b15 der naechste Klick entfernt ALLE vier wieder",
          not any(b.isChecked() for b in _boxen15))
    check("b15 ... und raeumt sie auch aus den Einstellungen",
          not any(7 in (win.settings.get(k) or []) for k in _rollen15))

    # HALBZUSTAND: steht nur EIN Haken, muss der Klick auffuellen (nicht
    # leeren) - sonst macht derselbe Klick mal das eine, mal das andere.
    _boxen15[0].setChecked(True)
    _app.processEvents()
    win._toggle_char_alle_rollen(7)
    _app.processEvents()
    check("b15 bei halb gesetzten Rollen fuellt der Klick auf",
          all(b.isChecked() for b in _boxen15))

    # TEMPO: der Namensklick darf die vier Kreuze nur STUMM umlegen. Wuerde
    # jedes Kreuz sein toggled-Signal feuern, liefe _save_build_chars viermal
    # - genau die Haeufung, gegen die die Beschleunigung gebaut ist.
    # GEZAEHLT WIRD DAS SIGNAL, nicht der Schreibauftrag: der Schreibauftrag
    # haengt an der Entprellung und waere auch bei vier Laeufen nur einer -
    # eine Zaehlung dort saehe den Unterschied gar nicht (beim ersten Anlauf
    # genau so passiert, die Mutation blieb blind).
    _signale15 = {"n": 0}
    for _b15 in _boxen15:
        _b15.toggled.connect(lambda *_a: _signale15.__setitem__(
            "n", _signale15["n"] + 1))
    win._toggle_char_alle_rollen(7)          # alle vier aus
    _app.processEvents()
    eq("b15 vier Rollen auf einen Schlag feuern KEIN einziges Kreuz-Signal",
       _signale15["n"], 0)
    check("b15 ... und trotzdem sind danach alle vier aus",
          not any(b.isChecked() for b in _boxen15)
          and not any(7 in (win.settings.get(k) or []) for k in _rollen15))

    # NICHTS GEAENDERT -> GAR NICHT SCHREIBEN.
    _t15 = getattr(win, "_char_roles_save_timer", None)
    if _t15 is not None:
        _t15.stop()                 # die eben faellige Entprellung abraeumen
    win._save_build_chars()
    _t15 = getattr(win, "_char_roles_save_timer", None)
    check("b15 unveraenderte Auswahl loest kein Schreiben aus",
          _t15 is None or not _t15.isActive())
finally:
    store.list_characters = _orig_lc15
    config.save_settings = _orig_save15
    config.save_settings_async = _orig_async15
    win._char_roles_dirty = False


# ---------------------------------------------------------------- (b16)
# SETTINGS SCHREIBEN BLOCKIERT DIE OBERFLAECHE NICHT MEHR (Nutzer Sitzung 11:
# "beschleunige das hacken setzten"). Gemessen war: JSON bauen ~57 ms, Platte
# + fsync ~8 ms hier - beim Nutzer ist der Platten-Teil der teure, weil der
# Virenscanner jede frische Temp-Datei anfasst. Also: Text sofort erzeugen
# (Momentaufnahme, kann nicht mehr verfaelscht werden), schreiben im
# Hintergrund. Hier ECHT gefahren, nicht am Quelltext gelesen.
import json as _json16                                    # noqa: E402
import tempfile as _tmp16                                 # noqa: E402
import time as _time16                                    # noqa: E402
_dir16 = _tmp16.mkdtemp(prefix="settings16-")
_orig_dir16 = config.app_data_dir
_orig_path16 = config.settings_path
config.app_data_dir = lambda: _dir16
config.settings_path = lambda: os.path.join(_dir16, "settings.json")
try:
    _s16 = {"bau_build_chars": [1, 2, 3], "fuellung": ["x" * 50] * 200}
    config.save_settings_async(_s16)
    # Die Momentaufnahme muss SOFORT stehen: eine Aenderung direkt nach dem
    # Aufruf darf nicht mehr in der Datei landen (und darf den laufenden
    # Schreibvorgang auch nicht zum Absturz bringen).
    _s16["bau_build_chars"] = [99]
    config.flush_settings()

    def _lies16():
        """Nie direkt oeffnen: bleibt die Datei aus (kaputter Schreibfaden),
        soll eine BENANNTE Pruefung rot werden statt die Suite abzubrechen -
        Arbeitsregel aus Sitzung 10."""
        try:
            return _json16.load(open(config.settings_path(), encoding="utf-8"))
        except Exception:
            return {"__nicht_lesbar__": True}

    _gelesen16 = _lies16()
    eq("b16 geschrieben wird der Stand VOM AUFRUF, nicht der spaetere",
       _gelesen16.get("bau_build_chars"), [1, 2, 3])
    check("b16 flush_settings wartet, bis die Datei wirklich da ist",
          os.path.exists(config.settings_path()))
    # Der teure Teil darf den Aufrufer nicht aufhalten: der Aufruf selbst
    # muss deutlich schneller zurueckkommen als das synchrone Speichern.
    # NICHT ZWEI ZEITEN VERGLEICHEN: das war eine Uhrmessung auf einem
    # geteilten Rechner und schlug gelegentlich grundlos fehl. Die ZUSAGE
    # ist nicht "schneller", sondern "wartet NICHT auf die Platte" - und das
    # laesst sich ohne Uhr beweisen: das Schreiben wird angehalten, und der
    # Aufruf muss trotzdem zurueckkommen.
    import threading as _th16
    _blockiert16 = _th16.Event()
    _darf16 = _th16.Event()
    _echt_schreib16 = config._schreibe_settings

    def _lahm16(text, _e=_echt_schreib16):
        _blockiert16.set()
        _darf16.wait(5)
        return _e(text)

    config._schreibe_settings = _lahm16
    try:
        config.save_settings_async(_s16)          # darf NICHT blockieren
        _kam_zurueck16 = _blockiert16.wait(3)
        check("b16 der Aufruf kehrt zurueck, waehrend noch geschrieben wird",
              _kam_zurueck16)
    finally:
        _darf16.set()
        config.flush_settings()
        config._schreibe_settings = _echt_schreib16
    # Mehrere Auftraege hintereinander: es gewinnt der LETZTE Stand, und es
    # bleibt bei EINEM Faden (keine Warteschlange veralteter Staende).
    for _i16 in range(5):
        _s16["bau_build_chars"] = [_i16]
        config.save_settings_async(_s16)
    config.flush_settings()
    _gelesen16b = _lies16()
    eq("b16 bei mehreren Auftraegen gewinnt der letzte Stand",
       _gelesen16b.get("bau_build_chars"), [4])
    # Und die Datei ist NIE halb geschrieben - auch nicht, wenn mittendrin
    # ein synchrones Speichern dazwischenfunkt.
    _ganz16 = True
    for _i16 in range(3):
        _s16["bau_build_chars"] = [100 + _i16]
        config.save_settings_async(_s16)
        config.save_settings(_s16)
        if "__nicht_lesbar__" in _lies16():           # pragma: no cover
            _ganz16 = False
    check("b16 die Datei ist nie halb geschrieben", _ganz16)
finally:
    config.app_data_dir = _orig_dir16
    config.settings_path = _orig_path16
    import shutil as _sh16
    _sh16.rmtree(_dir16, ignore_errors=True)


# ---------------------------------------------------------------- (b2t)
# "MEINE BAUPLAENE" NEU GEORDNET (Nutzer-Screenshot, Sitzung 9: "alle sollen
# die selbe groesse haben, keine unterschiede erkennbar", "etwas breitere
# Textboxen", "ganz rechts eine Auflistung ... und den Totalgewinn").
# FUNKTIONAL geprueft an echten Widgets, nicht am Quelltext: eine Textprobe
# saehe die ungleichen Kaesten gar nicht.
try:
    from PySide6.QtWidgets import QFrame as _QF2t
    _alt2t = win.settings.get("bau_saved_plans")
    # Absichtlich EIN sehr langer und ein kurzer Name - genau der Unterschied,
    # der die Karten vorher verschieden breit gemacht hat.
    win.settings["bau_saved_plans"] = [
        {"id": 1, "label": "Medium Projectile Collision Accelerator II Blueprint x80",
         "item_name": "Medium Projectile Collision Accelerator II", "qty": 80,
         "type_id": 31000, "checked": []},
        {"id": 2, "label": "Cerberus x12", "item_name": "Cerberus", "qty": 12,
         "type_id": 11993, "checked": [1, 2]},
        {"id": 3, "label": "Large Hydraulic Bay Thrusters II Blueprint x40",
         "item_name": "Large Hydraulic Bay Thrusters II", "qty": 40,
         "type_id": 31001, "checked": []},
    ]
    win._reload_saved_plans()
    _lay2t = win._plans_layout
    eq("b2t die Seite haengt in EINEM Container", _lay2t.count(), 1)
    _hold2t = _lay2t.itemAt(0).widget()
    check("b2t der Container ist ein Widget", _hold2t is not None)
    _cards2t = [w for w in (_hold2t.findChildren(_QF2t) if _hold2t else [])
                if w.objectName() == "Card"]
    # SITZUNG 20: die Gewinn-Uebersicht ist auf Nutzer-Wunsch breiter
    # geworden (620). Die Schwelle 400 trennte die beiden nicht mehr - die
    # Uebersicht rutschte als vierte "Karte" in die Pruefung und liess jede
    # Gleichheits-Zusage scheitern. Getrennt wird jetzt an der Mindestbreite:
    # Plan-Karten haben MINW 520, die Uebersicht 320. Das haengt an den
    # Konstanten, nicht an einer geratenen Zahl dazwischen.
    _plan2t = [c for c in _cards2t if c.minimumWidth() >= 520]
    eq("b2t drei Plaene ergeben drei Karten", len(_plan2t), 3)
    # BREITE: Layout ERZWINGEN, sonst ist die Pruefung blind (Sitzung 10,
    # vom Rotproben-Komplettlauf aufgedeckt). Ohne adjustSize() liefert ein
    # nie angezeigtes Widget bei width() Qts Platzhalter - fuer ALLE Karten
    # denselben. Die Pruefung zaehlte also dreimal denselben Platzhalter und
    # blieb auch dann gruen, wenn setFixedWidth wieder zu setMaximumWidth
    # zurueckgedreht wurde (gemessen: gesund 980/980/980, krank 952/857/900).
    # sizeHint().width() taugt hier NICHT: es ignoriert die feste Breite und
    # liefert auch bei gesundem Code drei verschiedene Werte.
    # Es ist dieselbe Falle, die drei Zeilen tiefer fuer die HOEHE laengst
    # beschrieben steht - fuer die Breite war sie uebersehen worden.
    # ABGESICHERT gegen None: bei einer Mutation, die den Aufbau zerlegt, ist
    # `_hold2t` None. Ein ungeschuetztes .adjustSize() sprengt dann den GANZEN
    # b2t-Block - und die Geister-Kopfzeilen-Pruefung ganz unten wird nie
    # erreicht. Genau das ist beim Einbau dieser Zeile passiert (Sitzung 10):
    # Mutation 184 wurde dadurch BLIND. Alle anderen Zugriffe auf _hold2t im
    # Block sind aus demselben Grund seit jeher geschuetzt.
    if _hold2t is not None:
        _hold2t.adjustSize()
    for _c in _plan2t:
        _c.adjustSize()
    # SITZUNG 20: die Karten haben keine FESTE Breite mehr - sie wachsen
    # zwischen MINW und MAXW mit dem Fenster, damit auf einem kleinen Monitor
    # nicht waagerecht gescrollt werden muss. `adjustSize()` umgeht das Layout
    # und liefert dann die INHALTS-Breite, die je Karte verschieden ist.
    # Die Zusage ist unveraendert - was sie haelt, ist jetzt: dieselben
    # Grenzen und dieselbe Groessenregel bei jeder Karte. Genau das wird
    # gemessen, statt einer Zahl, die vom Inhalt abhaengt.
    eq("b2t alle Karten haben dieselbe Hoechstbreite",
       len({c.maximumWidth() for c in _plan2t}), 1)
    eq("b2t und dieselbe Mindestbreite",
       len({c.minimumWidth() for c in _plan2t}), 1)
    eq("b2t und dieselbe Groessenregel",
       len({c.sizePolicy().horizontalPolicy() for c in _plan2t}), 1)
    check("b2t sie duerfen kleiner werden als die Hoechstbreite",
          all(c.minimumWidth() < c.maximumWidth() for c in _plan2t))
    # WICHTIG: sizeHint() nach adjustSize(), NICHT height(). Ein nie
    # angezeigtes Widget liefert bei height() Qts Standardmass (480) - die
    # Pruefung verglich vorher also Platzhalter und war damit blind.
    for _c in _plan2t:
        _c.adjustSize()
    eq("b2t alle Karten sind exakt gleich HOCH",
       len({c.sizeHint().height() for c in _plan2t}), 1)
    # DER EIGENTLICHE FALL aus dem Screenshot: die ESI-Meldung "fertig"
    # trifft SPAETER ein und war frueher dreizeilig - genau daran wuchsen
    # einzelne Karten.
    _h_vor2t = {c.sizeHint().height() for c in _plan2t}
    _dlbl2t = win._plan_done_labels.get(2)
    if _dlbl2t is not None:
        _dlbl2t.setText("\u2705 Abgeschlossen\n"
                        "Bau 70'439'801 \u00b7 Verk. 88'419'085")
        _dlbl2t.setVisible(True)
        _app.processEvents()
        for _c in _plan2t:
            _c.adjustSize()
    check("b2t die Fertig-Meldung ist erreichbar", _dlbl2t is not None)
    eq("b2t auch MIT Fertig-Meldung bleiben alle Karten gleich hoch",
       len({c.sizeHint().height() for c in _plan2t}), 1)
    eq("b2t und die Meldung macht die Karte nicht hoeher",
       {c.sizeHint().height() for c in _plan2t}, _h_vor2t)
    check("b2t die Fertig-Meldung wird dabei NICHT abgeschnitten",
          _dlbl2t is not None
          and _dlbl2t.height() >= _dlbl2t.sizeHint().height())
    check("b2t die Karten sind breiter als die alten 760",
          bool(_plan2t) and _plan2t[0].width() > 760)
    # Rechte Spalte: je Plan eine Zeile plus eine Gesamtsumme.
    eq("b2t rechts steht jeder Plan mit einer Gewinn-Zeile",
       len(getattr(win, "_plan_sum_labels", {})), 3)
    check("b2t es gibt ein Gesamt-Label",
          getattr(win, "_plan_total_lbl", None) is not None)
    # SITZUNG 20: an der Mindestbreite erkannt statt an einer Zahl, die mit
    # jeder Verbreiterung nachgezogen werden muesste.
    check("b2t die Gewinn-Uebersicht haengt im selben Container",
          any(c not in _plan2t for c in _cards2t))
    # Der lange Name darf nicht mehr abgeschnitten werden.
    _lbls2t = [l for l in (_hold2t.findChildren(QLabel) if _hold2t else [])
               if "Projectile Collision" in (l.text() or "")]
    check("b2t der lange Plan-Name ist ueberhaupt da", bool(_lbls2t))
    check("b2t und bricht um, statt abgeschnitten zu werden",
          bool(_lbls2t) and _lbls2t[0].wordWrap())
    check("b2t der volle Name steht zusaetzlich im Tooltip",
          bool(_lbls2t) and "Projectile Collision" in (_lbls2t[0].toolTip() or ""))
    # GEWINN-UEBERSICHT (18.09.2026): der Name wird mit "..." gekuerzt statt
    # hart abgeschnitten, der Betrag steht in Festbreitenschrift.
    from eve_trader.ui.main_window import ElideLabel as _EL2t
    _el2t = [l for l in (_hold2t.findChildren(_EL2t) if _hold2t else [])
             if "Projectile Collision" in (l.text() or "")]
    check("b2t in der Gewinn-Uebersicht ist der lange Name ein ElideLabel",
          bool(_el2t) and "Projectile Collision" in (_el2t[0].toolTip() or "")
          and _el2t[0].minimumSizeHint().width() == 0)
    _probe2t = _EL2t("Medium Projectile Collision Accelerator II \u00d7200")
    _probe2t.resize(120, 20)
    _fm2t = _probe2t.fontMetrics()
    check("b2t ElideLabel kuerzt mit \u2026 auf die verfuegbare Breite",
          _fm2t.elidedText(_probe2t.text(), Qt.ElideRight, 120).endswith("\u2026")
          and "drawText(r, int(self.alignment()) | Qt.TextSingleLine, txt)" in
          __import__("inspect").getsource(_EL2t.paintEvent)
          and "elidedText(self.text(), Qt.ElideRight, r.width())" in
          __import__("inspect").getsource(_EL2t.paintEvent))
    check("b2t die Betraege stehen in Festbreitenschrift",
          any("font-family" in (l.styleSheet() or "")
              for l in getattr(win, "_plan_sum_labels", {}).values()))
    # GEISTER-KOPFZEILEN: das alte Aufraeumen sammelte nur Widgets ein, die
    # per addLayout() eingehaengte Kopfzeile blieb stehen und stapelte sich.
    for _ in range(3):
        win._reload_saved_plans()
    _kopf2t = [l for l in win.findChildren(QLabel)
               if (l.text() or "").startswith(_t4("MY BUILD PLANS"))]
    eq("b2t vier Aufbauten hinterlassen GENAU EINE Kopfzeile",
       len(_kopf2t), 1)
    eq("b2t und genau ein Element im Seitenlayout", win._plans_layout.count(), 1)
    win.settings["bau_saved_plans"] = _alt2t
except Exception as _e2t:                                # pragma: no cover
    _fail.append(f"b2t Block geplatzt: {_e2t!r}")


# ---------------------------------------------------------------- (b2u)
# FROZEN-SCHAETZUNG FUNKTIONAL, AUF DEN ISK (Nutzer, Sitzung 9: "Du kannst
# doch mit den Zahlen selber gegenrechnen, warum muss ich jedesmal das
# Tool neu herunterladen ..."). BERECHTIGT: diese Fehlerklasse (Karte vs.
# Dialog beim eingefrorenen Plan) wurde dreimal per Nutzer-Screenshot
# gejagt. Dieser Test rechnet sie HIER nach - mit den ECHTEN Zahlen des
# Hydraulic-Falls: Snapshot-Kosten 3'481'354'464, Sell 60M x 50,
# Gebuehren 4,401% -> Gewinn MUSS -613'384'464 sein (die Karte zeigte
# damals -724'079'984, weil sie die globalen 8,091% nahm).
try:
    _alt2u = {k: win.settings.get(k) for k in
              ("char_fees", "hub_standings", "bau_extra_cost",
               "sales_tax_pct", "broker_fee_pct")}
    # Verkaufscharakter mit exakt 4,401% Gesamtgebuehr herstellen:
    # Accounting/Broker-Skill + Standings so, dass _fees_for_hub die
    # Dialog-Werte liefert. Statt die Skill-Formeln rueckwaerts zu raten,
    # nehmen wir den Rueckfall-Pfad: KEINE char_fees -> _fees9 faellt auf
    # die globalen Einstellungen zurueck, die wir exakt setzen. Damit
    # testet b2u die RECHNUNG (Snapshot + Gebuehren + Extra), und eine
    # zweite Pruefung unten stellt sicher, dass mit char_fees die
    # CHARAKTER-Quelle gewinnt.
    win.settings["char_fees"] = {}
    win.settings["hub_standings"] = {}
    win.settings["sales_tax_pct"] = 2.2005
    win.settings["broker_fee_pct"] = 2.2005   # zusammen 4,401%
    win.settings["bau_extra_cost"] = 0
    _p2u = {"id": 991, "type_id": 424242, "qty": 50,
            "label": "b2u Hydraulic-Nachstellung",
            "item_name": "b2u", "checked": [],
            "frozen": {"ts": 1755200000.0, "qty": 50,
                       "prices": {"424242": 60000000.0},
                       "plan_snapshot": {"total_cost": 3481354464.0}}}
    _pm2u = {424242: 60000000.0}
    _est2u = win._bau_saved_plan_quick_estimate(_p2u, None, _pm2u, {})
    check("b2u die Schaetzung liefert fuer den Frozen-Plan ein Ergebnis",
          _est2u is not None)
    eq("b2u Kosten = Snapshot-Kosten, keine Neuplanung",
       round((_est2u or {}).get("cost", 0)), 3481354464)
    eq("b2u Gewinn auf den ISK wie der Dialog (-613'384'464)",
       round((_est2u or {}).get("profit", 0)), -613384464)
    check("b2u der Einfrier-Zeitstempel kommt mit",
          (_est2u or {}).get("frozen_ts") == 1755200000.0)
    # Und: sobald ein Verkaufscharakter existiert, gewinnt DESSEN Gebuehr
    # (die Quelle nennt ihn beim Namen) - nicht die globalen Prozente.
    win.settings["char_fees"] = {"77": {"combined": 4.401, "acc": 5,
                                        "br": 5, "name": "Lezaar"}}
    win.settings["hub_standings"] = {"jita": {"faction": 5.0, "corp": 5.0}}
    _est2u2 = win._bau_saved_plan_quick_estimate(_p2u, None, _pm2u, {})
    check("b2u mit char_fees stammt die Gebuehr vom Verkaufscharakter",
          "Lezaar" in str((_est2u2 or {}).get("fee_quelle", "")))
    for _k2u, _v2u in _alt2u.items():
        if _v2u is None:
            win.settings.pop(_k2u, None)
        else:
            win.settings[_k2u] = _v2u
except Exception as _e2u:                                # pragma: no cover
    _fail.append(f"b2u Block geplatzt: {_e2u!r}")


# ---------------------------------------------------------------- (b2v)
# FORTSCHRITTSBALKEN (Nutzer, Sitzung 9: "hier waere ein Fortschrittsbalken
# gut, 60/100 gebaut"). Funktional an echten Widgets.
try:
    from PySide6.QtWidgets import QProgressBar as _QPB2v
    from eve_trader.ui import theme as _th
    _alt2v = win.settings.get("bau_saved_plans")
    win.settings["bau_saved_plans"] = [
        {"id": 1, "label": "b2v Plan A", "item_name": "A", "qty": 100,
         "type_id": 31000, "checked": []},
        {"id": 2, "label": "b2v Plan B", "item_name": "B", "qty": 50,
         "type_id": 31001, "checked": []},
    ]
    win._reload_saved_plans()
    _hold2v = win._plans_layout.itemAt(0).widget()
    _bars2v = _hold2v.findChildren(_QPB2v) if _hold2v else []
    eq("b2v jede Karte traegt genau einen Fortschrittsbalken",
       len(_bars2v), 2)
    check("b2v vor dem ESI-Ergebnis steht ehrlich 'wird geprueft'",
          all("wird gepr" in b.format() or "being checked" in b.format()
              for b in _bars2v))
    eq("b2v das Verzeichnis kennt beide Balken",
       len(getattr(win, "_plan_progress", {})), 2)
    # Den ESI-Teilstand von Hand einspielen - wie done() es taete.
    _bar2v = win._plan_progress[1]
    _bar2v.setMaximum(100); _bar2v.setValue(60)
    _bar2v.setFormat("60/100 gebaut")
    check("b2v der Teilstand ist darstellbar (60/100)",
          _bar2v.value() == 60 and _bar2v.maximum() == 100
          and "60/100" in _bar2v.format())
    check("b2v Farben kommen aus theme, kein Hex im Balken-Stil noetig",
          "#" not in _bar2v.styleSheet().replace(_th.BORDER, "").replace(
              _th.MUTED, "").replace(_th.CYAN, "").replace(_th.GREEN, ""))
    win.settings["bau_saved_plans"] = _alt2v
except Exception as _e2v:                                # pragma: no cover
    _fail.append(f"b2v Block geplatzt: {_e2v!r}")


# ---------------------------------------------------------------- (b2x)
# AUSWAHLLISTEN-SYMBOLE (Nutzer, Sitzung 9: "du hast hier Emojis
# vergessen"). _combo_item zieht das Emoji aus dem Text und haengt
# stattdessen ein gezeichnetes Symbol an - hier am ECHTEN Widget
# geprueft, nicht am Quelltext.
try:
    from PySide6.QtWidgets import QComboBox as _QCB2x
    import eve_trader.ui.main_window as _MW2x
    _c2x = _QCB2x()
    _MW2x._combo_item(_c2x, "\u26a1 Aktiv am PC \u00b7 viele Flips", "stunden")
    _MW2x._combo_item(_c2x, "\u2014 Eigene Einstellung \u2014", None)
    _MW2x._combo_item(_c2x, "\U0001F6E1 Kleine sichere Dips", {"a": 1})
    eq("b2x das Emoji ist aus dem Text verschwunden",
       _c2x.itemText(0), "Aktiv am PC \u00b7 viele Flips")
    check("b2x und wurde durch ein Symbol ersetzt",
          not _c2x.itemIcon(0).isNull())
    eq("b2x die hinterlegten Daten bleiben unversehrt",
       _c2x.itemData(0), "stunden")
    eq("b2x Eintraege ohne Emoji bleiben wortgleich",
       _c2x.itemText(1), "\u2014 Eigene Einstellung \u2014")
    check("b2x und bekommen KEIN Symbol untergeschoben",
          _c2x.itemIcon(1).isNull())
    check("b2x auch Preset-Eintraege mit dict-Daten funktionieren",
          _c2x.itemData(2) == {"a": 1} and not _c2x.itemIcon(2).isNull())
except Exception as _e2x:                                # pragma: no cover
    _fail.append(f"b2x Block geplatzt: {_e2x!r}")



# ---------------------------------------------------------------- (b17)
# ZWEI UPDATE-KNOEPFE NEBENEINANDER (Nutzer-Wunsch Sitzung 11: "den Button
# 'Auf neue Programm-Version pruefen' haette ich gerne oben rechts neben
# 'Updates'").
#
# DAS IST HEIKEL, DESHALB FUNKTIONAL GEPRUEFT: die beiden Knoepfe pruefen
# voellig VERSCHIEDENE Dinge - der eine EVE-Server-Version und Baurezepte,
# der andere die Programmfassung. Solange einer davon schlicht "Updates"
# hiess, war die Beschriftung nebeneinander eine Etikettenluege: jeder
# haette den falschen gedrueckt und danach geglaubt, er sei auf dem
# neuesten Stand. Deshalb heisst der EVE-Knopf jetzt "EVE-Daten".
_upd17 = [b for b in win.findChildren(QPushButton)
          if b.text() in (win.update_btn.text(), win.ver_btn.text())]
import ast as _a17
_src17 = open("eve_trader/ui/main_window.py", encoding="utf-8").read()
check("b17 beide Knoepfe stehen im Fenster", len(_upd17) >= 2)
# DIE BESCHRIFTUNGEN MUESSEN UNVERWECHSELBAR SEIN - das ist die Zusage,
# nicht ein bestimmtes Wort. Der Nutzer wollte "Updates" fuer das Programm
# (Sitzung 11); neben "EVE-Daten" ist das eindeutig. Die fruehere Fassung
# verbot "Updates" auf beiden Knoepfen und waere hier rot geworden, obwohl
# nichts verwechselbar ist.
check("b17 der EVE-Knopf nennt EVE",
      "EVE" in win.update_btn.text())
check("b17 der Programm-Knopf nennt NICHT EVE (sonst verwechselbar)",
      "EVE" not in win.ver_btn.text())
check("b17 die beiden heissen nicht gleich",
      win.update_btn.text().strip() != win.ver_btn.text().strip())
# Die Tooltips muessen die Verwechslung ausdruecklich ausschliessen.
# SPRACHUNABHAENGIG (Sitzung 12): die Zusage ist "jeder Tooltip grenzt
# sich vom anderen Knopf ab". Auf Deutsch steht dort "NICHT das Programm",
# auf Englisch "NOT the program" - ein fest gesuchtes Wort haelt nur in
# einer Sprache. Geprueft wird gegen den uebersetzten Katalogtext.
from eve_trader.sprache import t as _t17
check("b17 der EVE-Tooltip grenzt sich vom Programm ab",
      _t17("Does NOT check the program \u2013 use the button next to it.")
      in win.update_btn.toolTip())
check("b17 der Programm-Tooltip grenzt sich von den EVE-Daten ab",
      _t17("Does NOT check the EVE data \u2013 use the button next to it.")
      in win.ver_btn.toolTip())
# Sie muessen auch WIRKLICH verschiedene Wege gehen.
# WOHIN DIE KNOEPFE ZEIGEN - am Quelltext, nicht per Klick.
# Erster Versuch war ein echter Klicktest: er trennte die Verdrahtung und
# legte sie neu an, um mitzuzaehlen - und pruefte damit seine EIGENE
# Verdrahtung statt der des Programms. Er blieb gruen, als eine Mutation
# beide Knoepfe auf dasselbe Ziel legte. Qt laesst eine bereits gebundene
# Verbindung nicht abfangen, also wird hier festgenagelt, WAS verbunden
# wird.
check("b17 jeder Knopf loest seinen EIGENEN Weg aus",
      "self.ver_btn.clicked.connect(self.check_programm_update)" in _src17
      and "self.update_btn.clicked.connect(self._check_for_updates)" in _src17)
# Der Knopf in den Einstellungen bleibt zusaetzlich bestehen - dort steht
# die Versionsnummer und der CCP-Hinweis daneben.
check("b17 der Knopf in den Einstellungen bleibt erhalten",
      getattr(win, "s_ver_btn", None) is not None)
# UND BEIDE muessen sich waehrend der Abfrage sperren und danach wieder
# freigeben. Ohne den oberen wuerde man doppelt klicken koennen.
_cpu17 = ""
for _n17 in _a17.walk(_a17.parse(_src17)):
    if isinstance(_n17, _a17.FunctionDef) and _n17.name == "check_programm_update":
        _cpu17 = "\n".join(_src17.splitlines()[_n17.lineno - 1:_n17.end_lineno])
check("b17 die Abfrage sperrt beide Knoepfe, nicht nur einen",
      '("s_ver_btn", "ver_btn")' in _cpu17)


# ---------------------------------------------------------------- (b18)
# DIE .ico WIRD FRISCH ERZEUGT UND NACHGERECHNET (Nutzer-Befund Sitzung 11:
# "kein Icon" - die EXE trug im Explorer weiter das Standardsymbol).
#
# WARUM HIER UND NICHT IN DER aa-SUITE: erzeugen braucht Qt. Und warum
# ueberhaupt frisch: die fertige .ico liegt im Paket - eine kaputte
# Schreibfunktion faellt daran NICHT auf. Genau daran blieben zwei
# Mutationen blind, obwohl der Erzeuger nachweislich falsch arbeitete.
import importlib.util as _ilu18
import struct as _st18
import tempfile as _tmp18

_spec18 = _ilu18.spec_from_file_location("_mi18", "mache_icon.py")
_mod18 = _ilu18.module_from_spec(_spec18)
_spec18.loader.exec_module(_mod18)
_ziel18 = os.path.join(_tmp18.mkdtemp(prefix="ico18-"), "logo.ico")
_alt_ziel18 = _mod18.ZIEL
try:
    _mod18.ZIEL = _ziel18
    _mod18.main()
    _roh18 = open(_ziel18, "rb").read()
finally:
    _mod18.ZIEL = _alt_ziel18

_res18, _typ18, _anz18 = _st18.unpack("<HHH", _roh18[:6])
eq("b18 frisch erzeugt ist es ein gueltiges Symbol", _typ18, 1)
eq("b18 alle Groessen sind drin", _anz18, len(_mod18.GROESSEN))

_form18 = {}
_bild18 = {}
for _i18 in range(_anz18):
    _e18 = _roh18[6 + 16 * _i18:22 + 16 * _i18]
    _g18 = _e18[0] or 256
    _ln18, _of18 = _st18.unpack("<II", _e18[8:16])
    _d18 = _roh18[_of18:_of18 + _ln18]
    _bild18[_g18] = _d18
    _form18[_g18] = ("PNG" if _d18[:4] == b"\x89PNG"
                     else "DIB" if _st18.unpack("<I", _d18[:4])[0] == 40
                     else "?")
# KLEINE GROESSEN ALS BITMAP: seit Vista DARF ein Symbol PNG-komprimiert
# sein, aber der Explorer zeigt bei den kleinen Groessen dann gern das
# Standardsymbol - der wahrscheinlichste Grund fuer den Nutzer-Befund.
for _g18 in (16, 32, 48):
    eq(f"b18 Groesse {_g18} liegt als Bitmap vor", _form18.get(_g18), "DIB")
eq("b18 nur die 256er ist PNG (als Bitmap waere sie unnoetig gross)",
   _form18.get(256), "PNG")

# DAS BITMAP ZAEHLT VON UNTEN NACH OBEN. Dreht man die Zeilen nicht um,
# steht das Logo auf dem Kopf - und zwar NUR in der EXE, im Programm nie.
_g18 = 32
_kopf18 = _bild18[_g18][:40]
_br18, _ho18 = _st18.unpack("<ii", _kopf18[4:12])
eq(f"b18 der Bitmap-Kopf nennt die doppelte Hoehe (Farbe + Maske)",
   (_br18, _ho18), (_g18, _g18 * 2))
# Oberste Bildzeile mit der LETZTEN Zeile in der Datei vergleichen.
_von_qt18 = _ic2r.logo_pixmap(_g18).toImage()
_zeilen_bytes18 = _g18 * 4
_letzte18 = _bild18[_g18][40 + (_g18 - 1) * _zeilen_bytes18:
                          40 + _g18 * _zeilen_bytes18]
_treffer18 = 0
for _x18 in range(_g18):
    _c18 = _von_qt18.pixelColor(_x18, 0)
    _b18 = _letzte18[_x18 * 4:_x18 * 4 + 4]
    if bytes((_c18.blue(), _c18.green(), _c18.red(), _c18.alpha())) == _b18:
        _treffer18 += 1
check(f"b18 das Bitmap steht richtig herum ({_treffer18}/{_g18} Punkte)",
      _treffer18 >= _g18 - 1)


# ---------------------------------------------------------------- (b19)
# DAS FENSTER MUSS AUF EINEN KLEINEN BILDSCHIRM PASSEN (Nutzer-Befund
# Sitzung 11: "ich kann das tool an den raendern nicht kleiner oder
# groesser ziehen ... alles wird zusammengedrueckt").
#
# URSACHE: Qt laesst ein Fenster NIE kleiner werden als die Summe der
# Mindestgroessen seines Inhalts. Gemessen waren das 2346 x 1271 Pixel -
# mehr, als auf viele Bildschirme passt. Windows verweigerte das
# Verkleinern also nicht aus Willkuer, es ging schlicht nicht.
#
# NEU GEFASST (zweiter Anlauf derselben Sitzung): der Rollbereich umschliesst
# jetzt NUR den Reiter-Inhalt - Sidebar und Hub-Zeile sollen beim Rollen
# stehenbleiben. Damit zaehlt die Hub-Zeile wieder zur Mindestbreite; die
# ehrliche Grenze ist, was die FESTSTEHENDEN Teile brauchen. Entscheidend
# bleibt: kein Vielfaches der Bildschirmbreite, und in der HOEHE fast nichts
# (vorher 1271 px, jetzt unter 400).
# FUNKTIONAL geprueft: eine Quelltextsuche saehe eine solche Zahl nie.
# DIE HARTE GRENZE MESSEN, NICHT DEN WUNSCH (Nutzer, Sitzung 16):
# `minimumSizeHint()` ist nur, was Qt gerne haette - der Inhalt liegt in
# sieben Scrollbereichen, das Fenster darf also kleiner sein. Verbindlich
# ist `minimumWidth()`, und die wurde bewusst gesetzt.
#
# WARUM DAS WICHTIG IST: unter Windows ist dieselbe Schrift ~35 % breiter,
# der Hint lag beim Nutzer bei 1534 - die Pruefung war dort ROT, obwohl er
# das Fenster problemlos auf 1100 zieht. Sie mass das Falsche.
_mh19 = win.minimumSizeHint()
_grenze19 = win.minimumWidth()
check(f"b19 die harte Mindestbreite bleibt notebook-tauglich "
      f"({_grenze19}, Hint {_mh19.width()}x{_mh19.height()})",
      0 < _grenze19 <= 1150)
# UND SIE IST UEBERHAUPT GESETZT: ohne eigene Grenze wuerde Qt den Hint
# nehmen - dann waere der Nutzer wieder bei 1534.
check("b19 eine eigene Mindestbreite ist gesetzt", _grenze19 > 0)
# AM QUELLTEXT MITGEPRUEFT: faellt `setMinimumSize` weg, nimmt Qt den Hint -
# der liegt HIER zufaellig noch unter der Schwelle, unter Windows aber weit
# darueber. Die Messung allein haette den Wegfall also nicht gemeldet.
check("b19 die Grenze wird ausdruecklich gesetzt, nicht von Qt geraten",
      "self.setMinimumSize(1100, 520)" in _src_mw)
# GEMESSEN, nicht behauptet: bei breiterer Schrift (Windows) wandert der
# HINT mit, die Grenze nicht. Genau deshalb ist sie der richtige Massstab.
#   Schrift x1.0  -> Hint 1121, Grenze 1100
#   Schrift x1.35 -> Hint 1349, Grenze 1100
#   Schrift x1.6  -> Hint 1485, Grenze 1100
# (Eine Pruefung "Grenze <= Hint" waere sinnlos - beide koennen sich
# unabhaengig bewegen. Die Zahlen oben belegen das Verhalten.)
# Es muss auf einen kleinen Bildschirm passen - 1366x768 ist die
# Untergrenze, die man bei Notebooks noch antrifft.
# NOTEBOOK-GROESSE: 1366x768 ist die Untergrenze, die man bei Notebooks
# noch antrifft. Kleiner geht bewusst nicht - Sidebar, Hub-Zeile und die
# rechte Werkzeugleiste brauchen zusammen rund 1100 px, und die sollen
# stehenbleiben statt gestaucht zu werden.
win.resize(1366, 768)
_app.processEvents()
eq("b19 es laesst sich auf Notebook-Groesse ziehen",
   (win.width(), win.height()), (1366, 768))
win.resize(1100, 600)
_app.processEvents()
eq("b19 ... und bis an die ehrliche Untergrenze",
   (win.width(), win.height()), (1100, 600))
# ... aber nicht auf Briefmarkengroesse: darunter findet man den Rand zum
# Aufziehen kaum wieder.
check("b19 eine sinnvolle Untergrenze bleibt bestehen",
      win.minimumSize().width() >= 600 and win.minimumSize().height() >= 400)
# WAS NICHT MEHR HINEINPASST, WIRD GEROLLT statt gestaucht.
from PySide6.QtWidgets import QScrollArea as _QSA19
from PySide6.QtWidgets import QFrame as _QF19

# DER ROLLBEREICH SITZT IN JEDEM REITER UM DIE MITTE - nicht aussen um
# alles. Zweiter Anlauf derselben Sitzung: der erste Wurf legte ihn um die
# ganze Huelle, dann rollte die Sidebar mit weg; der zweite um die Reiter,
# dann rollte die rechte WERKZEUGLEISTE mit weg, sobald das Fenster schmal
# wurde ("wenn ich weiter kuerzer ziehe verschwindet die rechte sidebar").
# Jeder Reiter ist [Inhalt | Leiste] - der Rollbereich gehoert INNEN um den
# Inhalt.
_rolls19 = getattr(win, "_mitte_rollbereiche", [])
check(f"b19 die Reiter-Mitten rollen ({len(_rolls19)} Bereiche)",
      len(_rolls19) >= 4
      and all(isinstance(_r, _QSA19) for _r in _rolls19))
check("b19 sie sind auch eingehaengt, nicht nur erzeugt",
      all(_r.parentWidget() is not None for _r in _rolls19))
check("b19 sie nutzen bei grossen Fenstern die volle Breite",
      all(bool(getattr(_r, "widgetResizable", lambda: False)())
          for _r in _rolls19))


def _im_rollbereich19(widget):
    """Steckt das Widget IN einem Rollbereich - rollt es also mit weg?"""
    _p = widget.parentWidget() if widget is not None else None
    while _p is not None:
        if isinstance(_p, _QSA19):
            return True
        _p = _p.parentWidget()
    return False


# DIE BEIDEN LEISTEN MUESSEN STEHENBLEIBEN. Das ist der Kern des Wunsches:
# "die Sidebar links und rechts bleibt immer ersichtlich, somit wird man nur
# in der Mitte scrollen muessen".
check("b19 die Sidebar rollt nicht mit dem Inhalt weg",
      not any(win._sidebar_widget is _r.widget() for _r in _rolls19))
_rails19 = [f for f in win.tabs.findChildren(_QF19)
            if f.objectName() == "Card" and f.maximumWidth() == 210]
check(f"b19 die Werkzeugleisten sind auffindbar ({len(_rails19)})",
      len(_rails19) >= 3)
eq("b19 keine Werkzeugleiste rollt mit dem Inhalt weg",
   [f for f in _rails19 if _im_rollbereich19(f)], [])
# Sie darf aber IN SICH rollen: mit dem grossen Logo forderte sie sonst
# 723 px Mindesthoehe und zwang damit das ganze Fenster.
_sr19 = getattr(win, "_side_roll", None)
check("b19 die Sidebar darf in sich rollen",
      isinstance(_sr19, _QSA19)
      and _sr19.widget() is win._sidebar_widget
      and _sr19.parentWidget() is not None)


# ---------------------------------------------------------------- (b20)
# JEDER AUSGANG DER UPDATE-PRUEFUNG WIRD SICHTBAR GEMELDET (Nutzer-Befund
# Sitzung 11: "beim klicken auf den Knopf passiert nichts, keine Meldung").
# Die Antwort stand NUR in der Statuszeile ganz unten - auf einem kleinen
# Bildschirm sieht die niemand, und ein Knopf, der scheinbar nichts tut,
# wirkt kaputt.
import eve_trader.programm_update as _pu20
import eve_trader.ui.main_window as MW_MOD
import time as _t13x
_alt_pruefen20 = _pu20.pruefen
_alt_box20 = MW_MOD.QMessageBox.information
_gezeigt20 = []
try:
    MW_MOD.QMessageBox.information = staticmethod(
        lambda *_a, **_k: _gezeigt20.append(_a[1] if len(_a) > 1 else "?"))
    # Sitzung 17: der Fall "nicht vergleichbar" laeuft jetzt ueber ein Fenster
    # MIT KNOPF zur Releases-Seite (nichts mehr abtippen) - also auch das
    # ersetzen, sonst bleibt es im Test modal stehen.
    win._releases_wahl = lambda _t: (_gezeigt20.append(_t), False)[1]
    for _fall20, _antwort20 in (
            ("aktuell", {"neuer": False, "hinweis": "", "version": "0.1.0",
                         "url": None}),
            ("nicht vergleichbar", {"neuer": False, "hinweis": "keine Antwort",
                                    "version": None, "url": None})):
        _gezeigt20.clear()
        _pu20.pruefen = lambda _r, _v, holen=None, _a=_antwort20: _a
        win.check_programm_update()
        for _ in range(40):
            _app.processEvents()
            if _gezeigt20:
                break
            _t13x.sleep(0.05)
        check(f"b20 Fall '{_fall20}' wird sichtbar gemeldet", bool(_gezeigt20))
    check("b20 danach ist der Knopf wieder bedienbar", win.ver_btn.isEnabled())
    check("b20 der Fehlerfall bietet die Releases-Seite als KNOPF an",
          "Open releases page" in __import__("inspect").getsource(
              type(win)._releases_wahl))
finally:
    _pu20.pruefen = _alt_pruefen20
    MW_MOD.QMessageBox.information = _alt_box20
    if "_releases_wahl" in win.__dict__:
        del win._releases_wahl


# ---------------------------------------------------------------- (b21)
# JEDER AUSWAHL-EINTRAG TRAEGT EIN GEZEICHNETES SYMBOL (Nutzer-Befund
# Sitzung 11: "da fehlen teilweise einfach noch Icons - auf keinen Fall
# Emojis einfuegen").
#
# WARUM ES FEHLTE: die Symbole entstehen in `_combo_item`, das einen
# Emoji-Marker am Zeilenanfang gegen eine gezeichnete Grafik tauscht.
# Eintraege OHNE Marker blieben symbollos - und das Preset-Feld im
# Daytrade-Tab wurde beim Moduswechsel ueber schlichtes addItem neu
# aufgebaut, verlor die Symbole also selbst dort, wo ein Marker da war.
# Genau deshalb sah der Nutzer sie im Modus-Feld, aber nicht daneben.
#
# FUNKTIONAL geprueft: eine Quelltextsuche saehe ein leeres QIcon nicht.
from PySide6.QtWidgets import QComboBox as _QCB21
from eve_trader.sprache import t as _t21
_neutral21 = _t21("\u2014 Custom \u2014")
for _name21 in ("d_mode", "d_preset", "h_mode", "h_preset", "b_preset"):
    _c21 = getattr(win, _name21, None)
    if not isinstance(_c21, _QCB21):
        _fail.append(f"b21 {_name21}: Auswahlfeld nicht gefunden")
        continue
    _ohne21 = [_c21.itemText(_i) for _i in range(_c21.count())
               if _c21.itemIcon(_i).isNull()
               and _c21.itemText(_i).strip() != _neutral21]
    eq(f"b21 {_name21}: jeder Eintrag hat ein Symbol", _ohne21, [])
    # KEIN EMOJI IM TEXT. Der Marker im Quelltext wird von _combo_item
    # entfernt; bleibt er stehen, fehlt die Zuordnung und der Nutzer sieht
    # genau das, was er nicht wollte.
    _emoji21 = [_c21.itemText(_i) for _i in range(_c21.count())
                if any(ord(_z) > 0x2100 for _z in _c21.itemText(_i))]
    eq(f"b21 {_name21}: kein Emoji im Text stehengeblieben", _emoji21, [])

# DER NEUAUFBAU DARF SIE NICHT VERLIEREN: das war der eigentliche Fehler.
win.d_mode.setCurrentIndex(1)
_app.processEvents()
win._reload_deal_presets()
_app.processEvents()
_ohne21b = [win.d_preset.itemText(_i) for _i in range(win.d_preset.count())
            if win.d_preset.itemIcon(_i).isNull()
            and win.d_preset.itemText(_i).strip() != _neutral21]
eq("b21 auch nach einem Moduswechsel bleiben die Symbole", _ohne21b, [])
win.d_mode.setCurrentIndex(0)
_app.processEvents()


# ---------------------------------------------------------------- (b22)
# DER EINRICHTUNGS-KNOPF STEHT NICHT MEHR IM WEG (Nutzer-Befund Sitzung 11:
# "muss das jeder sehen koennen?").
#
# Im Charaktere-Reiter sass "Einrichtung" direkt neben "Charakter
# verknuepfen". Er lud zum Klicken ein, und was dann kam, sah nach
# Pflichtarbeit aus ("Einmalige Einrichtung, ~2 Minuten") - obwohl der
# ausgelieferte Stand eine eingebaute Client-ID hat und niemand das je
# braucht. Ein Schritt, den 99 % nicht gehen muessen, gehoert nicht neben
# den einen Knopf, den ALLE druecken.
from PySide6.QtWidgets import QPushButton as _QPB22
_knoepfe22 = [b.text() for b in win.findChildren(_QPB22)]
eq("b22 kein Einrichtungs-Knopf mehr neben 'Charakter verknuepfen'",
   [t for t in _knoepfe22 if "Einrichtung" in t], [])
# DER ANLEITUNGS-KNOPF IST WEG (Nutzer-Entscheid 17.09.2026: "raus"). Er
# fuehrte zur Anleitung fuer eine EIGENE ESI-Anwendung - seit der
# eingebauten Client-ID braucht das niemand. Der Einrichtungs-Dialog
# bleibt als Notausgang fuer "Client-ID leer" (open_setup), nur der Weg
# aus den Einstellungen ist zu.
check("b22 kein Anleitungs-Knopf mehr in den Einstellungen",
      getattr(win, "s_setup_btn", None) is None
      and "s_setup_btn" not in _src_mw)
check("b22 das Client-ID-Feld bleibt (die Login-Logik liest es)",
      getattr(win, "s_client", None) is not None)
check("b22 der Notausgang bei leerer Client-ID bleibt",
      "QTimer.singleShot(250, self.open_setup)" in _src_mw)


# ---------------------------------------------------------------- (b23)
# DIE TIEFENPRUEFUNG IST WIEDER ERREICHBAR (Sitzung 11).
#
# Sie hing als Zusatz-Knopf im "Alles aktuell"-Dialog. Der wurde auf
# Nutzerwunsch aufgeraeumt ("das braucht keiner zu sehen") - damit war die
# Funktion aus der Oberflaeche NICHT MEHR AUFRUFBAR, obwohl sie im Programm
# blieb. Code, den niemand erreicht, kann spaeter niemand mehr einordnen.
#
# JETZT: Rechtsklick auf "Baurezepte laden". KEIN eigener Knopf - die
# Hub-Zeile bestimmt die Mindestbreite des Fensters (1100 px), und ein
# vierter Knopf haette sie weiter hochgetrieben, fuer eine Funktion, die
# man vielleicht dreimal im Jahr braucht.
from PySide6.QtCore import Qt as _Qt23
check("b23 der Baurezepte-Knopf hat ein eigenes Kontextmenue",
      win.g_sde_btn.contextMenuPolicy() == _Qt23.CustomContextMenu)
check("b23 es ist mit dem Menue-Aufbau verbunden",
      "self.g_sde_btn.customContextMenuRequested.connect(" in _src_mw
      and "self._sde_kontextmenue" in _src_mw)
_menu23 = _fn_src_mw23 = None
import ast as _a23
for _n23 in _a23.walk(_a23.parse(_src_mw)):
    if isinstance(_n23, _a23.FunctionDef) and _n23.name == "_sde_kontextmenue":
        _menu23 = "\n".join(
            _src_mw.splitlines()[_n23.lineno - 1:_n23.end_lineno])
check("b23 das Menue bietet genau die Tiefenpruefung an",
      _menu23 is not None
      and 'm.addAction(t("Deep-check values"))' in _menu23)
check("b23 der Klick darauf startet sie wirklich",
      _menu23 is not None and "self._check_recipes()" in _menu23)
# ENTDECKBAR: ein Rechtsklick, den niemand ahnt, ist so gut wie kein Weg.
# SPRACHUNABHAENGIG: auf Englisch heisst es "RIGHT-CLICK". Geprueft wird,
# dass der Tooltip die zweite Zeile ueberhaupt traegt - sie ist der EINZIGE
# Hinweis darauf, dass es die Tiefenpruefung noch gibt.
check("b23 der Tooltip verraet den Rechtsklick",
      _t17("RIGHT-CLICK: deep-check values \u2013 compares every yield and "
           "ingredient amount against the game data.")
      in win.g_sde_btn.toolTip())
# UND SIE DARF DIE HUB-ZEILE NICHT BREITER MACHEN - genau dafuer wurde der
# Rechtsklick gewaehlt statt eines vierten Knopfes.
check(f"b23 die Mindestbreite bleibt unter 1150 "
      f"({win.minimumWidth()})",
      0 < win.minimumWidth() <= 1150)


# ---------------------------------------------------------------- (b23)
# DIE OBERFLAECHE SPRICHT WIRKLICH DIE GEWAEHLTE SPRACHE (Sitzung 12).
# FUNKTIONAL an echten Widgets - eine Quelltextsuche saehe nicht, ob der
# Text am Ende auch im Knopf landet.
from eve_trader import sprache as _sp23
import eve_trader.ui.main_window as _MW23

_alt23 = _sp23.aktuelle_sprache()
try:
    _sp23.sprache_setzen("en")
    _w_en = _MW23.MainWindow()
    _app.processEvents()
    eq("b23 auf Englisch heisst der Reiter 'Industry'",
       _w_en._tab_labels["build"], "Industry")
    eq("b23 auf Englisch heisst der Knopf 'Refresh all'",
       _w_en.global_refresh_btn.text(), "Refresh all")
    check("b23 auf Englisch steht kein deutscher Umlaut in der Kopfzeile",
          not any(_z in _w_en.g_sde_btn.text() for _z in "äöüÄÖÜß"))
    # DIE SPRACHWAHL IST SICHTBAR, nicht hinter einem Dialog versteckt.
    _lb23 = getattr(_w_en, "lang_box", None)
    check("b23 die Sprachwahl steht oben und zeigt die aktuelle Sprache",
          _lb23 is not None and _lb23.currentData() == "en")
    eq("b23 beide Sprachen stehen zur Wahl",
       sorted(_lb23.itemData(_i) for _i in range(_lb23.count())),
       ["de", "en"])

    # DAS PORTFOLIO ist die zweite umgestellte Schicht - Kopfzeile, Karten,
    # Tabellenkoepfe und die Zustandsworte in der Status-Spalte.
    eq("b23 auf Englisch heisst der Spaltenkopf 'Qty'",
       _w_en.pf_table.horizontalHeaderItem(1).text(), "Qty")
    eq("b23 auf Englisch sagt die Altersangabe 'never'",
       _w_en._age_str(None), "never")
    eq("b23 ... und setzt die Zahl in den uebersetzten Satz ein",
       _w_en._age_str(300), "5 min ago")
    eq("b23 der Daytrade-Kopf ist auf Englisch",
       _w_en.deals_table.horizontalHeaderItem(6).text(), "Profit/unit")
    # AUCH DIE VORDEREN SPALTEN - eine Mutation, die nur die erste Zeile der
    # Liste anfasst, bliebe sonst unbemerkt (genau so passiert).
    eq("b23 ... auch die vorderste Wert-Spalte",
       _w_en.deals_table.horizontalHeaderItem(1).text(), "Now (buy)")
    eq("b23 der Swing-Kopf ist auf Englisch",
       _w_en.hold_table.horizontalHeaderItem(3).text(), "below normal %")
    eq("b23 ... auch dessen vorderste Wert-Spalte",
       _w_en.hold_table.horizontalHeaderItem(1).text(), "Now (sell)")
    # KEIN UMLAUT MEHR in den sichtbaren Koepfen der englischen Fassung -
    # ein einzelnes vergessenes Wort faellt sonst niemandem auf.
    _koepfe23 = [_w_en.deals_table.horizontalHeaderItem(_i).text()
                 for _i in range(_w_en.deals_table.columnCount())]
    _koepfe23 += [_w_en.hold_table.horizontalHeaderItem(_i).text()
                  for _i in range(_w_en.hold_table.columnCount())]
    eq("b23 kein deutscher Umlaut in den englischen Spaltenkoepfen",
       [_k for _k in _koepfe23 if any(_z in _k for _z in "äöüÄÖÜß")], [])

    # ------------------------------------------------------------ (b62)
    # NUTZER-SCREENSHOTS SITZUNG 17, AM FENSTER GEMESSEN: Profits
    # ("Zeitraum", "Gewinn (netto)", "Umsatz", "Ø Marge"), Transactions
    # ("Typ", "Zeitraum", "Suche"), Settings ("Ziel-Marge", "Broker Fee
    # (Struktur)"), Industry-Presets ("Lohnende Produktion", "Reaktionen",
    # "STRATEGIE"), My blueprints ("Kategorie", "Anzeigen", "Suche", "Typ").
    # Alle Beschriftungen, Knoepfe, Haken und Listeneintraege des ENGLISCHEN
    # Fensters einsammeln - keiner dieser Texte darf dort stehen.
    from PySide6.QtWidgets import QAbstractButton as _QAB62
    _txt62 = [x.text() for x in _w_en.findChildren(QLabel)]
    _txt62 += [x.text() for x in _w_en.findChildren(_QAB62)]
    for _cb62 in _w_en.findChildren(QComboBox):
        _txt62 += [_cb62.itemText(_i) for _i in range(_cb62.count())]
    _verboten62 = ("Zeitraum", "Gewinn (netto)", "Umsatz", "\u00d8 Marge",
                   "Typ:", "Suche:", "Ziel-Marge", "Broker Fee (Struktur)",
                   "Lohnende Produktion", "Reaktionen", "STRATEGIE",
                   "Kategorie:", "Anzeigen:",
                   # Sitzung 17, zweite Runde (eigene Anzeige-Helfer):
                   "Investiert", "Item-Wert", "Erwarteter Gewinn",
                   "FEINFILTER", "CAPITAL-SCHIFFE")
    _gefunden62 = sorted({_v for _v in _verboten62 for _x in _txt62 if _v in (_x or "")})
    eq("b62 keiner der gemeldeten deutschen Texte im englischen Fenster",
       _gefunden62, [])
    check(f"b62 die Sammlung ist nicht leer ({len(_txt62)} Texte)", len(_txt62) > 300)
    check("b62 ... und enthaelt die neuen englischen Texte",
          all(any(_e in (_x or "") for _x in _txt62)
              for _e in ("Period:", "Profit (net)", "Revenue", "Target margin",
                         "Profitable production (T1)", "Category:")))

    _sp23.sprache_setzen("de")
    _w_de = _MW23.MainWindow()
    _app.processEvents()
    eq("b23 auf Deutsch heisst derselbe Reiter 'Bauen'",
       _w_de._tab_labels["build"], "Bauen")
    eq("b23 auf Deutsch heisst der Knopf 'Alles aktualisieren'",
       _w_de.global_refresh_btn.text(), "Alles aktualisieren")
    # DER EVE-DATEN-KNOPF wird nach jeder Pruefung neu beschriftet - er muss
    # dabei uebersetzt BLEIBEN. In Sitzung 11 hiess er nach dem ersten Klick
    # wieder anders, weil die Beschriftung an drei Stellen stand.
    eq("b23 der EVE-Knopf ist uebersetzt",
       _w_de.update_btn.text(), "EVE-Daten")
    eq("b23 ... und bleibt es nach dem Zuruecksetzen",
       _w_de._eve_update_text(), "EVE-Daten")
    eq("b23 auf Deutsch heisst derselbe Spaltenkopf 'Menge'",
       _w_de.pf_table.horizontalHeaderItem(1).text(), "Menge")
    eq("b23 die Altersangabe setzt die Zahl auch auf Deutsch ein",
       _w_de._age_str(300), "vor 5 Min.")

    # DIE TRICHTERZEILE ("warum so wenige Treffer?") ist die wichtigste
    # Erklaerung im Werkzeug - genau die Zeile, an der der Nutzer auf dem
    # frisch installierten Rechner haengen blieb. Sie wird aus Zahl +
    # Grund zusammengesetzt; die Zahl darf NICHT im Katalog stehen.
    _w_de._last_deal_diag = {"analyzed": 3775, "two_sided_low": 562}
    _diag_de = _w_de._deal_diag_text()
    check(f"b23 die Trichterzeile ist auf Deutsch ({_diag_de[:34]!r})",
          "3'775 analysiert" in _diag_de
          and "562 nicht beidseitig t\u00e4glich" in _diag_de)
    # SPRACHE UMSCHALTEN VOR DEM MESSEN: die Trichterzeile wird beim
    # ANZEIGEN uebersetzt, nicht beim Fensterbau - sie folgt also der
    # aktuellen Sprache, nicht der, in der das Fenster entstand. Das ist
    # richtig so (Beschriftungen frieren beim Bauen ein, laufende Texte
    # nicht), muss beim Pruefen aber beachtet werden.
    _sp23.sprache_setzen("en")
    _w_en._last_deal_diag = {"analyzed": 3775, "two_sided_low": 562}
    _diag_en = _w_en._deal_diag_text()
    check(f"b23 ... und auf Englisch ({_diag_en[:34]!r})",
          "3'775 analysed" in _diag_en
          and "562 not traded on both sides daily" in _diag_en)
    check("b23 kein deutscher Umlaut in der englischen Trichterzeile",
          not any(_z in _diag_en for _z in "äöüÄÖÜß"))
    # ETAPPE 3: die Handels-Reiter. Spaltenkoepfe, Strategie-Karte und die
    # Feinfilter-Beschriftungen - alles, was man sieht, ohne etwas zu
    # oeffnen.
    eq("b23 der Daytrade-Kopf ist auf Deutsch uebersetzt",
       _w_de.deals_table.horizontalHeaderItem(6).text(), "Gewinn/Stk")
    eq("b23 der Swing-Kopf ebenso",
       _w_de.hold_table.horizontalHeaderItem(3).text(), "unter Normal %")
    # AUCH DIE TOOLTIPS. Auf Englisch faellt ein vergessenes t() nicht auf -
    # der Schluessel IST der englische Text. Erst auf Deutsch zeigt sich,
    # ob die Uebersetzung wirklich greift.
    check(f"b23 der Markt-Scan-Tooltip ist auf Deutsch "
          f"({_w_de.g_scan_btn.toolTip()[:24]!r})",
          _w_de.g_scan_btn.toolTip().startswith("Scannt den aktiven Hub"))
    check("b23 der SDE-Tooltip ebenso",
          "RECHTSKLICK" in _w_de.g_sde_btn.toolTip())
    # AUCH DIE FEINFILTER-TOOLTIPS - sie erklaeren, was jeder Filter tut,
    # und sind der laengste zusammenhaengende Textblock im Werkzeug.
    # (Sitzung 17: Handelsplan-Knopf entfernt - Pruefung entfaellt)
    check("b23 der Preset-Tooltip ebenso",
          _w_de.d_preset.toolTip().startswith("Fertige Komplett"))

    # NUTZER-FUND: der neutrale Preset-Eintrag stand als "— Custom —"
    # mitten in der deutschen Oberflaeche. Ursache: er steht in einer
    # KLASSEN-KONSTANTE, und t() dort laeuft beim IMPORT - also bevor die
    # Sprache feststeht. Uebersetzt wird jetzt beim EINFUEGEN.
    # ALLE VIER LISTEN pruefen: drei waren richtig, die vierte
    # (Regional) lief ueber einen anderen Weg und blieb englisch.
    _neutral_de = [getattr(_w_de, _n).itemText(0)
                   for _n in ("d_preset", "h_preset", "b_preset", "rg_preset")]
    eq("b23 der neutrale Preset-Eintrag ist ueberall uebersetzt",
       sorted(set(_neutral_de)), ["\u2014 Eigene Einstellung \u2014"])
    # DIE WERKZEUGLEISTEN RECHTS - auf der DEUTSCHEN Seite pruefen: auf
    # Englisch IST der Schluessel der Text, ein vergessenes t() faellt dort
    # nicht auf.
    # BEIDE SEITEN PRUEFEN, und das ist kein Luxus:
    #  * ein fest eingetippter DEUTSCHER Text faellt nur auf ENGLISCH auf,
    #  * ein vergessenes t() (Schluessel = englischer Text) nur auf DEUTSCH.
    # Wer nur eine Seite prueft, laesst die halbe Fehlerklasse durch.
    eq("b23 die Werkzeugleiste rechts ist uebersetzt",
       [_w_de.deals_btn.text(), _w_de.gold_btn.text()],
       ["Deals laden", "Gold-Suche"])
    # DIE UNTERREITER (Etappe 13): Einkaufswagen, Verkaufsliste,
    # Order-Update, Charaktere - ganze Bildschirme, die der Nutzer auf
    # Englisch noch komplett deutsch vorgefunden hat.
    # DIE DAYTRADE-PRESETS (Nutzer-Fund): sie stehen in einer
    # KLASSEN-KONSTANTE, uebersetzt wird beim EINFUEGEN - der Emoji-Marker
    # vorn wird dabei abgetrennt und wieder vorangestellt.
    # NUTZER-SCREENSHOTS: Container-Kopf, Zeitfenster-Auswahl und die
    # Preset-Listen von Swing UND Regional waren auf Deutsch noch englisch
    # bzw. auf Englisch noch deutsch. Beide Seiten pruefen.
    # BEIDE SEITEN: ein fest eingetippter DEUTSCHER Kopf faellt auf der
    # deutschen Seite gar nicht auf - er sieht dort ja richtig aus. Eine
    # Mutation, die genau das tut, lief deshalb blind durch.
    # INDUSTRIE-REITER (Nutzer-Screenshots): rechte Leiste, "Fertig"-Knopf
    # und die Gewinn-Zeilen der Plan-Karten.
    _rail_de = [_b.text() for _b in _w_de.findChildren(_QPB23)
                if _b.text() in ("Meine Blueprints", "My blueprints",
                                 "Strukturen", "Structures")]
    _rail_en = [_b.text() for _b in _w_en.findChildren(_QPB23)
                if _b.text() in ("Meine Blueprints", "My blueprints",
                                 "Strukturen", "Structures")]
    eq("b23 die Industrie-Leiste ist uebersetzt",
       [sorted(_rail_de), sorted(_rail_en)],
       [["Meine Blueprints", "Strukturen"], ["My blueprints", "Structures"]])
    eq("b23 der Container-Kopf ist uebersetzt",
       [[_w_de.cont_tree.headerItem().text(_i) for _i in range(3)],
        [_w_en.cont_tree.headerItem().text(_i) for _i in range(3)]],
       [["Handeln / Container", "Menge", "Jita-Wert"],
        ["Trade / container", "Qty", "Hub value"]])
    eq("b23 die Zeitfenster-Auswahl ebenso",
       [_w_de.d_window.itemText(2), _w_en.d_window.itemText(2)],
       ["30 Tage", "30 days"])
    eq("b23 die Swing-Presets ebenso",
       [_w_de.h_preset.itemText(1), _w_en.h_preset.itemText(1)],
       # OHNE MARKER: `_combo_item` trennt das Emoji ab und ersetzt es
       # durch ein gezeichnetes Symbol - im Text steht es nicht mehr.
       ["Kleine sichere Dips \u00b7 schnelle Erholung",
        "Small safe dips \u00b7 quick recovery"])
    eq("b23 die Regional-Presets ebenso",
       [_w_de.rg_preset.itemText(1), _w_en.rg_preset.itemText(1)],
       ["Sichere Marge (liquide Ziele)", "Safe margin (liquid destinations)"])
    eq("b23 die Presets sind auf Deutsch uebersetzt",
       _w_de.d_preset.itemText(1), "Empfohlen \u00b7 alle Preise")
    eq("b23 ... und auf Englisch englisch (Presets)",
       _w_en.d_preset.itemText(1), "Recommended \u00b7 all prices")
    # LETZTE RUNDE (Sitzung 12): Einstellungen, Bauplaene, Strukturen,
    # Gewinne. Auf BEIDEN Seiten geprueft - ein fest eingetippter deutscher
    # Text faellt nur auf Englisch auf, ein vergessenes t() nur auf Deutsch.
    eq("b23 die Einstellungen sind uebersetzt (deutsch)",
       [_w_de.s_corp_names_btn.text(),
        _w_de.findChild(type(_w_de.s_corp_names_btn), "") is not None],
       ["Namen laden", True])
    eq("b23 die Unterreiter sind uebersetzt (deutsch)",
       [_w_de._sh_step_toggle.text(), _w_de._sh_copy_btn.text()],
       ["\u25b6 Abarbeiten-Modus", "Multibuy kopieren"])
    eq("b23 ... und auf Englisch englisch (Unterreiter)",
       [_w_en._sh_step_toggle.text(), _w_en._sh_copy_btn.text()],
       ["\u25b6 Work-through mode", "Copy multibuy"])
    eq("b23 ... und auf Englisch englisch",
       [_w_en.deals_btn.text(), _w_en.gold_btn.text()],
       ["Load deals", "Gold search"])
    # (Sitzung 17: Akkumulationsplan-Knopf entfernt - Pruefung entfaellt)
    # NICHT AM EINGABEFELD MESSEN: `_install_tip` verschiebt den Tooltip
    # absichtlich vom Feld auf die BESCHRIFTUNG darueber (damit er beim
    # Tippen nicht im Weg steht). Am Feld steht danach "" - das sieht wie
    # ein fehlender Tooltip aus, ist aber Absicht.
    _tips_de = list(getattr(_w_de, "_tip_anchor", {}).values())
    check(f"b23 der Regional-Fracht-Tooltip ebenso ({len(_tips_de)} Tipps)",
          any(_x.startswith("Transportkosten pro m") for _x in _tips_de))
    # UND AUF ENGLISCH KEIN UMLAUT: der Schluessel IST der englische Text,
    # ein vergessenes t() faellt dort sonst nicht auf.
    _tips_en = ([_w_en.d_preset.toolTip()]
                + list(getattr(_w_en, "_tip_anchor", {}).values()))
    _mit_umlaut23 = [_x[:36] for _x in _tips_en
                     if any(_z in _x for _z in "äöüÄÖÜß")]
    eq(f"b23 englische Tooltips ohne Umlaut ({len(_tips_en)} geprueft)",
       _mit_umlaut23, [])
finally:
    _sp23.sprache_setzen(_alt23)


# ---------------------------------------------------------------- (b24)
# DIE ORDER-LEITER HAT KEINE INFO-ZEILE MEHR (Nutzer-Befund Sitzung 12).
#
# Der Text ueber der Leiter beschrieb das angeklickte Item und brauchte je
# nach Name und Zahlen ein bis drei Zeilen. Weil er im selben Kasten sitzt,
# WANDERTE DIE ITEM-LISTE DARUNTER bei jedem Klick um eine Zeile. Ein
# Erklaertext, der die Liste verschiebt, kostet mehr als er nuetzt.
#
# FUNKTIONAL geprueft: es geht nicht um den Wortlaut, sondern darum, dass
# nichts Sichtbares mehr die Hoehe des Kastens veraendern kann.
from PySide6.QtWidgets import QLabel as _QL24
_sichtbar24 = []
for _key24 in ("day", "swing", "region"):
    _ctx24 = getattr(win, "_ladder_ctx", {}).get(_key24)
    if not _ctx24:
        continue
    _inf24 = _ctx24.get("info")
    if _inf24 is not None and _inf24.isVisible():
        _sichtbar24.append(_key24)
eq("b24 keine sichtbare Info-Zeile ueber der Order-Leiter", _sichtbar24, [])

# SIE DARF ABER WEITER BESCHREIBBAR SEIN: rund ein Dutzend Stellen setzen
# dort Text (Ladehinweis, Fehler, Mengenvorschlag). Waere das Objekt weg,
# muesste man sie alle umbauen - viel Risiko fuer nichts.
_ctx24 = getattr(win, "_ladder_ctx", {}).get("day")
check("b24 das Feld existiert weiterhin (Schreibzugriffe laufen ins Leere)",
      _ctx24 is not None and isinstance(_ctx24.get("info"), _QL24))
if _ctx24 and _ctx24.get("info") is not None:
    _ctx24["info"].setText("Testtext")
    check("b24 auch nach dem Beschreiben bleibt es unsichtbar",
          not _ctx24["info"].isVisible())


# ---------------------------------------------------------------- (b25)
# FEHLBEDARF LAEUFT VON SELBST (Nutzer-Wunsch Sitzung 12).
#
# Der Nutzer hatte alles eingekauft, eingefroren, dann Reaktionen gebaut -
# und stand ploetzlich vor "kaufe nach". Die Fehlbedarf-Pruefung sagte
# gleichzeitig "alles deckt sich". Beides stimmte: der Materialien-Reiter
# rechnet den GESAMT-Bedarf, die Pruefung den REST-Bedarf. Der Widerspruch
# war die eigentliche Falle.
#
# FUNKTIONAL geprueft, nicht am Wortlaut: die geteilte Funktion muss es
# geben, sie muss ohne offenen Plan SCHWEIGEN (leere Liste, keine Warnung)
# und darf nie eine Ausnahme werfen - sie laeuft bei jedem Aufbau mit.
check("b25 die geteilte Fehlbedarf-Funktion existiert",
      callable(getattr(win, "_fehlbedarf_jetzt", None)))
try:
    _fb25 = win._fehlbedarf_jetzt()
    _fehler25 = None
except Exception as _e25:
    _fb25, _fehler25 = None, f"{type(_e25).__name__}: {_e25}"
eq("b25 sie wirft nie (laeuft bei jedem Aufbau mit)", _fehler25, None)
# (Ein Plan aus einer frueheren Pruefung ist hier noch offen - deshalb
# NICHT auf "leer" pruefen, sondern auf die FORM: eine Liste von
# 5er-Tupeln. Genau die erwartet der Aufrufer im Materialien-Reiter.)
check("b25 sie liefert eine Liste von 5er-Tupeln",
      isinstance(_fb25, list)
      and all(isinstance(_x, tuple) and len(_x) == 5 for _x in _fb25))


# ---------------------------------------------------------------- (b26)
# DER ESI-NACHLAUF LAEUFT - UND HOERT BEIM SCHLIESSEN AUF.
#
# AM LAUFENDEN FENSTER geprueft, nicht am Quelltext: eine Sonde hat genau
# hier einen Fehler gefunden, den der Quelltext nicht zeigte. `destroyed`
# reicht NICHT - der Dialog wird beim Schliessen nur versteckt, nicht
# geloescht. Der Takt lief munter weiter und haette fuer einen laengst
# geschlossenen Bauplan alle zwei Minuten ESI abgefragt.
from PySide6.QtCore import QTimer as _QT26
# ESI VORTAEUSCHEN: der Nachlauf haengt bewusst am selben Zweig wie der
# Auto-Abruf beim Oeffnen - ohne verknuepfte Charaktere gaebe es nichts
# nachzuladen, und die Pruefung liefe ins Leere (erste Fassung tat genau
# das). Der echte ESI-Aufruf wird dabei abgefangen: geprueft wird der
# TAKT, nicht das Netz.
import eve_trader.store as _store26
_alt_list26 = _store26.list_characters
_alt_core26 = win._load_all_esi_for_plan_core
win.settings["client_id"] = "b26"
_store26.list_characters = lambda: [{"character_id": 1, "name": "b26"}]
win._load_all_esi_for_plan_core = lambda tid: ("", None, None)
try:
    win._show_build_detail(100, "Testship-Nachlauf", _res)
    _app.processEvents()
    _dlg26 = getattr(win, "_bd_dialog", None)
    _timers26 = [_t for _t in _dlg26.findChildren(_QT26)
                 if _t.interval() == 300_000] if _dlg26 else []
    check("b26 mit ESI entsteht ein Nachlauf-Timer", bool(_timers26))
    if _timers26:
        check("b26 der Nachlauf laeuft mit 5-Minuten-Takt",
              _timers26[0].isActive() and _timers26[0].interval() == 300_000)
        _dlg26.close()
        _app.processEvents()
        # DER EIGENTLICHE FUND: `destroyed` reicht nicht - der Dialog wird
        # beim Schliessen nur versteckt. Ohne diese Pruefung liefe der Takt
        # fuer einen geschlossenen Plan weiter.
        check("b26 und steht nach dem SCHLIESSEN (nicht erst beim Loeschen)",
              not _timers26[0].isActive())
finally:
    # ERST DEN AUTO-ABRUF ABWARTEN, DANN ZURUECKSTELLEN (Sitzung 17).
    # Das Oeffnen stoesst einen ESI-Abruf im Hintergrund an. Er ruft den
    # Kern erst auf, wenn er LAEUFT - stand bis dahin schon wieder der
    # echte Kern da, meldete der "No ESI access" und oeffnete eine modale
    # Warnung. Gemessen im Container: die Suite hing genau daran. Ein
    # Wettlauf, der je nach Rechner anders ausgeht.
    # ZWEI PHASEN: der Abruf STARTET erst ueber `QTimer.singleShot(50, ...)`.
    # Wer nur "solange busy" wartet, sieht vor dem Start `False` und stellt
    # sofort zurueck - so ging der erste Reparaturversuch daneben (gemessen).
    # Also mindestens 300 ms laufen lassen, danach bis der Abruf fertig ist.
    import time as _time26
    _ab26 = _time26.time()
    while _time26.time() < _ab26 + 10 and (
            _time26.time() < _ab26 + 0.3
            or getattr(win, "_bd_esi_busy", False)):
        _app.processEvents()
        _time26.sleep(0.02)
    _store26.list_characters = _alt_list26
    win._load_all_esi_for_plan_core = _alt_core26
    win.settings.pop("client_id", None)


# ---------------------------------------------------------------- (b27)
# GRUENER PUNKT STATT KAESTCHEN, wenn ESI den Bau bestaetigt
# (Nutzer-Wunsch Sitzung 12: "ein anderes Symbol fuer 'fertig gebaut und
# ESI geprueft', ohne Kommentar im Bauplan").
#
# WARUM UEBERHAUPT: ein abgehaktes Kaestchen sieht aus wie "ich habe es mir
# vorgenommen". Der gruene Punkt sagt "gebaut UND bestaetigt" - das ist
# eine andere Aussage, und der Nutzer will sie auf einen Blick sehen.
#
# AM SYMBOL selbst geprueft (nicht am Quelltext): es muss ueberhaupt eines
# geben, sonst bliebe die Zeile leer und der Zustand unsichtbar.
from eve_trader.ui import icons as _ic27
_punkt27 = _ic27.gruener_punkt()
check("b27 es gibt ein Punkt-Symbol und es ist nicht leer",
      _punkt27 is not None and not _punkt27.isNull())
# UND ES FOLGT DEM THEME: eine hart eingetippte Farbe wuerde beim naechsten
# Themenwechsel auseinanderdriften (aa170/aa175 verbieten das).
# (Die b-Suite hat kein `_fn_src` - hier direkt die Quelle lesen.)
import inspect as _insp27
_qs27 = _insp27.getsource(_ic27.gruener_punkt)
# NUR AUSGEFUEHRTE ZEILEN: im Beschreibungstext der Funktion steht das Wort
# des Nutzers, dort darf alles vorkommen (dieselbe Falle wie bei aa234).
_code27 = "\n".join(_z for _z in _qs27.splitlines()
                    if not _z.strip().startswith("#"))
_code27 = _code27.split('"""')[0] + _code27.split('"""')[-1]
check("b27 die Farbe kommt aus dem Theme, nicht aus dem Symbol-Modul",
      "_theme.GREEN" in _code27 and "#" not in _code27)


# ---------------------------------------------------------------- (b40)
# NUR EIN BAUPLAN GLEICHZEITIG (Sitzung 13).
#
# NUTZER-MELDUNG: "wenn ich 2 oder mehrere Bauplaene gleichzeitig offen
# habe, dann wird irgendwas gemischt und vermischt, so als ob die sich
# kreuzen oder voneinander etwas geben und nehmen."
#
# REPRODUZIERT (vor der Sperre): zwei Fenster liessen sich oeffnen, danach
# trug `_bd_mat_rows` die Zeilen des ZWEITEN Plans - und "Einkaufsliste
# erstellen" im ERSTEN Fenster liest genau dieses Feld. Ursache: der Dialog
# legt seinen gesamten Zustand auf der MainWindow ab (414 `self._bd_...`
# ueber drei Dateien), zwei Fenster teilen sich also jedes Feld.
#
# Ausgangslage: EIN Bauplan ist offen. Der aus b2 ist bis hierher meist
# schon wieder zu (spaetere Bloecke schliessen ihn) - dann einmal neu
# oeffnen. Das Aufraeumen am Ende schliesst ihn ueber _dlg mit.
_offen40 = win._offener_bauplan()
if _offen40 is None:
    win._show_build_detail(100, "Testship", _res)
    _offen40 = win._offener_bauplan()
    _dlg = _offen40
check("b40 ein Bauplan ist offen (Ausgangslage)", _offen40 is not None)
if _offen40 is not None:
    from PySide6.QtWidgets import QMessageBox as _QMB40
    # DAS POPUP IST MODAL - ungefangen wartet es ewig auf einen Klick und
    # die Suite haengt. Deshalb hier abfangen UND pruefen, dass es kommt:
    # eine Sperre ohne Hinweis waere ein stilles Nichts-passiert (Regel 6).
    _pop40 = []
    _orig40 = _QMB40.information
    _QMB40.information = staticmethod(
        lambda *a40, **k40: _pop40.append((str(a40[1]), str(a40[2]))))
    try:
        # ABSICHTLICH KAPUTTES res: greift die Sperre, kehrt die Funktion
        # zurueck, BEVOR sie res anfasst - es wird gar kein zweiter Dialog
        # gebaut. Greift sie nicht, fliegt sofort ein KeyError auf
        # res["tree"]. So laesst sich die Zusage pruefen, ohne ein zweites
        # schweres Fenster aufzubauen.
        _err40 = None
        try:
            _sbd_echt(100, "Testship", {})      # die UNGEWICKELTE Methode
        except Exception as _e40:
            _err40 = _e40
    finally:
        _QMB40.information = staticmethod(_orig40)
    check(f"b40 die Sperre greift, bevor irgendetwas gebaut wird "
          f"({type(_err40).__name__}: {_err40})" if _err40 else
          "b40 die Sperre greift, bevor irgendetwas gebaut wird",
          _err40 is None)
    check("b40 kein zweites Fenster wird gebaut",
          getattr(win, "_bd_dialog", None) is _offen40)
    check("b40 der Nutzer bekommt einen Hinweis, kein stilles Nichts",
          len(_pop40) == 1)
    check("b40 der Hinweis sagt, worum es geht",
          bool(_pop40) and "Only one build plan" in _pop40[0][0])
    check("b40 und nennt den Grund (geteilte Daten)",
          bool(_pop40) and "share their data" in _pop40[0][1])
    # Ein GESCHLOSSENES Fenster darf nicht sperren - sonst kaeme man nach
    # dem ersten Bauplan an keinen zweiten mehr heran.
    check("b40 ein offenes Fenster wird erkannt",
          win._offener_bauplan() is _offen40)
    _offen40.hide()
    check("b40 ein unsichtbares Fenster sperrt NICHT",
          win._offener_bauplan() is None)
    _offen40.show()


# ---------------------------------------------------------------- (b41)
# ERLEDIGTE RUNS BLEIBEN STEHEN - GEDIMMT, MIT PUNKT STATT KAESTCHEN
# (Nutzer, Sitzung 14, woertlich): "Am liebsten haette ich gerne noch
# sichtbar die runs die ich gemacht habe aber halt gedimmt. damit ich sehen
# kann was ich mal gemacht habe, auch was es mal an materialien gebraucht
# hat usw. ... wenn etwas tatsaechlich per ESI getrackt gebaut wurde, dann
# darf ein Gruener Punkt anstelle des hackens kommen. ists noch in der
# Bauschleife auch schon gedimmt aber violetter punkt. ... Aber das muss
# auch funktionieren ob ich etwas gehackt habe oder nicht. Also imprinzip
# wird nie etwas mehr ausgeblendet nurnoch gedimmt und eingefaerbt und mit
# punkten versehen."
#
# DAS WIDERRUFT DIE ANSAGE AUS SITZUNG 8 ("die ESI soll Sachen ausblenden").
# Die alten Zusagen dazu standen in aa164 und sind dort mit Begruendung
# umgestellt worden.
#
# WARUM FUNKTIONAL UND NICHT ALS TEXTPROBE: alle bisherigen Pruefungen an
# `_fill_bauplan_schedule` lesen nur den Quelltext. Zusagen wie "die Zeile
# steht noch da, hat aber KEIN Kaestchen mehr und ist gedimmt" kann eine
# Textprobe nicht halten - dafuer muss der Baum wirklich gebaut und danach
# nachgesehen werden. Genau die Lehre aus Sitzung 11.
from PySide6.QtWidgets import QTreeWidget as _QTW41
from eve_trader.ui import icons as _icons41
from eve_trader.ui import theme as _theme41
import datetime as _dt41


class _Recipes41:
    """ZWEI Stufen mit ZWEI Items in der unteren: 100 <- 201 + 202, beide
    aus 200. Nur so laesst sich der gefaehrliche Zwischenfall pruefen - eine
    Stufe, in der EINE Position erledigt ist und eine noch offen. Mit dem
    Einzel-Item-Rezept der uebrigen Suite waere jede Stufe entweder ganz
    fertig oder ganz offen, und eine Mutation, die schon bei der ERSTEN
    erledigten Position zuklappt, bliebe blind.
    PREISE: das Endprodukt muss teuer und das Rohmaterial billig sein, sonst
    stuft der Plan die Komponenten als "Kauf billiger" ein und baut sie gar
    nicht (beim ersten Anlauf genau so passiert - der Runplaner war leer)."""
    product_to_bp = {100: (900, I.MANUFACTURING, 1),
                     201: (901, I.MANUFACTURING, 1),
                     202: (902, I.MANUFACTURING, 1)}
    bp_materials = {(900, I.MANUFACTURING): [(201, 5), (202, 5)],
                    (901, I.MANUFACTURING): [(200, 10)],
                    (902, I.MANUFACTURING): [(200, 10)]}
    activity_time = {(900, I.MANUFACTURING): 60, (901, I.MANUFACTURING): 60,
                     (902, I.MANUFACTURING): 60}
    activity_max_runs = {(900, I.MANUFACTURING): 0, (901, I.MANUFACTURING): 0,
                         (902, I.MANUFACTURING): 0}
    reaction_products = set()
    invention_for_bpc = {}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return t in self.product_to_bp


_PRICES41 = {100: 500000.0, 200: 100.0, 201: 9000.0, 202: 9000.0}
_orig_lc41 = store.list_characters
_bak41 = {_k41: win.settings.get(_k41) for _k41 in
          ("bau_build_chars", "bau_reaction_chars", "bau_char_slots",
           "bau_char_free")}
try:
    store.list_characters = lambda: [{"character_id": 1,
                                      "character_name": "Peanut Motor"}]
    win.settings["bau_build_chars"] = [1]
    win.settings["bau_reaction_chars"] = []
    win.settings["bau_char_slots"] = {"1": [10, 10]}
    win.settings["bau_char_free"] = {}
    win._bd_pricemap = dict(_PRICES41)
    win._bd_recipes = _Recipes41()
    win._bd_opts = {"me": 0, "te": 0, "job_pct": 0, "build_reactions": False,
                    "tree_depth": 4}
    win._bd_type = 100
    win._bd_qty = 10
    win._bd_runplan_checked = set()
    _plan41 = I.production_plan(100, 10, _PRICES41.get, _Recipes41(),
                                dict(win._bd_opts))
    # Eingefroren, denn NUR dort wertet das Tool ESI-Fortschritt aus.
    win._bd_frozen = {"ts": _t13.time() - 100, "qty": 10,
                      "prices": dict(_PRICES41), "adjusted": {}, "stock": {},
                      "cost_idx": {},
                      "plan_snapshot": MainWindow._plan_snapshot_pack(_plan41)}
    win._bd_frozen_plan_cache = None
    win._bd_delivered_jobs = []
    _names41 = {100: "Testship", 200: "Testmat", 201: "KompA", 202: "KompB"}
    # Die Komponenten-Stufe MUSS wirklich zwei Bau-Positionen haben, sonst
    # prueft unten alles ins Leere (Preise falsch -> Plan kauft statt baut).
    eq("b41 Vorbedingung: beide Komponenten werden auch wirklich gebaut",
       sorted(int(_k41) for _k41 in (_plan41.get("build_runs") or {})),
       [100, 201, 202])

    def _fuelle41(aktiv=None, geliefert=None):
        """Baum einmal fuellen. `aktiv` = laufende ESI-Jobs je Item,
        `geliefert` = fertig abgelieferte Jobs. Beides getrennt, weil es
        zwei VERSCHIEDENE Zustaende sind (Lauf-Punkt vs. gruener Punkt)."""
        win._bd_active_jobs_map = aktiv or {}
        win._bd_delivered_jobs = geliefert or []
        _tbl41 = _QTW41()
        _tbl41.setColumnCount(6)
        win._fill_bauplan_schedule(_plan41, _names41, 100, 10,
                                   QLabel(), QLabel(), _tbl41)
        return _tbl41

    def _stufen41(tbl):
        return [tbl.topLevelItem(_i) for _i in range(tbl.topLevelItemCount())]

    def _pos41(stufe):
        """Alle ITEM-Zeilen unter einer Stufe (Ebene: Stufe > Charakter >
        Item), als {Name: Item}. Ueber getattr/Schleife statt direktem
        Indexzugriff - eine Mutation soll eine BENANNTE Pruefung rot machen,
        nicht die Suite mit einer Ausnahme abbrechen (Lehre Sitzung 11)."""
        _raus = {}
        for _i in range(stufe.childCount() if stufe is not None else 0):
            _ch = stufe.child(_i)
            for _g in range(_ch.childCount()):
                _it = _ch.child(_g)
                _raus[(_it.text(0) or "").strip()] = _it
        return _raus

    def _charzeilen41(stufe):
        return [stufe.child(_i).text(0) or ""
                for _i in range(stufe.childCount() if stufe is not None else 0)]

    def _hat_kaestchen41(item):
        return (item is not None
                and item.data(0, Qt.CheckStateRole) is not None)

    def _ist_gedimmt41(item):
        return (item is not None
                and item.foreground(0).color().name().lower()
                == _theme41.MUTED.lower())

    _spaet41 = _dt41.datetime.utcfromtimestamp(
        _t13.time() + 60).strftime("%Y-%m-%dT%H:%M:%SZ")

    def _geliefert41(*tids):
        return [{"product_type_id": _t, "activity_id": 1, "runs": 99999,
                 "completed_date": _spaet41} for _t in tids]

    # ---- A) NICHTS laeuft -> alles offen (Gegenprobe) ----
    _off41 = _fuelle41()
    # Den Index der KOMPONENTEN-Stufe aus diesem Lauf holen statt ihn zu
    # raten: die Stufenbeschriftung ist uebersetzbar, die Reihenfolge koennte
    # sich aendern. Ein fester Index waere genau die Sorte Anker, die in
    # Sitzung 10 dreimal umgefallen ist.
    _ikomp41 = next((_i for _i, _s in enumerate(_stufen41(_off41))
                     if "KompA" in _pos41(_s)), None)
    _iend41 = next((_i for _i, _s in enumerate(_stufen41(_off41))
                    if "Testship" in _pos41(_s)), None)
    check("b41 Vorbedingung: Komponenten- und Endprodukt-Stufe sind auffindbar",
          _ikomp41 is not None and _iend41 is not None and _ikomp41 != _iend41)
    _s_off41 = (_off41.topLevelItem(_ikomp41)
                if _ikomp41 is not None else None)
    _p_off41 = _pos41(_s_off41)
    check("b41 Gegenprobe: die offene Position traegt ein Kaestchen",
          _hat_kaestchen41(_p_off41.get("KompA")))
    check("b41 Gegenprobe: die offene Position traegt KEINEN Punkt",
          _p_off41.get("KompA") is not None
          and _p_off41["KompA"].icon(0).isNull())
    check("b41 Gegenprobe: die offene Position ist NICHT gedimmt",
          not _ist_gedimmt41(_p_off41.get("KompA")))
    check("b41 Gegenprobe: die offene Stufe ist aufgeklappt",
          _s_off41 is not None and _s_off41.isExpanded())
    check("b41 Gegenprobe: die offene Stufe traegt KEINEN Fertig-Haken",
          _s_off41 is not None
          and not (_s_off41.text(0) or "").startswith("\u2713"))

    # ---- B) EINE Position in Bau -> TEILWEISE fertig ----
    # DER GEFAEHRLICHE FALL. Klappte die Stufe schon hier zu, geriete die
    # noch OFFENE Position aus dem Blick - der Nutzer steht im Spiel davor
    # und baut sie nie.
    _tei41 = _fuelle41(aktiv={201: [{"runs": 99999}]})
    _s_tei41 = (_tei41.topLevelItem(_ikomp41)
                if _ikomp41 is not None else None)
    _p_tei41 = _pos41(_s_tei41)
    check(f"b41 teilweise: BEIDE Positionen stehen da {sorted(_p_tei41)}",
          "KompA" in _p_tei41 and "KompB" in _p_tei41)
    check("b41 teilweise: die offene Position behaelt ihr Kaestchen",
          _hat_kaestchen41(_p_tei41.get("KompB")))
    check("b41 teilweise: die offene Position bleibt ungedimmt",
          not _ist_gedimmt41(_p_tei41.get("KompB")))
    check("b41 teilweise: die laufende Position hat KEIN Kaestchen mehr",
          not _hat_kaestchen41(_p_tei41.get("KompA")))
    check("b41 teilweise: die Stufe bleibt aufgeklappt",
          _s_tei41 is not None and _s_tei41.isExpanded())
    # GEGENPROBE ZUM MITZIEHEN: solange EINE Position offen ist, behaelt der
    # Charakter sein Kaestchen - er ist ja noch nicht durch.
    _cz_tei41 = (_s_tei41.child(0)
                 if _s_tei41 is not None and _s_tei41.childCount() else None)
    check("b41 teilweise: die Charakter-Zeile behaelt ihr Kaestchen",
          _hat_kaestchen41(_cz_tei41))
    check("b41 teilweise: und traegt noch keinen Punkt",
          _cz_tei41 is not None and _cz_tei41.icon(0).isNull())
    check("b41 teilweise: die Stufe wird NICHT als fertig beschriftet",
          _s_tei41 is not None
          and not (_s_tei41.text(0) or "").startswith("\u2713"))

    # ---- C) ALLES in der Bauschleife -> Stufe fertig, LAUF-Punkt ----
    _lau41 = _fuelle41(aktiv={201: [{"runs": 99999}], 202: [{"runs": 99999}]})
    _s_lau41 = (_lau41.topLevelItem(_ikomp41)
                if _ikomp41 is not None else None)
    _p_lau41 = _pos41(_s_lau41)
    check("b41 in Bau: die Zeilen bleiben ALLE stehen (nichts ausgeblendet)",
          "KompA" in _p_lau41 and "KompB" in _p_lau41)
    check("b41 in Bau: die Charakter-Zeile bleibt ebenfalls stehen",
          any("Peanut Motor" in _z for _z in _charzeilen41(_s_lau41)))
    # DIE CHARAKTER-ZEILE ZIEHT MIT (Nutzer: "dann muessen wir die
    # charaktere auch abhacken"). Sonst stuende ueber lauter gedimmten
    # Punkt-Zeilen ein leeres Kaestchen - die Zeile behauptete das Gegenteil
    # ihrer eigenen Kinder.
    _cz_lau41 = (_s_lau41.child(0)
                 if _s_lau41 is not None and _s_lau41.childCount() else None)
    check("b41 in Bau: die Charakter-Zeile hat KEIN Kaestchen mehr",
          not _hat_kaestchen41(_cz_lau41))
    check("b41 in Bau: die Charakter-Zeile ist gedimmt",
          _ist_gedimmt41(_cz_lau41))
    check("b41 in Bau: auf der Charakter-Zeile steht der LAUF-Punkt",
          _cz_lau41 is not None
          and _cz_lau41.icon(0).cacheKey() == _icons41.lauf_punkt().cacheKey())
    check("b41 in Bau: die Zeile ist gedimmt",
          _ist_gedimmt41(_p_lau41.get("KompA")))
    check("b41 in Bau: KEIN Kaestchen mehr",
          not _hat_kaestchen41(_p_lau41.get("KompA")))
    # DER PUNKT MUSS DER RICHTIGE SEIN. Nur "irgendein Icon" zu pruefen
    # waere blind gegen die Verwechslung der beiden Zustaende - und genau
    # die ist die Aussage, die der Nutzer sehen will.
    check("b41 in Bau: es ist der LAUF-Punkt, nicht der gruene",
          _p_lau41.get("KompA") is not None
          and _p_lau41["KompA"].icon(0).cacheKey()
          == _icons41.lauf_punkt().cacheKey())
    check("b41 in Bau: die Materialien bleiben nachschlagbar",
          _p_lau41.get("KompA") is not None
          and _p_lau41["KompA"].childCount() > 0)
    check("b41 in Bau: die Zeile zeigt die PLAN-Runs, nicht 0",
          _p_lau41.get("KompA") is not None
          and (_p_lau41["KompA"].text(1) or "").strip() not in ("", "0"))
    check("b41 in Bau: die Stufe ist zugeklappt",
          _s_lau41 is not None and not _s_lau41.isExpanded())
    # EIN KLICK MUSS REICHEN (Nutzer-Screenshot: "wo gibts jetzt da gruene
    # punkte?"): wer eine fertige Stufe aufklappt, will die Items sehen -
    # nicht noch eine zugeklappte Charakter-Ebene davor.
    check("b41 in Bau: die Charakter-Zeilen sind offen, ein Klick genuegt",
          _s_lau41 is not None and _s_lau41.childCount() > 0
          and all(_s_lau41.child(_i).isExpanded()
                  for _i in range(_s_lau41.childCount())))
    check("b41 Gegenprobe: in der OFFENEN Stufe bleiben sie zu (Uebersicht)",
          _s_off41 is not None and _s_off41.childCount() > 0
          and not any(_s_off41.child(_i).isExpanded()
                      for _i in range(_s_off41.childCount())))
    # SITZUNG 16, NUTZER-BEFUND: "die blauen Sachen besagen ja, dass etwas im
    # Bau ist. Aber die Ueberkategorie davon zeigt gruen mit Checkhaken - das
    # ist verwirrend." Genau diese Zeile hatte den Fehler FESTGESCHRIEBEN:
    # sie verlangte den Fertig-Haken auf einer Stufe, in der alles noch
    # LAEUFT. Jetzt traegt die Stufe den LAUF-Punkt und sagt "im Bau".
    from eve_trader.ui import theme as _theme41
    check("b41 in Bau: die Stufe traegt den LAUF-Punkt, nicht den Haken",
          _s_lau41 is not None
          and (_s_lau41.text(0) or "").startswith("\u25cf")
          and not (_s_lau41.text(0) or "").startswith("\u2713"))
    check("b41 in Bau: die Stufe sagt 'im Bau', nicht 'finished'",
          _s_lau41 is not None
          and "finished" not in (_s_lau41.text(2) or "").lower())
    # DIE FARBE MUSS MITZIEHEN - gruen auf einer laufenden Stufe waere
    # dieselbe Luege wie der Haken.
    check("b41 in Bau: die Stufe ist NICHT gruen eingefaerbt",
          _s_lau41 is not None
          and _s_lau41.foreground(0).color().name().lower()
          != _theme41.GREEN.lower())
    check(f"b41 in Bau: die Stufe nennt BEIDE Positionen "
          f"({_s_lau41.text(2) if _s_lau41 else None!r})",
          _s_lau41 is not None and "2" in (_s_lau41.text(2) or ""))
    check("b41 in Bau: die Stufe behauptet keine Restdauer mehr",
          _s_lau41 is not None and not (_s_lau41.text(3) or "").strip())
    check("b41 in Bau: die geplante Dauer bleibt im Tooltip nachlesbar",
          _s_lau41 is not None and bool((_s_lau41.toolTip(3) or "").strip()))
    # Die naechste, noch offene Stufe darf davon nichts abbekommen - das ist
    # der Kern des Wunsches ("nurnoch komponents sehen").
    _s_end41 = (_lau41.topLevelItem(_iend41)
                if _iend41 is not None else None)
    check("b41 in Bau: die naechste offene Stufe bleibt unberuehrt",
          _s_end41 is not None and _s_end41.isExpanded()
          and _hat_kaestchen41(_pos41(_s_end41).get("Testship")))

    # ---- D) WIRKLICH GELIEFERT -> gruener Punkt, OHNE eigenen Haken ----
    # "Aber das muss auch funktionieren ob ich etwas gehackt habe oder
    # nicht." Bis Sitzung 13 hing der gruene Punkt INNERHALB von
    # `if _ckey_item in _checked_set:` - ohne Haken kein Punkt. Deshalb hier
    # ausdruecklich mit LEEREM Haken-Satz.
    win._bd_runplan_checked = set()
    _ger41 = _fuelle41(geliefert=_geliefert41(201, 202))
    _s_ger41 = (_ger41.topLevelItem(_ikomp41)
                if _ikomp41 is not None else None)
    _p_ger41 = _pos41(_s_ger41)
    check("b41 geliefert: die Zeilen bleiben stehen",
          "KompA" in _p_ger41 and "KompB" in _p_ger41)
    check("b41 geliefert: gruener Punkt OHNE dass der Nutzer gehakt hat",
          _p_ger41.get("KompA") is not None
          and _p_ger41["KompA"].icon(0).cacheKey()
          == _icons41.gruener_punkt().cacheKey())
    check("b41 geliefert: kein Kaestchen mehr",
          not _hat_kaestchen41(_p_ger41.get("KompA")))
    check("b41 geliefert: gedimmt",
          _ist_gedimmt41(_p_ger41.get("KompA")))
    check("b41 geliefert: die Stufe ist zugeklappt",
          _s_ger41 is not None and not _s_ger41.isExpanded())
    # GEGENPROBE ZUR FARBE: geliefert und laufend duerfen NICHT denselben
    # Punkt bekommen, sonst sagt die Anzeige beide Male dasselbe.
    check("b41 geliefert: es ist NICHT der Lauf-Punkt",
          _p_ger41.get("KompA") is not None
          and _p_ger41["KompA"].icon(0).cacheKey()
          != _icons41.lauf_punkt().cacheKey())

    # ---- E) VOM NUTZER SELBST ABGEHAKT, ESI sieht nichts ----
    # "Abhacken kann ja nur ich": sein Haken bleibt ein Haken (kein Punkt),
    # zaehlt aber fuer den Stufen-Zustand mit - sonst bliebe eine von Hand
    # durchgearbeitete Stufe fuer immer aufgeklappt.
    _sch41 = _fuelle41()
    _s_sch41 = (_sch41.topLevelItem(_ikomp41)
                if _ikomp41 is not None else None)
    _keys41 = set()
    for _nm41 in ("KompA", "KompB"):
        _it41 = _pos41(_s_sch41).get(_nm41)
        if _it41 is not None:
            _k41x = _it41.data(0, Qt.UserRole + 6)
            if _k41x:
                _keys41.add(_k41x)
    eq("b41 Vorbedingung: beide Positionen haben einen Haken-Schluessel",
       len(_keys41), 2)
    win._bd_runplan_checked = set(_keys41)
    _han41 = _fuelle41()
    _s_han41 = (_han41.topLevelItem(_ikomp41)
                if _ikomp41 is not None else None)
    _p_han41 = _pos41(_s_han41)
    check("b41 handabgehakt: die Zeile behaelt ihr Kaestchen (nur ICH hake)",
          _hat_kaestchen41(_p_han41.get("KompA")))
    check("b41 handabgehakt: und traegt KEINEN Punkt (ESI hat nichts gesehen)",
          _p_han41.get("KompA") is not None
          and _p_han41["KompA"].icon(0).isNull())
    check("b41 handabgehakt: die Stufe gilt trotzdem als fertig",
          _s_han41 is not None
          and (_s_han41.text(0) or "").startswith("\u2713")
          and not _s_han41.isExpanded())

    # ---- F) FERTIG GEBAUT, ABER NICHT ABGEHOLT (status "ready") ----
    # NUTZER-SCREENSHOT (Sitzung 14): "da steckt aber schon lange nichts mehr
    # in der Bauschleife". `_bd_active_jobs_map` fuehrt ZWEI Sorten: "active"
    # (laeuft wirklich) und "ready" (fertig, ingame nur nicht abgeholt) - ESI
    # meldet fertige Jobs sogar weiter als "active", erst `job_is_finished`
    # trennt sie. Wer beides zusammenwirft, setzt den Lauf-Punkt auf laengst
    # Gebautes. Nutzer-Entscheid: "ready" gilt als FERTIG.
    win._bd_runplan_checked = set()
    _rdy41 = _fuelle41(aktiv={201: [{"runs": 99999, "status": "ready"}],
                              202: [{"runs": 99999, "status": "ready"}]})
    _s_rdy41 = (_rdy41.topLevelItem(_ikomp41)
                if _ikomp41 is not None else None)
    _z_rdy41 = next((_v for _k, _v in _pos41(_s_rdy41).items()
                     if "KompA" in _k), None)
    check("b41 ready: fertig Gebautes zeigt den GRUENEN Punkt",
          _z_rdy41 is not None
          and _z_rdy41.icon(0).cacheKey()
          == _icons41.gruener_punkt().cacheKey())
    check("b41 ready: und NICHT den Lauf-Punkt (das war der gemeldete Fehler)",
          _z_rdy41 is not None
          and _z_rdy41.icon(0).cacheKey() != _icons41.lauf_punkt().cacheKey())
    # GEGENPROBE: ein WIRKLICH laufender Job bleibt beim Lauf-Punkt.
    _act41 = _fuelle41(aktiv={201: [{"runs": 99999, "status": "active"}],
                              202: [{"runs": 99999, "status": "active"}]})
    _s_act41 = (_act41.topLevelItem(_ikomp41)
                if _ikomp41 is not None else None)
    _z_act41 = next((_v for _k, _v in _pos41(_s_act41).items()
                     if "KompA" in _k), None)
    check("b41 active: ein echt laufender Job behaelt den Lauf-Punkt",
          _z_act41 is not None
          and _z_act41.icon(0).cacheKey() == _icons41.lauf_punkt().cacheKey())
except Exception as e:                                   # pragma: no cover
    import traceback
    traceback.print_exc()
    _fail.append(f"b41 erledigte Runs: {type(e).__name__}: {e}")
finally:
    store.list_characters = _orig_lc41
    for _k41, _v41 in _bak41.items():
        if _v41 is None:
            win.settings.pop(_k41, None)
        else:
            win.settings[_k41] = _v41
    win._bd_frozen = None
    win._bd_frozen_plan_cache = None
    win._bd_active_jobs_map = {}
    win._bd_delivered_jobs = []
    win._bd_runplan_checked = set()
# ---------------------------------------------------------------- (b42)
# DIE DREI BAU-SCHALTER SPERREN EINANDER (Nutzer, Sitzung 14: "komisch das
# man beides anhacken kann, das eine sollte das andere aushebeln" / "wenn man
# das eine anhackt sollte das andere frei werden").
#
# WARUM: `industry.production_plan` entscheidet
#     _prefer_owned = opts["prefer_build_if_owned"] and stock_used[tid] > 0
#     do_build = force or _prefer_owned or ...
# Steht `force` ("Kosten ignorieren") vorne, wird `_prefer_owned` NIE
# ausgewertet. Und ohne "Assets abziehen" gibt es keinen Bestand, also kann
# `stock_used[tid] > 0` nie zutreffen. In beiden Faellen ist der mittlere
# Haken wirkungslos - sah aber bedienbar aus. Dieselbe Fehlerklasse wie die
# Kaestchen an fertigen Runs.
#
# FUNKTIONAL: die Zusage ist "dieser Haken ist grau". Eine Textprobe koennte
# das nicht halten.
_boxen42 = _dlg.findChildren(QCheckBox) if _dlg is not None else []


def _box42(*teile):
    """Findet den Haken ueber einen Textteil - in BEIDEN Sprachen, seit die
    Beschriftungen durch t() laufen (Sitzung 16). Welche Sprache das
    Testfenster hat, soll die Pruefung nicht wissen muessen."""
    return next((c for c in _boxen42
                 if any(teil in (c.text() or "") for teil in teile)), None)


_force42 = _box42("Kosten ignorieren", "Ignore cost")
_prefer42 = _box42("Vorhandenes verbauen", "Use what you have")
_asset42 = _box42("Assets abziehen", "Subtract assets")
check("b42 alle drei Bau-Schalter sind auffindbar",
      _force42 is not None and _prefer42 is not None and _asset42 is not None)
# UMBENENNUNG: der alte Name beschrieb einen Materialfluss ("Lagerbestand
# immer verwenden"), der Haken entscheidet aber ueber das BAUEN.
# In BEIDEN Sprachen pruefen (seit Sitzung 16 laufen die Beschriftungen
# durch t()): weder der alte deutsche noch ein englischer Materialfluss-Name.
check("b42 der mittlere Haken heisst nicht mehr nach Materialfluss",
      not any(("Lagerbestand immer verwenden" in (c.text() or ""))
              or ("Always use stock" in (c.text() or ""))
              for c in _boxen42))
if _force42 is not None and _prefer42 is not None and _asset42 is not None:
    _bak42 = (_force42.isChecked(), _prefer42.isChecked(),
              _asset42.isChecked())
    try:
        # Ausgangslage: Assets AN, Kosten-ignorieren AUS -> bedienbar.
        # OHNE SIGNALE schalten und die Sperre gezielt nachziehen: an
        # `toggled` haengen weitere Slots, die den ganzen Bauplan neu rechnen.
        _sperre42 = getattr(win, "_bd_pbtn_sperre", None)
        check("b42 die Sperrfunktion ist erreichbar", callable(_sperre42))

        def _setz42(force, assets):
            for _c, _v in ((_force42, force), (_asset42, assets)):
                _c.blockSignals(True)
                _c.setChecked(_v)
                _c.blockSignals(False)
            if callable(_sperre42):
                _sperre42()

        _setz42(False, True)
        check("b42 normal bedienbar: Assets an, Kosten-ignorieren aus",
              _prefer42.isEnabled())
        # 1) "Kosten ignorieren" an -> wirkungslos, also grau.
        _setz42(True, True)
        check("b42 'Kosten ignorieren' an -> mittlerer Haken ist grau",
              not _prefer42.isEnabled())
        check("b42 und der Tooltip sagt WARUM er grau ist",
              "Kosten" in (_prefer42.toolTip() or "")
              or "Ignore costs" in (_prefer42.toolTip() or ""))
        # GEGENPROBE: wieder aus -> wieder frei.
        _setz42(False, True)
        check("b42 Gegenprobe: wieder aus -> wieder bedienbar",
              _prefer42.isEnabled())
        # 2) "Assets abziehen" aus -> ohne Bestand wirkungslos, also grau.
        _setz42(False, False)
        check("b42 'Assets abziehen' aus -> mittlerer Haken ist grau",
              not _prefer42.isEnabled())
        check("b42 und der Tooltip nennt den Bestand als Grund",
              "Bestand" in (_prefer42.toolTip() or "")
              or "stock" in (_prefer42.toolTip() or "").lower())
        _setz42(False, True)
        check("b42 Gegenprobe: Assets wieder an -> wieder bedienbar",
              _prefer42.isEnabled())
    finally:
        for _c42, _v42 in ((_force42, _bak42[0]), (_prefer42, _bak42[1]),
                           (_asset42, _bak42[2])):
            _c42.blockSignals(True)
            _c42.setChecked(_v42)
            _c42.blockSignals(False)


# ---------------------------------------------------------------- (b43)
# EINKAUFSLISTE IN DER AUFSCHLUESSELUNG (Nutzer, Sitzung 14: "die
# gesammtkosten der einkaufsliste und pro stueck, ich will aber jita Sell
# preis sehen"). Ihm war aufgefallen, dass dort "nirgendwo die einkaufsliste
# mitgerechnet oder angezeigt wird".
#
# WARUM DIE ZAHL FEHLTE UND WARUM SIE ZAEHLT: "Material" laesst weg, was aus
# eigenem Bestand kommt; "Baukosten gesamt" rechnet diesen Bestand zu
# Ersatzkosten mit. Keine der beiden sagt, was der Nutzer JETZT ausgeben
# muss. Bei ihm sanken die Materialkosten um 250 Mio, waehrend der Bestand um
# 240 Mio stieg - in der Summe fast unsichtbar. Sein Gegencheck mit Janice:
# 1'297 Mio fuer die Einkaufsliste gegen 1'835 Mio in der Material-Zeile.
_lbl43 = [l.text() for l in _dlg.findChildren(QLabel)] if _dlg is not None else []
# Zweisprachig (Sitzung 16): die Beschriftung laeuft durch t().
check("b43 die Aufschluesselung nennt die Einkaufsliste",
      any("Einkaufsliste (Jita Sell)" in (t or "") or "Shopping list (Jita sell)" in (t or "")
          for t in _lbl43))
check("b43 und dieselbe Summe je Stueck",
      any("Einkaufsliste / St\u00fcck" in (t or "") or "Shopping list / unit" in (t or "")
          for t in _lbl43))
# DIE BEIDEN ZEILEN MUESSEN AUCH EINEN WERT TRAGEN - eine Beschriftung ohne
# Zahl waere wieder ein Etikett, das mehr verspricht als es haelt.
_vals43 = [l for l in (_dlg.findChildren(QLabel) if _dlg is not None else [])
           if (l.toolTip() or "").find("Einkaufsliste") >= 0
           or "spend NOW" in (l.toolTip() or "")
           or "JETZT ausgeben" in (l.toolTip() or "")]
check(f"b43 die Zeilen tragen einen Wert und einen erklaerenden Tooltip "
      f"({len(_vals43)} Beschriftungen/Werte gefunden)",
      len(_vals43) >= 2)
# Die Quelltext-Zusagen (Herkunft der Zahl, Umgang mit fehlenden Preisen)
# stehen in der aa-Suite - dort gibt es `_fn_src`, um sie auf GENAU EINE
# Funktion einzugrenzen, statt "irgendwo in der Datei" zu suchen.


# ---------------------------------------------------------------- (b44)
# BLUEPRINTS-TAB: FUENF SPALTEN STATT FUENFZEHN (Sitzung 16).
#
# NUTZER: "Siehst du wie sauber der Scanner Tab aussieht? So sauber muessen
# wir den My Blueprints Tab gestalten, da hat es viel zu viele Spalten die
# alles ueberladen wirken lassen ... wir begrenzen uns auf 5 Spalten."
# Auswahl nach seiner Vorgabe "die sinnvollsten fuer Profitvorschau":
# Blueprint + Runs + Baukosten/Stk + Profit/Stk + ISK/Std.
#
# AM FENSTER GEPRUEFT, nicht am Quelltext: eine Textprobe koennte nicht
# halten, dass am Ende WIRKLICH fuenf Spalten zu sehen sind - die Liste
# koennte stimmen und ein setColumnHidden trotzdem danebengehen.
_bpt44 = win.bp_table
_sicht44 = [i for i in range(_bpt44.columnCount()) if not _bpt44.isColumnHidden(i)]
_kopf44 = {}
for _i44 in range(_bpt44.columnCount()):
    _h44 = _bpt44.horizontalHeaderItem(_i44)
    _kopf44[_i44] = _h44.text() if _h44 is not None else ""
check(f"b44 genau fuenf Spalten sichtbar (sind {len(_sicht44)})",
      len(_sicht44) == 5)
check("b44 und es sind die fuer die Profitvorschau",
      _sicht44 == [0, 6, 8, 10, 11])
# SPALTE 0 IST NICHT ABWAEHLBAR - ohne Namen ist die Zeile wertlos.
check("b44 Blueprint-Spalte steht nicht im Menue",
      0 not in getattr(win, "_bp_col_acts", {}))
# GEGENPROBE: die versteckten Spalten sind NICHT weg, nur aus. Ohne diese
# Probe wuerde die Pruefung oben auch dann gruen, wenn jemand die zehn
# Spalten ersatzlos geloescht haette - und damit die Daten mit ihnen.
# Sitzung 17: +1 Spalte "Profit/m3" (Nutzer) - weiterhin alle vorhanden.
check(f"b44 alle sechzehn Spalten sind noch da (sind {_bpt44.columnCount()})",
      _bpt44.columnCount() == 16)
check("b44 die neue Spalte Profit/m3 steht im Menue und ist standardmaessig aus",
      15 in getattr(win, "_bp_col_acts", {})
      and not win._bp_col_acts[15].isChecked() and _bpt44.isColumnHidden(15))
eq("b44 ... und traegt den uebersetzten Kopf",
   _bpt44.horizontalHeaderItem(15).text(), _t4("Profit/m\u00b3"))
_akt44 = getattr(win, "_bp_col_acts", {}).get(14)          # Standort
if _akt44 is not None:
    _akt44.setChecked(True)
    check("b44 eine versteckte Spalte laesst sich wieder einblenden",
          not _bpt44.isColumnHidden(14))
    _akt44.setChecked(False)
    check("b44 und wieder ausblenden",
          _bpt44.isColumnHidden(14))
else:
    check("b44 eine versteckte Spalte laesst sich wieder einblenden", False)
    check("b44 und wieder ausblenden", False)


from eve_trader.ui.main_window import MainWindow as _MW45
# ---------------------------------------------------------------- (b45)
# BLUEPRINTS-TAB RECHNET MIT DEM ECHTEN ME - SCHLECHTESTER FALL (Sitzung 16).
#
# NUTZER: "lieber haette ich, dass da der geringere Wert angezeigt wird, dass
# wenn man den Bauplan dann genauer einstellt mit ME, dass man dann positiv
# ueberrascht wird."
#
# Vorher rechnete JEDE Zeile mit der globalen `bau_me` (Vorgabe 10), waehrend
# die ME-Spalte daneben das echte ME aus ESI zeigte. Jetzt baut
# `_bp_me_map` eine Karte Produkt -> ME aus den echten Blaupausen.
_mem45 = _MW45._bp_me_map if hasattr(_MW45, "_bp_me_map") else None
check("b45 es gibt eine ME-Karte fuer den Blueprints-Tab", _mem45 is not None)
if _mem45 is not None:
    _bp2p45 = {100: (500, 1), 101: (501, 1)}
    # MEHRERE KOPIEN DESSELBEN TYPS -> die SCHLECHTESTE zaehlt (Regel 3).
    # Der Mittelwert waere hier 4.67 - genau die Zahl, die im Spiel nicht
    # eintritt, wenn er die schlechte Kopie einlegt.
    _r45 = [{"type_id": 100, "material_efficiency": 10},
            {"type_id": 100, "material_efficiency": 4},
            {"type_id": 100, "material_efficiency": 0}]
    check("b45 bei mehreren Kopien zaehlt die schlechteste ME",
          _mem45(_r45, _bp2p45, 10).get(500) == 0.0)
    # DECKEL GEGEN DIE GLOBALE EINSTELLUNG: keine Zahl darf optimistischer
    # werden als vorher. Blaupause ME 10, global 0 -> es gilt 0.
    check("b45 nie optimistischer als die globale Einstellung",
          _mem45([{"type_id": 100, "material_efficiency": 10}],
                 _bp2p45, 0).get(500) == 0.0)
    # ... und umgekehrt greift das echte ME, wenn es schlechter ist.
    check("b45 das echte ME schlaegt die globale Einstellung, wenn schlechter",
          _mem45([{"type_id": 100, "material_efficiency": 2}],
                 _bp2p45, 10).get(500) == 2.0)
    # ZWEI TYPEN BLEIBEN GETRENNT - sonst faerbte eine schlechte Blaupause
    # alle anderen mit ein.
    _z45 = _mem45([{"type_id": 100, "material_efficiency": 2},
                   {"type_id": 101, "material_efficiency": 7}], _bp2p45, 10)
    check("b45 verschiedene Blaupausen bleiben getrennt",
          _z45.get(500) == 2.0 and _z45.get(501) == 7.0)
    # GEGENPROBEN: nichts Erfundenes und kein Absturz bei Luecken.
    check("b45 ohne bekanntes Produkt entsteht kein Eintrag",
          _mem45([{"type_id": 999, "material_efficiency": 0}], _bp2p45, 10) == {})
    check("b45 leere Eingaben stuerzen nicht ab",
          _mem45(None, None, 10) == {}
          and _mem45([{"type_id": 100}], _bp2p45, 10) == {})
# UND SIE WIRD AUCH BENUTZT: die Karte in die opts zu legen ist der ganze
# Zweck. Auf die ZUWEISUNG geprueft, nicht auf den blossen Namen - eine
# Mutation koennte den Aufruf abklemmen und den Namen stehen lassen
# (die Lehre aus Sitzung 15).
import inspect as _insp45
_src45 = _insp45.getsource(_MW45._reload_my_blueprints)
check("b45 die Karte landet wirklich in den opts",
      'opts["me_map"] = self._bp_me_map(' in _src45)


# ---------------------------------------------------------------- (b46)
# BLUEPRINTS-FILTER: VORGABEN UND DAS ENTFALLENE GRUPPEN-FELD (Sitzung 16).
#
# NUTZER: "standardmaessig haette ich da gerne angehakt nur Endprodukte und
# Erfindbare T2 sowie nur profitabel. Der Dropdown Alle Gruppen kann komplett
# weg. die Kategorie Dropdown reicht voellig."
#
# AM FENSTER GEPRUEFT: eine Textprobe koennte nicht halten, dass die Haken am
# Ende WIRKLICH so stehen - ein spaeteres setChecked wuerde sie umwerfen,
# ohne dass die Zeile im Quelltext sich aendert.
for _nm46, _soll46 in (("bp_cb_end", True), ("bp_cb_invent", True),
                       ("bp_cb_profit", True),
                       ("bp_cb_comp", False), ("bp_cb_react", False)):
    _cb46 = getattr(win, _nm46, None)
    check(f"b46 {_nm46} startet {'angehakt' if _soll46 else 'leer'}",
          _cb46 is not None and _cb46.isChecked() is _soll46)
# DAS GRUPPEN-FELD IST WEG - und zwar wirklich, nicht nur unsichtbar.
check("b46 Gruppen-Dropdown gibt es nicht mehr",
      not hasattr(win, "bp_myb_group"))
check("b46 und auch die Fuell-Methode dazu nicht",
      not hasattr(win, "_reload_bp_group_filter"))
_txt46 = [c.itemText(_i46) for c in win.findChildren(QComboBox)
          for _i46 in range(c.count())]
check("b46 nirgends mehr ein Eintrag \u201eAlle Gruppen\u201c",
      not any("Alle Gruppen" in (x or "") for x in _txt46))
# GEGENPROBE: die Kategorie-Auswahl MUSS bleiben - sonst haette man mit dem
# Gruppenfeld auch den Filter mitgerissen, den der Nutzer behalten wollte.
check("b46 Gegenprobe: die Kategorie-Auswahl steht noch",
      hasattr(win, "bp_myb_cat")
      and any("Alle Kategorien" in (x or "") or "All categories" in (x or "")
              for x in _txt46))


# ---------------------------------------------------------------- (b47)
# SPALTEN-KNOPF AUCH IN SWING TRADE UND REGIONAL TRADING (Sitzung 16).
#
# NUTZER: "Wir haben ja im Industry unter My blueprints diese Columns-
# Dropdown ... koennen wir das auch einfuegen fuer Daytrade, Swing Trade und
# Regional Trade? ... koennten wir diese ausgeblendet lassen aber in so ein
# Dropdown nehmen, damit man sie bei Bedarf einblenden kann?"
#
# GEMESSEN VOR DEM UMBAU (nicht geraten): in Swing (11) und Regional (10)
# war KEINE Spalte versteckt - es war also nie etwas weggenommen worden,
# entgegen der Erinnerung des Nutzers. Nichts wiederherzustellen.
# SWING-VORGABE zweite Runde (Sitzung 16): der Nutzer hat seine eigene
# Auswahl UND Reihenfolge gesetzt ("dann lass den Swingtrade so aussehen").
# `_soll47` ist deshalb die Liste in SICHTBARER Reihenfolge, nicht sortiert.
for _tb47, _acts47, _n47, _soll47, _lbl47 in (
        ("hold_table", "_hold_col_acts", 11, [0, 1, 4, 8, 3, 6], "Swing"),
        ("rg_table", "_rg_col_acts", 10, [0, 1, 2, 5, 4, 8, 9], "Regional")):
    _t47 = getattr(win, _tb47, None)
    _a47 = getattr(win, _acts47, None)
    check(f"b47 {_lbl47}: Spalten-Knopf ist angeschlossen", _a47 is not None)
    if _t47 is None or _a47 is None:
        continue
    _s47 = [_i for _i in range(_t47.columnCount()) if not _t47.isColumnHidden(_i)]
    check(f"b47 {_lbl47}: {len(_soll47)} Spalten sichtbar (sind {len(_s47)})",
          len(_s47) == len(_soll47))
    check(f"b47 {_lbl47}: und es sind die vorgesehenen",
          sorted(_s47) == sorted(_soll47))
    # REIHENFOLGE VON LINKS NACH RECHTS ist Teil der Zusage - sie steht
    # nicht in der Spalten-Reihenfolge, sondern wird per moveSection
    # gesetzt. Ohne diese Pruefung ginge sie still verloren.
    _h47 = _t47.horizontalHeader()
    _lr47 = sorted(_s47, key=_h47.visualIndex)
    check(f"b47 {_lbl47}: Reihenfolge stimmt ({_lr47})", _lr47 == _soll47)
    # GEGENPROBE: die uebrigen sind NICHT geloescht, nur aus. Ohne sie waere
    # die Pruefung oben auch dann gruen, wenn jemand die Spalten entfernt und
    # damit die Daten mitgenommen haette.
    check(f"b47 {_lbl47}: alle {_n47} Spalten sind noch da",
          _t47.columnCount() == _n47)
    check(f"b47 {_lbl47}: Item-Spalte ist nicht abwaehlbar", 0 not in _a47)
    # DER KNOPF MUSS AUCH IN DER OBERFLAECHE HAENGEN. Gemerkt, weil eine
    # Mutation, die genau das abklemmt, BLIND blieb: `_spalten_knopf` blendet
    # die Spalten schon beim Bauen aus - ohne diese Pruefung saehe man fuenf
    # Spalten und haette keinen Weg mehr, die anderen zurueckzuholen.
    _btn47 = getattr(win, {"hold_table": "_hold_spalten_btn",
                           "rg_table": "_rg_spalten_btn"}[_tb47], None)
    check(f"b47 {_lbl47}: der Knopf haengt wirklich im Fenster",
          _btn47 is not None and _btn47.parent() is not None
          and _btn47.window() is win)
    # UND JEDE VERSTECKTE SPALTE MUSS ERREICHBAR SEIN. Sonst waere sie nicht
    # weggeraeumt, sondern verschwunden - genau das, was der Nutzer NICHT
    # wollte ("ausgeblendet lassen aber in so ein Dropdown nehmen").
    _fehlt47 = [_i for _i in range(_t47.columnCount())
                if _t47.isColumnHidden(_i) and _i not in _a47]
    check(f"b47 {_lbl47}: jede versteckte Spalte steht im Menue "
          f"(fehlen: {_fehlt47})", not _fehlt47)
    _v47 = [_i for _i in range(_t47.columnCount()) if _t47.isColumnHidden(_i)]
    if _v47 and _v47[0] in _a47:
        _a47[_v47[0]].setChecked(True)
        check(f"b47 {_lbl47}: versteckte Spalte laesst sich einblenden",
              not _t47.isColumnHidden(_v47[0]))
        _a47[_v47[0]].setChecked(False)
        check(f"b47 {_lbl47}: und wieder ausblenden",
              _t47.isColumnHidden(_v47[0]))
    else:
        check(f"b47 {_lbl47}: versteckte Spalte laesst sich einblenden", False)
        check(f"b47 {_lbl47}: und wieder ausblenden", False)
# ---------------------------------------------------------------- (b48)
# DAYTRADE: SECHS FESTE SPALTEN STATT MODUS-LOGIK (Sitzung 16).
#
# NUTZER: "Dropdown ersetzt die Modus-Logik (immer dieselben 6 Spalten, egal
# welcher Modus)" - und danach "ja bau das so, aktuell sieht Daytrade ja so
# aus. zu viele spalten".
#
# WELCHE SECHS wurde GERECHNET, nicht gewaehlt: die Schnittmenge aller vier
# Modus-Mengen in _DEAL_COLS ist genau {0, 2, 4, 8, 9, 10}. Diese Pruefung
# rechnet sie NEU aus, statt die Zahlen abzuschreiben - so faellt auf, wenn
# jemand _DEAL_COLS aendert und die Vorgabe nicht mitzieht.
# ZWEITE RUNDE, Sitzung 16: der Nutzer hat seine eigenen acht Spalten
# gewaehlt ("mache diese Columns standard eingeschaltet bei Daytrade und
# auch in dieser Reihenfolge von links nach rechts"). Damit gilt NICHT
# mehr die Schnittmenge aller Modi - er arbeitet im Flip und weiss, dass
# "Now (buy)"/"Margin %" nur dort tragen (der Hinweis steht im Menue).
_DAY_SOLL48 = [0, 1, 2, 7, 8, 10, 4, 17]
_dt48 = win.deals_table
_sicht48 = [_i for _i in range(_dt48.columnCount())
            if not _dt48.isColumnHidden(_i)]
check(f"b48 acht Spalten sichtbar (sind {len(_sicht48)})",
      len(_sicht48) == 8)
check("b48 und es sind die vom Nutzer gewaehlten",
      sorted(_sicht48) == sorted(_DAY_SOLL48))
# DIE REIHENFOLGE IST TEIL DER ZUSAGE. Sie steht NICHT in der Spalten-
# Reihenfolge der Tabelle, sondern wird per moveSection gesetzt - ohne
# diese Pruefung koennte sie still verloren gehen (der Deals-Header wird
# nirgends gespeichert).
_hdr48 = _dt48.horizontalHeader()
_lr48 = sorted(_sicht48, key=_hdr48.visualIndex)
check(f"b48 Reihenfolge von links nach rechts stimmt ({_lr48})",
      _lr48 == _DAY_SOLL48)
check("b48 alle 19 Spalten sind noch da", _dt48.columnCount() == 19)
_a48 = getattr(win, "_deals_col_acts", {})
check("b48 Item-Spalte ist nicht abwaehlbar", 0 not in _a48)
_fehlt48 = [_i for _i in range(_dt48.columnCount())
            if _dt48.isColumnHidden(_i) and _i not in _a48]
check(f"b48 jede versteckte Spalte steht im Menue (fehlen: {_fehlt48})",
      not _fehlt48)
_b48 = getattr(win, "_deals_spalten_btn", None)
check("b48 der Knopf haengt wirklich im Fenster",
      _b48 is not None and _b48.parent() is not None and _b48.window() is win)
# DER KERN DES UMBAUS: die Auswahl muss ein Neuzeichnen UEBERLEBEN. Frueher
# lief bei jedem _render_deals eine Schleife, die je Modus aus- und
# einblendete - sie haette die Wahl des Nutzers nach jedem Scan umgeworfen.
if 6 in _a48:
    _a48[6].setChecked(True)
    win._render_deals([], "drop")
    check("b48 zugeschaltete Spalte ueberlebt das Neuzeichnen",
          not _dt48.isColumnHidden(6))
    _a48[6].setChecked(False)
    win._render_deals([], "flip")
    check("b48 und eine abgewaehlte bleibt weg",
          _dt48.isColumnHidden(6))
else:
    check("b48 zugeschaltete Spalte ueberlebt das Neuzeichnen", False)
    check("b48 und eine abgewaehlte bleibt weg", False)
# GEGENPROBE: die Kopfzeile von Spalte 4 wird WEITER je Modus umbenannt -
# sie ist in jedem Modus die Entscheidungszahl, nur unter anderem Namen.
# Ohne diese Probe koennte man die Modus-Logik komplett herausreissen und
# der Nutzer saehe in "Schnaeppchen" die Beschriftung von "Flip".
win._render_deals([], "drop")
_k_drop48 = _dt48.horizontalHeaderItem(4).text()
win._render_deals([], "flip")
_k_flip48 = _dt48.horizontalHeaderItem(4).text()
check(f"b48 Kopf von Spalte 4 folgt dem Modus ({_k_drop48} / {_k_flip48})",
      _k_drop48 != _k_flip48
      and _k_drop48 == type(win)._DEV_LABEL["drop"]
      and _k_flip48 == type(win)._DEV_LABEL["flip"])


# ---------------------------------------------------------------- (b49)
# BAUPLAN NIMMT ME/TE AUS DEN ECHTEN BLAUPAUSEN (Sitzung 16).
#
# NUTZER: "Ich habe festgestellt, dass wir im Bauplan nicht alle meine
# Blueprints traecken ... da ist es teilweise so eingestellt, dass wir einfach
# von voll geforschten Blueprints ausgehen. Jetzt habe ich aber gemerkt, dass
# man nicht immer alle T1-Huellen voll ausgeforscht hat, deswegen hatte ich
# jetzt zu wenig Material eingekauft gehabt."
#
# Vorher kam das ME fuer Komponenten/Huellen/Fuel/Tools NUR aus vier
# Drehfeldern (Vorgabe 10 %/20 % = voll ausgeforscht). Jetzt gewinnt die
# echte, SCHLECHTESTE eigene Kopie je Bauteil (Regel 3).
class _FakeRec49:
    product_to_bp = {777: (7770, 1, 1)}


_alt_rec49 = getattr(win, "_bd_recipes", None)
_alt_cache49 = getattr(win, "_bd_owned_bp_cache", None)
_alt_sch49 = win.settings.get("bau_me_aus_esi")
win._bd_recipes = _FakeRec49()
win._bd_owned_bp_cache = [
    {"type_id": 7770, "material_efficiency": 10, "time_efficiency": 20},
    {"type_id": 7770, "material_efficiency": 4, "time_efficiency": 8},
    {"type_id": 7770, "material_efficiency": 7, "time_efficiency": 14}]
# DREI KOPIEN, DIE SCHLECHTESTE ZAEHLT - nicht der Mittelwert (7) und nicht
# die beste (10). Welche Kopie er im Spiel einlegt, weiss das Werkzeug nicht.
check("b49 schlechteste eigene Kopie gewinnt (ME und TE)",
      win._bd_esi_me_te_for_item(777) == (4.0, 8.0))
check("b49 ohne eigene Blaupause gibt es keinen Wert",
      win._bd_esi_me_te_for_item(999) is None)
# DIE SCHLUESSEL-ABBILDUNG. Beim ersten Versuch griff der Schalter NICHT,
# weil _category_key nie "components" liefert, sondern "t1_components",
# "advanced_components", "hybrid_components", ... Ohne diese Pruefung waere
# der Abhak-Schalter fuer Komponenten wirkungslos geblieben.
for _k49 in ("t1_components", "advanced_components", "hybrid_components",
             "capital_components", "advanced_capital_components"):
    check(f"b49 {_k49} gehoert zur Karte Komponenten",
          type(win)._bd_esi_kat_key(_k49) == "components")
for _k49 in ("t1_hulls", "fuel_blocks", "tools"):
    check(f"b49 {_k49} bleibt eigenstaendig",
          type(win)._bd_esi_kat_key(_k49) == _k49)
# DER SCHALTER WIRKT WIRKLICH BIS IN DIE KOSTENRECHNUNG.
win._bd_me_component = 10
win.settings["bau_me_component"] = 10
win.settings["bau_me_aus_esi"] = {}
check("b49 mit ESI schlaegt das echte ME die Kategorie-Annahme",
      win._bau_category_me_map([777], {777: ""}, set(), type_id=1).get(777) == 4.0)
win.settings["bau_me_aus_esi"] = {"components": False}
check("b49 abgeschaltet gilt wieder die Handeingabe",
      win._bau_category_me_map([777], {777: ""}, set(), type_id=1).get(777) == 10)
# GEGENPROBE, DIE TEUER WAERE WENN SIE FEHLT: ohne eigene Blaupause darf die
# Rechnung NICHT auf ME 0 fallen - das kaufte absurd viel Material ein.
win.settings["bau_me_aus_esi"] = {}
win._bd_owned_bp_cache = []
check("b49 ohne Blaupause faengt die Kategorie auf, kein Sturz auf 0",
      win._bau_category_me_map([777], {777: ""}, set(), type_id=1).get(777) == 10)
check("b49 Vorgabe ist AN, solange nichts eingestellt ist",
      win._bd_esi_me_aktiv("t1_hulls") is True)
win._bd_recipes = _alt_rec49
win._bd_owned_bp_cache = _alt_cache49
if _alt_sch49 is None:
    win.settings.pop("bau_me_aus_esi", None)
else:
    win.settings["bau_me_aus_esi"] = _alt_sch49


# ---------------------------------------------------------------- (b50)
# ENDE-ZU-ENDE: SCHLAEGT DAS ECHTE ME BIS IN DIE BAUKOSTEN DURCH?
#
# b49 prueft die Bausteine einzeln. Das reicht NICHT - der Nutzer hat genau
# danach gefragt ("ist das gefaehrlich oder koennte man es besser machen?").
# Die Gefahr ist nicht eine falsche Zahl, sondern eine Aenderung, die STILL
# nicht ankommt: die Kosten blieben, wie sie waren, und niemand merkt es.
# Deshalb hier die GANZE Kette, so wie _bd_recalc sie geht:
#   _bau_category_me_map -> cat_me_map -> _bau_me_maps -> opts["me_map"]
#   -> industry.production_plan -> total_cost
#
# ZWEISTUFIGES REZEPT: Endprodukt 500 <- 10x Komponente 501 <- 1000x Rohstoff
# 502. Nur so wirkt das KOMPONENTEN-ME ueberhaupt; im Ein-Stufen-Rezept der
# uebrigen Suite gibt es gar keine Komponente, an der es haengen koennte.
class _Rec50:
    product_to_bp = {500: (5000, I.MANUFACTURING, 1),
                     501: (5001, I.MANUFACTURING, 1)}
    bp_materials = {(5000, I.MANUFACTURING): [(501, 10)],
                    (5001, I.MANUFACTURING): [(502, 1000)]}
    activity_time = {(5000, I.MANUFACTURING): 60,
                     (5001, I.MANUFACTURING): 60}
    activity_max_runs = {(5000, I.MANUFACTURING): 0,
                         (5001, I.MANUFACTURING): 0}
    reaction_products = set()
    invention_for_bpc = {}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return t in self.product_to_bp


_alt_rec50 = getattr(win, "_bd_recipes", None)
_alt_cache50 = getattr(win, "_bd_owned_bp_cache", None)
_alt_sch50 = win.settings.get("bau_me_aus_esi")
_alt_comp50 = getattr(win, "_bd_me_component", None)


def _kosten50(esi_an, esi_me):
    """Baukosten fuer 1 Stueck, EINMAL komplett durchgerechnet."""
    win._bd_recipes = _Rec50()
    win._bd_owned_bp_cache = ([{"type_id": 5001, "material_efficiency": esi_me,
                                "time_efficiency": 0}] if esi_me is not None
                              else [])
    win.settings["bau_me_aus_esi"] = {"components": bool(esi_an)}
    win._bd_me_component = 10           # Annahme "voll ausgeforscht"
    win.settings["bau_me_component"] = 10
    _ids50 = [500, 501, 502]
    _grp50 = {500: "", 501: "", 502: ""}
    _cat50 = win._bau_category_me_map(_ids50, _grp50, set(), 500)
    _o50 = {"me": 10, "me_map": dict(_cat50), "job_pct": 0,
            "build_reactions": False, "invention": False,
            "force_build": True, "tree_depth": 4, "adjusted_prices": {}}
    _pl50 = I.production_plan(500, 1, {502: 100.0, 501: 1e9, 500: 1e12}.get,
                              _Rec50(), _o50)
    return _pl50["total_cost"], _cat50.get(501)


_k_esi50, _me_esi50 = _kosten50(True, 0)      # eigene Kopie: gar nicht erforscht
_k_hand50, _me_hand50 = _kosten50(False, 0)   # Handeingabe: "voll ausgeforscht"
_k_ohne50, _me_ohne50 = _kosten50(True, None)  # ESI an, aber keine Blaupause da

check(f"b50 ESI an: Komponente rechnet mit ihrem echten ME ({_me_esi50})",
      _me_esi50 == 0.0)
check(f"b50 ESI aus: es gilt die Handeingabe ({_me_hand50})",
      _me_hand50 == 10)
check(f"b50 ohne eigene Blaupause faengt die Handeingabe auf ({_me_ohne50})",
      _me_ohne50 == 10)
# DAS IST DER PUNKT: die Kosten muessen sich WIRKLICH unterscheiden. Wuerde
# die Aenderung still nicht ankommen, waeren beide Zahlen gleich - und genau
# das haette man ohne diese Pruefung nicht gemerkt.
check(f"b50 schlechteres ME kostet mehr ({_k_esi50:.0f} > {_k_hand50:.0f})",
      _k_esi50 > _k_hand50)
# Und zwar in der RICHTIGEN GROESSENORDNUNG - HIER LAG ICH ZUERST DANEBEN
# UND DER TEST HAT ES GEFANGEN: ich hatte 1'000'000 / 900'000 erwartet,
# gemessen wurden 900'000 / 810'000. Beide Zahlen sind um 10 % kleiner, weil
# das ENDPRODUKT-ME (opts["me"] = 10) schon die Komponentenzahl von 10 auf 9
# drueckt - bevor das Komponenten-ME ueberhaupt auf den Rohstoff wirkt.
# Rechnung: 9 Komponenten x 1'000 Rohstoff a 100 ISK = 900'000 (Komponente
# ME 0) gegen 9 x 900 x 100 = 810'000 (Komponente ME 10). Der Unterschied
# ist also genau die 10 % Material, nur auf der richtigen Grundmenge.
check(f"b50 und zwar um genau die 10 % Material ({_k_esi50:.0f} / {_k_hand50:.0f})",
      abs(_k_esi50 - 900_000) < 1 and abs(_k_hand50 - 810_000) < 1)

# UND DIE LETZTE MEILE: b50 rechnet die Kette selbst nach - das beweist
# NICHT, dass `_bd_recalc` die Karte auch wirklich weiterreicht. Eine
# Mutation, die dort `cat_me_map = {}` setzt, blieb zuerst BLIND. Beide Wege
# muessen belegt sein: MIT Struktur laeuft sie durch _bau_me_maps, OHNE
# Struktur direkt in die opts.
import inspect as _insp50
_src50 = _insp50.getsource(type(win)._bd_recalc) \
    if hasattr(type(win), "_bd_recalc") else ""
if not _src50:
    _src50 = open(os.path.join(_ROOT,
                               "eve_trader", "ui", "main_window.py"),
                  encoding="utf-8").read()
# FUEHRENDES LEERZEICHEN IST PFLICHT: weiter unten steht
# `_cat_me_map = self._bau_category_me_map(` (mit Unterstrich) - der Text
# ohne Leerzeichen steckt darin als Teilstring, und die Pruefung blieb
# deshalb gruen, obwohl die Mutation die Stelle zerstoert hatte.
check("b50 die Karte wird im Bauplan wirklich gebaut",
      " cat_me_map = self._bau_category_me_map(" in _src50)
check("b50 ohne Struktur geht sie direkt in die opts",
      'opts["me_map"] = cat_me_map' in _src50)
check("b50 mit Struktur geht sie durch _bau_me_maps",
      "recipes.reaction_products, cat_me_map," in _src50)

win._bd_recipes = _alt_rec50
win._bd_owned_bp_cache = _alt_cache50
if _alt_sch50 is None:
    win.settings.pop("bau_me_aus_esi", None)
else:
    win.settings["bau_me_aus_esi"] = _alt_sch50
if _alt_comp50 is not None:
    win._bd_me_component = _alt_comp50


# ---------------------------------------------------------------- (b51)
# REGIONAL: LEERE ZIELMAERKTE MIT ABSATZ (Nutzer-Idee, Sitzung 16).
#
# NUTZER: "Falls der Zielhub ein Item gar nicht mehr hat, was passiert dann
# mit dem Tool? Eigentlich waere das eine wahre Goldgrube, ein Item was
# Handelsvolumen hat, aber der Markt leer ist. So etwas muss gefunden
# werden!"
#
# GEMESSEN, WARUM ES BISHER NICHT GEFUNDEN WURDE - `hubs.arbitrage` hat zwei
# harte Ausstiege: `if not t: continue` (Item am Ziel unbekannt) und
# `if sell_price <= 0: continue` (keine Sell-Order da). Genau der
# interessante Fall fiel raus, BEVOR die Absatzpruefung begann.
import eve_trader.hubs as _hb51


def _q51(preis, menge):
    return {"sell_min": preis, "sell_qty": menge, "buy_max": preis * 0.9,
            "buy_qty": 10, "sell_orders": [(preis, menge)]}


_quelle51 = {1: _q51(100, 1000), 2: _q51(5000, 50), 3: _q51(20, 100000),
             4: _q51(300, 10)}
_ziel51 = {1: {"sell_min": 200.0, "sell_qty": 50, "buy_max": 150.0, "buy_qty": 10},
           2: {"sell_min": 0.0, "sell_qty": 0, "buy_max": 6000.0, "buy_qty": 40},
           4: {"sell_min": 0.0, "sell_qty": 0, "buy_max": 0.0, "buy_qty": 0}}
# Item 3 kennt das Ziel GAR NICHT - der Fall, der bisher komplett unsichtbar war.
_k51 = _hb51.leere_zielmaerkte(_quelle51, _ziel51, [{"type_id": 1}])
check("b51 Item ohne jeden Eintrag am Ziel wird gefunden", 3 in _k51)
check("b51 leergekauftes Ziel (nur Buy-Orders) wird gefunden", 2 in _k51)
# GEGENPROBE: was am Ziel eine Sell-Order HAT, ist der normale Fall und darf
# hier nicht auftauchen - sonst doppelte Zeilen und falsche Zahlen.
check("b51 Gegenprobe: bereits bewertetes Item bleibt draussen", 1 not in _k51)
check("b51 nach Quell-Wert sortiert (teuerstes zuerst)", _k51[0] == 2)
check("b51 der Deckel greift",
      len(_hb51.leere_zielmaerkte(_quelle51, _ziel51, [], cap=2)) == 2)


def _h51(tage, preis=1000.0):
    return [{"volume": v, "average": (preis if v else 0)} for v in tage]


_T51, _B51 = 0.036, 0.015
_r51 = _hb51.bewerte_leeren_markt(1, 500.0, _h51([10] * 30), _T51, _B51)
check("b51 lebendiger leerer Markt wird zum Treffer", _r51 is not None)
if _r51:
    check("b51 er ist als Schaetzung gekennzeichnet",
          _r51.get("sell_geschaetzt") is True and _r51.get("leerer_markt") is True)
    check("b51 er bringt sein Ziel-Volumen selbst mit",
          _r51.get("target_vol") == 10.0)
    # DER PREIS IST DER DURCHSCHNITT, NICHT DAS HOCH. Ein einziger
    # Ausreisser-Tag darf keine gruene Traum-Marge erzeugen (Regel 3).
    _hi51 = _h51([10] * 29) + [{"volume": 10, "average": 1000.0, "highest": 99999.0}]
    _r51b = _hb51.bewerte_leeren_markt(1, 500.0, _hi51, _T51, _B51)
    check("b51 der Zielpreis ist der Durchschnitt, nicht das Tageshoch",
          _r51b is not None and abs(_r51b["target_sell"] - 1000.0) < 0.01)
# TOTER MARKT: Umsatz vor drei Wochen, seither nichts. Das ist KEINE
# Goldgrube, sondern ein Item, auf dem man sitzen bleibt.
check("b51 toter Markt (7 Tage ohne Umsatz) wird verworfen",
      _hb51.bewerte_leeren_markt(1, 500.0, _h51([10] * 20 + [0] * 10),
                                 _T51, _B51) is None)
check("b51 ohne Gewinn nach Gebuehren wird verworfen",
      _hb51.bewerte_leeren_markt(1, 1000.0, _h51([10] * 30), _T51, _B51) is None)
check("b51 leere Historie stuerzt nicht ab",
      _hb51.bewerte_leeren_markt(1, 500.0, [], _T51, _B51) is None)
# DIE ANZEIGE MUSS DIE SCHAETZUNG KENNZEICHNEN - sonst sieht sie aus wie ein
# abgelesener Preis. Auf die ZUWEISUNG geprueft, nicht auf den Namen.
_srcrg51 = open(os.path.join(_ROOT,
                             "eve_trader", "ui", "main_window.py"),
                encoding="utf-8").read()
check("b51 die Tabelle markiert geschaetzte Zielpreise mit einer Tilde",
      '("~" if d.get("sell_geschaetzt") else "")' in _srcrg51)
check("b51 und der Scan holt die Kandidaten wirklich",
      "hubs.leere_zielmaerkte(so, to, deals, cap=200)" in _srcrg51)


# ---------------------------------------------------------------- (b52)
# HANDELS-CHARAKTERE (Nutzer-Idee, Sitzung 16).
#
# NUTZER: "im Fall von Regional Trading habe ich 2 Charaktere, einer in Jita
# und einer in 4-HWWF. Wenn man da beide Charaktere als Ein- und Verkaeufer
# eintragen koennte, und man nur von diesen 2 Charakteren die Transaktionen
# wertet?"
#
# DER FALL DAHINTER: ein DRITTER Charakter kaufte einmal 2 Stueck zum Fitten
# eines Schiffs - kein Handel. Weil der Ø-Einkauf ueber ALLE Charaktere
# zusammengelegt wird, zog dieser Kauf ihn hoch, und das Order-Update meldete
# Verlust, wo keiner war.
#
# SEINE ZWEITE IDEE ("nur der aktive Charakter") WURDE GEMESSEN UND VERWORFEN:
# der Verkaeufer in 4-HWWF hat nie etwas GEKAUFT. Allein betrachtet haette er
# gar keinen Einstand - die Spalte zeigte ueberall "-" und die Verlust-
# Pruefung waere ganz aus. Es braucht die MENGE, nicht den einen.
_alt52 = win.settings.get("handels_charaktere")
win.settings.pop("handels_charaktere", None)
# LEER = ALLE. Eine neue Einstellung darf niemandem still die Zahlen
# verschieben - wer nichts einstellt, sieht das Verhalten von vorher.
check("b52 ohne Einstellung zaehlen alle Charaktere",
      win._handels_charaktere() == set())
win.settings["handels_charaktere"] = [11, 22]
check("b52 gesetzte Menge kommt an", win._handels_charaktere() == {11, 22})
# ROBUST GEGEN SCHROTT IN DER EINSTELLUNGSDATEI: sie ist von Hand
# editierbar, und ein Absturz beim Start waere das schlechteste Ergebnis.
win.settings["handels_charaktere"] = ["11", 22, "kaputt", None]
# DIE PRUEFUNG MUSS DEN ABSTURZ SELBST ABFANGEN. Ohne das try riss eine
# Mutation, die den int()-Schutz entfernt, die GANZE Suite mit
# ("ValueError: invalid literal for int()") - und galt damit als BLIND,
# obwohl sie genau den Schaden anrichtete, den diese Zeile pruefen soll.
try:
    _robust52 = win._handels_charaktere() == {11, 22}
except Exception:
    _robust52 = False
check("b52 unbrauchbare Eintraege werden uebergangen, nicht geworfen",
      _robust52)
win.settings["handels_charaktere"] = "gar keine Liste"
check("b52 falscher Typ faellt auf 'alle' zurueck",
      win._handels_charaktere() == set())
# Das Setzen laeuft jetzt ueber die beiden Auswahllisten im Regional-Tab -
# geprueft weiter unten, nachdem die Listen da sind.
# DIE SPALTE IST DA UND DER HAKEN AUCH - sonst gaebe es die Einstellung nur
# in der Datei und niemand koennte sie bedienen.
# DIE BEDIENUNG SITZT IM REGIONAL-TAB, NICHT BEI DEN CHARAKTEREN.
# Zuerst hatte ich eine Haken-Spalte im Charaktere-Tab gebaut; der Nutzer hat
# sie dort nicht gesucht: "Ein und Verkaeufer gehoert zum Regional Tab, wenn
# dann will ich es da waehlen koennen." Sie ist dort wieder WEG - eine
# Einstellung, EINE Stelle.
check("b52 Charaktere-Tabelle hat wieder ihre drei Spalten",
      win.char_table.columnCount() == 3)
check("b52 und keine Haken-Spalte mehr",
      not hasattr(win, "_handels_boxes"))
check("b52 die Auswahl sitzt im Regional-Tab",
      hasattr(win, "rg_buyer") and hasattr(win, "rg_seller"))
# BEIDE LEER = ALLE. Der erste Eintrag ist ein Strich ohne Daten.
check("b52 beide Listen beginnen mit einem leeren Eintrag",
      win.rg_buyer.itemData(0) is None and win.rg_seller.itemData(0) is None)
_bi52, _si52 = win.rg_buyer.count(), win.rg_seller.count()
win.rg_buyer.addItem("T-Kaeufer", 111)
win.rg_seller.addItem("T-Verkaeufer", 222)
win.rg_buyer.setCurrentIndex(_bi52)
win.rg_seller.setCurrentIndex(_si52)
check("b52 die Wahl landet in der Einstellung",
      win._handels_charaktere() == {111, 222})
# DERSELBE CHARAKTER ZWEIMAL: auf die GESPEICHERTE LISTE pruefen, nicht auf
# _handels_charaktere() - das liefert eine Menge, dort verschwindet ein
# Duplikat von selbst und die Pruefung waere blind (genau so passiert).
# In der Einstellungsdatei soll trotzdem [111] stehen und nicht [111, 111]:
# eine Liste mit zwei gleichen Eintraegen verwirrt jeden, der sie spaeter
# liest oder von Hand bearbeitet.
win.rg_seller.addItem("T-Kaeufer", 111)
win.rg_seller.setCurrentIndex(win.rg_seller.count() - 1)
check(f"b52 zweimal derselbe Charakter steht einmal in der Datei "
      f"({win.settings.get('handels_charaktere')})",
      win.settings.get("handels_charaktere") == [111])
win.rg_buyer.setCurrentIndex(0)
win.rg_seller.setCurrentIndex(0)
check("b52 beide zurueck auf leer heisst wieder alle",
      win._handels_charaktere() == set())
# DAS ORDER-UPDATE MUSS DIE MENGE AUCH BENUTZEN. Auf die ZUWEISUNG geprueft:
# eine Mutation koennte den Aufruf stehen lassen und das Ergebnis verwerfen.
_src52 = open(os.path.join(_ROOT,
                           "eve_trader", "ui", "main_window.py"),
              encoding="utf-8").read()
check("b52 das Order-Update fragt die Handels-Menge ab",
      "_hchars9 = self._handels_charaktere()" in _src52)
check("b52 und rechnet den Einstand dann nur aus deren Transaktionen",
      "market.aggregate_holdings(self._handels_transaktionen())" in _src52)
# GEGENPROBE: der alte Rueckfall ueber ALLE Charaktere darf nur noch laufen,
# wenn KEINE Menge gesetzt ist - sonst schliche der Fremdkauf doch wieder ein.
check("b52 der Rueckfall ueber alle laeuft nur ohne gesetzte Menge",
      "if not _hchars9 else {})" in _src52)
if _alt52 is None:
    win.settings.pop("handels_charaktere", None)
else:
    win.settings["handels_charaktere"] = _alt52


# ---------------------------------------------------------------- (b53)
# PROFITS: DAS HANDELS-PAAR ALS EIN BETRIEB (Sitzung 16).
#
# NUTZER: "Kann ich jetzt Einkaeufer-Char in Jita setzen und Verkaeufer-Char
# in Struktur in 4-HWWF? Und das Tool trackt die Preise und Historie sowie
# Gewinne richtig?" - Preise ja, Gewinne NEIN: FIFO lief je Charakter, ein
# Verkauf des einen fand nie ein Kauf-Lot des anderen. In seinen ECHTEN Daten
# gemessen: 26,4 Mrd ISK Umsatz, der so verschwand.
import eve_trader.market as _mk53


def _tx53(cid, tag, tid, menge, preis, kauf):
    return {"character_id": cid, "date": f"2026-07-{tag:02d}T12:00:00Z",
            "type_id": tid, "quantity": menge, "unit_price": preis,
            "is_buy": kauf}


_T53 = [_tx53(1, 1, 1, 100, 1000, True),      # Jita-Charakter kauft
        _tx53(2, 10, 1, 100, 1500, False)]    # 4-HWWF-Charakter verkauft
check("b53 ohne Paar bleibt der Handel unsichtbar (wie bisher)",
      len(_mk53.realized_trades(_T53, 0.036, 0.015)) == 0)
_ev53 = _mk53.realized_trades(_T53, 0.036, 0.015, paar={1, 2})
check("b53 mit Paar entsteht die Gewinnzeile", len(_ev53) == 1)
if _ev53:
    check("b53 und sie nimmt den Einstand des EINKAEUFERS",
          _ev53[0]["buy"] == 1000.0 and _ev53[0]["sell"] == 1500)
# GEGENPROBE, DIE DIE ENTSCHEIDUNG AUS SITZUNG 9 SCHUETZT: ein DRITTER
# Charakter darf sich NICHT mit einmischen. Sonst matchten wieder fremde
# Kaeufe gegen fremde Verkaeufe und der Umsatz blaehte sich auf - genau der
# Grund, warum die Trennung damals eingebaut wurde.
# DER FREMDE KAUF MUSS VOR DEM DES PAARES LIEGEN, sonst prueft die Zeile
# nichts: liegt er danach, greift FIFO ohnehin zuerst auf das Paar-Lot und
# eine Mutation, die ALLE zusammenwirft, faellt nicht auf (genau so
# passiert - sie blieb BLIND). Mit dem fremden Kauf VORNE wuerde eine
# globale Poolung dem Paar-Verkauf das teure Lot unterschieben.
_T53b = [_tx53(3, 1, 1, 50, 9999, True),      # Fremdkauf ZUERST
         _tx53(1, 2, 1, 100, 1000, True),     # dann der Einkaeufer des Paares
         _tx53(2, 10, 1, 100, 1500, False),   # Verkauf des Paares
         _tx53(3, 11, 1, 50, 10, False)]      # eigener Verkauf des Fremden
_ev53b = _mk53.realized_trades(_T53b, 0.036, 0.015, paar={1, 2})
check("b53 ein Charakter ausserhalb des Paares bleibt getrennt",
      len(_ev53b) == 2
      and sorted(round(_e["buy"]) for _e in _ev53b) == [1000, 9999])
# ROBUST: leeres oder unbrauchbares Paar aendert NICHTS. Eine kaputte
# Einstellungsdatei darf die Bilanz nicht still umstellen.
check("b53 leeres Paar aendert nichts",
      len(_mk53.realized_trades(_T53, 0.036, 0.015, paar=None)) == 0
      and len(_mk53.realized_trades(_T53, 0.036, 0.015, paar=[])) == 0)
# ABSTURZ SELBST ABFANGEN: eine Mutation, die den Ziffern-Schutz entfernt,
# riss sonst die GANZE Suite mit ("ValueError: invalid literal for int()")
# und galt als blind - obwohl sie genau den Schaden anrichtete, den diese
# Zeile pruefen soll. Dieselbe Falle wie bei b52.
try:
    _robust53 = len(_mk53.realized_trades(_T53, 0.036, 0.015,
                                          paar=["x", None])) == 0
except Exception:
    _robust53 = False
check("b53 unbrauchbare Eintraege im Paar aendern nichts", _robust53)
# UND DER PROFITS-TAB MUSS ES BENUTZEN. Auf die ZUWEISUNG geprueft.
_srcp53 = open(os.path.join(_ROOT,
                            "eve_trader", "ui", "main_window.py"),
               encoding="utf-8").read()
check("b53 der Profits-Tab reicht das Paar weiter",
      "market.realized_trades(txs, tax, broker, paar=_paar)" in _srcp53)
# NUR BEI "ALLE CHARAKTERE": waehlt der Nutzer einen EINZELNEN, will er
# dessen Zahlen sehen - sonst zeigte die Auswahl etwas anderes an, als sie
# verspricht.
check("b53 bei einem einzelnen Charakter wird NICHT gepaart",
      '_paar = (self._handels_charaktere() if cid in (None, "all") else None)'
      in _srcp53)


# ---------------------------------------------------------------- (b54)
# VERBRAUCH DURCH EINEN ANDEREN PLAN DARF SICH NICHT VERSTECKEN (Sitzung 16).
#
# DER VERLUST: Viator (juenger, reserviert) hatte 13'400 Thulium Hafnite
# gebaut. Vagabond (aelter) sah sie als freien Bestand, der Nutzer baute
# damit Vagabonds Composite - im Spiel blieben 96. Der Viator-Plan zeigte
# weiter 13'400 (max(eingefroren, live)) und "noch zu bauen 4'730". Der
# Warn-Banner oben nannte drei Namen und "..." - Thulium stand dahinter.
#
# ZWEI ZUSAGEN: (1) der Banner nennt ALLE fehlenden Materialien, nicht drei;
# (2) die betroffene ZEILE traegt den Live-Fehlbedarf selbst, in Rot.
# Geprueft am Quelltext des Materialien-Reiters: das Fenster hat im
# Container keinen ESI-Bestand, mit dem sich "live < eingefroren"
# nachstellen liesse. Was sich messen laesst, wird gemessen (unten die
# Reservierungs-Richtung), der Rest auf die ZUWEISUNG.
_srcm54 = open(os.path.join(_ROOT,
                            "eve_trader", "ui", "mw_bauplan_tabs.py"),
               encoding="utf-8").read()
check("b54 der Fehlbedarf-Banner nennt ALLE Namen (kein [:3] mehr)",
      "for _t, *_ in _fehl_auto)" in _srcm54
      and "for _t, *_ in _fehl_auto[:3])" not in _srcm54)
# AUF DIE BEDINGUNG PRUEFEN, NICHT AUF DEN TEXT: eine Mutation, die den
# Zweig mit `if False and ...` totlegt, laesst den Text stehen - die erste
# Fassung dieser Pruefung blieb dabei GRUEN. Die Lehre aus Sitzung 15.
check("b54 die Zeile traegt den Live-Fehlbedarf",
      "_bd_fehl_live" in _srcm54
      and 'LIVE: only {da} on hand' in _srcm54
      and "            if _fl and _fl[0] > 0:" in _srcm54)
check("b54 und faerbt sich rot",
      "status_col = theme.RED" in _srcm54.split("LIVE: only {da} on hand")[1][:400])

# RESERVIERUNG IN BEIDE RICHTUNGEN - funktional, an der geteilten Funktion.
# Das ist der eigentliche Grund des Verlusts: der aeltere Plan sah den
# juengeren nicht. Zwei Plaene, der aeltere hat id 1, der juengere id 2.
from eve_trader.ui.mw_helpers import MainWindowHelpers as _MH54
_set54 = {"bau_saved_plans": [
    {"id": 1, "label": "Vagabond", "reserve": True, "reserve_map": {16674: 5000}},
    {"id": 2, "label": "Viator", "reserve": True, "reserve_map": {16674: 13400}}]}
_vaga54, _lbl54 = _MH54._reserved_by_other_plans(_set54, 1)
check("b54 der AELTERE Plan (Vagabond) sieht die Reservierung des juengeren",
      _vaga54.get(16674) == 13400 and "Viator" in _lbl54)
_viat54, _ = _MH54._reserved_by_other_plans(_set54, 2)
check("b54 und der juengere (Viator) sieht die des aelteren - wie bisher",
      _viat54.get(16674) == 5000)


# ---------------------------------------------------------------- (b55)
# BEDIENELEMENTE TRAGEN EIN SYMBOL (Nutzer, Sitzung 16: "das sind fuer mich
# halt auch so Eyecatcher, um das Auge dahin zu fuehren, wo die wichtigen
# Knoepfe sind").
#
# Beim Emoji-Umbau verloren viele Knoepfe ihr Zeichen, ohne eins aus dem
# eigenen Set zu bekommen - "weg" ist nicht dasselbe wie "ersetzt". Diese
# Pruefung misst am ECHTEN Fenster, nicht am Quelltext.
#
# AUSGENOMMEN sind Klapp-Koepfe: die tragen ihr Zustandszeichen (\u25be/\u25b8)
# selbst und wuerden mit einem zweiten Symbol unruhig.
try:
    _bed55 = ([_b for _b in win.findChildren(QPushButton) if _b.text()]
              + [_c for _c in win.findChildren(QCheckBox) if _c.text()])
    _ohne55 = [_b.text() for _b in _bed55
               if _b.icon().isNull()
               and not _b.text().lstrip().startswith(("\u25be", "\u25b8"))]
    check(f"b55 hoechstens wenige Bedienelemente ohne Symbol "
          f"({len(_ohne55)}: {sorted(_ohne55)[:8]})",
          len(_ohne55) <= 6)
    # UND DER BESTAND STIMMT: mindestens 80 tragen wirklich eins - sonst
    # koennte die Pruefung auch bei einem leeren Fenster gruen sein.
    _mit55 = [_b for _b in _bed55 if not _b.icon().isNull()]
    check(f"b55 die meisten tragen ein Symbol ({len(_mit55)}/{len(_bed55)})",
          len(_mit55) >= 80)
    # DIE WICHTIGEN EINZELN: eine Mengenpruefung mit Spielraum merkt nicht,
    # wenn ausgerechnet der Haupt-Knopf eines Reiters seins verliert.
    # JEDER REITER traegt ein Symbol - auch die, die erst spaeter befuellt
    # werden. Die Order-Reiter bekamen ihres frueher erst beim ersten Laden;
    # bis dahin standen sie nackt da.
    _tabs55 = []
    for _tw55 in win.findChildren(QTabWidget):
        _tabs55 += [_tw55.tabText(_i) for _i in range(_tw55.count())
                    if _tw55.tabIcon(_i).isNull()]
    eq("b55 kein Reiter ohne Symbol", _tabs55, [])
    for _n55 in ("deals_btn", "hold_btn", "rg_go", "b_scan_btn"):
        _w55 = getattr(win, _n55, None)
        check(f"b55 {_n55} traegt ein Symbol",
              _w55 is not None and not _w55.icon().isNull())
except Exception as _e55:                                # pragma: no cover
    _fail.append(f"b55 Symbole: {type(_e55).__name__}: {_e55}")


# ---------------------------------------------------------------- (b56)
# GEMESSEN: gesperrt und offen sehen wirklich verschieden aus (Nutzer,
# Sitzung 16). Ein Waechter auf den Quelltext merkt nicht, wenn beide
# Zeichnungen bei 16 px praktisch gleich aussehen - hier werden die Bilder
# punktweise verglichen.
try:
    from eve_trader.ui import icons as _ic56, theme as _th56
    _a56 = _ic56.icon("lock", farbe=_th56.AMBER).pixmap(16, 16).toImage()
    _b56 = _ic56.icon("lock_open", farbe=_th56.MUTED).pixmap(16, 16).toImage()
    _d56 = sum(1 for _x in range(16) for _y in range(16)
               if _a56.pixel(_x, _y) != _b56.pixel(_x, _y))
    check(f"b56 gesperrt und offen sind unterscheidbar ({_d56}/256)", _d56 >= 40)
except Exception as _e56:                                # pragma: no cover
    _fail.append(f"b56 Schloss-Vergleich: {type(_e56).__name__}: {_e56}")


# ---------------------------------------------------------------- (b57)
# ERSTSTART-DIALOGE STAPELN SICH NICHT (Nutzer, Sitzung 16: "kommt sich das
# nicht in die Quere?").
#
# Beim ersten Start feuern drei Zeitgeber kurz nacheinander: "kein
# Charakter" (250 ms), Rezeptfrage (400 ms), Verlaufsfrage (4000 ms). Jeder
# oeffnet einen MODALEN Dialog - ohne Absprache legt sich der zweite auf
# den ersten. Genau der Moment, in dem ein Fremder das Werkzeug zum ersten
# Mal sieht.
#
# GEPRUEFT OHNE ECHTES FENSTER: ein wirklich modaler Dialog blockiert den
# Testlauf. Stattdessen wird `activeModalWidget` vorgetaeuscht - die
# Entscheidung haengt genau daran.
try:
    from PySide6.QtWidgets import QApplication as _QA57
    _echt57 = _QA57.activeModalWidget
    try:
        _QA57.activeModalWidget = staticmethod(lambda: win)   # Buehne belegt
        check("b57 bei offenem Dialog tritt die Erststart-Frage zurueck",
              win._warte_auf_freie_buehne("_test57", ms=1) is True)
        # UND SIE VERSUCHT ES NICHT EWIG: wer einen Dialog lange offen
        # laesst, soll nicht spaeter unvermittelt ueberfallen werden.
        for _ in range(9):
            win._warte_auf_freie_buehne("_test57b", ms=1, versuche=3)
        check("b57 nach wenigen Versuchen gibt sie auf",
              win._buehne_versuche.get("_test57b", 0) > 3)
        _QA57.activeModalWidget = staticmethod(lambda: None)  # Buehne frei
        check("b57 auf freier Buehne wird nicht mehr gewartet",
              win._warte_auf_freie_buehne("_test57c") is False)
    finally:
        _QA57.activeModalWidget = _echt57
except Exception as _e57:                                # pragma: no cover
    _fail.append(f"b57 Erststart-Dialoge: {type(_e57).__name__}: {_e57}")


# ---------------------------------------------------------------- (b58)
# EINRICHTUNG BEIM ERSTEN START (Nutzer, Sitzung 16: "ein Installations-
# Popup fuer diese wichtigen Daten, ohne es herunterzuladen kommt man nicht
# weiter").
#
# Statt dreier einzelner Dialoge fuehrt EIN blockierendes Fenster durch:
# Charakter verlinken, Rezeptdaten laden, Preisverlaeufe. Am Fenster
# gemessen, nicht am Quelltext.
try:
    from eve_trader.ui.erst_einrichtung import ErstEinrichtung as _EE58
    # auto=False: NICHT die Kette anstossen - sonst laedt der Testlauf
    # 140 MB herunter (erster Versuch hing genau daran).
    _e58 = _EE58(win, auto=False)
    check("b58 alle drei Schritte sind da",
          bool(_e58.s1.titel.text() and _e58.s2.titel.text()
               and _e58.s3.titel.text()))
    # DER START-KNOPF IST GESPERRT, solange nichts erledigt ist - das ist
    # der Kern der Zusage ("ohne Download kommt man nicht weiter").
    check("b58 Starten ist gesperrt, bevor etwas erledigt ist",
          not _e58.weiter_btn.isEnabled())
    # KEIN SCHLIESSEN-KREUZ: der Weg hinaus ist "Beenden".
    from PySide6.QtCore import Qt as _Qt58
    check("b58 kein Schliessen-Kreuz",
          not bool(_e58.windowFlags() & _Qt58.WindowCloseButtonHint))
    check("b58 es gibt einen Weg hinaus", _e58.beenden_btn.isEnabled())
    # ESC DARF NICHT HEIMLICH DURCHLASSEN (Regel 3 andersherum: der Nutzer
    # soll nicht versehentlich in einem leeren Werkzeug landen).
    _e58.reject()
    check("b58 Esc laesst nicht durch, solange nichts erledigt ist",
          _e58.isVisible() or not _e58.result())
    # UND WENN ALLES STEHT, geht es weiter.
    _e58._fertig_machen()
    check("b58 nach Abschluss ist Starten frei", _e58.weiter_btn.isEnabled())
    # (b66) FORTSCHRITT IN DREI ZUSTAENDEN (Sitzung 17, Nutzer: "bleibt bei
    # 0% und ploppt dann auf 100%"): Prozent, Groesse unbekannt (Laufband mit
    # MB), Entpacken (Laufband mit Text). Am Fenster gemessen.
    _s66 = _e58.s2
    _s66.fortschritt(50, 140)
    check("b66 bekannte Groesse: Prozent-Balken",
          _s66.balken.maximum() == 140 and _s66.balken.value() == 50
          and "140" in _s66.zeile.text())
    _s66.fortschritt(7, 0)
    check("b66 unbekannte Groesse: Laufband mit MB-Zahl statt stumm 0 %",
          _s66.balken.maximum() == 0 and "7" in _s66.zeile.text())
    _s66.fortschritt(-1, 0)
    check("b66 Entpacken/Einlesen: eigene Anzeige, nicht stumm 100 %",
          _s66.balken.maximum() == 0
          and _s66.zeile.text() == _t4("Unpacking and importing \u2026"))
    _e58.deleteLater()
except Exception as _e58f:                               # pragma: no cover
    _fail.append(f"b58 Einrichtung: {type(_e58f).__name__}: {_e58f}")


# ---------------------------------------------------------------- (b61)
# REGIONAL: DIE PREISSPALTEN SAGEN, WOMIT GERECHNET WIRD (Sitzung 17, Nutzer:
# "im regional trading tab ist die column Buy(source) ... da muesste Sell
# source und Sell Destination sein"). Gemessen: die Rechnung nahm LAENGST die
# Sell-Orders beider Maerkte - falsch war das ETIKETT. Und bei "Immediate to
# buy order" rechnete der Gewinn gegen das Kaufgebot am Ziel, waehrend Spalte 2
# den Sell-Preis zeigte. FUNKTIONAL: echte Rechnung, echte Tabelle.
try:
    from eve_trader import hubs as _h61
    import eve_trader.ui.main_window as _mw61
    _src61 = {34: {"sell_min": 100.0, "buy_max": 50.0, "buy_qty": 0, "sell_qty": 10,
                   "sell_orders": [(100.0, 5), (110.0, 5)]}}
    _tgt61 = {34: {"sell_min": 200.0, "buy_max": 150.0, "buy_qty": 10, "sell_qty": 3}}
    _st61 = {"sales_tax_pct": 0.0, "broker_fee_pct": 0.0}
    _alt61 = getattr(win, "_arb_modus", None)
    eq("b61 Spalte 1 heisst Sell (source)",
       win.rg_table.horizontalHeaderItem(1).text(), _t4("Sell (source)"))
    for _m61, _kopf61, _preis61 in (("relist", "Sell (destination)", 200.0),
                                    ("instant", "Buy order (destination)", 150.0)):
        _d61 = _h61.arbitrage(_src61, _tgt61, _st61, {}, sell_mode=_m61)
        win._arb_modus = _m61
        win._render_arbitrage(_d61)
        _app.processEvents()
        eq(f"b61 {_m61}: Spalte 2 heisst nach der Verkaufsart",
           win.rg_table.horizontalHeaderItem(2).text(), _t4(_kopf61))
        _z61 = win.rg_table.item(0, 2)
        eq(f"b61 {_m61}: Spalte 2 zeigt den Preis, gegen den gerechnet wurde",
           _z61.text() if _z61 is not None else None,
           _mw61.isk(_preis61, suffix=False))
        _z61a = win.rg_table.item(0, 1)
        eq(f"b61 {_m61}: Spalte 1 = Schnitt der Sell-Orders der Quelle (105)",
           _z61a.text() if _z61a is not None else None, _mw61.isk(105.0, suffix=False))
    win._arb_modus = _alt61
except Exception as _e61:                                # pragma: no cover
    _fail.append(f"b61 Regional-Spalten: {type(_e61).__name__}: {_e61}")


# ---------------------------------------------------------------- (b63)
# DISCORD-KNOPF UEBER DEM SPENDEN-KNOPF (Nutzer, Sitzung 17: "wenn man
# draufklickt kommt man dahin https://discord.gg/Atuqe6c2Rj"). Am Fenster
# gemessen: Platz in der Seitenleiste und die geoeffnete Adresse.
try:
    from PySide6.QtGui import QDesktopServices as _QDS63
    from eve_trader import config as _cfg63
    _db63 = getattr(win, "discord_btn", None)
    check("b63 der Discord-Knopf existiert", _db63 is not None)
    eq("b63 die Adresse steht an EINER Stelle", _cfg63.DISCORD_URL,
       "https://discord.gg/Atuqe6c2Rj")
    if _db63 is not None:
        # VORSICHTIG ZUGREIFEN: faellt der Knopf aus dem Layout, hat er kein
        # Elternfenster - dann soll eine BENANNTE Pruefung rot werden, nicht
        # der ganze Block abstuerzen.
        _pw63 = _db63.parentWidget()
        _lay63 = _pw63.layout() if _pw63 is not None else None
        _spende63 = [b for b in win.findChildren(QPushButton)
                     if _t4("Donate") in (b.text() or "")]
        check("b63 er sitzt DIREKT ueber dem Spenden-Knopf",
              bool(_spende63) and _lay63 is not None
              and _lay63.indexOf(_spende63[0]) == _lay63.indexOf(_db63) + 1)
        _auf63 = []
        _orig63 = _QDS63.openUrl
        _QDS63.openUrl = staticmethod(lambda u: _auf63.append(u.toString()) or True)
        try:
            _db63.click()
            _app.processEvents()
        finally:
            _QDS63.openUrl = _orig63
        eq("b63 ein Klick oeffnet genau den Discord-Server", _auf63,
           ["https://discord.gg/Atuqe6c2Rj"])
except Exception as _e63:                                # pragma: no cover
    _fail.append(f"b63 Discord-Knopf: {type(_e63).__name__}: {_e63}")


# ---------------------------------------------------------------- (b65)
# ITEM-BILDER SITZEN GANZ IM RAHMEN (Sitzung 17, Nutzer: "die Bilder ... zu
# nahe rangezoomt fuer dessen Rahmen"). Der Bildserver liefert 64 px, wenn
# 48 angefragt werden; ohne Verkleinern zeigte das Label nur die Mitte -
# gemessen: 8 px Beschnitt je Rand. Hier dieselbe Messung als Waechter.
try:
    from PySide6.QtGui import QPixmap as _QPx65, QPainter as _QPt65, QColor as _QC65
    _pm65 = _QPx65(64, 64); _pm65.fill(_QC65("white"))
    _p65 = _QPt65(_pm65)
    _p65.fillRect(0, 0, 64, 6, _QC65("red")); _p65.fillRect(0, 58, 64, 6, _QC65("red"))
    _p65.end()
    _in65 = win._pixmap_im_rahmen(_pm65, 40)
    check("b65 das Bild wird auf die Rahmengroesse verkleinert",
          _in65 is not None and max(_in65.width(), _in65.height()) <= 40)
    _l65 = QLabel(); _l65.setFixedSize(48, 48); _l65.setAlignment(Qt.AlignCenter)
    _l65.setPixmap(_in65)
    _img65 = _l65.grab().toImage()
    _rot65 = [_y for _y in range(48)
              if _img65.pixelColor(24, _y).red() > 200 and _img65.pixelColor(24, _y).green() < 80]
    check(f"b65 der obere UND untere Bildrand bleiben sichtbar (rote Zeilen {_rot65[:2]}..)",
          bool(_rot65) and min(_rot65) < 12 and max(_rot65) > 36)
    _l65.deleteLater()
    _src65 = _src_mw
    check("b65 Plan-Karte und Blaupausen-Kategorie benutzen den Helfer",
          "icon_lbl.setPixmap(self._pixmap_im_rahmen(_pix, 40))" in _src65
          and "icon_lbl.setPixmap(self._pixmap_im_rahmen(_pix, 20))" in _src65)
except Exception as _e65:                                # pragma: no cover
    _fail.append(f"b65 Bild im Rahmen: {type(_e65).__name__}: {_e65}")


# ---------------------------------------------------------------- (b67)
# KAESTCHEN IN BAEUMEN SIND GESTALTET (Sitzung 17, Nutzer-Screenshot vom
# 2. PC: grellweisse Haken-Boxen im Rezept-Baum, auf seinem PC dunkel).
# Den Windows-Fall kann der Container nicht zeichnen - gemessen wird, dass
# UNSER Stylesheet das Kaestchen uebernimmt: Innenflaeche = theme.PANEL2.
# (Vorher im Container #16273b aus der Standard-Palette.)
try:
    from eve_trader.ui import theme as _th67
    from PySide6.QtWidgets import QStyle as _QSt67, QStyleOptionViewItem as _QSO67
    from PySide6.QtWidgets import QTreeWidgetItem as _QTI67
    _tw67 = QTreeWidget(); _tw67.setStyleSheet(_th67.QSS)
    _tw67.setColumnCount(1); _tw67.resize(220, 60)
    _it67 = _QTI67(["Item"]); _it67.setCheckState(0, Qt.Unchecked)
    _tw67.addTopLevelItem(_it67); _tw67.show(); _app.processEvents()
    _r67 = _tw67.visualItemRect(_it67)
    _o67 = _QSO67(); _o67.rect = _r67
    _o67.features |= _QSO67.HasCheckIndicator
    _ir67 = _tw67.style().subElementRect(_QSt67.SE_ItemViewItemCheckIndicator, _o67, _tw67)
    _farbe67 = _tw67.viewport().grab().toImage().pixelColor(_ir67.center()).name()
    eq("b67 das Baum-Kaestchen traegt die Farbe aus theme.PANEL2",
       _farbe67.lower(), _th67.PANEL2.lower())
    _tw67.hide(); _tw67.deleteLater()
except Exception as _e67:                                # pragma: no cover
    _fail.append(f"b67 Baum-Kaestchen: {type(_e67).__name__}: {_e67}")


# ---------------------------------------------------------------- (b68)
# NACH DER EINRICHTUNG LAEDT DER VERLAUF VON SELBST (Sitzung 17, Nutzer-
# Screenshot vom 2. PC: beim ZWEITEN Start "kennt erst 0 von 5'731 Items mit
# Preisverlauf" - obwohl die Einrichtung "laeuft im Hintergrund" versprach.
# Die Frage war waehrend der Einrichtung ausgewichen und kam nie wieder.)
try:
    import eve_trader.ui.main_window as _mw68
    from eve_trader import verlauf_laden as _vl68, config as _cfg68
    _alt68 = (_mw68.store.get_snapshot, _mw68.store.get_scan_region,
              _vl68.abdeckung, _cfg68.save_settings_async)
    _ges68 = dict(win.settings)
    _gest68 = []
    win.starte_verlauf_laden = lambda: _gest68.append(1)
    try:
        _mw68.store.get_scan_region = lambda: 10000002
        _cfg68.save_settings_async = lambda *_a, **_k: None
        # (1) kein Schnappschuss: nichts starten, spaeter erneut schauen
        _mw68.store.get_snapshot = lambda: None
        win._verlauf_nach_einrichtung(versuch=60)      # letzter Versuch: kein Timer
        eq("b68 ohne Markt-Schnappschuss startet nichts", len(_gest68), 0)
        # (2) Schnappschuss, 0 % Verlauf: laden, OHNE zu fragen
        _mw68.store.get_snapshot = lambda: {"34": {}}
        _vl68.abdeckung = lambda _s, _r: (0, 5731)
        win.settings["verlauf_gefragt"] = []
        win._verlauf_nach_einrichtung()
        eq("b68 0 von 5731 mit Verlauf: das Laden startet von selbst", len(_gest68), 1)
        check("b68 ... und die Frage fuer diesen Hub entfaellt danach",
              "10000002" in (win.settings.get("verlauf_gefragt") or []))
        # (3) genug Verlauf: nichts laden
        _vl68.abdeckung = lambda _s, _r: (5000, 5731)
        win._verlauf_nach_einrichtung()
        eq("b68 genug Verlauf: kein zweites Laden", len(_gest68), 1)
    finally:
        (_mw68.store.get_snapshot, _mw68.store.get_scan_region,
         _vl68.abdeckung, _cfg68.save_settings_async) = _alt68
        del win.starte_verlauf_laden
        win.settings.clear(); win.settings.update(_ges68)
    check("b68 die Einrichtung stoesst es an",
          "QTimer.singleShot(3000, self._verlauf_nach_einrichtung)" in _src_mw)
except Exception as _e68:                                # pragma: no cover
    _fail.append(f"b68 Verlauf nach Einrichtung: {type(_e68).__name__}: {_e68}")


# ---------------------------------------------------------------- (b69)
# VERLAUFSLADEN UEBERLEBT DAS SCHLIESSEN, STOPP NUR MIT WARNUNG (Sitzung 17,
# Nutzer: "laeuft es weiter, wenn ich das Programm schliesse ... oder
# bricht es ab und laedt nie wieder?" - vorher: nie wieder. Und "wer
# abbrechen drueckt, soll eine Warnung bekommen" - einen Abbruch gab es
# vorher gar nicht). Ablauf am Fenster, Hintergrundlauf abgefangen.
try:
    import eve_trader.ui.main_window as _mw69
    from eve_trader import verlauf_laden as _vl69, config as _cfg69
    _alt69 = (_mw69.store.get_snapshot, _mw69.store.get_scan_region,
              _vl69.fehlende_items, _cfg69.save_settings_async)
    _ges69 = dict(win.settings)
    _cb69 = {}
    win._run = lambda _w, done, fail_cb=None, **_k: _cb69.update(done=done, fail=fail_cb)
    try:
        _mw69.store.get_snapshot = lambda: {"34": {}}
        _mw69.store.get_scan_region = lambda: 10000002
        _vl69.fehlende_items = lambda _s, _r: [34, 35, 36]
        _cfg69.save_settings_async = lambda *_a, **_k: None
        win.settings["verlauf_offen"] = []
        win._verlauf_laeuft = False
        # (1) Start: Merker gesetzt, Stopp-Knopf sichtbar
        win.starte_verlauf_laden()
        check("b69 ein gestarteter Lauf wird als OFFEN gemerkt",
              "10000002" in win.settings.get("verlauf_offen", []))
        check("b69 ... und der Stopp-Knopf ist sichtbar",
              not win._verlauf_stopp_btn.isHidden())
        # (2) "Programm geschlossen": der Lauf endet nie -> neuer Start setzt fort
        win._verlauf_laeuft = False
        _cb69.clear()
        win._verlauf_fortsetzen()
        check("b69 beim naechsten Start geht der offene Lauf von selbst weiter",
              "done" in _cb69)
        # (3) gedrosselt: Merker bleibt
        _cb69["done"]({"geholt": 1, "leer": 0, "fehler": 0, "gedrosselt": True, "dauer": 1})
        check("b69 gedrosselt: der Merker bleibt fuer den naechsten Start",
              "10000002" in win.settings.get("verlauf_offen", []))
        # (4) fertig: Merker weg
        win._verlauf_laeuft = False
        win.starte_verlauf_laden()
        _cb69["done"]({"geholt": 3, "leer": 0, "fehler": 0, "gedrosselt": False, "dauer": 1})
        check("b69 fertig: der Merker ist weg, der Knopf verschwindet",
              "10000002" not in win.settings.get("verlauf_offen", [])
              and win._verlauf_stopp_btn.isHidden())
        # (5) Stopp mit Warnung
        win._verlauf_laeuft = False
        win.starte_verlauf_laden()
        _warn69 = []
        win._verlauf_abbruch_bestaetigen = lambda: (_warn69.append(1), False)[1]
        win._verlauf_stopp_klick()
        check("b69 Stopp fragt ERST nach (Warnung) - 'Weiterladen' aendert nichts",
              _warn69 == [1] and not win._verlauf_abbruch
              and "10000002" in win.settings.get("verlauf_offen", []))
        win._verlauf_abbruch_bestaetigen = lambda: True
        win._verlauf_stopp_klick()
        check("b69 'Stoppen' bricht ab und loescht den Merker (Nutzer-Entscheid)",
              win._verlauf_abbruch
              and "10000002" not in win.settings.get("verlauf_offen", []))
    finally:
        (_mw69.store.get_snapshot, _mw69.store.get_scan_region,
         _vl69.fehlende_items, _cfg69.save_settings_async) = _alt69
        for _n69 in ("_run", "_verlauf_abbruch_bestaetigen"):
            if _n69 in win.__dict__:
                delattr(win, _n69)
        win._verlauf_laeuft = False
        _tk69 = getattr(win, "_verlauf_ticker", None)
        if _tk69 is not None:
            _tk69.stop()
        win._verlauf_stopp_btn.setVisible(False)
        win.settings.clear(); win.settings.update(_ges69)
except Exception as _e69:                                # pragma: no cover
    _fail.append(f"b69 Verlauf fortsetzen/stoppen: {type(_e69).__name__}: {_e69}")


# ---------------------------------------------------------------- (b70)
# GEFUNDENE STRUKTUREN WERDEN FERTIGE BAU-EINTRAEGE (Sitzung 17, Nutzer:
# "wenn ich da auf ok druecke, waere es doch voll geil wenn mir die Struktur
# eintraege soweit es geht direkt fertiggestellt werden. Die rigs muss ich
# dann selber eintragen"). Rechnung ohne Netz, dann der Ablauf am Fenster.
try:
    import eve_trader.ui.main_window as _mw70
    _funde70 = [
        {"name": "Jita - Bauhalle", "structure_id": 101, "character_id": 7,
         "solar_system_id": 30000142, "type_id": 35825},
        {"name": "Tama - Reaktor", "structure_id": 102, "character_id": 7,
         "solar_system_id": 30002813, "type_id": 35836},
        {"name": "Jita - Markt", "structure_id": 103, "character_id": 7,
         "solar_system_id": 30000142, "type_id": 35832},
        {"name": "Schon da", "structure_id": 104, "character_id": 7,
         "solar_system_id": 30000142, "type_id": 35825},
    ]
    _tn70 = {35825: "Raitaru", 35836: "Tatara", 35832: "Astrahus"}
    _sy70 = {30000142: {"name": "Jita", "security": 0.95},
             30002813: {"name": "Tama", "security": 0.3}}
    _ix70 = {30000142: {"manufacturing": 0.07, "reaction": 0.01},
             30002813: {"manufacturing": 0.03, "reaction": 0.05}}
    _neu70, _weg70 = win._bau_eintraege_aus_funden(
        _funde70, _tn70, _sy70, _ix70, {104}, 0.25, 1000)
    eq("b70 Raitaru und Tatara werden angelegt, der Rest uebersprungen",
       [(e["name"], e["type"]) for e in _neu70],
       [("Jita - Bauhalle", "raitaru"), ("Tama - Reaktor", "tatara")])
    _e70 = _neu70[0]
    eq("b70 der Eintrag ist fertig bis auf die Rigs",
       {k: _e70[k] for k in ("system", "system_id", "security", "rigs",
                              "system_mfg_index", "system_reaction_index",
                              "facility_tax", "link_structure_id", "link_character_id")},
       {"system": "Jita", "system_id": 30000142, "security": 1.0, "rigs": [],
        "system_mfg_index": 0.07, "system_reaction_index": 0.01,
        "facility_tax": 0.25, "link_structure_id": 101, "link_character_id": 7})
    eq("b70 Lowsec bekommt den Lowsec-Faktor (wie im Dialog)", _neu70[1]["security"], 1.9)
    eq("b70 Citadel und Verknuepftes werden mit Grund uebersprungen", _weg70,
       [("Jita - Markt", "not an engineering complex or refinery"),
        ("Schon da", "already linked")])
    # --- Ablauf am Fenster ---
    _alt70 = (_mw70.esi.resolve_names, _mw70.esi.system_info,
              _mw70.esi.system_cost_indices, _mw70.config.save_settings,
              _mw70.QMessageBox.information)
    _bs70 = list(win.settings.get("bau_structures", []) or [])
    _meld70 = []
    try:
        _mw70.esi.resolve_names = lambda ids: {i: _tn70.get(i) for i in ids}
        _mw70.esi.system_info = lambda sid: _sy70.get(sid, {})
        _mw70.esi.system_cost_indices = lambda: _ix70
        _mw70.config.save_settings = lambda *_a, **_k: None
        _mw70.QMessageBox.information = staticmethod(
            lambda *_a, **_k: _meld70.append(_a[1] if len(_a) > 1 else ""))
        win._run = lambda w, done, fail_cb=None, **_k: done(w._fn())
        win.settings["bau_structures"] = []
        # Die Suche traegt den Typnamen schon ein (Hintergrund, s. _bau_pick_structure)
        _mitname70 = [dict(f, type_name=_tn70.get(f["type_id"])) for f in _funde70]
        win._bau_funde_frage = lambda _t: False
        win._bau_funde_anbieten(["Jita - Bauhalle"], _mitname70[:1])
        eq("b70 'Only save as locations' legt nichts an",
           win.settings.get("bau_structures"), [])
        win._bau_funde_frage = lambda _t: True
        _fragetext70 = []
        win._bau_funde_frage = lambda _t: (_fragetext70.append(_t), True)[1]
        # "Schon da" ist GESPEICHERT, aber nicht verknuepft -> wird mit angeboten
        win._bau_funde_anbieten(["Jita - Bauhalle"],
                                _mitname70[:2] + [dict(_mitname70[3], neu=False)]
                                + [_mitname70[2]])
        check("b70 auch schon gespeicherte, unverknuepfte Strukturen werden angeboten, "
              "Citadels nicht",
              bool(_fragetext70) and "Schon da" in _fragetext70[-1]
              and "Jita - Markt" not in _fragetext70[-1])
        eq("b70 'Create entries' legt alle drei Bau-Strukturen fertig an",
           [(e["name"], e["type"], e["link_structure_id"])
            for e in win.settings.get("bau_structures", [])],
           [("Jita - Bauhalle", "raitaru", 101), ("Tama - Reaktor", "tatara", 102),
            ("Schon da", "raitaru", 104)])
        check("b70 ... und sagt, dass die Rigs noch fehlen",
              bool(_meld70) and _meld70[-1] == _t4("Build structures created"))
        # --- die SUCHE selbst: neuer Fund + schon gespeicherte, unverknuepfte ---
        _alt70b = (_mw70.store.list_characters, _mw70.store.list_favorites,
                   _mw70.store.add_favorite, _mw70.esi.structure_location_ids,
                   _mw70.esi.resolve_structure, _mw70.esi.region_of_system)
        _angebot70 = []
        try:
            _mw70.store.list_characters = lambda: [{"character_id": 7}]
            _mw70.store.list_favorites = lambda: [
                {"kind": "structure", "structure_id": 104, "character_id": 7,
                 "name": "Schon da", "region_id": 10000002, "station_id": None}]
            _mw70.store.add_favorite = lambda *_a, **_k: None
            _mw70.esi.structure_location_ids = lambda _c, _ch: {101}
            _mw70.esi.resolve_structure = lambda _c, _ch, _sid: {
                "name": {101: "Jita - Bauhalle", 104: "Schon da"}[_sid],
                "solar_system_id": 30000142, "type_id": 35825}
            _mw70.esi.region_of_system = lambda _s: 10000002
            win.settings["bau_structures"] = []
            win._bau_funde_anbieten = lambda added, funde: _angebot70.append(
                (list(added), [(f["structure_id"], f.get("neu"), f.get("type_name"))
                               for f in funde]))
            win._bau_pick_structure()
            eq("b70 die Suche bietet den neuen UND den schon gespeicherten Fund an",
               _angebot70[-1] if _angebot70 else None,
               (["Jita - Bauhalle"], [(101, True, "Raitaru"), (104, False, "Raitaru")]))
        finally:
            (_mw70.store.list_characters, _mw70.store.list_favorites,
             _mw70.store.add_favorite, _mw70.esi.structure_location_ids,
             _mw70.esi.resolve_structure, _mw70.esi.region_of_system) = _alt70b
            if "_bau_funde_anbieten" in win.__dict__:
                del win._bau_funde_anbieten
    finally:
        (_mw70.esi.resolve_names, _mw70.esi.system_info,
         _mw70.esi.system_cost_indices, _mw70.config.save_settings,
         _mw70.QMessageBox.information) = _alt70
        for _n70 in ("_run", "_bau_funde_frage"):
            if _n70 in win.__dict__:
                delattr(win, _n70)
        win.settings["bau_structures"] = _bs70
        win._reload_structures()
except Exception as _e70:                                # pragma: no cover
    _fail.append(f"b70 Strukturen aus Funden: {type(_e70).__name__}: {_e70}")


# ---------------------------------------------------------------- (b71)
# UPDATE-MELDUNG MIT KNOEPFEN (Sitzung 17, Nutzer: "koennen wir da nicht
# direkt den richtigen Githublink einfuegen? vielleicht noch den link zum
# Discord"). Vorher stand die Adresse nur als Text da.
try:
    from PySide6.QtGui import QDesktopServices as _QDS71
    from eve_trader import config as _cfg71
    _url71 = "https://github.com/PeanutMotor/eve-motor-market/releases/tag/1.0"
    _auf71, _text71 = [], []
    _orig71 = _QDS71.openUrl
    _QDS71.openUrl = staticmethod(lambda u: _auf71.append(u.toString()) or True)
    try:
        for _w71 in ("download", "discord", None):
            win._update_wahl = lambda _t, _w=_w71: (_text71.append(_t), _w)[1]
            win._update_meldung(_url71, "0.1.3", "1.0")
    finally:
        _QDS71.openUrl = _orig71
        if "_update_wahl" in win.__dict__:
            del win._update_wahl
    eq("b71 Download oeffnet die Release-Seite, Discord den Server, Schliessen nichts",
       _auf71, [_url71, _cfg71.DISCORD_URL])
    # AUCH DIE FEHLERMELDUNG hat einen Knopf (Sitzung 17): sie zeigte die
    # Releases-Adresse nur als Text zum Abtippen. ECHTE Methode aufrufen, nur
    # das Fenster ersetzen - sonst prueft der Test seinen eigenen Ersatz.
    _auf71b = []
    _orig71b = _QDS71.openUrl
    _QDS71.openUrl = staticmethod(lambda u: _auf71b.append(u.toString()) or True)
    try:
        for _klick71 in (True, False):
            win._releases_wahl = lambda _t, _k=_klick71: _k
            win._releases_meldung("Test", "https://github.com/x/y/releases")
    finally:
        _QDS71.openUrl = _orig71b
        if "_releases_wahl" in win.__dict__:
            del win._releases_wahl
    check("b71 die Fehlermeldung oeffnet die Releases-Seite nur auf Klick",
          _auf71b == ["https://github.com/x/y/releases"])
    check("b71 der Text nennt beide Versionen",
          bool(_text71) and "0.1.3" in _text71[0] and "1.0" in _text71[0])
except Exception as _e71:                                # pragma: no cover
    _fail.append(f"b71 Update-Meldung: {type(_e71).__name__}: {_e71}")


# ---------------------------------------------------------------- (b72)
# ORDER UPDATE LAEDT BEIM OEFFNEN SELBST (Sitzung 17, Nutzer: "brauchen wir
# den refresh orders button wirklich? kann das nicht automatisch gehen?").
# ABER GEDROSSELT: ein Lauf holt EIN ORDERBUCH JE ARTIKEL - bei jedem
# Tab-Wechsel neu waere ein Sturm auf ESI. Am Fenster gemessen.
try:
    import time as _t72
    _w72 = getattr(win, "_orders_w", None)
    _idx72 = win.tabs.indexOf(_w72) if _w72 is not None else -1
    check("b72 der Order-Update-Tab ist auffindbar", _idx72 >= 0)
    _rufe72 = []
    _hatte72 = "client_id" in win.settings
    _alt72 = (win.settings.get("client_id"), getattr(win, "_ord_geladen_at", 0),
              getattr(win, "_ord_geladen_hub", None))
    win._load_order_mods = lambda: _rufe72.append(1)
    try:
        win.settings["client_id"] = "test"
        win._ord_laeuft = False
        win._ord_geladen_at = 0
        win._ord_geladen_hub = None
        win._on_tab_changed(_idx72)
        eq("b72 beim ersten Oeffnen wird geladen", len(_rufe72), 1)
        # Jetzt frisch geladen (gleicher Hub) -> kein zweiter Lauf
        _hub72 = win._active_hub()[2] or win._active_hub()[1]
        _hub72 = _hub72.get("structure_id") if isinstance(_hub72, dict) else _hub72
        win._ord_geladen_at = _t72.time()
        win._ord_geladen_hub = _hub72
        win._on_tab_changed(_idx72)
        eq("b72 gleich danach NICHT nochmal (kein ESI-Sturm)", len(_rufe72), 1)
        # Hub gewechselt -> neu laden, sonst zeigt der Tab fremde Orders
        win._ord_geladen_hub = -999
        win._on_tab_changed(_idx72)
        eq("b72 nach einem Hub-Wechsel wird neu geladen", len(_rufe72), 2)
        # Aelter als 5 Minuten -> neu laden
        win._ord_geladen_hub = _hub72
        win._ord_geladen_at = _t72.time() - 600
        win._on_tab_changed(_idx72)
        eq("b72 nach 5 Minuten wieder", len(_rufe72), 3)
        # Laeuft gerade -> nicht doppelt starten
        win._ord_laeuft = True
        win._ord_geladen_at = 0
        win._on_tab_changed(_idx72)
        eq("b72 waehrend ein Lauf laeuft: kein zweiter", len(_rufe72), 3)
    finally:
        del win._load_order_mods
        if _hatte72:
            win.settings["client_id"] = _alt72[0]
        else:
            win.settings.pop("client_id", None)
        win._ord_geladen_at, win._ord_geladen_hub = _alt72[1], _alt72[2]
        win._ord_laeuft = False
    # Die Laufsperre MUSS sich nach einem Fehler wieder oeffnen.
    import inspect as _insp72
    _src72 = _insp72.getsource(type(win)._load_order_mods)
    check("b72 ein Fehler gibt die Sperre wieder frei",
          "self._ord_laeuft = False" in _src72
          and "fail_cb=_ord_fehler" in _src72)
    check("b72 der Refresh-Knopf bleibt fuer 'jetzt sofort'",
          "load.clicked.connect(self._load_order_mods)" in _src_mw)
except Exception as _e72:                                # pragma: no cover
    _fail.append(f"b72 Order-Update automatisch: {type(_e72).__name__}: {_e72}")


# ---------------------------------------------------------------- (b73)
# HINWEIS AUF ORDERS AN ANDEREN ORTEN (Sitzung 17, Discord-Meldung: die
# Orders lagen in einem Keepstar, der Hub stand auf Jita - die Liste blieb
# leer OHNE Grund). Der Abruf liefert alle Orders, das Werkzeug filtert die
# fremden weg; jetzt sagt es, wie viele wo liegen.
try:
    import eve_trader.ui.main_window as _mw73
    _alt73 = (_mw73.store.list_characters, _mw73.esi.fetch_character_orders,
              _mw73.esi.resolve_names, _mw73.esi.resolve_structure,
              _mw73.esi.fetch_type_orders, getattr(win, "_active_hub"))
    _cid73 = win.settings.get("client_id")
    try:
        _mw73.store.list_characters = lambda: [{"character_id": 7}]
        # Hub = NPC-Station 60003760 (Jita 4-4)
        win._active_hub = lambda: (10000002, 60003760, None)
        _mw73.esi.fetch_character_orders = lambda _c, _ch: [
            {"type_id": 34, "price": 5.0, "is_buy_order": False, "order_id": 1,
             "volume_remain": 10, "location_id": 60003760},          # am Hub
            {"type_id": 35, "price": 6.0, "is_buy_order": False, "order_id": 2,
             "volume_remain": 5, "location_id": 1234567890123},      # Keepstar
            {"type_id": 36, "price": 7.0, "is_buy_order": True, "order_id": 3,
             "volume_remain": 5, "location_id": 1234567890123},      # Keepstar
            {"type_id": 37, "price": 8.0, "is_buy_order": False, "order_id": 4,
             "volume_remain": 5, "location_id": 60008494},           # Amarr
        ]
        _mw73.esi.resolve_names = lambda ids: {60008494: "Amarr VIII - Emperor Family"}
        _mw73.esi.resolve_structure = lambda _c, _ch, _sid: {"name": "1DQ1-A - Keepstar"}
        _mw73.esi.fetch_type_orders = lambda _t, _s, _r: {"buy": [], "sell": []}
        win.settings["client_id"] = "test"
        win._run = lambda w, done, fail_cb=None, **_k: done(w._fn())
        win._load_order_mods()
        _app.processEvents()
        _txt73 = win.ord_andere.text()
        check("b73 der Hinweis ist sichtbar", not win.ord_andere.isHidden())
        check(f"b73 er nennt die Gesamtzahl der fremden Orders ({_txt73[:40]})",
              "3" in _txt73)
        check("b73 er nennt den Keepstar MIT Anzahl (2) und Amarr (1)",
              "1DQ1-A - Keepstar (2)" in _txt73
              and "Amarr VIII - Emperor Family (1)" in _txt73)
        # Liegen alle Orders am Hub, darf nichts stehen.
        _mw73.esi.fetch_character_orders = lambda _c, _ch: [
            {"type_id": 34, "price": 5.0, "is_buy_order": False, "order_id": 1,
             "volume_remain": 10, "location_id": 60003760}]
        win._load_order_mods()
        _app.processEvents()
        check("b73 ohne fremde Orders verschwindet der Hinweis wieder",
              win.ord_andere.isHidden())
    finally:
        (_mw73.store.list_characters, _mw73.esi.fetch_character_orders,
         _mw73.esi.resolve_names, _mw73.esi.resolve_structure,
         _mw73.esi.fetch_type_orders) = _alt73[:5]
        win._active_hub = _alt73[5]
        if "_run" in win.__dict__:
            del win._run
        if _cid73 is None:
            win.settings.pop("client_id", None)
        else:
            win.settings["client_id"] = _cid73
        win._ord_laeuft = False
except Exception as _e73:                                # pragma: no cover
    _fail.append(f"b73 Orders an anderen Orten: {type(_e73).__name__}: {_e73}")


# ---------------------------------------------------------------- (b74)
# DAS TOOL MERKT SICH DIE EINSTELLUNG DES NUTZERS (Sitzung 17: "alles was er
# setzt und zieht soll beim naechsten Mal wieder so sein"): Hub, Charakter je
# Dropdown, Spaltenbreiten ALLER Tabellen. Am Fenster gemessen.
try:
    _ges74 = dict(win.settings)
    try:
        # --- (1) Spaltenbreiten: ziehen -> merken -> woanders hin -> zurueck
        _reg74 = dict(win._tabellen_register())
        check(f"b74 alle Tabellen werden erfasst ({len(_reg74)} Stueck)",
              len(_reg74) >= 8 and "bp_table" in _reg74)
        _t74 = win.bp_table
        # LEER STARTEN: sonst steht dort noch etwas aus einem frueheren Lauf
        # und die Pruefung waere auch dann gruen, wenn nichts gemerkt wird.
        win.settings["ui_spalten"] = {}
        _t74.setColumnWidth(0, 321)
        win._spalten_merken()
        check("b74 die Breiten landen in den Einstellungen",
              bool((win.settings.get("ui_spalten") or {}).get("bp_table")))
        _t74.setColumnWidth(0, 90)
        win._sized.discard("bp_table")
        win._spalten_wiederherstellen()
        eq("b74 nach dem Neustart steht die Spalte wieder auf 321",
           _t74.columnWidth(0), 321)
        check("b74 ... und _autosize_once ueberschreibt sie nicht mehr",
              "bp_table" in win._sized)
        # --- (2) Charakter-Auswahl je Dropdown
        # ZWEI CHARAKTERE VORTAEUSCHEN: im Testfenster ist sonst nur "All
        # characters" da - dann waere jede Auswahl "all" und die Pruefung
        # gruen, egal was der Code tut.
        import eve_trader.ui.main_window as _mw74
        _altl74 = _mw74.store.list_characters
        try:
            _mw74.store.list_characters = lambda: [
                {"character_id": 111, "character_name": "Alpha"},
                {"character_id": 222, "character_name": "Beta"}]
            win._reload_character_combos()
            _cb74 = win.pf_char
            eq("b74 das Dropdown enthaelt beide Charaktere + Alle",
               _cb74.count(), 3)
            _cb74.setCurrentIndex(2)                 # Beta
            win._char_wahl_merken("pf_char")
            eq("b74 die Charakter-Auswahl wird je Dropdown gemerkt",
               (win.settings.get("ui_char_wahl") or {}).get("pf_char"), 222)
            win._reload_character_combos()
            eq("b74 nach dem Neuaufbau steht derselbe Charakter da",
               win.pf_char.currentData(), 222)
        finally:
            _mw74.store.list_characters = _altl74
            win._reload_character_combos()
        check("b74 alle sieben Charakter-Dropdowns sind eingetragen",
              len(win._CHAR_COMBOS) == 7 and "ord_char" in win._CHAR_COMBOS)
        # --- (3) Hub
        win._hub_merken()
        check("b74 der Hub wird gemerkt", "ui_hub" in win.settings)
        check("b74 gemerkt wird das, was oben ausgewaehlt ist",
              win.settings.get("ui_hub") == win.g_hub.currentData())
    finally:
        win.settings.clear(); win.settings.update(_ges74)
except Exception as _e74:                                # pragma: no cover
    _fail.append(f"b74 Personalisierung: {type(_e74).__name__}: {_e74}")


# ---------------------------------------------------------------- (b75)
# UPDATE-PRUEFUNG BEIM START (Sitzung 17, Nutzer: "damit sich keine Updates
# reinschleichen koennen und sie vergessen den Update-Knopf zu druecken").
# STILL: nur bei einem echten Update ein Fenster - "alles aktuell" und
# Netzfehler bleiben in der Statuszeile, sonst waere jeder Start eine
# Belaestigung. Am Fenster gemessen, ohne Netz.
try:
    import eve_trader.programm_update as _pu75
    import eve_trader.ui.main_window as _mw75
    _alt75 = (_pu75.pruefen, _mw75.QMessageBox.information)
    _fenster75, _meldung75, _rel75 = [], [], []
    try:
        _mw75.QMessageBox.information = staticmethod(
            lambda *_a, **_k: _fenster75.append(_a[1] if len(_a) > 1 else "?"))
        win._update_meldung = lambda url, own, neu, name="x": _meldung75.append(neu)
        win._releases_meldung = lambda text, url: _rel75.append(text)
        win._run = lambda w, done, fail_cb=None, **_k: done(w._fn())
        # (1) aktuell -> beim Start KEIN Fenster
        _pu75.pruefen = lambda _r, _v, holen=None: {
            "neuer": False, "hinweis": "", "version": _v, "url": None}
        win.check_programm_update(still=True)
        _app.processEvents()
        eq("b75 aktuell: beim Start kein Fenster", (_fenster75, _meldung75), ([], []))
        # (2) NEUE Fassung -> Fenster kommt auch beim Start
        _pu75.pruefen = lambda _r, _v, holen=None: {
            "neuer": True, "hinweis": "", "version": "9.9.9",
            "url": "https://github.com/x/y/releases/tag/9.9.9"}
        win.check_programm_update(still=True)
        _app.processEvents()
        eq("b75 neue Fassung: die Update-Meldung erscheint", _meldung75, ["9.9.9"])
        # (3) nicht vergleichbar -> beim Start still
        _pu75.pruefen = lambda _r, _v, holen=None: {
            "neuer": False, "hinweis": "keine Antwort", "version": None, "url": None}
        win.check_programm_update(still=True)
        _app.processEvents()
        eq("b75 Netzproblem: beim Start kein Fenster", _rel75, [])
        # (4) derselbe Fall VON HAND -> Fenster kommt sehr wohl
        win.check_programm_update()
        _app.processEvents()
        check("b75 von Hand meldet sich das Netzproblem weiterhin", bool(_rel75))
    finally:
        _pu75.pruefen, _mw75.QMessageBox.information = _alt75
        for _n75 in ("_update_meldung", "_releases_meldung", "_run"):
            if _n75 in win.__dict__:
                delattr(win, _n75)
    check("b75 der Start stoesst die stille Pruefung an",
          "self.check_programm_update(still=True)" in _src_mw
          and "QTimer.singleShot(12000," in _src_mw)
except Exception as _e75:                                # pragma: no cover
    _fail.append(f"b75 Update-Pruefung beim Start: {type(_e75).__name__}: {_e75}")


# ---------------------------------------------------------------- (b76)
# SORTIERUNG UND FILTER UEBERLEBEN DEN NEUSTART (Sitzung 17, Nutzer: "das
# werden wir sofort machen"). Ergaenzt b74 (Hub, Charakter, Spaltenbreiten).
try:
    from PySide6.QtCore import Qt as _Qt76
    _ges76 = dict(win.settings)
    _alt76 = _bpc76 = None
    try:
        # --- Sortierung
        win.settings["ui_sort"] = {}
        win.bp_table.sortItems(3, _Qt76.DescendingOrder)
        win._sortierung_merken()
        eq("b76 die Sortierung wird gemerkt (Spalte + Richtung)",
           (win.settings.get("ui_sort") or {}).get("bp_table"), [3, 1])
        win.bp_table.sortItems(0, _Qt76.AscendingOrder)
        win._sortierung_wiederherstellen()
        eq("b76 nach dem Neustart sortiert sie wieder wie zuletzt",
           (win.bp_table.horizontalHeader().sortIndicatorSection(),
            int(win.bp_table.horizontalHeader().sortIndicatorOrder().value)), (3, 1))
        # --- Filter
        win.settings["ui_filter"] = {}
        _alt76 = win.bp_cb_profit.isChecked()
        _bpc76 = win.bp_cb_bpc.isChecked()
        win.bp_cb_profit.setChecked(not _alt76)
        win.bp_cb_bpc.setChecked(False)
        win._filter_merken()
        eq("b76 die Filter-Haken werden gemerkt",
           {k: (win.settings.get("ui_filter") or {}).get(k)
            for k in ("bp_cb_profit", "bp_cb_bpc")},
           {"bp_cb_profit": not _alt76, "bp_cb_bpc": False})
        win.bp_cb_profit.setChecked(_alt76)
        win.bp_cb_bpc.setChecked(True)
        win._filter_wiederherstellen()
        eq("b76 nach dem Neustart stehen sie wieder so",
           (win.bp_cb_profit.isChecked(), win.bp_cb_bpc.isChecked()),
           (not _alt76, False))
        # AUCH EIN AUSWAHLFELD (sonst prueft der Test nur Haken - Mutation
        # 649 blieb genau deshalb blind).
        if win.tx_period.count() > 1:
            win.tx_period.setCurrentIndex(1)
            _wahl76 = win.tx_period.currentData()
            win._filter_merken()
            eq("b76 auch Auswahlfelder werden gemerkt",
               (win.settings.get("ui_filter") or {}).get("tx_period"), _wahl76)
            win.tx_period.setCurrentIndex(0)
            win._filter_wiederherstellen()
            eq("b76 und nach dem Neustart wieder gesetzt",
               win.tx_period.currentData(), _wahl76)
        check("b76 gemerkt wird NUR, was eine Ansicht filtert",
              "asset_cb" not in win._FILTER_WIDGETS
              and "stock_scope_cb" not in win._FILTER_WIDGETS
              and "bp_cb_profit" in win._FILTER_WIDGETS)
        check("b76 beim Wiederherstellen laufen keine Signale los",
              "_w.blockSignals(True)" in
              __import__("inspect").getsource(type(win)._filter_wiederherstellen))
    finally:
        win.settings.clear(); win.settings.update(_ges76)
        win._filter_wiederherstellen()
        # DIE HAKEN AUSDRUECKLICH ZURUECKSETZEN (18.09.2026): kannten die
        # Settings vorher kein ui_filter, stellt _filter_wiederherstellen
        # NICHTS zurueck - "profitable only" blieb AUS, closeEvent schrieb
        # das in die Test-Settings, und der naechste Lauf fiel bei b46.
        for _w76, _v76 in ((win.bp_cb_profit, _alt76), (win.bp_cb_bpc, _bpc76)):
            if _v76 is None:
                continue
            try:
                _w76.blockSignals(True)
                _w76.setChecked(_v76)
            finally:
                _w76.blockSignals(False)
        check("b76 Aufraeumen: die Haken stehen wieder wie vorher",
              _alt76 is not None and win.bp_cb_profit.isChecked() is _alt76
              and win.bp_cb_bpc.isChecked() is _bpc76)
except Exception as _e76:                                # pragma: no cover
    _fail.append(f"b76 Sortierung/Filter merken: {type(_e76).__name__}: {_e76}")


# ---------------------------------------------------------------- (b77)
# LEERE LISTEN SAGEN, WARUM SIE LEER SIND (Sitzung 17, Nutzer). ANLASS: ein
# Discord-Nutzer hielt das Werkzeug fuer kaputt, weil die Listen leer waren -
# der Grund stand nur in der kleinen Statuszeile. Am Fenster gemessen.
try:
    from PySide6.QtWidgets import QLabel as _QL77, QWidget as _QW77
    _fund77 = {}
    for _n77 in ("deals_table", "hold_table", "rg_table", "bp_table",
                 "pf_table", "pr_table", "tx_table"):
        _t77 = getattr(win, _n77, None)
        if _t77 is None:
            continue
        _boxen = [w for w in _t77.viewport().findChildren(_QW77)
                  if w.findChildren(_QL77) and w.parent() is _t77.viewport()]
        _fund77[_n77] = _boxen[0] if _boxen else None
    check(f"b77 jede der sieben Listen hat einen Hinweis ({len(_fund77)})",
          all(_b is not None for _b in _fund77.values()) and len(_fund77) == 7)
    _bp77 = _fund77.get("bp_table")
    eq("b77 der Hinweis nennt den Grund",
       [l.text() for l in _bp77.findChildren(_QL77)][0],
       _t4("No blueprints loaded yet"))
    _btn77 = _bp77.findChildren(QPushButton)
    check("b77 und bietet genau den fehlenden Knopf an",
          len(_btn77) == 1 and _btn77[0].text() == _t4("Load blueprints"))
    check("b77 der Knopf traegt ein Symbol (b55 verlangt das)",
          not _btn77[0].icon().isNull())
    # KLICK LOEST DIE RICHTIGE AKTION AUS
    # AM VORBILD-KNOPF LAUSCHEN statt seine Methode zu ersetzen: das ist die
    # Wirkung, die zaehlt - und es loest den echten Ladevorgang nicht aus.
    # SEIT 17.09.2026: das Vorbild ist "Meine Blaupausen laden"
    # (bp_refresh_btn), NICHT der SDE-Download (g_sde_btn) - der fragte bei
    # geladener SDE nur zurueck und tat sonst nichts (Nutzer: "bei Blueprint
    # genauso, keine Wirkung").
    _geklickt77 = []
    _c77 = win.bp_refresh_btn.clicked.connect(lambda *_a: _geklickt77.append(1))
    _lade77 = win._reload_my_blueprints
    win._reload_my_blueprints = lambda *_a, **_k: None
    try:
        _btn77[0].click()
        _app.processEvents()
    finally:
        win.bp_refresh_btn.clicked.disconnect(_c77)
        win._reload_my_blueprints = _lade77
    eq("b77 ein Klick loest denselben Vorgang aus wie der Knopf oben",
       _geklickt77, [1])
    # SICHTBAR NUR SOLANGE LEER
    check("b77 bei leerer Liste ist er sichtbar",
          win.bp_table.rowCount() == 0 and not _bp77.isHidden())
    win.bp_table.setRowCount(1)
    _app.processEvents()
    check("b77 sobald Daten da sind, verschwindet er", _bp77.isHidden())
    win.bp_table.setRowCount(0)
    _app.processEvents()
    check("b77 und kommt zurueck, wenn die Liste wieder leer ist",
          not _bp77.isHidden())
    # OHNE KNOPF: die Transaktionen-Listen nennen den Weg als Satz
    _tx77 = _fund77.get("tx_table")
    check("b77 ohne passenden Knopf steht ein Satz statt eines Knopfes",
          not _tx77.findChildren(QPushButton)
          and any(_t4("Link a character under \u201eCharacters\u201c.") == l.text()
                  for l in _tx77.findChildren(_QL77)))
except Exception as _e77:                                # pragma: no cover
    _fail.append(f"b77 Leer-Hinweise: {type(_e77).__name__}: {_e77}")


# ---------------------------------------------------------------- (b78)
# GEFUEHRTE TOUR (Sitzung 17, Nutzer-Auftrag). NICHT MODAL, damit man
# waehrenddessen einrichten kann ("Charaktere verlinken, Strukturen anlegen").
# Durchgeklickt wird sie hier von vorne bis hinten - ohne Netz, ohne Klicks.
try:
    from eve_trader.ui.tutorial import TutorialFenster as _TF78, schritte as _S78
    for _zweig78 in ("trading", "industry"):
        _st78 = _S78(_zweig78)
        check(f"b78 {_zweig78}: die Tour hat Schritte ({len(_st78)})",
              10 <= len(_st78) <= 30)
        check(f"b78 {_zweig78}: jeder Schritt hat Titel UND Text",
              all(x[1] and x[2] for x in _st78))
        check(f"b78 {_zweig78}: kurze Texte, kein Absatz",
              all(len(x[2]) <= 180 for x in _st78))
    _tut78 = _TF78(win, "trading")
    _app.processEvents()
    eq("b78 die Tour startet beim ersten Schritt", _tut78.zaehler.text(),
       f"1 / {len(_S78('trading'))}")
    check("b78 am Anfang ist Zurueck gesperrt", not _tut78.zurueck_btn.isEnabled())
    _texte78 = []
    for _ in range(len(_S78("trading")) - 1):
        _texte78.append(_tut78.titel.text())
        _tut78.weiter()
        _app.processEvents()
    # Titel duerfen sich wiederholen (z.B. "Strategie und Presets" in allen
    # drei Handels-Tabs) - was zaehlt: die Tour bleibt nicht stehen.
    check("b78 die Tour laeuft wirklich durch alle Schritte",
          len(_texte78) == len(_S78("trading")) - 1
          and len(set(_texte78)) >= len(_texte78) - 4)
    eq("b78 der Zaehler zeigt, wie oft man noch klicken muss",
       _tut78.zaehler.text(),
       f"{len(_S78('trading'))} / {len(_S78('trading'))}")
    eq("b78 der letzte Schritt heisst 'Fertig'", _tut78.weiter_btn.text(),
       _t4("Finish"))
    # ABBRECHEN MUSS DEN RAHMEN ZURUECKNEHMEN
    # RAHMEN LIEGT UEBER dem Element, NICHT in seinem Stylesheet (Nutzer-Fund
    # Sitzung 17: ein border im Stil einer TABELLE vererbt sich auf jede
    # Zelle - die Sell list stand komplett gelb umrandet da).
    _tut78.i = 1
    _tut78.zeigen()
    _app.processEvents()
    check("b78 der aktuelle Schritt hebt sein Element hervor",
          _tut78._rahmen and _tut78._hervor == [win.g_hub])
    check("b78 der Rahmen fasst NICHT ins Stylesheet des Elements",
          "border:2px solid" not in (win.g_hub.styleSheet() or ""))
    # DAS RAHMEN-FENSTER SELBST muss weg sein, nicht bloss die Variable -
    # sonst bliebe ein gelber Rahmen im Bild stehen (Mutation 655 war so
    # zuerst blind).
    _ov78 = list(_tut78._rahmen)
    _tut78.abbrechen()
    _app.processEvents()
    def _weg78(w):
        try:
            return not w.isVisible()
        except RuntimeError:
            return True                 # C++-Objekt abgeraeumt = weg
    check("b78 nach dem Abbrechen ist der Rahmen wieder weg",
          not _tut78._rahmen and not _tut78._blink.isActive()
          and all(_weg78(_o) for _o in _ov78))
    # SEITENLEISTEN-SCHRITTE zeigen auf den EINTRAG, nicht auf die Tabelle.
    _tutn = _TF78(win, "trading")
    _inav = [i for i, st in enumerate(_S78("trading"))
             if str(st[0] or "").startswith("nav:")]
    check(f"b78 die Seitenleisten-Schritte zeigen auf ihren Eintrag "
          f"({len(_inav)})", len(_inav) >= 8)
    _tutn.i = _inav[0]
    _tutn.zeigen()
    _app.processEvents()
    check("b78 und heben genau diesen Eintrag hervor",
          _tutn._hervor == [(getattr(win, "_nav_buttons", {}) or {}).get(
              _S78("trading")[_inav[0]][0][4:])])
    check("b78 der letzte Schritt fuehrt zurueck ins Portfolio",
          _S78("trading")[-1][3] == "portfolio")
    # UND BLINKT NICHTS MEHR (Nutzer, Sitzung 17): am Schluss gibt es nichts
    # zu klicken - ein blinkender Knopf fordert nur dazu auf.
    for _zw78e in ("trading", "industry"):
        eq(f"b78 {_zw78e}: der Schlussschritt hebt nichts mehr hervor",
           _S78(_zw78e)[-1][0], None)
    # DER SCHLUSS DARF NICHT EINFRIEREN (Nutzer-Fund Sitzung 17: "wenn ich
    # auf Finish klicke, friert alles ein"). URSACHE: ab Schritt 9 haengt die
    # Tour AM BAUPLAN; wird der beim letzten Schritt geschlossen, nimmt er
    # sein Kind mit - der Klick lief auf ein abgeraeumtes Objekt.
    _zt78 = __import__("inspect").getsource(_TF78.zeigen)
    check("b78 vor dem Schliessen wird die Tour ans Haupttool umgehaengt",
          "if self.parent() is _d:" in _zt78
          and "self.setParent(self.mw, self.windowFlags())" in _zt78)
    _ab78 = __import__("inspect").getsource(_TF78.abbrechen)
    check("b78 das Nachfolge-Fenster kommt NICHT aus dem Klick heraus",
          "QTimer.singleShot(0, lambda: _mw._tutorial_anderer_zweig" in _ab78)
    # DURCHSPIELEN: Bauplan als Elternfenster, letzter Schritt, dann Finish.
    _di78 = getattr(win, "_bd_dialog", None)
    if _di78 is not None and _di78.isVisible():
        _tf78 = _TF78(win, "industry")
        _alt78z = win._tutorial_anderer_zweig
        win._tutorial_anderer_zweig = lambda *_a: None
        try:
            _tf78.setParent(_di78, _tf78.windowFlags())
            _tf78.show()
            _tf78.i = len(_S78("industry")) - 1
            _tf78.zeigen()
            _app.processEvents()
            check("b78 nach dem Schliessen lebt die Tour noch",
                  _tf78.parent() is win and _tf78.isVisible())
            _tf78.weiter()               # = Finish
            _app.processEvents()
            check("b78 'Finish' laeuft ohne Haenger durch",
                  getattr(win, "_tutorial", "weg") is None)
        finally:
            win._tutorial_anderer_zweig = _alt78z
            _app.processEvents()
    _te78 = _TF78(win, "trading")
    try:
        _te78.i = len(_S78("trading")) - 1
        _te78.zeigen()
        _app.processEvents()
        check("b78 am Schluss laeuft kein Blinken mehr",
              not _te78._rahmen and not _te78._blink.isActive())
    finally:
        _te78.abbrechen()
        _app.processEvents()
    # NACH NAMEN SUCHEN, NICHT NACH POSITION: die Tour waechst (Nutzer hat
    # Strategie- und "Deals laden"-Schritte ergaenzt) - feste Indizes waeren
    # bei jeder Erweiterung rot, ohne dass etwas kaputt ist.
    # EIN SCHRITT KANN MEHRERE ELEMENTE BLINKEN LASSEN (Nutzer, Sitzung 17:
    # "lass beide Dropdowns blinken", "lass auch den Hub mitblinken") - der
    # Name ist dann ein Tupel. Also nach JEDEM Namen einzeln nachschlagen.
    _pos78 = {}
    for _i78, _st78x in enumerate(_S78("trading")):
        _n78 = _st78x[0]
        for _one in ((_n78,) if isinstance(_n78, str) or _n78 is None
                     else tuple(_n78)):
            if _one is not None:
                _pos78.setdefault(_one, _i78)
    # DIE DREI HANDELS-TABS ERKLAEREN JEWEILS STRATEGIE UND "DEALS LADEN"
    # (Nutzer, Sitzung 17). Regional zusaetzlich die zwei Hubs.
    for _need78 in ("d_preset", "deals_btn", "h_preset", "hold_btn",
                    "rg_src", "rg_preset", "rg_go"):
        check(f"b78 der Schritt zu {_need78} ist da", _need78 in _pos78)
    # UND DIE ZUSATZ-ELEMENTE BLINKEN WIRKLICH MIT
    def _namen78(i):
        _n = _S78("trading")[i][0]
        return ((_n,) if isinstance(_n, str) else tuple(_n or ()))
    check("b78 Daytrade: Mode UND Preset blinken",
          set(_namen78(_pos78["d_preset"])) == {"d_mode", "d_preset"})
    check("b78 Daytrade: bei 'Deals laden' blinkt der Hub mit",
          "g_hub" in _namen78(_pos78["deals_btn"]))
    check("b78 Swing: Mode UND Preset blinken",
          set(_namen78(_pos78["h_preset"])) == {"h_mode", "h_preset"})
    check("b78 Swing: bei 'Deals laden' blinkt der Hub mit",
          "g_hub" in _namen78(_pos78["hold_btn"]))
    check("b78 Regional: Kauf- UND Verkaufs-Hub blinken",
          set(_namen78(_pos78["rg_src"])) == {"rg_src", "rg_tgt"})
    check("b78 Regional: es gibt einen Schritt zu Kaeufer und Verkaeufer",
          set(_namen78(_pos78["rg_buyer"])) == {"rg_buyer", "rg_seller"})
    # HIER NICHT: der obere Hub ist im Regional wirklich ohne Wirkung -
    # GEMESSEN: compute_arbitrage liest nur rg_src/rg_tgt.
    check("b78 Regional: bei 'Deals laden' blinkt der obere Hub NICHT mit",
          "g_hub" not in _namen78(_pos78["rg_go"])
          and {"rg_src", "rg_tgt", "rg_buyer", "rg_seller"}
          <= set(_namen78(_pos78["rg_go"])))
    check("b78 und die Regional-Rechnung nimmt wirklich nur die zwei Hubs",
          "src = self.rg_src.currentData()"
          in __import__("inspect").getsource(type(win).compute_arbitrage)
          and "_active_hub"
          not in __import__("inspect").getsource(type(win).compute_arbitrage))
    for _tab78, _pre78, _btn78 in (("deals", "d_preset", "deals_btn"),
                                   ("swing", "h_preset", "hold_btn"),
                                   ("region", "rg_preset", "rg_go")):
        check(f"b78 {_tab78}: erst Reiter, dann Strategie, dann Deals laden",
              _pos78["nav:" + _tab78] < _pos78[_pre78] < _pos78[_btn78])
    check("b78 hervorgehoben wird der einzelne Reiter, nicht die Leiste",
          all(k in _pos78 for k in ("nav:deals", "nav:swing", "nav:region")))
    _tt78 = _TF78(win, "trading")
    try:
        for _erw78 in ("deals", "swing", "region"):
            _k78 = _pos78["nav:" + _erw78]
            _tt78.i = _k78
            _tt78.zeigen()
            _app.processEvents()
            eq(f"b78 der Schritt zu {_erw78} schaltet den Reiter um",
               [k for k, w in win._tab_widget.items()
                if w is win.tabs.currentWidget()], [_erw78])
            check(f"b78 ... und hebt den Reiter {_erw78} hervor",
                  (getattr(win, "_nav_buttons", {}) or {}).get(_erw78)
                  in _tt78._hervor)
    finally:
        _tt78.abbrechen()
        _app.processEvents()
    # BLINKEN
    check("b78 der hervorgehobene Knopf blinkt", _tutn._blink.isActive())
    _s1 = _tutn._rahmen[0].styleSheet()
    _tutn._blinken()
    check("b78 ... und wechselt dabei wirklich sein Aussehen",
          _tutn._rahmen[0].styleSheet() != _s1)
    # ALLE Rahmen eines Schritts muessen mitblinken, nicht nur der erste
    # (Nutzer: "lass beide Dropdowns blinken").
    _tutn.i = _pos78["d_preset"]
    _tutn.zeigen()
    _app.processEvents()
    check(f"b78 ein Schritt kann mehrere Rahmen haben ({len(_tutn._rahmen)})",
          len(_tutn._rahmen) == 2)
    _vor78 = [r.styleSheet() for r in _tutn._rahmen]
    _tutn._blinken()
    check("b78 und ALLE davon blinken mit",
          all(r.styleSheet() != v for r, v in zip(_tutn._rahmen, _vor78)))
    _tutn.abbrechen()
    _app.processEvents()
    # WARTEN AUF EINE AKTION: der Bauplan-Schritt sperrt "Weiter".
    _tut78c = _TF78(win, "industry")
    _idx78 = [i for i, st in enumerate(_S78("industry"))
              if st[4] == "bauplan_offen"]
    check("b78 genau EIN Schritt wartet auf eine Aktion", len(_idx78) == 1)
    _alt78d = getattr(win, "_bd_dialog", None)
    try:
        win._bd_dialog = None
        _tut78c.i = _idx78[0]
        _tut78c.zeigen()
        _app.processEvents()
        check("b78 ohne offenen Bauplan bleibt 'Weiter' gesperrt",
              not _tut78c.weiter_btn.isEnabled() and _tut78c._warte.isActive())
        class _Fake78:
            def isVisible(self):
                return True

            def raise_(self):
                pass                      # die Tour holt den Bauplan nach vorn

            def activateWindow(self):
                pass
        win._bd_dialog = _Fake78()
        _tut78c._warte_pruefen()
        _app.processEvents()
        check("b78 sobald einer offen ist, geht es von selbst weiter",
              _tut78c.weiter_btn.isEnabled() and not _tut78c._warte.isActive())
        # UND DAS BLINKEN HOERT AUF (Nutzer, Sitzung 17): ein zweiter Klick
        # auf "New build plan" oeffnet das Auswahlfenster erneut und schiebt
        # alles wieder nach hinten.
        check("b78 danach blinkt 'Neuer Bauplan' nicht mehr",
              not _tut78c._rahmen and not _tut78c._blink.isActive()
              and _tut78c._fertig_kein_blinken)
        _tut78c._nachfuehren()
        _app.processEvents()
        check("b78 und das Nachfuehren bringt es nicht zurueck",
              not _tut78c._rahmen)
    finally:
        win._bd_dialog = _alt78d
        _tut78c.abbrechen()
        _app.processEvents()
    # KURSVERLAUF WIRD WIRKLICH GEZEICHNET (Nutzer, Sitzung 17: "es steht
    # zwar im Item-Dropdown, aber es soll geladen werden"). Vorher kehrte die
    # Funktion zurueck, sobald irgendetwas ausgewaehlt war.
    _plots78 = []
    _altp78 = win._plot_history
    win._plot_history = lambda *_a, **_k: _plots78.append(1)
    _mk78 = win.mk_item.count()
    win.mk_item.addItem("Testitem", 34)
    win.mk_item.setCurrentIndex(win.mk_item.findData(34))
    try:
        win._tutorial_kursverlauf_beispiel()      # mit schon gewaehltem Item
        _app.processEvents()
        check("b78 der Kursverlauf wird auch bei schon gewaehltem Item gezeichnet",
              len(_plots78) >= 1)
    finally:
        win._plot_history = _altp78
        win.mk_item.setCurrentIndex(-1 if _mk78 == 0 else 0)
        win.mk_item.removeItem(win.mk_item.findData(34))
    # JEDER SCHRITT MUSS SEIN ELEMENT FINDEN (Nutzer, Sitzung 17: "schau
    # drauf, dass das Tutorial-Fenster auch da immer am richtigen Ort ist").
    # Fand ein Schritt seins nicht, landete das Fenster mittig - und im
    # Bauplan-Schritt zeigte der Text auf einen Knopf, der gar nicht blinkte.
    for _zw78 in ("trading", "industry"):
        _tp78 = _TF78(win, _zw78)
        try:
            # JEDEN NAMEN EINZELN pruefen: bei einem Tupel liefert _widget
            # eine LISTE - die ist nie None, und die Pruefung war blind
            # (Mutation 663 fiel genau darauf herein).
            _fehlt78 = []
            for _i78f, _st78f in enumerate(_S78(_zw78)):
                _n78f = _st78f[0]
                for _one78 in ((_n78f,) if isinstance(_n78f, str)
                               else tuple(_n78f or ())):
                    # AUSNAHME: `_picker_open_btn` entsteht erst, wenn das
                    # Auswahlfenster offen ist. Der Schritt meint ihn
                    # trotzdem - `_nachfuehren` holt ihn nach, sobald er da
                    # ist. Deshalb hier nicht als Fehler zaehlen.
                    # NUR VORUEBERGEHEND VORHANDEN: der "Open"-Knopf gibt
                    # es erst mit offenem Auswahlfenster, die bd:-Anker nur
                    # mit offenem Bauplan. `_nachfuehren` holt beides nach.
                    if _one78 in ("_picker_open_btn", "_bd_karte_bauenkaufen",
                                  "_bd_karte_tiefe",
                                  "_bd_save_btn", "_bd_frozen_btn") \
                            or str(_one78).startswith("bd:"):
                        continue
                    if _one78 and _tp78._widget(_one78) is None:
                        _fehlt78.append(f"{_i78f + 1}:{_one78}")
            eq(f"b78 {_zw78}: jeder Schritt findet sein Element", _fehlt78, [])
        finally:
            _tp78.abbrechen()
            _app.processEvents()
    # JEDER SCHRITT, DER AUF EIN ELEMENT IM HAUPTFENSTER ZEIGT, MUSS AUCH
    # DORTHIN SCHALTEN (Nutzer-Fund Sitzung 17: "Industrie-Tab blinkt, aber
    # wir werden nicht dahin gefuehrt"). Im Industriezweig fehlte das bei
    # ALLEN Schritten.
    _ind78 = _S78("industry")           # EINMAL holen: schritte() baut jedes
    for _i78i, _st78i in enumerate(_ind78):   # Mal eine NEUE Liste (is faellt sonst durch)
        _n78i = _st78i[0]
        _alle78i = ((_n78i,) if isinstance(_n78i, str) else tuple(_n78i or ()))
        # Der SCHLUSS-Schritt fuehrt bewusst ins Portfolio zurueck (Nutzer).
        if _i78i == len(_ind78) - 1:
            eq("b78 der letzte Industrie-Schritt fuehrt ins Portfolio",
               _st78i[3], "portfolio")
            continue
        if any(str(x).startswith(("nav:", "bau:")) or x == "_bau_newplan_btn"
               for x in _alle78i):
            eq(f"b78 industry Schritt {_i78i + 1} schaltet in den Bauen-Tab",
               _st78i[3], "build")
    # UND SIE OEFFNET AUCH DIE UNTERSEITE DES BAUEN-TABS (Nutzer-Fund
    # Sitzung 17: "3/15 soll mich in den Struktur-Tab hineinfuehren ... kein
    # Tutorial fuehrt mich in den Tab hinein"). Der Bauen-Tab hat vier eigene
    # Seiten - der Reiterwechsel allein zeigte die falsche.
    _tp78s = _TF78(win, "industry")
    try:
        for _seite78, _titel78 in ((3, "Structures first"), (0, "Scanner"),
                                   (1, "My blueprints")):
            _i78s = [i for i, st in enumerate(_S78("industry"))
                     if f"bau:{_seite78}" in
                     ((st[0],) if isinstance(st[0], str) else tuple(st[0] or ()))]
            if not _i78s:
                continue
            # VORHER WOANDERS HIN: sonst ist die Pruefung zufaellig gruen,
            # weil die Seite schon stimmte (Mutation blieb so blind).
            win.b_stack.setCurrentIndex(2 if _seite78 != 2 else 0)
            _tp78s.i = _i78s[0]
            _tp78s.zeigen()
            _app.processEvents()
            eq(f"b78 der Schritt '{_titel78}' oeffnet Seite {_seite78}",
               win.b_stack.currentIndex(), _seite78)
    finally:
        _tp78s.abbrechen()
        _app.processEvents()
    # Ein Schritt kann mehrere Elemente haben - also im TUPEL suchen.
    def _hat78(st, name):
        _n = st[0]
        return name in ((_n,) if isinstance(_n, str) else tuple(_n or ()))
    _iS = [i for i, st in enumerate(_S78("industry")) if _hat78(st, "bau:3")]
    _iC = [i for i, st in enumerate(_S78("industry")) if _hat78(st, "bau:0")]
    # BEIDE "Load blueprints"-KNOEPFE BLINKEN (Nutzer, Sitzung 17): der oben
    # laedt die REZEPTDATEN, der auf der Seite holt SEINE Blaupausen aus EVE.
    # Zwei Knoepfe mit demselben Text - genau deshalb muessen beide leuchten.
    _bp78 = [st for st in _S78("industry")
             if "bau:1" in ((st[0],) if isinstance(st[0], str)
                            else tuple(st[0] or ()))]
    # DIE DREI SCHRITTE IM BAUPLAN ZEIGEN AUF ECHTE ELEMENTE (Nutzer-Fund
    # Sitzung 17: "Build or buy haengt irgendwo", "14/15 ist nicht am
    # richtigen Freeze-Ort"). Vorher hingen beide nur am Fenster.
    _names78 = [st[0] for st in _S78("industry")]
    # DAS FENSTER DARF KEIN ELEMENT DES SCHRITTS VERDECKEN (Nutzer, Sitzung
    # 17: "das Tutorial verdeckt den Einkaufswagen-Knopf"). Es stellt sich
    # deshalb unter das UNTERSTE hervorgehobene Element.
    check("b78 der Materialien-Schritt laesst 'Einkaufsliste' mitblinken",
          any("_bd_mat_copy_btn" in (n if isinstance(n, tuple) else (n,))
              for n in [st[0] for st in _S78("industry")]))
    check("b78 platziert wird unter dem UNTERSTEN Element",
          "max(_sicht, key=lambda w: w.mapToGlobal(" in
          open("eve_trader/ui/tutorial.py", encoding="utf-8").read())
    # NACHGEZOGEN 16.09.2026: der Schritt traegt jetzt REITER + Karte, damit
    # "Back" aus dem Invention-Schritt wieder in der Rezeptstruktur landet.
    check("b78 'Build or buy' zeigt auf seine Karte",
          any(isinstance(n, tuple) and "_bd_karte_bauenkaufen" in n
              for n in _names78))
    # BEIDE KARTEN (Nutzer 18.09.2026): der Text nennt "Production depth",
    # also blinkt die Karte mit - und sie existiert im Bauplan-Fenster.
    check("b78 'Build or buy' laesst auch 'Production depth' blinken",
          any(isinstance(n, tuple) and "_bd_karte_bauenkaufen" in n
              and "_bd_karte_tiefe" in n for n in _names78))
    check("b78 die Karte 'Production depth' ist am Fenster gemerkt",
          "self._bd_karte_tiefe = self._collapsible(" in open(
              "eve_trader/ui/mw_bauplan_fenster.py", encoding="utf-8").read())
    check("b78 und stellt dabei den Rezeptstruktur-Reiter selbst her",
          any(isinstance(n, tuple) and "_bd_karte_bauenkaufen" in n
              and any(str(x).startswith("bd:tab:") for x in n)
              for n in _names78))
    check("b78 'Speichern und einfrieren' zeigt auf BEIDE Knoepfe",
          any({"_bd_save_btn", "_bd_frozen_btn"} <= set(n)
              for n in _names78 if isinstance(n, tuple)))
    check("b78 der letzte Schritt macht den Bauplan zu",
          "_d.close()" in __import__("inspect").getsource(
              _TF78.zeigen))
    check("b78 der Blaupausen-Schritt laesst BEIDE Knoepfe blinken",
          _bp78 and {"bp_refresh_btn", "g_sde_btn"} <= set(_bp78[0][0]))
    check("b78 Strukturen kommen VOR dem Scanner (Nutzer-Reihenfolge)",
          _iS and _iC and _iS[0] < _iC[0])
    # DIE TOUR SCHALTET IM BAUPLAN-FENSTER VON REITER ZU REITER (Sitzung 17).
    # ANGESPROCHEN WIRD DER NAME, nicht die Nummer: bei einem T1-Plan fehlt
    # "Invention", dann verschieben sich alle Nummern dahinter (gemessen).
    _d78 = getattr(win, "_bd_dialog", None)
    if _d78 is not None and _d78.isVisible():
        from PySide6.QtWidgets import QTabWidget as _QTW78
        _tw78 = (_d78.findChildren(_QTW78) or [None])[0]
        _tp78b = _TF78(win, "industry")
        try:
            for _ziel78 in (_t4("Materials"), _t4("Run planner"),
                            _t4("Recipe structure")):
                _i78 = [i for i, st in enumerate(_S78("industry"))
                        if st[0] == "bd:tab:" + _ziel78]
                if not _i78 or _tw78 is None:
                    continue
                _tp78b.i = _i78[0]
                _tp78b.zeigen()
                _app.processEvents()
                eq(f"b78 der Schritt zu '{_ziel78}' schaltet dorthin",
                   _tw78.tabText(_tw78.currentIndex()), _ziel78)
        finally:
            _tp78b.abbrechen()
            _app.processEvents()
    check("b78 fehlt ein Reiter (T1-Plan ohne Invention), bricht nichts",
          "return _d                              # Reiter fehlt: Fenster"
          in open("eve_trader/ui/tutorial.py", encoding="utf-8").read())
    eq("b78 die Bauplan-Schritte haengen ALLE am Bauplan-Fenster",
       [st[1] for st in _S78("industry")
        if st[0] is None and st[1] not in (_t4("Welcome to EVE-MoMa"),
                                           _t4("That is the industry side"))],
       [])
    # DAS FENSTER BRAUCHT EINEN ANKER (Nutzer-Fund Sitzung 17: "der Bauplan
    # rutscht in den Hintergrund ... wenn man das Haupttool herumzieht,
    # verschiebt sich das Tutorial-Fenster nicht mit").
    _tq78 = _TF78(win, "trading")
    try:
        _fl78 = int(_tq78.windowFlags())
        # Qt.Tool liegt ueber SEINEM Besitzer - genau das wollen wir. KEIN
        # WindowStaysOnTopHint: das laege auch ueber Discord & Co.
        check("b78 die Tour ist ein eigenes Werkzeugfenster",
              bool(_fl78 & int(_Qt76.Tool)))
        check("b78 aber NICHT ueber fremden Programmen",
              not (_fl78 & int(_Qt76.WindowStaysOnTopHint)))
        # AUSSEHEN (Nutzer, Sitzung 17): deutlich dunkler als das Werkzeug,
        # goldener Rahmen, groessere Schrift. EINE FRUEHERE FASSUNG DAVON GING
        # STILL VERLOREN (ein abgebrochenes Skript schrieb nicht) - deshalb
        # hier festgenagelt.
        from eve_trader.ui import theme as _th78
        check("b78 das Fenster ist dunkler als das Werkzeug",
              "#03060B" in _tq78.styleSheet()
              and _th78.BG not in _tq78.styleSheet())
        check("b78 der Rahmen ist in der Icon-Goldfarbe",
              f"solid {_th78.AMBER}" in _tq78.styleSheet())
        check("b78 die Schrift ist gross genug zum Lesen",
              "font-size:19px" in _tq78.titel.styleSheet()
              and "font-size:15px" in _tq78.text.styleSheet())
        check("b78 sie fuehrt sich selbst nach (Zeitgeber laeuft)",
              _tq78._folgen.isActive())
        _tq78.i = 1
        _tq78.zeigen()
        _app.processEvents()
        # Der Rahmen gehoert zum FENSTER seines Elements, nicht immer zum
        # Hauptfenster - sonst laege er hinter dem Bauplan.
        check("b78 der Rahmen haengt am Fenster seines Elements",
              _tq78._rahmen and _tq78._rahmen[0].parent() is win.g_hub.window())
        # ENTSCHEIDEND ist der Fall im BAUPLAN-FENSTER: dort lag der Rahmen
        # frueher hinter dem Bauplan, weil er am Hauptfenster hing.
        _dq78 = getattr(win, "_bd_dialog", None)
        if _dq78 is not None and _dq78.isVisible():
            _tb78 = _TF78(win, "industry")
            try:
                _ib78 = [i for i, st in enumerate(_S78("industry"))
                         if str(st[0]).startswith("bd:tab:")]
                if _ib78:
                    _tb78.i = _ib78[0]
                    _tb78.zeigen()
                    _app.processEvents()
                    check("b78 im Bauplan haengt der Rahmen am BAUPLAN-Fenster",
                          _tb78._rahmen
                          and _tb78._rahmen[0].window() is _dq78)
            finally:
                _tb78.abbrechen()
                _app.processEvents()
        # Verschieben: nach dem Nachfuehren muss der Rahmen wieder sitzen.
        _vor78q = _tq78._rahmen[0].geometry()
        _tq78._nachfuehren()
        _app.processEvents()
        check("b78 das Nachfuehren setzt den Rahmen wieder passend",
              _tq78._rahmen[0].geometry().width()
              == win.g_hub.width() + 6)
        # NICHT BEI JEDEM TAKT NACH VORN (Nutzer-Fund Sitzung 17: "der
        # Bauplan bleibt hinter dem Haupttool, ich kann ihn nicht mehr
        # hervorheben"). Ein raise_() alle 200 ms zog das Besitzerfenster mit.
        _src78t = __import__("inspect").getsource(type(_tq78)._nachfuehren)
        check("b78 das Nachfuehren holt die Tour NICHT staendig nach vorn",
              "self.raise_()" not in _src78t)
        check("b78 nach vorn geholt wird nur beim Schrittwechsel",
              "if vor:" in __import__("inspect").getsource(
                  type(_tq78)._platzieren)
              and "self._platzieren(vor=True)" in
              __import__("inspect").getsource(type(_tq78)._fenster_ordnen))
        _fo78 = __import__("inspect").getsource(type(_tq78)._fenster_ordnen)
        check("b78 und der Bauplan wird dabei selbst nach vorn geholt",
              "_ziel.raise_()" in _fo78)
        # ENTSCHEIDEND: die Tour HAENGT sich an das Fenster, um das es geht -
        # sonst zieht sie beim Nach-vorn-Holen ihren Besitzer (Haupttool) mit
        # und drueckt den Bauplan zurueck (Nutzer-Fund Sitzung 17).
        check("b78 die Tour haengt sich an das Fenster des Schritts",
              "self.setParent(_ziel, _flags)" in _fo78)
        # DAS ZIELFENSTER WIRD AM ELEMENT ABGELESEN, nicht am Namen
        # (Nutzer-Fund: "_bd_karte_bauenkaufen" zeigt in den BAUPLAN, heisst
        # aber nicht "bd:" - die Tour hielt es fuer einen Haupttool-Schritt
        # und schob den Bauplan nach hinten).
        _zf78 = __import__("inspect").getsource(type(_tq78)._zielfenster)
        check("b78 das Zielfenster kommt vom Element, nicht vom Namen",
              "return _w.window()" in _zf78)
        # RUECKFALL fuer Schritte NACH dem Oeffnen: ein gemerkter Knopf kann
        # auf ein ALTES Bauplan-Fenster zeigen (unsichtbar). Ohne den
        # Rueckfall landete die Tour am Haupttool und schob den Bauplan nach
        # hinten (Nutzer-Fund 14/15).
        check("b78 nach dem Oeffnen gilt der Bauplan als Zielfenster",
              '_nach_oeffnen = any(st[4] == "bauplan_offen"' in _zf78
              and "if _nach_oeffnen or self._schritt_im_bauplan():" in _zf78)
        check("b78 beim Schrittwechsel kommt auch das Anker-Fenster nach vorn",
              "_anker.window().raise_()" in __import__("inspect").getsource(
                  type(_tq78)._platzieren))
        _d78z = getattr(win, "_bd_dialog", None)
        if _d78z is not None and _d78z.isVisible():
            _tz78 = _TF78(win, "industry")
            try:
                _ik78 = [i for i, st in enumerate(_S78("industry"))
                         if st[0] == "_bd_karte_bauenkaufen"]
                if _ik78 and getattr(win, "_bd_karte_bauenkaufen", None):
                    _tz78.i = _ik78[0]
                    _tz78.zeigen()
                    _app.processEvents()
                    check("b78 'Build or buy' zaehlt zum BAUPLAN-Fenster",
                          _tz78._zielfenster() is _d78z)
            finally:
                _tz78.abbrechen()
                _app.processEvents()
        check("b78 spaeter auftauchende Elemente blinken nach",
              "self._hervorheben(_soll)" in _src78t)
        check("b78 platziert wird in BILDSCHIRM-Koordinaten",
              "mapToGlobal" in __import__("inspect").getsource(
                  type(_tq78)._platzieren))
    finally:
        _tq78.abbrechen()
        _app.processEvents()
    check("b78 der Knopf sitzt in der Seitenleiste",
          getattr(win, "tutorial_btn", None) is not None
          and win.tutorial_btn.text() == _t4("Tutorial"))
    check("b78 beim ersten Start wird EINMAL gefragt",
          "self.settings[\"tutorial_gefragt\"] = True" in _src_mw
          and "QTimer.singleShot(1500, self._tutorial_erstfrage)" in _src_mw)
except Exception as _e78:                                # pragma: no cover
    _fail.append(f"b78 Tutorial: {type(_e78).__name__}: {_e78}")


# ---------------------------------------------------------------- (b60)
# BERECHTIGUNGS-SCHALTER GELTEN SOFORT (Sitzung 17, Nutzer-Befund bei der
# Erstinstallation): "Structure markets" stand sichtbar auf On, intern galt
# Off, bis ganz unten "Save" gedrueckt wurde - das Neu-Verlinken fragte die
# Struktur-Berechtigung deshalb nicht an. Funktional am echten Feld.
try:
    from eve_trader import config as _cfg60
    _alt60 = win.settings.get("use_structures")
    _cb60 = getattr(win, "s_struct", None)
    check("b60 der Struktur-Schalter existiert", _cb60 is not None)
    if _cb60 is not None:
        _cb60.setCurrentIndex(0); _app.processEvents()
        _cb60.setCurrentIndex(1); _app.processEvents()
        check("b60 Umstellen auf On gilt SOFORT, ohne Save",
              win.settings.get("use_structures") is True)
        check("b60 ... und steht auf der Platte (Verlinken liest die Einstellung)",
              _cfg60.load_settings().get("use_structures") is True)
        _cb60.setCurrentIndex(0); _app.processEvents()
        check("b60 Umstellen auf Off gilt ebenso sofort",
              win.settings.get("use_structures") is False)
        _cb60.setCurrentIndex(1 if _alt60 else 0); _app.processEvents()
except Exception as _e60:                                # pragma: no cover
    _fail.append(f"b60 Berechtigungs-Schalter: {type(_e60).__name__}: {_e60}")


# ---------------------------------------------------------------- (b59)
# DIE SUITE HAENGT NICHT AM EINRICHTUNGS-FENSTER (Sitzung 17).
# Die Zeitgeber der Hauptfenster feuern oft erst beim Abraeumen - also
# NACH den Pruefungen. Deshalb hier einmal die Ereignisse abarbeiten, damit
# ein vergessenes Stilllegen noch VOR der Schlusszeile auffaellt.
import time as _time59
_bis59 = _time59.time() + 0.6            # > 300 ms Erststart-Zeitgeber
while _time59.time() < _bis59:
    _app.processEvents()
    _time59.sleep(0.02)
# UMGEBUNGSUNABHAENGIG: das Stilllegen gilt fuer die KLASSE. Ob das Fenster
# anspringt, haengt an `.smoke_home` - diese Pruefung nicht.
check("b59 das Einrichtungsfenster ist fuer JEDES Hauptfenster stillgelegt",
      MainWindow.__dict__.get("_erste_einrichtung_pruefen") is _einrichtung_still)
check("b59 auch die drei Erststart-Fragen sind fuer jedes Hauptfenster still",
      all(MainWindow.__dict__.get(_n59) is _einrichtung_still
          for _n59 in ("_erststart_rezepte_anbieten", "_erststart_ohne_charakter",
                       "_frage_verlauf_laden")))
check("b59 kein Einrichtungsfenster oeffnet sich unbestellt im Testlauf "
      f"(geoeffnet von: {_EINRICHTUNG_UNBESTELLT})",
      not _EINRICHTUNG_UNBESTELLT)
check(f"b59 kein anderes modales Fenster blieb offen ({_MODAL_UNBESTELLT})",
      not _MODAL_UNBESTELLT)

# ---------------------------------------------------------------- (b63)
# EINE GEDECKTE ZEILE DARF NICHT "kaufen" SAGEN.
#
# NUTZER-BEFUND (Sitzung 20, Ametat II x20): in der Rezept-Struktur stand bei
# Fermionic Condensates "kaufen", waehrend der Materialien-Reiter fuer dasselbe
# Item "genug" meldete (10.2k im Hangar) und der Einkauf leer blieb. Hier am
# ECHTEN Fenster gemessen, nicht nur am Quelltext: die Zeile eines Items, das
# der Plan vollstaendig aus dem Bestand deckt und NICHT kauft, muss "aus
# Bestand gedeckt" tragen.
class _Recipes63b:
    """100 (Fertigung) <- 10x 201 (Reaktion) <- 10x 301. Kaufen ist bei 201
    billiger als Bauen - der Baum entscheidet also 'buy'."""
    product_to_bp = {100: (900, I.MANUFACTURING, 1), 201: (901, I.REACTION, 1)}
    bp_materials = {(900, I.MANUFACTURING): [(201, 10)],
                    (901, I.REACTION): [(301, 10)]}
    activity_time = {(900, I.MANUFACTURING): 60, (901, I.REACTION): 60}
    activity_max_runs = {(900, I.MANUFACTURING): 0, (901, I.REACTION): 0}
    reaction_products = {201}
    invention_for_bpc = {}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return t in self.product_to_bp


_pr63b = {100: 100000.0, 201: 5.0, 301: 10.0}
_rec63b = _Recipes63b()
_opts63b = {"me": 0, "te": 0, "job_pct": 0, "invention": False,
            "build_reactions": True, "tree_depth": 4, "stock": {201: 10000}}
win._bd_recipes = _rec63b
win._bd_opts = dict(_opts63b)
win._bd_pricemap = dict(_pr63b)
_tree63b = I.build_tree(100, _pr63b.get, _rec63b, dict(_opts63b))
_plan63b = I.production_plan(100, 10, _pr63b.get, _rec63b, dict(_opts63b))
# VORBEDINGUNG - ohne sie prueft der Rest nichts (die Zeile faellt sonst gar
# nicht auf den Rueckfall zurueck).
_komp63b = [c for c in (_tree63b or {}).get("components", [])
            if c.get("type_id") == 201]
check("b63 der Baum entscheidet fuer 201 'kaufen'",
      bool(_komp63b) and _komp63b[0].get("decision") == "buy")
check("b63 der Plan setzt fuer 201 gar keine Entscheidung",
      201 not in (_plan63b.get("decision") or {}))
check("b63 und kauft 201 auch nicht",
      201 not in (_plan63b.get("buy") or {}))
check("b63 der Bestand deckt 201",
      201 in (_plan63b.get("stock_used") or {}))

_res63b = {"tree": _tree63b, "plan": _plan63b, "sell": 200000.0,
           "sell_is_contract": False,
           "names": {100: "Testendprodukt", 201: "Testreaktion", 301: "Testmat"}}
_dlg63b = None
try:
    win._show_build_detail(100, "Testendprodukt", _res63b)
    _dlg63b = getattr(win, "_bd_dialog", None)
    check("b63 Bauplan geoeffnet", _dlg63b is not None)
    _zeilen63b = []
    for _tw63 in (_dlg63b.findChildren(QTreeWidget) if _dlg63b else []):
        # NUR DIE REZEPT-STRUKTUR: der Runplaner ist ebenfalls ein Baum, hat
        # aber andere Spalten - dort stuende in Spalte 2 eine Zahl, und die
        # Pruefung waere an der falschen Stelle rot geworden (in der ersten
        # Fassung genau passiert).
        if _tw63.columnCount() < 3 or _tw63.topLevelItemCount() != 1:
            continue
        if "Testendprodukt" not in _tw63.topLevelItem(0).text(0):
            continue

        def _sammle63(_it):
            _zeilen63b.append((_it.text(0), _it.text(2)))
            for _i in range(_it.childCount()):
                _sammle63(_it.child(_i))
        for _i in range(_tw63.topLevelItemCount()):
            _sammle63(_tw63.topLevelItem(_i))
    _treffer63 = [a for n, a in _zeilen63b if "Testreaktion" in n]
    check(f"b63 die Zeile steht im Baum ({_zeilen63b[:6]})", bool(_treffer63))
    # BEIDE SPRACHEN akzeptieren - das Testfenster kann englisch oder deutsch
    # laufen (b3/b13/b42 gelernt).
    _gedeckt63 = {_t4("covered from stock"), "covered from stock",
                  "aus Bestand gedeckt"}
    check(f"b63 sie sagt 'aus Bestand gedeckt' ({_treffer63})",
          bool(_treffer63) and _treffer63[0] in _gedeckt63)
    check(f"b63 und eben NICHT 'kaufen' ({_treffer63})",
          bool(_treffer63)
          and _treffer63[0] not in (_t4("buy"), "buy", "kaufen"))
finally:
    try:
        if _dlg63b is not None:
            _dlg63b.close()
        _app.processEvents()
    except Exception:
        pass

# ---------------------------------------------------------------- (b64)
# GRUPPEN-BLACKLIST VON DER OBERFLAECHE BIS IN DEN PLAN (Punkt F, Sitzung 20).
# Nicht nur "die Funktion liest die Einstellung", sondern: Haekchen klicken ->
# Einstellung gespeichert -> Ausschluss neu gerechnet -> Item weder gebaut
# noch gekauft. Der ganze Weg, den der Nutzer geht.
class _Recipes64:
    """100 (Fertigung) <- 10x 301. 301 ist ein Mineral (Gruppe 'Mineral')."""
    product_to_bp = {100: (900, I.MANUFACTURING, 1)}
    bp_materials = {(900, I.MANUFACTURING): [(301, 10)]}
    activity_time = {(900, I.MANUFACTURING): 60}
    activity_max_runs = {(900, I.MANUFACTURING): 0}
    reaction_products = set()
    invention_for_bpc = {}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return t in self.product_to_bp


_pr64 = {100: 100000.0, 301: 10.0}
_rec64 = _Recipes64()
_opts64 = {"me": 0, "te": 0, "job_pct": 0, "invention": False,
           "build_reactions": True, "tree_depth": 4}
# Zustand, den ein offener Bauplan hinterlaesst - genau die Felder, die
# _bau_refresh_exclusions_and_rebuild braucht.
win._bd_recipes = _rec64
win._bd_opts = dict(_opts64)
win._bd_all_ids = {100, 301}
win._bd_groups_cache = {100: "Fighter", 301: "Mineral"}
win._bd_bl_names_cache = {100: "Testendprodukt", 301: "Testmineral"}
win._bd_bp_type = 100
_alt64 = list(win.settings.get("bau_blacklist_gruppen", []) or [])
_rebuilt64 = {"n": 0}
win._bd_full_rebuild = lambda: _rebuilt64.__setitem__("n", _rebuilt64["n"] + 1)
try:
    win.settings["bau_blacklist_gruppen"] = []
    _w64 = win._build_blacklist_compact()
    _boxes64 = getattr(win, "_bl_gruppen_boxes", None) or {}
    check("b64 die Haekchenliste ist da", bool(_boxes64))
    check("b64 alle Gruppen des Materialien-Reiters stehen zur Wahl",
          set(_boxes64) == set(win._MATERIAL_GRUPPEN))
    check("b64 anfangs ist nichts angehakt",
          not any(cb.isChecked() for cb in _boxes64.values()))
    # VORHER: das Mineral wird gekauft.
    _plan64a = I.production_plan(100, 10, _pr64.get, _rec64,
                                 dict(_opts64, excluded=win._bau_never_build(
                                     [100, 301], win._bd_groups_cache, set(),
                                     win._bd_bl_names_cache)))
    check("b64 ohne Haekchen wird das Mineral gekauft",
          301 in (_plan64a.get("buy") or {}))
    # KLICK auf "Mineralien".
    _boxes64["Mineralien"].setChecked(True)
    _app.processEvents()
    check("b64 der Klick landet in den Einstellungen",
          win.settings.get("bau_blacklist_gruppen") == ["Mineralien"])
    check("b64 und stoesst die Neurechnung an", _rebuilt64["n"] >= 1)
    check("b64 der Ausschluss ist im Plan-Zustand angekommen",
          301 in (win._bd_opts.get("excluded") or set()))
    # NACHHER: weder gebaut noch gekauft, Endprodukt unveraendert.
    _plan64b = I.production_plan(100, 10, _pr64.get, _rec64,
                                 dict(_opts64, excluded=win._bd_opts.get("excluded")))
    check("b64 mit Haekchen wird das Mineral nicht mehr gekauft",
          301 not in (_plan64b.get("buy") or {}))
    check("b64 und der Plan meldet den Treffer",
          301 in (_plan64b.get("excluded_hit") or set()))
    check("b64 das Endprodukt wird weiterhin gebaut",
          100 in (_plan64b.get("build_runs") or {}))
    # RUECKWEG: Haekchen weg -> alles wie vorher.
    _boxes64["Mineralien"].setChecked(False)
    _app.processEvents()
    check("b64 Haekchen weg -> Einstellung leer",
          win.settings.get("bau_blacklist_gruppen") == [])
    check("b64 und das Mineral ist wieder im Einkauf",
          301 not in (win._bd_opts.get("excluded") or set()))
finally:
    win.settings["bau_blacklist_gruppen"] = _alt64
    try:
        _w64.deleteLater(); _app.processEvents()
    except Exception:
        pass

# ---------------------------------------------------------------- (b66)
# KEINE WAAGERECHTE BILDLAUFLEISTE WEGEN EINER FREMDEN SEITE.
# NUTZER (Sitzung 20, zwei Screenshots): die Gewinn-Uebersicht rechts war
# nur nach dem Scrollen zu sehen. Ursache war NICHT "Meine Bauplaene",
# sondern der Stapel: er nimmt die Mindestbreite der BREITESTEN Seite fuer
# alle, und das war die 16-spaltige Blueprints-Tabelle.
_st66 = getattr(win, "b_stack", None)
check("b66 der Bau-Stapel ist da", _st66 is not None)


def _breiteste66(pg, n=4):
    """Die n breitesten Blaetter der Seite - damit ein roter b66 SAGT, wer
    schuld ist (Windows-Befund 19.09.2026: nur die Zahl 1'527 stand da)."""
    out = []
    for w in pg.findChildren(QWidget):
        if w.layout() is not None:
            continue
        txt = (w.text() if hasattr(w, "text") else "")
        out.append((w.minimumSizeHint().width(), type(w).__name__, str(txt)[:40]))
    return sorted(out, reverse=True)[:n]


if _st66 is not None:
    _breiten66 = [_st66.widget(i).minimumSizeHint().width()
                  for i in range(_st66.count())]
    check(f"b66 keine Seite sprengt 1366 px mit Seitenleiste ({_breiten66})",
          all(b + 230 <= 1366 for b in _breiten66))
    check(f"b66 der Stapel selbst passt auf 1366 px ({_st66.minimumSizeHint().width()}; "
          f"breiteste: {_breiteste66(_st66)})",
          _st66.minimumSizeHint().width() + 230 <= 1366)
    # GEGENPROBE: die Bauplan-Seite ist wirklich die schmale von beiden -
    # sonst haette die Pruefung oben auch bei vertauschten Seiten gehalten.
    # SITZUNG 20: die Seite traegt jetzt Karte (520) + Gewinn-Uebersicht (320)
    # als Mindestbreiten, also rund 870 statt vorher 391. Die Zusage bleibt,
    # dass sie mit der Seitenleiste in 1366 px passt - das wird gerechnet
    # statt geraten.
    check(f"b66 Bauplan-Seite plus Seitenleiste passen in 1366 px "
          f"({_st66.widget(2).minimumSizeHint().width()}; "
          f"breiteste: {_breiteste66(_st66.widget(2))})",
          _st66.widget(2).minimumSizeHint().width() + 230 <= 1366)
    # KOPFZEILEN-KNOEPFE DUERFEN SCHRUMPFEN (Windows-Befund 19.09.2026).
    check("b66 die drei Kopfzeilen-Knoepfe haben eine kleine Untergrenze (40 px)",
          all(getattr(win, _n).minimumWidth() == 40
              for _n in ("bp_order_btn", "bp_progress_btn")))

# ---------------------------------------------------------------- (b67)
# WARNER FUER EINEN ALTEN ODER FALSCHEN MARKT (Nutzer, Sitzung 20).
# Am echten Fenster gemessen, nicht nur am Quelltext: der Knopf muss blinken
# und die Meldung neben dem Charakter-Feld erscheinen.
check("b67 die Warn-Beschriftung gibt es", getattr(win, "g_scan_warn", None) is not None)
# GEMESSEN WIRD DER ZUSTAND, NICHT isVisible(): ein Widget in einem nie
# angezeigten Fenster meldet IMMER "unsichtbar" - die Pruefung waere blind
# (dieselbe Falle wie bei height() in b2t). Der Blink-Zeitgeber und der Text
# sagen die Wahrheit.
win._scan_warnung_setzen("")
check("b67 ausgeschaltet laeuft kein Zeitgeber", not win._scan_blink_timer.isActive())
# HUB GEWECHSELT -> Warnung, Blinken an.
win._scan_hub_gewechselt = True
win._scan_alter_pruefen()
_app.processEvents()
check("b67 nach Hub-Wechsel steht eine Warnung", bool(win.g_scan_warn.text()))
check("b67 und der Knopf blinkt", win._scan_blink_timer.isActive())
check(f"b67 die Meldung nennt den Markt ({win.g_scan_warn.text()!r})",
      "arkt" in win.g_scan_warn.text() or "arket" in win.g_scan_warn.text())
_txt_hub67 = win.g_scan_warn.text()
# Ein Blinkschritt aendert den Rahmen des Knopfs und nimmt ihn wieder weg.
win._scan_blink_schritt()
_an67 = win.g_scan_btn.styleSheet()
win._scan_blink_schritt()
_aus67 = win.g_scan_btn.styleSheet()
check("b67 ein Blinkschritt faerbt den Rahmen amber", "border" in _an67
      and "transparent" not in _an67)
# GLEICHE GROESSE IN BEIDEN ZUSTAENDEN (Nutzer: "das Blinken laesst das ganze
# UI minimal nach unten rutschen"). Ein Rahmen, der nur im An-Zustand da ist,
# aendert die Knopfgroesse im Takt - deshalb hat auch der Aus-Zustand einen,
# nur durchsichtig.
check("b67 der Aus-Zustand hat denselben Rahmen, nur durchsichtig",
      "border:2px" in _aus67 and "transparent" in _aus67)
# SCAN GEDRUECKT -> Hub-Wechsel gilt als erledigt.
win._scan_hub_gewechselt = False
win._scan_alter_pruefen()
_app.processEvents()
_txt_alt67 = win.g_scan_warn.text()
check("b67 ohne Hub-Wechsel entscheidet das ALTER",
      _txt_alt67 != _txt_hub67 or not win._scan_blink_timer.isActive())
# Frischer Scan -> keine Warnung mehr, Blinken aus, Rahmen weg.
import eve_trader.store as _st67
_alt_fn67 = _st67.snapshot_age_seconds
try:
    _st67.snapshot_age_seconds = lambda *a, **k: 60.0
    win._scan_alter_pruefen(); _app.processEvents()
    check("b67 frischer Scan -> keine Warnung", not win._scan_blink_timer.isActive())
    check("b67 und das Blinken hoert auf", not win._scan_blink_timer.isActive())
    check("b67 der Rahmen bleibt nicht stehen", win.g_scan_btn.styleSheet() == "")
    # SOFORT AUFHOEREN beim Klick auf den Scan-Knopf - nicht erst bei der
    # naechsten Alterspruefung (Nutzer: im Ladefenster blinkte es weiter).
    _st67.snapshot_age_seconds = lambda *a, **k: 7200.0
    win._scan_alter_pruefen(); _app.processEvents()
    check("b67 vor dem Scan blinkt es", win._scan_blink_timer.isActive())
    _sg67 = getattr(win, "scan_global", None)
    check("b67 der Scan schaltet es sofort aus",
          "self._scan_warnung_setzen(\"\")" in
          __import__("inspect").getsource(_sg67))
    # UND SCHWEIGT, SOLANGE ER LAEUFT (Nutzer, zweiter Befund): die Pruefung
    # alle 30 s schaltete das Blinken sonst mitten im Scan wieder an - der
    # Schnappschuss wird ja erst am ENDE frisch.
    win._scan_laeuft = True
    win._scan_alter_pruefen(); _app.processEvents()
    check("b67 waehrend des Scans blinkt nichts", not win._scan_blink_timer.isActive())
    win._set_scan_buttons(True)          # Scan fertig
    _app.processEvents()
    check("b67 danach darf wieder geprueft werden", not win._scan_laeuft)
    # GROESSE: waehrend des Blinkens ist der Knopf festgenagelt, danach frei.
    _st67.snapshot_age_seconds = lambda *a, **k: 7200.0
    win._scan_alter_pruefen(); _app.processEvents()
    check("b67 beim Blinken ist die Knopfgroesse fest",
          win.g_scan_btn.minimumSize() == win.g_scan_btn.maximumSize())
    # Die Hover-Regel entsteht erst beim naechsten Blinkschritt.
    win._scan_blink_schritt()
    check("b67 die Hover-Regel hat denselben Rahmen",
          "QPushButton:hover{border:2px" in win.g_scan_btn.styleSheet())
    win._scan_warnung_setzen("")
    check("b67 danach ist die Groesse wieder frei",
          win.g_scan_btn.maximumSize().width() > 1000)
    _st67.snapshot_age_seconds = lambda *a, **k: 7200.0
    win._scan_alter_pruefen(); _app.processEvents()
    check("b67 nach zwei Stunden warnt es wieder", win._scan_blink_timer.isActive())
    _st67.snapshot_age_seconds = lambda *a, **k: 3599.0
    win._scan_alter_pruefen(); _app.processEvents()
    check("b67 kurz vor einer Stunde noch nicht", not win._scan_blink_timer.isActive())
    _st67.snapshot_age_seconds = lambda *a, **k: None
    win._scan_alter_pruefen(); _app.processEvents()
    check("b67 gar kein Scan zaehlt als zu alt", win._scan_blink_timer.isActive())
finally:
    _st67.snapshot_age_seconds = _alt_fn67
    win._scan_warnung_setzen("")

# ---------------------------------------------------------------- (b68)
# KENNZAHLEN VERDECKEN (Nutzer, Sitzung 20): "wenn man jemandem etwas an dem
# Tool zeigen will, online oder on Stream, dann kann man diese heiklen Daten
# einfach zensieren." Am echten Fenster gemessen.
_keys68 = ("pf_wealth", "pf_wallet", "pf_pl", "pf_flag",
           "pr_net", "pr_rev", "pr_trades", "pr_margin")
_reg68 = getattr(win, "_kpi_labels", None) or {}
for _k68 in _keys68:
    check(f"b68 {_k68} hat ein Auge", _k68 in _reg68)
_alt68 = list(win.settings.get("kpi_zensiert", []) or [])
try:
    win.settings["kpi_zensiert"] = []
    win._kpi_zensur_anwenden()
    _lbl68, _btn68 = _reg68["pf_wealth"]
    _lbl68.setText("343'533'257'585 ISK")
    check("b68 offen zeigt die echte Zahl", _lbl68.text() == "343'533'257'585 ISK")
    # VERDECKEN
    win._kpi_zensur_umschalten("pf_wealth")
    _app.processEvents()
    check("b68 verdeckt zeigt die Maske", _lbl68.text() != "343'533'257'585 ISK")
    check("b68 und die Zahl steht nicht mehr da", "343" not in _lbl68.text())
    check("b68 der Zustand ist gespeichert",
          "pf_wealth" in (win.settings.get("kpi_zensiert") or []))
    # DIE ENTSCHEIDENDE ZUSAGE: ein neuer setText() darf NICHTS preisgeben -
    # die Kennzahlen werden laufend neu gefuellt, waehrend der Stream laeuft.
    _lbl68.setText("999'999'999 ISK")
    check("b68 auch ein neuer Wert bleibt verdeckt", "999" not in _lbl68.text())
    # WIEDER ZEIGEN - und zwar den NEUEN Wert, nicht den alten.
    win._kpi_zensur_umschalten("pf_wealth")
    _app.processEvents()
    check("b68 wieder offen zeigt den aktuellen Wert",
          _lbl68.text() == "999'999'999 ISK")
    check("b68 und der Zustand ist wieder weg",
          "pf_wealth" not in (win.settings.get("kpi_zensiert") or []))
    # Jede Karte einzeln - eine verdeckte darf die anderen nicht mitnehmen.
    win._kpi_zensur_umschalten("pr_net")
    _app.processEvents()
    _lbl_rev68 = _reg68["pr_rev"][0]
    _lbl_rev68.setText("20'596'678'163 ISK")
    check("b68 die Nachbarkarte bleibt offen",
          _lbl_rev68.text() == "20'596'678'163 ISK")
finally:
    win.settings["kpi_zensiert"] = _alt68
    win._kpi_zensur_anwenden()


# ---------------------------------------------------------------- (b7u)
# REPROCESSING IM BAUPLAN, WEG B (1.0.9, Nutzer 18.09.2026 "also los"):
# Karte "Reprocessing" in der Rezeptstruktur, Schalter an -> die
# Einkaufsliste kauft komprimiertes Erz statt des Minerals, wo es
# guenstiger ist; Schalter aus -> exakt der alte Plan. Alles ohne ESI und
# ohne SDE: Karte, Struktur-Werte, Skills und Preise sind hier vorgegeben.
# Rechnung: 10 Testship brauchen 100 Testmat, 40 aus Bestand -> 60 kaufen zu
# 100 ISK = 6'000. Compressed Testore (1 ISK) ergibt je Portion 100
# floor(400 x 0.83854) = 335 Testmat -> 1 Portion = 100 ISK. Ersparnis 5'900,
# Ueberschuss 275.
import eve_trader.reprocess as _R7u                                  # noqa: E402
from eve_trader import config, esi, store                            # noqa: E402
_alt7u = {
    "map": I.reprocess_map, "cats": I.item_category_map, "sde": I.reprocess_struktur_sde,
    "ids": I.reprocess_skill_ids, "erz": I.reprocess_erz_skill,
    "chars": store.list_characters, "save": config.save_settings,
    "names": esi.resolve_names,
}
_alt_set7u = {k: win.settings.get(k) for k in
              ("bau_reprocess_on", "bau_reprocess_struct", "bau_structures",
               "bau_char_skills", "bau_build_chars")}
I.reprocess_map = lambda: {62516: {"portion": 100, "out": {200: 400}}}
I.item_category_map = lambda: {62516: (25, 462, 0), 200: (4, 18, 0), 100: (6, 25, 0)}
I.reprocess_struktur_sde = lambda: {
    "bonus": {"Tatara": 5.5},
    "rig": {46639: {"name": "Standup L-Set Reprocessing Monitor I", "mult": 0.51,
                    "hi": 1.0, "low": 1.06, "null": 1.12}}}
I.reprocess_skill_ids = lambda: {"Reprocessing": 3385, "Reprocessing Efficiency": 3389}
I.reprocess_erz_skill = lambda: {62516: 60377}
store.list_characters = lambda: [{"character_id": 1, "character_name": "Peanut Motor"}]
config.save_settings = lambda s: None
esi.resolve_names = lambda ids: {int(i): {62516: "Compressed Testore", 200: "Testmat",
                                          100: "Testship"}.get(int(i), f"#{i}")
                                 for i in ids}
_dlg7u = None
try:
    win.settings["bau_structures"] = [{"id": "s7u", "name": "R&R Yard", "type": "tatara",
                                       "rigs": ["sde:46639", "", ""], "security": 2.1}]
    win.settings["bau_reprocess_struct"] = "s7u"
    win.settings["bau_reprocess_on"] = True
    win.settings["bau_char_skills"] = {"1": {"3385": 5, "3389": 5, "60377": 5}}
    # Ohne Bau-Charakter bleibt der Runplaner leer - Stufe 0 haengt an ihm.
    win.settings["bau_build_chars"] = [1]
    _pr7u = dict(PRICES); _pr7u[62516] = 1.0
    win._bd_pricemap = dict(_pr7u)
    win._bd_recipes = _Recipes()
    win._bd_opts = {"me": 0, "te": 0, "job_pct": 0, "build_reactions": False,
                    "tree_depth": 4, "stock": {200: 40}}
    _ro7u = win._reprocess_opts()
    eq("b7u die Struktur-Basis der Tatara ist die gemessene",
       round(_ro7u["basis"], 6), 0.602616)
    win._bd_opts["reprocess"] = _ro7u
    win._bd_type = 100
    win._bd_qty = 10
    _plan7u = I.production_plan(100, 10, _pr7u.get, _Recipes(), dict(win._bd_opts))
    _tree7u = I.build_tree(100, _pr7u.get, _Recipes(), dict(win._bd_opts))
    _res7u = {"tree": _tree7u,
              "names": {100: "Testship", 200: "Testmat", 62516: "Compressed Testore"},
              "sell": 6000.0, "sell_is_contract": False, "plan": _plan7u}
    _sbd_frisch(100, "Testship", _res7u)
    _dlg7u = getattr(win, "_bd_dialog", None)
    _app.processEvents()

    def _mat_zeilen7u():
        _tbl = getattr(win, "_bd_mat_tab_tbl", None)
        out = []
        if _tbl is None:
            return out
        _root = _tbl.invisibleRootItem()
        _st = [_root.child(i) for i in range(_root.childCount())]
        while _st:
            _x = _st.pop()
            out.append(_x.text(0))
            _st += [_x.child(i) for i in range(_x.childCount())]
        return out

    def _mat_zeilen7u_alle():
        _tbl = getattr(win, "_bd_mat_tab_tbl", None)
        out = []
        if _tbl is None:
            return out
        _root = _tbl.invisibleRootItem()
        _st = [_root.child(i) for i in range(_root.childCount())]
        while _st:
            _x = _st.pop()
            # Der Status steht als Daten (UserRole), nicht als Text.
            out += [_x.text(c) for c in range(_tbl.columnCount())]
            out += [str(_x.data(c, Qt.UserRole) or "") for c in range(_tbl.columnCount())]
            _st += [_x.child(i) for i in range(_x.childCount())]
        return out

    def _info7u():
        _l = getattr(win, "_bd_mat_tab_info", None)
        return _l.text() if _l is not None else ""
    _cb7u = getattr(win, "_bd_reprocess_cb", None)
    check("b7u die Karte hat den Schalter, und er ist an", _cb7u is not None and _cb7u.isChecked())
    # LAGE (Nutzer 18.09.2026: "schieb das bitte hoeher, da wo man es sieht.
    # Direkt unter Production depth, lass zugeklappt"): Reihenfolge der
    # Klappkarten und Zustand der Reprocessing-Karte.
    _karten7u = []
    _zu7u = {}
    for _b7 in _dlg7u.findChildren(QPushButton):
        for _ti in ("Build or buy?", "Production depth", "Reprocessing", "Blacklist",
                    "Do I have the blueprints?"):
            if (_b7.text() or "").endswith(_t4(_ti)) and _b7.isCheckable():
                _karten7u.append(_ti)
                _zu7u[_ti] = _b7.isChecked()
    eq("b7u die Karte steht direkt unter Production depth",
       _karten7u, ["Build or buy?", "Production depth", "Reprocessing", "Blacklist",
                   "Do I have the blueprints?"])
    eq("b7u ... und ist zugeklappt, auch mit Schalter an", _zu7u.get("Reprocessing"), False)
    _sc7u = getattr(win, "_bd_reprocess_struct_cb", None)
    check("b7u die Struktur-Auswahl steht auf der Tatara",
          _sc7u is not None and _sc7u.currentData() == "s7u")
    _plan_a = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    eq("b7u der Plan kauft 100 Compressed Testore statt 60 Testmat",
       dict(_plan_a.get("buy") or {}), {62516: 100})
    eq("b7u ... Ersparnis 5'900 ISK, Ueberschuss 275 Testmat",
       (round(_plan_a.get("reprocess", {}).get("ersparnis") or 0), dict(_plan_a.get("surplus") or {})),
       (5900, {200: 275}))
    eq("b7u ... und total_cost ist um die Ersparnis gesunken",
       round(float(_plan7u["total_cost"]) - float(_plan_a["total_cost"])), 5900)
    check("b7u der Materialien-Tab zeigt das Erz",
          any("Compressed Testore" in z for z in _mat_zeilen7u()))
    # REZEPT-BAUM (Nutzer 18.09.2026: "im Rezeptbaum noch keine Beschreibung
    # fuer compressed Ores"): die Mineral-Zeile nennt das Erz.
    from PySide6.QtWidgets import QTreeWidget as _QTW7u

    def _baum_aktion7u(name):
        for _tw in _dlg7u.findChildren(_QTW7u):
            _hi = _tw.headerItem()
            if _hi is None or _tw.columnCount() < 3 or _hi.text(2) != _t4("Action"):
                continue                      # nur der Rezept-Baum
            _root = _tw.invisibleRootItem()
            _st = [_root.child(i) for i in range(_root.childCount())]
            while _st:
                _x = _st.pop()
                if _x.text(0) == name:
                    return _x.text(2)
                _st += [_x.child(i) for i in range(_x.childCount())]
        return None
    eq("b7u der Rezept-Baum sagt bei Testmat 'aus komprimiertem Erz'",
       _baum_aktion7u("Testmat"),
       _t4("from compressed ore \u267b \u00b7 {ore}").format(ore="Compressed Testore"))
    # DIE ROHZEILEN, aus denen Einkaufsfenster und Kopier-Knoepfe lesen
    # (Nutzer-Befund 18.09.2026: Einkaufsliste ohne Tritanium UND ohne Erz).
    _mr7u = [r for r in (getattr(win, "_bd_mat_rows", None) or []) if r.get("tid") == 62516]
    eq("b7u die Rohzeile des Erzes traegt missing=100, total=100, built=0",
       [(r["missing"], r["total"], r["built"], r["category"]) for r in _mr7u][:1],
       [(100, 100, 0, _mr7u[0]["category"] if _mr7u else None)])
    # GEDECKTE MINERALE BLEIBEN SICHTBAR (Nutzer-Befund): Testmat steht mit
    # 60 "aus Reprocessing", nichts zu kaufen.
    _tm7u = [r for r in (getattr(win, "_bd_mat_rows", None) or []) if r.get("tid") == 200]
    eq("b7u Testmat-Zeile: 60 aus Reprocessing, 0 zu kaufen, 100 Bedarf",
       [(r.get("reprocessed"), r["missing"], r["total"]) for r in _tm7u], [(60, 0, 100)])
    # Der Status steht im Deckungs-Balken (Widget) - pruefbar ist der
    # Grund, den die Zeile dabei bekommt.
    check("b7u ... und die Zeile sagt 'gedeckt durch Reprocessing'",
          bool(_tm7u) and "reprocessing" in (_tm7u[0].get("reason") or "").lower()
          and "stage 0" in (_tm7u[0].get("reason") or "").lower())
    # EINKAUFSLISTE (Restbedarf): Erz statt Mineral, solange nicht abgehakt.
    eq("b7u Restbedarf: 100 Erz + 40 Testmat (100 Bedarf - 60 gedeckt), kein Kauf",
       win._restbedarf_jetzt(), {200: 40, 62516: 100})
    eq("b7u Fehlbedarf jetzt: nur das Erz fehlt (100), Testmat ist gedeckt",
       [(r[0], r[1]) for r in win._fehlbedarf_jetzt()], [(62516, 100)])
    # HAKEN IN STUFE 0 = reprocesst: jetzt fehlt Testmat (60), das Erz nicht.
    _tr0 = getattr(win, "_sched_tree_ref", None)
    _row0 = None
    if _tr0 is not None and _tr0.topLevelItemCount() > 0:
        _s0 = _tr0.topLevelItem(0)
        for _i in range(_s0.childCount()):
            for _j in range(_s0.child(_i).childCount()):
                _row0 = _s0.child(_i).child(_j)
    check("b7u die Stufe-0-Zeile ist abhakbar",
          _row0 is not None and bool(_row0.flags() & Qt.ItemIsUserCheckable))
    if _row0 is not None:
        _row0.setCheckState(0, Qt.Checked)
        _app.processEvents()
    check("b7u der Haken landet als repro|62516 im Plan",
          "repro|62516" in (getattr(win, "_bd_runplan_checked", None) or set()))
    eq("b7u abgehakt: Testmat fehlt wieder (60), Erz nicht mehr",
       [(r[0], r[1]) for r in win._fehlbedarf_jetzt()], [(200, 60)])
    eq("b7u abgehakt: Restbedarf ohne Erz", win._restbedarf_jetzt(), {200: 100})
    if _row0 is not None:
        _row0.setCheckState(0, Qt.Unchecked)
        _app.processEvents()
    # CHARAKTERZEILE (Nutzer 19.09.2026): Haken am Charakter (zieht die Erz-
    # Zeilen mit, Schluessel char|repro|<cid>), und standardmaessig ZU wie
    # bei den anderen Stufen - die Stufe selbst offen.
    _cz0 = _row0.parent() if _row0 is not None else None
    check("b7u die Charakterzeile in Stufe 0 hat ein Kaestchen (char|repro|1) und ist zu",
          _cz0 is not None and _cz0.data(0, Qt.CheckStateRole) is not None
          and _cz0.data(0, Qt.UserRole + 6) == "char|repro|1"
          and not _cz0.isExpanded() and _tr0.topLevelItem(0).isExpanded())
    if _cz0 is not None:
        _cz0.setCheckState(0, Qt.Checked); _app.processEvents()
    check("b7u Haken am Charakter hakt die Erz-Zeile mit ab (repro|62516 + char|repro|1)",
          _row0 is not None and _row0.checkState(0) == Qt.Checked
          and {"repro|62516", "char|repro|1"} <= (
              getattr(win, "_bd_runplan_checked", None) or set()))
    if _cz0 is not None:
        _cz0.setCheckState(0, Qt.Unchecked); _app.processEvents()
    check("b7u ... und wieder loesen loest beides",
          _row0 is not None and _row0.checkState(0) == Qt.Unchecked
          and not ({"repro|62516", "char|repro|1"} & (
              getattr(win, "_bd_runplan_checked", None) or set())))

    def _sched_zeilen7u():
        _tr = getattr(win, "_sched_tree_ref", None)
        out = []
        if _tr is None:
            return out
        _root = _tr.invisibleRootItem()
        _st = [_root.child(i) for i in range(_root.childCount())]
        while _st:
            _x = _st.pop()
            out.append(tuple(_x.text(c) for c in range(_tr.columnCount())))
            _st += [_x.child(i) for i in range(_x.childCount())]
        return out
    _sz7u = _sched_zeilen7u()
    _stufe0 = [z for z in _sz7u if z[0].startswith("0. ")]
    check("b7u der Runplaner hat Stufe 0 Reprocessing mit der Struktur",
          len(_stufe0) == 1 and "R&R Yard" in _stufe0[0][0]
          and _t4("Reprocessing") in _stufe0[0][0])
    _tr7u = getattr(win, "_sched_tree_ref", None)
    check("b7u ... und sie steht ganz oben",
          _tr7u is not None and _tr7u.topLevelItemCount() > 0
          and _tr7u.topLevelItem(0).text(0).startswith("0. "))
    # SPALTEN WIE BEI DEN ANDEREN STUFEN (Nutzer 18.09.2026): Erz-Name in
    # Spalte 0, Menge in "Runs", Ergebnis + Ausbeute in "Stage", Charakter-
    # zeile nennt die Bloecke in "Blueprints".
    check("b7u ... Charakter und Zeile: 100 x Erz -> 60 Testmat (+275), 1 Block, 83.9 %",
          any(z[0] == "Peanut Motor" and z[2] == _t4("{n} batches").format(n=1)
              for z in _sz7u)
          and any(z[0] == "Compressed Testore" and z[1] == "100"
                  and z[4] == "\u2192 60 Testmat  \u00b7  83.9 %" and z[5] == "+275 Testmat"
                  for z in _sz7u))
    check("b7u ... Klick auf das Erz kopiert den Erz-Namen (ROLLE_KOPIERNAME)",
          _row0 is not None and _row0.data(0, _RKN7f) == "Compressed Testore")
    _cw7u = _tr7u.itemWidget(_row0, 2) if (_tr7u is not None and _row0 is not None) else None
    _btn7u = [w for w in (_cw7u.findChildren(QPushButton) if _cw7u is not None else [])]
    check("b7u ... und die Menge ist ein Kopier-Knopf '100'",
          len(_btn7u) == 1 and _btn7u[0].text() == "100")
    if _btn7u:
        _btn7u[0].click(); _app.processEvents()
        eq("b7u ... Klick auf den Knopf legt 100 in die Zwischenablage",
           QApplication.clipboard().text(), "100")
    # KEIN TEXTBLOCK MEHR UEBER DER LISTE (Nutzer 19.09.2026): das Erz ist
    # eine eigene Gruppe, die Zeile nennt Ausgang/Ausbeute/Charakter, die
    # Ersparnis steht in der Reprocessing-Karte, der Baum hat einen Erz-Kopf.
    check("b7u die Info-Zeile schweigt ueber Schritte und Ersparnis",
          "83.9" not in _info7u() and "5'900" not in _info7u())
    _alle7u = _mat_zeilen7u_alle()

    def _balken7u():
        # Der Status steht im Deckungs-Balken (QProgressBar.format), nicht im Item.
        _tbl = getattr(win, "_bd_mat_tab_tbl", None)
        out = []
        _root = _tbl.invisibleRootItem()
        _st = [_root.child(i) for i in range(_root.childCount())]
        while _st:
            _x = _st.pop()
            _w = _tbl.itemWidget(_x, 6)
            if _w is not None and hasattr(_w, "format"):
                out.append((_x.text(0), _w.format()))
            _st += [_x.child(i) for i in range(_x.childCount())]
        return out
    check("b7u die Erz-Zeile steht unter 'Compressed ore' und nennt 60 Testmat, 83.9 %, Peanut Motor",
          _t4("Compressed ore ♻") in _alle7u
          and any(n == "Compressed Testore" and "60 Testmat" in f and "83.9 %" in f
                  and "Peanut Motor" in f for n, f in _balken7u()))
    _rpl7u = getattr(win, "_bd_reprocess_lbl", None)
    check("b7u die Karte nennt die Ersparnis 5'900 und 1 Erz",
          _rpl7u is not None and "5'900" in _rpl7u.text()
          and _t4("saves {isk} · {n} ores").format(isk="", n=1).split("·")[1].strip()
          in _rpl7u.text())
    _tw7u = [w for w in _dlg7u.findChildren(QTreeWidget)]
    _baum7u = []
    for _w in _tw7u:
        _r = _w.invisibleRootItem(); _st = [_r.child(i) for i in range(_r.childCount())]
        while _st:
            _x = _st.pop(); _baum7u.append(tuple(_x.text(c) for c in range(3)))
            _st += [_x.child(i) for i in range(_x.childCount())]
    check("b7u der Rezept-Baum hat den Kopf 'Compressed ore (1)' mit der Erz-Zeile",
          any(z[0].startswith(_t4("Compressed ore ♻")) and "(1)" in z[0] for z in _baum7u)
          and any(z[0] == "Compressed Testore" and z[1] == "100"
                  and _t4("reprocess → {out} · {pct} %").format(out="60 Testmat", pct="83.9") in z[2]
                  for z in _baum7u))
    # BLACKLIST GILT AUCH FUER ERZ (Nutzer 19.09.2026: "wir rechnen damit,
    # es zu reprocessen, ABER es kommt weder in die Einkaufsliste noch in
    # den Runplaner - man bekommt es z. B. von einem Kollegen"): Gruppe
    # "Erz" -> das Erz ist gratis, deckt Testmat, steht nirgends zum Kauf.
    _bl_alt7u = win.settings.get("bau_blacklist_gruppen")
    win.settings["bau_blacklist_gruppen"] = ["Erz"]
    _cb7u.click(); _app.processEvents(); _cb7u.click(); _app.processEvents()
    _plan_bl = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    _st_bl = (_plan_bl.get("reprocess") or {}).get("schritte") or []
    eq("b7u Erz auf der Blacklist: Einkaufsliste leer, Schritt gratis, deckt 60 Testmat, Ersparnis 6'000",
       (dict(_plan_bl.get("buy") or {}),
        [(s.get("erz"), s.get("gratis"), s.get("deckt")) for s in _st_bl],
        (_plan_bl.get("reprocess") or {}).get("ersparnis")),
       ({}, [(62516, True, {200: 60})], 6000.0))
    eq("b7u ... Restbedarf ohne Erz, Testmat gedeckt", win._restbedarf_jetzt(), {200: 40})
    _tr_bl = getattr(win, "_sched_tree_ref", None)
    check("b7u ... und der Runplaner hat KEINE Stufe 0",
          _tr_bl is not None and not any(
              _tr_bl.topLevelItem(i).text(0).startswith("0. ")
              for i in range(_tr_bl.topLevelItemCount())))
    _baum_bl = []
    for _w in _dlg7u.findChildren(QTreeWidget):
        _r = _w.invisibleRootItem(); _st = [_r.child(i) for i in range(_r.childCount())]
        while _st:
            _x = _st.pop(); _baum_bl.append(tuple(_x.text(c) for c in range(3)))
            _st += [_x.child(i) for i in range(_x.childCount())]
    check("b7u ... der Materials-Tab zeigt das Erz trotzdem: 100 gestellt, nichts fehlt",
          any(n == "Compressed Testore" and _t4("on blacklist \u2013 provided, not bought") in f
              and "60 Testmat" in f for n, f in _balken7u())
          and any(r.get("tid") == 62516 and int(r.get("total") or 0) == 100
                  and int(r.get("missing") or 0) == 0 for r in (win._bd_mat_rows or [])))
    check("b7u ... der Rezept-Baum sagt beim Erz 'on blacklist - provided'",
          any(z[0] == "Compressed Testore"
              and _t4("on blacklist \u2013 provided, not bought") in z[2] for z in _baum_bl))
    check("b7u ... und die Blacklist-Karte hat das Haekchen 'Compressed ore'",
          "Erz" in (getattr(win, "_bl_gruppen_boxes", None) or {}))
    if _bl_alt7u is None:
        win.settings.pop("bau_blacklist_gruppen", None)
    else:
        win.settings["bau_blacklist_gruppen"] = _bl_alt7u
    _cb7u.click(); _app.processEvents(); _cb7u.click(); _app.processEvents()
    # WARUM NICHT: Testmat ist getauscht, also KEINE "nicht guenstiger"-Zeile;
    # der Zweig darf nicht abstuerzen, wenn abgelehnt leer ist.
    check("b7u keine 'Ore not cheaper'-Zeile, wenn alles getauscht ist",
          _t4("Ore not cheaper for: {liste}").format(liste="")[:10] not in _info7u())
    # SCHALTER AUS: exakt der alte Plan, kein Schluessel mehr in den opts.
    _cb7u.click()
    _app.processEvents()
    _plan_b = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    eq("b7u Schalter aus: der Plan kauft wieder 60 Testmat",
       dict(_plan_b.get("buy") or {}), {200: 60})
    check("b7u ... ohne 'reprocess' in den opts und ohne Erz im Tab",
          "reprocess" not in win._bd_opts
          and not any("Compressed Testore" in z for z in _mat_zeilen7u())
          and "Compressed" not in _info7u())
    check("b7u ... und Stufe 0 ist aus dem Runplaner verschwunden",
          not any(z[0].startswith("0. ") for z in _sched_zeilen7u()))
    check("b7u ... und der Rezept-Baum sagt wieder 'kaufen'",
          (_baum_aktion7u("Testmat") or "").startswith(_t4("buy")))
    eq("b7u ... und die Einstellung ist gespeichert", win.settings.get("bau_reprocess_on"), False)
    # WIEDER AN: derselbe Weg wie beim Nutzer, der es im offenen Dialog setzt.
    _cb7u.click()
    _app.processEvents()
    _plan_c = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    eq("b7u wieder an: Erz statt Mineral", dict(_plan_c.get("buy") or {}), {62516: 100})
    # NPC-STATION gewaehlt: Basis 0.50 -> 0.50 x 1.3915 = 0.69575 -> 278 je
    # Portion, immer noch 1 Portion, Ueberschuss 218.
    _ix_npc = _sc7u.findData("npc")
    _sc7u.setCurrentIndex(_ix_npc)
    _app.processEvents()
    _plan_d = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    eq("b7u NPC-Station: 278 je Portion -> Ueberschuss 218",
       dict(_plan_d.get("surplus") or {}), {200: 218})
    check("b7u ... und die Karte nennt die Basis 50.0 %",
          any("50.0" in (lb.text() or "") for lb in _dlg7u.findChildren(QLabel)))
    # IMPLANTAT (Nutzer 18.09.2026: "Implantate muessen erkannt werden ...
    # Button implants laden"): Knopf in der Karte, ESI-Abruf gegen die SDE-
    # Tabelle, Ergebnis in Ausbeute und Zeile. 0.83854 x 1.04 = 0.87208 ->
    # floor(400 x 0.87208) = 348 je Portion -> Ueberschuss 288.
    _sc7u.setCurrentIndex(_sc7u.findData("s7u"))
    _app.processEvents()
    _alt_run7u = win._run
    _alt_imp7u = esi.fetch_character_implants
    _alt_repimp7u = I.reprocess_implants
    _alt_set_imp7u = win.settings.get("bau_char_reproc_implant")
    _alt_cid7u = win.settings.get("client_id")
    try:
        win.settings["client_id"] = win.settings.get("client_id") or "test-client-7u"
        win._run = lambda worker, done_cb, fail_cb=None, **kw: done_cb(
            worker._fn(*worker._args, **worker._kwargs))
        esi.fetch_character_implants = lambda c, cid: [27174, 99999]
        I.reprocess_implants = lambda: {27174: {"name": "Zainou 'Beancounter' Reprocessing RX-804",
                                                "attr": "refiningYieldMutator", "value": 4.0}}
        _btn_imp = getattr(win, "_bd_reprocess_imp_btn", None)
        check("b7u die Karte hat den Knopf 'Load implants'",
              _btn_imp is not None and _btn_imp.text().strip() == _t4("Load implants"))
        _btn_imp.click()
        _app.processEvents()
        eq("b7u das Implantat ist gespeichert (RX-804, 4 %)",
           (win.settings.get("bau_char_reproc_implant") or {}).get("1", {}).get("pct"), 4.0)
        check("b7u ... und die Zeile nennt Charakter und Implantat",
              "Peanut Motor" in win._bd_reprocess_imp_lbl.text()
              and "RX-804" in win._bd_reprocess_imp_lbl.text()
              and "+4" in win._bd_reprocess_imp_lbl.text())
        _plan_i = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
        eq("b7u ... und die Ausbeute steigt: 348 je Portion -> Ueberschuss 288",
           (dict(_plan_i.get("surplus") or {}), round(_plan_i["reprocess"]["schritte"][0]["ausbeute"], 5)),
           ({200: 288}, 0.87208))
    finally:
        win._run = _alt_run7u
        if _alt_cid7u is None:
            win.settings.pop("client_id", None)
        else:
            win.settings["client_id"] = _alt_cid7u
        esi.fetch_character_implants = _alt_imp7u
        I.reprocess_implants = _alt_repimp7u
        if _alt_set_imp7u is None:
            win.settings.pop("bau_char_reproc_implant", None)
        else:
            win.settings["bau_char_reproc_implant"] = _alt_set_imp7u
    # OHNE SDE-DATEN: keine geratene Basis, Warnung statt Rechnung.
    _sc7u.setCurrentIndex(_sc7u.findData("s7u"))
    I.reprocess_struktur_sde = lambda: {"bonus": {}, "rig": {}}
    _cb7u.click(); _app.processEvents()          # aus
    _cb7u.click(); _app.processEvents()          # an, jetzt ohne SDE
    _plan_e = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    eq("b7u ohne SDE-Daten: kein Tausch, Grund 'sde'",
       (dict(_plan_e.get("buy") or {}), (_plan_e.get("reprocess") or {}).get("grund")),
       ({200: 60}, "sde"))
    check("b7u ... und der Tab warnt statt zu schweigen",
          "Load recipes" in _info7u())
    # Die Texte sind zweisprachig hinterlegt.
    from eve_trader import sprache as _sp7u
    for _k7u in ("Buy compressed ore instead of minerals", "Reprocess at",
                 "Structure base {pct} %", "saves {isk} \u00b7 {n} ores",
                 "reprocess \u2192 {out} \u00b7 {pct} %", "Compressed ore \u267b"):
        check(f"b7u deutsche Fassung: {_k7u[:30]}", _k7u in _sp7u.KATALOG["de"])
except Exception as _e7u:                                # pragma: no cover
    _fail.append(f"b7u Reprocessing im Bauplan: {type(_e7u).__name__}: {_e7u}")
finally:
    I.reprocess_map = _alt7u["map"]; I.item_category_map = _alt7u["cats"]
    I.reprocess_struktur_sde = _alt7u["sde"]; I.reprocess_skill_ids = _alt7u["ids"]
    I.reprocess_erz_skill = _alt7u["erz"]; store.list_characters = _alt7u["chars"]
    config.save_settings = _alt7u["save"]; esi.resolve_names = _alt7u["names"]
    for _k, _v in _alt_set7u.items():
        if _v is None:
            win.settings.pop(_k, None)
        else:
            win.settings[_k] = _v
    try:
        if _dlg7u is not None:
            _dlg7u.close()
            _app.processEvents()
    except Exception:
        pass


# ---------------------------------------------------------------- (b7w)
# REPROCESSING IM BAUPLAN, WEG A (1.0.9, Nutzer 19.09.2026 "erraten und
# einfuegen" -> "ja"): Schalter "Unrefined-Reaktionen nutzen" in der Karte,
# Rezept-Kopie im Dialog (X ueber die Unrefined-Formel), Block im Runplaner
# NACH der Reaktionsstufe, Rezeptbaum "ueber ...", Blueprint-Name der
# Unrefined-Formel, Ruecklaeufer-Gutschrift als eigene Kostenzeile.
# Rechnung: 10 Testship <- 100 Testmat (X). Normal: 5 Fuel + 100 A + 100 B
# -> 200 X = 10'502.5 je X. Unrefined Testmat (U): 5 Fuel + 100 A + 100 C
# -> 1 U -> Reprocessing 36 X + 100 A je Stueck. SCRAPMETAL-PFAD (gemessen
# 19.09.2026): 0.50 x (1 + 0.02 x 3) = 0.53 -> 19 X + 53 A je Run; die
# Struktur-Basis der Tatara zaehlt NICHT. Je X: (500 + 100'000 + 5'000 -
# 53'000) / 19 = 2'763.16 -> Unrefined gewinnt. 100 X -> 6 Runs (114 X,
# 14 Ueberschuss), Ruecklaeufer 318 A = 318'000 ISK Gutschrift.
_alt7w = {
    "map": I.reprocess_map, "cats": I.item_category_map, "sde": I.reprocess_struktur_sde,
    "ids": I.reprocess_skill_ids, "erz": I.reprocess_erz_skill,
    "chars": store.list_characters, "save": config.save_settings,
    "names": esi.resolve_names, "groups": I.group_names,
}
_alt_set7w = {k: win.settings.get(k) for k in
              ("bau_reprocess_on", "bau_unrefined_on", "bau_reprocess_struct",
               "bau_structures", "bau_char_skills", "bau_build_chars",
               "bau_reaction_chars")}
_FU7, _A7, _B7, _C7, _X7, _U7 = 4051, 301, 302, 303, 200, 32999


class _RecipesU7w:
    """1 Testship <- 10 X; X normal aus A+B (200 je Run); U aus A+C (1 je Run)."""
    product_to_bp = {100: (900, I.MANUFACTURING, 1), _X7: (5000, I.REACTION, 200),
                     _U7: (5001, I.REACTION, 1)}
    bp_materials = {(900, I.MANUFACTURING): [(_X7, 10)],
                    (5000, I.REACTION): [(_FU7, 5), (_A7, 100), (_B7, 100)],
                    (5001, I.REACTION): [(_FU7, 5), (_A7, 100), (_C7, 100)]}
    activity_time = {(900, I.MANUFACTURING): 60, (5000, I.REACTION): 10800,
                     (5001, I.REACTION): 21600}
    activity_max_runs = {}
    reaction_products = {_X7, _U7}
    invention_for_bpc = {}
    bp_products = {}
    item_cat = {}

    def is_manufactured(self, t):
        return t == 100


_namen7w = {100: "Testship", _X7: "Testmat", _U7: "Unrefined Testmat", _FU7: "Fuel",
            _A7: "Alpha", _B7: "Beta", _C7: "Gamma"}
I.reprocess_map = lambda: {_U7: {"portion": 1, "out": {_X7: 36, _A7: 100}}}
I.item_category_map = lambda: {_X7: (4, 428, 0), _U7: (4, 428, 0), 100: (6, 25, 0),
                               _A7: (4, 427, 0), _B7: (4, 427, 0), _C7: (4, 427, 0),
                               _FU7: (4, 1136, 0)}
I.reprocess_struktur_sde = lambda: {
    "bonus": {"Tatara": 5.5},
    "rig": {46639: {"name": "Standup L-Set Reprocessing Monitor I", "mult": 0.51,
                    "hi": 1.0, "low": 1.06, "null": 1.12}}}
I.reprocess_skill_ids = lambda: {"Reprocessing": 3385, "Reprocessing Efficiency": 3389,
                                 "Scrapmetal Processing": 12196}
I.reprocess_erz_skill = lambda: {}
I.group_names = lambda ids: {int(i): "Intermediate Materials" for i in ids}
store.list_characters = lambda: [{"character_id": 1, "character_name": "Peanut Motor"}]
config.save_settings = lambda s: None
esi.resolve_names = lambda ids: {int(i): _namen7w.get(int(i), f"#{i}") for i in ids}
_dlg7w = None
try:
    win.settings["bau_structures"] = [{"id": "s7w", "name": "R&R Yard", "type": "tatara",
                                       "rigs": ["sde:46639", "", ""], "security": 2.1}]
    win.settings["bau_reprocess_struct"] = "s7w"
    win.settings["bau_reprocess_on"] = False
    win.settings["bau_unrefined_on"] = True
    win.settings["bau_char_skills"] = {"1": {"3385": 5, "3389": 5, "12196": 3}}
    win.settings["bau_build_chars"] = [1]
    win.settings["bau_reaction_chars"] = [1]
    _pr7w = {_FU7: 100.0, _A7: 1000.0, _B7: 20000.0, _C7: 50.0, _X7: 12000.0,
             100: 999999.0}
    win._bd_pricemap = dict(_pr7w)
    win._bd_recipes = _RecipesU7w()
    win._bd_recipes_basis = _RecipesU7w()
    win._bd_opts = {"me": 0, "te": 0, "job_pct": 0, "build_reactions": True,
                    "tree_depth": 4}
    _ro7w = win._reprocess_opts() or {}
    eq("b7w opts: Weg A an, Weg B aus, gemessene Basis",
       (_ro7w.get("unrefined"), _ro7w.get("on"), round(_ro7w.get("basis") or 0, 6)),
       (True, False, 0.602616))
    win._bd_opts["reprocess"] = _ro7w
    win._bd_type = 100
    win._bd_qty = 10
    _plan7w0 = I.production_plan(100, 10, _pr7w.get, _RecipesU7w(), dict(win._bd_opts))
    _tree7w0 = I.build_tree(100, _pr7w.get, _RecipesU7w(), dict(win._bd_opts))
    _res7w = {"tree": _tree7w0, "names": dict(_namen7w),
              "sell": 999999.0, "sell_is_contract": False, "plan": _plan7w0}
    _sbd_frisch(100, "Testship", _res7w)
    _dlg7w = getattr(win, "_bd_dialog", None)
    _app.processEvents()
    _ucb7w = getattr(win, "_bd_unrefined_cb", None)
    check("b7w die Karte hat den Weg-A-Schalter, und er ist an",
          _ucb7w is not None and _ucb7w.isChecked())
    _ulbl7w = getattr(win, "_bd_unrefined_lbl", None)
    eq("b7w ... und die Zeile nennt 53.0 %, den Charakter und '1 intermediates'",
       _ulbl7w.text() if _ulbl7w is not None else None,
       _t4("Unrefined: {pct} % · {char} (50 % × Scrapmetal Processing, "
           "structure does not apply)").format(pct="53.0", char="Peanut Motor")
       + "\n♻ " + _t4("{n} intermediates via unrefined reaction").format(n=1))
    _sc7w = getattr(win, "_bd_reprocess_struct_cb", None)
    check("b7w die Struktur-Auswahl ist auch ohne Weg B aktiv",
          _sc7w is not None and _sc7w.isEnabled())
    # DIE REZEPT-KOPIE: X laeuft ueber die Unrefined-Formel mit 27 je Run.
    eq("b7w die Wahl faellt auf X (19 X + 53 A je Run, Charakter 1)",
       {k: (v["out_je_run"], v["zurueck_je_run"], v["char"])
        for k, v in (getattr(win, "_bd_unrefined", None) or {}).items()},
       {_X7: (19, {_A7: 53}, 1)})
    eq("b7w ... und die Dialog-Rezepte bauen X ueber 5001",
       win._bd_recipes.product_to_bp.get(_X7), (5001, I.REACTION, 19))
    eq("b7w ... die Basis-Rezepte bleiben, wie sie sind",
       win._bd_recipes_basis.product_to_bp.get(_X7), (5000, I.REACTION, 200))
    _plan7w = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    eq("b7w der Plan: 6 Runs X, Einkauf Fuel/A/C der Unrefined-Formel (kein B)",
       (_plan7w.get("build_runs", {}).get(_X7),
        {k: int(v) for k, v in (_plan7w.get("buy") or {}).items()}),
       (6, {_FU7: 30, _A7: 600, _C7: 600}))
    _st7w = [s for s in ((_plan7w.get("reprocess") or {}).get("schritte") or [])]
    eq("b7w ... ein Unrefined-Schritt: 6 x U -> 100 X, 318 A zurueck, 318'000 Gutschrift, 53 %",
       [(s.get("art"), s.get("erz"), s.get("menge"), s.get("deckt"), s.get("ueberschuss"),
         s.get("kredit"), round(float(s.get("ausbeute") or 0), 6)) for s in _st7w],
       [("unrefined", _U7, 6, {_X7: 100}, {_A7: 318}, 318000.0, 0.53)])
    eq("b7w ... total_cost = Einkauf (3'000 + 600'000 + 30'000) minus 318'000",
       round(float(_plan7w.get("total_cost") or 0)), 315000)
    eq("b7w ... mat_cost bleibt die volle Einkaufsliste",
       round(float(_plan7w.get("mat_cost") or 0)), 633000)
    eq("b7w ... die Wahl reist im Plan mit (Einfrieren)",
       sorted(_plan7w.get("unrefined") or {}), [_X7])
    # RUNPLANER: Reaktionsstufe mit X (4 Runs), DANACH der Block mit U.
    _tr7w = getattr(win, "_sched_tree_ref", None)
    _tops7w = [_tr7w.topLevelItem(i).text(0) for i in range(_tr7w.topLevelItemCount())] \
        if _tr7w is not None else []
    # EIGENE STUFE "2. Unrefined reactions" (Nutzer 19.09.2026: "an erster
    # Stelle ueber den Intermediate Reactions"), der Job heisst nach dem
    # Unrefined-Produkt, der Reprocessing-Block folgt direkt danach.
    _ix_re7w = next((i for i, x in enumerate(_tops7w)
                     if x.startswith("2. " + _t4("Unrefined reactions"))), None)
    _ix_ub7w = next((i for i, x in enumerate(_tops7w)
                     if _t4("Reprocessing of unrefined products") in x), None)
    check("b7w der Runplaner hat die Stufe '2. Unrefined reactions' und den Block direkt danach",
          _ix_re7w is not None and _ix_ub7w == _ix_re7w + 1
          and "R&R Yard" not in _tops7w[_ix_ub7w])
    check("b7w ... und keine Stufe 'Reactions - Intermediate' (X laeuft nur unrefined)",
          not any(_t4("Reactions \u2013 Intermediate") in x for x in _tops7w))
    _st7w_times = getattr(win, "_bd_last_stage_times", None) or {}
    check("b7w ... die Stufenzeit 'unrefined' ist gesetzt (6 Runs a 6 h auf 1 Slot = 36 h)",
          float(_st7w_times.get("unrefined", 0) or 0) > 0)
    check("b7w ... mit 'Base 50 % x Scrapmetal Processing' statt der Struktur-Basis",
          _ix_ub7w is not None
          and _tr7w.topLevelItem(_ix_ub7w).text(4) == _t4("Base 50 % × Scrapmetal Processing"))
    check("b7w ... und keine Stufe 0 (nichts wird als Erz gekauft)",
          not any(x.startswith("0. ") for x in _tops7w))

    def _zeilen7w():
        out = []
        if _tr7w is None:
            return out
        _root = _tr7w.invisibleRootItem()
        _st = [_root.child(i) for i in range(_root.childCount())]
        while _st:
            _x = _st.pop()
            out.append((tuple(_x.text(c) for c in range(_tr7w.columnCount())), _x))
            _st += [_x.child(i) for i in range(_x.childCount())]
        return out
    _z7w = _zeilen7w()
    check("b7w ... Charakterzeile '6 units', Zeile 'Unrefined Testmat' 6 -> 100 Testmat, 53.0 %, +318 Alpha",
          any(z[0] == "Peanut Motor" and z[2] == _t4("{n} units").format(n=6) for z, _ in _z7w)
          and any(z[0] == "Unrefined Testmat" and z[1] == "6"
                  and z[4] == "→ 100 Testmat  ·  53.0 %" and z[5] == "+318 Alpha"
                  for z, _ in _z7w))
    _row_u7w = next((it for z, it in _z7w if z[0] == "Unrefined Testmat"), None)
    check("b7w ... Klick auf die Zeile kopiert 'Unrefined Testmat'",
          _row_u7w is not None and _row_u7w.data(0, _RKN7f) == "Unrefined Testmat")
    # Der Reaktions-Job selbst: X mit 4 Runs, Blueprint-Name = Unrefined-Formel.
    _row_x7w = next((it for z, it in _z7w if z[0] == "Unrefined Testmat" and z[1] == "6"
                     and it is not _row_u7w), None)
    check("b7w der Reaktions-Job heisst 'Unrefined Testmat' (das, was man baut)",
          _row_x7w is not None)
    eq("b7w der Reaktions-Job traegt den Namen der Unrefined-Formel zum Kopieren",
       _row_x7w.data(0, _RKN7f) if _row_x7w is not None else None,
       "Unrefined Testmat Reaction Formula")
    # Blueprint-Tab: die Zeile heisst nach dem Unrefined-Produkt.
    _bpt7w = getattr(win, "_bd_bp_tab_tbl", None)
    _bp_namen7w = [_bpt7w.item(i, 0).text() for i in range(_bpt7w.rowCount())
                   if _bpt7w.item(i, 0) is not None] if _bpt7w is not None else []
    check("b7w der Blueprint-Tab nennt 'Unrefined Testmat' statt 'Testmat'",
          any("Unrefined Testmat" in n for n in _bp_namen7w)
          and not any(n.strip() == "Testmat" for n in _bp_namen7w))
    # Rezeptbaum: X sagt "ueber Unrefined Testmat".
    _tw7w = getattr(win, "_bd_tree_widget", None) or _dlg7w.findChild(QTreeWidget)

    def _baum7w(w):
        out = []
        if w is None:
            return out
        _root = w.invisibleRootItem()
        _st = [_root.child(i) for i in range(_root.childCount())]
        while _st:
            _x = _st.pop()
            out.append(tuple(_x.text(c) for c in range(w.columnCount())))
            _st += [_x.child(i) for i in range(_x.childCount())]
        return out
    _bz7w = []
    for _w7 in _dlg7w.findChildren(QTreeWidget):
        _bz7w += _baum7w(_w7)
    check("b7w der Rezept-Baum sagt bei Testmat 'BUILD - 6 runs - via Unrefined Testmat'",
          any(z[0] == "Testmat" and _t4("via {formula} ♻").format(
              formula="Unrefined Testmat") in " ".join(z) and "6" in " ".join(z)
              for z in _bz7w))
    # Materials-Tab: Ruecklaeufer-Zeile mit Gutschrift, Annahme genannt.
    _info7w = (getattr(win, "_bd_mat_tab_info", None).text()
               if getattr(win, "_bd_mat_tab_info", None) is not None else "")
    check("b7w der Materials-Tab traegt keinen Unrefined-Textblock mehr",
          "Unrefined Testmat" not in _info7w and "318" not in _info7w)
    # Kostenzeile: Ruecklaeufer sichtbar.
    _rl7w = (getattr(win, "_bd_detail_val_lbls", None) or {}).get("− Rückläufer")
    check("b7w die Kostenzeile 'Ruecklaeufer' ist sichtbar und nennt 318'000",
          _rl7w is not None and not _rl7w.isHidden() and "318" in _rl7w.text())
    # NACH "RECALCULATE" (Orderbuch-Ladder; Nutzer-Befund 19.09.2026: Plan mit
    # Unrefined 139.8 statt 127.6 M je Stueck - die Gutschrift fehlte NUR in
    # der Summe, die dieser Zweig neu aufbaut). Orderbuch = dieselben Preise;
    # Gesamt muss Ladder + Job + Bestand - 318'000 sein.
    win._bd_ladder_result = {"qty": 10, "_orderbooks": {_FU7: [(100.0, 100)],
                                                        _A7: [(1000.0, 1000)],
                                                        _C7: [(50.0, 1000)]},
                             "mat_cost_ladder": 633000.0, "short_materials": []}
    # DER SCHALTER HOLT DIE ORDERBUECHER SELBST NACH (Nutzer 19.09.2026: "ich
    # moechte nicht Recalculate druecken"): je Klick ein Hintergrund-Job mit
    # dem Ladder-Etikett. Attrappe zaehlt nur, laeuft nichts (kein Netz).
    _laeufe7w = []
    _alt_run7w = win._run
    win._run = lambda _w, _done, fail_cb=None, **_k: _laeufe7w.append(_k.get("label"))
    _ucb7w.click(); _app.processEvents(); _ucb7w.click(); _app.processEvents()
    win._run = _alt_run7w
    eq("b7w jeder Schalter-Klick holt die Orderbuch-Preise nach (2 Klicks = 2 Abrufe)",
       [_l for _l in _laeufe7w if _l == _t4("Order book prices \u2026")],
       [_t4("Order book prices \u2026")] * 2)
    _plan7w_l = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    from eve_trader.ui.mw_basis import isk as _isk7w
    _lb7w = getattr(win, "_bd_detail_val_lbls", None) or {}
    eq("b7w Ladder: Gesamt-Baukosten ziehen die Gutschrift ab",
       _lb7w["= Baukosten gesamt"].text(),
       _isk7w(633000.0 + float(_plan7w_l.get("job_cost") or 0)
              + float(_plan7w_l.get("stock_cost") or 0)
              + float(_plan7w_l.get("inv_cost") or 0) - 318000.0, suffix=False))
    win._bd_ladder_result = None
    # Restbedarf: U wird nie gekauft; die Einkaufsliste ist die der Formel.
    eq("b7w Restbedarf ohne U (wird gebaut, nie gekauft; X braucht das Endprodukt)",
       sorted(win._restbedarf_jetzt()), [_X7, _A7, _C7, _FU7])
    # SCHALTER AUS: exakt der alte Plan (1 Run normal, B gekauft, kein Block).
    _ucb7w.click(); _app.processEvents()
    _plan7w_b = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    # Ohne Weg A kauft der Plan X: ein Run der normalen Formel (200 Stueck,
    # 2'100'500 ISK) ist teurer als 100 x 12'000 - Batch-Rundung, wie immer.
    eq("b7w Schalter aus: X wird gekauft (normale Formel zu grob), kein Schritt",
       (_plan7w_b.get("build_runs", {}).get(_X7),
        {k: int(v) for k, v in (_plan7w_b.get("buy") or {}).items()},
        (_plan7w_b.get("reprocess") or {}).get("schritte"),
        win._bd_recipes.product_to_bp.get(_X7)),
       (None, {_X7: 100}, None, (5000, I.REACTION, 200)))
    eq("b7w ... Einstellung gespeichert", win.settings.get("bau_unrefined_on"), False)
    _tops7w_b = [_tr7w.topLevelItem(i).text(0) for i in range(_tr7w.topLevelItemCount())]
    check("b7w ... und der Unrefined-Block ist weg",
          not any(_t4("Reprocessing of unrefined products") in x for x in _tops7w_b))
    check("b7w ... Kostenzeile 'Ruecklaeufer' versteckt",
          _rl7w is not None and _rl7w.isHidden())
    # WIEDER AN: gleiche Wahl wie beim ersten Mal.
    _ucb7w.click(); _app.processEvents()
    _plan7w_c = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    eq("b7w wieder an: 6 Runs ueber die Unrefined-Formel",
       (_plan7w_c.get("build_runs", {}).get(_X7), win._bd_recipes.product_to_bp.get(_X7)),
       (6, (5001, I.REACTION, 19)))
    # RUNS JE JOB DECKELN (Nutzer 19.09.2026, Einherji II: "17 Stueck mit
    # einem Blueprint ... gibts maximal 10 runs"): ohne Limit 1 Blueprint
    # mit 6 Runs; mit Limit 4 je Job (SDE maxProductionLimit, dieselbe
    # Quelle wie BPC-Runs) zwei Blaupausen 4 + 2 auf demselben Slot.
    def _bp_knoepfe7w(zeilen, runs):
        """Texte der Blaupausen-Knoepfe (Spalte 2) der Reaktions-Job-Zeile
        mit `runs` Runs - dazu der Name der Charakterzeile darueber."""
        from PySide6.QtWidgets import QPushButton as _PB7w, QLabel as _QL7w
        for z, it in zeilen:
            if z[0] != "Unrefined Testmat" or z[1] != runs or not z[4].startswith(
                    _t4("Unrefined reaction")):
                continue
            _w = _tr7w.itemWidget(it, 2)
            if _w is None:
                return None
            _lay = _w.layout()
            out = []
            for i in range(_lay.count()):
                _c = _lay.itemAt(i).widget()
                if isinstance(_c, (_PB7w, _QL7w)):
                    out.append(_c.text())
            return (it.parent().text(0) if it.parent() is not None else None, out)
        return None
    eq("b7w Runplaner ohne Limit: 1 Blueprint mit 6 Runs",
       _bp_knoepfe7w(_zeilen7w(), "6"),
       ("Peanut Motor", [_t4("{n} blueprints").format(n=1), "1\u00d7", "6"]))
    win._bd_recipes.activity_max_runs[(5001, I.REACTION)] = 4
    _ucb7w.click(); _app.processEvents(); _ucb7w.click(); _app.processEvents()
    # GANZE KOPIEN + WELLEN (Nutzer 19.09.2026): 6 Runs mit Limit 4 auf EINEM
    # Reaktions-Slot = Kopie 4 in Welle 1, Kopie 2 als zweite Auflistung
    # "Peanut Motor · Welle 2".
    eq("b7w Runplaner mit Limit 4 je Job, 1 Slot: Welle 1 = eine Kopie mit 4 Runs",
       _bp_knoepfe7w(_zeilen7w(), "4"),
       ("Peanut Motor", [_t4("{n} blueprints").format(n=1), "1\u00d7", "4"]))
    eq("b7w ... Welle 2 = zweite Auflistung des Charakters mit der Kopie 2",
       _bp_knoepfe7w(_zeilen7w(), "2"),
       ("Peanut Motor  \u00b7  " + _t4("wave {n}").format(n=2),
        [_t4("{n} blueprints").format(n=1), "1\u00d7", "2"]))
    _w2_7w = next((it for z, it in _zeilen7w() if z[0] == "Unrefined Testmat" and z[1] == "2"
                   and z[4].startswith(_t4("Unrefined reaction"))), None)
    check("b7w ... die Welle-2-Zeile hat einen eigenen Haken-Schluessel (|w2)",
          _w2_7w is not None and str(_w2_7w.data(0, Qt.UserRole + 6)).endswith("|w2")
          and _w2_7w.parent() is not None
          and str(_w2_7w.parent().data(0, Qt.UserRole + 6)).endswith("|w2"))
    win._bd_recipes.activity_max_runs.pop((5001, I.REACTION), None)
    # OHNE SCRAPMETAL-SKILL: 50 % flach -> 18 X + 50 A je Run (Stufe 0 zaehlt,
    # nicht "fehlt"); OHNE STRUKTUR-DATEN laeuft Weg A trotzdem (Basis egal).
    win.settings["bau_char_skills"] = {"1": {"3385": 5, "3389": 5}}
    I.reprocess_struktur_sde = lambda: {"bonus": {}, "rig": {}}
    _ucb7w.click(); _app.processEvents(); _ucb7w.click(); _app.processEvents()
    eq("b7w ohne Scrapmetal-Skill und ohne Struktur-Daten: 18 X + 50 A je Run, 50 %",
       ({k: (v["out_je_run"], v["zurueck_je_run"]) for k, v in win._bd_unrefined.items()},
        win._bd_recipes.product_to_bp.get(_X7),
        win._bd_opts.get("reprocess", {}).get("basis")),
       ({_X7: (18, {_A7: 50})}, (5001, I.REACTION, 18), None))
    check("b7w ... die Karte warnt NICHT vor fehlenden Struktur-Daten (Weg B ist aus)",
          "Load recipes" not in (getattr(win, "_bd_mat_tab_info", None).text()
                                 if getattr(win, "_bd_mat_tab_info", None) is not None else ""))
    win.settings["bau_char_skills"] = {"1": {"3385": 5, "3389": 5, "12196": 3}}
    I.reprocess_struktur_sde = lambda: {
        "bonus": {"Tatara": 5.5},
        "rig": {46639: {"name": "Standup L-Set Reprocessing Monitor I", "mult": 0.51,
                        "hi": 1.0, "low": 1.06, "null": 1.12}}}
    _ucb7w.click(); _app.processEvents(); _ucb7w.click(); _app.processEvents()
    # TEURER INPUT (C = 5'000): Unrefined verliert, Zeile "nicht guenstiger".
    win._bd_pricemap[_C7] = 5000.0
    _ucb7w.click(); _app.processEvents(); _ucb7w.click(); _app.processEvents()
    _plan7w_d = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or {}
    _info7w_d = (getattr(win, "_bd_mat_tab_info", None).text()
                 if getattr(win, "_bd_mat_tab_info", None) is not None else "")
    check("b7w teurer Input: kein Unrefined-Weg, und die Karte sagt warum (Tooltip +% fuer Testmat)",
          _plan7w_d.get("build_runs", {}).get(_X7) is None
          and win._bd_recipes.product_to_bp.get(_X7) == (5000, I.REACTION, 200)
          and "Testmat (+" in (_ulbl7w.toolTip() if _ulbl7w is not None else "")
          and _t4("no unrefined reaction is cheaper") in (_ulbl7w.text() if _ulbl7w is not None else ""))
    win._bd_pricemap[_C7] = 50.0
    # Die Texte sind zweisprachig hinterlegt.
    from eve_trader import sprache as _sp7w
    for _k7w in ("Use unrefined reactions where cheaper",
                 "Base 50 % × Scrapmetal Processing",
                 "Reprocessing of unrefined products", "via {formula} ♻",
                 "Unrefined reaction not cheaper for: {liste}",
                 "− Returned (reprocessing)"):
        check(f"b7w deutsche Fassung: {_k7w[:30]}", _k7w in _sp7w.KATALOG["de"])
except Exception as _e7w:                                # pragma: no cover
    import traceback as _tb7w
    _tb7w.print_exc()
    _fail.append(f"b7w Unrefined im Bauplan: {type(_e7w).__name__}: {_e7w}")
finally:
    I.reprocess_map = _alt7w["map"]; I.item_category_map = _alt7w["cats"]
    I.reprocess_struktur_sde = _alt7w["sde"]; I.reprocess_skill_ids = _alt7w["ids"]
    I.reprocess_erz_skill = _alt7w["erz"]; store.list_characters = _alt7w["chars"]
    config.save_settings = _alt7w["save"]; esi.resolve_names = _alt7w["names"]
    I.group_names = _alt7w["groups"]
    for _k, _v in _alt_set7w.items():
        if _v is None:
            win.settings.pop(_k, None)
        else:
            win.settings[_k] = _v
    win._bd_recipes_basis = None
    win._bd_unrefined = {}
    win._bd_ladder_result = None
    try:
        if _dlg7w is not None:
            _dlg7w.close()
            _app.processEvents()
    except Exception:
        pass


# ---------------------------------------------------------------- (b7v)
# FRACHT + ORDERBUCH-LADDER (Befund 18.09.2026 am Compressed-Ore-Vergleich):
# mit "Fracht entscheidet mit" UND aktiver Ladder fehlte der Frachtdienst in
# Gesamtkosten und Gewinn - die Ladder rechnet reine Orderbuchpreise, der
# Abzug in der Material-Zeile nahm aber an, die Fracht stecke drin. Beim
# Nutzer: Gewinn ohne Erz -93 Mio, obwohl 372 Mio Frachtdienst anfallen.
# Rechnung hier: 60 Testmat x 100 ISK (Orderbuch) = 6'000; Volumen 60 x
# 0.01 m3 x 445 ISK/m3 = 267 Fracht. Gesamt muss die 267 enthalten, die
# Material-Zeile zeigt die 6'000 OHNE Fracht.
_alt_set7v = {k: win.settings.get(k) for k in
              ("bau_transport_rate", "bau_freight_in_decision", "bau_reprocess_on")}
_alt_vol7v = win._item_volumes_with_esi_fix
_alt_save7v = config.save_settings
config.save_settings = lambda s: None
_dlg7v = None
try:
    win.settings["bau_transport_rate"] = 445.0
    win.settings["bau_freight_in_decision"] = True
    win.settings["bau_reprocess_on"] = False
    win._item_volumes_with_esi_fix = lambda ids: ({200: 0.01, 100: 1.0}, [])
    win._bd_pricemap = dict(PRICES)
    win._bd_recipes = _Recipes()
    win._bd_opts = {"me": 0, "te": 0, "job_pct": 0, "build_reactions": False,
                    "tree_depth": 4, "stock": {200: 40}}
    win._bd_type = 100
    win._bd_qty = 10
    _plan7v = I.production_plan(100, 10, PRICES.get, _Recipes(), dict(win._bd_opts))
    _tree7v = I.build_tree(100, PRICES.get, _Recipes(), dict(win._bd_opts))
    _res7v = {"tree": _tree7v, "names": {100: "Testship", 200: "Testmat"},
              "sell": 6000.0, "sell_is_contract": False, "plan": _plan7v}
    # Orderbuch-Ladder wie nach "Neu berechnen": 100 ISK je Testmat, aber
    # nur 45 Stueck im Buch (60 gebraucht) - der Rest zum teuersten Angebot.
    win._bd_ladder_result = {"qty": 10, "_orderbooks": {200: [(100.0, 45)]},
                             "mat_cost_ladder": 6000.0, "short_materials": []}
    _sbd_frisch(100, "Testship", _res7v)
    _dlg7v = getattr(win, "_bd_dialog", None)
    _app.processEvents()
    _lb7v = getattr(win, "_bd_detail_val_lbls", None) or {}
    _plan_v = (getattr(win, "_bd_plan_cache", None) or (None, None))[1] or _plan7v
    _jc7v = float(_plan_v.get("job_cost") or 0.0)
    _sc7v = float(_plan_v.get("stock_cost") or 0.0)
    _iv7v = float(_plan_v.get("inv_cost") or 0.0)
    from eve_trader.ui.mw_basis import isk as _isk7v
    eq("b7v Material-Zeile = Orderbuch ohne Fracht (6'000)",
       _lb7v["Material"].text(), _isk7v(6000.0, suffix=False))
    eq("b7v Frachtdienst-Zeile = 267", _lb7v["Frachtdienst"].text(), _isk7v(267.0, suffix=False))
    eq("b7v Gesamt-Baukosten ENTHALTEN die Fracht",
       _lb7v["= Baukosten gesamt"].text(),
       _isk7v(6000.0 + 267.0 + _jc7v + _sc7v + _iv7v, suffix=False))
    # AUSVERKAUFT (Nutzer 18.09.2026: "was macht der Bauplan, wenn in Jita
    # etwas nicht da ist?"): der Materialien-Tab nennt das Material mit
    # "da / gebraucht" - nicht nur eine Zahl im Tooltip.
    _il7v = getattr(win, "_bd_mat_tab_info", None)
    _txt7v = _il7v.text() if _il7v is not None else ""
    check("b7v der Materialien-Tab warnt: Testmat 45 / 60 am Hub",
          "Testmat 45 / 60" in _txt7v and _il7v.isVisible() is not None)
    eq("b7v ... und die Knappheit ist am Dialog gemerkt",
       [(int(x["type_id"]), int(x["available"]), int(x["needed"]))
        for x in (getattr(win, "_bd_ladder_shorts", None) or [])], [(200, 45, 60)])
except Exception as _e7v:                                # pragma: no cover
    _fail.append(f"b7v Fracht in der Ladder: {type(_e7v).__name__}: {_e7v}")
finally:
    win._item_volumes_with_esi_fix = _alt_vol7v
    config.save_settings = _alt_save7v
    win._bd_ladder_result = None
    for _k, _v in _alt_set7v.items():
        if _v is None:
            win.settings.pop(_k, None)
        else:
            win.settings[_k] = _v
    try:
        if _dlg7v is not None:
            _dlg7v.close()
            _app.processEvents()
    except Exception:
        pass


# ---------------------------------------------------------------- (b80)
# PREISVERLAUF: VERVOLLSTAENDIGUNG UEBER ALLE NAMEN + START MIT GRAPH
# (Nutzer 18.09.2026: "zeigt nicht alle Items wenn ich anfange zu tippen"
# und "standardmaessig sollte ein Item aufgehen"). Die Combo-Liste bleibt
# der Bestand; der Completer hat ein eigenes Modell mit dem Namens-Cache.
try:
    from PySide6.QtWidgets import QCompleter as _QC80
    from eve_trader import store as _st80
    _geplottet80 = []
    _alt_plot80 = win._do_plot
    _alt_names80 = _st80.all_names
    try:
        win._do_plot = lambda tid: _geplottet80.append(int(tid))
        _st80.all_names = lambda: {990001: "Acolyte II Probe", 990002: "Acolyte I Probe",
                                   990003: "Warrior II Probe", 990004: "Acolyte II"}
        win._mk_namen_laden()
        _liste80 = win._mk_namen_modell.stringList()
        check("b80 der Completer kennt Namen, die NICHT im Bestand sind",
              "Acolyte II Probe" in _liste80 and "Warrior II Probe" in _liste80)
        _c80 = win.mk_item.completer()
        check("b80 der Completer haengt am Namens-Modell (nicht an der Combo)",
              _c80 is not None and _c80.model() is win._mk_namen_modell)
        check("b80 Teilwort reicht (MatchContains, Gross/Klein egal)",
              _c80.filterMode() == Qt.MatchContains
              and _c80.caseSensitivity() == Qt.CaseInsensitive)
        _c80.setCompletionPrefix("acoly")
        _treffer80 = [_c80.completionModel().index(i, 0).data()
                      for i in range(_c80.completionModel().rowCount())]
        check(f"b80 'acoly' findet beide Acolyte-Probe ({_treffer80})",
              set(_treffer80) >= {"Acolyte II Probe", "Acolyte I Probe"})
        # Auswahl aus der Vervollstaendigung -> Combo + Zeichnen
        win._mk_name_gewaehlt("Warrior II Probe")
        check("b80 Auswahl landet in der Combo und wird gezeichnet",
              win.mk_item.currentData() == 990003 and _geplottet80[-1:] == [990003])
        # Getippter Name + Enter: erst lokal, ohne Netz
        win.mk_item.setEditText("acolyte ii probe")
        _n80 = len(_geplottet80)
        win._plot_history()
        check("b80 getippter Name wird lokal aufgeloest (ohne ESI)",
              _geplottet80[_n80:] == [990001])
        # Auto-Start: zuletzt angesehenes Item
        win._mk_full = []
        win._mk_auto_lief = False
        win.settings["mk_last_item"] = [990002, "Acolyte I Probe"]
        _n80 = len(_geplottet80)
        win._mk_auto_start()
        check("b80 beim Oeffnen des Tabs wird das zuletzt angesehene Item gezeichnet",
              _geplottet80[_n80:] == [990002] and win.mk_item.currentData() == 990002)
        _n80 = len(_geplottet80)
        win._mk_auto_start()
        check("b80 ... aber nur einmal, nicht bei jedem Tab-Wechsel",
              _geplottet80[_n80:] == [])
        # Ohne gemerktes Item: "Acolyte II" (Tutorial-Item), ueber den Namen
        win._mk_auto_lief = False
        win.settings["mk_last_item"] = None
        _n80 = len(_geplottet80)
        win._mk_auto_start()
        check("b80 ohne gemerktes Item: Acolyte II, ueber den Namen aufgeloest",
              _geplottet80[_n80:] == [990004] and win.mk_item.currentText() == "Acolyte II")
        check("b80 keine Type-ID fuer das Startitem im Quelltext (Regel 2)",
              win._MK_STARTITEM == "Acolyte II" and "2488" not in
              __import__("inspect").getsource(type(win)._mk_auto_start))
        check("b80 der Tab-Wechsel ruft den Auto-Start",
              "self._mk_auto_start()" in
              __import__("inspect").getsource(type(win)._on_tab_changed))
        check("b80 mk_last_item hat einen Standard in DEFAULT_SETTINGS",
              "mk_last_item" in __import__("eve_trader.config", fromlist=["x"]).DEFAULT_SETTINGS)
    finally:
        win._do_plot = _alt_plot80
        _st80.all_names = _alt_names80
        win.settings["mk_last_item"] = None
        win._mk_auto_lief = False
        win._mk_namen_laden()
except Exception as _e80:                                # pragma: no cover
    _fail.append(f"b80 Preisverlauf-Vervollstaendigung: {type(_e80).__name__}: {_e80}")


# ---------------------------------------------------------------- (b81)
# "-1 ..." AUF DEM GROSSEN LADESCHIRM (Nutzer 18.09.2026, zweiter Fundort
# nach aa370): _set_loading_progress bekam progress(-1, 0) und schrieb die
# Zahl roh. Am Widget geprueft, nicht am Text.
try:
    win._set_loading_progress(-1, 0)
    check("b81 Ladeschirm: -1 wird als Entpack-Phase gezeigt, nicht als Zahl",
          "-1" not in win._overlay_progress.text()
          and win._overlay_progress.text() == _t4("Unpacking and importing …"))
    win._set_loading_progress(57, 140)
    check("b81 Gegenprobe: mit Groesse weiter Balken + Zahlen",
          "57" in win._overlay_progress.text() and "140" in win._overlay_progress.text())
    win._set_loading_progress(3, 0)
    check("b81 Gegenprobe: ohne Groesse weiter die nackte Zahl",
          win._overlay_progress.text().startswith("3"))
except Exception as _e81:                                # pragma: no cover
    _fail.append(f"b81 Ladeschirm -1: {type(_e81).__name__}: {_e81}")


# ---------------------------------------------------------------- (b82)
# EIN GEISTER-ANGEBOT DARF DEN QUELLPREIS NICHT SETZEN (Issue #2).
# `hubs.arbitrage` mittelt den Einkaufspreis ueber `want` Stueck, und `want`
# kam aus der KAUFGEBOTS-Menge des Ziels. Hat das Ziel keine Kaufgebote (bei
# "Sell via sell order" der Normalfall), war want = 1 und der "Durchschnitt"
# war die eine billigste Quell-Order: 1 Stueck zu 10 ISK vor 5'000 zu 100
# ergab 1136 % Marge statt der echten ~25 %. Fuer die Verkaufsart "relist"
# gilt jetzt eine Mindesttiefe (MIN_FILL_QTY); die Kaufgebote des Ziels sagen
# dort nichts darueber, wie viel man einkauft.
import eve_trader.hubs as _hb82

_set82 = {"sales_tax_pct": 3.375, "broker_fee_pct": 1.5}


def _buch82(sell=(), buy=()):
    _s = sorted(sell)
    _b = sorted(buy, reverse=True)
    return {"sell_min": _s[0][0] if _s else 0, "buy_max": _b[0][0] if _b else 0,
            "sell_qty": sum(v for _p, v in _s), "buy_qty": sum(v for _p, v in _b),
            "sell_orders": _s}


def _deal82(quelle, ziel, modus="relist"):
    _r = _hb82.arbitrage({1: quelle}, {1: ziel}, _set82, {"max_items": 400}, modus)
    return _r[0] if _r else None


_geist82 = _buch82(sell=[(10, 1), (100, 5000)])
_ohne_kauf82 = _buch82(sell=[(130, 100)])
_d82 = _deal82(_geist82, _ohne_kauf82)
check("b82 Geister-Order, Ziel ohne Kaufgebote: Preis ist der Tiefen-Durchschnitt",
      _d82 is not None and abs(_d82["source_sell"] - (10 + 99 * 100) / 100.0) < 1e-9)
check("b82 ... und die Marge ist die echte (~25 %), nicht 1136 %",
      _d82 is not None and 20 < _d82["margin"] < 30)
_d82 = _deal82(_geist82, _buch82(sell=[(130, 100)], buy=[(90, 5)]))
check("b82 auch mit winziger Nachfrage (5 Stueck) gilt die Mindesttiefe",
      _d82 is not None and abs(_d82["source_sell"] - (10 + 99 * 100) / 100.0) < 1e-9)
_d82 = _deal82(_geist82, _buch82(sell=[(130, 100)], buy=[(90, 300)]))
check("b82 grosse Nachfrage (300) bleibt die Tiefe - die Mindesttiefe verkleinert nichts",
      _d82 is not None and abs(_d82["source_sell"] - (10 + 299 * 100) / 300.0) < 1e-9)
_d82 = _deal82(_buch82(sell=[(100, 1)]), _ohne_kauf82)
check("b82 duenne Quelle (nur 1 Stueck da): der echte Einzelpreis bleibt",
      _d82 is not None and _d82["source_sell"] == 100.0)


# ---------------------------------------------------------------- (b83)
# SOFORT-VERKAUF RECHNET MIT DER TIEFE DES KAUFBUCHS (Issue #3).
# "Immediate to buy order" bewertete JEDE Einheit mit dem besten Kaufgebot
# (`buy_max`), obwohl `buy_qty` die Menge ueber ALLE Preisstufen ist: 1 Stueck
# zu 120 vor 999 zu 60 galt als "1000 Stueck zu 120". Jetzt werden Quell-
# Verkaufsorders (guenstigste zuerst) gegen Ziel-Kaufgebote (hoechste zuerst)
# abgearbeitet, solange gebot * (1 - Steuer) > Preis; Einkauf, Erloes und
# Gewinn beziehen sich auf genau diese Menge (`units`, hoechstens 1000).
# `target_buy` ist dabei der DURCHSCHNITTLICHE Erloes-Preis dieser Menge (so
# wie `source_sell` der durchschnittliche Einkaufspreis ist); das beste Gebot
# steht weiter in `target_buy_best`.
_tax83 = 0.03375


def _buchk83(sell=(), buy=()):
    _b = _buch82(sell=sell, buy=buy)
    _b["buy_ladder"] = sorted(buy, reverse=True)
    return _b


_d83 = _deal82(_buchk83(sell=[(100, 5000)]),
               _buchk83(buy=[(120, 100), (110, 100), (60, 800)]), "instant")
check("b83 Kaufbuch mit Stufen: gehandelt wird nur, was sich lohnt (200 Stueck)",
      _d83 is not None and _d83.get("units") == 200)
check("b83 ... der Gewinn ist der Durchschnitt dieser 200, nicht der des besten Gebots",
      _d83 is not None
      and abs(_d83["profit_unit"] - ((23000 * (1 - _tax83) - 20000) / 200.0)) < 1e-9)
check("b83 ... target_buy ist der durchschnittliche Erloes-Preis, das beste Gebot bleibt separat",
      _d83 is not None and abs(_d83["target_buy"] - 115.0) < 1e-9
      and _d83.get("target_buy_best") == 120)
check("b83 ... Score = Gewinn x gehandelte Menge (nicht x Gesamtnachfrage 1000)",
      _d83 is not None and abs(_d83["score"] - _d83["profit_unit"] * 200) < 1e-6)

_d83 = _deal82(_buchk83(sell=[(100, 50), (110, 50), (200, 5000)]),
               _buchk83(buy=[(150, 120)]), "instant")
check("b83 auch die Quell-Leiter wird abgeschritten (Einkauf 105 im Schnitt)",
      _d83 is not None and _d83.get("units") == 100
      and abs(_d83["source_sell"] - 105.0) < 1e-9
      and abs(_d83["profit_unit"] - (15000 * (1 - _tax83) - 10500) / 100.0) < 1e-9)

_d83 = _deal82(_buchk83(sell=[(100, 5000)]),
               _buchk83(buy=[(120, 1), (60, 999)]), "instant")
check("b83 das Beispiel aus dem Issue: 1 Stueck zu 120 vor 999 zu 60 = genau 1 Einheit",
      _d83 is not None and _d83.get("units") == 1)

_d83 = _deal82(_buchk83(sell=[(100, 5000)]), _buchk83(buy=[(90, 100)]), "instant")
check("b83 lohnt sich kein einziges Stueck, gibt es keinen Treffer", _d83 is None)

_d83 = _deal82(_buch82(sell=[(100, 5000)], buy=[(120, 50)]),
               {"sell_min": 0, "sell_qty": 0, "buy_max": 120.0, "buy_qty": 50},
               "instant")
check("b83 ohne Kaufbuch-Leiter (alte Daten) gilt das beste Gebot fuer die ganze Menge",
      _d83 is not None and _d83.get("units") == 50
      and abs(_d83["profit_unit"] - (120 * (1 - _tax83) - 100)) < 1e-9)

_d83 = _deal82(_buchk83(sell=[(100, 5000)]), _buchk83(buy=[(200, 5000)]), "instant")
check("b83 die Menge ist bei 1000 Stueck gedeckelt", _d83 is not None and _d83.get("units") == 1000)

_d83 = _deal82(_buchk83(sell=[(100, 5000)]),
               _buchk83(sell=[(130, 100)], buy=[(120, 100), (110, 100)]), "relist")
check("b83 Relist ist unberuehrt: target_buy ist das beste Gebot, keine Menge",
      _d83 is not None and _d83["target_buy"] == 120 and _d83.get("units") is None)

import eve_trader.esi as _esi83


class _Seite83:
    headers = {"X-Pages": "1"}

    def json(self):
        return [{"location_id": 60003760, "type_id": 7, "is_buy_order": True,
                 "price": 120.0, "volume_remain": 10},
                {"location_id": 60003760, "type_id": 7, "is_buy_order": True,
                 "price": 110.0, "volume_remain": 20},
                {"location_id": 60003760, "type_id": 7, "is_buy_order": False,
                 "price": 130.0, "volume_remain": 5},
                {"location_id": 999, "type_id": 7, "is_buy_order": True,
                 "price": 999.0, "volume_remain": 1}]


_alt83 = _esi83._get_with_retry
_esi83._get_with_retry = lambda *a, **k: _Seite83()
try:
    _agg83 = _hb82.fetch_hub_orders(10000002, 60003760)
finally:
    _esi83._get_with_retry = _alt83
check("b83 fetch_hub_orders liefert das Kaufbuch (nur diese Station)",
      sorted(_agg83[7].get("buy_ladder", [])) == [(110.0, 20), (120.0, 10)])

_alt83b = _esi83.fetch_structure_orders_full
_esi83.fetch_structure_orders_full = lambda *a, **k: {
    7: {"sell": [(130.0, 5)], "buy": [(120.0, 10), (110.0, 20)],
        "sell_min": 130.0, "buy_max": 120.0, "sell_qty": 5, "buy_qty": 30,
        "sell_orders": 1, "buy_orders": 2}}
try:
    _agg83b = _hb82.load_location_orders(
        {"kind": "structure", "structure_id": 1, "character_id": 2, "name": "x"},
        {"client_id": "c"})
finally:
    _esi83.fetch_structure_orders_full = _alt83b
check("b83 auch das Struktur-Ziel liefert das Kaufbuch",
      _agg83b[7].get("buy_ladder") == [(120.0, 10), (110.0, 20)])


# ---------------------------------------------------------------- (b84)
# DIE ANMELDE-SEITE FOLGT DER SPRACHE (Issue #8). Nach dem EVE-Login zeigt
# der lokale Rueckruf-Server eine Seite im Browser; sie stand fest auf
# Deutsch und lief an t() vorbei, ein englischer Nutzer las "Login
# erfolgreich". Geprueft wird der ECHTE Handler auf einem freien Port.
import threading as _th84
import urllib.request as _ur84
from http.server import HTTPServer as _HS84
import eve_trader.auth as _au84
import eve_trader.sprache as _sp84


def _seite84(sprache):
    _alt = _sp84._aktuell
    _sp84.sprache_setzen(sprache)
    _srv = _HS84(("127.0.0.1", 0), _au84._CallbackHandler)
    _t = _th84.Thread(target=_srv.handle_request)
    _t.start()
    try:
        _r = _ur84.urlopen(
            f"http://127.0.0.1:{_srv.server_address[1]}/callback?code=abc&state=xyz",
            timeout=10)
        return _r.read().decode("utf-8"), _r.headers.get("Content-Type", "")
    finally:
        _t.join(10)
        _srv.server_close()
        _sp84.sprache_setzen(_alt)


_en84, _kopf84 = _seite84("en")
check("b84 englisch: die Seite sagt 'Login successful' und nennt das Fenster",
      "Login successful" in _en84 and "close this window" in _en84)
check("b84 englisch: kein deutscher Text auf der Seite",
      "erfolgreich" not in _en84 and "schliessen" not in _en84)
_de84, _kopf84 = _seite84("de")
check("b84 deutsch: 'Login erfolgreich' mit Umlaut (UTF-8)",
      "Login erfolgreich" in _de84 and "zurückkehren" in _de84
      and "Login successful" not in _de84)
check("b84 die Seite kommt als UTF-8-HTML", "utf-8" in _kopf84.lower())
check("b84 der Handler merkt sich weiter code und state des Rueckrufs",
      _au84._CallbackHandler.result == {"code": "abc", "state": "xyz"})


# ---------------------------------------------------------------- (b85)
# REGIONAL RECHNET MIT DER MAKLERGEBUEHR DES ZIEL-HUBS (Issue #4).
# `broker_fee_pct` ist EINE globale Einstellung; `_sync_fees_to_hub` ueber-
# schreibt sie bei jedem Scan mit den Standings des SCAN-Hubs. Wer in Amarr
# gescannt hatte und dann Amarr -> Jita rechnete, bekam Amarrs Gebuehr statt
# der von Jita (Broker Relations V, Jita 5/5 -> 1.25 %, Amarr 0/0 -> 1.5 %).
# Jetzt gilt fuer den Verkauf am Ziel `_broker_pct_for(ziel)`: Skill-Gebuehr
# des Ziel-Hubs, bei Struktur ihre eigene, ohne "Gebuehren aus Skills" der
# eingestellte Wert. Betrifft Tabelle, Leer-Markt-Schaetzung und Leiter-Grenze.
import eve_trader.scanner as _sc85
import eve_trader.config as _cfg85

_KEYS85 = ("fees_from_skills", "skill_broker_relations", "hub_standings",
           "sales_tax_pct", "broker_fee_pct", "structure_broker_pct")
_LEER85 = object()
_alt85 = {k: win.settings.get(k, _LEER85) for k in _KEYS85}
_hub85 = lambda rid: {"kind": "hub", "name": "x", "region_id": rid, "station_id": 1}
_JITA85, _AMARR85 = 10000002, 10000043
try:
    win.settings.update({
        "fees_from_skills": True, "skill_broker_relations": 5,
        "hub_standings": {"jita": {"corp": 5.0, "faction": 5.0},
                          "amarr": {"corp": 0.0, "faction": 0.0}},
        "sales_tax_pct": 3.375, "broker_fee_pct": 9.99, "structure_broker_pct": 0.7})
    _jita_fee85 = _cfg85.effective_broker_fee(5, 5.0, 5.0)        # 1.25
    _amarr_fee85 = _cfg85.effective_broker_fee(5, 0.0, 0.0)       # 1.5
    eq("b85 Ziel Jita: Skill-Gebuehr mit Jitas Standings (nicht der geteilte Wert)",
       win._broker_pct_for(_hub85(_JITA85)), _jita_fee85)
    eq("b85 Ziel Amarr: Skill-Gebuehr mit Amarrs Standings",
       win._broker_pct_for(_hub85(_AMARR85)), _amarr_fee85)
    eq("b85 Ziel Struktur: die eigene Struktur-Gebuehr",
       win._broker_pct_for({"kind": "structure", "region_id": None,
                            "structure_id": 5}), 0.7)
    eq("b85 die Abfrage ist rein: der geteilte Wert bleibt unberuehrt",
       win.settings["broker_fee_pct"], 9.99)
    win.settings["fees_from_skills"] = False
    eq("b85 ohne 'Gebuehren aus Skills' gilt der eingestellte Wert",
       win._broker_pct_for(_hub85(_JITA85)), 9.99)
    win.settings["fees_from_skills"] = True

    # ---- Ende-zu-Ende: compute_arbitrage Amarr -> Jita, Amarr war zuletzt
    # der Scan-Hub (geteilte Gebuehr = Amarrs 1.5 %).
    win.settings["broker_fee_pct"] = _amarr_fee85
    _hist85 = [{"volume": 50, "average": 200.0, "highest": 210.0, "lowest": 190.0}
               for _ in range(30)]
    _books85 = {
        _AMARR85: {1: {"sell_min": 100, "sell_qty": 5000, "buy_max": 0, "buy_qty": 0,
                       "sell_orders": [(100, 5000)], "buy_ladder": []},
                   2: {"sell_min": 100, "sell_qty": 1000, "buy_max": 0, "buy_qty": 0,
                       "sell_orders": [(100, 1000)], "buy_ladder": []}},
        _JITA85: {1: {"sell_min": 130, "sell_qty": 100, "buy_max": 90, "buy_qty": 5,
                      "sell_orders": [(130, 100)], "buy_ladder": [(90, 5)]}}}
    _orig85 = (_hb82.load_location_orders, _esi83.resolve_names,
               _esi83.resolve_volumes, _sc85.history_cached, win._run,
               win._apply_rg_view)
    _hb82.load_location_orders = lambda loc, settings, progress=None: _books85[loc["region_id"]]
    _esi83.resolve_names = lambda ids: {}
    _esi83.resolve_volumes = lambda ids: {i: 1.0 for i in ids}
    _sc85.history_cached = lambda tid, region, *a, **k: _hist85
    win._run = lambda w, done, fail_cb=None, **k: done(w._fn(*w._args, **w._kwargs))
    win._apply_rg_view = lambda: None            # kein Zeichnen, keine Icon-Abrufe
    try:
        for _combo85, _rid85 in ((win.rg_src, _AMARR85), (win.rg_tgt, _JITA85)):
            for _i85 in range(_combo85.count()):
                _dd85 = _combo85.itemData(_i85) or {}
                if _dd85.get("kind") == "hub" and _dd85.get("region_id") == _rid85:
                    _combo85.setCurrentIndex(_i85)
        for _i85 in range(win.rg_mode.count()):
            if win.rg_mode.itemData(_i85) == "relist":
                win.rg_mode.setCurrentIndex(_i85)
        win._rg_raw = None
        win._rg_last_key = None
        win.compute_arbitrage()
        _dl85 = {d["type_id"]: d for d in (win._rg_raw or [])}
    finally:
        (_hb82.load_location_orders, _esi83.resolve_names, _esi83.resolve_volumes,
         _sc85.history_cached, win._run, win._apply_rg_view) = _orig85
    _tax85 = 0.03375
    check("b85 compute_arbitrage: Verkauf in Jita rechnet mit Jitas Gebuehr (1.25 %)",
          1 in _dl85 and abs(_dl85[1]["profit_unit"]
                             - (130 * (1 - _tax85 - _jita_fee85 / 100.0) - 100)) < 1e-9)
    check("b85 compute_arbitrage: auch die Leer-Markt-Schaetzung nimmt Jitas Gebuehr",
          2 in _dl85 and abs(_dl85[2]["profit_unit"]
                             - (200 * (1 - _tax85 - _jita_fee85 / 100.0) - 100)) < 1e-9)
    # ---- die Leiter-Grenze (welcher Einkaufspreis lohnt noch) gleich mit
    _m85 = win._ladder_min_margin("region") / 100.0
    _grenze85 = win._ladder_cutoff("region", {"target_sell": 130.0})
    check("b85 die Leiter-Grenze im Regional nimmt dieselbe Ziel-Gebuehr",
          abs(_grenze85 - 130 * (1 - _tax85 - _jita_fee85 / 100.0) / (1 + _m85)) < 1e-9)
finally:
    for _k85, _v85 in _alt85.items():
        if _v85 is _LEER85:
            win.settings.pop(_k85, None)
        else:
            win.settings[_k85] = _v85


# ---------------------------------------------------------------- (b86)
# DIE 400 FUER DIE NETZ-SCHRITTE WERDEN NACH DER TABELLEN-REIHENFOLGE
# GEWAEHLT (Issue #5). `compute_arbitrage` schnitt die Kandidaten NACH
# Gewinn x Nachfrage auf 400 - bevor Fracht und Feinfilter liefen. Schwere,
# teure Ware verdraengte leichte Schuettgut-Ware, obwohl die Tabelle nach
# Gewinn PRO m3 sortiert: bei Fracht 500 ISK/m3 war die Tabelle leer, obwohl
# jede leichte Ware Gewinn brachte. Gewinn/m3 minus Fracht behaelt die
# Reihenfolge bei (pm3 = gewinn/vol - fracht), die Auswahl braucht die Fracht
# also nicht. `hubs.preselect`: die eine Haelfte nach Gewinn/m3 (Volumen aus
# der lokalen SDE), der Rest nach dem alten Score; ohne Volumen wie vorher.
_deals86 = [{"type_id": i, "profit_unit": 428_000.0, "score": 42_800_000.0 + i}
            for i in range(1, 501)]                         # schwer, hoher Score
_deals86 += [{"type_id": i, "profit_unit": 52_000.0, "score": 52_000.0 + i}
             for i in range(1001, 1101)]                    # leicht, niedriger Score
_vol86 = {i: 50_000.0 for i in range(1, 501)}
_vol86.update({i: 0.01 for i in range(1001, 1101)})
_deals86.sort(key=lambda d: d["score"], reverse=True)

_alt_cap86 = _hb82.arbitrage(
    {1: {"sell_min": 100, "sell_qty": 9, "sell_orders": [(100, 9)]},
     2: {"sell_min": 100, "sell_qty": 9, "sell_orders": [(100, 9)]}},
    {1: {"sell_min": 200, "sell_qty": 9, "buy_max": 0, "buy_qty": 0},
     2: {"sell_min": 200, "sell_qty": 9, "buy_max": 0, "buy_qty": 0}},
    _set82, {"max_items": None}, "relist")
eq("b86 hubs.arbitrage ohne Obergrenze (max_items=None) liefert alle", len(_alt_cap86), 2)

_sel86 = getattr(_hb82, "preselect", None)
_p86 = _sel86(_deals86, _vol86, 400) if _sel86 else []
_ids86 = [d["type_id"] for d in _p86]
eq("b86 preselect: genau 400 bei 600 Kandidaten", len(_p86), 400)
check("b86 ... alle 100 leichten Waren sind dabei (vorher: keine)",
      sum(1 for i in _ids86 if i > 1000) == 100)
check("b86 ... ohne Doppelte", len(set(_ids86)) == len(_ids86))
check("b86 ... die schweren rutschen nach dem alten Score nach (300 Stueck)",
      sum(1 for i in _ids86 if i <= 500) == 300)
check("b86 ... Ergebnis bleibt nach Score absteigend sortiert",
      [d["score"] for d in _p86] == sorted((d["score"] for d in _p86), reverse=True))
_kurz86 = _deals86[:50]
check("b86 wenige Kandidaten (<= Obergrenze): unveraendert zurueck",
      _sel86 is not None and _sel86(_kurz86, _vol86, 400) == _kurz86)
_p86 = _sel86(_deals86, {}, 400) if _sel86 else []
check("b86 ohne Volumen (SDE leer): wie vorher, die 400 mit dem hoechsten Score",
      [d["type_id"] for d in _p86] == [d["type_id"] for d in _deals86[:400]])
_vol86b = dict(_vol86)
_top86 = _deals86[0]["type_id"]
_vol86b.pop(_top86)
_p86 = _sel86(_deals86, _vol86b, 400) if _sel86 else []
check("b86 ein Item ohne bekanntes Volumen faellt nicht raus, wenn sein Score traegt",
      _top86 in {d["type_id"] for d in _p86})

# ---- Ende-zu-Ende: compute_arbitrage, Fracht 500 ISK/m3, Filter auf 0
import eve_trader.industry as _ind86
_GES86 = {"kind": "hub", "region_id": _AMARR85, "station_id": 1, "name": "x"}


def _buch86(sell, qty, buy=0, bqty=0):
    return {"sell_min": sell, "sell_qty": qty, "buy_max": buy, "buy_qty": bqty,
            "sell_orders": [(sell, qty)], "buy_ladder": [(buy, bqty)] if bqty else []}


_q86, _z86 = {}, {}
for _i86 in range(1, 501):
    _q86[_i86] = _buch86(1_000_000, 50)
    _z86[_i86] = _buch86(1_500_000, 10, 900_000, 100)
for _i86 in range(1001, 1101):
    _q86[_i86] = _buch86(100_000, 5000)
    _z86[_i86] = _buch86(160_000, 10)
_bk86 = {_AMARR85: _q86, _JITA85: _z86}
_h86 = [{"volume": 50, "average": 1.0, "highest": 1.0, "lowest": 1.0}] * 30
_ui86 = {n: getattr(win, n).value() for n in ("rg_margin", "rg_profit", "rg_vol", "rg_haul")}
_orig86 = (_hb82.load_location_orders, _esi83.resolve_names, _esi83.resolve_volumes,
           _sc85.history_cached, win._run, win._render_arbitrage,
           win._icon_prefetch_pending, _ind86.item_volume_map)
_gezeigt86 = {}
try:
    _hb82.load_location_orders = lambda loc, s, progress=None: _bk86[loc["region_id"]]
    _esi83.resolve_names = lambda ids: {}
    _esi83.resolve_volumes = lambda ids: {i: _vol86.get(i, 0.0) for i in ids}
    _sc85.history_cached = lambda tid, region, *a, **k: _h86
    win._run = lambda w, done, fail_cb=None, **k: done(w._fn(*w._args, **w._kwargs))
    win._render_arbitrage = lambda deals: _gezeigt86.update(zeilen=list(deals))
    win._icon_prefetch_pending = lambda *a, **k: None
    for _c86, _r86 in ((win.rg_src, _AMARR85), (win.rg_tgt, _JITA85)):
        for _i86 in range(_c86.count()):
            _d86 = _c86.itemData(_i86) or {}
            if _d86.get("kind") == "hub" and _d86.get("region_id") == _r86:
                _c86.setCurrentIndex(_i86)
    for _i86 in range(win.rg_mode.count()):
        if win.rg_mode.itemData(_i86) == "relist":
            win.rg_mode.setCurrentIndex(_i86)
    win.rg_margin.setValue(0)
    win.rg_profit.setValue(0)
    win.rg_vol.setValue(0)
    win.rg_haul.setValue(500)
    _ind86.item_volume_map = lambda ids=None: dict(_vol86)
    win._rg_raw = None
    win._rg_last_key = None
    win.compute_arbitrage()
    _leicht86 = [d for d in _gezeigt86.get("zeilen", []) if d["type_id"] > 1000]
    eq("b86 compute_arbitrage: bei Fracht 500 zeigt die Tabelle die 100 leichten Waren",
       len(_leicht86), 100)
    check("b86 ... und keine schwere Ware (Fracht frisst ihren Gewinn)",
          not any(d["type_id"] <= 500 for d in _gezeigt86.get("zeilen", [])))
    check("b86 ... die Netz-Schritte bleiben bei hoechstens 400 Kandidaten",
          len(win._rg_raw or []) <= 400)
    _ind86.item_volume_map = lambda ids=None: {}
    win._rg_raw = None
    win._rg_last_key = None
    _gezeigt86.clear()
    win.compute_arbitrage()
    check("b86 ohne SDE-Volumen: wie vorher (400 Kandidaten, keine leichten)",
          len(win._rg_raw or []) == 400
          and not any(d["type_id"] > 1000 for d in (win._rg_raw or [])))
finally:
    (_hb82.load_location_orders, _esi83.resolve_names, _esi83.resolve_volumes,
     _sc85.history_cached, win._run, win._render_arbitrage,
     win._icon_prefetch_pending, _ind86.item_volume_map) = _orig86
    for _n86, _v86 in _ui86.items():
        getattr(win, _n86).setValue(_v86)
    win._rg_raw = None
    win._rg_last_key = None


# ---------------------------------------------------------------- (b87)
# DAS ZIEL-VOLUMEN IST DAS DER REGION, NICHT DER STATION (Issue #6).
# ESI-Markthistorie gibt es nur je REGION. Spalte, Filter, Trichterzeile und
# Tooltips sagten "dort gehandelt", gemeint war "irgendwo in der Region" - am
# Hub also eine OBERGRENZE. Jetzt steht "Zielregion" dran, die Tooltips
# sagen es, und als Beleg fuer den Hub selbst zaehlt fetch_hub_orders die
# Orders JEDER Station der Region mit (`region_orders`): der Tooltip nennt den
# Anteil, der an der Ziel-Station liegt. Eine Schaetzung des Stations-Volumens
# gibt es bewusst NICHT - die Daten dafuer fehlen.
import eve_trader.sprache as _sp87


class _Seite87:
    headers = {"X-Pages": "1"}

    def json(self):
        _o = lambda loc, buy, p, v, t=7: {"location_id": loc, "type_id": t,
                                          "is_buy_order": buy, "price": p,
                                          "volume_remain": v}
        return [_o(60003760, True, 120.0, 10), _o(60003760, False, 130.0, 5),
                _o(999, True, 100.0, 1), _o(999, True, 101.0, 2),
                _o(999, False, 140.0, 3), _o(999, False, 5.0, 1, t=8)]


_alt87 = _esi83._get_with_retry
_esi83._get_with_retry = lambda *a, **k: _Seite87()
try:
    _agg87 = _hb82.fetch_hub_orders(10000002, 60003760)
finally:
    _esi83._get_with_retry = _alt87
eq("b87 fetch_hub_orders zaehlt die Orders der ganzen Region mit (2 hier + 3 dort)",
   _agg87[7].get("region_orders"), 5)
check("b87 ... ein Item, das nur an einer anderen Station liegt, bekommt keinen Eintrag",
      8 not in _agg87)

_z87 = {"sell_min": 130.0, "sell_qty": 100, "buy_max": 90.0, "buy_qty": 5,
        "sell_orders": [(130.0, 100)], "buy_ladder": [(90.0, 5)], "region_orders": 10}
_d87 = _deal82(_buch82(sell=[(100, 5000)]), _z87)
check("b87 arbitrage: Anteil der Ziel-Station an den Region-Orders (2 von 10)",
      _d87 is not None and abs((_d87.get("target_order_share") or -1) - 0.2) < 1e-9)
_d87 = _deal82(_buch82(sell=[(100, 5000)]),
               {k: v for k, v in _z87.items() if k != "region_orders"})
check("b87 ... ohne Region-Zahl (Struktur): None statt einer erfundenen Zahl",
      _d87 is not None and "target_order_share" in _d87
      and _d87["target_order_share"] is None)

eq("b87 Spaltenkopf 9 nennt die Zielregion",
   win.rg_table.horizontalHeaderItem(9).text(), _t4("Ø daily vol dest. region"))
check("b87 Kopf-Tooltip: je Region, keine Historie je Station, Obergrenze",
      all(w in win.rg_table.horizontalHeaderItem(9).toolTip()
          for w in ("region", "per-station", "upper bound")))
# (`_install_tip` verschiebt den Tooltip vom Eingabefeld auf das Titel-Label)
_lab87 = [l for l in win._tip_anchor
          if l.text() == _t4("Min \u00d8 daily volume dest. region")]
eq("b87 der Filter heisst 'Min \u00d8 daily volume dest. region' (genau ein Label)",
   len(_lab87), 1)
check("b87 Filter-Tooltip sagt dasselbe und nennt die REGION",
      bool(_lab87) and all(w in win._tip_anchor[_lab87[0]] for w in ("REGION", "upper bound")))
eq("b87 Trichterzeile nennt die Zielregion",
   dict(win._RG_DIAG_LABELS)["target_vol_low"],
   "destination region sales (history) too small")

_basis87 = {"type_id": 34, "source_sell": 100.0, "target_sell": 200.0,
            "target_buy": 150.0, "profit_unit": 50.0, "margin": 50.0,
            "target_demand": 10, "target_supply": 3, "volume": 0.01,
            "profit_m3": 5000.0}
_alt_render87 = (win._icon_prefetch_pending, getattr(win, "_arb_modus", None),
                 _sp87._aktuell)
win._icon_prefetch_pending = lambda *a, **k: None
win._arb_modus = "relist"
try:
    win._render_arbitrage([dict(_basis87, target_vol=5.0, tgt_sell_reach=0.5,
                                target_order_share=0.25)])
    _tip87 = win.rg_table.item(0, 9).toolTip()
    check("b87 Zellen-Tooltip: der Anteil an der Ziel-Station (25 %)", "25 %" in _tip87)
    check("b87 ... die Warnung bei kleinem Volumen nennt die Zielregion",
          "destination region" in _tip87)
    check("b87 ... und der Verkaufs-Beleg (S %) bleibt daneben stehen",
          "S %" in _tip87)
    win._render_arbitrage([dict(_basis87, target_vol=500.0)])
    check("b87 ohne Anteil und bei gutem Volumen: kein Prozent-Satz im Tooltip",
          "%" not in win.rg_table.item(0, 9).toolTip())
    _sp87.sprache_setzen("de")
    win._render_arbitrage([dict(_basis87, target_vol=5.0, tgt_sell_reach=0.5,
                                target_order_share=0.25)])
    _tipd87 = win.rg_table.item(0, 9).toolTip()
    check("b87 deutsch: Anteils-Satz und Zielregion-Warnung sind uebersetzt",
          "25 %" in _tipd87 and "Orders" in _tipd87 and "Zielregion" in _tipd87)
    check("b87 deutsch: der Kopf nennt die Zielregion",
          "Zielregion" in win.rg_table.horizontalHeaderItem(9).text()
          or "Zielregion" in _t4("Ø daily vol dest. region"))
finally:
    _sp87.sprache_setzen(_alt_render87[2])
    win._icon_prefetch_pending = _alt_render87[0]
    win._arb_modus = _alt_render87[1]
    win.rg_table.setRowCount(0)


# ---------------------------------------------------------------- (b88)
# REGIONAL WARNT, WENN DER GEWINN OHNE FRACHT / OHNE ABSATZ-PRUEFUNG STEHT
# (Issue #7). Fracht steht auf 0 ISK/m3 und das Mindest-Volumen am Ziel auf
# 0: wer "Deals laden" drueckt, sah Gewinn VOR Fracht und ohne Pruefung, ob
# die Ware dort ueberhaupt laeuft - ohne jeden Hinweis. Die Vorgaben bleiben
# (Nutzer-Entscheid: nur warnen); ein bernsteinfarbener Hinweis unter der
# Statuszeile sagt es, solange es gilt, und verschwindet sonst.
_ui88 = {n: getattr(win, n).value() for n in ("rg_haul", "rg_vol")}
_orig88 = (win._render_arbitrage, getattr(win, "_rg_raw", None),
           win._run, _hb82.load_location_orders, _sp87._aktuell)
_deal88 = {"type_id": 34, "source_sell": 100.0, "target_sell": 200.0,
           "target_buy": 150.0, "profit_unit": 50.0, "margin": 50.0,
           "target_demand": 10, "target_supply": 3, "volume": 0.01,
           "target_vol": 500.0}


def _hinweis88(fracht, vol):
    win.rg_haul.setValue(fracht)
    win.rg_vol.setValue(vol)
    win._apply_rg_view()
    _w = getattr(win, "rg_warn", None)
    return (_w.text() if _w is not None else None,
            (not _w.isHidden()) if _w is not None else None)


try:
    win._render_arbitrage = lambda deals: None
    win._rg_raw = [dict(_deal88)]
    _t88, _sicht88 = _hinweis88(0, 0)
    check("b88 Fracht 0 und kein Mindest-Volumen: beide Hinweise stehen da",
          _sicht88 is True and "Transport cost" in (_t88 or "") and "Min Ø daily volume" in (_t88 or ""))
    _t88, _sicht88 = _hinweis88(500, 100)
    check("b88 Fracht und Volumen gesetzt: kein Hinweis, Feld versteckt",
          _t88 == "" and _sicht88 is False)
    _t88, _sicht88 = _hinweis88(500, 0)
    check("b88 nur das Volumen fehlt: nur der Volumen-Hinweis",
          _sicht88 is True and "Transport cost" not in (_t88 or "")
          and "Min Ø daily volume" in (_t88 or ""))
    _t88, _sicht88 = _hinweis88(0, 100)
    check("b88 nur die Fracht fehlt: nur der Fracht-Hinweis",
          _sicht88 is True and "Transport cost" in (_t88 or "")
          and "Min Ø daily volume" not in (_t88 or ""))
    _t88, _ = _hinweis88(0, 0)
    check("b88 der Hinweis nennt, wo man es einstellt (Feinfilter)", "Fine filters" in (_t88 or ""))
    _sp87.sprache_setzen("de")
    _t88, _ = _hinweis88(0, 0)
    check("b88 deutsch: beide Hinweise uebersetzt",
          "Transportkosten" in (_t88 or "") and "Tagesvolumen Zielregion" in (_t88 or "")
          and "Feinfilter" in (_t88 or "") and "Transport cost" not in (_t88 or ""))
    _sp87.sprache_setzen("en")
    # ein fehlgeschlagener Ladevorgang leert die Tabelle - der Hinweis geht mit
    _hinweis88(0, 0)

    def _lauf_fehl88(w, done, fail_cb=None, **k):
        try:
            _r = w._fn(*w._args, **w._kwargs)
        except Exception as _e:
            fail_cb(str(_e))
            return
        done(_r)

    def _boom88(*a, **k):
        raise RuntimeError("boom")
    _hb82.load_location_orders = _boom88
    win._run = _lauf_fehl88
    win._rg_raw = None
    win._rg_last_key = None
    win.compute_arbitrage()
    _w88 = getattr(win, "rg_warn", None)
    check("b88 nach einem Ladefehler ist der Hinweis weg",
          _w88 is not None and _w88.isHidden() and _w88.text() == "")
finally:
    (win._render_arbitrage, win._rg_raw, win._run, _hb82.load_location_orders,
     _sp87._aktuell) = _orig88
    for _n88, _v88 in _ui88.items():
        getattr(win, _n88).setValue(_v88)
    win._rg_last_key = None


# ---------------------------------------------------------------- (b89)
# EIN FEHLGESCHLAGENER MARKT-ABRUF IST "UNBEKANNT", NICHT "TOP" (Issue #17).
# `_load_order_mods` machte aus jeder Ausnahme ein leeres Orderbuch; mit
# best = 0 greift weder die Ueberboten- noch die Unterboten-Bedingung, die Zeile
# zeigte "-" und "top". Und `_get_with_retry` wiederholte 420/429 (Rate-Limit)
# nicht, obwohl sechs Abrufe gleichzeitig laufen. Jetzt: Zeile "? unknown",
# nicht als "zu aendern" gezaehlt, Zahl in der Statuszeile; 420/429 werden mit
# Wartezeit (Retry-After / X-Esi-Error-Limit-Reset, hoechstens 10 s) wiederholt.
import requests as _rq89
from types import SimpleNamespace as _NS89


class _Antw89:
    def __init__(self, code, headers=None):
        self.status_code = code
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise _rq89.HTTPError(f"{self.status_code}")

    def json(self):
        return []


def _lauf89(codes):
    """_get_with_retry gegen eine Folge von Statuscodes; (Aufrufe, Pausen, Ergebnis)."""
    _folge = list(codes)
    _pausen, _n = [], [0]

    class _Sess89:
        def get(self, *a, **k):
            _n[0] += 1
            _c = _folge.pop(0)
            return _Antw89(*_c) if isinstance(_c, tuple) else _Antw89(_c)

    class _Zeit89:
        sleep = staticmethod(lambda s: _pausen.append(s))

        def __getattr__(self, name):
            return getattr(__import__("time"), name)

    _alt_s, _alt_t = _esi83._session, _esi83.time
    _esi83._session, _esi83.time = _Sess89(), _Zeit89()
    try:
        try:
            _res = _esi83._get_with_retry("http://x")
        except _rq89.HTTPError as _e:
            _res = _e
    finally:
        _esi83._session, _esi83.time = _alt_s, _alt_t
    return _n[0], _pausen, _res


_n89, _p89, _r89 = _lauf89([429, 200])
check("b89 429 wird wiederholt und klappt danach (2 Aufrufe, 1 Pause)",
      _n89 == 2 and len(_p89) == 1 and getattr(_r89, "status_code", None) == 200)
_n89, _p89, _r89 = _lauf89([(429, {"Retry-After": "3"}), 200])
check("b89 die Wartezeit folgt Retry-After", _p89 == [3.0])
_n89, _p89, _r89 = _lauf89([(420, {"X-Esi-Error-Limit-Reset": "7"}), 200])
check("b89 420 wartet die Fehlerlimit-Zeit ab und wiederholt",
      _n89 == 2 and _p89 == [7.0])
_n89, _p89, _r89 = _lauf89([(429, {"Retry-After": "600"}), 200])
check("b89 die Wartezeit ist auf 10 s gedeckelt", _p89 == [10.0])
_n89, _p89, _r89 = _lauf89([429, 429, 429])
check("b89 bleibt es beim Limit, wird nach 3 Versuchen aufgegeben (Fehler wie vorher)",
      _n89 == 3 and isinstance(_r89, _rq89.HTTPError))
_n89, _p89, _r89 = _lauf89([404])
check("b89 4xx ausser 420/429 wird weiter NICHT wiederholt",
      _n89 == 1 and isinstance(_r89, _rq89.HTTPError) and _p89 == [])
_n89, _p89, _r89 = _lauf89([503, 200])
check("b89 5xx wird wie vorher wiederholt", _n89 == 2 and getattr(_r89, "status_code", None) == 200)

# ---- Order update: ein Item, dessen Marktabruf scheitert
import eve_trader.store as _st89
_stat89 = win._active_hub()[1]
_alt89 = (_st89.list_characters, _esi83.fetch_character_orders,
          _esi83.fetch_type_orders, _esi83.resolve_names, win._run,
          win._table_icon, _sp87._aktuell)


def _order89(tid, preis, oid):
    return {"type_id": tid, "price": preis, "is_buy_order": False, "order_id": oid,
            "volume_remain": 10, "location_id": _stat89}


def _buch89(tid, s, r):
    if tid == 34:
        raise RuntimeError("420 error limited")
    return {"sell": [(900.0, 5)], "buy": []}


def _zeile89(name):
    for _r in range(win.sellord_table.rowCount()):
        if win.sellord_table.item(_r, 0).text() == name:
            return _r
    return None


try:
    _st89.list_characters = lambda: [{"character_id": 1, "character_name": "T"}]
    _esi83.fetch_character_orders = lambda c, cid: [_order89(34, 1000.0, 1),
                                                    _order89(35, 1000.0, 2)]
    _esi83.fetch_type_orders = _buch89
    _esi83.resolve_names = lambda ids: {i: f"Item{i}" for i in ids}
    win._run = lambda w, done, fail_cb=None, **k: done(w._fn(*w._args, **w._kwargs))
    win._table_icon = lambda *a, **k: None
    _sp87.sprache_setzen("en")
    win._load_order_mods()
    _r34 = _zeile89("Item34")
    _r35 = _zeile89("Item35")
    check("b89 Zeile mit gescheitertem Abruf: Status '? unknown', nicht 'top'",
          _r34 is not None and win.sellord_table.item(_r34, 5).text() == _t4("? unknown"))
    check("b89 ... sie ist als unbekannt markiert und NICHT als 'zu aendern' gezaehlt",
          any(r.get("unknown") for r in win._ordmod_sell)
          and not any(r["flag"] for r in win._ordmod_sell if r.get("unknown")))
    check("b89 ... der Tooltip sagt, dass der Abruf scheiterte",
          _r34 is not None
          and "failed" in win.sellord_table.item(_r34, 5).toolTip())
    check("b89 die andere Zeile bleibt normal: Konkurrent bei 900 = 'undercut'",
          _r35 is not None
          and win.sellord_table.item(_r35, 5).text() == _t4("⚠ undercut"))
    check("b89 Unbekannte stehen vor den Guten (aber nach den zu aendernden)",
          _r35 is not None and _r34 is not None and _r35 < _r34
          and win.sellord_table.rowCount() == 2)
    check("b89 die Statuszeile nennt die Zahl der nicht pruefbaren Zeilen",
          "1" in win.statusBar().currentMessage()
          and "could not be checked" in win.statusBar().currentMessage())
    check("b89 der Reiter zaehlt nur echte Nachbesserungen (1)",
          "1 to adjust" in win._orders_inner.tabText(1))
    _sp87.sprache_setzen("de")
    win._fill_order_table(win.sellord_table, win._ordmod_sell, False)
    _z89 = _zeile89("Item34")
    check("b89 deutsch: Status und Tooltip der unbekannten Zeile sind uebersetzt",
          _z89 is not None and "unbekannt" in win.sellord_table.item(_z89, 5).text()
          and "fehlgeschlagen" in win.sellord_table.item(_z89, 5).toolTip())
finally:
    (_st89.list_characters, _esi83.fetch_character_orders, _esi83.fetch_type_orders,
     _esi83.resolve_names, win._run, win._table_icon, _sp87._aktuell) = _alt89
    win._ordmod_sell = []
    win._ordmod_buy = []
    win.sellord_table.setRowCount(0)
    win.buyord_table.setRowCount(0)
    win._ord_laeuft = False


# ---------------------------------------------------------------- (b90)
# STRUKTUR-HUB: "CHECK ORDERS" HOLT FRISCH, EIN FEHLSCHLAG BLEIBT EINER
# (Issue #18). `_structure_agg` hielt das Orderbuch 300 s im Speicher - auch
# fuer den Knopf, der "jetzt sofort" heisst. Und schlug ein Abruf fehl, kam das
# ALTE Buch zurueck und wurde mit neuem Zeitstempel wieder eingelagert: alte
# Daten galten weitere 5 Minuten als frisch. Jetzt: `force` umgeht den Speicher
# (Order update nutzt es immer), ein Fehlschlag fasst den alten Zeitstempel nicht
# an und wird gemeldet; die Zeilen stehen dann auf "? unknown" (wie #17).
_S90 = {"structure_id": 555, "character_id": 1, "name": "Cit", "region_id": 10000002}
_aufr90 = {"n": 0, "modus": "ok", "preis": 900.0}


def _voll90(client_id, cid, sid, progress=None):
    _aufr90["n"] += 1
    if _aufr90["modus"] == "fehl":
        raise RuntimeError("timeout")
    return {34: {"sell": [(_aufr90["preis"], 5)], "buy": [],
                 "sell_min": _aufr90["preis"], "buy_max": 0.0,
                 "sell_qty": 5, "buy_qty": 0}}


def _agg90(**kw):
    try:
        return win._structure_agg(_S90, **kw)
    except TypeError:
        return None


_alt90 = (_esi83.fetch_structure_orders_full, getattr(win, "_struct_cache", None),
          win._active_hub, _st89.list_characters, _esi83.fetch_character_orders,
          _esi83.resolve_names, win._run, win._table_icon, _sp87._aktuell)
try:
    _esi83.fetch_structure_orders_full = _voll90
    win._struct_cache = {}
    _agg90()
    _agg90()
    eq("b90 zwei normale Aufrufe hintereinander holen nur einmal (Speicher gilt)",
       _aufr90["n"], 1)
    _agg90(force=True)
    eq("b90 mit force wird trotzdem neu geholt", _aufr90["n"], 2)
    _ts90, _buch90 = win._struct_cache[555]
    win._struct_cache[555] = (_ts90 - 360, _buch90)
    _aufr90["modus"] = "fehl"
    _b90 = _agg90()
    check("b90 abgelaufen + Abruf scheitert: das alte Buch kommt zurueck",
          _b90 is _buch90)
    check("b90 ... aber mit dem ALTEN Zeitstempel (nicht als frisch neu gestempelt)",
          __import__("time").time() - win._struct_cache[555][0] > 300)
    _vor90 = _aufr90["n"]
    _agg90()
    check("b90 ... der naechste Aufruf versucht es deshalb erneut", _aufr90["n"] > _vor90)
    _aufr90["modus"] = "ok"
    try:
        _b90 = win._structure_books(_S90, [34, 99], force=True)
    except TypeError:
        _b90 = None
    check("b90 _structure_books: Erfolg -> keine Fehlermarke, unbekanntes Item ist leer",
          _b90 is not None and not _b90[34].get("failed") and not _b90[99].get("failed")
          and _b90[99]["sell"] == [])
    _aufr90["modus"] = "fehl"
    try:
        _b90 = win._structure_books(_S90, [34, 99], force=True)
    except TypeError:
        _b90 = None
    check("b90 _structure_books: scheitert der Abruf, tragen ALLE Buecher 'failed'",
          _b90 is not None and _b90[34].get("failed") is True and _b90[99].get("failed") is True)

    # ---- Ende-zu-Ende: Order update an einer Struktur
    _st89.list_characters = lambda: [{"character_id": 1, "character_name": "T"}]
    _esi83.fetch_character_orders = lambda c, cid: [
        {"type_id": 34, "price": 1000.0, "is_buy_order": False, "order_id": 1,
         "volume_remain": 10, "location_id": 555}]
    _esi83.resolve_names = lambda ids: {i: f"Item{i}" for i in ids}
    win._active_hub = lambda: (10000002, None, _S90)
    win._run = lambda w, done, fail_cb=None, **k: done(w._fn(*w._args, **w._kwargs))
    win._table_icon = lambda *a, **k: None
    _sp87.sprache_setzen("en")
    win._struct_cache = {}
    _aufr90.update(n=0, modus="ok", preis=900.0)
    win._load_order_mods()
    _r90 = _zeile89("Item34")
    eq("b90 Order update, Struktur: Konkurrent bei 900 -> undercut",
       win.sellord_table.item(_r90, 5).text() if _r90 is not None else None,
       _t4("⚠ undercut"))
    _aufr90["preis"] = 1100.0          # der Konkurrent ist weg / teurer
    win._load_order_mods()
    _r90 = _zeile89("Item34")
    eq("b90 ... sofort nochmal 'Check orders': der neue Markt zaehlt (top), nicht der Speicher",
       win.sellord_table.item(_r90, 5).text() if _r90 is not None else None,
       _t4("✓ top"))
    _aufr90["modus"] = "fehl"
    win._load_order_mods()
    _r90 = _zeile89("Item34")
    eq("b90 ... scheitert der Abruf, steht '? unknown' statt der alten Zahlen",
       win.sellord_table.item(_r90, 5).text() if _r90 is not None else None,
       _t4("? unknown"))
    check("b90 ... und die Statuszeile nennt es",
          "could not be checked" in win.statusBar().currentMessage())
finally:
    (_esi83.fetch_structure_orders_full, win._struct_cache, win._active_hub,
     _st89.list_characters, _esi83.fetch_character_orders, _esi83.resolve_names,
     win._run, win._table_icon, _sp87._aktuell) = _alt90
    win._ordmod_sell = []
    win._ordmod_buy = []
    win.sellord_table.setRowCount(0)
    win.buyord_table.setRowCount(0)
    win._ord_laeuft = False


# ---------------------------------------------------------------- (b91)
# ORDER UPDATE: UEBERHOLTE LAEUFE ZAEHLEN NICHT, EIN AUSGEFALLENER CHARAKTER
# WIRD GENANNT (Issues #19 und #20). `_load_order_mods` startet der Knopf, die
# Charakterauswahl und das Oeffnen des Reiters; `_ord_laeuft` wurde gesetzt,
# aber nie geprueft, und die Ergebnisse galten in der Reihenfolge des EINTREFFENS:
# ein aelterer Lauf, der zuletzt fertig wurde, ueberschrieb die neuen Daten
# ("899 top" wurde zu "1'000 undercut"). Jetzt traegt jeder Lauf eine Nummer,
# nur der juengste zaehlt (Ergebnis UND Fehler). Ausserdem: scheiterte der Abruf
# EINES Charakters (`except: pass`), fehlten dessen Orders wortlos - jetzt nennt
# ein Hinweis den Namen, und die Statuszeile zaehlt mit.
_alt91 = (_st89.list_characters, _esi83.fetch_character_orders,
          _esi83.fetch_type_orders, _esi83.resolve_names, win._run,
          win._table_icon, _sp87._aktuell)
_queue91 = []


def _neu91():
    _queue91.clear()
    win.sellord_table.setRowCount(0)
    win._ordmod_sell = []
    win._ordmod_buy = []
    win._ord_laeuft = False


def _job91(preis):
    """Den Job des zuletzt eingereihten Laufs jetzt ausfuehren (Netz gestellt)."""
    _esi83.fetch_character_orders = lambda c, cid: [_order89(34, preis, 1)]
    _w, _done, _fail = _queue91[-1]
    return _w._fn(*_w._args, **_w._kwargs), _done, _fail


def _preis91():
    return (win.sellord_table.rowCount(),
            win.sellord_table.item(0, 1).text() if win.sellord_table.rowCount() else None)


try:
    _st89.list_characters = lambda: [{"character_id": 1, "character_name": "Alpha"}]
    _esi83.fetch_type_orders = lambda tid, s, r: {"sell": [(900.0, 5)], "buy": []}
    _esi83.resolve_names = lambda ids: {i: f"Item{i}" for i in ids}
    win._run = lambda w, done, fail_cb=None, **k: _queue91.append((w, done, fail_cb))
    win._table_icon = lambda *a, **k: None
    _sp87.sprache_setzen("en")

    # ---- #19: aelterer Lauf trifft NACH dem neueren ein
    _neu91()
    win._load_order_mods()
    _d1, _done1, _fail1 = _job91(1000.0)          # aelterer Lauf, alter Preis
    win._load_order_mods()
    _d2, _done2, _fail2 = _job91(899.0)           # juengerer Lauf, neuer Preis
    _done2(_d2)
    _done1(_d1)
    eq("b91 aelterer Lauf trifft NACH dem neueren ein: es bleibt der neue Stand (899)",
       _preis91(), (1, "899"))

    # ---- #19: aelterer Lauf trifft VOR dem neueren ein
    _neu91()
    win._load_order_mods()
    _d1, _done1, _fail1 = _job91(1000.0)
    win._load_order_mods()
    _d2, _done2, _fail2 = _job91(899.0)
    _done1(_d1)
    eq("b91 aelterer Lauf trifft VOR dem neueren ein: er wird uebergangen (Tabelle leer)",
       _preis91()[0], 0)
    check("b91 ... und der neuere Lauf gilt weiter als laufend",
          getattr(win, "_ord_laeuft", None) is True)
    _done2(_d2)
    eq("b91 dann kommt der neue Stand", _preis91(), (1, "899"))
    check("b91 ... und erst jetzt ist nichts mehr in Arbeit",
          getattr(win, "_ord_laeuft", None) is False)

    # ---- #19: der Fehler eines ueberholten Laufs meldet nichts
    _neu91()
    win._load_order_mods()
    _d1, _done1, _fail1 = _job91(1000.0)
    win._load_order_mods()
    _d2, _done2, _fail2 = _job91(899.0)
    _done2(_d2)
    _vorher91 = win.statusBar().currentMessage()
    _fail1("boom")
    check("b91 der Fehler eines ueberholten Laufs ueberschreibt die Statuszeile nicht",
          win.statusBar().currentMessage() == _vorher91
          and "boom" not in win.statusBar().currentMessage())

    # ---- #19: ein einzelner Lauf funktioniert wie vorher
    _neu91()
    win._load_order_mods()
    _d1, _done1, _fail1 = _job91(1000.0)
    _done1(_d1)
    eq("b91 ein einzelner Lauf zeigt seinen Stand (1'000, undercut)",
       (_preis91(), win.sellord_table.item(0, 5).text()),
       ((1, "1'000"), _t4("⚠ undercut")))

    # ---- #20: ein Charakter faellt aus
    _st89.list_characters = lambda: [{"character_id": 1, "character_name": "Alpha"},
                                     {"character_id": 2, "character_name": "Beta"}]
    _neu91()

    def _chars91(fehl):
        def _f(c, cid):
            if cid in fehl:
                raise RuntimeError("403")
            return [_order89(34, 1000.0, cid)]
        return _f
    _esi83.fetch_character_orders = _chars91({2})
    win._load_order_mods()
    _w91, _done91, _ = _queue91[-1]
    _done91(_w91._fn(*_w91._args, **_w91._kwargs))
    _lab91 = getattr(win, "ord_fehl", None)
    eq("b91 die Orders des anderen Charakters werden weiter gezeigt (1 Zeile)",
       win.sellord_table.rowCount(), 1)
    check("b91 Hinweis nennt den ausgefallenen Charakter (Beta), nicht den anderen",
          _lab91 is not None and not _lab91.isHidden()
          and "Beta" in _lab91.text() and "Alpha" not in _lab91.text()
          and "could not be loaded" in _lab91.text())
    check("b91 die Statuszeile zaehlt den Ausfall mit",
          "1 character(s) could not be loaded" in win.statusBar().currentMessage())
    _sp87.sprache_setzen("de")
    _neu91()
    win._load_order_mods()
    _w91, _done91, _ = _queue91[-1]
    _done91(_w91._fn(*_w91._args, **_w91._kwargs))
    check("b91 deutsch: Hinweis und Statuszeile uebersetzt",
          _lab91 is not None and "konnten nicht geladen" in _lab91.text()
          and "nicht geladen" in win.statusBar().currentMessage())
    _sp87.sprache_setzen("en")
    _neu91()
    _esi83.fetch_character_orders = _chars91(set())
    win._load_order_mods()
    _w91, _done91, _ = _queue91[-1]
    _done91(_w91._fn(*_w91._args, **_w91._kwargs))
    check("b91 faellt kein Charakter mehr aus, verschwindet der Hinweis wieder",
          _lab91 is not None and _lab91.isHidden()
          and "could not be loaded" not in win.statusBar().currentMessage())
    eq("b91 dann sind beide Charaktere in der Liste (2 Zeilen)",
       win.sellord_table.rowCount(), 2)
finally:
    (_st89.list_characters, _esi83.fetch_character_orders, _esi83.fetch_type_orders,
     _esi83.resolve_names, win._run, win._table_icon, _sp87._aktuell) = _alt91
    win._ordmod_sell = []
    win._ordmod_buy = []
    win.sellord_table.setRowCount(0)
    win.buyord_table.setRowCount(0)
    win._ord_laeuft = False


# ---------------------------------------------------------------- (b92)
# ALTERS-SPALTE (Issue #21) UND DIE UNDO-SPALTE (Issue #28). Nirgends stand,
# WIE ALT die Daten hinter einer Zeile sind - dabei haelt ESI die eigenen Orders
# bis ~20 Min und Marktdaten ~5 Min im Cache, "Check orders" kann also
# rechtmaessig Altes liefern. Jetzt: Spalte "Age" in Kauf- UND Verkaufs-
# Tabelle des Order update und in der Einkaufsliste, aus dem Last-Modified des
# ESI-Antwortkopfs (schliesst ESIs Cache ein; ohne Kopf: Abrufzeit), als
# "45 s" / "3 min" / "1 h 5 min", alle 10 s neu; ab 5 Min bernstein, ab 20 Min
# rot. Zeile = das AELTERE von "deine Orders" und "Marktpreise". Ausserdem: das
# Zaehler-Feld ("Redo") wurde per Undo immer in Spalte 5 geschrieben - in der
# Verkaufs-Tabelle ist das der Status.
import time as _tm92
from eve_trader.ui import theme as _th92
import email.utils as _eu92
try:
    import eve_trader.ui.dataage as _da92
except ImportError:                                   # vor der Umsetzung
    _da92 = None
_f92 = lambda name, *a: getattr(_da92, name)(*a) if _da92 else "n/a"
for _s92, _w92 in ((0, "0 s"), (45, "45 s"), (59.9, "59 s"), (60, "1 min"), (200, "3 min"),
                   (3599, "59 min"), (3600, "1 h"), (3900, "1 h 5 min"), (None, "—")):
    eq(f"b92 format_age({_s92})", _f92("format_age", _s92), _w92)
for _s92, _w92 in ((None, "unknown"), (0, "ok"), (300, "ok"), (300.1, "amber"),
                   (1200, "amber"), (1200.1, "red")):
    eq(f"b92 level({_s92}): bernstein NACH 5 Min, rot NACH 20 Min", _f92("level", _s92), _w92)
eq("b92 age_seconds: Uhr-Abweichung (Zukunft) wird auf 0 geklemmt",
   _f92("age_seconds", 110.0, 100.0), 0.0)
eq("b92 age_seconds ohne Zeitstempel: None", _f92("age_seconds", None, 100.0), None)
eq("b92 oldest: der aeltere Stempel, None wird uebergangen",
   _f92("oldest", 50.0, None, 30.0), 30.0)
eq("b92 oldest ohne jeden Stempel: None", _f92("oldest", None, None), None)

# ---- ESI: Last-Modified -> as_of
_HTTP92 = "Mon, 21 Sep 2026 10:00:00 GMT"
_T92 = _eu92.parsedate_to_datetime(_HTTP92).timestamp()


class _Antw92:
    def __init__(self, daten, kopf, seiten=1):
        self._d, self.headers = daten, dict(kopf, **{"X-Pages": str(seiten)})

    def json(self):
        return self._d

    def raise_for_status(self):
        pass


_dt92 = getattr(_esi83, "_data_time", None)
check("b92 _data_time liest Last-Modified", _dt92 is not None
      and _dt92(_Antw92([], {"Last-Modified": _HTTP92})) == _T92)
check("b92 ... ohne Kopf gilt die Abrufzeit (jetzt)",
      _dt92 is not None and abs(_dt92(_Antw92([], {})) - _tm92.time()) < 5)
_alt_g92 = (_esi83._get_with_retry, _esi83._auth_headers)
try:
    _esi83._auth_headers = lambda c, cid: {}
    _esi83._get_with_retry = lambda *a, **k: _Antw92([{"order_id": 1}],
                                                     {"Last-Modified": _HTTP92})
    _l92 = _esi83.fetch_character_orders("c", 1)
    check("b92 fetch_character_orders: Liste UND as_of (Inhalt unveraendert)",
          list(_l92) == [{"order_id": 1}] and getattr(_l92, "as_of", None) == _T92)
    _seite92 = [0]

    def _zwei92(*a, **k):
        _seite92[0] += 1
        _k = {"Last-Modified": "Mon, 21 Sep 2026 10:00:%02d GMT" % (30 if _seite92[0] == 1 else 0)}
        return _Antw92([{"location_id": 60003760, "is_buy_order": False,
                         "price": 5.0 * _seite92[0], "volume_remain": 1}], _k, seiten=2)
    _esi83._get_with_retry = _zwei92
    _b92 = _esi83.fetch_type_orders(34, station=60003760, region=10000002)
    check("b92 fetch_type_orders: as_of ist der AELTESTE Stempel der Seiten",
          _b92.get("as_of") == _T92 and len(_b92["sell"]) == 2)
    _seite92[0] = 0
    _esi83._get_with_retry = lambda *a, **k: _Antw92(
        [{"type_id": 34, "is_buy_order": False, "price": 9.0, "volume_remain": 1}],
        {"Last-Modified": _HTTP92})
    _s92 = _esi83.fetch_structure_orders_full("c", 1, 5)
    check("b92 fetch_structure_orders_full: das Buch traegt as_of, bleibt ein dict",
          getattr(_s92, "as_of", None) == _T92 and 34 in _s92)
finally:
    _esi83._get_with_retry, _esi83._auth_headers = _alt_g92

# ---- Order update: Kauf- UND Verkaufs-Tabelle
_alt92 = (_st89.list_characters, _esi83.fetch_character_orders,
          _esi83.fetch_type_orders, _esi83.resolve_names, win._run,
          win._table_icon, _sp87._aktuell)
def _tick92(jetzt):
    _f = getattr(win, "_age_tick", None)
    if _f is not None:
        _f(now=jetzt)


_TL92 = getattr(_esi83, "TimedList", type("_Liste92", (list,), {}))


def _txt92(tabelle, zeile, spalte):
    _i = tabelle.item(zeile, spalte) if zeile is not None else None
    return _i.text() if _i is not None else None


def _farbe92(tabelle, zeile, spalte):
    _i = tabelle.item(zeile, spalte) if zeile is not None else None
    return _i.foreground().color().name().lower() if _i is not None else None


def _lade92(orders_alter, markt_alter, fehl=()):
    _jetzt = _tm92.time()
    _o = _TL92([_order89(34, 1000.0, 1),
                {"type_id": 35, "price": 100.0, "is_buy_order": True, "order_id": 2,
                 "volume_remain": 5, "location_id": _stat89}])
    _o.as_of = _jetzt - orders_alter
    _esi83.fetch_character_orders = lambda c, cid: _o

    def _buch(tid, s, r):
        if tid in fehl:
            raise RuntimeError("420")
        return {"sell": [(900.0, 5)], "buy": [(120.0, 5)], "as_of": _jetzt - markt_alter}
    _esi83.fetch_type_orders = _buch
    win._load_order_mods()
    return _jetzt


def _zeile92(tabelle, name):
    for _r in range(tabelle.rowCount()):
        if tabelle.item(_r, 0).text() == name:
            return _r
    return None


try:
    _st89.list_characters = lambda: [{"character_id": 1, "character_name": "T"}]
    _esi83.resolve_names = lambda ids: {i: f"Item{i}" for i in ids}
    win._run = lambda w, done, fail_cb=None, **k: done(w._fn(*w._args, **w._kwargs))
    win._table_icon = lambda *a, **k: None
    _sp87.sprache_setzen("en")
    _lade92(100, 400)                       # Orders 100 s alt, Markt 400 s alt
    _rb92 = _zeile92(win.buyord_table, "Item35")
    _rs92 = _zeile92(win.sellord_table, "Item34")
    eq("b92 Kauf-Tabelle: Spalte 4 heisst 'Age'",
       win.buyord_table.horizontalHeaderItem(4).text(), _t4("Age"))
    eq("b92 Verkaufs-Tabelle: Spalte 6 heisst 'Age'",
       win.sellord_table.horizontalHeaderItem(6).text(), _t4("Age"))
    eq("b92 Kauf-Tabelle: das AELTERE zaehlt (Markt 400 s = 6 min)",
       _txt92(win.buyord_table, _rb92, 4), "6 min")
    eq("b92 Verkaufs-Tabelle: dasselbe (6 min)",
       _txt92(win.sellord_table, _rs92, 6), "6 min")
    eq("b92 Farbe ab 5 Min: bernstein (Kauf)",
       _farbe92(win.buyord_table, _rb92, 4), _th92.AMBER.lower())
    eq("b92 Farbe ab 5 Min: bernstein (Verkauf)",
       _farbe92(win.sellord_table, _rs92, 6), _th92.AMBER.lower())
    _tip92 = win.sellord_table.item(_rs92, 6).toolTip() if _rs92 is not None else ""
    check("b92 Tooltip nennt beide Alter getrennt (Orders 1 min, Markt 6 min)",
          "Your orders: 1 min" in _tip92 and "Market prices: 6 min" in _tip92)
    check("b92 die Status-Spalten bleiben, wo sie waren (Kauf 3, Verkauf 5)",
          _txt92(win.buyord_table, _rb92, 3) == _t4("⚠ outbid")
          and _txt92(win.sellord_table, _rs92, 5) == _t4("⚠ undercut"))
    _jetzt92 = _tm92.time()
    _tick92(_jetzt92 + 900)
    eq("b92 Zaehler tickt: nach 15 weiteren Minuten (Markt 1300 s) = 21 min",
       _txt92(win.sellord_table, _rs92, 6), "21 min")
    eq("b92 ... und ist jetzt rot (ueber 20 Min)",
       _farbe92(win.sellord_table, _rs92, 6), _th92.RED.lower())
    eq("b92 ... auch in der Kauf-Tabelle", _txt92(win.buyord_table, _rb92, 4), "21 min")
    check("b92 der Zeit-Takt laeuft (10 s)",
          getattr(win, "_age_cell_timer", None) is not None
          and win._age_cell_timer.isActive() and win._age_cell_timer.interval() == 10000)
    _lade92(10, 20)
    _rs92 = _zeile92(win.sellord_table, "Item34")
    eq("b92 frische Daten: '20 s', normale Textfarbe",
       (_txt92(win.sellord_table, _rs92, 6), _farbe92(win.sellord_table, _rs92, 6)),
       ("20 s", _th92.TEXT.lower()))
    _lade92(10, 20, fehl=(34,))
    _rs92 = _zeile92(win.sellord_table, "Item34")
    eq("b92 gescheiterter Marktabruf (unknown): kein Alter erfunden, '—'",
       _txt92(win.sellord_table, _rs92, 6), "—")
    _sp87.sprache_setzen("de")
    win._fill_order_table(win.sellord_table, win._ordmod_sell, False)
    eq("b92 deutsch: der Spaltenkopf heisst 'Alter'", _t4("Age"), "Alter")
    _sp87.sprache_setzen("en")

    # ---- Undo-Zaehler (Issue #28): richtige Spalte je Tabelle
    _lade92(10, 20)
    _rs92 = _zeile92(win.sellord_table, "Item34")
    _rb92 = _zeile92(win.buyord_table, "Item35")
    win._set_order_mod_cell(win.sellord_table, 1, 3)
    eq("b92 Undo an einer Verkaufs-Order: der ZAEHLER (Spalte 8) zeigt 3",
       _txt92(win.sellord_table, _rs92, 8), "3")
    eq("b92 ... und der Status (Spalte 5) bleibt unangetastet",
       _txt92(win.sellord_table, _rs92, 5), _t4("⚠ undercut"))
    win._set_order_mod_cell(win.buyord_table, 2, 2)
    eq("b92 Undo an einer Kauf-Order: Zaehler in Spalte 6", _txt92(win.buyord_table, _rb92, 6), "2")
    eq("b92 ... Status (Spalte 3) unangetastet",
       _txt92(win.buyord_table, _rb92, 3), _t4("⚠ outbid"))
finally:
    (_st89.list_characters, _esi83.fetch_character_orders, _esi83.fetch_type_orders,
     _esi83.resolve_names, win._run, win._table_icon, _sp87._aktuell) = _alt92
    win._ordmod_sell = []
    win._ordmod_buy = []
    win.sellord_table.setRowCount(0)
    win.buyord_table.setRowCount(0)
    win._ord_laeuft = False

# ---- Einkaufsliste
_alt_sh92 = (_st89.list_shopping, win._table_icon, getattr(win, "_sh_ladders", {}),
             getattr(win, "_sh_sort", (None, True)), _sp87._aktuell)
try:
    _st89.list_shopping = lambda: [
        {"id": 1, "type_id": 34, "name": "Item34", "qty": 5, "source": "manual"},
        {"id": 2, "type_id": 35, "name": "Item35", "qty": 2, "source": "manual"}]
    win._table_icon = lambda *a, **k: None
    _sp87.sprache_setzen("en")
    win._sh_sort = (None, True)
    _jetzt92 = _tm92.time()
    win._sh_ladders = {34: {"sell": [(900.0, 5)], "buy": [(800.0, 5)],
                            "as_of": _jetzt92 - 400}}
    win._render_shopping()
    eq("b92 Einkaufsliste: 11 Spalten, Alter vor dem Loeschen-Knopf",
       (win.sh_table.columnCount(), win.sh_table.horizontalHeaderItem(9).text()),
       (11, _t4("Age")))
    check("b92 ... der Loeschen-Knopf sitzt jetzt in Spalte 10",
          win.sh_table.cellWidget(0, 10) is not None)
    _r34 = next((r for r in range(win.sh_table.rowCount())
                 if "Item34" in win.sh_table.item(r, 0).text()), None)
    _r35 = next((r for r in range(win.sh_table.rowCount())
                 if "Item35" in win.sh_table.item(r, 0).text()), None)
    eq("b92 Einkaufsliste: Alter der geladenen Preise (6 min), bernstein",
       (_txt92(win.sh_table, _r34, 9), _farbe92(win.sh_table, _r34, 9)),
       ("6 min", _th92.AMBER.lower()))
    eq("b92 ... ohne geladene Preise: '—' (nichts erfunden)",
       _txt92(win.sh_table, _r35, 9), "—")
    _tick92(_jetzt92 + 1000)
    eq("b92 ... tickt mit (1400 s = 23 min, rot)",
       (_txt92(win.sh_table, _r34, 9), _farbe92(win.sh_table, _r34, 9)),
       ("23 min", _th92.RED.lower()))
    _tax92 = win.settings["sales_tax_pct"] / 100.0
    _brk92 = win.settings["broker_fee_pct"] / 100.0
    _rows92 = _st89.list_shopping()
    _sv34 = win._shopping_sort_value(_rows92[0], 9, _tax92, _brk92)
    _sv35 = win._shopping_sort_value(_rows92[1], 9, _tax92, _brk92)
    check("b92 Sortierung nach Alter: geladen zaehlt Sekunden, ohne Preise zuletzt",
          isinstance(_sv34, (int, float)) and 390 < _sv34 < 500 and _sv35 > _sv34)
    _sp87.sprache_setzen("de")
    win._render_shopping()
    check("b92 deutsch: Spaltenkopf der Einkaufsliste 'Alter'",
          _t4("Age") == "Alter")
finally:
    (_st89.list_shopping, win._table_icon, win._sh_ladders, win._sh_sort,
     _sp87._aktuell) = _alt_sh92
    win._render_shopping()


# ---------------------------------------------------------------- (b93)
# DER ITEM-NAME STEHT OBEN IM AUSWAHL-PANEL, NEBEN DER MENGE (Issue #22). Das
# Panel oben rechts (Daytrade, Swing, Regional teilen es) zeigte die Order-Leiter
# eines Items, aber nicht, WELCHES Item das ist. Der fruehere Info-Text war aus
# gutem Grund versteckt (Sitzung 12): er brach auf mehrere Zeilen um und schob die
# Item-Liste darunter bei jedem Klick. Deshalb EINE Zeile, hinten mit "..."
# gekuerzt (ElideLabel, Mindestbreite 0), voller Name im Tooltip. Der Name folgt
# der Leiter, die darunter steht: gesetzt wird er dort, wo die Leiter gezeichnet
# wird - scheitert ein Abruf, bleiben beide beim vorigen Item.
_alt93 = (win._run, getattr(win, "_hub_orders", None), _sp87._aktuell)
try:
    _sp87.sprache_setzen("en")
    for _k93 in ("day", "swing", "region"):
        _c93 = win._ladder_ctx.get(_k93) or {}
        _l93 = _c93.get("name_lbl")
        check(f"b93 {_k93}: das Panel hat ein Namens-Label (ElideLabel, eine Zeile)",
              _l93 is not None and type(_l93).__name__ == "ElideLabel"
              and not _l93.wordWrap())
        _box93 = _c93["table"].parentWidget() if _c93 else None
        _head93 = _box93.layout().itemAt(0).layout() if _box93 is not None else None
        check(f"b93 {_k93}: der Name steht in der Kopfzeile VOR dem Mengen-Feld",
              _l93 is not None and _head93 is not None
              and 0 <= _head93.indexOf(_l93) < _head93.indexOf(_c93["spin"]))
    _c93 = win._ladder_ctx["day"]
    _l93 = _c93.get("name_lbl")
    win._render_ladder("day", 34, "Tritanium", [(5.0, 100), (5.1, 200)], 0)
    eq("b93 nach dem Zeichnen der Leiter steht der Name da",
       _l93.text() if _l93 is not None else None, "Tritanium")
    eq("b93 ... und der volle Name auch im Tooltip",
       _l93.toolTip() if _l93 is not None else None, "Tritanium")
    _h_kurz93 = _l93.sizeHint().height() if _l93 is not None else None
    _lang93 = "Medium Capacitor Control Circuit II " * 6
    win._render_ladder("day", 35, _lang93, [(6.0, 50)], 0)
    check("b93 ein sehr langer Name bricht NICHT um: gleiche Hoehe wie ein kurzer",
          _l93 is not None and _l93.sizeHint().height() == _h_kurz93)
    check("b93 ... und verbreitert das Panel nicht (Mindestbreite 0, Breite ignoriert)",
          _l93 is not None and _l93.minimumSizeHint().width() == 0
          and _l93.sizePolicy().horizontalPolicy().name == "Ignored")
    eq("b93 ... der volle lange Name bleibt lesbar (Text und Tooltip)",
       (_l93.text(), _l93.toolTip()) if _l93 is not None else None, (_lang93, _lang93))
    # Abruf per Klick: Erfolg setzt den Namen, ein Fehler laesst Name UND Leiter stehen
    win._render_ladder("day", 34, "Tritanium", [(5.0, 100)], 0)

    def _sync93(w, done, fail_cb=None, **k):
        try:
            _r = w._fn(*w._args, **w._kwargs)
        except Exception as _e:
            if fail_cb:
                fail_cb(str(_e))
            return
        done(_r)
    win._run = _sync93
    win._hub_orders = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("420"))
    win._load_ladder("day", 36, "Pyerite")
    eq("b93 scheitert der Abruf, bleibt der Name beim Item, dessen Leiter noch da steht",
       _l93.text() if _l93 is not None else None, "Tritanium")
    win._hub_orders = lambda *a, **k: {"buy": [(7.0, 10)], "sell": [(8.0, 10)]}
    win._load_ladder("day", 36, "Pyerite")
    eq("b93 klappt der Abruf, steht der neue Name da",
       _l93.text() if _l93 is not None else None, "Pyerite")
    _sp87.sprache_setzen("de")
    win._render_ladder("day", 34, "Tritanium", [(5.0, 100)], 0)
    eq("b93 Item-Namen kommen aus EVE und werden nicht uebersetzt (auch auf Deutsch)",
       _l93.text() if _l93 is not None else None, "Tritanium")
finally:
    win._run = _alt93[0]
    if _alt93[1] is not None:
        win._hub_orders = _alt93[1]
    _sp87.sprache_setzen(_alt93[2] if _alt93[2] in ("en", "de") else "en")
    for _k93 in ("day", "swing", "region"):
        _c93 = win._ladder_ctx.get(_k93)
        if _c93:
            _c93["table"].setRowCount(0)
            _c93["current"] = None
            _c93["ladder"] = []


# ---------------------------------------------------------------- (b94)
# DAYTRADE: EIN FEHLER LEERT DIE TABELLE (Issue #23) UND DER WAGEN NIMMT DEN
# TAGESBEDARF (Issue #24). #23: schlug "Deals berechnen" fehl, stand nur die
# Fehlerzeile da - die Tabelle des VORIGEN Laufs blieb und sah aus wie das
# Ergebnis der aktuellen Einstellungen (Regional hat dafuer seit langem einen
# Stale-Schutz). #24: nach dem Einfuegen sagte die Meldung "Menge = Tages-
# bedarf", der Wagen bekam aber Menge 1 (der Vorschlag lag nur in sugg_qty).
# Nutzer-Entscheid: die MENGE wird angepasst - Tagesbedarf = Anteil am
# Tagesvolumen nach Konkurrenz, mindestens 1.
import eve_trader.scanner as _sc94
from PySide6.QtWidgets import QTableWidgetItem as _QTWI94
_alt94 = (_st89.get_snapshot, _sc94.find_deals, _esi83.resolve_names, win._run,
          _sp87._aktuell)
_kopf94 = "  – no results (old table discarded)."


def _seed94():
    win.deals_table.setRowCount(2)
    for _r in range(2):
        win.deals_table.setItem(_r, 0, _QTWI94(f"Old{_r}"))
    win._last_deals = [{"type_id": 34}]
    win._deals_last = ([{"type_id": 34}], "flip")
    win._ladder_ctx["day"]["deals"] = {34: {"type_id": 34}}


def _boom94(*a, **k):
    raise RuntimeError("420 error limited")


def _lauf94(w, done, fail_cb=None, **k):
    try:
        _r = w._fn(*w._args, **w._kwargs)
    except Exception as _e:
        if fail_cb:
            fail_cb(str(_e))
        return
    done(_r)


try:
    _st89.get_snapshot = lambda: [{"type_id": 34, "sell_min": 100.0, "buy_max": 90.0,
                                   "sell_qty": 5, "buy_qty": 5}]
    _esi83.resolve_names = lambda ids: {}
    win._run = _lauf94
    _sp87.sprache_setzen("en")
    _seed94()
    _sc94.find_deals = _boom94
    win.compute_deals()
    eq("b94 Fehler beim Berechnen: die Tabelle des vorigen Laufs ist weg",
       win.deals_table.rowCount(), 0)
    check("b94 ... auch die gemerkten Deals und die der Leiter (nichts Altes bleibt)",
          win._last_deals == [] and win._ladder_ctx["day"]["deals"] == {})
    try:
        win._rerender_deals()
        _neu94 = win.deals_table.rowCount()
    except Exception:
        _neu94 = -1
    eq("b94 ... und ein spaeteres Neuzeichnen (Bilder-Nachtrag) holt sie nicht zurueck",
       _neu94, 0)
    check("b94 die Statuszeile nennt den Fehler UND dass die alte Tabelle verworfen wurde",
          "Error: " in win.deal_status.text() and "420 error limited" in win.deal_status.text()
          and _kopf94 in win.deal_status.text())
    check("b94 der Knopf ist wieder frei", win.deals_btn.isEnabled())
    _sp87.sprache_setzen("de")
    _seed94()
    win.compute_deals()
    check("b94 deutsch: der Hinweis 'alte Tabelle verworfen' ist uebersetzt",
          _t4(_kopf94) != _kopf94 and _t4(_kopf94) in win.deal_status.text())
    _sp87.sprache_setzen("en")
    _sc94.find_deals = lambda *a, **k: []
    win.compute_deals()
    check("b94 danach klappt ein normaler Lauf wieder (kein Fehler in der Statuszeile)",
          "Error: " not in win.deal_status.text() and win.deals_btn.isEnabled())
finally:
    (_st89.get_snapshot, _sc94.find_deals, _esi83.resolve_names, win._run,
     _sp87._aktuell) = _alt94
    win.deals_table.setRowCount(0)
    win._last_deals = []
    win._deals_last = (None, None)
    win._ladder_ctx["day"]["deals"] = {}

# ---- #24: der Wagen bekommt den Tagesbedarf
_wagen94 = []
_alt2_94 = (_st89.add_shopping, win._cart_ids, win._render_shopping,
            win._cart_conflict_filter)
_deals94 = win._ladder_ctx["day"]["deals"]
try:
    _st89.add_shopping = (lambda tid, name, qty, buy=0.0, sell=0.0, source="",
                          sugg_qty=0: _wagen94.append((tid, qty, source, sugg_qty)))
    win._cart_ids = lambda: set()
    win._render_shopping = lambda: None
    win._cart_conflict_filter = lambda items: items
    win._ladder_ctx["day"]["deals"] = {
        34: {"type_id": 34, "daily_vol": 300, "competitors": 2},
        35: {"type_id": 35, "daily_vol": 0.4, "competitors": 0}}
    _r94 = win._add_deal_to_cart(34, "Item34")
    check("b94 Wagen: Menge = Tagesbedarf (300 / (2 + 1 Konkurrenten) = 100), Vorschlag gleich",
          _wagen94[-1] == (34, 100, "daytrade", 100) and _r94 == 100)
    win._add_deal_to_cart(34, "Item34", qty=7)
    check("b94 ... eine ausdrueckliche Menge gilt weiter (7), der Vorschlag wird trotzdem gemerkt",
          _wagen94[-1] == (34, 7, "daytrade", 100))
    win._add_deal_to_cart(35, "Item35")
    check("b94 ... sehr kleines Volumen: mindestens 1", _wagen94[-1][1] == 1)
    win._add_deal_to_cart(99, "Unknown")
    check("b94 ... Deal nicht bekannt: Menge 1, kein Vorschlag",
          _wagen94[-1] == (99, 1, "daytrade", 0))
    _n94 = len(_wagen94)
    win._cart_ids = lambda: {34}
    _r94 = win._add_deal_to_cart(34, "Item34")
    check("b94 ... schon im Wagen: False, nichts wird hinzugefuegt",
          _r94 is False and len(_wagen94) == _n94)
    # die Mehrfachauswahl im Daytrade-Tab
    win._cart_ids = lambda: set()
    win.deals_table.setRowCount(1)
    _z94 = _QTWI94("Item34")
    _z94.setData(Qt.UserRole, 34)
    win.deals_table.setItem(0, 0, _z94)
    _n94 = len(_wagen94)
    win._deals_add_selection([0])
    check("b94 Daytrade-Auswahl -> Wagen: Menge 100 (Tagesbedarf), wie die Meldung sagt",
          len(_wagen94) == _n94 + 1 and _wagen94[-1][:2] == (34, 100)
          and "1-day intake" in win.statusBar().currentMessage())
    _src94 = __import__("inspect").getsource(type(win)._show_gold_dialog)
    check("b94 Gold-Suche (Kontextmenue): die Meldung nennt die WIRKLICHE Menge",
          "(quantity {qty})" in _src94 and "(quantity 1)" not in _src94)
    _sp87.sprache_setzen("de")
    _m94 = _t4("{name} added to the shopping cart (quantity {qty}).")
    check("b94 ... und ist uebersetzt (mit beiden Platzhaltern)",
          "{qty}" in _m94 and "{name}" in _m94
          and _m94 != "{name} added to the shopping cart (quantity {qty}).")
finally:
    (_st89.add_shopping, win._cart_ids, win._render_shopping,
     win._cart_conflict_filter) = _alt2_94
    _sp87.sprache_setzen("en")
    win._ladder_ctx["day"]["deals"] = _deals94
    win.deals_table.setRowCount(0)


# ---------------------------------------------------------------- (b95)
# DAYTRADE RECHNET UND ZEIGT DEN REALISTISCHEN GEWINN (Issue #32, Variante B).
# find_deals kannte den realistischen Gewinn (Spread auf den Median-Tagesspread
# der Historie gedeckelt, "spread_capped"), aber Tabelle, Filter (Gewinn/Stueck,
# ROI, Gewinn/Tag) und Standard-Sortierung liefen auf dem PAPIER-Gewinn aus dem
# Momentanbuch; der realistische Wert skalierte nur den Score (mit Boden 10 %).
# Jetzt: bei gedeckeltem Spread SIND profit_unit / roi / profit_day / capture_day
# die realistischen Werte (Filter wirken darauf, ein realistisch negativer Deal
# faellt raus), die Papier-Zahlen stehen in profit_paper / roi_paper /
# profit_day_paper, die Tabelle kennzeichnet sie mit einer Tilde.
# Zahlenbasis (Steuer 3.375 %, Broker 1.5 %):
#   A kauf 1000 / verkauf 1500, Tagesspanne 300: Papier 411.875, real 221.625
#   B kauf 1000 / verkauf 1200, Tagesspanne 250: nicht gedeckelt, 126.5
#   C kauf 1000 / verkauf 1300, Tagesspanne  50: Papier 221.625, real -16.1875
import eve_trader.scanner as _sc95


def _hist95(lo, hi):
    return [{"date": f"2026-08-{d + 1:02d}", "average": (lo + hi) / 2.0,
             "highest": float(hi), "lowest": float(lo), "volume": 100,
             "order_count": 20} for d in range(28)]


_HIST95 = {1: _hist95(1000, 1300), 2: _hist95(1000, 1250), 3: _hist95(1000, 1050)}
_SNAP95 = [{"type_id": t95, "sell_min": s95, "buy_max": 1000.0, "sell_qty": 500,
            "buy_qty": 500, "sell_orders": 3, "buy_orders": 3,
            "sell_best_qty": 50, "buy_best_qty": 50}
           for t95, s95 in ((1, 1500.0), (2, 1200.0), (3, 1300.0))]
_SET95 = {"sales_tax_pct": 3.375, "broker_fee_pct": 1.5}
_alt_hc95 = _sc95.history_cached
_sc95.history_cached = lambda tid, region=10000002, *a, **k: _HIST95[tid]


def _deals95(**filt):
    _f = {"min_buy_ratio": 25, "max_items": 100}
    _f.update(filt)
    return {d["type_id"]: d for d in
            _sc95.find_deals(_SNAP95, _SET95, 28, "flip", _f, region=10000002)}


def _nahe95(a, b, tol=1e-6):
    return a is not None and abs(a - b) < tol


try:
    _r95 = _deals95()
    _a95, _b95 = _r95.get(1) or {}, _r95.get(2) or {}
    check("b95 A (gedeckelt): profit_unit ist der REALISTISCHE Gewinn (221.625)",
          _a95.get("spread_capped") is True and _nahe95(_a95.get("profit_unit"), 221.625))
    check("b95 ... das Papier steht in profit_paper (411.875)",
          _nahe95(_a95.get("profit_paper"), 411.875))
    check("b95 ... ROI real 22.16 %, ROI Papier 41.19 %",
          _nahe95(_a95.get("roi"), 22.1625, 1e-4) and _nahe95(_a95.get("roi_paper"), 41.1875, 1e-4))
    check("b95 ... Gewinn/Tag real 22'162.5, Papier 41'187.5",
          _nahe95(_a95.get("profit_day"), 22162.5) and _nahe95(_a95.get("profit_day_paper"), 41187.5))
    check("b95 ... einnehmbar/Tag folgt dem realistischen Wert (durch 3 + 1 Konkurrenten)",
          _nahe95(_a95.get("capture_day"), 22162.5 / 4))
    check("b95 B (nicht gedeckelt): Papier = real = 126.5, keine Kennzeichnung",
          _b95.get("spread_capped") is False and _nahe95(_b95.get("profit_unit"), 126.5)
          and _nahe95(_b95.get("profit_paper"), 126.5) and _nahe95(_b95.get("roi"), 12.65, 1e-4))
    check("b95 C (realistisch negativ) faellt raus, obwohl das Papier +221.6 zeigte",
          3 not in _r95)
    eq("b95 min. Gewinn/Stueck 300 liegt zwischen real und Papier: A faellt raus, B auch",
       sorted(_deals95(min_profit_isk=300)), [])
    eq("b95 min. Gewinn/Stueck 200: A bleibt (real 221.6), B faellt (126.5)",
       sorted(_deals95(min_profit_isk=200)), [1])
    eq("b95 min. ROI 30 % (real 22 %, Papier 41 %): A faellt raus",
       sorted(_deals95(min_roi=30)), [])
    eq("b95 min. ROI 20 %: A bleibt, B (12.65 %) faellt",
       sorted(_deals95(min_roi=20)), [1])
    eq("b95 min. Gewinn/Tag 30'000 (real 22'162, Papier 41'187): A faellt raus",
       sorted(_deals95(min_profit_day=30000)), [])
    eq("b95 min. Gewinn/Tag 20'000: A bleibt, B (12'650) faellt",
       sorted(_deals95(min_profit_day=20000)), [1])

    # ---- Tabelle
    _alt_ui95 = (win._icon_prefetch_pending, win._table_icon,
                 getattr(win, "_deals_last", (None, None)), _sp87._aktuell)
    win._icon_prefetch_pending = lambda *a, **k: None
    win._table_icon = lambda *a, **k: None
    try:
        _sp87.sprache_setzen("en")
        win._render_deals([_a95, _b95], "flip")
        _zeilen95 = {win.deals_table.item(r, 0).data(Qt.UserRole): r
                     for r in range(win.deals_table.rowCount())}
        _ra, _rb = _zeilen95.get(1), _zeilen95.get(2)

        def _z95(zeile, spalte):
            return win.deals_table.item(zeile, spalte) if zeile is not None else None
        check("b95 Tabelle A: Gewinn, ROI und Gewinn/Tag tragen die Tilde (real)",
              all(_z95(_ra, c) is not None and _z95(_ra, c).text().startswith("≈")
                  for c in (6, 7, 11)))
        check("b95 ... der Tooltip nennt den Papier-Wert (Gewinn 412, ROI 41.2 %, Gewinn/Tag 41'188)",
              "412" in _z95(_ra, 6).toolTip() and "41.2 %" in _z95(_ra, 7).toolTip()
              and "41'188" in _z95(_ra, 11).toolTip().replace(",", "'"))
        check("b95 ... und erklaert es (Median-Tagesspread)",
              "median daily spread" in _z95(_ra, 6).toolTip())
        check("b95 Tabelle B (nicht gedeckelt): keine Tilde, kein Zusatz-Tooltip",
              all(_z95(_rb, c).text()[:1] != "≈" and _z95(_rb, c).toolTip() == ""
                  for c in (6, 7, 11)))
        check("b95 Tradability-Tooltip von A: 'nutzt den realistischen Gewinn' (kein 'Bewertung')",
              "profit, ROI and profit/day use the realistic profit" in _z95(_ra, 17).toolTip())
        _sp87.sprache_setzen("de")
        win._render_deals([_a95], "flip")
        _tipd95 = win.deals_table.item(0, 6).toolTip()
        check("b95 deutsch: der Tooltip ist uebersetzt",
              "Realistic figure" not in _tipd95 and "Median" in _tipd95
              and "412" in _tipd95)
    finally:
        win._icon_prefetch_pending, win._table_icon = _alt_ui95[0], _alt_ui95[1]
        win._deals_last = _alt_ui95[2]
        _sp87.sprache_setzen("en")
        win.deals_table.setRowCount(0)
finally:
    _sc95.history_cached = _alt_hc95


# ---------------------------------------------------------------- (b79)
# FEHLER.LOG-NETZ (siehe Kopf der Datei): alles, was dieser Lauf an
# fehler.log angehaengt hat, darf keinen Programmierfehler enthalten.
# Netz-/ESI-Fehler (offline, Test-Corp 403) sind erwartet und bleiben erlaubt.
_flog_neu = ""
try:
    with open(_FLOG, "r", encoding="utf-8", errors="replace") as _fh79:
        _fh79.seek(_FLOG_START)
        _flog_neu = _fh79.read()
except OSError:
    pass
_flog_bad = [_z.strip() for _z in _flog_neu.splitlines()
             if "has no attribute" in _z or "NameError" in _z
             or "is not defined" in _z or "TypeError" in _z
             or "KeyError" in _z or "IndexError" in _z]
check("b79 fehler.log: keine Programmierfehler waehrend des Laufs angehaengt"
      + (" - " + " | ".join(sorted(set(_flog_bad))[:3]) if _flog_bad else ""),
      not _flog_bad)

print(f"(b) Bauplan-Aufbau: {_ok}/{_ok + len(_fail)} gruen")
for f in _fail:
    print("  FEHLER: " + f)
# Sauber abraeumen: im Hintergrund koennen noch Worker laufen (Auto-Suche
# nach Asset-Orten, Preisabrufe). Ohne das beendet sich der Prozess mit
# "QThread: Destroyed while thread is still running" + Abort - das saehe wie
# ein Testfehler aus, obwohl alle Pruefungen gruen sind.
try:
    if _dlg is not None:
        _dlg.close()
    win.close()
    _app.processEvents()
except Exception:
    pass
sys.stdout.flush()
os._exit(1 if _fail else 0)
