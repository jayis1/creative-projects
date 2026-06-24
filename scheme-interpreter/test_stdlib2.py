from scheme_interpreter.parser import parse
from scheme_interpreter.lexer import tokenize

source = open("scheme_interpreter/stdlib.scm").read()
toks = tokenize(source)
opens = sum(1 for t in toks if t.type in ("LPAREN", "LBRACKET"))
closes = sum(1 for t in toks if t.type in ("RPAREN", "RBRACKET"))
print(f"Opens: {opens}, Closes: {closes}")
try:
    forms = parse(source)
    print(f"Forms: {len(forms)}")
except Exception as e:
    print(f"Error: {e}")