"""relive_api's own reading of the TLVs, swept from the decomp, for the exporter
that writes the level editor's JSON: per object type the CTOR literal and its
properties — display string, payload word from the data struct's real layout,
byte width, registered type name — plus the AddEnum label tables verbatim and
the collision-line structure. The viewer caches model the ADD order instead, so
the two views disagree exactly where a member name lies about its offset.

Cached under tools/data/ with the pathdata/objects discipline: re-parsed only
when deleted, and only from the checkout at the pin. The parse validates its
layouts against the decomp's own ALIVE_ASSERT_SIZEOF lines and raises on any
type it cannot width, so a thinner sweep fails rather than caching wrong words."""
import re

from oddmap.decomp import cached
from oddmap.paths import HERE, REPO
from oddmap.schema import _lib_headers, _match_brace, _relive_headers, _strip_comments, norm

_PRIM_SIZES = {"s8": 1, "u8": 1, "int8_t": 1, "uint8_t": 1, "char_type": 1, "bool": 1,
               "s16": 2, "u16": 2, "int16_t": 2, "uint16_t": 2,
               "s32": 4, "u32": 4, "int32_t": 4, "uint32_t": 4, "f32": 4, "FP": 4,
               "s64": 8, "u64": 8, "int64_t": 8, "uint64_t": 8}
# relive names a property's type from its typeid, so the stdint spellings land
# on the same five registered basic types
_BASIC_NAMES = {"u8": "Byte", "uint8_t": "Byte", "u16": "UInt16", "uint16_t": "UInt16",
                "s16": "SInt16", "int16_t": "SInt16", "u32": "Uint32", "uint32_t": "Uint32",
                "s32": "SInt32", "int32_t": "SInt32"}
_NOT_MEMBERS = {"static", "const", "constexpr", "using", "typedef", "public", "private",
                "void", "return", "friend", "virtual", "inline", "explicit",
                "struct", "union", "enum", "class", "namespace", "template"}

_AGG_RE = re.compile(r'\b(struct|class|union)\s+([A-Za-z_]\w*)\b([^{;]*)\{')
_ENUM_DEF_RE = re.compile(r'\benum\s+(?:class\s+)?([A-Za-z_]\w*)\s*(?::\s*(\w+))?\s*\{')
_DECL = r'[A-Za-z_]\w*(?:\s*\[\s*\d+\s*\])?(?:\s*=[^;,]*)?'
_MEMBER_RE = re.compile(rf'(?m)^\s*([A-Za-z_][\w:]*(?:<[^<>;]*>)?)\s+({_DECL}(?:\s*,\s*{_DECL})*)\s*;')
_ADD_RE = re.compile(r'\bADD(_HIDDEN|_LINKED)?\(\s*"([^"]+)"\s*,\s*m(?:Tlv|Line)\.(.+?)\s*\)\s*;')
_SIZEOF_RE = re.compile(r'\bALIVE_ASSERT_SIZEOF(?:_ALWAYS)?\(\s*(\w+)\s*,\s*(0x[0-9A-Fa-f]+|\d+)\s*\)')
_ADDENUM_RE = re.compile(r'AddEnum<\s*([A-Za-z0-9_:]+)\s*>\s*\(\s*"([^"]+)"\s*,\s*\{(.*?)\}\s*\)', re.S)

def _unqualify(ty):
    return re.sub(r"^(?:::)?(?:AO::|AE::)?", "", ty)

