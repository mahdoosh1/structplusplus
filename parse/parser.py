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

    def current(self):
        if self.index < len(self.tokens):
            return self.tokens[self.index]
        return None

    def match(self, *types):
        cur = self.current()
        if cur is None:
            return False
        if cur.type in types:
            return True
        return False

    # --- expression parsing ---
    def parse_expression(self, min_prec=0):
        left = self.parse_unary()
        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.type != TokenType.OPERATOR:
                break
            prec = self.get_precedence(cur.value)
            if prec < min_prec:
                break
            op_tok = cur
            self.next()
            right = self.parse_expression(prec + 1)
            left = BinaryOp(left.pos, left, op_tok.value, right)
        return left

    def parse_unary(self):
        cur = self.current()
        if cur is not None:
            if cur.type == TokenType.OPERATOR:
                if cur.value in ("+", "-", "!", "~"):
                    op_tok = cur
                    self.next()
                    operand = self.parse_unary()
                    return UnaryOp(op_tok.position, op_tok.value, operand)
        return self.parse_atom()

    def parse_atom(self):
        tok = self.current()
        if tok is None:
            raise ParseError("Unexpected EOF in expression")

        if tok.type == TokenType.IDENT:
            self.next()
            node = Identifier(tok.position, tok.value)
            while True:
                cur = self.current()
                if cur is None:
                    break
                if cur.type != TokenType.OPERATOR:
                    break
                if cur.value != ".":
                    break
                self.next()
                field_tok = self.expect(TokenType.IDENT)
                self.next()
                node = FieldAccess(node.pos, node, field_tok.value)
            return node

        if tok.type == TokenType.INTEGER:
            self.next()
            return NumberLiteral(tok.position, tok.value, "integer")

        if tok.type == TokenType.SIZE:
            self.next()
            return NumberLiteral(tok.position, tok.value, "size")

        if tok.type == TokenType.FLOAT:
            self.next()
            return NumberLiteral(tok.position, tok.value, "float")

        if tok.type == TokenType.STRING:
            self.next()
            return StringLiteral(tok.position, tok.value)

        if tok.type == TokenType.PAREN_LEFT:
            self.next()
            expr = self.parse_expression()
            self.expect(TokenType.PAREN_RIGHT)
            self.next()
            return expr

        raise ParseError(f"Unexpected token {tok.value} in expression at {tok.position}")

    def get_precedence(self, op):
        prec_table = {
            "||": 1, "&&": 2,
            "|": 3, "^": 4, "&": 5,
            "==": 6, "!=": 6,
            "<": 7, "<=": 7, ">": 7, ">=": 7,
            "+": 8, "-": 8,
            "*": 9, "/": 9, "%": 9,
            ".": 10
        }
        if op in prec_table:
            return prec_table[op]
        return 0

    # --- block parsing ---
    def parse_block(self):
        self.expect(TokenType.BRACE_LEFT)
        self.next()
        statements = []

        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.type == TokenType.BRACE_RIGHT:
                break
            stmt = self.parse_statement()
            statements.append(stmt)

        self.expect(TokenType.BRACE_RIGHT)
        self.next()
        return Block(statements)

    # --- statement parsing ---
    def parse_statement(self):
        tok = self.current()
        if tok is None:
            raise ParseError("Unexpected EOF in statement")

        if tok.type == TokenType.KEYWORD:
            if tok.value == "raise":
                self.next()
                str_tok = self.expect(TokenType.STRING)
                self.next()
                self.expect(TokenType.SEMICOLON)
                self.next()
                return RaiseStmt(str_tok.position, StringLiteral(str_tok.position, str_tok.value))

            if tok.value in ("reserve", "noreserve", "endian"):
                self.next()
                arg = None
                cur = self.current()
                if cur is not None:
                    if cur.type == TokenType.KEYWORD:
                        arg = cur.value
                        self.next()
                return SpecialLocal(tok.value, arg)

            if tok.value == "if":
                return self.parse_if()

        if tok.type == TokenType.IDENT:
            return self.parse_declaration()

        raise ParseError(f"Unexpected token {tok.value} in statement at {tok.position}")

    def parse_declaration(self):
        name = self.expect(TokenType.IDENT)
        self.next()
        self.expect(TokenType.COLON)
        self.next()

        type_tok = self.expect(TokenType.IDENT, TokenType.KEYWORD)
        self.next()
        type_expr = Identifier(type_tok.position, type_tok.value)

        array_expr = None
        if self.match(TokenType.BRACK_LEFT):
            self.next()
            size_tok = self.expect(TokenType.IDENT, TokenType.INTEGER, TokenType.SIZE)
            if size_tok.type == TokenType.INTEGER:
                array_expr = NumberLiteral(size_tok.position, size_tok.value, "integer")
            elif size_tok.type == TokenType.SIZE:
                array_expr = NumberLiteral(size_tok.position, size_tok.value, "size")
            else:
                array_expr = Identifier(size_tok.position, size_tok.value)
            self.expect(TokenType.BRACK_RIGHT)
            self.next()

        default_expr = None
        if self.match(TokenType.EQUALS):
            self.next()
            default_expr = self.parse_expression()

        self.expect(TokenType.SEMICOLON)
        self.next()
        return DeclareStatement(name.position, Identifier(name.position, name.value),
                                type_expr, array_expr, default_expr)

    def parse_if(self):
        if_tok = self.expect(TokenType.KEYWORD)
        self.next()
        self.expect(TokenType.PAREN_LEFT)
        self.next()
        cond = self.parse_expression()
        self.expect(TokenType.PAREN_RIGHT)
        self.next()

        if_block = self.parse_block()
        if_block_pos = if_block.statements[0].pos if len(if_block.statements) > 0 else if_tok.position
        if_block_node = ConditionalBlock(if_block_pos, cond, if_block.statements)

        elif_blocks = []
        else_block_node = None

        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.value != "elif":
                break
            elif_tok = cur
            self.next()
            self.expect(TokenType.PAREN_LEFT)
            self.next()
            cond2 = self.parse_expression()
            self.expect(TokenType.PAREN_RIGHT)
            self.next()
            block = self.parse_block()
            block_pos = block.statements[0].pos if len(block.statements) > 0 else elif_tok.position
            elif_blocks.append(ConditionalBlock(block_pos, cond2, block.statements))

        cur = self.current()
        if cur is not None:
            if cur.value == "else":
                else_tok = cur
                self.next()
                block = self.parse_block()
                block_pos = block.statements[0].pos if len(block.statements) > 0 else else_tok.position
                else_block_node = block

        return IfThenElse(if_block_node, elif_blocks, else_block_node)

    # --- top-level parsing ---
    def parse_struct(self):
        name_tok = self.expect(TokenType.IDENT)
        self.next()
        params = []
        if self.match(TokenType.PAREN_LEFT):
            self.next()
            while True:
                cur = self.current()
                if cur is None:
                    break
                if cur.type == TokenType.PAREN_RIGHT:
                    break
                param_tok = self.expect(TokenType.IDENT)
                params.append(Identifier(param_tok.position, param_tok.value))
                self.next()
                if self.match(TokenType.COMMA):
                    self.next()
            self.expect(TokenType.PAREN_RIGHT)
            self.next()
        block = self.parse_block()
        return Struct(name_tok.value, params, block)

    def parse_preprocessor(self):
        tok = self.expect(TokenType.HASHTAG)
        self.next()
        name_tok = self.expect(TokenType.KEYWORD)
        self.next()
        args = []
        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.type != TokenType.IDENT:
                break
            args.append(cur.value)
            self.next()
        return Preprocessor(name_tok.value, args)

    def parse_special_global(self):
        tok = self.expect(TokenType.ATSIGN)
        self.next()
        name_tok = self.expect(TokenType.KEYWORD)
        self.next()
        arg = None
        cur = self.current()
        if cur is not None:
            if cur.type == TokenType.KEYWORD:
                arg = cur.value
                self.next()
        return SpecialGlobal(name_tok.value, arg)

    def parse_program(self):
        items = []
        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.type == TokenType.HASHTAG:
                items.append(self.parse_preprocessor())
                continue
            if cur.type == TokenType.ATSIGN:
                items.append(self.parse_special_global())
                continue
            if cur.type == TokenType.IDENT:
                items.append(self.parse_struct())
                continue
            raise ParseError(f"Unexpected top-level token {cur.value} at {cur.position}")
        return Program(items)
