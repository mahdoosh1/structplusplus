# code_gen.py
from .ast_ import Program, Struct, DeclareStatement, CallExpression, FieldAccess, IfThenElse, BinaryOp, RaiseStmt, Identifier, NumberLiteral, StringLiteral, Size

def write_helper_functions(f):
    f.write("""from ctypes import c_uint8, c_uint16, c_uint32

def to_uint8(data, offset):
    raw = data[offset:offset+1]
    if len(raw) < 1:
        raise ValueError(f'Not enough bytes for uint8 at {offset}')
    value = c_uint8.from_buffer_copy(raw).value
    return value, offset + 1

def to_uint16(data, offset):
    raw = data[offset:offset+2]
    if len(raw) < 2:
        raise ValueError(f'Not enough bytes for uint16 at {offset}')
    value = raw[0] | (raw[1] << 8)
    return value, offset + 2

def to_uint32(data, offset):
    raw = data[offset:offset+4]
    if len(raw) < 4:
        raise ValueError(f'Not enough bytes for uint32 at {offset}')
    value = raw[0] | (raw[1] << 8) | (raw[2] << 16) | (raw[3] << 24)
    return value, offset + 4

def to_nB_uint8_array(data, offset, n):
    raw = data[offset:offset+n]
    if len(raw) < n:
        raise ValueError(f'Not enough bytes for {n}B at {offset}')
    array_vals = []
    for b in raw:
        value = c_uint8.from_buffer_copy(bytes([b])).value
        array_vals.append(value)
    return array_vals, offset + n

""")

def ast_to_expr(node):
    """Convert AST expression node to Python expression string"""
    if isinstance(node, FieldAccess):
        return f"{ast_to_expr(node.target)}.get('{node.field}')"
    elif isinstance(node, Identifier):
        return f"ctx.get('{node.name}')"
    elif isinstance(node, NumberLiteral):
        return node.raw
    elif isinstance(node, BinaryOp):
        left = ast_to_expr(node.left)
        right = ast_to_expr(node.right)
        return f"({left} {node.op} {right})"
    else:
        return '0'

def generate_parser(struct: Struct, parse_requires_extra, f):
    """
    Generates a parser function for a given struct and writes to file-like `f`.
    - struct: Struct AST node
    - parse_requires_extra: dict mapping struct name -> tuple of required extra argument names
    """
    name = struct.name
    f.write(f"def parse_{name}(data, offset, extra):\n")
    f.write(f"    ctx = extra or {{}}\n")

    # First check that all required extra args are present
    for param in struct.params:
        f.write(f"    if ctx.get('{param.name}') is None:\n")
        f.write(f"        raise ValueError('Missing {param.name} in context')\n")

    # Iterate over statements in the struct
    for stmt in struct.block.statements:
        if isinstance(stmt, DeclareStatement):
            field_name = stmt.name.name
            type_node = stmt.type
            array_size = stmt.array_size

            # Convert type/size node to string representation
            if isinstance(type_node, Identifier):
                type_name = type_node.name
            elif isinstance(type_node, Size):
                # fixed-size byte array
                n_bytes = int(type_node.value.raw[:-1])
                type_name = f"{n_bytes}B"
            else:
                type_name = "unknown"

            # Fixed-size byte arrays
            if type_name.endswith("B") and type_name[:-1].isdigit():
                n_bytes = int(type_name[:-1])
                f.write(f"    value_{field_name}, offset = to_nB_uint8_array(data, offset, {n_bytes})\n")
                f.write(f"    ctx['{field_name}'] = value_{field_name}\n")
                continue

            # Array fields
            if array_size is not None:
                # Determine length expression
                if isinstance(array_size, Identifier):
                    length_expr = f"int(ctx.get('{array_size.name}'))"
                else:
                    # For complex expressions (e.g. padding)
                    length_expr = ast_to_expr(array_size)  # convert AST expr to Python
                f.write(f"    array_{field_name} = []\n")
                f.write(f"    for index_{field_name} in range({length_expr}):\n")

                # Determine call for element
                if type_name in parse_requires_extra:
                    extra_args = parse_requires_extra[type_name]
                    f.write(f"        subctx = {{")
                    f.write(", ".join([f"'{arg}': ctx.get('{arg}')" for arg in extra_args]))
                    f.write("}\n")
                    f.write(f"        value_{field_name}, offset = parse_{type_name}(data, offset, subctx)\n")
                else:
                    f.write(f"        value_{field_name}, offset = parse_{type_name}(data, offset, ctx)\n")
                f.write(f"        array_{field_name}.append(value_{field_name})\n")
                f.write(f"    ctx['{field_name}'] = array_{field_name}\n")
                continue

            # Single struct/primitive field
            if type_name in parse_requires_extra:
                # Requires extra arguments → define subctx
                extra_args = parse_requires_extra[type_name]
                f.write(f"    subctx = {{")
                f.write(", ".join([f"'{arg}': ctx.get('{arg}')" for arg in extra_args]))
                f.write("}\n")
                f.write(f"    value_{field_name}, offset = parse_{type_name}(data, offset, subctx)\n")
            else:
                # Primitive types
                f.write(f"    value_{field_name}, offset = to_{type_name}(data, offset)\n")
            f.write(f"    ctx['{field_name}'] = value_{field_name}\n")

    f.write(f"    return ctx, offset\n\n")

def generate_code(program: Program, f):
    write_helper_functions(f)
    functions = {}
    for struct in program.items:
        if isinstance(struct, Struct):
            params = tuple([p.name for p in struct.params])
            functions[struct.name] = params
    for struct in program.items:
        if isinstance(struct, Struct):
            generate_parser(struct, functions, f)
