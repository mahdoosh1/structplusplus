from .ast import *
from .lexer import Token, TokenType

class ParseError(Exception):
    pass


class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.index = 0
    def next(self):
        self.index += 1
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return None
    def peek(self):
        if self.index+1 < len(self.tokens):
            return self.tokens[self.index + 1]
        return None
    def safe_peek(self):
        if self.index+1 < len(self.tokens):
            return self.tokens[self.index + 1]
        raise EOFError("Code ended too early.")
    def expect(self, *values):
        x = self.peek()
        if x is None:
            raise EOFError(f"Code ended too early. Expected any of {values}")
        if x.type in values:
            return x
        raise ParseError(f"Expected any of {values}. got {x.type} (at :{x.position[0]}:{x.position[1]})")