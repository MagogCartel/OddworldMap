"""Unit tests for the builder's pure functions: python3 -m unittest discover -s tools/tests

Stdlib only, and nothing here needs a disc image. The committed sidecars must
reproduce from the committed caches, and the caches from a fresh parse of the
alive_reversing checkout — the checkout-probing tests (the member-type parser
pair and the cache freshness checks) skip where none is found, beside the repo or
at $ODDWORLD_DECOMP, which CI points at a clone of the pin; a variable naming no
checkout fails them instead.
"""

import contextlib
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from oddmap import decomp, disc, emit, games, image, messages, schema, tlv  # noqa: E402
from oddmap.paths import AO_COMMIT, DECOMP_COMMIT, DECOMP_ENV, HERE, REPO, SITE  # noqa: E402

# the CLI has no test of its own and lint cannot resolve a cross-module import,
# so loading it here is what catches a name it asks the package for and misses
import build_map  # noqa: E402,F401


def chunk(tag, rid, payload, size=None):
    """one .BND chunk: 16-byte header (size covers it) + payload"""
    typ = int.from_bytes(tag.encode("latin1"), "little")
    size = len(payload) + 16 if size is None else size
    return struct.pack("<IHHII", size, 0, 0, typ, rid) + payload


class ParseChunks(unittest.TestCase):
    def test_keys_by_tag_and_id(self):
        data = chunk("Path", 1, b"abcd") + chunk("Path", 2, b"efgh") + chunk("End!", 0, b"")
        self.assertEqual(disc.parse_chunks(data), {("Path", 1): b"abcd", ("Path", 2): b"efgh"})

    def test_first_of_a_repeated_key_wins(self):
        data = chunk("Path", 1, b"first") + chunk("Path", 1, b"second")
        self.assertEqual(disc.parse_chunks(data), {("Path", 1): b"first"})

    def test_stops_at_the_end_marker(self):
        data = chunk("Path", 1, b"abcd") + chunk("End!", 0, b"") + chunk("Path", 2, b"never")
        self.assertNotIn(("Path", 2), disc.parse_chunks(data))

    def test_a_garbage_header_terminates(self):
        # a size that doesn't advance, or one that runs past the buffer, must end
        # the walk: both spun forever or read out of bounds before the guards
        self.assertEqual(disc.parse_chunks(chunk("Path", 1, b"abcd", size=8)), {})
        self.assertEqual(disc.parse_chunks(chunk("Path", 1, b"abcd", size=4096)), {})


class IntRows(unittest.TestCase):
    def test_keeps_integers_in_order_and_drops_the_rest(self):
        body = """
            { 0, 1, -2, kNullThing, 0x10, 3 },
            { 4, "name", 5 },
        """
        self.assertEqual(decomp.int_rows(body), [[0, 1, -2, 3], [4, 5]])


class MatchBrace(unittest.TestCase):
    def test_returns_past_the_matching_close(self):
        text = "enum E { a, b } trailing"
        self.assertEqual(text[: schema._match_brace(text, text.index("{"))], "enum E { a, b }")

    def test_skips_nested_braces(self):
        text = "struct S { enum E { a } m; } after"
        self.assertEqual(text[schema._match_brace(text, text.index("{")) :], " after")

    def test_unbalanced_ends_at_the_text(self):
        text = "struct S { enum E { a }"
        self.assertEqual(schema._match_brace(text, text.index("{")), len(text))


class StripComments(unittest.TestCase):
    def test_removes_line_and_block_comments(self):
        self.assertEqual(schema._strip_comments("a /* b */ c // d\ne"), "a  c \ne")

    def test_a_commented_enum_does_not_swallow_the_next_definition(self):
        src = "// enum Ignored {\nenum Real { a, b };"
        self.assertEqual(schema._strip_comments(src), "\nenum Real { a, b };")

    def test_a_comma_in_a_comment_mints_no_enumerator(self):
        src = "enum E { a, /* one, two */ b };"
        self.assertEqual(schema._strip_comments(src).count(","), 1)


class DeriveLabel(unittest.TestCase):
    def test_drops_the_value_suffix_and_e_prefix_and_splits_camel_case(self):
        self.assertEqual(schema._derive_label("eChaseAndDisappear_4"), "Chase And Disappear")

    def test_keeps_an_e_that_is_part_of_the_word(self):
        self.assertEqual(schema._derive_label("end_3"), "End")

    def test_leaves_an_all_caps_run_alone(self):
        self.assertEqual(schema._derive_label("eTLVSpawn_1"), "TLVSpawn")