def _sweep_defs(game_key):
    """aggregate bodies, enum values/backings and sizeof assertions across every
    header the game's relive_api can reach, the sibling lib tree filling in only
    what the own sweep lacks (AO fields use AE's XDirection_short). A name defined
    twice in disagreement is poisoned, so a layout that needs it raises."""
    aggs, enums, asserts, aliases = {}, {}, {}, {}
    poisoned = set()

    def scan(paths, fill_only):
        for p in paths:
            src = _strip_comments(p.read_text(errors="replace"))
            spans = [(m.group(1), m.end(), _match_brace(src, m.end() - 1))
                     for m in re.finditer(r'\b(?:struct|class)\s+([A-Za-z_]\w*)\b[^{;]*\{', src)]

            def owner_of(pos):
                inner = [n for n, a, b in spans if a <= pos < b]
                return inner[-1] if inner else None

            for em in _ENUM_DEF_RE.finditer(src):
                owner = owner_of(em.start())
                key = f"{owner}::{em.group(1)}" if owner else em.group(1)
                backing = _PRIM_SIZES.get(em.group(2), 4) if em.group(2) else 4
                body = src[em.end():_match_brace(src, em.end() - 1) - 1]
                vals, running, ok = {}, 0, True
                for part in body.split(","):
                    if not part.strip():
                        continue
                    dm = re.match(r"\s*([A-Za-z_]\w*)\s*(?:=\s*(-?\d+|0x[0-9A-Fa-f]+))?\s*\Z", part)
                    if not dm:
                        ok = False
                        break
                    v = int(dm.group(2), 0) if dm.group(2) else running
                    vals[dm.group(1)] = v
                    running = v + 1
                # an initializer the parser can't value leaves the width usable
                entry = {"backing": backing, "vals": vals if ok else None}
                if key in poisoned or (fill_only and key in enums):
                    continue
                if key in enums and enums[key] != entry:
                    poisoned.add(key)
                    enums.pop(key)
                else:
                    enums[key] = entry

            for am in _AGG_RE.finditer(src):
                kind, name, head = am.group(1), am.group(2), am.group(3)
                if "TlvObjectBase" in head or "PropertyCollection" in head:
                    continue
                owner = owner_of(am.start())
                key = f"{owner}::{name}" if owner else name
                bm = re.search(r':\s*public\s+(?:\w+::)?(\w+)', head)
                body = src[am.end():_match_brace(src, am.end() - 1) - 1]
                # cut nested enum/struct/union bodies so their members stay their own
                kept, i = [], 0
                for nm in re.finditer(r'\b(?:enum\s+(?:class\s+)?|struct\s+|class\s+|union\s+)[A-Za-z_]\w*[^{;]*\{', body):
                    if nm.start() < i:
                        continue
                    kept.append(body[i:nm.start()])
                    i = _match_brace(body, nm.end() - 1)
                kept.append(body[i:])
                members = []
                for mm in _MEMBER_RE.finditer("".join(kept)):
                    ty = mm.group(1)
                    if ty in _NOT_MEMBERS or ty.split("<")[0] in _NOT_MEMBERS:
                        continue
                    for decl in mm.group(2).split(","):
                        dm = re.match(r'\s*([A-Za-z_]\w*)\s*(?:\[\s*(\d+)\s*\])?', decl)
                        members.append([ty, dm.group(1), int(dm.group(2)) if dm.group(2) else 1])
                entry = {"union": kind == "union", "base": bm.group(1) if bm else None,
                         "members": members}
                if key in poisoned or (fill_only and key in aggs):
                    continue
                if key in aggs and aggs[key] != entry:
                    poisoned.add(key)
                    aggs.pop(key)
                else:
                    aggs[key] = entry

            for um in re.finditer(r'\busing\s+([A-Za-z_]\w*)\s*=\s*([\w:]+)\s*;', src):
                key, target = um.group(1), _unqualify(um.group(2))
                if key in poisoned or (fill_only and key in aliases):
                    continue
                if key in aliases and aliases[key] != target:
                    poisoned.add(key)
                    aliases.pop(key)
                else:
                    aliases[key] = target

            if not fill_only:  # a sibling's sizeof must not judge this game's layout
                for sm in _SIZEOF_RE.finditer(src):
                    asserts.setdefault(sm.group(1), int(sm.group(2), 0))

    scan(_relive_headers(game_key) + _lib_headers(game_key), fill_only=False)
    scan(_lib_headers("AE" if game_key == "AO" else "AO"), fill_only=True)
    return aggs, enums, asserts, aliases

