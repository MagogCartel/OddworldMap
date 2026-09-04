# 42. Level editor — could this site host one?

**Status:** open — Phase 1 shipped 2026-09-04 (exporter, reference-reader oracle, structural diff), its cross-check diff pending a disc session; Phases 2–3 parked · **Effort:** Phases 2–3 large · **Where:** builder-only, no disc — the disc session owes the diff run plus the rebuild that retires the export fallbacks; Phase 2's FG1 layer split would need one too

**Outcome: what the site should produce is a *description* of a path, not a level — and the write path belongs in `tools/`, not on the page.** AliveTeam's level editor already exists, is released for Windows and Linux, and pins the exact decomp tree the builder's parsers already read; it reads the user's own LVL files and can patch them from a JSON. So the site's job is not to be an editor but to emit that JSON — and the first thing that JSON buys is not modding at all, it is a **cross-check of our extraction against AliveTeam's**, object for object, over 16,225 objects and 9,540 collision lines (measured 2026-08-26).

**Scheduling is carried by the phase split, not by a section of the backlog.** **Phase 1 is ready now:** no disc image, no site change, and — for the exporter itself — nothing beyond the committed data and the decomp headers the builder already parses. Only its verification step adds a local prerequisite, a `relive_api` build, which that project's own CI does on macOS. **Phases 2 and 3 are the moonshot it earns** — a download button, then editing in the browser — and neither should start before Phase 1's diff comes back clean.

---

## What was checked (2026-07-31)

### The editor exists, is released, and is not Windows-only

