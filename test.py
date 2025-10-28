from parse import lexer, parser, ast_
from pprint import pprint
from types import NoneType

with open("example.spp") as file:
    example_code = file.read()
lexed = lexer.lex(example_code)
#pprint(lexed[:10])
parse = parser.Parser(lexed)
parsed = parse.parse_program()
#pprint(parsed.items[3].block.code)

import json

def valid(obj, key, value):
    if not value:
        return False
    if key == "pos":
        return False
    if key == "name":
        if isinstance(value, str):
            if not isinstance(obj, ast_.Identifier):
                return False
    return True

def keyrepr(obj, key, value):
    output = key
    if not isinstance(value, str):
        output = f"{key}={value.__class__.__name__}"
    if isinstance(getattr(value, "name", None), str):
        if not isinstance(value, ast_.Identifier):
            if isinstance(value, str):
                output += f"({value})"
            else:
                output += f"({value.name})"
    return output

def ast_to_json(obj):
    if isinstance(obj, (list, tuple)):
        iterator = enumerate(obj)
    elif hasattr(obj, "__dict__"):
        iterator = vars(obj).items()
    elif isinstance(obj, (str, int, NoneType)):
        return obj
    else:
        return obj
    return {
            keyrepr(obj, k, v):ast_to_json(v) for k, v in iterator if valid(obj, k, v)
        }

#print(parsed.items[-1])

with open("ast.json", "w") as f:
    json.dump(ast_to_json(parsed), f, indent=2)

from os import system
system("open ast.json")
