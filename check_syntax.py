import ast, pathlib, sys
root = pathlib.Path(r"C:\Users\Robby\yt-clip-crewai")
ok = True
for p in root.rglob("*.py"):
    if ".hermes-tmp" in str(p): continue
    try:
        ast.parse(p.read_text(encoding="utf-8"))
        print("parse OK ", p.relative_to(root))
    except SyntaxError as e:
        ok = False
        print("PARSE FAIL", p.relative_to(root), e)
print("\nALL PARSE OK" if ok else "\nSYNTAX ERRORS FOUND")
