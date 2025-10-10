import lexer, parser
from pprint import pprint

with open("example.spp") as file:
    example_code = file.read()
lexed = lexer.lex(example_code)
parse = parser.Parser(lexed)
parsed = parse.parse_program()
import ctree
ctree.ipython_show_ast(parsed)
pprint(parsed)
