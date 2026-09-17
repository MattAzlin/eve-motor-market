"""Die vier grossen Fuell-Funktionen der Bauplan-Tabs - als Mixin
ausgelagert (Sitzung 8, Nutzer: "wir haben zu viel Code, es ist zu
unuebersichtlich").

REGELN FUER DIESES MODUL (wie mw_helpers.py):
* Die Methodenruempfe sind WOERTLICH aus main_window.py verschoben - kein
  Zeichen geaendert. Verhalten ist damit identisch.
* Es gibt hier KEINE `MainWindow.`-Selbstbezuege (vor dem Schnitt per AST
  geprueft: null Treffer). Falls jemand welche ergaenzt: sie muessten
  `BauplanTabs.` heissen, sonst Zirkel-Import.
* `isk`/`NumericItem` kommen aus `mw_basis.py`, NICHT aus main_window -
  genau dafuer wurde mw_basis angelegt.
* Die aa-Suite liest alle Dateien in eve_trader/ui/ zusammengehaengt
  (`_ui_dateien8` in test_bestand_herkunft.py), Text- und AST-Pruefungen
  sehen diese Datei also mit.
"""
from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout,
    QLabel, QPushButton, QSlider, QSpinBox, QStackedWidget, QTableWidget,
    QVBoxLayout, QWidget,
)

from .. import esi, hubs, industry, store
from . import icons, theme
from ..sprache import t
from .mw_basis import (KEIN_DECRYPTOR, ROLLE_KOPIERNAME, NumericItem,
                       dec_anzeige, isk)


