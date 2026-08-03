# 29. Decomp label-correctness sweep

**Status:** ongoing · **Effort:** alive_reversing PRs plus a sidecar regen · **Where:** anywhere — the scans read committed caches, the regen needs no disc

## What and why

A field label is only as good as the decomp's declaration behind it, so a field declared as the wrong type — or as a bare int where an enum belongs — renders raw or, worse, renders as the wrong word. The `chase_abe_when_spotted` fix (merged, [PR #1697](https://github.com/AliveTeam/alive_reversing/pull/1697)) was one misdeclaration; a full `objects_{ao,ae}.json` type scan showed it was the *only* one of its kind — every other cross-carrier type difference (`start_state`, `grab_direction`, `off_sound`, `type`) is a legitimate per-object enum. Two more were raised upstream that a *type* scan cannot catch:

- **ContinuePoint `scale` values possibly swapped** — the decomp has two scale enums for different objects and the checkpoint's may be reversed (full↔half). A *value*-correctness bug, invisible to a type scan.
- **AO `PathTransition` `level` not using `LevelIds`** — a bare int where the enum belongs, so it renders raw. The "missing enum" class, the same family as the numeric fields in [28](item-028-readable-units.md).

## Sketch

The type-inconsistency scan is done (only `chase_abe`). Value-swaps and missing-enums need eyeballing — the map itself is now the tool (search a suspect field, or pan-zoom-click), or diff enumerator order against the raw values in `map_data`. Each confirmed fix is an `alive_reversing` PR to **master's** version converter (bump `kApiVersion`, add an `UpgraderAE`/`AO` step remapping old maps), then regenerate the sidecars here — better labels in the viewer, a faithful decomp upstream.

**Batch the upstream fix — do not ship a scale-only PR.** `scale` is one member of this class, so one PR should fix the whole *confirmed* set at once: change the bare `s16` decls to their enum type in `Tlvs{AO,AE}.hpp` / the `AliveLib*` headers, bump `kApiVersion`, and add an AE **and** an AO upgrade step registered with `ADD_UPGRADE_STEP_FROM` — `RemapNumberToEnum` for `scale` (`0 → "Full"`, `1 → "Half"`) on each object's Scale property, and `LevelIds` numbers → labels for `level`. One version bump per class is the upstream preference, since the relive submodule is not re-pinned on every change. Then regenerate the two sidecars, and the 13 `scale` fields plus PathTransition/Teleporter `level` start reading as words with zero viewer change.

`_FIELD_TYPE_OVERRIDES` can't do this locally — it only *corrects* an existing type, it can't *add* one to a bare-int field; and per [CLAUDE.md](../CLAUDE.md)'s policy decomp quirks are fixed upstream and re-pinned, never by patching the local checkout.

**Why the parsers target `master`.** AliveTeam's released level editor pins `alive_reversing` **master** (`e2badb8df`) as its submodule, so the declarations these parsers read are the declarations the tooling built on the decomp uses. That is the whole argument. The `beta` branch is a ~1783-commit refactor (measured 2026-07-31: 1783 ahead of master, 42 behind) with a different JSON schema and a rewritten relive_api, so `parse_member_types` / `parse_object_schema` / `parse_enum_labels` would each need a rewrite to read it; if it ever becomes the base, that rewrite is the cost. See [42](item-042-level-editor.md), which established the pin.

## Findings

**Missing-enum scan (2026-07-23):** a "sometimes-typed, sometimes-bare" scan over `objects_{ao,ae}.json` — a field name that is enum-typed on some carriers but a bare `s16` on others, the pattern a missing enum leaves — surfaces the candidates in one shot.

- **`scale` — confirmed, ready to fix.** Declared bare `s16` on 13 objects (AO: `BellSongStone`, `HandStone`, `MovieStone`, `MovingBomb`, `WellExpress`, `WellLocal`; AE: `Drill`, `FlyingSlig`, `FlyingSligSpawner`, `SligGetPants`, `Slurg`, `SlurgSpawner`, `Teleporter`), every value only 0/1 — genuinely `Scale_short`. `Slig` uses `Scale_short` while `SligGetPants`/`FlyingSlig` sit bare: classic copy-drift. Renders raw today (the Teleporter tooltip's `scale=1`), which is *visually clear*, so no rush.
- **`level` — confirmed missing-enum.** Bare on AE `PathTransition` **and** `Teleporter` (should be `LevelIds`) — the same report as the AO `PathTransition` one above, on the AE side, and it hits Teleporter too.
- **Candidates needing a value-check (name-collision, not yet confirmed):** AO `action` (DeathDrop), `speed` (Bat/Bees/MeatSaw/MotionDetector/MovingBomb/RollingBall/BeeSwarmHole), `type` (BellSongStone), `persist_offscreen` (MovingBomb/Mudokon); AE `start_direction` (Drill/FlyingSlig/FlyingSligSpawner/Slurg/SlurgSpawner), `persistant` (FlyingSlig/Spawner), `spawn_delay_state` (FlyingSlig/Spawner), `sound_direction` (CrawlingSligButton), `stay_awake` (SligSpawner), `state` (TimedMine), `behavior` (Drill), `colour` (DoorFlame). Some are real missing-enums, some legitimately different fields — eyeball each before touching upstream.

**Which tree the version numbers describe (checked 2026-07-31).** The sibling `alive_reversing` checkout sits on `master` at `e2badb8df` (2026-02-26), and there `kApiVersion = 4`, the newest registered upgrade steps are `UpgraderAO3`/`UpgraderAE3`, and SligSpawner's `chase_abe_when_spotted` is still declared `XDirection_short` — so PR #1697 and any version bump past 4 are upstream of the pin, not in it. Fetch master and re-read the version and the newest upgrade step before opening the PR, rather than carrying a number from here; and note that the override correcting `chase_abe_when_spotted` is still load-bearing against the pinned tree.

**Recorded so it isn't re-proposed as the reason:** what makes master the right base is the editor's pin, not the state of the `beta` branch.
