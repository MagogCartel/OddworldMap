#!/usr/bin/env python3
"""
Oddworld interactive map builder (PS1 NTSC-U).

Reads game disc images directly, extracts every level's path data
(camera grid, TLV objects, collision lines) and camera backgrounds
(MDEC-compressed, decoded via the bundled cam2rgba tool built from
alive_reversing's PSXMDECDecoder), and emits the data files for the viewer.

Supports both games:
  python3 build_map.py --game AO --disc "Oddworld - Abe's Oddysee.bin"
  python3 build_map.py --game AE --disc "Exoddus (Disc 1).bin" "Exoddus (Disc 2).bin"

--disc defaults to $ODDWORLD_DISC_AO (AO) / $ODDWORLD_DISC_AE (AE, os.pathsep-separated).
"""
import argparse
import gzip
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

from oddmap.paths import CAM2RGBA, HERE, SITE
from oddmap.tables import AE_LEVEL_DISPLAY, AO_LEVELS, AO_R2_ZULAGS, AO_TLV_NAMES
from oddmap.disc import Disc, Lvl, parse_chunks

from oddmap.decomp import load_cache, parse_pathdata_cpp_ae, parse_pathdata_cpp_ao

from oddmap.schema import load_object_schema, parse_enum_labels
from oddmap.tlv import (discover_path_meta, tlv_extra_ae, tlv_extra_ao,
                        walk_obj_region)


# decomp quirks corrected when emitting field_types (the schema cache stays
# faithful to the source): a field whose declared type contradicts its meaning
# gets the type it behaves as, keyed (game, object, field)
_FIELD_TYPE_OVERRIDES = {
    # a boolean declared as a direction instead of choice
    ("AE", "SligSpawner", "chase_abe_when_spotted"): "Choice_short",
    # an enum the member-type parser can't reach: Path_Drill_Data sits outside the Tlvs include graph
    ("AE", "Drill", "start_direction"): "DrillDirection",
}

def write_field_types(game_key, out):
    """the viewer's field->game-type sidecar for one game: {object: {field: type}}
    over the enum-typed fields only. Derived from the schema cache alone (no disc),
    keyed by object name the way the viewer sees it, so it maps a shown field to
    the type its value transform is keyed by."""
    game = game_setup(game_key)
    ft = {}
    for tid, rows in game["schema"].items():
        name = game["tlv_names"].get(tid)
        typed = {r[1]: r[2] for r in rows if len(r) > 2}
        if name and typed:
            ft[name] = {k: typed[k] for k in sorted(typed)}
    names = {game["tlv_names"].get(tid): rows for tid, rows in game["schema"].items()}
    for (gk, obj, fld), ty in _FIELD_TYPE_OVERRIDES.items():
        if gk == game_key:
            if all(r[1] != fld for r in names.get(obj) or []):
                raise RuntimeError(f"stale field-type override: {gk} {obj}.{fld}")
            ft.setdefault(obj, {})[fld] = ty
    dst = out / game["field_types_file"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps({k: ft[k] for k in sorted(ft)}, indent=1))
    print(f"field types -> {dst} ({len(ft)} object types)")
    return dst

