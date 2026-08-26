"""The games' own LCD and hint-fly message tables, lifted from the level
overlays."""
import json
import struct

# The scroll-in run of spaces every LCD message opens with; the engine's own
# source calls it out as something that should have been added at runtime.
MESSAGE_LEAD = " " * 31

# Button commands a message can name, as the font's own code points. Only the
# viewer names them; the build fails on a code outside this range so a name can
# never be missing at the point one is needed.
MESSAGE_BUTTONS = range(0x08, 0x14)

# The string tables to lift, per game: (anchor, the anchor's index, entries).
# Each is a pointer array plus a 4-byte-aligned string blob compiled into the
# level overlays rather than into the executable, so the sweep reads *.OVL.
MESSAGE_TABLES = {
    "AO": {
        "lcd": (MESSAGE_LEAD + "The profits justify the means.", 1, 90),
        "hintfly": ("SNEAK TO BOMB", 0, 36),
    },
    "AE": {
        "lcd": (MESSAGE_LEAD + "SoulStorm Mining Company is an equal opportunity employer.", 1, 101),
    },
}

def string_table(blob, anchor, lead, count):
    """the `count` C strings of a pointer table whose entry `lead` is `anchor`.

    Anchoring on a string rather than an address derives the overlay's load base
    from the data itself. The table is found by the run of gaps between the first
    strings, which is a signature no other array shares, and is believed only if
    the slot past its declared end points nowhere: that is what makes the length
    self-proving rather than asserted."""
    at = blob.find(anchor.encode("latin1"))
    if at < 0:
        return None
    starts, pos = [], at
    for _ in range(8):
        end = blob.find(b"\x00", pos)
        if end < 0:
            return None             # the anchor sits too near the end to read a run
        starts.append(pos)
        pos = end + 1
        while pos < len(blob) and blob[pos] == 0:   # alignment padding between strings
            pos += 1
        if pos >= len(blob):
            return None
    gaps = [starts[i + 1] - starts[i] for i in range(len(starts) - 1)]
    words = struct.unpack_from(f"<{len(blob) // 4}I", blob, 0)
    table = None
    for q in range(lead, len(words) - max(count - lead, len(gaps))):
        if all(words[q + i + 1] - words[q + i] == gaps[i] for i in range(len(gaps))):
            table = q - lead
            break
    if table is None:
        return None
    base = words[table + lead] - starts[0]
    out = []
    for i in range(count):
        off = words[table + i] - base
        end = blob.find(b"\x00", off) if 0 <= off < len(blob) else -1
        if end < 0:
            return None
        out.append(blob[off:end].decode("latin1"))
    if 0 <= words[table + count] - base < len(blob):
        return None
    return out

def extract_messages(game_key, discs):
    """the game's message tables, read from every overlay carrying them.

    Each table is compiled into every overlay whose level needs it, so the copies
    are a free cross-check: they must all agree, and one disagreeing means the
    tables are per-level and nothing here holds. An overlay holding the anchor
    but no readable table is that same disagreement wearing a different length,
    so it raises."""
    specs = sorted(MESSAGE_TABLES[game_key].items())
    seen = {name: {} for name, _ in specs}
    unreadable = {name: [] for name, _ in specs}
    copies = {name: 0 for name, _ in specs}
    for disc in discs:
        for ovl in sorted(f for f in disc.files if f.endswith(".OVL")):
            blob = disc.read(*disc.files[ovl])       # read once, offered to every table
            for name, (anchor, lead, count) in specs:
                if anchor.encode("latin1") not in blob:
                    continue
                found = string_table(blob, anchor, lead, count)
                if found is None:
                    unreadable[name].append(ovl)
                else:
                    seen[name].setdefault(tuple(found), []).append(ovl)
                    copies[name] += 1
    out = {}
    for name, (_, _, count) in specs:
        if unreadable[name]:
            raise RuntimeError(f"{game_key}: {name} message table unreadable in "
                               f"{','.join(unreadable[name])}, which carries its text")
        if not seen[name]:
            raise RuntimeError(f"{game_key}: no overlay carries the {name} message table")
        if len(seen[name]) > 1:
            raise RuntimeError(f"{game_key}: overlays disagree on the {name} message table: "
                               + "; ".join(",".join(v) for v in seen[name].values()))
        # the scroll-in lead is spaces; stripping whitespace would also eat a
        # trailing button code, 0x09-0x0d being both
        table = [s.strip(" ") for s in next(iter(seen[name]))]
        for msg in table:
            unknown = {c for c in msg if ord(c) < 0x20 and ord(c) not in MESSAGE_BUTTONS}
            if unknown:
                raise RuntimeError(f"{game_key} {name}: unnamed button code(s) "
                                   f"{sorted(hex(ord(c)) for c in unknown)} in {msg!r}")
        out[name] = table
        print(f"  {name}: {sum(1 for s in table if s)} of {count} messages, "
              f"{copies[name]} identical copies")
    return out

def message_json(tables):
    """the tables as JSON, every button code written \\u00XX.

    json's shorthand for 0x08-0x0d would put \\n and \\t in the middle of a
    sentence, where they read as whitespace rather than as the button they are.
    No message contains a backslash, which is what makes rewriting them exact."""
    text = json.dumps(tables, indent=1)
    for shorthand, code in (("b", 0x08), ("t", 0x09), ("n", 0x0A),
                            ("f", 0x0C), ("r", 0x0D)):
        text = text.replace("\\" + shorthand, "\\u%04x" % code)
    return text

def write_messages(game_key, discs, dst):
    """the viewer's message sidecar for one game: {table: [message by id]}.

    Needs the discs: the decomp carries both LCD tables in source, but those are
    the PC build's and differ from PS1's in wording, not only in button names."""
    tables = extract_messages(game_key, discs)
    if any("\\" in msg for t in tables.values() for msg in t):
        raise RuntimeError(f"{game_key}: a message contains a backslash")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(message_json(tables))
    print(f"messages -> {dst}")
    return dst
