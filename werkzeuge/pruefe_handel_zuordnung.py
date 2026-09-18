"""Prueft, wie viele deiner VERKAEUFE das Tool ueberhaupt einem KAUF zuordnen
kann - und wie viele stillschweigend wegfallen oder gegen ein fremdes Lot
gerechnet werden.

WOZU (Sitzung 16): der Profits-Tab rechnet FIFO. Ein Verkauf ohne passendes
Kauf-Lot wird uebersprungen (`if matched_qty <= 0: continue` in
market.realized_trades), ein TEILWEISE gedecktes Item wird nur zum gedeckten
Teil gezeigt - mit dem Einstand des alten Kaufs. Im Container nachgestellt:

  A) 100 verkauft, nie gekauft            -> 0 Zeilen (unsichtbar)
  B) 10 gekauft, 100 verkauft             -> 1 Zeile: Sold 10, Marge +374,5 %
  C) Charakter A kauft, B verkauft        -> 0 Zeilen
  D) Verkauf vor dem aeltesten Kauf       -> 0 Zeilen

Das Tool KANN nicht wissen, woher ein verkauftes Stueck stammt: ESI liefert
unter /wallet/transactions/ nur Marktgeschaefte. Loot, Industrie-Ausstoss,
Vertraege und Reprocessing-Ertrag hinterlassen dort keine Spur. Dieses Skript
misst, wie gross der Effekt bei DIR ist.

WAS AUSGEGEBEN WIRD:
  * je Item: gekauft, verkauft, davon zugeordnet, davon unzugeordnet
  * die Aufteilung der unzugeordneten Menge in "vor dem ersten Kauf"
    (Fall D - Historie reicht nicht zurueck) und "kein Bestand mehr"
    (Fall B - Loot / selbst gebaut / Vertrag)
  * Items, die ein Charakter verkauft und ein ANDERER gekauft hat (Fall C)
  * Items, die nie gekauft wurden und deshalb nirgends auftauchen (Fall A)

WAS NICHT AUSGEGEBEN WIRD:
  * Client-ID, Zugangsdaten, Token
  * Charakternamen und -IDs (nur als "C1", "C2", ... durchnummeriert)
  * Einstellungen, Orders, Assets, Bauplaene
  * ISK-Kontostand

Item-NAMEN stehen drin - ohne sie kannst du mit dem Ergebnis nichts anfangen.
Es ist reiner Text, oeffne die Datei vor dem Hochladen ruhig einmal.

ES AENDERT NICHTS. Die Datenbank wird SCHREIBGESCHUETZT geoeffnet.

AUFRUF (im Projektordner, neben main.py):
    python pruefe_handel_zuordnung.py

Danach liegt `handel_zuordnung.json` daneben, und auf dem Bildschirm steht
eine Kurzfassung.
"""
import json
import os
import sqlite3
import sys
from collections import defaultdict, deque


def _lade_transaktionen(db):
    """Alle Transaktionen, schreibgeschuetzt gelesen. Reihenfolge wie im
    Produktcode: nach Datum, KAEUFE vor Verkaeufen am selben Tag - sonst
    verbraucht FIFO ein Lot, das an dem Tag erst noch entsteht."""
    uri = "file:" + db.replace("?", "%3f").replace("#", "%23") + "?mode=ro"
    c = sqlite3.connect(uri, uri=True, timeout=30)
    c.row_factory = sqlite3.Row
    try:
        rows = [dict(r) for r in c.execute(
            "SELECT character_id, date, type_id, quantity, unit_price, is_buy "
            "FROM transactions")]
    finally:
        c.close()
    rows.sort(key=lambda x: (x["date"], 0 if x["is_buy"] else 1))
    return rows


def _lade_namen(db):
    uri = "file:" + db.replace("?", "%3f").replace("#", "%23") + "?mode=ro"
    c = sqlite3.connect(uri, uri=True, timeout=30)
    try:
        return {r[0]: r[1] for r in c.execute("SELECT type_id,name FROM type_names")}
    except Exception:
        return {}
    finally:
        c.close()


def _isk(v):
    return f"{v:,.0f}".replace(",", "'")


def _stk(v, breite=0):
    """Stueckzahl mit Hochkomma. EIGENE Funktion, weil ein zeilenweites
    .replace(",", "'") auch die Kommas im TEXT trifft - genau das ist beim
    ersten Testlauf passiert ("vor erstem Kauf' Historie zu kurz")."""
    return f"{v:,}".replace(",", "'").rjust(breite)


