#!/usr/bin/env python3
"""Run every exported path through relive_api's own JSON reader — the oracle for
what our tests cannot judge: whether the reference implementation accepts each
document and resolves every enum label without a silent remap.

    python3 tools/relive_verify.py                     # both games, every path
    python3 tools/relive_verify.py --game AO
    python3 tools/relive_verify.py --dump-lvl AO R1 /tmp/R1.LVL   # for the disc session

Needs cmake and the alive_reversing checkout ($ODDWORLD_DECOMP, else beside this
repo) sitting at the pin: every run (re)builds tools/relive_check against it, a
no-op when nothing changed and a fresh build dir after a re-pin, into
~/.cache/oddworldmap/relive_check (outside the repo: a binary in a synced working
tree can lose its signature under it and die on launch). Each document is
checked in a subprocess of its own, because relive aborts the process outright
on a missing numeric property.

--dump-lvl needs a disc image ($ODDWORLD_DISC_AO / $ODDWORLD_DISC_AE) and writes
the byte-exact LVL the reference exporter is then pointed at.
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from oddmap.decomp import pinned_checkout  # noqa: E402
from oddmap.games import GAMES  # noqa: E402
from oddmap.paths import DECOMP_COMMIT  # noqa: E402
from relive_export import export_game  # noqa: E402

BUILD = Path(os.environ.get("RELIVE_CHECK_BUILD",
                            Path.home() / ".cache" / "oddworldmap" / "relive_check"))
SHIM_SUBMODULES = ("3rdParty/googletest", "3rdParty/json", "3rdParty/jsonxx", "3rdParty/lodepng",
                   "3rdParty/magic_enum")

def ensure_harness():
    """the relive_check binary, (re)built against the pinned checkout on every run:
    cmake's own dependency tracking makes an unchanged build a no-op, and a build
    dir stamped with another revision, or configured from another checkout of
    this repo, is wiped rather than trusted"""
    src = HERE / "relive_check"
    try:
        repo = pinned_checkout()
    except RuntimeError as e:
        sys.exit(f"the harness builds against the pinned checkout: {e}")
    status = subprocess.run(["git", "-C", str(repo), "submodule", "status", "--", *SHIM_SUBMODULES],
                            capture_output=True, text=True)
    if status.returncode:
        sys.exit(f"cannot read the shim's submodules:\n{status.stderr}")
    off = [line.split()[1] for line in status.stdout.splitlines() if line[:1] != " "]
    if off:
        sys.exit(f"submodule(s) {', '.join(off)} not at their recorded commit — run: "
                 f"git -C {repo} submodule update --init")
    if not shutil.which("cmake"):
        sys.exit("cmake not found — install it (brew install cmake) to build the harness")
    stamp, cache = BUILD / "decomp_head", BUILD / "CMakeCache.txt"
    home = next((line.split("=", 1)[1] for line in cache.read_text().splitlines()
                 if line.startswith("CMAKE_HOME_DIRECTORY:INTERNAL=")), str(src)) if cache.exists() else str(src)
    if (stamp.exists() and stamp.read_text().strip() != DECOMP_COMMIT) or Path(home).resolve() != src.resolve():
        shutil.rmtree(BUILD)
    for args in (["cmake", "-S", str(src), "-B", str(BUILD), f"-DALIVE_DIR={repo}"],
                 ["cmake", "--build", str(BUILD), "-j"]):
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode:
            sys.exit(f"harness build failed:\n{r.stdout}\n{r.stderr}")
    stamp.write_text(DECOMP_COMMIT + "\n")
    return BUILD / "relive_check"

def verify(game_keys):
    binary = ensure_harness()
    failed = 0
    with tempfile.TemporaryDirectory(prefix="relive-verify-") as tmp:
        for game_key in game_keys:
            out = Path(tmp) / game_key
            out.mkdir()
            _written, withheld, _missing, fallbacks = export_game(game_key, out)
            if withheld:
                sys.exit(f"{game_key}: {len(withheld)} path(s) unexportable — run relive_export for the manifest")
            checked = 0
            for f in sorted(out.iterdir()):
                r = subprocess.run([str(binary), "check", str(f)], capture_output=True, text=True)
                if r.returncode:
                    failed += 1
                    print(f"{game_key} {f.name}: FAILED\n{r.stdout}{r.stderr}")
                checked += 1
            print(f"{game_key}: {checked} path documents checked, "
                  f"{len(fallbacks)} fallback-filled properties")
    return failed

def dump_lvl(game_key, short, dst):
    from oddmap.disc import Disc, Lvl
    paths = [p for p in os.environ.get(GAMES[game_key]["env"], "").split(os.pathsep) if p]
    if not paths:
        sys.exit(f"no disc image: set ${GAMES[game_key]['env']}")
    name = f"{short.upper()}.LVL"
    # multi-disc games carry stub copies of the other disc's levels: pick the largest
    having = [d for d in (Disc(p) for p in paths) if name in d.files]
    if not having:
        sys.exit(f"no {name} on the disc image(s)")
    disc = max(having, key=lambda d: d.files[name][1])
    lvl = Lvl(disc, name)
    Path(dst).write_bytes(disc.read(lvl.lba, lvl.size))
    print(f"{name} ({lvl.size} bytes) -> {dst}")

def main():
    ap = argparse.ArgumentParser(description="check exported paths against relive_api's reader")
    ap.add_argument("--game", choices=sorted(GAMES), help="one game (default: both)")
    ap.add_argument("--dump-lvl", nargs=3, metavar=("GAME", "LEVEL", "OUT"),
                    help="write a byte-exact LVL off the disc image instead")
    args = ap.parse_args()
    if args.dump_lvl:
        game_key = args.dump_lvl[0].upper()
        if game_key not in GAMES:
            ap.error(f"unknown game {args.dump_lvl[0]!r}")
        dump_lvl(game_key, args.dump_lvl[1], args.dump_lvl[2])
        return
    failed = verify([args.game] if args.game else sorted(GAMES))
    print("every document read clean" if not failed else f"{failed} document(s) failed")
    sys.exit(1 if failed else 0)

if __name__ == "__main__":
    main()
