from . import ast_

PRECODE = """
from ast import literal_eval
from ctypes import c_float, c_double

def type_uint8(data, offset):
    obj = int.from_bytes(data[offset:offset+1],'little')
    return obj, offset + 1

def type_uint16(data, offset):
    obj = int.from_bytes(data[offset:offset+2],'little')
    return obj, offset + 2

def type_uint32(data, offset):
    obj = int.from_bytes(data[offset:offset+4],'little')
    return obj, offset + 4

def type_int8(data, offset):
    obj = int.from_bytes(data[offset:offset+1],'little')
    if obj & 128:
        obj -= 256
    return obj, offset + 1

def type_int16(data, offset):
    obj = int.from_bytes(data[offset:offset+2],'little')
    if obj & 32768:
        obj -= 65536
    return obj, offset + 2

def type_int32(data, offset):
    obj = int.from_bytes(data[offset:offset+4],'little')
    if obj & 2147483648:
        obj -= 4294967296
    return obj, offset + 4

def type_float(data, offset):
    obj = c_float.from_buffer_copy(data, offset).value
    return obj, offset + 4

def type_double(data, offset):
    obj = c_double.from_buffer_copy(data, offset).value
    return obj, offset + 8

def type_array(data, offset, function, array_size, function_args):
    arr = []
    for _ in range(array_size):
        val, offset = function(data, offset, *function_args)
        arr.append(val)
    return arr, offset

def size(data, offset, bytes_):
    n = int(literal_eval(bytes_[:-1]))
    val = int.from_bytes(data[offset:offset+n], 'little')
    return val, offset + n

""".lstrip()

