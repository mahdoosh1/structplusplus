from ast_ import *
from lexer import Token, TokenType

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

    # changed: match now checks peek token
    def match(self, *types):
        p = self.peek()
        if p is None:
            return False
        return p.type in types

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
                # consume '.'
                self.next()
                field_tok = self.current()
                if field_tok is None or field_tok.type != TokenType.IDENT:
                    raise ParseError(f"Expected identifier after '.' at {tok.position}")
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
            cur = self.current()
            if cur is None or cur.type != TokenType.PAREN_RIGHT:
                raise ParseError(f"Expected ')' after expression at {tok.position}")
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
        cur = self.current()
        if cur is None or cur.type != TokenType.BRACE_LEFT:
            raise ParseError(f"Expected '{{' at start of block, got {cur}")
        # consume '{'
        self.next()
        statements = []

        while True:
            cur = self.current()
            if cur is None:
                raise ParseError("Unterminated block (expected '}')")
            if cur.type == TokenType.BRACE_RIGHT:
                break
            stmt = self.parse_statement()
            statements.append(stmt)

        # consume '}'
        self.next()
        return Block(cur.position,statements)

    # --- statement parsing ---
    def parse_statement(self):
        tok = self.current()
        if tok is None:
            raise ParseError("Unexpected EOF in statement")

        if tok.type == TokenType.KEYWORD:
            if tok.value == "raise":
                # consume 'raise'
                self.next()
                str_tok = self.current()
                if str_tok is None or str_tok.type != TokenType.STRING:
                    raise ParseError(f"Expected string after raise at {tok.position}")
                self.next()
                semi = self.current()
                if semi is None or semi.type != TokenType.SEMICOLON:
                    raise ParseError(f"Expected ';' after raise at {str_tok.position}")
                self.next()
                return RaiseStmt(str_tok.position, StringLiteral(str_tok.position, str_tok.value))

            if tok.value in ("reserve", "noreserve", "endian"):
                # consume keyword
                self.next()
                arg = None
                cur = self.current()
                if cur is not None and cur.type == TokenType.KEYWORD:
                    arg = cur.value
                    self.next()
                # expect semicolon
                semi = self.current()
                if semi is None or semi.type != TokenType.SEMICOLON:
                    raise ParseError(f"Expected ';' after special local at {tok.position}")
                self.next()
                return SpecialLocal(tok.position, tok.value, arg)

            if tok.value == "if":
                return self.parse_if()

        if tok.type == TokenType.IDENT:
            return self.parse_declaration()

        raise ParseError(f"Unexpected token {tok.value} in statement at {tok.position}")

    def parse_declaration(self):
        name_tok = self.current()
        if name_tok is None or name_tok.type != TokenType.IDENT:
            raise ParseError(f"Expected identifier at start of declaration, got {name_tok}")
        # consume name
        self.next()
    
        cur = self.current()
        if cur is None or cur.type != TokenType.COLON:
            raise ParseError(f"Expected ':' after identifier in declaration at {name_tok.position}")
        # consume ':'
        self.next()
    
        type_tok = self.current()
        if type_tok is None or (type_tok.type != TokenType.IDENT and type_tok.type != TokenType.KEYWORD and type_tok.type != TokenType.SIZE):
            raise ParseError(f"Expected type name after ':' at {name_tok.position}")
        # consume type
        self.next()
        type_expr = Identifier(type_tok.position, type_tok.value)
    
        # check for constructor-style default: Type(...)
        default_expr = None
        cur = self.current()
        if cur is not None and cur.type == TokenType.PAREN_LEFT:
            # type(...) style constructor
            self.next()  # consume '('
            args = []
            while True:
                cur = self.current()
                if cur is None:
                    raise ParseError(f"Unterminated constructor call at {type_tok.position}")
                if cur.type == TokenType.PAREN_RIGHT:
                    break
                arg_expr = self.parse_expression()
                args.append(arg_expr)
                cur = self.current()
                if cur is not None and cur.type == TokenType.COMMA:
                    self.next()  # consume ','
                    continue
                else:
                    break
            # consume ')'
            cur = self.current()
            if cur is None or cur.type != TokenType.PAREN_RIGHT:
                raise ParseError(f"Expected ')' to close constructor at {type_tok.position}")
            self.next()
            default_expr = CallExpression(type_expr.pos, type_expr, args)
    
        array_expr = None
        cur = self.current()
        if cur is not None and cur.type == TokenType.BRACK_LEFT:
            self.next()  # consume '['
            array_expr = self.parse_expression()
            cur = self.current()
            if cur is None or cur.type != TokenType.BRACK_RIGHT:
                raise ParseError(f"Expected ']' after array expression at {type_tok.position}")
            self.next()  # consume ']'
    
        cur = self.current()
        if cur is not None and cur.type == TokenType.EQUALS:
            self.next()  # consume '='
            default_expr = self.parse_expression()
    
        cur = self.current()
        if cur is None or cur.type != TokenType.SEMICOLON:
            raise ParseError(f"Expected ';' after declaration at {type_tok.position}")
        self.next()  # consume ';'
    
        return DeclareStatement(
            name_tok.position,
            Identifier(name_tok.position, name_tok.value),
            type_expr,
            array_expr,
            default_expr
        )

    def parse_if(self):
        if_tok = self.current()
        if if_tok is None or if_tok.type != TokenType.KEYWORD or if_tok.value != "if":
            raise ParseError(f"Expected 'if' at {if_tok}")
        # consume 'if'
        self.next()

        cur = self.current()
        if cur is None or cur.type != TokenType.PAREN_LEFT:
            raise ParseError(f"Expected '(' after if at {if_tok.position}")
        # consume '('
        self.next()

        cond = self.parse_expression()

        cur = self.current()
        if cur is None or cur.type != TokenType.PAREN_RIGHT:
            raise ParseError(f"Expected ')' after if condition at {if_tok.position}")
        # consume ')'
        self.next()

        if_block = self.parse_block()
        if_block_pos = if_block.statements[0].pos if len(if_block.statements) > 0 else if_tok.position
        if_block_node = ConditionalBlock(if_block_pos, if_block.statements, cond)

        elif_blocks = []
        else_block_node = None

        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.value != "elif":
                break
            elif_tok = cur
            # consume 'elif'
            self.next()

            cur = self.current()
            if cur is None or cur.type != TokenType.PAREN_LEFT:
                raise ParseError(f"Expected '(' after elif at {elif_tok.position}")
            self.next()

            cond2 = self.parse_expression()

            cur = self.current()
            if cur is None or cur.type != TokenType.PAREN_RIGHT:
                raise ParseError(f"Expected ')' after elif condition at {elif_tok.position}")
            self.next()

            block = self.parse_block()
            block_pos = block.statements[0].pos if len(block.statements) > 0 else elif_tok.position
            elif_blocks.append(ConditionalBlock(block_pos, block.statements, cond2))

        cur = self.current()
        if cur is not None and cur.value == "else":
            else_tok = cur
            # consume 'else'
            self.next()
            block = self.parse_block()
            else_block_node = block

        return IfThenElse(if_block_node.pos, if_block_node, elif_blocks, else_block_node)

    # --- top-level parsing ---
    def parse_struct(self):
        name_tok = self.current()
        if name_tok is None or name_tok.type != TokenType.IDENT:
            raise ParseError(f"Expected struct name identifier at {self.current()}")
        # consume name
        self.next()

        params = []
        cur = self.current()
        if cur is not None and cur.type == TokenType.PAREN_LEFT:
            # consume '('
            self.next()
            while True:
                cur = self.current()
                if cur is None:
                    raise ParseError("Unterminated parameter list in struct")
                if cur.type == TokenType.PAREN_RIGHT:
                    break
                param_tok = cur
                if param_tok.type != TokenType.IDENT:
                    raise ParseError(f"Expected parameter identifier in struct at {param_tok.position}")
                params.append(Identifier(param_tok.position, param_tok.value))
                # consume param
                self.next()
                cur = self.current()
                if cur is not None and cur.type == TokenType.COMMA:
                    # consume comma
                    self.next()
                    continue
                else:
                    break
            # expect ')'
            cur = self.current()
            if cur is None or cur.type != TokenType.PAREN_RIGHT:
                raise ParseError(f"Expected ')' after struct params at {name_tok.position}")
            # consume ')'
            self.next()

        block = self.parse_block()
        return Struct(name_tok.position, name_tok.value, params, block)

    def parse_preprocessor(self):
        cur = self.current()
        if cur is None or cur.type != TokenType.HASHTAG:
            raise ParseError(f"Expected '#' preprocessor at {cur}")
        # consume '#'
        self.next()
        name_tok = self.current()
        if name_tok is None or name_tok.type != TokenType.KEYWORD:
            raise ParseError(f"Expected preprocessor keyword after '#' at {cur.position}")
        # consume keyword
        self.next()
        args = []
        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.type != TokenType.KEYWORD:
                break
            args.append(cur.value)
            self.next()
        return Preprocessor(name_tok.value, args)

    def parse_special_global(self):
        cur = self.current()
        if cur is None or cur.type != TokenType.ATSIGN:
            raise ParseError(f"Expected '@' special global at {cur}")
        # consume '@'
        self.next()
        name_tok = self.current()
        if name_tok is None or name_tok.type != TokenType.KEYWORD:
            raise ParseError(f"Expected keyword after '@' at {cur.position}")
        # consume keyword
        self.next()
        arg = None
        cur = self.current()
        if cur is not None and cur.type == TokenType.KEYWORD:
            arg = cur.value
            self.next()
        return SpecialGlobal(name_tok.position, name_tok.value, arg)

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