def einstufen(a):
    """Ordnet die UNZUGEORDNETE Menge eines Items einer Ursache zu.

    WICHTIG - DIE GRENZE DIESER EINSTUFUNG: sie schaetzt, sie misst nicht.
    Ob ein verkauftes Stueck von einem anderen Charakter kam (Fall C) oder
    selbst gebaut wurde (Fall A), steht NIRGENDS in den Daten. Bester
    verfuegbarer Anhaltspunkt: hat ein ANDERER Charakter von diesem Item
    mehr gekauft als verkauft, koennte der Ueberschuss umgelagert worden
    sein. Mehr als "koennte" ist es nicht.
    (Erste Fassung hat Fall C nur daran erkannt, DASS irgendwer gekauft hat -
    das ueberzaehlt massiv: bei Liquid Ozone kaufen drei Charaktere ein paar
    Stueck, die verkauften 40 Mio kommen aber aus dem Eis-Reprocessing.)"""
    unzug = a["unzug_stk"]
    if unzug <= 0:
        return {}
    ueberschuss = sum(max(0, v["kauf"] - v["verk"]) for v in a["je_char"].values())
    c_menge = min(unzug, ueberschuss)
    rest = unzug - c_menge
    if a["kauf_stk"] == 0:
        rest_fall = "A"                       # niemand hat es je gekauft
    elif a["unzug_vor_erstem_kauf"] > a["unzug_kein_bestand"]:
        rest_fall = "D"                       # Historie reicht nicht zurueck
    else:
        rest_fall = "B"                       # Bestand war alle -> fremde Herkunft
    out = {}
    if c_menge:
        out["C"] = c_menge
    if rest:
        out[rest_fall] = out.get(rest_fall, 0) + rest
    return out


def auswerten(txs):
    """FIFO je (Charakter, Item) - dieselbe Aufteilung wie market.py. Liefert
    je Item die zugeordneten und die unzugeordneten Mengen."""
    lots = defaultdict(deque)          # (cid, tid) -> deque[[menge, preis]]
    monate = defaultdict(lambda: {"zug": 0.0, "unzug": 0.0})
    erster_kauf = {}                   # (cid, tid) -> Datum des ersten Kaufs
    it = defaultdict(lambda: {
        "kauf_stk": 0, "kauf_isk": 0.0,
        "verk_stk": 0, "verk_isk": 0.0,
        "zug_stk": 0, "zug_umsatz": 0.0, "zug_kosten": 0.0,
        "unzug_stk": 0, "unzug_isk": 0.0,
        "unzug_vor_erstem_kauf": 0, "unzug_kein_bestand": 0,
        "chars_kauf": set(), "chars_verk_unzug": set(),
        # JE CHARAKTER die Mengen - ohne sie laesst sich Fall C (ein anderer
        # Charakter hat gekauft) NICHT von Fall A (selbst gebaut/erbeutet)
        # trennen. Die blosse Frage "hat irgendwer das Item mal gekauft"
        # ueberzaehlt C: bei Liquid Ozone kaufen drei Charaktere ein paar
        # Stueck, waehrend die verkauften 40 Mio aus dem Eis-Reprocessing
        # stammen koennen.
        "je_char": defaultdict(lambda: {"kauf": 0, "verk": 0, "unzug": 0}),
    })

    for t in txs:
        cid, tid = t["character_id"], t["type_id"]
        menge = int(t["quantity"] or 0)
        preis = float(t["unit_price"] or 0.0)
        a = it[tid]
        if t["is_buy"]:
            lots[(cid, tid)].append([menge, preis])
            erster_kauf.setdefault((cid, tid), t["date"])
            a["kauf_stk"] += menge
            a["kauf_isk"] += menge * preis
            a["chars_kauf"].add(cid)
            a["je_char"][cid]["kauf"] += menge
            continue

        a["verk_stk"] += menge
        a["verk_isk"] += menge * preis
        a["je_char"][cid]["verk"] += menge
        monat = t["date"][:7]
        offen = menge
        dq = lots[(cid, tid)]
        while offen > 0 and dq:
            lot = dq[0]
            nimm = min(offen, lot[0])
            a["zug_stk"] += nimm
            a["zug_umsatz"] += nimm * preis
            a["zug_kosten"] += nimm * lot[1]
            lot[0] -= nimm
            offen -= nimm
            if lot[0] == 0:
                dq.popleft()
        monate[monat]["zug"] += (menge - offen) * preis
        monate[monat]["unzug"] += offen * preis
        if offen > 0:
            a["unzug_stk"] += offen
            a["unzug_isk"] += offen * preis
            a["chars_verk_unzug"].add(cid)
            a["je_char"][cid]["unzug"] += offen
            # Lag ueberhaupt schon ein Kauf dieses Items bei diesem Charakter
            # vor diesem Verkauf? Wenn nein, reicht die Historie nicht zurueck
            # (Fall D). Wenn ja, kam die Ware von woanders her (Fall B).
            ek = erster_kauf.get((cid, tid))
            if ek is None or ek > t["date"]:
                a["unzug_vor_erstem_kauf"] += offen
            else:
                a["unzug_kein_bestand"] += offen
    return it, monate


