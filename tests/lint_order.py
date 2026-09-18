"""Statischer Prüfer gegen die Fehlerklasse „Name vor seiner Zuweisung benutzt".

Zwei reale Nutzer-Abstürze dieser Art (UnboundLocalError decryptor_list,
NameError refz_btn) hat KEIN Syntax-Check und kein String-Test gefunden -
beide traten erst zur Laufzeit auf, tief in sehr langen UI-Funktionen.

Erkannt werden zwei Muster innerhalb JEDER Funktion:
  A) Direkte Vorwärts-Referenz: ein lokaler Name wird auf Statement-Ebene
     gelesen, bevor er in derselben Funktion zugewiesen wird.
  B) Closure-Falle: eine verschachtelte Funktion liest einen Namen der
     äußeren Funktion, und die äußere Funktion RUFT diese verschachtelte
     Funktion auf, BEVOR der Name zugewiesen ist.

Bewusst konservativ: nur Namen, die in derselben Funktion zugewiesen werden
(keine Globals/Builtins/Argumente), und nur Aufrufe auf Statement-Ebene.
"""
import ast
import sys


def _assigned_names(fn):
    """Namen, die im Funktionskörper (ohne verschachtelte Defs) zugewiesen
    werden -> erste Zeilennummer."""
    out = {}

    def walk(node, top=True):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.Lambda, ast.ClassDef, ast.ListComp,
                                  ast.SetComp, ast.DictComp, ast.GeneratorExp)):
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out.setdefault(child.name, child.lineno)
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Store):
                out.setdefault(child.id, child.lineno)
            elif isinstance(child, ast.alias):
                nm = (child.asname or child.name).split(".")[0]
                out.setdefault(nm, getattr(child, "lineno", 0))
            walk(child, False)
    walk(fn)
    return out


def _nested_funcs(fn):
    return {c.name: c for c in ast.iter_child_nodes(fn)
            if isinstance(c, (ast.FunctionDef, ast.AsyncFunctionDef))}


def _names_read(node):
    """Alle gelesenen Namen (rekursiv, inkl. verschachtelter Defs)."""
    out = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.add(n.id)
    return out


def _declared_global(fn):
    """Namen aus `global`/`nonlocal`: die gehören NICHT der Funktion, eine
    Zuweisung weiter unten ist also keine Vorwärts-Referenz (Fehlalarme an
    _skill_time_bonus_cache und ci real geprüft)."""
    out = set()
    for n in ast.walk(fn):
        if isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
    return out


def _params(fn):
    a = fn.args
    names = {p.arg for p in list(a.args) + list(a.posonlyargs) + list(a.kwonlyargs)}
    if a.vararg:
        names.add(a.vararg.arg)
    if a.kwarg:
        names.add(a.kwarg.arg)
    return names


