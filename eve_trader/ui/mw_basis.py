"""Basis-Bausteine der Oberflaeche: ISK-Formatierung, sortierende
Tabellenzelle und die beiden ISK-Eingabefelder.

Ausgelagert in Sitzung 8, damit `mw_bauplan_tabs.py` sie nutzen kann, ohne
`main_window` zu importieren (das waere ein Zirkel-Import - main_window
importiert die Mixins ja selbst).

Die Ruempfe sind WOERTLICH aus main_window.py verschoben, kein Zeichen
geaendert. ACHTUNG beim Aufraeumen: `__lt__`, `textFromValue`,
`valueFromText` und `validate` sehen "nie aufgerufen" aus - sie sind
Qt-Overrides und werden vom Framework gerufen. Nicht loeschen.
"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QDoubleSpinBox, QSpinBox,
                               QTableWidgetItem)

from . import icons


def tab_icon(tabs, widget, text, name):
    """Reiter mit GEZEICHNETEM Symbol statt Emoji im Reitertext.

    Gleiche Bauweise wie `_btn_icon` (Sitzung 9, Knoepfe) und
    `_combo_item` (Auswahllisten): der TEXT bleibt sauber lesbar - wichtig
    fuer Suche, Screenreader und die Prueftexte -, das Symbol kommt aus dem
    eigenen Set und sieht damit auf jedem Betriebssystem gleich aus statt
    je nach Emoji-Font zu variieren.

    Faellt das Symbol aus, bleibt der Reiter voll bedienbar und beschriftet -
    er hat dann eben keins. Der Reiter darf NIE an einem fehlenden Bild
    haengen, deshalb wird er ZUERST angelegt und das Symbol danach gesetzt.

    Gibt den Index des neuen Reiters zurueck.
    """
    _i = tabs.addTab(widget, text)
    try:
        tabs.setTabIcon(_i, icons.icon(name))
    except Exception:
        pass
    return _i


def tab_icon_at(tabs, pos, widget, text, name):
    """Wie `tab_icon`, nur an einer festen POSITION eingefuegt.

    Drei Bauplan-Reiter werden nachtraeglich einsortiert (Blueprints vor
    Materialien vor Runplaner) und liefen deshalb ueber `insertTab` mit
    Emoji im Text. Emojis sehen je nach Betriebssystem-Font anders aus -
    genau dafuer gibt es das eigene Symbol-Set (Sitzung 9).

    Auch hier: Reiter ZUERST anlegen, Symbol danach. Faellt es aus, bleibt
    der Reiter voll bedienbar und beschriftet.
    """
    tabs.insertTab(pos, widget, text)
    try:
        tabs.setTabIcon(pos, icons.icon(name))
    except Exception:
        pass
    return pos


def isk(n, suffix=True):
    if n is None:
        return "—"
    s = f"{round(n):,}".replace(",", "'")
    return s + " ISK" if suffix else s



class NumericItem(QTableWidgetItem):
    """Table cell that sorts by a numeric value but displays formatted text."""
    def __init__(self, text, value):
        super().__init__(text)
        self._value = value if value is not None else float("-inf")

    def __lt__(self, other):
        other_val = getattr(other, "_value", None)
        if other_val is not None:
            return self._value < other_val
        # Zellentyp-Mismatch (z.B. eine normale QTableWidgetItem in derselben
        # Spalte) - NIE super().__lt__() aufrufen: das kann in PySide6 bei
        # gemischten Zelltypen in einer sortierten Spalte unbegrenzt rekursiv
        # zurück in genau dieses __lt__ springen -> Stack overflow/Absturz.
        # Text-Vergleich ist immer sicher (keine Rekursion möglich).
        return self.text() < other.text()


class IskMillionSpin(QDoubleSpinBox):
    """Value is held in MILLIONS of ISK, but displayed human-readably:
    850 → '850M', 1000 → '1B', 1150 → '1,15B'. Accepts typing with M/B too."""
    def textFromValue(self, v):
        if v >= 1000:
            s = f"{v / 1000:.2f}".rstrip("0").rstrip(".").replace(".", ",")
            return f"{s}B"
        return f"{v:.0f}M"

    def valueFromText(self, text):
        t = text.strip().upper().replace(" ", "").replace(",", ".")
        try:
            if t.endswith("B"):
                return float(t[:-1]) * 1000.0
            if t.endswith("M"):
                return float(t[:-1])
            return float(t)
        except ValueError:
            return self.value()

    def validate(self, text, pos):
        from PySide6.QtGui import QValidator
        return (QValidator.Acceptable, text, pos)


class IskGroupedSpin(QSpinBox):
    """Plain-ISK integer spin box with apostrophe thousand separators
    (50000 -> '50'000'), so it stays readable without switching to M/B."""
    def textFromValue(self, v):
        return f"{v:,}".replace(",", "'")

    def _plain(self, text):
        """Angezeigten Text -> reine Ziffernfolge. Muss Prefix UND Suffix
        abraeumen: im Eingabefeld steht immer die volle Anzeige (z.B.
        "445 ISK/m3"), nicht nur die Zahl."""
        t = text or ""
        _p, _s = self.prefix(), self.suffix()
        if _p and t.startswith(_p):
            t = t[len(_p):]
        if _s and t.endswith(_s):
            t = t[:-len(_s)]
        return t.strip().replace("'", "").replace("\u2019", "").replace(" ", "")

    def validate(self, text, pos):
        """MUSSTE ueberschrieben werden (Nutzer: "kann bei Frachtdienst nicht
        mehr als 10 ISK eingeben, springt nach Enter zurueck"). Die Klasse
        SCHREIBT Werte mit Tausender-Apostroph (textFromValue), der geerbte
        Pruefer von QSpinBox kennt dieses Trennzeichen aber nicht und wies
        genau das Format als ungueltig zurueck, das die Box selbst anzeigt -
        eine Zahl ab 1'000 liess sich dadurch gar nicht mehr bearbeiten.
        Zusammen mit dem Suffix im Feld landete jede Eingabe im
        Rueckfall "alten Wert behalten"."""
        from PySide6.QtGui import QValidator
        raw = self._plain(text)
        if raw in ("", "+", "-"):
            return (QValidator.Intermediate, text, pos)   # noch am Tippen
        if not raw.lstrip("+-").isdigit():
            return (QValidator.Invalid, text, pos)
        return ((QValidator.Acceptable
                 if self.minimum() <= int(raw) <= self.maximum()
                 else QValidator.Intermediate), text, pos)

    def valueFromText(self, text):
        try:
            return int(round(float(self._plain(text))))
        except ValueError:
            return self.value()


class MinimizableDialog(QDialog):
    """Plain QDialog zeigt standardmäßig NUR einen Schließen-Button in der
    Titelleiste, kein Minimieren - man kann so ein offenes Bauplan-/Optimierer-/
    Kalender-Fenster nicht kurz wegklicken, ohne es zu schließen. Diese
    Basisklasse erzwingt den Minimieren-Button für ALLE Werkzeug-Dialoge im
    Tool, damit man z.B. kurz ins Spiel wechseln kann, ohne den Bauplan-Dialog
    zu verlieren."""
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        # WICHTIG: KEIN Qt.CustomizeWindowHint (siehe vorheriger Versuch - das
        # hat auf manchen Windows-Systemen zu einem KOMPLETT rahmenlosen
        # Fenster geführt). Aber auch nur Qt.WindowMinimizeButtonHint auf die
        # bestehenden Flags draufzupacken reichte NICHT: der Fenstertyp bleibt
        # dabei Qt.Dialog, und Qt.Dialog-Fenster unterstützen unter Windows
        # das Minimieren strukturell oft gar nicht zuverlässig, egal welche
        # Zusatz-Hints gesetzt sind. Deshalb jetzt der Fenstertyp selbst
        # explizit auf Qt.Window umgestellt (normales Top-Level-Fenster,
        # kein Dialog-Typ mehr) - dafür sind Minimieren/Maximieren/Verschieben
        # von Haus aus vorgesehen.
        flags = self.windowFlags()
        flags &= ~Qt.WindowType_Mask
        flags |= Qt.Window
        flags |= Qt.WindowMinimizeButtonHint | Qt.WindowCloseButtonHint
        self.setWindowFlags(flags)
