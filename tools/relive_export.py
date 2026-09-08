#!/usr/bin/env python3
"""Write paths as relive_api v4 JSON — the AliveTeam level editor's format — from
the committed map data and caches. No disc and no site change: the artifact is a
description of a path, for cross-checking this repo's extraction against
relive_api's own reader.

    python3 tools/relive_export.py --game AO --level R1 --path 15 --out /tmp/relive
    python3 tools/relive_export.py --all --out /tmp/relive

A property whose value the archive does not hold fails the run with a manifest
naming every miss, and that path's file is not written: relive's importer aborts
outright on a missing numeric key, so an incomplete file must never look whole.
--allow-incomplete writes such files anyway, manifest printed the same.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from oddmap.decomp import load_cache  # noqa: E402
from oddmap.games import GAMES, game_setup  # noqa: E402
from oddmap.paths import SITE  # noqa: E402
from oddmap.relive import digest, export_path, load_line_links, load_relive_schema  # noqa: E402

def export_game(game_key, out, only=None, allow_incomplete=False):
    """(files written, paths withheld, manifest) for one game; `only` narrows to
    one (level short, path id)"""
    game = game_setup(game_key)
    rel = load_relive_schema(game_key, game)
    links = load_line_links(game_key, game)
    data = json.loads((SITE / game["data_file"]).read_text())
    muds = load_cache(game).get("muds_in_level") if game_key == "AE" else None
    written, withheld = 0, []
    missing, fallbacks = set(), set()
    for level in data["levels"]:
        for path in level["paths"]:
            if only and only != (level["short"], path["id"]):
                continue
            doc, manifest = export_path(game_key, game, rel, level, path, muds, links)
            missing |= manifest["missing"]
            fallbacks |= manifest["fallbacks"]
            if manifest["missing"] and not allow_incomplete:
                withheld.append(f"{level['short']} P{path['id']}")
                continue
            dst = out / f"{game_key}_{level['short']}_P{path['id']}.json"
            dst.write_text(json.dumps(doc, indent=1, sort_keys=True))
            written += 1
    return written, withheld, missing, fallbacks

def write_digests(dst):
    """one canonical-form sha256 per path, which is what pins the page's exporter
    to this one: the browser has no Python to compare itself against, so both
    sides answer to the same file"""
    out = {}
    for game_key in sorted(GAMES):
        game = game_setup(game_key)
        rel = load_relive_schema(game_key, game)
        links = load_line_links(game_key, game)
        data = json.loads((SITE / game["data_file"]).read_text())
        muds = load_cache(game).get("muds_in_level") if game_key == "AE" else None
        rows = {}
        for level in data["levels"]:
            for path in level["paths"]:
                doc, _ = export_path(game_key, game, rel, level, path, muds, links)
                rows[f"{level['short']} P{path['id']}"] = digest(doc)
        out[game_key] = rows
    Path(dst).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return sum(len(v) for v in out.values())

def main():
    ap = argparse.ArgumentParser(description="export paths as relive_api v4 JSON")
    ap.add_argument("--game", choices=sorted(GAMES), help="with --level and --path, one path; with --all, one game")
    ap.add_argument("--level", help="level short name, e.g. R1")
    ap.add_argument("--path", type=int, help="numeric path id")
    ap.add_argument("--all", action="store_true", help="every path of the game(s)")
    ap.add_argument("--out", help="output directory (never public/); required unless --digests")
    ap.add_argument("--allow-incomplete", action="store_true",
                    help="write files the importer would refuse, manifest printed the same")
    ap.add_argument("--digests", metavar="FILE",
                    help="write one canonical sha256 per path instead, for the page's exporter")
    args = ap.parse_args()
    if args.digests:
        print(f"{write_digests(args.digests)} path digests -> {args.digests}")
        return
    if not args.out:
        ap.error("--out is required")
    if not args.all and not (args.game and args.level and args.path is not None):
        ap.error("either --all or all three of --game/--level/--path")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ok = True
    for game_key in [args.game] if args.game else sorted(GAMES):
        only = None if args.all else (args.level.upper(), args.path)
        written, withheld, missing, fallbacks = export_game(game_key, out, only, args.allow_incomplete)
        if only and not written and not withheld:
            ap.error(f"no {only[0]} P{only[1]} in {game_key}")
        print(f"{game_key}: {written} path file(s) -> {out}")
        for literal, prop in sorted(fallbacks):
            print(f"{game_key}: {literal}.{prop} written from its fallback (word not archived)")
        for literal, prop in sorted(missing):
            print(f"{game_key}: {literal}.{prop} has no archived value")
        if withheld:
            print(f"{game_key}: withheld {len(withheld)} incomplete path(s): {', '.join(withheld)}")
            ok = False
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
