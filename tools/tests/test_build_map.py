"""Unit tests for the builder's pure functions: python3 -m unittest discover -s tools/tests

Stdlib only, and nothing here needs a disc image. The parsers that read the
alive_reversing checkout are covered by the reproducibility tests at the bottom,
which skip when the checkout is absent (as it is in CI).
"""

import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import build_map as bm  # noqa: E402


def chunk(tag, rid, payload, size=None):
    """one .BND chunk: 16-byte header (size covers it) + payload"""
    typ = int.from_bytes(tag.encode("latin1"), "little")
    size = len(payload) + 16 if size is None else size
    return struct.pack("<IHHII", size, 0, 0, typ, rid) + payload


class ParseChunks(unittest.TestCase):
    def test_keys_by_tag_and_id(self):
        data = chunk("Path", 1, b"abcd") + chunk("Path", 2, b"efgh") + chunk("End!", 0, b"")
        self.assertEqual(bm.parse_chunks(data), {("Path", 1): b"abcd", ("Path", 2): b"efgh"})

    def test_first_of_a_repeated_key_wins(self):
        data = chunk("Path", 1, b"first") + chunk("Path", 1, b"second")
        self.assertEqual(bm.parse_chunks(data), {("Path", 1): b"first"})

    def test_stops_at_the_end_marker(self):
        data = chunk("Path", 1, b"abcd") + chunk("End!", 0, b"") + chunk("Path", 2, b"never")
        self.assertNotIn(("Path", 2), bm.parse_chunks(data))

    def test_a_garbage_header_terminates(self):
        # a size that doesn't advance, or one that runs past the buffer, must end
        # the walk: both spun forever or read out of bounds before the guards
        self.assertEqual(bm.parse_chunks(chunk("Path", 1, b"abcd", size=8)), {})
        self.assertEqual(bm.parse_chunks(chunk("Path", 1, b"abcd", size=4096)), {})


class IntRows(unittest.TestCase):
    def test_keeps_integers_in_order_and_drops_the_rest(self):
        body = """
            { 0, 1, -2, kNullThing, 0x10, 3 },
            { 4, "name", 5 },
        """
        self.assertEqual(bm.int_rows(body), [[0, 1, -2, 3], [4, 5]])


class MatchBrace(unittest.TestCase):
    def test_returns_past_the_matching_close(self):
        text = "enum E { a, b } trailing"
        self.assertEqual(text[: bm._match_brace(text, text.index("{"))], "enum E { a, b }")

    def test_skips_nested_braces(self):
        text = "struct S { enum E { a } m; } after"
        self.assertEqual(text[bm._match_brace(text, text.index("{")) :], " after")

    def test_unbalanced_ends_at_the_text(self):
        text = "struct S { enum E { a }"
        self.assertEqual(bm._match_brace(text, text.index("{")), len(text))


class StripComments(unittest.TestCase):
    def test_removes_line_and_block_comments(self):
        self.assertEqual(bm._strip_comments("a /* b */ c // d\ne"), "a  c \ne")

    def test_a_commented_enum_does_not_swallow_the_next_definition(self):
        src = "// enum Ignored {\nenum Real { a, b };"
        self.assertEqual(bm._strip_comments(src), "\nenum Real { a, b };")

    def test_a_comma_in_a_comment_mints_no_enumerator(self):
        src = "enum E { a, /* one, two */ b };"
        self.assertEqual(bm._strip_comments(src).count(","), 1)


class DeriveLabel(unittest.TestCase):
    def test_drops_the_value_suffix_and_e_prefix_and_splits_camel_case(self):
        self.assertEqual(bm._derive_label("eChaseAndDisappear_4"), "Chase And Disappear")

    def test_keeps_an_e_that_is_part_of_the_word(self):
        self.assertEqual(bm._derive_label("end_3"), "End")

    def test_leaves_an_all_caps_run_alone(self):
        self.assertEqual(bm._derive_label("eTLVSpawn_1"), "TLVSpawn")


class Decompress4or5(unittest.TestCase):
    def test_literal_run_then_overlapping_back_copy(self):
        stream = struct.pack("<I", 5) + bytes([1]) + b"AB" + bytes([0x80, 1])
        self.assertEqual(bm.decompress_4or5(stream), b"ABABA")

    def test_stops_at_the_declared_length(self):
        stream = struct.pack("<I", 2) + bytes([1]) + b"AB" + bytes([1]) + b"CD"
        self.assertEqual(bm.decompress_4or5(stream), b"AB")


class ObjectFields(unittest.TestCase):
    schema = {1: [[0, "first"], [1, "second", "Path_X::Y"]], 2: []}

    def fields(self, payload, length=None, t=1):
        blob = bytes(16) + payload
        length = 16 + len(payload) if length is None else length
        return bm.object_fields(self.schema, t, blob, 0, length, 16)

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


DECOMP = bm.REPO
needs_decomp = unittest.skipUnless(DECOMP.exists(), f"no alive_reversing checkout at {DECOMP}")


class Sidecars(unittest.TestCase):
    """the committed sidecars must be reproducible from the sources they claim"""

    def emit(self, writer, game_key):
        with tempfile.TemporaryDirectory() as tmp, contextlib.redirect_stdout(io.StringIO()):
            written = writer(game_key, Path(tmp))
            return written.read_bytes()

    def assertReproduces(self, writer, game_key, filename):
        self.assertEqual(
            self.emit(writer, game_key),
            (bm.SITE / filename).read_bytes(),
            f"{filename} differs from a fresh emit — rebuild it or fix the emitter",
        )

    def test_field_types_ao(self):
        self.assertReproduces(bm.write_field_types, "AO", "field_types_ao.json")

    def test_field_types_ae(self):
        self.assertReproduces(bm.write_field_types, "AE", "field_types_ae.json")

    @needs_decomp
    def test_enum_labels_ao(self):
        self.assertReproduces(bm.write_enum_labels, "AO", "enum_labels_ao.json")

    @needs_decomp
    def test_enum_labels_ae(self):
        self.assertReproduces(bm.write_enum_labels, "AE", "enum_labels_ae.json")

    def test_a_stale_field_type_override_fails_the_emit(self):
        stale = {("AO", "Door", "no_such_field"): "Choice_short"}
        with mock.patch.dict(bm._FIELD_TYPE_OVERRIDES, stale), self.assertRaises(RuntimeError):
            self.emit(bm.write_field_types, "AO")


class SchemaCaches(unittest.TestCase):
    def test_every_layout_override_targets_a_known_type(self):
        for (game_key, tid), _ in bm._SCHEMA_LAYOUT_OVERRIDES.items():
            names = bm.game_setup(game_key)["tlv_names"]
            self.assertIn(tid, names, f"{game_key} layout override for unknown type {tid}")

    def test_cached_layouts_are_word_and_name_pairs(self):
        for game_key in ("AO", "AE"):
            cache = bm.HERE / "data" / bm.GAMES[game_key]["schema_cache"]
            for tid, rows in json.loads(cache.read_text()).items():
                for row in rows:
                    self.assertIn(len(row), (2, 3), f"{cache.name} type {tid}: {row}")
                    self.assertIsInstance(row[0], int)
                    self.assertRegex(row[1], r"^[a-z0-9_]+$")


if __name__ == "__main__":
    unittest.main()
