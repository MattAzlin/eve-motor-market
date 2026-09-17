"""ROT-PROBE (Arbeitsregel 11) fuer den aa92-Block

AUFRUF:  python3 rotprobe.py            (alle Mutationen, dauert ~7 Minuten)
         python3 rotprobe.py 0 3        (nur Mutation 0..2)

Drei der zehn Pruefungen waren beim ersten Durchlauf BLIND: sie fanden ihren
Suchtext im Kommentar bzw. Docstring ueber dem Aufruf, nicht im Aufruf selbst.
Deshalb pruefen die betroffenen Stellen jetzt per AST, ob der Aufruf/Vergleich
WIRKLICH dasteht. Wer hier etwas ergaenzt: neue Mutation dazuschreiben und
nachsehen, dass sie auch erkannt wird.
: ein gruener Test zaehlt erst, wenn er auch
rot werden kann. Jede Mutation dreht GENAU EINEN Fix zurueck; danach muss die
zugehoerige Pruefung fehlschlagen. Faellt nichts aus, war die Pruefung blind.
"""
import os
import re
import shutil
import tempfile
import subprocess
import sys

SRC = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(tempfile.gettempdir(), "rotprobe_arbeitskopie")

# NICHT in die Arbeitskopie (Sitzung 10, Nutzer-Befund): auf dem Rechner des
# Nutzers liegen `.venv`, `build` und `dist` im Projektordner - zusammen
# mehrere hundert MB, die hier 242 Mal umkopiert wuerden, jedes Mal unter den
# Augen des Virenscanners. Fuer den Testlauf braucht es nichts davon: er
# startet mit `sys.executable`, also dem Python, das die Rotprobe selbst
# faehrt, und ruehrt die Kopie des venv nie an. `.smoke_home` MUSS bleiben -
# die b-Suite legt ihr Arbeitsverzeichnis dorthin.
_nicht_kopieren = shutil.ignore_patterns(
    ".venv", "build", "dist", "__pycache__", "*.pyc",
    "rotprobe_komplett.txt", "fehler.log")

# (Name, Datei, alt, neu, erwartete Teilzeichenkette in einem FEHLER-Label)
MUTATIONEN = [
    ('eigene BPCs wirken nicht mehr in build_cost',
     'eve_trader/industry.py',
     'if _inv_override or int(\n                        (opts.get("inv_owned_runs") or {}).get(bp_id, 0) or 0) > 0:',
     'if _inv_override or False:',
     'eigene BPCs -> keine Invention'),
    ('Rueckfall-Material wird nicht getrennt',
     'eve_trader/industry.py',
     '            elif from_adj:\n                _p_adj += unit * qeff',
     '            elif from_adj:\n                _p_market += unit * qeff',
     'Rueckfall-Material wird getrennt'),
    ('Aufschluesselung geht nicht mehr auf',
     'eve_trader/industry.py',
     '        _p_job += jc\n',
     '        _p_job += jc * 0.5\n',
     'Aufschluesselung geht exakt auf'),
    ('Dialog rechnet die Aggregation wieder selbst',
     'eve_trader/ui/main_window.py',
     '        owned, bpo_ids = industry.owned_bp_runs(owned_bp, target_bp_ids)',
     '        owned, bpo_ids = {}, set()   # MUTATION',
     'Dialog rechnet es NICHT mehr selbst'),
    ('Scan zieht die eigenen BPCs nicht',
     'eve_trader/ui/main_window.py',
     '            build_opts.update(self._scan_owned_bpc_opts())',
     '            pass   # MUTATION',
     'Scan zieht die eigenen BPCs'),
    ('Plan meldet den Rueckfall-Anteil nicht',
     'eve_trader/industry.py',
     '            "mat_cost_adjusted": mat_cost_adjusted,\n',
     '            "mat_cost_adjusted": 0.0,\n',
     'Plan trennt den Rueckfall-Anteil'),
    ('Nachrechnung behaelt den alten Anteil',
     'eve_trader/scanner.py',
     '                r["fallback_pct"] = (float(plan.get("mat_cost_adjusted", 0.0) or 0.0)\n                                     / total_cost * 100.0)',
     '                pass   # MUTATION',
     'nachgerechnete Zeile bekommt den Anteil'),
    ('Zeile wird nicht mehr markiert',
     'eve_trader/ui/main_window.py',
     '            if _fb is not None and _fb >= self.BAU_FALLBACK_WARN_PCT:',
     '            if False:',
     'Zeile markiert hohen Rueckfall'),
    ('Scanner reicht den Anteil nicht durch',
     'eve_trader/scanner.py',
     '                "fallback_pct": _fallback_pct,',
     '                "fallback_pct_MUTIERT": _fallback_pct,',
     'Rueckfall-Anteil steht in der Trefferzeile'),
    ('TE-Rebuild wieder synchron (App-Absturz)',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            QTimer.singleShot(0, rebuild)',
     '            rebuild()',
     'kein direkter rebuild() im Fokus-Signal'),
    ('geteilte Widgets nicht mehr ausgeklinkt',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    _shared.setParent(None)',
     '                    pass   # MUTATION',
     'geteilte Widgets werden ausgeklinkt'),
    ('Zusatzkosten fehlen in der Kartenschaetzung',
     'eve_trader/ui/main_window.py',
     '"profit": net_sell_total - total_cost - _extra}',
     '"profit": net_sell_total - total_cost}',
     'Schnellschaetzung zieht die Zusatzkosten ab'),
    ('Messskript baut die Optionen selbst nach',
     'messung_bau_vs_bauplan.py',
     '    opts = win._bau_scan_build_opts(recipes)',
     '    opts = {}   # MUTATION',
     'Messskript nutzt die Scan-Optionen'),
    ("Kopier-Modus leitet 'own' wieder aus dem Plan ab",
     'eve_trader/ui/main_window.py',
     '                _r["status"], _r["status_txt"] = self._copy_mode_status(\n                    _r["missing"], _pq.get("built", 0), _r["need"], _r["own"])',
     '                _r["own"] = max(0, _r["need"] - _r["missing"])   # MUTATION\n                _r["status"], _r["status_txt"] = self._copy_mode_status(\n                    _r["missing"], _pq.get("built", 0), _r["need"], _r["own"])\n                _r["cart_qty"] = _r["missing"] or _r["need"]',
     "fasst 'own' nicht an"),
    ('Gruppen-Nachzug entfernt (spaete Items ohne Gruppe)',
     'eve_trader/ui/main_window.py',
     '            if _g_miss:\n                groups.update(industry.group_names(_g_miss))',
     '            if _g_miss:\n                pass   # MUTATION',
     'erweiterte ids-Set geholt'),
    ('Job-Kosten-Teile gehen nicht mehr auf',
     'eve_trader/industry.py',
     '        parts_out["scc"] = parts_out.get("scc", 0.0) + _p_scc',
     '        parts_out["scc"] = parts_out.get("scc", 0.0) + _p_scc * 0.5',
     'Teile ergeben EXAKT die Summe'),
    ('Orts-Zweig ignoriert die verknuepften Bau-Strukturen wieder',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    _sid = bs.get("link_structure_id")',
     '                    _sid = None   # MUTATION',
     'ALLE verknuepften Bau-Strukturen'),
    ('Ladefall loescht die geladene ME wieder',
     'eve_trader/ui/main_window.py',
     '                # Gespeicherter Plan OHNE Blaupausen-Nutzlast: nur die',
     '                self._bd_me = 0   # MUTATION\n                # Gespeicherter Plan OHNE Blaupausen-Nutzlast: nur die',
     'Ladefall ueberschreibt die geladene ME NICHT'),
    ('Bewertung ignoriert den duennen Markt',
     'eve_trader/ui/main_window.py',
     '        if _vol and _vol < cls.BAU_VOL_DUENN:',
     '        if False:   # MUTATION',
     'duenner Markt schlaegt die gute Marge'),
    ('Ohne Treffer verschwindet der Grund im Tooltip',
     'eve_trader/ui/main_window.py',
     '        else:\n            self.build_status.setText(_full_status)',
     '        else:\n            self.build_status.setText("")   # MUTATION',
     'ohne Treffer bleibt der Grund sichtbar'),
    ('Rechtsklick fuettert wieder ein Geister-Feld',
     'eve_trader/ui/main_window.py',
     '        elif chosen is a_plan:\n            self._build_row_open_plan(self.b_table, row)',
     '        elif chosen is a_plan:\n            pass   # MUTATION',
     'Rechtsklick oeffnet direkt (normale Liste)'),
    ('Suchen-Knopf haengt in keinem Layout mehr (unsichtbar)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        btn_row.addWidget(self.b_compute_btn, 1)',
     '        pass   # MUTATION',
     'Knopf haengt in der Strategie-Karte'),
    ('Capital-Sektion klebt wieder unter der normalen Liste',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        self.b_cap_wrap.setVisible(False)',
     '        self.b_cap_wrap.setVisible(True)   # MUTATION',
     'Capital-Karte startet unsichtbar'),
    ('Karten kleben wieder ueber der Trefferliste',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        self.b_side.addWidget(b_strat_card)\n        self.b_side.addWidget(b_filter_card)',
     '        root.addWidget(b_strat_card)   # MUTATION\n        root.addWidget(b_filter_card)',
     'sitzen in der Seitenspalte'),
    ('Tote Kopier-Zusage kehrt ins Label zurueck',
     'eve_trader/ui/main_window.py',
     '        if iv:',
     '        _cp = self._struct_extra_rig_pct(s, "copy")\n        if _cp:\n            bonuses.append(f"Kopie {_cp:.0f}% (noch nicht in Baurechnung genutzt)")   # MUTATION\n        if iv:',
     "keine 'noch nicht genutzt'-Zeilen mehr"),
    ('Gestrichenes Margen-Preset kehrt zurueck',
     'eve_trader/ui/main_window.py',
     '          "pmax": 0, "reactions": True}),',
     '          "pmax": 0, "reactions": True}),\n        ("Liquide Massenware (T1)",   # MUTATION\n         {"window": 30, "margin": 5, "vol": 500, "tech": "t1",\n          "pmin": 0, "pmax": 1000000, "only_cap": False}),',
     "'Liquide Massenware' ist gestrichen"),
    ('Fehlende Historie faellt wieder still raus',
     'eve_trader/scanner.py',
     'if daily_vol < min_vol and not (vol_unknown and mode == "build"):',
     'if daily_vol < min_vol:   # MUTATION',
     'Tor unterscheidet nach Modus'),
    ('Unbekannter Absatz wird als Traum-Treffer verkauft',
     'eve_trader/ui/main_window.py',
     '        if d.get("vol_unknown"):',
     '        if False:   # MUTATION',
     'fehlende Historie -> Absatz unbekannt'),
    # Fuel muss VOR die Reaktionen, die es verbrauchen (Nutzer, Sitzung 8).
    ('Fuel faellt zurueck zu den Komponenten (hinter seine Verbraucher)',
     'eve_trader/industry.py',
     '        elif j.get("is_fuel") or j.get("tid") in _fuel:',
     '        elif False:   # MUTATION',
     'Fuel Block steht in der eigenen Treibstoff-Stufe'),
    # Die ANZEIGE-Reihenfolge im Runplaner ist die, die der Nutzer abarbeitet.
    # (Die Schleife in industry.schedule_build ist dafuer NICHT der Hebel - die
    # Stufen rechnen unabhaengig, ein Umsortieren dort aendert nichts am
    # Ergebnis. Genau das hat die Rotprobe gezeigt: erster Versuch war blind.)
    ('Runplaner zeigt Treibstoff erst nach den Reaktionen',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        for stage in ("fuel", "reaction_1", "reaction_2", "component", "end"):',
     '        for stage in ("reaction_1", "reaction_2", "fuel", "component", "end"):   # MUTATION',
     'Runplaner zeigt Treibstoff VOR den Reaktionen'),
    # ORDER-FARBEN (Sitzung 8, Nutzer): ROT = Gebuehren fressen Gewinn,
    # VIOLETT = ueberboten. Wer es zuruecktauscht, kehrt die Warnstufen um.
    ('Status-Farben verdreht: Verlust gruen, Handlung rot',
     'eve_trader/ui/main_window.py',
     '            st_col = (theme.RED if loss else theme.AMBER) if flag else theme.GREEN',
     '            st_col = (theme.AMBER if loss else theme.RED) if flag else theme.GREEN   # MUTATION',
     'Status traegt die Warnfarbe'),
    # TRADING-TABS (Sitzung 8): Feinfilter muessen ZU starten - offen ist
    # exakt das ueberladene Bild, das der Nutzer loswerden wollte.
    ('Feinfilter starten wieder aufgeklappt',
     'eve_trader/ui/main_window.py',
     '''d_filter_card = self._collapsible(t("FINE FILTERS (OPTIONAL)"), ctl, expanded=False)''',
     '''d_filter_card = self._collapsible(t("FINE FILTERS (OPTIONAL)"), ctl)   # MUTATION''',
     'alle drei Feinfilter starten ZUGEKLAPPT'),
    # ORDER-UPDATE (Sitzung 8): der Bilder-Rueckruf darf NIE wieder auf den
    # ESI-Voll-Reload zeigen - sonst laedt jedes fehlende Icon die Orders neu.
    ('Bilder-Nachtrag laedt die Orders wieder komplett aus ESI',
     'eve_trader/ui/main_window.py',
     '        self._icon_prefetch_pending(self._rerender_order_tables)',
     '        self._icon_prefetch_pending(self._load_order_mods)   # MUTATION',
     'Bilder-Nachtrag zeichnet NUR neu'),
    # VERKAUFSLISTE (Sitzung 8): dritte _tool_pairs-Instanz - reisst die
    # Verkabelung, sind drei Aktionen still tot.
    ('Verkaufslisten-Menue drueckt die Knoepfe nicht mehr',
     'eve_trader/ui/main_window.py',
     """        self._sl_tool_pairs = ((_sl_load_act, refresh),
                               (_sl_check_act, check),
                               (_sl_clear_act, clear))
        for _a, _b in self._sl_tool_pairs:
            _a.setToolTip(_b.toolTip())
            _a.triggered.connect(_b.click)""",
     """        self._sl_tool_pairs = ((_sl_load_act, refresh),
                               (_sl_check_act, check),
                               (_sl_clear_act, clear))
        for _a, _b in self._sl_tool_pairs:
            _a.setToolTip(_b.toolTip())   # MUTATION""",
     'alle drei Menue-Aktionen rufen ihre Handler'),
    ('Marge rutscht wieder hinter die anderen Kennzahlen',
     'eve_trader/ui/main_window.py',
     """        for c in (self.pk_margin_c, self.pk_net_c, self.pk_rev_c,
                  self.pk_trades_c, self.pk_fees_c):""",
     """        for c in (self.pk_net_c, self.pk_rev_c, self.pk_trades_c,
                  self.pk_margin_c, self.pk_fees_c):   # MUTATION""",
     'an Position 0 der Kennzahlen-Zeile'),
    # CORP-FENSTER (Sitzung 8): der falsche Endpunkt oeffnet stillschweigend
    # das FALSCHE Fenster - Markt statt Corp-Info.
    ('Corp-Knopf oeffnet wieder das Marktfenster',
     'eve_trader/esi.py',
     '    url = f"{config.ESI_BASE}/ui/openwindow/information/"',
     '    url = f"{config.ESI_BASE}/ui/openwindow/marketdetails/"   # MUTATION',
     'es gibt den information-Endpunkt'),
    ('Namensaufloesung faellt weg (feste ID-Annahme)',
     'eve_trader/ui/main_window.py',
     '            corp_id = esi.resolve_corp_id(config.DONATION_CORP)',
     '            corp_id = 98000000   # MUTATION',
     'der Corp-Name wird zur Laufzeit aufgeloest'),
    ('Ruhende Reiter verlieren ihren Amber-Rahmen',
     'eve_trader/ui/main_window.py',
     '            f"border:1px solid {theme.AMBER_DIM}; border-bottom:none; "',
     '            f"border:1px solid {theme.BORDER}; border-bottom:none; "   # MUTATION',
     'ruhende Reiter haben schon einen Amber-Rahmen'),
    ('Aktiver Reiter faellt zurueck auf Cyan',
     'eve_trader/ui/main_window.py',
     '            f"#NavTab:checked{{background:{theme.BG}; color:{theme.AMBER}; "',
     '            f"#NavTab:checked{{background:{theme.BG}; color:{theme.CYAN}; "   # MUTATION',
     'der aktive Reiter ist AMBER, nicht Cyan'),
    ('Zeilenhoehe wieder geraten statt gemessen (Knopf beschnitten)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     """                            _hoehe = max(34, _cw.sizeHint().height() + 10)""",
     '                            _hoehe = 30   # MUTATION',
     'die Zeile ist hoch genug fuer den Knopf'),
    # BAUPLAN-POPUP (Sitzung 8, zweimal gemeldet): kehrt der Dialog zurueck,
    # rutscht der Bauplan beim Oeffnen wieder in den Hintergrund.
    ('Popup beim Bauplan-Oeffnen kehrt zurueck',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    self._flash_tip(_txt("no blueprints of your own"))',
     """                    QMessageBox.information(
                        self, "Alles aus ESI laden", "Keine eigenen Blaupausen")""",
     'der automatische ESI-Lauf zeigt KEIN Popup mehr'),
    ('Bauplan wird nach dem ESI-Lauf nicht mehr nach vorne geholt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     """                QTimer.singleShot(0, lambda: dlg.raise_()
                                  or dlg.activateWindow())

            def _fail(msg):""",
     "            def _fail(msg):",
     'holt den Bauplan danach wieder nach vorne'),
    # LOGO KOMMT SEIT SITZUNG 11 AUS assets/logo.png (Nutzer-Vorlage).
    # Die beiden alten Mutationen (Gold-Verlauf, Waben-Innenkante) sind
    # entfallen: sie zielten auf das GEZEICHNETE Logo, das jetzt nur noch
    # Rueckfallebene ist. Eine Mutation ohne lebende Zusage waere ein
    # Waechter vor einer offenen Tuer.
    ('Bilddatei des Logos wird nicht mehr benutzt',
     'eve_trader/ui/icons.py',
     '        _pfad = theme.asset_pfad("logo.png")',
     '        _pfad = theme.asset_pfad("gibtesnicht.png")',
     'das angezeigte Logo IST die Bilddatei'),

    ('ohne Bilddatei bleibt das Logo leer',
     'eve_trader/ui/icons.py',
     "    if pm is None:\n        pm = QPixmap(int(groesse), int(groesse))",
     "    if pm is None and False:\n        pm = QPixmap(int(groesse), int(groesse))",
     'ohne Bilddatei gibt es trotzdem ein Logo'),

    # LOGO (Sitzung 8): die zwei Orte, an denen es still verschwinden kann.
    ('Fenster verliert sein Symbol (nacktes Python-Zeichen)',
     'eve_trader/ui/main_window.py',
     '        self.setWindowIcon(icons.logo_icon())',
     '        pass   # MUTATION',
     'das Fenster traegt ein Symbol'),
    # NACHGEZOGEN (Sitzung 11): das Logo wird nicht mehr beim Aufbau auf
    # feste 30 px gesetzt, sondern nachtraeglich auf die gemessene
    # Sidebar-Breite. Der alte Anker existiert nicht mehr.
    ('Logo verschwindet aus dem Sidebar-Kopf',
     'eve_trader/ui/main_window.py',
     '                logo.setPixmap(icons.logo_pixmap(breite))',
     '                pass   # MUTATION',
     'das Logo nutzt die Sidebar-Breite'),

    ('Logo bleibt winzig statt die Sidebar zu nutzen',
     'eve_trader/ui/main_window.py',
     '            breite = max(96, min(sb.width() - 20, 240))',
     '            breite = 30',
     'es ist deutlich groesser als die alten 30 px'),

    ('Logo waechst unbegrenzt (Werkzeugliste faellt aus dem Fenster)',
     'eve_trader/ui/main_window.py',
     '            breite = max(96, min(sb.width() - 20, 240))',
     '            breite = max(96, sb.width() - 20)',
     'aber nach oben begrenzt'),
    # ANZAHL AM KNOPF (Sitzung 8): faellt sie weg, sieht man wieder nicht,
    # wie oft man dieselbe Zahl braucht.
    ('Anzahl vor dem Kopier-Knopf verschwindet',
     'eve_trader/ui/mw_bauplan_tabs.py',
     """                                _mal = QLabel(f"{_anz}\\u00d7")""",
     '                                _mal = QLabel("")   # MUTATION',
     'die Anzahl steht als eigenes Label VOR dem Knopf'),
    # KOPIER-KNOEPFE + PFEILE (Sitzung 8, Nutzer-Komfort).
    ('Kopier-Knopf kopiert mehr als die nackte Zahl',
     'eve_trader/ui/main_window.py',
     '        _QApp.clipboard().setText(str(int(runs)))',
     '        _QApp.clipboard().setText(f"{int(runs)} Runs")   # MUTATION',
     'kopiert wird die NACKTE Zahl'),
    ('Spinbox-Pfeile verschwinden wieder',
     'eve_trader/ui/theme.py',
     """QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url({_SPIN_UP}); width: 11px; height: 11px;
}}""",
     '/* MUTATION */',
     'die Spinbox-Pfeile haben eigene Grafiken'),
    # EINGABE-TOD (Sitzung 8, Nutzer: "ich kann hier gar nichts eingeben"):
    # haengen die Regler wieder am vollen Rebuild, zerstoert der erste
    # Tastendruck das Eingabefeld.
    ('Kopien-Regler haengt wieder am vollen Rebuild',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            self._inv_kopien.valueChanged.connect(_split_refresh)',
     '            self._inv_kopien.valueChanged.connect(\n                lambda *_a: _on_manual_change())   # MUTATION',
     'die Regler loesen eine Neuberechnung aus'),
    ('Einordnung der Items verschwindet aus der Diagnose',
     'eve_trader/ui/main_window.py',
     '            self._bd_struct_diag[activity] = _u[:4]',
     '            pass   # MUTATION',
     'die Einordnung der Items wird miterfasst'),
    # VERKAUFSLISTE (Sitzung 8): der Weg zurueck nach "Liste leeren" und
    # die Ingame-Grenze.
    ('Aktion "Aus Portfolio fuellen" verschwindet wieder',
     'eve_trader/ui/main_window.py',
     '        _sl_fill_act.triggered.connect(self._sell_fill_from_portfolio)',
     '        pass   # MUTATION',
     'und sie ist mit dem Handler verbunden'),
    ('Ingame-Grenze wird auf einen Fantasiewert gesetzt',
     'eve_trader/ui/main_window.py',
     '    SELL_LIMIT = 50',
     '    SELL_LIMIT = 999   # MUTATION',
     'die Ingame-Grenze steht zentral und ist 50'),
    # SIDEBAR-BREITE (Sitzung 8, zweimal gemeldet): faellt die Messung weg,
    # ist der Schriftzug auf fremden Schriften wieder beschnitten.
    ('Sidebar-Breite wird nicht mehr gemessen',
     'eve_trader/ui/main_window.py',
     '        QTimer.singleShot(0, self._sidebar_breite_anpassen)',
     '        pass   # MUTATION',
     'gemessen wird NACH dem Aufbau'),
    # STRUKTUR-WAHL (Sitzung 8, Nutzer-Frage "warum Dockside und nicht
    # Capslock?"): faellt die Begruendung weg, ist die Wahl wieder Blackbox.
    ('Struktur-Wahl merkt sich keine Begruendung mehr',
     'eve_trader/ui/main_window.py',
     """            self._bd_struct_choice[activity] = (
                ([(t("{name} (fixed assignment)").format(
                       name=_fest.get('name', '?')),
                   round(benefit(_fest), 2))] if _fest is not None else [])
                + [(x.get("name", "?"), round(benefit(x), 2))
                   for x in ranked
                   if _fest is None or x.get("id") != _fest.get("id")])""",
     '            self._bd_struct_choice[activity] = []   # MUTATION',
     'merkt sich die Rangliste MIT Nutzen-Werten'),
    # KOPIEN FUERS BAUEN (Sitzung 8): die Aufteilung MUSS der des
    # Runplaners entsprechen - sonst zieht der Nutzer die falschen Kopien.
    ('Kopien-Aufteilung weicht vom Runplaner ab (Rest falsch verteilt)',
     'eve_trader/industry.py',
     '        teile = [basis + 1] * rest + [basis] * (njobs - rest)',
     '        teile = [basis] * njobs   # MUTATION',
     'die Run-Gruppen stimmen mit dem Runplaner ueberein'),
    ('Kopienzahl zaehlt Items statt Jobs',
     'eve_trader/industry.py',
     '        blaupausen = len(e["teile"])',
     '        blaupausen = 1   # MUTATION',
     '16 Jobs -> 16 Blaupausen'),
    # NUTZER-FUND (Bild 3): bei Rigs kommen die Endprodukt-BPCs aus der
    # INVENTION - faellt der Filter, raet das Tool, sie zu kopieren.
    ('Invention-Ziele werden wieder als Kopie-Bedarf gelistet',
     'eve_trader/industry.py',
     '        if tid is None or tid in (ohne_tids or ()):',
     '        if tid is None:   # MUTATION',
     'Invention-Ziele werden ausgeschlossen'),
    ('Original wird nicht mehr angerechnet (eine Kopie zu viel)',
     'eve_trader/industry.py',
     '        kopien = blaupausen - 1 if hat_original else blaupausen',
     '        kopien = blaupausen   # MUTATION',
     'mit Original in der Hand sind es 15 Kopien'),
    # LEITZAHL IM INVENTION-TAB (Sitzung 8): "das ist die Zahl, die ich
    # ingame eingeben muss" - schrumpft sie auf Fliesstext, ist der Tab
    # wieder eine Bleiwueste.
    ('Leitzahl schrumpft auf normale Textgroesse',
     'eve_trader/ui/mw_bauplan_tabs.py',
     """                        f'<div style="font-size:26px;font-weight:800;'
                        f'color:{theme.AMBER};font-family:{theme.MONO};'
                        f'line-height:1.05;">{ap["confident_attempts"]}'""",
     """                        f'<div style="font-size:11px;'   # MUTATION
                        f'color:{theme.MUTED};'
                        f'">{ap["confident_attempts"]}'""",
     'und zwar in Kennzahl-Groesse, nicht als Fliesstext'),
    # KOPIEN-AUFTEILUNG (Sitzung 8): die zwei Rueckbauten, die den Nutzen
    # still zerstoeren wuerden.
    ('Aufteilung ignoriert die Slot-Grenze (verspricht zu viel parallel)',
     'eve_trader/industry.py',
     '    parallel = min(n, frei)',
     '    parallel = n   # MUTATION',
     'mit 3 Slots laufen trotz 10 Kopien nur 3 parallel'),
    ('Kopier-Deckel wird ignoriert (Kopien mit zu vielen Runs)',
     'eve_trader/industry.py',
     """    if max_runs_je_kopie:
        runs_je = min(runs_je, int(max_runs_je_kopie))""",
     '    if False:   # MUTATION\n        runs_je = min(runs_je, int(max_runs_je_kopie))',
     'ein Kopier-Deckel erzwingt mehr Kopien'),
    # REAKTIONS-RIG (Sitzung 8, NUTZER-MESSUNG): kehrt die Intermediate-
    # Ausnahme zurueck, plant das Tool 2 % zu viel Material fuer jede
    # Intermediate-Reaktion ein - stumm und dauerhaft.
    ('Intermediate-Reaktionen verlieren den Reaktor-Rig wieder',
     'eve_trader/ui/main_window.py',
     """        if not s or not item_doms:
            return 0.0
        _, bonus = self._rig_catalog()""",
     """        if not s or not item_doms:
            return 0.0
        if "reaction_intermediate" in item_doms:   # MUTATION
            return 0.0
        _, bonus = self._rig_catalog()""",
     'Intermediate-Reaktion bekommt den Reaktor-Rig'),
    # NAVIGATION (Sitzung 8, Runde 2): zeigt die Symbol-Karte wieder auf
    # Textzeichen, sind die Reiter stumm (Icon leer, Zeichen weg).
    ('Navigations-Karte zeigt wieder auf Textzeichen',
     'eve_trader/ui/main_window.py',
     '        "portfolio": "chart", "shopping": "cart", "sell": "coins",',
     '        "portfolio": "\u25ae", "shopping": "\u25a4", "sell": "\u25a5",   # MUTATION',
     'jeder Navigations-Eintrag zeigt auf ein echtes Symbol'),
    # SYMBOLE IM EINSATZ (Sitzung 8): faellt ein Icon weg, steht der Knopf
    # nackt da - und mit zurueckkehrendem Emoji haette man beides doppelt.
    ('Werkzeuge-Knopf verliert sein Symbol',
     'eve_trader/ui/main_window.py',
     """        _sh_tools_btn = QPushButton(t("Tools"))
        _sh_tools_btn.setIcon(icons.icon("menu"))""",
     '        _sh_tools_btn = QPushButton(t("Tools"))   # MUTATION',
     'der Werkzeuge-Knopf traegt selbst ein Symbol'),
    # SYMBOL-ZUSTAENDE (Sitzung 8): faellt die Aufhellung weg, sieht man im
    # Augenwinkel nicht mehr, was gerade aktiv ist.
    ('Aktive Symbole werden nicht mehr aufgehellt',
     'eve_trader/ui/icons.py',
     """        ic.addPixmap(pixmap(name, theme.ICON_ACTIVE, groesse, strich),
                     QIcon.Active)""",
     '        pass   # MUTATION',
     'aktiv ist HELLER als Ruhe'),
    ('Symbole leuchten wieder cyan statt ruhig zu begleiten',
     'eve_trader/ui/theme.py',
     'ICON = "#C9A06A"             # Ruhe: Standard-Ton aller Symbole',
     'ICON = "#3EE5CE"   # MUTATION',
     'der Symbol-Ton ist lesbar, aber kein Leuchtakzent'),
    # SYMBOL-SET (Sitzung 8): die Theme-Faerbung ist der ganze Witz - wird
    # sie hart verdrahtet, sind Zustandsfarben (Amber/Rot) wirkungslos.
    ('Symbole werden hart eingefaerbt (Theme-Farbe wirkungslos)',
     'eve_trader/ui/icons.py',
     "f'<path d=\"{pfad}\" fill=\"none\" stroke=\"{farbe or theme.ICON}\" '",
     "f'<path d=\"{pfad}\" fill=\"none\" stroke=\"{theme.ICON}\" '   # MUTATION",
     'die Farbe kommt von aussen'),
    # INDUSTRIE-SCHRIFT (Sitzung 8): faellt die Kette auf eine fest
    # verdrahtete Familie zurueck, ist die Schrift-Wahl wirkungslos.
    ('Schrift-Kette wird wieder fest verdrahtet',
     'eve_trader/ui/theme.py',
     "FONT_STACK = ['\"Bahnschrift\"', '\"Segoe UI\"', '\"Inter\"', \"sans-serif\"]",
     "FONT_STACK = ['\"Segoe UI\"', \"sans-serif\"]   # MUTATION",
     'die Schrift-Kette beginnt mit der Industrie-Schrift'),
    # KNOPF-BESCHRIFTUNG (Sitzung 8, Nutzer: "Kontrastprobleme"): faellt sie
    # auf CYAN zurueck, steht Cyan auf Cyan - matschig.
    ('Primary-Beschriftung faellt auf Cyan zurueck (Cyan auf Cyan)',
     'eve_trader/ui/theme.py',
     'CYAN_ON_FILL = "#DFFAF4"',
     'CYAN_ON_FILL = "#3EE5CE"   # MUTATION',
     'die Beschriftung darauf ist deutlich lesbar'),
    ('Sidebar-Mindestbreite faellt unter das Noetige',
     'eve_trader/ui/main_window.py',
     '        sidebar.setMinimumWidth(232)',
     '        sidebar.setMinimumWidth(150)   # MUTATION',
     'die Mindestbreite bleibt als Untergrenze bestehen'),
    # KNOPF-LEUCHTKRAFT (Sitzung 8): wird die Akzentflaeche wieder voll
    # cyan, blendet jeder Hauptknopf gegen den dunklen Grund.
    ('Akzentflaeche leuchtet wieder voll (Scheinwerfer-Knoepfe)',
     'eve_trader/ui/theme.py',
     'CYAN_FILL = "#15514A"        # ruhige Akzentflaeche (Primary-Knopf)',
     'CYAN_FILL = "#3EE5CE"   # MUTATION',
     'die Akzentflaeche blendet nicht'),
    # FARB-WAECHTER (Sitzung 8): die drei Zusagen der Palette.
    ('Hintergrund kippt ins komplette Schwarz',
     'eve_trader/ui/theme.py',
     'BG = "#080D16"        # Tiefes Blauschwarz - Weltraum, nicht Loch',
     'BG = "#000000"   # MUTATION',
     'der Hintergrund ist kein Schwarz'),
    ('Panels verschwinden im Hintergrund (alles ein dunkler Brei)',
     'eve_trader/ui/theme.py',
     'PANEL = "#16273B"     # Karten/Panels: kuehles Marine',
     'PANEL = "#0A1019"   # MUTATION',
     'Panels heben sich vom Hintergrund ab'),
    ('Nebentext wird unlesbar dunkel',
     'eve_trader/ui/theme.py',
     'MUTED = "#9DB4C6"',
     'MUTED = "#2A3540"   # MUTATION',
     'MUTED auf BG ist gut lesbar'),
    # REITER-FLAECHE (Sitzung 8): werden sie wieder transparent, sehen sie
    # aus wie Beschriftung statt wie Knoepfe.
    ('Reiter werden wieder transparent (nicht als klickbar erkennbar)',
     'eve_trader/ui/main_window.py',
     '            f"color:{theme.MUTED}; background:{theme.PANEL2}; "',
     '            f"color:{theme.MUTED}; background:transparent; "   # MUTATION',
     'die Reiter haben eine eigene Flaeche'),
    # ABO-WAECHTER (Sitzung 8): kehrt irgendein Abo-Element zurueck, muss
    # aa172 rot werden.
    ('Testmodus-Knopf kehrt in die Oberflaeche zurueck',
     'eve_trader/ui/main_window.py',
     '        howto = QPushButton("\\u2665 " + t("Donate"))',
     '        howto = QPushButton("Testmodus")   # MUTATION',
     "kein 'Testmodus' mehr in der Oberflaeche"),
    ('Spalten-Auswahl rutscht wieder nach links zu den Aktionen',
     'eve_trader/ui/main_window.py',
     """        head.addStretch()
        head.addWidget(_pf_cols_btn)""",
     """        head.addWidget(_pf_cols_btn)
        head.addStretch()   # MUTATION""",
     'Spalten-Auswahl sitzt ganz rechts'),
    # ABO-RUECKBAU (Sitzung 8): die Reiter muessen REITER bleiben (eigener
    # Stil) - faellt der Stil auf Knopf-Optik zurueck, ist die Nutzer-
    # Anforderung "man soll sehen, dass es Tabs sind" verletzt.
    ('Reiter sehen wieder aus wie normale Knoepfe',
     'eve_trader/ui/main_window.py',
     '            f"border-top-left-radius:10px; border-top-right-radius:10px; "',
     '            f"border-radius:8px; "   # MUTATION',
     'sehen wie Reiter aus: nur oben rund'),
    ('Reiter-Objektname faellt auf den alten Knopf-Stil zurueck',
     'eve_trader/ui/main_window.py',
     '            b.setObjectName("NavTab"); b.setCheckable(True)',
     '            b.setObjectName("NavPaid"); b.setCheckable(True)   # MUTATION',
     'die Reiter tragen den eigenen Tab-Stil'),
    # GEWINNE-MARGE (Sitzung 8): die Farb-Regel ist die Aussage. Wird sie
    # verdreht, liest man einen Verlust als Gewinn.
    ('Gewinne-Marge faerbt Verlust gruen',
     'eve_trader/ui/main_window.py',
     '            f"color:{theme.GREEN if avg_margin >= 0 else theme.RED}; "',
     '            f"color:{theme.RED if avg_margin >= 0 else theme.GREEN}; "   # MUTATION',
     'die Gewinne-Marge ist gross und vorzeichen-gefaerbt'),
    # PORTFOLIO-SPALTENWAHL (Sitzung 8): reisst die Haken-Verbindung, ist
    # die Auswahl eine Attrappe - Haken bewegen sich, Spalten nicht.
    ('Spalten-Haken schalten die Spalten nicht mehr',
     'eve_trader/ui/main_window.py',
     """            _act.toggled.connect(
                lambda on, c=_ci: self.pf_table.setColumnHidden(c, not on))""",
     '            pass   # MUTATION',
     'Haken entfernen versteckt die Spalte sofort'),
    ('Portfolio startet wieder mit allen Spalten (Ueberfluss)',
     'eve_trader/ui/main_window.py',
     '            self.pf_table.setColumnHidden(_ci, _ci not in _PF_STD)',
     '            self.pf_table.setColumnHidden(_ci, False)   # MUTATION',
     'genau die sind sichtbar, der Rest ist versteckt'),
    # VERKAUFSLISTEN-FUSSZEILE (Sitzung 8): rutscht der Zaehler wieder nach
    # rechts, ist er beim Gegenchecken wieder schlecht auffindbar.
    ('Item-Zaehler rutscht wieder nach rechts',
     'eve_trader/ui/main_window.py',
     """        tot = QHBoxLayout()
        tot.addWidget(self.sell_t_count)      # LINKS aussen
        tot.addStretch()""",
     """        tot = QHBoxLayout()
        tot.addStretch()
        tot.addWidget(self.sell_t_count)   # MUTATION""",
     'der Zaehler sitzt LINKS aussen'),
    # T1-KOPIEN-ZEILE (Sitzung 8): faellt sie aus dem Automatik-Zweig,
    # steht der Nutzer wieder ohne Kopie-Bedarf da.
    ('T1-Kopien-Zeile verschwindet aus dem Automatik-Zweig',
     'eve_trader/ui/mw_bauplan_tabs.py',
     """                            (t("T1 copies"),
                             t("{n} copy runs (1 attempt = 1 run, split as you like)").format(
                                 n=ap["confident_attempts"]),
                             theme.CYAN),""",
     '                            # MUTATION',
     'die T1-Kopien-Zeile steht in beiden Invention-Zweigen'),
    # TYPOGRAFIE-WAECHTER (Sitzung 8): schleicht sich eine Zwischengroesse
    # oder eine Hex-Farbe am Theme vorbei ein, muss aa170 rot werden.
    ('Zwischengroesse schleicht sich an der Skala vorbei ein',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '"color:{theme.AMBER}; font-weight:700; font-size:13px; padding:4px 0;")',
     '"color:{theme.AMBER}; font-weight:700; font-size:12px; padding:4px 0;")   # MUTATION',
     'ALLE Schriftgroessen kommen aus der Skala'),
    ('Zusage-Gruen wird wieder als Hex hart verdrahtet',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    status_col = theme.GREEN_BRIGHT',
     '                    status_col = "#7CE8A4"   # MUTATION',
     'keine Hex-Farben am Theme vorbei'),
    # GRUPPEN-RUECKFALL (Sitzung 8, Ferrogel-trotz-immer-bauen): faellt der
    # Rueckfall weg, landet ein Item ohne Markt-Gruppenname wieder beim
    # generischen "reactions"-Schluessel und wird still gekauft.
    ('Kategorien-Schluessel faellt wieder blind auf generisches reactions',
     'eve_trader/ui/main_window.py',
     """            if tid not in _gn:
                _gn.update(industry.group_names([tid]) or {tid: ""})
            g = _gn.get(tid, "") or \"\"""",
     '            pass   # MUTATION',
     'leerer Gruppenname -> SDE-Rueckfall'),
    # ICON-VERHUNGERUNG (Sitzung 8, Order-Update-Fund): wer die Wuensche
    # wieder VOR der Laeuft-schon-Pruefung leert, laesst den zweiten Tab
    # fuer die ganze Sitzung ohne Bilder.
    ('Zweiter Tab verliert seine Icon-Wuensche wieder (Verhungern)',
     'eve_trader/ui/main_window.py',
     """            if refresh_cb is not None:
                self._icon_prefetch_followup = refresh_cb
            return False""",
     """            self._icon_wanted = set()   # MUTATION
            return False""",
     "bei 'laeuft schon' bleiben die Wuensche STEHEN"),
    # RUNDE 4 (Sitzung 8, Nutzer-Umentscheidung): Marge/Gewinn kehren
    # sichtbar zurueck -> Fehlanzeigen bei Strategie-Mix. Festgenagelt.
    ('Marge- und Gewinn-Spalte werden wieder sichtbar (Fehlanzeigen)',
     'eve_trader/ui/main_window.py',
     """        self.sh_table.setColumnHidden(6, True)
        self.sh_table.setColumnHidden(8, True)""",
     '        pass   # MUTATION',
     'Marge- und Gewinn-Spalte sind ausgeblendet'),
    # RUNDE 3 (Sitzung 8): die Rechenbasis-Regel. Sofortkauf kostet KEINEN
    # Broker - wer ihn wieder draufschlaegt, macht jede Marge zu pessimistisch
    # und die Karte unten luegt rot.
    ('Sofortkauf zahlt wieder Kauf-Broker (Marge zu pessimistisch)',
     'eve_trader/ui/main_window.py',
     '                cost = buy_now_avg * qty',
     '                cost = buy_now_avg * qty * (1 + broker)   # MUTATION',
     'mit Orderbuch gilt die Order-Tiefe auf Sofortkauf-Basis'),
    # ITEM-BILDER IM WAGEN (Sitzung 8): ohne den Anstoss merkt der Wagen
    # fehlende Bilder nur vor und holt sie NIE - exakt der Nutzer-Fund.
    ('Wagen merkt Bilder vor, stoesst den Nachtrag aber nie an',
     'eve_trader/ui/main_window.py',
     '        self._icon_prefetch_pending(self._render_shopping)',
     '        pass   # MUTATION',
     'der Wagen stoesst den Bilder-Nachtrag an'),
    # AUFRAEURUNDE 2 (Sitzung 8): fliegt das Vorschlag-Panel aus dem Menue,
    # sind Prozentfeld und Uebernehmen unerreichbar - still.
    ('Vorschlag-Panel fliegt aus dem Werkzeuge-Menue',
     'eve_trader/ui/main_window.py',
     '        self._sh_tools_menu.insertAction(self._sh_tools_sep, self._sh_sug_wa)',
     '        pass   # MUTATION',
     "das Vorschlag-Panel haengt als Widget-Aktion im Menue"),
    # EINKAUFSWAGEN-WERKZEUGE (Sitzung 8, Layout-Programm): reisst die
    # Menue-zu-Knopf-Verkabelung, sind vier Aktionen still tot.
    ('Werkzeuge-Menue drueckt die Knoepfe nicht mehr',
     'eve_trader/ui/main_window.py',
     """        self._sh_tool_pairs = ((_sh_load_act, load), (_sh_check_act, check),
                               (_sh_sugg_act, sugg_btn),
                               (_sh_clear_act, clear))
        for _a, _b in self._sh_tool_pairs:
            _a.setToolTip(_b.toolTip())
            _a.triggered.connect(_b.click)""",
     """        self._sh_tool_pairs = ((_sh_load_act, load), (_sh_check_act, check),
                               (_sh_sugg_act, sugg_btn),
                               (_sh_clear_act, clear))
        for _a, _b in self._sh_tool_pairs:
            _a.setToolTip(_b.toolTip())   # MUTATION""",
     'Menue-Aktion drueckt den Knopf'),
    # SORTIER-GIFT (Sitzung 8, Capital-Fund): ein blankes
    # sortIndicatorChanged.disconnect() trennt auch Qts interne
    # Sortier-Verbindung - Headerklick aendert nur noch den Pfeil.
    ('Blankes disconnect() kehrt in die Capital-Tabelle zurueck',
     'eve_trader/ui/main_window.py',
     """            _alt_cap = getattr(self, "_cap_bars_sort_slot", None)
            if _alt_cap is not None:
                try:
                    _hdr_cap.sortIndicatorChanged.disconnect(_alt_cap)
                except (TypeError, RuntimeError):
                    pass""",
     """            try:
                _hdr_cap.sortIndicatorChanged.disconnect()
            except (TypeError, RuntimeError):
                pass   # MUTATION""",
     'NIRGENDS mehr ein blankes sortIndicatorChanged.disconnect()'),
    # FEHLBEDARF-VORSCHAU (Sitzung 8): die zwei Rueckbauten, die die
    # Vorschau leise wertlos machen wuerden.
    ('Vorschau vergisst die Rest-Produktion (Daueralarm auf alles)',
     'eve_trader/ui/mw_helpers.py',
     '        prod = rem.get(m, 0) * int((out_qty_map or {}).get(m, 1) or 1)',
     '        prod = 0   # MUTATION',
     'Rest-Produktion eigener Runs wird gutgeschrieben'),
    ('Vorschau ignoriert Geliefertes (Bedarf dauerhaft zu hoch)',
     'eve_trader/ui/mw_helpers.py',
     """    rem = {t: max(0, int(r or 0) - int((delivered or {}).get(t, 0) or 0))
           for t, r in (build_runs or {}).items()}""",
     """    rem = {t: max(0, int(r or 0))
           for t, r in (build_runs or {}).items()}   # MUTATION""",
     'voll gelieferte Items erzeugen keinen Rest-Bedarf'),
    # HANGAR vs. PIPELINE (Sitzung 8, 805-Ferrogel-Vorfall): zaehlt die
    # Sofort-Start-Zusage die Pipeline wieder mit, verspricht sie Jobs, die
    # nicht starten koennen.
    ('Sofort-Start-Zusage zaehlt den Reaktor-Inhalt wieder als Hangar',
     'eve_trader/ui/mw_bauplan_tabs.py',
     """                _lager = (int(stock.get(m, 0) or 0)
                          - int(_virt.get(m, 0) or 0))""",
     '                _lager = int(stock.get(m, 0) or 0)   # MUTATION',
     'Sofort-Start-Zusage zieht die Pipeline vom Bestand AB'),
    # BLAUPAUSEN-REFRESH (Sitzung 8): die zwei stillen Rueckbauten.
    ('Neue Blaupausen erreichen den Runplaner wieder nicht',
     'eve_trader/ui/mw_bauplan_fenster.py',
     """                if result.get("owned_bp") is not None:
                    self._bd_owned_bp_cache = result["owned_bp"]""",
     '                pass   # MUTATION',
     'der done-Pfad erneuert den Cache nur bei vollem Erfolg'),
    ('Teilliste ersetzt bei Fehlschlag den vollen Cache',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''return {"agg": agg, "assets": _assets_only,
                            "owned_bp": owned_bp_fresh if bp_fetch_ok else None,''',
     '''return {"agg": agg, "assets": _assets_only,
                            "owned_bp": owned_bp_fresh,   # MUTATION''',
     'gescheiterter Charakter ersetzt den Cache NICHT'),
    # ESI-AUSBLENDUNG (Sitzung 8, "nur ich darf streichen"): die zwei
    # Rueckbauten, die den Nutzer wieder blind machen wuerden.
    ('Laufende Jobs zaehlen nicht mehr zur Deckung (Plan schrumpft nie)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     # ANKER UMGEZOGEN (Sitzung 14): die Zusage aus Sitzung 8 gilt
     # unveraendert, sitzt aber nicht mehr in der Ausblend-Rechnung (die ist
     # mit dem Ausblenden weggefallen), sondern im Rest-Budget.
     '''            _fertig += sum(int(_j.get("runs") or 0) for _j in''',
     '''            _fertig += 0 * sum(int(_j.get("runs") or 0) for _j in''',
     'laufende Jobs zaehlen zur Deckung'),
    ('ESI-Deckung setzt keinen Zustand (Zeile sieht wieder nach Arbeit aus)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     # ANKER ZWEIMAL UMGEZOGEN (Sitzung 14). Erst zeigte diese Mutation auf
     # die Zaehl-Zeile (mit dem Ausblenden weggefallen), dann auf einen
     # zweiten Zustands-Block, der sich als redundant herausstellte. Jetzt
     # auf den EINEN verbliebenen Weg.
     '''                        _zustand = ("laeuft"''',
     '''                        _zustand = (None or "" and "laeuft"   # MUTATION''',
     # ERWARTUNG NACHGEZOGEN (Sitzung 14, Umfeld-Rotprobe): die Mutation
     # WIRD erkannt, aber von den Textproben, nicht von der funktionalen.
     # Grund: der Ersatzausdruck liefert bei geliefertem Material weiterhin
     # "fertig", der gruene Punkt kommt also. Scharf ist sie fuer die
     # Zusage, DASS der Zustand hier ueberhaupt bestimmt wird.
     'aa164 stattdessen bekommt die Zeile einen ZUSTAND'),
    # ESI-SICHTBARKEIT IM RUNPLANER (Sitzung 8): die zwei stillen
    # Rueckbauten - Teilfortschritt verschwindet / Geliefert-Stand wird
    # nicht mehr gefuellt. Beides liesse den Nutzer wieder blind bauen.
    ('ESI-Suffix kehrt in die Runplaner-Zeile zurueck',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                            iit.setForeground(0, QColor(theme.CYAN))''',
     '''                            iit.setText(0, iit.text(0)
                                        + f"  \\u00b7  ESI {_del_n}/"
                                          f"{int(a.get('runs') or 0)}")   # MUTATION
                            iit.setForeground(0, QColor(theme.CYAN))''',
     'das ESI-X/Y-Suffix bleibt aus der Zeile draussen'),
    ('Marker-Tor faellt weg - fremde Jobs faerben wieder violett',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                        if not _passt9 and sum(_lauf9) != _pl_runs9:
                            _active = []''',
     '''                        if False:   # MUTATION
                            _active = []''',
     'das Tor steht VOR der Marker-Entscheidung'),
    # --- aa199: Order-Update Verlust-Warnung ---
    ('Einstand-Auffuellen je Item entfaellt wieder',
     'eve_trader/ui/main_window.py',
     '''            for _tid9, _info9 in (_agg9 or {}).items():
                if not costs.get(_tid9):''',
     '''            for _tid9, _info9 in ({} or {}).items():   # MUTATION
                if not costs.get(_tid9):''',
     'der Einstand wird JE ITEM aus den Transaktionen aufgefuellt'),
    ('Order-Gebuehren fallen auf die globalen Prozente zurueck',
     'eve_trader/ui/main_window.py',
     '''                tax, broker = _fees_row9(char_id)''',
     '''                tax, broker = _tax_glob9, _brk_glob9   # MUTATION''',
     'die Gebuehren kommen je Zeile vom Order-Charakter'),
    # --- aa200: Langzeit-Gedaechtnis ---
    ('Charakter-Entfernen loescht die Transaktions-Historie wieder mit',
     'eve_trader/store.py',
     '''    with _conn() as c:
        c.execute("DELETE FROM characters WHERE character_id=?", (cid,))''',
     '''    with _conn() as c:
        c.execute("DELETE FROM transactions WHERE character_id=?", (cid,))   # MUTATION
        c.execute("DELETE FROM characters WHERE character_id=?", (cid,))''',
     'die Historie ueberlebt das Entfernen des Charakters'),
    # --- aa201: drei Portfolio-Zustaende ---
    ('Zwischenzustand "guter Preis" kehrt ins Portfolio zurueck',
     'eve_trader/ui/main_window.py',
     '''            elif not has_cost and at_price:
                signal, srank = t("● Hold"), 1''',
     '''            elif not has_cost and at_price:
                signal, srank = "● guter Preis", 1   # MUTATION''',
     'Zwischenzustand \'\u25cf guter Preis\' existiert nicht mehr'),
    ('VERKAUFEN verlangt wieder das Normalniveau',
     'eve_trader/ui/main_window.py',
     '''        sellable = has_cost and round(h.margin_pct, 1) >= target''',
     '''        _normal = self._normal_levels.get(h.type_id, 0)
        _at = bool(_normal) and h.jita_sell_min >= _normal * 0.98   # MUTATION
        sellable = _at and has_cost and round(h.margin_pct, 1) >= target''',
     'VERKAUFEN haengt NUR an Einstand + Ziel-Marge (+ nicht gelistet)'),
    ('Geliefert-Stand wird nicht mehr uebernommen',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            self._bd_runplan_delivered = dict(_auto_runs or {})',
     '            self._bd_runplan_delivered = {}   # MUTATION',
     'der Geliefert-Stand wird VOLL gemerkt'),
    # SCHNELL-FLIP-TRACKING (Sitzung 8): der (date, 0/1)-Zweitschluessel
    # sortiert bei identischem Zeitstempel den KAUF vor den Verkauf. Dreht
    # ihn jemand um, findet der Verkauf kein Los und faellt still aus den
    # Gewinnen - exakt die Sorge des Nutzers.
    ('Verkauf sortiert vor den Kauf (Flip verschwindet aus den Gewinnen)',
     'eve_trader/market.py',
     '    events = []\n    ordered = sorted(transactions, key=lambda x: (x["date"], 0 if x["is_buy"] else 1))',
     '    events = []\n    ordered = sorted(transactions, key=lambda x: (x["date"], 1 if x["is_buy"] else 0))   # MUTATION',
     'sogar bei identischem Kauf-/Verkaufs-Zeitstempel'),
    # "WENIGER EXCEL" (Sitzung 8): die zwei Rueckfaelle, die dem Nutzer
    # wirklich schaden wuerden. (a) Capital-Balken ohne Sortier-Neuzuordnung
    # -> Balken einer FREMDEN Zeile (die Materialien-Tab-Falle, dritte
    # Auflage). (b) no_price-Zweig weg -> ein Capital ohne Contract-Preis
    # bekaeme eine Bewertung aus dem Nichts.
    ('Capital-Balken kleben nach dem Sortieren an fremden Zeilen',
     'eve_trader/ui/main_window.py',
     '            _hdr_cap.sortIndicatorChanged.connect(self._cap_bars_sort_slot)',
     '            pass   # MUTATION',
     'Capital-Balken werden nach dem Sortieren neu gehaengt'),
    ('Capital ohne Contract-Preis bekommt eine erfundene Bewertung',
     'eve_trader/ui/main_window.py',
     '        if d.get("no_price"):',
     '        if False:   # MUTATION',
     'ohne Contract-Preis sagt der Balken das ehrlich'),
    # "KANN GEBAUT WERDEN" (Sitzung 8): der gefaehrlichste Rueckbau waere,
    # die Zutaten-am-Bau-Sperre zu entfernen - dann verspraeche der Tab
    # Startbereitschaft fuer Items, deren Zutaten erst NACH einem anderen
    # Job existieren (exakt der Ferrofluid-Engpass des Nutzers).
    # REZEPT-ZENSUS: wer die NULL/0-Erkennung entschaerft, laesst maskierte
    # Ausbeuten (or 1 -> bis 200-fach zu viele Runs) wieder unbemerkt durch.
    ('Zensus meldet NULL-Ausbeuten nicht mehr',
     'pruefe_rezepte.py',
     '    hart = [(bp, p, q) for bp, p, q in zeilen if q is None or q <= 0]',
     '    hart = []   # MUTATION',
     'NULL- und 0-Ausbeuten werden als FEHLER gemeldet'),
    # UPDATES-KNOPF (Sitzung 8): das war der gefundene Luegen-Pfad - NEIN
    # klicken, und der naechste Klick behauptet "Alles aktuell", obwohl die
    # Baurezepte veraltet sind. Der Merker darf nicht wieder verschwinden.
    ('Updates-Knopf vergisst das ausstehende Neuladen wieder',
     'eve_trader/ui/main_window.py',
     '            self.settings["sde_reload_ausstehend"] = (r != QMessageBox.Yes\n                                                      and sde_changed)',
     '            self.settings["sde_reload_ausstehend"] = False   # MUTATION',
     'NEIN setzt den Ausstehend-Merker statt still zu vergessen'),
    # KNOPF "REZEPTE PRUEFEN" (Sitzung 8): derselbe Fehlertyp wie beim
    # Verkaufslisten-Knopf - Job ohne Worker an _run. b2h drueckt wirklich.
    ('Rezepte-Knopf gibt den Job ohne Worker an _run (Absturz-Muster)',
     'eve_trader/ui/main_window.py',
     '        self._run(Worker(job), done, fail_cb=fail,\n                  label=_txt("Checking recipes \\u2026"))',
     '        self._run(job, done, fail_cb=fail,   # MUTATION\n                  label=_txt("Checking recipes \\u2026"))',
     'b2h Rezepte pruefen'),
    # REZEPT-PRUEFUNG (Sitzung 8): der Diff darf eine veraltete Ausbeute
    # nicht verschlucken - sonst wiegt das Werkzeug in falscher Sicherheit.
    ('SDE-Abgleich uebersieht veraltete Ausbeuten',
     'pruefe_rezepte.py',
     '    ausbeute = [(k, prod_alt[k], prod_neu[k])\n                for k in prod_alt.keys() & prod_neu.keys()\n                if prod_alt[k] != prod_neu[k]]',
     '    ausbeute = []   # MUTATION',
     'veraltete AUSBEUTE wird erkannt'),
    ('Startbereit trotz Zutat, die selbst erst gebaut wird',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            for m, jq in mats:\n                if build_runs.get(m):\n                    return False          # Zutat haengt selbst am Bau',
     '            for m, jq in mats:\n                if False:   # MUTATION\n                    return False',
     'eine Zutat, die selbst am Bau haengt, macht NICHT startbereit'),
    # "genau passen": die Zusage muss an den EXPORTIERTEN Planmengen haengen.
    # Wer build_mats wieder durch eine nachgebaute Rechnung ersetzt, faellt.
    ('Zusage rechnet die Mengen wieder selbst nach statt build_mats',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            mats = (plan.get("build_mats") or {}).get(tid)',
     '            mats = None   # MUTATION',
     'die Zusage prueft gegen die EXAKTEN Planmengen (build_mats)'),
    ('Zwei-Verbraucher-Kette verliert einen Verbraucher',
     'eve_trader/industry.py',
     '            demand[m] += jq',
     '            demand[m] = jq   # MUTATION',
     'Zwischenprodukt aggregiert BEIDE Verbraucher und zieht Bestand ab'),
    # NUTZER-ABSTURZ (Sitzung 8): `_run` erwartet ein Worker-OBJEKT, bekam
    # aber die nackte Job-Funktion. b2f pruefte nur, dass die Methode
    # EXISTIERT - das reichte nicht. b2g loest den Knopf jetzt wirklich aus.
    ('Job wird ohne Worker an _run gegeben (Nutzer-Absturz)',
     'eve_trader/ui/main_window.py',
     '        self._run(Worker(job), done, fail_cb=fail,\n                  label=t("Sell prices {hub} \\u2026").format(hub=hub_lbl))',
     '        self._run(job, done, fail_cb=fail,   # MUTATION\n                  label=t("Sell prices {hub} \\u2026").format(hub=hub_lbl))',
     'Verkaufspreise kopieren'),
    # UNTERBIETEN (Nutzer-Wunsch, Sitzung 8). Die alte Fassung rechnete die
    # Tick-Groesse immer aus dem AUSGANGSpreis - an der Zehnerpotenz war das
    # zu tief (999'000 statt 999'900) und bei billigen Items entstanden
    # ungueltige Preise (0,04999).
    ('Tick-Wechsel an der Zehnerpotenz faellt weg',
     'eve_trader/ui/mw_helpers.py',
     '            if abs(p - 10.0 ** d) < 1e-9:\n                tick = 10.0 ** (d - 4)     # Potenzgrenze: darunter feiner',
     '            if False:   # MUTATION\n                tick = 10.0 ** (d - 4)',
     'CCP-Ticks um 1 Mio exakt nachgebildet'),
    # ACHTUNG beim Aendern: `round(kand, 2)` als Mutation ist BLIND - das
    # zweite Netz (`if kand >= p`) faengt es ab und liefert doch 0,04. Die
    # Mutation muss das Abrunden GANZ weglassen, dann bleibt 0,04999 stehen -
    # ein Preis mit fuenf Nachkommastellen, den EVE wegrundet.
    ('Ungueltiger Preis mit mehr als zwei Nachkommastellen',
     'eve_trader/ui/mw_helpers.py',
     '        kand = math.floor(kand * 100.0 + 1e-6) / 100.0',
     '        kand = kand   # MUTATION',
     'billige Items werden wirklich unterboten'),
    ('Ausgefallene Zeile wird weggelassen statt markiert',
     'eve_trader/ui/mw_helpers.py',
     '                preise.append("?")\n                notizen.append(_txt("{name}: name not recognised").format(name=name))',
     '                notizen.append(_txt("{name}: name not recognised").format(name=name))',
     'genau eine Ausgabezeile je Eingabezeile'),
    # STRUKTUR JE BAU-STUFE (Nutzer-Wunsch, Sitzung 8). Drei Arten, das
    # wieder kaputtzumachen - jede muss auffallen.
    ('Endprodukt faellt wieder in den Komponenten-Topf',
     'eve_trader/ui/main_window.py',
     '        if endprodukt is not None and tid == endprodukt:\n            return "endproduct"',
     '        if False:   # MUTATION\n            return "endproduct"',
     'das Endprodukt ist eine eigene Stufe'),
    ('Reaktions-Stufen werden wieder zusammengeworfen',
     'eve_trader/ui/main_window.py',
     '            return ("reaction_2" if (stage_map or {}).get(tid, 1) == 2\n                    else "reaction_1")',
     '            return "reaction_1"   # MUTATION',
     'Composite-Reaktion ist Stufe 2'),
    # Ohne den Rueckfall verloere der Nutzer beim Update seine gespeicherte
    # Zuordnung - still, ohne Fehlermeldung.
    ('Alte Struktur-Zuordnung wird beim Update verworfen',
     'eve_trader/ui/main_window.py',
     '        sid = _amap.get(activity) or _amap.get(\n            self._STUFE_LEGACY.get(activity, ""), "")',
     '        sid = _amap.get(activity)   # MUTATION',
     'alte \'manufacturing\'-Zuweisung gilt fuer Komponenten'),
    # BESTANDS-STAND IM BAUPLAN-KOPF (Nutzer-Wunsch). Die Anzeige war voll
    # gebaut, aber von KEINER Pruefung gedeckt - sie haette still ausfallen
    # koennen. Diese drei Mutationen decken die drei Arten des Ausfalls ab.
    ('Bestands-Zeile haengt in keinem Layout (unsichtbar)',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        hv.addWidget(self._bd_esi_stand_lbl)',
     '        pass   # MUTATION',
     'Bestands-Zeile haengt im Fenster'),
    ('Unveraenderter Bestand gilt wieder als Aenderung',
     'eve_trader/store.py',
     '        if alt != fp:',
     '        if True:   # MUTATION',
     'unveraenderter Bestand verschiebt den Aenderungs-Zeitpunkt NICHT'),
    ('Gescheiterter Teil-Abruf schreibt wieder mit',
     'eve_trader/store.py',
     '    if not vollstaendig:\n        return asset_snapshot_info()',
     '    if False:   # MUTATION\n        return asset_snapshot_info()',
     'gescheiterter Teil-Abruf faelscht den Zeitpunkt nicht'),
    # FALCON-VORFALL, Teil 2: die Schiffsgroesse. Ohne sie schneidet sich ein
    # Schiff mit keinem groessenspezifischen Rig -> nie ein Rig-Bonus.
    ('Schiffsgroesse faellt aus der Rig-Zuordnung',
     'eve_trader/industry.py',
     '        return allgemein | {f"{stufe}_{groesse}_ship"}',
     '        return allgemein   # MUTATION',
     'T2-Cruiser ist ein Advanced-MEDIUM-Schiff'),
    # Freighter als Capital zu fuehren gaebe ihnen einen Rig-Bonus, den EVE
    # nicht gibt - derselbe Fehlertyp wie beim Falcon, nur andersherum.
    ('Freighter gilt wieder als Capital (Rig-Bonus zu viel)',
     'eve_trader/industry.py',
     '        if any(h in g for h in _RIG_CAP_SHIP_HINTS):',
     '        if any(h in g for h in _CAP_SHIP_HINTS):   # MUTATION',
     'Freighter ist fuer die Rig-Frage KEIN Capital'),
    # Unbekannte Gruppen raten statt markieren (gegen Arbeitsregel 6).
    ('Unbekannte Schiffsgruppe wird geraten statt markiert',
     'eve_trader/industry.py',
     '    return GROESSE_UNBEKANNT',
     '    return "medium"   # MUTATION',
     'unbekannte Schiffsgruppe wird markiert'),
    # FALCON-VORFALL (Sitzung 8): der optimistische Rig-Rueckfall rechnete den
    # Materialbedarf 4,2 % zu niedrig. Wer den Schalter zurueckdreht, muss ROT
    # sehen - sonst passiert derselbe Fehlbau nochmal.
    ('Rig-Rueckfall wieder optimistisch (Falcon-Vorfall)',
     'eve_trader/ui/main_window.py',
     '    _RIG_FALLBACK_T1 = False',
     '    _RIG_FALLBACK_T1 = True   # MUTATION',
     'Rueckfall ist ein benannter Schalter und steht auf AUS'),
    ('Platzhalter-Rezepte gelten wieder als baubar',
     'eve_trader/industry.py',
     '        if sum(q for _m, q in mats) <= 1:\n            return False',
     '        if False:   # MUTATION\n            return False',
     "'1x Tritanium'-Platzhalter ist NICHT baubar"),
    ('Vorton-Gruppen rutschen wieder in den Bau-Scan',
     'eve_trader/industry.py',
     '    return _gids_matching_from(names_by_gid, ("vorton", "condenser pack"))',
     '    return set()   # MUTATION',
     'Vorton-Gruppen werden erkannt'),
    ('Capital-Bau-Teile fluten wieder die T2-Liste',
     'eve_trader/industry.py',
     '    return _gids_matching_from(names_by_gid,\n                               ("capital construction components",))',
     '    return set()   # MUTATION',
     'Bau-Teile-Gruppen werden erkannt'),
    ('Drogen fluten wieder das Reaktionen-Preset',
     'eve_trader/ui/main_window.py',
     '                if _info_r and _info_r[1] in _booster_gids:',
     '                if False:   # MUTATION',
     'Reaktions-Zweig prueft die Booster-Sperrliste'),
    ('Reservierung schont den eigenen Plan nicht mehr',
     'eve_trader/ui/mw_helpers.py',
     '            if exclude_plan_id is not None and p.get("id") == exclude_plan_id:\n                continue',
     '            if False:   # MUTATION\n                continue',
     'Plan wird ausgenommen'),
    ('Neu-Speichern schaltet die Reservierung wieder still aus',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                          "reserve": bool(existing.get("reserve"))',
     '                          "reserve": False and bool(existing.get("reserve"))   # MUTATION',
     'Flag ueberlebt das Ueberschreiben'),
    ('Faction-Items ohne kaufbare BPO fluten wieder den T1-Scan',
     'eve_trader/ui/main_window.py',
     '            return _bpo_gate and bp[0] not in _bpo_ids',
     '            return False   # MUTATION',
     'T1-Zweig prueft die BPO am Markt'),
    ('Abhaken speichert wieder synchron je Signal',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                _sched_save_timer.start()   # entprellt: einmal am Ende',
     '                _sched_save_now()   # MUTATION',
     'gespeichert wird ENTPRELLT'),
    ('Kinder ziehen nicht mehr mit',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    _ch.setCheckState(0, _want)',
     '                    pass   # MUTATION',
     'Kinder werden mitgezogen'),
    ('Der gestrichene Alle-Materialien-Knopf kehrt zurueck',
     'eve_trader/ui/main_window.py',
     '            _b_miss = QPushButton(_txt("Copy missing materials"))',
     '            _b_all = QPushButton("\\U0001F4CB Alle Materialien kopieren")   # MUTATION\n            _b_all.clicked.connect(lambda: _copy_rows("vollkauf", "x"))\n            row.insertWidget(0, _b_all)\n            _b_miss = QPushButton("\\U0001F4CB Fehlende Materialien kopieren")',
     'kein Knopf kopiert mehr den Vollkauf'),
    ('Asset-Fehlschlaege verschlucken den Grund wieder',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                        self._log_exception(\n                            f"Bestand: Assets {ch.get(\'character_name\', \'?\')}",\n                            str(_af2_err))',
     '                        pass   # MUTATION',
     'alle drei Fehlerstellen loggen den Grund'),
    ('Einfuege-Panel verschweigt den Reservierungs-Abzug wieder',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _ra_p = getattr(self, "_bd_reserved_applied", None) or {}',
     '            _ra_p = {}   # MUTATION',
     'Einfuege-Panel zeigt den Reservierungs-Abzug'),
    ('rebuild rechnet trotz eingefrorenem Plan neu',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            if _frozen_plan is not None:\n                plan = _frozen_plan\n            elif _cached',
     '            if False:\n                plan = _frozen_plan\n            elif _cached',
     'rebuild(): _frozen_plan-Zweig existiert'),
    ('Dialog-Aufbau (job) ignoriert den Schnappschuss',
     'eve_trader/ui/main_window.py',
     '            _frozen_plan = self._frozen_snapshot_plan() if _frozen else None',
     '            _frozen_plan = None   # MUTATION',
     'genau EIN job() nutzt den Schnappschuss'),
    ('Snapshot-Unpack laesst die JSON-String-Keys stehen',
     'eve_trader/ui/mw_helpers.py',
     '                if _k.isdigit():\n                    return int(k)',
     '                if _k.isdigit():\n                    return k',
     'Mengen-Map kommt mit INT-Keys zurueck'),
    ('Fortschritt zaehlt auch Jobs von VOR dem Einfrieren',
     'eve_trader/ui/mw_helpers.py',
     '            if cts is None or cts < _fts:',
     '            if cts is None:',
     'Alt-Job vor dem Einfrieren haakt nichts ab'),
    ('Fortschritt ignoriert die Aktivitaet (Reaktion vs. Fertigung)',
     'eve_trader/ui/mw_helpers.py',
     '            if is_react.get(tid):\n                if act not in (9, 11):\n                    continue\n            elif act != 1:\n                continue',
     '            if False:\n                continue',
     'falsche Aktivitaet haakt nichts ab'),
    ('Live-Neuberechnen laesst die Alt-Haken kleben',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''            if _hakerl_reset():
                self._flash_tip(_txt("\\u21bb Runs recalculated \\u2013 old run planner "
                                     "ticks reset"))''',
     '            pass   # MUTATION',
     'BEIDE Neu-berechnen-Wege setzen zurueck'),
    ('Haekchen-Reset vergisst das Speichern',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _sched_save_now()          # sofort sichern, nicht entprellt -',
     '            pass   # MUTATION         # sofort sichern, nicht entprellt -',
     'sichert SOFORT im Plan'),
    ('Kopier-Ampel behauptet wieder Fehlmengen trotz Plan-missing=0',
     'eve_trader/ui/mw_helpers.py',
     '        if int(missing or 0) > 0:',
     '        if True:',
     'missing=0 + gebaut -> gruen mit Grund'),
    ('Kopier-Ergebnis verschwindet wieder hinterm Dialog',
     'eve_trader/ui/main_window.py',
     '                    _copy_note.setText(_txt(\n                        "Nothing copied \\u2013 the plan has 0 {what} (everything is built "\n                        "or covered from stock/jobs, see status per row).").format(what=was)',
     '                    pass   # MUTATION',
     'auch der Null-Fall nennt den GRUND im Dialog'),
    ('Runplaner ignoriert die echte Blaupausen-Zahl wieder',
     'eve_trader/ui/mw_helpers.py',
     '            out.update(self._bp_copies_by_tid(\n                _cache, _plan.get("build_runs"),\n                getattr(_rec, "product_to_bp", None)))',
     '            pass   # MUTATION',
     'Resolver liefert die echten Blaupausen-Zahlen'),
    ('BPO zaehlt wieder als unbegrenzt viele Kopien',
     'eve_trader/ui/mw_helpers.py',
     '            by_bp[_bid] = by_bp.get(_bid, 0) + int(b.get("quantity", 1) or 1)',
     '            by_bp[_bid] = 99 if b.get("is_bpo") else (   # MUTATION\n                by_bp.get(_bid, 0) + int(b.get("quantity", 1) or 1))',
     'eine einzelne BPO deckelt auf 1'),
    ('Items fallen bei Slot-Mangel wieder still aus dem Plan',
     'eve_trader/industry.py',
     '                if not use and tracks:',
     '                if False and tracks:',
     'KEIN Item faellt still aus dem Runplaner'),
    ('Massen-Aufbau holt Icons wieder synchron (langsames Oeffnen)',
     'eve_trader/ui/main_window.py',
     '        pm = self._item_pixmap(type_id, size=size, kind=kind, allow_fetch=False)\n        if not pm or pm.isNull():\n            return None\n        from PySide6.QtGui import QIcon',
     '        pm = self._item_pixmap(type_id, size=size, kind=kind)   # MUTATION\n        if not pm or pm.isNull():\n            return None\n        from PySide6.QtGui import QIcon',
     '_table_icon baut cache-only auf'),
    ('Icon-Nachtrag laeuft endlos (versuchte Schluessel vergessen)',
     'eve_trader/ui/mw_helpers.py',
     '        return sorted(set(wanted or ()) - set(tried or ()))',
     '        return sorted(set(wanted or ()))   # MUTATION',
     'schon versuchte Schluessel bleiben draussen'),
    ('Icon-Nachtrag wieder synchron aus dem Signal (Absturz-Muster)',
     'eve_trader/ui/main_window.py',
     '                QTimer.singleShot(0, refresh_cb)',
     '                refresh_cb()   # MUTATION',
     'Nachtrag ist ENTKOPPELT'),
    ('Ein fehlendes Icon stoppt den ganzen Hintergrund-Lauf',
     'eve_trader/ui/mw_helpers.py',
     '            except Exception:\n                _err += 1\n        return _ok, _err',
     '            except Exception:\n                raise\n        return _ok, _err',
     'Fehler halten den Rest NICHT auf'),
    ('Contract-Preise kommen wieder nur aus einer Region',
     'eve_trader/ui/main_window.py',
     '            contract_prices.update(\n                store.get_contract_prices(store.ALL_REGIONS) or {})',
     '            pass   # MUTATION',
     'Capital-Tab bevorzugt den New-Eden-Stand'),
    ('Ausreisser-Preise verziehen den angezeigten Richtwert',
     'eve_trader/scanner.py',
     '        out[tid] = {"median": statistics.median(vals),',
     '        out[tid] = {"median": statistics.fmean(vals),   # MUTATION',
     'laesst den Median aber in Ruhe'),
    # UMGEBAUT (Sitzung 8): Bundles zaehlen jetzt MIT - aber nur mit
    # ABGEZOGENEN Beilagen. Der gefaehrliche Rueckbau: den Abzug vergessen -
    # dann ginge der ROHE Bundle-Preis (Schiff+Rigs+Fuel) als Schiffspreis
    # durch und der Richtwert laege systematisch zu hoch.
    ('Bundle zaehlt mit ROHEM Preis (Beilagen-Abzug vergessen)',
     'eve_trader/scanner.py',
     '    abgeleitet = float(price) - wert',
     '    abgeleitet = float(price)   # MUTATION',
     'Beilagen werden zum Jita-Preis abgezogen'),
    ('Beilage ohne Marktpreis wird geschaetzt statt verworfen',
     'eve_trader/scanner.py',
     '''        if p_it <= 0:
            return None''',
     '''        if False:   # MUTATION
            return None''',
     'Beilage OHNE Marktpreis -> ehrlich None'),
    # --- aa182: Sortier-Rueckmeldung + Gold-Tabellen ---
    ('Verkaufsliste zeigt keinen Sortierpfeil mehr',
     'eve_trader/ui/main_window.py',
     'self.sell_table.horizontalHeader().setSortIndicatorShown(True)',
     'pass   # MUTATION',
     'die Verkaufsliste zeigt ueberhaupt einen Sortierpfeil'),
    ('Einkaufswagen faellt auf Qts Sortierung zurueck (frisst die Knoepfe)',
     'eve_trader/ui/main_window.py',
     'self.sh_table.horizontalHeader().setSortIndicatorShown(True)',
     'self.sh_table.setSortingEnabled(True)   # MUTATION',
     'der Einkaufswagen schaltet Qts Sortierung NICHT ein'),
    ('Sortierpfeil steht wieder starr auf aufsteigend',
     'eve_trader/ui/main_window.py',
     '''        self.sell_table.horizontalHeader().setSortIndicator(
            col, _Qt.AscendingOrder if asc else _Qt.DescendingOrder)''',
     '''        self.sell_table.horizontalHeader().setSortIndicator(
            col, _Qt.AscendingOrder)   # MUTATION''',
     'der Pfeil folgt der Richtung, statt immer aufsteigend zu zeigen'),
    ('Gold-Tabelle sortiert waehrend des Fuellens (Zeilen zerfallen)',
     'eve_trader/ui/main_window.py',
     '        tbl.setSortingEnabled(False)\n        gold_c = QColor(theme.AMBER)',
     '        pass   # MUTATION\n        gold_c = QColor(theme.AMBER)',
     '_fill_gold_table pausiert die Sortierung beim Fuellen'),
    ('Swing-Gold sortiert waehrend des Fuellens',
     'eve_trader/ui/main_window.py',
     '        tbl.setSortingEnabled(False)\n        tbl.setRowCount(len(rows))',
     '        pass   # MUTATION\n        tbl.setRowCount(len(rows))',
     '_fill_swing_gold_table pausiert die Sortierung beim Fuellen'),
    ('Rang-Spalte faellt auf Textsortierung zurueck',
     'eve_trader/ui/main_window.py',
     'j in (0, 2, 4, 5, 6, 7)',
     'j in (2, 4, 5, 6, 7)',
     'und wird deshalb als NumericItem gebaut'),
    ('Trend-Spalte sortiert wieder nichts',
     'eve_trader/ui/main_window.py',
     '(trend_txt, trend_rank),',
     '(trend_txt, 0),   # MUTATION',
     'der Trend sortiert nach echter Rangfolge'),
    # --- aa183: Doppelmenue + gestrichene Sortier-Kandidaten ---
    ('zweites Kontextmenue kehrt in die Gold-Suche zurueck',
     'eve_trader/ui/main_window.py',
     '        tbl.customContextMenuRequested.connect(gold_menu)',
     '''        tbl.customContextMenuRequested.connect(gold_menu)
        tbl.customContextMenuRequested.connect(gold_menu)   # MUTATION''',
     'die Gold-Suche verbindet GENAU EIN Kontextmenue'),
    ('Gold-Menue schreibt wieder von Hand in den Wagen',
     'eve_trader/ui/main_window.py',
     '                if self._add_deal_to_cart(tid, nm):',
     '''                if store.add_shopping(tid, nm, 1, 0, 0,
                                      source="daytrade") or True:   # MUTATION''',
     'der Wagen-Zweig nutzt den gepflegten Helfer'),
    ('Gold-Menue oeffnet den Markt wieder ohne type_id',
     'eve_trader/ui/main_window.py',
     '''            tid = cell.data(Qt.UserRole); nm = cell.text()
            if not tid:
                return''',
     '            tid = cell.data(Qt.UserRole); nm = cell.text()   # MUTATION',
     'ohne type_id passiert gar nichts'),
    ('Charakter-Tabelle bekommt doch Qt-Sortierung (frisst die Knoepfe)',
     'eve_trader/ui/main_window.py',
     '        # KEINE Sortierung (Auftrag A, Sitzung 9 gestrichen): Spalte 2 traegt',
     '''        self.char_table.setSortingEnabled(True)   # MUTATION
        # Sortierung geloescht''',
     'Charaktere schaltet keine Sortierung ein'),
    ('Orderbuch-Leiter bekommt doch Sortierung (Summen verlieren den Bezug)',
     'eve_trader/ui/main_window.py',
     '        # KEINE Sortierung (Auftrag A, Sitzung 9 gestrichen): "Kumuliert" und',
     '''        table.setSortingEnabled(True)   # MUTATION
        # Sortierung geloescht''',
     'die Orderbuch-Leiter schaltet keine Sortierung ein'),
    # --- b2t: "Meine Bauplaene" neu geordnet ---
    ('Karten richten sich wieder nach ihrer Textlaenge',
     'eve_trader/ui/main_window.py',
     '            card.setMinimumWidth(MINW)',
     '            pass   # MUTATION',
     'b2t und dieselbe Mindestbreite'),
    ('Titel-Reservierung faellt weg - Karten werden verschieden hoch',
     'eve_trader/ui/main_window.py',
     '''            title_lbl.setFixedHeight(
                title_lbl.fontMetrics().lineSpacing() * 2 + 4)''',
     '''            pass   # MUTATION''',
     'alle Karten sind exakt gleich HOCH'),
    ('Kartenbreite faellt auf die alten 760 zurueck',
     'eve_trader/ui/main_window.py',
     '        MAXW = 980',
     '        MAXW = 760   # MUTATION',
     'die Karten sind breiter als die alten 760'),
    ('lange Plan-Namen werden wieder abgeschnitten',
     'eve_trader/ui/main_window.py',
     '            title_lbl.setWordWrap(True)',
     '            title_lbl.setWordWrap(False)   # MUTATION',
     'bricht um, statt abgeschnitten zu werden'),
    ('Gewinn-Uebersicht rechts verschwindet',
     'eve_trader/ui/main_window.py',
     '        outer.addWidget(_side, 0)',
     '        pass   # MUTATION',
     'rechts steht jeder Plan mit einer Gewinn-Zeile'),
    ('Kopfzeile haengt wieder direkt an der Seite (Geister-Kopfzeilen)',
     'eve_trader/ui/main_window.py',
     '        lv.addLayout(head_row)',
     '        lay.addLayout(head_row)   # MUTATION',
     'vier Aufbauten hinterlassen GENAU EINE Kopfzeile'),
    # --- aa184: Command Carrier ---
    ('Command Carrier faellt aus der Rig-Capital-Liste',
     'eve_trader/industry.py',
     '''_RIG_CAP_SHIP_HINTS = ("Carrier", "Command Carrier", "Dreadnought", "Titan",''',
     '''_RIG_CAP_SHIP_HINTS = ("Dreadnought", "Titan",''',
     "'Command Carrier' steht AUSDRUECKLICH in der Rig-Capital-Liste"),
    # --- aa185: Strukturname je Stufe ---
    ('Runplaner zeigt wieder die Komponenten-Struktur fuer alle Stufen',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''            _stufe_key = {"fuel": "components", "component": "components",''',
     '''            _stufe_key = {"fuel": "XX", "component": "components",''',
     'der Runplaner schlaegt die Struktur je Stufe nach'),
    ('Rig-Einordnung verschwindet wieder in den Tooltip',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                stage_item.setText(
                    4, _txt("Item type: ") + ", ".join(_kat[:3]) if _kat
                    else _txt("Item type: not classified"))''',
     '''                pass   # MUTATION''',
     'die Rig-Einordnung steht in der ZEILE, nicht nur im Tooltip'),
    # --- aa186: Endprodukt rechnet mit seiner eigenen Struktur ---
    ('Jobkosten ignorieren die Je-Item-Ueberschreibung wieder',
     'eve_trader/industry.py',
     '''    _ov = (opts.get("jobcost_by_tid") or {}).get(type_id) \\
        if type_id is not None else None''',
     '    _ov = None   # MUTATION',
     'MIT Ueberschreibung gilt der Je-Item-Index'),
    ('build_time faellt auf die Pauschal-TE zurueck',
     'eve_trader/industry.py',
     '    te = (opts.get("te_by_tid") or {}).get(type_id, te)',
     '    pass   # MUTATION',
     'build_time kennt die Je-Item-TE'),
    ('Runplaner-Jobs bekommen wieder die Komponenten-Struktur',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''            _s_item = self._bau_struct_fuer_item(
                _tid, recipes.reaction_products, _stage_map_rp, type_id)''',
     '            _s_item = None   # MUTATION',
     'Runplaner + Blueprints-Tab nutzen die Je-Stufe-Struktur'),
    # --- aa187: Diagnose-Schluessel, feste Zuweisung, Reset ---
    ('Rig-Spalte fragt wieder mit dem Anzeige-Schluessel nach',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                _dg2 = (getattr(self, "_bd_struct_diag", {}) or {}).get(
                    _stufe_key or stage) or []''',
     '''                _dg2 = (getattr(self, "_bd_struct_diag", {}) or {}).get(
                    stage) or []''',
     'ALLE drei Nachschlagestellen nutzen den Rechen-Schluessel'),
    ('feste Zuweisung kehrt wieder vor der Aufzeichnung um',
     'eve_trader/ui/main_window.py',
     '''        _fest = None
        if sid:
            _fest = next((x for x in structs if x["id"] == sid), None)''',
     '''        _fest = None
        if sid:
            _fest = next((x for x in structs if x["id"] == sid), None)
            if _fest is not None:
                return _fest   # MUTATION''',
     'es gibt GENAU EINE Rueckgabe der festen Zuweisung'),
    ('Diagnose-Speicher werden nie mehr geleert',
     'eve_trader/ui/main_window.py',
     '''        if use_dialog_me:
            self._bd_struct_choice = {}
            self._bd_struct_diag = {}''',
     '''        if False:   # MUTATION
            self._bd_struct_choice = {}
            self._bd_struct_diag = {}''',
     'aber NUR im Dialog-Kontext, nicht vom Scanner aus'),
    # --- aa188: Waechter Einkaufswagen-Ziehen ---
    ('Qt-Zieh-Logik kehrt in den Einkaufswagen zurueck (frisst die Knoepfe)',
     'eve_trader/ui/main_window.py',
     '''        self.sh_table.horizontalHeader().setSortIndicatorShown(True)''',
     '''        self.sh_table.setDragDropMode(self.sh_table.InternalMove)   # MUTATION
        self.sh_table.horizontalHeader().setSortIndicatorShown(True)''',
     'der Einkaufswagen bekommt KEINE Qt-Zieh-Logik'),
    # --- aa189: Contract-Preise im Bauplan ---
    ('Contract-Median ueberschreibt den Verkaufspreis nicht mehr',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''            _ct9 = getattr(self, "_bd_contract_sell", None)
            if _ct9 and _ct9.get("median"):
                _sell_eff = float(_ct9["median"])''',
     '''            _ct9 = getattr(self, "_bd_contract_sell", None)
            if False:   # MUTATION
                _sell_eff = float(_ct9["median"])''',
     'der Contract-Median ueberschreibt den Verkaufspreis'),
    ('Ein-Item-Scan wirft den New-Eden-Stand des Scanners weg',
     'eve_trader/ui/main_window.py',
     '''            merged = dict(store.get_contract_prices(store.ALL_REGIONS) or {})
            merged.update(result)''',
     '''            merged = dict(result)   # MUTATION
            merged.update(result)''',
     'der Ein-Item-Scan MERGT in den New-Eden-Stand'),
    # --- aa190: ehrliche Slot-Beschriftung ---
    ('Slot-Text behauptet wieder Gleichzeitigkeit',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                if jobs_sum > cap:
                    slot_txt = _txt("{n} starts on {cap} slots \\u00b7 waves").format(
                        n=jobs_sum, cap=cap)''',
     '''                if jobs_sum > cap:
                    slot_txt = f"{jobs_sum}/{cap} gleichzeitig"   # MUTATION''',
     'kein Slot-Text behauptet mehr Gleichzeitigkeit'),
    # --- aa191: besetzte Slots werden ignoriert, aber nicht verschwiegen ---
    # NACHGEZOGEN (Sitzung 11): der alte Anker war die Zeile
    # `elif cap_max and cap < cap_max:` in der Slot-Beschriftung. Seit dem
    # Nutzer-Entscheid "die besetzten slots sollen ignoriert werden" gibt es
    # diesen Zweig nicht mehr - die Zeile zeigt immer das Maximum. Die ZUSAGE
    # hat sich verschoben: nicht mehr "die Zeile nennt frei < maximal",
    # sondern "der TOOLTIP sagt, wie viele gerade belegt sind". Genau darauf
    # zeigt die Mutation jetzt.
    ('Anzeige verschweigt wieder, dass Slots belegt sind',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                if _frei_jetzt is not None and cap_max and _frei_jetzt < cap_max:''',
     '''                if False:   # MUTATION''',
     'Tooltip nennt Quelle UND Stand'),
    # --- aa192: Reihenfolge-Falle der Stufen-Karte ---
    ('Bauplan-Oeffner faellt wieder auf den spaeten Instanz-Zustand zurueck',
     'eve_trader/ui/main_window.py',
     '''                    list(ids), groups, recipes.reaction_products, cat_me_map,
                    type_id, recipes=recipes)''',
     '''                    list(ids), groups, recipes.reaction_products, cat_me_map,
                    type_id)   # MUTATION''',
     'alle drei Aufrufer reichen recipes durch'),
    # --- aa193: eingefrorene Plaene in der Listen-Schaetzung ---
    ('Listen-Schaetzung rechnet eingefrorene Plaene wieder zu Live-Preisen',
     'eve_trader/ui/main_window.py',
     '''        _frz = p.get("frozen") or None''',
     '''        _frz = None   # MUTATION''',
     'die Schaetzung liest die eingefrorene Preistabelle'),
    ('Listen-Schaetzung plant eingefrorene Plaene wieder neu (Live-Bestand)',
     'eve_trader/ui/main_window.py',
     '''        if _frz and _frz.get("plan_snapshot") \\
                and int(_frz.get("qty") or 0) == qty:''',
     '''        if False:   # MUTATION
            pass
        elif False:''',
     'der Plan-Schnappschuss hat VORRANG vor der Neuplanung'),
    ('Karten-Schaetzung faellt auf die globalen Gebuehren zurueck',
     'eve_trader/ui/main_window.py',
     '''                _tax9, _brk9, _fq9 = _fees9()''',
     '''                _tax9 = float(self.settings.get("sales_tax_pct", 0) or 0) / 100.0
                _brk9 = float(self.settings.get("broker_fee_pct", 0) or 0) / 100.0
                _fq9 = "globale Einstellungen"   # MUTATION''',
     'mit char_fees stammt die Gebuehr vom Verkaufscharakter'),
    ('Fortschrittsbalken verschwindet aus den Karten',
     'eve_trader/ui/main_window.py',
     '''            text_v.addWidget(fort)
            self._plan_progress[p["id"]] = fort''',
     '''            pass   # MUTATION''',
     'jede Karte traegt genau einen Fortschrittsbalken'),
    ('Fertig-Check wirft den Zwischenstand wieder weg',
     'eve_trader/ui/main_window.py',
     '''                out[p["id"]] = eintrag''',
     '''                if total_built == target_qty:   # MUTATION
                    out[p["id"]] = eintrag''',
     'der Fertig-Check meldet auch den Zwischenstand'),
    # --- aa195: Icon-Nachtrag Restanschluss ---
    ('Bauplan-Blueprints-Tab verliert den Icon-Nachtrag',
     'eve_trader/ui/main_window.py',
     '''        self._icon_prefetch_pending(_icons_nach)''',
     '''        pass   # MUTATION''',
     'GENAU 13 Stellen sind am Icon-Nachtrag angeschlossen'),
    ('Scanner verliert den Icon-Nachtrag',
     'eve_trader/ui/main_window.py',
     '''        self._icon_prefetch_pending(
            lambda: self._render_build(
                getattr(self, "_last_build_deals", None) or []))''',
     '''        pass   # MUTATION''',
     'der Scanner rendert aus den gemerkten Deals nach'),
    # --- aa196: Symbol-Runde 3, erster Schnitt ---
    ('Sidebar-Knopf faellt aufs Emoji zurueck',
     'eve_trader/ui/main_window.py',
     '''        b_struct = page_btn(t("Structures"), 3, icon="factory")''',
     '''        b_struct = page_btn("\U0001F3D7   Strukturen", 3)   # MUTATION''',
     'Rail-Knopf Strukturen traegt ein gezeichnetes Symbol'),
    # --- aa197: Blueprint-Namen sauber ins Clipboard ---
    ('Kopieren liest wieder den geschmueckten Anzeigetext',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''            base = str(item.data(0, Qt.UserRole + 8) or item.text(0)).strip()''',
     '''            base = item.text(0).strip()   # MUTATION''',
     'das Kopieren liest die Daten vor dem Anzeigetext'),
    ('Alle-kopieren nimmt auch Stufen- und Charakter-Zeilen mit',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                    if _it9.data(0, Qt.UserRole + 7) is not None:''',
     '''                    if True:   # MUTATION''',
     'und NUR echte Item-Zeilen kommen in die Liste'),
    # --- b2w: Zeit-Regler der Invention-Aufteilung ---
    ('Zeit-Regler entkoppelt sich vom Kopien-Feld',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''            def _zeit_zieht(v):
                v = _nutzstufe(v)''',
     '''            def _zeit_zieht(v):
                return   # MUTATION
                v = _nutzstufe(v)''',
     'Regler ziehen stellt die Kopienzahl'),
    ('Nutzstufen-Schnappen faellt weg - nutzlose Positionen bleiben stehen',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                if _att <= 0 or v <= 1:
                    return v
                return math.ceil(_att / math.ceil(_att / min(v, _att)))''',
     '''                return v   # MUTATION
                if _att <= 0 or v <= 1:
                    return v
                return math.ceil(_att / math.ceil(_att / min(v, _att)))''',
     'Regler ueber der Versuchszahl schnappt zurueck (10 -> 4)'),
    ('Ingame-Uebersetzung verschwindet aus der Aufteilungs-Zeile',
     'eve_trader/ui/mw_bauplan_tabs.py',
     "                            + f'<b>Job Runs {_auf[\"kopien\"]}</b> \\u00b7 '",
     '                            + ""   # MUTATION',
     'die Zeile uebersetzt in Ingame-Felder'),
    # --- aa202: Sell-Spalten Oe-Einkauf + Marge neu ---
    ('Marge-neu-Spalte rechnet ohne Gebuehren',
     'eve_trader/ui/main_window.py',
     '''                                      "marge_new": (
                                          (newp * (1 - tax - broker) - cost)
                                          / cost * 100.0
                                          if cost > 0 and newp else None),''',
     '''                                      "marge_new": (
                                          (newp - cost)
                                          / cost * 100.0
                                          if cost > 0 and newp else None),   # MUTATION''',
     'die Marge rechnet mit den Zeilen-Gebuehren des Charakters'),
    # --- aa203: Kopieren im Blueprints-Tab ---
    ('Alle-kopieren-Aktion haengt ohne Handler in der Luft',
     'eve_trader/ui/main_window.py',
     '''            a2.triggered.connect(_alle_kopieren)''',
     '''            pass   # MUTATION''',
     'die Alle-Aktion ist mit ihrem Handler verbunden'),
    # --- aa204: Science-Jobgebuehren ---
    ('Science-Basis verliert den 0.02-Faktor',
     'eve_trader/industry.py',
     '''    base = 0.02 * float(eiv_run or 0.0) * float(runs or 0.0)''',
     '''    base = float(eiv_run or 0.0) * float(runs or 0.0)   # MUTATION''',
     "goldene Zahl GESAMT: 53'451 ISK auf den ISK exakt"),
    ('Jobgebuehr faellt aus den Invention-Kosten',
     'eve_trader/industry.py',
     '''    return attempts * dc + fee''',
     '''    return attempts * dc   # MUTATION''',
     'die Gebuehr fliesst in die Invention-Kosten ein'),
    # --- aa205: Preisquellen-Waechter ---
    ('Portfolio empfiehlt wieder gegen fremde Preisquellen',
     'eve_trader/ui/main_window.py',
     '''        return sellable and not in_market and self._pf_price_source_ok()''',
     '''        return sellable and not in_market   # MUTATION''',
     '_sell_ready gibt ohne Hub-Quelle keine Empfehlung'),
    ('Waechter haelt jede Quelle fuer den Hub',
     'eve_trader/ui/main_window.py',
     '''        return any(_lbl == _l for _k, _l, _r, _s in hubs.NPC_HUBS)''',
     '''        return True   # MUTATION''',
     'der Waechter vergleicht das Scan-Label mit den NPC-Hubs'),
    # --- aa206: Quellen-Trennung des Snapshots ---
    ('Scan loescht wieder ALLE Quellen des Snapshots',
     'eve_trader/store.py',
     '''        c.execute("DELETE FROM market_snapshot WHERE source=?", (src,))''',
     '''        c.execute("DELETE FROM market_snapshot")   # MUTATION''',
     'der Struktur-Scan laesst die Hub-Preise unangetastet'),
    ('Portfolio liest wieder die zuletzt gescannte Quelle',
     'eve_trader/ui/main_window.py',
     '''            _snap = store.get_snapshot(store.get_hub_source())''',
     '''            _snap = store.get_snapshot()   # MUTATION''',
     'das Portfolio liest ausdruecklich die HUB-Quelle'),
    ('Balken verschweigt die geteilte Zaehlung wieder',
     'eve_trader/ui/main_window.py',
     '''                           "shared": _mehrfach.get(type_id, 0) > 1,''',
     '''                           "shared": False,   # MUTATION''',
     'mehrfach beplante Produkte werden erkannt'),
    # --- aa207: Reservierung beim Speichern anbieten ---
    ('Ein JA beim Reservieren bleibt wirkungslos',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                    new_entry["reserve"] = True
                    config.save_settings(self.settings)''',
     '''                    pass   # MUTATION''',
     'ein JA wird sofort gespeichert'),
    ('Kollidierende Plaene werden nicht mehr gesucht',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                        _koll9.append(str(_p9.get("label")
                                          or _p9.get("item_name") or "?"))''',
     '''                        pass   # MUTATION''',
     'kollidierende Plaene werden NAMENTLICH genannt'),
    # --- aa208: freie Slots automatisch nachziehen ---
    ('Slots werden beim Oeffnen nicht mehr nachgezogen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''            QTimer.singleShot(0, lambda: self._load_char_slots(silent=True))''',
     '''            pass   # MUTATION''',
     'der Bauplan-Dialog zieht die Slots beim Oeffnen nach'),
    ('Nachzug laeuft bei JEDEM Oeffnen (kein Alters-Limit)',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                and (_t9auto.time() - _fts9) > 600):''',
     '''                and True):   # MUTATION''',
     'aber nur bei veraltetem Stand (10-Minuten-Schwelle)'),
    # --- aa208: Gesamtfortschritt ueber alle Stufen ---
    ('Fortschritt zaehlt wieder nur das Endprodukt',
     'eve_trader/ui/main_window.py',
     # ANKER UMGEZOGEN (Sitzung 14): die Rekursion `_baum9` ist weg, der
     # Nenner kommt jetzt aus `plan["build_runs"]`. Die ABSICHT bleibt:
     # der Positions-Anteil darf nicht stillschweigend verschwinden,
     # sonst zaehlt der Balken wieder nur das Endprodukt.
     '''                    _plan9 = industry.production_plan(''',
     '''                    _plan9 = None and industry.production_plan(''',
     'der Plan dafuer kommt aus production_plan'),
    ('Balken faellt auf Stueck-Anzeige zurueck',
     'eve_trader/ui/main_window.py',
     '''                if _pc9 is not None and info.get("pos_all"):''',
     '''                if False:   # MUTATION''',
     'ohne Rezept bleibt es beim reinen Stueck-Stand'),
    # --- aa209: manuell abschliessen ---
    ('Handabschluss gibt die Reservierung nicht mehr frei',
     'eve_trader/ui/main_window.py',
     '''        _plan["reserve"] = False          # Schloss auf, s. Docstring''',
     '''        pass   # MUTATION''',
     'und gibt die Reservierung IMMER frei'),
    ('ESI ueberschreibt den Handabschluss wieder',
     'eve_trader/ui/main_window.py',
     '''                if info.get("done_manual"):
                    continue      # von Hand gesetzt - ESI ueberstimmt nicht''',
     '''                if False:   # MUTATION
                    continue''',
     'der ESI-Check ueberstimmt die Handmarkierung NICHT'),
    # --- aa210: reserviert vs. nicht vor Ort ---
    ('Reservierte Materialien heissen wieder "nicht vor Ort"',
     'eve_trader/ui/main_window.py',
     '''                    if _resv > 0:''',
     '''                    if False:   # MUTATION''',
     'der Reservierungs-Fall wird eigens erkannt'),
    ('Fertige Plaene fallen wieder auf den Positions-Anteil zurueck',
     'eve_trader/ui/main_window.py',
     '''                _prozent9 = max(_pos_pct9, _stk_pct9)''',
     '''                _prozent9 = _pos_pct9   # MUTATION''',
     'der Stueck-Anteil zaehlt ebenfalls'),
    # --- aa211: Symbol-Runde 3, zweiter Schnitt ---
    ('Knopf-Symbole fallen weg (Helfer setzt nichts mehr)',
     'eve_trader/ui/main_window.py',
     '''        btn.setIcon(icons.icon(name))''',
     '''        pass   # MUTATION''',
     'es gibt einen Helfer fuer Knopf-Symbole'),
    ('Medaille kehrt in die Preset-Liste zurueck',
     'eve_trader/ui/main_window.py',
     '''        ("Recommended \u00b7 all prices",''',
     '''        ("\U0001F947 Recommended \u00b7 all prices",   # MUTATION''',
     'Medaille \\U0001F947 ist gestrichen'),
    # --- aa212: Reaktions-Skill-Warnung ---
    ('Skill-Erkennung prueft wieder nur den String-Schluessel',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                        if int(_k) == 45746:''',
     '''                        if _k == str(45746):   # MUTATION''',
     'die Erkennung normalisiert die Skill-IDs'),
    # --- aa213: Invention-Erwartungswert ---
    ('Details-Zeile heisst wieder nur "Invention"',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                        ("Invention (\\u00d8)", "Invention (\\u00d8)"),''',
     '''                        ("Invention (\\u00d8)", "Invention"),   # MUTATION''',
     'die Zeile heisst jetzt ausdruecklich Erwartungswert'),
    ('Tooltip zur Abweichung faellt weg',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                _cap.setToolTip(_tt9)
                _val.setToolTip(_tt9)''',
     '''                pass   # MUTATION''',
     'er haengt an Beschriftung UND Wert'),
    # --- aa214: Symbol-Grundton Gold ---
    ('Symbole werden wieder grau',
     'eve_trader/ui/theme.py',
     '''ICON = "#C9A06A"             # Ruhe: Standard-Ton aller Symbole''',
     '''ICON = "#94A2B3"   # MUTATION''',
     'der Symbol-Grundton ist das gedaempfte Gold'),
    ('Symbolton wird zur Signalfarbe AMBER',
     'eve_trader/ui/theme.py',
     '''ICON = "#C9A06A"             # Ruhe: Standard-Ton aller Symbole''',
     '''ICON = "#F2A23C"   # MUTATION''',
     'und deutlich weniger gesaettigt als sie'),
    # --- aa215/b2x: Symbole in den Auswahllisten ---
    ('Combo-Eintraege behalten ihr Emoji im Text',
     'eve_trader/ui/main_window.py',
     '''    _sym = _EMOJI_ZU_SYMBOL.get(text[:1])''',
     '''    _sym = None   # MUTATION''',
     'das Emoji ist aus dem Text verschwunden'),
    ('Preset-Listen umgehen die Symbol-Zuordnung',
     'eve_trader/ui/main_window.py',
     '''            _combo_item(self.h_preset, label, p,
                        symbol=(p or {}).get("sym"))''',
     '''            self.h_preset.addItem(label, p)   # MUTATION''',
     'beide Preset-Listen nutzen sie'),

    # --- Optimierer (Sitzung 10) -------------------------------------
    # Der Optimierer war bis hierher von KEINER Mutation gedeckt. Aufgefallen
    # bei Schnitt 2: der Umzug von 1'203 Zeilen nach mw_optimizer.py bewegte
    # die Rotproben-Zahl nicht um eine einzige Stelle.
    ('Optimierer richtet sich wieder nach der Bauplan-Menge',
     'eve_trader/ui/mw_optimizer.py',
     '''        dlg.resize(900, 860)''',
     '''        dlg.resize(900, 860)
        _mut_qty = int(getattr(self, "_bd_qty", 1) or 1)   # MUTATION''',
     'Optimierer uebernimmt die Bauplan-Menge NICHT'),

    ('Frachtraum faellt auf den toten Alt-Schluessel zurueck',
     'eve_trader/ui/mw_optimizer.py',
     '''        vol.setValue(int(self.settings.get("bau_transport_m3", 350000)''',
     '''        vol.setValue(int(self.settings.get("bau_freight_m3", 350000)   # MUTATION''',
     'Frachtraum kommt aus bau_transport_m3'),

    ('Optimierer-Hub friert beim Hub-Wechsel ein',
     'eve_trader/ui/mw_optimizer.py',
     '''        self._register_tool_hub_label(_ahub_lbl)
        row.addWidget(_ahub_lbl)
        row.addWidget(QLabel(_txt("Sale price/unit:")))''',
     '''        row.addWidget(_ahub_lbl)   # MUTATION
        row.addWidget(QLabel(_txt("Sale price/unit:")))''',
     'Hub-Anzeige ist am Hub-Wechsel angemeldet'),

    ('Verkaufspreis wird nicht mehr aus dem Bauplan vorbelegt',
     'eve_trader/ui/mw_optimizer.py',
     '''        default_sell = float((getattr(self, "_bd_pricemap", None) or {}).get(tid) or 0.0)''',
     '''        default_sell = 0.0   # MUTATION''',
     'Verkaufspreis kommt aus dem Bauplan'),

    # --- Reihenfolge im Ja-Pfad (Sitzung 10) --------------------------
    # Diese Zusage hatte bis hierher keinen Rot-Nachweis. Aufgefallen ist sie,
    # weil genau an dieser Pruefung ein index() stand, das beim Schnitt 3
    # geworfen und die ganze aa-Suite abgebrochen hat.
    # --- Bau-Charaktere: kein Rechnen/Schreiben je Klick (Sitzung 10) --
    ('Kreuz rechnet wieder sofort (Tool friert ein)',
     'eve_trader/ui/main_window.py',
     """        self._char_roles_dirty = True
        _btn = getattr(self, "_char_roles_apply_btn", None)""",
     """        self._char_roles_dirty = True
        _cb_m = getattr(self, "_char_roles_on_change", None)   # MUTATION
        if _cb_m:
            _cb_m()
        _btn = getattr(self, "_char_roles_apply_btn", None)""",
     'ein Kreuz rechnet NICHT mehr sofort'),

    ('Kreuz schreibt wieder die ganze settings.json',
     'eve_trader/ui/main_window.py',
     """        _t.start()""",
     """        config.save_settings(self.settings)   # MUTATION""",
     'auf die Platte geht sie ENTPRELLT'),

    ('Uebernehmen rechnet gar nicht mehr',
     'eve_trader/ui/main_window.py',
     """        cb = getattr(self, "_char_roles_on_change", None)   # Runplaner neu füllen""",
     """        cb = None   # MUTATION""",
     "erst 'Uebernehmen' stoesst die Neuberechnung an"),

    # --- Mitlaufende Reservierung (Sitzung 10) ------------------------
    # Nutzer-Fall: gebaute Zwischenprodukte wurden von ANDEREN Bauplaenen
    # als freier Bestand gewertet und verbaut - der erste Plan stand am
    # Ende ohne da.
    ('Selbstgebautes faellt wieder aus der Reservierung',
     'eve_trader/ui/mw_helpers.py',
     """        for key in ("buy", "stock_used", "inv_buy", "inv_stock_used",
                    "build_made"):""",
     """        for key in ("buy", "stock_used", "inv_buy", "inv_stock_used"):   # MUTATION""",
     'die Verbrauchsliste enthaelt das Selbstgebaute'),

    ('Reservierung nimmt Runs statt Stueck',
     'eve_trader/industry.py',
     """            build_made[tid] = build_made.get(tid, 0) + int(made)""",
     """            build_made[tid] = build_made.get(tid, 0) + int(runs)   # MUTATION""",
     'build_made sind STUECK'),

    ('ESI-Verzug wird ignoriert (Zutaten zu frueh freigegeben)',
     'eve_trader/ui/mw_helpers.py',
     """            if stock_seen_ts is None or float(_ts) > float(stock_seen_ts):
                continue          # ESI hat den Verbrauch noch nicht gesehen""",
     """            if False:   # MUTATION
                continue""",
     'Haken juenger als der ESI-Stand gibt NICHTS frei'),

    ('Abhaken bucht alles ab statt anteilig',
     'eve_trader/ui/mw_helpers.py',
     """            _anteil = min(1.0, float(_fertig) / float(_ges))""",
     """            _anteil = 1.0   # MUTATION""",
     'erledigte Runs buchen ihre Zutaten anteilig ab'),

    ('Pool nimmt wieder die starre Liste vom Speichern',
     'eve_trader/ui/mw_helpers.py',
     """            labels.append(str(p.get("label") or p.get("item_name") or "?"))""",
     """            rm = {}   # MUTATION
            labels.append(str(p.get("label") or p.get("item_name") or "?"))""",
     'erledigte Runs buchen ihre Zutaten anteilig ab'),

    ('Haken bekommt keinen Zeitstempel mehr',
     'eve_trader/ui/mw_bauplan_fenster.py',
     """                    _tsmap[key] = _time_mod.time()""",
     """                    pass   # MUTATION""",
     'ein gesetzter Haken bekommt einen Zeitstempel'),

    ('Plan wird beim Speichern nicht mehr festgenagelt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     """                    frozen_btn.setChecked(True)   # -> _on_freeze_toggle(True)""",
     """                    pass   # MUTATION""",
     'Speichern nagelt den Plan fest'),

    ('Alt-Plan wird still falsch reserviert (kein Hinweis)',
     'eve_trader/ui/main_window.py',
     """                elif on and not (p.get("frozen") or {}).get("plan_snapshot"):""",
     """                elif False:   # MUTATION""",
     'der Hinweis haengt an der Schnappschuss-Bedingung'),

    # --- Symbol-Runde 3 (Sitzung 10) ---------------------------------
    ('Reiter faellt auf Emoji-Text zurueck',
     'eve_trader/ui/mw_bauplan_fenster.py',
     """        tab_icon(_tabs, struct_w, _txt("Recipe structure"), "blueprint")""",
     """        _tabs.addTab(struct_w, "\\U0001F333 " + _txt("Recipe structure"))   # MUTATION""",
     'beide Bauplan-Reiter laufen ueber tab_icon'),

    ('Reiter-Symbol wird VOR dem Anlegen gesetzt',
     'eve_trader/ui/mw_basis.py',
     """    _i = tabs.addTab(widget, text)
    try:
        tabs.setTabIcon(_i, icons.icon(name))
    except Exception:
        pass
    return _i""",
     """    try:
        tabs.setTabIcon(tabs.count(), icons.icon(name))   # MUTATION
    except Exception:
        pass
    _i = tabs.addTab(widget, text)
    return _i""",
     'Reiter wird ZUERST angelegt, Symbol danach'),

    ('Suchfeld behaelt das Lupen-Emoji im Platzhalter',
     'eve_trader/ui/main_window.py',
     """    le.setPlaceholderText(t("Search \\u2026"))""",
     """    le.setPlaceholderText("\\U0001F50D " + t("Search \\u2026"))   # MUTATION""",
     'Platzhalter ohne Emoji'),

    ('Lupe verschwindet aus dem Suchfeld',
     'eve_trader/ui/main_window.py',
     """        le.addAction(icons.icon("search"), QLineEdit.LeadingPosition)""",
     """        pass   # MUTATION""",
     'Lupe sitzt links im Feld'),

    ('Ein Suchfeld umgeht den Helfer wieder',
     'eve_trader/ui/main_window.py',
     """        _such_feld(self._sell_search)""",
     """        self._sell_search.setPlaceholderText("Suchen \\u2026")   # MUTATION""",
     'alle drei Suchfelder laufen ueber den Helfer'),

    ('Haken werden erst NACH dem Auftauen geleert',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                        _hakerl_reset()
                        frozen_btn.setChecked(False)''',
     '''                        frozen_btn.setChecked(False)
                        _hakerl_reset()   # MUTATION''',
     'erst leeren, DANN auftauen'),

    ('Roster-Neuaufbau raeumt Unter-Layouts wieder nicht weg',
     'eve_trader/ui/main_window.py',
     '            self._leere_layout(lay)',
     '''            while lay.count():
                it = lay.takeAt(0)
                wd = it.widget()
                if wd:
                    wd.setParent(None)
                    wd.deleteLater()''',
     "GENAU EINEN 'Uebernehmen'"),

    ('gemerkter Uebernehmen-Knopf ueberlebt den Neuaufbau',
     'eve_trader/ui/main_window.py',
     '        self._char_roles_apply_btn = None\n',
     '        pass   # MUTATION\n',
     'Merker auf nichts'),

    ('ein Kreuz schaltet Uebernehmen nicht mehr frei',
     'eve_trader/ui/main_window.py',
     '''        self._char_roles_dirty = True
        _btn = getattr(self, "_char_roles_apply_btn", None)
        if _btn is not None:
            _btn.setEnabled(True)''',
     '        self._char_roles_dirty = True   # MUTATION',
     "Kreuz macht 'Uebernehmen' anklickbar"),

    ('Namensklick leert statt aufzufuellen (Halbzustand)',
     'eve_trader/ui/main_window.py',
     '        neuer_stand = not all(cb.isChecked() for _key, cb in boxen)',
     '        neuer_stand = not any(cb.isChecked() for _key, cb in boxen)',
     'bei halb gesetzten Rollen fuellt der Klick auf'),

    ('Namensklick fasst nur die erste Rolle an',
     'eve_trader/ui/main_window.py',
     '''        boxen = [(key, cb) for key, cb in boxen if cb is not None]''',
     '''        boxen = [(key, cb) for key, cb in boxen if cb is not None][:1]''',
     'ein Klick auf den Namen setzt ALLE vier'),

    ('Namensklick speichert wieder je Kreuz einzeln',
     'eve_trader/ui/main_window.py',
     '''            cb.blockSignals(True)
            cb.setChecked(neuer_stand)
            cb.blockSignals(False)''',
     '            cb.setChecked(neuer_stand)',
     'KEIN einziges Kreuz-Signal'),

    ('Name ist nicht mehr anklickbar',
     'eve_trader/ui/main_window.py',
     '''            nm_lbl.mousePressEvent = (
                lambda _ev, _cid=cid: self._toggle_char_alle_rollen(_cid))''',
     '            pass   # MUTATION',
     'der Name ist anklickbar gemacht'),

    ('Settings-Text erst im Hintergrund gebaut (Stand kann kippen)',
     'eve_trader/config.py',
     '''    text = json.dumps(settings, indent=2)
    with _schreib_sperre_holen():
        _schreib_offen["text"] = text''',
     '''    with _schreib_sperre_holen():
        _schreib_offen["text"] = settings''',
     'Stand VOM AUFRUF'),

    ('synchrones Speichern wartet den Hintergrund nicht mehr ab',
     'eve_trader/config.py',
     '    flush_settings()\n    _schreibe_settings(json.dumps(settings, indent=2))',
     '    _schreibe_settings(json.dumps(settings, indent=2))',
     'synchrones Speichern wartet erst den Hintergrund ab'),

    ('Kreuz-Pfad schreibt wieder synchron (Oberflaeche wartet)',
     'eve_trader/ui/main_window.py',
     '            _t.timeout.connect(lambda: config.save_settings_async(self.settings))',
     '            _t.timeout.connect(lambda: config.save_settings(self.settings))',
     'ENTPRELLT, nicht je Klick'),

    ('unveraenderte Auswahl schreibt wieder',
     'eve_trader/ui/main_window.py',
     '        if _stand == getattr(self, "_char_roles_last_saved", None):\n            return',
     '        if False:\n            return',
     'unveraenderte Auswahl loest kein Schreiben aus'),

    ('Schliessen nimmt die entprellte Auswahl nicht mit',
     'eve_trader/ui/main_window.py',
     '''            _t = getattr(self, "_char_roles_save_timer", None)
            if _t is not None and _t.isActive():
                _t.stop()
            config.save_settings(self.settings)''',
     '            config.save_settings(self.settings)',
     'beim Schliessen geht die entprellte Auswahl nicht verloren'),

    ('Runplaner plant wieder nach FREIEN Slots',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            sl = mx\n',
     '            sl = fr if fr else mx\n',
     'die Planung nimmt das MAXIMUM'),

    ('0-Slot-Charakter faellt wieder aus der Stufe',
     'eve_trader/industry.py',
     '''        return [(c["id"], c["name"], max(1, int(c.get(key, 0) or 0)))
                for c in chars if c.get(flag, True)]''',
     '''        out = [(c["id"], c["name"], max(1, int(c.get(key, 0) or 0)))
               for c in chars if c.get(flag, True) and int(c.get(key, 0) or 0) >= 1]
        if not out:
            out = [(c["id"], c["name"], 1) for c in chars if c.get(flag, True)]
        return out''',
     '0 freien Slots faellt NICHT aus der Stufe'),

    ('Kreuz zaehlt nicht mehr - jeder darf alles',
     'eve_trader/industry.py',
     '                for c in chars if c.get(flag, True)]',
     '                for c in chars]',
     'ohne Kreuz bleibt der Charakter aussen vor'),

    ('freie Slots verschwinden aus dem Tooltip',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                                "frei_slots": tuple(fr) if fr else (),',
     '                                "frei_slots": (),   # MUTATION',
     'Tooltip nennt Quelle UND Stand'),

    # --- aa222: Auftrag F2, Waechter fuer den Build ---
    ('Build packt den assets-Ordner nicht mehr mit',
     'build.bat',
     '  --add-data "eve_trader/ui/assets;eve_trader/ui/assets" ^\n',
     '',
     'der Build packt den assets-Ordner mit ein'),

    ('Waechter uebersieht einen ganzen Projektordner',
     'test_bestand_herkunft.py',
     '        [q for q in _q if q in (".", "./", "..", "eve_trader", "*")],',
     '        [],   # MUTATION',
     'Waechter faengt: spec mit ganzem Projektordner (ganzer Ordner)'),

    ('Waechter liest .spec-datas nicht mehr mit',
     'test_bestand_herkunft.py',
     '            quellen.append(_q)',
     '            pass   # MUTATION',
     'Waechter faengt: spec mit dem Datenverzeichnis (fremde Quelle)'),

    ('Waechter liest --add-data nicht mehr mit',
     'test_bestand_herkunft.py',
     '''    for _m in _re222.findall(r'--add-data\\s+"([^"]+)"', _t):
        quellen.append(_m)''',
     '''    for _m in []:
        quellen.append(_m)''',
     'Waechter faengt: add-data mit dem ganzen Paket (fremde Quelle)'),

    ('Waechter meldet alles als Verstoss (waere abgeschaltet worden)',
     'test_bestand_herkunft.py',
     '        [n for n in _verboten222 if n in _t],',
     '        list(_verboten222),   # MUTATION',
     'Waechter laesst einen sauberen Build durch'),

    ('Asset-Pfad faellt zurueck auf __file__ (leer in der EXE)',
     'eve_trader/ui/theme.py',
     '''    _mei = getattr(_sys, "_MEIPASS", None)
    if _mei:
        basis = _os.path.join(_mei, "eve_trader", "ui")''',
     '    pass   # MUTATION',
     'auch in der ausgelieferten EXE'),

    # --- aa223: Auftrag F1, neutrale Standardwerte ---
    ('Vorgaben liefern wieder die Standings des Entwicklers mit',
     'eve_trader/config.py',
     '_NEUTRALE_STANDINGS = {"corp": 0.0, "faction": 0.0}',
     '_NEUTRALE_STANDINGS = {"corp": 9.86, "faction": 9.40}',
     'keine persoenliche Standing-Zahl'),

    ('Vorgaben behaupten wieder einen maximal geskillten Haendler',
     'eve_trader/config.py',
     '    "skill_accounting": 0,         # Accounting level 0-5 (sales tax)',
     '    "skill_accounting": 5,         # MUTATION',
     'frische Installation: Accounting 0'),

    ('Vorgabe-Gebuehr passt nicht mehr zur Formel',
     'eve_trader/config.py',
     '    "sales_tax_pct": effective_sales_tax(0),',
     '    "sales_tax_pct": 4.5,   # MUTATION',
     'die Steuer ist der ungeskillte Grundfall'),

    ('hub_standings wird wieder vorbelegt',
     'eve_trader/config.py',
     '    "hub_standings": {},',
     '    "hub_standings": {"jita": {"corp": 9.86, "faction": 9.40}},',
     'frische Installation: keine Standings'),

    ('Erststart ohne Charakter fuehrt wieder nirgendwohin',
     'eve_trader/ui/main_window.py',
     '            QTimer.singleShot(250, self._erststart_ohne_charakter)',
     '            pass   # MUTATION',
     'fuehrt der Start zum Charaktere-Reiter'),

    ('Wegweiser springt nicht mehr zum Charaktere-Reiter',
     'eve_trader/ui/main_window.py',
     '''            if hasattr(self, "_go_tab"):
                self._go_tab("characters")
            self.statusBar().showMessage(''',
     '''            if False:
                self._go_tab("characters")
            self.statusBar().showMessage(''',
     'springt an die richtige Stelle'),

    # --- aa224: Auftrag F4, Programm-Update-Pruefung ---
    ('Versionen werden wieder als Text verglichen (0.10 < 0.9)',
     'eve_trader/programm_update.py',
     """    a, b = version_tupel(fern), version_tupel(lokal)
    if not a or not b:
        return False""",
     """    a, b = str(fern).lstrip("vV"), str(lokal).lstrip("vV")
    if not a or not b:
        return a > b""",
     'verglichen wird als ZAHL'),

    ('0.1 und 0.1.0 gelten wieder als verschieden',
     'eve_trader/programm_update.py',
     """    laenge = max(len(a), len(b))
    a = a + (0,) * (laenge - len(a))
    b = b + (0,) * (laenge - len(b))""",
     '    pass   # MUTATION',
     'Vergleich: auch andersherum'),

    ('Vorabfassungen werden wieder an alle gemeldet',
     'eve_trader/programm_update.py',
     '    if daten.get("draft") or daten.get("prerelease"):',
     '    if False:   # MUTATION',
     'eine Vorabfassung wird nicht gemeldet'),

    ('Netzfehler reisst die Pruefung wieder mit',
     'eve_trader/programm_update.py',
     '''    except Exception:
        # Kein Netz, Repo noch ohne Ver\u00f6ffentlichung (GitHub antwortet dann''',
     '''    except ValueError:
        # Kein Netz, Repo noch ohne Ver\u00f6ffentlichung (GitHub antwortet dann''',
     'Netzfehler wird zu einer leeren Antwort'),

    ('Update-Pruefung blockiert wieder die Oberflaeche',
     'eve_trader/ui/main_window.py',
     '''        self._run(Worker(job), done, fail_cb=fehler, overlay=False)

    def _check_for_updates''',
     '''        done(_pu.pruefen(_repo, _eigene))   # MUTATION

    def _check_for_updates''',
     'laeuft im Hintergrund'),

    ('Repo-Angabe wandert aus der einen Stelle in den Knopf',
     'eve_trader/ui/main_window.py',
     '        _repo = config.GITHUB_REPO',
     '        _repo = "PeanutMotor/motor-market"   # MUTATION',
     'der Knopf benutzt die zentrale Repo-Angabe'),

    # --- aa225: Anzeigename an EINER Stelle, Datenordner davon getrennt ---
    ('Fenstertitel wieder fest eingetippt statt aus der einen Quelle',
     'eve_trader/ui/main_window.py',
     '''        from eve_trader import APP_NAME as _app_name
        self.setWindowTitle(_app_name)''',
     '        self.setWindowTitle("Motor Market")',
     'der Fenstertitel kommt aus dieser einen Quelle'),

    ('EXE heisst anders als das Programm',
     'build.bat',
     '  --name "EVE Motor Market" ^',
     '  --name "Motor Market" ^',
     'die EXE heisst wie das Programm'),

    ('alter Ordnername geloescht (Umzug findet die Daten nicht mehr)',
     'eve_trader/config.py',
     '_ALTER_DATENORDNER_NAME = "EveTradeLedger"',
     '_ALTER_DATENORDNER_NAME = "GibtEsNicht"',
     'der alte Ordner wird auf den neuen Namen umbenannt'),

    ('misslungener Umzug legt einen leeren Ordner an (Daten scheinbar weg)',
     'eve_trader/config.py',
     '''    if os.path.isdir(alt) and not os.path.isdir(neu):''',
     '''    if False:   # MUTATION''',
     'misslingt der Umzug, wird der ALTE Ordner weiterbenutzt'),

    ('bei zwei Ordnern gewinnt wieder der alte',
     'eve_trader/config.py',
     '''    if os.path.isdir(alt) and not os.path.isdir(neu):
        # HIER haengt die Zusage''',
     '''    if os.path.isdir(alt):
        # HIER haengt die Zusage''',
     'sind beide da, gewinnt der neue Ordner'),

    # --- aa231: unlesbare settings.json ---
    ('unlesbare Einstellungen werden wieder still verworfen',
     'eve_trader/config.py',
     '            _rette_defekte_settings(path)',
     '            pass',
     'wird beiseitegelegt, nicht verworfen'),

    ('die kaputte Datei wird geloescht statt umbenannt',
     'eve_trader/config.py',
     '        os.replace(path, ziel)',
     '        os.remove(path)',
     'ihr Inhalt ist unveraendert erhalten'),

    # --- aa233: Preisverlaeufe nachladen ---
    ('Verlauf-Lauf holt die unwichtigsten Items zuerst',
     'eve_trader/verlauf_laden.py',
     '''    offen.sort(key=lambda s: (s.get("sell_qty") or 0) + (s.get("buy_qty") or 0),
               reverse=True)''',
     '''    offen.sort(key=lambda s: (s.get("sell_qty") or 0) + (s.get("buy_qty") or 0))''',
     'die liquidesten Items kommen zuerst'),

    ('Abdeckung misst mit anderer Grenze als der Scanner',
     'eve_trader/verlauf_laden.py',
     'ANALYSE_ALTER_H = scanner._CACHE_ANALYZE_MAX_AGE_H',
     'ANALYSE_ALTER_H = 24',
     'misst mit der Grenze des Scanners'),

    ('Knoepfe der Frage werden wieder von Qt geerbt (Yes/No)',
     'eve_trader/ui/main_window.py',
     '            _ja = _box.addButton(t("Load now"), QMessageBox.YesRole)',
     '            _ja = _box.addButton(QMessageBox.Yes)',
     'die Knoepfe sind beschriftet'),

    # --- aa234/b23: Sprachumschaltung ---
    ('Uebersetzung faellt bei einer Luecke auf Deutsch statt Englisch',
     'eve_trader/sprache.py',
     '    return KATALOG.get(_aktuell, {}).get(text, text)',
     '    return KATALOG.get(_aktuell, {}).get(text, "FEHLT")',
     'ein fehlender Eintrag bleibt englisch'),

    ('unbekannte Sprache wird uebernommen statt abgefangen',
     'eve_trader/sprache.py',
     '    _aktuell = code if code in SPRACHEN else "en"',
     '    _aktuell = code',
     'unbekannte Sprache faellt auf Englisch zurueck'),

    ('Sprache wird erst NACH dem Fensterbau gesetzt',
     'eve_trader/__main__.py',
     '        _sprache.sprache_setzen(\n'
     '            (_cfg_sprache.load_settings() or {}).get("sprache", "en"))',
     '        pass   # MUTATION',
     'die Sprache wird VOR dem Fenster gesetzt'),

    ('Standard ist wieder Deutsch statt Englisch',
     'eve_trader/__main__.py',
     '.get("sprache", "en"))',
     '.get("sprache", "de"))',
     'ohne Einstellung bleibt es bei Englisch'),

    ('Reiter-Namen laufen nicht mehr durch die Uebersetzung',
     'eve_trader/ui/main_window.py',
     '"build": t("Industry"),',
     '"build": "Bauen",',
     "auf Englisch heisst der Reiter 'Industry'"),

    ('Sprachwechsel wird nicht gespeichert',
     'eve_trader/ui/main_window.py',
     '        self.settings["sprache"] = _code\n'
     '        config.save_settings(self.settings)',
     '        self.settings["sprache"] = _code',
     'die Wahl wird sofort gespeichert'),

    ('EVE-Knopf verliert die Uebersetzung beim Zuruecksetzen',
     'eve_trader/ui/main_window.py',
     '        return self.EVE_UPDATE_ICON + t("EVE data")',
     '        return self.EVE_UPDATE_ICON + "EVE data"',
     'der EVE-Knopf ist uebersetzt'),

    ('Portfolio-Spaltenkoepfe wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '            [t("Item"), t("Qty"), t("\\u00d8 buy"), t("Oldest buy"),',
     '            ["Item", "Menge", "\\u00d8-Kauf", "\\u00c4ltester Kauf",',
     "auf Englisch heisst der Spaltenkopf 'Qty'"),

    ('Altersangabe wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '            return t("never")',
     '            return "nie"',
     "auf Englisch sagt die Altersangabe 'never'"),

    ('Zahl wandert in den Katalog statt in den Platzhalter',
     'eve_trader/ui/main_window.py',
     '            return t("{n} min ago").format(n=int(sec / 60))',
     '            return t(f"vor {int(sec / 60)} Min.")',
     'setzt die Zahl in den uebersetzten Satz ein'),

    ('Zustandswort in der Status-Spalte bleibt deutsch',
     'eve_trader/ui/main_window.py',
     '                signal, srank = t("\u25cf SELL"), 3',
     '                signal, srank = "\u25cf VERKAUFEN", 3',
     'kein Zustand mehr fest auf Deutsch'),

    ('Daytrade-Spaltenkopf wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '            [t("Item"), t("Now (buy)"), t("Now (sell)"), t("\u00d8 price (window)"),',
     '            ["Item", "Jetzt (Buy)", "Jetzt (Sell)", "\u00d8-Preis (Zeitraum)",',
     'auch die vorderste Wert-Spalte'),

    ('Swing-Spaltenkopf wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '            [t("Item"), t("Now (sell)"), t("Target price"),',
     '            ["Item", "Jetzt (Sell)", "Zielpreis",',
     'auch dessen vorderste Wert-Spalte'),

    ('Feinfilter-Titel wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '        d_filter_card = self._collapsible(t("FINE FILTERS (OPTIONAL)")',
     '        d_filter_card = self._collapsible("FEINFILTER (OPTIONAL)"',
     'alle drei Feinfilter starten ZUGEKLAPPT'),

    ('Bauen-Spaltenkopf wieder fest auf Deutsch',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '[t("Item"), t("Build margin"), t("Profit/unit"), t("Rating")]',
     '["Item", "Bau-Marge", "Gewinn/Stk", "Bewertung"]',
     'Trefferliste hat vier Spalten'),

    ('Material-Baum wieder fest auf Deutsch',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        tbl.setHeaderLabels([t("Material"), t("Category"), t("Required"),',
     '        tbl.setHeaderLabels(["Material", "Kategorie", "Ben\\u00f6tigt",',
     'die vordere Kopfspalte ist uebersetzt'),

    ('Marge-Karte im Bauplan wieder fest auf Deutsch',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        st_marge = _box(_txt("Margin"))',
     '        st_marge = _box("Marge")',
     'Marge ist eine eigene KPI-Karte'),

    ('Dialog "keine Charaktere" wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '''                t("No blueprints (BPO/BPC) of your own found for the items here.")''',
     '''                "Keine eigenen Blaupausen (BPO/BPC) fuer die Items hier gefunden."''',
     'die knopfgesteuerten Meldungen bleiben erhalten'),

    ('Update-Dialog-Titel wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '''                    self, t("Check for updates"),
                    t("You are up to date''',
     '''                    self, "Auf Updates pruefen",
                    t("You are up to date''',
     'alle Update-Dialoge tragen den uebersetzten Titel'),

    ('Statuszeile "Deals werden berechnet" wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '''            t("Computing deals \u2026 (the first run per hub loads the market "''',
     '''            ("Berechne Deals \u2026 (erster Lauf laedt die Markthistorie "''',
     'Statuszeile uebersetzt: Computing deals'),

    ('Katalog bekommt einen Eintrag, den niemand benutzt',
     'eve_trader/sprache.py',
     '        "Tools": "Werkzeuge",',
     '        "Tools": "Werkzeuge",\n        "Never used anywhere": "Nie benutzt",',
     'kein Katalog-Eintrag ohne Fundstelle'),

    ('Trichterzeile wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '        ("two_sided_low", "not traded on both sides daily"),',
     '        ("two_sided_low", "nicht beidseitig taeglich"),',
     'und auf Englisch'),

    ('Kopfzeilen-Tooltip wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '        self.g_scan_btn.setToolTip(t(',
     '        self.g_scan_btn.setToolTip((',
     'der Markt-Scan-Tooltip ist auf Deutsch'),



    ('t() wandert zurueck in eine Klassen-Konstante',
     'eve_trader/ui/main_window.py',
     '        (_CUSTOM_KEY, None),\n'
     '        # Empfohlen (rank: spanne)',
     '        (t("\u2014 Custom \u2014"), None),\n'
     '        # Empfohlen (rank: spanne)',
     'kein t() im Rumpf einer Klasse'),

    ('Uebersetzung kollidiert mit einer lokalen Variable `t`',
     'eve_trader/ui/main_window.py',
     '        from ..sprache import t as _txt\n'
     '        if is_buy:\n'
     '            t.setHorizontalHeaderLabels(\n'
     '                [_txt("Item")',
     '        from ..sprache import t as _txt\n'
     '        if is_buy:\n'
     '            t.setHorizontalHeaderLabels(\n'
     '                [t("Item")',
     'nirgends ein lokales `t` neben einem t()-Aufruf'),

    ('Lambda-Parameter `t` verdeckt die Uebersetzung (Absturz beim Klick)',
     'eve_trader/ui/main_window.py',
     '            lambda _d, _g: self.deal_status.setText(',
     '            lambda _d, t: self.deal_status.setText(',
     'nirgends ein lokales `t` neben einem t()-Aufruf'),


    ('Werkzeugleiste rechts wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '        self.deals_btn = QPushButton(t("Load deals"))',
     '        self.deals_btn = QPushButton("Deals laden")',
     'und auf Englisch englisch'),

    ('Einkaufswagen wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '        self._sh_step_toggle = QPushButton("\u25b6 " + t("Work-through mode"))',
     '        self._sh_step_toggle = QPushButton("\u25b6 Abarbeiten-Modus")',
     'und auf Englisch englisch (Unterreiter)'),

    ('Container-Kopf wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '            [t("Trade / container"), t("Qty"), t("Hub value")])',
     '            ["Handeln / Container", "Menge", "Jita-Wert"])',
     'der Container-Kopf ist uebersetzt'),

    ('Zeitfenster-Auswahl wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '''        for label, days in [(t("{n} days").format(n=5), 5),
                            (t("{n} days").format(n=14), 14),
                            (t("{n} days").format(n=30), 30),''',
     '''        for label, days in [(t("{n} days").format(n=5), 5),
                            (t("{n} days").format(n=14), 14),
                            ("30 Tage", 30),''',
     'die Zeitfenster-Auswahl ebenso'),

    ('Industrie-Leiste wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '        b_myblue = page_btn(t("My blueprints"), 1, icon="blueprint")',
     '        b_myblue = page_btn("Meine Blueprints", 1, icon="blueprint")',
     'die Industrie-Leiste ist uebersetzt'),

    ('Fehlbedarf-Knopf rechnet wieder selbst (zwei Wahrheiten)',
     'eve_trader/ui/main_window.py',
     '        defizite = self._fehlbedarf_jetzt()',
     '        defizite = []   # MUTATION',
     'der Knopf rechnet NICHT selbst, sondern ruft die geteilte'),

    ('Dauer-Anzeige des Fehlbedarfs faellt weg',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                _fehl_auto = self._fehlbedarf_jetzt()',
     '                _fehl_auto = None   # MUTATION',
     'die Dauer-Anzeige ruft dieselbe Funktion'),

    ('Verlust wird wie ein normaler Kauf angezeigt',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            elif int(r["tid"]) in _verloren:',
     '            elif False:   # MUTATION',
     'die Anzeige hat einen eigenen Verlust-Zweig'),

    ('"war gedeckt" ueberlebt den Neustart nicht mehr',
     'eve_trader/ui/main_window.py',
     '        self._bd_covered_once = {int(_x) for _x in',
     '        self._bd_covered_once = set()   # MUTATION\n        _weg = {int(_x) for _x in',
     'und beim Oeffnen zurueckgeholt'),

    ('frischer Plan erbt die Erinnerung des vorherigen',
     'eve_trader/ui/main_window.py',
     '                self._bd_covered_once = set()',
     '                pass   # MUTATION',
     'ein frischer Plan startet ohne Erinnerung'),

    ('ESI-Nachlauf laeuft nur einmal (Runplaner bleibt stehen)',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _nach_timer.start()',
     '            pass   # MUTATION',
     'der Nachlauf laeuft wiederholt'),

    ('Nachlauf laeuft nach dem Schliessen weiter (ESI-Abrufe ins Leere)',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            dlg.closeEvent = _close_stop',
     '            pass   # MUTATION',
     'steht nach dem SCHLIESSEN'),


    ('Verlust wird auch bei veralteten Job-Daten gemeldet (Fehlalarm)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                _verl_roh if _jobs_frisch else {},',
     '                _verl_roh,   # MUTATION',
     'Verlust nur bei frischen Job-Daten'),

    ('Verlust wird sofort gemeldet (Fehlalarm direkt nach dem Einkauf)',
     'eve_trader/ui/mw_helpers.py',
     '                 if (jetzt - seit_neu[t]) >= mindestdauer}',
     '                 if True}   # MUTATION',
     'ein frischer Fehlbetrag wird noch nicht gemeldet'),

    ('Nachlauf fragt haeufiger als CCPs Job-Cache',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _nach_timer.setInterval(300_000)          # 5 Minuten',
     '            _nach_timer.setInterval(20_000)   # MUTATION',
     'mit ESI entsteht ein Nachlauf-Timer'),

    ('ESI-bestaetigte Zeile behaelt das Kaestchen (kein gruener Punkt)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     # ANKER UMGEZOGEN (Nutzer-Freigabe, Sitzung 14): der zweite Weg zum
     # gruenen Punkt im Haken-Zweig ist entfernt - die Rotprobe hatte ihn als
     # ueberfluessig ausgewiesen (Mutation machte KEINE Pruefung rot). Der
     # Punkt kommt jetzt nur noch aus der Zustands-Anzeige.
     '                            iit.setIcon(0, icons.gruener_punkt())',
     '                            pass   # MUTATION',
     'geliefert: gruener Punkt OHNE dass der Nutzer gehakt hat'),

    ('gedeckte Items landen wieder in voller Menge im Wagen',
     'eve_trader/ui/main_window.py',
     '            cart_qty = missing',
     '            cart_qty = need if not missing else missing',
     'voll gedeckt -> NICHTS'),

    ('Status rechnet die Fehlmenge wieder selbst (zwei Zahlen je Zeile)',
     'eve_trader/ui/mw_helpers.py',
     '            _fehlt_txt = f"{int(missing):,}".replace(",", "\'")',
     '            _fehlt_txt = f"{int(need or 0) - int(own or 0):,}".replace(",", "\'")',
     'der Status nennt die PLAN-Fehlmenge'),

    ('Rest-Rechnung nimmt wieder den ROHEN Live-Bestand (Reservierungen ignoriert)',
     'eve_trader/ui/main_window.py',
     '        live = ((getattr(self, "_bd_opts", None) or {}).get("stock")\n'
     '                or getattr(self, "_bd_live_stock", None) or {})',
     '        live = (getattr(self, "_bd_live_stock", None)\n'
     '                or (getattr(self, "_bd_opts", None) or {}).get("stock") or {})',
     'der rohe Live-Stand ist nur der Rueckfall'),

    ('"Fertig" ist wieder eine Einbahnstrasse',
     'eve_trader/ui/main_window.py',
     '        if _plan.get("done_manual"):',
     '        if False:   # MUTATION',
     'ein zweiter Klick nimmt den Abschluss zurueck'),

    ('Wagen nimmt wieder die eingefrorene Kaufmenge',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                                     "missing": (_rest_kaufmenge(r)',
     '                                     "missing": (int(r.get("missing", 0) or 0)',
     'die Liste UND die Mengen-Uebergabe nutzen dieselbe Rechnung'),


    ('Wiederoeffnen schaltet die Reservierung heimlich wieder an',
     'eve_trader/ui/main_window.py',
     '            _plan["done_manual"] = False\n'
     '            config.save_settings(self.settings)',
     '            _plan["done_manual"] = False\n'
     '            _plan["reserve"] = True   # MUTATION\n'
     '            config.save_settings(self.settings)',
     'die Reservierung wird NICHT automatisch reaktiviert'),




    ('Kopier-Modus legt wieder den vollen Bedarf in den Wagen',
     'eve_trader/ui/main_window.py',
     '                _r["cart_qty"] = _r["missing"]',
     '                _r["cart_qty"] = _r["missing"] or _r["need"]',
     'auch der Kopier-Modus nimmt nur die Fehlmenge'),


    ('_txt benutzt, aber nicht geholt (NameError im Betrieb)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        from ..sprache import t as _txt   # `t` ist hier lokal belegt\n'
     '        from PySide6.QtWidgets import QTableWidgetItem',
     '        from PySide6.QtWidgets import QTableWidgetItem',
     '_fill_bauplan_schedule holt `_txt`, bevor es ruft'),

    ('beide Reaktions-Stufen wieder in derselben Farbe',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                          "flask", "rs", theme.VIOLET_2),',
     '                          "flask", "rs", theme.VIOLET),',
     'und die Stufen-Tabelle benutzt beide'),


    ('Punkt-Farbe wieder hart im Symbol-Modul',
     'eve_trader/ui/icons.py',
     # ANKER NACHGEZOGEN (Sitzung 14): die Malroutine ist jetzt der geteilte
     # Helfer `_punkt(farbe, groesse)`, den gruener_punkt() und lauf_punkt()
     # beide benutzen. Die Farbe wird also nicht mehr IN der Malroutine
     # gewaehlt, sondern beim Aufruf - dort muss der Waechter greifen.
     '    return _punkt(_theme.GREEN, groesse)',
     '    return _punkt("#3ddc84", groesse)   # MUTATION',
     'die Farbe kommt aus dem Theme'),



    ('Laeuft-Merker bleibt im Fehlerfall haengen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                self._bd_esi_busy = False\n                _dlg_overlay_hide()\n                QMessageBox.warning',
     '                _dlg_overlay_hide()\n                QMessageBox.warning',
     'der Laeuft-Merker wird in BEIDEN Ausgaengen freigegeben'),



    ('Nachkauf nimmt auch den gewoehnlichen Rest-Bedarf auf',
     'eve_trader/ui/main_window.py',
     '        verlust = dict(getattr(self, "_bd_verlust", None) or {})',
     '        verlust = dict(getattr(self, "_rest_fehlt", None) or {})',
     'der Nachkauf nimmt NUR echte Verluste'),


    ('Materialien-Reiter rechnet wieder den GESAMT-Bedarf',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            elif _rest_bekannt and int(r["tid"]) not in _rest_fehlt:',
     '            elif False:   # MUTATION',
     'ohne Rest-Rechnung keine falsche Entwarnung'),

    ('Ausfall der Rest-Rechnung gibt falsche Entwarnung',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            _rest_fehlt, _rest_bekannt = {}, False',
     '            _rest_fehlt, _rest_bekannt = {}, True   # MUTATION',
     'ohne Rest-Rechnung keine falsche Entwarnung'),



    # KEINE MUTATION FUER DIALOG-TOOLTIPS: sie sitzen im Bauplan-FENSTER,
    # das die b-Suite nur in EINER Sprache oeffnet. Ein entferntes t()
    # aendert an der englischen Ausgabe nichts (der Schluessel IST der
    # englische Text) - die Mutation waere blind. Wirksam wird sie erst,
    # wenn der Dialog auch auf Deutsch geprueft wird.




    ('Dauerzeile unter dem Diagramm kehrt zurueck',
     'eve_trader/ui/main_window.py',
     '        chart_lbl = QLabel("")\n'
     '        chart_lbl.setObjectName("Muted"); v.addWidget(chart_lbl)',
     '        chart_lbl = QLabel("Zeile anklicken zeigt hier den Kursverlauf.")\n'
     '        chart_lbl.setObjectName("Muted"); v.addWidget(chart_lbl)',
     'keine Dauerzeile mehr unter den Diagrammen'),

    ('Info-Zeile ueber der Order-Leiter kommt zurueck',
     'eve_trader/ui/main_window.py',
     '        info = QLabel("")\n        info.setVisible(False)\n        head.addStretch()',
     '        info = QLabel("Item anklicken \u2026")\n        info.setVisible(True)\n        head.addStretch()',
     'keine sichtbare Info-Zeile ueber der Order-Leiter'),

    ('Dauerhinweis unter der Strategie-Karte kehrt zurueck',
     'eve_trader/ui/main_window.py',
     '''        hint = QLabel("")
        hint.setVisible(False)
        hint.setObjectName("Muted"); hint.setWordWrap(True)''',
     '''        hint = QLabel("W\u00e4hle zuerst den Modus, dann ein passendes Preset")
        hint.setObjectName("Muted"); hint.setWordWrap(True)''',
     'Dauerhinweis entfernt: W'),

    ('Leerzustands-Meldung wird mitentfernt (Nutzer steht vor leerer Flaeche)',
     'eve_trader/ui/main_window.py',
     '                "No build plans saved yet. Open a build plan and click "',
     '                "" if False else "",',
     'Leerzustand bleibt: No build plans saved yet.'),

    ('deutscher Anzeigetext kehrt in main_window zurueck',
     'eve_trader/ui/main_window.py',
     '        self.deals_btn = QPushButton(t("Load deals"))',
     '        self.deals_btn = QPushButton("Deals ausw\u00e4hlen")',
     'kein deutscher Anzeigetext mehr in main_window.py'),








    ('Ladebildschirm-Beschriftung wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     'label=_txt("Refreshing portfolio + prices \u2026"))',
     'label="Aktualisiere Portfolio + Preise \u2026")',
     'kein Katalog-Eintrag ohne Fundstelle'),


    ('neutraler Preset-Eintrag bleibt englisch',
     'eve_trader/ui/main_window.py',
     '    text = _marker + t(text)',
     '    text = _marker + text   # MUTATION',
     'der neutrale Preset-Eintrag ist ueberall uebersetzt'),

    ('Regional-Preset laeuft wieder an der Uebersetzung vorbei',
     'eve_trader/ui/main_window.py',
     '            self.rg_preset.addItem(t(label), p)',
     '            self.rg_preset.addItem(label, p)',
     'der neutrale Preset-Eintrag ist ueberall uebersetzt'),


    ('Regional-Tooltip wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '        self.rg_haul.setToolTip(t(',
     '        self.rg_haul.setToolTip((',
     'der Regional-Fracht-Tooltip ebenso'),



    # KEINE MUTATION "t() entfernt" GEGEN DIE ENGLISCHE PRUEFUNG: nach der
    # Uebersetzung IST der Schluessel der englische Text - t() wegzunehmen
    # aendert an der englischen Ausgabe nichts, die Mutation bliebe blind.
    # Wirksam ist nur eine Pruefung auf der DEUTSCHEN Seite; genau die
    # leisten die beiden Mutationen darueber.




    ('Grund-Text der Trichterzeile laeuft nicht mehr durch t()',
     'eve_trader/ui/main_window.py',
     '''        for key, label in self._DEAL_DIAG_LABELS:
            if d.get(key):
                parts.append(f"{_n(d[key])} {t(label)}")''',
     '''        for key, label in self._DEAL_DIAG_LABELS:
            if d.get(key):
                parts.append(f"{_n(d[key])} {label}")''',
     'die Trichterzeile ist auf Deutsch'),








    ('Abbrechen wird ignoriert (Lauf haelt nicht an)',
     'eve_trader/verlauf_laden.py',
     '        if abbrechen is not None and abbrechen():\n            break',
     '        if False:\n            break',
     'Abbrechen haelt sofort an'),

    ('Restzeit wird geraten statt gemessen',
     'eve_trader/verlauf_laden.py',
     '            if _fertig >= 25:',
     '            if True:',
     'KEINE Restzeit behauptet'),

    ('ein einzelnes kaputtes Item reisst den ganzen Lauf ab',
     'eve_trader/verlauf_laden.py',
     '''            if type(e).__name__ == "RateLimited":
                gedrosselt = True
                break
            fehler += 1''',
     '''            raise''',
     'ein einzelner Fehler stoppt den Lauf nicht'),

    ('vorhandene Verlaeufe werden erneut geholt',
     'eve_trader/verlauf_laden.py',
     '    offen = [s for s in snapshot if s.get("type_id") not in da]',
     '    offen = list(snapshot)',
     'vorhandene Verlaeufe werden uebersprungen'),

    ('Frage kommt auch bei guter Abdeckung',
     'eve_trader/ui/main_window.py',
     '            if not _gesamt or _da >= _gesamt * 0.25:',
     '            if not _gesamt:',
     'gefragt wird nur bei duenner Abdeckung'),

    ('Verlauf-Lauf blockiert wieder die Oberflaeche',
     'eve_trader/ui/main_window.py',
     '        self._run(Worker(job), done, fail_cb=fehler, overlay=False)\n\n    def _verlauf_merker',
     '        self._run(Worker(job), done, fail_cb=fehler)\n\n    def _verlauf_merker',
     'der Lauf blockiert die Oberflaeche nicht'),


    ('der Nutzer erfaehrt nichts vom Verlust',
     'eve_trader/ui/main_window.py',
     '        QTimer.singleShot(150, self._warne_defekte_settings)',
     '        pass   # MUTATION',
     'Hinweis wird beim Start ueberhaupt gerufen'),

    # --- b19/b20/aa232: kleiner Bildschirm, sichtbare Meldung, Spendentext ---
    ('Reiter-Mitte rollt nicht mehr (Tabellen werden gestaucht)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        outer.addWidget(self._roll_mitte(self.b_stack), 1)',
     '        outer.addWidget(self.b_stack, 1)',
     'fordert keine riesige Mindestgroesse'),

    ('Rollbereich der Mitte wird erzeugt, aber nicht eingehaengt',
     'eve_trader/ui/main_window.py',
     '        self._mitte_rollbereiche.append(roll)\n        return roll',
     '        self._mitte_rollbereiche.append(roll)\n        return inhalt',
     'auch eingehaengt, nicht nur erzeugt'),

    ('Sidebar darf nicht mehr in sich rollen (zwingt 723 px Hoehe)',
     'eve_trader/ui/main_window.py',
     '        ch.addWidget(_side_roll)',
     '        ch.addWidget(sidebar)',
     'die Sidebar darf in sich rollen'),

    # KEINE MUTATION FUER "Werkzeugleiste rollt mit weg": jeder Versuch,
    # das textlich nachzubauen, erzeugte ungueltigen Python-Code (die drei
    # Aufrufe sind mehrzeilig und identisch). Eine Mutation, die nur die
    # Suite abstuerzen laesst, prueft nichts - sie taeuscht Deckung vor.
    # Die Zusage haelt b19 selbst: es sucht die Leisten und stellt fest,
    # dass keine davon in einem Rollbereich steckt.


    ('Inhalt klebt bei grossen Fenstern in der Ecke',
     'eve_trader/ui/main_window.py',
     '        roll.setWidgetResizable(True)',
     '        roll.setWidgetResizable(False)',
     'nutzen bei grossen Fenstern die volle Breite'),

    ('Fenster darf auf Briefmarkengroesse schrumpfen',
     'eve_trader/ui/main_window.py',
     '        self.setMinimumSize(1100, 520)',
     '        pass   # MUTATION',
     'bis an die ehrliche Untergrenze'),

    ('Spenden-Hinweis nennt wieder einen Menuepunkt, den es nicht gibt',
     'eve_trader/ui/main_window.py',
     '\\u201eGive Money\\u201c / a contract',
     '\\u201eGive ISK\\u201c / a contract',
     "nennt 'Give Money'"),

    ('Updates-Dialog bekommt den Zusatz-Knopf zurueck',
     'eve_trader/ui/main_window.py',
     '                    t("You are up to date \\u2705"))',
     '                    t("You are up to date \\u2705") + "\\n\\n(deep check below)")',
     'die Gut-Meldung ist kurz'),

    # --- b21: Symbole in den Auswahlfeldern ---
    ('Preset-Neuaufbau verliert die Symbole wieder',
     'eve_trader/ui/main_window.py',
     '                _combo_item(self.d_preset, label, p,\n'
     '                            symbol=(p or {}).get("sym"))',
     '                self.d_preset.addItem(label, p)',
     'nach einem Moduswechsel bleiben die Symbole'),

    ('Swing-Strategie steht wieder ohne Symbol da',
     'eve_trader/ui/main_window.py',
     '        self.h_mode.addItem(icons.icon("trend_up"),\n'
     '                            t("Below \u00d8 (return to the mean)"), "under")',
     '        self.h_mode.addItem("Unter \u00d8 (R\u00fcckkehr zum Schnitt)", "under")',
     'h_mode: jeder Eintrag hat ein Symbol'),

    ('ausdrueckliches Symbol wird ignoriert (nur noch Emoji-Marker)',
     'eve_trader/ui/main_window.py',
     '''    if symbol:
        try:
            combo.addItem(icons.icon(symbol), text, data)
            return''',
     '''    if False:
        try:
            combo.addItem(icons.icon(symbol), text, data)
            return''',
     'd_preset: jeder Eintrag hat ein Symbol'),

    # --- b22: Einrichtungs-Knopf ---
    ('Einrichtungs-Knopf steht wieder neben "Charakter verknuepfen"',
     'eve_trader/ui/main_window.py',
     '        btnrow.addWidget(add)\n        btnrow.addStretch()',
     '        btnrow.addWidget(add)\n'
     '        _s22 = QPushButton("Einrichtung")\n'
     '        btnrow.addWidget(_s22)\n'
     '        btnrow.addStretch()',
     "kein Einrichtungs-Knopf mehr neben"),

    # MUTATION "Anleitung nicht mehr erreichbar" GESTRICHEN (17.09.2026): der
    # Anleitungs-Knopf ist auf Nutzer-Entscheid entfernt ("raus").

    # --- b23: Tiefenpruefung wieder erreichbar ---
    ('Tiefenpruefung ist wieder aus der Oberflaeche verschwunden',
     'eve_trader/ui/main_window.py',
     '        self.g_sde_btn.setContextMenuPolicy(Qt.CustomContextMenu)',
     '        pass   # MUTATION',
     'eigenes Kontextmenue'),

    ('Menue-Eintrag startet die Pruefung nicht mehr',
     'eve_trader/ui/main_window.py',
     '        if m.exec(self.g_sde_btn.mapToGlobal(pos)) is _akt:\n'
     '            self._check_recipes()',
     '        m.exec(self.g_sde_btn.mapToGlobal(pos))',
     'der Klick darauf startet sie wirklich'),

    ('Rechtsklick wird nirgends erwaehnt (niemand findet ihn)',
     'eve_trader/ui/main_window.py',
     '              "Industry tab. Stored locally afterwards.\\nRIGHT-CLICK: "',
     '              "Industry tab. Stored locally afterwards. "',
     'Tooltip verraet den Rechtsklick'),






    # --- aa228: keine persoenlichen Angaben in der Oberflaeche ---
    ('Heimatsystem des Entwicklers steht wieder im Tooltip',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        self.bs_syspick.setToolTip(t("Search for the build system (e.g. type \\u201eJita\\u201c). "',
     '        self.bs_syspick.setToolTip(t("Search for the build system (e.g. type \\u201eA-DDGY\\u201c). "',
     'keine persoenliche Angabe sichtbar: A-DDGY'),

    ('Waechter zaehlt Docstrings faelschlich als sichtbar',
     'test_bestand_herkunft.py',
     '        and id(_n) not in _doc_ids)',
     '        )',
     'keine persoenliche Angabe sichtbar: Peanut Motor'),

    # --- aa229: Fehlerprotokoll erst im Fehlerfall ---
    ('leere Fehlerdatei wird wieder beim Start angelegt',
     'main.py',
     '''    base = os.path.dirname(os.path.abspath(sys.argv[0])) or os.getcwd()
    return os.path.join(base, "fehler.log")''',
     '''    base = os.path.dirname(os.path.abspath(sys.argv[0])) or os.getcwd()
    p = os.path.join(base, "fehler.log")
    with open(p, "a", encoding="utf-8"):
        pass
    return p''',
     'die Pfad-Funktion legt die Datei NICHT an'),

    ('kein Rueckfall, wenn neben der Anwendung nicht geschrieben werden darf',
     'main.py',
     '        for _ziel in (path, _rueckfall_pfad()):',
     '        for _ziel in (path,):',
     'Rueckfallebene wird im Fehlerfall auch versucht'),

    # --- b17: zwei Update-Knoepfe nebeneinander ---
    ('EVE-Knopf heisst wieder bloss "Updates" (Etikettenluege daneben)',
     'eve_trader/ui/main_window.py',
     '        return self.EVE_UPDATE_ICON + t("EVE data")',
     '        return self.EVE_UPDATE_ICON + t("Updates")',
     'der EVE-Knopf nennt EVE'),

    ('Programm-Knopf oben rechts verschwindet wieder',
     'eve_trader/ui/main_window.py',
     '        tb.addWidget(self.ver_btn)',
     '        pass   # MUTATION',
     'beide Knoepfe stehen im Fenster'),

    ('beide Knoepfe loesen dasselbe aus',
     'eve_trader/ui/main_window.py',
     '        self.ver_btn.clicked.connect(self.check_programm_update)',
     '        self.ver_btn.clicked.connect(self._check_for_updates)',
     'jeder Knopf loest seinen EIGENEN Weg aus'),

    ('Abfrage sperrt nur den Knopf in den Einstellungen',
     'eve_trader/ui/main_window.py',
     '            for _n in ("s_ver_btn", "ver_btn"):',
     '            for _n in ("s_ver_btn",):',
     'sperrt beide Knoepfe, nicht nur einen'),

    # --- aa230: Symbol der EXE-Datei ---
    ('EXE bekommt wieder kein Symbol',
     'build.bat',
     '  --icon "eve_trader/ui/assets/logo.ico" ^\n',
     '',
     'der Build gibt sie PyInstaller mit'),

    ('Icon wird nicht mehr aus dem Code erzeugt (zweite Wahrheit)',
     'build.bat',
     'python mache_icon.py\nif errorlevel 1 (',
     'echo    (uebersprungen)\nif errorlevel 1 (',
     'erzeugt sie bei jedem Lauf neu aus dem Code'),

    ('misslungenes Icon bricht den Bau nicht mehr ab',
     'build.bat',
     '''if errorlevel 1 (
  echo    Icon konnte nicht erzeugt werden - Bau wird abgebrochen.''',
     '''if errorlevel 9009 (
  echo    Icon konnte nicht erzeugt werden - Bau wird abgebrochen.''',
     'schlaegt das Erzeugen fehl, bricht der Bau ab'),

    ('Installer traegt das Symbol nicht mehr',
     'installer.iss',
     'SetupIconFile=eve_trader\\ui\\assets\\logo.ico',
     '; SetupIconFile entfernt',
     'auch der Installer traegt das Symbol'),

    ('Icon-Bau braucht wieder Pillow (nicht installiert -> dist leer)',
     'mache_icon.py',
     '    import tempfile\n    from PySide6.QtWidgets import QApplication',
     '    import tempfile\n    from PIL import Image\n    from PySide6.QtWidgets import QApplication',
     'braucht nichts, was nicht installiert wird'),

    ('ICO-Kopf wird falsch geschrieben (Windows erkennt kein Symbol)',
     'mache_icon.py',
     '    kopf = struct.pack("<HHH", 0, 1, len(png_bilder))',
     '    kopf = struct.pack("<HHH", 0, 2, len(png_bilder))',
     "der Kopf sagt 'Symbol' (Typ 1)"),

    ('kleine Groessen wieder PNG (Explorer zeigt Standardsymbol)',
     'mache_icon.py',
     'PNG_AB = 256',
     'PNG_AB = 0',
     'b18 Groesse 16 liegt als Bitmap vor'),

    ('Bitmap steht auf dem Kopf (DIB zaehlt von unten)',
     'mache_icon.py',
     '    farbe = b"".join(reversed(bgra_zeilen))',
     '    farbe = b"".join(bgra_zeilen)',
     'das Bitmap steht richtig herum'),



    ('CCP-Hinweis verschwindet aus dem Fenster',
     'eve_trader/ui/main_window.py',
     '        vl.addWidget(_ccp_lbl)',
     '        pass   # MUTATION',
     'Hinweis steht auch wirklich im Fenster'),

    # --- aa226: Auftrag F5, Windows-Installer ---
    ('Installer nimmt beim Entfernen die Nutzerdaten mit',
     'installer.iss',
     '[Run]',
     '''[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\\EVE Motor Market"

[Run]''',
     'loescht beim Entfernen keine Nutzerdaten'),

    ('Installer packt die Einstellungen mit ein',
     'installer.iss',
     'Source: "dist\\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion',
     '''Source: "dist\\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "settings.json"; DestDir: "{app}"''',
     'eingepackt wird ausschliesslich die gebaute EXE'),

    ('Installer-Version wird fest eingetippt statt hereingereicht',
     'installer.iss',
     '#ifndef MyAppVersion\n  #define MyAppVersion "0.0.0"\n#endif',
     '#define MyAppVersion "0.1.0"',
     'Name und Version kommen von aussen herein'),

    ('build.bat reicht Name und Version nicht mehr weiter',
     'build.bat',
     '"%ISCC%" /DMyAppName="%MM_NAME%" /DMyAppVersion="%MM_VER%" installer.iss',
     '"%ISCC%" installer.iss',
     'build.bat liest beide aus'),

    ('fehlendes Inno Setup laesst den ganzen Bau scheitern',
     'build.bat',
     '''if not exist "%ISCC%" (
  echo    Inno Setup 6 nicht gefunden - Installer uebersprungen.''',
     '''if not exist "%ISCC%" no_goto (
  echo    Inno Setup 6 nicht gefunden - Installer uebersprungen.''',
     'fehlendes Inno Setup laesst den Bau nicht scheitern'),

    ('Installer verlangt wieder Adminrechte',
     'installer.iss',
     'PrivilegesRequired=lowest',
     'PrivilegesRequired=admin',
     'verlangt keine Adminrechte'),

    # --- (aa254) EINKAUFSMENGE GEGEN DIE JOB-AUFTEILUNG (Sitzung 13) ---
    # Nutzer-Vorfall: "195 / 196" im Industry-Fenster, weil der Plan alle
    # Runs als EINEN Job rundete, der Runplaner sie aber auf vier verteilt.
    ('Materialmenge rundet wieder erst auf die Summe aller Runs',
     'eve_trader/industry.py',
     '    pro_run = int(math.ceil(float(base_qty) * float(me) - 1e-9))\n'
     '    return max(1, pro_run) * r',
     '    return max(r, int(math.ceil(float(base_qty) * r * float(me))))   # MUTATION',
     'der Einkauf deckt JEDE Aufteilung'),
    ('Epsilon-Schwelle raus - Fliesskomma-Rest kauft ein Stueck zu viel',
     'eve_trader/industry.py',
     '    pro_run = int(math.ceil(float(base_qty) * float(me) - 1e-9))',
     '    pro_run = int(math.ceil(float(base_qty) * float(me)))   # MUTATION',
     'Fliesskomma-Rest treibt die Menge nicht hoch'),
    ('Planmengen umgehen den Helfer wieder (Kaskade bricht)',
     'eve_trader/industry.py',
     '            jq = material_menge(base_qty, runs, me)\n'
     '            build_mats[tid].append((m, jq))',
     '            jq = max(runs, int(math.ceil(base_qty * runs * me)))   # MUTATION\n'
     '            build_mats[tid].append((m, jq))',
     'auch das Unter-Material erbt die sichere Menge'),
    ('Rezept-Baum rechnet die Menge wieder selbst nach',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            aq = (industry.material_menge(comp["qty"], parent_runs, 1.0)',
     '            aq = (_math.ceil(aq_raw - 1e-9)   # MUTATION',
     'der Rezept-Baum benutzt dieselbe Funktion'),

    # --- (aa255) RIG-ZEITBONUS BEI REAKTIONEN (Sitzung 13) ---
    # EVEs eigenes Tooltip "JOB DURATION MODIFIERS" weist ihn mit -22 % aus.
    ('Reaktionen verlieren den Rig-Zeitbonus wieder (Zeiten 28 % zu lang)',
     'eve_trader/ui/main_window.py',
     '            rig_te = self._bau_rig_te_for_item(react_struct, doms, reaction=True)',
     '            rig_te = 0.0   # MUTATION',
     'der Reaktionszweig holt den Rig-Zeitbonus'),
    ('Reactor-Rig nimmt den Fertigungs-Multiplikator (Zeiten zu kurz)',
     'eve_trader/ui/main_window.py',
     '''        secmult = float(s.get("security", 1.0))
        if reaction:
            secmult = 1.1 if secmult >= 2.0 else 1.0
        return best * secmult

    def _bau_best_struct''',
     '''        secmult = float(s.get("security", 1.0))
        if False:   # MUTATION
            secmult = 1.1 if secmult >= 2.0 else 1.0
        return best * secmult

    def _bau_best_struct''',
     'Reactor-Rig-Zeitbonus in Null: 22 %'),

    # --- (aa256) RUNPLANER-BAUM ZEIGT DIE PLANZUTATEN (Sitzung 13) ---
    ('Zutaten je Run werden abgerundet (alter Schnappschuss zeigt zu wenig)',
     'eve_trader/industry.py',
     '    return [(m, -(-int(q) // runs)) for m, q in mats]',
     '    return [(m, int(q) // runs) for m, q in mats]   # MUTATION',
     'alter Schnappschuss wird je Run aufgerundet'),
    ('Runplaner-Baum rechnet die Zutaten wieder selbst nach',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    _pr = industry.plan_mats_pro_run(plan, a["tid"])',
     '                    _pr = None   # MUTATION',
     'der Runplaner-Baum nimmt die Zutaten aus dem Plan'),
    ("'Selber aufteilen' bekommt den Plan nicht mehr",
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            self._fill_schedule_manual(jobs, recipes, names, hdr, sub, tbl, plan=plan)',
     '            self._fill_schedule_manual(jobs, recipes, names, hdr, sub, tbl)   # MUTATION',
     'bekommt den Plan auch wirklich durchgereicht'),

    # --- (aa257) KEIN DEUTSCHER TOOLTIP MEHR IN main_window.py (Sitzung 13) ---
    ('Ein Tooltip faellt ins Deutsche zurueck',
     'eve_trader/ui/main_window.py',
     '        howto.setToolTip(t("If the tool helps you: donations go to my corporation in game."))',
     '        howto.setToolTip("Wenn dir das Tool hilft: Spenden gehen ingame an meine Corporation.")   # MUTATION',
     'hat keinen deutschen Tooltip mehr'),
    ('Katalog verliert einen deutschen Eintrag (Oberflaeche bleibt still englisch)',
     'eve_trader/sprache.py',
     '''        "Sell order listed \\u2013 waiting for a buyer.":
            "Verkaufs-Order gelistet \\u2013 wartet auf einen K\\u00e4ufer.",
''',
     '',
     'der Katalog kennt jeden benutzten Schluessel auf Deutsch'),

    # --- (aa258) REST-RUNS STATT URSPRUNGSZAHL (Sitzung 13) ---
    # Nutzer-Fund: Runplaner verlangte 7'321 Runs, offen waren 3'661.
    ('Erledigt-Menge wird nicht mehr auf den Plan gedeckelt',
     'eve_trader/ui/mw_helpers.py',
     '''    return max(0, min(int(geliefert or 0) + int(laufend or 0),
                      int(plan_runs or 0)))''',
     '''    return max(0, int(geliefert or 0) + int(laufend or 0))   # MUTATION''',
     'mehr gebaut als geplant wird gedeckelt'),
    ('Budget wird je Zuteilung neu verbraucht statt weitergereicht',
     'eve_trader/ui/mw_helpers.py',
     '    weg = min(b, r)\n    return r - weg, b - weg',
     '    weg = min(b, r)\n    return r - weg, b   # MUTATION',
     'das Budget ist restlos verteilt'),
    ('Runplaner-Baum rechnet die offenen Runs wieder selbst nach',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                    R, _rest_budget[_tid_a] = _mwh_rest(
                        R_plan, _rest_budget.get(_tid_a, 0))''',
     '''                    R = R_plan   # MUTATION''',
     'der Runplaner-Baum benutzt die Helfer'),
    ('Materialien-Reiter zeigt wieder die eingefrorene Planmenge',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            _noch_bauen = max(0, int(r["total"]) - int(owned))',
     '            _noch_bauen = built   # MUTATION',
     'der Materialien-Reiter rechnet die Restmenge live'),

    # --- (b40) NUR EIN BAUPLAN GLEICHZEITIG (Sitzung 13) ---
    # GENAU DIESE Mutation stand einen Tag lang im Code: `if False and ...`
    # als "ISOLATIONSTEST" - und die b-Suite blieb gruen, weil nichts sie
    # bewachte. Jetzt faellt b40.
    ('Sperre still abgeschaltet (if False and ...)',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        _offen = self._offener_bauplan()\n        if _offen is not None:\n',
     '        _offen = self._offener_bauplan()\n        if False and _offen is not None:   # MUTATION\n',
     'die Sperre greift, bevor irgendetwas gebaut wird'),
    ('Sperre ohne Hinweis - stilles Nichts-passiert',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''            _QMB.information(
                _offen, _txt("Only one build plan at a time"),''',
     '''            (lambda *a, **k: None)(   # MUTATION
                _offen, _txt("Only one build plan at a time"),''',
     'der Nutzer bekommt einen Hinweis'),

    # --- (b41) ERLEDIGTE RUNS BLEIBEN STEHEN, GEDIMMT (Sitzung 14) ---
    # Der Nutzer hat die Richtung waehrend der Sitzung geaendert: erst
    # "fertige Stufen sollen fertig aussehen", dann "imprinzip wird nie etwas
    # mehr ausgeblendet nurnoch gedimmt und eingefaerbt und mit punkten
    # versehen". Die vier Mutationen der ersten Fassung (Charakter-Zeilen
    # entfernen, Zaehl-Zeile, `_stage_hidden`) zeigten danach auf Code, den es
    # nicht mehr gibt - sie sind hier durch die Zusagen der zweiten Fassung
    # ersetzt.
    #
    # DIE GEFAEHRLICHSTE IST DIE ZWEITE: sie klappt eine Stufe schon zu, wenn
    # EINE Position erledigt ist. Die noch offene geriete damit aus dem Blick,
    # und der Nutzer merkt es erst, wenn er im Spiel davorsteht.
    ('Erledigte Zeile wird nicht mehr gedimmt (sieht nach Arbeit aus)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                            iit.setForeground(_c_z, _dim)',
     '                            pass   # MUTATION',
     'in Bau: die Zeile ist gedimmt'),
    ('Stufe gilt schon als fertig, wenn EINE Position erledigt ist',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''            _stufe_abgedeckt = (_stage_items > 0
                                and _stage_erledigt == _stage_items)''',
     '''            _stufe_abgedeckt = _stage_erledigt > 0   # MUTATION''',
     'teilweise: die Stufe bleibt aufgeklappt'),
    ('Positionen werden gar nicht mehr gezaehlt (Stufe nie fertig)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    _stage_items += 1',
     '                    pass   # MUTATION',
     'in Bau: die Stufe ist zugeklappt'),
    ('Eigene Haken zaehlen nicht mehr fuer den Stufen-Zustand',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                        _stage_erledigt += 1',
     '                        pass   # MUTATION',
     'handabgehakt: die Stufe gilt trotzdem als fertig'),
    ('Erledigte Zeile behaelt ihr Kaestchen',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                        iit.setFlags(iit.flags() & ~Qt.ItemIsUserCheckable)
                        iit.setData(0, Qt.CheckStateRole, None)''',
     '''                        pass   # MUTATION''',
     'in Bau: KEIN Kaestchen mehr'),
    ('Laufender Job bekommt den GRUENEN Punkt (Zustaende verwechselt)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                            iit.setIcon(0, icons.lauf_punkt())',
     '                            iit.setIcon(0, icons.gruener_punkt())   # MUTATION',
     'in Bau: es ist der LAUF-Punkt, nicht der gruene'),
    ('Erledigte Zeile zeigt wieder die Rest-Null statt der Plan-Runs',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                                    else "fertig")\n                        # de_scan4: an\n                        R = R_plan',
     '                                    else "fertig")   # MUTATION\n                        # de_scan4: an',
     'in Bau: die Zeile zeigt die PLAN-Runs, nicht 0'),
    ('Laufender Job gilt pauschal als gebaut (gedeckt = fertig)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     # DIE FEHLERKLASSE, die die Rotprobe in dieser Sitzung gefunden hat:
     # `mw_helpers.fertig_menge` zaehlt geliefert UND laufend zusammen. Wer
     # daraus pauschal "fertig" macht, setzt einen GRUENEN Punkt auf eine
     # Position, die noch in der Bauschleife steckt.
     '''                        _zustand = ("laeuft"
                                    if (_lauf_r > 0 and _gel_r < R_plan)
                                    else "fertig")''',
     '''                        _zustand = "fertig"   # MUTATION''',
     'in Bau: es ist der LAUF-Punkt, nicht der gruene'),
    ('Fertige, nicht abgeholte Jobs gelten wieder als laufend',
     'eve_trader/ui/mw_bauplan_tabs.py',
     # DER GEMELDETE FEHLER (Nutzer-Screenshot, Sitzung 14): "da steckt aber
     # schon lange nichts mehr in der Bauschleife". `_bd_active_jobs_map`
     # fuehrt "active" UND "ready" - ohne die Trennung bekommt laengst
     # Gebautes den Lauf-Punkt.
     '                            if _j.get("status") != "ready")',
     '                            )   # MUTATION',
     'ready: fertig Gebautes zeigt den GRUENEN Punkt'),
    ('Charakter-Zeile zieht nicht mit (leeres Kaestchen ueber Punkt-Zeilen)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     # NUTZER (Sitzung 14): "dann muessen wir die charaktere auch abhacken".
     # Ohne das behauptet die Zeile das Gegenteil ihrer eigenen Kinder.
     '                if _c_items > 0 and _c_zustand == _c_items:',
     '                if False:   # MUTATION',
     'in Bau: die Charakter-Zeile hat KEIN Kaestchen mehr'),
    ('Charakter-Zeile zeigt gruen, obwohl noch etwas laeuft',
     'eve_trader/ui/mw_bauplan_tabs.py',
     # Die vorsichtigere Aussage muss gewinnen (Regel 3): laeuft auch nur
     # EINE Position, ist der Charakter nicht fertig.
     '''                    citem.setIcon(0, icons.lauf_punkt() if _c_laeuft
                                  else icons.gruener_punkt())''',
     '''                    citem.setIcon(0, icons.gruener_punkt())   # MUTATION''',
     'auf der Charakter-Zeile steht der LAUF-Punkt'),
    ('Fertige Stufe: Charakter-Zeilen bleiben zu (Punkte unauffindbar)',
     'eve_trader/ui/mw_bauplan_tabs.py',
     # NUTZER-SCREENSHOT (Sitzung 14): "wo gibts jetzt da gruene punkte?" -
     # er musste zweimal aufklappen, um sie zu finden. Ein Klick muss reichen.
     '                _cf.setExpanded(_stufe_abgedeckt)',
     '                _cf.setExpanded(False)   # MUTATION',
     'die Charakter-Zeilen sind offen, ein Klick genuegt'),
    ('Fertige Stufe startet wieder aufgeklappt',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            stage_item.setExpanded(not _stufe_abgedeckt)',
     '            stage_item.setExpanded(True)   # MUTATION',
     'in Bau: die Stufe ist zugeklappt'),
    ('Fertige Stufe behauptet weiter eine Restdauer',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                stage_item.setText(3, "")\n',
     '                pass   # MUTATION\n',
     'in Bau: die Stufe behauptet keine Restdauer mehr'),
    ('Fertige Stufe verliert den Haken vorn',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                stage_item.setText(0, f"\\u2713  {label}")',
     '                stage_item.setText(0, label)   # MUTATION',
     'handabgehakt: die Stufe gilt trotzdem als fertig'),
    ('Fertig-Zeile nennt eine feste Anzahl statt der echten',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                                               n=_stage_erledigt))',
     '                                               n=1))   # MUTATION',
     'in Bau: die Stufe nennt BEIDE Positionen'),
    ('Geplante Dauer der fertigen Stufe ist nirgends mehr nachlesbar',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                stage_item.setToolTip(3, _txt("Planned duration of this stage "
                                              "was {d}.").format(
                                                  d=self._fmt_dur(dur)))''',
     '''                pass   # MUTATION''',
     'in Bau: die geplante Dauer bleibt im Tooltip nachlesbar'),

    # --- (aa259) STILLE NULL BEI FEHLENDEM PREIS (Sitzung 14) ---
    # Der Nutzer-Befund dieser Sitzung: "es ist nicht moeglich dass eine
    # Ametat II nur 10 mio kostet". Material ohne Orderbuch UND ohne
    # Flachpreis ging mit 0 ISK in die Baukosten - stumm, weil die
    # Knappheits-Warnung nur auf `short_materials` schaut und die Liste in
    # diesem Fall leer bleibt.
    ('Material ohne Preis faellt wieder still auf 0 ISK',
     'eve_trader/industry.py',
     '''                if _flat is None:
                    # KEIN PREIS ZU BEKOMMEN: die Menge fehlt in der Summe.
                    # Das wird GEMELDET, nicht als 0 behauptet (Regel 6).
                    unpriced.append(tid)''',
     '''                if _flat is None:
                    pass   # MUTATION''',
     'Material ganz ohne Preis wird GEMELDET'),
    ('CCP-Durchschnitt wird nicht mehr als Rueckfall benutzt',
     'eve_trader/industry.py',
     '                if _flat is None and avg_fn:',
     '                if False and avg_fn:   # MUTATION',
     'Material ohne Buch faellt auf den CCP-Durchschnitt'),
    ('Durchschnitt schlaegt den genaueren Hub-Preis',
     'eve_trader/industry.py',
     '                _flat = price_fn(tid) if price_fn else None',
     '                _flat = None   # MUTATION',
     'der Hub-Flachpreis schlaegt den Durchschnitt'),
    ('Geschaetzte Posten werden nicht mehr gemeldet (Tooltip schweigt)',
     'eve_trader/industry.py',
     '                        avg_priced.append(tid)',
     '                        pass   # MUTATION',
     'Material ohne Buch faellt auf den CCP-Durchschnitt'),
    ('market_prices wirft den Durchschnittspreis wieder weg',
     'eve_trader/esi.py',
     '''        av = e.get("average_price")
        if av is not None:
            avg[_tid] = float(av)''',
     '''        pass   # MUTATION''',
     'der Durchschnittspreis wird wirklich eingelesen'),

    # --- (aa260) ITEM-LISTE HING AN DER KAUF/BAU-ENTSCHEIDUNG (Sitzung 14) ---
    # Der Kreis, der die Fertigungstiefe stellenweise wirkungslos machte:
    # Item wird gekauft -> kein Teilbaum -> seine Materialien fehlen in der
    # Liste -> nie auf never_build geprueft -> werden gebaut, egal was
    # angekreuzt ist.
    ('Rezeptkette wird nicht mehr in die Item-Liste aufgenommen',
     'eve_trader/ui/main_window.py',
     '                ids |= industry.alle_items_der_kette(type_id, recipes)',
     '                pass   # MUTATION',
     'der Bauplan nimmt die Rezeptkette in die Item-Liste auf'),
    ('Rezeptkette bricht bei Kauf-Items wieder ab',
     'eve_trader/industry.py',
     '''        bp = recipes.product_to_bp.get(tid)
        if not bp:
            return                      # Rohstoff - selbst schon aufgenommen
        mats = recipes.bp_materials.get((bp[0], bp[1])) or []
        for mtid, _q in mats:
            raus.add(mtid)
            _geh(mtid, tiefe + 1)''',
     '''        bp = recipes.product_to_bp.get(tid)
        if not bp:
            return
        mats = recipes.bp_materials.get((bp[0], bp[1])) or []
        for mtid, _q in mats:
            raus.add(mtid)   # MUTATION: keine Rekursion mehr''',
     'alle_items_der_kette liefert die VOLLSTAENDIGE Kette'),
    # HIER STAND EINE MUTATION 'Zyklusschutz der Rezeptkette entfernt'.
    # ENTFERNT (Sitzung 14), weil sie BLIND war und das auch bleiben muss:
    # ohne `tid in gesehen` bricht die Suche trotzdem bei `max_depth` ab, das
    # ERGEBNIS ist identisch. `gesehen` spart Arbeit (Diamant-Strukturen
    # werden sonst mehrfach durchlaufen), haelt aber keine Zusage ueber die
    # Ausgabe. Eine Mutation ohne beobachtbare Wirkung durch eine erfundene
    # Pruefung gruen zu bekommen waere genau die Sorte Schein-Absicherung,
    # gegen die die Rotprobe da ist. Die Pruefung aa260 zum Zyklus bleibt -
    # sie ist gueltig, wird nur von der Tiefengrenze gehalten.
    ('Tiefen-Lauf verschluckt Fehler wieder still',
     'eve_trader/ui/main_window.py',
     '                self._log_exception("Tiefen-Discovery fuer ids", str(_deep_err))',
     '                pass   # MUTATION',
     'ein Fehler im Tiefen-Lauf wird protokolliert statt verschluckt'),

    # --- (b42) DIE DREI BAU-SCHALTER SPERREN EINANDER (Sitzung 14) ---
    # Nutzer: "komisch das man beides anhacken kann, das eine sollte das
    # andere aushebeln". `do_build = force or _prefer_owned or ...` - steht
    # force vorne, ist der mittlere Haken wirkungslos; ohne "Assets abziehen"
    # ebenso, weil dann kein Bestand existiert.
    ('Mittlerer Bau-Haken bleibt trotz "Kosten ignorieren" bedienbar',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _aus = _f or not _a',
     '            _aus = not _a   # MUTATION',
     "'Kosten ignorieren' an -> mittlerer Haken ist grau"),
    ('Mittlerer Bau-Haken bleibt ohne Bestand bedienbar',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            pbtn.setEnabled(not _aus)',
     '            pbtn.setEnabled(True)   # MUTATION',
     "'Assets abziehen' aus -> mittlerer Haken ist grau"),
    ('Sperre wird beim Aufbau nicht angewandt (erst nach Klick)',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''        asset_cb.toggled.connect(lambda _v: _pbtn_sperre())
        _pbtn_sperre()''',
     '''        asset_cb.toggled.connect(lambda _v: _pbtn_sperre())''',
     # ERWARTUNG AUF DIE TEXTPROBE (Sitzung 14): funktional laesst sich der
     # ANFANGSZUSTAND nicht pruefen - b42 schaltet selbst um und ruft die
     # Sperre dabei auf, sieht den Ausgangszustand also nie. Die Mutation
     # blieb deshalb blind. aa261 haelt die Zusage stattdessen als Textprobe.
     'die Sperre wird schon beim Aufbau einmal angewandt'),
    ('Haken heisst wieder nach Materialfluss statt nach Bauentscheidung',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''        pbtn = _QCheckBox(_txt("Use what you have, even if buying "
                               "would be cheaper"))''',
     '''        pbtn = _QCheckBox(_txt("\\U0001F9F1 Always use stock"))''',
     'der mittlere Haken heisst nicht mehr nach Materialfluss'),

    # --- (b43/aa262) EINKAUFSLISTE IN DER AUFSCHLUESSELUNG (Sitzung 14) ---
    # Nutzer: "die gesammtkosten der einkaufsliste und pro stueck, ich will
    # aber jita Sell preis sehen" - ihm fehlte die Zahl, die sagt, was er
    # JETZT ausgeben muss.
    ('Einkaufsliste verschwindet wieder aus der Aufschluesselung',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                        ("Einkaufsliste (Jita Sell)", "Shopping list (Jita sell)"),
                        ("Einkaufsliste / St\\u00fcck", "Shopping list / unit")]''',
     '''                        ]''',
     'die Aufschluesselung nennt die Einkaufsliste'),
    ('Einkaufsliste rechnet mit eigener Mengenliste statt plan[buy]',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                _buy_map_e = (plan or {}).get("buy") or {}',
     '                _buy_map_e = {}   # MUTATION',
     "die Einkaufslisten-Summe stammt aus plan['buy']"),
    ('Posten ohne Preis fallen in der Einkaufsliste wieder still weg',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                        _ekl_ohne += 1',
     '                        pass   # MUTATION',
     'Posten ohne Preis werden gezaehlt, nicht verschwiegen'),

    # --- (aa263) FERTIGUNGSTIEFE NACH REZEPTSTUFE (Sitzung 14) ---
    # Kategorien mischen Rezeptstufen (an echten Daten gemessen:
    # intermediate_reactions 24/17, biochemical 16/16). Deshalb entscheidet
    # fuer Reaktionsprodukte jetzt die Stufe, nicht der Kategoriename.
    ('Reaktionen laufen wieder ueber den Kategorienamen',
     'eve_trader/ui/main_window.py',
     '''            _st = _stufen_map.get(tid)
            if _st is not None:''',
     '''            _st = None   # MUTATION
            if _st is not None:''',
     'nur REAKTIONSPRODUKTE gehen ueber die Stufe'),
    ('Stufe 1 und Stufe 2 haengen am selben Haekchen',
     'eve_trader/ui/main_window.py',
     '''                _schl = ("intermediate_reactions" if _st == 1
                         else "composite_reactions")''',
     '''                _schl = "composite_reactions"   # MUTATION''',
     'Stufe 1 haengt an intermediate, Stufe 2 an composite'),
    ('Stufenkarte wird gar nicht mehr gebildet',
     'eve_trader/ui/main_window.py',
     '            _stufen_map = industry.reaction_stage_map(recipes) if recipes else {}',
     '            _stufen_map = {}   # MUTATION',
     'die Stufenkarte wird ueberhaupt gebildet'),
    ('Ausfall der Stufenkarte wird still verschluckt',
     'eve_trader/ui/main_window.py',
     '            self._log_exception("Fertigungstiefe: Reaktionsstufen", str(_st_err))',
     '            pass   # MUTATION',
     'ein Fehler der Stufenkarte wird protokolliert'),

    # --- (aa264) AM HUB NICHT KAUFBAR -> BAUEN (Sitzung 14) ---
    # Nutzer: "der Bauplan will immer dass ich Ametat I kaufe,.. ja aber in
    # Jita gibts gar keine." Der Adjusted-Price-Rueckfall liess den Plan so
    # tun, als koenne man kaufen. Ein Preis, den niemand anbietet, ist keine
    # Kaufoption.
    ('Rueckfall-Preis gilt wieder als Kaufoption',
     'eve_trader/industry.py',
     '''                do_build = (force or _prefer_owned or buy_est is None
                            or _fallback or bcost <= buy_est)''',
     '''                do_build = (force or _prefer_owned or buy_est is None
                            or bcost <= buy_est)   # MUTATION''',
     'ohne Sell-Order am Hub wird gebaut, nicht gekauft'),
    ('Nicht kaufbare Items werden nicht mehr gemeldet',
     'eve_trader/industry.py',
     '                    nicht_kaufbar.add(tid)',
     '                    pass   # MUTATION',
     'das Item wird als nicht kaufbar GEMELDET'),
    ('Herkunft des Preises wird nicht mehr geprueft',
     'eve_trader/industry.py',
     '                _fallback = buy_price_src(tid)[1] if buy_est is not None else False',
     '                _fallback = False   # MUTATION',
     'ohne Sell-Order am Hub wird gebaut, nicht gekauft'),
    ('Vermerk in der Rezept-Struktur faellt weg',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        _nicht_kaufbar = plan.get("nicht_kaufbar") or set()',
     '        _nicht_kaufbar = set()   # MUTATION',
     'die Anzeige holt die Liste aus dem Plan'),

    # --- (aa208) FORTSCHRITTSBALKEN: NENNER = WAS DER PLAN BAUT (Sitzung 14) ---
    # Nutzer: "die Fortschrittsbalken im meine Baupläne gehen nicht weiter
    # oder sind stehen geblieben". Gekaufte Positionen standen im Nenner und
    # konnten nie erledigt werden - an 40 echten Plaenen gemessen war der
    # Balken auf 13 % gedeckelt, im schlechtesten Fall auf 1 %.
    ('Nenner zaehlt wieder alles Baubare statt des Plans',
     'eve_trader/ui/main_window.py',
     '''                _pos9 = [_t9x for _t9x in ((_plan9 or {}).get("build_runs") or {})
                         if _t9x != type_id]''',
     '''                _pos9 = list(recipes.product_to_bp)   # MUTATION''',
     'der Nenner ist, was der Plan WIRKLICH baut'),
    ('Endprodukt zaehlt wieder als Zwischen-Position',
     'eve_trader/ui/main_window.py',
     '                         if _t9x != type_id]',
     '                         ]   # MUTATION',
     'das Endprodukt selbst zaehlt nicht als Zwischen-Position'),
    ('Ausfall des Nenner-Plans wird still verschluckt',
     'eve_trader/ui/main_window.py',
     '''                    self._log_exception("Fortschritt: Plan fuer Nenner",
                                        str(_pl_err))''',
     '''                    pass   # MUTATION''',
     'ein Ausfall des Plans wird protokolliert, nicht verschluckt'),

    # --- (aa265) FRACHTAUFSCHLAG DARF NICHT STILL AUSFALLEN (Sitzung 14) ---
    # Faellt die Volumen-Ermittlung aus, entscheidet der Plan wieder ohne
    # Fracht - waehrend die Frachtkosten in der Anzeige weiter erscheinen.
    # An echten Daten: 50 Cormorants kaufen = 250'000 m3, bauen = 50'500 m3,
    # bei 350 ISK/m3 rund 70 Mio ISK Unterschied.
    ('Ausfall der Volumen-Ermittlung wird still verschluckt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    self._log_exception("Frachtaufschlag: Volumen", str(_fr_err))',
     '                    pass   # MUTATION',
     'ein Ausfall der Volumen-Ermittlung wird protokolliert'),
    ('Frachtaufschlag rechnet das Volumen nicht mehr ein',
     'eve_trader/industry.py',
     '        return float(p) + float(vols.get(tid, 0) or 0) * rate',
     '        return float(p)   # MUTATION',
     'der Aufschlag rechnet Volumen x Satz auf den Kaufpreis'),
    ('Item ohne Preis bekommt durch die Fracht eine erfundene Null',
     'eve_trader/industry.py',
     '''        p = price_fn(tid)
        if p is None:
            return None''',
     '''        p = price_fn(tid)
        if p is None:
            p = 0.0   # MUTATION''',
     'ein Item ohne Preis bleibt ohne Preis'),

    # --- (aa237) UEBERSETZUNGSNAME UEBERSCHRIEBEN -> ABSTURZ (Sitzung 14) ---
    # Vom NUTZER gemeldet, mitten im Bauen: in `_fill_bauplan_schedule` war
    # `_txt` die Uebersetzungsfunktion und wurde spaeter mit einem Warntext
    # ueberschrieben -> "TypeError: 'str' object is not callable". Die
    # Pruefung sah damals nur `t`, nicht `_txt`.
    ('Warntext ueberschreibt wieder den Uebersetzungsnamen',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    _warn_html = (_word + "<br>" + "<br>".join(_lines))',
     '                    _txt = (_word + "<br>" + "<br>".join(_lines))',
     'nirgends ein lokales `t` neben einem t()-Aufruf'),

    # --- (aa266) SICHTBAR MACHEN, WANN ESI LAEDT (Sitzung 14) ---
    # Nutzer merkte den 5-Minuten-Nachlauf nur an ploetzlich anderen Zahlen,
    # mitten beim Planen von Jobs.
    ('Nachlauf zeigt wieder das volle Overlay mitten in der Arbeit',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    _run_esi_load_all(still=True)',
     '                    _run_esi_load_all()   # MUTATION',
     'der Nachlauf nutzt ihn - kein Overlay mitten in der Arbeit'),
    ('ESI-Ladeanzeige geht nie wieder aus',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                self._bd_esi_busy = False
                _esi_lade_anzeige(False)''',
     '''                self._bd_esi_busy = False''',
     'und im Abschluss wieder aus'),
    ('Ladeanzeige wird gar nicht erst eingeschaltet',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _esi_lade_anzeige(True)',
     '            pass   # MUTATION',
     'die Anzeige geht beim Start an'),
    # --- aa267: Emoji zurueck auf die Bau-Knoepfe (Sitzung 16) ---
    # Der Aufruf wird ABGEKLEMMT, der Name bleibt stehen - genau die Falle
    # aus Sitzung 15. Eine Pruefung, die nur "icons.icon" sucht, bliebe gruen.
    ('Blaupausen-Knopf bekommt sein Symbol nicht mehr',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        self.b_compute_btn.setIcon(icons.icon("search"))',
     '        _weg267 = None and icons.icon("search")   # MUTATION',
     'Blaupausen-Knopf holt sein Symbol aus icons'),
    ('Capital-Umschalter traegt wieder das Satelliten-Emoji',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''        self.b_cap_mode = QPushButton(t("Capital mode"))
        self.b_cap_mode.setIcon(icons.icon("satellite"))''',
     '''        self.b_cap_mode = QPushButton(t("\\U0001F6F0 Capital mode"))''',
     'Capital-Knopf holt sein Symbol aus icons'),
    ('Capital-Kosten-Knopf bekommt sein Symbol nicht mehr',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        self.b_cap_btn.setIcon(icons.icon("satellite"))',
     '        _weg267b = None and icons.icon("satellite")   # MUTATION',
     'Capital-Kosten-Knopf holt sein Symbol aus icons'),
    # --- b44: Spalten-Reduktion im Blueprints-Tab (Sitzung 16) ---
    ('Blueprints-Tab zeigt wieder alle fuenfzehn Spalten',
     'eve_trader/ui/main_window.py',
     '            self.bp_table.setColumnHidden(_ci, _ci not in _BP_STD)',
     '            pass   # MUTATION',
     'genau fuenf Spalten sichtbar'),
    # ANDERE FUENF: die Anzahl stimmt weiter, nur die AUSWAHL kippt. Ohne
    # die zweite Pruefung waere das unbemerkt durchgegangen.
    ('Blueprints-Tab zeigt fuenf Spalten, aber die falschen',
     'eve_trader/ui/main_window.py',
     '        _BP_STD = {6, 8, 10, 11}        # Runs, Baukosten/Stk, Profit/Stk, ISK/Std',
     '        _BP_STD = {1, 2, 3, 4}   # MUTATION',
     'es sind die fuer die Profitvorschau'),
    ('Spalten-Menue schaltet nichts mehr ein',
     'eve_trader/ui/main_window.py',
     '''            _act.toggled.connect(
                lambda on, c=_ci: self.bp_table.setColumnHidden(c, not on))
            self._bp_col_acts[_ci] = _act''',
     '''            _act.toggled.connect(lambda on, c=_ci: None)   # MUTATION
            self._bp_col_acts[_ci] = _act''',
     'eine versteckte Spalte laesst sich wieder einblenden'),
    # --- b45: echtes ME statt globaler Einstellung (Sitzung 16) ---
    ('ME-Karte wird gar nicht erst in die opts gelegt',
     'eve_trader/ui/main_window.py',
     '''                opts["me_map"] = self._bp_me_map(
                    rows, bp_to_product, float(self.settings.get("bau_me", 10)))''',
     '''                _weg45 = None and self._bp_me_map(
                    rows, bp_to_product, float(self.settings.get("bau_me", 10)))''',
     'die Karte landet wirklich in den opts'),
    # MITTELWERT STATT SCHLECHTESTEM FALL - die Zahl sieht plausibel aus und
    # ist genau die, die im Spiel nicht eintritt (Regel 3).
    ('Mehrere Kopien: beste statt schlechteste ME',
     'eve_trader/ui/main_window.py',
     '''            schlechtestes[bp_type] = (float(me_wert) if vorher is None
                                      else min(vorher, float(me_wert)))''',
     '''            schlechtestes[bp_type] = (float(me_wert) if vorher is None
                                      else max(vorher, float(me_wert)))''',
     'bei mehreren Kopien zaehlt die schlechteste ME'),
    ('Deckel gegen die globale Einstellung faellt weg',
     'eve_trader/ui/main_window.py',
     '                raus[ziel[0]] = min(float(me_global), me_wert)',
     '                raus[ziel[0]] = me_wert   # MUTATION',
     'nie optimistischer als die globale Einstellung'),
    # --- b46: Filter-Vorgaben + entfallenes Gruppenfeld (Sitzung 16) ---
    ('Components und Reactions sind wieder vorangehakt',
     'eve_trader/ui/main_window.py',
     '''        for cb in (self.bp_cb_comp, self.bp_cb_react):
            cb.setChecked(False)''',
     '''        for cb in (self.bp_cb_comp, self.bp_cb_react):
            cb.setChecked(True)   # MUTATION''',
     'bp_cb_comp startet leer'),
    ('"nur profitable" startet wieder leer',
     'eve_trader/ui/main_window.py',
     '        self.bp_cb_profit.setChecked(True)',
     '        pass   # MUTATION',
     'bp_cb_profit startet angehakt'),
    ('Gruppen-Dropdown ist wieder da',
     'eve_trader/ui/main_window.py',
     '        frow.addWidget(self.bp_myb_cat)',
     '''        frow.addWidget(self.bp_myb_cat)
        self.bp_myb_group = QComboBox()   # MUTATION
        self.bp_myb_group.addItem("Alle Gruppen", None)
        frow.addWidget(self.bp_myb_group)''',
     'Gruppen-Dropdown gibt es nicht mehr'),
    # --- b47: Spalten-Knopf in Swing und Regional (Sitzung 16) ---
    ('Swing-Spalten-Knopf haengt nicht mehr an der Liste',
     'eve_trader/ui/main_window.py',
     '''        self._assemble_top_and_table(root, h_boxes, self.hold_table, "swing",
                                     box_ratio=60,
                                     spalten_btn=self._hold_spalten_btn)''',
     '''        self._assemble_top_and_table(root, h_boxes, self.hold_table, "swing",
                                     box_ratio=60)   # MUTATION''',
     'Swing: der Knopf haengt wirklich im Fenster'),
    ('Regional zeigt andere Spalten als gewaehlt',
     'eve_trader/ui/main_window.py',
     '        _REG_STD = [0, 1, 2, 5, 4, 8, 9]',
     '        _REG_STD = [0, 3, 4, 6, 7, 1, 2]   # MUTATION',
     'Regional: und es sind die vorgesehenen'),
    ('Regional-Reihenfolge wird nicht mehr gesetzt',
     'eve_trader/ui/main_window.py',
     '''        for _ziel, _log in enumerate(_REG_STD):
            _ist = _rhdr.visualIndex(_log)
            if _ist != _ziel:
                _rhdr.moveSection(_ist, _ziel)''',
     '        pass   # MUTATION',
     'Regional: Reihenfolge stimmt'),
    # --- Swing: Auswahl UND Reihenfolge (Sitzung 16, zweite Runde) ---
    ('Swing zeigt andere Spalten als gewaehlt',
     'eve_trader/ui/main_window.py',
     '        _SWING_STD = [0, 1, 4, 8, 3, 6]',
     '        _SWING_STD = [0, 1, 3, 6, 10, 2]   # MUTATION',
     'Swing: und es sind die vorgesehenen'),
    ('Swing-Reihenfolge wird nicht mehr gesetzt',
     'eve_trader/ui/main_window.py',
     '''        for _ziel, _log in enumerate(_SWING_STD):
            _ist = _shdr.visualIndex(_log)
            if _ist != _ziel:
                _shdr.moveSection(_ist, _ziel)''',
     '        pass   # MUTATION',
     'Swing: Reihenfolge stimmt'),
    # SPALTEN WIRKLICH GELOESCHT statt versteckt - die Anzahl sichtbarer
    # Spalten waere weiter 5, die Daten aber weg.
    # VERSTECKT, ABER UNERREICHBAR: das Menue kennt nur noch die sichtbaren
    # Spalten. Die Anzahl stimmt, die Daten sind da - aber der Nutzer kommt
    # nie wieder an sie heran. Genau das, was er NICHT wollte.
    ('Menue kennt nur noch die sichtbaren Spalten',
     'eve_trader/ui/main_window.py',
     '            acts[idx] = act',
     '            if idx in standard:   # MUTATION\n                acts[idx] = act',
     'jede versteckte Spalte steht im Menue'),
    # --- b48: Daytrade, sechs feste Spalten (Sitzung 16) ---
    # DIE MODUS-SCHLEIFE KEHRT ZURUECK: sie wirft die Wahl des Nutzers nach
    # JEDEM Scan wieder um. Beim Start saehe alles richtig aus - der Schaden
    # zeigt sich erst nach dem ersten Neuzeichnen.
    ('Modus-Logik blendet wieder bei jedem Neuzeichnen um',
     'eve_trader/ui/main_window.py',
     '        self.deals_table.horizontalHeaderItem(4).setText(t(self._DEV_LABEL[mode]))',
     '''        for _c in range(19):   # MUTATION
            self.deals_table.setColumnHidden(_c, _c not in self._DEAL_COLS[mode])
        self.deals_table.horizontalHeaderItem(4).setText(t(self._DEV_LABEL[mode]))''',
     'zugeschaltete Spalte ueberlebt das Neuzeichnen'),
    # ANDERE SECHS: die ANZAHL stimmt weiter, nur tragen zwei davon nicht in
    # jedem Modus - genau der Unsinn, den die Rechnung verhindern sollte.
    ('Daytrade zeigt andere Spalten als gewaehlt',
     'eve_trader/ui/main_window.py',
     '        _DAY_STD = [0, 1, 2, 7, 8, 10, 4, 17]',
     '        _DAY_STD = [0, 2, 4, 8, 9, 10, 11, 12]   # MUTATION',
     'es sind die vom Nutzer gewaehlten'),
    # DIE REIHENFOLGE geht still verloren, wenn moveSection wegfaellt: die
    # Auswahl stimmt, die Spalten stehen aber wieder in Index-Reihenfolge.
    ('Spalten-Reihenfolge wird nicht mehr gesetzt',
     'eve_trader/ui/main_window.py',
     '''            _ist = _dhdr.visualIndex(_log)
            if _ist != _ziel:
                _dhdr.moveSection(_ist, _ziel)''',
     '            pass   # MUTATION',
     'Reihenfolge von links nach rechts stimmt'),
    ('Kopfzeile folgt nicht mehr dem Modus',
     'eve_trader/ui/main_window.py',
     '        self.deals_table.horizontalHeaderItem(4).setText(t(self._DEV_LABEL[mode]))\n',
     '        pass   # MUTATION\n',
     'Kopf von Spalte 4 folgt dem Modus'),
    # --- b49: ME/TE aus den echten Blaupausen (Sitzung 16) ---
    # BESTE STATT SCHLECHTESTE KOPIE: die Zahl sieht plausibel aus, kauft aber
    # zu wenig Material ein - genau der Schaden, den der Nutzer gemeldet hat.
    ('Bauplan nimmt die BESTE eigene Kopie statt der schlechtesten',
     'eve_trader/ui/main_window.py',
     '''        return (float(min(me_werte)) if me_werte else None,
                float(min(te_werte)) if te_werte else None)''',
     '''        return (float(max(me_werte)) if me_werte else None,
                float(max(te_werte)) if te_werte else None)''',
     'schlechteste eigene Kopie gewinnt'),
    ('Echtes ME wird gar nicht erst nachgeschlagen',
     'eve_trader/ui/main_window.py',
     '''            if self._bd_esi_me_aktiv(key):
                _esi = self._bd_esi_me_te_for_item(tid)''',
     '''            if False and self._bd_esi_me_aktiv(key):   # MUTATION
                _esi = self._bd_esi_me_te_for_item(tid)''',
     'mit ESI schlaegt das echte ME die Kategorie-Annahme'),
    # DER SCHALTER HAENGT WIEDER AM FEINEN SCHLUESSEL - genau der Fehler, der
    # beim Bauen zuerst drin war: "Komponenten" abhaken blieb wirkungslos.
    ('Schalter greift bei Komponenten nicht mehr',
     'eve_trader/ui/main_window.py',
     '        return key if key in ("t1_hulls", "fuel_blocks", "tools") else "components"',
     '        return key   # MUTATION',
     'abgeschaltet gilt wieder die Handeingabe'),
    # OHNE EIGENE BLAUPAUSE AUF 0 FALLEN: kauft absurd viel Material ein.
    ('Ohne eigene Blaupause faellt die Rechnung auf ME 0',
     'eve_trader/ui/main_window.py',
     '''                if _esi is not None and _esi[0] is not None:
                    out[tid] = _esi[0]
                    continue''',
     '''                out[tid] = (_esi[0] if (_esi and _esi[0] is not None) else 0)
                continue''',
     'ohne Blaupause faengt die Kategorie auf'),
    # --- b50: kommt es bis in die BAUKOSTEN an? ---
    # Die Kategorie-Karte wird gebaut, aber nicht in die opts gelegt: alle
    # Einzelteile funktionieren, die Kosten aendern sich trotzdem nicht.
    # GENAU DIESE STILLE WIRKUNGSLOSIGKEIT war die Sorge des Nutzers.
    ('ME-Karte erreicht die Kostenrechnung nicht',
     'eve_trader/ui/main_window.py',
     '''            cat_me_map = self._bau_category_me_map(list(ids), groups,
                                                    recipes.reaction_products, type_id)''',
     '''            cat_me_map = {}   # MUTATION
            self._bau_category_me_map(list(ids), groups,
                                      recipes.reaction_products, type_id)''',
     'die Karte wird im Bauplan wirklich gebaut'),
    # --- b51: leere Zielmaerkte mit Absatz (Sitzung 16) ---
    # DER FALL, DER DIE GANZE IDEE TRAEGT: das Ziel kennt das Item gar nicht.
    # Filtert man ihn weg, findet man nur noch die halb leeren Maerkte.
    ('Nur halb leere Ziele, gar nicht gelistete fallen wieder raus',
     'eve_trader/hubs.py',
     '        if t is not None and (t.get("sell_min") or 0) > 0:',
     '        if t is None or (t.get("sell_min") or 0) > 0:   # MUTATION',
     'Item ohne jeden Eintrag am Ziel wird gefunden'),
    # TOTE MAERKTE DURCHLASSEN: Umsatz vor drei Wochen zaehlt wieder. Die
    # Liste fuellt sich mit Ware, auf der man sitzen bleibt.
    ('Auch tote Zielmaerkte gelten als Fund',
     'eve_trader/hubs.py',
     '''    if tage_mit_umsatz < 1:
        return None                       # am Ziel wird gar nicht gehandelt''',
     '    pass   # MUTATION',
     'toter Markt (7 Tage ohne Umsatz) wird verworfen'),
    # TAGESHOCH STATT DURCHSCHNITT: ein einziger Ausreisser-Tag erzeugt eine
    # gruene Traum-Marge, die es nie gab.
    ('Zielpreis wird aus dem Tageshoch geschaetzt',
     'eve_trader/hubs.py',
     '''    preise = [r.get("average") or 0 for r in hist[-30:]
              if (r.get("volume") or 0) > 0 and (r.get("average") or 0) > 0]''',
     '''    preise = [r.get("highest") or r.get("average") or 0 for r in hist[-30:]
              if (r.get("volume") or 0) > 0]''',
     'der Zielpreis ist der Durchschnitt, nicht das Tageshoch'),
    # SCHAETZUNG SIEHT AUS WIE EIN ABGELESENER PREIS.
    ('Geschaetzter Zielpreis wird nicht mehr gekennzeichnet',
     'eve_trader/ui/main_window.py',
     '                (("~" if d.get("sell_geschaetzt") else "")\n                 + isk(d["target_sell"], suffix=False), d["target_sell"]),',
     '                (isk(d["target_sell"], suffix=False), d["target_sell"]),',
     'die Tabelle markiert geschaetzte Zielpreise mit einer Tilde'),
    # --- b52: Handels-Charaktere (Sitzung 16) ---
    # LEER HEISST NICHT MEHR "ALLE": wer nichts einstellt, verliert plötzlich
    # jeden Einstand. Eine neue Einstellung darf niemandem still die Zahlen
    # verschieben - das ist der gefaehrlichste Fehler dieser Familie.
    ('Ohne Einstellung zaehlt plötzlich niemand mehr',
     'eve_trader/ui/main_window.py',
     '''        roh = self.settings.get("handels_charaktere")
        if not isinstance(roh, (list, tuple, set)):
            return set()''',
     '''        roh = self.settings.get("handels_charaktere")
        if not isinstance(roh, (list, tuple, set)):
            return {0}   # MUTATION''',
     'ohne Einstellung zaehlen alle Charaktere'),
    ('Schrott in der Einstellungsdatei wirft einen Fehler',
     'eve_trader/ui/main_window.py',
     '''            try:
                raus.add(int(x))
            except (TypeError, ValueError):
                continue''',
     '            raus.add(int(x))   # MUTATION',
     'unbrauchbare Eintraege werden uebergangen'),
    # DIE AUSWAHL WIRD NICHT GESICHERT: sie steht in der Liste, wirkt aber
    # nirgends - der Nutzer waehlt und nichts aendert sich.
    ('Ein-/Verkaeufer-Wahl wird nicht gespeichert',
     'eve_trader/ui/main_window.py',
     '''        self.settings["handels_charaktere"] = ids
        config.save_settings(self.settings)''',
     '        pass   # MUTATION',
     'die Wahl landet in der Einstellung'),
    # DOPPELTER CHARAKTER ZAEHLT ZWEIMAL - eine Menge mit zwei gleichen
    # Eintraegen ist keine Menge.
    ('Derselbe Charakter landet doppelt in der Menge',
     'eve_trader/ui/main_window.py',
     '            if d is not None and int(d) not in ids:',
     '            if d is not None:   # MUTATION',
     'zweimal derselbe Charakter steht einmal in der Datei'),
    # DER FREMDKAUF SCHLEICHT SICH WIEDER EIN: der Rueckfall ueber ALLE
    # Charaktere laeuft auch dann, wenn eine Handels-Menge gesetzt ist.
    ('Rueckfall ueber alle Charaktere laeuft immer mit',
     'eve_trader/ui/main_window.py',
     '''                _agg9 = (market.aggregate_holdings(store.get_transactions())
                         if not _hchars9 else {})''',
     '                _agg9 = market.aggregate_holdings(store.get_transactions())',
     'der Rueckfall ueber alle laeuft nur ohne gesetzte Menge'),
    # --- b53: Handels-Paar als ein Betrieb im Profits-Tab (Sitzung 16) ---
    ('Paar teilt sich die Lots nicht, der Handel bleibt unsichtbar',
     'eve_trader/market.py',
     '''        key = (("paar" if (_cid is not None and int(_cid) in paar) else _cid),
               tid)''',
     '        key = (_cid, tid)   # MUTATION',
     'mit Paar entsteht die Gewinnzeile'),
    # ALLE CHARAKTERE WERDEN ZUSAMMENGEWORFEN - das ist der Fehler, gegen den
    # die Trennung aus Sitzung 9 gebaut wurde: fremde Kaeufe matchen gegen
    # fremde Verkaeufe, der Umsatz blaeht sich auf.
    ('Alle Charaktere teilen sich die Lots, nicht nur das Paar',
     'eve_trader/market.py',
     '''        key = (("paar" if (_cid is not None and int(_cid) in paar) else _cid),
               tid)''',
     '        key = ("paar", tid)   # MUTATION',
     'ein Charakter ausserhalb des Paares bleibt getrennt'),
    ('Kaputte Eintraege im Paar werfen einen Fehler',
     'eve_trader/market.py',
     '    paar = {int(c) for c in (paar or []) if str(c).lstrip("-").isdigit()}',
     '    paar = {int(c) for c in (paar or [])}   # MUTATION',
     'unbrauchbare Eintraege im Paar aendern nichts'),
    ('Profits-Tab reicht das Paar gar nicht erst weiter',
     'eve_trader/ui/main_window.py',
     '        events = market.realized_trades(txs, tax, broker, paar=_paar)',
     '        events = market.realized_trades(txs, tax, broker)   # MUTATION',
     'der Profits-Tab reicht das Paar weiter'),
    # --- aa268: Platzhalter (Sitzung 16) ---
    # GENAU DER FEHLER, der beim Uebersetzen passiert ist: Text {what},
    # Aufruf format(was=...). Zur Laufzeit ein KeyError - vorher unsichtbar.
    ('Platzhalter im Aufruf falsch benannt',
     'eve_trader/ui/main_window.py',
     '"or covered from stock/jobs, see status per row).").format(what=was)',
     '"or covered from stock/jobs, see status per row).").format(was=was)',
     'jeder t(...).format(...)-Aufruf deckt alle Platzhalter ab'),
    # DEUTSCHE UEBERSETZUNG mit anderem Platzhalter als der Schluessel:
    # Englisch formatiert sauber, Deutsch stuerzt ab.
    ('Deutsche Uebersetzung nennt den Platzhalter anders',
     'eve_trader/sprache.py',
     '            "Keine {what} zum Kopieren.",',
     '            "Keine {was} zum Kopieren.",',
     'deutscher Katalog traegt dieselben Platzhalter wie der Schluessel'),
    # --- Sitzung 16: Warnbalken entfernt, stille Sperre muss bleiben ---
    # Der Sitzung-9-Fund: Portfolio zeigte +105 % statt -4 %, weil es gegen
    # Struktur-Preise rechnete. Der Warntext ist jetzt weg (Nutzer: "nervt"),
    # aber die Empfehlungs-Sperre ist der eigentliche Schutz und muss halten.
    ('Verkaufs-Empfehlung ignoriert die Preisquelle wieder',
     'eve_trader/ui/main_window.py',
     '        return sellable and not in_market and self._pf_price_source_ok()',
     '        return sellable and not in_market   # MUTATION',
     '_sell_ready gibt ohne Hub-Quelle keine Empfehlung'),
    # --- Sitzung 16: laufende Stufe darf nicht "fertig" sagen ---
    # Der Nutzer-Befund: blaue Kindzeilen (im Bau), gruener Haken auf der
    # zugeklappten Stufe darueber. `_zustand is not None` zaehlte "laeuft"
    # als erledigt. Diese Mutation stellt genau das wieder her.
    ('Laufende Positionen zaehlen wieder als fertig',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            _stufe_fertig = _stufe_abgedeckt and _stage_laeuft == 0',
     '            _stufe_fertig = _stufe_abgedeckt   # MUTATION',
     'in Bau: die Stufe traegt den LAUF-Punkt, nicht den Haken'),
    # Und die Farbe darf nicht still gruen bleiben.
    ('Laufende Stufe wird wieder gruen eingefaerbt',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                _stufe_farbe = (QColor(theme.GREEN) if _stufe_fertig
                                else QColor(theme.CYAN_RUN))''',
     '                _stufe_farbe = QColor(theme.GREEN)   # MUTATION',
     'in Bau: die Stufe ist NICHT gruen eingefaerbt'),
    # --- Sitzung 16: Reservierung in beide Richtungen ---
    # DIE ALTE SITZUNG-10-REGEL KEHRT ZURUECK: juengere Plaene blockieren
    # nicht. Zugesagt ist seit Sitzung 16 das Gegenteil - reserviert heisst
    # vergeben, unabhaengig vom Alter des Plans.
    ('Juengere Plaene blockieren wieder nicht (Vorrang-Regel zurueck)',
     'eve_trader/ui/mw_helpers.py',
     '''            # selbst aushungern.
            rm = p.get("reserve_map") or {}
            if not rm:
                continue''',
     '''            # selbst aushungern.
            if exclude_plan_id is not None and int(p.get("id") or 0) > int(exclude_plan_id):
                continue   # MUTATION
            rm = p.get("reserve_map") or {}
            if not rm:
                continue''',
     'auch der aeltere Plan sieht die Reservierung des juengeren'),
    # DER BANNER KUERZT WIEDER AUF DREI - der entscheidende Name verschwindet
    # hinter drei Punkten, genau wie beim Verlust.
    ('Fehlbedarf-Banner nennt wieder nur drei Namen',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    for _t, *_ in _fehl_auto)',
     '                    for _t, *_ in _fehl_auto[:3])',
     'der Fehlbedarf-Banner nennt ALLE Namen'),
    # DIE ZEILE SCHWEIGT WIEDER: der Live-Fehlbedarf wird gemerkt, aber
    # nicht in die Zeile geschrieben.
    ('Zeile traegt den Live-Fehlbedarf nicht mehr',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            if _fl and _fl[0] > 0:',
     '            if False and _fl and _fl[0] > 0:   # MUTATION',
     'die Zeile traegt den Live-Fehlbedarf'),
    # --- aa269: Tipps werden beim Anzeigen uebersetzt ---
    ('Tipps werden roh angezeigt, nicht uebersetzt',
     'eve_trader/ui/main_window.py',
     '        return t(self._TRADING_TIPS[self._tip_idx])   # beim Anzeigen uebersetzen',
     '        return self._TRADING_TIPS[self._tip_idx]   # MUTATION',
     '_pick_tip uebersetzt beim Anzeigen'),
    # Swing und Regional haben seit Sitzung 16 dasselbe Muster wie Daytrade -
    # und dieselbe Falle, wenn jemand das t() wieder entfernt.
    ('Swing-Trichterzeile laeuft nicht mehr durch t()',
     'eve_trader/ui/main_window.py',
     '''        for key, label in self._HOLD_DIAG_LABELS:
            if d.get(key):
                parts.append(f"{_n(d[key])} {t(label)}")''',
     '''        for key, label in self._HOLD_DIAG_LABELS:
            if d.get(key):
                parts.append(f"{_n(d[key])} {label}")''',
     'Swing-Trichterzeile uebersetzt beim Zusammensetzen'),
    ('Regional-Trichterzeile laeuft nicht mehr durch t()',
     'eve_trader/ui/main_window.py',
     '''        for key, label in self._RG_DIAG_LABELS:
            if d.get(key):
                parts.append(f"{_n(d[key])} {t(label)}")''',
     '''        for key, label in self._RG_DIAG_LABELS:
            if d.get(key):
                parts.append(f"{_n(d[key])} {label}")''',
     'Regional-Trichterzeile uebersetzt beim Zusammensetzen'),
    # --- aa271: der Zweisprachigkeits-Waechter selbst ---
    # Ein neuer deutscher Text direkt in einem Qt-Aufruf. Genau das, was ab
    # jetzt nie wieder still durchgehen darf.
    ('Neuer deutscher Text in einem Qt-Aufruf',
     'eve_trader/ui/main_window.py',
     '            self.statusBar().showMessage(t("Settings saved."))',
     '            self.statusBar().showMessage("Einstellungen wurden gespeichert und sind ab jetzt aktiv.")',
     'de_scan.py bleibt auf 0'),
    # --- aa272: Einkaufsliste folgt dem Baufortschritt (Sitzung 16) ---
    # Der Nutzer-Fall: sie zeigte die VOLLE Planmenge, obwohl Runs schon
    # erledigt waren - "ich will ja nicht mehr einkaufen als noetig".
    ('Einkaufsliste nimmt wieder die volle Planmenge',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            if _rest_only_cb.isChecked():',
     '            if False and _rest_only_cb.isChecked():   # MUTATION',
     'die Einkaufsliste kennt den Restbedarf'),
    # Der Schalter verschwindet aus der Leiste - er existiert, aber niemand
    # kann ihn bedienen.
    ('Restbedarf-Schalter nicht mehr sichtbar',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        mat_tab_toolbar.addWidget(_rest_only_cb)',
     '        pass   # MUTATION',
     'der Schalter ist sichtbar und vorbelegt'),
    # Erledigte Runs zaehlen nicht mehr ab -> die Liste schrumpft nie.
    ('Erledigte Runs zaehlen beim Restbedarf nicht mehr ab',
     'eve_trader/ui/mw_helpers.py',
     '    rem = {t: max(0, int(r or 0) - int((delivered or {}).get(t, 0) or 0))\n           for t, r in (build_runs or {}).items()}',
     '    rem = {t: int(r or 0) for t, r in (build_runs or {}).items()}   # MUTATION',
     'nach 153 von 200 Runs nur noch der Rest'),
    # --- aa273: Hand-Haekchen zaehlen fuer die Einkaufsliste ---
    ('Einkaufsliste ignoriert die Hand-Haekchen wieder',
     'eve_trader/ui/main_window.py',
     '        _checked = getattr(self, "_bd_runplan_checked", None) or set()',
     '        _checked = set()   # MUTATION',
     'der Restbedarf liest auch die Hand-Haekchen'),
    ('Beide Quellen werden addiert statt max',
     'eve_trader/ui/main_window.py',
     '            geliefert[_t] = max(int(geliefert.get(_t, 0) or 0), int(_n))',
     '            geliefert[_t] = int(geliefert.get(_t, 0) or 0) + int(_n)   # MUTATION',
     'beide Quellen werden per max verrechnet'),
    # --- aa275: Kaufmenge kommt aus der Fehlbedarfs-Rechnung ---
    # Die erste Fassung rechnete gegen den EINGEFRORENEN Bestand und zog die
    # volle Planproduktion ab - beides zu wenig Kaufmenge, also die
    # gefaehrliche Richtung (Nutzer: "koennte ich mir gar nicht meine
    # fehlenden Materialien zusammenbauen").
    ('Kaufmenge rechnet wieder gegen den eingefrorenen Bestand',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '''                    _rest_fehlt = {int(_m): int(_f)
                                   for _m, _f, *_r in (self._fehlbedarf_jetzt() or [])}''',
     '''                    _rest_fehlt = {int(_r["tid"]): max(0, int(_r.get("total", 0) or 0)
                                                       - int(_r.get("owned", 0) or 0))
                                   for _r in _rows}   # MUTATION''',
     'die Kaufmenge kommt aus der Fehlbedarfs-Rechnung'),
    ('Fehlmenge wird still auf Null gesetzt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                return int(_rest_fehlt.get(_t, 0) or 0)',
     '                return 0   # MUTATION',
     'die Fehlmenge wird zurueckgegeben, nicht verschluckt'),
    # --- aa276: Kleingedrucktes im Tooltip ---
    # Wird das Label wieder immer sichtbar, ist der Kasten zugestellt.
    ('Kleingedrucktes steht wieder komplett im Kasten',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                asset_age_lbl.setText("\\n".join(_wichtig))',
     '                asset_age_lbl.setText("\\n".join(parts))   # MUTATION',
     'nur Reservierung und Warnung bleiben sichtbar'),
    # Und die Reservierungszeile darf NICHT mit verschwinden - sie hat den
    # Ametat-Fall aufgeklaert.
    ('Auch die Reservierung verschwindet aus dem Kasten',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                asset_age_lbl.setVisible(bool(_wichtig))',
     '                asset_age_lbl.setVisible(False)   # MUTATION',
     'das Label ist ohne Befund unsichtbar'),
    # --- aa277: Ziel-Marge als zweite Schwelle ---
    ('Nachbessern prueft wieder nur gegen Null',
     'eve_trader/ui/main_window.py',
     '''                    under_target = bool(flag and cost > 0 and not loss
                                        and _ziel > 0 and _marge_neu < _ziel)''',
     '                    under_target = False   # MUTATION',
     'die Zeile kennt den Unter-Ziel-Zustand'),
    # VERLUST MUSS UNTER-ZIEL SCHLAGEN: sonst kommt bei einem Verlust die
    # harmlose gelbe Rueckfrage statt der roten Warnung.
    ('Unter-Ziel-Dialog verdraengt die Verlust-Warnung',
     'eve_trader/ui/main_window.py',
     '        if under_target and not (loss or fee_wiped):',
     '        if under_target:   # MUTATION',
     'der Dialog unterscheidet Verlust und Unter-Ziel'),
    # --- aa278: Profits startet auf 'Alles' ---
    # Zurueck auf 30 Tage = zurueck zur Tesseract-Falle (-12,5 Mio
    # angezeigt, +70,6 Mio echt).
    ('Profits-Tab startet wieder auf 30 Tage',
     'eve_trader/ui/main_window.py',
     '        self.pr_window.setCurrentIndex(max(0, self.pr_window.findData(0)))',
     '        self.pr_window.setCurrentIndex(1)   # MUTATION',
     "der Zeitraum startet auf 'Alles'"),
    # --- aa279: Bau-Charaktere aufgeklappt ---
    # Zugeklappt sieht der Nutzer bei frischer Installation nicht, dass
    # noch kein Charakter zugeteilt ist.
    ('Bau-Charaktere-Panel startet wieder zugeklappt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            self._build_char_roles_widget(), expanded=True, accent=theme.GREEN)',
     '            self._build_char_roles_widget(), expanded=False, accent=theme.GREEN)',
     'das Bau-Charaktere-Panel ist aufgeklappt'),
    # --- aa280: laufende Jobs einem Plan zuordnen ---
    ('Lauf-Punkt ignoriert die fremde Reservierung wieder',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                        if _lauf_r > 0 and self._job_gehoert_anderem_plan(
                                _tid_a, _fremd_res, eigene=_eigene_res):
                            _lauf_r = 0''',
     '                        pass   # MUTATION',
     'der Lauf-Punkt fragt nach der Zuordnung'),
    # Die eigene Reservierung MUSS die fremde schlagen - sonst verschwindet
    # der Punkt auch dort, wo dieser Plan selbst baut.
    ('Eigene Reservierung schlaegt die fremde nicht mehr',
     'eve_trader/ui/mw_helpers.py',
     '        if int((eigene or {}).get(tid, 0) or 0) > 0:',
     '        if False:   # MUTATION',
     'eigene Reservierung schlaegt die fremde'),
    # --- aa281: unsichere Zuordnung wird benannt ---
    ('Der Hinweis auf den anderen Bauplan verschwindet',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '''                            _mit_anspruch = self._plan_mit_anspruch(
                                _tid_a, _fremd_res)''',
     '                            _mit_anspruch = None   # MUTATION',
     'der Punkt traegt den Hinweis, wenn ein anderer Plan mit-beansprucht'),
    # Fragt der Hinweis den EIGENEN Anspruch ab, feuert er nie - genau der
    # haeufigste Fall (beide Plaene bauen dasselbe) faellt dann weg.
    ('Hinweis prueft wieder den eigenen Anspruch mit',
     'eve_trader/ui/mw_helpers.py',
     '''    def _plan_mit_anspruch(type_id, fremde_reservierungen):''',
     '''    def _plan_mit_anspruch(type_id, fremde_reservierungen, eigene=None):
        if eigene:
            return None   # MUTATION''',
     'der eigene Anspruch unterdrueckt den Hinweis NICHT'),
    # --- aa282: keine Emojis in den Bauplan-Reitern ---
    ('Blueprints-Reiter traegt wieder ein Emoji im Text',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        tab_icon_at(_tabs, 1, bp_tab_w, "Blueprints", "columns")',
     '        _tabs.insertTab(1, bp_tab_w, "\\U0001F4CB Blueprints")   # MUTATION',
     'kein Emoji in einer Reiter-Zeile'),
    # --- aa284: kaputter Import aus `sprache` ---
    # Der Nutzer-Absturz vom Blueprints-Tab: eine verunglueckte
    # Umbenennung traf die Import-Zeile mit.
    ('Import holt einen Namen, den `sprache` nicht kennt',
     'eve_trader/ui/main_window.py',
     '''    def _reload_my_blueprints(self):
        from ..sprache import t as _txt   # `t` ist hier lokal belegt''',
     '''    def _reload_my_blueprints(self):
        from ..sprache import _tbl as _txt   # MUTATION''',
     'kein Import eines Namens, den `sprache` nicht kennt'),
    # --- aa285: keine Emojis in der Oberflaeche ---
    ('Ein Emoji kehrt in eine Anzeige zurueck',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        cap_srch_lbl = QLabel()',
     '        cap_srch_lbl = QLabel("\\U0001F50D")   # MUTATION',
     'Emojis nur noch in Kommentaren/Docstrings'),
    # --- b55: Bedienelemente tragen ein Symbol ---
    ('Der Deals-Knopf verliert sein Symbol',
     'eve_trader/ui/main_window.py',
     '        self.deals_btn.setIcon(icons.icon("search"))',
     '        pass   # MUTATION',
     'deals_btn traegt ein Symbol'),
    ('Order-Reiter starten wieder ohne Symbol',
     'eve_trader/ui/main_window.py',
     '        tab_icon(self._orders_inner, buy_page, t("Buy orders (outbid?)"), "cart")',
     '        self._orders_inner.addTab(buy_page, t("Buy orders (outbid?)"))   # MUTATION',
     'kein Reiter ohne Symbol'),
    # --- aa286/aa287: Schloss-Zustand und nackte Knopftexte ---
    ('Reservier-Knopf faerbt nicht mehr nach Zustand',
     'eve_trader/ui/main_window.py',
     '                farbe=theme.AMBER if p.get("reserve") else theme.MUTED))',
     '                farbe=theme.MUTED))   # MUTATION',
     'der Reservier-Knopf faerbt nach Zustand'),
    ('Haken kehrt in den Done-Knopftext zurueck',
     'eve_trader/ui/main_window.py',
     '            ab = QPushButton(t("Reopen") if _ist_fertig else t("Done"))',
     '            ab = QPushButton(t("\\u21ba Reopen") if _ist_fertig else t("\\u2713 Done"))',
     'kein Zeichen im Knopftext'),
    # --- aa288: benutztes Modul ohne Import ---
    # Genau der Nutzer-Absturz: setIcon(icons...) ohne `import icons`.
    ('Der icons-Import im Setup-Assistenten faellt weg',
     'eve_trader/ui/setup_wizard.py',
     'from . import icons, theme',
     'from . import theme   # MUTATION',
     'kein benutztes Modul ohne Import'),
    # --- b19/b23: harte Mindestbreite, nicht der Hint ---
    ('Die Mindestbreite des Fensters faellt weg',
     'eve_trader/ui/main_window.py',
     '        self.setMinimumSize(1100, 520)',
     '        pass   # MUTATION',
     'die Grenze wird ausdruecklich gesetzt, nicht von Qt geraten'),
    # --- aa291: Erststart bietet die Rezeptdaten an ---
    ('Der Erststart fragt nicht mehr nach den Rezepten',
     'eve_trader/ui/main_window.py',
     '        QTimer.singleShot(400, self._erststart_rezepte_anbieten)',
     '        pass   # MUTATION',
     'die Frage wird beim Start angestossen'),
    # KEINE MUTATION FUER "nur einmal fragen" (Sitzung 16): jede Fassung,
    # die den Merker aushebelt, laesst den Dialog bei JEDEM Fensterbau
    # aufgehen - und `QMessageBox.exec()` blockiert dann die ganze Rotprobe
    # bis zur Zeitgrenze. Der Waechter aa291 prueft die Zusage am Quelltext;
    # eine Mutation dafuer waere die Kur, die den Patienten umbringt.
    # --- b57: Erststart-Dialoge stapeln sich nicht ---
    ('Die Rezeptfrage legt sich wieder auf offene Dialoge',
     'eve_trader/ui/main_window.py',
     '''        if QApplication.activeModalWidget() is None:
            return False''',
     '        return False   # MUTATION',
     'bei offenem Dialog tritt die Erststart-Frage zurueck'),
    # --- aa292/b59: die b-Suite haengt nicht an modalen Fenstern ---------
    # BIS SITZUNG 16 STAND HIER "KEINE MUTATION MOEGLICH": jede Mutation
    # liess die b-Suite endlos im modalen Einrichtungsfenster haengen. Seit
    # Sitzung 17 legt die Suite das Fenster an der KLASSE still und faengt
    # jedes uebrige modale Fenster ab (b59) - ein Fehler wird rot, statt die
    # Rotprobe eine Stunde bis zum Notausstieg warten zu lassen.
    ('Das Einrichtungsfenster wird nicht mehr an der Klasse stillgelegt',
     'test_bauplan_aufbau.py',
     '\nMainWindow._erste_einrichtung_pruefen = _einrichtung_still\n',
     '\npass   # MUTATION\n',
     'b59 das Einrichtungsfenster ist fuer JEDES Hauptfenster stillgelegt'),
    ('Der Erststart-Zeitgeber bindet wieder frueh',
     'eve_trader/ui/main_window.py',
     '        QTimer.singleShot(300, lambda: self._erste_einrichtung_pruefen())',
     '        QTimer.singleShot(300, self._erste_einrichtung_pruefen)   # MUTATION',
     'aa292 der Erststart-Zeitgeber bindet spaet'),
    # --- aa293: die README nennt jeden Server (Sitzung 17) ---
    ('Der Code spricht einen Server an, den die README nicht nennt',
     'eve_trader/industry.py',
     '_BASE = "https://www.fuzzwork.co.uk/dump/latest/"',
     '_BASE = "https://spiegel.example.net/dump/latest/"   # MUTATION',
     'aa293 jeder Server aus dem Code steht in der README'),
    ('Die README verschweigt Fuzzwork wieder',
     'README.md',
     '`www.fuzzwork.co.uk` (recipe data)',
     '`www.example.invalid` (recipe data)',
     'aa293 jeder Server aus dem Code steht in der README'),
    # --- aa312: ein 403 ist nicht "Berechtigung fehlt" (Sitzung 19) ---
    ('Die Meldung behauptet wieder eine fehlende Berechtigung',
     'eve_trader/ui/main_window.py',
     '                if _verweigert["no_scope"] or _verweigert["unclear"]:',
     '                if True:   # MUTATION',
     'aa312 entwarnt wird nur ohne fehlenden Scope und ohne Unklarheit'),
    ('Ein unlesbares Token gilt still als Entwarnung',
     'eve_trader/ui/main_window.py',
     '                    _verweigert["unclear"] = True',
     '                    pass   # MUTATION',
     'aa312 unlesbares Token setzt die Unklarheit'),
    ('Unlesbare Token liefern statt leer eine erfundene Berechtigung',
     'eve_trader/esi.py',
     '    if len(teile) < 2:\n        return set()',
     '    if len(teile) < 2:\n        return {"esi-universe.read_structures.v1"}   # MUTATION',
     "aa312 unlesbares Token liefert leer ('')"),
    ('Der Scope-Name loest sich von der einen Quelle',
     'eve_trader/config.py',
     'STRUCTURE_SCOPES = ["esi-markets.structure_markets.v1", STRUCTURE_READ_SCOPE]',
     'STRUCTURE_SCOPES = ["esi-markets.structure_markets.v1"]   # MUTATION',
     'aa312 der Scope-Name hat eine Quelle'),
    # --- aa313: die NPC-Station bekommt keinen Bonus (Sitzung 19) ---
    ('Die NPC-Station erbt still den Raitaru-Zeitbonus',
     'eve_trader/ui/main_window.py',
     '        "npc":     {"mfg": 0.0, "react": 0.0},',
     '        "npc":     {"mfg": 15.0, "react": 0.0},   # MUTATION',
     'aa313 die NPC-Station hat keinen Rollen-Zeitbonus'),
    ('Die NPC-Station bekommt Rig-Slots',
     'eve_trader/ui/main_window.py',
     '        "npc": 0,\n    }',
     '        "npc": 3,   # MUTATION\n    }',
     'aa313 die NPC-Station hat keine Rig-Slots'),
    ('Die NPC-Station soll ploetzlich reagieren koennen',
     'eve_trader/ui/main_window.py',
     '        "npc": ({"mfg", "invention", "copy", "research"}, "L"),',
     '        "npc": ({"mfg", "react"}, "L"),   # MUTATION',
     'aa313 aber NICHT reagiert (dafuer braucht es eine Refinery)'),
    ('Ein Typ wird eingetragen, aber nicht in allen Tabellen',
     'eve_trader/ui/main_window.py',
     '        ("npc", "NPC station"),',
     '        ("npc", "NPC station"),\n        ("keepstar", "Keepstar"),   # MUTATION',
     'aa313 Typ keepstar steht in der Rollenbonus-Tabelle'),
    ('Die Facility Tax der NPC-Station wird wieder frei geraten',
     'eve_trader/ui/main_window.py',
     '            ftax_sp.setEnabled(not _ist_npc)',
     '            ftax_sp.setEnabled(True)   # MUTATION',
     'aa313 die Facility Tax der NPC-Station steht fest auf 0,25 %'),
    # --- aa314: eine NPC-Station laesst sich verknuepfen (Sitzung 19) ---
    ('Die Stationsgrenze rutscht und schluckt Upwell-Strukturen',
     'eve_trader/esi.py',
     'NPC_STATION_MAX = 64_000_000',
     'NPC_STATION_MAX = 2_000_000_000_000   # MUTATION',
     'aa314 eine Upwell-Struktur ist keine Station'),
    ('Die untere Stationsgrenze schneidet die erste Station ab',
     'eve_trader/esi.py',
     '    return NPC_STATION_MIN <= lid < NPC_STATION_MAX',
     '    return NPC_STATION_MIN < lid < NPC_STATION_MAX   # MUTATION',
     'aa314 die untere Grenze gehoert dazu'),
    ('Die Stationsauflösung verlangt wieder eine Anmeldung',
     'eve_trader/esi.py',
     '    r = _get_with_retry(url, headers={"User-Agent": _USER_AGENT}, timeout=30)\n'
     '    r.raise_for_status()\n'
     '    return r.json()   # {name, system_id, type_id, owner, ...}',
     '    r = _get_with_retry(url, headers=_auth_headers("x", 1), timeout=30)   # MUTATION\n'
     '    r.raise_for_status()\n'
     '    return r.json()',
     'aa314 und ohne Anmeldung - eine Station kennt kein Andockrecht'),
    ('Die Auswahlliste vergisst die Stationen wieder',
     'eve_trader/ui/main_window.py',
     '                if f.get("kind") == "station" and f.get("station_id"):',
     '                if False:   # MUTATION',
     'aa314 Struktur und Station stehen beide zur Wahl'),
    ('Der Verknuepfungs-Dialog faellt auf die Kauf-Hub-Liste zurueck',
     'eve_trader/ui/main_window.py',
     '        _known = self._link_orte()',
     '        _known = self._market_structures()   # MUTATION',
     'aa314 der Dialog fuellt die Auswahl aus der neuen Liste'),
    ('Gespeicherte Stationen werden bei jedem Klick neu angelegt',
     'eve_trader/ui/main_window.py',
     '                     if f.get("kind") == "station" and f.get("station_id")}',
     '                     if False}   # MUTATION',
     'aa314 gespeicherte Stationen werden nicht doppelt angelegt'),
    ('Der Ingame-Link-Weg schickt Stationen wieder zum Struktur-Endpunkt',
     'eve_trader/ui/main_window.py',
     '        _ist_station = esi.is_npc_station(structure_id)',
     '        _ist_station = False   # MUTATION',
     'aa314 der Ingame-Link-Weg erkennt eine Station an der Id'),
    ('Die von Hand eingetragene Station wird als Struktur gespeichert',
     'eve_trader/ui/main_window.py',
     '                {"kind": "station" if _ist_station else "structure",',
     '                {"kind": "structure",   # MUTATION',
     'aa314 die Station wird als Station gespeichert, nicht als Struktur'),
    ('Das Systemfeld der Station bleibt unvereinheitlicht',
     'eve_trader/ui/main_window.py',
     '                info["solar_system_id"] = info.get("system_id")',
     '                pass   # MUTATION',
     'aa314 das Systemfeld beider Endpunkte wird vereinheitlicht'),
    ('Die Systemauskunft wirft die Stationen wieder weg',
     'eve_trader/esi.py',
     '            "stations": [int(x) for x in (d.get("stations") or [])]}',
     '            "stations": []}   # MUTATION',
     'aa314 die Systemauskunft reicht die Stationen durch'),
    ('Die Stationsauswahl wird nicht mehr gefuellt',
     'eve_trader/ui/main_window.py',
     '                _fuelle_stationen(r.get("stationen") or [])',
     '                pass   # MUTATION',
     'aa314 sie wird aus der Systemantwort gefuellt'),
    ('Die gewaehlte Station verknuepft sich nicht mehr selbst',
     'eve_trader/ui/main_window.py',
     '                data["link_structure_id"] = int(_stat_gewaehlt["id"])',
     '                pass   # MUTATION',
     'aa314 die gewaehlte Station ist zugleich die Verknuepfung'),
    ('Stationsnamen werden auch fuer Spielerstrukturen geholt',
     'eve_trader/ui/main_window.py',
     '                              if typ.currentData() == "npc" else []):',
     '                              if True else []):   # MUTATION',
     'aa314 Stationsnamen werden nur geholt, wenn sie gebraucht werden'),
    ('Die gewaehlte Station wird nicht als Ort gemerkt - nur die Nummer bleibt',
     'eve_trader/ui/main_window.py',
     '                             "region_id": None, "station_id": _sid_fav})',
     '                             "region_id": None, "station_id": None})   # MUTATION',
     'aa314 die gewaehlte Station wird auch als Ort gemerkt'),
    ('Beide Verknuepfungswege stehen wieder nebeneinander',
     'eve_trader/ui/main_window.py',
     '                form.setRowVisible(_link_row, not _ist_npc)',
     '                pass   # MUTATION',
     'aa314 die Verknuepfungszeile verschwindet bei der NPC-Station'),
    ('Ein Tippfehler im System bleibt wieder stumm',
     'eve_trader/ui/main_window.py',
     '                    station_cb.setItemText(0, t("\\u2014 system not found \\u2014"))',
     '                    pass   # MUTATION',
     'aa314 ein unbekannter Systemname sagt das auch'),
    ('Die Stationsauswahl erscheint bei jedem Strukturtyp',
     'eve_trader/ui/main_window.py',
     '                form.setRowVisible(_stat_row, _ist_npc)',
     '                form.setRowVisible(_stat_row, True)   # MUTATION',
     'aa314 sie ist nur beim Typ NPC-Station sichtbar'),
    # --- aa315: warnen, wenn ohne Struktur gerechnet wird (Sitzung 19) ---
    ('Gekaufte Zweige loesen wieder Struktur-Warnungen aus',
     'eve_trader/ui/main_window.py',
     '                if (_k or {}).get("decision") == "build":',
     '                if True:   # MUTATION',
     'aa315 ein gekaufter Zweig loest keine Warnung aus'),
    ('Reaktionen gelten nicht mehr als unmoeglich',
     'eve_trader/ui/main_window.py',
     '                fehlt.append((_st, _st.startswith("reaction")))',
     '                fehlt.append((_st, False))   # MUTATION',
     'aa315 die Reaktion ist die kritische, die anderen nicht'),
    ('Die Warnzeile verschwindet aus dem Bauplan',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            v.addWidget(_warn_lbl)',
     '            pass   # MUTATION',
     'aa315 die Warnzeile steht ueber den Tabs'),
    ('Der Fertigungsindex startet nicht mehr bei 0',
     'eve_trader/config.py',
     '    "bau_mfg_index": 0.0,     # manufacturing system cost index (live from ESI)',
     '    "bau_mfg_index": 0.05,   # MUTATION',
     'aa315 der Fertigungsindex startet bei 0'),
    # --- aa316: keine unmoeglichen Zuweisungen (Sitzung 19) ---
    ('Die feste Zuweisung hebelt die Fit-Pruefung wieder aus',
     'eve_trader/ui/main_window.py',
     '            if s and self._struct_kann(s, activity):',
     '            if s:   # MUTATION',
     'aa316 und die Reaktion faellt auf die Refinery zurueck'),
    ('Die Auswahl bietet wieder jede Struktur fuer jede Stufe an',
     'eve_trader/ui/main_window.py',
     '                    if self._struct_kann(s, akey):',
     '                    if True:   # MUTATION',
     'aa316 die Auswahl bietet nur faehige Strukturen an'),
    ('Der Rechenweg nimmt die unmoegliche Zuweisung wieder an',
     'eve_trader/ui/main_window.py',
     '            if _fest is not None and not self._struct_kann(_fest, activity):\n'
     '                _fest = None',
     '            pass   # MUTATION',
     'aa316 der Rechenweg verwirft die unmoegliche Zuweisung auch'),
    ('Eine NPC-Station duerfte ploetzlich reagieren',
     'eve_trader/ui/main_window.py',
     '        "npc": ({"mfg", "invention", "copy", "research"}, "L"),',
     '        "npc": ({"mfg", "invention", "copy", "research", "react"}, "L"),   # MUTATION',
     'aa316 eine NPC-Station kann es nicht'),
    # --- aa317: Bestand nur dort, wo dieser Plan baut (Sitzung 19) ---
    ('Der neue Bestandsbereich zaehlt wieder alle Bau-Strukturen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    structs = self._bau_plan_structs()',
     '                    pass   # MUTATION',
     'aa317 gezaehlt werden dann nur die Strukturen des Plans'),
    ('Ohne gespeicherte Wahl gilt wieder der alte Bereich',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            self.settings.get("bau_stock_scope") or "structures")',
     '            self.settings.get("bau_stock_scope") or "plan")   # MUTATION',
     'aa317 das Dropdown zeigt ohne gespeicherte Wahl'),
    ('Der Rechenweg faellt wieder auf den alten Bereich zurueck',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                _scope0 = (self.settings.get("bau_stock_scope") or "structures")',
     '                _scope0 = (self.settings.get("bau_stock_scope") or "plan")   # MUTATION',
     'aa317 und der Rechenweg nimmt denselben Standard an'),
    # --- aa318: OWNED nennt den reservierten Anteil (Sitzung 19) ---
    ('Die Spalte verschweigt den reservierten Anteil wieder',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            if _res_row > 0 and 3 in _exact:',
     '            if False:   # MUTATION',
     'aa318 nur wenn ueberhaupt etwas reserviert ist'),
    # --- aa319: eigene BPC -> ME/TE 0/0 (Sitzung 19) ---
    ('Beim Umschalten auf eigene BPC bleibt die erfundene ME stehen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                self._bd_me, self._bd_te = self._bd_own_bpc_me_te(type_id)',
     '                pass   # MUTATION',
     'aa319 das Umschalten holt die echten Werte'),
    ('Aus der Invention-Sperre heraus bleibt die fremde ME stehen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                        me_spin.setValue(_obc_me)',
     '                        me_spin.setValue(0)   # MUTATION',
     'aa319 auch aus der Invention-Sperre heraus werden sie gesetzt'),
    ('Statt der schlechtesten Kopie gewinnt die beste',
     'eve_trader/ui/main_window.py',
     '            return min(_w) if _w else 0',
     '            return max(_w) if _w else 0   # MUTATION',
     'aa319 bei mehreren gewinnt die SCHLECHTESTE'),
    ('Unbekannte Blaupausen bekommen still einen guten Wert',
     'eve_trader/ui/main_window.py',
     '        _d = self._bd_lookup_owned_bp_for_item(type_id) or {}',
     '        _d = self._bd_lookup_owned_bp_for_item(type_id) or {"me": 10, "te": 20}',
     'aa319 leerer Cache -> 0/0 (Nichtwissen darf nichts verguenstigen)'),
    ('Der Rueckfall greift bei JEDEM Rebuild und ueberschreibt die Eingabe',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    if not me_spin.isEnabled():\n'
     '                        me_spin.setEnabled(True)\n'
     '                        me_spin.blockSignals(True)',
     '                    if True:   # MUTATION\n'
     '                        me_spin.setEnabled(True)\n'
     '                        me_spin.blockSignals(True)',
     'aa319 der Rueckfall haengt an der Sperre, nicht am Rebuild'),
    ('Der Hinweis zur eigenen BPC verschwindet',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    _obc_gefunden = self._bd_lookup_owned_bp_for_item(top_type_id)',
     '                    _obc_gefunden = None   # MUTATION',
     'aa319 der Hinweis sagt, was GERADE gilt - nicht beide Faelle'),
    # --- aa320: kein roher Platzhalter in der Anzeige (Sitzung 19) ---
    ('Das f-Praefix faellt wieder weg, der Platzhalter steht roh da',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    + f\'</span> <b>{outcome["me_pct"]}%</b>\'',
     '                    + \'</span> <b>{outcome["me_pct"]}%</b>\'   # MUTATION',
     'aa320 kein unaufgeloester Platzhalter in der Invention-Karte'),
    # --- aa321: Blacklist speichert nicht je Tastendruck (Sitzung 19) ---
    ('Die Blacklist schreibt wieder bei jedem Buchstaben auf die Platte',
     'eve_trader/ui/main_window.py',
     '        self.bl_items.textChanged.connect(self._blacklist_verzoegert)',
     '        self.bl_items.textChanged.connect(self._save_blacklist_items)',
     'aa321 das Feld haengt am verzoegerten Speichern'),
    ('Der Timer feuert dauernd statt einmal',
     'eve_trader/ui/main_window.py',
     '            _tm.setSingleShot(True)',
     '            _tm.setSingleShot(False)   # MUTATION',
     'aa321 der Timer feuert nur einmal'),
    ('Das bearbeitete Feld wird nicht mehr gemerkt',
     'eve_trader/ui/main_window.py',
     '            self._bl_last_widget = _w',
     '            pass   # MUTATION',
     'aa321 das bearbeitete Feld wird gemerkt (der Timer ist spaeter der Sender)'),
    ('Das Blacklist-Feld stoesst die Neurechnung der Ausschluesse nicht an',
     'eve_trader/ui/main_window.py',
     '        self._bau_refresh_exclusions_and_rebuild()\n\n    def _bau_cant_build',
     '        pass   # MUTATION\n\n    def _bau_cant_build',
     'aa321 das Textfeld stoesst die Ausschluss-Neurechnung an'),
    # --- aa322: verknuepfter Charakter ist sofort benutzbar (Sitzung 19) ---
    ('Ein neuer Charakter bekommt keine Rollen mehr',
     'eve_trader/ui/main_window.py',
     '            self._bau_rollen_vorbelegen(res["character_id"])',
     '            pass   # MUTATION',
     'aa322 beim Verknuepfen werden die Rollen vorbelegt'),
    ('Die Reaktions-Rolle faellt aus der Vorbelegung',
     'eve_trader/ui/main_window.py',
     '        for _key in ("bau_build_chars", "bau_reaction_chars",',
     '        for _key in ("bau_build_chars",   # MUTATION',
     'aa322 die Rolle bau_reaction_chars wird gesetzt'),
    ('Die Einmal-Migration ueberschreibt auch bewusste Abwahl',
     'eve_trader/config.py',
     '        if not any(data.get(_k) for _k in _rollen):',
     '        if True:   # MUTATION',
     'aa322 sie greift nur, wenn keine einzige Rolle gesetzt ist'),
    # --- aa294: Versionsnummer lesbar und vor der Freigabe sichtbar ---
    ('Die Versionsnummer ist fuer die Update-Pruefung unlesbar',
     'eve_trader/__init__.py',
     '__version__ = "1.0.7"',
     '__version__ = "unbekannt"',
     'aa294 die Versionsnummer ist lesbar und hat drei Teile'),
    ('pruefe.py zeigt die Programmversion nicht mehr',
     'pruefe.py',
     'print(f"Programmversion: {_ver}  -  die Release-Marke',
     'pass  # MUTATION\nif 0: print(f"Programmversion {_ver}  -  die Release-Marke',
     'aa294 pruefe.py zeigt die Programmversion vor der Freigabe'),
    # --- aa270/aa271: die 133 Anzeigetexte (Sitzung 17) ---
    ('Ein Trichter-Label faellt aus dem Katalog',
     'eve_trader/ui/main_window.py',
     '        ("errors", "⚠ analysis error (please load again)"),',
     '        ("errors", "⚠ analysis error (please reload)"),   # MUTATION',
     'aa270 jedes Label in _DEAL_DIAG_LABELS hat eine deutsche Uebersetzung'),
    ('Ein deutscher Anzeigetext kehrt ueber eine Variable zurueck',
     'eve_trader/ui/main_window.py',
     '                    status_txt = t("enough \\u2713")',
     '                    status_txt = "genug \\u2713"   # MUTATION',
     'aa271 de_scan3.py steigt nicht ueber die Ratsche'),
    # --- aa271: de_scan4 und Katalog-Konstanten (Sitzung 17) ---
    ('Eine Fehlermeldung im Hintergrund-Modul ist wieder deutsch',
     'eve_trader/auth.py',
     '        raise TimeoutError(_txt("Login cancelled or timed out."))',
     '        raise TimeoutError("Login abgebrochen oder Zeitueberschreitung.")   # MUTATION',
     'aa271 de_scan4.py steigt nicht ueber die Ratsche'),
    ('Der CCP-Hinweis faellt aus dem Katalog',
     'eve_trader/__init__.py',
     '    "trademarks belong to CCP hf."',
     '    "trademarks belong to CCP."   # MUTATION',
     'aa271 CCP_HINWEIS steht im Katalog'),
    # --- aa295: Status-Rang aus der Farbe (Sitzung 17) ---
    ('Fehlendes Material sortiert wieder nach unten',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            if status_col in (theme.RED, theme.AMBER, theme.VIOLET):',
     '            if status_col in (theme.RED, theme.VIOLET):   # MUTATION',
     'aa295 rot/gelb/violett'),
    ('Die Stufen-Spalte zeigt wieder den deutschen Schluessel',
     'eve_trader/ui/main_window.py',
     'r["name"], self._kategorie_anzeige(r["stage"]), ',
     'r["name"], r["stage"], ',
     'aa295 die Stufen-Spalte zeigt uebersetzte Namen'),
    ('Unbekannte Stufen fallen wieder still aus der Warnzeile',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        folge += sorted(s for s in (by_stage or {})',
     '        folge += sorted(s for s in ()   # MUTATION',
     'aa296 eine UNBEKANNTE Stufe wird angehaengt'),
    ('Die Warnzeile kennt wieder nur drei Stufen',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '    _BP_STUFEN_FOLGE = ("Endprodukt", "Komponente", "H\\u00fcllen", "Fuel", "Tools",',
     '    _BP_STUFEN_FOLGE = ("Endprodukt", "Komponente", "Reaktion"); _x = ("Fuel", "Tools",   # MUTATION',
     'aa296 Reihenfolge wie im Blaupausen-Reiter'),
    ('Die Rezeptfrage wird im Testlauf nicht mehr stillgelegt',
     'test_bauplan_aufbau.py',
     '\nMainWindow._erststart_rezepte_anbieten = _einrichtung_still\n',
     '\npass   # MUTATION\n',
     'b59 auch die drei Erststart-Fragen'),
    # --- b60/aa297: Struktur-Berechtigung (Sitzung 17) ---
    ('Berechtigungs-Schalter gelten wieder erst nach Save',
     'eve_trader/ui/main_window.py',
     '                lambda _i, k=_key, c=_cb: self._scope_schalter_sofort(k, c))',
     '                lambda _i, k=_key, c=_cb: None)   # MUTATION',
     'b60 Umstellen auf On gilt SOFORT'),
    ('Verweigerter Strukturname wird wieder still uebersprungen',
     'eve_trader/ui/main_window.py',
     '                            _verweigert["n"] += 1',
     '                            pass   # MUTATION',
     'aa297 ein verweigerter Strukturname'),
    ('Struktur-Maerkte wieder standardmaessig aus',
     'eve_trader/config.py',
     '    "use_structures": True,   # player-structure markets (needs structure scopes)',
     '    "use_structures": False,   # MUTATION',
     'aa297 Struktur-Maerkte sind fuer neue Installationen AN'),
    # --- aa298: Handelsplan-Knopf bleibt draussen (Sitzung 17) ---
    # Entfernt mit den Knoepfen (Code existiert nicht mehr): Handelsplan
    # 332/373/374, Akkumulationsplan 332/366 (Nummern zum jeweiligen Stand).
    ('Der Handelsplan-Knopf kehrt in die Daytrade-Leiste zurueck',
     'eve_trader/ui/main_window.py',
     '        for name in ("deals_btn", "gold_btn", "refresh_btn",\n',
     '        for name in ("deals_btn", "gold_btn", "refresh_btn", "plan_btn",\n',
     'aa298 der Handelsplan bleibt entfernt'),
    ('Der Akkumulationsplan-Knopf kehrt in die Swing-Leiste zurueck',
     'eve_trader/ui/main_window.py',
     '            [self.hold_btn, self.hold_top_btn, self.hold_gold_btn]))',
     '            [self.hold_btn, self.hold_top_btn, self.hold_gold_btn]))\n        self.hold_plan_btn = None   # MUTATION',
     'aa298 der Akkumulationsplan (Swing) bleibt entfernt'),
    ('Der Frachtplan-Knopf kehrt in die Regional-Leiste zurueck',
     'eve_trader/ui/main_window.py',
     '            [self.rg_go, self.rg_top_btn]))',
     '            [self.rg_go, self.rg_top_btn]))\n        self.rg_plan_btn = None   # MUTATION',
     'aa298 der Frachtplan (Regional) bleibt entfernt'),
    # --- b61: Regional-Preisspalten sagen, womit gerechnet wird (Sitzung 17) ---
    ('Spalte 2 zeigt bei Sofortverkauf wieder den Sell-Preis',
     'eve_trader/ui/main_window.py',
     '                if _sofort_rg else\n',
     '                if False else   # MUTATION\n',
     'b61 instant: Spalte 2 zeigt den Preis'),
    ('Spalte 1 heisst wieder Buy (source)',
     'eve_trader/ui/main_window.py',
     '            [t("Item"), t("Sell (source)"), t("Sell (destination)"),',
     '            [t("Item"), t("Buy (source)"), t("Sell (destination)"),   # MUTATION',
     'b61 Spalte 1 heisst Sell (source)'),
    # --- de_scan4 Regel A/B: Ladetexte (Sitzung 17, Nutzer-Screenshot) ---
    ('Das Ladebild im Regional-Tab ist wieder deutsch',
     'eve_trader/ui/main_window.py',
     '                status(t("Loading destination order book \\u2026 (whole region, may take a while)"))',
     '                status("Lade Ziel-Orderbuch \\u2026 (ganze Region, kann dauern)")   # MUTATION',
     'aa271 de_scan4.py steigt nicht ueber die Ratsche'),
    # --- b62 / Scanner-Selbsttests (Sitzung 17, Nutzer-Screenshots) ---
    ('Profits-Tab: Zeitraum wieder fest auf Deutsch',
     'eve_trader/ui/main_window.py',
     '        head.addWidget(QLabel(t("Period:")))',
     '        head.addWidget(QLabel("Zeitraum:"))   # MUTATION',
     'b62 keiner der gemeldeten deutschen Texte'),
    ('de_scan3 haelt Beschriftungen wieder fuer CSS',
     'de_scan3.py',
     '    r"\\b(?:color|background',
     '    r"(?:[A-Za-z-]+)|(?:color|background',
     'aa271 de_scan3: eine Beschriftung mit Doppelpunkt'),
    # --- aa193/aa296b: Karten ohne Schloss, Ueberschrift ohne Zahnrad (Sitzung 17) ---
    ('Das Schloss kehrt hinter den Gewinn auf der Karte zurueck',
     'eve_trader/ui/main_window.py',
     '                    # Die Erklaerung (eingefroren, seit wann) bleibt im Tooltip.\n',
     '                    lbl.setText(lbl.text() + " " + icons.html("lock"))   # MUTATION\n',
     'aa193 die Karte traegt KEIN Schloss'),
    ('Das Zahnrad kehrt vor Production depth zurueck',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _txt("Production depth"),',
     '            _txt("\\u2699 Production depth"),',
     'aa296b die Ueberschrift Production depth'),
    # --- b63: Discord-Knopf (Sitzung 17) ---
    ('Der Discord-Knopf oeffnet nichts mehr',
     'eve_trader/ui/main_window.py',
     '        from PySide6.QtGui import QDesktopServices\n        QDesktopServices.openUrl(QUrl(config.DISCORD_URL))',
     '        from PySide6.QtGui import QDesktopServices\n        pass   # MUTATION',
     'b63 ein Klick oeffnet genau den Discord-Server'),
    ('Der Discord-Knopf rutscht unter den Spenden-Knopf',
     'eve_trader/ui/main_window.py',
     '        self.discord_btn.clicked.connect(self._open_discord)\n        sv.addWidget(self.discord_btn)\n',
     '        self.discord_btn.clicked.connect(self._open_discord)\n',
     'b63 er sitzt DIREKT ueber dem Spenden-Knopf'),
    # --- b64: Bauplan-Seitenleiste offen, Endprodukt-Zeile uebersetzt (Sitzung 17) ---
    ('Build or buy startet wieder zugeklappt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _strat_panel, expanded=True, accent=theme.CYAN)',
     '            _strat_panel, expanded=False, accent=theme.CYAN)   # MUTATION',
     'b64 Build or buy und Production depth starten'),
    ('Die Endprodukt-Zeile sagt wieder BAUEN',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            root_act = (_txt("BUILD \\u00b7 {n} run") if rr == 1\n                        else _txt("BUILD \\u00b7 {n} runs")).format(n=rr)',
     '            root_act = f"BAUEN \\u00b7 {rr} Run" + ("s" if rr != 1 else "")   # MUTATION',
     'b64 kein \'BAUEN\''),
    # --- b65: Item-Bilder ganz im Rahmen (Sitzung 17) ---
    ('Item-Bilder werden wieder unverkleinert beschnitten',
     'eve_trader/ui/mw_helpers.py',
     '        return pm.scaled(int(groesse), int(groesse), _Qt.KeepAspectRatio,\n                         _Qt.SmoothTransformation)',
     '        return pm   # MUTATION',
     'b65 das Bild wird auf die Rahmengroesse verkleinert'),
    # --- aa299/b66: Download-Fortschritt (Sitzung 17) ---
    ('Ohne Groessenangabe meldet der Download wieder nichts',
     'eve_trader/industry.py',
     '                            if progress:\n                                progress(done // (1 << 20), total // (1 << 20))',
     '                            if progress and total:\n                                progress(done // (1 << 20), total // (1 << 20))',
     'aa299 OHNE Groessenangabe'),
    ('Unbekannte Groesse steht wieder stumm auf 0 %',
     'eve_trader/ui/erst_einrichtung.py',
     '            self.balken.setRange(0, 0)                 # Groesse unbekannt',
     '            self.balken.setRange(0, 1)   # MUTATION',
     'b66 unbekannte Groesse'),
    # --- b67: Kaestchen in Baeumen gestaltet (Sitzung 17) ---
    ('Baum-Kaestchen fallen wieder aus der Gestaltung',
     'eve_trader/ui/theme.py',
     'QCheckBox::indicator, QTreeView::indicator, QTableView::indicator,\nQListView::indicator {{',
     'QCheckBox::indicator, QTableView::indicator,\nQListView::indicator {{',
     'b67 das Baum-Kaestchen'),
    # --- b68: Verlauf nach der Einrichtung (Sitzung 17) ---
    ('Nach der Einrichtung laedt der Verlauf wieder nicht',
     'eve_trader/ui/main_window.py',
     '            if _gesamt and _da < _gesamt * 0.25:\n                self.starte_verlauf_laden()',
     '            if _gesamt and _da < _gesamt * 0.25:\n                pass   # MUTATION',
     'b68 0 von 5731 mit Verlauf'),
    # --- b69: Verlaufsladen fortsetzen / stoppen mit Warnung (Sitzung 17) ---
    ('Ein offener Verlaufs-Lauf wird nicht mehr gemerkt',
     'eve_trader/ui/main_window.py',
     '        self._verlauf_merker(_region, offen=True)\n',
     '',
     'b69 ein gestarteter Lauf wird als OFFEN gemerkt'),
    ('Stopp bricht ohne Warnung ab',
     'eve_trader/ui/main_window.py',
     '        if not self._verlauf_abbruch_bestaetigen():\n            return\n',
     '',
     "b69 Stopp fragt ERST nach"),
    ('Gedrosselter Lauf vergisst seinen Merker',
     'eve_trader/ui/main_window.py',
     '            if not res.get("gedrosselt") and not self._verlauf_abbruch:',
     '            if not self._verlauf_abbruch:   # MUTATION',
     'b69 gedrosselt: der Merker bleibt'),
    # --- b70: Bau-Strukturen aus Funden (Sitzung 17) ---
    ('Gefundene Strukturen werden ohne Rueckfrage angelegt',
     'eve_trader/ui/main_window.py',
     '        if not self._bau_funde_frage(',
     '        if False and not self._bau_funde_frage(',
     "b70 'Only save as locations' legt nichts an"),
    ('Der Strukturtyp wird nicht mehr erkannt',
     'eve_trader/ui/main_window.py',
     '            typ = str(typnamen.get(f.get("type_id")) or "").strip().lower()',
     '            typ = str(typnamen.get(f.get("type_id")) or "").strip()   # MUTATION',
     'b70 Raitaru und Tatara werden angelegt'),
    ('Neue Eintraege verlieren die Verknuepfung',
     'eve_trader/ui/main_window.py',
     '                "link_structure_id": sid,\n',
     '                "link_structure_id": None,   # MUTATION\n',
     'b70 der Eintrag ist fertig bis auf die Rigs'),
    ('Schon gespeicherte Strukturen werden nie angeboten',
     'eve_trader/ui/main_window.py',
     '            for f in _gespeichert:\n',
     '            for f in []:   # MUTATION\n',
     'b70 die Suche bietet den neuen UND den schon gespeicherten Fund an'),
    # --- b71: Update-Meldung mit Knoepfen (Sitzung 17) ---
    ('Der Download-Knopf der Update-Meldung oeffnet nichts',
     'eve_trader/ui/main_window.py',
     '        if wahl == "download":\n            QDesktopServices.openUrl(QUrl(url))',
     '        if wahl == "download":\n            pass   # MUTATION',
     'b71 Download oeffnet die Release-Seite'),
    # --- aa300/b44: Spalte Gewinn je m3 (Sitzung 17) ---
    ('Gewinn/m3 teilt durch das Volumen der BLAUPAUSE statt des Produkts',
     'eve_trader/ui/main_window.py',
     '                _pids = {e.get("product_id") for e in profit_by_bp.values()',
     '                _pids = {e.get("bp_id") for e in profit_by_bp.values()',
     'aa300 das Volumen kommt aus item_volume_map'),
    ('Ohne Volumen wird Gewinn/m3 geraten',
     'eve_trader/ui/main_window.py',
     '                if econ and econ.get("profit") is not None and _vol:',
     '                if econ and econ.get("profit") is not None:\n                    _vol = _vol or 1.0',
     'aa300 ohne Volumen oder ohne Gewinn bleibt die Zelle leer'),
    ('Die Spalte Gewinn/m3 verschwindet wieder',
     'eve_trader/ui/main_window.py',
     '            (15, t("Profit/m\\u00b3"))]',
     '            ]',
     'b44 die neue Spalte Profit/m3 steht im Menue'),
    # --- aa301: alte Kaeufe nachholen (Sitzung 17, Nutzer-Meldung) ---
    ('Der Nachhol-Abruf bricht nach der ersten Seite ab',
     'eve_trader/esi.py',
     '        from_id = min(int(t.get("transaction_id") or 0) for t in rows)\n        if len(rows) < 2000:\n            fertig = True\n            break\n    return out, fertig',
     '        fertig = True\n        break\n    return out, fertig',
     'aa301 der Nachhol-Abruf blaettert weiter bis zum alten Kauf'),
    ('Das Nachholen wird nie angestossen',
     'eve_trader/ui/main_window.py',
     '                    self._tx_altes_nachholen(client_id, cid)\n                    # Gebuehren-Journal mitziehen',
     '                    # Gebuehren-Journal mitziehen',
     'aa301 und haengt an BEIDEN Abruf-Stellen'),
    ('Das Nachholen rutscht wieder hinter die Frische-Sperre',
     'eve_trader/ui/main_window.py',
     '                self._tx_altes_nachholen(client_id, cid)\n                if not store.tx_is_fresh(cid, max_min):',
     '                if not store.tx_is_fresh(cid, max_min):',
     'aa301 beim Start laeuft es auch bei frischen Transaktionen'),
    # --- b72: Order Update laedt beim Oeffnen (Sitzung 17) ---
    ('Der Order-Tab laedt beim Oeffnen nicht mehr von selbst',
     'eve_trader/ui/main_window.py',
     '                    self._load_order_mods()\n        # opening Transaktionen',
     '                    pass   # MUTATION\n        # opening Transaktionen',
     'b72 beim ersten Oeffnen wird geladen'),
    ('Der Order-Tab laedt bei JEDEM Wechsel neu (ESI-Sturm)',
     'eve_trader/ui/main_window.py',
     '                if (not _alt or _hub_jetzt != getattr(self, "_ord_geladen_hub", None)\n                        or (_t_ord.time() - _alt) > 300):',
     '                if True:   # MUTATION',
     'b72 gleich danach NICHT nochmal'),
    ('Ein Fehler laesst die Order-Laufsperre stehen',
     'eve_trader/ui/main_window.py',
     '        self._run(Worker(job), done, fail_cb=_ord_fehler)',
     '        self._run(Worker(job), done)',
     'b72 ein Fehler gibt die Sperre wieder frei'),
    # --- b73: Hinweis auf Orders an anderen Orten (Sitzung 17) ---
    ('Fremde Orders werden wieder still weggeworfen',
     'eve_trader/ui/main_window.py',
     '                            if _lid:\n                                _woanders[_lid] = _woanders.get(_lid, 0) + 1\n',
     '',
     'b73 der Hinweis ist sichtbar'),
    ('Der Hinweis nennt die Orte nicht mehr beim Namen',
     'eve_trader/ui/main_window.py',
     '                    _andere.append((_n or str(_lid), _anz))',
     '                    _andere.append((str(_lid), _anz))   # MUTATION',
     'b73 er nennt den Keepstar MIT Anzahl'),
    ('Der Hinweis bleibt stehen, obwohl alles am Hub liegt',
     'eve_trader/ui/main_window.py',
     '            else:\n                self.ord_andere.setVisible(False)\n            self._orders_inner.setTabText(0,',
     '            self._orders_inner.setTabText(0,',
     'b73 ohne fremde Orders verschwindet der Hinweis wieder'),
    ('Die Fehlermeldung zeigt den Link wieder nur als Text',
     'eve_trader/ui/main_window.py',
     '        _auf = _box.addButton(t("Open releases page"), QMessageBox.AcceptRole)',
     '        _auf = _box.addButton(t("Close"), QMessageBox.AcceptRole)   # MUTATION',
     'b20 der Fehlerfall bietet die Releases-Seite als KNOPF an'),
    ('Der Knopf der Fehlermeldung oeffnet nichts',
     'eve_trader/ui/main_window.py',
     '        if self._releases_wahl(text):\n            QDesktopServices.openUrl(QUrl(url))',
     '        self._releases_wahl(text)',
     'b71 die Fehlermeldung oeffnet die Releases-Seite nur auf Klick'),
    ('Unbekannter Kaufpreis wird wieder still uebersprungen',
     'eve_trader/ui/main_window.py',
     '                    t("\\u26a0 Purchase price unknown \\u2013 no loss check. "\n                      "Check the price yourself."))',
     '                    "")',
     'aa199 unbekannter Kaufpreis wird benannt'),
    # --- b74: Personalisierung (Sitzung 17) ---
    ('Spaltenbreiten werden beim Schliessen nicht mehr gemerkt',
     'eve_trader/ui/main_window.py',
     '                _alle[_n] = bytes(_hv.saveState().toBase64()).decode()',
     '                pass   # MUTATION',
     'b74 die Breiten landen in den Einstellungen'),
    ('Gemerkte Spaltenbreiten werden beim Start ignoriert',
     'eve_trader/ui/main_window.py',
     '                _hv.restoreState(QByteArray.fromBase64(_s.encode()))\n                self._sized.add(_n)',
     '                pass   # MUTATION',
     'b74 nach dem Neustart steht die Spalte wieder'),
    ('Die Charakter-Auswahl faellt beim Neuaufbau zurueck',
     'eve_trader/ui/main_window.py',
     '            if _vorher is not None:\n                _i = combo.findData(_vorher)\n                if _i >= 0:\n                    combo.setCurrentIndex(_i)',
     '            pass   # MUTATION',
     'b74 nach dem Neuaufbau steht derselbe Charakter da'),
    ('Der Hub wird nicht mehr gemerkt',
     'eve_trader/ui/main_window.py',
     '            self.settings["ui_hub"] = _d',
     '            pass   # MUTATION',
     'b74 der Hub wird gemerkt'),
    # --- aa302: Erfindungsmaterial in der Einkaufsliste (Sitzung 17) ---
    ('Datacores/Decryptoren fallen wieder aus der Einkaufsliste',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                if _t in _inv_tids:\n                    return int(r.get("missing", 0) or 0)\n',
     '',
     'aa302 fuer diese Zeilen zaehlt die EIGENE Fehlmenge'),
    ('Erfindungsmaterial wird nicht mehr erkannt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                             (set(_p_inv.get("inv_buy") or {})\n                              | set(_p_inv.get("inv_stock_used") or {}))}',
     '                             set()}   # MUTATION',
     'aa302 Erfindungsmaterial wird als solches erkannt'),
    # --- aa303/aa304: eigene Reservierung schuetzt, Vollmenge ohne Eigenbau ---
    ('Die eigene Reservierung schuetzt den Bestand nicht mehr',
     'eve_trader/ui/mw_helpers.py',
     '            _schutz = min(int((eigen or {}).get(int(_t), 0) or 0), _have)',
     '            _schutz = 0   # MUTATION',
     'aa303 Mangelfall: der eigene Anteil bleibt stehen'),
    ('Der eigene Plan wird beim Schutz nicht mehr gefunden',
     'eve_trader/ui/mw_helpers.py',
     '            if p.get("id") != plan_id or not p.get("reserve"):',
     '            if True:   # MUTATION',
     'aa303 die eigene Reservierung wird gefunden'),
    ('Die Vollmenge kauft wieder die selbst gebauten Stufen mit',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                return max(0, int(r.get("total", 0) or 0)\n                           - int(r.get("built", 0) or 0))',
     '                return int(r.get("total", 0) or 0)   # MUTATION',
     'aa304 die Vollmenge zieht die Eigenproduktion ab'),
    # --- aa49: gedeckte Fehlmengen sind gruen (Sitzung 17) ---
    ('Gedeckte Mengen werden wieder amber angezeigt',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            elif _gedeckt:\n                miss_col = theme.GREEN\n',
     '',
     'aa49 offene Menge wird amber hervorgehoben, gedeckte gruen'),
    ('Eigenbau zaehlt nicht mehr als gedeckt',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            _gedeckt = status_col in (theme.GREEN, theme.GREEN_BRIGHT, theme.BLUE)',
     '            _gedeckt = False   # MUTATION',
     'aa49 offene Menge wird amber hervorgehoben, gedeckte gruen'),
    # --- aa305: drei Bedienelemente sichtbar (Sitzung 17) ---
    ('Die ESI-Bestandszeile wird wieder grau',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            f"color:{theme.TEXT}; font-size:13px; padding:1px 0;")',
     '            f"color:{theme.MUTED}; font-size:11px;")',
     'aa305 die ESI-Bestandszeile ist nicht mehr grau'),
    ('Der Bestandsbereich verliert seinen Rahmen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        stock_scope_cb.setCursor(Qt.PointingHandCursor)\n',
     '',
     'aa305 der Bestandsbereich sieht nach Bedienelement aus'),
    # --- aa306: Zwischenablage-Bestand, Namen mit Ziffern (Sitzung 17) ---
    ('Der Rueckfall auf die ganze Zeile faellt weg',
     'eve_trader/ui/main_window.py',
     '            if tid is None and name_map.get(line.lower()) is not None:\n                tid, qty = name_map[line.lower()], 1\n',
     '',
     'aa306 der Rueckfall steht im Code'),
    # --- aa307/aa308: T1-Basis + Sperre bei eingefrorenem Plan (Sitzung 17) ---
    ('Drohnen und Fighter fallen wieder in den Sammeltopf',
     'eve_trader/ui/main_window.py',
     '        if category_id in (6, 18, 87) and (meta in (0, 1, None)):',
     '        if category_id == 6 and (meta in (0, 1, None)):',
     'aa307 Einherji I (Fighter) -> t1_hulls'),
    ('Der eingefrorene Plan laesst sich wieder heimlich verstellen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    _w.setEnabled(not _snap_on)',
     '                    _w.setEnabled(True)   # MUTATION',
     'aa308 Kategorie-Haken und Fertigungstiefe werden gesperrt'),
    ('Auftauen passiert wieder ohne Rueckfrage',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                if not self._auftauen_bestaetigen():\n',
     '                if False:\n',
     'aa308 Auftauen fragt vorher nach'),
    # --- aa309: gleiche Blaupausen in einer Zeile (Sitzung 17) ---
    ('Blaupausen werden wieder einzeln aufgelistet',
     'eve_trader/ui/main_window.py',
     '            rows = self._bp_zeilen_gruppieren(rows)\n',
     '',
     'aa309 die Tabelle benutzt die Gruppierung'),
    ('Die Gruppe nimmt die BESTE ME/TE statt der schlechtesten',
     'eve_trader/ui/main_window.py',
     '                g[_f] = min(int(g.get(_f, 0) or 0), int(b.get(_f, 0) or 0))',
     '                g[_f] = max(int(g.get(_f, 0) or 0), int(b.get(_f, 0) or 0))',
     'aa309 die BPCs eines Charakters: Anzahl 2, ME/TE die SCHLECHTESTEN'),
    ('BPO und BPC landen wieder in einer Zeile',
     'eve_trader/ui/main_window.py',
     '            key = (b.get("type_id"), bool(b.get("is_bpo")), b.get("_cid"),',
     '            key = (b.get("type_id"), False, b.get("_cid"),',
     'aa309 aus vier Zeilen werden drei'),
    # --- b75: stille Update-Pruefung beim Start (Sitzung 17) ---
    ('Beim Start wird nicht mehr nach Updates gesucht',
     'eve_trader/ui/main_window.py',
     '        QTimer.singleShot(12000, lambda: self.check_programm_update(still=True))\n',
     '',
     'b75 der Start stoesst die stille Pruefung an'),
    ('Der Start-Abruf meldet auch "alles aktuell"',
     'eve_trader/ui/main_window.py',
     '            if still:\n                return          # kein Fenster beim automatischen Start-Abruf',
     '            if False:\n                return',
     'b75 aktuell: beim Start kein Fenster'),
    # --- b76: Sortierung und Filter merken (Sitzung 17) ---
    ('Die Sortierung wird beim Schliessen vergessen',
     'eve_trader/ui/main_window.py',
     '                    _alle[_n] = [int(_sp), int(_hv.sortIndicatorOrder().value)]',
     '                    pass   # MUTATION',
     'b76 die Sortierung wird gemerkt'),
    ('Gemerkte Filter werden beim Start ignoriert',
     'eve_trader/ui/main_window.py',
     '                    _i = _w.findData(_v)\n',
     '                    continue\n',
     'b76 und nach dem Neustart wieder gesetzt'),
    ('Beim Wiederherstellen der Filter laufen die Signale mit',
     'eve_trader/ui/main_window.py',
     '                _w.blockSignals(True)\n                if isinstance(_w, _QCB):\n                    _w.setChecked(bool(_v))',
     '                if isinstance(_w, _QCB):\n                    _w.setChecked(bool(_v))',
     'b76 beim Wiederherstellen laufen keine Signale los'),
    # --- b77/aa310: Hinweise in leeren Listen (Sitzung 17) ---
    ('Leere Listen schweigen wieder',
     'eve_trader/ui/main_window.py',
     '        _GeomTimer.singleShot(0, self._leerhinweise_anlegen)\n',
     '',
     'b77 jede der sieben Listen hat einen Hinweis'),
    ('Der Hinweis bleibt stehen, obwohl Daten da sind',
     'eve_trader/ui/main_window.py',
     '                box.setVisible(_leer)',
     '                box.setVisible(True)   # MUTATION',
     'b77 sobald Daten da sind, verschwindet er'),
    ('Der Hinweis-Knopf tut nichts mehr',
     'eve_trader/ui/main_window.py',
     '                    (lambda _b=_btn: _b.click()) if _btn is not None else None,',
     '                    None,',
     'b77 ein Klick loest denselben Vorgang aus'),
    # --- b78: gefuehrte Tour (Sitzung 17) ---
    ('Die Tour bleibt beim ersten Schritt stehen',
     'eve_trader/ui/tutorial.py',
     '        self.i += 1\n        self.zeigen()',
     '        self.zeigen()',
     'b78 der Zaehler zeigt, wie oft man noch klicken muss'),
    ('Der Rahmen bleibt nach der Tour stehen',
     'eve_trader/ui/tutorial.py',
     '                _r.hide()\n                _r.setParent(None)\n                _r.deleteLater()',
     '                pass   # MUTATION',
     'b78 nach dem Abbrechen ist der Rahmen wieder weg'),
    ('Die Tour wird beim ersten Start nicht mehr angeboten',
     'eve_trader/ui/main_window.py',
     '        QTimer.singleShot(1500, self._tutorial_erstfrage)\n',
     '',
     'b78 beim ersten Start wird EINMAL gefragt'),
    ('Die hervorgehobenen Knoepfe blinken nicht mehr',
     'eve_trader/ui/tutorial.py',
     '            self._blink.start()\n',
     '',
     'b78 der hervorgehobene Knopf blinkt'),
    ('Der Bauplan-Schritt wartet nicht mehr auf den Nutzer',
     'eve_trader/ui/tutorial.py',
     '        if warten and not self._bedingung_erfuellt(warten):',
     '        if False:',
     'b78 ohne offenen Bauplan bleibt'),
    ('Der Kursverlauf im Tutorial wird nicht gezeichnet',
     'eve_trader/ui/main_window.py',
     '            QTimer.singleShot(0, self._plot_history)',
     '            pass   # MUTATION',
     'b78 der Kursverlauf wird auch bei schon gewaehltem Item gezeichnet'),
    ('Die Handels-Reiter heben wieder die ganze Leiste hervor',
     'eve_trader/ui/tutorial.py',
     '            ("nav:deals", t("Daytrade"),',
     '            ("tabs", t("Daytrade"),',
     'b78 hervorgehoben wird der einzelne Reiter'),
    ('Der Strategie-Schritt im Daytrade faellt weg',
     'eve_trader/ui/tutorial.py',
     '            (("d_mode", "d_preset"), t("Strategy and presets"),\n',
     '            ("g_hub", t("Strategy and presets"),\n',
     'b78 der Schritt zu d_preset ist da'),
    ('"Deals laden" wird im Regional nicht mehr erklaert',
     'eve_trader/ui/tutorial.py',
     '            (("rg_go", "rg_src", "rg_tgt", "rg_buyer", "rg_seller"),\n',
     '            (("g_hub",),\n',
     'b78 der Schritt zu rg_go ist da'),
    ('Ein Tutorial-Schritt zeigt wieder ins Leere',
     'eve_trader/ui/tutorial.py',
     '        (("bau:3", "_struct_add_btn", "_struct_link_btn"),',
     '        (("b_gibtsnicht", "_struct_add_btn", "_struct_link_btn"),',
     'b78 industry: jeder Schritt findet sein Element'),
    ('Die Bauplan-Schritte haengen wieder in der Luft',
     'eve_trader/ui/tutorial.py',
     '        ("bd:tab:" + t("Recipe structure"), t("Recipe structure"),',
     '        (None, t("Recipe structure"),',
     'b78 die Bauplan-Schritte haengen ALLE am Bauplan-Fenster'),
    ('Nur noch EIN Dropdown blinkt im Daytrade',
     'eve_trader/ui/tutorial.py',
     '            (("d_mode", "d_preset"), t("Strategy and presets"),',
     '            ("d_preset", t("Strategy and presets"),',
     'b78 Daytrade: Mode UND Preset blinken'),
    ('Der Hub blinkt bei "Deals laden" nicht mehr mit',
     'eve_trader/ui/tutorial.py',
     '            (("deals_btn", "g_hub"), t("Load deals"),',
     '            ("deals_btn", t("Load deals"),',
     'b78 Daytrade: bei \'Deals laden\' blinkt der Hub mit'),
    ('Der Schritt zu Kaeufer und Verkaeufer faellt weg',
     'eve_trader/ui/tutorial.py',
     '            (("rg_buyer", "rg_seller"), t("Who buys, who sells"),',
     '            (("rg_src", "rg_tgt"), t("Who buys, who sells"),',
     'b78 Regional: es gibt einen Schritt zu Kaeufer und Verkaeufer'),
    ('Im Regional blinkt faelschlich der obere Hub mit',
     'eve_trader/ui/tutorial.py',
     '            (("rg_go", "rg_src", "rg_tgt", "rg_buyer", "rg_seller"),',
     '            (("rg_go", "g_hub", "rg_tgt", "rg_buyer", "rg_seller"),',
     'b78 Regional: bei \'Deals laden\' blinkt der obere Hub NICHT mit'),
    ('Nur der erste Rahmen blinkt, die anderen bleiben stumm',
     'eve_trader/ui/tutorial.py',
     '        for _r in list(self._rahmen):',
     '        for _r in list(self._rahmen)[:1]:',
     'b78 und ALLE davon blinken mit'),
    ('Die Tour schaltet im Bauplan nicht mehr zum Reiter',
     'eve_trader/ui/tutorial.py',
     '                            _tw.setCurrentIndex(_i)   # hinschalten',
     '                            pass   # MUTATION',
     "b78 der Schritt zu"),
    ('Der Reiter wird wieder ueber eine Nummer gesucht',
     'eve_trader/ui/tutorial.py',
     '                        if _tw.tabText(_i).strip() == _ziel.strip():',
     '                        if _i == 1:   # MUTATION',
     "b78 der Schritt zu"),
    ('Die Industrie-Tour blinkt, fuehrt aber nicht hin',
     'eve_trader/ui/tutorial.py',
     '           "your starting point."), "build", None),',
     '           "your starting point."), None, None),',
     'b78 industry Schritt 2 schaltet in den Bauen-Tab'),
    ('Die Tour oeffnet die Unterseite des Bauen-Tabs nicht',
     'eve_trader/ui/tutorial.py',
     '                self.mw._bau_nav(_i)\n',
     '',
     "b78 der Schritt 'Structures first' oeffnet Seite 3"),
    ('Die Tour haengt wieder starr im Hauptfenster',
     'eve_trader/ui/tutorial.py',
     '        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)\n',
     '',
     'b78 die Tour ist ein eigenes Werkzeugfenster'),
    ('Die Tour fuehrt sich nicht mehr nach',
     'eve_trader/ui/tutorial.py',
     '        self._folgen.start()\n',
     '',
     'b78 sie fuehrt sich selbst nach'),
    ('Der Rahmen haengt wieder immer am Hauptfenster',
     'eve_trader/ui/tutorial.py',
     '                _r = QWidget(_w.window())',
     '                _r = QWidget(self.mw)',
     'b78 im Bauplan haengt der Rahmen am BAUPLAN-Fenster'),
    ('Nur der SDE-Knopf blinkt, nicht der eigene Blaupausen-Knopf',
     'eve_trader/ui/tutorial.py',
     '        (("bau:1", "bp_refresh_btn", "g_sde_btn"), t("My blueprints"),',
     '        (("bau:1", "g_sde_btn"), t("My blueprints"),',
     'b78 der Blaupausen-Schritt laesst BEIDE Knoepfe blinken'),
    ('Die Tour draengt sich bei jedem Takt nach vorn',
     'eve_trader/ui/tutorial.py',
     '            if vor:\n                # Erst das Fenster des Ankers, dann die Tour darueber.',
     '            if True:\n                # MUTATION',
     'b78 nach vorn geholt wird nur beim Schrittwechsel'),
    ('Der Bauplan wird beim Schrittwechsel nicht nach vorn geholt',
     'eve_trader/ui/tutorial.py',
     '                _ziel.raise_()\n                _ziel.activateWindow()',
     '                pass   # MUTATION',
     'b78 und der Bauplan wird dabei selbst nach vorn geholt'),
    ('Spaeter auftauchende Knoepfe blinken nicht nach',
     'eve_trader/ui/tutorial.py',
     '                self._hervorheben(_soll)\n',
     '',
     'b78 spaeter auftauchende Elemente blinken nach'),
    ('Die Tour haengt weiter am Haupttool statt am Bauplan',
     'eve_trader/ui/tutorial.py',
     '                self.setParent(_ziel, _flags)   # nimmt das Fenster mit\n                self.show()',
     '                pass   # MUTATION',
     'b78 die Tour haengt sich an das Fenster des Schritts'),
    ('"Build or buy" haengt wieder nur am Fenster',
     'eve_trader/ui/tutorial.py',
     '        (("bd:tab:" + t("Recipe structure"), "_bd_karte_bauenkaufen"),\n'
     '         t("Build or buy?"),',
     '        ("bd:dialog",\n'
     '         t("Build or buy?"),',
     "b78 'Build or buy' zeigt auf seine Karte"),
    ('Der Einfrier-Schritt zeigt nicht mehr auf die Knoepfe',
     'eve_trader/ui/tutorial.py',
     '        (("_bd_save_btn", "_bd_frozen_btn"), t("Save and freeze"),',
     '        ("bd:dialog", t("Save and freeze"),',
     "b78 'Speichern und einfrieren' zeigt auf BEIDE Knoepfe"),
    ('Der Bauplan bleibt am Ende der Tour offen',
     'eve_trader/ui/tutorial.py',
     '                    _d.close()',
     '                    pass   # MUTATION',
     'b78 der letzte Schritt macht den Bauplan zu'),
    ('"Neuer Bauplan" blinkt weiter, obwohl der Plan offen ist',
     'eve_trader/ui/tutorial.py',
     '                self._fertig_kein_blinken = True\n                self._hervorheben(None)',
     '                pass   # MUTATION',
     "b78 danach blinkt 'Neuer Bauplan' nicht mehr"),
    ('Das Nachfuehren holt das Blinken wieder zurueck',
     'eve_trader/ui/tutorial.py',
     '            if getattr(self, "_fertig_kein_blinken", False):\n                return          # Schritt erledigt - nichts mehr hervorheben\n',
     '',
     'b78 und das Nachfuehren bringt es nicht zurueck'),
    ('Das Zielfenster wird wieder nur am Namen erraten',
     'eve_trader/ui/tutorial.py',
     '        for _w in (self._hervor or []):\n            try:\n                if _w is not None and _w.isVisible():\n                    return _w.window()\n            except RuntimeError:\n                continue\n',
     '',
     'b78 das Zielfenster kommt vom Element, nicht vom Namen'),
    ('Der Einkaufslisten-Knopf blinkt nicht mehr mit',
     'eve_trader/ui/tutorial.py',
     '        (("bd:tab:" + t("Materials"), "_bd_mat_copy_btn"), t("Materials"),',
     '        ("bd:tab:" + t("Materials"), t("Materials"),',
     "b78 der Materialien-Schritt laesst 'Einkaufsliste' mitblinken"),
    ('Die Tour stellt sich wieder unter das ERSTE Element',
     'eve_trader/ui/tutorial.py',
     '            _anker = (max(_sicht, key=lambda w: w.mapToGlobal(\n                QPoint(0, w.height())).y()) if _sicht else None)',
     '            _anker = _sicht[0] if _sicht else None',
     'b78 platziert wird unter dem UNTERSTEN Element'),
    ('Nach dem Oeffnen zaehlt der Bauplan nicht mehr als Zielfenster',
     'eve_trader/ui/tutorial.py',
     '        if _nach_oeffnen or self._schritt_im_bauplan():',
     '        if self._schritt_im_bauplan():',
     'b78 nach dem Oeffnen gilt der Bauplan als Zielfenster'),
    ('Das Fenster des Ankers wird nicht nach vorn geholt',
     'eve_trader/ui/tutorial.py',
     '                        _anker.window().raise_()',
     '                        pass   # MUTATION',
     'b78 beim Schrittwechsel kommt auch das Anker-Fenster nach vorn'),
    ('Am Schluss blinkt der Portfolio-Knopf wieder',
     'eve_trader/ui/tutorial.py',
     '            (None, t("That is the trading side"),',
     '            ("nav:portfolio", t("That is the trading side"),',
     'b78 trading: der Schlussschritt hebt nichts mehr hervor'),
    ('Die Tour wird mit dem Bauplan zusammen abgeraeumt',
     'eve_trader/ui/tutorial.py',
     '                    if self.parent() is _d:\n                        self.setParent(self.mw, self.windowFlags())\n                        self.show()\n',
     '',
     'b78 vor dem Schliessen wird die Tour ans Haupttool umgehaengt'),
    ('Das Nachfolge-Fenster oeffnet wieder aus dem Klick heraus',
     'eve_trader/ui/tutorial.py',
     '            QTimer.singleShot(0, lambda: _mw._tutorial_anderer_zweig(_zweig))',
     '            _mw._tutorial_anderer_zweig(_zweig)',
     'b78 das Nachfolge-Fenster kommt NICHT aus dem Klick heraus'),
    ('Die Tour liegt wieder ueber ALLEN Programmen',
     'eve_trader/ui/tutorial.py',
     '        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint)',
     '        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint\n                            | Qt.WindowStaysOnTopHint)',
     'b78 aber NICHT ueber fremden Programmen'),
    ('Das Tutorial-Fenster hebt sich nicht mehr ab',
     'eve_trader/ui/tutorial.py',
     '            f"#TutorFrame{{background:#03060B; "\n            f"border:2px solid {theme.AMBER}; border-radius:8px;}}")',
     '            f"#TutorFrame{{background:{theme.PANEL}; "\n            f"border:2px solid {theme.CYAN}; border-radius:8px;}}")',
     'b78 das Fenster ist dunkler als das Werkzeug'),
    ('Die Tutorial-Schrift wird wieder klein',
     'eve_trader/ui/tutorial.py',
     '            f"color:{theme.GOLD_HELL}; font-size:19px; font-weight:700; "',
     '            f"color:{theme.GOLD_HELL}; font-size:13px; font-weight:700; "',
     'b78 die Schrift ist gross genug zum Lesen'),
    ('Der Sprachschalter faellt wieder aus der Reihe',
     'eve_trader/ui/main_window.py',
     '            f"padding:5px 12px; color:{theme.TEXT};}}"',
     '            f"padding:3px 6px; color:{theme.TEXT};}}"',
     'aa311 der Sprachschalter uebernimmt das Polster der Knoepfe'),
    # KEINE MUTATION FUER DIE WARTESCHLEIFE IN b26 (Sitzung 17): ob der
    # ESI-Abruf nach dem Zurueckstellen noch den echten Kern trifft, haengt
    # am Takt des Rechners. Im Container wurde b59 ohne sie dreimal rot -
    # beim Nutzer hing die Suite aber nie. Eine Mutation, die je nach
    # Rechner rot oder blind ist, prueft nichts. Die Zusage "die Suite haengt
    # nicht" haelt das Netz selbst (b59), unabhaengig davon.
    # --- Sitzung 20: der Rezept-Baum wird in rebuild() mitgerechnet ---
    ('Der Rezept-Baum friert beim Oeffnen wieder ein',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                        _neu_tree = industry.build_tree(\n'
     '                            type_id, _pfn, self._bd_recipes, self._bd_opts)',
     '                        _neu_tree = None   # MUTATION',
     'aa323 rebuild() rechnet den Baum selbst'),
    ('Der eingefrorene Plan bekommt doch einen frischen Baum',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            if _frozen_plan is None:\n'
     '                _tc = getattr(self, "_bd_tree_cache", None)',
     '            if True:\n'
     '                _tc = getattr(self, "_bd_tree_cache", None)',
     'aa323 eingefrorener Plan bekommt KEINEN frischen Baum'),
    ('Ein echter Zukauf verschwindet hinter "aus Bestand gedeckt"',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                if (aq > 0 and _cid_b in _su_b and _by_b is not None\n'
     '                        and _cid_b not in _by_b):',
     '                if aq > 0 and _cid_b in _su_b:',
     'aa324 aber nur, wenn der Plan das Item wirklich nicht kauft'),
    ('Die gedeckte Zeile sagt wieder "kaufen"',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    act = _txt("covered from stock")\n                elif (aq > 0',
     '                    act = _txt("buy")\n                elif (aq > 0',
     "b63 sie sagt 'aus Bestand gedeckt'"),
    ('Der teils gedeckte Fall faellt wieder auf "kaufen" zurueck',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    act = _txt("buy \\u00b7 partly from stock")',
     '                    act = _txt("buy")   # MUTATION',
     'aa324 teils gedeckt bekommt ein eigenes Wort'),
    # --- Sitzung 20: Rollen-Netz beim Oeffnen ---
    ('Der Bauplan startet wieder ohne Rollen-Netz',
     'eve_trader/ui/main_window.py',
     '            self._bau_rollen_netz()',
     '            pass   # MUTATION',
     'aa327 jeder Bauplan-Start laeuft durch das Netz'),
    ('Das Netz ueberschreibt eine bewusste Abwahl',
     'eve_trader/ui/main_window.py',
     '        if any(self.settings.get(k) for k in keys):\n            return False',
     '        if False:\n            return False',
     'aa327 es greift NUR im vollstaendig leeren Zustand'),
    ('Charaktere ohne Rolle bleiben wieder unbenannt',
     'eve_trader/ui/main_window.py',
     '            info.setVisible(True)',
     '            info.setVisible(False)   # MUTATION',
     'aa327 der Hinweis erscheint nur dann'),
    ('Das Fehlerprotokoll verschweigt wieder, woher die ID kam',
     'eve_trader/esi.py',
     '                     + "  (aufgerufen aus " + _woher + ")\\n")',
     '                     + "\\n")',
     'aa328 und jetzt auch der Aufrufer'),
    ('Die Herkunft zeigt auf den Melder statt auf den Verursacher',
     'eve_trader/esi.py',
     '            if _os.path.basename(_f.filename) != _hier:',
     '            if True:',
     'aa328 nicht auf esi.py selbst'),
    ('Blaupausen anderswo werden wieder verschwiegen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    if _loc is not None and _loc in _bekannt and _loc not in _bau_orte:',
     '                    if False:',
     'aa329 gezaehlt wird gegen die Bau-Orte des Plans'),
    ('Ein Container gilt wieder als "woanders"',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    if _loc is not None and _loc in _bekannt and _loc not in _bau_orte:',
     '                    if _loc is not None and _loc not in _bau_orte:',
     'aa329 nur bekannte eigene Orte zaehlen als'),
    ('Ohne Bau-Ort wird "anderswo" trotzdem behauptet',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                if _bau_orte:\n                    _loc = b.get("location_id")',
     '                if True:\n                    _loc = b.get("location_id")',
     'aa329 ohne Bau-Ort wird nichts behauptet'),
    ('Der geliehene Index nimmt wieder den erstbesten statt den hoechsten',
     'eve_trader/ui/main_window.py',
     '            _v, _sysname = max(_kand)',
     '            _v, _sysname = _kand[0]',
     'aa330 geliehen wird der hoechste Index, nicht der erste'),
    ('Die Warnzeile verschweigt wieder, dass der Index geliehen ist',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            if _gl:',
     '            if False:',
     'aa330 die Warnzeile liest ihn'),
    ('Rigs mit "Blueprint" im Namen fliegen wieder aus dem Import',
     'eve_trader/industry.py',
     '        if name.strip().lower().endswith(" blueprint"):',
     '        if "blueprint" in name.lower():',
     'aa331 der Import prueft auf das Wortende'),
    ('Die Menge im Bauplan endet wieder bei sechs Stellen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        qty_spin = QSpinBox(); qty_spin.setRange(1, 100000000)',
     '        qty_spin = QSpinBox(); qty_spin.setRange(1, 1000000)',
     'aa332 die Obergrenze liegt bei 100 Mio'),
    ('Die grosse Menge wird im Feld abgeschnitten',
     'eve_trader/ui/mw_bauplan_fenster.py',
     'qty_spin.setMaximumWidth(140)',
     'qty_spin.setMaximumWidth(90)',
     'aa332 und ist breit genug fuer neun Stellen'),
    ('Das Endprodukt rechnet wieder mit ME/TE 0 statt der eigenen Blaupause',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        if _me_te_in_header and not getattr(self, "_bd_me_manuell", False):',
     '        if False:',
     'aa333 das Endprodukt wird aus der eigenen Blaupause vorbelegt'),
    ('Die Vorbelegung ueberschreibt die eigene Eingabe',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            self._bd_me_manuell = True\n            self._bd_me = me_spin.value()\n            self._bd_te = te_spin.value()\n            _rig = self._bau_rig_me()',
     '            self._bd_me = me_spin.value()\n            self._bd_te = te_spin.value()\n            _rig = self._bau_rig_me()',
     'aa333 eine eigene Eingabe wird nicht ueberschrieben'),
    ('Das Equipment-Rig wirkt wieder auf Fighter',
     'eve_trader/industry.py',
     '    if category_id == 87:',
     '    if category_id == 87 and False:',
     'aa334 Fighter (Kategorie 87) sind nur'),
    ('Drohnen bekommen den Equipment-Rig zurueck',
     'eve_trader/industry.py',
     '    if category_id == 18:\n        return {"drone"}',
     '    if category_id == 18:\n        return {"drone", "equipment"}',
     'aa334 Drohnen (Kategorie 18) ebenso'),
    ('Meine Bauplaene werden nicht mehr nach Fortschritt sortiert',
     'eve_trader/ui/main_window.py',
     '            self._sortiere_plan_karten(res)',
     '            pass   # MUTATION',
     'aa335 sie wird gerufen, wenn der Fortschritt da ist'),
    ('Fertige Bauplaene bleiben wieder oben stehen',
     'eve_trader/ui/main_window.py',
     '            return (1 if fertig else 0, -float(_pc))',
     '            return (0, -float(_pc))',
     'aa335 fertige bekommen den unteren Rang'),
    ('Die Gruppen-Blacklist wird nicht mehr gelesen',
     'eve_trader/ui/main_window.py',
     '        bl_gruppen = set(self.settings.get("bau_blacklist_gruppen", []) or [])',
     '        bl_gruppen = set()   # MUTATION',
     'aa336 die Gruppen-Blacklist wird gelesen'),
    ('Das Gruppen-Haekchen wirkt erst nach Neuoeffnen',
     'eve_trader/ui/main_window.py',
     '        self._bau_refresh_exclusions_and_rebuild()\n\n    def _push_blacklist_to_ui(self):',
     '        pass   # MUTATION\n\n    def _push_blacklist_to_ui(self):',
     'aa336 ein Haekchen wirkt sofort'),
    ('Die Gruppen-Blacklist erfindet eine zweite Einteilung',
     'eve_trader/ui/main_window.py',
     '                    _g = self._bd_material_gruppe(',
     '                    _g = None or self._bd_rohstoff_gruppe(',
     'aa336 sie benutzt DIESELBE Einteilung wie der Materialien-Reiter'),
    ('Die Menge rechnet wieder bei jedem Tastendruck',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        qty_spin.valueChanged.connect(lambda _=0: _qty_timer.start())',
     '        qty_spin.valueChanged.connect(lambda _=0: _qty_uebernehmen())',
     'aa338 jeder Tastendruck startet ihn nur neu'),
    ('Enter wartet wieder auf den Timer',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        qty_spin.editingFinished.connect(_qty_uebernehmen)',
     '        pass   # MUTATION',
     'aa338 Enter und Klick woanders rechnen sofort'),
    ('ME/TE rechnen wieder beim blossen Verlassen des Feldes',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            if (me_spin.value() == int(getattr(self, "_bd_me", 0) or 0)\n                    and te_spin.value() == int(getattr(self, "_bd_te", 0) or 0)):\n                return',
     '            if False:\n                return',
     'aa338 ME/TE rechnen nur bei echter Aenderung'),
    ('Die offene Kauforder steht wieder nur in der Farbe',
     'eve_trader/ui/main_window.py',
     '                nm_it.setText(nm_it.text() + " " + t("(order running)"))',
     '                pass   # MUTATION',
     'aa339 und traegt den Hinweis im Namen'),
    ('Die Bauplan-Karten bekommen wieder eine feste Breite',
     'eve_trader/ui/main_window.py',
     '            card.setMaximumWidth(MAXW)\n            card.setMinimumWidth(MINW)',
     '            card.setFixedWidth(MAXW)\n            card.setMinimumWidth(MINW)',
     'aa340 die Karten haben keine feste Breite mehr'),
    ('Die Gewinn-Uebersicht bleibt wieder starr',
     'eve_trader/ui/main_window.py',
     '        panel.setMaximumWidth(breite)',
     '        panel.setFixedWidth(breite)',
     'aa340 auch ihr Rahmen ist nicht mehr fest'),
    ('Die breite Blueprints-Seite zwingt allen ihre Breite auf',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        self.b_stack.addWidget(_bp_scroll)      # 1 \u2013 Meine Blueprints',
     '        self.b_stack.addWidget(bp_page)      # MUTATION',
     'b66 keine Seite verlangt mehr als 900 px'),
    ('Der Mengen-Vorschlag kennt wieder nur Daytrade',
     'eve_trader/ui/main_window.py',
     '                _dv = (stats.get(r["type_id"]) or {}).get("daily_vol", 0) or 0',
     '                _dv = 0   # MUTATION',
     'aa342 sonst zaehlt das Tagesvolumen der Einkaufsliste'),
    ('Der Anteilsregler wird beim Massen-Vorschlag ignoriert',
     'eve_trader/ui/main_window.py',
     '        share = (share.value() / 100.0) if share is not None else 0.25',
     '        share = 0.25   # MUTATION',
     'aa342 mit DEMSELBEN Anteilsregler wie der Einzel-Vorschlag'),
    ('Der Dialog bietet wieder an, Gebautes zu kaufen',
     'eve_trader/ui/main_window.py',
     '                _pre = (show_all and not _wird_gebaut',
     '                _pre = (show_all or _wird_gebaut',
     'aa343 gebaute Posten werden nicht vorangekreuzt'),
    ('Der Kopf zaehlt Gebautes wieder als fehlend',
     'eve_trader/ui/main_window.py',
     '                          if int(_r["tid"]) not in _baut_kopf',
     '                          if True',
     'aa343 der Kopf zaehlt Gebautes nicht als fehlend'),
    ('Multibuy kopiert wieder, was der Plan selbst baut',
     'eve_trader/ui/main_window.py',
     '                    if int(_r["tid"]) in _baut_kopie:',
     '                    if False:',
     'aa344 gebaute Posten werden uebersprungen'),
    ('Das Weglassen wird verschwiegen',
     'eve_trader/ui/main_window.py',
     '                    + (_txt(" \\u2013 {n} left out, this plan builds them").format(',
     '                    + (_txt("").format(',
     'aa344 und das wird gesagt, nicht verschwiegen'),
    ('Die Karten springen beim Oeffnen wieder sichtbar um',
     'eve_trader/ui/main_window.py',
     '            plans = sorted(plans, key=lambda _p: _rang.get(str(_p.get("id")), 10**6))',
     '            pass   # MUTATION',
     'aa345 und beim Aufbau angewandt'),
    ('Die Reihenfolge wird nicht mehr gemerkt',
     'eve_trader/ui/main_window.py',
     '                self.settings["bau_plan_sortierung"] = _neu',
     '                pass   # MUTATION',
     'aa345 die letzte Reihenfolge wird gemerkt'),
    ('Eine teilweise Reservierung kuerzt wieder still',
     'eve_trader/ui/main_window.py',
     '                    if _resv_t > 0:',
     '                    if False:',
     'aa347 auch ein Rest zeigt die Reservierung'),
    ('Der Materialien-Reiter verschweigt wieder den Gesamtbesitz',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '            if _ges_row > int(_q_esi) and 3 in _exact:',
     '            if False:',
     'aa348 und nur genannt, wenn er groesser ist'),
    ('Der eingefrorene Plan bekommt seinen Bestand wieder ohne Reservierungen',
     'eve_trader/ui/main_window.py',
     '                self._reservierungen_anwenden(_fz_stock)\n                opts["stock"] = _fz_stock',
     '                opts["stock"] = _fz_stock',
     'aa139 beide Wege laufen durch die eine Funktion'),
    ('Der Bestandsbereich waehlt die Strukturen wieder selbst',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    structs = self._bau_plan_structs()',
     '                    structs = [s for k, s in ((k, self._struct_for_activity(k)) for k, _l in self._STRUCT_ACTIVITIES) if s]',
     'aa349 der Bestandsbereich benutzt sie'),
    ('Die Stufen des Plans werden bei der Ortsmenge ignoriert',
     'eve_trader/ui/main_window.py',
     '        for _k, _s in stufen.items():\n            if _s and id(_s) not in seen:',
     '        for _k, _s in {}.items():\n            if _s and id(_s) not in seen:',
     'aa349 die Plan-Struktur A zaehlt'),
    ('Die Invention-Haken verschwinden aus dem Invention-Reiter',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                left.addWidget(_inv_kauf_row)',
     '                pass   # MUTATION',
     'aa59 die Invention-Haken stehen im Invention-Reiter'),
    ('Die Kategorien-Karte heisst wieder nur "Categories"',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _txt("Do I have the blueprints?"),',
     '            _txt("Categories"),',
     'aa59 die Kategorien-Karte heisst nach ihrer Frage'),
    ('Das Mengenfeld meldet wieder jede Ziffer',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        qty_spin.setKeyboardTracking(False)',
     '        pass   # MUTATION',
     'aa338 das Mengenfeld schweigt waehrend des Tippens'),
    ('Der Prozent-Suffix von ME faellt weg',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        me_spin.setSuffix(" %")',
     '        pass   # MUTATION',
     'aa338 ME und TE zeigen weiter Prozent'),
    ('Abgehakte Datacores landen wieder im Wagen',
     'eve_trader/ui/main_window.py',
     '            items = [(t, n) for t, n in items if int(t) not in _inv_aus]',
     '            pass   # MUTATION',
     'aa350 und nimmt die betroffenen Zeilen ganz heraus'),
    ('Ein Gruppen-Haekchen laesst die Zeile wieder "vorhanden" sagen',
     'eve_trader/ui/main_window.py',
     '        self._bd_excluded_ids = set(opts["excluded"])\n        opts["never_build"] = self._bau_cant_build(list(ids), groups,',
     '        opts["never_build"] = self._bau_cant_build(list(ids), groups,',
     'aa351 der Auffrischer merkt sie ebenfalls'),
    ('Der Blaupausen-Name ist wieder nur eine Beschriftung',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                                self._copy_bp_name_value(_nm))',
     '                                None)',
     'aa352 die Blaupausen-Zelle ist ein Knopf'),
    ('Reaktionen bekommen wieder "Blueprint" statt "Reaction Formula"',
     'eve_trader/ui/main_window.py',
     '        if activity == industry.REACTION:\n            return f"{base} Reaction Formula"',
     '        if False:\n            return f"{base} Reaction Formula"',
     'aa352 Reaktionen heissen Reaction Formula'),
    ('Die Blacklist startet wieder eingeklappt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            self._build_blacklist_compact(), expanded=True, accent=theme.AMBER))',
     '            self._build_blacklist_compact(), expanded=False, accent=theme.AMBER))',
     'aa59 Build or buy, Production depth und Blacklist starten offen'),
    ('Blacklisten per Rechtsklick wirkt wieder nicht',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                self._bau_refresh_exclusions_and_rebuild()\n\n            a_chart',
     '                pass   # MUTATION\n\n            a_chart',
     'aa350 er rechnet die Ausschlussliste neu'),
    ('Die Rezepte werden bei jedem Oeffnen neu eingelesen',
     'eve_trader/ui/main_window.py',
     '            # geladen wurde - s. industry.recipes_cached.\n            recipes = industry.recipes_cached()',
     '            recipes = industry.Recipes()',
     'aa351 und der Bauplan benutzt sie'),
    ('Der Systemkostenindex wird bei jedem Oeffnen neu geholt',
     'eve_trader/esi.py',
     '    return _ttl_geholt("system_cost_indices", _system_cost_indices_frisch)',
     '    return _system_cost_indices_frisch()',
     'aa351 die beiden grossen Listen werden vorgehalten'),
    ('"Alles aktualisieren" verwirft die alten Listen nicht mehr',
     'eve_trader/ui/main_window.py',
     '            esi.cache_leeren()',
     '            pass   # MUTATION',
     "aa351 'Alles aktualisieren' verwirft sie"),
    ('Ein neuer Bauplan erbt wieder die Blacklist des letzten',
     'eve_trader/ui/main_window.py',
     '                _std = config.DEFAULT_SETTINGS',
     '                _std = {}   # MUTATION',
     'aa352 bau_blacklist_names wird zurueckgesetzt'),
    ('Ein gespeicherter Plan bringt seine Einstellungen nicht mehr mit',
     'eve_trader/ui/main_window.py',
     '            if _pk in p:\n                self.settings[_sk] = p[_pk]',
     '            if False:\n                self.settings[_sk] = p[_pk]',
     'aa352 und beim Oeffnen zurueckgeholt'),
    ('Der alte Markt-Scan wird nicht mehr gemeldet',
     'eve_trader/ui/main_window.py',
     '            if _alter is None or _alter > self._SCAN_ALT_SEKUNDEN:',
     '            if False:',
     'b67 nach 20 Minuten warnt es wieder'),
    ('Der Hub-Wechsel loest keine Warnung mehr aus',
     'eve_trader/ui/main_window.py',
     '            if getattr(self, "_scan_hub_gewechselt", False):',
     '            if False:',
     'b67 nach Hub-Wechsel steht eine Warnung'),
    ('Das Blinken hoert nach dem Scan nicht mehr auf',
     'eve_trader/ui/main_window.py',
     '            if tmr.isActive():\n                tmr.stop()',
     '            if False:\n                tmr.stop()',
     'b67 und das Blinken hoert auf'),
    ('Ein neuer Wert umgeht die Zensur',
     'eve_trader/ui/main_window.py',
     '        super().setText(self._MASKE if self._zensiert else text)',
     '        super().setText(text)',
     'b68 auch ein neuer Wert bleibt verdeckt'),
    ('Die Zensur wird nicht mehr gespeichert',
     'eve_trader/ui/main_window.py',
     '        self.settings["kpi_zensiert"] = sorted(_aus)',
     '        pass   # MUTATION',
     'b68 der Zustand ist gespeichert'),
    ('Verdecken nimmt gleich alle Karten mit',
     'eve_trader/ui/main_window.py',
     '            _an = _k in _aus',
     '            _an = bool(_aus)',
     'b68 die Nachbarkarte bleibt offen'),
    ('Die Stueckzahl rutscht wieder in den Verkaufspreis-Zweig',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            _q = max(1, int(qty or 1))\n            if _sell_eff:',
     '            if _sell_eff:',
     'aa353 die Stueckzahl steht VOR der Verzweigung'),
    ('Der Blink-Rahmen aendert wieder die Knopfgroesse',
     'eve_trader/ui/main_window.py',
     '        _farbe = theme.AMBER if an else "transparent"',
     '        _farbe = theme.AMBER if an else "none"',
     'b67 der Aus-Zustand hat denselben Rahmen, nur durchsichtig'),
    ('Das Blinken laeuft nach dem Scan weiter',
     'eve_trader/ui/main_window.py',
     '        self._scan_laeuft = True',
     '        self._scan_laeuft = False   # MUTATION',
     'b67 waehrend des Scans blinkt nichts'),
    ('Total assets ist wieder cyan und klein',
     'eve_trader/ui/main_window.py',
     '        self.k_wealth.setStyleSheet(\n            f"color:{theme.TEXT}; font-family:{theme.MONO}; "\n            f"font-size:26px; font-weight:800;")\n        self.k_wealth.setToolTip(',
     '        self.k_wealth.setStyleSheet(f"color:{theme.CYAN}")\n        self.k_wealth.setToolTip(',
     'b2o Leitzahl gross und neutral'),
    ('Der Knopf wird beim Blinken nicht mehr festgenagelt',
     'eve_trader/ui/main_window.py',
     '                btn.setFixedSize(btn.size())',
     '                pass   # MUTATION',
     'b67 beim Blinken ist die Knopfgroesse fest'),
    ('Die Warnung bleibt nach dem Scan stumm',
     'eve_trader/ui/main_window.py',
     '            self._scan_laeuft = False\n            if hasattr(self, "_scan_alter_pruefen"):',
     '            self._scan_laeuft = True\n            if hasattr(self, "_scan_alter_pruefen"):',
     'b67 danach darf wieder geprueft werden'),
    ('Tooltips erben wieder die Riesenschrift des Widgets',
     'eve_trader/ui/tooltips.py',
     '            f"font-family:{theme.FONT}; font-size:{SCHRIFT_PX}px; "',
     '            f"font-family:{theme.FONT}; "',
     'aa354 die Schrift ist fest und klein'),
    ('Die Tooltip-Umleitung wird beim Start nicht mehr aktiviert',
     'eve_trader/__main__.py',
     '    _tt.aktivieren()',
     '    pass   # MUTATION',
     'aa354 die Umleitung wird beim Start aktiviert'),
    ('Die Tooltip-Regel kommt nicht mehr ins Widget-Stylesheet',
     'eve_trader/ui/tooltips.py',
     '    QWidget.setStyleSheet = _setStyleSheet',
     '    pass   # MUTATION',
     'aa354 die Regel landet im Widget-Stylesheet'),
    ('Eine Liste ohne Selektor wird nicht mehr eingefasst',
     'eve_trader/ui/tooltips.py',
     '    if "{" not in sheet:\n        sheet = "*{" + sheet + "}"',
     '    if False:\n        sheet = "*{" + sheet + "}"',
     'aa354 eine Liste ohne Selektor wird eingefasst'),
    ('Fehlendes Rezept wird wieder verschwiegen',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    if not _p2b.get(_cid_b):\n'
     '                        act = _txt("buy \\u00b7 no recipe")',
     '                    if False:\n                        pass   # MUTATION',
     'aa325 es haengt an product_to_bp'),
    # ABSTURZ OHNE VERKAUFSPREIS (Nutzer "buyenne", 15.09.2026): faellt die
    # Vorbelegung weg, ist `gross` im Capital-Fall wieder unbelegt und der
    # Bauplan stuerzt beim Oeffnen ab. Der Waechter dafuer ist aa355, der
    # Verhaltenstest b7d.
    ('Gewinn-Zahlen sind ohne Verkaufspreis wieder unbelegt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            gross = None\n'
     '            prof = None\n'
     '            prof_raw = None\n'
     '            total_all = None',
     '            pass   # MUTATION',
     'aa355 keine Gewinn-Zahl wird ohne Verkaufspreis gelesen'),
    # CONTRACT-KNOPF (Nutzer-Wunsch 15.09.2026): blinkt er nicht mehr, ist er
    # wieder so unauffaellig wie im Dropdown - der Grund fuer den Umbau faellt
    # damit weg, ohne dass irgendetwas kaputt aussieht.
    ('Der Contract-Knopf blinkt nicht mehr',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '            if not tmr.isActive():\n                tmr.start()',
     '            pass   # MUTATION',
     'b7e und er blinkt'),
    # KOPIERBARER FORMEL-NAME (Nutzer-Wunsch 15.09.2026): faellt die Hinterlegung
    # weg, sieht der Runplaner unveraendert aus - nur klickt man ins Leere.
    ('Der Formel-Name im Runplaner ist nicht mehr hinterlegt',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                    iit.setData(0, ROLLE_KOPIERNAME,',
     '                    iit.setData(0, Qt.UserRole + 99,   # MUTATION',
     'b7f der Formel-Name wird an der Zeile hinterlegt'),
    # HANDSORTIERUNG (Nutzer-Wunsch 15.09.2026): faellt der Vorrang weg, wirft
    # der naechste ESI-Lauf die selbst gezogene Reihenfolge wieder um - und
    # zwar erst Minuten spaeter, wenn niemand mehr den Zusammenhang sieht.
    ('Die Automatik ordnet wieder um, obwohl handsortiert',
     'eve_trader/ui/main_window.py',
     '        if self._plan_eigene_folge_gilt():\n            return',
     '        if False:   # MUTATION\n            return',
     'b7g die Automatik ruehrt die Handfolge nicht an'),
    # ALTER CONTRACT-STAND (Nutzer-Wunsch 15.09.2026): blinkt der Knopf nicht
    # mehr, vergleicht man still Preise von gestern - die Zahlen sehen dabei
    # voellig normal aus, nur eben falsch.
    ('Ein alter Contract-Stand blinkt nicht mehr',
     'eve_trader/ui/main_window.py',
     '            _alt = _alter is None or _alter > self._CONTRACT_ALT_SEKUNDEN',
     '            _alt = False   # MUTATION',
     'b7h ohne Stand blinkt er'),
    # WARNUNG VOR DEM SCAN: faellt sie weg, haelt der Naechste das Programm
    # fuer haengen geblieben (genau die Frage des Nutzers).
    ('Der Contract-Scan startet wieder ohne Rueckfrage',
     'eve_trader/ui/main_window.py',
     '        if _QMB.question(\n                self, t("Load contract prices"),\n                t("This searches the public contracts of ALL regions and then "\n                  "looks into every hit individually \\u2013 that takes SEVERAL "\n                  "MINUTES (around five is normal).\\n\\nIt runs in the "\n                  "background, you can keep working. Start now?"),\n                _QMB.Ok | _QMB.Cancel, _QMB.Ok) != _QMB.Ok:\n            return',
     '        pass   # MUTATION',
     'b7h vor dem Scan wird gefragt'),
    # EIGENE FOLGE UEBERLEBT DAS AUSSCHALTEN (Nutzer-Wunsch 15.09.2026):
    # zaehlt wieder nur der Anordnen-Modus, wirft das Ausschalten die
    # Handarbeit sofort um - sein Einwand "da liegt kein Sinn dahinter".
    ('Nur noch der Anordnen-Modus haelt die Automatik heraus',
     'eve_trader/ui/main_window.py',
     '        return bool(self.settings.get("bau_plan_manuell")\n'
     '                    or self.settings.get("bau_plan_eigene_folge"))',
     '        return bool(self.settings.get("bau_plan_manuell"))  # MUTATION',
     'b7g aber die eigene Folge gilt weiter'),
    # ZUSTAND AM KNOPF: ohne ihn sieht man nicht, ob der Modus laeuft - und
    # wundert sich, warum die Karten-Knoepfe nicht reagieren.
    ('Der Anordnen-Knopf zeigt seinen Zustand nicht mehr',
     'eve_trader/ui/main_window.py',
     '            btn.setObjectName("Primary" if an else "")',
     '            btn.setObjectName("")   # MUTATION',
     'b7g eingeschaltet leuchtet er wie'),
    # HERVORHEBUNG NUR AUF DER KARTE (Nutzer-Befund 15.09.2026): ohne
    # Selektor vererbt Qt die Regel an jedes Label darin - dann ist ploetzlich
    # auch "Profit" umrahmt.
    ('Die Hervorhebung faerbt wieder die ganze Karte samt Kindern',
     'eve_trader/ui/mw_basis.py',
     '    OBJEKTNAME = "SortierKarte"',
     '    OBJEKTNAME = ""   # MUTATION',
     'b7g Zustand'),
    # DER WEG ZURUECK ZUR AUTOMATIK (Nutzer-Wunsch 15.09.2026): beendet der
    # Knopf die eigene Folge nicht, sortiert er einmal - und der naechste
    # ESI-Lauf stellt die Handfolge wieder her. Ein Knopf, der sich selbst
    # widerruft.
    ('Der Fortschritts-Knopf beendet die eigene Folge nicht mehr',
     'eve_trader/ui/main_window.py',
     '        self.settings["bau_plan_eigene_folge"] = False\n',
     '',
     'b7g er beendet die eigene Folge'),
    # DIE ABKUERZUNG DARF NIE RATEN (Nutzer-Frage 16.09.2026): ordnet
    # `suite_fuer` nach dem Anfangsbuchstaben statt nach der Pruefnummer,
    # landen deutsche Woerter mit b ("billige Items ...") bei der b-Suite.
    # Dann laeuft die falsche Suite, die erwartete Pruefung ist nicht dabei
    # und die Rotprobe meldet BLIND fuer etwas, das sauber ROT ist - der
    # gefaehrlichste Ausfall, den dieses Werkzeug haben kann.
    ('Die Suiten-Zuordnung geht wieder nach dem Anfangsbuchstaben',
     'rotprobe.py',
     '    if _re_suite.match(_e):\n'
     '        return "aa" if _e.startswith("aa") else "b"\n',
     '    if _e.startswith("aa"):\n'
     '        return "aa"\n'
     '    if _e.startswith("b"):\n'
     '        return "b"\n',
     'aa359 keine zugeordnete Pruefung liegt in der ANDEREN Suite'),
    # CHARAKTER-FILTER DER BEHAELTER-LISTE (Nutzer-Befund 15.09.2026):
    # faellt er weg, stehen die Behaelter ALLER Charaktere unter einer
    # Liste, die oben nur einen zeigt.
    ('Die Behaelter-Liste beachtet die Charakter-Wahl nicht mehr',
     'eve_trader/ui/main_window.py',
     '            if _wahl not in (None, "all") and _cid != _wahl:\n'
     '                continue\n',
     '',
     'b7o bei einem Charakter nur SEINE Behaelter'),
    # UND SIE MUSS BEIM UMSCHALTEN MITGEHEN.
    ('Der Charakter-Wechsel zeichnet die Behaelter-Liste nicht mehr neu',
     'eve_trader/ui/main_window.py',
     '        self.pf_char.currentIndexChanged.connect('
     'self._container_neu_zeichnen)\n',
     '',
     'b7o der Wahlschalter zeichnet die Liste neu'),
    # NUR STATION-CONTAINER (Nutzer-Befund 15.09.2026): faellt die
    # Typ-Erkennung weg, zaehlt wieder nur, was die Schloss-Markierung
    # traegt - und alles in einem Freight Container ist fuers Portfolio
    # unsichtbar.
    ('Ein Behaelter wird wieder nur am Inhalt erkannt, nicht am Typ',
     'eve_trader/esi.py',
     '        if a.get("type_id") in _ctypes:\n'
     '            return True\n',
     '',
     'aa358 MIT Typwissen wird der Behaelter erkannt'),
    # DIE TYPEN MUESSEN AUCH ANKOMMEN.
    ('Der Assets-Abruf reicht die Behaelter-Typen nicht mehr durch',
     'eve_trader/esi.py',
     '    hangar, containers = hangar_und_container(assets, _ctypes)\n',
     '    hangar, containers = hangar_und_container(assets)   # MUTATION\n',
     'aa358 der Assets-Abruf reicht die Behaelter-Typen durch'),
    # UND "FREIGHTER" DARF KEIN BEHAELTER WERDEN - sonst zaehlte die
    # Ladung jedes Frachters als Hangarbestand.
    ('Die Behaelter-Regel greift auch nach "freight" im Gruppennamen',
     'eve_trader/industry.py',
     '        if "container" in low and "blueprint" not in low:\n',
     '        if ("container" in low or "freight" in low) and "blueprint" not in low:\n',
     'aa358 Freighter/Jump Freighter sind KEINE Behaelter'),
    # DER BAUPLAN-BEREICH "UEBERALL" (Nutzer-Frage 16.09.2026): zaehlt die
    # gemeinsame Regel den Behaelter-Inhalt nicht mehr, ist im Bauplan
    # wieder alles unsichtbar, was in einem Frachtcontainer liegt.
    ('Der Bestand zaehlt den Inhalt eines Behaelters nicht mehr mit',
     'eve_trader/esi.py',
     '            summe[int(t)] = summe.get(int(t), 0) + int(q)\n',
     '            pass   # MUTATION\n',
     'aa360 Inhalt eines Frachtcontainers zaehlt zum Bestand'),
    # UND DER BEHAELTER SELBST DARF NICHT VERSCHWINDEN - ein Cargo
    # Container ist baubares Material. Zu niedriger Bestand = Einkauf zu
    # viel.
    ('Der Behaelter selbst faellt aus dem Bestand',
     'eve_trader/esi.py',
     '        summe[_t] = summe.get(_t, 0) + int(c.get("qty") or 1)\n',
     '        pass   # MUTATION\n',
     'aa360 der Behaelter selbst bleibt gezaehlt'),
    # UND DER ABRUF MUSS DIE TYPEN AUCH HIER DURCHREICHEN.
    ('Der Bestands-Abruf faellt auf die alte Inhalts-Regel zurueck',
     'eve_trader/esi.py',
     '    return hangar_summe(assets, container_type_ids_safe())\n',
     '    return hangar_summe(assets, set())   # MUTATION\n',
     'aa360 der Bestands-Abruf benutzt dieselbe Zaehlung'),
    # DIE ORTSGEBUNDENEN BEREICHE (Nutzer, 16.09.2026): steigt die Zaehlung
    # nicht mehr in die Behaelter hinab, ist an der Bau-Struktur nur noch
    # sichtbar, was lose im Hangar liegt.
    ('Die Ortszaehlung steigt nicht mehr in Behaelter hinab',
     'eve_trader/esi.py',
     '                collect(iid)     # in den Behaelter-Inhalt hinein\n',
     '                pass   # MUTATION\n',
     'aa361 Frachtcontainer-Inhalt zaehlt am Bau-Ort'),
    # UND SIE DARF NICHT EINFACH ALLES ZAEHLEN - sonst waere der ganze Sinn
    # des Bereichs ("nur was hier liegt") dahin.
    ('Die Ortszaehlung nimmt jeden Ort mit, nicht nur die gewaehlten',
     'eve_trader/esi.py',
     '    for loc in {int(x) for x in location_ids or ()}:\n',
     '    for loc in list(by_parent.keys()):   # MUTATION\n',
     'aa361 Material an einem anderen Ort zaehlt NICHT mit'),
    # UND DER ABRUF MUSS SIE BENUTZEN.
    ('Der ortsgebundene Abruf benutzt die gemeinsame Zaehlung nicht mehr',
     'eve_trader/esi.py',
     '    out, seen, _per_loc = bestand_an_orten(assets, location_ids,\n',
     '    out, seen, _per_loc = (lambda *a: ({}, set(), {}))(   # MUTATION\n',
     'aa361 der ortsgebundene Abruf benutzt dieselbe Zaehlung'),
    # ==== CORP-HANGAR (1.0.8) ====
    # DIE VERDREIFACHUNG (CLAUDE.md): wird der Plan je CHARAKTER statt je
    # Corp gefuehrt, holt der Bauplan denselben Hangar dreimal - Bestand
    # dreifach, Plan kauft ZU WENIG.
    ('Der Corp-Abruf laeuft wieder je Charakter statt je Corporation',
     'eve_trader/corp.py',
     '        if rolle in rollen:\n            plan[corp] = cid\n',
     '        if rolle in rollen:\n            plan[cid] = cid   # MUTATION\n',
     'b7q EIN Corp-Abruf fuer drei Charaktere derselben Corp'),
    # DIVISION-FILTER (Entscheid 14.09.2026): faellt er weg, wandert
    # Material aus JEDER Division in die Bauplanung.
    ('Der Corp-Bestand ignoriert die gewaehlten Divisions',
     'eve_trader/corp.py',
     '        if not div or div not in gewaehlt:\n',
     '        if not div:   # MUTATION\n',
     'aa362 Material einer NICHT gewaehlten Division zaehlt nicht'),
    # SCHIFFE (Nutzer, 16.09.2026): auch im Corp-Hangar zaehlt Schiffsinhalt
    # nie.
    ('Der Corp-Bestand steigt in Corp-Schiffe hinein',
     'eve_trader/corp.py',
     '        if ist_behaelter(a):\n            for c in by_parent.get(iid, []):\n',
     '        if True:   # MUTATION\n            for c in by_parent.get(iid, []):\n',
     'aa362 Schiffsladung zaehlt NICHT (sonst 6000 statt 1000 Tritanium)'),
    # ORTSGRENZE: der Corp-Hangar an einer fremden Struktur darf im
    # Struktur-Bereich nicht zaehlen - dieselbe Regel wie beim eigenen.
    ('Der Corp-Bestand kennt keine Ortsgrenze mehr',
     'eve_trader/corp.py',
     '        if orte is not None and wurzel_ort(a, by_id) not in orte:\n',
     '        if False:   # MUTATION\n',
     'aa362 Ortsgrenze: die andere Struktur bleibt draussen'),
    # DAS BUERO DAZWISCHEN: ohne das Hochlaufen haengt die Division am Buero-
    # Item, nicht an der Station, und die Ortsgrenze findet nichts.
    ('Die Ortsaufloesung laeuft nicht mehr bis zur Station hoch',
     'eve_trader/corp.py',
     '    loc = a.get("location_id")\n    for _ in range(max_tiefe):\n',
     '    loc = a.get("location_id")\n    for _ in range(0):   # MUTATION\n',
     'aa362 Ortsgrenze: unter dem Buero wird die Station erkannt'),
    # STANDARD AUS (Entscheid 14.09.2026, Regel 3).
    ('Der Corp-Hangar ist standardmaessig AN',
     'eve_trader/config.py',
     '    "use_corp": False,\n',
     '    "use_corp": True,\n',
     'aa362 Corp-Hangar ist standardmaessig AUS'),
    # KEINE DIVISION -> NICHTS, nicht "alle".
    ('Ohne gewaehlte Division zaehlt der Corp-Bestand ALLE Divisions',
     'eve_trader/corp.py',
     '    if not gewaehlt:\n        return {}, {}\n',
     '    if not gewaehlt:\n        gewaehlt = set(ALLE_DIVISIONS)   # MUTATION\n',
     'aa362 keine Division gewaehlt -> nichts'),
    # DIE SCOPES KOMMEN NUR MIT SCHALTER - sonst fragt jedes Verlinken jeden
    # Nutzer nach Corp-Rechten, die er nie wollte.
    ('Beim Verlinken werden die Corp-Scopes nicht mehr angehaengt',
     'eve_trader/ui/main_window.py',
     '        if self.settings.get("use_corp"):\n'
     '            scopes.extend(config.CORP_SCOPES)',
     '        if self.settings.get("use_corp"):\n'
     '            pass   # MUTATION',
     'aa362 beim Verlinken kommen die Corp-Scopes nur mit Schalter'),
    # SCHALTER AUS MUSS "KEIN ABRUF" HEISSEN - nicht nur "nicht zaehlen".
    ('Der Bauplan fragt die Corp auch bei ausgeschaltetem Schalter ab',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        if not self.settings.get("use_corp"):\n            return leer\n',
     '        if False:   # MUTATION\n            return leer\n',
     'b7q Schalter aus -> kein Corp-Bestand, kein Abruf'),
    # OHNE CORP-SCOPE IM TOKEN: kein Abruf, sondern "neu verknuepfen".
    ('Ein Token ohne Corp-Scope wird trotzdem fuer den Abruf benutzt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                out["relink"].append(namen.get(cid, str(cid)))\n'
     '                rollen_von[cid] = None\n                continue\n',
     '                out["relink"].append(namen.get(cid, str(cid)))\n'
     '                rollen_von[cid] = None\n',
     'b7q ohne Corp-Scope: kein Abruf'),
    # DER CORP-BESTAND MUSS IM POOL ANKOMMEN - in beiden Bereichen.
    ('Der Corp-Bestand wird im Struktur-Bereich nicht mehr aufaddiert',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    for t, q in (_corp.get("summe") or {}).items():\n'
     '                        agg[int(t)] = agg.get(int(t), 0) + int(q)\n',
     '',
     'aa362 der Corp-Bestand wird in BEIDEN Bereichen aufaddiert'),
    # DIVISION-KAESTCHEN SPEICHERN SOFORT - sonst gilt, was man sieht, nicht.
    ('Ein Division-Kaestchen speichert nicht mehr sofort',
     'eve_trader/ui/main_window.py',
     '        self.settings["corp_divisions"] = neu\n',
     '        pass   # MUTATION\n',
     'b7q ein Kaestchen speichert die Division sofort'),
    # ==== ZWEI KNOEPFE, ZWEI NAMEN (17.09.2026) ====
    ('Der SDE-Knopf heisst wieder "Load blueprints"',
     'eve_trader/ui/main_window.py',
     '        self.g_sde_btn = QPushButton(t("Load recipes"))\n',
     '        self.g_sde_btn = QPushButton(t("Load blueprints"))   # MUTATION\n',
     "aa363 der SDE-Knopf oben heisst 'Load recipes'"),
    # ==== LEER-HINWEIS TUT, WAS FEHLT (Nutzer-Befund 17.09.2026) ====
    ('Der Leer-Hinweis bietet nach dem Scan weiter nur den Scan an',
     'eve_trader/ui/main_window.py',
     '                if store.snapshot_age_seconds() is None:\n',
     '                if True:   # MUTATION\n',
     "b7s nach dem Scan bietet der Knopf 'Load deals' an"),
    ('Der Blaupausen-Hinweis zeigt wieder auf den SDE-Download',
     'eve_trader/ui/main_window.py',
     '        _bp = getattr(self, "bp_refresh_btn", None) or getattr(self, "g_sde_btn", None)\n',
     '        _bp = getattr(self, "g_sde_btn", None)   # MUTATION\n',
     'b7s der Blaupausen-Knopf laedt MEINE Blaupausen, nicht die SDE'),
    ('Nach dem Scan werden die Leer-Hinweise nicht mehr neu gestellt',
     'eve_trader/ui/main_window.py',
     '            self._leerhinweise_aktualisieren()   # "Market scan" -> "Load deals"\n',
     '',
     'b7s nach dem Scan stellt das Programm die Hinweise neu'),
    # ==== RUNS DIREKT EINGEBEN (Discord, 16.09.2026) ====
    # Das Runs-Feld muss ins Stueckfeld schreiben - sonst rechnet der Plan
    # mit der alten Menge, waehrend der Nutzer eine andere sieht.
    ('Das Runs-Feld schreibt nicht mehr ins Mengenfeld',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    qty_spin.setValue(runs_spin.value() * _out_per_run)\n',
     '                    pass   # MUTATION\n',
     "b10 7 Runs -> 1'400 Stueck im Mengenfeld"),
    ('Das Mengenfeld schreibt nicht mehr ins Runs-Feld',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    runs_spin.setValue(-(-qty_spin.value() // _out_per_run))\n',
     '                    pass   # MUTATION\n',
     "b10 1'000 Stueck -> 5 Runs"),
    # NUR BEI MEHR ALS 1 STUECK JE RUN - beim Einzelstueck waere der
    # Schalter Laerm (Nutzer: "nur bei Produkten, die wirklich mehr liefern").
    ('Der Runs-Umschalter erscheint auch beim Einzelstueck',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        runs_spin = None\n        _qty_mode_btn = None\n        if _out_per_run > 1:\n',
     '        runs_spin = None\n        _qty_mode_btn = None\n        if _out_per_run >= 1:   # MUTATION\n',
     'b10 und keinen Runs-Umschalter (waere nur Laerm)'),
    ('Enter im Runs-Feld rechnet den Plan nicht mehr sofort',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '        if runs_spin is not None:\n'
     '            runs_spin.editingFinished.connect(_qty_uebernehmen)\n',
     '',
     "b10 Enter im Runs-Feld -> der Plan rechnet mit 1'400"),
    ('Die Runs/Stueck-Wahl wird nicht mehr gespeichert',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                    self.settings["bau_qty_in_runs"] = _qty_mode["runs"]\n',
     '                    pass   # MUTATION\n',
     'b10 die Wahl wird gespeichert'),
    # SCHIFFE (Nutzer, 16.09.2026): steigt die Ortszaehlung wieder in JEDES
    # Kind hinab, zaehlen gefittete Module, Drohnen und Schiffsladung als
    # Baumaterial an der Struktur - Bestand zu hoch, die gefaehrliche
    # Richtung.
    ('Die Ortszaehlung steigt wieder in Schiffe hinein',
     'eve_trader/esi.py',
     '            if _ist_behaelter(a):\n'
     '                collect(iid)     # in den Behaelter-Inhalt hinein\n',
     '            collect(iid)   # MUTATION\n',
     'aa361 Schiffsladung zaehlt NICHT'),
    # WO BIN ICH (Nutzer-Wunsch 15.09.2026): faellt die Hervorhebung weg,
    # steht die rechte Leiste wieder durchweg neutral - genau der Zustand,
    # den er gemeldet hat.
    ('Die rechte Bau-Leiste hebt die offene Seite nicht mehr hervor',
     'eve_trader/ui/main_window.py',
     '            b.setStyleSheet(self._bau_rail_active_css if _i == idx\n'
     '                            else self._bau_rail_idle_css)\n',
     '            b.setStyleSheet(self._bau_rail_idle_css)   # MUTATION\n',
     'b7n Seite 0: genau dieser eine Knopf leuchtet'),
    # DER BALKEN IST DIE "SELBE OPTIK" - ohne ihn ist es eine aehnliche.
    ('Dem aktiven Knopf fehlt der Cyan-Balken der linken Leiste',
     'eve_trader/ui/main_window.py',
     '                  f"border-left:3px solid {theme.CYAN}; "\n',
     '',
     'b7n der aktive Knopf traegt den Cyan-Balken links'),
    # RIGS FINDEN (Nutzer-Wunsch 15.09.2026): faellt die Verengung weg,
    # zeigt das Rig-Preset wieder alle Module - der Knopf verspricht dann
    # etwas, das er nicht haelt.
    ('Das Rig-Preset verengt nicht mehr auf die Rig-Gruppen',
     'eve_trader/ui/main_window.py',
     '            if rigs_only and _rig_gids and _g not in _rig_gids:\n'
     '                return False\n',
     '',
     'aa357 der Scan verengt auf die Rig-Gruppen'),
    # DIE NAMENSREGEL: mit der Teilwortsuche waeren alle FREGATTEN Rigs.
    ('Die Rig-Regel sucht wieder Teilworte statt den Namensanfang',
     'eve_trader/industry.py',
     '        if low.startswith("rig ") and "blueprint" not in low:\n',
     '        if "rig" in low:   # MUTATION\n',
     'aa357 Fregatten sind KEINE Rigs'),
    # TOUR UEBER DER RECHTEN LEISTE (Nutzer-Befund 15.09.2026): faellt der
    # Sonderfall weg, steht die Tour wieder UNTER dem Anker - und deckt
    # damit genau die Leiste zu, ueber die der Schritt gerade spricht.
    ('Die Tour stellt sich wieder unter einen Anker in der rechten Leiste',
     'eve_trader/ui/tutorial.py',
     'if (_win is not self.mw and _r.width() > 0\n'
     '                        and _a_links.x() >= _r.left() '
     '+ (_r.width() * 2) // 3):\n'
     '                    x, y = _a_links.x() - _b - 12, _a_links.y()\n',
     'pass   # MUTATION\n',
     'b7m bei einem Anker in der rechten Leiste steht die Tour links '
     'DANEBEN, nicht darunter'),
    # MEINE EIGENE REGRESSION (Nutzer-Befund 16.09.2026, Schritt 7/15): gilt
    # die Links-Regel auch im HAUPTFENSTER, landet die Tour unter dem
    # modalen "New build plan"-Fenster.
    ('Die Links-Regel gilt wieder auch im Hauptfenster',
     'eve_trader/ui/tutorial.py',
     'if (_win is not self.mw and _r.width() > 0\n',
     'if (_r.width() > 0\n',
     'b7m im HAUPTFENSTER bleibt es an derselben Stelle beim Platz DARUNTER'),
    # MODALES FENSTER (Nutzer-Screenshot 16.09.2026, Schritt 7/15): faellt der
    # Sonderfall weg, richtet sich die Tour wieder am ANKER aus - und der
    # steckt im modalen Fenster, das immer oben liegt. Sie ist dann verdeckt.
    ('Die Tour richtet sich in einem modalen Fenster wieder am Anker aus',
     'eve_trader/ui/tutorial.py',
     '                if _modal:\n',
     '                if False:   # MUTATION\n',
     'b7m die Tour verdeckt ein MODALES Fenster nicht'),
    # UND SIE MUSS DABEI WIRKLICH AM FENSTER HAENGEN, nicht nur zufaellig
    # danebenstehen: unter den DIALOG, nicht unter den Anker.
    ('Die Tour stellt sich unter den Anker statt unter den ganzen Dialog',
     'eve_trader/ui/tutorial.py',
     '                        x, y = _r.left(), _r.bottom() + 8\n',
     '                        x, y = _r.left(), _a_links.y() + 8\n',
     'b7m und steht dann unter dem modalen Fenster'),
    # TOUR LAG HINTER DEM BAUPLAN (Nutzer-Screenshot 16.09.2026): faellt
    # dieser Vorrang weg, gewinnt der sichtbare Knopf im Hauptfenster und
    # die Tour bleibt dort haengen - genau das Bild aus dem Screenshot.
    ('Der Bauplan-oeffnen-Schritt zielt wieder aufs Hauptfenster',
     'eve_trader/ui/tutorial.py',
     '            if self.schritte[self.i][4] == "bauplan_offen":\n',
     '            if False:   # MUTATION\n',
     'b7p ist der Bauplan offen, zielt er auf den Bauplan'),
    # TOUR HINTER DEM BAUPLAN (Nutzer-Befund 16.09.2026): oeffnet sich das
    # Fenster mitten im Schritt, muss die Tour mitgehen.
    ('Die Tour merkt einen Fensterwechsel mitten im Schritt nicht mehr',
     'eve_trader/ui/tutorial.py',
     '            _jetzt = self._zielfenster()\n'
     '            if _jetzt is not getattr(self, "_letztes_ziel", None):\n'
     '                self._fenster_ordnen()\n'
     '                return\n',
     '            pass   # MUTATION\n',
     'b7p bei einem Fensterwechsel ordnet sie sich neu'),
    # UND SIE DARF NICHT BEI JEDEM TICK UMHAENGEN - das zog den Bauplan
    # frueher nach hinten (Sitzung 17).
    ('Die Tour haengt bei JEDEM Tick um, nicht nur beim Wechsel',
     'eve_trader/ui/tutorial.py',
     '        self._letztes_ziel = _ziel\n',
     '',
     'b7p ohne Fensterwechsel wird NICHT umgehaengt'),
    # "BACK" LANDETE IM FALSCHEN REITER (Nutzer-Befund 16.09.2026): der
    # Schritt muss seinen Reiter selbst herstellen, sonst haengt er davon
    # ab, woher man kommt.
    ('Der Build-or-buy-Schritt stellt seinen Reiter nicht mehr selbst her',
     'eve_trader/ui/tutorial.py',
     '        (("bd:tab:" + t("Recipe structure"), "_bd_karte_bauenkaufen"),\n'
     '         t("Build or buy?"),\n',
     '        ("_bd_karte_bauenkaufen",\n'
     '         t("Build or buy?"),\n',
     'b78 und stellt dabei den Rezeptstruktur-Reiter selbst her'),
    # RECHTSKLICK AUF DIE OBERE LEISTE (Nutzer-Befund 15.09.2026): faellt
    # ein Riegel weg, blendet Qts eingebautes Fenster-Menue die ganze obere
    # Reihe aus - und niemand kommt darauf, dass ein Rechtsklick schuld war.
    ('Die obere Leiste reicht den Rechtsklick wieder weiter',
     'eve_trader/ui/main_window.py',
     '        tb.setContextMenuPolicy(Qt.PreventContextMenu)\n',
     '',
     'b7l sie reicht den Rechtsklick nicht mehr weiter'),
    # DER ZWEITE WEG: Qt baut das Menue in createPopupMenu, auch beim
    # Rechtsklick NEBEN die Leiste.
    ('Das Fenster baut sein Werkzeugleisten-Menue wieder',
     'eve_trader/ui/main_window.py',
     '        loeschen.\n        """\n        return None\n',
     '        loeschen.\n        """\n'
     '        return super().createPopupMenu()   # MUTATION\n',
     'b7l das Fenster bietet gar kein solches Menue mehr an'),
    # UNGESPEICHERTE EINSTELLUNGEN (Nutzer-Wunsch 15.09.2026): ohne Riegel
    # verlaesst man die Seite still, und die Einstellung wirkt nie - genau
    # der Befund, mit dem er gekommen ist.
    ('Der Seitenwechsel per Widget fragt nicht mehr nach',
     'eve_trader/ui/main_window.py',
     '    def setCurrentWidget(self, w):\n'
     '        if not self._darf_wechseln(self._stack.indexOf(w)):\n'
     '            return\n',
     '    def setCurrentWidget(self, w):\n',
     'b7k und \u201eZurueck\u201c laesst einen auf der Seite'),
    # DERSELBE WEG UEBER DEN INDEX - die Seitenleiste nimmt ihn.
    ('Der Seitenwechsel per Index fragt nicht mehr nach',
     'eve_trader/ui/main_window.py',
     '    def setCurrentIndex(self, i):\n'
     '        if not self._darf_wechseln(i):\n'
     '            return\n',
     '    def setCurrentIndex(self, i):\n',
     'b7k auch der Wechsel ueber den Index wird abgefangen'),
    # OHNE VERGLEICH KEINE ERKENNUNG: dann ist nie etwas "offen" und der
    # Riegel schweigt, obwohl er haengt - die gefaehrlichste Variante,
    # weil alles gebaut aussieht.
    ('Eine Aenderung in den Einstellungen wird nicht mehr erkannt',
     'eve_trader/ui/main_window.py',
     '            return self._einstellungen_feldstand() != alt\n',
     '            return False   # MUTATION\n',
     'b7k eine Aenderung wird erkannt'),
    # NACH DEM SPEICHERN NACHZIEHEN: sonst kommt die Rueckfrage beim
    # naechsten Wechsel trotz Speichern wieder.
    ('Der Feldstand wird nach dem Speichern nicht nachgezogen',
     'eve_trader/ui/main_window.py',
     '        self._einstellungen_stand_merken()\n        self._update_cb_label()\n',
     '        self._update_cb_label()\n',
     'b7k danach ist nichts mehr offen'),
    # KNOEPFE AUF DEN KARTEN (Nutzer-Wunsch 15.09.2026): schluckt der
    # Sortierer wieder jeden Druck, ist der Anordnen-Modus ein Modus, in dem
    # man nichts mehr tun kann.
    ('Der Sortierer schluckt im Anordnen-Modus wieder jeden Knopfdruck',
     'eve_trader/ui/mw_basis.py',
     '                if self._ist_bedienelement(obj):',
     '                if False:   # MUTATION',
     "b7g ein Druck auf 'Open' geht an den Knopf"),
    # CAPITAL-MODUS BEIM START (Nutzer-Wunsch 15.09.2026): bleibt er an,
    # sucht der Naechste vergeblich nach normalen Blaupausen.
    ('Der Capital-Modus wird beim Start nicht mehr ausgeschaltet',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '        self.b_cap_mode.setChecked(False)\n',
     '',
     'b7i und er wird beim Aufbau ausdruecklich ausgeschaltet'),
    # DER HAKEN, DEN NIEMAND GESETZT HAT (Nutzer-Bild 15.09.2026): ohne den
    # Kaestchen-Riegel legt die Kinder-Kaskade den Stuecklisten-Zeilen ein
    # Kaestchen NEU AN - und beim Loesen bleibt das leere stehen.
    ('Die Kaskade fragt nicht mehr, ob es ueberhaupt ein Kaestchen gibt',
     'eve_trader/ui/mw_bauplan_fenster.py',
     '                if (_ch.data(0, Qt.CheckStateRole) is not None\n'
     '                        and _ch.flags() & Qt.ItemIsUserCheckable\n',
     '                if (_ch.flags() & Qt.ItemIsUserCheckable\n',
     'b7j die Kaskade fragt nach dem vorhandenen Kaestchen'),
    # ZWEITER RIEGEL: die Material-Unterzeile ist gar nicht erst abhakbar.
    ('Die Material-Unterzeile behaelt die abhakbaren Standard-Flags',
     'eve_trader/ui/mw_bauplan_tabs.py',
     '                        mit.setFlags(mit.flags() '
     '& ~Qt.ItemIsUserCheckable)\n',
     '',
     'b7j die Material-Unterzeile ist gar nicht erst abhakbar'),
]


_re_suite = re.compile(r"^(aa|b)\d")


def suite_fuer(erwartet):
    """Welche Suite enthaelt die erwartete Pruefung? "aa", "b" oder "beide".

    NUTZER, 16.09.2026: "reicht es nicht, nur den Bereich zu fahren, den wir
    gerade geaendert haben?" Fuer die Rotprobe: ja, und zwar beweisbar. Eine
    Mutation nennt die Pruefung, die rot werden SOLL - und jede Pruefung lebt
    in genau EINER Suite. Die andere kann sie gar nicht enthalten, also
    aendert ihr Weglassen das Urteil ROT/BLIND nicht.

    GEMESSEN: eine Mutation lief vorher ~62 s (aa ~50 s + b ~12 s). Eine
    b-Mutation braucht jetzt ~12 s.

    IM ZWEIFEL BEIDE: ein Name, der weder mit "aa" noch mit "b" anfaengt,
    ist eine kuenftige dritte Suite oder ein Tippfehler. Dann lieber
    gruendlich als schnell - eine Abkuerzung darf nie raten.
    """
    _e = (erwartet or "").strip()
    # EINE PRUEF-NUMMER, KEIN ANFANGSBUCHSTABE. Der erste Anlauf fragte nur
    # `startswith("b")` - und ordnete damit "billige Items werden wirklich
    # unterboten", "build_time kennt die Je-Item-TE" und "beide Preset-Listen
    # nutzen sie" der b-Suite zu. Das sind Textstuecke aus aa-Pruefungen.
    # Die falsche Suite waere gelaufen, die erwartete Pruefung waere nicht
    # dabei gewesen, und die Rotprobe haette BLIND gemeldet fuer etwas, das
    # sauber ROT ist. Gefunden hat das aa359 - deshalb steht es dort.
    # Eine Pruefung heisst "aa358 ..." oder "b7o ..." - Buchstaben, dann
    # ZIFFER. Ein deutsches Wort tut das nie.
    if _re_suite.match(_e):
        return "aa" if _e.startswith("aa") else "b"
    return "beide"


def lauf(erwartet=None):
    # NOTAUSSTIEG JE TESTLAUF (Sitzung 10 von 1200 s angehoben): auf dem
    # Rechner des Nutzers riss die aa-Suite die alte 20-Minuten-Grenze schon
    # bei der ERSTEN Mutation - die Rotprobe brach mit TimeoutExpired ab und
    # hatte damit KEINE einzige Pruefung bewertet. Ursache war das
    # 225-fache Neuparsen in `_fn_src` (dort behoben, aa-Suite jetzt ~7 s
    # statt ~142 s hier bzw. >20 min dort). Der Notausstieg bleibt als
    # Sicherung gegen echte Haenger, aber grosszuegiger - ein einzelner
    # langsamer Lauf soll nicht den ganzen Durchgang mitreissen.
    _NOTAUS = 3600
    _welche = suite_fuer(erwartet)
    r = None
    fehler = []
    if _welche in ("aa", "beide"):
        r = subprocess.run([sys.executable, "test_bestand_herkunft.py"], cwd=TMP,
                           capture_output=True, text=True, timeout=_NOTAUS)
        fehler = [l.strip() for l in r.stdout.splitlines() if "FEHLER" in l]
    # DIE b-SUITE LAEUFT SEIT SITZUNG 8 MIT. Vorher fuhr die Rotprobe NUR
    # test_bestand_herkunft.py - alle 185 Pruefungen aus test_bauplan_aufbau.py
    # hatten damit ueberhaupt keinen Rot-Nachweis, und eine Mutation, die nur
    # dort auffaellt, wurde faelschlich als BLIND gemeldet (so gefunden bei
    # der Bestands-Zeile im Bauplan-Kopf). Kosten: die b-Suite braucht ~2 s
    # gegenueber ~87 s fuer aa, also rund 3 % mehr Laufzeit - fuer 185
    # zusaetzlich abgesicherte Pruefungen ein guter Handel.
    if _welche in ("b", "beide"):
        _umg = dict(os.environ)
        _umg["QT_QPA_PLATFORM"] = "offscreen"
        _umg["PYTHONPATH"] = TMP
        rb = subprocess.run([sys.executable, "test_bauplan_aufbau.py"], cwd=TMP,
                            capture_output=True, text=True, timeout=_NOTAUS,
                            env=_umg)
        fehler += [l.strip() for l in rb.stdout.splitlines() if "FEHLER" in l]
        if rb.returncode != 0 and not [f for f in fehler
                                       if f.startswith("FEHLER: b")]:
            _tb = [l.strip() for l in (rb.stdout + rb.stderr).splitlines()
                   if l.strip()][-1:]
            fehler.append("FEHLER: b-SUITE ABGEBROCHEN - "
                          + (_tb[0] if _tb else "ohne Ausgabe"))
    # ABBRUCH IST NICHT GRUEN (Befund bei Mutation 32): stirbt die Suite
    # unter einer Mutation mit einer Exception, gab es KEINE FEHLER-Zeilen -
    # und die Auswertung meldete faelschlich "BLIND", obwohl die Mutation
    # den Test sehr wohl umwarf. Ein Traceback wird deshalb als eigener
    # Fehler-Eintrag gefuehrt; die letzte Traceback-Zeile macht ihn in der
    # Ausgabe zuordenbar.
    if r is not None and r.returncode != 0 and not fehler:
        _tail = [l.strip() for l in (r.stdout + r.stderr).splitlines()
                 if l.strip()][-1:]
        fehler = ["FEHLER: TESTLAUF ABGEBROCHEN - "
                  + (_tail[0] if _tail else "ohne Ausgabe")]
    return fehler


def nur_anwendbarkeit():
    """SCHNELLMODUS (--check, ~1 s statt ~65 min): prueft NUR, ob jedes
    Mutations-Muster im aktuellen Quelltext noch GENAU EINMAL vorkommt -
    also ob die Rotprobe ueberhaupt noch anwendbar ist. Ersetzt NICHT den
    vollen Lauf (der belegt, dass die Pruefungen rot werden KOENNEN),
    faengt aber die haeufigste Alterung sofort: Code zog um, Mutation
    zeigt ins Leere. Genau so blieben die Mutationen 21+25 nach Sitzung 5
    unbemerkt kaputt, waehrend die Uebergabe noch "41/41" behauptete.
    SITZUNGSSTART: --check reicht. VOR DEM PACKEN: voller Lauf."""
    schlecht = 0
    for i, (name, datei, alt, _neu, _erw) in enumerate(MUTATIONEN):
        try:
            txt = open(os.path.join(SRC, datei), encoding="utf-8").read()
        except OSError as e:
            print(f"  ?? {i} {name}: Datei fehlt ({e})")
            schlecht += 1
            continue
        c = txt.count(alt)
        if c != 1:
            print(f"  ?? {i} {name}: Muster {c}x gefunden")
            schlecht += 1
    print(f"{len(MUTATIONEN) - schlecht}/{len(MUTATIONEN)} Mutationen "
          f"anwendbar (nur Muster-Check, kein Testlauf).")
    return 1 if schlecht else 0


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        return nur_anwendbarkeit()
    schlecht = 0
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(MUTATIONEN)
    gewaehlt = MUTATIONEN[lo:hi]
    for name, datei, alt, neu, erwartet in gewaehlt:
        if os.path.exists(TMP):
            # ignore_errors: Windows loescht keine Datei mit offenem Handle
            # (WinError 32, Sitzung 16). Ein liegengebliebener Temp-Ordner
            # ist harmlos - ein Abbruch der Rotprobe nicht.
            shutil.rmtree(TMP, ignore_errors=True)
        shutil.copytree(SRC, TMP, ignore=_nicht_kopieren)
        pfad = os.path.join(TMP, datei)
        txt = open(pfad, encoding="utf-8").read()
        if txt.count(alt) != 1:
            print(f"  ?? {name}: Muster {txt.count(alt)}x gefunden - Mutation "
                  f"nicht eindeutig anwendbar")
            schlecht += 1
            continue
        open(pfad, "w", encoding="utf-8").write(txt.replace(alt, neu))
        # NUR DIE SUITE, IN DER DIE ERWARTETE PRUEFUNG LEBT (Nutzer-Frage
        # 16.09.2026). Die andere kann sie nicht enthalten - das Urteil
        # bleibt gleich, die Wartezeit faellt weg.
        fehler = lauf(erwartet)
        traf = [f for f in fehler if erwartet in f]
        if traf:
            print(flush=True) or print(f"  ROT  {name}  ({len(fehler)} Fehler, u.a. {traf[0][:70]})")
        else:
            print(f"  BLIND! {name}: erwartete Pruefung blieb gruen. "
                  f"Fehler waren: {fehler[:3]}")
            schlecht += 1
    print(f"\n{len(gewaehlt) - schlecht}/{len(gewaehlt)} Mutationen erkannt.", flush=True)
    return 1 if schlecht else 0


if __name__ == "__main__":
    sys.exit(main())
