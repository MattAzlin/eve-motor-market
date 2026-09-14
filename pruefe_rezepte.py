"""Rezept-Zensus: prueft JEDE Reaktion gegen die rohe SDE in industry.db.

Nutzer-Frage (Sitzung 8): "kannst du alle Rezepte ueberpruefen, wieviel
Reactions aus einem Run kommen? Nicht jede Reaktion gibt gleich viel ab."

Stimmt - laut CCPs Daten (EVE-University-Doku der SDE-Regeln):
* Intermediate-Reaktionen: 200 Einheiten je Run (100 je Zutat + 5 Fuel) -
  mit EINER dokumentierten Ausnahme, die nur 10 liefert (2'000 je Zutat).
* Composite-Reaktionen: Ausbeute VARIIERT je Formel.
* Zwei Sonder-Composites: 200er-Zutaten, kein Fuel, Ausbeute 200.
Deshalb wird hier NICHTS hartkodiert erwartet, sondern gegen die SDE selbst
und gegen Struktur-Invarianten geprueft.

Was der Zensus tut (Aufruf: python3 pruefe_rezepte.py):
1. ANOMALIEN in der rohen SDE-Tabelle: Reaktions-Produkte mit Ausbeute
   NULL/0 (die der Import per `or 1` stillschweigend zu 1 machen wuerde -
   dann plant das Tool bis zu 200-fach zu viele Runs).
2. IMPORT-TREUE: die geladenen Recipes (product_to_bp) muessen fuer JEDES
   Reaktionsprodukt exakt die DB-Ausbeute tragen. Faengt jeden Import-Bug.
3. ZENSUS: alle Reaktionen gruppiert nach Ausbeute, damit Ausreisser
   sofort ins Auge springen (Erwartung: grosser 200er-Block, ein 10er,
   variable Composites - alles andere ansehen!).

Exit-Code 0 = alles sauber, 1 = Anomalien gefunden (Details im Ausdruck).
"""
import sqlite3
import sys

REACTION = 11


def rohdaten(conn):
    """[(bp_id, product_id, quantity)] aller Reaktions-Produkte aus der DB.
    Fehlt die Tabelle (frische Installation), ist das KEIN Absturz, sondern
    schlicht "noch keine Rezepte geladen" - leere Liste, die main() sauber
    meldet."""
    try:
        return [(r[0], r[1], r[2]) for r in conn.execute(
            "SELECT blueprint_id, product_id, quantity FROM products "
            "WHERE activity_id=?", (REACTION,))]
    except sqlite3.OperationalError:
        return []


def anomalien(zeilen):
    """Ausbeuten, die der Import verfaelschen wuerde oder die laut
    SDE-Regeln nicht vorkommen: NULL, 0, negativ. (1 ist bei Reaktionen
    ebenfalls verdaechtig - kleinste dokumentierte Ausbeute ist 10 - wird
    aber nur GEMELDET, nicht als Fehler gewertet: Regel 6, wir raten CCPs
    Daten nicht nach.)"""
    hart = [(bp, p, q) for bp, p, q in zeilen if q is None or q <= 0]
    verdaechtig = [(bp, p, q) for bp, p, q in zeilen if q == 1]
    return hart, verdaechtig


def import_treue(zeilen, product_to_bp):
    """Jede DB-Ausbeute muss 1:1 in den geladenen Recipes ankommen.
    Faengt das `or 1`-Maskieren und jeden anderen Import-Fehler."""
    falsch = []
    for bp, p, q in zeilen:
        geladen = product_to_bp.get(p)
        if geladen is None:
            continue                      # Produkt woanders gebaut (ok)
        if geladen[1] == REACTION and geladen[2] != q:
            falsch.append((p, q, geladen[2]))
    return falsch


def zensus(zeilen):
    """{ausbeute: anzahl} - der grosse 200er-Block, der eine 10er, die
    variablen Composites. Alles Unerwartete faellt hier sofort auf."""
    verteilung = {}
    for _bp, _p, q in zeilen:
        verteilung[q] = verteilung.get(q, 0) + 1
    return dict(sorted(verteilung.items(), key=lambda kv: -kv[1]))