class InheritMemberTypes(unittest.TestCase):
    def test_a_base_members_type_reaches_the_derived_struct(self):
        flat = schema._inherit_member_types(
            {("Base", "scale"): "Scale_short"}, {"Derived": "Base"}, {("Base", "scale")})
        self.assertEqual(flat[("Derived", "scale")], "Scale_short")

    def test_the_derived_structs_own_declaration_wins(self):
        types = {("Base", "m"): "A", ("Derived", "m"): "B"}
        flat = schema._inherit_member_types(types, {"Derived": "Base"},
                                            {("Base", "m"), ("Derived", "m")})
        self.assertEqual(flat[("Derived", "m")], "B")

    def test_an_own_declaration_hides_the_base_even_where_a_filter_left_it_untyped(self):
        flat = schema._inherit_member_types({("Base", "m"): "A"}, {"Derived": "Base"},
                                            {("Base", "m"), ("Derived", "m")})
        self.assertNotIn(("Derived", "m"), flat)

    def test_a_chain_resolves_through_every_base(self):
        flat = schema._inherit_member_types({("Top", "m"): "A"}, {"Mid": "Top", "Bottom": "Mid"},
                                            {("Top", "m")})
        self.assertEqual(flat[("Bottom", "m")], "A")

    def test_an_untyped_declaration_midway_hides_the_top_of_the_chain(self):
        flat = schema._inherit_member_types({("Top", "m"): "A"}, {"Mid": "Top", "Bottom": "Mid"},
                                            {("Top", "m"), ("Mid", "m")})
        self.assertNotIn(("Mid", "m"), flat)
        self.assertNotIn(("Bottom", "m"), flat)

    def test_a_cycle_terminates(self):
        flat = schema._inherit_member_types({("A", "m"): "T"}, {"A": "B", "B": "A"},
                                            {("A", "m")})
        self.assertEqual(flat[("B", "m")], "T")


class Decompress4or5(unittest.TestCase):
    def test_literal_run_then_overlapping_back_copy(self):
        stream = struct.pack("<I", 5) + bytes([1]) + b"AB" + bytes([0x80, 1])
        self.assertEqual(image.decompress_4or5(stream), b"ABABA")

    def test_stops_at_the_declared_length(self):
        stream = struct.pack("<I", 2) + bytes([1]) + b"AB" + bytes([1]) + b"CD"
        self.assertEqual(image.decompress_4or5(stream), b"AB")


class ObjectFields(unittest.TestCase):
    schema = {1: [[0, "first"], [1, "second", "Path_X::Y"]], 2: []}

    def fields(self, payload, length=None, t=1):
        blob = bytes(16) + payload
        length = 16 + len(payload) if length is None else length
        return tlv.object_fields(self.schema, t, blob, 0, length, 16)

    def test_reads_each_word_as_s16(self):
        self.assertEqual(self.fields(struct.pack("<hh", 5, -1)), {"first": 5, "second": -1})

    def test_a_declared_type_does_not_disturb_the_layout(self):
        self.assertIn("second", self.fields(struct.pack("<hh", 0, 0)))

    def test_a_short_payload_drops_the_words_it_lacks(self):
        self.assertEqual(self.fields(struct.pack("<hh", 5, 9), length=18), {"first": 5})

    def test_a_field_less_type_yields_an_empty_dict(self):
        self.assertEqual(self.fields(b"", t=2), {})

    def test_an_unschemad_type_yields_none(self):
        self.assertIsNone(self.fields(struct.pack("<hh", 0, 0), t=3))