class Generator:
    def __init__(self, ast_tree: ast_.Program):
        self.program = ast_tree
        self.functions = {}
        self.load_functions()
        self.result = PRECODE
        self.depth = 0
        self.indent_ = "    "
        
    def load_functions(self):
        program = self.program
        for statement in program.items:
            if isinstance(statement, ast_.Struct):
                name = statement.name
                parameters = tuple(param.name for param in statement.params)
                self.functions[name] = parameters
    
    def indent(self, text, depth=1):
        return depth*self.indent_ + text.replace('\n','\n'+depth*self.indent_)
    
    def _gen_statement(self, statement: ast_.Statement, extras, certains: list, certain = False):
        if isinstance(statement, ast_.DeclareStatement):
            this_block = ""
            callable_ = ""
            call_arguments = ["data", "offset"]
            if isinstance(statement.type, ast_.Size):
                callable_ = "size"
                call_arguments.append(f"'{statement.type.value.raw}'")
            elif isinstance(statement.type, ast_.RegularSize):
                callable_ = f"type_{statement.type.value}"
            elif isinstance(statement.type, ast_.Identifier):
                parameters = self.functions[statement.type.name]
                if isinstance(statement.default, ast_.CallExpression) and len(parameters) > 0:
                    arguments = (self._gen_expression(argument, extras, certains) for argument in statement.default.args)
                    this_block = "sub_ctx = {\n"
                    for parameter, argument in zip(parameters, arguments):
                        this_block += f"{self.indent_}'{parameter}':{argument},\n"
                    this_block += "}"
                    callable_ = f"parse{statement.type.name}"
                    call_arguments.append("sub_ctx")
                else:
                    callable_ = f"parse{statement.type.name}"
                    call_arguments.append("{}")
            if this_block:
                result_ = this_block+"\n"+f"ctx['{statement.name.name}'], offset = "
            else:
                result_ = f"ctx['{statement.name.name}'], offset = "
            if statement.array_size is not None:
                if len(call_arguments) == 3:
                    call_arguments.append("")
                call_arguments = ", ".join(call_arguments[2:]).strip()
                call_arguments = "("+call_arguments+")"
                size_ = self._gen_expression(statement.array_size, extras, certains)
                result_ += f"type_array(data, offset, {callable_}, int({size_}), {call_arguments})"
            else:
                call_arguments = ", ".join(call_arguments).strip()
                call_arguments = "("+call_arguments+")"
                result_ += f"{callable_}{call_arguments}"
            if certain:
                certains.append(statement.name.name)
            return result_
        elif isinstance(statement, ast_.IfThenElse):
            return self._gen_condition(statement, extras, certains)
        elif isinstance(statement, ast_.RaiseStmt):
            return f"raise ValueError({statement.message.value})"
        print("E: ",statement)
        return ""
    
    def _gen_expression(self, expression: ast_.Expression, extras = None, certains = None, return_certain = False) -> str:
        if isinstance(expression, ast_.Identifier):
            if extras is not None and expression.name in extras:
                if return_certain:
                    return f"extras['{expression.name}']", True # type: ignore
                return f"extras['{expression.name}']"
            if certains is not None and expression.name in certains:
                if return_certain:
                    return f"ctx['{expression.name}']", True # type: ignore
                return f"ctx['{expression.name}']"
            if return_certain:
                return f"ctx.get('{expression.name}')", False # type: ignore
            return f"ctx.get('{expression.name}')"
        if isinstance(expression, ast_.FieldAccess):
            result, is_certain = self._gen_expression(expression.target, extras, certains, True)
            if is_certain:
                if return_certain:
                    return result+f"['{expression.field}']", True # type: ignore
                return result+f"['{expression.field}']"
            if return_certain:
                return result+f".get('{expression.field}')", False # type: ignore
            return result+f".get('{expression.field}')"
        if isinstance(expression, ast_.BinaryOp):
            left = self._gen_expression(expression.left, extras, certains)
            right = self._gen_expression(expression.right, extras, certains)
            result = "("+left+expression.op+right+")"
            if return_certain:
                return result, False # type: ignore
            return result
        if isinstance(expression, ast_.NumberLiteral):
            if return_certain:
                return expression.raw, False # type: ignore
            return expression.raw
        print("X: ",expression)
        return ""
    
    def _gen_condition(self, ifthenelse: ast_.IfThenElse, extras, certains: list):
        this_block = f"if " + self._gen_expression(ifthenelse.if_.condition, extras, certains)+":\n"
        for statement in ifthenelse.if_.statements:
            this_block += f"{self.indent_}{self._gen_statement(statement, extras, certains, False)}\n"
        if len(ifthenelse.elif_) > 0:
            for elif_ in ifthenelse.elif_:
                this_block += f"elif " + self._gen_expression(elif_.condition, extras, certains)+":\n"
                for statement in elif_.statements:
                    this_block += f"{self.indent_}{self._gen_statement(statement, extras, certains, False)}\n"
        if ifthenelse.else_ is not None:
            this_block += "else:\n"
            for statement in ifthenelse.else_.statements:
                self.depth += 1
                this_block += f"{self.indent_}{self._gen_statement(statement, extras, certains, False)}\n"
                self.depth -= 1
        return this_block
    
    def _gen_struct(self, struct: ast_.Struct):
        if isinstance(struct.block, ast_.CodeBlock):
            this_block = struct.block.code
        else:
            if struct.name == "File":
                this_block = f"def parse{struct.name}(data: bytes, offset: int = 0) -> tuple[dict, int]:\n"
            else:
                this_block = f"def parse{struct.name}(data: bytes, offset: int, extras: dict) -> tuple[dict, int]:\n"
            this_block += self.indent_+"ctx = {}\n"
            extras = self.functions[struct.name]
            certains = []
            for parameter in extras:
                this_block += f"{self.indent_}if extras.get('{parameter}') is None:\n"
                this_block += f"{self.indent_*2}raise ValueError(\"Argument for {repr(parameter)} is not passed\")\n"
            for statement in struct.block.statements:
                statement = self._gen_statement(statement, extras, certains, True)
                this_block += self.indent(statement) + "\n"
            this_block += f"{self.indent_}return ctx, offset\n"
        return this_block
    
    def generate(self):
        iterable = self.program.items
        for statement in iterable:
            if isinstance(statement, ast_.Preprocessor):
                this_block = f"# PRE: \"{statement.name} {" ".join(statement.args)}\""
                self.result += this_block
            elif isinstance(statement, ast_.SpecialGlobal):
                this_block = f"# GLOBAL: \"{statement.name} {statement.arg}\""
                self.result += this_block
            elif isinstance(statement, ast_.SpecialLocal):
                this_block = f"# LOCAL: \"{statement.name} {statement.arg}\""
                self.result += this_block
            elif isinstance(statement, ast_.Struct):
                this_block = self._gen_struct(statement)
                self.result += this_block
            else:
                raise ValueError(statement)
            self.result += "\n"
        return self.result