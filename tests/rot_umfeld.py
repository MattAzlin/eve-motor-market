"""Rotprobe NUR fuer das Umfeld dieses Umbaus (Sitzung 14).

WARUM NICHT DER KOMPLETTLAUF: in diesem Container braucht eine Mutation
~18 s (jede fuehrt beide Suiten, die b-Suite baut dabei ein echtes Qt-
Fenster). 459 Mutationen waeren damit rund 2 h 15 - die in start.sh
genannten "~35 min" gelten fuer die Umgebung des Nutzers, nicht hier.

WAS STATTDESSEN: alle Mutationen der drei Dateien, die dieser Umbau
angefasst hat (mw_bauplan_tabs.py, icons.py, mw_helpers.py). Das ist mehr
als die von der Rotproben-Regel verlangte Stichprobe von 20-30 - es ist das
VOLLSTAENDIGE Umfeld. Genau dort liegen laut Regel die ergiebigen Faelle:
Mutationen, deren Anker sich bewegt haben.

    python3 rot_umfeld.py <von> <bis>     (Index in die Umfeld-Liste)
"""
import sys

import rotprobe

# ERWEITERT (Sitzung 14): der zweite Teil der Sitzung hat main_window.py,
# mw_bauplan_fenster.py, industry.py, esi.py und sprache.py angefasst -
# Fertigungstiefe nach Rezeptstufe, Preis-Rueckfall, ids-Liste,
# Schalter-Sperre, Einkaufsliste, nicht-kaufbar, Fortschrittsbalken,
# Frachtaufschlag. Das Umfeld ist damit deutlich groesser als am Anfang.
DATEIEN = ("eve_trader/ui/mw_bauplan_tabs.py",
           "eve_trader/ui/icons.py",
           "eve_trader/ui/mw_helpers.py",
           "eve_trader/ui/main_window.py",
           "eve_trader/ui/mw_bauplan_fenster.py",
           "eve_trader/industry.py",
           "eve_trader/esi.py")

_alle = rotprobe.MUTATIONEN
_idx = [i for i, m in enumerate(_alle) if m[1] in DATEIEN]

if __name__ == "__main__":
    lo = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    hi = int(sys.argv[2]) if len(sys.argv) > 2 else len(_idx)
    teil = _idx[lo:hi]
    print(f"Umfeld: {len(_idx)} Mutationen gesamt, fahre {lo}..{hi} "
          f"(Original-Indizes {teil[0]}..{teil[-1]})", flush=True)
    rotprobe.MUTATIONEN = [_alle[i] for i in teil]
    sys.argv = ["rotprobe.py", "0", str(len(teil))]
    rotprobe.main()
