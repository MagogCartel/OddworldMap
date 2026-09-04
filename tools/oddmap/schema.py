"""Per-object field layouts and enum labels, swept from the decomp's headers, with
the override tables carrying what the source gets wrong or cannot express.

The caches under tools/data/ are re-parsed only when deleted, so builds and the
sidecar emit run from the committed tree alone; only regenerating a cache needs
the checkout."""
import re

from oddmap.decomp import cached
from oddmap.paths import HERE, REPO

_SKIP_TYPES = {"s8", "s16", "s32", "s64", "u8", "u16", "u32", "u64", "int", "short", "char",
               "bool", "float", "BYTE", "FP",
               "const", "static", "using", "public", "private", "void", "return", "friend"}
_ENUM_RE = r'\benum\s+(?:class\s+)?([A-Za-z0-9_]+)'

def _match_brace(text, open_idx):
    """index just past the } matching the { at open_idx"""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    return len(text)

def _relive_headers(game_key):
    """the Tlvs header for a game plus the AliveLib headers it includes — where
    the data structs and enums are declared"""
    tlv = REPO / f"Source/Tools/relive_api/Tlvs{game_key}.hpp"
    paths = [tlv]
    for inc in re.finditer(r'#include\s+"([^"]+)"', tlv.read_text()):
        p = (tlv.parent / inc.group(1)).resolve()
        if p.exists():
            paths.append(p)
    return paths

# the viewer owns these value-type transforms (bool, full/half) and keeps them
# uniform across games, so the label generator leaves them out; direction enums
# are generated like any other (left/right comes from the decomp's enumerators)
_VALUE_TYPES = {"Choice_short", "Choice_int", "Scale_short", "Scale_int"}

# layouts the schema parser can't derive from the relive_api CTOR alone. An empty
# layout marks a genuinely field-less type so it still retires its raw fallback.
_SCHEMA_LAYOUT_OVERRIDES = {
    ("AO", 109): [],  # RingCancel — EMPTY_CTOR, no payload fields
}

# layouts the CTOR expresses wrongly, as (derived, corrected): keyed to what the
# parser currently yields, so an upstream fix retires the entry loudly instead of
# silently double-correcting.
_SCHEMA_LAYOUT_CORRECTIONS = {
    # MovieHandStone: relive_api's field order contradicts the engine, which reads
    # word 0 as the movie number and words 2-3 as one s32 switch id (Path_MovieStone);
    # the s32's meaningless high word is dropped rather than kept as a phantom field
    ("AE", 27): (
        [[0, "scale", "Scale_short"], [1, "movie_number"], [2, "trigger_switch_id"], [3, "padding"]],
        [[0, "movie_number"], [1, "scale", "Scale_short"], [2, "trigger_switch_id"]],
    ),
}

def norm(label):
    """a display string down to the archive's key: parens and apostrophes out,
    everything non-alphanumeric to one underscore, lowercased"""
    label = re.sub(r"\([^)]*\)", "", label).replace("'", "")
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_").lower()

def _derive_label(enumerator):
    """a readable label from an enumerator name: drop the value suffix and the
    decomp's `e` prefix, split CamelCase (eChaseAndDisappear_4 -> Chase And Disappear)"""
    n = re.sub(r"_\d+$", "", enumerator)
    n = re.sub(r"^e(?=[A-Z])", "", n)
    n = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", n)
    return n[:1].upper() + n[1:] if n else enumerator

def _inherit_member_types(types, bases, declared):
    """a derived struct answers for its base chain's members; the nearest
    declaration wins, typed or not, the way C++ name hiding reads"""
    flat = dict(types)
    for struct, base in bases.items():
        hidden = {m for s, m in declared if s == struct}
        seen = set()
        while base and base not in seen:
            seen.add(base)
            for s, m in declared:
                if s == base and m not in hidden:
                    ty = types.get((base, m))
                    if ty:
                        flat[(struct, m)] = ty
                    hidden.add(m)
            base = bases.get(base)
    return flat

