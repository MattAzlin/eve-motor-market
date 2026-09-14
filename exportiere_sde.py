"""Erzeugt eine KOMPAKTE Kopie deiner industry.db zum Hochladen.

WOZU: ohne Rezeptdaten kann ich im Container nur mit erfundenen Testrezepten
arbeiten. Damit lassen sich Mechanismen zeigen, aber nie beantworten, was bei
DIR konkret passiert - genau daran sind in Sitzung 14 vier Analysen
gescheitert.

WAS ES TUT: kopiert die Tabellen, die `eve_trader/industry.py` wirklich
liest, in eine neue Datei und komprimiert sie. Deine Original-Datenbank wird
NICHT verändert - nur gelesen.

WAS NICHT DRIN IST: keine Kontodaten, keine Charaktere, keine Orders, keine
Assets, kein Handelsjournal. Die industry.db enthält ohnehin nur die
oeffentliche SDE-Struktur (Rezepte, Gruppen, Kategorien) - dieselben Daten,
die jeder aus dem Static Data Export bekommt.

AUFRUF (im Projektordner, neben main.py):
    python exportiere_sde.py

Danach liegt `sde_kompakt.zip` daneben. Die hochladen.
"""
import os
import sqlite3
import sys
import zipfile


# Genau die Tabellen, aus denen industry.py liest (per "FROM <name>"
# ermittelt, nicht geraten). Fehlt eine, wird sie uebersprungen und
# GEMELDET - lieber eine unvollstaendige Kopie mit Hinweis als eine, die
# vollstaendig aussieht.
TABELLEN = [
    "inv", "dgm", "item_cat", "industry", "group_name", "rigs",
    "products", "activities", "probabilities", "materials",
    "implant_time_bonus", "decryptors", "bp_science_skills",
    "bp_invention_skills",
]


def main():
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from eve_trader import config
        quelle = os.path.join(config.app_data_dir(), "industry.db")
    except Exception as _e:
        print(f"FEHLER: Datenpfad nicht ermittelbar ({_e}).")
        print("Liegt dieses Skript im Projektordner, neben main.py?")
        return 1

    if not os.path.exists(quelle):
        print(f"FEHLER: {quelle} gibt es nicht.")
        print("Starte einmal das Tool und lass es die SDE laden.")
        return 1

    print(f"Quelle : {quelle}")
    print(f"Groesse: {os.path.getsize(quelle) / 1024 / 1024:.1f} MB")

    ziel = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "sde_kompakt.db")
    for _alt in (ziel, ziel + ".zip"):
        if os.path.exists(_alt):
            os.remove(_alt)

    src = sqlite3.connect(f"file:{quelle}?mode=ro", uri=True)
    dst = sqlite3.connect(ziel)
    vorhanden = {r[0] for r in src.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    fehlen, kopiert = [], []
    for t in TABELLEN:
        if t not in vorhanden:
            fehlen.append(t)
            continue
        ddl = src.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (t,)).fetchone()
        if not ddl or not ddl[0]:
            fehlen.append(t)
            continue
        dst.execute(ddl[0])
        spalten = [r[1] for r in src.execute(f"PRAGMA table_info({t})")]
        platz = ",".join("?" * len(spalten))
        n = 0
        for zeile in src.execute(f"SELECT * FROM {t}"):
            dst.execute(f"INSERT INTO {t} VALUES ({platz})", zeile)
            n += 1
        kopiert.append((t, n))
    dst.commit()
    dst.close()
    src.close()

    print("\nKopiert:")
    for t, n in kopiert:
        print(f"  {t:<22} {n:>9,} Zeilen")
    if fehlen:
        print("\nNICHT GEFUNDEN (in deiner DB nicht vorhanden):")
        for t in fehlen:
            print(f"  {t}")
        print("Das ist nicht zwingend ein Fehler - bitte mitteilen.")

    with zipfile.ZipFile(ziel + ".zip", "w", zipfile.ZIP_DEFLATED,
                         compresslevel=9) as z:
        z.write(ziel, "sde_kompakt.db")
    os.remove(ziel)
    _mb = os.path.getsize(ziel + ".zip") / 1024 / 1024
    print(f"\nFERTIG: sde_kompakt.zip ({_mb:.1f} MB)")
    print(f"Liegt hier: {ziel + '.zip'}")
    if _mb > 30:
        print("\nWARNUNG: fuer einen Upload womoeglich zu gross. Dann "
              "Bescheid sagen - es gibt einen schlankeren Weg (nur die "
              "Rezept- und Kategorietabellen).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
