from ctypes import c_uint8, c_uint16, c_uint32, c_uint64, c_int8, c_int16, c_int32, c_int64, c_float, c_double
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

def type_uint64(data, offset):
    if ENDIAN == 'little':
        type_ = c_uint64.__ctype_le__ # type: ignore
    else:
        type_ = c_uint64.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 8

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
        type_ = c_int32.__ctype_le__ # type: ignore
    else:
        type_ = c_int32.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 4

def type_int64(data, offset):
    if ENDIAN == 'little':
        type_ = c_int64.__ctype_le__ # type: ignore
    else:
        type_ = c_int64.__ctype_be__ # type: ignore
    obj = type_.from_buffer_copy(data, offset)
    return obj, offset + 8

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

## CODE_START
def parseFile(unused):
    raise RuntimeError("This is pre-computed code")
## CODE_END

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