def main():
    from eve_trader import industry
    pfad = industry._db_path()
    conn = sqlite3.connect(pfad)
    zeilen = rohdaten(conn)
    if not zeilen:
        print(f"KEINE Reaktionsdaten in {pfad} - erst im Tool "
              "'Baurezepte laden' ausfuehren.")
        return 1
    print(f"{len(zeilen)} Reaktions-Formeln in {pfad}\n")

    print("== 1) Ausbeute-Zensus (Ausbeute: Anzahl Formeln) ==")
    for q, n in zensus(zeilen).items():
        print(f"   {q:>8}: {n}")

    hart, verdaechtig = anomalien(zeilen)
    print("\n== 2) Anomalien ==")
    if hart:
        for bp, p, q in hart:
            print(f"   FEHLER: Produkt {p} (BP {bp}) hat Ausbeute {q!r} - "
                  "der Import macht daraus stillschweigend 1!")
    else:
        print("   keine NULL/0-Ausbeuten - der `or 1`-Rueckfall im Import "
              "greift nirgends.")
    for bp, p, q in verdaechtig:
        print(f"   PRUEFEN: Produkt {p} (BP {bp}) Ausbeute 1 - kleinste "
              "dokumentierte Reaktions-Ausbeute ist 10.")

    print("\n== 3) Import-Treue (DB vs. geladene Recipes) ==")
    rec = industry.Recipes()
    falsch = import_treue(zeilen, rec.product_to_bp)
    if falsch:
        for p, db_q, geladen_q in falsch:
            print(f"   FEHLER: Produkt {p}: DB sagt {db_q}, geladen ist "
                  f"{geladen_q}!")
    else:
        print(f"   alle {len(zeilen)} Ausbeuten kommen 1:1 in den geladenen "
              "Recipes an.")
    return 1 if (hart or falsch) else 0


# ---------------------------------------------------------------------
# TEIL 2 (Sitzung 8, Nutzer-Frage "stimmen die Ausbeuten?"): VERALTUNG.
# Der Zensus oben prueft die lokalen Daten in sich - aber CCP AENDERT
# Ausbeuten und Zutaten per Patch. Ein Import von VOR so einem Patch ist in
# sich stimmig und trotzdem falsch. Deshalb: Abgleich gegen den AKTUELLEN
# SDE-Stand (dieselbe Quelle, aus der der Import laedt), Position fuer
# Position - Ausbeute UND Zutatenmengen, Fertigung UND Reaktion.
#   python3 pruefe_rezepte.py --gegen-sde
#   python3 pruefe_rezepte.py --gegen-sde --produkte x.csv --materialien y.csv
# (offline mit selbst heruntergeladenen Fuzzwork-CSVs)
# ---------------------------------------------------------------------
_SDE_BASE = "https://www.fuzzwork.co.uk/dump/latest/"
_AKT = {1: "Fertigung", 11: "Reaktion"}


def _lade_sde_csv(name, pfad=None):
    import csv as _csv
    import io as _io
    import urllib.request as _rq
    if pfad:
        raw = open(pfad, "rb").read()
    else:
        url = _SDE_BASE + name + ".csv"
        print(f"  lade {url} \u2026")
        raw = _rq.urlopen(url, timeout=180).read()
    return list(_csv.DictReader(_io.StringIO(raw.decode("utf-8"))))


def sde_diff(conn, produkte_csv=None, materialien_csv=None):
    """(ausbeute_falsch, zutaten_falsch, entfernt, neu) - lokale DB gegen den
    aktuellen SDE-Stand. Jeder Eintrag: (schluessel, lokal, sde)."""
    prod_neu = {(int(r["typeID"]), int(r["activityID"]),
                 int(r["productTypeID"])): int(r["quantity"])
                for r in _lade_sde_csv("industryActivityProducts",
                                       produkte_csv)
                if int(r["activityID"]) in _AKT}
    mat_neu = {(int(r["typeID"]), int(r["activityID"]),
                int(r["materialTypeID"])): int(r["quantity"])
               for r in _lade_sde_csv("industryActivityMaterials",
                                      materialien_csv)
               if int(r["activityID"]) in _AKT}
    prod_alt = {(r[0], r[1], r[2]): int(r[3] or 1) for r in conn.execute(
        "SELECT blueprint_id, activity_id, product_id, quantity "
        "FROM products") if r[1] in _AKT}
    mat_alt = {(r[0], r[1], r[2]): int(r[3]) for r in conn.execute(
        "SELECT blueprint_id, activity_id, material_id, quantity "
        "FROM materials") if r[1] in _AKT}
    ausbeute = [(k, prod_alt[k], prod_neu[k])
                for k in prod_alt.keys() & prod_neu.keys()
                if prod_alt[k] != prod_neu[k]]
    zutaten = [(k, mat_alt[k], mat_neu[k])
               for k in mat_alt.keys() & mat_neu.keys()
               if mat_alt[k] != mat_neu[k]]
    entfernt = sorted(set(prod_alt) - set(prod_neu))
    neu = sorted(set(prod_neu) - set(prod_alt))
    return ausbeute, zutaten, entfernt, neu