class _Layouts:
    """byte offsets, sizes and alignments over the swept aggregates. Path_TLV is
    opaque — the game's own header length, which is where every payload starts."""

    def __init__(self, game_key, aggs, enums, aliases):
        self.header_len = 0x18 if game_key == "AO" else 0x10
        self.aggs, self.enums, self.aliases = aggs, enums, aliases
        self._memo = {}

    def canon(self, ty):
        ty, seen = _unqualify(ty), set()
        while ty in self.aliases and ty not in seen:
            seen.add(ty)
            ty = self.aliases[ty]
        return ty

    def enum_of(self, ty, owner=None):
        ty = self.canon(ty)
        if owner and f"{owner}::{ty}" in self.enums:
            return f"{owner}::{ty}", self.enums[f"{owner}::{ty}"]
        return (ty, self.enums[ty]) if ty in self.enums else (None, None)

    def size_align(self, ty, owner=None):
        """(size, alignment, leaf) for a member type: leaf is a primitive name,
        ("enum", key) or ("agg", key)"""
        ty = self.canon(ty)
        if ty in _PRIM_SIZES:
            return _PRIM_SIZES[ty], _PRIM_SIZES[ty], ty
        if ty.startswith("BitField16<"):
            return 2, 2, "u16"
        if ty.startswith("BitField8<"):
            return 1, 1, "u8"
        key, en = self.enum_of(ty, owner)
        if en:
            return en["backing"], en["backing"], ("enum", key)
        for agg_key in ((f"{owner}::{ty}",) if owner else ()) + (ty,):
            if agg_key in self.aggs:
                lay = self.layout(agg_key)
                return lay["size"], lay["align"], ("agg", agg_key)
        raise RuntimeError(f"cannot width type {ty!r} (owner {owner})")

    def layout(self, name):
        """{"size", "align", "members": {name: (offset, type, count)}} with the
        base chain sized in; a union's members all sit at its start"""
        name = self.canon(name)
        if name in self._memo:
            return self._memo[name]
        agg = self.aggs[name]
        off, align, members = 0, 1, {}
        if agg["base"] == "Path_TLV":
            off, align = self.header_len, 4
        elif agg["base"]:
            base = self.layout(agg["base"])
            off, align = base["size"], base["align"]
            members.update(base["members"])
        for ty, mname, count in agg["members"]:
            size, m_align, _leaf = self.size_align(ty, owner=name)
            align = max(align, m_align)
            if agg["union"]:
                members[mname] = (0, ty, count)
                off = max(off, size * count)
            else:
                off += -off % m_align
                members[mname] = (off, ty, count)
                off += size * count
        size = off + (-off % align)
        self._memo[name] = {"size": size, "align": align, "members": members}
        return self._memo[name]

    def resolve(self, struct, expr):
        """(byte offset, size, leaf type) of an ADD expression's member path; an
        accessor call ends the walk on the member it was called on (.Raw().all
        reads a BitField16's u16 storage)"""
        cur, off = struct, 0
        segs = expr.split(".")
        for i, seg in enumerate(segs):
            if "(" in seg:
                break
            lay = self.layout(cur)
            if seg not in lay["members"]:
                raise RuntimeError(f"{struct}: no member {seg!r} on {cur} (expr {expr!r})")
            m_off, ty, _count = lay["members"][seg]
            off += m_off
            size, _a, leaf = self.size_align(ty, owner=cur)
            if isinstance(leaf, tuple) and leaf[0] == "agg":
                cur = leaf[1]
                continue
            if i + 1 < len(segs) and "(" not in segs[i + 1]:
                raise RuntimeError(f"{struct}: scalar {seg!r} has trailing path in {expr!r}")
            return off, size, leaf
        raise RuntimeError(f"{struct}: path {expr!r} never reached a scalar")

def _registered_enums(game_key, enums):
    """AddEnum registrations from the game's TypesCollection and the per-TLV
    AddTypes overrides: registered name -> verbatim {value: label}, plus the
    C++-type -> registered-name map property typing needs. The reader knows only
    the enumerators a registration lists, so the labels here are that list, not
    the definition's."""
    labels, by_type, order = {}, {}, []
    for fname in (f"TypesCollection{game_key}.cpp", f"Tlvs{game_key}.hpp"):
        src = _strip_comments((REPO / "Source/Tools/relive_api" / fname).read_text())
        for am in _ADDENUM_RE.finditer(src):
            cpp = _unqualify(am.group(1))
            reg = am.group(2)
            if cpp not in enums:
                raise RuntimeError(f"AddEnum<{cpp}> has no swept definition")
            vals = enums[cpp]["vals"]
            if vals is None:
                raise RuntimeError(f"AddEnum<{cpp}>: the definition's values are unparseable")
            table = {}
            for pm in re.finditer(r'\{\s*[A-Za-z0-9_:]+::([A-Za-z0-9_]+)\s*,\s*"([^"]*)"\s*\}', am.group(3)):
                if pm.group(1) not in vals:
                    raise RuntimeError(f"AddEnum<{cpp}> lists {pm.group(1)}, not in the definition")
                table[str(vals[pm.group(1)])] = pm.group(2)
            if reg in labels and labels[reg] != table:
                raise RuntimeError(f"enum {reg} registered twice in disagreement")
            if reg not in labels:
                order.append(reg)
            labels[reg] = table
            by_type[cpp] = reg
    return labels, by_type, order