def write_enum_labels(game_key, out):
    """the viewer's enum-value labels sidecar for one game: {type: {value: label}}.
    Generated from the decomp (no disc) so the viewer renders enum ints as words
    without hand-maintaining them; keyed by the same game type as field_types and
    limited to the types some field is actually declared as, so it ships only
    labels the viewer can use (the decomp defines many enums that aren't fields)."""
    game = game_setup(game_key)
    used = {r[2] for tid, rows in game["schema"].items() if game["tlv_names"].get(tid)
            for r in rows if len(r) > 2}
    used |= {ty for (gk, _, _), ty in _FIELD_TYPE_OVERRIDES.items() if gk == game_key}
    labels, bad = parse_enum_labels(game_key)
    broken = used & bad
    if broken:  # a used type must never ship silently unlabelled or mislabelled
        raise RuntimeError(f"{game_key}: field types with unlabelable enums: {sorted(broken)}")
    kept = {t: {str(v): labels[t][v] for v in sorted(labels[t])}
            for t in sorted(labels) if t in used}
    dst = out / game["enum_labels_file"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(json.dumps(kept, indent=1))
    print(f"enum labels -> {dst} ({len(kept)} of {len(labels)} enum types used)")
    return dst

# --------------------------------------------------- in-game message tables

# The scroll-in run of spaces every LCD message opens with; the engine's own
# source calls it out as something that should have been added at runtime.
MESSAGE_LEAD = " " * 31

# Button commands a message can name, as the font's own code points. Only the
# viewer names them; the build fails on a code outside this range so a name can
# never be missing at the point one is needed.
MESSAGE_BUTTONS = range(0x08, 0x14)

# The string tables to lift, per game: (anchor, the anchor's index, entries).
# Each is a pointer array plus a 4-byte-aligned string blob compiled into the
# level overlays rather than into the executable, so the sweep reads *.OVL.
MESSAGE_TABLES = {
    "AO": {
        "lcd": (MESSAGE_LEAD + "The profits justify the means.", 1, 90),
        "hintfly": ("SNEAK TO BOMB", 0, 36),
    },
    "AE": {
        "lcd": (MESSAGE_LEAD + "SoulStorm Mining Company is an equal opportunity employer.", 1, 101),
    },
}

def string_table(blob, anchor, lead, count):
    """the `count` C strings of a pointer table whose entry `lead` is `anchor`.

    Anchoring on a string rather than an address derives the overlay's load base
    from the data itself. The table is found by the run of gaps between the first
    strings, which is a signature no other array shares, and is believed only if
    the slot past its declared end points nowhere: that is what makes the length
    self-proving rather than asserted."""
    at = blob.find(anchor.encode("latin1"))
    if at < 0:
        return None
    starts, pos = [], at
    for _ in range(8):
        end = blob.find(b"\x00", pos)
        if end < 0:
            return None             # the anchor sits too near the end to read a run
        starts.append(pos)
        pos = end + 1
        while pos < len(blob) and blob[pos] == 0:   # alignment padding between strings
            pos += 1
        if pos >= len(blob):
            return None
    gaps = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
    words = struct.unpack_from(f"<{len(blob) // 4}I", blob, 0)
    table = None
    for q in range(lead, len(words) - max(count - lead, len(gaps))):
        if all(words[q + i + 1] - words[q + i] == gaps[i] for i in range(len(gaps))):
            table = q - lead
            break
    if table is None:
        return None
    base = words[table + lead] - starts[0]
    out = []
    for i in range(count):
        off = words[table + i] - base
        end = blob.find(b"\x00", off) if 0 <= off < len(blob) else -1
        if end < 0:
            return None
        out.append(blob[off:end].decode("latin1"))
    if 0 <= words[table + count] - base < len(blob):
        return None
    return out

def extract_messages(game_key, discs):
    """the game's message tables, read from every overlay carrying them.

    Each table is compiled into every overlay whose level needs it, so the copies
    are a free cross-check: they must all agree, and one disagreeing means the
    tables are per-level and nothing here holds. An overlay holding the anchor
    but no readable table is that same disagreement wearing a different length,
    so it raises."""
    specs = sorted(MESSAGE_TABLES[game_key].items())
    seen = {name: {} for name, _ in specs}
    unreadable = {name: [] for name, _ in specs}
    copies = {name: 0 for name, _ in specs}
    for disc in discs:
        for ovl in sorted(f for f in disc.files if f.endswith(".OVL")):
            blob = disc.read(*disc.files[ovl])       # read once, offered to every table
            for name, (anchor, lead, count) in specs:
                if anchor.encode("latin1") not in blob:
                    continue
                found = string_table(blob, anchor, lead, count)
                if found is None:
                    unreadable[name].append(ovl)
                else:
                    seen[name].setdefault(tuple(found), []).append(ovl)
                    copies[name] += 1
    out = {}
    for name, (_, _, count) in specs:
        if unreadable[name]:
            raise RuntimeError(f"{game_key}: {name} message table unreadable in "
                               f"{','.join(unreadable[name])}, which carries its text")
        if not seen[name]:
            raise RuntimeError(f"{game_key}: no overlay carries the {name} message table")
        if len(seen[name]) > 1:
            raise RuntimeError(f"{game_key}: overlays disagree on the {name} message table: "
                               + "; ".join(",".join(v) for v in seen[name].values()))
        # the scroll-in lead is spaces; stripping whitespace would also eat a
        # trailing button code, 0x09-0x0d being both
        table = [s.strip(" ") for s in next(iter(seen[name]))]
        for msg in table:
            unknown = {c for c in msg if ord(c) < 0x20 and ord(c) not in MESSAGE_BUTTONS}
            if unknown:
                raise RuntimeError(f"{game_key} {name}: unnamed button code(s) "
                                   f"{sorted(hex(ord(c)) for c in unknown)} in {msg!r}")
        out[name] = table
        print(f"  {name}: {sum(1 for s in table if s)} of {count} messages, "
              f"{copies[name]} identical copies")
    return out

def message_json(tables):
    """the tables as JSON, every button code written \\u00XX.

    json's shorthand for 0x08-0x0d would put \\n and \\t in the middle of a
    sentence, where they read as whitespace rather than as the button they are.
    No message contains a backslash, which is what makes rewriting them exact."""
    text = json.dumps(tables, indent=1)
    for shorthand, code in (("b", 0x08), ("t", 0x09), ("n", 0x0A),
                            ("f", 0x0C), ("r", 0x0D)):
        text = text.replace("\\" + shorthand, "\\u%04x" % code)
    return text

def write_messages(game_key, discs, out):
    """the viewer's message sidecar for one game: {table: [message by id]}.

    Needs the discs: the decomp carries both LCD tables in source, but those are
    the PC build's and differ from PS1's in wording, not only in button names."""
    tables = extract_messages(game_key, discs)
    if any("\\" in msg for t in tables.values() for msg in t):
        raise RuntimeError(f"{game_key}: a message contains a backslash")
    dst = out / GAMES[game_key]["messages_file"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(message_json(tables))
    print(f"messages -> {dst}")
    return dst


# --------------------------------------------------------------- PNG encoding

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

# ------------------------------------------------------------- game profiles

GAMES = {
    "AO": {
        "title": "Oddworld: Abe's Oddysee",
        "data_file": "map_data_ao.json",
        "cams_dir": "cams/ao",
        "cache": "pathdata_ao.json",
        "schema_cache": "objects_ao.json",
        "field_types_file": "field_types_ao.json",
        "enum_labels_file": "enum_labels_ao.json",
        "messages_file": "messages_ao.json",
        "env": "ODDWORLD_DISC_AO",
        "geometry": {"cellW": 368, "cellH": 240, "worldW": 1024, "worldH": 480,
                     "winX": 256, "winY": 120, "visW": 368, "visH": 240},
        "tlv": {"header_len": 0x18, "rect_off": 0x10, "min_len": 24, "max_len": 480,
                "max_type": 115, "check_flags": True, "extra_fn": tlv_extra_ao},
        "fg1_bitmask": False,
        "parse_tables": parse_pathdata_cpp_ao,
    },
    "AE": {
        "title": "Oddworld: Abe's Exoddus",
        "data_file": "map_data_ae.json",
        "cams_dir": "cams/ae",
        "cache": "pathdata_ae.json",
        "schema_cache": "objects_ae.json",
        "field_types_file": "field_types_ae.json",
        "enum_labels_file": "enum_labels_ae.json",
        "messages_file": "messages_ae.json",
        "env": "ODDWORLD_DISC_AE",
        "geometry": {"cellW": 368, "cellH": 240, "worldW": 375, "worldH": 260,
                     "winX": 0, "winY": 0, "visW": 368, "visH": 240},
        "tlv": {"header_len": 0x10, "rect_off": 0x08, "min_len": 16, "max_len": 512,
                "max_type": 150, "check_flags": False, "extra_fn": tlv_extra_ae},
        "fg1_bitmask": True,
        "parse_tables": parse_pathdata_cpp_ae,
    },
}

def game_setup(game_key):
    """resolve per-game level list, tlv names and tables (loading the cache)"""
    game = dict(GAMES[game_key])
    cache = load_cache(game)
    if game_key == "AO":
        game["levels"] = AO_LEVELS
        game["tlv_names"] = AO_TLV_NAMES
        game["tables"] = {short: {int(k): v for k, v in paths.items()} for short, paths in cache.items()}
    else:
        game["levels"] = [tuple(l) for l in cache["levels"]]
        game["tlv_names"] = {int(k): v for k, v in cache["tlv_names"].items()}
        game["tables"] = {short: {int(k): v for k, v in paths.items()} for short, paths in cache["tables"].items()}
        game["tlv"] = dict(game["tlv"])
        game["tlv"]["max_type"] = max(game["tlv_names"])
    # TLV destinations name ender level ids too, so the id map must cover every
    # id, not just the one kept per archive in the level list
    game["level_short"] = {lid: s for lid, s, _ in game["levels"]} if game_key == "AO" \
        else {int(k): v for k, v in cache["id_to_short"].items()}
    # the layout overrides are checked against tlv_names, so the schema resolves after it
    game["schema"] = load_object_schema(game_key, game)
    return game

# ----------------------------------------------------------------------- main

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

CACHE_NAME_LINE = re.compile(r'(?m)^const CACHE_NAME = "[^"]*";$')

def cams_stamp(cams_dir):
    """name the artwork cache after the artwork, so regenerating a PNG expires it
    and a build that decodes nothing leaves every visitor's copy alone. One worker
    serves both games, so the stamp answers to either tree."""
    h = hashlib.sha1()
    for rel in sorted(p.relative_to(cams_dir).as_posix() for p in cams_dir.rglob("*.png")):
        h.update(rel.encode())
        h.update(hashlib.sha1((cams_dir / rel).read_bytes()).digest())
    return f"cams-{h.hexdigest()[:12]}"

def require_stampable(sw_file):
    """a worker that cannot be stamped fails before the build spends its time,
    not after it has written everything except the line it could not find"""
    if not CACHE_NAME_LINE.search(sw_file.read_text()):
        sys.exit(f"{sw_file.name}: no CACHE_NAME line to stamp")

def stamp_cache_name(sw_file, cams_dir):
    name = cams_stamp(cams_dir)
    src = sw_file.read_text()
    new, hits = CACHE_NAME_LINE.subn(f'const CACHE_NAME = "{name}";', src, count=1)
    if not hits:  # returning a name nothing carries would report a stamp that isn't there
        sys.exit(f"{sw_file.name}: no CACHE_NAME line to stamp")
    if new != src:
        sw_file.write_text(new)
    return name

def print_build_summary(game_key, built, data_file, all_levels, cam_stats, cache_name):
    """report card for the finished build: geometry counts, object-field
    coverage, the raw= health line, the data file's on-disk + gzip size, and the
    name the artwork cache now carries.
    `built` is the levels built this run — a subset build merges into a larger
    file, whose full level count is reported alongside."""
    paths = sum(len(L["paths"]) for L in built)
    lines = sum(len(P["lines"]) for L in built for P in L["paths"])
    tlvs = [t for L in built for P in L["paths"] for t in P["tlvs"]]
    types = {t["name"] for t in tlvs}
    with_fields = sum(1 for t in tlvs if "fields" in t)
    raw = {}
    for t in tlvs:
        if "raw" in t.get("extra", {}):
            raw[t["name"]] = raw.get(t["name"], 0) + 1
    blob = data_file.read_bytes()
    cams = cam_stats["reused"] + cam_stats["decoded"] + cam_stats["failed"]

    def row(k, v):
        print(f"  {k:<10} {v}")
    print(f"\n=== {game_key} build summary ===")
    scope = f" of {len(all_levels)} in the file" if len(built) != len(all_levels) else ""
    row("levels", f"{len(built)} built{scope}")
    row("paths", paths)
    row("cameras", f"{cams}  ({cam_stats['decoded']} decoded, {cam_stats['reused']} reused"
        + (f", {cam_stats['failed']} missing/failed" if cam_stats["failed"] else "") + ")")
    row("collision", f"{lines} lines")
    row("objects", f"{len(tlvs)} TLVs across {len(types)} types")
    if tlvs:
        row("fields", f"{with_fields} carry an archive ({100 * with_fields // len(tlvs)}% of objects)")
    row("raw=", f"{sum(raw.values())} undecoded across {len(raw)} types {raw} — will fail the invariant test"
        if raw else "0 (every object decoded)")
    row("data file", f"{data_file.name}  {len(blob) / 1e6:.1f} MB raw / {len(gzip.compress(blob)) // 1024} KB gzip")
    if cache_name:
        row("cam cache", cache_name)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", default="AO", choices=sorted(GAMES),
                    help="which game to build (default AO)")
    ap.add_argument("--disc", nargs="+",
                    help="raw PS1 disc image(s) (.bin, 2352-byte sectors); AE takes both discs. "
                         "Defaults to $ODDWORLD_DISC_AO / $ODDWORLD_DISC_AE")
    ap.add_argument("--out", default=str(SITE))
    ap.add_argument("--levels", default="", help="comma list of level shorts to limit (e.g. R2,R6)")
    ap.add_argument("--emit-field-data", action="store_true",
                    help="regenerate the viewer sidecars field_types_{ao,ae}.json and "
                         "enum_labels_{ao,ae}.json from the decomp (no disc needed) and exit")
    args = ap.parse_args()

    if args.emit_field_data:
        for gk in sorted(GAMES):
            write_field_types(gk, Path(args.out))
            write_enum_labels(gk, Path(args.out))
        return

    game = game_setup(args.game)
    discs_arg = args.disc or [p for p in os.environ.get(game["env"], "").split(os.pathsep) if p]
    if not discs_arg:
        ap.error(f"no disc image: pass --disc or set ${game['env']}")

    ensure_tools()
    out = Path(args.out)
    if (out / "sw.js").exists():
        require_stampable(out / "sw.js")
    (out / game["cams_dir"]).mkdir(parents=True, exist_ok=True)
    tmpdir = HERE / ".tmp"
    tmpdir.mkdir(exist_ok=True)

    only = set(s.strip().upper() for s in args.levels.split(",") if s.strip())
    discs = [Disc(p) for p in discs_arg]
    tables = game["tables"]
    level_short = game["level_short"]

    data = {"id": args.game, "game": game["title"], "geometry": game["geometry"], "levels": []}
    cam_stats = {"reused": 0, "decoded": 0, "failed": 0}
    for lid, short, display in game["levels"]:
        if only and short not in only:
            continue
        if short not in tables:
            continue
        lvl_file = f"{short}.LVL"
        # multi-disc games carry stub copies of the other disc's levels
        # (paths present, cam files absent), so pick the largest instance
        having = [d for d in discs if lvl_file.upper() in d.files]
        if not having:
            print(f"{short}: no {lvl_file} on disc, skipping")
            continue
        disc = max(having, key=lambda d: d.files[lvl_file.upper()][1])
        print(f"=== {short} ({display}) ===")
        try:
            lvl = Lvl(disc, lvl_file)
        except (ValueError, EOFError) as ex:
            print(f"  skipping: {ex}")
            continue
        bnd_name = f"{short}PATH.BND"
        if bnd_name not in lvl.files:
            print(f"  no {bnd_name}, skipping")
            continue
        chunks = parse_chunks(lvl.read(bnd_name))
        (out / game["cams_dir"] / short).mkdir(parents=True, exist_ok=True)

        cell_w, cell_h = game["geometry"]["worldW"], game["geometry"]["worldH"]
        # a path the decomp tabulates nothing for reads its own grid; a path it
        # does is never guessed at, so the two can't disagree
        path_meta = dict(tables[short])
        untabulated = sorted(k[1] for k in chunks if k[0] == "Path" and k[1] not in path_meta)
        for path_id in untabulated:
            path_meta[path_id] = discover_path_meta(chunks[("Path", path_id)], game["tlv"],
                                                    cell_w, cell_h)
        if untabulated:
            print(f"  no table for {', '.join(f'P{p}' for p in untabulated)}: "
                  "grid read from the path chunk")
        level_entry = {"id": lid, "short": short, "name": display, "paths": []}
        # paths entered under an ender id belong to the endgame revisit; raw
        # destination ids (decoded with an identity level map) reveal which
        ender_ids = [i for i, s in level_short.items() if s == short and i != lid]
        raw_refs = {}
        for path_id, meta in sorted(path_meta.items()):
            key = ("Path", path_id)
            if key not in chunks:
                continue
            blob = chunks[key]
            W = max(1, meta["w_units"] // cell_w)
            H = max(1, meta["h_units"] // cell_h)
            n = W * H

            # camera name table
            cells = []
            for i in range(n):
                nm = blob[i*8:(i+1)*8].decode("latin1").strip("\0 ")
                nm = nm if re.fullmatch(r"[A-Z0-9]{4,8}", nm or "") else None
                cells.append(nm)

            # collision lines (20 bytes each; coords + type share the layout in both games)
            lines = []
            co, cc = meta["coll_off"], meta["coll_count"]
            for i in range(cc):
                p = co + i * 20
                if p + 20 > len(blob):
                    break
                x1, y1, x2, y2 = struct.unpack_from("<hhhh", blob, p)
                ltype = blob[p + 8]
                lines.append([x1, y1, x2, y2, ltype])

            # TLVs: linear walk of object region
            region_end = meta["idx_off"] if meta["idx_off"] > meta["obj_off"] else len(blob)
            tlvs = walk_obj_region(blob, meta["obj_off"], region_end, game, level_short)
            if ender_ids:
                for rt in walk_obj_region(blob, meta["obj_off"], region_end, game, {}):
                    e = rt["extra"]
                    for lk, pk in (("to_level", "to_path"), ("alt_level", "alt_path")):
                        if isinstance(e.get(lk), int) and e.get(pk):
                            raw_refs.setdefault(e[lk], set()).add(e[pk])

            # cameras
            cams = []
            for i, nm in enumerate(cells):
                if not nm:
                    continue
                png_rel = f"{game['cams_dir']}/{short}/{nm}.png"
                png_path = out / png_rel
                if png_path.exists():
                    cam_stats["reused"] += 1
                    ok = True
                else:
                    # AE names three dev-cut cells with no .CAM and nothing linking
                    # to them (FDP08C13, FDP10C14, BRP08C10), so a "failed" count of
                    # 3 is expected for AE; decode_cam's warning tells a missing file
                    # from a genuine decode failure.
                    ok = decode_cam(lvl, nm, png_path, tmpdir, game["fg1_bitmask"])
                    cam_stats["decoded" if ok else "failed"] += 1
                entry = {"cell": i, "name": nm, "png": png_rel if ok else None}
                if (out / f"{game['cams_dir']}/{short}/{nm}_fg.png").exists():
                    entry["fg"] = f"{game['cams_dir']}/{short}/{nm}_fg.png"
                cams.append(entry)

            print(f"  path {path_id}: {W}x{H} cams={sum(1 for c in cells if c)} tlvs={len(tlvs)} lines={len(lines)}")
            level_entry["paths"].append({
                "id": path_id, "w": W, "h": H,
                "cams": cams, "tlvs": tlvs, "lines": lines,
            })

        # the two labels the games define: a name is what the game calls the
        # place (AO R2's zulags, from the save slots), a section which half of
        # the level it belongs to. Paths the base level also leads to are
        # shared geography and carry neither.
        path_names, path_sections = {}, {}
        if args.game == "AO" and short == "R2":
            path_names = {p: f"Zulag {z}" for z, ps in AO_R2_ZULAGS.items() for p in ps}
        for eid in ender_ids:
            for p in raw_refs.get(eid, set()) - raw_refs.get(lid, set()):
                path_sections[p] = AE_LEVEL_DISPLAY.get(eid, f"level {eid}")
        for P in level_entry["paths"]:
            if P["id"] in path_names:
                P["name"] = path_names[P["id"]]
            if P["id"] in path_sections:
                P["section"] = path_sections[P["id"]]

        if level_entry["paths"]:
            data["levels"].append(level_entry)

    # subset builds merge into existing data instead of clobbering other levels
    built_this_run = data["levels"]
    data_file = out / game["data_file"]
    if only and data_file.exists():
        old = json.loads(data_file.read_text())
        built = {L["short"]: L for L in data["levels"]}
        merged = [built.get(L["short"], L) for L in old["levels"]]
        have = {L["short"] for L in merged}
        merged += [L for L in data["levels"] if L["short"] not in have]
        data["levels"] = merged
    data_file.write_text(json.dumps(data, indent=1))
    write_field_types(args.game, out)  # decomp-derived sidecars, kept in sync each build
    write_enum_labels(args.game, out)
    write_messages(args.game, discs, out)  # game-wide, so a subset build writes it whole
    sw_file = out / "sw.js"
    # a scratch --out holds no worker, so a verification build stamps nothing
    cache_name = stamp_cache_name(sw_file, out / "cams") if sw_file.exists() else None
    print(f"\ndone -> {data_file}")
    print_build_summary(args.game, built_this_run, data_file, data["levels"], cam_stats, cache_name)

if __name__ == "__main__":
    main()