class BauplanTabs:
    # REIHENFOLGE DER BAU-STUFEN in der Blaupausen-Warnzeile - dieselbe wie
    # `_stage_order` im Blaupausen-Reiter (main_window). Die Werte sind die
    # SCHLUESSEL, die dort vergeben werden; angezeigt wird uebersetzt.
    # de_scan4: aus - Stufen-SCHLUESSEL, Anzeige via _kategorie_anzeige
    # de_scan2: aus
    _BP_STUFEN_FOLGE = ("Endprodukt", "Komponente", "H\u00fcllen", "Fuel", "Tools",
                        "Reaktion \u00b7 Stufe 1", "Reaktion \u00b7 Stufe 2",
                        "Reaktion")
    # de_scan2: an
    # de_scan4: an

    @classmethod
    def _bp_stufen_liste(cls, by_stage):
        """Aufschluesselung "Stufe Anzahl" fuer die Blaupausen-Warnzeile.

        SITZUNG 17 (Nutzer: "warum sollte man sie nicht korrigieren?"): die
        alte Fassung kannte nur "Endprodukt"/"Komponente"/"Reaktion". Die
        Stufen heissen laengst "Reaktion \u00b7 Stufe 1/2", "H\u00fcllen", "Fuel",
        "Tools" - die fielen STILL heraus. Nachgestellt: 7 fehlende
        Blaupausen, angezeigt wurde "Components 3".

        Unbekannte Stufen werden HINTEN ANGEHAENGT statt weggelassen (Regel 3:
        lieber ein Eintrag zu viel als ein verschwiegener) - kommt je eine neue
        Stufe dazu, steht sie da, auch bevor jemand die Reihenfolge pflegt.
        """
        folge = [s for s in cls._BP_STUFEN_FOLGE if (by_stage or {}).get(s)]
        folge += sorted(s for s in (by_stage or {})
                        if by_stage.get(s) and s not in cls._BP_STUFEN_FOLGE)
        # Doppelpunkt: "Reaktion \u00b7 Stufe 1: 2" - ohne ihn las sich die Stufe
        # und die Anzahl wie eine Zahl ("Stufe 1 2").
        return [f"{cls._kategorie_anzeige(s)}: {by_stage[s]}" for s in folge]

    def _ist_fuel_block(self, tid, groups, reaction_products):
        """Ist dieses Item ein Fuel Block? EINE Wahrheit (Arbeitsregel 9):
        derselbe Klassifizierer wie im Materialien-Baum und im Blueprints-Tab
        (`_category_key` -> "fuel_blocks"), nicht ein zweiter Gruppennamen-
        Vergleich, der davon abdriften kann.

        Gebraucht fuer die eigene Runplaner-Stufe VOR den Reaktionen: Fuel
        Blocks sind FERTIGUNGS-Jobs und landeten deshalb bei den Komponenten -
        also hinter den Reaktionen, die sie verbrauchen (Nutzer, Sitzung 8:
        "Oxygen Fuel Block müsste ich vor Reactions bauen").
        """
        if tid in (reaction_products or set()):
            return False
        try:
            return self._category_key(
                tid, (groups or {}).get(tid, ""), False) == "fuel_blocks"
        except Exception as _err:
            self._log_exception("Runplaner: Fuel-Erkennung", str(_err))
            return False
    def _build_build_tab(self):
        w = QWidget()
        outer = QHBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.b_stack = QStackedWidget()
        outer.addWidget(self._roll_mitte(self.b_stack), 1)

        # Seite „Scanner“ – die Haupt-Arbeitsansicht (Tabelle + Filter)
        scan_page = QWidget()
        # BAUPLAN-MUSTER (Nutzer: "Strategie offen, Feinfilter geschlossen,
        # rechts am Rand wie im Bauplan - dann kann die Itemliste hoeher
        # sein"): links die Liste in voller Hoehe, rechts eine schmale
        # Spalte mit den Einstell-Karten. `root` bleibt der LINKE Strang,
        # damit alle bestehenden root.addWidget-Stellen (Status, Tabelle,
        # Capital-Karte) unveraendert weiterfunktionieren; die Karten
        # wandern unten explizit in `b_side` statt in `root`.
        _sp = QHBoxLayout(scan_page)
        _sp.setContentsMargins(14, 8, 14, 8)
        _sp.setSpacing(10)
        _left = QWidget()
        root = QVBoxLayout(_left)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(7)
        _side_w = QWidget()
        _side_w.setFixedWidth(380)
        self.b_side = QVBoxLayout(_side_w)
        self.b_side.setContentsMargins(0, 0, 0, 0)
        self.b_side.setSpacing(7)
        _sp.addWidget(_left, 1)
        _sp.addWidget(_side_w, 0, Qt.AlignTop)

        # Seite „Setup“ – Profil + Bau-Setup + Blacklist (einmal einstellen)
        setup_page = QWidget()
        sroot = QVBoxLayout(setup_page)
        sroot.setContentsMargins(14, 8, 14, 8)
        sroot.setSpacing(7)

        head = QHBoxLayout()
        # hub + scan live in the top toolbar now; keep objects as synced state only
        self.b_hub = QComboBox()
        for _key, _label, _region_id, _station_id in hubs.NPC_HUBS:
            self.b_hub.addItem(_label, _region_id)
        self.b_hub.currentIndexChanged.connect(self._on_hub_change_build)
        self.b_scan_btn = QPushButton(t("Market scan"))
        self.b_scan_btn.setIcon(icons.icon("satellite"))
        self.b_scan_btn.clicked.connect(self.scan_build)
        self.b_preset = QComboBox()
        self.b_preset.setMinimumWidth(230)
        for label, p in self._BUILD_PRESETS:
            # Symbol aus dem Preset (Sitzung 11) - hier fehlte es ganz.
            _sym = (p or {}).get("sym")
            if _sym:
                try:
                    # Sitzung 17: t() beim Einfuegen (Schluessel englisch)
                    self.b_preset.addItem(icons.icon(_sym), t(label), p)
                    continue
                except Exception:
                    pass
            # Der neutrale Eintrag kommt als SCHLUESSEL aus der
            # Klassen-Konstante - hier uebersetzen, nicht dort.
            self.b_preset.addItem(t(label) if p is None else label, p)
        self.b_preset.currentIndexChanged.connect(self._apply_build_preset)
        self.b_load_btn = QPushButton(t("Load recipes"))   # kept for load_sde refs
        self.b_load_btn.setIcon(icons.icon("blueprint"))
        self.b_load_btn.clicked.connect(self.load_sde)
        # GEZEICHNETES SYMBOL STATT EMOJI (Nutzer-Fund Sitzung 16, "wir machen
        # keine Emojis in dem Tool"). Das Emoji sah je nach Emoji-Schriftart
        # des Betriebssystems anders aus als der Rest; icons.icon() liefert
        # dasselbe Set wie ueberall sonst. Der TEXT bleibt sauber - daran
        # haengen Suche, Screenreader und die Prueftexte.
        self.b_compute_btn = QPushButton(t("Find blueprints"))
        self.b_compute_btn.setIcon(icons.icon("search"))
        self.b_compute_btn.clicked.connect(self.compute_build)
        # Primaer-Stil (cyan): das ist DER Ausloese-Knopf des Tabs.
        self.b_compute_btn.setStyleSheet(
            f"QPushButton{{background:{theme.CYAN_FILL}; color:{theme.CYAN}; "
            f"border:none; border-radius:6px; font-weight:800; "
            f"padding:6px 14px;}}"
            f"QPushButton:hover{{background:{theme.BLUE};}}")

        # ---- STRATEGIE-KARTE: Preset + Blaupausen-Suche, gleiche Optik wie bei
        # Daytrade/Swing (dort: Modus + Preset) ------------------------------
        strat = QFrame(); strat.setObjectName("StrategyCard")
        strat.setStyleSheet(
            f"#StrategyCard {{ background:{theme.PANEL2}; border:1px solid "
            f"{theme.CYAN}; border-radius:10px; }}")
        sg = QGridLayout(strat)
        sg.setContentsMargins(16, 12, 16, 12)
        sg.setHorizontalSpacing(14); sg.setVerticalSpacing(8)
        b_strat_title = QLabel(t("What you want to build"))
        b_strat_title.setStyleSheet(f"color:{theme.CYAN}; font-size:13px; "
                                    f"font-weight:700; letter-spacing:1px;")
        # dito - gezeichnetes Symbol statt Emoji (Sitzung 16).
        self.b_cap_mode = QPushButton(t("Capital mode"))
        self.b_cap_mode.setIcon(icons.icon("satellite"))
        self.b_cap_mode.setCheckable(True)
        self.b_cap_mode.setToolTip(t(
            "Hides the normal result list and fine filters and shows "
              "ONLY the capital ships "
              "(carrier/dreadnought/FAX/titan/supercarrier/freighter) "
              "filling the window – since capitals have no market "
              "price, they need different filters anyway. Right-click "
              "a ship to open its build plan directly."))
        self.b_cap_mode.setStyleSheet(
            f"QPushButton{{background:{theme.PANEL2}; border:1px solid {theme.BORDER}; "
            f"border-radius:6px; color:{theme.MUTED}; font-weight:700; padding:6px 12px;}} "
            f"QPushButton:checked{{background:{theme.CYAN_FILL}; "
            f"color:{theme.CYAN}; "
            f"border-color:{theme.CYAN};}}")
        # BEIM START IMMER AUS (Nutzer, 15.09.2026: "die Gefahr ist gross,
        # dass man vergisst da herauszugehen, bevor man das Tool schliesst,
        # und dann ist man verwirrt, warum man keine normalen Blueprints
        # suchen kann"). Der Zustand wird deshalb BEWUSST NICHT gespeichert -
        # der Capital-Modus ist etwas fuer Fortgeschrittene und soll nie der
        # Zustand sein, in dem man das Programm unbemerkt vorfindet.
        # Ausdruecklich gesetzt statt sich auf den Qt-Standard zu verlassen:
        # so steht die Zusage im Code und kann geprueft werden (b7i).
        self.b_cap_mode.setChecked(False)
        self.b_cap_mode.toggled.connect(self._toggle_capital_mode)
        # SCHMALE SPALTE: Titel allein oben, die beiden Knoepfe als eigene
        # Zeile in voller Breite darunter (Titel + zwei Knoepfe nebeneinander
        # wuerden bei 380 px quetschen). "Blaupausen suchen" bekommt den
        # Stretch - der Primaer-Knopf darf der breiteste sein.
        title_row = QHBoxLayout(); title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title_row.addWidget(b_strat_title, 1)
        sg.addLayout(title_row, 0, 0, 1, 2)
        btn_row = QHBoxLayout(); btn_row.setContentsMargins(0, 0, 0, 0)
        btn_row.setSpacing(8)
        btn_row.addWidget(self.b_compute_btn, 1)
        btn_row.addWidget(self.b_cap_mode)
        sg.addLayout(btn_row, 3, 0, 1, 2)

        # BLAUPAUSEN-TIPPFELD + BAUPLAN-KNOPF ENTFERNT (Nutzer: "kann weg").
        # Beide Wege existieren woanders sauberer: Rechtsklick auf einen
        # Treffer oeffnet den Bauplan direkt, und "Neuer Bauplan" in der
        # rechten Leiste hat die volle Tipp-Suche. Zwei Eingaenge fuer
        # dieselbe Sache waren Redundanz, kein Komfort. Die Karte traegt
        # jetzt nur noch das Preset.
        b_plab = QLabel(t("Preset"))
        b_plab.setStyleSheet(f"color:{theme.TEXT}; font-size:15px; font-weight:600;")
        self.b_preset.setMinimumHeight(34)
        self.b_preset.setStyleSheet("font-size:15px; padding:2px 8px;")
        sg.addWidget(b_plab, 1, 0)
        sg.addWidget(self.b_preset, 2, 0)
        # DAUERTEXT ENTFERNT (Nutzer: "so textfrei und sauber wie der
        # Bauplan") - die Aussage steht als Tooltip am Element selbst.
        self.b_preset.setToolTip(t("Sets the fine filters automatically."))
        sg.setColumnStretch(0, 1)
        b_strat_card = self._collapsible(t("STRATEGY"), strat, accent=theme.CYAN)

        # ---- Profil: gesamtes Bau-Setup speichern / laden -----------------------
        prow = QHBoxLayout()
        pl = QLabel(t("Profile:")); pl.setObjectName("Muted")
        prow.addWidget(pl)
        self.bs_profile = QComboBox(); self.bs_profile.setMinimumWidth(240)
        self.bs_profile.setToolTip(t(
            "Save and load the whole build setup (system, structure, "
              "rigs, ME/TE, decryptor, surplus …) as a profile – so "
              "you do not have to set everything up again."))
        prow.addWidget(self.bs_profile)
        pload = QPushButton(t("Load")); pload.clicked.connect(self._load_bau_profile)
        pload.setIcon(icons.icon("package"))
        prow.addWidget(pload)
        psave = QPushButton(t("Save as \u2026"))
        psave.setIcon(icons.icon("check"))
        psave.clicked.connect(self._save_bau_profile)
        prow.addWidget(psave)
        pdel = QPushButton(t("Delete")); pdel.clicked.connect(self._delete_bau_profile)
        pdel.setIcon(icons.icon("trash"))
        prow.addWidget(pdel)
        prow.addStretch()
        sroot.addLayout(prow)

        # ---- 🏭 Bau-Setup: Struktur + Rigs bestimmen ME/Zeit/Job-Kosten ----------
        setup = QFrame(); setup.setObjectName("Card")
        sg = QGridLayout(setup); sg.setContentsMargins(14, 8, 14, 8)
        sg.setHorizontalSpacing(14); sg.setVerticalSpacing(6)
        stitle = QLabel(t("Manufacturing \u2014 structure & rigs determine material efficiency "
                        "(job cost & build time follow)"))
        stitle.setObjectName("Muted")
        sg.addWidget(stitle, 0, 0, 1, 4)
        self.bs_loc = QComboBox(); self.bs_loc.setMinimumWidth(220)
        self._reload_bau_loc()
        self.bs_sec = QComboBox()
        for lab, v in [("Highsec (×1.0)", 1.0), ("Lowsec (×1.9)", 1.9),
                       ("Null / WH (×2.1)", 2.1)]:
            self.bs_sec.addItem(lab, v)
        self._combo_select(self.bs_sec, float(self.settings.get("bau_security", 1.0)))
        self.bs_ftax = QDoubleSpinBox(); self.bs_ftax.setRange(0, 20)
        self.bs_ftax.setDecimals(2); self.bs_ftax.setSuffix(" %")
        self.bs_ftax.setValue(float(self.settings.get("bau_facility_tax", 0.25)))
        self.bs_ftax.setToolTip(t("Facility tax charged by the structure owner "
                                  "(shown in the structure info). Goes into the job cost."))
        self.bs_bpme = QSpinBox(); self.bs_bpme.setRange(0, 10); self.bs_bpme.setSuffix(" %")
        self.bs_bpme.setValue(int(self.settings.get("bau_me", 10)))
        self.bs_bpme.setToolTip(t("Assumed blueprint material efficiency "
                                  "(fully researched BPO = 10 %)."))
        self.bs_bpte = QSpinBox(); self.bs_bpte.setRange(0, 20); self.bs_bpte.setSuffix(" %")
        self.bs_bpte.setValue(int(self.settings.get("bau_te", 0)))
        self.bs_bpte.setToolTip(t("Blueprint time efficiency (fully researched = 20 %). "
                                  "Reduces build time."))
        self.bs_react = QComboBox()
        self.bs_react.addItem(t("Build reactions yourself"), True)
        self.bs_react.addItem(t("Buy reactions"), False)
        self.bs_react.setCurrentIndex(0 if self.settings.get("bau_reactions", True) else 1)
        self.bs_inv = QComboBox()
        self.bs_inv.addItem(t("Include invention"), True)
        self.bs_inv.addItem(t("Ignore invention"), False)
        self.bs_inv.setCurrentIndex(0 if self.settings.get("bau_invention", False) else 1)
        self.bs_decry = QComboBox()
        for nm, _v in self._decryptor_list():
            # ANZEIGE uebersetzt, DATEN nicht: `_combo_select` waehlt ueber
            # itemData, und genau dieser Wert wandert in die Einstellungen.
            self.bs_decry.addItem(dec_anzeige(nm), nm)
        self._combo_select(self.bs_decry, self.settings.get("bau_decryptor", KEIN_DECRYPTOR))
        self.bs_decry.setToolTip(t(
            "Decryptor for invention (changes success chance and "
              "runs → invention cost per unit)."))
        from PySide6.QtWidgets import QCompleter
        self.bs_syspick = QComboBox(); self.bs_syspick.setEditable(True)
        self.bs_syspick.setMinimumWidth(150)
        self.bs_syspick.setInsertPolicy(QComboBox.NoInsert)
        self.bs_syspick.completer().setCompletionMode(QCompleter.PopupCompletion)
        self.bs_syspick.completer().setFilterMode(Qt.MatchContains)
        self.bs_syspick.completer().setCaseSensitivity(Qt.CaseInsensitive)
        # BEISPIEL IM TOOLTIP NEUTRAL HALTEN: hier stand "A-DDGY", das
        # Heimatsystem des Entwicklers. In einer oeffentlichen Fassung ist
        # das erstens verwirrend (kein Fremder kennt es) und zweitens eine
        # unnoetige Angabe ueber den, der das Werkzeug gebaut hat. Jita
        # kennt jeder und erklaert dieselbe Sache.
        self.bs_syspick.setToolTip(t("Search for the build system (e.g. type \u201eJita\u201c). "
                                     "Sets the cost index (live from ESI) and the security "
                                     "automatically."))
        for c, (lab, wdg) in enumerate([("System", self.bs_syspick),
                                        (t("Build location (structure)"), self.bs_loc),
                                        (t("Security"), self.bs_sec)]):
            l = QLabel(lab); l.setObjectName("Muted")
            sg.addWidget(l, 1, c); sg.addWidget(wdg, 2, c)
        for c, (lab, wdg) in enumerate([(t("Facility tax"), self.bs_ftax),
                                        (t("Blueprint ME"), self.bs_bpme),
                                        (t("Blueprint TE"), self.bs_bpte),
                                        (t("Reactions"), self.bs_react),
                                        (t("Invention"), self.bs_inv)]):
            l = QLabel(lab); l.setObjectName("Muted")
            sg.addWidget(l, 3, c); sg.addWidget(wdg, 4, c)
        ldc = QLabel(t("Decryptor")); ldc.setObjectName("Muted")
        sg.addWidget(ldc, 5, 0); sg.addWidget(self.bs_decry, 6, 0)
        self.bs_eff = QLabel("")
        self.bs_eff.setStyleSheet(f"color:{theme.AMBER}; font-weight:700; font-size:13px;")
        sg.addWidget(self.bs_eff, 7, 0, 1, 5)
        self.bs_sys = QLabel("")
        self.bs_sys.setObjectName("Muted"); self.bs_sys.setWordWrap(True)
        sg.addWidget(self.bs_sys, 8, 0, 1, 5)
        self.bs_loc.currentIndexChanged.connect(self._on_bau_loc_change)
        self.bs_syspick.activated.connect(self._on_bau_syspick)
        self.bs_syspick.lineEdit().editingFinished.connect(self._on_bau_syspick)
        self.bs_bpme.valueChanged.connect(self._save_bau_setup)
        self.bs_bpte.valueChanged.connect(self._save_bau_setup)
        self.bs_ftax.valueChanged.connect(self._save_bau_setup)
        for wdg in (self.bs_sec, self.bs_react,
                    self.bs_inv, self.bs_decry):
            wdg.currentIndexChanged.connect(self._save_bau_setup)
        self._update_bau_eff()
        self._update_bau_sys()
        # BAU-SETUP wird NICHT mehr angezeigt: System/Sicherheit/Facility-Tax kommen aus
        # der Struktur, ME/TE stellst du im Bauplan, Reaktionen/Invention sind Standard,
        # Decryptor-Wahl steckt im Invention-Tab des Bauplan-Dialogs. Das setup-Widget
        # wird nur noch für gespeicherte Werte + Profile gebaut (Referenz halten, damit
        # bs_* nicht vom Garbage Collector gelöscht werden – NICHT ins Layout gehängt).
        self._bau_setup_hidden = setup
        setup.hide()
        self._reload_bau_profiles()

        ctl = QFrame(); ctl.setObjectName("Card")
        g = QGridLayout(ctl); g.setContentsMargins(14, 6, 14, 6)
        g.setHorizontalSpacing(16); g.setVerticalSpacing(2)
        self.b_cat = QComboBox(); self.b_cat.setMinimumWidth(170)
        self.b_cat.addItem(t("All categories"), None)
        self.b_tech = QComboBox(); self.b_tech.setMinimumWidth(130)
        # WICHTIG: als String-Key speichern, NICHT als Python-Set - QComboBox.
        # findData() (in _apply_build_preset für die Presets gebraucht) vergleicht
        # über QVariant und matcht Sets zuverlässig NIE (immer -1) - das ließ
        # JEDES Preset mit Tech-Filter beim Setzen lautlos auf "Alle baubaren"
        # zurückfallen, ohne Fehlermeldung. String-Keys vergleichen korrekt.
        # "t1" deckt hier auch meta_level 0 ab (in der SDE oft unget) T1-Items).
        for label, key in [(t("All buildable (T1\u2013T3)"), "all"), ("Tech I", "t1"),
                           ("Tech II", "t2"), ("Tech III", "t3")]:
            self.b_tech.addItem(label, key)
        self.b_window = QComboBox()
        for label, days in [(t("{n} days").format(n=_d), _d)
                            for _d in (5, 14, 30, 90, 180)]:
            self.b_window.addItem(label, days)
        self.b_window.setCurrentIndex(2)
        self.b_margin = QDoubleSpinBox(); self.b_margin.setRange(0, 100000)
        self.b_margin.setValue(10); self.b_margin.setSuffix(" %")
        self.b_vol = QSpinBox(); self.b_vol.setRange(0, 10_000_000); self.b_vol.setValue(20)
        self.b_pmin = QSpinBox(); self.b_pmin.setRange(0, 2_000_000_000)
        self.b_pmin.setGroupSeparatorShown(True)
        self.b_pmax = QSpinBox(); self.b_pmax.setRange(0, 2_000_000_000)
        self.b_pmax.setGroupSeparatorShown(True)
        self.b_race = QComboBox(); self.b_race.setMinimumWidth(130)
        self.b_race.addItem(t("All races"), None)
        for rid, rname in sorted(industry.RACE_NAMES.items(), key=lambda x: x[1]):
            self.b_race.addItem(rname, rid)

        self.b_cat.setToolTip(t("Only items of this category (ships, modules, ammo \u2026). "
                                "Needs the SDE \u2013 \u201eLoad recipes\u201c."))
        self.b_tech.setToolTip(t(
            "Tech level. LP/faction items are excluded on principle "
              "because their BPC cost (LP + ISK) cannot be calculated "
              "reliably."))
        self.b_margin.setToolTip(t("Minimum build margin: (sale \u2212 build cost) / "
                                   "build cost. 10 %+ counts as usable, below that it "
                                   "hardly pays."))
        self.b_vol.setToolTip(t("Minimum daily volume \u2013 so you can actually sell what you build."))
        self.b_pmin.setToolTip(t("Only items from this sale price upwards."))
        self.b_pmax.setToolTip(t("Only items up to this sale price (0 = \u221e)."))
        self.b_race.setToolTip(t("Only items of this race (mainly relevant for ships - "
                                 "modules/ammo usually have no race assigned in the SDE "
                                 "and stay visible whatever you choose)."))

        bcontrols = [
            (t("Category"), self.b_cat), ("Tech", self.b_tech),
            (t("Race/faction"), self.b_race),
            (t("Time window"), self.b_window), (t("Min build margin %"), self.b_margin),
            (t("Min \u00d8 daily volume"), self.b_vol),
            (t("Price from"), self.b_pmin), (t("Price to (0=∞)"), self.b_pmax),
        ]
        for i, (label, wdg) in enumerate(bcontrols):
            wdg.setMaximumWidth(190); wdg.setMinimumWidth(90)
            lab = QLabel(label); lab.setObjectName("Muted")
            r = (i // 5) * 2
            g.addWidget(lab, r, i % 5)
            g.addWidget(wdg, r + 1, i % 5)
            self._install_tip(wdg, lab)
            if hasattr(wdg, "valueChanged"):
                wdg.valueChanged.connect(self._build_preset_to_custom)
            elif hasattr(wdg, "currentIndexChanged"):
                wdg.currentIndexChanged.connect(self._build_preset_to_custom)
        g.setColumnStretch(5, 1)
        # Zeigt an, wenn das Reaktions-Preset aktiv ist, damit der Schalter
        # nicht unsichtbar im Hintergrund wirkt. (only_cap gibt es nicht
        # mehr - Capital-Module laufen regulaer unter T1/T2 mit.)
        self.b_only_cap_lbl = QLabel("")
        self.b_only_cap_lbl.setStyleSheet(f"color:{theme.CYAN}; font-size:11px;")
        g.addWidget(self.b_only_cap_lbl, 4, 0, 1, 4)
        self.b_refine_btn = QPushButton(" " + t("Optimal quantity"))
        self.b_refine_btn.setIcon(icons.icon("trend_up"))
        self.b_refine_btn.setToolTip(t(
            "Recomputes the exact build-plan maths for EVERY result "
              "below (batch size and rounding effects, real job costs) "
              "instead of the quick per-unit estimate – quantity = Ø "
              "daily volume (a realistic build and sell size). Takes a "
              "few seconds to a minute depending on the number of "
              "hits. Results are kept for this session only (RAM, no "
              "file) – no data litter on the disk."))
        self.b_refine_btn.clicked.connect(self._refine_all_optimal_qty)
        g.addWidget(self.b_refine_btn, 4, 4, 1, 2)
        # ZUGEKLAPPT starten (Nutzer: "keine ueberladenen Layouts, ich will
        # nur 3-4 Knoepfe"). Die Feinfilter setzt normalerweise das
        # Preset - wer sie braucht, klappt sie auf. Nichts entfernt,
        # nur weggeraeumt; dasselbe Muster wie im Materialien-Tab des
        # Bauplans, unserem Vorbild.
        self.b_filter_card = self._collapsible(t("FINE FILTERS"), ctl,
                                               expanded=False)
        b_filter_card = self.b_filter_card
        # STRATEGIE (offen) + FEINFILTER (zu) rechts uebereinander -
        # gleiche Anmutung wie die "Bauen oder kaufen?"-Spalte im Bauplan.
        self.b_side.addWidget(b_strat_card)
        self.b_side.addWidget(b_filter_card)
        self.b_side.addStretch(1)

        self.build_status = QLabel(t("\u201eLoad recipes\u201c, then \u201eFind blueprints\u201c "
                                     "(after a hub scan in the Daytrade or Swing tab)."))
        self.build_status.setObjectName("Muted")
        self.build_status.setWordWrap(True)
        root.addWidget(self.build_status)

        # VIER SPALTEN STATT ELF (Nutzer: "nur die zwei Zahlen, die
        # entscheiden"). Item, Bau-Marge, Gewinn/Stk und ein Bewertungs-
        # Balken wie im Materialien-Tab des Bauplans. Alle uebrigen
        # Kennzahlen (Baukosten, Sell, Gewinn/m3, Tagesvolumen,
        # Volatilitaet, Bestandstage, Gewinn/Tag, ISK/Std) stehen im
        # Zeilen-Tooltip - nichts ist verloren, nur nicht mehr im Weg.
        self.b_table = QTableWidget(0, 4)
        self.b_table.setHorizontalHeaderLabels(
            [t("Item"), t("Build margin"), t("Profit/unit"), t("Rating")])
        self._make_columns_friendly(self.b_table)
        # WENIGER DATENBLATT (Nutzer: "weniger wie ne Excel-Tabelle"): das
        # Zellen-GITTER ist der staerkste Excel-Ausloeser - weg damit; die
        # Zeilen trennt weiterhin die Selektion/Hover-Farbe. Dazu etwas
        # Luft pro Zeile, damit Icons und Bewertungs-Balken atmen.
        self.b_table.setShowGrid(False)
        # KARTEN-GEFUEHL STATT DATENZEILE (Nutzer-Liste "weniger Excel",
        # Punkt 1): grosses Icon als visueller Anker links, kraeftiger
        # Item-Name, mehr Luft je Zeile. Werte aus der Nutzer-Liste
        # (32 px Icon, ~38 px Zeile) - nicht neu erfinden.
        self.b_table.setIconSize(QSize(32, 32))
        self.b_table.verticalHeader().setDefaultSectionSize(38)
        self.b_table.setSortingEnabled(True)
        self.b_table.verticalHeader().setVisible(False)
        self.b_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.b_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.b_table.cellDoubleClicked.connect(self._build_to_chart)
        self.b_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_table.customContextMenuRequested.connect(self._build_menu)
        root.addWidget(self.b_table, 1)

        # ---- Capital-Schiffe: eigene, klar getrennte Sektion ------------------
        # Carrier/Dread/FAX/Titan/Supercarrier/Freighter haben in Jita fast nie
        # echte Marktorders (Handel läuft über Contracts, oft Allianz-intern) -
        # deshalb NICHT in die normale, nach Marge/ISK-Std sortierte b_table
        # mischen (dort bräuchte jede Zeile einen echten Verkaufspreis, sonst
        # verzerrt eine erfundene "0 ISK Gewinn"-Zeile das Ranking). Stattdessen
        # eine eigene Tabelle, NUR Baukosten (aus SDE-Materialbedarf + Jita-
        # Materialpreisen), klar als "kein Marktpreis" gekennzeichnet.
        cap_inner = QWidget()
        self.b_cap_inner = cap_inner
        cap_v = QVBoxLayout(cap_inner); cap_v.setContentsMargins(0, 4, 0, 0)
        cap_head = QHBoxLayout()
        cap_info = QLabel(t(
            "These ships are practically never traded in Jita via normal market "
            "orders, but via contracts (often alliance-internal, null/lowsec). "
            "\u201eLoad contract prices\u201c looks up public contracts as a reference - "
            "\u00d8 daily volume/volatility do not exist for them (no price history "
            "for contracts in ESI), so you get \u201eActive contracts\u201c/\u201ePrice "
            "range\u201c instead."))
        cap_info.setObjectName("Muted"); cap_info.setWordWrap(True)
        cap_head.addWidget(cap_info, 1)
        cap_srch_lbl = QLabel()
        cap_srch_lbl.setPixmap(icons.pixmap("search", groesse=16))
        cap_head.addWidget(cap_srch_lbl)
        from PySide6.QtWidgets import QCompleter as _QCompleter2
        self.b_cap_search = QComboBox(); self.b_cap_search.setEditable(True)
        self.b_cap_search.setMinimumWidth(180)
        self.b_cap_search.setInsertPolicy(QComboBox.NoInsert)
        self.b_cap_search.lineEdit().setPlaceholderText(t("Ship name \u2026"))
        self.b_cap_search.completer().setCompletionMode(_QCompleter2.PopupCompletion)
        self.b_cap_search.completer().setFilterMode(Qt.MatchContains)
        self.b_cap_search.completer().setCaseSensitivity(Qt.CaseInsensitive)
        self.b_cap_search.editTextChanged.connect(self._apply_cap_filter)
        cap_head.addWidget(self.b_cap_search)
        # dito - gezeichnetes Symbol statt Emoji (Sitzung 16). Dieser Knopf
        # sitzt in derselben Capital-Karte wie b_cap_mode; ein Emoji auf dem
        # einen und ein Symbol auf dem anderen haetten nebeneinander gestanden.
        self.b_cap_btn = QPushButton(t("Estimate capital build cost"))
        self.b_cap_btn.setIcon(icons.icon("satellite"))
        self.b_cap_btn.clicked.connect(self._compute_capital_costs)
        cap_head.addWidget(self.b_cap_btn)
        self.b_cap_contract_btn = QPushButton(
            t("Load contract prices (all of New Eden)"))
        self.b_cap_contract_btn.setIcon(icons.icon("globe"))
        self.b_cap_contract_btn.setToolTip(t(
            "Searches public contracts in ALL regions for capital "
              "sales and derives a reference value per ship type. "
              "Capitals are sold everywhere, not only in the hub – a "
              "scan over a single region yields no price at all for "
              "many types, or just one.\nTAKES LONGER (all of New Eden "
              "instead of one region, several minutes depending on "
              "time of day) – runs in the background, you can keep "
              "working.\nThe MEDIAN is shown (the middle price): "
              "contract prices regularly have outliers on the high "
              "side that would skew an average. The average is in the "
              "tooltip of the cell next to it.\nPublic offers only – "
              "ESI sees alliance-internal contracts only through a "
              "character with the director or accountant role in that "
              "corp, which this scan does not cover."))
        self.b_cap_contract_btn.clicked.connect(self._load_capital_contract_prices)
        cap_head.addWidget(self.b_cap_contract_btn)
        cap_v.addLayout(cap_head)
        self.b_cap_status = QLabel("")
        self.b_cap_status.setObjectName("Muted"); self.b_cap_status.setWordWrap(True)
        cap_v.addWidget(self.b_cap_status)
        # 4-SPALTEN-SCHEMA wie die Hauptliste (Nutzer-Liste "weniger
        # Excel", Punkt 3 - vorher 11 Spalten). Der Rest steht im
        # Zeilen-Tooltip; Bewertung kommt aus derselben _bau_bewertung.
        self.b_cap_table = QTableWidget(0, 4)
        self.b_cap_table.setHorizontalHeaderLabels(
            [t("Ship"), t("Build cost"), t("Contract reference"), t("Rating")])
        self._make_columns_friendly(self.b_cap_table)
        self.b_cap_table.setShowGrid(False)   # gleiche Optik wie die Liste oben
        self.b_cap_table.setIconSize(QSize(32, 32))
        self.b_cap_table.verticalHeader().setDefaultSectionSize(38)
        self.b_cap_table.setSortingEnabled(True)
        self.b_cap_table.verticalHeader().setVisible(False)
        self.b_cap_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.b_cap_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.b_cap_table.setMinimumHeight(320)
        self.b_cap_table.setMaximumHeight(560)
        self.b_cap_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.b_cap_table.customContextMenuRequested.connect(self._build_menu_cap)
        cap_v.addWidget(self.b_cap_table)
        self.b_cap_wrap = self._collapsible(
            t("CAPITAL SHIPS (BUILD COST, NO MARKET PRICE)"), cap_inner,
            expanded=False, header_attr="b_cap_header",
            tip=t("Carrier/Dreadnought/FAX/Titan/Supercarrier/Freighter - trading "
                  "runs via contracts instead of market orders, hence separate from "
                  "the normal profit table above. Does NOT run automatically with the "
                  "normal search - only when expanded or in Capital mode."))
        root.addWidget(self.b_cap_wrap)
        # Erst beim tatsächlichen Aufklappen berechnen (nicht bei jeder normalen
        # "Blaupausen suchen"-Suche mitlaufen lassen - das gehörte hier vorher
        # nicht her und ist jetzt sauber getrennt vom Capital-Modus).
        self.b_cap_header.toggled.connect(self._on_cap_header_toggled)
        # AUSSERHALB des Capital-Modus KOMPLETT unsichtbar (Nutzer: "das
        # gehoert nicht dahin"). Capitals haben ihren eigenen Modus - der
        # Umschalter sitzt oben in der Strategie-Karte; eine zweite,
        # dauerhaft sichtbare Capital-Sektion unter der normalen Liste war
        # Redundanz und Platzfresser. _toggle_capital_mode blendet die
        # Karte beim Einschalten ein.
        self.b_cap_wrap.setVisible(False)

        # Seite „Aktuelle Baupläne“ (gespeicherte Baupläne zum Abarbeiten)
        plans_page = QWidget()
        self._plans_layout = QVBoxLayout(plans_page)
        self._plans_layout.setContentsMargins(14, 8, 14, 8); self._plans_layout.setSpacing(7)
        # Struktur-Fitting-Seite enthält jetzt auch das frühere „Setup“ (Profile + Basiswerte)
        from PySide6.QtWidgets import QScrollArea
        _combined = QWidget()
        _cv = QVBoxLayout(_combined); _cv.setContentsMargins(0, 0, 0, 0); _cv.setSpacing(6)
        _cv.addWidget(setup_page)                        # Profile + BAU-SETUP (oben)
        _cv.addWidget(self._build_structures_page(), 1)  # Strukturen (darunter)
        _struct_scroll = QScrollArea(); _struct_scroll.setWidgetResizable(True)
        _struct_scroll.setFrameShape(QScrollArea.NoFrame); _struct_scroll.setWidget(_combined)
        # Seite „Meine Blueprints“ (ESI-getrackt: welche BPs besitze ich, was ist
        # baubar/profitabel). Wird per Button aktualisiert (ESI-Abruf pro Char).
        bp_page = QWidget()
        self._bp_page_layout = QVBoxLayout(bp_page)
        self._bp_page_layout.setContentsMargins(14, 8, 14, 8)
        self._bp_page_layout.setSpacing(7)
        self._build_my_blueprints_page()
        from PySide6.QtWidgets import QScrollArea
        _combined = QWidget()
        _cv = QVBoxLayout(_combined); _cv.setContentsMargins(0, 0, 0, 0); _cv.setSpacing(6)
        _cv.addWidget(setup_page)                        # Profile + BAU-SETUP (oben)
        _cv.addWidget(self._build_structures_page(), 1)  # Strukturen (darunter)
        _struct_scroll = QScrollArea(); _struct_scroll.setWidgetResizable(True)
        _struct_scroll.setFrameShape(QScrollArea.NoFrame); _struct_scroll.setWidget(_combined)
        # BAU-KALENDER VOLLSTAENDIG ENTFERNT (Nutzer: "wir werden nie einen
        # Kalender einbauen") - Seite, Knopf UND Code (Sitzung 7: 1977 Zeilen,
        # 18 Methoden). Seiten-Indizes sind nachgezogen, "Strukturen" ist 3.
        # VORSICHT bei kuenftigem Aufraeumen: `_cal_fit_top_fns` ist trotz
        # des Namens KEIN Kalender-Code, sondern ein allgemeiner Layout-Helfer.
        self.b_stack.addWidget(scan_page)       # 0 – Scanner
        # MEINE BLUEPRINTS IN EINEN EIGENEN ROLLBEREICH (Nutzer, Sitzung 20:
        # "ich muss immernoch nach rechts scrollen wenn ich die profits sehen
        # will").
        # GEMESSEN: ein QStackedWidget nimmt die MINDESTBREITE der BREITESTEN
        # Seite fuer ALLE. Die Seiten waren
        #   0 Scanner 488 · 1 Meine Blueprints 1861 · 2 Bauplaene 391 ·
        #   3 Strukturen 68
        # Die 16-spaltige Blueprints-Tabelle zwang also auch "Meine
        # Bauplaene" auf 1861 px - daher die waagerechte Bildlaufleiste,
        # obwohl auf dieser Seite viel Luft ist.
        # Ein eigener Rollbereich kappt das, GENAU WIE bei Seite 3 weiter
        # oben: die breite Seite rollt fuer sich, die anderen nicht mehr mit.
        _bp_scroll = QScrollArea(); _bp_scroll.setWidgetResizable(True)
        _bp_scroll.setFrameShape(QScrollArea.NoFrame)
        _bp_scroll.setWidget(bp_page)
        self.b_stack.addWidget(_bp_scroll)      # 1 – Meine Blueprints
        self.b_stack.addWidget(plans_page)      # 2 – Aktuelle Baupläne
        self.b_stack.addWidget(_struct_scroll)  # 3 – Struktur-Fitting (+ Setup)
        self._reload_saved_plans()
        outer.addWidget(self._build_bau_rail())

        self.tabs.addTab(w, t("Build"))
        from PySide6.QtCore import QTimer
        if industry.sde_ready():
            QTimer.singleShot(0, self._reload_build_picker)
        QTimer.singleShot(0, self._reload_system_picker)   # Systemnamen für die Suche

    def _fill_invention_tab(self, plan, recipes, names, cards_layout, top_type_id=None,
                            own_bpc_widgets=None):
        """Baut die Invention-Tab-Karten neu: ein Panel pro Item, das über
        Invention entsteht. Datacores sind fix (aus dem Blueprint-Rezept),
        der Decryptor ist wählbar - Erfolgschance/Runs/ME/TE aktualisieren sich
        live (industry.invention_outcome), und der Gesamtbedarf (Versuche/
        Datacores/Kosten) für die aktuelle Bauplan-Menge wird direkt gezeigt.
        Ein Decryptor-Wechsel schreibt in self._bd_opts['inv_decryptor_map']
        und löst self._bd_full_rebuild() aus, damit auch die Kopfzeile
        (Invention-Kosten, Gewinn) sofort den neuen Wert zeigt."""

        def _kv_rows(rows):
            """Kompakte Zwei-Spalten-Liste: Beschriftung links (gedaempft),
            Wert rechts. Ersetzt die frueheren Fliesstext-Zeilen, die mit
            Mittelpunkten getrennt ueber die volle Breite liefen und sich
            schlecht ueberfliegen liessen (Nutzer)."""
            _out = ["<table cellspacing='0' cellpadding='0' "
                    "style='font-size:11px;'>"]
            for _lbl, _val, _col in rows:
                _st = f"color:{_col};font-weight:700;" if _col else ""
                _out.append(
                    f"<tr><td style='color:{theme.MUTED}; "
                    f"padding:0 10px 1px 0;'>{_lbl}</td>"
                    f"<td style='{_st}'>{_val}</td></tr>")
            _out.append("</table>")
            return "".join(_out)

        # KOMPLETT LEEREN und danach genau EINEN Stretch ans Ende. Die alte
        # Schleife liess das LETZTE Element stehen - solange das der Stretch
        # war, ging das gut. Seit Struktur/Skills in der Seitenleiste sitzen,
        # standen die Karten aber HINTER dem Stretch (s. insert_at unten), und
        # das letzte Element war die Gesamtzeile: die blieb stehen und bekam
        # bei jedem Rebuild eine zweite dazu ("Invention gesamt" doppelt,
        # Nutzer-Screenshot) - plus eine riesige Luecke, weil der Stretch
        # oberhalb der Karten sass.
        # ZWEITE ABSICHERUNG GEGEN DEN TE-ABSTURZ: me/te/Eigene-BPC sind
        # DIESELBEN Widget-Objekte ueber alle Rebuilds hinweg (sie werden unten
        # nur neu einsortiert). Solange sie noch Kinder einer Karte sind,
        # nimmt deleteLater() der Karte sie MIT ins Grab - danach zeigt der
        # Dialog auf ein totes C++-Objekt und der naechste Klick beendet die
        # App. Bisher ging das nur gut, weil sie weiter unten rechtzeitig neu
        # eingehaengt wurden; jeder Pfad, der das nicht tut (Ausnahme mitten im
        # Aufbau, Endprodukt ohne Karte), war ein Absturz. Deshalb VORHER
        # ausklinken - `setParent(None)` loest sie aus der Karte, ohne sie zu
        # zerstoeren.
        if own_bpc_widgets is not None:
            for _shared in own_bpc_widgets:
                if _shared is not None:
                    _shared.setParent(None)
        while cards_layout.count():
            it = cards_layout.takeAt(0)
            w = it.widget()
            if w:
                w.deleteLater()
        cards_layout.addStretch()
        # SEITENLEISTE EBENFALLS LEEREN. Diese Funktion laeuft bei JEDEM
        # Rebuild - ohne das stapeln sich Struktur-Zeile und Skill-Auswahl
        # bei jeder Mengenaenderung erneut untereinander.
        _side_clear = getattr(self, "_bd_inv_side_v", None)
        if _side_clear is not None:
            while _side_clear.count():
                _it = _side_clear.takeAt(0)
                _w = _it.widget()
                if _w:
                    _w.deleteLater()
        if not plan:
            return
        items = []
        for tid, runs in (plan.get("build_runs") or {}).items():
            if runs < 1:
                continue
            bp = recipes.product_to_bp.get(tid)
            if not bp:
                continue
            bp_id, activity, _oq = bp
            if activity != industry.MANUFACTURING:
                continue
            inv = recipes.invention_for_bpc.get(bp_id)
            if not inv:
                continue
            items.append((tid, bp_id, runs, inv))

        def _own_bpc_fallback_card():
            """Kleine eigenständige Karte NUR für ME/TE/Eigene-BPC, falls das
            Endprodukt selbst keine Invention braucht (reines T1/BPO) - sonst
            wären diese Felder nirgends mehr zu finden."""
            if own_bpc_widgets is None:
                return
            _me_sp, _te_sp, _obc_cb, _obc_runs_lbl, _obc_runs_sp = own_bpc_widgets
            fb_card = QFrame(); fb_card.setObjectName("Card")
            fb_v = QVBoxLayout(fb_card)
            fb_v.setContentsMargins(14, 10, 14, 10); fb_v.setSpacing(6)
            fb_title = QLabel(t("\u2699 End product ME/TE ({name})").format(name=names.get(top_type_id, "")))
            fb_title.setStyleSheet(f"color:{theme.CYAN}; font-weight:700;")
            fb_v.addWidget(fb_title)
            fb_info = QLabel(t("This item needs no invention (T1/BPO) - ME/TE still "
                               "apply, e.g. if your own blueprint is already researched."))
            fb_info.setObjectName("Muted"); fb_info.setWordWrap(True)
            fb_v.addWidget(fb_info)
            fb_row1 = QHBoxLayout(); fb_row1.setSpacing(6)
            _me_cap = QLabel(t("ME:")); _me_cap.setStyleSheet("font-size:11px;")
            fb_row1.addWidget(_me_cap); fb_row1.addWidget(_me_sp)
            _te_cap = QLabel(t("TE:")); _te_cap.setStyleSheet("font-size:11px;")
            fb_row1.addWidget(_te_cap); fb_row1.addWidget(_te_sp)
            fb_row1.addStretch()
            fb_v.addLayout(fb_row1)
            fb_row2 = QHBoxLayout(); fb_row2.setSpacing(6)
            fb_row2.addWidget(_obc_cb); fb_row2.addWidget(_obc_runs_lbl)
            fb_row2.addWidget(_obc_runs_sp); fb_row2.addStretch()
            fb_v.addLayout(fb_row2)
            cards_layout.insertWidget(0, fb_card)
        if not items:
            empty = QLabel(t("No item in this build plan needs invention (either "
                             "everything is T1/BPO, or invention is switched off in the "
                             "build settings)."))
            empty.setObjectName("Muted"); empty.setWordWrap(True)
            cards_layout.insertWidget(cards_layout.count() - 1, empty)
            _own_bpc_fallback_card()
            return
        need_names = set()
        for _tid, _bp_id, _runs, inv in items:
            t1_bp, _br, _pr, datacores = inv
            need_names.add(t1_bp)
            for d, _q in datacores:
                need_names.add(d)
        # Decryptor-Namen gleich mit auflösen - die Gesamt-Zeilen (je Karte +
        # Gesamt-Karte) nennen sie namentlich statt "#34201". WICHTIG: über
        # die METHODE self._decryptor_list(), nicht die lokale Variable
        # decryptor_list - die wird erst WEITER UNTEN in dieser Funktion
        # definiert (UnboundLocalError beim Öffnen des Bauplans, Nutzer-
        # Traceback 28.07.).
        try:
            for _nm, _dv in self._decryptor_list():
                if _dv and _dv[4]:
                    need_names.add(_dv[4])
        except Exception:
            pass
        try:
            extra_names = esi.resolve_names(list(need_names))
        except Exception:
            extra_names = {}
        # Struktur für Invention (zugewiesen oder Auto-Wahl) - Warnung, wenn
        # noch gar keine Struktur angelegt ist.
        has_structs = bool(self.settings.get("bau_structures"))
        inv_struct = self._struct_for_activity("invention") if has_structs else None
        assigned_map = self.settings.get("bau_activity_struct", {}) or {}
        struct_lbl = QLabel()
        if not has_structs:
            struct_lbl.setText(t("\u26a0 No structure set up - please add an "
                                 "invention-capable structure in the Structures tab."))
            struct_lbl.setStyleSheet(f"color:{theme.AMBER}; font-weight:700;")
        elif inv_struct:
            # "Auto" heisst in beiden Sprachen gleich und bleibt.
            tag = t("assigned") if assigned_map.get("invention") else "Auto"
            struct_lbl.setText(t("Structure: ") + f"<b>{inv_struct.get('name','?')}</b> "
                               f"({tag})")
            struct_lbl.setStyleSheet(f"color:{theme.MUTED};")
        else:
            struct_lbl.setText(t("\u26a0 Please choose a structure for invention in the "
                                 "Structures tab."))
            struct_lbl.setStyleSheet(f"color:{theme.AMBER}; font-weight:700;")
        # IN DIE SEITENLEISTE (Nutzer). Faellt sie mal weg, landet alles wie
        # frueher oben in der Kartenspalte - kein harter Bruch.
        _side_v = getattr(self, "_bd_inv_side_v", None)
        if _side_v is not None:
            struct_lbl.setWordWrap(True)
            _side_v.addWidget(struct_lbl)
        else:
            cards_layout.insertWidget(0, struct_lbl)

        # Charakter-Wahl für den Skill-Modifier (Encryption+Datacore-Skills):
        # Standard "Bester automatisch" (wie bisher), oder gezielt EINEN der
        # "Für Invention"-markierten Charaktere fixieren - rein für die
        # Erfolgschance-Berechnung, KEINE Job-/Slot-Zuteilung. Auffälliger
        # gestaltet (auf Nutzerwunsch), da das direkt beeinflusst, was als
        # Erfolgschance angezeigt wird.
        # Kein eigener blauer Karten-Stil mehr: in der Seitenleiste sitzt das
        # in der amber Klapp-Karte wie ueberall sonst. Senkrecht statt
        # waagerecht, weil 380px fuer Label + Dropdown + Knopf nebeneinander
        # nicht reichen.
        char_row = QFrame()
        char_row_l = QVBoxLayout(char_row)
        char_row_l.setContentsMargins(0, 0, 0, 0); char_row_l.setSpacing(4)
        # SICHERHEIT DER PLANUNG - einstellbar (Nutzer), Vorgabe 75 %.
        # Sie aendert NICHT die Erfolgschance je Versuch, sondern nur, fuer
        # wieviel Pech Material eingekauft wird: 12 Cerberus bei 33,8 % sind
        # 41 Versuche bei 75 %, aber 47 bei 90 %. Je kleiner die Serie, desto
        # teurer wird jedes Prozent - bei 1 Erfolg sind es 4 gegen 6 Versuche.
        _conf_lbl = QLabel(t("Planned certainty:"))
        _conf_lbl.setObjectName("Muted"); _conf_lbl.setStyleSheet("font-size:11px;")
        char_row_l.addWidget(_conf_lbl)
        _conf_sp = QSpinBox()
        _conf_sp.setRange(50, 99)
        _conf_sp.setSuffix(" %")
        _conf_sp.setValue(int(round(self._bd_inv_confidence() * 100)))
        _conf_sp.setToolTip(t(
            "How likely the planned attempts are really enough.\n"
            "Higher = more attempts, more datacores, more certain to finish - but "
            "more expensive.\nThis does NOT change the success chance per attempt.\n"
            "Also affects \u201eBest choice for profit\u201c: at high certainty, "
            "decryptors with a better success chance pay off sooner.\n"
            "Applies to this build plan only; a new one starts again at {pct} %."
        ).format(pct=int(industry.DEFAULT_INVENTION_CONFIDENCE * 100)))

        def _conf_changed(_v):
            self._bd_inv_conf = float(_v) / 100.0
            _cb = getattr(self, "_bd_full_rebuild", None)
            if _cb:
                QTimer.singleShot(0, _cb)   # entprellt wie die anderen Felder
        _conf_sp.valueChanged.connect(_conf_changed)
        char_row_l.addWidget(_conf_sp)

        char_row_lbl = QLabel(t("Skills for success chance of:"))
        char_row_lbl.setObjectName("Muted")
        char_row_lbl.setStyleSheet("font-size:11px;")
        char_row_l.addWidget(char_row_lbl)
        inv_char_combo = QComboBox()
        inv_char_combo.addItem(t("\u2014 Best automatically \u2014"), 0)
        _char_names_map = {c["character_id"]: (c.get("character_name") or c.get("name")
                                                or str(c["character_id"]))
                           for c in store.list_characters()}
        for cid in (self.settings.get("bau_invention_chars", []) or []):
            icon = self._character_icon(cid, size=24)
            name = _char_names_map.get(cid, str(cid))
            if icon:
                inv_char_combo.addItem(icon, name, cid)
            else:
                inv_char_combo.addItem(name, cid)
        inv_char_combo.setMinimumWidth(240)
        inv_char_combo.setStyleSheet("font-size:13px; font-weight:700; padding:4px 8px;")
        self._combo_select(inv_char_combo, getattr(self, "_bd_invention_char", 0) or 0)

        def _on_inv_char_change(_i, combo=inv_char_combo):
            self._bd_invention_char = combo.currentData() or 0
            cb = getattr(self, "_bd_full_rebuild", None)
            if cb:
                cb()
        inv_char_combo.currentIndexChanged.connect(_on_inv_char_change)
        char_row_l.addWidget(inv_char_combo)
        # Der einzelne Lade-Knopf wurde entfernt (Übersichtlichkeit) - "🛰 Alles
        # aus ESI laden" oben im Dialog deckt das jetzt mit ab. Nur der
        # Zurücksetzen-Knopf bleibt hier.
        esi_undo_btn = QPushButton("\u21ba " + t("Reset"))
        esi_undo_btn.setIcon(icons.icon("refresh"))
        esi_undo_btn.setStyleSheet("font-size:11px; padding:4px 10px;")
        esi_undo_btn.setVisible(bool(getattr(self, "_bd_owned_bpc_by_id", None)))
        char_row_l.addWidget(esi_undo_btn)
        esi_undo_btn.clicked.connect(lambda: self._undo_all_invention_bpc_esi(esi_undo_btn))
        if _side_v is not None:
            _side_v.addWidget(char_row)
        else:
            cards_layout.insertWidget(1, char_row)

        decryptor_list = self._decryptor_list()
        adj_prices = (getattr(self, "_bd_opts", None) or {}).get("adjusted_prices", {}) or {}
        total_box = QLabel(); total_box.setStyleSheet(
            f"color:{theme.AMBER}; font-weight:800; font-size:15px;")
        _card_costs = {}
        self._bd_invention_needs = {}   # bp_id -> {datacores:[(id,qty)], decryptor_id, decryptor_qty}
        # Welche Items entstehen per INVENTION? Ihre Blaupausen sind
        # erfundene BPCs - die kopiert man NICHT (Nutzer-Fund, Sitzung 8:
        # bei Rigs braucht das T2 kein T1-Modul, die Endprodukt-"Blueprints"
        # im Runplaner sind die Invention-Ergebnisse).
        self._bd_invention_targets = set()

        def _dv_label(nm, v):
            """Decryptor-Name + Boni fürs Dropdown, z.B. 'Parity (+50% success,
            +3 Runs, ME+1%, TE-2%)' - damit man die Wahl sieht, ohne extra
            nachzuschlagen. Die Boni laufen durch t(), der Name ist ein
            EVE-Eigenname und bleibt."""
            pm, rm, me, te, tid = v
            if tid is None:
                return dec_anzeige(nm)
            bits = []
            if abs(pm - 1.0) > 1e-9:
                # "% Erfolg" stand hier bis Sitzung 22 als nackter f-String und
                # KEIN Scanner sah es: de_scan folgt `addItem(_dv_label(...))`
                # nicht in den Helfer hinein, und "Erfolg" stand in keiner
                # Wortliste. Dafuer gibt es jetzt de_scan5.
                bits.append(t("{v}% success").format(
                    v=f"{'+' if pm >= 1 else ''}{(pm - 1) * 100:.0f}"))
            if rm:
                bits.append(f"{'+' if rm >= 0 else ''}{rm} Runs")
            if me:
                bits.append(f"ME{'+' if me >= 0 else ''}{me}%")
            if te:
                bits.append(f"TE{'+' if te >= 0 else ''}{te}%")
            return f"{nm}  ({', '.join(bits)})" if bits else nm

        def _update_total():
            # Die Summe enthaelt seit Sitzung 9 auch die Jobgebuehren fuer
            # Kopieren und Invention (Formel in industry.science_job_fee,
            # EVE-Ref-verifiziert). Der Klammer-Zusatz dazu ist auf
            # NUTZER-ANSAGE wieder RAUS ("die Info stoert und ist
            # selbsterklaerend") - die Zeile ist ohnehin lang. Nicht
            # erneut anbieten.
            txt = (t("Invention total (all items): ")
                   + isk(sum(_card_costs.values())))
            dc, dcy, att = self._aggregate_invention_needs(
                getattr(self, "_bd_invention_needs", None))
            if att:
                stock = (getattr(self, "_bd_opts", None) or {}).get("stock") or {}
                bits = []
                for tid, q in sorted(dc.items(), key=lambda kv: -kv[1]):
                    have = int(stock.get(tid, 0) or 0)
                    bits.append(f"{q}\u00d7 {extra_names.get(tid, f'#{tid}')}"
                                + (t(" ({n} in the hangar)").format(n=min(have, q))
                                   if have else ""))
                for tid, q in sorted(dcy.items(), key=lambda kv: -kv[1]):
                    have = int(stock.get(tid, 0) or 0)
                    bits.append(f"{q}\u00d7 {extra_names.get(tid, f'#{tid}')}"
                                + (t(" ({n} in the hangar)").format(n=min(have, q))
                                   if have else ""))
                if bits:
                    txt += (t("  \u00b7  {n} attempts in total \u2192 ").format(n=att)
                            + " \u00b7 ".join(bits))
            # KOPIEN FUERS BAUEN (Nutzer, Sitzung 8): "Zusaetzlich brauche
            # ich ja noch T1-Kopien, um genuegend T1 bauen zu koennen wie im
            # Runplaner angegeben - 3 Blueprint-Copys mit jeweils 28 Runs,
            # damit alle 3 Charaktere gleichzeitig bauen koennen."
            # Eine Blaupause traegt EINEN Job: wer 9 Jobs parallel fahren
            # will, braucht 9 Blaupausen desselben Items. Der Runplaner
            # zeigte die Aufteilung, sagte aber nie, dass es KOPIEN sind.
            try:
                _zut = getattr(self, "_bd_last_assignments", None) or []
                _kop = industry.kopien_fuers_bauen(
                    _zut,
                    ohne_tids=getattr(self, "_bd_invention_targets", set()))
                if _kop:
                    _z = []
                    for _e in _kop[:6]:
                        _g = " / ".join(f"{_n}\u00d7{_r}"
                                        for _r, _n in _e["gruppen"])
                        _z.append(t("{name}: <b>{k}</b> copies ({j} jobs \u2013 {g} "
                                    "runs)").format(name=_e["name"], k=_e["kopien"],
                                                    j=_e["blaupausen"], g=_g))
                    _mehr = (t(" \u00b7 +{n} more").format(n=len(_kop) - 6)
                             if len(_kop) > 6 else "")
                    txt += (f'<br><span style="color:{theme.CYAN};">'
                            + t("Copy first for building (1 blueprint = 1 "
                                "simultaneous job, the original covers one of them): ")
                            + '</span>' + " \u00b7 ".join(_z) + _mehr)
            except Exception:
                pass          # Zusatzinfo darf den Tab nie blockieren
            total_box.setText(txt)
        # 0, nicht mehr 2: struct_lbl und char_row sitzen jetzt in der
        # Seitenleiste, die Kartenspalte beginnt also bei 0. Mit 2 landete
        # alles hinter dem Stretch.
        insert_at = 0
        for tid, bp_id, runs_needed, inv in items:
            self._bd_invention_targets.add(tid)
            t1_bp, base_runs, base_prob_sde, datacores = inv
            # Offizielle Formel: SkillModifier = 1 + Encryption/40 +
            # (Datacore1+Datacore2)/30, VOR dem Decryptor-Modifikator auf die
            # Basis-Erfolgschance angewandt. Ohne passende Charakter-/SDE-
            # Daten bleibt der Modifier bei 1.0 (reiner SDE-Basiswert, wie
            # bisher) - kein Raten.
            _skill_mod, _skill_char = self._bau_invention_skill_modifier_with_char(t1_bp)
            base_prob = min(1.0, base_prob_sde * _skill_mod)
            card = QFrame(); card.setObjectName("Card")
            outer = QVBoxLayout(card); outer.setContentsMargins(14, 12, 14, 12)
            outer.setSpacing(8)
            head = QLabel(f"{self._icon_html(t1_bp, size=22, kind='bp')}\u2699 "
                         f"{extra_names.get(t1_bp, f'#{t1_bp}')}")
            head.setStyleSheet(f"color:{theme.CYAN}; font-size:15px; font-weight:700;")
            outer.addWidget(head)
            _via_txt = (t("pinned") if getattr(self, "_bd_invention_char", 0)
                       else t("best character marked \u201eFor invention\u201c"))
            if _skill_mod > 1.0 + 1e-9:
                # DER CHARAKTERNAME IST DIE WICHTIGSTE INFORMATION DER ZEILE
                # (Nutzer: "welcher Charakter den besten Skillbonus hat, sollte
                # farblich hervorgehoben werden") - deshalb amber und groesser
                # als der Rest, statt nur fett im gleichen Gruen unterzugehen.
                # `html.escape`, weil EVE-Namen Zeichen wie & enthalten
                # duerfen und das Label Rich-Text rendert.
                import html as _h_sk
                _skill_lbl = QLabel(t(
                    "<b>Skill bonus active: \u00d7{mod}</b> on the base success "
                    "chance \u2013 skills of <span style='color:{color}; font-size:15px; "
                    "font-weight:800;'>{name}</span> ({via})"
                ).format(mod=f"{_skill_mod:.3f}", color=theme.AMBER,
                         name=_h_sk.escape(str(_skill_char)), via=_via_txt))
                # Lange Namen sind moeglich - umbrechen statt den Dialog
                # breiter zu ziehen.
                _skill_lbl.setWordWrap(True)
                _skill_lbl.setStyleSheet(
                    f"color:{theme.GREEN}; font-size:13px; font-weight:700; "
                    f"padding:4px 8px; background: rgba(63,185,80,0.12); "
                    f"border-radius:6px;")
                outer.addWidget(_skill_lbl)
            else:
                _skill_lbl = QLabel(t(
                    "\u26A0 <b>No skill bonus included</b> (base SDE value) - mark a "
                    "character as \u201eFor invention\u201c in the build characters tab "
                    "+ \u201eLoad job slots\u201c for the real, higher success chance."))
                _skill_lbl.setStyleSheet(
                    f"color:{theme.AMBER}; font-size:13px; font-weight:700; "
                    f"padding:4px 8px; background: rgba(242,162,60,0.12); "
                    f"border-radius:6px;")
                outer.addWidget(_skill_lbl)

            # Ingame-Layout nachgebaut: LINKS Input (Datacores + Decryptor mit
            # Icons, wie die zwei Slots + der Decryptor-Slot im Spiel), Pfeil,
            # RECHTS Outcome (Ziel-Icon + Erfolgschance/ME/TE/Runs als Balken-
            # artige Zeilen, wie das "OUTCOME"-Panel im Ingame-Fenster).
            row = QHBoxLayout(); row.setSpacing(14)
            left = QVBoxLayout(); left.setSpacing(4)
            for d, q in datacores:
                dc_row = QHBoxLayout(); dc_row.setSpacing(6)
                dc_row.addWidget(self._icon_label(d, size=32))
                dc_lbl = QLabel(f"{extra_names.get(d, f'#{d}')}")
                dc_lbl.setStyleSheet("font-size:11px;")
                dc_col = QVBoxLayout(); dc_col.setSpacing(0)
                dc_col.addWidget(dc_lbl)
                qty_lbl = QLabel(t("\u00d7{n} per attempt").format(n=q)); qty_lbl.setObjectName("Muted")
                qty_lbl.setStyleSheet("font-size:11px;")
                dc_col.addWidget(qty_lbl)
                dc_row.addLayout(dc_col); dc_row.addStretch()
                left.addLayout(dc_row)
            dec_row = QHBoxLayout(); dec_row.setSpacing(6)
            dec_icon_lbl = QLabel(); dec_icon_lbl.setFixedSize(32, 32)
            dec_row.addWidget(dec_icon_lbl)
            combo = QComboBox()
            for nm, v in decryptor_list:
                combo.addItem(_dv_label(nm, v), nm)
            self._combo_select(combo, self._bd_decryptor_map.get(bp_id, KEIN_DECRYPTOR))
            dec_row.addWidget(combo, 1)
            left.addLayout(dec_row)
            dc_sum_lbl = QLabel("")
            dc_sum_lbl.setObjectName("Muted")
            dc_sum_lbl.setStyleSheet("font-size:11px;")
            dc_sum_lbl.setWordWrap(True)
            left.addWidget(dc_sum_lbl)
            best_btn = QPushButton(t("Best choice for profit"))
            best_btn.setIcon(icons.icon("trophy"))
            best_btn.setToolTip(t(
                "Runs through all decryptors (plus „no decryptor“) for "
                  "the current build quantity and picks the one with the "
                  "lowest expected total cost."))
            # AUFFAELLIGER (Nutzer, Sitzung 20: "groesser, fetter, amber
            # umrandet"). Es ist der Knopf, der die Decryptor-Wahl abnimmt -
            # er sah aus wie eine Beschriftung.
            best_btn.setMinimumHeight(34)
            best_btn.setStyleSheet(
                f"QPushButton{{border:1px solid {theme.AMBER}; "
                f"color:{theme.AMBER}; font-weight:800; font-size:13px; "
                f"border-radius:6px; padding:4px 10px;}}"
                f"QPushButton:hover{{background:{theme.AMBER}; "
                f"color:{theme.BG};}}")
            left.addWidget(best_btn)
            # DIE ZWEI EINKAUFS-HAEKCHEN DIREKT DARUNTER (Nutzer): dort, wo
            # man die Decryptor- und Datacore-Frage ohnehin entscheidet, und
            # neben ME/TE sichtbar - statt ganz unten am Reiterende.
            try:
                _inv_kauf_row = self._build_invention_purchase_panel()
                left.addWidget(_inv_kauf_row)
            except Exception:
                pass
            manual_row = QHBoxLayout(); manual_row.setSpacing(6)
            manual_cb = QCheckBox(t("Attempts manually:"))
            manual_cb.setToolTip(t(
                "Off: the number of attempts is calculated automatically from the "
                "build plan quantity (\u2265{pct}% certainty). On: you set yourself how "
                "many invention attempts you want to make - also affects the header "
                "(job cost/margin/profit)."
            ).format(pct=int(industry.DEFAULT_INVENTION_CONFIDENCE * 100)))
            manual_row.addWidget(manual_cb)
            manual_spin = QSpinBox(); manual_spin.setRange(0, 100000)
            manual_spin.setEnabled(False)
            # Erst bei Enter/Fokusverlust (oder Pfeiltasten) auslösen, nicht bei
            # jedem Tastendruck - sonst würde ein Full-Rebuild (für die Kopfzeile,
            # s.u.) mitten im Tippen die Eingabe unterbrechen.
            manual_spin.setKeyboardTracking(False)
            _restore = (getattr(self, "_bd_manual_attempts", None) or {}).get(bp_id)
            if _restore:
                _r_manual, _r_val = _restore
                manual_cb.setChecked(bool(_r_manual))
                manual_spin.setEnabled(bool(_r_manual))
                if _r_val:
                    manual_spin.setValue(int(_r_val))
            manual_row.addWidget(manual_spin)
            manual_row.addStretch()
            left.addLayout(manual_row)
            # EINSPALTIG (Nutzer: "Flycatcher-Blueprint nach links nehmen,
            # unter Datacores und Decryptor-Dropdown"). Vorher lag das Ergebnis
            # RECHTS neben der Eingabe, mit einem Pfeil dazwischen - das war
            # dem Ingame-Fenster nachgebaut, passte aber nicht zu den anderen
            # Tabs, die ihren Inhalt links stapeln und rechts eine Seitenleiste
            # haben. Jetzt: Datacores -> Decryptor -> Ergebnis untereinander.
            # Der Pfeil entfaellt; die Reihenfolge von oben nach unten sagt
            # dasselbe.
            row.addLayout(left, 1)

            right = QHBoxLayout(); right.setSpacing(10)
            out_icon_lbl = self._icon_label(bp_id, size=48, kind="bp")
            right.addWidget(out_icon_lbl)
            out_col = QVBoxLayout(); out_col.setSpacing(2)
            out_name = QLabel("<b>" + t("{name} Blueprint").format(name=names.get(tid, f"#{tid}")) + "</b>")
            out_name.setStyleSheet(f"color:{theme.CYAN};")
            out_col.addWidget(out_name)
            outcome_lbl = QLabel(); outcome_lbl.setWordWrap(True)
            out_col.addWidget(outcome_lbl)
            if own_bpc_widgets is not None and tid == top_type_id:
                # Diese Karte ist die des tatsächlichen Endprodukts (nicht
                # irgendeines Zwischen-T2-Items) - hier gehören ME/TE/Eigene-BPC
                # hin, direkt neben der Erfolgschance/ME/TE-Zeile. Dieselben
                # Widget-Objekte wie vorher oben im Dialog-Header (nur der Ort
                # hat sich geändert) - ihre ganze bestehende Logik funktioniert
                # unverändert weiter.
                _me_sp, _te_sp, _obc_cb, _obc_runs_lbl, _obc_runs_sp = own_bpc_widgets
                # BUGFIX: Decryptor-Dropdown blieb bisher immer aktiv, auch wenn
                # "Eigene BPC statt Invention" angehakt ist - dabei wird die
                # ganze Invention-Rechnung für DIESES Item ignoriert, der
                # Decryptor spielt dann gar keine Rolle mehr. Jetzt ausgegraut,
                # solange die Checkbox an ist. own_bpc_cb löst beim Umschalten
                # bereits einen kompletten Rebuild aus (_bd_full_rebuild), der
                # diese ganze Funktion samt combo neu aufbaut - hier reicht also
                # der reine Ist-Zustand, KEIN zusätzliches .toggled.connect()
                # nötig (das hätte sich bei jedem Rebuild ein weiteres Mal auf
                # die alte, längst zerstörte combo verbunden -> Absturz beim
                # nächsten Umschalten, siehe Test).
                combo.setEnabled(not _obc_cb.isChecked())
                combo.setToolTip(
                    t("With \u201eOwn BPC instead of invention\u201c the invention is "
                      "skipped - the decryptor no longer matters.")
                    if _obc_cb.isChecked() else "")
                # SAGEN, WESSEN ME/TE HIER GEFRAGT SIND (Sitzung 19). Mit
                # "Eigene BPC" wird nicht mehr erfunden - die Felder darunter
                # meinen dann DEINE Kopie, nicht die erfundene. Sie starten
                # deshalb bei 0/0, und wer nichts eintraegt, rechnet mit 0/0.
                # Das ist die vorsichtige Richtung: mehr Material, laengere
                # Zeit, kein zu schoener Gewinn.
                if _obc_cb.isChecked():
                    # SAGEN, WAS GERADE GILT - nicht beide Faelle aufzaehlen
                    # (Nutzer, Sitzung 19: "also meine 3/2 zaehlt jetzt als
                    # 0/0 oder wie?"). Der alte Text erklaerte das Wenn-Dann
                    # und las sich, als seien die gefundenen Werte doch
                    # verworfen worden.
                    _obc_gefunden = self._bd_lookup_owned_bp_for_item(top_type_id)
                    if _obc_gefunden:
                        _obc_txt = t(
                            "\u26a0 Own BPC: the invention settings above do not "
                            "apply. ME {me} % / TE {te} % come from your own copy "
                            "(the worst-researched one you own) and are what is "
                            "being calculated. Change them if you want.").format(
                                me=int(_obc_gefunden.get("me", 0) or 0),
                                te=int(_obc_gefunden.get("te", 0) or 0))
                    else:
                        _obc_txt = t(
                            "\u26a0 Own BPC: the invention settings above do not "
                            "apply. No copy of your own was found via ESI, so ME/TE "
                            "stay at 0/0 and 0/0 is what is being calculated \u2013 "
                            "enter your own values.")
                    _obc_hint = QLabel(_obc_txt)
                    _obc_hint.setWordWrap(True)
                    _obc_hint.setStyleSheet(f"color:{theme.AMBER}; font-size:11px;")
                    out_col.addWidget(_obc_hint)
                _own_row1 = QHBoxLayout(); _own_row1.setSpacing(6)
                _me_cap = QLabel(t("ME:")); _me_cap.setStyleSheet("font-size:11px;")
                _own_row1.addWidget(_me_cap); _own_row1.addWidget(_me_sp)
                _te_cap = QLabel(t("TE:")); _te_cap.setStyleSheet("font-size:11px;")
                _own_row1.addWidget(_te_cap); _own_row1.addWidget(_te_sp)
                _own_row1.addStretch()
                out_col.addLayout(_own_row1)
                _own_row2 = QHBoxLayout(); _own_row2.setSpacing(6)
                _own_row2.addWidget(_obc_cb)
                _own_row2.addWidget(_obc_runs_lbl)
                _own_row2.addWidget(_obc_runs_sp)
                _own_row2.addStretch()
                out_col.addLayout(_own_row2)
            right.addLayout(out_col, 1)
            outer.addLayout(row)          # Eingabe (Datacores + Decryptor)
            _out_w = QWidget(); _out_w.setLayout(right)
            outer.addWidget(_out_w)       # Ergebnis DARUNTER, nicht daneben

            need_lbl = QLabel(); need_lbl.setWordWrap(True)
            outer.addWidget(need_lbl)

            # AUFTEILUNG AUF T1-KOPIEN (Nutzer-Problem, Sitzung 8): "ich kann
            # nicht aufteilen, in wievielen Tagen ich die Invention gemacht
            # haben will. Wenn ich 500 T2-Runs brauche, macht es mehr Sinn,
            # das auf 10 Kopien aufzuteilen." Der Grund ist Parallelitaet:
            # EIN Invention-Job verbraucht EINEN Run EINER Kopie, und eine
            # Kopie traegt nur EINEN Job gleichzeitig. Eine 212-Run-Kopie
            # arbeitet 212 Jobs NACHEINANDER ab; 10 Kopien lassen 10 Jobs
            # parallel laufen.
            _sp_box = QFrame(); _sp_box.setObjectName("Card")
            _spl = QHBoxLayout(_sp_box)
            _spl.setContentsMargins(12, 8, 12, 8); _spl.setSpacing(10)
            _spl.addWidget(QLabel(t("Split across")))
            self._inv_kopien = QSpinBox()
            self._inv_kopien.setRange(1, 50)
            self._inv_kopien.setValue(1)
            self._inv_kopien.setSuffix(t(" copies"))
            self._inv_kopien.setToolTip(t(
                "How many T1 copies the attempts are spread across.\n"
                "Each copy can carry ONE invention job at a time - more copies = "
                "more parallel jobs = less waiting.\n"
                "You have to make the copies from the original first (copy jobs "
                "run one after another on ONE original)."))
            _spl.addWidget(self._inv_kopien)
            _spl.addWidget(QLabel(t("\u00b7 free slots")))
            self._inv_slots = QSpinBox()
            self._inv_slots.setRange(1, 30)
            self._inv_slots.setValue(10)
            self._inv_slots.setToolTip(t(
                "Your simultaneously usable science slots (in game at the bottom "
                "left of the industry window, e.g. \u201eScience jobs 4/10\u201c). "
                "Limits how many copies can really work in parallel."))
            _spl.addWidget(self._inv_slots)
            # ZEIT-REGLER (Nutzer, Sitzung 9: "nur einen Regler bedienen, der
            # mir die Zeit anzeigt - wenn ich ihn auf 2 Tage ziehe, zeigt das
            # Tool, wie ich die T1-Kopien aufteilen soll"). Die Zeit ist eine
            # TREPPENFUNKTION der Kopienzahl (Wandzeit = Wellen x Versuchs-
            # zeit) - mehr Stufen als 1..freie Slots gibt es nicht. Der
            # Regler faehrt deshalb ueber genau diese Stufen und die Zeile
            # rechts zeigt beim Ziehen LIVE die Wandzeit samt Ingame-Eingabe.
            # Regler und Kopien-Feld sind DERSELBE Wert, nur zwei Griffe.
            _spl.addWidget(QLabel(t("\u00b7 time")))
            self._inv_zeit = QSlider(Qt.Horizontal)
            self._inv_zeit.setRange(1, self._inv_slots.value())
            self._inv_zeit.setValue(1)
            self._inv_zeit.setMinimumWidth(120)
            self._inv_zeit.setToolTip(t(
                "Drag until the shown wall time fits.\n"
                "Left = 1 copy (slow, few slots used),\n"
                "right = all free slots (as fast as possible)."))
            _spl.addWidget(self._inv_zeit)
            self._inv_split_lbl = QLabel("\u2013")
            self._inv_split_lbl.setWordWrap(True)
            _spl.addWidget(self._inv_split_lbl, 1)
            outer.addWidget(_sp_box)
            # ZEILE "Materialkosten / Bauzeit / Invention-Zeit" ENTFERNT
            # (Nutzer: "unnoetige Ueberlastung des UI"). Alle drei Werte sind
            # NEBENINFORMATION: die Materialkosten stehen als Gesamtsumme oben
            # in der Kopfzeile, die Bauzeit im Runplaner, und die
            # Invention-Zeit war laut eigenem Hinweis ohnehin "nur zur Info".
            # Das Label bleibt als TOOLTIP-Traeger - die drei Zahlen sind fuer
            # den Decryptor-Vergleich weiterhin abrufbar, nur nicht mehr
            # dauerhaft sichtbar.
            score_lbl = QLabel(); score_lbl.setWordWrap(True)
            score_lbl.setObjectName("Muted"); score_lbl.setStyleSheet("font-size:11px;")
            score_lbl.setVisible(False)
            outer.addWidget(score_lbl)
            cards_layout.insertWidget(insert_at, card)
            insert_at += 1

            # Materialkosten EINES Bau-Runs bei 0% ME (isoliert für dieses Item,
            # Sub-Komponenten behalten ihre normale Bau-vs-Kauf-Logik) - Basis,
            # auf die die BPC-ME (vom Decryptor) angewandt wird, damit "Beste
            # Wahl für Profit" nicht nur Invention-, sondern auch Material-
            # kosten mit einrechnet. Rig-/Struktur-ME bleibt hier bewusst außen
            # vor (siehe industry.invention_decryptor_options).
            try:
                _prod_qty = (recipes.product_to_bp.get(tid) or (0, 0, 1))[2] or 1
                _opts0 = dict(getattr(self, "_bd_opts", None) or {})
                _opts0["me_map"] = dict(_opts0.get("me_map") or {})
                _opts0["me_map"][tid] = 0
                _opts0["invention"] = False
                _pm = (getattr(self, "_bd_pricemap", None) or {}).get
                mc0_per_run = (industry.build_cost(tid, _pm, recipes, _opts0) or 0.0) * _prod_qty
            except Exception:
                mc0_per_run = 0.0

            # Bauzeit EINES Runs mit aktuellen Struktur-/Skill-Boni, aber OHNE
            # Decryptor-TE (direkt aus SDE: recipes.activity_time) - Basis für
            # die Zeitgewichtung in invention_decryptor_options (Schritt 2/3).
            try:
                _te_mfg = (getattr(self, "_bd_opts", None) or {}).get(
                    "te_factor_mfg", (getattr(self, "_bd_opts", None) or {})
                    .get("te_factor", 1.0))
                build_seconds_0dec = (recipes.activity_time.get(
                    (bp_id, industry.MANUFACTURING), 0) or 0) * _te_mfg
            except Exception:
                build_seconds_0dec = 0.0

            # Invention-JOB-Zeit (nicht Bauzeit!) direkt aus der SDE
            # (recipes.activity_time für activity_id=INVENTION), mit dem
            # Zeit-Rig-Bonus der für Invention gewählten Struktur (Struktur-
            # Tab zeigte den bisher nur an, ohne ihn irgendwo zu verrechnen -
            # das war die Lücke hinter "noch nicht in Baurechnung genutzt").
            # Decryptoren wirken NICHT auf die Job-Zeit selbst (nur auf Runs/
            # ME/TE/Erfolgschance der fertigen BPC), deshalb hier fix pro Item.
            _inv_time_base = recipes.activity_time.get((t1_bp, industry.INVENTION), 0) or 0
            _inv_struct_pct = (self._struct_extra_rig_pct(inv_struct, "invention")
                               if inv_struct else 0) or 0
            _inv_time_per_attempt = _inv_time_base * (1 - _inv_struct_pct / 100.0)

            def _recompute(combo=combo, bp_id=bp_id, base_runs=base_runs,
                          base_prob=base_prob, datacores=datacores,
                          runs_needed=runs_needed, outcome_lbl=outcome_lbl,
                          need_lbl=need_lbl, dec_icon_lbl=dec_icon_lbl,
                          manual_cb=manual_cb, manual_spin=manual_spin,
                          score_lbl=score_lbl, mc0_per_run=mc0_per_run,
                          build_seconds_0dec=build_seconds_0dec,
                          inv_time_per_attempt=_inv_time_per_attempt,
                          inv_struct_pct=_inv_struct_pct,
                          copy_secs_per_attempt=(
                              recipes.activity_time.get(
                                  (t1_bp, industry.COPYING), 0) or 0)):
                key = combo.currentData()
                dv = next((v for n, v in decryptor_list if n == key),
                          (1.0, 0, 0, 0, None))
                dec_icon_lbl.clear()
                if dv[4]:
                    pm = self._item_pixmap(dv[4], size=32)
                    if pm:
                        dec_icon_lbl.setPixmap(
                            pm.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                outcome = industry.invention_outcome(base_runs, base_prob, dv)
                outcome_lbl.setText(
                    f'<span style="color:{theme.MUTED};">' + t("Success chance") + '</span> '
                    f'<b>{outcome["prob"]*100:.1f}%</b>  \u00b7  '
                    f'<span style="color:{theme.MUTED};">' + t("Runs/success") + '</span> '
                    f'<b>{outcome["runs"]}</b>  \u00b7  '
                    # de_scan3: aus  (HTML-Geruest, die Woerter laufen durch t())
                    f'<span style="color:{theme.MUTED};">' + t("ME")
                    # FEHLENDES f (Nutzer, Sitzung 19): ohne das Praefix stand
                    # der Platzhalter woertlich in der Zeile - "ME
                    # {outcome["me_pct"]}%". Die TE-Haelfte darunter war eine
                    # f-Zeichenkette und zeigte richtig 4 %, deshalb fiel es
                    # lange nicht auf.
                    + f'</span> <b>{outcome["me_pct"]}%</b>'
                    # de_scan3: an
                    f'  \u00b7  <span style="color:{theme.MUTED};">' + t("TE") + '</span> '
                    f'<b>{outcome["te_pct"]}%</b>')
                dc_cost = sum((adj_prices.get(d, 0) or 0) * q for d, q in datacores)
                dcy_tid = dv[4]
                dcy_cost = (adj_prices.get(dcy_tid, 0) or 0) if dcy_tid else 0.0
                # Bereits per ESI geladene, eigene BPC-Runs decken einen Teil
                # ab - egal ob Endprodukt oder Komponente, für JEDES Item hier
                # mit eigenem bp_id-Eintrag (aus "Eigene BPCs für alle Items
                # laden" bzw. dem Endprodukt-spezifischen ESI-Laden im
                # "Blaupausen je Stufe"-Panel).
                _owned_runs = self._resolve_inv_owned_runs().get(bp_id, 0)
                _runs_still_needed = max(0, runs_needed - _owned_runs)
                ap = industry.invention_attempt_plan(
                    _runs_still_needed, outcome, [dc_cost], dcy_cost,
                    confidence=self._bd_inv_confidence())
                _dc_stock = (getattr(self, "_bd_opts", None) or {}).get("stock") or {}
                _dc_attempts = int(ap["confident_attempts"] or 0)
                _dc_total_needed = 0
                _dc_owned = 0
                for _d, _q in datacores:
                    _needed_d = _dc_attempts * _q
                    _dc_total_needed += _needed_d
                    _dc_owned += min(_needed_d, int(_dc_stock.get(_d, 0) or 0))
                _dc_stock_txt = (t(" ({have} already in the hangar \u2192 {buy} more to buy)").format(
                                    have=_dc_owned, buy=max(0, _dc_total_needed - _dc_owned))
                                if _dc_owned else "")
                if not manual_cb.isChecked():
                    manual_spin.blockSignals(True)
                    manual_spin.setValue(int(ap["confident_attempts"] or 0))
                    manual_spin.blockSignals(False)
                    _owned_txt = (t(" (\u2212{n} already on hand as own BPC)").format(n=_owned_runs)
                                 if _owned_runs else "")
                    # ZEILENWEISE STATT FLIESSTEXT (Nutzer: "weniger Text zum
                    # Lesen, schoener aufgelistet untereinander"). Vorher stand
                    # das alles in EINER Zeile mit Mittelpunkten getrennt und
                    # lief ueber die volle Fensterbreite.
                    # AUFGERAEUMT (Nutzer, Sitzung 8): "Entferne jegliche
                    # unnoetigen Informationen, behalte nur was ich
                    # brauche. Davon gelingen -> nicht noetig. Datacores
                    # -> nicht noetig. Hervorheben: fuer 75% Sicherheit,
                    # weil das ist die Zahl, die ich ingame eingeben muss."
                    # Also: EINE grosse Leitzahl, darunter der Kontext
                    # klein. Die Datacore-Rechnung laeuft weiter (die
                    # Gesamtzeile unten nennt sie), nur die Doppelung hier
                    # ist weg.
                    need_lbl.setText(
                        f'<div style="font-size:11px;color:{theme.MUTED};'
                        f'margin-bottom:2px;">'
                        + t("Enter in game \u2013 attempts for \u2265{pct}% certainty").format(
                            pct=int(ap["confidence"] * 100))
                        + f'</div>'
                        f'<div style="font-size:26px;font-weight:800;'
                        f'color:{theme.AMBER};font-family:{theme.MONO};'
                        f'line-height:1.05;">{ap["confident_attempts"]}'
                        f'<span style="font-size:13px;font-weight:600;'
                        f'"> ' + t("attempts") + '</span></div>'
                        + _kv_rows([
                            (t("for {n} runs").format(n=runs_needed) + _owned_txt,
                             t("{n} successes").format(n=ap["successes_needed"]), None),
                            (t("on average it would take"),
                             t("\u2248{n} attempts").format(n=f'{ap["expected_attempts"]:.1f}'),
                             None),
                            (t("T1 copies"),
                             t("{n} copy runs (1 attempt = 1 run, split as you like)").format(
                                 n=ap["confident_attempts"]),
                             theme.CYAN),
                            (t("Invention cost"),
                             f'\u2248{isk(ap["confident_cost"])}',
                             theme.AMBER),
                        ]))
                    total_cost = ap["confident_cost"]
                    _inv_attempts_n = int(ap["confident_attempts"] or 0)
                else:
                    mpn = industry.invention_manual_plan(
                        manual_spin.value(), outcome, [dc_cost], dcy_cost,
                        successes_needed=ap["successes_needed"])
                    conf_actual = mpn.get("confidence_actual", 0.0)
                    status_col = (theme.GREEN if conf_actual >= 0.75 else
                                 theme.AMBER if conf_actual >= 0.5 else theme.RED)
                    # Manueller Zweig, gleicher Aufbau wie oben: die Zahl,
                    # die ingame eingetippt wird, ist die Leitzahl - hier
                    # der selbst gesetzte Wert. Darunter, wie sicher er
                    # reicht (gruen/amber/rot) und der Kontext.
                    need_lbl.setText(
                        f'<div style="font-size:11px;color:{theme.MUTED};'
                        f'margin-bottom:2px;">'
                        + t("Enter in game \u2013 set by you")
                        + f'</div>'
                        f'<div style="font-size:26px;font-weight:800;'
                        f'color:{theme.AMBER};font-family:{theme.MONO};'
                        f'line-height:1.05;">{manual_spin.value()}'
                        f'<span style="font-size:13px;font-weight:600;'
                        f'"> ' + t("attempts") + '</span></div>'
                        + _kv_rows([
                            (t("enough for all {n} runs").format(n=runs_needed),
                             f'<b>{conf_actual*100:.0f}%</b>', status_col),
                            (t("yields on average"),
                             t("\u2248{runs} runs from \u2248{succ} successes").format(
                                 runs=f'{mpn["expected_runs"]:.1f}',
                                 succ=f'{mpn["expected_successes"]:.1f}'),
                             None),
                            (t("T1 copies"),
                             t("{n} copy runs (1 attempt = 1 run, split as you like)").format(
                                 n=manual_spin.value()),
                             theme.CYAN),
                            (t("Invention cost"),
                             f'\u2248{isk(mpn["total_cost"])}', theme.AMBER),
                        ]))
                    total_cost = mpn["total_cost"]
                    _inv_attempts_n = max(0, int(manual_spin.value() or 0))
                material_cost = mc0_per_run * (1 - outcome["me_pct"] / 100.0) * runs_needed
                _bz_txt = _iz_txt = _iz_tip_extra = ""
                time_txt = ""
                if build_seconds_0dec:
                    days = (build_seconds_0dec * (1 - outcome["te_pct"] / 100.0)
                           * runs_needed) / 86400.0
                    time_txt = "x"          # nur noch Bedingung
                    _bz_txt = t("\u2248{d} days").format(d=f"{days:.2f}")
                # AUFTEILUNGS-PANEL fuellen (Nutzer: Parallelitaet planen).
                # Als Funktion auf self gemerkt, damit die Regler sie ohne
                # vollen Rebuild aufrufen koennen (s. _split_refresh).
                def _fuelle_aufteilung(_att=_inv_attempts_n, _oc=outcome,
                                       _ipa=inv_time_per_attempt):
                    # Versuchszahl fuer die Nutzstufen des Zeit-Reglers
                    # merken (s. _zeit_zieht unten).
                    self._bd_inv_att_n = int(_att or 0)
                    _auf = industry.kopien_aufteilung(
                        _att, int(_oc.get("runs") or 1),
                        slots=self._inv_slots.value(),
                        kopien=self._inv_kopien.value(),
                        prob=_oc.get("prob"))
                    if _auf["kopien"]:
                        # Bis Sitzung 22 ohne t(): kein deutscher Text, aber
                        # in der deutschen Fassung waere er englisch geblieben.
                        # de_scan3 sah ihn nicht - er laeuft ueber `_rest` in
                        # setText, und dorthin folgt der Scanner nicht.
                        _rest = (" \u00b7 " + t("{n} runs in reserve").format(
                                     n=_auf["rest_reserve"])
                                 if _auf["rest_reserve"] else "")
                        # Wandzeit = Wellen x Zeit je Versuch. Bei 1 Kopie
                        # ist das die volle Kette, bei N Kopien entsprechend
                        # weniger - genau die Zahl, nach der der Nutzer
                        # gefragt hat ("in wievielen Tagen").
                        _dauer = ""
                        if _ipa:
                            _secs = _ipa * _auf["wellen"]
                            # "bei N parallel" lief bis Sitzung 22 ohne t():
                            # der Text wandert ueber die Variable `_dauer` in
                            # setText, de_scan sieht dort nur einen Namen.
                            _dauer = (f' \u00b7 <b>{self._fmt_dur(_secs)}</b> '
                                      + t("at {n} in parallel").format(
                                          n=_auf["parallel"]))
                        self._inv_split_lbl.setText(
                            f'<span style="color:{theme.CYAN};">'
                            + t("{n}\u00d7 T1 copy with ").format(n=_auf["kopien"])
                            + '<b>'
                            + t("{n} runs").format(n=_auf["runs_je_kopie"])
                            + '</b></span>'
                            + f'{_rest}{_dauer}'
                            # INGAME-UEBERSETZUNG (Nutzer, Sitzung 9: "wie
                            # lese ich es nochmal, was muss ich ingame
                            # eingeben?"). Die Feldnamen des Kopierfensters
                            # stehen WOERTLICH dabei - "Job Runs" und "Runs
                            # per Copy" heissen im Spiel so und bleiben
                            # englisch, in JEDER Sprachfassung.
                            + '<br>' + t("\u2192 in-game copy job: ")
                            # de_scan3: aus  (EVE-Feldnamen, bleiben in jeder Sprache englisch)
                            + f'<b>Job Runs {_auf["kopien"]}</b> \u00b7 '
                            + f'<b>Runs per Copy {_auf["runs_je_kopie"]}</b>')
                            # de_scan3: an
                        _warn = ""
                        if _auf["kopien"] > self._inv_slots.value():
                            _warn = (f'<br><span style="color:{theme.AMBER};">'
                                     + t("More copies than slots \u2013 only {n} run "
                                         "at a time.").format(n=_auf["parallel"])
                                     + '</span>')
                            self._inv_split_lbl.setText(
                                self._inv_split_lbl.text() + _warn)
                        self._inv_split_lbl.setToolTip(t(
                            "{total} copy runs in total for {att} required attempts.\n"
                            "{waves} job waves one after another (each wave {par} jobs "
                            "in parallel).\n"
                            "You have to make the copies yourself first \u2013 with ONE "
                            "original, copy jobs run one after another."
                        ).format(total=_auf["versuche_gesamt"], att=_att,
                                 waves=_auf["wellen"], par=_auf["parallel"]))
                self._fuelle_aufteilung = _fuelle_aufteilung
                try:
                    _fuelle_aufteilung()
                except Exception:
                    pass          # Anzeige darf den Bauplan nie blockieren

                inv_time_txt = ""
                if inv_time_per_attempt:
                    total_inv_secs = inv_time_per_attempt * _inv_attempts_n
                    inv_time_txt = "x"      # nur noch Bedingung
                    # Der Rig-Bonus ist im Wert schon DRIN - er stand vorher
                    # als Klammer daneben. Gehoert in den Tooltip, nicht in
                    # die Zeile.
                    _iz_txt = (f"\u2248{self._fmt_dur(total_inv_secs)} "
                               f"({_inv_attempts_n}\u00d7)")
                    if inv_struct_pct:
                        _iz_tip_extra = t(
                            "Invention time includes {pct}% structure rig bonus."
                        ).format(pct=f"{inv_struct_pct:.0f}")
                # Auch hier zeilenweise; die Klammer-Erklaerungen wandern in
                # den Tooltip, statt die Zeile zu verdoppeln.
                _sc_rows = [(t("Material cost ({me}% ME)").format(
                                 me=outcome["me_pct"]),
                             f"\u2248{isk(material_cost)}", None)]
                if time_txt:
                    _sc_rows.append((t("Build time"), _bz_txt, None))
                if inv_time_txt:
                    _sc_rows.append((t("Invention time"), _iz_txt, None))
                score_lbl.setText(_kv_rows(_sc_rows))
                # Unsichtbar, aber die Zahlen bleiben abrufbar: derselbe Text
                # haengt am Ergebnis-Block, wo man den Decryptor waehlt.
                _sc_plain = " \u00b7 ".join(
                    f"{_l}: {_v}" for _l, _v, _c in _sc_rows)
                outcome_lbl.setToolTip(_sc_plain)
                score_lbl.setToolTip(t(
                    "Material cost: only the base ME of this item \u2013 structure and "
                    "rig ME apply on top and are the same for all decryptors.\n"
                    "Build time is for information only \u2013 \u201eBest choice\u201c looks "
                    "at total profit alone.\n"
                    "Invention time is sequential with 1 free science slot; faster "
                    "accordingly with more slots.")
                    + (("\n" + _iz_tip_extra) if _iz_tip_extra else ""))
                self._bd_decryptor_map[bp_id] = key
                _card_costs[bp_id] = total_cost
                _attempts_n = max(0, int(manual_spin.value() or 0))
                self._bd_invention_needs[bp_id] = {
                    "datacores": [(d, q * _attempts_n) for d, q in datacores],
                    "decryptor_id": dv[4], "decryptor_qty": _attempts_n if dv[4] else 0,
                    "attempts": _attempts_n, "successes_needed": ap["successes_needed"],
                    # für die Runplaner-Gesamtzeile: Invention + Kopieren
                    # (1 x 1-Run-BPC je Versuch; Kopierzeit aus der SDE,
                    # Struktur-/Skill-Boni bewusst weggelassen -> "grob")
                    "inv_secs": int((inv_time_per_attempt or 0) * _attempts_n),
                    "copy_secs": int((copy_secs_per_attempt or 0) * _attempts_n),
                }
                # Nutzer-Wunsch: nicht nur „x2 je Versuch", sondern die
                # GESAMT-Stückzahl für alle Versuche dieses Items sichtbar.
                _parts = [f"{int(q * _attempts_n)}\u00d7 "
                          f"{extra_names.get(d, f'#{d}')}"
                          for d, q in datacores]
                if dv[4]:
                    _parts.append(f"{_attempts_n}\u00d7 "
                                  f"{extra_names.get(dv[4], f'#{dv[4]}')}")
                dc_sum_lbl.setText(
                    t("Total for {n} attempts: ").format(n=_attempts_n)
                    + " \u00b7 ".join(_parts) if _parts and _attempts_n else "")
                _update_total()

            def _on_change(_idx, bp_id=bp_id, combo=combo):
                key = combo.currentData()
                self._bd_decryptor_map[bp_id] = key
                dv = next((v for n, v in decryptor_list if n == key),
                          (1.0, 0, 0, 0, None))
                self._bd_opts.setdefault("inv_decryptor_map", {})[bp_id] = dv
                cb = getattr(self, "_bd_full_rebuild", None)
                if cb:
                    cb()
            combo.currentIndexChanged.connect(_on_change)

            def _on_manual_change(bp_id=bp_id, manual_cb=manual_cb, manual_spin=manual_spin):
                self._bd_manual_attempts[bp_id] = (manual_cb.isChecked(),
                                                   manual_spin.value())
                cb = getattr(self, "_bd_full_rebuild", None)
                if cb:
                    cb()   # aktualisiert auch Kopfzeile (Job-Kosten/Marge/Gewinn)
                else:
                    _recompute()

            def _on_manual_toggle(v, s=manual_spin):
                s.setEnabled(v)
                _on_manual_change()
            manual_cb.toggled.connect(_on_manual_toggle)
            manual_spin.valueChanged.connect(lambda *_a: _on_manual_change())
            # NUTZER-FUND (Sitzung 8): "ich kann hier gar nichts eingeben."
            # URSACHE: die Regler hingen an _on_manual_change, und das ruft
            # _bd_full_rebuild - der baut den GANZEN Invention-Tab neu und
            # ZERSTOERT dabei genau die Spinbox, in die man gerade tippt.
            # Nach dem ersten Tastendruck war das Widget weg, Fokus futsch,
            # Eingabe unmoeglich. FIX: die Regler rufen NUR die
            # Panel-Aktualisierung (_split_refresh) - kein Rebuild, kein
            # Fokusverlust. Die Werte werden gemerkt, damit sie einen
            # spaeteren echten Rebuild ueberleben.
            def _split_refresh(*_a):
                self._bd_inv_split = (self._inv_kopien.value(),
                                      self._inv_slots.value())
                _fn = getattr(self, "_fuelle_aufteilung", None)
                if _fn:
                    try:
                        _fn()
                    except Exception:
                        pass
            self._inv_kopien.valueChanged.connect(_split_refresh)
            self._inv_slots.valueChanged.connect(_split_refresh)
            # Regler <-> Kopien-Feld: EIN Wert, zwei Griffe. blockSignals
            # gegen das Signal-Pingpong; die Slot-Zahl deckelt den Regler.
            # NUTZSTUFEN-SCHNAPPEN (Nutzer, Sitzung 9: "ich kann ihn hoeher
            # ziehen als er einen Nutzen hat"): die Wandzeit haengt an
            # ceil(Versuche/Kopien) - jede Kopienzahl, die dieselben Runs je
            # Kopie ergibt wie eine kleinere, bringt NICHTS (gleiche Zeit,
            # nur mehr belegte Slots und Reserve-Runs). Beide Griffe
            # schnappen deshalb auf die KLEINSTE Kopienzahl derselben
            # Zeitstufe: ceil(att / ceil(att / N)).
            def _nutzstufe(v):
                import math
                _att = int(getattr(self, "_bd_inv_att_n", 0) or 0)
                v = int(v)
                if _att <= 0 or v <= 1:
                    return v
                return math.ceil(_att / math.ceil(_att / min(v, _att)))

            def _zeit_zieht(v):
                v = _nutzstufe(v)
                _s = self._inv_zeit
                if _s.value() != v:
                    _s.blockSignals(True)
                    _s.setValue(v)
                    _s.blockSignals(False)
                if self._inv_kopien.value() != v:
                    self._inv_kopien.setValue(v)
            self._inv_zeit.valueChanged.connect(_zeit_zieht)

            def _kopien_zieht(v):
                v = _nutzstufe(v)
                if self._inv_kopien.value() != v:
                    self._inv_kopien.blockSignals(True)
                    self._inv_kopien.setValue(v)
                    self._inv_kopien.blockSignals(False)
                _s = self._inv_zeit
                if _s.value() != int(v):
                    _s.blockSignals(True)
                    _s.setValue(min(int(v), _s.maximum()))
                    _s.blockSignals(False)
            self._inv_kopien.valueChanged.connect(_kopien_zieht)

            def _slots_deckeln(v):
                self._inv_zeit.setMaximum(max(1, int(v)))
            self._inv_slots.valueChanged.connect(_slots_deckeln)
            # Gemerkte Werte nach einem Rebuild zurueckstellen (ohne dabei
            # ein weiteres Signal auszuloesen).
            _alt = getattr(self, "_bd_inv_split", None)
            if _alt:
                for _w, _v in ((self._inv_kopien, _alt[0]),
                               (self._inv_slots, _alt[1])):
                    _w.blockSignals(True); _w.setValue(int(_v))
                    _w.blockSignals(False)

            def _pick_best(_checked=False, combo=combo, base_runs=base_runs,
                          base_prob=base_prob, datacores=datacores,
                          runs_needed=runs_needed, mc0_per_run=mc0_per_run,
                          build_seconds_0dec=build_seconds_0dec, score_lbl=score_lbl,
                          bp_id=bp_id, top_type_id=top_type_id):
                """Rechnet ALLE Decryptoren (inkl. 'Kein Decryptor') mit der
                ECHTEN production_plan-Formel durch (exakt dieselbe wie die
                Kopfzeile: Material inkl. Job-Kosten-Kopplung an den
                Materialwert, Invention-Kosten) und wählt den mit dem
                niedrigsten Gesamtpreis = höchstem Gewinn - keine separate
                Näherungsformel mehr, die von der Kopfzeile abweichen könnte."""
                if top_type_id is not None:
                    ranked = industry.invention_best_decryptor_by_real_cost(
                        top_type_id, self._bd_qty, self._bd_pricemap.get,
                        self._bd_recipes, self._bd_opts, bp_id, decryptor_list)
                    # Ist gerade eine Orderbuch-Ladder aktiv (nach "Neu
                    # berechnen"), muss das Ranking dieselbe ladder-korrigierte
                    # Materialkosten-Basis nutzen wie die Kopfzeile - sonst
                    # könnte "Beste Wahl" wieder von "Gesamt" abweichen, genau
                    # wie der zuletzt gefundene Bug.
                    # Gueltigkeit NUR ueber _bd_ladder_ctx - sonst faellt das
                    # Ranking bei geaenderter Menge auf Flachpreise zurueck,
                    # waehrend die Kopfzeile schon orderbuch-genau rechnet.
                    _lctx = self._bd_ladder_ctx(self._bd_qty)
                    _obs = (_lctx or {}).get("obs")
                    if _obs is not None:
                        for _r in ranked:
                            _test_opts = dict(self._bd_opts)
                            _dm = dict(self._bd_opts.get("inv_decryptor_map") or {})
                            _dm[bp_id] = _r["decryptor"]
                            _test_opts["inv_decryptor_map"] = _dm
                            try:
                                _tp = industry.production_plan(
                                    top_type_id, self._bd_qty, self._bd_pricemap.get,
                                    self._bd_recipes, _test_opts)
                                _mat_ladder = industry.ladder_cost_for_buy(
                                    (_tp or {}).get("buy") or {}, _obs,
                                    self._bd_pricemap.get)
                                # BESTAND NICHT VERGESSEN. Die Kopfzeile rechnet
                                # mat_ladder + job + inv + stock_cost; hier
                                # fehlte der letzte Summand. Folge: Decryptoren,
                                # die weniger KAUFEN und dafuer mehr aus dem
                                # BESTAND ziehen, sahen kuenstlich guenstig aus -
                                # "Beste Wahl" nahm Attainment (27,8 % Marge)
                                # statt Parity (30,8 %), obwohl die Kopfzeile
                                # Parity als besser auswies (Nutzer-Fund).
                                # Der ungefilterte Rang aus
                                # invention_best_decryptor_by_real_cost war
                                # richtig - erst diese Korrektur hat ihn
                                # verdorben.
                                _r["total_cost"] = (_mat_ladder
                                                    + float((_tp or {}).get("job_cost", 0.0))
                                                    + float((_tp or {}).get("inv_cost", 0.0))
                                                    + float((_tp or {}).get("stock_cost", 0.0)))
                            except Exception:
                                pass
                        ranked.sort(key=lambda r: r["total_cost"])
                else:
                    dc_cost = sum((adj_prices.get(d, 0) or 0) * q for d, q in datacores)
                    ranked = industry.invention_decryptor_options(
                        base_runs, base_prob, runs_needed, decryptor_list, [dc_cost],
                        mc0_per_run, lambda t: adj_prices.get(t, 0) or 0.0,
                        build_seconds_per_run_0decryptor=build_seconds_0dec)
                if ranked:
                    best = ranked[0]
                    self._combo_select(combo, best["name"])  # löst _on_change aus
            best_btn.clicked.connect(_pick_best)

            _recompute()
            # Direkt beim Aufbau auch in opts eintragen (falls schon ein
            # Decryptor gewählt war, z.B. nach einer Mengenänderung).
            _dv0 = next((v for n, v in decryptor_list
                        if n == self._bd_decryptor_map.get(bp_id, KEIN_DECRYPTOR)),
                       None)
            if _dv0 and _dv0[4] is not None:
                self._bd_opts.setdefault("inv_decryptor_map", {})[bp_id] = _dv0
        _update_total()
        cards_layout.insertWidget(insert_at, total_box)
        # DIE ZWEI EINKAUFS-HAKEN GEHOEREN HIERHER (Nutzer-Entscheid,
        # Sitzung 20). Sie standen als eigene Mini-Karte in der Seitenleiste
        # des Bauplans, danach kurz als Anhaengsel der Kategorien-Karte -
        # beides falsch am Platz: die Kategorien-Karte beantwortet "habe ich
        # die Blaupausen", diese zwei "soll das Invention-Material in die
        # Einkaufsliste". Hier stehen sie direkt unter der Rechnung, aus der
        # ihre Mengen stammen (Versuche x Datacores je Versuch).
        # (Die zwei Einkaufs-Haekchen stehen seit Sitzung 20 oben unter
        # "Best choice for profit", nicht mehr am Reiterende.)
        _top_covered = any(tid == top_type_id for tid, _bp_id, _runs, _inv in items)
        if not _top_covered:
            _own_bpc_fallback_card()

    def _fill_material_tab(self, plan, names, tbl, status_lbl=None):
        """Füllt den 'Materialien'-Tab: jedes Rohmaterial, das laut production_plan()
        tatsächlich eingekauft werden muss (plan["buy"]) plus, was schon durch
        Bestand gedeckt ist (plan["stock_used"]) - macht zusammen den GESAMTEN
        Bedarf. Bestand kommt aus self._bd_opts["stock"] - derselben Quelle, die
        "Assets abziehen" oben schon befüllt, kein zweiter ESI-Abruf nötig.
        Genau dasselbe genug/fehlt-Muster wie im Blueprints-Tab."""
        # QTreeWidgetItem wird fuer die Kategorie-Gruppen gebraucht.
        from PySide6.QtWidgets import QTreeWidgetItem
        from PySide6.QtWidgets import QTableWidgetItem
        tbl.setSortingEnabled(False)
        stock = (getattr(self, "_bd_opts", None) or {}).get("stock") or {}
        _virt_tab = getattr(self, "_bd_virt_stock", None) or {}
        # GESAMTBESITZ (Portfolio, ALLE Orte) - nur fuer den Tooltip, EINMAL
        # geholt statt je Zeile. Die Spalte selbst bleibt unveraendert: sie
        # zaehlt weiter nur, was der Plan wirklich verplanen kann.
        try:
            _besitz_gesamt = self._owned_and_selling()[0]
        except Exception:
            _besitz_gesamt = {}
        # Herkunft je Item (s. _resolve_stock_sources). Fehlt sie (sehr alter
        # Zustand / noch kein Abruf), wird die effektive Zahl ehrlich als
        # „ESI" ausgewiesen statt eine Einfügung zu erfinden.
        src_map = getattr(self, "_bd_stock_src", None) or {}
        # SPALTENBESCHRIFTUNG ehrlich halten (Nutzer-Fund): bei EINGEFRORENEN
        # Plänen steht in der "ESI"-Spalte gar nicht der rohe ESI-Wert,
        # sondern max(Einfrier-Stand, live) je Item - der Einfrier-Stand hält
        # verbrauchtes Material bewusst fest. "Besitze (ESI)" wäre dort
        # schlicht falsch. Dieselbe Ehrlichkeits-Regel wie überall sonst:
        # jede angezeigte Zahl muss sagen, woher sie kommt.
        _is_frozen = bool(getattr(self, "_bd_frozen", None))
        _esi_hdr = (t("Owned ( frozen+live)") if _is_frozen
                    else t("Owned (ESI)"))
        if _is_frozen:
            _esi_hdr_tip = t(
                "FROZEN plan: this shows max(frozen state, live stock) \u2013 NOT the "
                "raw ESI value.\nThe frozen state records what you had bought on the "
                "freeze day; anything built since is credited live.\nCan therefore be "
                "higher than your real hangar. Reset: Tools \u2192 \u201eReset frozen "
                "stock\u201c.")
        else:
            _esi_hdr_tip = t(
                "Hangar stock per ESI \u2013 only the locations/characters of the "
                "chosen stock scope.\nWhat ESI does not see, you can paste on the right.")
        _hi = tbl.headerItem()
        if _hi is not None:
            _hi.setText(3, _esi_hdr)
            _hi.setToolTip(3, _esi_hdr_tip)
        _info_lbl = getattr(self, "_bd_mat_tab_info", None)
        if _info_lbl is not None:
            # NUR die Warnung, kein Dauertext mehr - und nur dann sichtbar.
            _zeilen_info = []
            if _is_frozen:
                _zeilen_info.append(
                    "\u26a0 " + t(
                        "FROZEN: the left stock column shows "
                        "max(frozen state, live)."))
            # FEHLBEDARF AUTOMATISCH (Nutzer-Wunsch Sitzung 12: "fuer den
            # Check-Shortfall-Knopf haette ich lieber eine staendige
            # automatische Loesung").
            #
            # WARUM ALS EIGENE ZEILE UND NICHT IN DER EINKAUFSLISTE: der
            # Nutzer will ausdruecklich, dass die Einkaufsliste NICHT wieder
            # waechst ("gekauft ist gekauft"). Ein real verschwundenes
            # Material darf ihn trotzdem nicht am Reaktor ueberraschen -
            # also warnen, ohne die Liste anzufassen.
            try:
                _fehl_auto = self._fehlbedarf_jetzt()
            except Exception:
                _fehl_auto = None          # Anzeige, nie kritisch
            if _fehl_auto:
                _n_f = len(_fehl_auto)
                # NAMEN AUS DEM PARAMETER `names` - `_bd_names` gibt es in
                # dieser Funktion NICHT. Der Nutzer sah deshalb Typ-Nummern
                # statt Item-Namen ("16656, 16660, 16667") und konnte mit
                # der Warnung nichts anfangen.
                # ALLE NAMEN, NICHT DIE ERSTEN DREI (Sitzung 16): waehrend
                # einer Materialsuche stand ausgerechnet das gesuchte Item
                # hinter den drei Punkten, der Nutzer hat es nicht gesehen.
                # Eine Warnung, die den entscheidenden Namen verschweigt, ist
                # keine. Das Label bricht um.
                _erste = ", ".join(
                    str((names or {}).get(_t) or _t)
                    for _t, *_ in _fehl_auto)
                _zeilen_info.append(
                    "\u26a0 " + t("{n} materials will be missing for the "
                                  "remaining runs: {items}").format(
                        n=_n_f, items=_erste))
                # FUER DIE TABELLE MERKEN: die Zeile des Materials soll den
                # Live-Fehlbedarf selbst tragen, nicht nur der Banner oben.
                self._bd_fehl_live = {int(_t): (int(_f or 0), int(_da or 0))
                                      for _t, _f, _rb, _da, *_ in _fehl_auto}
            else:
                self._bd_fehl_live = {}
            _verl_vor = getattr(self, "_bd_verlust", None) or {}
            if _verl_vor:
                _zeilen_info.append(
                    "\u26a0 " + t(
                        "{n} materials were already covered and are missing "
                        "now \u2013 check „{action}“ in the tools menu."
                    ).format(n=len(_verl_vor),
                             action=t("Buy missing again")))
            _info_lbl.setText("\n".join(_zeilen_info))
            _info_lbl.setVisible(bool(_zeilen_info))
        # REST-BEDARF STATT GESAMT-BEDARF (Nutzer-Vorfall Sitzung 12).
        #
        # `buy` ist der Bedarf des GANZEN Plans, als finge man bei null an.
        # Wer die halbe Kette schon gebaut hat, liest dort weiter "noch 78
        # kaufen" - obwohl alles gedeckt ist. Genau das hat den Nutzer fast
        # zu unnoetigen Kaeufen gebracht.
        #
        # Die Zeilen-Mengen bleiben unveraendert (sie sind die Plan-Wahrheit),
        # aber der STATUS wird gegen den Rest-Bedarf gestellt: was fuer die
        # restlichen Runs gedeckt ist, meldet nicht mehr "kaufen".
        # `_fehlbedarf_jetzt` ist dieselbe Rechnung wie der Werkzeuge-Knopf -
        # zwei Wahrheiten waeren hier der schlimmste Ausgang.
        try:
            _rest_fehlt = {int(_r[0]): int(_r[1])
                           for _r in (self._fehlbedarf_jetzt() or [])}
            _rest_bekannt = True
        except Exception:
            _rest_fehlt, _rest_bekannt = {}, False
        buy = plan.get("buy") or {}
        stock_used = plan.get("stock_used") or {}
        build_runs = plan.get("build_runs") or {}
        surplus = plan.get("surplus") or {}
        _root = getattr(self, "_bd_type", None)
        excluded_hit = plan.get("excluded_hit") or set()
        never_hit = plan.get("never_build_hit") or set()
        # Items ohne echte Sell-Order am Hub - der Preis ist dort nur eine
        # Schaetzung. Kommt aus dem Plan, wird NICHT hier neu abgeleitet
        # (Arbeitsregel 9: eine Wahrheit, eine Stelle).
        _nicht_kaufbar = plan.get("nicht_kaufbar") or set()
        _recipes = getattr(self, "_bd_recipes", None)
        # Gebauter Netto-Anteil je Item: Runs x Ausstoß - Überschuss. Ohne den
        # log der Tab: bei einem Item, das teils aus Bestand kommt und teils
        # GEBAUT wird, war "Benötigt" = nur der Bestandsanteil -> exakt gleich
        # "Besitze" -> fälschlich "genug ✓", während der Runplaner korrekt den
        # ungedeckten Rest als Reaktions-/Bau-Runs einplante (gemeldeter Bug:
        # "Materialien sagt alles da, Runplaner will trotzdem bauen").
        built_net = {}
        for tid, runs in build_runs.items():
            if tid == _root:
                continue          # das Endprodukt selbst ist kein "Material"
            out_qty = 1
            if _recipes is not None:
                bp = _recipes.product_to_bp.get(tid)
                if bp:
                    out_qty = int(bp[2]) or 1
            net = int(runs) * out_qty - int(surplus.get(tid, 0) or 0)
            if net > 0:
                built_net[tid] = net
        try:
            _stage_map = industry.reaction_stage_map(_recipes) if _recipes else {}
        except Exception:
            _stage_map = {}
        _react_products = (getattr(_recipes, "reaction_products", None) or set()) \
            if _recipes else set()
        _CAT_ORDER = ["Intermediate Reactions", "Composite Reactions",
                     # de_scan2: aus  (Kategorie-SCHLUESSEL, Anzeige via _kategorie_anzeige)
                     "Komponenten", "H\u00fcllen", "Fuel", "Tools", "PI",
                     # de_scan2: an
                     t("Datacores and decryptors"),
                     # de_scan4: aus - interner SCHLUESSEL (Kategorie/Stufe/Dict), Anzeige uebersetzt woanders
                     "Mineralien", "Mond-Materialien", "Rohstoffe",
                     # de_scan4: an
                     # Markierung, keine Kategorie: Items, deren SDE-Gruppe
                     # (noch) fehlt. Eigener Kopf ganz unten, damit sie
                     # SICHTBAR bleiben (Arbeitsregel 6) statt faelschlich
                     # unter "Rohstoffe" zu stehen.
                     self.GRUPPE_UNBEKANNT]
        _CAT_RANK = {c: i for i, c in enumerate(_CAT_ORDER)}

        # EIGENE GRUPPEN fuer Fuel und Tools (Nutzer-Wunsch). Bisher landeten
        # Fuel Blocks und R.A.M. unter "Komponenten" - dabei sind es in der
        # Bau-Logik laengst eigene Kategorien (`_category_key` kennt
        # "fuel_blocks" und "tools"). Genau der Klassifizierer wird hier
        # wiederverwendet, statt eine zweite Einteilung zu erfinden.
        _catmap_disp = industry.item_category_map() or {}
        # Gruppen-Namen: derselbe Cache, den auch die Bau-Kategorien nutzen.
        _groups_disp = (getattr(self, "_bd_groups", None)
                        or getattr(self, "_bd_groups_cache", None) or {})

        def _category_for(tid):
            # EINE Wahrheit (Sitzung 20): die Einteilung steht seit dem Umbau
            # als `_bd_material_gruppe` an EINER Stelle - die Gruppen-Blacklist
            # im Bauplan benutzt genau dieselbe. Vorher lag sie nur hier als
            # geschachtelte Funktion; eine zweite Kopie waere ein zweiter
            # Wahrheitsstand gewesen.
            return self._bd_material_gruppe(
                tid, recipes=_recipes, groups=_groups_disp,
                stage_map=_stage_map, react_products=_react_products,
                catmap=_catmap_disp, inv_ids=_inv_ids)

        # INVENTION-MATERIAL (Datacores/Decryptoren): production_plan meldet
        # sie in EIGENEN Schluesseln, weil ihre Kosten bereits in `inv_cost`
        # stecken - sie duerfen nicht in `buy` landen, sonst zaehlt `mat_cost`
        # sie doppelt. Fuer die ANZEIGE sind sie aber ganz normales Material:
        # Bedarf, Bestand, Fehlmenge. Damit stehen sie automatisch auch im
        # Einkaufsfenster, das `self._bd_mat_rows` liest.
        _inv_buy = (plan or {}).get("inv_buy") or {}
        _inv_stock = (plan or {}).get("inv_stock_used") or {}
        _inv_ids = set(_inv_buy) | set(_inv_stock)
        all_ids = set(buy) | set(stock_used) | set(built_net) | _inv_ids
        rows = []
        # Die ZAHLEN dieser Funktion werden auch vom Einkaufsfenster gebraucht.
        # Sie dort aus den angezeigten Texten zurueckzulesen war ein Fehler:
        # die Tabelle kuerzt ("5.53M", "368.7k"), float() scheitert daran und
        # machte daraus 0 - im Fenster stand ueberall 0 (Nutzer-Screenshot).
        # Deshalb hier die Rohwerte hinterlegen (Arbeitsregel 9/10: dieselbe
        # Quelle, nicht die Anzeige davon).
        self._bd_mat_rows = rows
        # "WAR GEDECKT - JETZT FEHLEN X" (Nutzer-Vorfall Sitzung 12).
        # Der Nutzer hatte recht: wer einmal alles gekauft hat, KANN keinen
        # Fehlbedarf haben. Tritt trotzdem einer auf, ist es ein echter
        # Vorfall (weggeworfen, anderweitig verbaut) - und nur DANN darf die
        # Einkaufsliste ueberhaupt wieder wachsen.
        _verloren = {}
        # SPERRE BEI VERALTETEN JOB-DATEN.
        #
        # Die Verlust-Warnung ist nur so gut wie der Fortschritts-Stand. Weiss
        # die Rechnung nichts von schon gebauten Runs, haelt sie ALLE Runs fuer
        # offen - und meldet verbrauchtes Grundmaterial als "fehlt". Genau der
        # Fall, den der Nutzer beschrieben hat: "wenn ich ein Zwischenkomponent
        # gebaut habe, sind die Grundmaterialien weg, brauche sie aber nicht
        # mehr".
        #
        # Bei frischen Job-Daten stimmt die Rechnung (nachgerechnet: alle Runs
        # geliefert -> Grundmaterial wird NICHT mehr gebraucht, keine Warnung).
        # Sind die Daten alt, wird lieber GESCHWIEGEN als falsch gewarnt: ein
        # Fehlalarm sieht genauso aus wie ein echter Verlust und wuerde den
        # Nutzer zu unnoetigen Kaeufen bringen.
        import time as _t_frisch
        _jobs_ts = float(getattr(self, "_bd_jobs_ts", 0) or 0)
        _jobs_frisch = bool(_jobs_ts) and (_t_frisch.time() - _jobs_ts) < 600
        try:
            from eve_trader.ui.mw_helpers import war_gedeckt_status
            _gd_alt = set(getattr(self, "_bd_covered_once", None) or ())
            _neu_gd, _verl_roh = war_gedeckt_status(
                _rest_fehlt, _gd_alt, list(all_ids))
            if _rest_bekannt:
                self._bd_covered_once = _gd_alt | _neu_gd
            # ZWEI HUERDEN, gegen zwei verschiedene Fehlalarme:
            #  1) JOB-DATEN FRISCH? Sonst haelt die Rechnung schon gebaute
            #     Runs fuer offen und meldet VERBRAUCHTES Material als weg.
            #  2) BESTEHT DER FEHLBETRAG LANGE GENUG? CCP cacht Assets bis
            #     zu einer Stunde - frisch gekauftes Material ist in ESI noch
            #     nicht sichtbar und saehe sonst aus wie ein Verlust.
            #     Ein Fehlalarm direkt nach dem Einkauf wuerde zum
            #     Doppelkauf verleiten - genau das, was der Nutzer nicht will.
            from eve_trader.ui.mw_helpers import verlust_stabil
            _verl_stab, _seit_neu = verlust_stabil(
                _verl_roh if _jobs_frisch else {},
                getattr(self, "_bd_verlust_seit", None) or {},
                _t_frisch.time())
            self._bd_verlust_seit = _seit_neu
            _verloren = _verl_stab
        except Exception:
            _verloren = {}          # Anzeige, nie kritisch
        # Fuer den Nachkauf-Knopf merken: NUR echte Verluste, nie der
        # gewoehnliche Rest-Bedarf. Sonst waere der Knopf ein Weg, die
        # Einkaufsliste doch wieder wachsen zu lassen - genau das, was der
        # Nutzer nicht will.
        self._bd_verlust = dict(_verloren)
        for tid in all_ids:
            missing = (buy.get(tid, 0) or 0) + (_inv_buy.get(tid, 0) or 0)
            used = (stock_used.get(tid, 0) or 0) + (_inv_stock.get(tid, 0) or 0)
            built = built_net.get(tid, 0) or 0
            total = missing + used + built
            if total <= 0:
                continue
            has_recipe = False
            if _recipes is not None:
                has_recipe = (tid in _recipes.product_to_bp
                             or tid in (getattr(_recipes, "reaction_products", None) or ()))
            reason = None
            # GRUND-KENNUNG statt Emoji-Praefix (Sitzung 16): frueher stand
            # vor dem Text ein Zeichen (\U0001F6AB / \U0001F527), an dem die
            # Faerbung weiter unten haengt. Mit dem Emoji-Umbau fiel es weg
            # und die Faerbung griff ins Leere. Die Kennung ist unsichtbar
            # und uebersteht jede Uebersetzung.
            grund_art = None
            if tid in excluded_hit:
                grund_art = "blacklist"
                reason = t("On the blacklist (\u201ealready have it\u201c, recipe "
                           "structure tab) - therefore NEVER built, not even with "
                           "\u201eBuild everything yourself: ON\u201c. Untick it there to make "
                           "it buildable again.")
            elif tid in never_hit:
                grund_art = "kein_bp"
                reason = t("Blueprint category in \u201eMy blueprints\u201c (recipe "
                           "structure tab) not marked as owned - the tool assumes you do "
                           "not have the blueprint/reaction formula and therefore buys, "
                           "even with \u201eBuild everything yourself: ON\u201c (cannot build "
                           "what you do not own). If you really have it: tick the matching "
                           "category there.")
            elif not has_recipe:
                reason = t("No recipe of its own in the SDE (real raw material/commodity) "
                           "- cannot be built, MUST be bought.")
                if tid in _nicht_kaufbar:
                    # SCHLIMMSTER FALL: nicht kaufbar UND nicht baubar. Das
                    # muss der Nutzer VOR dem Einkauf sehen, nicht vor dem
                    # leeren Marktfenster.
                    reason += t("\n\u26d4 AND there is no sell order for it at the chosen "
                                "hub. The price above is an estimate (ESI average), not an "
                                "offer - you will not be able to buy it there.")
            elif tid in _nicht_kaufbar:
                # AM HUB NICHT KAUFBAR (Nutzer, Sitzung 14: "aber mit vermerk
                # dazu in Rezeptstruktur sollte etwas stehen"). Ohne den
                # Vermerk staende hier ploetzlich BAUEN, ohne erkennbaren
                # Grund - und beim naechsten Scan, wenn wieder Orders da
                # sind, waere es stillschweigend wieder KAUFEN.
                reason = t("There is NO sell order for this item at the chosen "
                           "hub. The plan therefore builds it itself instead of planning a "
                           "purchase you could not make.\nThe price in the cost is an "
                           "estimate (ESI average), not an offer. As soon as someone sells "
                           "at the hub again, the normal cost comparison decides.")
            _si = src_map.get(tid) or {}
            _used_q = stock.get(tid, 0) or 0
            rows.append({"tid": tid, "name": names.get(tid, f"#{tid}"),
                        "total": total, "owned": _used_q,
                        "missing": missing, "built": built, "reason": reason,
                        "grund_art": grund_art,
                        "category": _category_for(tid),
                        # Herkunfts-Bausteine: ohne src_map fällt alles auf
                        # „ESI" zurück (kein erfundener Einfüge-Wert).
                        "src": _si.get("src", "esi"),
                        "q_esi": int(_si.get("esi", _used_q) or 0),
                        "q_manual": _si.get("manual"),
                        "q_job": int(_si.get("job", 0) or 0)})
        rows.sort(key=lambda r: (_CAT_RANK.get(r["category"], 99),
                                 -r["missing"], r["name"]))
        # Daten fuer die Deckungs-Balken; angehaengt wird erst nach
        # setSortingEnabled(), weil das Sortieren Zell-Widgets verwirft.
        _bar_data = {}
        # GRUPPEN nach Kategorie, in der Reihenfolge der Produktionskette.
        tbl.clear()
        tbl.setHeaderLabels([t("Material"), t("Category"), t("Required"),
                             t("Owned"), t("Pasted"), t("Missing"),
                             t("Status")])
        _groups, _gstat = {}, {}

        def _baubereit(tid):
            """True, wenn die Zutaten fuer die geplanten Runs dieses Items
            JETZT im Bestand liegen - dann kann der Job sofort starten.

            Nutzer-Wunsch (Sitzung 8): "wenn wir genuegend Materialien haben
            um die fehlenden Komponenten zu bauen, soll 'kann gebaut werden'
            stehen und gruen sein" - und auf Nachfrage: "es soll GENAU
            passen, ich will so guenstig wie moeglich bauen". Deshalb wird
            gegen `plan["build_mats"]` geprueft - die EXAKTEN Mengen (inkl.
            ME, je Job gerundet), mit denen der Plan selbst rechnet. EINE
            Quelle (Arbeitsregel 9), nichts nachgebaut, nichts doppelt.
            Grenze der Zusage: haengt eine Zutat SELBST am Bau (Ferrogel
            wartet auf Ferrofluid), ist das Item NICHT startbereit - gruen
            darf nichts versprechen, was erst nach einem anderen Job stimmt
            (genau die Kette des Ferrofluid-Vorfalls)."""
            mats = (plan.get("build_mats") or {}).get(tid)
            if not mats:
                return False
            # NUTZER-VORFALL (Sitzung 8, 805 Ferrogel): der Gesamtbestand
            # enthaelt den PIPELINE-Anteil (laufende/fertige, noch nicht
            # abgelieferte Jobs) - fuer die Einkaufsliste richtig ("ein
            # laufender Run ist ein Run"), fuer die SOFORT-Start-Zusage
            # falsch: der Reaktor-Inhalt liegt nicht im Hangar. Ingame stand
            # 830/1'635, das Tool sagte "genug". Die Zusage rechnet deshalb
            # NUR mit dem, was wirklich im Lager liegt.
            _virt = getattr(self, "_bd_virt_stock", None) or {}
            for m, jq in mats:
                if build_runs.get(m):
                    return False          # Zutat haengt selbst am Bau
                _lager = (int(stock.get(m, 0) or 0)
                          - int(_virt.get(m, 0) or 0))
                if _lager < jq:
                    return False
            return True

        for _c in _CAT_ORDER:
            if not any(r["category"] == _c for r in rows):
                continue
            _g = QTreeWidgetItem(tbl, [self._kategorie_anzeige(_c),
                                       self._kategorie_anzeige(_c), "", "", "", "", ""])
            # SCHLUESSEL AM KNOTEN: der Fortschrittsbalken schlug die Gruppe
            # ueber text(0) nach - seit die Anzeige uebersetzt ist, ist das
            # nicht mehr der Schluessel. Der Schluessel haengt als Daten dran.
            _g.setData(1, Qt.UserRole, _c)
            _gf = _g.font(0); _gf.setBold(True); _g.setFont(0, _gf)
            _g.setForeground(0, QColor(theme.CYAN))
            _groups[_c] = _g
            _gstat[_c] = [0, 0, 0.0, 0.0]      # gedeckt, gesamt, ist, soll
        n_missing = 0
        n_built = 0
        for i, r in enumerate(rows):
            owned = r["owned"]
            built = r.get("built", 0)
            # NOCH ZU BAUEN statt URSPRUENGLICH GEPLANT (Sitzung 13).
            # `built` stammt aus plan["build_runs"] und ist bei EINGEFRORENEN
            # Plaenen der Stand vom Einfrier-Tag. `owned` ist live. Der Reiter
            # zeigte deshalb "Rest wird gebaut 7'321", waehrend zwei Spalten
            # weiter links 3'700 besessen und 3'661 fehlend standen - zwei
            # Zahlen fuer dieselbe Sache auf EINEM Bildschirm (Nutzer-Fund
            # mit Screenshot). Gerechnet wird jetzt aus DENSELBEN Zahlen wie
            # die MISSING-Spalte, damit die Zeile in sich stimmt.
            _noch_bauen = max(0, int(r["total"]) - int(owned))
            if not stock:
                have_txt = t("\u23f3 loading \u2026")
                have_col = theme.MUTED
                status_txt, status_col = t("Subtract assets needed"), theme.MUTED
            elif r["missing"] <= 0 and built <= 0:
                have_txt = f"{int(owned):,}".replace(",", "'")
                have_col = theme.GREEN
                _virt_n = int(_virt_tab.get(r["tid"], 0) or 0)
                if _virt_n > 0:
                    # NUTZER-VORFALL (805 Ferrogel): "genug" stimmte nur
                    # inklusive Pipeline - im Hangar lagen 830 von 1'635.
                    # Ehrlich trennen: gedeckt ja, aber X davon stecken noch
                    # in laufenden/fertigen Jobs und liegen erst nach der
                    # ABLIEFERUNG im Hangar. Ausserdem landet der Output der
                    # Reaktionen in der REAKTIONS-Struktur - ggf. umziehen.
                    status_txt = t("enough \u2713 \u00b7 {n} of them in build").format(
                        n=f"{min(_virt_n, int(owned)):,}".replace(",", "'"))
                    status_col = theme.CYAN
                    r["reason"] = t("Covered \u2013 but {n} units are still in running/"
                                    "finished jobs (pipeline) and only land in the hangar "
                                    "after delivery. For the SHOPPING LIST that rightly "
                                    "counts (nothing to rebuy!); for the JOB START it has "
                                    "to be delivered first and possibly moved to the build "
                                    "structure.").format(
                        n=f"{min(_virt_n, int(owned)):,}".replace(",", "'"))
                else:
                    status_txt = t("enough \u2713")
                status_col = status_col if _virt_n > 0 else theme.GREEN
                if _virt_n <= 0:
                    status_txt, status_col = t("enough \u2713"), theme.GREEN
            elif r["missing"] <= 0:
                # nichts zu KAUFEN - aber der Rest über dem Bestand wird laut
                # Plan selbst GEBAUT (Runplaner). Vorher stand hier fälschlich
                # "genug ✓", weil der gebaute Anteil in "Benötigt" fehlte.
                have_txt = f"{int(owned):,}".replace(",", "'")
                have_col = theme.GREEN if owned > 0 else theme.MUTED
                # NUTZER-FUND: "Rest wird gebaut" klang so, als h\u00e4tte man
                # schon Bestand - bei owned=0 wird aber die GANZE Menge
                # gebaut, da ist kein "Rest".
                if _baubereit(r["tid"]):
                    # Zutaten liegen KOMPLETT im Bestand -> Job kann sofort
                    # starten. Helleres Gruen als "genug" (das hier ist eine
                    # Handlungs-Zusage, kein blosser Deckungs-Status).
                    status_txt = t("can be built \u2713 \u00b7 {n} units").format(
                        n=f"{int(_noch_bauen):,}".replace(",", "'"))
                    status_col = theme.GREEN_BRIGHT
                    r["reason"] = t("All ingredients for the planned runs are in stock "
                                    "NOW \u2013 the build job can be started right away "
                                    "(see run planner). Nothing to buy.")
                elif owned > 0:
                    status_txt = t("still to build \u00b7 {n} units").format(
                        n=f"{int(_noch_bauen):,}".replace(",", "'"))
                    status_col = theme.BLUE
                    r["reason"] = t("Stock covers part of it, the rest is BUILT per plan "
                                    "(see run planner) \u2013 nothing to buy here.")
                else:
                    status_txt = t("will be built \u00b7 {n} units").format(
                        n=f"{int(_noch_bauen):,}".replace(",", "'"))
                    status_col = theme.BLUE
                    r["reason"] = t("Built entirely per plan (see run planner) \u2013 "
                                    "nothing to buy, no stock needed.")
                n_built += 1
            elif _rest_bekannt and int(r["tid"]) not in _rest_fehlt:
                # FUER DIE RESTLICHEN RUNS GEDECKT. Der Gesamt-Bedarf oben
                # sagt zwar noch "es fehlt etwas", aber das bezieht sich auf
                # Runs, die laengst gebaut oder in der Bauschleife sind.
                # Hier steht deshalb, was WIRKLICH gilt - sonst kauft der
                # Nutzer nach, was er nicht braucht.
                have_txt = f"{int(owned):,}".replace(",", "'") if owned else "0"
                have_col = theme.GREEN
                status_txt = t("covered for the remaining runs \u2713")
                status_col = theme.GREEN
            elif int(r["tid"]) in _verloren:
                # WAR SCHON EINMAL GEDECKT und fehlt jetzt. Das ist eine
                # andere Aussage als "noch nicht gekauft": hier ist wirklich
                # etwas passiert (weggeworfen, anderweitig verbaut). Der
                # Nutzer soll das SEHEN und nicht mit einem gewoehnlichen
                # Kauf-Posten verwechseln - nur an dieser Stelle darf die
                # Einkaufsliste ueberhaupt wieder wachsen, und auch dann nur
                # auf seinen Klick ("gekauft ist gekauft").
                have_txt = f"{int(owned):,}".replace(",", "'") if owned else "0"
                have_col = theme.AMBER
                status_txt = t("was covered \u2013 {n} missing now").format(
                    n=f"{int(_verloren[int(r['tid'])]):,}".replace(",", "'"))
                status_col = theme.RED
                n_missing += 1
            elif owned > 0:
                # teilweise vorhanden - ein Teil ist "gratis" (Bestand), der Rest
                # muss noch dazugekauft werden. Eigene Farbe (Orange), damit klar
                # ist: nicht bei NULL, nur eben nicht ganz genug.
                have_txt = f"{int(owned):,}".replace(",", "'")
                have_col = theme.GREEN
                status_txt = t("partly \u2013 {n} still to buy").format(
                    n=f"{int(_rest_fehlt.get(int(r['tid']), r['missing'])):,}"
                      .replace(",", "'"))
                status_col = theme.AMBER
                n_missing += 1
            else:
                # komplett nichts davon vorhanden (oder außerhalb der verknüpften
                # Bau-/Reaktions-Struktur bzw. -Charaktere, siehe Info-Text oben).
                have_txt = "0"
                have_col = theme.RED
                status_txt = t("missing completely \u2013 buy {n}").format(
                    n=f"{int(r['missing']):,}".replace(",", "'"))
                status_col = theme.RED
                n_missing += 1
            if r.get("grund_art") == "blacklist":
                # Blacklist ist der einzige Grund, den "Alles selbst bauen" NICHT
                # überstimmen kann - eigene, klar sichtbare Farbe statt normalem Rot.
                status_txt = t("on blacklist \u2013 never built")
                status_col = theme.VIOLET
            elif r.get("grund_art") == "kein_bp":
                # "Meine Blueprints"-Kategorie nicht als besessen markiert - auch
                # das überstimmt "Alles selbst bauen" nicht (kann ja nicht ohne
                # eigene Blaupause bauen). Eigene Farbe (Cyan), damit man's von
                # Blacklist UND von "wirklich kein Rezept" unterscheiden kann.
                status_txt = t("Blueprint not marked as owned")
                status_col = theme.CYAN
            # ---- Herkunft getrennt ausweisen (Nutzer-Kernwunsch) -----------
            # Bisher stand hier EINE Spalte „Besitze", in der der eingefügte
            # Wert den ESI-Wert still überschrieb. Jetzt: beide Quellen als
            # eigene Spalten, die tatsächlich benutzte fett/farbig, die
            # abgelöste gedämpft - und „Genutzt" als die Zahl, mit der der
            # Plan rechnet (inkl. Pipeline aus laufenden/fertigen Jobs).
            _is_manual = (r.get("src") == "manuell")
            _q_esi, _q_man, _q_job = r["q_esi"], r.get("q_manual"), r["q_job"]
            if not stock:
                esi_txt, man_txt = "\u23f3 \u2026", "\u23f3 \u2026"
            else:
                esi_txt = f"{int(_q_esi):,}".replace(",", "'")
                man_txt = ("\u2013" if _q_man is None
                           else f"{int(_q_man):,}".replace(",", "'"))
            _dim, _act = QColor(theme.MUTED), QColor(theme.CYAN)
            esi_col = _dim if (_is_manual or not _q_esi) else QColor(theme.TEXT)
            man_col = _act if _is_manual else _dim
            _job_hint = ""
            if _q_job:
                _job_hint = (
                    "\n\u2795 " + t("{n} units from running/finished jobs (pipeline) - "
                                     "they ALWAYS count, whichever source wins (job "
                                     "output is in no hangar).").format(
                        n=f"{int(_q_job):,}".replace(",", "'")))
            esi_tip = ((t("Frozen state, merged with the live stock (max per item).")
                        if _is_frozen else
                        t("Hangar stock per ESI in the chosen scope."))
                       + (t("\nCurrently NOT used \u2013 the pasted stock is newer.")
                          if _is_manual else t("\nThis source counts right now."))
                       + _job_hint)
            man_tip = (t("Pasted quantity (panel on the right).")
                       if _q_man is not None else
                       t("Nothing was pasted for this item."))
            if _q_man is not None:
                man_tip += (t("\nThis source counts right now.") if _is_manual else
                            t("\nSuperseded \u2013 the ESI data is fresher. Can be "
                              "forced with \u201ePermanent\u201c."))
            man_tip += _job_hint
            _src_word = (t("pasted") if _is_manual
                         else (t("frozen+live") if _is_frozen else "ESI"))
            _src_qty = int(_q_man or 0) if _is_manual else int(_q_esi)
            used_tip = (t("The plan calculates with this.\nSource: ") + _src_word
                        + " (" + f"{_src_qty:,}".replace(",", "'") + ")"
                        + _job_hint)
            # FEHLT statt GENUTZT (Nutzer: "ich will wissen, wie viele
            # Materialien mir fehlen"). "Genutzt" wiederholte im Wesentlichen
            # den Bestand; die offene Menge musste man sich aus Benoetigt
            # minus Bestand selbst ausrechnen.
            _missing_q = max(0, int(r["total"]) - int(_src_qty))
            miss_txt = ("\u2013" if _missing_q <= 0
                        else f"{_missing_q:,}".replace(",", "'"))
            # DIE FARBE FOLGT DER AUSSAGE (Sitzung 17, Nutzer: "es sieht auf
            # den ersten Blick so aus, als haette ich nicht alles - dabei
            # habe ich es, weil ich es noch bauen werde"). Die Spalte rechnet
            # stur Benoetigt minus Bestand; was der Plan SELBST baut, stand
            # deshalb bernsteinfarben da, obwohl nichts zu kaufen ist.
            # GEDECKT = gruen, egal ob aus dem Bestand oder aus Eigenbau.
            # Bernstein/Rot bleibt dem vorbehalten, was wirklich fehlt.
            _gedeckt = status_col in (theme.GREEN, theme.GREEN_BRIGHT, theme.BLUE)
            if _missing_q <= 0:
                miss_col = theme.MUTED
            elif _gedeckt:
                miss_col = theme.GREEN
            else:
                miss_col = theme.AMBER
            used_tip = (t("What still has to be procured after deducting your stock "
                          "(buy or build).\n")
                        + t("Required ") + f"{int(r['total']):,}".replace(",", "'")
                        + " \u2212 " + _src_word + " "
                        + f"{_src_qty:,}".replace(",", "'")
                        + " = " + f"{_missing_q:,}".replace(",", "'")
                        + _job_hint)
            # GROSSE ZAHLEN KUERZEN (Nutzer): 21'957'687 -> 21.96M. Der
            # exakte Wert steht im Tooltip der jeweiligen Zelle, es geht also
            # keine Information verloren.
            _exact = {}

            def _sq(_v, _col):
                _exact[_col] = f"{int(_v):,}".replace(",", "'")
                return self._short_qty(_v)
            # LIVE-FEHLBEDARF IN DER ZEILE SELBST (Sitzung 16).
            # Der eingefrorene Bestand zeigt max(eingefroren, live) - das ist
            # richtig fuer den EIGENEN Verbrauch (die Einkaufsliste darf nicht
            # wieder aufreissen). Aber jeder Schwund DANACH versteckt sich
            # dahinter, egal woher er kommt: anderer Plan, anderer Charakter,
            # in einen Contract gelegt. Der Anlassfall war Letzteres - die
            # Zeile sagte "noch zu bauen 4'730", waehrend im Hangar 96 lagen,
            # und der Nutzer suchte stundenlang. Deshalb traegt die Zeile den
            # LIVE-Stand mit, wenn er den Bedarf nicht deckt - rot, nicht zu
            # ueberlesen.
            _fl = (getattr(self, "_bd_fehl_live", None) or {}).get(int(r["tid"]))
            if _fl and _fl[0] > 0:
                status_txt = (t("\u26a0 LIVE: only {da} on hand \u2013 {fehlt} missing "
                                "for the remaining runs").format(
                    da=f"{_fl[1]:,}".replace(",", "'"),
                    fehlt=f"{_fl[0]:,}".replace(",", "'"))
                              + "  \u00b7  " + status_txt)
                status_col = theme.RED
            # WIEVIEL DAVON IST SCHON VERGEBEN? (Nutzer, Sitzung 19)
            # In der Spalte OWNED stand der ROHE Bestand, in der roten
            # LIVE-Zeile daneben der Bestand NACH Abzug der Reservierungen
            # anderer Plaene - "1'266 vorhanden" und "only 0 on hand"
            # nebeneinander. Beide Zahlen stimmen, der Widerspruch war nur
            # nicht erklaert. Reine Anzeige: an der Deckungslogik und an der
            # Einkaufsliste aendert sich NICHTS (dort gilt weiter "gekauft
            # ist gekauft"; verbaute Grundmaterialien duerfen nicht wieder
            # auf die Liste).
            _res_row = int((getattr(self, "_bd_reserved_applied", None)
                            or {}).get(int(r["tid"]), 0) or 0)
            _esi_zelle = (_sq(int(_q_esi), 3)
                          if esi_txt not in ("\u2013", "?") else esi_txt)
            if _res_row > 0 and 3 in _exact:
                # IN DEN TOOLTIP, NICHT IN DIE ZELLE (Nutzer, Sitzung 19).
                # Erst stand " (53.1k reserved)" in der Spalte - die ist zu
                # schmal, es wurde zu "53.1k (53.1k r...". Ein Emoji als
                # Kuerzel verbietet aa285 zu Recht. Der Tooltip traegt die
                # Zahl ungekuerzt, die Spalte bleibt lesbar.
                _exact[3] = _exact[3] + t(", of which {n} reserved by other "
                                          "build plans").format(
                    n=f"{_res_row:,}".replace(",", "'"))
            # UND WIEVIEL BESITZT DU INSGESAMT? (Nutzer, Sitzung 20:
            # "Tritanium 20'076'549 besitze ich - ich weiss nicht, woher
            # diese Zahlen im Tool kommen.") Die Spalte zaehlt nur, was an
            # den Strukturen DIESES Plans liegt; der Rest ist unsichtbar.
            # Dass eine Zahl kleiner ist als der eigene Besitz, muss die
            # Zeile sagen - sonst sieht es aus, als haette das Werkzeug den
            # Bestand verloren. Im Dialog gibt es die Unterscheidung
            # ("0 - not on site") laengst, hier fehlte sie.
            _ges_row = int((_besitz_gesamt or {}).get(int(r["tid"]), 0) or 0)
            if _ges_row > int(_q_esi) and 3 in _exact:
                _exact[3] = _exact[3] + t(
                    " \u2013 you own {n} in total, the rest is not at this "
                    "plan's structures").format(
                        n=f"{_ges_row:,}".replace(",", "'"))
            cells = [r["name"], self._kategorie_anzeige(r["category"]),
                    _sq(int(r["total"]), 2),
                    _esi_zelle,
                    man_txt,
                    _sq(_missing_q, 5) if _missing_q > 0 else miss_txt,
                    status_txt]
            # STATUS + KATEGORIE SORTIERBAR (Nutzer). Nach TEXT zu sortieren
            # waere sinnlos: "genug" kaeme vor "Rest wird gebaut", und
            # "Composite" vor "Intermediate" - die Kette stuende auf dem Kopf.
            # Deshalb NumericItem mit einem RANG.
            # Status-Reihenfolge wie gewuenscht: was fehlt zuerst, dann was
            # gebaut wird, zuletzt was gedeckt ist.
            # RANG AUS DER FARBE, NICHT AUS DEM TEXT (Sitzung 17). Vorher:
            # `"fehlt" in status_txt.lower()` - seit der Status uebersetzt ist,
            # fand das auf Englisch nichts ("partly - ... still to buy"), und
            # fehlendes Material rutschte beim Sortieren nach UNTEN. Die Farbe
            # traegt dieselbe Aussage in jeder Sprache.
            if status_col in (theme.RED, theme.AMBER, theme.VIOLET):
                _st_rank = 0          # muss beschafft werden -> nach oben
            elif status_col in (theme.BLUE, theme.GREEN_BRIGHT):
                _st_rank = 1          # laeuft ueber die eigene Produktion
            else:
                _st_rank = 2          # gedeckt -> nach unten
            _cells_out = []
            for col, text in enumerate(cells):
                if col == 1:
                    # Kategorie nach Ketten-RANG, nicht alphabetisch.
                    it = NumericItem(text, _CAT_RANK.get(r["category"], 99))
                elif col == 6:
                    # Leerer Text: der Balken traegt die Aussage, das Item
                    # nur den Sortier-Rang.
                    it = NumericItem("", _st_rank)
                    it.setData(Qt.UserRole, status_txt)
                else:
                    it = QTableWidgetItem(text)
                if col >= 2:
                    it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if col == 1:
                    it.setForeground(QColor(theme.MUTED))
                if col == 3:
                    it.setForeground(esi_col)
                    it.setToolTip(esi_tip)
                if col == 4:
                    it.setForeground(man_col)
                    if _is_manual:
                        _f = it.font(); _f.setBold(True); it.setFont(_f)
                    it.setToolTip(man_tip)
                if col == 5:
                    it.setForeground(QColor(miss_col))
                    if _missing_q > 0:
                        _f = it.font(); _f.setBold(True); it.setFont(_f)
                    it.setToolTip(used_tip)
                if col in _exact:
                    it.setToolTip((it.toolTip() + "\n" if it.toolTip() else "")
                                  + t("Exact: ") + _exact[col])
                if col == 6:
                    it.setForeground(QColor(status_col))
                    if r.get("reason"):
                        it.setToolTip(r["reason"])
                if col == 0:
                    it.setData(Qt.UserRole, r["tid"])
                    icon = self._table_icon(r["tid"])
                    if icon:
                        it.setIcon(icon)
                _cells_out.append(it)
            # Knoten an seine Kategorie-Gruppe haengen. Ohne passende Gruppe
            # kommt er auf die oberste Ebene - so verschwindet nie eine Zeile.
            _par = _groups.get(r["category"])
            _node = QTreeWidgetItem(_par if _par is not None else tbl)
            for _ci, _src_it in enumerate(_cells_out):
                _node.setText(_ci, _src_it.text())
                _node.setTextAlignment(_ci, _src_it.textAlignment())
                _node.setForeground(_ci, _src_it.foreground())
                _node.setFont(_ci, _src_it.font())
                if _src_it.toolTip():
                    _node.setToolTip(_ci, _src_it.toolTip())
            _node.setData(0, Qt.UserRole, r["tid"])
            _node.setData(6, Qt.UserRole + 1, _st_rank)
            _ic0 = self._table_icon(r["tid"])
            if _ic0:
                _node.setIcon(0, _ic0)
            if _par is not None:
                _s = _gstat[r["category"]]
                _s[1] += 1
                if not _missing_q:
                    _s[0] += 1
                _s[2] += float(min(int(_src_qty), int(r["total"])))
                _s[3] += float(r["total"])
            # Daten fuer den Deckungs-Balken merken - angehaengt wird er
            # ERST NACH setSortingEnabled(), s. unten.
            _bar_data[int(r["tid"])] = (
                int(min(100, max(0, round(int(_src_qty)
                                          / max(1, int(r["total"])) * 100)))),
                status_txt, status_col, used_tip)
        tbl.setSortingEnabled(True)
        # DECKUNGS-BALKEN erst JETZT anhaengen (Nutzer: "weniger wie eine
        # Excel-Tabelle, mehr wie ein Spiel"). WICHTIG: nach
        # setSortingEnabled() - das sortiert die Zeilen um und verwirft dabei
        # gesetzte Zell-Widgets. Deshalb wird die Zeile ueber die Item-Id
        # gesucht statt ueber den Schleifenindex.
        from PySide6.QtWidgets import QProgressBar as _QPB

        def _apply_bars():
            """Deckungs-Balken (neu) an die Zeilen haengen.

            MUSS nach JEDEM Sortieren erneut laufen. Qt sortiert die ITEMS um,
            laesst die ZELL-WIDGETS aber an ihrem alten Zeilenindex stehen -
            danach zeigt der Balken die Aussage einer FREMDEN Zeile. Genau das
            ist passiert, als die Status-Spalte sortierbar wurde: der Nutzer
            sah "teilweise - noch 94 kaufen" neben einer Zeile, zu der
            "Rest wird gebaut - 7'699 Stk" gehoerte.
            Die Zuordnung laeuft ueber die type_id aus Spalte 0, nie ueber den
            Schleifenindex.
            """
            _nodes = []
            for _gi in range(tbl.topLevelItemCount()):
                _g = tbl.topLevelItem(_gi)
                _nodes.append(_g)
                for _ci in range(_g.childCount()):
                    _nodes.append(_g.child(_ci))
            for _node in _nodes:
                _tid0 = _node.data(0, Qt.UserRole)
                if _tid0 is None:
                    # GRUPPENZEILE: Fortschritt der ganzen Kategorie.
                    _s = _gstat.get(_node.data(1, Qt.UserRole) or _node.text(0))
                    if not _s or not _s[1]:
                        continue
                    _pct = int(min(100, max(0, round(
                        _s[2] / max(1.0, _s[3]) * 100))))
                    _stxt = t("{a} / {b} covered").format(a=_s[0], b=_s[1])
                    _scol = (theme.GREEN if _s[0] == _s[1]
                             else theme.AMBER if _s[0] else theme.RED)
                    _stip = t("{a} of {b} materials of this category are fully "
                              "covered.").format(a=_s[0], b=_s[1])
                else:
                    _d = _bar_data.get(_tid0)
                    if not _d:
                        continue
                    _pct, _stxt, _scol, _stip = _d
                _bar = _QPB()
                _bar.setRange(0, 100); _bar.setValue(_pct)
                _bar.setTextVisible(True); _bar.setFormat(_stxt)
                _bar.setFixedHeight(20)
                # Diese Balken entstehen auch NACH dem zentralen
                # Umbruch-Lauf neu (bei jedem Sortieren) - deshalb selbst
                # umbrechen, sonst zieht der Tooltip sich ueber die volle
                # Fensterbreite.
                _bar.setToolTip(t("{pct} % covered\n").format(pct=_pct) + _stip)
                self._wrap_tooltips(_bar)
                _bar.setStyleSheet(
                    f"QProgressBar{{background:rgba(255,255,255,0.05); "
                    f"border:none; border-radius:5px; color:{_scol}; "
                    f"font-size:11px; text-align:center;}}"
                    f"QProgressBar::chunk{{background:rgba(255,255,255,0.10); "
                    f"border-radius:5px;}}")
                tbl.setItemWidget(_node, 6, _bar)
        _apply_bars()
        # Nach jedem Klick auf eine Spaltenueberschrift neu zuordnen.
        _hdr_mat = tbl.header()
        # Auch hier: nur die EIGENE alte Verbindung loesen (disconnect()
        # ohne Argument toetet Qts internes Sortieren, s. Capital-Fund).
        _alt_mat = getattr(self, "_mat_bars_sort_slot", None)
        if _alt_mat is not None:
            try:
                _hdr_mat.sortIndicatorChanged.disconnect(_alt_mat)
            except (TypeError, RuntimeError):
                pass
        # WIEDEREINTRITTS-SCHUTZ (Sitzung 16): `_apply_bars` setzt fuer jede
        # Zeile ein Widget. Laeuft waehrenddessen erneut ein Sortier-Signal
        # ein, ruft es sich selbst - im Betrieb faellt das nicht auf (der
        # Nutzer klickt nicht schnell genug), im Testlauf mit
        # `processEvents()` schon: die b-Suite blieb an genau dieser Stelle
        # haengen. Kostet nichts und kann nur helfen.
        def _sort_slot(*_a):
            if getattr(self, "_mat_bars_laeuft", False):
                return
            self._mat_bars_laeuft = True
            try:
                _apply_bars()
            finally:
                self._mat_bars_laeuft = False

        self._mat_bars_sort_slot = _sort_slot
        _hdr_mat.sortIndicatorChanged.connect(self._mat_bars_sort_slot)
        # Startzustand: nach Kategorie gruppiert. Wer nach Status sortiert,
        # bekommt weiterhin "fehlt zuerst" - ein Klick auf "Kategorie" holt
        # die Gruppierung zurueck.
        # Sortiert INNERHALB der Gruppen - die Gliederung bleibt erhalten.
        tbl.sortByColumn(1, Qt.AscendingOrder)
        # ZUGEKLAPPT starten (Nutzer: "wegen Ueberflutung von Informationen").
        # Man sieht die Kategorien mit ihrem Fortschrittsbalken und klappt
        # gezielt auf, was einen interessiert - statt 51 Zeilen auf einmal.
        # WICHTIG: der Zustand pro Gruppe bleibt ueber "Neu berechnen"
        # erhalten, sonst waere jede Aenderung ein Rueckschritt.
        _open_before = getattr(self, "_bd_mat_open_groups", None)
        for _gi2 in range(tbl.topLevelItemCount()):
            _g2 = tbl.topLevelItem(_gi2)
            _g2.setExpanded(bool(_open_before) and _g2.text(0) in _open_before)

        def _remember_open(*_a):
            self._bd_mat_open_groups = {
                tbl.topLevelItem(_i).text(0)
                for _i in range(tbl.topLevelItemCount())
                if tbl.topLevelItem(_i).isExpanded()}
        if not getattr(self, "_bd_mat_expand_connected", False):
            tbl.itemExpanded.connect(_remember_open)
            tbl.itemCollapsed.connect(_remember_open)
            self._bd_mat_expand_connected = True
        # SPALTEN NUR ZEIGEN, WENN SIE ETWAS AUSSAGEN (Nutzer-Linie).
        # MUSS nach dem Aufbau von `rows` stehen - beim ersten Versuch stand
        # es im Kopfbereich und knallte als UnboundLocalError; der
        # Aufbau-Test hat es sofort gemeldet.
        # "Kategorie" ist Kontext, kein Wert. "Eingefuegt" ist ohne
        # Einfuegung eine Spalte voller Striche.
        # KATEGORIE WIEDER SICHTBAR (Nutzer: "Materialien-Tab wirkt
        # ueberladen, kann man nach Reaktionen/Komponenten aufteilen?").
        # Sichere Zwischenloesung statt Umbau auf einen Baum: die Zeilen sind
        # ohnehin schon nach Kategorie sortiert (s. rows.sort weiter oben) -
        # mit sichtbarer Spalte stehen gleichartige Materialien erkennbar
        # beieinander, ohne dass an Sortierung, Balken oder Einfuege-Panel
        # etwas geaendert werden muss.
        tbl.setColumnHidden(1, False)
        # setColumnHidden(False) stellt die FRUEHERE Breite wieder her - und
        # die kann 0 sein, wenn die Spalte vorher versteckt war. Dann waere
        # sie zwar "sichtbar", aber null Pixel breit (Nutzer: "es sieht alles
        # aus wie vorher"). Deshalb eine Mindestbreite erzwingen.
        if tbl.columnWidth(1) < 60:
            tbl.setColumnWidth(1, 165)
        tbl.setColumnHidden(4, not any(r.get("q_manual") is not None
                                       for r in rows))
        # `_autosize_once` ist auf QTableWidget zugeschnitten (rowCount).
        # Fuer den Baum die Spalten einmalig selbst bemessen.
        _sz_key = f"mat_tree_{id(tbl)}"
        if _sz_key not in self._sized and tbl.topLevelItemCount():
            for _c in range(tbl.columnCount()):
                tbl.resizeColumnToContents(_c)
                tbl.setColumnWidth(_c, max(tbl.columnWidth(_c) + 18, 80))
            self._sized.add(_sz_key)
        # STATUS-Spalte fuellt den Rest der Breite. Sie wird sonst nach INHALT
        # bemessen - und der Fortschrittsbalken ist ein Zell-WIDGET, das dabei
        # nicht mitzaehlt. Ergebnis war eine gequetschte Spalte, in der der
        # Text abgeschnitten wurde (Nutzer zog sie jedes Mal von Hand breit).
        # Nach _autosize_once gesetzt, sonst ueberschreibt das die Vorgabe.
        from PySide6.QtWidgets import QHeaderView as _QHV
        _mh = tbl.header()
        _mh.setSectionResizeMode(6, _QHV.Stretch)
        # Kein setMinimumSectionSize - s. Blueprints-Tab: es holt versteckte
        # Spalten zurueck. Stattdessen die Ausblendung danach bestaetigen.
        tbl.setColumnHidden(4, not any(r.get("q_manual") is not None
                                       for r in rows))
        if status_lbl is not None:
            if not stock:
                status_lbl.setText(t(
                    "\u2139 No stock data yet - \u201e Subtract assets\u201c above "
                    "normally runs automatically on opening."))
            else:
                _n_man = sum(1 for r in rows if r.get("src") == "manuell")
                _txt = t("{types} material types \u00b7 {buy} to buy \u00b7 {build} "
                         "will be built \u00b7 {stock} covered from stock \u2713").format(
                    types=len(rows), buy=n_missing, build=n_built,
                    stock=len(rows) - n_missing - n_built)
                # Herkunft NICHT verschweigen: wenn eingefügte Zahlen mitspielen,
                # muss das in der Kopfzeile stehen, nicht nur in den Spalten.
                if _n_man:
                    _txt += t(" \u00b7 {n} of them from PASTED stock").format(
                        n=_n_man)
                elif getattr(self, "_bd_manual_stock", None):
                    _txt += t(" \u00b7 pasted stock present, but superseded "
                              "(ESI data is fresher)")
                status_lbl.setText(_txt)
        return n_missing

    def _fill_bauplan_schedule(self, plan, names, type_id, qty, hdr, sub, tbl, bp_tbl=None,
                               bp_warn_lbl=None):
        from ..sprache import t as _txt   # `t` ist hier lokal belegt
        from PySide6.QtWidgets import QTableWidgetItem
        mfg_sel = set(self.settings.get("bau_build_chars", []) or [])
        react_sel = set(self.settings.get("bau_reaction_chars", []) or [])
        all_sel = mfg_sel | react_sel
        if not all_sel:
            hdr.setText(_txt("Tick characters in the setup (\u201eFor building\u201c / "
                             "\u201eFor reactions\u201c) + \u201eLoad skills\u201c, then the run "
                             "planner appears here."))
            sub.setText(""); tbl.clear()
            # Kalender-Zeit trotzdem aktuell halten (seriell, da keine Parallelität).
            self._bd_last_sched_seconds = self._serial_plan_seconds(plan, type_id)
            return
        recipes = getattr(self, "_bd_recipes", None)
        if not plan or not recipes:
            tbl.clear()
            self._bd_last_sched_seconds = self._serial_plan_seconds(plan, type_id)
            return
        slots_map = self.settings.get("bau_char_slots", {}) or {}
        free_map = self.settings.get("bau_char_free", {}) or {}
        skills_map = self.settings.get("bau_char_skills", {}) or {}
        cmap = {c["character_id"]: (c.get("character_name") or str(c["character_id"]))
                for c in store.list_characters()}
        sched_chars = []
        for cid in all_sel:
            mx = slots_map.get(str(cid)) or [1, 1]
            fr = free_map.get(str(cid))
            # BESETZTE SLOTS WERDEN IGNORIERT (Nutzer-Entscheid Sitzung 11:
            # "die besetzten slots sollen ignoriert werden").
            #
            # Vorher wurden hier die FREIEN Slots bevorzugt - geplant wurde
            # also
            # mit den FREIEN Slots vom letzten "Skills laden". Das hatte eine
            # Folge, die niemand wollte: `elig()` in schedule_build wirft
            # jeden Charakter mit weniger als EINEM Slot komplett aus der
            # Stufe. Wer gerade baute, hatte 0 freie Fertigungs-Slots und war
            # damit im Plan nicht mehr vorhanden - je weiter der Nutzer den
            # Plan abarbeitete, desto weniger Charaktere benutzte der Planer.
            # Sein Befund: drei Bau-Charaktere angekreuzt, alle neun
            # Komponenten landeten auf EINEM (nachgerechnet: 9,4 Tage, sein
            # Bildschirm zeigte 9 T 10 h 34 m - derselbe Fall).
            #
            # Der Plan laeuft ueber TAGE; die jetzt belegten Slots sind
            # laengst wieder frei, wenn die Stufe drankommt. Deshalb jetzt
            # immer das Maximum laut Skills. Die freien Slots gehen NICHT
            # verloren, sie stehen weiter im Tooltip der Zeile (Regel 6) -
            # sie steuern nur die Planung nicht mehr.
            sl = mx
            sk = skills_map.get(str(cid), {}) or {}
            # Skill-Keys als int normalisieren (gespeichert evtl. als str) – für den
            # Science-Skill-Lookup pro Item.
            sk_int = {}
            for _k, _v in sk.items():
                try:
                    sk_int[int(_k)] = int(_v or 0)
                except (TypeError, ValueError):
                    pass
            sched_chars.append({"id": cid, "name": cmap.get(cid, str(cid)),
                                "mfg_slots": sl[0], "reaction_slots": sl[1],
                                # MAXIMUM laut Skills mitfuehren (Sitzung 9).
                                # Seit Sitzung 11 ist `sl` selbst schon das
                                # Maximum - die Felder bleiben trotzdem, weil
                                # Anzeige und Rechnung getrennt lesbar sein
                                # sollen und _transform_schedule_result sie
                                # weiterreicht.
                                "mfg_slots_max": mx[0],
                                "reaction_slots_max": mx[1],
                                # NUR FUER DIE ANZEIGE: was war beim letzten
                                # "Skills laden" frei? Steuert nichts mehr.
                                "frei_slots": tuple(fr) if fr else (),
                                "can_mfg": cid in mfg_sel, "can_react": cid in react_sel,
                                "mfg_time": (industry.skill_time_factor(sk, False)
                                            * self._char_implant_mfg_mult(cid)),
                                "react_time": industry.skill_time_factor(sk, True),
                                "all_skills": sk_int})
        # Hinweis, falls Reaktions-Chars gewählt sind, aber die gespeicherten Skills
        # den Reactions-Skill (45746) noch nicht kennen (z.B. nach einem Update mit
        # neuer Skill-ID). Dann fehlt der Reaktions-Zeitbonus -> Zeiten zu lang.
        self._bd_react_skill_missing = False
        if react_sel:
            # SCHLUESSEL-TYP IST NICHT VERLASSBAR (Nutzer-Befund Sitzung 9:
            # "ich habe auf Skills laden gedrueckt und die Warnung
            # verschwindet nicht"). Frisch von ESI geladen sind die
            # Skill-IDs INTs, nach einem Neustart aus der JSON-Datei
            # STRINGS. Die Pruefung verglich nur gegen str(45746) - direkt
            # nach "Skills laden" fand sie den Skill also NIE und die
            # Warnung blieb stehen, obwohl alles geladen war. Genau
            # deshalb normalisiert der Code ein paar Zeilen weiter oben
            # ebenfalls auf int; hier fehlte es.
            def _hat_react(_cid):
                _sk = skills_map.get(str(_cid)) or skills_map.get(_cid) or {}
                for _k in _sk:
                    try:
                        if int(_k) == 45746:
                            return True
                    except (TypeError, ValueError):
                        continue
                return False
            if not any(_hat_react(cid) for cid in react_sel):
                self._bd_react_skill_missing = True
        te = (getattr(self, "_bd_opts", None) or {}).get("te_factor", 1.0)
        _groups = getattr(self, "_bd_groups", {}) or {}
        _mfg_struct = getattr(self, "_bd_mfg_struct", None)
        _react_struct = getattr(self, "_bd_react_struct", None)
        _sci_map = industry.bp_science_skills_map()   # bp_id -> set(science_skill_id)
        # Flag: fehlen die Science-Skill-Daten ganz (alte SDE ohne die neue Tabelle)?
        # Dann fehlt der item-spezifische Zeitbonus -> Fertigungszeiten etwas zu lang.
        self._bd_science_data_missing = not _sci_map
        # Stufen-Map (1=Intermediate, 2=Composite) - jetzt schon gebraucht, um
        # jeden Reaktions-Job mit seiner Stufe zu taggen (für die zwei
        # getrennten, nacheinander laufenden Reaktions-Phasen im Scheduler).
        try:
            _stage_map_rp = industry.reaction_stage_map(self._bd_recipes)
        except Exception:
            _stage_map_rp = {}
        jobs = []
        for _tid, runs in plan.get("build_runs", {}).items():
            if runs < 1:
                continue
            bp = recipes.product_to_bp.get(_tid)
            if not bp:
                continue
            bp_id, activity, _oq = bp
            base_t = recipes.activity_time.get((bp_id, activity), 0) or 0
            _sci = _sci_map.get(bp_id, set())
            # STRUKTUR JE STUFE (Sitzung 9, Simurgh): vorher bekam JEDER
            # Fertigungs-Job die Komponenten-Struktur - auch das Endprodukt.
            _s_item = self._bau_struct_fuer_item(
                _tid, recipes.reaction_products, _stage_map_rp, type_id)
            _tef = self._bau_category_te_factor(
                _tid, _groups, recipes.reaction_products, type_id,
                mfg_struct=_s_item or _mfg_struct,
                react_struct=_s_item or _react_struct)
            jobs.append({"tid": _tid, "name": names.get(_tid, f"#{_tid}"), "runs": runs,
                         "activity": activity, "base_time": base_t,
                         "is_end": (_tid == type_id), "bp_id": bp_id,
                         "is_fuel": self._ist_fuel_block(_tid, _groups,
                                                         recipes.reaction_products),
                         "sci_skills": _sci,
                         "te_factor": _tef,
                         "reaction_tier": (_stage_map_rp.get(_tid, 2)
                                          if activity == industry.REACTION else None)})
        if bp_tbl is not None:
            try:
                # Für den Blueprints-Tab NICHT den kostenoptimierten Plan nehmen
                # (der zeigt nur, was gerade gekauft statt gebaut wird), und auch
                # NICHT production_plan(force_build=True) - das kann trotz "force"
                # noch einzelne Items als "kaufen" behandeln (z.B. wenn irgendein
                # Unter-Material weder bau- noch bepreisbar ist - eine
                # Sicherheitsbremse dort, die Vorrang vor "force" hat und dadurch
                # ganze Intermediate-Reaktionsketten aus der Liste kippen konnte).
                # Stattdessen: reiner Struktur-Durchlauf (full_build_chain), der
                # jedes Item mit eigenem Rezept bedingungslos "baut", komplett
                # unabhängig von Preisen - damit ist wirklich die KOMPLETTE
                # Rezept-Kette sichtbar. Der Runplaner selbst nutzt weiterhin die
                # echten, kostenoptimierten "jobs" oben - hier geht's nur um die
                # Übersichts-Tabelle.
                _force_opts = dict(getattr(self, "_bd_opts", None) or {})
                _bp_build_runs = industry.full_build_chain(
                    type_id, qty, recipes, _force_opts)
                # NAMEN NACHLADEN (Nutzer: "sind noch Zahlen statt Item-
                # namen"). `names` wird nur fuer PLAN-Items aufgeloest
                # (build_runs/buy/stock_used). full_build_chain enthaelt aber
                # auch Stufen, die der Plan gar nicht anfasst - deren IDs
                # blieben als "#17769" stehen. Ein Abruf fuer alle fehlenden
                # zusammen, nicht je Zeile.
                _bp_miss = [_i for _i in _bp_build_runs if _i not in names]
                if _bp_miss:
                    try:
                        names.update(esi.resolve_names(_bp_miss))
                    except Exception as _nm_err:
                        # Nicht still schlucken - sonst sucht man die "#"-Namen
                        # spaeter wieder im Rechenweg statt im Netz.
                        self._log_exception("Blueprints-Tab: Namen", str(_nm_err))
                _bp_jobs = []
                for _tid, runs in _bp_build_runs.items():
                    if runs < 1:
                        continue
                    bp = recipes.product_to_bp.get(_tid)
                    if not bp:
                        continue
                    bp_id, activity, _oq = bp
                    base_t = recipes.activity_time.get((bp_id, activity), 0) or 0
                    _sci = _sci_map.get(bp_id, set())
                    _s_item = self._bau_struct_fuer_item(
                        _tid, recipes.reaction_products, _stage_map_rp, type_id)
                    _tef = self._bau_category_te_factor(
                        _tid, _groups, recipes.reaction_products, type_id,
                        mfg_struct=_s_item or _mfg_struct,
                        react_struct=_s_item or _react_struct)
                    _bp_jobs.append({"tid": _tid, "name": names.get(_tid, f"#{_tid}"),
                                     "runs": runs, "activity": activity,
                                     "base_time": base_t, "is_end": (_tid == type_id),
                                     "bp_id": bp_id, "sci_skills": _sci,
                                     "is_fuel": self._ist_fuel_block(
                                         _tid, _groups, recipes.reaction_products),
                                     "te_factor": _tef,
                                     "reaction_tier": (_stage_map_rp.get(_tid, 2)
                                                       if activity == industry.REACTION
                                                       else None)})
                (_n_missing, _n_low, _n_missing_by_stage,
                 _n_low_by_stage) = self._fill_blueprint_tab(_bp_jobs, sched_chars,
                                                             recipes, bp_tbl)
            except Exception:
                # NICHT MEHR STUMM SCHLUCKEN. Genau dieses except hat den
                # Blueprints-Tab kaputt aussehen lassen, ohne dass irgendwo
                # etwas davon stand: die Fuell-Funktion brach mittendrin ab,
                # der Tab blieb halb leer, und der Nutzer fragte zu Recht
                # "welches Konsolenfenster?". Ab jetzt landet der Traceback
                # im Fehlerprotokoll (s. main.py) und ein Hinweis im Tab.
                import traceback as _tb
                _err = _tb.format_exc()
                try:
                    self._log_exception("Blueprints-Tab", _err)
                except Exception:
                    pass
                if bp_warn_lbl is not None:
                    bp_warn_lbl.setText(_txt(
                        "\u26a0 The Blueprints tab could not be built completely. "
                        "Details are in fehler.log next to the application."))
                    bp_warn_lbl.setStyleSheet(f"color:{theme.RED};")
                _n_missing, _n_low = 0, 0
                _n_missing_by_stage, _n_low_by_stage = {}, {}
            if bp_warn_lbl is not None:
                # Sitzung 17: ALLE Stufen, nicht nur drei (s. _bp_stufen_liste).
                _breakdown = self._bp_stufen_liste
                # Fehlt NUR das Endprodukt (keine Komponenten/Reaktionen) -> meist
                # normal, das T2-BPC wird ja meist erst NACH der Planung per
                # Invention erzeugt, nicht vorher schon besessen. Dezenter Hinweis
                # statt Alarm-Rot. Fehlen aber auch Komponenten/Reaktionen -> das
                # sind echte Engpässe, die man vor dem Bauen beheben muss -> Alarm.
                # de_scan4: aus - interner SCHLUESSEL (Kategorie/Stufe/Dict), Anzeige uebersetzt woanders
                _only_end_missing = (_n_missing and set(_n_missing_by_stage) <= {"Endprodukt"}
                # de_scan4: an
                                     and not _n_low_by_stage)
                if _n_missing and not _only_end_missing:
                    _word = (t("\u26a0 {n} item missing completely:") if _n_missing == 1
                             else t("\u26a0 {n} items missing completely:")).format(n=_n_missing)
                    _lines = _breakdown(_n_missing_by_stage)
                    # NICHT `_txt` NENNEN (Absturz-Fund Sitzung 14): das ist
                    # in dieser Funktion die UEBERSETZUNGSFUNKTION
                    # (`from ..sprache import t as _txt`, Zeile oben). Die
                    # Zuweisung machte daraus einen String - jeder spaetere
                    # `_txt(...)`-Aufruf riss den Bauplan mit
                    # "TypeError: 'str' object is not callable" ab. Der
                    # Nutzer stand mitten im Bauen davor, ausgeloest vom
                    # 10-Minuten-ESI-Lauf.
                    _warn_html = (_word + "<br>" + "<br>".join(_lines))
                    if _n_low:
                        _warn_html += ("<br>" + t("Also {n} too few: ").format(n=_n_low)
                                       + ", ".join(_breakdown(_n_low_by_stage)))
                    _warn_html += ("<br><span style='font-size:11px;'>"
                                   + t("Details in the Blueprints tab.")
                                   + "</span>")
                    bp_warn_lbl.setText(_warn_html)
                    bp_warn_lbl.setStyleSheet(
                        f"background:rgba(226,54,54,0.12); color:{theme.RED}; "
                        f"border:1px solid {theme.RED}; border-radius:6px; "
                        f"padding:6px 10px; font-weight:600;")
                    bp_warn_lbl.setVisible(True)
                elif _only_end_missing:
                    bp_warn_lbl.setText(_txt(
                        "\u2139 End product blueprint ({n}) still missing - normal if you "
                        "create the T2 BPC via invention only AFTER planning."
                    # de_scan4: aus - interner SCHLUESSEL (Kategorie/Stufe/Dict), Anzeige uebersetzt woanders
                    ).format(n=_n_missing_by_stage.get('Endprodukt', _n_missing)))
                    # de_scan4: an
                    bp_warn_lbl.setStyleSheet(
                        f"background:rgba(107,114,128,0.12); color:{theme.MUTED}; "
                        f"border:1px solid {theme.BORDER}; border-radius:6px; "
                        f"padding:6px 10px;")
                    bp_warn_lbl.setVisible(True)
                elif _n_low:
                    bp_warn_lbl.setText(
                        _txt("\u26a0 {n} item(s) have too few blueprint copies for the "
                             "fastest possible build:<br>").format(n=_n_low)
                        + "<br>".join(_breakdown(_n_low_by_stage))
                        + "<br><span style='font-size:11px;'>"
                        + _txt("Details in the Blueprints tab.") + "</span>")
                    bp_warn_lbl.setStyleSheet(
                        f"background:rgba(224,177,44,0.12); color:{theme.AMBER}; "
                        f"border:1px solid {theme.AMBER}; border-radius:6px; "
                        f"padding:6px 10px; font-weight:600;")
                    bp_warn_lbl.setVisible(True)
                else:
                    bp_warn_lbl.setVisible(False)
        if not jobs:
            hdr.setText(_txt("Nothing to build yourself (all bought?).")); sub.setText("")
            tbl.clear()
            return
        bpset = getattr(self, "_bd_bp", None) or {}

        def _cap(key, default=1):
            d = bpset.get(key) or {}
            return int(d.get("copies", default) or default)
        # Kapazitäts-Anzeige je Stufe (Kopien × Runs vs. größter Job) aktualisieren
        max_runs = {"end": 0, "component": 0, "reaction": 0}
        for j in jobs:
            st = ("reaction" if j["activity"] == industry.REACTION
                  else "end" if j.get("is_end") else "component")
            max_runs[st] = max(max_runs[st], int(j["runs"]))
        for key, lbl in (getattr(self, "_bd_bp_widgets", {}) or {}).items():
            d = bpset.get(key) or {}
            need = max_runs.get(key, 0)
            capw = lbl.get("cap")
            if not capw:
                continue
            if d.get("bpo"):
                capw.setText(_txt("\u221e \u00b7 largest job {need}").format(need=need))
                capw.setStyleSheet(f"color:{theme.GREEN};")
            else:
                cap = int(d.get("copies", 1)) * int(d.get("runs", 1))
                ok = cap >= need
                capw.setText(_txt("Cap. {cap} \u00b7 largest job {need}").format(cap=cap, need=need)
                             + ("" if ok else _txt(" \u26a0 not enough")))
                capw.setStyleSheet(f"color:{theme.GREEN if ok else theme.AMBER};")
        # „Selber aufteilen“: nur alle Runs je Item listen, ohne Charakter-Zuteilung.
        if bpset.get("manual"):
            self._fill_schedule_manual(jobs, recipes, names, hdr, sub, tbl, plan=plan)
            # Ohne Char-Zuteilung gibt es keine Parallelität -> serielle Zeit merken
            # (sonst behält der Kalender eine veraltete Zeit).
            self._bd_last_sched_seconds = self._serial_plan_seconds(plan, type_id)
            return
        res = industry.schedule_build(
            jobs, sched_chars, te_factor=te,
            mfg_bp=_cap("component"), react_bp=_cap("reaction"), end_bp=_cap("end"),
            fuel_ids={j["tid"] for j in jobs if j.get("is_fuel")},
            per_item_cap=self._resolve_per_item_bp_cap())
        # FORTSCHRITT AUS ESI-JOBS (nur eingefrorene Plaene, Nutzer-Spez
        # Punkt 2): gelieferte Runs seit dem Einfrieren je Item aufsummieren;
        # deckt die Summe die Plan-Runs, wird die Zeile automatisch abgehakt -
        # ueber DENSELBEN checked_runplan-Mechanismus wie die Hand-Haekchen
        # (EINE Wahrheit; nicht loeschen, sonst verliert man die Uebersicht,
        # was lief). _bd_runplan_auto traegt nur den Tooltip-Zusatz und wird
        # hier bei JEDEM Aufbau neu bestimmt (transient, nichts Gespeichertes).
        self._bd_runplan_auto = {}
        self._bd_runplan_delivered = {}
        self._bd_runplan_runs_by_key = {}
        # Fremde Reservierungen EINMAL je Aufbau (fuer die Job-Zuordnung).
        _fremd_res = self._fremde_reservierungen(
            self.settings, getattr(self, "_bd_open_plan_id", None))
        # Der EIGENE Anspruch: dieselbe Karte, die beim Speichern geschrieben
        # wird. Beansprucht dieser Plan das Item auch, gibt es keine Aussage -
        # dann bleibt der Lauf-Punkt stehen (Regel 3: lieber einer zu viel).
        try:
            _eigene_res = self._plan_reserve_map(
                (getattr(self, "_bd_plan_ref", None) or {}).get("plan") or {})
        except Exception:
            _eigene_res = {}
        _frz_sched = getattr(self, "_bd_frozen", None)
        if _frz_sched and _frz_sched.get("plan_snapshot") and _frz_sched.get("ts"):
            _auto_keys, _auto_runs = self._frozen_auto_checked(
                getattr(self, "_bd_delivered_jobs", None) or [],
                res["assignments"], float(_frz_sched["ts"]))
            # Geliefert-Stand JE ITEM auch fuer teilweise gelieferte merken -
            # der Nutzer will sehen "ESI hat 12 von 24 Runs gesehen", nicht
            # erst beim Vollstand ein Zeichen bekommen (Sitzung 8).
            self._bd_runplan_delivered = dict(_auto_runs or {})
            # NUTZER-ENTSCHEIDUNG (Sitzung 8): "nur ich darf streichen" -
            # Haekchen setzt AUSSCHLIESSLICH der Nutzer (das fruehere
            # Auto-Abhaken ist raus). ESI blendet stattdessen voll gedeckte
            # Items AUS: geliefert + in der Bauschleife laufend >= Plan-Runs
            # ("schon dass es aktiv gebaut wird soll reichen, damit der
            # Bauplan nach und nach kleiner wird"). AUSBLENDEN heisst NICHT
            # loeschen - der eingefrorene Plan bleibt intakt, und je Stufe
            # bleibt eine Zaehl-Zeile sichtbar (Regel 6). Teilweise gedeckte
            # Items bleiben stehen (ihre Rest-Runs waeren sonst unsichtbar).
            # HIER WURDE `_bd_runplan_hidden` BEFUELLT - ERSATZLOS ENTFERNT
            # (Sitzung 14). Es diente allein dem Ausblenden voll gedeckter
            # Positionen, und das ist per Nutzer-Ansage weggefallen
            # ("imprinzip wird nie etwas mehr ausgeblendet nurnoch gedimmt").
            # Die Zusage "laufende Jobs zaehlen zur Deckung, die Bauschleife
            # reicht" (Sitzung 8) gilt UNVERAENDERT weiter - sie steckt jetzt
            # in `_rest_budget` oben, das aus genau denselben Zahlen entsteht
            # (geliefert + laufend, gedeckelt auf die Plan-Runs).
            # Stehengeblieben waere es toter Code, der aussieht, als taete er
            # etwas.
        stt = res["stage_times"]; tot = res["total_seconds"]
        self._bd_last_sched_seconds = tot        # für den Bau-Kalender merken
        # Frisches Ergebnis auch für "Bauplan speichern" merken, damit der
        # Kalender-Nachfüll-Plan sofort dieselben Zuteilungen zeigt wie hier
        # im Runplaner-Tab - nicht erst nach dem nächsten (zeitversetzten)
        # Hintergrund-Recompute, der zu anderen/veralteten Werten führen kann.
        # Gleiche Transformation wie der Hintergrund-Recompute (geteilte
        # Funktion), sonst passen die Feldnamen nicht zur Kalender-Anzeige.
        (self._bd_last_assignments, self._bd_last_waves,
         self._bd_last_stage_times) = self._transform_schedule_result(res, sched_chars)
        react_total = stt.get("reaction_1", 0) + stt.get("reaction_2", 0)
        # Nutzer-Frage "wo steht die Gesamtzeit?": Bau-Durchlauf stand hier,
        # Invention nur im anderen Tab, Kopierzeit NIRGENDS. Jetzt eine Zeile:
        _needs_t = getattr(self, "_bd_invention_needs", None) or {}
        _inv_s = sum(int(i.get("inv_secs") or 0) for i in _needs_t.values())
        _cp_s = sum(int(i.get("copy_secs") or 0) for i in _needs_t.values())
        _extra_t = ""
        if _inv_s or _cp_s:
            _bits_t = []
            if _cp_s:
                _bits_t.append(_txt("Copying \u2248{d}").format(d=self._fmt_dur(_cp_s)))
            if _inv_s:
                _bits_t.append(_txt("Invention \u2248{d}").format(d=self._fmt_dur(_inv_s)))
            _extra_t = ("   \u00b7   " + _txt("plus ") + " + ".join(_bits_t)
                        + _txt(" (rough, sequential \u2013 runs parallel to the build)"))
        hdr.setText(_txt("Total (rough): {tot}   \u00b7   Reactions {react} \u2192 "
                         "Components {comp} \u2192 End product {end}").format(
            tot=self._fmt_dur(tot), react=self._fmt_dur(react_total),
            comp=self._fmt_dur(stt.get('component', 0)),
            end=self._fmt_dur(stt.get('end', 0))) + _extra_t)
        # Der Header zeigt bereits die Gesamtzeiten (Reaktionen → Komponenten →
        # Endprodukt). Die frühere „Zeit je Charakter“-Detailzeile war zu überladen
        # und wurde entfernt. Der Sub-Text ist jetzt für WARNUNGEN reserviert und
        # wird nur dann sichtbar/auffällig, wenn wirklich etwas fehlt.
        warns = []
        if getattr(self, "_bd_science_data_missing", False):
            warns.append(_txt("\u26a0 Science skill data missing \u2013 press \u201eLoad "
                              "recipes\u201c once (reload SDE), otherwise the manufacturing "
                              "times are too long."))
        if getattr(self, "_bd_react_skill_missing", False):
            warns.append(_txt("\u26a0 Reaction skill not loaded \u2013 press \u201eLoad skills "
                              "\u2192 Job slots\u201c, otherwise the reaction times are too "
                              "long."))
        if warns:
            sub.setText("\n".join(warns))
            sub.setStyleSheet(
                f"color:{theme.AMBER}; font-weight:700; font-size:13px; padding:4px 0;")
        else:
            sub.setText("")
            sub.setStyleSheet("")
        sd = {"fuel": t("Fuel"),
              "reaction_1": t("Reaction"), "reaction_2": t("Reaction"),
              "component": t("Component"), "end": t("End product")}
        _cat_short = {
            "intermediate_reactions": "Intermediate", "composite_reactions": "Composite",
            "hybrid_reactions": "Hybrid Poly", "biochemical_reactions": "Biochem",
            "molecular_reactions": "Molecular", "unrefined_reactions": "Unrefined",
            "reactions": _txt("Other"),
            "advanced_components": "Advanced", "capital_components": "Capital",
            "advanced_capital_components": "Adv. Capital", "hybrid_components": "Hybrid",
            "t1_hulls": _txt("T1 hull"), "fuel_blocks": "Fuel Block", "tools": "Tool",
        }
        _catmap_fine = industry.item_category_map() or {}
        # _stage_map_rp wurde schon weiter oben (vor dem jobs-Aufbau) berechnet.

        def _stufe_label(a):
            """Feinere Stufen-Anzeige. Bei Reaktionen wird zus\u00e4tzlich die STUFE
            (1 = geht in weitere Reaktion, 2 = geht in den Bau) gezeigt, konsistent
            mit der Rezept-Struktur \u2013 plus der Materialtyp (Composite etc.), damit
            klar ist, welche \u201eMeine Blueprints\u201c-Checkbox zust\u00e4ndig ist."""
            stage = a["stage"]
            if stage == "end":
                # de_scan4: aus - interner SCHLUESSEL (Kategorie/Stufe/Dict), Anzeige uebersetzt woanders
                return "Endprodukt"
                # de_scan4: an
            tid = a["tid"]
            is_react = stage.startswith("reaction")
            info = _catmap_fine.get(tid)
            cat = info[0] if info else None
            meta = info[2] if info else None
            key = self._category_key(tid, _groups.get(tid, ""), is_react, cat, meta)
            fine = _cat_short.get(key)
            base = sd.get(stage, stage)
            if is_react:
                # Die Stufe steht jetzt schon direkt im Stage-Namen (reaction_1/2) -
                # kein erneutes Nachschlagen nötig, das war vorher pro Item einzeln.
                st = 1 if stage == "reaction_1" else 2
                base = f"{base} \u00b7 " + t("stage {n}").format(n=st)
            return f"{base} \u00b7 {fine}" if fine else base
        from PySide6.QtWidgets import QTreeWidgetItem
        from collections import defaultdict as _dd
        import math as _math
        me_pct = float((getattr(self, "_bd_opts", None) or {}).get("me", 0))
        # Nach PHASE gruppieren (nicht nach Charakter) – so steht von oben nach
        # unten exakt die Reihenfolge, in der wirklich gebaut wird: erst ALLE
        # Intermediate-Reaktionen fertig, DANN Composite-Reaktionen (die brauchen
        # die Intermediate-Produkte als Zutat!), DANN Komponenten, DANN
        # Endprodukt. Innerhalb jeder Phase steht, wer was macht.
        by_stage_char = _dd(lambda: _dd(list))
        for a in res["assignments"]:
            by_stage_char[a["stage"]][a["char_id"]].append(a)
        # Überschuss (aus production_plan()) ist eine Eigenschaft des GANZEN
        # Items, nicht pro Charakter - wenn ein Item auf mehrere Charaktere
        # aufgeteilt ist (z.B. Titanium Chromide auf Elrasier UND Peanut
        # Motor), wird der Überschuss proportional zum jeweiligen Runs-Anteil
        # aufgeteilt, statt ihn irreführend bei JEDEM Charakter voll zu zeigen.
        _surplus_all = (plan or {}).get("surplus") or {}
        _runs_by_tid = _dd(float)
        for a in res["assignments"]:
            _runs_by_tid[a["tid"]] += float(a.get("runs", 0) or 0)
        # TEILWEISE GEBAUTE POSITIONEN: REST-RUNS STATT URSPRUNGSZAHL
        # (Sitzung 13, Nutzer-Fund mit Screenshot).
        #
        # VORFALL: eingefrorener Plan vom 28.08., Quantum Microprocessor.
        # Der Runplaner verlangte 7'321 Runs, obwohl der Materialien-Reiter
        # daneben 3'700 im Bestand und nur noch 3'661 fehlend auswies. Zwei
        # Zahlen fuer dieselbe Sache auf EINEM Bildschirm. Nutzer: "erstens
        # habe ich nicht genuegend Materialien dafuer gebaut".
        #
        # URSACHE (Stand Sitzung 13): `_bd_runplan_hidden` blendete nur
        # ALLES-ODER-NICHTS aus (geliefert + laufend >= Plan-Runs). Halb
        # fertige Items blieben mit ihrer URSPRUENGLICHEN Run-Zahl stehen -
        # als haette man noch nichts gemacht. Der Kommentar dort ("Teilweise
        # gedeckte Items bleiben stehen, ihre Rest-Runs waeren sonst
        # unsichtbar") hatte die richtige Sorge, loeste sie aber nur halb:
        # die Zeile blieb, die Zahl war alt.
        # SEIT SITZUNG 14 gibt es das Ausblenden gar nicht mehr (Nutzer-
        # Ansage), `_bd_runplan_hidden` ist ersatzlos weg. Das Rest-Budget
        # unten leistet beides: jede Zeile bleibt stehen UND zeigt ihre
        # aktuelle Zahl.
        #
        # WARUM NICHT DER LAGERBESTAND ABGEZOGEN WIRD: Bestand kann gekauft,
        # gelootet oder fuer einen anderen Plan gedacht sein. Abgezogen wird
        # deshalb NUR, was ESI als abgelieferte oder gerade laufende Jobs
        # DIESES Plans gesehen hat (`_bd_runplan_delivered` +
        # `_bd_active_jobs_map`) - dieselbe Quelle, aus der auch das
        # Ausblenden gespeist wird.
        #
        # REGEL 3 GILT HIER NICHT: "lieber zu viel als zu wenig" ist eine
        # Regel fuers EINKAUFEN (Material uebrig ist harmlos). Sie ist keine
        # Erlaubnis, jemanden 7'321 Runs fahren zu lassen, wenn 3'661 offen
        # sind - dafuer fehlt ihm das Material.
        #
        # Der eingefrorene Plan bleibt UNANGETASTET; nur die Anzeige zeigt
        # den Rest, und die Ursprungszahl steht daneben (Regel 6: nichts
        # verschwindet spurlos).
        from .mw_helpers import (fertig_menge as _mwh_fertig,
                                 rest_und_budget as _mwh_rest)
        _rest_budget = {}
        _plan_runs_tid = {}
        for _t_r, _r_r in _runs_by_tid.items():
            _plan_runs_tid[int(_t_r)] = int(_r_r)
        for _t_r, _pl_r in _plan_runs_tid.items():
            _fertig = int((getattr(self, "_bd_runplan_delivered", None)
                           or {}).get(_t_r, 0) or 0)
            _fertig += sum(int(_j.get("runs") or 0) for _j in
                           ((getattr(self, "_bd_active_jobs_map", None) or {})
                            .get(_t_r) or []))
            # nie mehr abziehen als geplant war - sonst wuerde ein Item, von
            # dem man MEHR gebaut hat als der Plan vorsah, negative Runs
            # zeigen.
            _rest_budget[_t_r] = _mwh_fertig(_pl_r, _fertig, 0)
        tbl.blockSignals(True)
        tbl.clear()
        cslots = {c["id"]: (c["mfg_slots"], c["reaction_slots"]) for c in sched_chars}
        cmax = {c["id"]: (c.get("mfg_slots_max"), c.get("reaction_slots_max"))
                for c in sched_chars}
        # FREIE Slots vom letzten "Skills laden" - seit Sitzung 11 steuern sie
        # die Planung NICHT mehr (Nutzer: "die besetzten slots sollen ignoriert
        # werden"). Verloren gehen sie trotzdem nicht: sie stehen weiter im
        # Tooltip der Charakter-Zeile, damit man sieht, was gerade laeuft.
        cfree = {c["id"]: tuple(c.get("frei_slots") or ()) for c in sched_chars}
        stage_meta = {
            # OHNE Klammer-Zusaetze: "(Zutaten)" / "(braucht Stufe 1)" haben den
            # Strukturnamen aus der Zeile gedraengt (bei Stufe 2 stand nur noch
            # "R&..."). Die Reihenfolge steht schon in der Nummerierung, und
            # dass eine Stufe auf die vorige wartet, sagt der Tooltip der Zeile.
            # Der BAU-ORT ist die wichtigere Information - er ist die
            # Handlungsanweisung.
            # FUEL ZUERST: die Reaktionen verbrauchen es (Nutzer, Sitzung 8).
            # Vorher stand es bei den Komponenten, also HINTER seinen eigenen
            # Verbrauchern.
            # SYMBOL-NAMEN statt Emoji (Sitzung 16) - gesetzt per setIcon.
            "fuel": ("1. " + t("Fuel"), "package", "ms", theme.GREEN),
            "reaction_1": ("2. " + t("Reactions \u2013 Intermediate"),
                          "flask", "rs", theme.VIOLET),
            # EIGENE FARBE fuer die zweite Reaktions-Stufe (Nutzer,
            # Sitzung 12): beide Stufen sahen gleich aus, obwohl sie
            # nacheinander laufen und getrennt geplant werden.
            "reaction_2": ("3. " + t("Reactions \u2013 Composite"),
                          "flask", "rs", theme.VIOLET_2),
            "component": ("4. " + t("Components"), "wrench", "ms", theme.BLUE),
            "end": ("5. " + t("End product"), "target", "ms", theme.AMBER)}
        for stage in ("fuel", "reaction_1", "reaction_2", "component", "end"):
            char_map = by_stage_char.get(stage)
            if not char_map:
                continue
            label, icon, slot_kind, stage_color = stage_meta[stage]
            # WO wird das gebaut? (Nutzer-Wunsch) Ohne den Strukturnamen ist der
            # Runplaner keine Arbeitsanweisung: bei zwei Azbels mit
            # unterschiedlichen Rigs sieht man weder, welche gemeint ist, noch
            # warum die Zeiten sich unterscheiden. Genau daran hat ein ganzer
            # Abend Fehlersuche gehangen. Nur der NAME - keine Prozent-Liste,
            # die die Zeile zumuellt; die Boni stehen weiter im Struktur-Dialog.
            # KORREKTUR Sitzung 9: pro STUFE nachschlagen. Vorher stand hier
            # fuer JEDE Fertigungsstufe die Komponenten-Struktur - "1.
            # Treibstoff", "4. Komponenten" und "5. Endprodukt" zeigten
            # zwangslaeufig denselben Namen, auch wenn die Auto-Wahl fuers
            # Endprodukt eine andere Struktur genommen hatte.
            _stufe_key = {"fuel": "components", "component": "components",
                          "end": "endproduct", "reaction_1": "reaction_1",
                          "reaction_2": "reaction_2"}.get(stage)
            _stage_struct = (getattr(self, "_bd_stage_structs", {}) or {}).get(
                _stufe_key)
            if _stage_struct is None:
                # Rueckfall auf die alten Sammelvariablen, wenn die Stufen-Karte
                # (noch) fehlt - z.B. bei eingefrorenen Alt-Plaenen.
                _stage_struct = (getattr(self, "_bd_react_struct", None)
                                 if stage.startswith("reaction")
                                 else getattr(self, "_bd_mfg_struct", None))
            _sname = (_stage_struct or {}).get("name")
            if _sname:
                label = f"{label}  \u00b7  {_sname}"
            dur = res["stage_times"].get(stage, 0.0)
            stage_item = QTreeWidgetItem([label, "", "",
                                          self._fmt_dur(dur), ""])
            stage_item.setIcon(0, icons.icon(icon, farbe=stage_color))
            # WARUM DIESE STRUKTUR? (Nutzer, Sitzung 8: "theoretisch
            # muesste das Tool fuer ein Capital-Schiff den Bauort auf
            # Capslock aendern.") Die Auto-Wahl vergleicht den RIG-Nutzen
            # fuer genau die Items dieser Stufe. Der Tooltip legt die
            # Rangliste offen - so sieht man sofort, ob eine Struktur
            # gewonnen hat oder ob alle bei 0 % lagen und schlicht die
            # erste genommen wurde.
            try:
                _rang = (getattr(self, "_bd_struct_choice", {}) or {}).get(
                    _stufe_key or stage) or []
                if _rang:
                    _zeilen = "\n".join(
                        f"  {'\u2713' if i == 0 else '\u00b7'} {_n}: "
                        f"{_b:+.1f} % " + _txt("material rig")
                        for i, (_n, _b) in enumerate(_rang))
                    _gleich = (len({b for _, b in _rang}) == 1
                               and len(_rang) > 1)
                    # Die EINORDNUNG der Items dazu - daran haengt alles.
                    # Steht dort "advanced_large_ship" statt "capital_ship",
                    # ist sofort klar, warum das Capital-Rig nicht greift.
                    _dg = (getattr(self, "_bd_struct_diag", {}) or {}).get(
                        _stufe_key or stage) or []
                    _einordnung = ""
                    if _dg:
                        _einordnung = (
                            "\n\n" + t("Classification of the items (group \u2192 "
                                       "rig category):") + "\n"
                            + "\n".join(f"  {_g} \u2192 {', '.join(_d)}"
                                        for _g, _d in _dg))
                    stage_item.setToolTip(
                        0, _txt("Auto-choice by rig benefit for the items of THIS "
                                "stage:\n") + _zeilen
                        + (_txt("\n\nAll level \u2013 no rig fits this item type, so the "
                                "order decides. A capital rig, for instance, does NOT "
                                "affect freighters (they count as Large Ship).")
                           if _gleich else "")
                        + _einordnung)
            except Exception:
                pass
            # SICHTBAR statt versteckt (Nutzer, Sitzung 9: "weiss nicht wo das
            # stehen soll"). Der Tooltip oben ist ein schlechtes
            # Diagnosewerkzeug: man muss die richtige Stelle treffen, und wenn
            # die Daten fehlen, wird er still gar nicht gesetzt - Zeigen auf
            # die Zeile ergibt dann einfach nichts, ohne dass jemand erfaehrt
            # warum. Die Rig-Kategorie gehoert deshalb in die ZEILE.
            try:
                # SCHLUESSEL-FALLE (Nutzer-Screenshot, Sitzung 9: "Rig: keine
                # Einordnung" bei 4 von 5 Stufen): die Diagnose liegt unter den
                # RECHEN-Schluesseln (components/endproduct/...), diese Schleife
                # laeuft aber ueber die ANZEIGE-Schluessel (fuel/component/end).
                # Nur reaction_1/reaction_2 stimmen zufaellig ueberein - genau
                # die eine Stufe, die Daten zeigte. Deshalb hier _stufe_key.
                _dg2 = (getattr(self, "_bd_struct_diag", {}) or {}).get(
                    _stufe_key or stage) or []
                _kat = []
                for _g, _d in _dg2:
                    for _x in _d:
                        if _x not in _kat:
                            _kat.append(_x)
                # BESCHRIFTUNG KORRIGIERT (Nutzer, Sitzung 9: "Dann werden da
                # Rigs frei erfunden"): hier steht die Rig-KATEGORIE der
                # ITEMS dieser Stufe - nicht die verbauten Rigs der Struktur.
                # Mit dem Wort "Rig:" davor las sich das zwangslaeufig wie
                # eine erfundene Rig-Liste. Jetzt "Item-Art:" plus Tooltip,
                # der den Unterschied ausspricht.
                stage_item.setText(
                    4, _txt("Item type: ") + ", ".join(_kat[:3]) if _kat
                    else _txt("Item type: not classified"))
                stage_item.setToolTip(
                    4, _txt("Rig CATEGORY of the items of this stage \u2013 NOT the rigs "
                            "fitted to the structure (those are in the Structures "
                            "tab).\nA material/time rig of the chosen structure only "
                            "applies if it covers this category.\nFull ranking with "
                            "classification: hover over the stage name on the left."))
            except Exception:
                stage_item.setText(4, _txt("Item type: not classified"))
            sf = stage_item.font(0)
            sf.setBold(True); sf.setPointSize(sf.pointSize() + 2)
            stage_item.setFont(0, sf)
            f4 = stage_item.font(3); f4.setBold(True); f4.setPointSize(f4.pointSize() + 1)
            stage_item.setFont(3, f4)
            # Farbiger HINTERGRUND (nicht nur Text) über die ganze Zeile – so sieht
            # die Phase wirklich wie eine Abschnitts-Überschrift aus, statt nur eine
            # andersfarbige Tabellenzeile zu sein ("Excel-Look" vermeiden).
            bg = QColor(stage_color); bg.setAlpha(38)
            for col in range(5):
                stage_item.setBackground(col, QBrush(bg))
            stage_item.setForeground(0, QColor(stage_color))
            stage_item.setForeground(4, QColor(stage_color))
            stage_item.setToolTip(0, _txt("This phase only starts once the previous one is "
                                          "completely finished \u2013 never at the same time."))
            tbl.addTopLevelItem(stage_item)
            _checked_set = getattr(self, "_bd_runplan_checked", None) or set()

            def _apply_struck(titem):
                """Durchgestrichen-Optik manuell anwenden (Signale sind während
                des Baumaufbaus geblockt, also löst setCheckState hier KEIN
                itemChanged/_on_sched_check aus - beim Wiederherstellen eines
                gespeicherten Häkchens sonst nur die Box an, aber kein Strich)."""
                for c in range(tbl.columnCount()):
                    f = titem.font(c); f.setStrikeOut(True); titem.setFont(c, f)
                    if titem.data(c, Qt.UserRole + 5) is None:
                        titem.setData(c, Qt.UserRole + 5, titem.foreground(c))
                    titem.setForeground(c, QColor(theme.GREEN))
            # ZAEHLER FUER DEN STUFEN-ZUSTAND (Nutzer, Sitzung 14). Eine
            # Stufe gilt als fertig, wenn JEDE ihrer Positionen erledigt ist
            # (ESI-belegt oder vom Nutzer abgehakt). Entschieden wird NACH
            # der Charakter-Schleife - vorher kann niemand wissen, ob noch
            # eine offene Position kommt.
            _stage_citems = []
            _stage_items = 0
            _stage_erledigt = 0
            # LAUFENDE POSITIONEN SEPARAT (Nutzer, Sitzung 16): "die blauen
            # Sachen besagen ja, dass etwas im Bau ist. Aber die
            # Ueberkategorie davon zeigt gruen mit Checkhaken. Das ist
            # verwirrend - wenn noch etwas im Bau ist, sollte auch die
            # Kategorie blau sein mit (building) / (im Bau)."
            # Bis hierher zaehlte `_zustand is not None` AUCH "laeuft" als
            # erledigt - eine Stufe mit laufenden Jobs bekam den Haken.
            _stage_laeuft = 0
            for cid, alist in char_map.items():
                ms, rs = cslots.get(cid, (1, 1))
                cap = rs if slot_kind == "rs" else ms
                _mx2 = cmax.get(cid, (None, None))
                cap_max = _mx2[1] if slot_kind == "rs" else _mx2[0]
                jobs_sum = sum(a.get("jobs", 1) for a in alist)
                # WORTWAHL (Nutzer, Sitzung 9: "wie kann Banana Motor 11
                # Reaction-Auftraege bekommen? Er hat ingame nur 10 Slots
                # frei"): die Zahl links sind die STARTS (Blaupausen-Jobs)
                # dieser Stufe insgesamt - nicht gleichzeitig laufende Jobs.
                # Ueberzaehlige startet man nach, sobald ein Slot frei wird
                # (2. Welle); der Scheduler stapelt sie zeitlich hinter die
                # laufenden Jobs desselben Slots, die Stufenzeit enthaelt
                # dieses Warten also bereits. Das alte "11/10 gleichzeitig"
                # behauptete dagegen elf PARALLELE Jobs - dieselbe
                # Fehlerklasse wie das "Rig:"-Praefix: die Beschriftung log,
                # die Rechnung nicht.
                if jobs_sum > cap:
                    slot_txt = _txt("{n} starts on {cap} slots \u00b7 waves").format(
                        n=jobs_sum, cap=cap)
                else:
                    slot_txt = _txt("{n}/{cap} slots").format(n=jobs_sum, cap=cap)
                citem = QTreeWidgetItem([cmap.get(cid, str(cid)), "", slot_txt, "", ""])
                # BESETZTE SLOTS: seit Sitzung 11 plant das Tool mit dem
                # MAXIMUM (Nutzer-Entscheid: "die besetzten slots sollen
                # ignoriert werden") - der Plan laeuft ueber Tage, die jetzt
                # laufenden Jobs sind dann laengst fertig. Die Zahl bleibt
                # aber sichtbar, damit niemand raten muss, warum ingame
                # gerade weniger geht als hier steht.
                _fr2 = cfree.get(cid) or ()
                _frei_jetzt = None
                if len(_fr2) == 2:
                    _frei_jetzt = _fr2[1] if slot_kind == "rs" else _fr2[0]
                if _frei_jetzt is not None and cap_max and _frei_jetzt < cap_max:
                    _ts9 = self.settings.get("bau_char_free_ts")
                    try:
                        from datetime import datetime as _dt9
                        _wann9 = (_dt9.fromtimestamp(float(_ts9))
                                  .strftime("%d.%m. %H:%M") if _ts9 else None)
                    except Exception:
                        _wann9 = None
                    citem.setToolTip(2, _txt(
                        "Planning uses {cap} slots (maximum per skills).\nIn game, at "
                        "the last \u201eLoad skills\u201c{when} only {free} of them were "
                        "free \u2013 the rest were busy.\nThis is DELIBERATELY ignored: "
                        "by the time this stage comes up, those jobs are done. "
                        "Previously a character with 0 free slots dropped out of the "
                        "plan entirely and all the work landed on a single one.\nWhen "
                        "opening a build plan the tool refreshes this state "
                        "automatically if it is older than 10 minutes."
                    ).format(cap=cap_max, free=_frei_jetzt,
                             when=(_txt(" on {d}").format(d=_wann9) if _wann9 else "")))
                citem.setForeground(0, QColor(theme.CYAN))  # alle Charaktere gleiche
                                                            # Farbe (Personen-Ebene),
                                                            # unterscheidet sich von
                                                            # den Phasen-Farben oben
                citem.setFlags(citem.flags() | Qt.ItemIsUserCheckable)
                _ckey_char = f"char|{stage}|{cid}"
                citem.setData(0, Qt.UserRole + 6, _ckey_char)
                if _ckey_char in _checked_set:
                    citem.setCheckState(0, Qt.Checked)
                    _apply_struck(citem)
                else:
                    citem.setCheckState(0, Qt.Unchecked)
                if jobs_sum > cap:
                    citem.setForeground(2, QColor(theme.AMBER))
                    citem.setToolTip(2, _txt(
                        "More starts ({jobs}) than simultaneous slots ({cap}) \u2013 you "
                        "start the surplus ones as soon as a slot frees up (next "
                        "wave). The stage time already includes this waiting."
                    ).format(jobs=jobs_sum, cap=cap)
                        + (_txt("\n({cap} = FREE slots at the last \u201eLoad skills\u201c, "
                                "maximum {max} per skills.)").format(cap=cap, max=cap_max)
                           if cap_max and cap < cap_max else ""))
                f0 = citem.font(0); f0.setBold(True); citem.setFont(0, f0)
                # ZUSTAND JE CHARAKTER-ZEILE (Nutzer, Sitzung 14: "dann
                # muessen wir die charaktere auch abhacken"). Sind ALLE
                # Positionen dieses Charakters in dieser Stufe erledigt oder
                # in Bau, soll auch seine Zeile so aussehen - sonst steht
                # ueber lauter gedimmten Punkt-Zeilen ein leeres Kaestchen,
                # das wieder nach Arbeit aussieht.
                _c_items = 0
                _c_zustand = 0
                _c_laeuft = 0
                for a in sorted(alist, key=lambda x: -x["runs"]):
                    njobs = a.get("jobs", 1) or 1
                    R_plan = int(a["runs"])
                    # Vom Rest-Budget dieses Items abknabbern (siehe oben).
                    # Die Zuteilungen eines Items werden in fester Reihenfolge
                    # abgearbeitet, deshalb reicht ein laufender Zaehler - die
                    # Summe ueber alle Zuteilungen bleibt exakt.
                    _tid_a = int(a["tid"])
                    R, _rest_budget[_tid_a] = _mwh_rest(
                        R_plan, _rest_budget.get(_tid_a, 0))
                    _weg = R_plan - R
                    # ---- ZUSTAND STATT AUSBLENDEN (Nutzer, Sitzung 14) ------
                    # WIDERRUFT DIE ANSAGE AUS SITZUNG 8 ("die ESI soll
                    # Sachen ausblenden ... damit der Bauplan nach und nach
                    # kleiner wird"). Neue Ansage, woertlich: "imprinzip wird
                    # nie etwas mehr ausgeblendet nurnoch gedimmt und
                    # eingefaerbt und mit punkten versehen. Somit kann ich
                    # immer nachsehen was und wie ich etwas gebaut habe,
                    # weiss aber gleichzeitig okey. ich muss da nicht mehr
                    # ran". Die Zeile bleibt also stehen - samt ihren
                    # Material-Unterzeilen, denn genau die wollte er
                    # nachschlagen koennen ("auch was es mal an materialien
                    # gebraucht hat").
                    #
                    # `_zustand` ist die EINE Wahrheit fuer diese Zeile:
                    #   None     - offen, normales Kaestchen
                    #   "fertig" - ESI hat die Runs geliefert -> gruener Punkt
                    #   "laeuft" - steckt in der Bauschleife -> CYAN_RUN-Punkt
                    # Gedimmt werden beide erledigten Faelle.
                    _zustand = None
                    if R <= 0:
                        # Rest-Budget dieses Items ist auf: die Runs dieser
                        # Zuteilung sind gedeckt. ANZEIGE mit den PLAN-Runs,
                        # nicht mit der 0 - sonst stuende dort "0 Runs" und
                        # die Zeile waere als Rueckblick wertlos.
                        #
                        # GEDECKT HEISST NICHT GEBAUT: `mw_helpers.
                        # fertig_menge` zaehlt geliefert UND laufend
                        # zusammen. Ein pauschales "fertig" haette hier also
                        # einen gruenen Punkt auf eine Position gesetzt, die
                        # noch in der Bauschleife steckt - eine
                        # Falschaussage. Gefunden von der Rotprobe
                        # (Sitzung 14). Deshalb dieselbe Unterscheidung wie
                        # unten beim ESI-Befund, aus denselben Rohdaten.
                        _gel_r = int((getattr(self, "_bd_runplan_delivered",
                                              None) or {}).get(_tid_a, 0) or 0)
                        # NUR ECHT LAUFENDE JOBS ZAEHLEN (Nutzer-Screenshot,
                        # Sitzung 14: "da steckt aber schon lange nichts mehr
                        # in der Bauschleife"). `_bd_active_jobs_map` enthaelt
                        # ZWEI Sorten: status "active" (laeuft wirklich) und
                        # status "ready" - fertig gebaut, ingame nur noch
                        # nicht abgeholt. ESI meldet fertige Jobs sogar
                        # weiter als "active"; das Tool korrigiert sie ueber
                        # das abgelaufene end_date zu "ready" (s.
                        # esi.job_is_finished). Wer beide zusammenwirft,
                        # setzt den Lauf-Punkt auf laengst gebaute Sachen -
                        # genau das ist passiert.
                        # NUTZER-ENTSCHEID (Sitzung 14): "ready" gilt als
                        # FERTIG - gedimmt, gruener Punkt. Der Output
                        # existiert; dass er noch abgeholt werden muss, sagt
                        # weiterhin das ✅ vor dem Namen samt Tooltip aus dem
                        # bestehenden Zweig weiter unten.
                        _lauf_r = sum(
                            int(_j.get("runs") or 0) for _j in
                            ((getattr(self, "_bd_active_jobs_map", None)
                              or {}).get(_tid_a) or [])
                            if _j.get("status") != "ready")
                        # JOB-ZUORDNUNG (Nutzer, Sitzung 16): laeuft der Job
                        # fuer einen ANDEREN Plan? ESI verraet das nicht -
                        # aber Reservierungen sind plan-zugeordnet, und die
                        # Karte enthaelt auch selbst gebaute Zwischenprodukte.
                        # Reserviert genau ein fremder Plan dieses Item und
                        # dieser nicht, gehoert der Job dorthin - dann hier
                        # KEIN "laeuft" behaupten.
                        if _lauf_r > 0 and self._job_gehoert_anderem_plan(
                                _tid_a, _fremd_res, eigene=_eigene_res):
                            _lauf_r = 0
                        # de_scan4: aus - interner Zustands-Schluessel, nie angezeigt
                        _zustand = ("laeuft"
                                    if (_lauf_r > 0 and _gel_r < R_plan)
                                    else "fertig")
                        # de_scan4: an
                        R = R_plan
                    njobs = max(1, min(int(njobs), R))
                    base, extra = divmod(R, njobs)
                    parts = [base + 1] * extra + [base] * (njobs - extra)
                    # Klare, schnell lesbare Blaupausen-Angabe: wie viele BPs muss
                    # ich diesem Char geben und mit wie vielen Runs je BP. Bei
                    # ungleichen Runs die Gruppen zeigen, z. B. "5×42 / 1×43 Runs".
                    if njobs == 1:
                        bp_txt = f"1 Blueprint \u00b7 {R} Runs"
                    else:
                        from collections import Counter as _Cnt
                        cnt = _Cnt(parts)
                        # nach Run-Zahl absteigend gruppieren
                        grp = " / ".join(f"{n}\u00d7{runs}"
                                         for runs, n in sorted(cnt.items(), reverse=True))
                        bp_txt = f"{njobs} Blueprints \u00b7 {grp} Runs"
                    # KEIN ZWEITER WEG ZUM ZUSTAND (Rotprobe-Fund,
                    # Sitzung 14): hier stand ein zweiter Block, der den
                    # Zustand nochmals aus `_bd_runplan_hidden` bestimmte.
                    # Er war VOLLSTAENDIG REDUNDANT - `_rest_budget` oben
                    # entsteht aus genau denselben Zahlen (geliefert +
                    # laufend, gedeckelt auf die Plan-Runs des Items). Ist
                    # `_bd_runplan_hidden[tid]` gesetzt, ist das Budget also
                    # zwangslaeufig voll und jede Zuteilung landet bei R <= 0.
                    # Aufgefallen ist es, weil eine Mutation den Block
                    # abklemmte und KEINE einzige Pruefung rot wurde: er
                    # aenderte nichts mehr. Zwei Stellen mit derselben
                    # Meinung sind zwei Wahrheiten, die auseinanderlaufen
                    # koennen - deshalb bleibt nur der Weg ueber das
                    # Rest-Budget.
                    _tid_total_runs = _runs_by_tid.get(a["tid"], 0) or 0
                    _surp_total = _surplus_all.get(a["tid"], 0) or 0
                    _surp_here = (round(_surp_total * (a["runs"] / _tid_total_runs))
                                 if _surp_total and _tid_total_runs else 0)
                    iit = QTreeWidgetItem([a["name"], f"{R:,}".replace(",", "'"),
                                           bp_txt, self._fmt_dur(a.get("seconds", 0)),
                                           _stufe_label(a),
                                           (f"+{_surp_here:,}".replace(",", "'")
                                            if _surp_here else "\u2013")])
                    iit.setTextAlignment(1, Qt.AlignCenter)   # Runs mittig
                    if _weg:
                        # NICHTS VERSCHWINDET SPURLOS: die Zeile zeigt den
                        # REST, der Tooltip nennt Plan und bereits Gebautes.
                        iit.setForeground(1, QColor(theme.CYAN))
                        iit.setToolTip(
                            1, _txt("{rest} of {plan} runs still open \u2013 {done} "
                                 "already delivered or currently building "
                                 "(seen via ESI). The frozen plan itself stays "
                                 "unchanged.").format(
                                     rest=f"{R:,}".replace(",", "'"),
                                     plan=f"{R_plan:,}".replace(",", "'"),
                                     done=f"{_weg:,}".replace(",", "'")))
                    iit.setTextAlignment(3, Qt.AlignRight | Qt.AlignVCenter)  # Zeit rechts
                    iit.setTextAlignment(5, Qt.AlignCenter)
                    if _surp_here:
                        iit.setForeground(5, QColor(theme.AMBER))
                        iit.setToolTip(5, _txt(
                            "{n} units surplus in total for this item (reaction batch "
                            "size) - split here proportionally by runs."
                        ).format(n=int(round(_surp_total))))
                    iit.setFlags(iit.flags() | Qt.ItemIsUserCheckable)
                    _ckey_item = f"{stage}|{cid}|{a['tid']}"
                    iit.setData(0, Qt.UserRole + 6, _ckey_item)
                    # HAND-HAEKCHEN FUER DIE EINKAUFSLISTE MERKEN (Sitzung 16,
                    # Nutzer: "die Einkaufsliste zeigt absurd viele
                    # Materialien ... die ich schon hergebaut habe").
                    # `_bd_runplan_delivered` traegt NUR ESI-gelieferte Runs.
                    # Wer von Hand abhakt (weil ESI den Job nicht mehr sieht
                    # oder er ausserhalb lief), galt fuer den Restbedarf
                    # weiter als OFFEN - und das Material stand wieder auf
                    # der Liste. Diese Zuordnung Schluessel -> (Item, Runs)
                    # macht die Haken fuer `_restbedarf_jetzt` lesbar.
                    self._bd_runplan_runs_by_key[_ckey_item] = (
                        int(a["tid"]), int(a.get("runs") or 0))
                    if _ckey_item in _checked_set:
                        iit.setCheckState(0, Qt.Checked)
                        _apply_struck(iit)
                        # HIER STAND EIN ZWEITER WEG ZUM GRUENEN PUNKT -
                        # ENTFERNT (Nutzer-Freigabe, Sitzung 14: "das mit dem
                        # Runplaner mach mal so").
                        #
                        # Er verglich `geliefert + laufend` (Stand des GANZEN
                        # Items) gegen `a["runs"]` (Runs NUR DIESER
                        # Zuteilung). Das ist ein anderer Massstab als der
                        # Zustands-Weg oben, der das Rest-Budget ueber alle
                        # Zuteilungen des Items verteilt. Bei einem Item, das
                        # auf MEHRERE Charaktere aufgeteilt ist, sagte der
                        # alte Weg deshalb zu frueh "fertig": sind 50 von 100
                        # Runs geliefert und je 50 auf zwei Charaktere
                        # verteilt, gilt 50 >= 50 fuer BEIDE Zeilen - beide
                        # bekamen den gruenen Punkt, obwohl nur die Haelfte
                        # gebaut ist. Mit dem Punkt verschwindet das
                        # Kaestchen, der Nutzer koennte seinen eigenen Haken
                        # auf der offenen Zeile also nicht mehr loesen.
                        # Nach Regel 3 ist das die unsichere Richtung.
                        #
                        # Dass der Fall ihn trifft, ist belegt: in seinem
                        # Vagabond-Plan steht Ferrogel bei Elrasier mit 19
                        # und bei Peanut Motor mit 4 Runs.
                        #
                        # Die Rotprobe hatte den Block unabhaengig als
                        # ueberfluessig ausgewiesen: die Mutation, die ihn
                        # abklemmt, machte KEINE einzige Pruefung rot
                        # (Fehlerliste leer) - dieselbe Signatur wie beim
                        # redundanten `_bd_runplan_hidden`-Block. Der
                        # Zustands-Weg oben setzt den Punkt ohnehin, nur mit
                        # dem richtigen Massstab.
                        # Von Hand gestrichen (NUR der Nutzer streicht,
                        # seine Entscheidung Sitzung 8): KEIN automatisches
                        # Entstreichen - ESI-Jobs erscheinen verzoegert, und
                        # der Strich ist seine Arbeitsnotiz. Der Tooltip
                        # ordnet ehrlich ein, was ESI dazu sieht.
                        if not iit.toolTip(0):
                            _del_n = (getattr(self, "_bd_runplan_delivered",
                                              None) or {}).get(a["tid"], 0)
                            iit.setToolTip(0, (_txt("Ticked by hand. ESI: ")
                                               + (_txt("{n} runs delivered.").format(n=_del_n)
                                                  if _del_n else
                                                  _txt("no delivered jobs seen for it yet "
                                                       "(may lag behind)."))))
                    else:
                        iit.setCheckState(0, Qt.Unchecked)
                        # TEILFORTSCHRITT sichtbar machen: ESI hat schon
                        # geliefert, aber noch nicht alle Plan-Runs - genau
                        # das "in der Bauschleife"-Signal des Nutzers.
                        _del_n = ((getattr(self, "_bd_runplan_delivered",
                                            None) or {}).get(a["tid"], 0)
                                  + sum(int(_jj.get("runs") or 0) for _jj in
                                        ((getattr(self, "_bd_active_jobs_map",
                                                  None) or {})
                                         .get(a["tid"]) or [])))
                        if _del_n:
                            # ESI-N/M AUS DER ZEILE ENTFERNT (Nutzer,
                            # Sitzung 9: "unnoetige Info" - und berechtigt
                            # verwirrend: die Zahl ist der GLOBALE Stand des
                            # Items ueber ALLE Plaene/Jobs, nicht der Anteil
                            # dieser Zeile; bei reservierten Items in
                            # mehreren Bauplaenen zeigt jeder Plan dieselbe
                            # Zahl). Punkt + Faerbung bleiben als Signal,
                            # das Detail steht im Tooltip auf Abruf.
                            iit.setForeground(0, QColor(theme.CYAN))
                            iit.setToolTip(0, _txt(
                                "ESI sees {seen} runs of this item (delivered or in the "
                                "build pipeline, across ALL plans) \u2013 this row needs "
                                "{need}. Once fully covered, the item is HIDDEN from "
                                "the plan."
                            ).format(seen=_del_n, need=int(a.get('runs') or 0)))
                    _cname_here = cmap.get(cid, str(cid))
                    _active_all = (getattr(self, "_bd_active_jobs_map", None)
                                  or {}).get(a["tid"]) or []
                    # NUR die Einträge, die zu DIESEM Charakter gehören - sonst
                    # markierte ein einzelner laufender Job (z.B. bei Elrasier)
                    # fälschlich JEDE Zeile desselben Items bei ALLEN anderen
                    # Charakteren als "läuft gerade" mit, obwohl nur einer es
                    # wirklich tut.
                    _active = [j for j in _active_all if j.get("char") == _cname_here]
                    # DIESELBE ZUORDNUNG WIE BEIM LAUF-PUNKT (Sitzung 16):
                    # sonst sagen Punkt und "(building)" Verschiedenes - genau
                    # der Widerspruch, den der Nutzer gesehen hat.
                    if _active and self._job_gehoert_anderem_plan(
                            a["tid"], _fremd_res, eigene=_eigene_res):
                        _active = []
                    # NUR MARKIEREN, WENN DIE JOBS ZU DIESER ZEILE PASSEN
                    # (Nutzer, Sitzung 9: "Es koennte ja sein, dass das Item
                    # in der Bauschleife ist fuer einen ANDEREN Bauplan").
                    # Sein Kriterium: exakt die Menge und/oder die richtigen
                    # Runs wie im Plan. Umsetzung: die geplante Aufteilung
                    # dieser Zeile ist aus runs/jobs herleitbar (dieselbe
                    # Rechnung wie die Blaupausen-Anzeige); ein laufender
                    # Job zaehlt nur, wenn seine Run-Zahl in diese Aufteilung
                    # passt (Teilmenge mit Vielfachheit - auch teilweise
                    # gestartete Kopien-Saetze passen) ODER die Summe aller
                    # laufenden Jobs exakt der Zeilen-Menge entspricht
                    # (anders geschnitten, aber dieselbe Bestellung). Fremde
                    # Jobs (falsche Run-Zahlen) markieren NICHTS mehr - die
                    # globale Aktivitaet zeigt weiterhin die CYAN-Faerbung
                    # samt Tooltip oben.
                    if _active:
                        _pl_runs9 = int(a.get("runs") or 0)
                        _pl_jobs9 = max(1, int(a.get("jobs") or 1))
                        _b9, _r9 = divmod(_pl_runs9, _pl_jobs9)
                        _split9 = [_b9 + 1] * _r9 + [_b9] * (_pl_jobs9 - _r9)
                        _lauf9 = [int(j.get("runs") or 0) for j in _active]
                        _rest9 = list(_split9)
                        _passt9 = True
                        for _x9 in _lauf9:
                            if _x9 in _rest9:
                                _rest9.remove(_x9)
                            else:
                                _passt9 = False
                                break
                        if not _passt9 and sum(_lauf9) != _pl_runs9:
                            _active = []
                    if _active:
                        _ready = [j for j in _active if j.get("status") == "ready"]
                        _running = [j for j in _active if j.get("status") != "ready"]
                        if _ready and not _running:
                            # Fertig, aber noch nicht abgeliefert: grün markieren -
                            # der Output existiert schon, er muss nur ins Lager.
                            _green = QColor(theme.GREEN)
                            for c in range(tbl.columnCount()):
                                iit.setForeground(c, _green)
                            _who = ", ".join(f"{j.get('runs') or '?'} Runs"
                                             for j in _ready)
                            iit.setToolTip(0, _txt(
                                "\u2705 DONE per ESI at {name} ({who}) - only DELIVER in "
                                "game now. It can then take up to 1 h until ESI updates "
                                "the stock (CCP cache)."
                            ).format(name=_cname_here, who=_who))
                            iit.setText(0, "\u2705 " + iit.text(0))
                        else:
                            # "WIRD GEBAUT" (Nutzer-Wunsch Sitzung 12).
                            #
                            # Frueher: violettes Symbol vor dem Namen. Violett
                            # ist aber die Farbe der Reaktions-STUFE - ein
                            # laufender Job ist ein ZUSTAND. Zwei verschiedene
                            # Aussagen in derselben Farbe verwirren.
                            #
                            # Jetzt: eigene Farbe + Klartext hinter dem Namen.
                            # Beides verschwindet, sobald der Job fertig ist -
                            # die Zeile sieht dann wieder normal aus.
                            _lauf = QColor(theme.CYAN_RUN)
                            for c in range(tbl.columnCount()):
                                iit.setForeground(c, _lauf)
                            _who = ", ".join(
                                f"{j.get('runs') or '?'} Runs"
                                + (t(" (ready!)") if j.get("status") == "ready" else "")
                                for j in _active)
                            iit.setToolTip(0, _txt(
                                "Already running according to ESI at {who} "
                                "({what}) - before starting this again, check "
                                "whether it is already enough.").format(
                                    who=_cname_here, what=_who))
                            iit.setText(0, iit.text(0) + " " + _txt("(building)"))
                    # Aktivität merken (für "Blueprint-Name kopieren": Reaktion vs
                    # Fertigung -> "Reaction Formula" bzw. "Blueprint").
                    iit.setData(0, Qt.UserRole + 7, a.get("activity"))
                    # DER NAME IST ANKLICKBAR (Nutzer, 15.09.2026): "im
                    # Runplaner steht Silicon Diborite - klickt man drauf,
                    # bekommt man Silicon Diborite Reaction Formula ins
                    # Clipboard". Hier steht die Zeile schon fest, also wird
                    # der Blaupausen-Name hier abgelegt; Rahmen malt
                    # KopierRahmenDelegate, den Klick nimmt _sched_name_klick.
                    # EINE Quelle fuer den Namen: _bp_name_fuer, dieselbe
                    # Regel wie im Rechtsklick-Menue und in der BP-Spalte.
                    iit.setData(0, ROLLE_KOPIERNAME,
                                self._bp_name_fuer(a.get("name"),
                                                   a.get("activity")))
                    # RUNS FETT (Nutzer, 15.09.2026): das ist die Zahl, nach
                    # der man ingame den Job einstellt - sie soll sich vom
                    # Rest der Zeile abheben.
                    _fr = iit.font(1)
                    _fr.setBold(True)
                    iit.setFont(1, _fr)
                    # BP-Spalte hervorheben, wenn mehr als 1 BP nötig (das ist die
                    # Info, wie viele Blueprints du aufteilen musst).
                    fb = iit.font(2)
                    fb.setBold(njobs > 1)
                    iit.setFont(2, fb)
                    if njobs > 1:
                        iit.setForeground(2, QColor(theme.AMBER))
                        iit.setToolTip(2, _txt(
                            "{name}: split {runs} runs across {n} blueprints ("
                        ).format(name=a["name"], runs=R, n=njobs)
                                       + "+".join(str(p) for p in parts)
                                       + _txt(" = {runs}). ~{n}\u00d7 faster than 1 BP."
                                              ).format(runs=R, n=njobs))
                    else:
                        iit.setForeground(2, QColor(theme.MUTED))
                    bp = recipes.product_to_bp.get(a["tid"])
                    # ZUTATEN AUS DEM PLAN, nicht nachgerechnet (Sitzung 13):
                    # die alte Rechnung hier kannte nur den globalen
                    # Fertigungs-ME und setzte Reaktionen auf 1,0 - der Baum
                    # zeigte 1'000 Vanadium, der Materialien-Reiter 980.
                    # plan_mats_pro_run liefert die Menge je Run aus
                    # build_mats; Rueckfall auf die Nachrechnung nur, wenn ein
                    # alter Schnappschuss keine build_mats hat.
                    # OFFENE Runs, nicht die Plan-Runs (Sitzung 13): steht in
                    # der Zeile "5'000 Runs offen", muss die Zutat darunter die
                    # Menge fuer 5'000 Runs nennen. Sonst widerspricht das
                    # Kind seiner eigenen Elternzeile - genau die Sorte
                    # Doppel-Wahrheit, die der Nutzer gemeldet hat.
                    _pr = industry.plan_mats_pro_run(plan, a["tid"])
                    if _pr is not None:
                        _zut = [(m, pr * int(R)) for m, pr in _pr]
                    elif bp:
                        bp_id, activity, _oq = bp
                        mfac = (1 - me_pct / 100.0) if activity == industry.MANUFACTURING else 1.0
                        _zut = [(m, industry.material_menge(bq, R, mfac))
                                for m, bq in recipes.bp_materials.get((bp_id, activity), [])]
                    else:
                        _zut = []
                    for mat_id, q in _zut:
                        mit = QTreeWidgetItem([names.get(mat_id, f"#{mat_id}"),
                                               f"{int(q):,}".replace(",", "'"),
                                               "", "", ""])
                        mit.setTextAlignment(1, Qt.AlignCenter)
                        mit.setForeground(0, QColor(theme.MUTED))
                        mit.setForeground(1, QColor(theme.MUTED))
                        # NIE ABHAKBAR (Nutzer, 15.09.2026, mit Zoom-Bild:
                        # "dieser gruene Haken ist nicht von mir, den kann
                        # ich nicht setzen ... ich kann ihn auch nicht
                        # wegmachen"). Eine Material-Unterzeile ist eine
                        # Stueckliste, keine Entscheidung - sie hatte nie ein
                        # Kaestchen und soll auch keins bekommen.
                        #
                        # WARUM SIE TROTZDEM EINS BEKAM: QTreeWidgetItem
                        # traegt Qt.ItemIsUserCheckable BEREITS in seinen
                        # Standard-Flags (nachgemessen). Sichtbar wird ein
                        # Kaestchen zwar erst mit CheckStateRole - aber die
                        # Kinder-Kaskade in _on_sched_check ("hake ich den
                        # Charakter ab, sollen seine Positionen mit") fragte
                        # nur die Flags ab und setzte dann setCheckState.
                        # Damit malte sie den Stuecklisten-Zeilen ein
                        # Kaestchen samt Haken hin, und ein Loesen liess das
                        # LEERE Kaestchen stehen (CheckStateRole ist dann 0,
                        # nicht mehr None) - genau der Haken, der "von
                        # niemandem" kam und nicht wegging.
                        mit.setFlags(mit.flags() & ~Qt.ItemIsUserCheckable)
                        iit.addChild(mit)
                    # ---- ZUSTAND ANWENDEN: PUNKT STATT KAESTCHEN, GEDIMMT ---
                    # GANZ ZUM SCHLUSS, damit es die Faerbungen davor
                    # (CYAN_RUN, GREEN, AMBER) bewusst ueberschreibt - sonst
                    # haetten zwei Stellen eine Meinung zur selben Zeile und
                    # es entstuenden wieder zwei Wahrheiten.
                    #
                    # WARUM DAS KAESTCHEN VERSCHWINDET: "Abhacken kann ja nur
                    # ich" - ein Kaestchen ist eine offene Entscheidung. Ist
                    # die Position von ESI belegt, gibt es nichts mehr zu
                    # entscheiden, und ein Kaestchen saehe wieder nach Arbeit
                    # aus. Das war der ganze Ausgangspunkt.
                    #
                    # UNABHAENGIG VOM HAKEN (Nutzer: "das muss auch
                    # funktionieren ob ich etwas gehackt habe oder nicht"):
                    # bis Sitzung 13 hing `icons.gruener_punkt()` INNERHALB
                    # von `if _ckey_item in _checked_set:` - ohne eigenen
                    # Haken also kein Punkt. Aufgefallen ist das nie, weil
                    # voll gedeckte Zeilen ohnehin ausgeblendet wurden. Jetzt
                    # entscheidet allein der ESI-Befund.
                    if _zustand is not None:
                        iit.setFlags(iit.flags() & ~Qt.ItemIsUserCheckable)
                        iit.setData(0, Qt.CheckStateRole, None)
                        # de_scan4: aus - interner Zustands-Schluessel
                        if _zustand == "fertig":
                            # de_scan4: an
                            iit.setIcon(0, icons.gruener_punkt())
                        else:
                            iit.setIcon(0, icons.lauf_punkt())
                            # UNSICHERE ZUORDNUNG BENENNEN (Nutzer, Sitzung
                            # 16): bauen zwei Plaene dasselbe Zwischen-
                            # produkt, beansprucht es jeder - dann laesst
                            # sich der Job nicht zuordnen und der Punkt
                            # bleibt. Statt eine Zuordnung vorzutaeuschen:
                            # kurz sagen, dass sie unsicher ist.
                            _mit_anspruch = self._plan_mit_anspruch(
                                _tid_a, _fremd_res)
                            if _mit_anspruch:
                                iit.setText(0, iit.text(0) + "  "
                                            + _txt("\u2753 could belong to "
                                                   "another build plan"))
                                iit.setToolTip(0, _txt(
                                    "A job for this item is running - but "
                                    "\u201e{plan}\u201c claims it too. ESI does not "
                                    "say which build plan a job belongs to."
                                ).format(plan=_mit_anspruch))
                        # GEDIMMT, ABER LESBAR: alle Spalten auf MUTED,
                        # einschliesslich der Material-Unterzeilen (die sind
                        # ohnehin schon MUTED). Der Nutzer will nachschlagen
                        # koennen, nicht raten muessen.
                        _dim = QColor(theme.MUTED)
                        for _c_z in range(tbl.columnCount()):
                            iit.setForeground(_c_z, _dim)
                        if not iit.toolTip(0):
                            iit.setToolTip(0, _txt(
                                "Nothing left to do here \u2013 ESI has this "
                                "covered. The line stays so you can look up "
                                "later what was built and what it needed.")
                                # de_scan4: aus - interner Zustands-Schluessel
                                if _zustand == "fertig" else _txt(
                                # de_scan4: an
                                "Currently in the build queue according to "
                                "ESI \u2013 nothing to do here."))
                    citem.addChild(iit)
                    _stage_items += 1
                    _c_items += 1
                    if _zustand is not None:
                        _c_zustand += 1
                        if _zustand == "laeuft":
                            _c_laeuft += 1
                    # ERLEDIGT ist entweder ESI-belegt ODER vom Nutzer selbst
                    # abgehakt - seine Arbeitsnotiz zaehlt genauso, sonst
                    # bliebe eine von Hand durchgearbeitete Stufe fuer immer
                    # aufgeklappt.
                    if _zustand is not None or _ckey_item in _checked_set:
                        _stage_erledigt += 1
                    if _zustand == "laeuft":
                        _stage_laeuft += 1
                    # KOPIER-KNOEPFE fuer die Run-Zahlen (Nutzer, Sitzung 8):
                    # "ich moechte Buttons, in denen die Zahl steht - draufklicken
                    # kopiert sie ins Clipboard, damit ich ingame nichts tippen
                    # muss." Je VERSCHIEDENER Run-Zahl ein Knopf (bei
                    # '2x28 / 7x27' also zwei: 28 und 27), Reihenfolge wie im
                    # Text. Die Knoepfe leben in Spalte 2 NEBEN dem Text.
                    try:
                        # NUTZER (Sitzung 8): "es laesst sich nicht gut
                        # erkennen, wieviel mal ich 28 kopieren muss und
                        # wieviel mal 27 - es soll stehen 2x (28) 7x (27)."
                        # Also die ANZAHL direkt vor den Knopf, und der
                        # Knopf traegt nur noch die Zahl, die kopiert wird.
                        # Reihenfolge wie im alten Text: groesste Run-Zahl
                        # zuerst.
                        from collections import Counter as _Cnt2
                        _cnt2 = _Cnt2(parts)
                        _gruppen = sorted(_cnt2.items(), reverse=True)
                        if _gruppen:
                            _cw = QWidget()
                            _cl = QHBoxLayout(_cw)
                            _cl.setContentsMargins(0, 3, 0, 3)
                            _cl.setSpacing(3)
                            # DER BLAUPAUSEN-NAME IST JETZT ANKLICKBAR
                            # (Nutzer, Sitzung 20): "moechte ich auf
                            # Crystallite Alloy klicken und dann Crystallite
                            # Alloy Reaction Formula ins Clipboard bekommen."
                            # Die Run-Zahlen daneben tun das seit Sitzung 8;
                            # den Namen gab es nur ueber das Rechtsklick-Menue,
                            # und das findet man nicht.
                            _bp_nm = self._bp_name_fuer(a.get("name"),
                                                        a.get("activity"))
                            _kopf = QPushButton(
                                _txt("{n} blueprints").format(n=njobs))
                            _kopf.setCursor(Qt.PointingHandCursor)
                            _kopf.setMinimumHeight(24)
                            _kopf.setToolTip(
                                _txt("Click copies the blueprint name:")
                                + f"\n{_bp_nm}")
                            # GERAHMT WIE DIE RUN-ZAHLEN (Nutzer,
                            # 15.09.2026: "alle anderen blueprints die da
                            # vorkommen" sollen denselben kleinen Rahmen
                            # tragen). Vorher war der Rahmen erst beim
                            # Darueberfahren da - man sah dem Knopf nicht an,
                            # dass er ueberhaupt einer ist.
                            _kopf.setStyleSheet(
                                f"QPushButton{{background:{theme.PANEL2}; "
                                f"border:1px solid {theme.AMBER_DIM}; "
                                f"color:{theme.AMBER}; border-radius:5px; "
                                f"padding:0px 8px;}}"
                                f"QPushButton:hover{{border-color:"
                                f"{theme.AMBER}; background:{theme.PANEL};}}")
                            _kopf.clicked.connect(
                                lambda _c=False, _nm=_bp_nm:
                                self._copy_bp_name_value(_nm))
                            _cl.addWidget(_kopf)
                            for _r, _anz in _gruppen:
                                _mal = QLabel(f"{_anz}\u00d7")
                                _mal.setStyleSheet(
                                    f"color:{theme.AMBER}; font-weight:700;")
                                _cl.addWidget(_mal)
                                _b = QPushButton(str(_r))
                                _b.setCursor(Qt.PointingHandCursor)
                                _b.setMinimumHeight(24)
                                _b.setToolTip(
                                    (_txt("{n} blueprints with {r} runs each.")
                                     if _anz != 1 else
                                     _txt("{n} blueprint with {r} runs.")).format(n=_anz, r=_r)
                                    + _txt("\nClick copies {r} \u2013 paste it into the "
                                           "\u201eRuns\u201c field in game (Ctrl+V).").format(r=_r))
                                _b.setStyleSheet(
                                    f"QPushButton{{background:{theme.PANEL2}; "
                                    f"border:1px solid {theme.AMBER_DIM}; "
                                    f"color:{theme.AMBER}; border-radius:5px; "
                                    f"padding:0px 10px; font-weight:700;}}"
                                    f"QPushButton:hover{{border-color:"
                                    f"{theme.AMBER}; background:{theme.PANEL};}}")
                                _b.clicked.connect(
                                    lambda _c=False, _v=_r, _n=a["name"]:
                                    self._copy_runs_value(_v, _n))
                                _cl.addWidget(_b)
                            _cl.addStretch()
                            # Der Text steckt jetzt IM Widget - die Spalte
                            # selbst leeren, sonst stuende er doppelt da.
                            iit.setText(2, "")
                            # NUTZER (zweimal gemeldet): "Knoepfe sind unten
                            # leicht abgeschnitten." Erster Versuch war eine
                            # GERATENE feste Hoehe (30 px) - zu knapp.
                            # Jetzt MESSEN statt raten: das fertige Widget
                            # nach seiner eigenen Wunschhoehe fragen und
                            # etwas Luft draufgeben. Damit passt es auch,
                            # wenn sich Schriftgroesse oder Knopf-Rahmen
                            # spaeter aendern.
                            _cw.adjustSize()
                            # DRITTER ANLAUF (Nutzer, 15.09.2026: "der Rahmen
                            # ist an der Unterkante etwas abgeschnitten").
                            # Mehr Luft UND dieselbe Hoehe fuer Spalte 0 -
                            # dort sitzt seit heute der Rahmen um den
                            # Formel-Namen, und die Zeilenhoehe richtet sich
                            # nach der GROESSTEN Wunschhoehe der Zeile.
                            _hoehe = max(34, _cw.sizeHint().height() + 10)
                            iit.setSizeHint(2, QSize(0, _hoehe))
                            iit.setSizeHint(0, QSize(0, _hoehe))
                            tbl.setItemWidget(iit, 2, _cw)
                    except Exception:
                        pass       # Knoepfe sind Komfort, nie kritisch
                # ---- CHARAKTER-ZEILE: PUNKT STATT KAESTCHEN, GEDIMMT -------
                # Dieselbe Regel wie eine Ebene tiefer, damit die Zeile nicht
                # das Gegenteil ihrer eigenen Kinder behauptet.
                # WELCHER PUNKT: laeuft auch nur EINE Position noch, ist der
                # Charakter nicht fertig - dann der Lauf-Punkt. Gruen erst,
                # wenn wirklich alles geliefert ist. Die vorsichtigere
                # Aussage gewinnt (Regel 3).
                if _c_items > 0 and _c_zustand == _c_items:
                    citem.setFlags(citem.flags() & ~Qt.ItemIsUserCheckable)
                    citem.setData(0, Qt.CheckStateRole, None)
                    citem.setIcon(0, icons.lauf_punkt() if _c_laeuft
                                  else icons.gruener_punkt())
                    _dim_c = QColor(theme.MUTED)
                    for _c_cc in range(tbl.columnCount()):
                        citem.setForeground(_c_cc, _dim_c)
                stage_item.addChild(citem)
                _stage_citems.append(citem)
                citem.setExpanded(False)
            # ---- FERTIGE STUFE: ZUGEKLAPPT, ABER VOLLSTAENDIG -------------
            # NUTZER (Sitzung 14): "wie koennte man die darstellung schoener
            # machen fuer fertige Runs? aktuell kann ich da immernoch haken
            # setzen und es sieht aus als gaebe es noch was zu tun bei 2-4",
            # dazu "am liebsten solls weg sein. ich will wenn ich reactions
            # gemacht habe nurnoch komponents sehen" - und, wichtiger:
            # "imprinzip wird nie etwas mehr ausgeblendet nurnoch gedimmt".
            #
            # BEIDES ZUSAMMEN heisst ZUKLAPPEN, nicht wegnehmen (sein
            # Entscheid: "Zugeklappt - ein Klick holt alles zurueck"). Die
            # Charakter-Zeilen, die Item-Zeilen und ihre Material-Unterzeilen
            # bleiben also ALLE erhalten; die Stufe faltet sich nur auf ihre
            # Kopfzeile zusammen. So sieht er beim Arbeiten nur die offene
            # Stufe, kann aber jederzeit nachschlagen, was er gebaut hat und
            # was es gebraucht hat.
            #
            # WANN IST EINE STUFE FERTIG: wenn JEDE ihrer Positionen einen
            # Zustand hat - ESI-belegt (gebaut oder in der Bauschleife) oder
            # vom Nutzer selbst abgehakt. Bewusst NICHT "keine Zeilen mehr
            # da": seit dieser Sitzung wird nichts mehr ausgeblendet, es gibt
            # also immer Zeilen. Die alte Bedingung waere still nie wieder
            # wahr geworden - eine Zusage, die niemand mehr haelt.
            #
            # `_stage_items > 0` ist Absicht: eine Stufe ohne jede Position
            # ist nicht "fertig", sondern leer. Ohne die Bedingung bekaeme
            # sie faelschlich einen Haken.
            # ALLE POSITIONEN ABGEDECKT - aber "abgedeckt" heisst nicht
            # "fertig": laufende Jobs zaehlen mit, sind aber noch im Bau.
            _stufe_abgedeckt = (_stage_items > 0
                                and _stage_erledigt == _stage_items)
            # ECHT FERTIG ist die Stufe nur ohne laufende Position.
            _stufe_fertig = _stufe_abgedeckt and _stage_laeuft == 0
            if _stufe_abgedeckt:
                if _stufe_fertig:
                    stage_item.setText(0, f"\u2713  {label}")
                    stage_item.setText(2, _txt("finished \u00b7 {n} position(s) "
                                               "completed").format(
                                                   n=_stage_erledigt))
                else:
                    # IM BAU: derselbe Punkt und dieselbe Farbe wie bei den
                    # laufenden Kindzeilen - sonst sagt die Stufe etwas
                    # anderes als das, was darunter steht.
                    stage_item.setText(0, f"\u25cf  {label}")
                    stage_item.setText(2, _txt(
                        "in build \u00b7 {n} of {ges} position(s) running").format(
                        n=_stage_laeuft, ges=_stage_items))
                # DAUER RAUS: die Stufenzeit ist die GEPLANTE Dauer. In einer
                # fertigen Stufe liest man sie als "so lange dauert es noch" -
                # und genau das waere gelogen. Sie bleibt im Tooltip.
                stage_item.setToolTip(3, _txt("Planned duration of this stage "
                                              "was {d}.").format(
                                                  d=self._fmt_dur(dur)))
                stage_item.setText(3, "")
                stage_item.setText(4, "")     # Item-Art: hier ohne Belang
                _bg_f = QColor(stage_color); _bg_f.setAlpha(12)
                for _c_f in range(5):
                    stage_item.setBackground(_c_f, QBrush(_bg_f))
                    stage_item.setForeground(_c_f, QColor(theme.MUTED))
                # CYAN_RUN, nicht CYAN: die laufenden Kindzeilen nutzen
                # denselben Ton (icons.lauf_punkt -> theme.CYAN_RUN,
                # Nutzer-Entscheid Sitzung 14). Dieselbe Aussage, dieselbe
                # Farbe - sonst haette "laeuft" zwei Erscheinungsbilder.
                _stufe_farbe = (QColor(theme.GREEN) if _stufe_fertig
                                else QColor(theme.CYAN_RUN))
                stage_item.setForeground(0, _stufe_farbe)
                stage_item.setForeground(2, _stufe_farbe)
            # DIE ZAEHL-ZEILE IST WEG (Nutzer, Sitzung 14). Sie war das
            # Gegenstueck zum Ausblenden ("Regel 6: nichts verschwindet
            # spurlos") - sie fasste zusammen, was der Baum nicht mehr zeigte.
            # Seit nichts mehr ausgeblendet wird, steht jede Position wieder
            # selbst da, gedimmt und mit Punkt. Eine Zusammenfassung von
            # Zeilen, die daneben vollstaendig sichtbar sind, waere eine
            # zweite Wahrheit ueber dieselbe Sache.
            #
            # ZUGEKLAPPT, WENN FERTIG - offene Stufen bleiben offen.
            # AUFKLAPP-ZUSTAND DER CHARAKTER-ZEILEN (Nutzer-Screenshot,
            # Sitzung 14: "wo gibts jetzt da gruene punkte?"). Bei einer
            # OFFENEN Stufe bleiben sie zu wie bisher - dort zaehlt die
            # Uebersicht. Bei einer FERTIGEN Stufe ist es umgekehrt: sie ist
            # ohnehin zugeklappt, und wer sie aufklappt, will genau EINES
            # sehen - was gebaut wurde und was es gebraucht hat. Blieben die
            # Charakter-Zeilen dann auch noch zu, muesste er zweimal
            # aufklappen, um die Punkte ueberhaupt zu finden. Genau daran ist
            # er haengengeblieben.
            # ZUKLAPPEN HAENGT AN "ABGEDECKT", NICHT AN "FERTIG": eine Stufe
            # im Bau hat nichts zu tun und soll zu bleiben - genau so hat der
            # Nutzer sie gesehen ("die Ueberkategorie davon, wenn zugeklappt").
            # Haenge das Zuklappen an _stufe_fertig, klappte sie ploetzlich auf.
            for _cf in _stage_citems:
                _cf.setExpanded(_stufe_abgedeckt)
            stage_item.setExpanded(not _stufe_abgedeckt)
        # ---- ℹ NICHT EINGEPLANT: Kauf billiger / Bestand deckt --------------
        # Nutzer-Fall Magpulse Thruster: eine baubare Komponente fehlte im
        # Runplaner und sah "vergessen" aus - in Wahrheit hatte der Plan sie
        # als KAUF eingestuft (Markt billiger als Bauen) bzw. der Bestand
        # deckte sie. Der Runplaner zeigte bisher NUR Bau-Zeilen; jetzt sagt
        # er ausdrücklich, was er bewusst NICHT einplant und warum - dieselbe
        # Ehrlichkeits-Regel wie die Swing-Trichterzeile.
        _built_tids = {a["tid"] for a in res["assignments"]}
        # Herkunft auch HIER ausweisen (Nutzer-Auftrag Punkt 2): „durch Bestand
        # gedeckt" ist eine andere Aussage, je nachdem ob die Zahl aus ESI, aus
        # einer eingefügten Liste oder aus der Job-Pipeline stammt.
        _src_map = getattr(self, "_bd_stock_src", None) or {}

        def _why_for(_tid, _kind):
            if _kind != "stock":
                return _txt("BUY \u2013 market cheaper than building "
                            "(is on the shopping list)")
            _i = _src_map.get(_tid) or {}
            if _i.get("src") == "manuell":
                return _txt("covered by PASTED stock ( Materials tab) \u2013 "
                            "nothing to do")
            if _i.get("job") and not _i.get("esi"):
                return _txt("covered by the pipeline (running/finished jobs) \u2013 "
                            "nothing to do")
            return _txt("covered by ESI stock \u2013 nothing to do")
        _info = [(_i, q, _why_for(_i, k)) for _i, q, k in
                 self._unscheduled_build_items(
                     plan, _built_tids,
                     # NICHT is_manufactured: das deckt nur MANUFACTURING ab
                     # und haette jede Reaktion aus dem "Nicht eingeplant"-
                     # Segment verschwinden lassen - obwohl der Plan sie
                     # bewusst kauft statt sie zu fahren. Genau die Zeile
                     # will der Nutzer sehen. Reaktionen sind selbst
                     # herstellbar, also gehoeren sie hier hin.
                     self._bd_producible_fn(recipes))]
        if _info:
            _ihdr = QTreeWidgetItem(
                [_txt("\u2139  Not planned \u2013 buying cheaper / stock covers ")
                 + _txt("({n} buildable items)").format(n=len(_info)), "", "", "", ""])
            _f = _ihdr.font(0); _f.setBold(True); _ihdr.setFont(0, _f)
            _mut = QColor(theme.MUTED)
            _ihdr.setForeground(0, _mut)
            _ihdr.setToolTip(0, _txt(
                "Buildable items the plan DELIBERATELY does not build: either buying "
                "at the current hub is cheaper than building (then they are on the "
                "shopping list), or your stock (incl. pipeline) covers the need. If "
                "an item you expected is missing here, THAT is the answer - not the "
                "plan forgetting it."))
            _shown = 0
            for _tid, _q, _why in _info:
                if _shown >= 40:
                    _more = QTreeWidgetItem(
                        [_txt("\u2026 and {n} more").format(n=len(_info) - _shown),
                         "", "", "", ""])
                    _more.setForeground(0, _mut)
                    _ihdr.addChild(_more)
                    break
                _iit = QTreeWidgetItem(
                    [names.get(_tid, f"#{_tid}"),
                     f"{_q:,}".replace(",", "'"), _why, "", ""])
                _iit.setTextAlignment(1, Qt.AlignCenter)
                for _c in range(3):
                    _iit.setForeground(_c, _mut)
                _ihdr.addChild(_iit)
                _shown += 1
            tbl.addTopLevelItem(_ihdr)
            _ihdr.setExpanded(False)
        tbl.blockSignals(False)
