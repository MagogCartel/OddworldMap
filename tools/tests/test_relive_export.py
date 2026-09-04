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
from unittest import mock

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

def muds_in_level():
    return json.loads((HERE / "data" / games.GAMES["AE"]["cache"]).read_text())["muds_in_level"]

def export(game_key, short, pid):
    game = games.game_setup(game_key)
    rel = relive.load_relive_schema(game_key, game)
    level = next(lv for lv in map_data(game_key)["levels"] if lv["short"] == short)
    path = next(p for p in level["paths"] if p["id"] == pid)
    muds = muds_in_level() if game_key == "AE" else None
    return relive.export_path(game_key, game, rel, level, path, muds)


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


class ExporterOutput(unittest.TestCase):
    FIXTURES = {"AO": ("R1", 15), "AE": ("MI", 1)}

    @classmethod
    def setUpClass(cls):
        cls.docs, cls.manifests, cls.paths = {}, {}, {}
        for game_key, (short, pid) in cls.FIXTURES.items():
            level = next(lv for lv in map_data(game_key)["levels"] if lv["short"] == short)
            cls.paths[game_key] = next(p for p in level["paths"] if p["id"] == pid)
            cls.docs[game_key], cls.manifests[game_key] = export(game_key, short, pid)

    def test_the_root_is_a_v4_document_of_the_game(self):
        for game_key, doc in self.docs.items():
            self.assertEqual(set(doc), {"api_version", "game", "map", "schema"})
            self.assertEqual(doc["api_version"], 4)
            self.assertEqual(doc["game"], game_key)

    def test_the_map_carries_every_key_the_import_reads(self):
        keys = {"path_bnd", "path_id", "x_size", "y_size", "x_grid_size", "y_grid_size",
                "abe_start_xpos", "abe_start_ypos", "num_muds_in_path", "total_muds",
                "num_muds_for_bad_ending", "num_muds_for_good_ending",
                "lcdscreen_messages", "hintfly_messages", "collisions", "cameras"}
        for game_key, doc in self.docs.items():
            self.assertEqual(set(doc["map"]), keys, game_key)
            self.assertEqual(set(doc["map"]["collisions"]), {"structure", "items"})

    def test_the_camera_set_is_named_cams_union_object_cells(self):
        for game_key, doc in self.docs.items():
            path, geo = self.paths[game_key], games.GAMES[game_key]["geometry"]
            named = {c["cell"]: c["name"] for c in path["cams"]}
            holding = {(t["y1"] // geo["worldH"]) * path["w"] + (t["x1"] // geo["worldW"])
                       for t in path["tlvs"]}
            cells = {c["y"] * path["w"] + c["x"]: c for c in doc["map"]["cameras"]}
            self.assertEqual(set(cells), set(named) | holding, game_key)
            for cell, cam in cells.items():
                self.assertEqual(cam["name"], named.get(cell, ""), game_key)

    def test_a_named_camera_takes_its_id_from_its_name_digits(self):
        for game_key, doc in self.docs.items():
            for cam in doc["map"]["cameras"]:
                n = cam["name"]
                want = relive.camera_id(n) if n else 0
                self.assertEqual(cam["id"], want, f"{game_key} {n!r}")
                if n:
                    self.assertEqual(cam["id"], int(n[3] + n[4]) * 100 + int(n[6] + n[7]))

    def test_positions_are_absolute_and_sizes_relative(self):
        for game_key, doc in self.docs.items():
            spans = {(t["x1"], t["y1"], t["x2"] - t["x1"], t["y2"] - t["y1"])
                     for t in self.paths[game_key]["tlvs"]}
            for cam in doc["map"]["cameras"]:
                for o in cam["map_objects"]:
                    p = o["properties"]
                    self.assertGreaterEqual(p["width"], 0)
                    self.assertGreaterEqual(p["height"], 0)
                    self.assertIn((p["xpos"], p["ypos"], p["width"], p["height"]), spans, game_key)

    def test_every_object_carries_exactly_the_registered_properties(self):
        for game_key, doc in self.docs.items():
            by_name = {s["name"]: s for s in relive_cache(game_key)["structures"].values()}
            for cam in doc["map"]["cameras"]:
                for o in cam["map_objects"]:
                    want = {"xpos", "ypos", "width", "height"} | \
                        {p["name"] for p in by_name[o["object_structures_type"]]["properties"]}
                    self.assertEqual(set(o["properties"]), want, f"{game_key} {o['name']}")

    def test_counts_match_the_map_data(self):
        for game_key, doc in self.docs.items():
            path = self.paths[game_key]
            self.assertEqual(sum(len(c["map_objects"]) for c in doc["map"]["cameras"]),
                             len(path["tlvs"]), game_key)
            items = doc["map"]["collisions"]["items"]
            self.assertEqual(len(items), len(path["lines"]), game_key)
            link_keys = {"Next", "Previous"} | ({"Next 2", "Previous 2", "Length"}
                                               if game_key == "AE" else set())
            for item in items:
                self.assertEqual(set(item), {"x1", "y1", "x2", "y2", "Type"} | link_keys)
                self.assertIsInstance(item["Type"], str)

    def test_the_message_arrays_are_empty_like_a_vanilla_lvl(self):
        for doc in self.docs.values():
            self.assertEqual(doc["map"]["lcdscreen_messages"], [])
            self.assertEqual(doc["map"]["hintfly_messages"], [])

    def test_the_mud_scalars_are_the_engines(self):
        ao, ae = self.docs["AO"]["map"], self.docs["AE"]["map"]
        self.assertEqual([ao[k] for k in ("abe_start_xpos", "abe_start_ypos", "num_muds_in_path",
                                          "total_muds", "num_muds_for_bad_ending",
                                          "num_muds_for_good_ending")], [0, 0, 0, 99, 75, 50])
        self.assertEqual([ae[k] for k in ("abe_start_xpos", "abe_start_ypos")], [1875, 0])
        self.assertEqual([ae[k] for k in ("num_muds_in_path", "total_muds",
                                          "num_muds_for_bad_ending", "num_muds_for_good_ending")],
                         [muds_in_level()[1], 300, 20, 255])
        # MI P2's level id (1) and path id (2) name different table rows, so this
        # is what pins the indexing as the engine's, by level
        mi2, _ = export("AE", "MI", 2)
        self.assertNotEqual(muds_in_level()[1], muds_in_level()[2])
        self.assertEqual(mi2["map"]["num_muds_in_path"], muds_in_level()[1])

    def test_the_schema_names_every_structure_and_used_enum(self):
        for game_key, doc in self.docs.items():
            cache = relive_cache(game_key)
            blob = doc["schema"]
            self.assertEqual({s["name"] for s in blob["object_structures"]},
                             {s["name"] for s in cache["structures"].values()})
            enum_names = {e["name"] for e in blob["object_structure_property_enums"]}
            for s in cache["structures"].values():
                for p in s["properties"]:
                    if p["enum"]:
                        self.assertIn(p["type"], enum_names)
            self.assertEqual([b["name"] for b in blob["object_structure_property_basic_types"]],
                             ["Byte", "UInt16", "SInt16", "Uint32", "SInt32"])

    def test_the_same_inputs_export_identical_bytes(self):
        for game_key, (short, pid) in self.FIXTURES.items():
            again, _ = export(game_key, short, pid)
            self.assertEqual(json.dumps(self.docs[game_key], indent=1, sort_keys=True),
                             json.dumps(again, indent=1, sort_keys=True))

    def test_a_fallback_for_an_archived_word_fails_the_export(self):
        entry = {("AO", "AbeStart", "Scale"): 0}
        with mock.patch.dict(relive._EXPORT_VALUE_FALLBACKS, entry), self.assertRaises(RuntimeError):
            export("AO", *self.FIXTURES["AO"])


class ExportSweep(unittest.TestCase):
    """every path of both games through the exporter: the archive answers every
    property relive reads, with the unarchived words pinned to the fallback table
    exactly — anything new goes missing loudly here first"""

    FALLBACKS = {
        "AO": {("ShadowZone", "R"), ("ShadowZone", "G"), ("ShadowZone", "B")},
        "AE": {("ShadowZone", "R"), ("ShadowZone", "G"), ("ShadowZone", "B"),
               ("MovieHandstone", "Trigger Switch ID"), ("SecurityClaw", "Unknown")},
    }

    def test_the_archive_answers_every_property_relive_reads(self):
        for game_key in ("AO", "AE"):
            game = games.game_setup(game_key)
            rel = relive.load_relive_schema(game_key, game)
            muds = muds_in_level() if game_key == "AE" else None
            missing, fallbacks = set(), set()
            for level in map_data(game_key)["levels"]:
                for path in level["paths"]:
                    _, manifest = relive.export_path(game_key, game, rel, level, path, muds)
                    missing |= manifest["missing"]
                    fallbacks |= manifest["fallbacks"]
            self.assertEqual(missing, set(), game_key)
            self.assertEqual(fallbacks, self.FALLBACKS[game_key], game_key)


if __name__ == "__main__":
    unittest.main()
