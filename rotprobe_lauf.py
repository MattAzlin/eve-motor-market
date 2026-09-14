"""Volle Rotprobe in Abschnitten - mit Gedaechtnis.

WARUM (Sitzung 16): ein voller Lauf dauert ~3,8 h (24 s je Mutation, 553
Stueck) und passt in keinen einzelnen Aufruf. Ohne Gedaechtnis faengt jeder
Versuch von vorn an und kommt nie durch.

Dieser Laeufer schreibt nach JEDER Mutation in `rotprobe_stand.json`:
welche gruen (erkannt), welche BLIND. Beim naechsten Aufruf macht er dort
weiter, wo er aufgehoert hat.

    python rotprobe_lauf.py            # weiter, bis das Zeitbudget reicht
    python rotprobe_lauf.py --minuten 4
    python rotprobe_lauf.py --bericht  # nur den Stand zeigen
    python rotprobe_lauf.py --neu      # von vorn

BLIND heisst: die Mutation wurde eingebaut, aber KEINE Pruefung ist
angeschlagen. Das ist der gefaehrliche Fall - eine Zusage ohne Waechter.
"""
import json
import os
import subprocess
import sys
import time

STAND = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "rotprobe_stand.json")


def _laden():
    try:
        with open(STAND, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"fertig": {}, "blind": []}


def _sichern(d):
    with open(STAND, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def main():
    import rotprobe
    gesamt = len(rotprobe.MUTATIONEN)
    if "--neu" in sys.argv:
        try:
            os.remove(STAND)
        except OSError:
            pass
    d = _laden()
    if "--bericht" in sys.argv:
        _bericht(d, gesamt)
        return 0
    minuten = 4.0
    if "--minuten" in sys.argv:
        minuten = float(sys.argv[sys.argv.index("--minuten") + 1])
    ende = time.time() + minuten * 60
    hier = os.path.dirname(os.path.abspath(__file__))
    for i in range(gesamt):
        if str(i) in d["fertig"]:
            continue
        if time.time() > ende:
            break
        r = subprocess.run([sys.executable, "rotprobe.py", str(i), str(i + 1)],
                           cwd=hier, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        aus = (r.stdout or "") + (r.stderr or "")
        blind = "BLIND!" in aus
        nicht_anwendbar = "Muster 0x" in aus or "nicht eindeutig" in aus
        d["fertig"][str(i)] = ("blind" if blind else
                               "anker" if nicht_anwendbar else "rot")
        if blind or nicht_anwendbar:
            name = rotprobe.MUTATIONEN[i][0]
            d["blind"].append(f"{i}: {name}"
                              + ("  [ANKER GREIFT NICHT]" if nicht_anwendbar
                                 else ""))
        _sichern(d)
    _bericht(d, gesamt)
    return 0


def _bericht(d, gesamt):
    f = d["fertig"]
    rot = sum(1 for v in f.values() if v == "rot")
    print(f"geprueft {len(f)}/{gesamt}  ·  rot {rot}  ·  "
          f"BLIND/Anker {len(d['blind'])}")
    for z in d["blind"]:
        print("   !! " + z)
    if len(f) < gesamt:
        print(f"   offen: {gesamt - len(f)} - nochmal aufrufen zum Fortsetzen")


if __name__ == "__main__":
    sys.exit(main())
