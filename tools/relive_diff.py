#!/usr/bin/env python3
"""Structurally diff two relive_api path JSONs — ours against a reference export
of the same path from the real LVL — printing what disagrees and holding back
the classes that are expected to, so a clean run means the extractions agree.

    python3 tools/relive_diff.py ours.json reference.json
    python3 tools/relive_diff.py ours.json reference.json --strict-links

Never a byte diff: the reference writer's key order is jsonxx's, its schema
arrays iterate unordered_maps, and its camera images are garbage base64 from a
PS1 CAM (never read here). Collision link fields stay a counted, non-fatal class
until a rebuild captures them (--strict-links promotes them), and the property
values the exporter's fallback table stands in for are held known-divergent by
that same table, so retiring an entry there retires its tolerance here.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from oddmap.relive import _EXPORT_VALUE_FALLBACKS  # noqa: E402

_LINK_KEYS = {"Next", "Previous", "Next 2", "Previous 2", "Length"}

def diff_documents(ours, theirs, strict_links=False):
    """{"diffs", "links", "known", "warnings"}: lists of finding strings. Clean
    means no diffs (and no links under --strict-links)."""
    out = {"diffs": [], "links": [], "known": [], "warnings": []}
    game = ours.get("game")
    known_props = {(lit, prop) for (gk, lit, prop) in _EXPORT_VALUE_FALLBACKS if gk == game}

    for key in ("api_version", "game"):
        if ours.get(key) != theirs.get(key):
            out["diffs"].append(f"{key}: {ours.get(key)!r} != {theirs.get(key)!r}")

    a_map, b_map = ours.get("map", {}), theirs.get("map", {})
    for key in sorted((set(a_map) | set(b_map)) - {"collisions", "cameras"}):
        if a_map.get(key) == b_map.get(key):
            continue
        finding = f"map.{key}: {a_map.get(key)!r} != {b_map.get(key)!r}"
        # the reference indexes AE's mud table by its path index (relive_api.cpp
        # hands ToPathInfo the id PathAt was given), ours by level id, which is
        # how the engine reads the table back — divergent by design on most paths
        if key == "num_muds_in_path" and game == "AE":
            out["known"].append(finding)
        else:
            out["diffs"].append(finding)

    a_items = a_map.get("collisions", {}).get("items", [])
    b_items = b_map.get("collisions", {}).get("items", [])
    if len(a_items) != len(b_items):
        out["diffs"].append(f"collisions: {len(a_items)} items != {len(b_items)}")
    for i, (a, b) in enumerate(zip(a_items, b_items)):
        for key in sorted(set(a) | set(b)):
            if a.get(key) == b.get(key):
                continue
            finding = f"collisions[{i}].{key}: {a.get(key)!r} != {b.get(key)!r}"
            out["diffs" if strict_links or key not in _LINK_KEYS else "links"].append(finding)

    a_cams = {(c["x"], c["y"]): c for c in a_map.get("cameras", [])}
    b_cams = {(c["x"], c["y"]): c for c in b_map.get("cameras", [])}
    for cell in sorted(set(a_cams) ^ set(b_cams)):
        side = "ours" if cell in a_cams else "reference"
        out["diffs"].append(f"camera {cell}: only in {side}")
    for cell in sorted(set(a_cams) & set(b_cams)):
        a, b = a_cams[cell], b_cams[cell]
        for key in ("name", "id"):
            if a.get(key) != b.get(key):
                out["diffs"].append(f"camera {cell} {key}: {a.get(key)!r} != {b.get(key)!r}")
        _diff_objects(cell, a.get("map_objects", []), b.get("map_objects", []), known_props, out)

    _diff_schema(ours.get("schema", {}), theirs.get("schema", {}), out)
    return out

def _canon(obj, known_props):
    props = {k: v for k, v in obj.get("properties", {}).items()
             if (obj.get("object_structures_type"), k) not in known_props}
    return json.dumps([obj.get("object_structures_type"), props], sort_keys=True)

def _diff_objects(cell, a_objs, b_objs, known_props, out):
    if len(a_objs) != len(b_objs):
        out["diffs"].append(f"camera {cell}: {len(a_objs)} objects != {len(b_objs)}")
        return
    local = {"diffs": [], "known": [], "warnings": []}
    for i, (a, b) in enumerate(zip(a_objs, b_objs)):
        ty = a.get("object_structures_type")
        if ty != b.get("object_structures_type"):
            local["diffs"].append(
                f"camera {cell} object {i}: {ty!r} != {b.get('object_structures_type')!r}")
            continue
        if a.get("name") != b.get("name"):
            local["warnings"].append(
                f"camera {cell} object {i} name: {a.get('name')!r} != {b.get('name')!r}")
        ap, bp = a.get("properties", {}), b.get("properties", {})
        for key in sorted(set(ap) | set(bp)):
            if ap.get(key) == bp.get(key):
                continue
            finding = f"camera {cell} {ty}.{key}: {ap.get(key)!r} != {bp.get(key)!r}"
            local["known" if (ty, key) in known_props else "diffs"].append(finding)
    # positional findings from a mere reorder are noise: retry as multisets,
    # re-pairing by content so the known-divergent values still get counted
    if local["diffs"] and sorted(_canon(o, known_props) for o in a_objs) == \
            sorted(_canon(o, known_props) for o in b_objs):
        out["warnings"].append(f"camera {cell}: same objects, different order")
        a_sorted = sorted(a_objs, key=lambda o: _canon(o, known_props))
        b_sorted = sorted(b_objs, key=lambda o: _canon(o, known_props))
        for a, b in zip(a_sorted, b_sorted):
            ap, bp = a.get("properties", {}), b.get("properties", {})
            for prop in sorted(set(ap) | set(bp)):
                if ap.get(prop) != bp.get(prop):
                    out["known"].append(f"camera {cell} {a.get('object_structures_type')}.{prop}: "
                                        f"{ap.get(prop)!r} != {bp.get(prop)!r}")
        return
    for kind, findings in local.items():
        out[kind].extend(findings)

def _diff_schema(a, b, out):
    a_structs = {s["name"]: s for s in a.get("object_structures", [])}
    b_structs = {s["name"]: s for s in b.get("object_structures", [])}
    for name in sorted(set(a_structs) ^ set(b_structs)):
        out["diffs"].append(f"schema structure {name}: one side only")
    for name in sorted(set(a_structs) & set(b_structs)):
        if a_structs[name] != b_structs[name]:
            out["diffs"].append(f"schema structure {name}: descriptors differ")
    for section, values_as_set in (("object_structure_property_enums", True),
                                   ("object_structure_property_basic_types", False)):
        a_by = {e["name"]: e for e in a.get(section, [])}
        b_by = {e["name"]: e for e in b.get(section, [])}
        for name in sorted(set(a_by) ^ set(b_by)):
            out["diffs"].append(f"schema {section} {name}: one side only")
        for name in sorted(set(a_by) & set(b_by)):
            ea, eb = dict(a_by[name]), dict(b_by[name])
            if values_as_set:  # the reference iterates an unordered_map here
                ea["values"], eb["values"] = sorted(ea.get("values", [])), sorted(eb.get("values", []))
            if ea != eb:
                out["diffs"].append(f"schema {section} {name}: differs")

def main():
    ap = argparse.ArgumentParser(description="structurally diff two relive_api path JSONs")
    ap.add_argument("ours")
    ap.add_argument("reference")
    ap.add_argument("--strict-links", action="store_true",
                    help="collision link fields count as real divergence")
    args = ap.parse_args()
    result = diff_documents(json.loads(Path(args.ours).read_text()),
                            json.loads(Path(args.reference).read_text()),
                            strict_links=args.strict_links)
    for kind in ("diffs", "links", "known", "warnings"):
        for line in result[kind]:
            print(f"{kind[:-1]}: {line}")
    counts = ", ".join(f"{len(result[k])} {k}" for k in ("diffs", "links", "known", "warnings"))
    print(("CLEAN — " if not result["diffs"] else "DIVERGENT — ") + counts)
    sys.exit(1 if result["diffs"] else 0)

if __name__ == "__main__":
    main()