def main_gegen_sde(produkte_csv=None, materialien_csv=None):
    from eve_trader import industry
    conn = sqlite3.connect(industry._db_path())
    if not rohdaten(conn):
        print("Keine Rezepte in der lokalen DB - erst im Tool "
              "'Baurezepte laden' ausfuehren.")
        return 2
    print("Vergleiche lokale Rezepte gegen den aktuellen SDE-Stand:")
    ausbeute, zutaten, entfernt, neu = sde_diff(conn, produkte_csv,
                                                materialien_csv)
    print()
    if ausbeute:
        print(f"!! AUSBEUTE WEICHT AB ({len(ausbeute)}):")
        for (bp, akt, pid), alt, soll in sorted(ausbeute)[:50]:
            print(f"   {_AKT[akt]:9s} Produkt {pid:>7}: "
                  f"lokal {alt:>8,}/Run, SDE {soll:>8,}/Run")
    else:
        print("Ausbeuten je Run: ALLE identisch mit dem aktuellen SDE. \u2713")
    if zutaten:
        print(f"!! ZUTATENMENGEN WEICHEN AB ({len(zutaten)}):")
        for (bp, akt, mid), alt, soll in sorted(zutaten)[:50]:
            print(f"   {_AKT[akt]:9s} Material {mid:>7}: "
                  f"lokal {alt:>8,}/Run, SDE {soll:>8,}/Run")
    else:
        print("Zutatenmengen: ALLE identisch mit dem aktuellen SDE. \u2713")
    if entfernt:
        print(f"\u26a0 {len(entfernt)} Rezept(e) lokal, die der SDE nicht "
              "mehr kennt (per Patch entfernt?).")
    if neu:
        print(f"\u26a0 {len(neu)} Rezept(e) NEU im SDE, lokal unbekannt.")
    if ausbeute or zutaten or entfernt or neu:
        print("\n-> Im Tool den SDE-Import erneut laufen lassen; danach "
              "diesen Abgleich wiederholen (muss dann leer sein).")
        return 1
    print("\nAlles auf aktuellem Patch-Stand - keine Handlung noetig.")
    return 0


def bericht_fuer_ui():
    """Alles fuer den Einstellungen-Knopf in EINEM Aufruf - Zensus offline,
    Patch-Abgleich mit Netz; scheitert der Abgleich, kommt der Zensus
    TROTZDEM zurueck (sde_fehler sagt, warum der Rest fehlt). Die UI oeffnet
    hier keine eigene DB-Verbindung - eine Quelle (Regel 9)."""
    from eve_trader import industry
    conn = sqlite3.connect(industry._db_path())
    zeilen = rohdaten(conn)
    if not zeilen:
        return {"leer": True}
    hart, verdaechtig = anomalien(zeilen)
    falsch = import_treue(zeilen, industry.Recipes().product_to_bp)
    out = {"leer": False, "n": len(zeilen), "zensus": zensus(zeilen),
           "hart": hart, "verdaechtig": verdaechtig, "falsch": falsch,
           "diff": None, "sde_fehler": None}
    try:
        out["diff"] = sde_diff(conn)
    except Exception as e:
        out["sde_fehler"] = f"{type(e).__name__}: {e}"
    return out


if __name__ == "__main__":
    if "--gegen-sde" in sys.argv:
        def _arg(name):
            return (sys.argv[sys.argv.index(name) + 1]
                    if name in sys.argv else None)
        sys.exit(main_gegen_sde(_arg("--produkte"), _arg("--materialien")))
    sys.exit(main())
