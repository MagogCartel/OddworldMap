"""The decomp's own tables, parsed out of C++ source: per-level path metadata and
the TLV type names. Cached under tools/data/ and re-parsed only when deleted."""
import json
import re
import subprocess

from oddmap.paths import AO_COMMIT, HERE, REPO
from oddmap.tables import AE_LEVEL_DISPLAY, AE_LEVEL_ORDER

def int_rows(body):
    rows = []
    for m in re.finditer(r"\{([^{}]*)\}", body):
        toks = [t.strip() for t in m.group(1).split(",")]
        nums = [int(t) for t in toks if re.fullmatch(r"-?\d+", t)]
        rows.append(nums)
    return rows

def parse_pathdata_cpp_ao():
    src = subprocess.run(["git", "-C", str(REPO), "show", f"{AO_COMMIT}:Source/AliveLibAO/PathData.cpp"],
                         stdout=subprocess.PIPE, text=True, check=True).stdout

    path_arrays = {}
    for m in re.finditer(r"PathData\s+(\w+)\[\]\s*=\s*\{(.*?)\n\};", src, re.S):
        path_arrays[m.group(1)] = int_rows(m.group(2))
    coll_arrays = {}
    for m in re.finditer(r"CollisionInfo\s+(\w+)\[\d*\]\s*=\s*\{(.*?)\n\};", src, re.S):
        coll_arrays[m.group(1)] = int_rows(m.group(2))

    bly_arrays = {}
    for m in re.finditer(r"PathBlyRec\s+(\w+)\[\d*\]\s*=\s*\{(.*?)\n\};", src, re.S):
        entries = []
        for rm in re.finditer(r"\{([^{}]*)\}", m.group(2)):
            row = rm.group(1)
            bm = re.search(r'"([^"]+)"\s*,\s*&(\w+)\[(\d+)\]\s*,\s*&(\w+)\[(\d+)\]', row)
            if bm:
                entries.append((bm.group(1), bm.group(2), int(bm.group(3)), bm.group(4), int(bm.group(5))))
            else:
                entries.append(None)
        bly_arrays[m.group(1)] = entries

    # gMapData rows -> map short level name to bly array
    level_bly = {}
    gm = re.search(r"PathRootContainer gMapData_4CAB58\s*=\s*\{(.*?)\n\};", src, re.S)
    for rm in re.finditer(r"\{\s*(\w+)\s*,[^{}]*?\"(\w+)\",\s*(\d+),", gm.group(1)):
        level_bly[rm.group(2)] = (rm.group(1), int(rm.group(3)))

    out = {}
    for short, (bly_name, num_paths) in level_bly.items():
        paths = {}
        arr = bly_arrays.get(bly_name, [])
        for path_id, e in enumerate(arr):
            if not e:
                continue
            bly, parr, pidx, carr, cidx = e
            pd = path_arrays[parr][pidx]
            cd = coll_arrays[carr][cidx]
            # PathData nums: [bLeft,bRight,bTop,bBottom,gw,gh,1024,480,obj_off,idx_off]
            # CollisionInfo nums: [left,right,top,bottom,coll_off,coll_count,gw,gh]
            paths[path_id] = {
                "bly": bly,
                "w_units": pd[2], "h_units": pd[3],
                "obj_off": pd[8], "idx_off": pd[9],
                "coll_off": cd[4], "coll_count": cd[5],
            }
        out[short] = paths
    return out

