"""Erzeugt eve_trader/ui/assets/logo.ico aus assets/logo.png.

WARUM EIN SKRIPT UND KEINE VON HAND ANGELEGTE .ico:
Die Bildquelle ist logo.png - dieselbe Datei, aus der das Programm sein
Fenster- und Sidebar-Symbol nimmt (icons.logo_pixmap). Eine daneben
gepflegte .ico waere eine ZWEITE Wahrheit: tauscht jemand das Logo aus,
zeigte die EXE weiter das alte Bild, und es faellt nicht auf, weil das
Symbol IM Programm ja stimmt. build.bat ruft dieses Skript deshalb VOR
PyInstaller auf. Die .ico ist ein Erzeugnis, kein gepflegter Bestand.

LOGO AUSTAUSCHEN heisst also: NUR eve_trader/ui/assets/logo.png ersetzen.
Alles andere zieht beim naechsten Bau von selbst nach.

Aufruf:  python mache_icon.py

KEINE ZUSAETZLICHE ABHAENGIGKEIT: die erste Fassung schrieb die .ico mit
Pillow. Pillow steht aber NICHT in requirements.txt - in der frisch
angelegten venv fehlte es, der Bau brach an dieser Stelle ab, und in dist
lag gar nichts (Nutzer-Befund Sitzung 11). Das ICO-Format ist einfach genug,
um es hier selbst zu schreiben; die Einzelbilder liefert Qt, das ohnehin
gebraucht wird.
"""
import os
import struct
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Windows waehlt je nach Ort eine andere Groesse: Taskleiste 32, Titelleiste
# 16, Alt-Tab 48, grosse Kacheln bis 256. Fehlt eine, skaliert Windows die
# naechstbeste hoch und das Ergebnis ist unscharf.
GROESSEN = (16, 20, 24, 32, 48, 64, 128, 256)

# AB DIESER KANTENLAENGE wird PNG benutzt, darunter das klassische DIB.
# 256 als DIB waere unnoetig gross (256 KB je Bild); kleine Groessen als
# PNG zeigt der Explorer nicht zuverlaessig an.
PNG_AB = 256

ZIEL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    "eve_trader", "ui", "assets", "logo.ico")


def dib_daten(breite, hoehe, bgra_zeilen):
    """Ein Einzelbild im klassischen DIB-Format (wie in .ico ueblich).

    WARUM NICHT UEBERALL PNG: seit Vista DARF ein Symbol PNG-komprimiert
    sein, aber der Explorer zeigt bei den KLEINEN Groessen dann gern das
    Standardsymbol statt des Bildes. Verbreitete Praxis - und die, die hier
    nach dem Nutzer-Befund "kein Icon" umgesetzt wurde: PNG nur fuer 256,
    darunter DIB.

    Aufbau: BITMAPINFOHEADER (40 Byte, HOEHE DOPPELT - das Format zaehlt
    Farb- und Maskenteil zusammen), dann die Farbwerte BGRA von UNTEN nach
    oben, dann die 1-Bit-Maske (bei 32 Bit mit Alpha komplett 0).
    """
    kopf = struct.pack("<IiiHHIIiiII", 40, breite, hoehe * 2, 1, 32, 0,
                       len(bgra_zeilen) * breite * 4, 0, 0, 0, 0)
    farbe = b"".join(reversed(bgra_zeilen))
    # Maskenzeilen auf 4 Byte aufgefuellt, Inhalt 0 (Alpha regelt alles).
    maske_zeile = b"\x00" * (((breite + 31) // 32) * 4)
    return kopf + farbe + maske_zeile * hoehe


def schreibe_ico(png_bilder, ziel):
    """Mehrere PNG-Bilder in EINE .ico-Datei packen.

    Aufbau (seit Windows Vista duerfen die Einzelbilder PNG sein):
      ICONDIR       6 Bytes: reserviert(0), Typ(1=Symbol), Anzahl
      ICONDIRENTRY  16 Bytes je Bild: Breite, Hoehe, Farben(0), reserviert,
                    Ebenen(1), Bittiefe(32), Laenge, Versatz
      danach die Bilddaten hintereinander.
    Breite und Hoehe stehen in EINEM Byte - 256 wird deshalb als 0
    geschrieben, so verlangt es das Format.
    """
    kopf = struct.pack("<HHH", 0, 1, len(png_bilder))
    versatz = len(kopf) + 16 * len(png_bilder)
    eintraege = b""
    daten = b""
    for groesse, roh in png_bilder:
        eintraege += struct.pack(
            "<BBBBHHII",
            0 if groesse >= 256 else groesse,
            0 if groesse >= 256 else groesse,
            0, 0, 1, 32, len(roh), versatz)
        daten += roh
        versatz += len(roh)
    with open(ziel, "wb") as fh:
        fh.write(kopf + eintraege + daten)


def main():
    import tempfile
    from PySide6.QtWidgets import QApplication

    _app = QApplication.instance() or QApplication([])
    from eve_trader.ui import icons

    # ZWISCHENDATEIEN statt Speicherpuffer: der Weg ueber QBuffer stuerzt
    # in manchen Qt-Umgebungen mit einem Speicherzugriffsfehler ab (im
    # Entwicklungscontainer reproduzierbar). Eine Temp-Datei tut dasselbe
    # und ist unempfindlich.
    bilder = []
    with tempfile.TemporaryDirectory() as _tmp:
        for g in GROESSEN:
            _pm = icons.logo_pixmap(g)
            if g >= PNG_AB:
                _pfad = os.path.join(_tmp, f"logo_{g}.png")
                if not _pm.save(_pfad, "PNG"):
                    raise RuntimeError(f"Konnte {g}x{g} nicht schreiben")
                with open(_pfad, "rb") as fh:
                    bilder.append((g, fh.read()))
                continue
            _img = _pm.toImage().convertToFormat(
                _pm.toImage().Format.Format_ARGB32)
            _zeilen = []
            for _y in range(g):
                _z = bytearray()
                for _x in range(g):
                    _c = _img.pixelColor(_x, _y)
                    _z += bytes((_c.blue(), _c.green(), _c.red(), _c.alpha()))
                _zeilen.append(bytes(_z))
            bilder.append((g, dib_daten(g, g, _zeilen)))

    os.makedirs(os.path.dirname(ZIEL), exist_ok=True)
    schreibe_ico(bilder, ZIEL)
    print(f"logo.ico geschrieben: {ZIEL} ({os.path.getsize(ZIEL)} Bytes, "
          f"{len(GROESSEN)} Groessen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