[AliveTeam/qt-editor](https://github.com/AliveTeam/qt-editor) is its **own repository**, not a branch of the decomp: created 2021-04, default branch `master`, last commits 2026-02-28. The latest release (`github_0.7.1`, 2026-02-28) ships `Windows32-Release-qt-editor.zip`, `Windows64-Release-qt-editor.zip` and `relive-qt-editor-0.1.1-Linux.deb`. Its CI builds Windows 32/64 (artifacts), Linux on `ubuntu-22.04` (a `.deb` artifact) and macOS Intel via `brew --prefix qt@5` (builds, artifacts still a TODO). So "Windows-only" is wrong: Windows and Linux get binaries, macOS builds from source, and an Apple Silicon build is untested rather than excluded.

**It pins `3rdParty/alive_reversing` at `e2badb8df`, a `master` commit** — confirmed by `git branch -a --contains` naming `master` alone, and the head of `master` in the local checkout, which has not been fetched past 2026-02-26. That is the same tree `parse_object_schema` / `parse_member_types` / `parse_enum_labels` read. The `beta` question that [29](item-029-decomp-label-sweep.md) records does not reach the editor at all.

There is a **command line**: `qt-editor --export <json> <lvl>` (`Source/main.cpp`, `exportJsonToLvlCommandLine`). `Source/Exporter.cpp` shows it imports the JSON into that LVL **in place** — writes a `.lvl.tmp`, deletes the original, renames over it — and adds the LVL's own directory to the resource search set. So the only artifact we would ever ship is one JSON; the user's game files never leave their machine. relive itself requires the PC game files, so anyone using the export already owns a copy.

**Prior art is public and long-standing**, which matters for the claim question below: Paul's Level Editor circulated for years (still linked as `aliveteam.github.io/legacy/Editor_0.6.2.rar`), the RELIVE site advertises the new editor as "the replacement for the legacy Paul's Level Editor", and a Steam guide walks people through installing both and invites them to share levels. The editor's own README is blunt that its output targets relive: "maps/paths exported to LVLs with this editor will not work with the original engine."

### The format, and how versioned it is

The format is **relive_api v4 JSON** — `kApiVersion = 4` at the pinned `e2badb8df` (`Source/Tools/relive_api/relive_api.cpp:259`), which is the version the released editor reads. Upstream master has moved past the pin, so this figure and [29](item-029-decomp-label-sweep.md)'s version numbers describe different trees; 29 records which is which. Root keys are `api_version`, `game` (`"AO"` / `"AE"`), `map` and `schema`.

Versioning is strict but survivable. Import compares the version and, on mismatch, throws through `context.JsonNeedsUpgrading` (`relive_api.cpp:1043-1046`) — there is no silent auto-upgrade. `UpgradePathJson` is the explicit path, and upgrade steps are registered per *source* version (`ADD_UPGRADE_STEP_FROM(3, UpgraderAO3)`, `JsonUpgraderAO.cpp:54-57`) with rename/remap operations (`RenameMapObjectProperty`, `RemapNumberToEnum`, …), reinjecting a fresh `schema` at the end. So a bump does not orphan our exporter: it means adding one step's worth of renames, and the editor already "handles json upgrading on opening existing json files" (its PR #168). This is the same versioning that mattered once here already — [29](item-029-decomp-label-sweep.md)'s `chase_abe_when_spotted` fix bumps `kApiVersion` upstream, and its confirmed `scale`/`level` batch is queued to bump it again.

### The import contract

Every key below was read out of the reader, not assumed.

- **`map` requires** `path_bnd`, `path_id`, `x_size`, `y_size`, `abe_start_xpos`, `abe_start_ypos`, `num_muds_in_path`, `total_muds`, `num_muds_for_bad_ending`, `num_muds_for_good_ending`, `lcdscreen_messages`, `hintfly_messages`, `cameras` (`JsonReaderBase.cpp:52-83`). Missing keys throw. `x_grid_size` / `y_grid_size` are written on export and never read back.
- **`schema` is not read on import** — but the **editor** reads it (`Model.cpp:93` takes `enum_and_basic_type_properties`), so a JSON meant to be *opened* must carry it. It is identical for every path in a game, so it is one generated blob per game, not per path.
- **Collisions:** import reads `collisions.items` only; `structure` is export metadata (`JsonReaderAO.cpp:11-13`, `JsonWriterBase.cpp:132-134`). AO items need `x1`, `y1`, `x2`, `y2`, `Type`, `Next`, `Previous`; AE adds `Next 2`, `Previous 2`, `Length` (`JsonReaderBase.hpp:20-29` and `45-59`). `Type` is an enum, so it takes a label string.
- **Cameras require** `x`, `y`, `id`, `name`, `map_objects`; `image` and the four FG1 layers are optional (`ReadOptionalString`, `JsonReaderBase.cpp:96-107`). **Every camera must be listed** or its grid cell is written as an 8-byte blank (`relive_api.cpp:702-728`).
- **An object** is `{name, object_structures_type, properties}`. The type string goes through `MakeTlvFromString`; an unknown one throws `UnknownStructureTypeException` (`JsonReaderBase.cpp:111-131`). `name` is required but cosmetic — the instance suffix (`Hoist_1`) is not read back into anything. `xpos`/`ypos`/`width`/`height` are ordinary properties, with **width/height relative** to the top-left, which import adds back (`TlvObjectBaseAO.cpp:31-35`, `49-57`). The binary `length` comes from `sizeof`, and the end-of-list flag is set on the last object of each camera (`TlvsAO.hpp:81-85`, `TlvObjectBaseAO.cpp:71-76`) — neither is ours to supply.
- **Every registered property is required per object**, `ADD_HIDDEN` included. A missing numeric throws; a missing enum throws through `context.MissingEnumType` (`PropertyCollection.hpp:48-54`). **An unknown enum *label* does not throw** — it silently takes the first enumerator and records the substitution in `context.UnknownEnumValue` / `Context::RemappedEnumValues()` (`EnumTypeBase.hpp:63-74`). That is the one way this format can accept our data and quietly mean something else, so `Context` is the oracle every export run must be checked against; the editor's CLI already prints both the remapped enums and the missing properties.

### Why the format is nearly free for us

**Our field keys already *are* the JSON's property names.** `parse_object_schema`'s `ADD` regex matches `ADD("Door Number", mTlv.field_20_door_number)` and `norm()`s the **display string** into the key we ship — and that display string is exactly the JSON key the `ADD` macro registers (`TlvObjectBaseMacros.hpp:4`). The mapping is not a table to be written; it is a column the parser has in hand and throws away. Checked over the shipped schemas: **zero collisions** after `norm()` in either game, so the correspondence is one-to-one and reversible.

**Our enum labels are the same `AddEnum` strings, lowercased.** `enum_labels_{ao,ae}.json` is generated from those blocks already. The JSON wants the originals, and un-lowercasing is *not* a mechanical inverse — the labels are not uniformly Title-Case-with-spaces (`{eOpen_0, "Open"}`, `"Hub Door Closed"`, `"Closing (Internal Only)"` at `TlvsAO.hpp:433-438`, but `SwitchOp` is `"SetTrue"` / `"SetFalse"` with no space, `TypesCollectionAO.cpp:179-185`). So the sidecar must carry the original strings verbatim rather than reconstruct them, which is the same discipline `write_enum_labels` already applies in the other direction.

**The field-less sets agree, which is evidence the two schemas are the same schema.** The 15 AO and 7 AE types that ship no `fields` are exactly types relive_api declares with `EMPTY_CTOR` — `LCDStatusBoard` (`TlvsAO.hpp:1623-1626`), `GasEmitter` (`365-368`), `ScrabLeftBound` (`1681-1684`), `InvisibleZone` (`698-701`), `ZSligCover` (`1673-1676`), `SoftLanding` (`1647-1650`), `KillUnsavedMuds` (`270-273`). Our archive is lossy in the same places theirs is, because both are driven by the same `ADD` lines.

**And PS1-versus-PC parity is better evidenced than the README's assertion.** The builder feeds **PC-derived** static tables — `obj_off`, `idx_off`, `coll_off`, `coll_count`, grid sizes, all parsed out of `PathData.cpp` by `parse_pathdata_cpp_{ao,ae}` — to **PS1** path chunks, and gets clean camera-name tables, exactly-sized collision arrays and sane object walks across all 190 paths. If the content differed the offsets would not land.

---

## Phase 1 — a `tools/` exporter whose first job is a cross-check

Our pipeline is an independent second implementation of AliveTeam's readers, and nothing has ever compared the two. Emitting their format makes the comparison mechanical: same path, same objects, same values, or a diff that names what disagrees. That is the strongest available answer to "is our data right" — the question [29](item-029-decomp-label-sweep.md) and [41](item-041-inherited-field-types.md) keep circling with eyeballing and heuristic scans.

### What it emits

A `tools/` entry point (a flag on the builder or a small sibling script) that takes `(game, level, path)` and writes a relive_api v4 JSON, reading **only** the committed `map_data_{ao,ae}.json` plus new generated sidecars. No disc, no LVL, no site change.

Three sidecars, all derived from the same decomp source the builder already parses, all emitted alongside `field_types_*` / `enum_labels_*` by the existing `--emit-field-data` path:

- **the property display names** — the string `norm()` currently discards, per `(type, field)`;
- **the enum labels verbatim**, un-lowercased, keyed as `enum_labels_*` already keys them;
- **the per-game `schema` blob**, one static object per game (types with their properties, the enum tables, the basic-type ranges), since the editor needs it and it never varies by path.

The rest is assembly: `map`'s required scalars, `collisions.items`, and `cameras` with `map_objects` bucketed by cell — which is a straight read of `c.cell` against each TLV's world rect, since [js/state.js](../public/js/state.js)'s transforms already establish the cell geometry.

### How to verify it

**Diff against the reference reader on a PS1-extracted LVL.** `relive_api` builds on macOS in `alive_reversing`'s own CI, and the builder's `Lvl` can already write out a `R1.LVL` byte-for-byte from the disc image. Point `ExportPathBinaryToJson` at that file and diff its `map_objects` and `collisions.items` against ours for the same path.

The reason this works without a PC copy of the games: a PS1 `.CAM` uses the **same chunk container** with the same `Bits` tag (`decode_cam`), only a different payload framing, and `CamConverter` never throws — it carries a bare `// todo: throw` (`CamConverter.cpp:202`). So the camera base64 comes out as garbage while the objects and collisions come out right, which is precisely the half the diff reads. **Time-box this step**: it is the one part of Phase 1 not established by reading code, and if it does not hold, the fallback is a GOG copy, which is a purchase rather than a redesign.

**Then read `Context`.** Run the export through the editor's CLI on a scratch copy of an LVL and check `RemappedEnumValues()` and `MissingJsonProperties()` are empty. A clean `Context` is what distinguishes "our JSON is accepted" from "our JSON is accepted and means what we meant" — the same distinction [28](item-028-readable-units.md) draws when it refuses to ship guessed seconds.

### The gaps to close, all disc-free

- **Collision link fields.** `Next` / `Previous` (and AE's `Next 2` / `Previous 2` / `Length`) live in the same 20-byte record the builder already reads and discards — it keeps the four coordinates and the type byte and stops, in the builder's collision walk. The offsets differ per game (AO `0x0C` previous / `0x10` next; AE `0x0A`, `0x0C`, `0x0E`, `0x10`, `0x12`). Capturing them makes the export lossless where the editor's own default is to write `-1` and recompute the length.
- **`ShadowZone`'s three RGB fields** are registered with `ADD_LINKED`, which the schema regex does not match (`ADD(?:_HIDDEN)?`) — three fields per game, one type, missing from our archive as well as from any export.
- **AE's Abe start** is `pd[10]` / `pd[11]` in the PathData row `positional_rows` reads and names in a comment without storing.
- **The mud counts are constants**, not data: relive_api hardcodes AO as `0 / 99 / 75 / 50` and AE as `Path_GetMudsInLevel(level) / 300 / 20 / 255` (`relive_api.cpp:106-113`, `131-137`). Copy them.
- **The two message arrays can be empty**, which is what a vanilla LVL yields — the strings only reach the file through the `Pxtd` chunk an editor round-trip writes. This is where [5](item-005-lcd-marquee-text.md) (LCD marquee text) would eventually plug in, but it blocks nothing.

### Why FG1 is not a Phase 1 concern

The FG1 trap described under Phase 2 is real, and it **only bites on import**. Phase 1 writes no LVL, touches no `.CAM` chunk, and reads no camera art: a diff against `ExportPathBinaryToJson` compares object and collision arrays and ignores the base64 entirely. **Nothing in Phase 1 needs a disc image or a data rebuild** — so a reader who meets the trap first should not conclude the exporter is gated behind one. It is gated behind the *download*, and only because a download invites someone to import it.

---

## Phase 2 — the download, and the FG1 trap that lives here

A button that hands the current path's JSON over as a file. Technically this is small and breaks nothing: the site stays a static page with no backend, and a generated JSON is a download like the PNG export already is.

**But the artefact has one silent failure, and it must be resolved before the button exists.** `ImportCameraAndFG1` removes every FG1 chunk **unconditionally** (`relive_api.cpp:1162`), and it is called for every camera with a non-empty name (`relive_api.cpp:518-538`) — while a camera left out of the JSON loses its grid cell instead. So there is no way to say "leave this screen alone": an art-free import **strips the foreground masks off the whole path**, and the visible result is Abe no longer hiding behind scenery on every screen of it. The public `ImportPathJsonToBinary` passes `skipCamerasAndFG1 = false` (`relive_api.cpp:875-878`); the `true` overload is `Detail::`, used by the integration tests, not reachable through the editor.

Two ways out, and the choice is the gate on Phase 2:

- **Say so.** Ship the download described as an object-and-collision description, and state that importing it drops the path's foreground masks. Honest, cheap, and consistent with how this project handles a known limitation — but it makes the artefact something you inspect rather than play.
- **Emit the layers.** The builder already decodes FG1, but it merges everything into one `_fg.png` for the viewer's overlay, and the import wants up to four separate layers (foreground, background, and the two well variants). Splitting them is a builder change and therefore **a disc rebuild** — which is the only place in this whole item where a disc is needed. AE's format is per-row bitmasks selecting camera pixels, so it should round-trip; AO's partial chunks carry their own RGB555 pixels, so it would be approximated exactly as the editor already approximates it.

---

## Phase 3 — editing in the browser

Only if Phases 1 and 2 land, and its output must be the Phase 1 JSON rather than a format of its own.

The property form is the cheap half and is close to free: for any field the viewer already knows the raw value, the game type, the full enum value list and the prose definition — `fieldHelp` in [js/fields.js](../public/js/fields.js) composes exactly that list today for the tooltips, so a `<select>` is a rendering of something already computed, and a bare-int field falls back to a number input.

What is genuinely missing:

- **no selection model** — hover yields a list, and `findTlv` identifies an object by name plus top-left ([js/model.js](../public/js/model.js)), so an object that moves loses its own permalink;
- **no dirty state and no undo**;
- **no way to re-derive `t.extra`** — the whole navigation layer (`destOf`, `computeConnections`, `computeEntryPaths`, `destTrusted`) reads `extra`, not `fields`, and the logic that produces it is Python in `tlv_extra_{ao,ae}`. Edit a door's destination and the arrows keep the old answer until that is ported;
- **caches with no invalidation for this** — `connCache` keyed on path identity, `state.entry` recomputed only on a game switch, `searchTextCache` keyed per TLV object, and the demo `WeakMap`.

---

## Ruled out

### Edits shared as a patch or a URL

Not on cost — on what it would cost the map. Nothing downstream consumes a patch of our own invention, and the hash already carries up to ~5.6 KB with a 512-point route, so the payload would have to be a file anyway. The decisive objection is that **a shared link showing edited data is indistinguishable from one showing the game.** Every other feature here is built the other way: `destTrusted` exists so the map never claims a destination the data cannot support, the override rule forbids a curated name from erasing the game's own, and the README states outright that the extracted data is never altered. A link a recipient cannot check undoes all of it. A purely local sandbox is a different proposition and is Phase 3.

### Writing back to a retail LVL or the PS1 disc

**For relive this is already solved** by `ImportPathJsonToBinary`, so reimplementing LVL and BND packing in JavaScript is strictly more work for a worse result — it would also have to carry the FG1 reconstruction and the animation-resource lookup that the import does for us.

**For the retail engine it is the one scope that breaks a stated constraint.** `obj_off`, `idx_off`, `coll_off` and `coll_count` are not in the level file at all: they are static tables in the executable, which is why the builder reads them out of `PathData.cpp` rather than out of the path chunk. relive overrides them at load from the `Resource_Pxtd` `PerPathExtension` chunk the import writes (`PathDataExtensionsTypes.hpp:54-76`, applied in `AliveLibAO/PathDataExtensions.cpp:126-140`) — that mechanism *is* the reason editor output runs in relive and not in the original engine. So anything structural on retail means patching the game's own tables, which is shipping a game-code patch. On the PS1 disc specifically, add per-sector EDC/ECC regeneration on a 2352-byte image — `Disc.sector` only ever touches the 2048-byte user area — plus ISO extent rewrites when a file changes size, for an output that is a modified copy of the game.

Worth stating plainly, since it is the reverse of the intuition: **the static-page and no-backend constraints rule nothing out here.** Every scope is a client-side download. The constraint that actually bites is "ships no game code", and only this one crosses it.

### Targeting `beta`'s cooked format

`beta` deleted `ImportPathJsonToBinary` outright, and playing an edit there means writing into the `relive_data/` tree the user's own install cooked from their LVLs — a directory of per-path JSON (`path_version: 13`), camera PNGs and FG1 manifests, keyed by unified `relive_tlvs` slugs with a vocabulary of their own. That is not a file you hand someone. The editor tree vendored in `beta` is a variant whose LVL export is stubbed out with "Exporting to lvls is obsolete now"; the *released* editor is the standalone repo, on master.

### "One click to playable"

Ruled out as a framing rather than as an implementation. The editor already produces a **better** artefact than we can synthesize, because it starts from the user's own LVL and therefore has the camera art, the FG1 chunks and the animation resources. Our JSON is worse as a level and valuable as a description; promising the former would be promising the part we are weakest at.

---

## Is this a claim the project should make?

**Phase 1 makes no new claim.** It is a verification harness in `tools/`, on exactly the same footing as the builder: it reads committed data and the decomp, and emits a file for our own checking.

**Phases 2 and 3 do, and the narrow form is defensible.** What ships is a JSON describing object placements the site already publishes, in a format defined by a third-party open-source project; the playable artefact is produced on the user's machine, by a tool they installed, from files they own — and relive requires the PC game files regardless, so there is no route by which our download reaches someone who has no copy. The precedent is public and unbroken: Paul's Level Editor circulated for years, the current editor ships signed GitHub releases, the RELIVE site advertises it, and a Steam guide teaches it.

**What to refuse is the rest of the slope.** No hosting or sharing of user-made levels — which the static-site constraint forbids anyway, and which would turn a description into a distribution channel. No modified disc images: that is a copy of the game rather than a description of it, and it is separately ruled out above.

**The reason to keep the write path in `tools/` is not legal, though — it is the site's credibility.** The promise of this map is that everything on it is what the disc says. An editor living inside the map puts that at risk; an exporter living beside it does not. If Phase 2 lands, the About dialog's "ships no game code" stays true and gains one sentence saying what the export is and is not, and the README's rebuild section gains the export beside the build. That touches [68](item-068-repo-licensing.md), the open question of what terms this project states about itself, but does not settle it: a download is not a licence.

---

## Shipped: Phase 1, 2026-09-04

In *Cache relive_api's own schema for the exporter* and the four commits around it: `tools/relive_export.py` writes any path — or all 191 — as a v4 document from the committed data alone, `tools/relive_diff.py` is the structural comparison the disc session will run, and `tools/relive_verify.py` builds `tools/relive_check` (a shim CMake project over the checkout's `Source/Tools/relive_api` directory alone, which is self-contained and SDL-free) and runs every document through relive_api's **own** JSON reader. That oracle came back clean over all 191 paths in both games: no exception, no abort, no silently remapped enum label.

What shipped drifted from the sketch, in ways worth keeping:

- **One committed cache per game (`tools/data/relive_{ao,ae}.json`), not three public sidecars.** None of this is viewer data — `public/` is the deploy artifact — and the `schema` blob is a root key of every exported document, assembled at export time. The `--emit-field-data` outputs never moved a byte.
- **The field→property join rides on payload words, never names.** relive's ADD order is not its read order: its own `Path_MovieHandstone` ADDs contradict its struct, so the cache computes each property's word from the data struct's real layout (base chains, unions, aggregates, alignment, enum backings), validated against the decomp's `ALIVE_ASSERT_SIZEOF` lines. The same sweep found the archive's own liar — AE SecurityClaw, now [93](item-093-securityclaw-layout.md) — and the `WordAudit` test pins the complete set so the next one fails a test instead of shipping.
- **Fourteen placed types' `object_structures_type` literals differ from the names `map_data` carries** — seven per game (our `LCD` is relive's `LCDScreen`, our `Switch` its `Lever`, `DeathClock` its `GasCountDown`); keying the cache by numeric type id made the mapping free rather than a table.
- **The collision-link gap is not disc-free** — this file's claim above is wrong: `Next`/`Previous` (AE `Next 2`/`Previous 2`/`Length`) live only in the path chunk, so capturing them is a builder change **plus a rebuild**, batched for the disc session. The exporter writes the editor's own `-1` and the diff holds those keys as a counted non-fatal class until `--strict-links` promotes them.
- **A pinned fallback table stands in for the words relive reads that the archive doesn't yet hold** — ShadowZone's R/G/B in both games (in the layouts since the ADD_LINKED widening, in `map_data` only at the next rebuild), MovieHandstone's meaningless s32 high word, and SecurityClaw's unarchived `Unknown`. Every entry prints on every run and doubles as the diff's known-divergent set, so retiring one retires its tolerance too; a rebuild spends them loudly — except MovieHandstone's, whose word the archive drops by design, so that one stays.
- **The Context wording under "How to verify it" was optimistic**: `Context::MissingJsonProperties()` is dead code upstream — nothing ever populates it. A missing numeric property *aborts the importer process* (jsonxx asserts stay on in release), a missing enum property throws, and only an unknown enum *label* lands in `Context::RemappedEnumValues()` — which is therefore what the oracle fails on.

