from parse import lexer, parser, ast_, code_gen
from pprint import pprint
from types import NoneType

with open("example.spp") as file:
    example_code = file.read()
lexed = lexer.lex(example_code)
parse = parser.Parser(lexed)
parsed = parse.parse_program()

with open("example.py", "w") as file:
    gen = code_gen.Generator(parsed)
    text = gen.generate()
    file.write(text)

import example
with open("example.bmp","rb") as file:
    data = file.read()
data = example.parseFile(data)[0]['pixels']['rows'][50]
pprint(data)