class StringTableParse(unittest.TestCase):
    """the overlay string-table reader, over a synthetic overlay"""

    BASE = 0x80000000
    # varied lengths, so the run of gaps between them is a real signature
    WORDS = ["alpha", "bee", "gamma sun", "delta", "ep", "zeta rain", "eta",
             "theta", "iota moon", "kappa", "lambda", "mu", "nu sky", "xi"]

    def overlay(self, strings, extra=()):
        """`strings` 4-byte aligned as the linker lays them, then a pointer to each
        plus any `extra` slots, closed by the unrelated word that follows a table"""
        blob, offsets = bytearray(), []
        for s in strings:
            offsets.append(len(blob))
            blob += s.encode("latin1") + b"\x00"
            blob += b"\x00" * (-len(blob) % 4)
        for off in list(offsets) + list(extra):
            blob += struct.pack("<I", self.BASE + off)
        return bytes(blob) + struct.pack("<I", 0)

    def test_reads_the_strings_the_pointers_name(self):
        got = messages.string_table(self.overlay(self.WORDS), "alpha", 0, len(self.WORDS))
        self.assertEqual(got, self.WORDS)

    def test_the_anchor_need_not_be_the_first_entry(self):
        words = [""] + self.WORDS
        got = messages.string_table(self.overlay(words), "alpha", 1, len(words))
        self.assertEqual(got[:2], ["", "alpha"])

    def test_a_missing_anchor_finds_nothing(self):
        self.assertIsNone(messages.string_table(self.overlay(self.WORDS), "omega", 0, 14))

    def test_slots_sharing_one_pointer_all_read_as_that_string(self):
        """the empty entries of a real table all point at one shared string"""
        words = [""] + self.WORDS
        blob = self.overlay(words, extra=[0] * 3)
        got = messages.string_table(blob, "alpha", 1, len(words) + 3)
        self.assertEqual(got[-4:], ["xi", "", "", ""])

    def test_a_table_that_runs_on_past_its_length_is_refused(self):
        """the slot after the last must point nowhere, or the length is a guess"""
        self.assertIsNone(messages.string_table(self.overlay(self.WORDS), "alpha", 0, 10))

    def test_a_pointer_out_of_the_overlay_is_refused(self):
        blob = self.overlay(self.WORDS, extra=[1 << 20])
        self.assertIsNone(messages.string_table(blob, "alpha", 0, len(self.WORDS) + 1))


class MessageJson(unittest.TestCase):
    def test_a_button_code_is_written_as_an_escape_not_as_whitespace(self):
        text = messages.message_json({"lcd": ["hold \x0a then \x09"]})
        self.assertIn("hold \\u000a then \\u0009", text)
        self.assertEqual(json.loads(text)["lcd"], ["hold \x0a then \x09"])


DECOMP = REPO
needs_decomp = unittest.skipUnless(os.environ.get(DECOMP_ENV) or DECOMP.exists(),
                                   f"no alive_reversing checkout at {DECOMP}: clone it there or set ${DECOMP_ENV}")


