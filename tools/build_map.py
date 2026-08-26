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
import struct
import sys
from pathlib import Path

from oddmap.paths import HERE, SITE
from oddmap.tables import AE_LEVEL_DISPLAY, AO_R2_ZULAGS
from oddmap.disc import Disc, Lvl, parse_chunks

from oddmap.schema import parse_enum_labels
from oddmap.image import decode_cam, ensure_tools
from oddmap.tlv import discover_path_meta, walk_obj_region
from oddmap.games import GAMES, game_setup


from oddmap.messages import write_messages
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

# ----------------------------------------------------------------------- main

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
    # game-wide, so a subset build writes it whole
    write_messages(args.game, discs, out / game["messages_file"])
    sw_file = out / "sw.js"
    # a scratch --out holds no worker, so a verification build stamps nothing
    cache_name = stamp_cache_name(sw_file, out / "cams") if sw_file.exists() else None
    print(f"\ndone -> {data_file}")
    print_build_summary(args.game, built_this_run, data_file, data["levels"], cam_stats, cache_name)

if __name__ == "__main__":
    main()
