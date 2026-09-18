"""Exportiert NUR die Reservierungs-Daten deiner gespeicherten Baupläne.

WOZU (Sitzung 14): du bleibst bei der Einschaetzung, dass mit der
Reservierung etwas nicht stimmt. Meine Tests liefen mit ERFUNDENEN Plaenen
und zeigten nichts - das schliesst einen Fehler bei DIR nicht aus. Mit deinen
echten Zahlen laesst sich nachrechnen, was jeder Plan reserviert, was er
davon sieht, und ob die mitlaufende Abbuchung stimmt.

WAS EXPORTIERT WIRD (nichts anderes):
  * Plan-ID (Speicherzeitpunkt), Label, Zielprodukt-ID und Menge
  * ob das Schloss (Reservierung) gesetzt ist
  * die reservierten Mengen je Material-ID
  * ob der Plan eingefroren ist, und die Zeitstempel der Haken
  * Anzahl der Zuteilungen im Runplaner

WAS NICHT EXPORTIERT WIRD:
  * Client-ID, Zugangsdaten, Token
  * Charakternamen und -IDs (nur als ANZAHL)
  * Handelsjournal, Orders, Assets, Einstellungen aller Art
  * Item-NAMEN (nur IDs - die sind oeffentliche SDE-Daten)

ES AENDERT NICHTS. Nur lesen.

AUFRUF (im Projektordner, neben main.py):
    python exportiere_reservierungen.py

Danach liegt `reservierungen.json` daneben. Vor dem Hochladen ruhig
oeffnen und durchsehen - es ist reiner Text.
"""
import json
import os
import sys


def main():
    try:
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # Projektwurzel
        from eve_trader import config
    except Exception as _e:
        print(f"FEHLER: eve_trader nicht importierbar ({_e}).")
        print("Liegt dieses Skript im Projektordner, neben main.py?")
        return 1

    pfad = os.path.join(config.app_data_dir(), "settings.json")
    if not os.path.exists(pfad):
        print(f"FEHLER: {pfad} gibt es nicht.")
        return 1
    try:
        with open(pfad, encoding="utf-8") as f:
            s = json.load(f)
    except Exception as _e:
        print(f"FEHLER: settings.json nicht lesbar ({_e}).")
        return 1

    plaene = s.get("bau_saved_plans") or []
    print(f"Gefundene Baupläne: {len(plaene)}")
    raus = []
    for p in plaene:
        fz = p.get("frozen") or {}
        # `checked_runplan_ts` sind Zeitstempel je Haken-Schluessel. Die
        # SCHLUESSEL enthalten Charakter-IDs - deshalb nur die ANZAHL und der
        # aelteste/juengste Zeitpunkt, nicht die Schluessel selbst.
        _ts = p.get("checked_runplan_ts") or {}
        _tsv = [v for v in _ts.values() if isinstance(v, (int, float))]
        raus.append({
            "id": p.get("id"),
            "label": p.get("label") or p.get("item_name"),
            "type_id": p.get("type_id"),
            "qty": p.get("qty"),
            "reserve": bool(p.get("reserve")),
            "reserve_map": {str(k): v
                            for k, v in (p.get("reserve_map") or {}).items()},
            "eingefroren": bool(fz),
            "frozen_ts": fz.get("ts"),
            "hat_plan_snapshot": bool(fz.get("plan_snapshot")),
            "stock_seen_ts": fz.get("stock_seen_ts"),
            "anzahl_haken": len(_ts),
            "haken_von": min(_tsv) if _tsv else None,
            "haken_bis": max(_tsv) if _tsv else None,
            "anzahl_zuteilungen": len(p.get("assignments") or []),
            "done_manual": bool(p.get("done_manual")),
        })
        _n = len(raus[-1]["reserve_map"])
        _schloss = "🔒" if raus[-1]["reserve"] else "  "
        _fr = "eingefroren" if raus[-1]["eingefroren"] else ""
        print(f"  {_schloss} id={p.get('id')}  "
              f"{str(raus[-1]['label'])[:34]:<34} "
              f"{_n:>4} Material-Typen reserviert  {_fr}")

    ziel = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "berichte", "reservierungen.json")
    with open(ziel, "w", encoding="utf-8") as f:
        json.dump(raus, f, indent=1, ensure_ascii=False)
    print(f"\nFERTIG: {ziel}")
    print(f"Größe: {os.path.getsize(ziel)/1024:.0f} KB")
    _ohne = [r["label"] for r in raus if not r["reserve"]]
    if _ohne:
        print("\nHINWEIS: bei diesen Plänen ist das Schloss NICHT gesetzt -")
        print("ihr Material gilt für andere Pläne als frei:")
        for lbl in _ohne:
            print(f"   {lbl}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
