from parse import lexer, parser, ast_, code_gen
from pprint import pprint
from types import NoneType
from sys import argv

file_name = argv[1] if len(argv) > 1 else "example.spp"
result = argv[2] if len(argv) > 2 else file_name.replace(".spp",".py")
test_data = argv[3] if len(argv) > 3 else file_name.replace(".spp",".bin")

with open(file_name) as file:
    example_code = file.read()
lexed = lexer.lex(example_code)
parse = parser.Parser(lexed)
parsed = parse.parse_program()

with open(result, "w") as file:
    gen = code_gen.Generator(parsed)
    text = gen.generate()
    file.write(text)

lib = __import__(result.replace(".py",""))
with open(test_data,"rb") as file:
    data = file.read()
data = lib.parseFile(data)
pprint(data)