def check_function(fn, path):
    problems = []
    assigned = _assigned_names(fn)
    params = _params(fn) | _declared_global(fn)
    nested = _nested_funcs(fn)
    # Default-Argumente einer verschachtelten Funktion werden bei der
    # DEFINITION ausgewertet - dort gilt die normale Vorwärts-Regel.
    for name, sub in nested.items():
        for d in list(sub.args.defaults) + [d for d in sub.args.kw_defaults if d]:
            for rd in _names_read(d):
                if rd in assigned and rd not in params and assigned[rd] > d.lineno:
                    problems.append(
                        f"{path}:{d.lineno}: Default-Argument von '{name}' liest "
                        f"'{rd}', zugewiesen erst Zeile {assigned[rd]}")

    # A) Direkte Vorwärts-Referenz im eigenen Ablauf (Muster decryptor_list):
    #    ein lokaler Name wird gelesen, bevor er zugewiesen ist.
    def _own_nodes(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.Lambda, ast.ClassDef, ast.ListComp,
                                  ast.SetComp, ast.DictComp,
                                  ast.GeneratorExp)):
                continue
            yield child
            yield from _own_nodes(child)

    for nd in _own_nodes(fn):
        if not (isinstance(nd, ast.Name) and isinstance(nd.ctx, ast.Load)):
            continue
        nm = nd.id
        if nm in params or nm not in assigned:
            continue
        if assigned[nm] > nd.lineno:
            problems.append(
                f"{path}:{nd.lineno}: '{nm}' wird gelesen, aber erst Zeile "
                f"{assigned[nm]} zugewiesen (Vorwärts-Referenz)")

    # Aufrufe verschachtelter Funktionen im EIGENEN Ablauf der äußeren
    # Funktion. Bewusst NICHT durch verschachtelte Defs hindurch: ein Aufruf
    # in einem Callback läuft asynchron SPÄTER, da ist die Zuweisung längst
    # passiert (das wäre ein Fehlalarm - real geprüft an _refill_schedule).
    def _own_statements(node):
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                                  ast.Lambda, ast.ClassDef, ast.ListComp,
                                  ast.SetComp, ast.DictComp,
                                  ast.GeneratorExp)):
                continue
            yield child
            yield from _own_statements(child)

    for stmt in _own_statements(fn):
        if not isinstance(stmt, ast.Expr) or not isinstance(stmt.value, ast.Call):
            continue
        f = stmt.value.func
        if not isinstance(f, ast.Name) or f.id not in nested:
            continue
        sub = nested[f.id]
        call_line = stmt.lineno
        if sub.lineno > call_line:
            continue                      # Aufruf vor der Definition: anderer Fall
        sub_params = _params(sub)
        sub_local = _assigned_names(sub)
        for rd in _names_read(sub):
            if rd in sub_params or rd in sub_local:
                continue                  # eigener Parameter/lokal -> harmlos
            if rd in assigned and rd not in params and assigned[rd] > call_line:
                problems.append(
                    f"{path}:{call_line}: Aufruf von '{f.id}()' liest '{rd}' "
                    f"aus der äußeren Funktion, dort erst Zeile {assigned[rd]} "
                    f"zugewiesen")

    # D) CLOSURE-SHADOWING (Nutzer-Absturz "cannot access local variable
    #    'sell'"): eine verschachtelte Funktion LIEST einen Namen aus der
    #    äußeren Funktion und WEIST ihm später auch zu. Durch die Zuweisung
    #    wird der Name für die GESAMTE innere Funktion lokal - der frühere
    #    Lesezugriff knallt zur Laufzeit als UnboundLocalError.
    #    Reine Syntax-Checks sehen das nicht; Regel A greift nicht, weil der
    #    Name in der ÄUSSEREN Funktion sauber vorher zugewiesen ist.
    for name, sub in nested.items():
        if any(isinstance(n, ast.Global) or isinstance(n, ast.Nonlocal)
               for n in ast.walk(sub)):
            continue                      # explizit deklariert -> Absicht
        sub_assigned = _assigned_names(sub)
        sub_params = _params(sub)
        for nm, aline in sub_assigned.items():
            if nm in sub_params or nm not in assigned:
                continue                  # kein Name aus der äußeren Funktion
            # NUR den eigenen Namensraum ansehen: Comprehensions, Lambdas und
            # verschachtelte Funktionen haben in Python 3 EIGENE Scopes - ein
            # gleichnamiger Name dort ist ein anderer Name. Ohne diese
            # Einschraenkung meldet die Regel z.B.
            # `[(bp_id, pid) for bp_id, pid in ...]` faelschlich (bemerkt beim
            # ersten Lauf ueber die Codebasis).
            first_read = None
            _stack = [sub]
            while _stack:
                _n = _stack.pop()
                for _c in ast.iter_child_nodes(_n):
                    if isinstance(_c, (ast.FunctionDef, ast.AsyncFunctionDef,
                                       ast.Lambda, ast.ClassDef, ast.ListComp,
                                       ast.SetComp, ast.DictComp,
                                       ast.GeneratorExp)):
                        continue
                    if (isinstance(_c, ast.Name)
                            and isinstance(_c.ctx, ast.Load) and _c.id == nm):
                        if first_read is None or _c.lineno < first_read:
                            first_read = _c.lineno
                    _stack.append(_c)
            if first_read is not None and first_read < aline:
                problems.append(
                    f"{path}:{first_read}: '{name}()' liest '{nm}' aus der "
                    f"äußeren Funktion, weist es aber Zeile {aline} auch zu "
                    f"-> UnboundLocalError. Anderen Namen verwenden.")
    return problems


def check_file(path):
    tree = ast.parse(open(path, encoding="utf-8").read(), filename=path)
    problems = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            problems += check_function(node, path)
    return problems


if __name__ == "__main__":
    allp = []
    for p in sys.argv[1:]:
        allp += check_file(p)
    for p in allp:
        print("  " + p)
    print(f"{len(allp)} Befund(e)")
    sys.exit(1 if allp else 0)