def main():
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # Projektwurzel
        from eve_trader import config
    except Exception as _e:
        print(f"FEHLER: eve_trader nicht importierbar ({_e}).")
        print("Liegt dieses Skript im Projektordner, neben main.py?")
        return 1

    db = config.db_path()
    if not os.path.exists(db):
        print(f"FEHLER: {db} gibt es nicht.")
        print("Einmal 'Transaktionen holen' im Charaktere-Tab laufen lassen.")
        return 1

    try:
        txs = _lade_transaktionen(db)
    except Exception as _e:
        print(f"FEHLER: Datenbank nicht lesbar ({_e}).")
        return 1
    if not txs:
        print("Die Transaktions-Tabelle ist leer - nichts zu messen.")
        return 1
    namen = _lade_namen(db)

    chars = sorted({t["character_id"] for t in txs})
    tarnung = {c: f"C{i + 1}" for i, c in enumerate(chars)}
    it, monate = auswerten(txs)

    v_stk = sum(a["verk_stk"] for a in it.values())
    v_isk = sum(a["verk_isk"] for a in it.values())
    z_stk = sum(a["zug_stk"] for a in it.values())
    z_isk = sum(a["zug_umsatz"] for a in it.values())
    u_stk = sum(a["unzug_stk"] for a in it.values())
    u_isk = sum(a["unzug_isk"] for a in it.values())
    u_vor = sum(a["unzug_vor_erstem_kauf"] for a in it.values())
    u_kein = sum(a["unzug_kein_bestand"] for a in it.values())
    anteil = (u_isk / v_isk * 100.0) if v_isk else 0.0

    print("=" * 68)
    print(f"Transaktionen: {_stk(len(txs))}"
          + f"   Zeitraum {txs[0]['date'][:10]} bis {txs[-1]['date'][:10]}"
          + f"   Charaktere: {len(chars)}")
    print("=" * 68)
    print("ZUORDNUNG DER VERKAEUFE")
    print(f"  verkauft gesamt        {_stk(v_stk, 12)} Stk   {_isk(v_isk):>20} ISK")
    print(f"  davon ZUGEORDNET       {_stk(z_stk, 12)} Stk   {_isk(z_isk):>20} ISK"
          + "   <- steht im Profits-Tab")
    print(f"  davon UNZUGEORDNET     {_stk(u_stk, 12)} Stk   {_isk(u_isk):>20} ISK"
          + f"   <- faellt weg ({anteil:.1f} % vom Umsatz)")
    faelle = {"A": [0, 0.0, 0], "B": [0, 0.0, 0], "C": [0, 0.0, 0], "D": [0, 0.0, 0]}
    for a in it.values():
        anteile = einstufen(a)
        if not anteile:
            continue
        stueckpreis = a["unzug_isk"] / a["unzug_stk"] if a["unzug_stk"] else 0.0
        for f, m in anteile.items():
            faelle[f][0] += m
            faelle[f][1] += m * stueckpreis
            faelle[f][2] += 1
    text = {"A": "A nie gekauft (Loot/Bau/Vertrag)  - KEIN Handel",
            "B": "B Bestand war alle, fremde Herkunft",
            "C": "C anderer Charakter hatte Ueberschuss (Schaetzung!)",
            "D": "D Historie reicht nicht zurueck"}
    print("\n  WORAN ES LIEGT (die unzugeordneten ISK nach Ursache)")
    for f in ("A", "C", "D", "B"):
        m, isk_, n = faelle[f]
        q = (isk_ / u_isk * 100.0) if u_isk else 0.0
        print(f"    {text[f]:<52}{_isk(isk_):>18} ISK ({q:>5.1f} %)")

    if monate:
        print("\n  JE MONAT (faellt der unzugeordnete Anteil mit laengerer Historie?)")
        for m in sorted(monate):
            z, u = monate[m]["zug"], monate[m]["unzug"]
            q = (u / (z + u) * 100.0) if (z + u) else 0.0
            print(f"    {m}   verkauft {_isk(z + u):>18} ISK   "
                  f"davon unzugeordnet {q:>5.1f} %")

    zeilen = []
    for tid, a in it.items():
        marge = ((a["zug_umsatz"] - a["zug_kosten"]) / a["zug_kosten"] * 100.0
                 if a["zug_kosten"] > 0 else None)
        fall_c = bool(a["chars_verk_unzug"]
                      and (a["chars_kauf"] - a["chars_verk_unzug"]))
        zeilen.append({
            "type_id": tid,
            "name": namen.get(tid, f"#{tid}"),
            "kauf_stk": a["kauf_stk"], "kauf_isk": round(a["kauf_isk"], 2),
            "verk_stk": a["verk_stk"], "verk_isk": round(a["verk_isk"], 2),
            "zugeordnet_stk": a["zug_stk"],
            "zugeordnet_umsatz": round(a["zug_umsatz"], 2),
            "zugeordnet_kosten": round(a["zug_kosten"], 2),
            "brutto_marge_pct": (round(marge, 1) if marge is not None else None),
            "unzugeordnet_stk": a["unzug_stk"],
            "unzugeordnet_isk": round(a["unzug_isk"], 2),
            "unzug_vor_erstem_kauf_stk": a["unzug_vor_erstem_kauf"],
            "unzug_kein_bestand_stk": a["unzug_kein_bestand"],
            "nie_gekauft": a["kauf_stk"] == 0 and a["verk_stk"] > 0,
            "fall_c_charakteruebergreifend": fall_c,
            "einstufung": einstufen(a),
            "je_charakter": {tarnung[c]: dict(v) for c, v in a["je_char"].items()},
            "chars_kauf": sorted(tarnung[c] for c in a["chars_kauf"]),
            "chars_verk_unzugeordnet": sorted(
                tarnung[c] for c in a["chars_verk_unzug"]),
        })
    zeilen.sort(key=lambda r: r["unzugeordnet_isk"], reverse=True)

    top = [r for r in zeilen if r["unzugeordnet_stk"] > 0][:25]
    if top:
        print("\nDIE GROESSTEN UNZUGEORDNETEN POSTEN")
        print(f"  {'Item':<38}{'unzug. Stk':>12}{'unzug. ISK':>18}  Fall")
        for r in top:
            e = r.get("einstufung") or {}
            fall = "+".join(f"{k}" for k, _ in
                            sorted(e.items(), key=lambda kv: -kv[1])) or "?"
            print(f"  {r['name'][:37]:<38}{_stk(r['unzugeordnet_stk'], 12)}"
                  + f"{_isk(r['unzugeordnet_isk']):>18}  {fall}")

    verdacht = [r for r in zeilen
                if r["brutto_marge_pct"] is not None
                and abs(r["brutto_marge_pct"]) >= 100.0
                and r["zugeordnet_stk"] > 0]
    if verdacht:
        verdacht.sort(key=lambda r: abs(r["brutto_marge_pct"]), reverse=True)
        print("\nVERDACHT AUF FREMDES LOT (Brutto-Marge ueber 100 % - beim reinen")
        print("Handel ungewoehnlich, typisch wenn ein alter Kauf gegen ein")
        print("spaeter selbst gebautes oder erbeutetes Stueck gerechnet wird)")
        for r in verdacht[:15]:
            print(f"  {r['name'][:37]:<38}{_stk(r['zugeordnet_stk'], 10)} Stk"
                  + f"{r['brutto_marge_pct']:>10.1f} %")

    ziel = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "berichte", "handel_zuordnung.json")
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump({
            "transaktionen": len(txs),
            "von": txs[0]["date"][:10], "bis": txs[-1]["date"][:10],
            "charaktere": len(chars),
            "summe": {
                "verkauft_stk": v_stk, "verkauft_isk": round(v_isk, 2),
                "zugeordnet_stk": z_stk, "zugeordnet_umsatz": round(z_isk, 2),
                "unzugeordnet_stk": u_stk, "unzugeordnet_isk": round(u_isk, 2),
                "unzug_vor_erstem_kauf_stk": u_vor,
                "unzug_kein_bestand_stk": u_kein,
                "unzugeordnet_anteil_pct": round(anteil, 2),
            },
            "je_monat": {m: {"zugeordnet_isk": round(v["zug"], 2),
                             "unzugeordnet_isk": round(v["unzug"], 2)}
                         for m, v in sorted(monate.items())},
            "items": zeilen,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nGeschrieben: {ziel}")
    print("Diese Datei kannst du mir schicken.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
