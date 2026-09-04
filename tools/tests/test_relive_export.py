"""Tests for the relive_api export path: the schema cache it reads and the JSON
it writes. Stdlib only, no disc; the fresh-sweep check skips where no checkout is
configured or found, a variable naming none failing it instead (CI points
$ODDWORLD_DECOMP at a clone of the pin, so it runs there), and everything else
runs from the committed tree.
"""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path[:0] = [str(Path(__file__).resolve().parents[1]), str(Path(__file__).resolve().parent)]

from oddmap import games, relive, schema  # noqa: E402
from oddmap.paths import DECOMP_COMMIT, HERE, SITE  # noqa: E402
from decomp_checkout import needs_decomp, stale  # noqa: E402
import relive_verify  # noqa: E402

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


class ReliveDiff(unittest.TestCase):
    """the structural diff over mutated copies of a real export: what must read
    clean, what lands in the tolerated classes, what is a real divergence"""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(HERE))
        import relive_diff
        cls.diff = staticmethod(relive_diff.diff_documents)
        cls.doc, _ = export("AO", "R1", 15)

    def copy(self):
        return json.loads(json.dumps(self.doc))

    def test_identical_documents_are_clean(self):
        result = self.diff(self.doc, self.copy())
        self.assertEqual(result, {"diffs": [], "links": [], "known": [], "warnings": []})

    def test_a_changed_property_names_the_object_and_key(self):
        other = self.copy()
        cam = next(c for c in other["map"]["cameras"] if c["map_objects"])
        cam["map_objects"][0]["properties"]["xpos"] += 1
        result = self.diff(self.doc, other)
        self.assertEqual(len(result["diffs"]), 1)
        self.assertIn(".xpos:", result["diffs"][0])

    def test_a_missing_camera_is_named_by_grid_cell(self):
        other = self.copy()
        gone = other["map"]["cameras"].pop()
        result = self.diff(self.doc, other)
        self.assertTrue(any(f"({gone['x']}, {gone['y']})" in d for d in result["diffs"]))

    def test_link_fields_divert_until_strict_promotes_them(self):
        other = self.copy()
        other["map"]["collisions"]["items"][0]["Next"] = 42
        lax = self.diff(self.doc, other)
        self.assertEqual((len(lax["diffs"]), len(lax["links"])), (0, 1))
        strict = self.diff(self.doc, other, strict_links=True)
        self.assertEqual((len(strict["diffs"]), len(strict["links"])), (1, 0))

    def test_the_references_mud_indexing_is_held_known_divergent(self):
        ae, _ = export("AE", "MI", 2)
        other = json.loads(json.dumps(ae))
        other["map"]["num_muds_in_path"] = muds_in_level()[2]
        result = self.diff(ae, other)
        self.assertEqual(result["diffs"], [])
        self.assertEqual(len(result["known"]), 1)
        strict_ao = self.copy()
        strict_ao["map"]["num_muds_in_path"] = 5
        self.assertEqual(len(self.diff(self.doc, strict_ao)["diffs"]), 1)

    def test_a_fallback_value_is_held_known_divergent(self):
        other = self.copy()
        zone = next(o for c in other["map"]["cameras"] for o in c["map_objects"]
                    if o["object_structures_type"] == "ShadowZone")
        zone["properties"]["R"] = 4096
        result = self.diff(self.doc, other)
        self.assertEqual(result["diffs"], [])
        self.assertEqual(len(result["known"]), 1)

    def test_reference_side_orderings_stay_clean(self):
        other = self.copy()
        for enum in other["schema"]["object_structure_property_enums"]:
            enum["values"].reverse()
        other["schema"]["object_structures"].reverse()
        other["map"]["cameras"][0]["image"] = "bm90IGEgcG5n"
        result = self.diff(self.doc, other)
        self.assertEqual(result["diffs"], [])

    def test_reordered_objects_are_a_warning_not_a_diff(self):
        other = self.copy()
        cam = next(c for c in other["map"]["cameras"] if len(c["map_objects"]) > 1)
        cam["map_objects"].reverse()
        result = self.diff(self.doc, other)
        self.assertEqual(result["diffs"], [])
        self.assertTrue(any("different order" in w for w in result["warnings"]))

    def test_a_reorder_still_counts_the_known_divergences(self):
        other = self.copy()
        cam = next(c for c in other["map"]["cameras"]
                   if len(c["map_objects"]) > 1
                   and any(o["object_structures_type"] == "ShadowZone" for o in c["map_objects"]))
        zone = next(o for o in cam["map_objects"] if o["object_structures_type"] == "ShadowZone")
        zone["properties"]["R"] = 4096
        cam["map_objects"].reverse()
        result = self.diff(self.doc, other)
        self.assertEqual(result["diffs"], [])
        self.assertTrue(any("different order" in w for w in result["warnings"]))
        self.assertEqual(len(result["known"]), 1)

    def test_a_renamed_instance_is_a_warning(self):
        other = self.copy()
        cam = next(c for c in other["map"]["cameras"] if c["map_objects"])
        cam["map_objects"][0]["name"] = "Renamed_9"
        result = self.diff(self.doc, other)
        self.assertEqual(result["diffs"], [])
        self.assertEqual(len(result["warnings"]), 1)


