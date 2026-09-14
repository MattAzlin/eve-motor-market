"""Tooltip-Konverter: deutsche Tooltip-Literale -> t("English") + Katalog.

AUFRUF:  python3 tt_konv.py uebersetzungen.json [--dry]

uebersetzungen.json: {"<deutscher Text exakt>": "<English text>", ...}

Was das Skript tut (und was nicht):
* Nur `.setToolTip(<Literal>)` mit EINEM Zeichenketten-Literal (auch
  implizit ueber mehrere Zeilen zusammengesetzt). f-Strings und
  Verkettungen mit Variablen werden gemeldet, nicht angefasst.
* Prueft VOR dem Ersetzen, ob `t` in einer umschliessenden Funktion
  lokal belegt ist (Zuweisung oder Parameter). Dann `_txt(` statt `t(`,
  und nur, wenn die Funktion `import t as _txt` schon hat - sonst wird
  die Stelle gemeldet und uebersprungen (NameError-Falle, aa237/aa247).
* Schneidet NICHT zeichenweise nach col_offset (das sind BYTES) - die
  Spalten werden ueber die UTF-8-Laenge in Zeichen umgerechnet.
* Nicht-ASCII im neuen Literal wird als \\uXXXX geschrieben (aa196).
* Katalog-Eintrag wird in sprache.py vor dem schliessenden `    },` von
  KATALOG["de"] eingefuegt. Vorher wird geprueft, dass der Schluessel
  noch nicht existiert.
"""
import ast
import json
import sys

MW = "eve_trader/ui/main_window.py"
SPR = "eve_trader/sprache.py"


def _lit(s):
    """Python-Literal mit \\u-Escapes, doppelte Anfuehrungszeichen.
    Zeichen ausserhalb der BMP (Emoji) als \\UXXXXXXXX - json.dumps schriebe
    sie als Surrogat-Paar, und das ergibt in Python KEIN Emoji, sondern zwei
    kaputte Codepunkte."""
    out = []
    for ch in s:
        o = ord(ch)
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif 32 <= o < 127:
            out.append(ch)
        elif o > 0xFFFF:
            out.append("\\U%08X" % o)
        else:
            out.append("\\u%04x" % o)
    return '"' + "".join(out) + '"'


def _wrap_lit(s, indent, width=72):
    """Langes Literal als implizite Verkettung ueber mehrere Zeilen."""
    if len(s) <= width and "\n" not in s:
        return _lit(s)
    teile = []
    rest = s
    while rest:
        if len(rest) <= width:
            teile.append(rest)
            break
        # Bevorzugt nach einem Zeilenumbruch schneiden, sonst am Leerzeichen
        cut = rest.rfind("\n", 0, width)
        if cut > 0:
            cut += 1
        else:
            cut = rest.rfind(" ", 0, width)
            if cut <= 0:
                cut = width
            else:
                cut += 1
        teile.append(rest[:cut])
        rest = rest[cut:]
    pad = " " * indent
    return ("\n" + pad).join(_lit(x) for x in teile)


def _col_to_char(line, col_bytes):
    return len(line.encode("utf-8")[:col_bytes].decode("utf-8", "replace"))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    dry = "--dry" in sys.argv
    uebers = json.load(open(sys.argv[1], encoding="utf-8"))
    src = open(MW, encoding="utf-8").read()
    lines = src.split("\n")
    tree = ast.parse(src)
    parent = {}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n):
            parent[c] = n

    def enclosing_funcs(node):
        out = []
        p = parent.get(node)
        while p is not None:
            if isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                out.append(p)
            p = parent.get(p)
        return out

    def t_shadowed(fn):
        if any(isinstance(x, ast.Name) and x.id == "t" and isinstance(x.ctx, ast.Store)
               for x in ast.walk(fn)):
            return True
        return any(a.arg == "t" for a in list(fn.args.args) + list(fn.args.kwonlyargs))

    edits = []      # (start_line, start_char, end_line, end_char, new_text)
    neu_katalog = []
    gemeldet = []
    getroffen = set()
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                and n.func.attr == "setToolTip" and n.args):
            continue
        arg = n.args[-1]        # setToolTip(text) UND setToolTip(spalte, text)
        if not (isinstance(arg, ast.Constant) and isinstance(arg.value, str)):
            continue
        de = arg.value
        if de not in uebers:
            continue
        en = uebers[de]
        fns = enclosing_funcs(n)
        shadow = any(t_shadowed(f) for f in fns)
        name = "t"
        if shadow:
            name = "_txt"
            # der innerste benannte Funktionsblock muss `_txt` holen
            fn_src = None
            for f in fns:
                if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    fn_src = ast.get_source_segment(src, f)
                    break
            if not fn_src or "import t as _txt" not in fn_src:
                gemeldet.append((n.lineno, "t lokal belegt, _txt nicht importiert"))
                continue
        sl, sc = arg.lineno, _col_to_char(lines[arg.lineno - 1], arg.col_offset)
        el, ec = arg.end_lineno, _col_to_char(lines[arg.end_lineno - 1], arg.end_col_offset)
        indent = sc + len(name) + 1
        neu = f"{name}({_wrap_lit(en, indent)})"
        edits.append((sl, sc, el, ec, neu))
        neu_katalog.append((en, de))
        getroffen.add(de)

    fehlt = [d for d in uebers if d not in getroffen]
    for d in fehlt:
        gemeldet.append((0, "kein passendes Literal gefunden: " + d[:60]))
    for ln, why in gemeldet:
        print(f"UEBERSPRUNGEN Zeile {ln}: {why}")

    # von hinten nach vorn einsetzen
    edits.sort(key=lambda e: (e[0], e[1]), reverse=True)
    for sl, sc, el, ec, neu in edits:
        vor = lines[sl - 1][:sc]
        nach = lines[el - 1][ec:]
        lines[sl - 1:el] = [vor + neu + nach]
    neu_src = "\n".join(lines)
    ast.parse(neu_src)          # muss weiterhin gueltiges Python sein

    spr = open(SPR, encoding="utf-8").read()
    anker = "    },\n}\n\n_aktuell = "
    assert spr.count(anker) == 1, "Katalog-Anker nicht eindeutig"
    _kopf = "        # ---- Tooltips main_window.py (Sitzung 13) ----"
    zeilen = [] if _kopf in spr else [_kopf]
    _schon = set()
    for en, de in neu_katalog:
        if en in _schon:
            continue                    # derselbe Text an mehreren Stellen
        _schon.add(en)
        if _lit(en) + ":" in spr:
            print(f"KATALOG: Schluessel schon vorhanden, nicht doppelt: {en[:50]}")
            continue
        zeilen.append(f"        {_lit(en)}:\n            {_lit(de)},")
    block = "\n".join(zeilen) + "\n"
    neu_spr = spr.replace(anker, block + anker)

    print(f"{len(edits)} Tooltips umgestellt, {len(neu_katalog)} Katalog-Eintraege")
    if dry:
        return 0
    open(MW, "w", encoding="utf-8").write(neu_src)
    open(SPR, "w", encoding="utf-8").write(neu_spr)
    # Katalog muss importierbar bleiben
    ast.parse(neu_spr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
