"""Camera artwork: MDEC strips decoded through the bundled cam2rgba, both games'
foreground-mask formats, and PNG encoding."""
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

from oddmap.disc import parse_chunks
from oddmap.paths import CAM2RGBA, HERE

OXIPNG = shutil.which("oxipng")

def ensure_tools():
    global OXIPNG
    OXIPNG = shutil.which("oxipng")
    if not OXIPNG:
        sys.exit("oxipng is required so rebuilds stay byte-identical to the committed images "
                 "(brew install oxipng / cargo install oxipng)")
    if CAM2RGBA.exists():
        return
    print("compiling cam2rgba...")
    subprocess.run(["c++", "-O2", "-std=c++17", f"-I{HERE}", "-include", "Types.hpp",
                    str(HERE / "cam2rgba.cpp"), str(HERE / "PSXMDECDecoder.cpp"),
                    "-o", str(CAM2RGBA)], check=True)

def write_png(path, w, h, rgba, keep_alpha=False):
    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c))
    rgba = bytearray(rgba)
    if not keep_alpha:
        for i in range(3, len(rgba), 4):
            rgba[i] = 255
    scan = b"".join(b"\x00" + bytes(rgba[y*w*4:(y+1)*w*4]) for y in range(h))
    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(scan, 6))
           + chunk(b"IEND", b""))
    Path(path).write_bytes(png)
    # lossless recompression (~30% smaller); pixel data is unchanged by design
    subprocess.run([OXIPNG, "-o", "2", "--strip", "safe", "-q", str(path)], check=True)

def decompress_4or5(data):
    """alive LZ variant: 0xxxxxxx = literals run, 1xxxxxyy yyyyyyyy = back-copy"""
    dst_len = struct.unpack_from("<I", data, 0)[0]
    out = bytearray()
    pos = 4
    while len(out) < dst_len and pos < len(data):
        c = data[pos]; pos += 1
        if c & 0x80:
            n = ((c & 0x7C) >> 2) + 3
            back = ((c & 0x03) << 8) + data[pos] + 1; pos += 1
            start = len(out) - back
            for i in range(n):
                out.append(out[start + i])
        else:
            n = c + 1
            out += data[pos:pos + n]
            pos += n
    return bytes(out)

def rgb555(px):
    r = (px & 0x1F) << 3; g = ((px >> 5) & 0x1F) << 3; b = ((px >> 10) & 0x1F) << 3
    return bytes((r | r >> 5, g | g >> 5, b | b >> 5, 255))

def decode_fg1(fg1, cam_rgba, w, h, bitmask_format):
    """walk an FG1 chunk stream, return overlay RGBA (or None if empty).

    Partial blocks carry RGB555 pixels in AO and per-row u32 bitmasks (over the
    camera bitmap) in AE; compressed sub-streams only exist in AO."""
    overlay = bytearray(w * h * 4)
    any_px = False
    stack = []          # saved (buffer, pos) while inside compressed sub-streams
    buf, pos = fg1, 4   # skip u32 count
    while True:
        if pos + 12 > len(buf):
            if stack: buf, pos = stack.pop(); continue
            break
        typ, layer, x, y, cw, ch = struct.unpack_from("<HHhhHH", buf, pos)
        if typ == 0xFFFF:            # end
            if stack: buf, pos = stack.pop(); continue
            break
        if typ == 0xFFFC:            # end of compressed sub-stream
            buf, pos = stack.pop(); continue
        if typ == 0xFFFD:            # compressed sub-stream (layer=decomp size, x=comp size)
            sub = decompress_4or5(buf[pos + 12:pos + 12 + (x & 0xFFFF)])
            stack.append((buf, pos + 12 + (x & 0xFFFF)))
            buf, pos = sub, 0
            continue
        if typ == 0xFFFE:            # full block: copy cam pixels
            for j in range(ch):
                yy = y + j
                if not (0 <= yy < h): continue
                x0 = max(0, x); x1 = min(w, x + cw)
                if x1 > x0:
                    o = (yy * w + x0) * 4
                    overlay[o:o + (x1 - x0) * 4] = cam_rgba[o:o + (x1 - x0) * 4]
                    any_px = True
            pos += 12
            continue
        if typ == 0:                 # partial block
            if bitmask_format:       # AE: one u32 bitmask per row selecting cam pixels
                if pos + 12 + ch * 4 > len(buf):
                    break            # truncated chunk
                for j in range(ch):
                    yy = y + j
                    if not (0 <= yy < h): continue
                    bits = struct.unpack_from("<I", buf, pos + 12 + j * 4)[0]
                    for i in range(min(cw, 32)):
                        if bits >> i & 1:
                            xx = x + i
                            if 0 <= xx < w:
                                o = (yy * w + xx) * 4
                                overlay[o:o + 4] = cam_rgba[o:o + 4]
                                any_px = True
                pos += 12 + ch * 4
            else:                    # AO: own RGB555 pixels follow
                px_off = pos + 12
                if px_off + cw * ch * 2 > len(buf):
                    break            # truncated chunk
                for j in range(ch):
                    yy = y + j
                    for i in range(cw):
                        px = struct.unpack_from("<H", buf, px_off + (j * cw + i) * 2)[0]
                        if px == 0: continue
                        xx = x + i
                        if 0 <= xx < w and 0 <= yy < h:
                            overlay[(yy * w + xx) * 4:(yy * w + xx) * 4 + 4] = rgb555(px)
                            any_px = True
                pos = px_off + cw * ch * 2
            continue
        # unknown chunk type: bail out of this stream
        if stack: buf, pos = stack.pop(); continue
        break
    return bytes(overlay) if any_px else None

def decode_cam(lvl, cam_name, out_png, tmpdir, bitmask_fg1):
    try:
        cam = lvl.read(cam_name + ".CAM")
    except KeyError:
        print(f"    ! cam file missing: {cam_name}.CAM")
        return False
    chunks = parse_chunks(cam)
    bits = next((v for (tag, _), v in chunks.items() if tag == "Bits"), None)
    if not bits:
        return False
    bits_file = tmpdir / "cam.bits"
    rgba_file = tmpdir / "cam.rgba"
    bits_file.write_bytes(bits)
    r = subprocess.run([str(CAM2RGBA), str(bits_file), str(rgba_file)], capture_output=True)
    if r.returncode != 0:
        print(f"    ! cam decode failed: {cam_name}")
        return False
    raw = rgba_file.read_bytes()
    w, h = struct.unpack_from("<II", raw, 0)
    rgba = raw[8:]
    # the MDEC stream pads 368 visible columns up to 384 (24 macroblocks);
    # crop the junk columns off before writing
    VISIBLE_W = 368
    if w > VISIBLE_W:
        rgba = b"".join(rgba[y*w*4:(y*w + VISIBLE_W)*4] for y in range(h))
        w = VISIBLE_W
    write_png(out_png, w, h, rgba)

    # foreground occlusion overlay from the FG1 chunk(s)
    fg_png = out_png.with_name(out_png.stem + "_fg.png")
    fg_parts = [v for (tag, _), v in chunks.items() if tag == "FG1 "]
    overlay = None
    for part in fg_parts:
        got = decode_fg1(part, rgba, w, h, bitmask_fg1)
        if got is None:
            continue
        if overlay is None:
            overlay = bytearray(got)
        else:
            for px in range(0, len(got), 4):
                if got[px + 3]:
                    overlay[px:px + 4] = got[px:px + 4]
    if overlay:
        write_png(fg_png, w, h, bytes(overlay), keep_alpha=True)
    return True