def parse_member_types(game_key):
    """(data-struct, member) -> its declared game type, across the Tlvs header
    and the AliveLib data-struct headers it includes. A field's game type is what
    lets the viewer group value transforms across objects that share it (Slig and
    SligSpawner both declare start_state as Path_Slig::StartState) while keeping
    unrelated same-named fields apart (a Door's start_state is DoorStates). Enum
    leaf names repeat across the decomp (StartState is both a Slig enum and a
    MeatSaw enum), so a nested enum is qualified with its owning struct; the
    decomp's own qualified references carry the cross-object sharing. A derived
    struct answers for its base chain's members (the wells' scale is declared on
    Path_WellBase). Primitives and aggregate-valued fields carry no type — a
    union's arms stay unresolved even where the CTOR reads one."""
    paths = _relive_headers(game_key)

    aggregates, bases, declared, raw = set(), {}, set(), []
    for p in paths:
        src = p.read_text(errors="replace")
        for am in re.finditer(r'(?<!enum )\b(?:struct|union)\s+([A-Za-z_]\w*)\b[^{;]*\{', src):
            aggregates.add(am.group(1))
        for sm in re.finditer(r'\bstruct\s+(Path_[A-Za-z0-9_]+)\b([^{;]*)\{', src):
            struct = sm.group(1)
            if "TlvObjectBase" in sm.group(2):  # a viewer-API wrapper, not a data struct
                continue
            bm = re.search(r':\s*public\s+(Path_\w+)', sm.group(2))
            if bm:
                bases[struct] = bm.group(1)
            body = src[sm.end():_match_brace(src, sm.end() - 1) - 1]
            nested = set(re.findall(_ENUM_RE, body))
            # cut nested enum bodies so their enumerators aren't read as members
            kept, i = [], 0
            for em in re.finditer(_ENUM_RE + r'[^{;]*\{', body):
                kept.append(body[i:em.start()])
                i = _match_brace(body, em.end() - 1)
            kept.append(body[i:])
            for mm in re.finditer(
                    r'(?m)^\s*([A-Za-z_]\w*(?:::[A-Za-z_]\w*)*)\s+'
                    r'(field_[0-9A-Fa-f]+_\w+|[a-z_]\w*)\s*(?:=\s*[^;]+)?;', "".join(kept)):
                ty, member = mm.group(1), mm.group(2)
                declared.add((struct, member))
                if ty in _SKIP_TYPES:
                    continue
                if "::" not in ty and ty in nested:
                    ty = f"{struct}::{ty}"
                raw.append((struct, member, ty))

    types = {}
    for struct, member, ty in raw:  # second pass: now that every aggregate name is known
        if "::" not in ty and ty in aggregates:
            continue  # an aggregate-valued field (struct or union), not an enum
        if ty.split("::")[-1].endswith(("_data", "_Data")):
            continue
        types[(struct, member)] = ty
    return _inherit_member_types(types, bases, declared)

def _lib_headers(game_key):
    """every header of one game's AliveLib tree plus AliveLibCommon. Enum
    definitions aren't always reachable through includes (SwitchOp is only
    forward-declared where fields use it), so definitions are swept by directory."""
    dirs = [REPO / f"Source/AliveLib{game_key}", REPO / "Source/AliveLibCommon"]
    for d in dirs:
        if not d.is_dir():  # rglob on a missing dir yields [], a quietly thinner sweep
            raise FileNotFoundError(f"no decomp tree at {d}")
    return [h for d in dirs for h in sorted(d.rglob("*.hpp"))]

def _strip_comments(src):
    return re.sub(r"//[^\n]*", "", re.sub(r"/\*.*?\*/", "", src, flags=re.S))

def parse_enum_labels(game_key):
    """(canonical enum type -> {value: label}, unlabelable type keys) for the
    viewer to render enum ints. Values come from the enum definitions
    (authoritative: explicit `= N` or positional), labels from the AddEnum blocks
    where the decomp curates one, else derived from the enumerator name. Keyed
    like parse_member_types so the labels line up with the field types; the basic
    value-types are left out — the viewer owns those (_VALUE_TYPES). The sweep
    covers the game's own lib and falls back to the sibling lib for shared types
    (AO fields use AE's XDirection_short). Comments are stripped first: an "enum"
    inside one otherwise swallows the definition that follows. A bare enum name
    defined differently twice, or an initializer the parser can't value, makes
    that key unlabelable rather than silently wrong — the caller fails the emit
    if a field actually uses one."""
    own = REPO / f"Source/Tools/relive_api/Tlvs{game_key}.hpp"
    sibling = _lib_headers("AE" if game_key == "AO" else "AO")
    enums, bad = {}, set()

    def scan(paths, fill_only):
        for p in paths:
            src = _strip_comments(p.read_text(errors="replace"))
            structs = [(sm.group(1), sm.start(), _match_brace(src, sm.end() - 1))
                       for sm in re.finditer(r'\bstruct\s+(Path_[A-Za-z0-9_]+)\b[^{;]*\{', src)]
            for em in re.finditer(_ENUM_RE + r'[^{;]*\{', src):
                body = src[em.end():_match_brace(src, em.end() - 1) - 1]
                owner = next((s for s, a, b in structs if a <= em.start() < b), None)
                key = f"{owner}::{em.group(1)}" if owner else em.group(1)
                if key in bad or (fill_only and key in enums):
                    continue
                vals, running, ok = {}, 0, True
                for part in body.split(","):
                    if not part.strip():
                        continue
                    dm = re.match(r"\s*([A-Za-z_]\w*)\s*(?:=\s*(-?\d+|0x[0-9A-Fa-f]+))?\s*\Z", part)
                    if not dm:  # an initializer with no literal value
                        ok = False
                        break
                    v = int(dm.group(2), 0) if dm.group(2) else running
                    vals[v] = dm.group(1)
                    running = v + 1
                if not ok or (key in enums and enums[key] != vals):
                    bad.add(key)
                    enums.pop(key, None)
                elif vals:
                    enums[key] = vals

    scan([own] + _lib_headers(game_key), fill_only=False)
    scan(sibling, fill_only=True)

    # AddEnum blocks (in the Tlvs header) give curated labels per enumerator
    curated = {}
    src = (REPO / f"Source/Tools/relive_api/Tlvs{game_key}.hpp").read_text()
    for am in re.finditer(r'AddEnum<\s*([A-Za-z0-9_:]+)\s*>\s*\(\s*"[^"]*"\s*,\s*\{(.*?)\}\s*\)', src, re.S):
        key = re.sub(r"^(?:AO|AE)?::", "", am.group(1))
        pairs = dict(re.findall(r'\{\s*[A-Za-z0-9_:]+::([A-Za-z0-9_]+)\s*,\s*"([^"]*)"\s*\}', am.group(2)))
        if pairs:
            curated[key] = pairs

    labels = {}
    for key, vals in enums.items():
        if key in _VALUE_TYPES:
            continue
        c = curated.get(key, {})
        labels[key] = {v: c.get(en, _derive_label(en)).lower() for v, en in vals.items()}
    return labels, bad

