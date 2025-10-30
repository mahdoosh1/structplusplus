from ctypes import c_uint8, c_uint16, c_uint32, c_int8, c_int16, c_int32, c_float, c_double
from ast import literal_eval

def type_uint8(data, offset):
    obj = c_uint8.from_buffer_copy(data, offset)
    return obj, offset + 1

def type_uint16(data, offset):
    obj = c_uint16.from_buffer_copy(data, offset)
    return obj, offset + 2

def type_uint32(data, offset):
    obj = c_uint32.from_buffer_copy(data, offset)
    return obj, offset + 4

def type_int8(data, offset):
    obj = c_int8.from_buffer_copy(data, offset)
    return obj, offset + 1

def type_int16(data, offset):
    obj = c_int16.from_buffer_copy(data, offset)
    return obj, offset + 2

def type_int32(data, offset):
    obj = c_int32.from_buffer_copy(data, offset)
    return obj, offset + 4

def type_float(data, offset):
    obj = c_float.from_buffer_copy(data, offset)
    return obj, offset + 4

def type_double(data, offset):
    obj = c_double.from_buffer_copy(data, offset)
    return obj, offset + 8

def type_array(data, offset, function, array_size, function_extra_argument):
    arr = []
    for _ in range(array_size):
        val, offset = function(data, offset, function_extra_argument)
        arr.append(val)
    return arr, offset

def size(data, offset, bytes_):
    n = int(literal_eval(bytes_[:-1]))
    val = int.from_bytes(data[offset:offset+n], 'little')
    return val, offset + n

# PRE: "endian little"
# PRE: "noreserve "
def parsePixel(data: bytes, offset: int, extras: dict):
    ctx = extras or {}
    ctx['blue'], offset = type_uint8(data, offset)
    ctx['green'], offset = type_uint8(data, offset)
    ctx['red'], offset = type_uint8(data, offset)
    return ctx, offset

def parseFile(data: bytes, offset: int, extras: dict):
    ctx = extras or {}
    ctx['file_header'], offset = parseFileHeader(data, offset, {})
    ctx['dib_header'], offset = parseDIBHeader(data, offset, {})
    subctx = {
        'width':ctx.get('dib_header').get('width'),
        'height':ctx.get('dib_header').get('height'),
        'bpp':ctx.get('dib_header').get('bpp'),
    }
    ctx['pixels'], offset = parsePixelArray(data, offset, subctx)
    return ctx, offset

def parseFileHeader(data: bytes, offset: int, extras: dict):
    ctx = extras or {}
    ctx['magic'], offset = size(data, offset, '2B')
    ctx['file_size'], offset = type_uint32(data, offset)
    ctx['reserved'], offset = size(data, offset, '4B')
    ctx['pixel_offset'], offset = type_uint32(data, offset)
    return ctx, offset

def parseDIBHeader(data: bytes, offset: int, extras: dict):
    ctx = extras or {}
    ctx['header_size'], offset = type_uint32(data, offset)
    if (ctx.get('header_size')!=40):
        raise ValueError("Invalid DIB header size")
    
    ctx['width'], offset = type_uint32(data, offset)
    ctx['height'], offset = type_uint32(data, offset)
    ctx['planes'], offset = type_uint16(data, offset)
    if (ctx.get('planes')!=1):
        raise ValueError("BMP must have 1 plane")
    
    ctx['bpp'], offset = type_uint16(data, offset)
    if (ctx.get('bpp')!=24):
        raise ValueError("Only 24-bit supported")
    
    ctx['compression'], offset = type_uint32(data, offset)
    if (ctx.get('compression')!=0):
        raise ValueError("Only uncompressed supported")
    
    ctx['image_size'], offset = type_uint32(data, offset)
    ctx['x_ppm'], offset = type_uint32(data, offset)
    ctx['y_ppm'], offset = type_uint32(data, offset)
    ctx['colors_used'], offset = type_uint32(data, offset)
    ctx['important_colors'], offset = type_uint32(data, offset)
    return ctx, offset

def parsePixelRow(data: bytes, offset: int, extras: dict):
    ctx = extras or {}
    if ctx.get('width') is None:
        raise ValueError("Argument for 'width' is not passed")
    if ctx.get('bpp') is None:
        raise ValueError("Argument for 'bpp' is not passed")
    ctx['pixels'], offset = type_array(data, offset, parsePixel, ctx.get('width'), ({},))
    ctx['padding'], offset = type_array(data, offset, type_uint8, ((4-((ctx.get('width')*(ctx.get('bpp')/8))%4))%4), ())
    return ctx, offset

def parsePixelArray(data: bytes, offset: int, extras: dict):
    ctx = extras or {}
    if ctx.get('width') is None:
        raise ValueError("Argument for 'width' is not passed")
    if ctx.get('height') is None:
        raise ValueError("Argument for 'height' is not passed")
    if ctx.get('bpp') is None:
        raise ValueError("Argument for 'bpp' is not passed")
    subctx = {
        'width':ctx.get('width'),
        'bpp':ctx.get('bpp'),
    }
    ctx['rows'], offset = type_array(data, offset, parsePixelRow, ctx.get('height'), (subctx,))
    return ctx, offset

