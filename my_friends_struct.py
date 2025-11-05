from ctypes import c_uint8, c_uint16, c_uint32, c_int8, c_int16, c_int32, c_float, c_double
from ast import literal_eval

ENDIAN = 'little'

def type_uint8(data, offset):
    if ENDIAN == 'little':
        type_ = c_uint8.__ctype_le__ # type: ignore
    else:
        type_ = c_uint8.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 1

def type_uint16(data, offset):
    if ENDIAN == 'little':
        type_ = c_uint16.__ctype_le__ # type: ignore
    else:
        type_ = c_uint16.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 2

def type_uint32(data, offset):
    if ENDIAN == 'little':
        type_ = c_uint32.__ctype_le__ # type: ignore
    else:
        type_ = c_uint32.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 4

def type_int8(data, offset):
    if ENDIAN == 'little':
        type_ = c_int8.__ctype_le__ # type: ignore
    else:
        type_ = c_int8.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 1

def type_int16(data, offset):
    if ENDIAN == 'little':
        type_ = c_int16.__ctype_le__ # type: ignore
    else:
        type_ = c_int16.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 2

def type_int32(data, offset):
    if ENDIAN == 'little':
        type_ = c_uint32.__ctype_le__ # type: ignore
    else:
        type_ = c_uint32.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 4

def type_float(data, offset):
    if ENDIAN == 'little':
        type_ = c_float.__ctype_le__ # type: ignore
    else:
        type_ = c_float.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 4

def type_double(data, offset):
    if ENDIAN == 'little':
        type_ = c_double.__ctype_le__ # type: ignore
    else:
        type_ = c_double.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 8

def type_array(data, offset, function, array_size, function_args):
    arr = []
    for _ in range(array_size):
        val, offset = function(data, offset, *function_args)
        arr.append(val)
    return arr, offset

def size(data, offset, size):
    offset += size
    if offset > len(data)-1:
        raise ValueError(f"Offset too big: {offset} (maximum {len(data)-1})")
    val = data[offset-size:offset]
    return val, offset

ENDIAN = 'little'
# GLOBAL: "noreserve"
def parseFile(data: bytes, offset: int = 0) -> tuple[dict, int]:
    ctx = {}
    ctx['itemCount'], offset = type_uint8(data, offset)
    ctx['items'], offset = type_array(data, offset, parseItem, int(ctx['itemCount']), ({},))
    return ctx, offset

def parseItem(data: bytes, offset: int, extras: dict) -> tuple[dict, int]:
    ctx = {}
    ctx['info'], offset = type_uint8(data, offset)
    ctx['type'] = ((ctx['info'] & 0x80) == 1)
    if (not ctx.get('type')):
        if (ctx['info'] == 0):
            ctx['mode'] = 'null'
        elif (ctx['info'] == 0x20):
            ctx['mode'] = 'inf'
        elif (ctx['info'] == 0x40):
            ctx['mode'] = 'false'
        elif (ctx['info'] == 0x60):
            ctx['mode'] = 'true'
        else:
            ctx['mode'] = ctx['info']
    else:
        ctx['mode'] = ((ctx['info'] & 0x7F) >> 5)
    ctx['lengthSize'] = ((1 + (ctx['info'] & 0x18)) >> 3)
    ctx['reserved'] = (ctx['info'] & 0x04)
    ctx['id'], offset = type_uint8(data, offset)
    if ctx.get('type'):
        ctx['length'], offset = type_array(data, offset, type_uint8, int(ctx.get('lengthSize')), ())
        ctx['data'], offset = type_array(data, offset, size, int(ctx.get('length')), (1,))
    return ctx, offset



def main():
    from sys import argv
    if len(argv) <= 1:
        return
    test_file = argv[1]
    result = None
    if len(argv) > 2:
        result = argv[2]
    with open(test_file,"rb") as file:
        data = file.read()
    parsed = parseFile(data)
    if result:
        with open(result, "w") as file:
            file.write(str(parsed))

if __name__ == '__main__':
    main()