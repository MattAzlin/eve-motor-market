"""Preisverläufe für EINEN Hub vollständig nachladen.

WARUM ES DAS BRAUCHT (Nutzer-Befund Sitzung 11): auf einem frisch
installierten Rechner fand der Daytrade-Scanner fast nichts - "0 Treffer,
722 analysiert, 562 nicht beidseitig täglich". Auf dem Entwicklungsrechner
dagegen 600 Treffer aus 3'775 analysierten Items.

Der Unterschied ist NICHT der Markt-Scan (der holt alle Orders in einer
Anfrage), sondern der PREISVERLAUF: Tages-Hoch, -Tief und Volumen je Item.
Den drosselt CCP hart, deshalb holt ein normaler Deals-Lauf höchstens
`max_new_history` (350) neue Verläufe. Bei ~19'000 Items im Hub braucht es
so rund fünfzig Läufe - und zwischen zwei Klicks sieht man nichts.

WAS DIESES MODUL ANDERS MACHT: es läuft EINMAL durch, im Hintergrund, mit
Fortschritt und jederzeit abbrechbar. Jeder geholte Verlauf ist sofort in
der Datenbank - ein Abbruch verliert also nichts, und der nächste Lauf
macht dort weiter.

DIE LIQUIDESTEN ZUERST: sonst wartet man bis zum Ende, bevor die
Trefferliste brauchbar wird. So sind nach den ersten Minuten schon die
Items da, mit denen man tatsächlich handelt.
"""

import time

from . import scanner, store

# DIESELBE ALTERSGRENZE WIE DER SCANNER (scanner._CACHE_ANALYZE_MAX_AGE_H,
# 7 Tage). Das ist keine Feinheit, sondern der Unterschied zwischen einer
# richtigen und einer falschen Aussage:
#
# Die erste Fassung fragte mit 24 Stunden. Auf dem Entwicklungsrechner des
# Nutzers - Monate an gesammelter Historie - meldete sie deshalb "1'451 von
# 18'780" und bot einen Sammellauf an, obwohl der Scanner dort laengst
# 3'775 Items analysiert. Sie zaehlte alles, was aelter als einen Tag war,
# als "fehlt", waehrend der Scanner es problemlos benutzt.
#
# Wer die Abdeckung meldet, muss dieselbe Grenze anlegen wie der, der die
# Daten benutzt. Sonst ist die Zahl eine Behauptung ueber etwas anderes.
ANALYSE_ALTER_H = scanner._CACHE_ANALYZE_MAX_AGE_H


def fehlende_items(snapshot, region, max_age_h=ANALYSE_ALTER_H):
    """type_ids aus dem Schnappschuss, deren Verlauf FEHLT - liquideste
    zuerst.

    Sortiert nach der angebotenen Menge: das ist der beste Anhaltspunkt
    dafür, dass ein Item überhaupt gehandelt wird, und er steht schon im
    Schnappschuss (kostet keinen Abruf).
    """
    try:
        da = store.fresh_history_type_ids(region, max_age_h)
    except Exception:
        da = set()                      # DB-Problem -> wie "nichts gecacht"
    offen = [s for s in snapshot if s.get("type_id") not in da]
    offen.sort(key=lambda s: (s.get("sell_qty") or 0) + (s.get("buy_qty") or 0),
               reverse=True)
    return [s["type_id"] for s in offen]


def abdeckung(snapshot, region, max_age_h=ANALYSE_ALTER_H):
    """(mit Verlauf, insgesamt) - für die Frage an den Nutzer."""
    gesamt = len({s.get("type_id") for s in snapshot if s.get("type_id")})
    try:
        da = store.fresh_history_type_ids(region, max_age_h)
    except Exception:
        return (0, gesamt)
    return (len({s["type_id"] for s in snapshot
                 if s.get("type_id") in da}), gesamt)


def lade_verlaeufe(type_ids, region, fortschritt=None, abbrechen=None,
                   max_age_h=ANALYSE_ALTER_H):
    """Holt die Verläufe der Reihe nach. Gibt eine Zusammenfassung zurück.

    `fortschritt(i, gesamt, sekunden_rest)` wird laufend gerufen -
    `sekunden_rest` ist ERST NACH den ersten Abrufen gesetzt (vorher None):
    eine Restzeit vor der ersten Messung wäre geraten, und geraten heisst
    hier: falsch. Die Dauer haengt an CCPs Drosselung und am Netz des
    Nutzers, nicht an etwas, das man vorher wissen koennte.

    `abbrechen()` wird vor jedem Item gefragt. Abbrechen ist FOLGENLOS:
    jeder Verlauf liegt bereits einzeln in der Datenbank.
    """
    gesamt = len(type_ids)
    start = time.time()
    geholt = leer = fehler = 0
    gedrosselt = False
    for i, tid in enumerate(type_ids):
        if abbrechen is not None and abbrechen():
            break
        try:
            rows = scanner.history_cached(tid, region, max_age_h=max_age_h)
            if rows:
                geholt += 1
            else:
                leer += 1               # Item ohne Handel - auch das ist Wissen
        except Exception as e:
            # RateLimited kommt als eigene Klasse aus esi; sie hier NICHT
            # weiterwerfen, sonst reisst ein einzelner Drosselungs-Treffer
            # den ganzen Lauf ab und alles Bisherige sieht wie ein
            # Fehlschlag aus (es ist aber laengst gespeichert).
            if type(e).__name__ == "RateLimited":
                gedrosselt = True
                break
            fehler += 1
        if fortschritt is not None:
            _fertig = i + 1
            _rest = None
            # Erst ab 25 Abrufen schaetzen - davor schwankt der Mittelwert
            # so stark, dass die Anzeige hin und her springt.
            if _fertig >= 25:
                _je = (time.time() - start) / _fertig
                _rest = _je * (gesamt - _fertig)
            fortschritt(_fertig, gesamt, _rest)
    return {"geholt": geholt, "leer": leer, "fehler": fehler,
            "gedrosselt": gedrosselt,
            "dauer": time.time() - start}
