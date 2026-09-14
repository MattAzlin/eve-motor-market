"""Einrichtung beim ERSTEN Start - drei Schritte, blockierend.

NUTZER (Sitzung 16, vor der Github-Welle): "so dass das Tool erstmal
ausgegraut ist oder im Ladezustand, dafuer kommt ein Installations-Popup
fuer diese wichtigen Daten, ohne es herunterzuladen kommt man nicht weiter."

WARUM UEBERHAUPT: bis hierher feuerten beim ersten Start DREI einzelne
Dialoge kurz nacheinander (kein Charakter / Rezepte / Preisverlaeufe) und
legten sich uebereinander. Ein Fremder sah einen Stapel Fenster und wusste
nicht, was zuerst zu tun ist - und wer die 140-MB-Frage wegklickte, hielt
den Bauplan-Teil danach fuer kaputt.

DIE DREI SCHRITTE SIND NICHT GLEICHARTIG:
  1. Charakter verlinken - eine ANMELDUNG im Browser. Kein Fortschritt
     moeglich, es wartet auf den Menschen. Muss ZUERST kommen: ohne Zugriff
     sieht das Werkzeug weder Assets noch Blaupausen.
  2. Rezeptdaten  - 140 MB Download, Fortschritt in Prozent.
  3. Preisverlaeufe - viele ESI-Abrufe, Fortschritt in Stueck.

Schritt 2 und 3 laufen von selbst; 3 darf uebersprungen werden (es laedt
sonst ohnehin im Hintergrund nach). 1 und 2 nicht - ohne sie ist das
Werkzeug leer.

KEINE SACKGASSE (Regel 3): wer offline ist oder es sich anders ueberlegt,
kommt ueber "Beenden" heraus - das Fenster schliesst das Programm, statt
den Nutzer festzuhalten. Beim naechsten Start faengt es wieder an.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QProgressBar,
                               QPushButton, QVBoxLayout, QWidget)

from ..sprache import t
from . import icons, theme


class _Schritt(QWidget):
    """Eine Zeile: Symbol, Titel, Zustandstext, Balken, Knopf."""

    def __init__(self, nummer, titel, erklaerung, knopftext=None):
        super().__init__()
        self._fertig = False
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 10)
        v.setSpacing(4)

        kopf = QHBoxLayout()
        self.marke = QLabel(str(nummer) + ".")
        self.marke.setFixedWidth(22)
        self.marke.setStyleSheet(f"color:{theme.MUTED}; font-weight:700;")
        kopf.addWidget(self.marke)

        self.titel = QLabel(titel)
        self.titel.setStyleSheet("font-size:13px; font-weight:700;")
        kopf.addWidget(self.titel)
        kopf.addStretch()

        self.knopf = QPushButton(knopftext or "")
        self.knopf.setVisible(bool(knopftext))
        if knopftext:
            self.knopf.setObjectName("Primary")
        kopf.addWidget(self.knopf)
        v.addLayout(kopf)

        self.zeile = QLabel(erklaerung)
        self.zeile.setWordWrap(True)
        self.zeile.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        self.zeile.setContentsMargins(22, 0, 0, 0)
        v.addWidget(self.zeile)

        self.balken = QProgressBar()
        self.balken.setTextVisible(True)
        self.balken.setVisible(False)
        self.balken.setContentsMargins(22, 0, 0, 0)
        v.addWidget(self.balken)

    def laeuft(self, text=""):
        self.balken.setVisible(True)
        if text:
            self.zeile.setText(text)
        self.marke.setStyleSheet(f"color:{theme.CYAN}; font-weight:700;")

    def fortschritt(self, getan, gesamt):
        """getan/gesamt in MB. Drei Zustaende (Sitzung 17):
        gesamt > 0  -> Prozent; gesamt 0 -> Groesse unbekannt, Laufband mit
        MB-Zahl; getan < 0 -> Entpacken/Einlesen, Laufband mit Text."""
        self.balken.setVisible(True)
        getan, gesamt = int(getan), int(gesamt)
        if getan < 0:
            self.balken.setRange(0, 0)                 # Laufband
            self.zeile.setText(t("Unpacking and importing \u2026"))
        elif gesamt > 0:
            self.balken.setRange(0, gesamt)
            self.balken.setValue(min(getan, gesamt))
            self.zeile.setText(t("Downloading \u2026 {n} of {total} MB").format(
                n=getan, total=gesamt))
        else:
            self.balken.setRange(0, 0)                 # Groesse unbekannt
            self.zeile.setText(t("Downloading \u2026 {n} MB").format(n=getan))

    def fertig(self, text):
        self._fertig = True
        self.balken.setVisible(False)
        self.knopf.setVisible(False)
        self.zeile.setText(text)
        self.zeile.setStyleSheet(f"color:{theme.GREEN}; font-size:11px;")
        self.marke.setPixmap(icons.pixmap("check", farbe=theme.GREEN,
                                          groesse=16))

    def fehler(self, text):
        self.balken.setVisible(False)
        self.zeile.setText(text)
        self.zeile.setStyleSheet(f"color:{theme.RED}; font-size:11px;")


class ErstEinrichtung(QDialog):
    """Blockierendes Fenster: erst einrichten, dann arbeiten."""

    def __init__(self, fenster, auto=True):
        """`auto=False` baut das Fenster, ohne die Kette anzustossen.

        WARUM DER SCHALTER (Sitzung 16): der Konstruktor stiess bisher
        selbst `_pruefe_stand()` an - und damit im Testlauf einen echten
        140-MB-Download. Ein Fenster, das beim BAUEN schon Daten holt, ist
        auch sonst schwer zu handhaben; wer es nur ansehen will, soll das
        koennen.
        """
        super().__init__(fenster)
        self._mw = fenster
        self._abgeschlossen = False
        self.setWindowTitle(t("Setting up EVE Motor Market"))
        self.setModal(True)
        # KEIN Schliessen-Kreuz: der Weg hinaus ist "Beenden" - das ist
        # ehrlicher als ein Kreuz, hinter dem ein halb eingerichtetes
        # Werkzeug steht.
        self.setWindowFlag(Qt.WindowCloseButtonHint, False)
        self.setMinimumWidth(560)

        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 16)

        kopf = QLabel(t("One-time setup"))
        kopf.setStyleSheet(f"color:{theme.CYAN}; font-size:15px; "
                           f"font-weight:800;")
        v.addWidget(kopf)
        unter = QLabel(t("Without this data the tool stays empty. It takes a "
                         "few minutes - you can leave the window open."))
        unter.setWordWrap(True)
        unter.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        v.addWidget(unter)
        v.addSpacing(12)

        self.s1 = _Schritt(1, t("Link character"),
                           t("Opens your browser. Log in with EVE and confirm "
                             "the access."),
                           knopftext=t("Link character"))
        self.s2 = _Schritt(2, t("Recipe data"),
                           t("About 140 MB, once. Needed for every build "
                             "plan."))
        self.s3 = _Schritt(3, t("Price histories"),
                           t("For the deal lists. Can also run later in the "
                             "background."))
        for s in (self.s1, self.s2, self.s3):
            v.addWidget(s)

        v.addStretch()
        unten = QHBoxLayout()
        self.hinweis = QLabel("")
        self.hinweis.setWordWrap(True)
        self.hinweis.setStyleSheet(f"color:{theme.MUTED}; font-size:11px;")
        unten.addWidget(self.hinweis, 1)
        self.beenden_btn = QPushButton(t("Quit"))
        self.beenden_btn.setToolTip(t(
            "Closes the program. The setup starts again next time."))
        unten.addWidget(self.beenden_btn)
        self.weiter_btn = QPushButton(t("Start"))
        self.weiter_btn.setObjectName("Primary")
        self.weiter_btn.setEnabled(False)
        unten.addWidget(self.weiter_btn)
        v.addLayout(unten)

        self.s1.knopf.clicked.connect(self._schritt1)
        self.beenden_btn.clicked.connect(self._beenden)
        self.weiter_btn.clicked.connect(self.accept)
        if auto:
            QTimer.singleShot(0, self._pruefe_stand)

    # ---- Ablauf ---------------------------------------------------------
    def _pruefe_stand(self):
        """Was ist schon da? Erledigte Schritte werden uebersprungen.

        Wer die Einrichtung beim letzten Mal beendet hat, faengt nicht von
        vorn an - das waere Strafe fuer einen Abbruch.
        """
        from .. import industry, store
        if store.list_characters():
            self.s1.fertig(t("linked \u2713"))
            if industry.sde_ready():
                self.s2.fertig(t("loaded \u2713"))
                self._schritt3()
            else:
                self._schritt2()

    def _schritt1(self):
        self.s1.knopf.setEnabled(False)
        self.s1.laeuft(t("Waiting for the login in your browser \u2026"))
        try:
            self._mw.link_character()
        except Exception as e:                       # pragma: no cover
            self.s1.fehler(t("Login failed: ") + str(e))
            self.s1.knopf.setEnabled(True)
            return
        QTimer.singleShot(1200, self._nach_schritt1)

    def _nach_schritt1(self):
        from .. import store
        if store.list_characters():
            self.s1.fertig(t("linked \u2713"))
            self._schritt2()
        else:
            self.s1.knopf.setEnabled(True)
            self.s1.fehler(t("No character linked yet - please try again."))

    def _schritt2(self):
        from .. import industry
        from ..workers import Worker
        if industry.sde_ready():
            self.s2.fertig(t("loaded \u2713"))
            self._schritt3()
            return
        self.s2.laeuft(t("Downloading \u2026"))
        self._stand2 = (0, 1)

        def job(progress=None):
            def _fort(getan, gesamt):
                self._stand2 = (getan, gesamt)
            return industry.download_sde(progress=_fort)

        def done(_res):
            self._takt.stop()
            self.s2.fertig(t("loaded \u2713"))
            self._schritt3()

        def fail(msg):
            self._takt.stop()
            self.s2.fehler(t("Download failed: ") + str(msg))
            self.hinweis.setText(t(
                "Check your internet connection. \u201eQuit\u201c closes the "
                "program; the setup starts again next time."))

        self._takt = QTimer(self)
        self._takt.timeout.connect(
            lambda: self.s2.fortschritt(*self._stand2))
        self._takt.start(200)
        self._w2 = Worker(job)
        self._w2.done.connect(done)
        self._w2.failed.connect(fail)
        self._w2.start()

    def _schritt3(self):
        """Preisverlaeufe - der EINZIGE Schritt, der uebersprungen werden
        darf: sie laden sonst im Hintergrund nach, und ohne sie ist das
        Werkzeug benutzbar (die Deal-Listen fuellen sich eben spaeter)."""
        self.s3.zeile.setText(t("Runs in the background once you start."))
        self.s3.fertig(t("will run in the background \u2713"))
        self._fertig_machen()

    def _fertig_machen(self):
        self._abgeschlossen = True
        self.weiter_btn.setEnabled(True)
        self.hinweis.setText(t("Everything ready."))

    def _beenden(self):
        from PySide6.QtWidgets import QApplication
        self.reject()
        QApplication.quit()

    def reject(self):
        """Esc darf nicht heimlich durchlassen."""
        if self._abgeschlossen:
            super().reject()