class Harness(unittest.TestCase):
    """ensure_harness's refusals and its build-dir stamp, with git and cmake stood in for"""

    def harness(self, status="", stamp=None, prebuilt=False, build_ok=True, pin_error=None, home=None, build=None):
        build = build or self.build_dir()
        if prebuilt:
            home = home or relive_verify.HERE / "relive_check"
            (build / "CMakeCache.txt").write_text(f"CMAKE_HOME_DIRECTORY:INTERNAL={home}\n")
        if stamp:
            (build / "decomp_head").write_text(stamp + "\n")
        calls = []

        def run(args, **kwargs):
            calls.append(args)
            if args[0] == "git":
                return subprocess.CompletedProcess(args, 0, stdout=status, stderr="")
            build.mkdir(exist_ok=True)
            return subprocess.CompletedProcess(args, 0 if build_ok else 1, stdout="", stderr="")

        pin = mock.Mock(side_effect=pin_error) if pin_error else mock.Mock(return_value=Path("/pin"))
        with mock.patch.object(relive_verify, "pinned_checkout", pin), \
             mock.patch.object(relive_verify, "BUILD", build), \
             mock.patch.object(relive_verify.shutil, "which", return_value="/usr/bin/cmake"), \
             mock.patch.object(relive_verify.subprocess, "run", side_effect=run):
            binary = relive_verify.ensure_harness()
        return binary, build, calls

    def build_dir(self):
        build = Path(tempfile.mkdtemp(prefix="rc-"))
        self.addCleanup(shutil.rmtree, build, ignore_errors=True)
        return build

    OK = " 1111111 3rdParty/googletest (v1)\n 2222222 3rdParty/json (v3)\n 3333333 3rdParty/jsonxx (v1)\n" \
         " 4444444 3rdParty/lodepng (x)\n 5555555 3rdParty/magic_enum (v0)\n"

    def test_a_refused_checkout_names_the_harness_first(self):
        with self.assertRaises(SystemExit) as cm:
            self.harness(pin_error=RuntimeError("the checkout at /pin is at 0000000 but the caches are pinned"))
        self.assertRegex(str(cm.exception), r"^the harness builds against the pinned checkout: the checkout at /pin")

    def test_submodules_off_their_commit_are_named(self):
        off = self.OK.replace(" 3333333", "-3333333").replace(" 5555555", "+5555555")
        with self.assertRaises(SystemExit) as cm:
            self.harness(status=off)
        self.assertIn("3rdParty/jsonxx, 3rdParty/magic_enum", str(cm.exception))

    def test_the_build_is_configured_against_the_pinned_checkout_and_stamped(self):
        binary, build, calls = self.harness(status=self.OK)
        self.assertEqual(binary, build / "relive_check")
        self.assertIn("-DALIVE_DIR=/pin", calls[1])
        self.assertEqual((build / "decomp_head").read_text().strip(), DECOMP_COMMIT)

    def test_a_build_dir_stamped_with_another_revision_is_wiped_first(self):
        _, build, _ = self.harness(status=self.OK, stamp="f" * 40, prebuilt=True)
        self.assertFalse((build / "CMakeCache.txt").exists())
        self.assertEqual((build / "decomp_head").read_text().strip(), DECOMP_COMMIT)

    def test_a_build_dir_configured_from_another_checkout_is_wiped_first(self):
        _, build, _ = self.harness(status=self.OK, stamp=DECOMP_COMMIT, prebuilt=True,
                                   home="/elsewhere/OddworldMap/tools/relive_check")
        self.assertFalse((build / "CMakeCache.txt").exists())

    def test_an_unstamped_or_matching_build_dir_is_kept(self):
        for stamp in (None, DECOMP_COMMIT):
            _, build, _ = self.harness(status=self.OK, stamp=stamp, prebuilt=True)
            self.assertTrue((build / "CMakeCache.txt").exists())

    def test_a_failed_build_leaves_no_stamp(self):
        build = self.build_dir()
        with self.assertRaises(SystemExit):
            self.harness(status=self.OK, build_ok=False, build=build)
        self.assertFalse((build / "decomp_head").exists())


if __name__ == "__main__":
    unittest.main()