def parse_object_schema(game_key):
    """per-type payload field layout from the relive_api CTOR blocks: each
    ADD("Name", mTlv.field_XX_...) gives a field's payload word (from the hex
    offset in the member name), a snake_cased name, and — where the decomp
    declares an enum/Choice/Scale rather than a bare int — its game type (see
    parse_member_types), so the viewer can key value transforms by it. Fields are
    sequential s16, so the offset holds except where the name lies — sequential
    members sharing one offset (Door's 8 hub ids are all "field_22_hubN"), or a
    member of an intermediate base struct numbering from its own start and so
    landing below the payload (Path_WellBase's four). Either way the offset fails
    to increase, and the next word is the answer. Members with no field_XX offset
    are positional too. Values stay raw."""
    src = (REPO / f"Source/Tools/relive_api/Tlvs{game_key}.hpp").read_text()
    base = 0x18 if game_key == "AO" else 0x10
    ctor = f"CTOR_{game_key}"
    member_types = parse_member_types(game_key)

    schema = {}
    for m in re.finditer(rf"{ctor}\([^)]*\)\s*\{{(.*?)\n    \}}", src, re.S):
        head = re.search(rf'{ctor}\(\s*(Path_\w+)\s*,\s*"[^"]+"\s*,\s*(?:\w+::)?TlvTypes::\w+_(\d+)\s*\)',
                         src[m.start():m.start() + 300])
        if not head:
            continue
        data_struct = head.group(1)
        fields = []
        last = -1
        for am in re.finditer(r'\bADD(?:_HIDDEN|_LINKED)?\(\s*"([^"]+)",\s*mTlv\.([^,\n;]+?)\s*[,)]', m.group(1)):
            off = re.match(r"field_([0-9A-Fa-f]+)_", am.group(2))
            if off:
                word = (int(off.group(1), 16) - base) // 2
                if word <= last:
                    word = last + 1
            else:
                word = last + 1
            member = re.split(r"[.\[]", am.group(2))[0]
            ty = member_types.get((data_struct, member))
            fields.append([word, norm(am.group(1)), ty] if ty else [word, norm(am.group(1))])
            last = word
        if fields:
            schema[int(head.group(2))] = fields
    return schema

def load_object_schema(game_key, game):
    raw = cached(HERE / "data" / game["schema_cache"], lambda: parse_object_schema(game_key))
    schema = {int(k): v for k, v in raw.items()}
    for (gk, tid), layout in _SCHEMA_LAYOUT_OVERRIDES.items():
        if gk != game_key:
            continue
        if tid not in game["tlv_names"]:
            raise RuntimeError(f"stale schema layout override: {game_key} has no type {tid}")
        # the table only supplies a layout the CTOR expressed none of, so anything derived spends it
        if tid in schema:
            raise RuntimeError(f"spent schema layout override: the parser derives {game_key} {game['tlv_names'][tid]}")
        schema[tid] = layout
    for (gk, tid), (derived, corrected) in _SCHEMA_LAYOUT_CORRECTIONS.items():
        if gk != game_key:
            continue
        if schema.get(tid) != derived:
            raise RuntimeError(f"spent schema layout correction: {game_key} type {tid} no longer derives as pinned")
        schema[tid] = corrected
    return schema

def load_enum_labels(game_key, game):
    def sweep():
        labels, bad = parse_enum_labels(game_key)
        return {"labels": labels, "bad": sorted(bad)}
    raw = cached(HERE / "data" / game["enum_cache"], sweep)
    return ({t: {int(v): lb for v, lb in vals.items()} for t, vals in raw["labels"].items()},
            set(raw["bad"]))