def parse_pathdata_cpp_ae():
    """AE tables live in the alive_reversing working tree (the decomp's primary target)"""
    src = (REPO / "Source/AliveLibAE/PathData.cpp").read_text()
    hpp = (REPO / "Source/AliveLibAE/Path.hpp").read_text()

    def positional_rows(body):
        """entries are either a null-identifier or a braced row; index = path id"""
        rows = []
        for m in re.finditer(r"kNull\w+|\{[^{}]*\}", body):
            tok = m.group(0)
            rows.append(None if tok.startswith("kNull") else
                        [int(t) for t in (x.strip() for x in tok[1:-1].split(",")) if re.fullmatch(r"-?\d+", t)])
        return rows

    path_arrays = {}
    for m in re.finditer(r"static PathData (\w+)_PathData\[\w*\] = \{(.*?\})\s*,?\s*\};", src, re.S):
        path_arrays[m.group(1)] = positional_rows(m.group(2))
    coll_arrays = {}
    for m in re.finditer(r"static CollisionInfo (\w+)_CollisionInfo\[\w*\] = \{(.*?\})\s*,?\s*\};", src, re.S):
        coll_arrays[m.group(1)] = positional_rows(m.group(2))
    bly_arrays = {}
    for m in re.finditer(r"static PathBlyRec (\w+)_PathBlyRecInfo\[\w*\] = \{(.*?\})\s*,?\s*\};", src, re.S):
        entries = []
        for em in re.finditer(r"kNullPathBlyRec|\{[^{}]*\}", m.group(2)):
            tok = em.group(0)
            bm = re.search(r'"([^"]+)"\s*,\s*&(\w+)_PathData\[(\d+)\]\s*,\s*&(\w+)_CollisionInfo\[(\d+)\]', tok)
            entries.append((bm.group(1), bm.group(2), int(bm.group(3)), bm.group(4), int(bm.group(5))) if bm else None)
        bly_arrays[m.group(1)] = entries

    # root container: level id order -> (bly prefix == level short, num paths)
    gm = re.search(r"PathRootContainer\s+\w+\s*=\s*\{(.*?)\};", src, re.S)
    roots = []
    for rm in re.finditer(r"\{\s*(\w+_PathBlyRecInfo|nullptr)[^{}]*\}", gm.group(1)):
        row = rm.group(0)
        prefix = rm.group(1).replace("_PathBlyRecInfo", "") if rm.group(1) != "nullptr" else None
        sm = re.search(r'"([A-Z0-9]{2})"\s*,\s*(\d+)\s*,', row)
        roots.append((prefix, sm.group(1) if sm else None, int(sm.group(2)) if sm else 0))

    tables = {}
    levels = []
    id_to_short = {}
    for level_id, (bly_prefix, short, num_paths) in enumerate(roots):
        if not bly_prefix or not short:
            continue
        id_to_short[level_id] = short
        paths = {}
        for path_id, e in enumerate(bly_arrays.get(bly_prefix, [])):
            if not e:
                continue
            bly, parr, pidx, carr, cidx = e
            pd = path_arrays[parr][pidx]
            cd = coll_arrays[carr][cidx]
            # PathData nums: [bLeft,bRight,bTop,bBottom,375,260,375,260,obj_off,idx_off,abe_x,abe_y]
            paths[path_id] = {
                "bly": bly,
                "w_units": pd[2], "h_units": pd[3],
                "obj_off": pd[8], "idx_off": pd[9],
                "coll_off": cd[4], "coll_count": cd[5],
            }
        if paths:
            tables[short] = paths
            levels.append([level_id, short, AE_LEVEL_DISPLAY.get(level_id, short)])

    # TLV type names from the enum (identifiers end in _<id>)
    tlv_names = {}
    em = re.search(r"enum class TlvTypes : s16\s*\{(.*?)\n\};", hpp, re.S)
    for nm in re.finditer(r"(\w+?)_(\d+)\s*=\s*(\d+)", em.group(1)):
        tlv_names[int(nm.group(3))] = nm.group(1)

    order = {lid: i for i, lid in enumerate(AE_LEVEL_ORDER)}
    levels.sort(key=lambda l: order.get(l[0], 99))
    # ender level ids reuse their base level's archive; keep one entry per archive
    seen, unique = set(), []
    for lid, short, display in levels:
        if short not in seen:
            seen.add(short)
            unique.append([lid, short, display])
    return {"levels": unique, "id_to_short": id_to_short, "tlv_names": tlv_names, "tables": tables}

def load_cache(game):
    cache = HERE / "data" / game["cache"]
    if cache.exists():
        return json.loads(cache.read_text())
    out = game["parse_tables"]()
    cache.parent.mkdir(exist_ok=True)
    cache.write_text(json.dumps(out, indent=1))
    return out
