"""The alive_reversing checkout as the tests see it: the decorator for the tests
that parse it, and the message for a cache that does not reproduce from it."""
import os
import subprocess
import unittest

from oddmap.paths import DECOMP_COMMIT, DECOMP_ENV, REPO

needs_decomp = unittest.skipUnless(os.environ.get(DECOMP_ENV) or REPO.exists(),
                                   f"no alive_reversing checkout at {REPO}: clone it there or set ${DECOMP_ENV}")


def stale(cache):
    """a cache differing from a fresh parse is usually the checkout having moved, not the cache"""
    head = subprocess.run(["git", "-C", str(REPO), "rev-parse", "--short", "HEAD"],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip()
    if head and DECOMP_COMMIT.startswith(head):
        return (f"{cache} does not reproduce from the pinned checkout ({head}): regenerate it there, "
                f"or move DECOMP_COMMIT to the revision it was parsed from")
    return (f"{cache} does not reproduce from the checkout at {head or 'an unknown revision'}; the caches are pinned to "
            f"{DECOMP_COMMIT[:9]}: check that out, or re-pin (move DECOMP_COMMIT, delete the cache, "
            f"regenerate, re-emit the sidecars)")
