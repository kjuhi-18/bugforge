import ast
def analyze_source(source,expected="",bug_report=""):
    try: tree=ast.parse(source)
    except SyntaxError as e: return [],[],[f"Syntax error at line {e.lineno}: {e.msg}"]
    funcs=[n.name for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))]
    context=(expected+" "+bug_report).lower(); found=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Compare) and any(isinstance(o,(ast.Gt,ast.Lt,ast.GtE,ast.LtE)) for o in n.ops) and any(w in context for w in ("threshold","boundary","at least","discount","inclusive","1000")):
            found.append({"title":"Boundary-sensitive comparison","description":"Comparison may disagree with the stated boundary requirement; validate with tests.","severity":"medium","confidence":.62,"line_numbers":[n.lineno],"evidence":[f"Line {n.lineno}: {ast.get_source_segment(source,n)}"],"recommendation":"Test immediately below, at, and above the boundary."})
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in ("eval","exec"):
            found.append({"title":"Dynamic code execution","description":f"{n.func.id}() can execute untrusted input.","severity":"high","confidence":.95,"line_numbers":[n.lineno],"evidence":[f"Line {n.lineno}: {ast.get_source_segment(source,n)}"],"recommendation":"Avoid dynamic execution on untrusted input."})
        if isinstance(n,ast.ExceptHandler) and n.type is None:
            found.append({"title":"Bare exception handler","description":"Bare except can hide unexpected failures.","severity":"low","confidence":.9,"line_numbers":[n.lineno],"evidence":[f"Bare except at line {n.lineno}"],"recommendation":"Catch specific exceptions."})
    unique={(f["title"],tuple(f["line_numbers"])):f for f in found}
    return list(unique.values()),funcs,[]
