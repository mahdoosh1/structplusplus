from types import NoneType
from .ast_ import *
from .lexer import Token, TokenType

class ParseError(Exception):
    pass

class Parser:
    def __init__(self, filename: str, tokens: list[Token]):
        self.filename = filename
        self.tokens = tokens
        self.index = 0
        
    def _get_token(self, oindex, w=True) -> tuple[Optional[Token], int]:
        if oindex >= len(self.tokens):
            return None, oindex
        index = oindex
        token = self.tokens[index]
        while w and (token.type == TokenType.WHITESPACE) and (index < len(self.tokens)):
            index += 1
            if index >= len(self.tokens):
                return None, index
            token = self.tokens[index]
        return token, index
    
    def _position(self):
        if self.index >= len(self.tokens):
            t = self.tokens[-1]
        else:
            t = self.tokens[self.index]
        return f"(at :{t.position[0]}:{t.position[1]})"
    
    def _raise(self, exception: Exception):
        new_args = (
            self.filename+":",
            *exception.args,
            self._position()
        )
        new_exception = exception.__class__(new_args)
        raise new_exception

    def next(self) -> Optional[Token]:
        self.index += 1
        r, i = self._get_token(self.index)
        
        if r: self.index = i
        else: self.index = i-1
        
        return r

    def peek(self) -> Optional[Token]:
        return self._get_token(self.index+1)[0]
    
    def current(self):
        return self._get_token(self.index)[0]
    
    def safe_next(self):
        r = self.next()
        if r: return r
        self._raise(EOFError("Code ended too early."))
    
    def safe_peek(self):
        r = self.peek()
        if r: return r
        self._raise(EOFError("Code ended too early."))
    
    def safe_current(self):
        r = self.current()
        if r: return r
        self._raise(EOFError("Code ended too early."))
    
    def expect_current(self, *values):
        n = self.current()
        if n is None:
            self._raise(EOFError(f"Code ended too early. Expected any of {values}"))
        if n.type not in values:
            self._raise(ParseError(f"Expected any of {values}. got {n.type}"))
        self.next()
        return n
    
    def expect_next(self, *values):
        n = self.next()
        if n is None:
            self._raise(EOFError(f"Code ended too early. Expected any of {values}"))
        if n.type not in values:
            self._raise(ParseError(f"Expected any of {values}. got {n.type}"))
        return n

    def parse_expression(self, min_prec=0):
        left = self.parse_unary()
        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.type == TokenType.OPERATOR:
                while cur.type == TokenType.OPERATOR and cur.value == ".":
                    field = self.safe_next()
                    if field.type not in (TokenType.IDENT, TokenType.KEYWORD):
                        self._raise(ParseError(f"Expected field after '.'"))
                    if field.type == TokenType.KEYWORD and field.value != "value":
                        self._raise(ParseError(f"Expected field after '.'"))
                    cur = self.safe_next()
                    left = FieldAccess(cur.position, left, field.value)
                if cur.type != TokenType.OPERATOR:
                    break
                prec = self.get_precedence(cur.value)
                if prec < min_prec:
                    break
                op_tok = cur
                self.next()
                right = self.parse_expression(prec + 1)
                left = BinaryOp(left.pos, left, op_tok.value, right)
            else:
                break
        return left
    
    def parse_arrays(self, terminator, return_cur=False, valid_types=None) -> list[Expression]:
        cur = self.safe_current()
        array = []
        while cur.type != terminator:
            array.append(self.parse_expression())
            cur = self.safe_current()
            if cur.type != terminator:
                self.expect_current(TokenType.COMMA)
            if valid_types is not None:
                found = False
                for valid_type in valid_types:
                    if isinstance(array[-1], valid_type):
                        found = True
                        continue
                if not found:
                    self._raise(ParseError(f"Valid types are {valid_types}, got {array[-1].__class__}"))
        if return_cur:
            return array, cur # type: ignore
        return array

    def parse_unary(self):
        cur = self.safe_current()
        if cur.type == TokenType.OPERATOR:
            if cur.value in ("+", "-", "!", "~"):
                op_tok = cur
                self.next()
                operand = self.parse_unary()
                return UnaryOp(op_tok.position, op_tok.value, operand)
            self._raise(ParseError("Unhandled OPERATOR"))

        if cur.type == TokenType.IDENT:
            name = Identifier(cur.position, cur.value)
            peek = self.peek()
            if peek and peek.type == TokenType.PAREN_LEFT:
                self.next() # cur = "("
                self.safe_next() # cur = "..."
                args = self.parse_arrays(TokenType.PAREN_RIGHT)
                self.next() # cur = "..." or None
                return FunctionCall(name.pos, name, args)
            self.next()
            return name

        if cur.type in (TokenType.INTEGER, TokenType.SIZE, TokenType.FLOAT):
            x = NumberLiteral(cur.position, cur.value)
            self.next()
            if cur.type == TokenType.SIZE:
                return Size(cur.position, x)
            return x
        
        if cur.type == TokenType.REGULARSIZE:
            self.next()
            return RegularSize(cur.position, cur.value)

        if cur.type == TokenType.STRING:
            self.next()
            return StringLiteral(cur.position, cur.value)

        if cur.type == TokenType.PAREN_LEFT:
            self.next()
            expr = self.parse_expression()
            self.expect_current(TokenType.PAREN_RIGHT)
            return expr

        self._raise(ParseError(f"Unhandled token {cur.type}"))

    def get_precedence(self, op):
        prec_table = {
            "||": 1, "&&": 2,
            "|": 3, "^": 4, "&": 5,
            "<<": 6, ">>": 6,
            "==": 7, "!=": 7,
            "<": 8, "<=": 8, ">": 8, ">=": 8,
            "+": 9, "-": 9,
            "*": 10, "/": 10, "%": 10,
            ".": 11
        }
        if op in prec_table:
            return prec_table[op]
        return 0

    def parse_code(self):
        self.expect_current(TokenType.BRACE_LEFT)
        code = ""
        while True:
            cur = self.safe_current()
            if cur.type == TokenType.BRACE_RIGHT:
                self.next()
                break
            code += self.parse_code_block()
        return Code(cur.position, code)

    def parse_code_block(self):
        depth = 0
        output = ""
        while True:
            tok = self._get_token(self.index, False)[0]
            if tok is None:
                break
            if tok.type == TokenType.BRACE_RIGHT:
                if depth == 0:
                    break
                depth -= 1
            elif tok.type == TokenType.BRACE_LEFT:
                depth += 1
            output += tok.value
            self.index += 1
        return output

    def parse_block(self):
        self.expect_current(TokenType.BRACE_LEFT)

        statements = []
        while True:
            cur = self.safe_current()
            if cur.type == TokenType.BRACE_RIGHT:
                self.next()
                break
            stmt = self.parse_statement()
            statements.append(stmt)

        return Block(cur.position,statements)

    def parse_statement(self):
        cur = self.safe_current()
        if cur.type == TokenType.KEYWORD:
            if cur.value == "raise":
                # consume 'raise'
                self.next()
                str_tok = self.expect_current(TokenType.STRING)
                self.expect_current(TokenType.SEMICOLON)
                return RaiseStmt(str_tok.position, StringLiteral(str_tok.position, str_tok.value))

            if cur.value == "if":
                return self.parse_if()

        if cur.type == TokenType.HASHTAG:
            return self.parse_preprocessor()
        if cur.type == TokenType.ATSIGN:
            return self.parse_special_local()
        if cur.type == TokenType.IDENT:
            peek = self.peek()
            if peek and peek.type == TokenType.EQUALS:
                return self.parse_assignment()
            return self.parse_declaration()

        self._raise(ParseError(f"Unhandled token {cur.type}"))

    def parse_assignment(self):
        name_tok = self.expect_current(TokenType.IDENT)
        self.expect_current(TokenType.EQUALS)
        value = self.parse_expression()
        self.expect_current(TokenType.SEMICOLON)
        return VariableAssignment(
            name_tok.position,
            Identifier(name_tok.position, name_tok.value),
            value
        )

    def parse_declaration(self):
        name_tok = self.expect_current(TokenType.IDENT)
        self.expect_current(TokenType.COLON)

        type_tok = self.expect_current(TokenType.IDENT, TokenType.REGULARSIZE, TokenType.SIZE)
        if type_tok.type == TokenType.SIZE:
            type_expr = Size(type_tok.position, NumberLiteral(type_tok.position, type_tok.value))
        elif type_tok.type == TokenType.REGULARSIZE:
            type_expr = RegularSize(type_tok.position, type_tok.value)
        else:
            type_expr = Identifier(type_tok.position, type_tok.value)
    
        # check for constructor-style default: Type(...)
        cur = self.safe_current()
        if cur.type == TokenType.PAREN_LEFT:
            if not isinstance(type_expr, Identifier):
                self._raise(ParseError("Only identifiers are allowed"))
            self.next()  # consume '('
            array = self.parse_arrays(TokenType.PAREN_RIGHT)
            self.next()
            type_expr = FunctionCall(type_expr.pos, type_expr, array)
    
        array_expr = None
        cur = self.safe_current()
        if cur.type == TokenType.BRACK_LEFT:
            self.next()  # consume '['
            array_expr = self.parse_expression()
            cur = self.expect_current(TokenType.BRACK_RIGHT)
    
        default = None
        cur = self.safe_current()
        if cur.type == TokenType.EQUALS:
            self.next()  # consume '='
            default = self.parse_expression()
    
        self.expect_current(TokenType.SEMICOLON)
    
        return DeclareStatement(
            name_tok.position,
            Identifier(name_tok.position, name_tok.value),
            type_expr,
            array_expr,
            default
        )

    def parse_if(self):
        if_tok = self.expect_current(TokenType.KEYWORD)
        if if_tok.value != "if":
            self._raise(ParseError(f"Expected 'if'"))

        cond = self.parse_expression()

        if_block = self.parse_block().statements
        if_block = ConditionalBlock(if_tok.position, if_block, cond)

        elif_blocks = []
        else_block = None

        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.type != TokenType.KEYWORD or cur.value != "elif":
                break
            elif_tok = cur
            # consume 'elif'
            self.next()

            cond2 = self.parse_expression()

            block = self.parse_block().statements
            elif_blocks.append(ConditionalBlock(elif_tok.position, block, cond2))

        cur = self.current()
        if cur is not None and cur.type == TokenType.KEYWORD and cur.value == "else":
            # consume 'else'
            self.next()
            else_block = self.parse_block()

        return IfThenElse(if_tok.position, if_block, elif_blocks, else_block)

    # --- top-level parsing ---
    def parse_struct(self):
        struct_type = self.expect_current(TokenType.KEYWORD)
        if struct_type.value not in ("struct", "code"):
            self._raise(ParseError(f"Expected struct type"))
        if struct_type.value == "code":
            code = self.parse_code()
            return code
        name_tok = self.expect_current(TokenType.IDENT)

        params: list[Identifier] = []
        cur = self.safe_current()
        if cur.type == TokenType.PAREN_LEFT:
            self.next()
            params = self.parse_arrays(TokenType.PAREN_RIGHT, valid_types=(Identifier,)) # type: ignore
            self.next()

        block = self.parse_block()
        return Struct(name_tok.position, name_tok.value, params, block)
    
    def parse_preprocessor(self):
        cur = self.expect_current(TokenType.HASHTAG)
        line = cur.position[0]
        name_tok = self.expect_current(TokenType.SPECIAL, TokenType.PREPROCESSOR)
        args = []
        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.position[0] != line:
                break
            if name_tok.type == TokenType.SPECIAL:
                if cur.type != TokenType.KEYWORD:
                    break
            args.append(cur.value)
            self.next()
        if name_tok.type == TokenType.SPECIAL:
            return SpecialGlobal(name_tok.position, name_tok.value, args)
        return Preprocessor(name_tok.position, name_tok.value, args)

    def parse_special_local(self):
        cur = self.expect_current(TokenType.ATSIGN)
        line = cur.position[0]
        name_tok = self.expect_current(TokenType.SPECIAL)
        args = []
        while True:
            cur = self.current()
            if cur is None:
                break
            if cur.position[0] != line:
                break
            if cur.type != TokenType.KEYWORD:
                break
            args.append(cur.value)
            self.next()
        return SpecialLocal(name_tok.position, name_tok.value, args)

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
                items.append(self.parse_special_local())
                continue
            if cur.type == TokenType.KEYWORD:
                items.append(self.parse_struct())
                continue
            print(self.index)
            self._raise(ParseError(f"Unexpected top-level token {cur.value}"))
        return Program(self.filename,items)