def parse_relive_schema(game_key):
    """the whole relive cache for one game: structures (CTOR literal + property
    rows), the verbatim enum tables, and the collision-line structure"""
    aggs, enums, asserts, aliases = _sweep_defs(game_key)
    lay = _Layouts(game_key, aggs, enums, aliases)
    enum_labels, enum_by_type, enum_order = _registered_enums(game_key, enums)

    def prop_row(kind, display, expr, id_str, struct):
        off, size, leaf = lay.resolve(struct, expr)
        if off < lay.header_len or (off - lay.header_len) % 2:
            raise RuntimeError(f"{struct}.{expr}: offset {off:#x} outside even payload words")
        if isinstance(leaf, tuple):
            reg = enum_by_type.get(leaf[1]) or enum_by_type.get(leaf[1].split("::")[-1])
            if not reg:
                raise RuntimeError(f"{struct}.{expr}: enum {leaf[1]} has no AddEnum registration")
            ty, is_enum = reg, True
        else:
            if leaf not in _BASIC_NAMES:
                raise RuntimeError(f"{struct}.{expr}: no basic type for {leaf}")
            ty, is_enum = _BASIC_NAMES[leaf], False
        row = {"name": display, "key": norm(display), "word": (off - lay.header_len) // 2,
               "size": size, "type": ty, "enum": is_enum, "visible": kind != "_HIDDEN"}
        if id_str is not None:
            row["id_str"] = id_str
        return row

    src = (REPO / f"Source/Tools/relive_api/Tlvs{game_key}.hpp").read_text()
    ctor = f"CTOR_{game_key}"
    structures, by_class = {}, {}
    for m in re.finditer(rf"{ctor}\([^)]*\)\s*\{{(.*?)\n    \}}", src, re.S):
        head = re.search(rf'{ctor}\(\s*(Path_\w+)\s*,\s*"([^"]+)"\s*,\s*(?:\w+::)?TlvTypes::\w+_(\d+)\s*\)',
                         src[m.start():m.start() + 300])
        if not head:
            continue
        struct, literal, tid = head.group(1), head.group(2), int(head.group(3))
        props = []
        for am in _ADD_RE.finditer(_strip_comments(m.group(1))):
            expr, id_str = am.group(3), None
            if am.group(1) == "_LINKED":
                expr, id_str = re.match(r'(.+?)\s*,\s*"([^"]*)"\s*$', expr).groups()
            props.append(prop_row(am.group(1), am.group(2), expr, id_str, struct))
        structures[str(tid)] = {"name": literal, "properties": props}
        by_class[struct] = literal

    reg_src = _strip_comments((REPO / f"Source/Tools/relive_api/TypesCollection{game_key}.cpp").read_text())
    order = [by_class[rm.group(1)] for rm in
             re.finditer(rf'REGISTER_TYPE_{game_key}\(\s*\w+::(\w+)\s*\)', reg_src)]
    if sorted(order) != sorted(s["name"] for s in structures.values()):
        raise RuntimeError(f"{game_key}: registered types and CTOR blocks disagree")

    line_class = re.search(rf'class {game_key}Line[^{{]*\{{',
                           (REPO / "Source/Tools/relive_api/JsonReaderBase.hpp").read_text())
    line_src = (REPO / "Source/Tools/relive_api/JsonReaderBase.hpp").read_text()
    body = line_src[line_class.end():_match_brace(line_src, line_class.end() - 1) - 1]
    line_struct = "AO::PathLine" if game_key == "AO" else "PathLine"
    collision = []
    for am in _ADD_RE.finditer(body):
        off, size, leaf = lay.resolve(_unqualify(line_struct), am.group(3))
        ty = enum_by_type[leaf[1]] if isinstance(leaf, tuple) else _BASIC_NAMES[leaf]
        collision.append({"name": am.group(2), "type": ty})

    for name, computed in lay._memo.items():
        want = asserts.get(name.split("::")[-1])
        if want is not None and computed["size"] != want:
            raise RuntimeError(f"{name}: computed sizeof {computed['size']:#x} != asserted {want:#x}")

    return {"structures": structures,
            "structure_order": order,
            "enums": {name: enum_labels[name] for name in enum_order},
            "collision_structure": collision}

