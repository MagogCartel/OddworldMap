"""Tests for the relive_api export path: the schema cache it reads and the JSON
it writes. Stdlib only, no disc; the fresh-sweep check skips where no checkout is
configured or found, a variable naming none failing it instead (CI points
$ODDWORLD_DECOMP at a clone of the pin, so it runs there), and everything else
runs from the committed tree.
"""

import json
import sys
import unittest
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]

from oddmap import games, relive, schema  # noqa: E402
from oddmap.paths import HERE, SITE  # noqa: E402
from decomp_checkout import needs_decomp, stale  # noqa: E402

def relive_cache(game_key):
    return json.loads((HERE / "data" / games.GAMES[game_key]["relive_cache"]).read_text())

def map_data(game_key):
    return json.loads((SITE / games.GAMES[game_key]["data_file"]).read_text())

def placed_types(game_key):
    return {t["t"] for lv in map_data(game_key)["levels"] for p in lv["paths"] for t in p["tlvs"]}


class ReliveCache(unittest.TestCase):
    def test_every_placed_type_has_a_structure(self):
        for game_key in ("AO", "AE"):
            structures = relive_cache(game_key)["structures"]
            for tid in placed_types(game_key):
                self.assertIn(str(tid), structures, f"{game_key} type {tid}")

    def test_property_rows_carry_the_join_and_the_typing(self):
        for game_key in ("AO", "AE"):
            for tid, s in relive_cache(game_key)["structures"].items():
                self.assertRegex(s["name"], r"^\w+$")
                for p in s["properties"]:
                    self.assertEqual(p["key"], schema.norm(p["name"]), f"{game_key} {tid}")
                    self.assertGreaterEqual(p["word"], 0)
                    self.assertIn(p["size"], (1, 2, 4))
                    self.assertIsInstance(p["enum"], bool)
                    self.assertIsInstance(p["visible"], bool)

    def test_enum_tables_are_verbatim_string_maps(self):
        for game_key in ("AO", "AE"):
            enums = relive_cache(game_key)["enums"]
            for name, table in enums.items():
                self.assertTrue(table, name)
                for v, label in table.items():
                    self.assertRegex(v, r"^-?\d+$", f"{name}: {v}")
                    self.assertTrue(label and isinstance(label, str), f"{name} {v}")
            self.assertEqual(enums["Enum_LineTypes"]["1"], "Wall Left")
            self.assertIn("Enum_Scale_short", enums)

    def test_the_collision_structure_names_the_reader_keys(self):
        shared = ["x1", "y1", "x2", "y2", "Type"]
        names = {"AO": shared + ["Next", "Previous"],
                 "AE": shared + ["Next", "Previous", "Next 2", "Previous 2", "Length"]}
        for game_key in ("AO", "AE"):
            rows = relive_cache(game_key)["collision_structure"]
            self.assertEqual([r["name"] for r in rows], names[game_key])
            self.assertEqual(rows[4]["type"], "Enum_LineTypes")

    @needs_decomp
    def test_the_committed_cache_matches_a_fresh_sweep(self):
        for game_key in ("AO", "AE"):
            cache = HERE / "data" / games.GAMES[game_key]["relive_cache"]
            self.assertEqual(
                cache.read_text(),
                json.dumps(relive.parse_relive_schema(game_key), indent=1),
                stale(cache.name),
            )


class WordAudit(unittest.TestCase):
    """relive's struct-derived words against the archive's ADD-order words: a
    disagreement is a member name lying about its offset, and every known liar
    is pinned so the next one fails here instead of shipping."""

    LIARS = {
        ("AE", "MovieHandstone", "movie_number"),
        ("AE", "MovieHandstone", "padding"),
        ("AE", "MovieHandstone", "trigger_switch_id"),
        ("AE", "SecurityClaw", "disabled_resources"),
        ("AE", "SecurityClaw", "unknown"),
    }

    def test_the_two_views_disagree_exactly_where_pinned(self):
        found = set()
        for game_key in ("AO", "AE"):
            game = games.game_setup(game_key)
            for tid, s in relive_cache(game_key)["structures"].items():
                ours = {name: word for word, name, *_ in game["schema"].get(int(tid), [])}
                theirs = {p["key"]: p["word"] for p in s["properties"]}
                for key in set(ours) | set(theirs):
                    if ours.get(key) != theirs.get(key):
                        found.add((game_key, s["name"], key))
        self.assertEqual(found, self.LIARS)


if __name__ == "__main__":
    unittest.main()
