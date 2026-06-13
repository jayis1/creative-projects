import ast
with open('aquarium.py') as f:
    tree = ast.parse(f.read())
print(f'Parse OK: {len(tree.body)} top-level nodes')
classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
print(f'Classes: {classes}')
print(f'Functions: {funcs}')