def load_relive_schema(game_key, game):
    return cached(HERE / "data" / game["relive_cache"], lambda: parse_relive_schema(game_key))

# relive registers its basic types from numeric_limits narrowed to s32, spelling
# quirks and all (TypesCollectionBase.cpp), so the blob is a constant
_BASIC_TYPES_JSON = [
    {"min_value": 0, "max_value": 255, "name": "Byte"},
    {"min_value": 0, "max_value": 65535, "name": "UInt16"},
    {"min_value": -32768, "max_value": 32767, "name": "SInt16"},
    {"min_value": 0, "max_value": -1, "name": "Uint32"},
    {"min_value": -2147483648, "max_value": 2147483647, "name": "SInt32"},
]

_BASE_PROPS = [{"Type": "SInt16", "Visible": True, "name": n}
               for n in ("xpos", "ypos", "width", "height")]

# words relive reads that the archive never captured, and what to write there:
# a diff against a reference export holds them known-divergent, and a rebuild
# that archives the word spends its entry loudly — bar the one dropped by design
_EXPORT_VALUE_FALLBACKS = {
    ("AE", "MovieHandstone", "Trigger Switch ID"): 0,
    ("AE", "SecurityClaw", "Unknown"): 0,
    ("AO", "ShadowZone", "R"): 0,
    ("AO", "ShadowZone", "G"): 0,
    ("AO", "ShadowZone", "B"): 0,
    ("AE", "ShadowZone", "R"): 0,
    ("AE", "ShadowZone", "G"): 0,
    ("AE", "ShadowZone", "B"): 0,
}

def schema_blob(rel):
    """the per-game `schema` root key the editor reads: identical for every path"""
    by_name = {s["name"]: s for s in rel["structures"].values()}
    structures = []
    for literal in rel["structure_order"]:
        descs = list(_BASE_PROPS)
        for p in by_name[literal]["properties"]:
            d = {"Type": p["type"], "Visible": p["visible"], "name": p["name"]}
            if "id_str" in p:
                d["Identity_string"] = p["id_str"]
            descs.append(d)
        structures.append({"name": literal, "enum_and_basic_type_properties": descs})
    return {"object_structure_property_basic_types": _BASIC_TYPES_JSON,
            "object_structure_property_enums": [{"name": n, "values": list(t.values())}
                                                for n, t in rel["enums"].items()],
            "object_structures": structures}

def camera_id(name):
    """the digit formula relive derives an id from an 8-char camera name with,
    char arithmetic and all (JsonWriterBase)"""
    return (1000 * (ord(name[3]) - 48) + 100 * (ord(name[4]) - 48)
            + 10 * (ord(name[6]) - 48) + (ord(name[7]) - 48))

