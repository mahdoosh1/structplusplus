from ctypes import c_uint8, c_uint16, c_uint32

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

def parse_Pixel(data, offset, extra):
    ctx = extra or {}
    value_blue, offset = to_uint8(data, offset)
    ctx['blue'] = value_blue
    value_green, offset = to_uint8(data, offset)
    ctx['green'] = value_green
    value_red, offset = to_uint8(data, offset)
    ctx['red'] = value_red
    return ctx, offset

def parse_FileHeader(data, offset, extra):
    ctx = extra or {}
    value_magic, offset = to_nB_uint8_array(data, offset, 2)
    ctx['magic'] = value_magic
    value_file_size, offset = to_uint32(data, offset)
    ctx['file_size'] = value_file_size
    value_reserved, offset = to_nB_uint8_array(data, offset, 4)
    ctx['reserved'] = value_reserved
    value_pixel_offset, offset = to_uint32(data, offset)
    ctx['pixel_offset'] = value_pixel_offset
    return ctx, offset

def parse_DIBHeader(data, offset, extra):
    ctx = extra or {}
    value_header_size, offset = to_uint32(data, offset)
    ctx['header_size'] = value_header_size
    if ctx.get('header_size') != 40:
        raise ValueError('Invalid DIB header size')
    value_width, offset = to_uint32(data, offset)
    ctx['width'] = value_width
    value_height, offset = to_uint32(data, offset)
    ctx['height'] = value_height
    value_planes, offset = to_uint16(data, offset)
    ctx['planes'] = value_planes
    if ctx.get('planes') != 1:
        raise ValueError('BMP must have 1 plane')
    value_bpp, offset = to_uint16(data, offset)
    ctx['bpp'] = value_bpp
    if ctx.get('bpp') != 24:
        raise ValueError('Only 24-bit supported')
    value_compression, offset = to_uint32(data, offset)
    ctx['compression'] = value_compression
    if ctx.get('compression') != 0:
        raise ValueError('Only uncompressed supported')
    value_image_size, offset = to_uint32(data, offset)
    ctx['image_size'] = value_image_size
    value_x_ppm, offset = to_uint32(data, offset)
    ctx['x_ppm'] = value_x_ppm
    value_y_ppm, offset = to_uint32(data, offset)
    ctx['y_ppm'] = value_y_ppm
    value_colors_used, offset = to_uint32(data, offset)
    ctx['colors_used'] = value_colors_used
    value_important_colors, offset = to_uint32(data, offset)
    ctx['important_colors'] = value_important_colors
    return ctx, offset

def parse_PixelRow(data, offset, extra):
    ctx = extra or {}
    if ctx.get('width') is None:
        raise ValueError('Missing width in context')
    if ctx.get('bpp') is None:
        raise ValueError('Missing bpp in context')
    array_pixels = []
    for index_pixels in range(int(ctx.get('width'))):
        value_pixels, offset = parse_Pixel(data, offset, ctx)
        array_pixels.append(value_pixels)
    ctx['pixels'] = array_pixels
    array_padding = []
    for index_padding in range(int((4 - (ctx.get('width') * (ctx.get('bpp') / 8)) % 4) % 4)):
        value_padding, offset = to_uint8(data, offset)
        array_padding.append(value_padding)
    ctx['padding'] = array_padding
    return ctx, offset

def parse_PixelArray(data, offset, extra):
    ctx = extra or {}
    if ctx.get('width') is None:
        raise ValueError('Missing width in context')
    if ctx.get('height') is None:
        raise ValueError('Missing height in context')
    if ctx.get('bpp') is None:
        raise ValueError('Missing bpp in context')
    array_rows = []
    for index_rows in range(int(ctx.get('height'))):
        subctx = {
            'width': ctx.get('width'),
            'bpp': ctx.get('bpp')
        }
        value_rows, offset = parse_PixelRow(data, offset, subctx)
        array_rows.append(value_rows)
    ctx['rows'] = array_rows
    return ctx, offset

def parse_File(data, offset, extra):
    ctx = extra or {}
    value_file_header, offset = parse_FileHeader(data, offset, ctx)
    ctx['file_header'] = value_file_header
    value_dib_header, offset = parse_DIBHeader(data, offset, ctx)
    ctx['dib_header'] = value_dib_header
    offset = ctx.get('file_header', {}).get('pixel_offset', offset)
    subctx = {
        'width': ctx.get('dib_header', {}).get('width'),
        'height': ctx.get('dib_header', {}).get('height'),
        'bpp': ctx.get('dib_header', {}).get('bpp')
    }
    value_pixels, offset = parse_PixelArray(data, offset, subctx)
    ctx['pixels'] = value_pixels
    return ctx, offset
