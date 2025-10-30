import re
from enum import StrEnum, auto
from typing import NamedTuple

class TokenType(StrEnum):
    IDENT = auto()
    INTEGER = auto()
    SIZE = auto()
    REGULARSIZE = auto()
    FLOAT = auto()
    STRING = auto()
    KEYWORD = auto()
    PREPROCESSOR = auto()
    
    PAREN_LEFT = auto()
    PAREN_RIGHT = auto()
    BRACE_LEFT = auto()
    BRACE_RIGHT = auto()
    BRACK_LEFT = auto()
    BRACK_RIGHT = auto()
    
    HASHTAG = auto()
    ATSIGN = auto()
    OPERATOR = auto()
    COMMA = auto()
    COLON = auto()
    SEMICOLON = auto()
    EQUALS = auto()

    WHITESPACE = auto()

class Token(NamedTuple):
    type: TokenType
    value: str
    position: tuple[int, int]

class Match:
    IDENT = re.compile(r"[A-Za-z_]\w*")
    STRING = re.compile(r'"([^"\\]|\\.)*"')
    INTEGER = re.compile(r"(?:0[bB][01_]+|0[oO][0-7_]+|0[xX][0-9A-Fa-f_]+|\d[\d_]*)")
    FLOAT = re.compile(r"(?:\d[\d_]*\.\d[\d_]*|\d[\d_]*\.|\.\d[\d_]*)(?:[eE][+-]?\d+)?|\d[\d_]*(?:[eE][+-]?\d+)")
    PREPROCESSORS = {
        "define","undef","ifdef","ifndef","endif"
    }
    REGULARSIZES = {
        "uint8","uint16","uint32","uint64","int8","int16","int32","int64",
        "float","double"
    }
    KEYWORDS = {
        "struct","code",
        "if","elif","else","raise",
        "reserve","noreserve","endian","front","behind","big","little",
        "define","undef","ifdef","ifndef","endif"
    }
    OPERATORS = {
        "||","&&","<=",">=","==","!=","+","-","&","*","!","/","%","|","~","^","<",">","."
    }
    SYMBOLS = {
        "(":TokenType.PAREN_LEFT,
        ")":TokenType.PAREN_RIGHT,
        "{":TokenType.BRACE_LEFT,
        "}":TokenType.BRACE_RIGHT,
        "[":TokenType.BRACK_LEFT,
        "]":TokenType.BRACK_RIGHT,
        ",":TokenType.COMMA,
        ":":TokenType.COLON,
        ";":TokenType.SEMICOLON,
        "=":TokenType.EQUALS
    }

def lex(code: str) -> list[Token]:
    index = 0
    line = 1
    column = 1
    code_length = len(code)
    tokens = []
    def add_token(tokentype: TokenType, value: str):
        tokens.append(Token(tokentype, value, (line, column)))
    while index < code_length:
        char = code[index]
        pos = (line, column)
        if char == "\n":
            add_token(TokenType.WHITESPACE, "\n")
            column = 1
            line += 1
            index += 1
        elif char.isspace():
            add_token(TokenType.WHITESPACE, char)
            index += 1
            column += 1
        elif code.startswith("//", index):
            index += 2
            column += 2
            while index < code_length and code[index] != "\n":
                index += 1
                column += 1
        elif code.startswith("/*", index):
            index += 2
            column += 2
            while index < code_length and not code.startswith("*/", index):
                if code[index] == "\n":
                    line += 1
                    column = 1
                else:
                    column += 1
                index += 1
            if index >= code_length:
                # raise SyntaxError(f"Unterminated block comment at {pos}")
                break
            index += 2
            column += 2
        elif char == "#":
            add_token(TokenType.HASHTAG, "#")
            index += 1
        elif char == "@":
            add_token(TokenType.ATSIGN, "@")
            index += 1
        elif char == '"':
            match = Match.STRING.match(code, index)
            if not match:
                raise SyntaxError(f"Unterminated string literal at {pos}")
            text = match.group()
            add_token(TokenType.STRING, text)
            index = match.end()
            column += len(text)
        elif (match := Match.FLOAT.match(code, index)):
            text = match.group().replace("_", "")
            add_token(TokenType.FLOAT, text)
            index = match.end()
            column += len(text)
        elif (match := Match.INTEGER.match(code, index)):
            text = match.group().replace("_", "")
            add_token(TokenType.INTEGER, text)
            index = match.end()
            column += len(text)
        elif (match := Match.IDENT.match(code, index)):
            text = match.group()
            if text in ("B","b") and tokens[-1][0] == TokenType.INTEGER:
                text = tokens.pop()[1]+text
                token_type = TokenType.SIZE
            elif text in Match.REGULARSIZES:
                token_type = TokenType.REGULARSIZE
            elif text in Match.PREPROCESSORS:
                token_type = TokenType.PREPROCESSOR
            elif text in Match.KEYWORDS:
                token_type = TokenType.KEYWORD
            else:
                token_type = TokenType.IDENT
            add_token(token_type, text)
            index = match.end()
            column += len(text)
        else:
            matched = False
            for operator in sorted(Match.OPERATORS, key=len, reverse=True):
                if code.startswith(operator, index):
                    add_token(TokenType.OPERATOR, operator)
                    index += len(operator)
                    column += len(operator)
                    matched = True
                    break

            if not matched:
                token_type = None
                if char in Match.SYMBOLS:
                    token_type = Match.SYMBOLS[char]
                elif token_type is None:
                    raise SyntaxError(f"Unexpected character {char!r} at {pos}")
                
                add_token(token_type, char)
                column += len(char)
                index += 1
                matched = True
    return tokens