def bucket_cells(path, geometry):
    """authored grid cell -> the path's TLVs in list order (the tlvCell rule)"""
    cells = {}
    for t in path["tlvs"]:
        cell = (t["y1"] // geometry["worldH"]) * path["w"] + (t["x1"] // geometry["worldW"])
        if not 0 <= cell < path["w"] * path["h"]:
            raise RuntimeError(f"{t['name']} at {t['x1']},{t['y1']} lands outside the grid")
        cells.setdefault(cell, []).append(t)
    return cells

def widen_value(lo, hi, ty, size):
    """a stored s16 word (with its neighbour for the 4-byte widths) as the
    property's own width; a missing high word sign-extends"""
    if size == 4:
        if hi is None:
            hi = -1 if lo < 0 else 0
        v = (lo & 0xFFFF) | ((hi & 0xFFFF) << 16)
        return v - (1 << 32) if ty != "Uint32" and v >= (1 << 31) else v
    if size == 1:
        return lo & 0xFF
    return lo & 0xFFFF if ty == "UInt16" else lo

def _property_value(game_key, literal, prop, words, rel, manifest):
    lo = words.get(prop["word"])
    fallback = _EXPORT_VALUE_FALLBACKS.get((game_key, literal, prop["name"]))
    if lo is None:
        if fallback is None:
            manifest["missing"].add((literal, prop["name"]))
            return None
        manifest["fallbacks"].add((literal, prop["name"]))
        v = fallback
    else:
        if fallback is not None:
            raise RuntimeError(f"spent export fallback: {literal}.{prop['name']} is archived now")
        v = widen_value(lo, words.get(prop["word"] + 1) if prop["size"] == 4 else None,
                        prop["type"], prop["size"])
    if not prop["enum"]:
        return v
    labels = rel["enums"][prop["type"]]
    label = labels.get(str(v))
    if label is None and prop["size"] == 2:
        label = labels.get(str(v & 0xFFFF))
    if label is None:
        raise RuntimeError(f"{literal}.{prop['name']}: value {v} has no {prop['type']} label")
    return label

def _map_object(game_key, game, rel, t, counters, manifest):
    s = rel["structures"][str(t["t"])]
    counters[s["name"]] = counters.get(s["name"], 0) + 1
    w, h = t["x2"] - t["x1"], t["y2"] - t["y1"]
    if w < 0 or h < 0:  # relive aborts an export on a negative size
        raise RuntimeError(f"{s['name']} at {t['x1']},{t['y1']}: negative size {w}x{h}")
    props = {"xpos": t["x1"], "ypos": t["y1"], "width": w, "height": h}
    fields = t.get("fields", {})
    words = {word: fields[name] for word, name, *_ in game["schema"].get(t["t"], [])
             if name in fields}
    for prop in s["properties"]:
        v = _property_value(game_key, s["name"], prop, words, rel, manifest)
        if v is not None:
            props[prop["name"]] = v
    return {"name": f"{s['name']}_{counters[s['name']]}",
            "object_structures_type": s["name"], "properties": props}

def export_path(game_key, game, rel, level, path, muds_in_level):
    """one path as a relive_api v4 document, plus the manifest of what the
    archive could not supply — a written file missing a property would abort
    relive's importer, so the caller decides whether an incomplete one ships"""
    geometry = game["geometry"]
    manifest = {"missing": set(), "fallbacks": set()}
    counters = {}
    cams_by_cell = {c["cell"]: c["name"] for c in path["cams"]}
    buckets = bucket_cells(path, geometry)
    cameras = []
    for cell in sorted(set(cams_by_cell) | set(buckets)):
        name = cams_by_cell.get(cell, "")
        cameras.append({"name": name, "x": cell % path["w"], "y": cell // path["w"],
                        "id": camera_id(name) if name else 0,
                        "map_objects": [_map_object(game_key, game, rel, t, counters, manifest)
                                        for t in buckets.get(cell, [])]})
    link_names = [r["name"] for r in rel["collision_structure"][5:]]
    items = []
    for x1, y1, x2, y2, ltype in path["lines"]:
        label = rel["enums"]["Enum_LineTypes"].get(str(ltype))
        if label is None:
            raise RuntimeError(f"collision type {ltype} has no Enum_LineTypes label")
        item = {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "Type": label}
        for n in link_names:  # the links live only in the path chunk; -1 is the editor's default
            item[n] = -1
        items.append(item)
    if game_key == "AO":
        abe_x = abe_y = 0
        muds = (0, 99, 75, 50)
    else:
        row = game["tables"][level["short"]][path["id"]]
        abe_x, abe_y = row["abe_x"], row["abe_y"]
        in_path = muds_in_level[level["id"]] if level["id"] < len(muds_in_level) else 0
        muds = (in_path, 300, 20, 255)
    doc = {"api_version": 4, "game": game_key,
           "map": {"path_bnd": f"{level['short']}PATH.BND", "path_id": path["id"],
                   "x_size": path["w"], "y_size": path["h"],
                   "x_grid_size": geometry["worldW"], "y_grid_size": geometry["worldH"],
                   "abe_start_xpos": abe_x, "abe_start_ypos": abe_y,
                   "num_muds_in_path": muds[0], "total_muds": muds[1],
                   "num_muds_for_bad_ending": muds[2], "num_muds_for_good_ending": muds[3],
                   "lcdscreen_messages": [], "hintfly_messages": [],
                   "collisions": {"structure": [{"Type": r["type"], "Visible": True, "name": r["name"]}
                                                for r in rel["collision_structure"]],
                                  "items": items},
                   "cameras": cameras},
           "schema": schema_blob(rel)}
    return doc, manifest
