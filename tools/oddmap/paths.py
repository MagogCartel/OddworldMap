"""Where the builder finds things, derived once: a module deeper in the package
must not recompute them from its own depth."""
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent   # tools/, one above this package
ROOT = HERE.parent                              # repo root
SITE = ROOT / "public"                          # the served site (default --out)
DECOMP_ENV = "ODDWORLD_DECOMP"                  # names the alive_reversing checkout; unset means the sibling
REPO = Path(os.environ.get(DECOMP_ENV) or ROOT.parent / "alive_reversing")  # only needed to regenerate tools/data caches
AO_COMMIT = "c1ba4c6c812ac65992d876d68c9e2e3e85636d6f"  # AO's PathData.cpp is read from this
                                                        # revision, not from the checkout
DECOMP_COMMIT = "e2badb8df33cafbd9b9056fe734f7a2df9f953ef"  # the checkout revision the tools/data caches were parsed from
CAM2RGBA = HERE / "cam2rgba"