The disc-session runbook: dump a byte-exact LVL (`tools/relive_verify.py --dump-lvl AO R1 /tmp/R1.LVL`), then `relive_check enum /tmp/R1.LVL` — the **time-boxed leg**, the first moment relive's `OpenPathBnd` meets a PS1 LVL; if it refuses, the fallback is the GOG PC copy priced above and everything else stands. Then per path `relive_check export` (garbage base64 expected — the diff never reads it) and `tools/relive_diff.py ours.json reference.json`, recording totals and the tolerated-class counts with the date. First divergence: minimize to one object or line, read the path-chunk bytes at that offset, classify as our extraction bug, our exporter bug, or a reference-side quirk (candidates already known: AE `Next_TLV`'s skip-the-last-entry TODO, and AO tables compiled from the pin versus our parse pinned at `AO_COMMIT`). One reference-side quirk is already confirmed and tolerated: the reference indexes AE's per-level mud table by the **path index** it was handed (`ToPathInfo` receives `PathAt`'s id, and past path 14 it reads beyond the 15-row table), where the engine — and our export — read it by level id, so the diff holds AE's `num_muds_in_path` known-divergent until an upstream fix. After the rebuild that captures the collision links, ShadowZone's colours and [93](item-093-securityclaw-layout.md)'s words: rerun with `--strict-links` and delete the spent fallback entries.

## Byproducts this spike owes elsewhere

- **[29](item-029-decomp-label-sweep.md)'s branch note now rests on the pin rather than on `beta` being dormant:** the released editor pins master, so the tree our parsers read is the tree the tooling downstream of it uses. That is the argument; the divergence — 1783 commits ahead of master and 42 behind, measured 2026-07-31 — sizes the parser rewrite `beta` would cost, and settles nothing about which branch to read.
- **Two real holes in the shipped archive**, found by reading the import contract rather than by looking for them, and worth fixing whether or not any of this is built: the `ADD_LINKED` blind spot costs `ShadowZone` three fields in both games, and the collision link fields are being dropped from bytes the builder already has in hand.
