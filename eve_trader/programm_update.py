"""Auftrag F4: gibt es eine neuere PROGRAMM-Version auf GitHub?

BEWUSST GETRENNT vom vorhandenen 🔄-Knopf. Der prüft die EVE-SERVER-Version
und das SDE-Datum, also ob CCP etwas geändert hat. Hier geht es um das
Programm selbst. Beides in einen Knopf zu legen wäre eine Etikettenlüge:
"Alles aktuell" würde dann zwei völlig verschiedene Dinge behaupten, und
wer sich auf eine der beiden Aussagen verlässt, läge die halbe Zeit falsch.

Das Tool kann sich NICHT selbst updaten - genau wie beim EVE-Knopf ist das
hier ein Frühwarnsystem: es sagt, dass es etwas Neues gibt, und wo.

Der Netzteil und die Entscheidung sind getrennt: `ist_neuer` und
`version_tupel` sind reine Funktionen ohne Netz, damit die Vergleichsregeln
prüfbar sind, ohne GitHub zu fragen.
"""

import re

# Zeitlimit klein halten: der Knopf darf nicht minutenlang hängen, wenn
# GitHub gerade nicht erreichbar ist (oder eine Firewall still schluckt).
ZEITLIMIT_S = 8


def version_tupel(text):
    """"v1.2.3" / "1.2" / "0.1.0-beta" -> (1, 2, 3) bzw. (1, 2), (0, 1, 0).

    TOLERANT, weil die Zahl von aussen kommt: GitHub-Marken schreibt man mal
    mit "v" davor, mal ohne, mal mit Zusatz dahinter. Was nicht als Zahl
    lesbar ist, wird abgeschnitten statt zu einem Absturz zu führen - eine
    unlesbare Marke darf höchstens dazu führen, dass NICHT gemeldet wird.
    """
    if not text:
        return ()
    _t = str(text).strip().lstrip("vV")
    _teile = []
    for stueck in re.split(r"[.\-+_ ]", _t):
        m = re.match(r"^(\d+)$", stueck)
        if not m:
            break          # ab dem ersten Nicht-Zahl-Teil ist Schluss
        _teile.append(int(m.group(1)))
    return tuple(_teile)


def ist_neuer(fern, lokal):
    """Ist die Fassung auf GitHub neuer als die laufende?

    Kürzere Angaben werden mit Nullen aufgefüllt, damit 1.2 und 1.2.0 als
    gleich gelten. Ist eine der beiden Angaben unlesbar, wird NICHTS
    gemeldet: lieber ein verpasster Hinweis als ein falscher Alarm bei
    jedem Start.
    """
    a, b = version_tupel(fern), version_tupel(lokal)
    if not a or not b:
        return False
    laenge = max(len(a), len(b))
    a = a + (0,) * (laenge - len(a))
    b = b + (0,) * (laenge - len(b))
    return a > b


def auswerten(daten, lokale_version):
    """GitHub-Antwort -> {neuer, version, url, hinweis}. Ohne Netz, prüfbar.

    `daten` ist die JSON-Antwort von /releases/latest. Ein Entwurf
    (draft) oder eine Vorabfassung (prerelease) zählt NICHT: sonst bekämen
    alle Nutzer einen Hinweis auf etwas, das noch gar nicht für sie
    gedacht ist.
    """
    from .sprache import t as _txt   # Hinweise erscheinen in der Oberflaeche
    if not isinstance(daten, dict) or not daten:
        return {"neuer": False, "version": None, "url": None,
                "hinweis": _txt("no answer")}
    if daten.get("draft") or daten.get("prerelease"):
        return {"neuer": False, "version": daten.get("tag_name"),
                "url": daten.get("html_url"),
                "hinweis": _txt("only a draft or a pre-release")}
    marke = daten.get("tag_name") or daten.get("name")
    if not version_tupel(marke):
        return {"neuer": False, "version": marke, "url": daten.get("html_url"),
                "hinweis": _txt("version tag not readable")}
    return {"neuer": ist_neuer(marke, lokale_version),
            "version": marke,
            "url": daten.get("html_url"),
            "hinweis": ""}


def neueste_release(repo, holen=None):
    """Fragt GitHub nach der neuesten Veröffentlichung. {} bei Problemen.

    `holen` ist nur für Prüfungen da (dort wird eine eigene Funktion
    eingesetzt, damit kein Netz nötig ist).
    """
    if not repo:
        return {}
    if holen is None:
        import requests

        def holen(url):
            r = requests.get(
                url, timeout=ZEITLIMIT_S,
                headers={"Accept": "application/vnd.github+json"})
            r.raise_for_status()
            return r.json()

    try:
        return holen(f"https://api.github.com/repos/{repo}/releases/latest") or {}
    except Exception:
        # Kein Netz, Repo noch ohne Veröffentlichung (GitHub antwortet dann
        # mit 404), Zeitlimit - alles kein Grund, den Nutzer zu erschrecken.
        # Der Aufrufer macht daraus eine ruhige Meldung.
        return {}


def pruefen(repo, lokale_version, holen=None):
    """Alles zusammen: fragen und auswerten."""
    return auswerten(neueste_release(repo, holen=holen), lokale_version)
