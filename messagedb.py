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

def size(data, offset, bytes_):
    n = int(literal_eval(bytes_[:-1]))
    val = data[offset:offset+n]
    return val, offset + n

ENDIAN = 'little'
# GLOBAL: "noreserve"
def parseFile(data: bytes, offset: int = 0) -> tuple[dict, int]:
    ctx = {}
    ctx['num_messages'], offset = type_uint32(data, offset)
    ctx['messages'], offset = type_array(data, offset, parseMessage, int(ctx['num_messages'].value), ({},))
    return ctx, offset

def parseMessage(data: bytes, offset: int, extras: dict) -> tuple[dict, int]:
    ctx = {}
    ctx['user_id'], offset = type_uint32(data, offset)
    ctx['message_id'], offset = type_uint32(data, offset)
    ctx['reply_id'], offset = type_uint32(data, offset)
    ctx['message_length'], offset = type_uint32(data, offset)
    ctx['message'], offset = type_array(data, offset, size, int(((ctx['message_length'].value+3)/4)), ('4B',))
    return ctx, offset