def stale(cache):
    """a cache differing from a fresh parse is usually the checkout having moved, not the cache"""
    head = subprocess.run(["git", "-C", str(DECOMP), "rev-parse", "--short", "HEAD"],
                          stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip()
    if head and DECOMP_COMMIT.startswith(head):
        return (f"{cache} does not reproduce from the pinned checkout ({head}): regenerate it there, "
                f"or move DECOMP_COMMIT to the revision it was parsed from")
    return (f"{cache} does not reproduce from the checkout at {head or 'an unknown revision'}; the caches are pinned to "
            f"{DECOMP_COMMIT[:9]}: check that out, or re-pin (move DECOMP_COMMIT, delete the cache, "
            f"regenerate, re-emit the sidecars)")


class PathDiscovery(unittest.TestCase):
    """the grid a path carries when the decomp tabulates none for it"""

    FMT = {k: v for k, v in games.GAMES["AO"]["tlv"].items() if k != "extra_fn"}
    CELL_W, CELL_H = 1024, 480

    def chunk(self, slots, objects, tail=b""):
        """a path chunk: camera-name slots, then 24-byte objects at cell origins"""
        blob = b"".join(f"AOP01C{i:02d}".encode() if named else b"\0" * 8
                        for i, named in enumerate(slots))
        for cx, cy in objects:
            blob += (struct.pack("<BBhI", 0, 0, 24, 6) + b"\0" * 8
                     + struct.pack("<hhhh", cx * self.CELL_W, cy * self.CELL_H, 0, 0))
        return blob + tail

    def discover(self, blob):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            meta = tlv.discover_path_meta(blob, self.FMT, self.CELL_W, self.CELL_H)
        return meta, out.getvalue()

    def test_the_slot_run_ends_at_the_first_thing_that_is_not_a_name(self):
        # 8 cells, an object in the far corner of a 4x2 -> only 4x2 holds it
        meta, note = self.discover(self.chunk([1, 0, 1, 0, 0, 1, 0, 1], [(3, 1)]))
        self.assertEqual((meta["w_units"], meta["h_units"]), (4 * 1024, 2 * 480))
        self.assertEqual(meta["obj_off"], 64)  # the objects begin where the slots end
        self.assertEqual(meta["coll_count"], 0)
        self.assertIn("index table would take 32", note)  # no tail at all: reported

    def test_the_region_end_is_where_the_records_stop(self):
        blob = self.chunk([1] * 4, [(0, 0), (3, 0)], tail=b"\xff" * 16)
        end, origins = tlv.contiguous_objects(blob, 32, self.FMT)
        self.assertEqual(end, 32 + 48)  # the -1 tail is an index table, not a record
        self.assertEqual(origins, [(0, 0), (3 * 1024, 0)])
        meta, note = self.discover(blob)
        self.assertEqual(meta["idx_off"], 80)
        self.assertEqual(note, "")  # a tail of exactly 4 bytes a cell: silent

    def test_an_undetermined_grid_raises_rather_than_picking(self):
        # 4 cells and one object at the origin fits 1x4, 2x2 and 4x1 alike
        with self.assertRaises(RuntimeError):
            self.discover(self.chunk([1] * 4, [(0, 0)]))

    def test_one_level_is_tabulated_nothing_at_all(self):
        """level scope is as far as this reaches without a disc: spotting a
        partially tabulated level needs the chunks to say which path is missing"""
        empty = {gk: {short for short, paths in games.game_setup(gk)["tables"].items() if not paths}
                 for gk in ("AO", "AE")}
        self.assertEqual(empty, {"AO": {"S1"}, "AE": set()},
                         "a table for S1 would retire the discovery")


class CacheStamp(unittest.TestCase):
    """the artwork cache name answers to the artwork and to nothing else"""

    def worker(self, tmp, files):
        cams = Path(tmp) / "cams"
        for rel, data in files.items():
            (cams / rel).parent.mkdir(parents=True, exist_ok=True)
            (cams / rel).write_bytes(data)
        sw = Path(tmp) / "sw.js"
        sw.write_text('// lead\nconst CACHE_NAME = "cams-v1";\nconst ENABLED = "cams-on";\n')
        return sw, cams

    def test_bytes_and_path_both_reach_the_stamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            sw, cams = self.worker(tmp, {"ao/L/A.png": b"a", "ae/L/B.png": b"b"})
            base = emit.stamp_cache_name(sw, cams)
            self.assertEqual(base, emit.stamp_cache_name(sw, cams))
            (cams / "ao/L/A.png").write_bytes(b"c")
            self.assertNotEqual(base, emit.stamp_cache_name(sw, cams))
            (cams / "ao/L/A.png").write_bytes(b"a")
            self.assertEqual(base, emit.stamp_cache_name(sw, cams))  # content, not a counter
            (cams / "ao/L/A.png").rename(cams / "ao/L/Z.png")
            self.assertNotEqual(base, emit.stamp_cache_name(sw, cams))

    def test_it_rewrites_the_one_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            sw, cams = self.worker(tmp, {"ao/L/A.png": b"a"})
            name = emit.stamp_cache_name(sw, cams)
            self.assertIn(f'const CACHE_NAME = "{name}";', sw.read_text())
            self.assertIn('const ENABLED = "cams-on";', sw.read_text())

    def test_a_worker_it_cannot_stamp_fails_the_build(self):
        # both the early precondition and the write itself, which must not report
        # a stamp it did not manage to write
        with tempfile.TemporaryDirectory() as tmp:
            sw, cams = self.worker(tmp, {"ao/L/A.png": b"a"})
            sw.write_text("const CACHE_NAME = 'cams-v1';\n")  # not the shape it writes
            with self.assertRaises(SystemExit):
                emit.require_stampable(sw)
            with self.assertRaises(SystemExit):
                emit.stamp_cache_name(sw, cams)

    def test_the_committed_worker_names_the_committed_artwork(self):
        self.assertIn(f'const CACHE_NAME = "{emit.cams_stamp(SITE / "cams")}";',
                      (SITE / "sw.js").read_text(),
                      "sw.js and public/cams disagree — commit the stamped line with the artwork")


class MemberTypes(unittest.TestCase):
    @needs_decomp
    def test_a_base_structs_member_carries_its_declared_type(self):
        types = schema.parse_member_types("AE")
        self.assertEqual(types[("Path_WellLocal", "field_0_scale")], "Scale_short")

    @needs_decomp
    def test_a_union_typed_member_carries_no_type(self):
        types = schema.parse_member_types("AO")
        self.assertEqual(types[("Path_WellLocal", "field_18_scale")], "Scale_short")
        self.assertNotIn(("Path_WellLocal", "field_24_off_level_or_dx"), types)


class Sidecars(unittest.TestCase):
    """the committed sidecars must be reproducible from the sources they claim"""

    def emit(self, writer, game_key):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            written = writer(game_key, Path(tmp))
            return written.read_bytes()

    def assertReproduces(self, writer, game_key, filename):
        self.assertEqual(
            self.emit(writer, game_key),
            (SITE / filename).read_bytes(),
            f"{filename} differs from a fresh emit — rebuild it or fix the emitter",
        )

    def test_field_types_ao(self):
        self.assertReproduces(emit.write_field_types, "AO", "field_types_ao.json")

    def test_field_types_ae(self):
        self.assertReproduces(emit.write_field_types, "AE", "field_types_ae.json")

    def test_enum_labels_ao(self):
        self.assertReproduces(emit.write_enum_labels, "AO", "enum_labels_ao.json")

    def test_enum_labels_ae(self):
        self.assertReproduces(emit.write_enum_labels, "AE", "enum_labels_ae.json")

    def test_a_stale_field_type_override_fails_the_emit(self):
        stale = {("AO", "Door", "no_such_field"): "Choice_short"}
        with mock.patch.dict(emit._FIELD_TYPE_OVERRIDES, stale), self.assertRaises(RuntimeError):
            self.emit(emit.write_field_types, "AO")


class SchemaCaches(unittest.TestCase):
    def cached_layout(self, game_key):
        """a (tid, layout) pair the parser derives on its own, so an override of
        it has nothing left to add. Read from the cache rather than from
        game_setup, whose schema already carries the overrides."""
        cache = HERE / "data" / games.GAMES[game_key]["schema_cache"]
        names = games.game_setup(game_key)["tlv_names"]
        return next((int(k), v) for k, v in json.loads(cache.read_text()).items()
                    if int(k) in names)

    def assertOverrideFails(self, game_key, tid, layout):
        entry = {(game_key, tid): layout}
        with mock.patch.dict(schema._SCHEMA_LAYOUT_OVERRIDES, entry), self.assertRaises(RuntimeError):
            games.game_setup(game_key)

    def test_a_layout_override_for_an_unknown_type_fails_the_build(self):
        self.assertOverrideFails("AO", 9999, [])

    def test_a_layout_override_the_parser_derives_fails_the_build(self):
        tid, layout = self.cached_layout("AO")
        self.assertOverrideFails("AO", tid, layout)

    def test_an_empty_override_cannot_blank_a_derived_layout(self):
        tid, _ = self.cached_layout("AO")
        self.assertOverrideFails("AO", tid, [])

    def test_cached_layouts_are_word_and_name_pairs(self):
        for game_key in ("AO", "AE"):
            cache = HERE / "data" / games.GAMES[game_key]["schema_cache"]
            for tid, rows in json.loads(cache.read_text()).items():
                for row in rows:
                    self.assertIn(len(row), (2, 3), f"{cache.name} type {tid}: {row}")
                    self.assertIsInstance(row[0], int)
                    self.assertRegex(row[1], r"^[a-z0-9_]+$")

    @needs_decomp
    def test_the_committed_cache_matches_a_fresh_parse(self):
        for game_key in ("AO", "AE"):
            cache = HERE / "data" / games.GAMES[game_key]["schema_cache"]
            self.assertEqual(
                cache.read_text(),
                json.dumps(schema.parse_object_schema(game_key), indent=1),
                stale(cache.name),
            )


class PathdataCache(unittest.TestCase):
    @needs_decomp
    def test_the_committed_cache_matches_a_fresh_parse(self):
        for game_key in ("AO", "AE"):
            game = games.GAMES[game_key]
            self.assertEqual(
                (HERE / "data" / game["cache"]).read_text(),
                json.dumps(game["parse_tables"](), indent=1),
                stale(game["cache"]),
            )


class EnumCache(unittest.TestCase):
    def cache_file(self, game_key):
        return HERE / "data" / games.GAMES[game_key]["enum_cache"]

    def test_cached_labels_are_numeric_value_to_label_maps(self):
        for game_key in ("AO", "AE"):
            raw = json.loads(self.cache_file(game_key).read_text())
            self.assertEqual(set(raw), {"labels", "bad"})
            for ty, vals in raw["labels"].items():
                self.assertTrue(vals, ty)
                for v, label in vals.items():
                    self.assertRegex(v, r"^-?\d+$", f"{ty}: {v}")
                    self.assertTrue(label and isinstance(label, str), f"{ty} {v}: {label!r}")
            for ty in raw["bad"]:
                self.assertIsInstance(ty, str)

    @needs_decomp
    def test_the_committed_cache_matches_a_fresh_sweep(self):
        for game_key in ("AO", "AE"):
            labels, bad = schema.parse_enum_labels(game_key)
            self.assertEqual(
                self.cache_file(game_key).read_text(),
                json.dumps({"labels": labels, "bad": sorted(bad)}, indent=1),
                stale(self.cache_file(game_key).name),
            )


class PinnedRevision(unittest.TestCase):
    def test_the_readme_names_both_pins(self):
        readme = (HERE.parent / "README.md").read_text()
        self.assertIn(DECOMP_COMMIT[:9], readme)
        self.assertIn(AO_COMMIT[:9], readme)


if __name__ == "__main__":
    unittest.main()
