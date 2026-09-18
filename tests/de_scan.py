import ast, re, sys, glob
import os as _os_wurzel
_os_wurzel.chdir(_os_wurzel.path.dirname(_os_wurzel.path.dirname(_os_wurzel.path.abspath(__file__))))   # Projektwurzel (tests\ -> ..)
DE=re.compile(r'[äöüÄÖÜß]|\b(und|nicht|der|die|das|wird|werden|für|fuer|oder|mit|bei|nur|wenn|dann|kein|keine|ohne|wieder|auch|noch|nach|von|zum|zur|des|dem|ein|eine|ist|sind|dieser|diese|dieses|Bitte|bitte)\b')
UI_ATTRS={"setToolTip","setText","showMessage","setWindowTitle","addItem","setPlaceholderText","setStatusTip","setWhatsThis","setTitle","setHeaderLabels","setHorizontalHeaderLabels","addTab","setTabText","information","warning","critical","question","about","setLabelText","addAction","setDescription"}
UI_NAMES={"QLabel","QPushButton","QCheckBox","QGroupBox","QAction","QRadioButton","QMessageBox","QTreeWidgetItem","QTableWidgetItem","QListWidgetItem","_QCheckBox","QMenu","QInputDialog","QToolButton","QDialog"}
def full_str(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str): return node.value
    if isinstance(node, ast.JoinedStr): return "".join(v.value for v in node.values if isinstance(v, ast.Constant))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add): return (full_str(node.left) or "") + (full_str(node.right) or "")
    return None
tot=0
for f in sorted(glob.glob("eve_trader/ui/*.py"))+["eve_trader/__main__.py"]:
    src=open(f,encoding="utf-8").read(); tree=ast.parse(src)
    parent={}
    for n in ast.walk(tree):
        for c in ast.iter_child_nodes(n): parent[c]=n
    hits=[]
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call): continue
        fn=n.func
        name = fn.attr if isinstance(fn,ast.Attribute) else (fn.id if isinstance(fn,ast.Name) else None)
        if name not in UI_ATTRS and name not in UI_NAMES: continue
        for arg in list(n.args)+[k.value for k in n.keywords]:
            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id in ("t","_txt"): continue
            s=full_str(arg)
            if s and DE.search(s):
                # innerhalb t(...)? (z.B. t("...") + x)
                inner=[c for c in ast.walk(arg) if isinstance(c,ast.Call) and isinstance(c.func,ast.Name) and c.func.id in ("t","_txt")]
                consts=[c for c in ast.walk(arg) if isinstance(c,ast.Constant) and isinstance(c.value,str) and DE.search(c.value)]
                # nur melden, wenn ein deutsches Literal NICHT unter t() haengt
                def under_t(c):
                    p=parent.get(c)
                    while p is not None and p is not arg:
                        if isinstance(p,ast.Call) and isinstance(p.func,ast.Name) and p.func.id in ("t","_txt"): return True
                        p=parent.get(p)
                    return False
                if any(not under_t(c) for c in consts):
                    hits.append((n.lineno, name, s[:90].replace("\n"," ")))
    hits=sorted(set(hits))
    tot+=len(hits)
    print(f"== {f}: {len(hits)}")
    for h in hits[:200]: print("  ", *h)
print("GESAMT", tot)
