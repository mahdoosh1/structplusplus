from parse import lex, Parser, ast_, Generator
from pprint import pprint
from types import NoneType
from sys import argv

file_name = argv[1] if len(argv) > 1 else "test/example.spp"
result = argv[2] if len(argv) > 2 else None
test_data = argv[3] if len(argv) > 3 else None

with open(file_name) as file:
    code = file.read()
lexed = lex(code)
parse = Parser(file_name, lexed)
parsed = parse.parse_program()

if result:
    with open(result, "w") as file:
        gen = Generator(parsed)
        text = gen.generate()
        file.write(text)

if result and test_data:
    lib = __import__(result.replace(".py",""))
    with open(test_data,"rb") as file:
        data = file.read()
    data = lib.parseFile(data)
    pprint(data)
