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

# PRE: "endian little"
# PRE: "noreserve "
def parsePixel(data: bytes, offset: int, extras: dict) -> tuple[dict, int]:
    ctx = {}
    ctx['blue'], offset = type_uint8(data, offset)
    ctx['green'], offset = type_uint8(data, offset)
    ctx['red'], offset = type_uint8(data, offset)
    return ctx, offset

def parseFile(data: bytes, offset: int = 0) -> tuple[dict, int]:
    ctx = {}
    ctx['file_header'], offset = parseFileHeader(data, offset, {})
    ctx['dib_header'], offset = parseDIBHeader(data, offset, {})
    sub_ctx = {
        'width':ctx['dib_header']['width'],
        'height':ctx['dib_header']['height'],
        'bpp':ctx['dib_header']['bpp'],
    }
    ctx['pixels'], offset = parsePixelArray(data, offset, sub_ctx)
    return ctx, offset

def parseFileHeader(data: bytes, offset: int, extras: dict) -> tuple[dict, int]:
    ctx = {}
    ctx['magic'], offset = size(data, offset, '2B')
    ctx['file_size'], offset = type_uint32(data, offset)
    ctx['reserved'], offset = size(data, offset, '4B')
    ctx['pixel_offset'], offset = type_uint32(data, offset)
    return ctx, offset

def parseDIBHeader(data: bytes, offset: int, extras: dict) -> tuple[dict, int]:
    ctx = {}
    ctx['header_size'], offset = type_uint32(data, offset)
    if (ctx['header_size']!=40):
        raise ValueError("Invalid DIB header size")
    
    ctx['width'], offset = type_uint32(data, offset)
    ctx['height'], offset = type_uint32(data, offset)
    ctx['planes'], offset = type_uint16(data, offset)
    if (ctx['planes']!=1):
        raise ValueError("BMP must have 1 plane")
    
    ctx['bpp'], offset = type_uint16(data, offset)
    if (ctx['bpp']!=24):
        raise ValueError("Only 24-bit supported")
    
    ctx['compression'], offset = type_uint32(data, offset)
    if (ctx['compression']!=0):
        raise ValueError("Only uncompressed supported")
    
    ctx['image_size'], offset = type_uint32(data, offset)
    ctx['x_ppm'], offset = type_uint32(data, offset)
    ctx['y_ppm'], offset = type_uint32(data, offset)
    ctx['colors_used'], offset = type_uint32(data, offset)
    ctx['important_colors'], offset = type_uint32(data, offset)
    return ctx, offset

def parsePixelRow(data: bytes, offset: int, extras: dict) -> tuple[dict, int]:
    ctx = {}
    if extras.get('width') is None:
        raise ValueError("Argument for 'width' is not passed")
    if extras.get('bpp') is None:
        raise ValueError("Argument for 'bpp' is not passed")
    ctx['pixels'], offset = type_array(data, offset, parsePixel, int(extras['width']), ({},))
    ctx['padding'], offset = type_array(data, offset, type_uint8, int(((4-((extras['width']*(extras['bpp']/8))%4))%4)), ())
    return ctx, offset

def parsePixelArray(data: bytes, offset: int, extras: dict) -> tuple[dict, int]:
    ctx = {}
    if extras.get('width') is None:
        raise ValueError("Argument for 'width' is not passed")
    if extras.get('height') is None:
        raise ValueError("Argument for 'height' is not passed")
    if extras.get('bpp') is None:
        raise ValueError("Argument for 'bpp' is not passed")
    sub_ctx = {
        'width':extras['width'],
        'bpp':extras['bpp'],
    }
    ctx['rows'], offset = type_array(data, offset, parsePixelRow, int(extras['height']), (sub_ctx,))
    return ctx, offset

