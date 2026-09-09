"""Camera artwork: MDEC strips decoded through the bundled cam2rgba, the
foreground masks, and PNG encoding."""
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
            if pos >= len(data): break
            n = ((c & 0x7C) >> 2) + 3
            back = ((c & 0x03) << 8) + data[pos] + 1; pos += 1
            start = len(out) - back
            if start < 0: break
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

def decode_fg1(fg1, cam_rgba, w, h):
    """walk an FG1 chunk stream, return (overlay RGBA or None, walked clean).

    Partial blocks carry their own RGB555 pixels in both games, and Exoddus
    keeps every block inside an LZ-compressed sub-stream: the per-row u32
    bitmask form and a game that never compresses are both PC facts. A walk
    that bails at any depth has lost the stride and is dropping blocks, which
    is silent in the output and so is reported rather than left to be noticed."""
    overlay = bytearray(w * h * 4)
    any_px = False
    clean = True
    stack = []          # saved (buffer, pos) while inside compressed sub-streams
    buf, pos = fg1, 4   # skip u32 count
    while True:
        if pos + 12 > len(buf):
            clean = False
            if stack: buf, pos = stack.pop(); continue
            break
        typ, layer, x, y, cw, ch = struct.unpack_from("<HHhhHH", buf, pos)
        if typ == 0xFFFF:            # end
            if stack: buf, pos = stack.pop(); continue
            break
        if typ == 0xFFFC:            # end of compressed sub-stream
            if stack: buf, pos = stack.pop(); continue
            clean = False
            break
        if typ == 0xFFFD:            # compressed sub-stream (layer=decomp size, x=comp size)
            comp = x & 0xFFFF
            if comp < 4 or pos + 12 + comp > len(buf):
                clean = False
                break                # truncated chunk
            sub = decompress_4or5(buf[pos + 12:pos + 12 + comp])
            stack.append((buf, pos + 12 + comp))
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
        if typ == 0:                 # partial block: own RGB555 pixels follow
            px_off = pos + 12
            if px_off + cw * ch * 2 > len(buf):
                clean = False
                break                # truncated chunk
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
        clean = False
        if stack: buf, pos = stack.pop(); continue
        break
    return (bytes(overlay) if any_px else None), clean

def decode_cam(lvl, cam_name, out_png, tmpdir):
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
        got, clean = decode_fg1(part, rgba, w, h)
        if not clean:
            print(f"    ! FG1 stream not walked clean: {cam_name}")
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
