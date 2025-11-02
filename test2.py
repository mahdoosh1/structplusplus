from parse import lexer, parser, ast_, code_gen
from pprint import pprint
from types import NoneType

with open("example.spp") as file:
    example_code = file.read()
lexed = lexer.lex(example_code)
#pprint(lexed[:10])
parse = parser.Parser(lexed)
parsed = parse.parse_program()
with open("example.py","w") as f:
    code_gen.generate_code(parsed, f)
