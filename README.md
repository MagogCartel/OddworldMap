# Oddworld Map

Interactive map of **Oddworld: Abe's Oddysee** and **Abe's Exoddus** (PS1, NTSC-U), extracted directly from the game discs: every camera background, every object (doors, levers, Mudokons, LCD status boards, hazards, enemies, ...) and every collision line, laid out on the games' real camera grids. The data comes from the PS1 discs, but level layouts, screens and object placements are the same in the PC releases, so the map applies to every version of the games.

Browse it at **[oddworldmap.com](https://oddworldmap.com/)** — or serve the `public/` folder with any static web server (`python3 -m http.server -d public`) to run it locally.

![The viewer on Stock Yards in Oddysee, inspecting a travel bird portal](screenshot.png)

One grid cell = one in-game camera: the viewer lays the games' camera screens out edge to edge on their real world grid and translates every object and collision coordinate to match, so markers land on the artwork.

## Controls

- **AO / AE** buttons switch between the two games
- **drag** or **arrow keys** to pan, **mouse wheel** (anchored at the cursor) or **`+` / `-`** to zoom; **`[` / `]`** step through the level's paths, **`g` / `c` / `f` / `a`** flip the grid, collision lines, foreground masks and connection arrows, **`r`** / **`m`** arm the route planner and the ruler, and **`i`** says where you are — press **`?`** for the full shortcut list
- **hover** any object for decoded details
  - the details open with what the thing *is*: one plain-English sentence per object type, the opening line of its encyclopedia entry (curated in [glossary_types.json](public/glossary_types.json))
  - door destinations (level/path/door#), switch IDs, path-transition targets, continue-point zones, Mudokon state (Oddysee job / Exoddus work state + mood), and enemy behaviour (a Slig's start state and how it attacks — `shoot_on_sight_delay=0` means it shoots the instant it sees Abe, no "FREEZE!" warning; whether a Slog starts asleep and the switch that angers it)
  - each object type surfaces its own notable fields too — a door's lock state, a trap door's or electric wall's on/off, a bird portal's type, a Glukkon's or Crawling Slig's type/state
  - Settings → "Show more object fields" picks which of the game's stored fields each object type shows; search covers them all either way
  - in the screen list and the Fields picker, every field name carries a definition, marked by a dotted underline — what it means and its possible values, curated in [glossary_fields.json](public/glossary_fields.json); hover it with a mouse or tap it on a touch screen, where the tap still does what it would have done anyway (tick the field, jump to the object)
- **click** a door, path transition, travel portal, express well, teleporter, level loader or hand stone to follow it to its destination (for hand stones, the camera they show), including across levels
  - while hovering one, its partner — the object you'd come out of — gets a dashed outline whenever the pair sits on the current path
  - a destination is only believed where the object it pairs with is really there: Exoddus stores a level of 1 on links that were never pointed anywhere, which reads as Necrum Mines, so those name no destination and offer no follow — their stored fields still show, raw as the game left them
  - an express well has a destination for each state of the switch it answers to, and the map follows whichever of the two leads somewhere
- **click/tap** anywhere else on a screen to list everything on it, grouped by category
  - hover a row to outline that object on the map, click it to jump there
  - tapping an object opens the list scrolled to that object's highlighted row: on touch devices, where there is no hover, this is how you inspect an object
  - the **ⓘ** at a row's edge (also next to each type in the Fields panel) opens that type's encyclopedia card: the full curated entry, how many are placed in each game — counted live, with what the hidden demo paths hold noted apart — what its stored fields mean, and a link that finds every one of them with search
  - on phones the panel opens as a bottom sheet with the map staying visible above it; switch "List a screen's objects on click" off in Settings if you'd rather those clicks did nothing
- level and path buttons top-left; object category filters with counts below
  - hover a path button for its area name: a curated community name from [annotations.json](public/annotations.json) where one is defined (a deliberate override), otherwise the in-game name (Rupture Farms Return's Zulag 1–4)
  - ahead of either, the section where the game gives one — which half of the level the path belongs to, for the thirteen Exoddus areas the endgame returns to
  - where players have a nickname for a place, that follows after a `·` — nine of the Brewery's zulags carry one, so zulag 3 reads `Zulag 3 · Industrial Machines`, dimmed because it is not what the game calls the place, and on the button itself only with "Show full names" on
  - Exoddus' 25 demo areas — copies of real places that only the demos on the title screen ever play, unreachable however you play — are left off the buttons; Settings → "Show demo paths" lists them, and a link to one opens it either way
- **where you are**: a chip at the top-left corner of the map names the level and path you are looking at
  - click it (or press **`i`**) for the level's full name, which half of it the path belongs to where the game says, the nickname players gave the place where it has one, whether the path is one the game arrives at from another level or one only the title-screen demos play, and the path's note where it has one — a remark on something odd about the place, marked by a dot on the chip
- **somewhere odd**: the shuffle button beside the chip jumps to a random screen — either game, any level — for when you'd rather the map did the choosing
- **minimap**: when a path outgrows the window, a small overview appears in the lower-right corner — the path's grid with the viewport drawn on it; click or drag inside it to move the view (it steps aside while the By-the-numbers panel is open, and hides once the whole path fits on screen)
- **reset** in the Display and Objects headers puts that section back to its defaults
- **search** (`/` to focus) matches object names and decoded fields across both games — try `mudokon`, `lcdstatusboard` or `switch_id=70`
  - it also knows the places themselves, listed as a **Places** group above the objects: a level or path by its name (`monsaic`, `feeco`, `zulag 2`), by the nickname players gave it (`tear extractors`), by the section the game files it under (`ender`), or by its code (`R2 P1`) — down to a single screen (`R2 P1 C3`, or a full camera name like `r1p15c03`) — clicking one takes you there, a level opens on the first path it lists, and a screen centers that camera
  - a place's level name finds what is inside it, so `paramonia temple` lists the temple and its trials; the code answers whole words only, so the `2` in `zulag 2` is not answered by the `R2` a path happens to sit in; a screen answers only a query that names one, so `brewery` brings back the Brewery and its paths, not its hundred screens
  - combine terms: a space means all must match (`Mudokon state=chisle` finds only chiselling Mudokons), a comma or the word `or` means any (`Slig, Slog`)
  - results are grouped by context (current path, current level, then per game), rank exact name matches first, and clicking (or Enter) jumps straight to the hit
  - a scope bar narrows the search to the current game/level/path
- on touch devices one finger pans and two fingers pinch-zoom the map; the page itself pinch-zooms too, and while it is zoomed two fingers on the map zoom the page back out instead; the sidebar collapses behind a menu button on narrow screens
- **What's new**: the top-right button opens a dated changelog of recent updates; a dot marks entries added since you last opened it, and the tags under the masthead switch each kind of update (new, improved, fixed) in or out of the list — a choice the panel forgets when it closes, so a filter can never hide the news
  - the handful of updates that added something the map was built around wear a shifting foil badge beside their kind, and a Flagship tag at the end of the row switches them; a flagship answers to that tag alone, so turning the other three off leaves the flagships by themselves — the shortest history of the map there is
- **About this map**: the link at the foot of the sidebar opens the notice that this is an unofficial fan project unaffiliated with Oddworld Inhabitants, alongside links to the map's source and to the project whose reverse-engineering the data formats come from

### Overlays

Every toggle in the Display section explains itself: hover it for a short note on what it draws (on a phone, the note appears as you tap the toggle). The toggles with a keyboard key wear it at the row's edge, and it lights while the key is held.

- **Object labels**: names each object beside its marker, from about half zoom in
- **Connection arrows**: draws the path's whole circulation — every door, express well, bird portal, teleporter and path transition linked to where it leads
  - a double-headed arrow is a two-way pair; a dashed arrow points at the arrival camera when the exact arrival object isn't resolvable; short 45° stubs labelled `→ MI P7` lead to other paths (stub labels appear zoomed in with object labels on)
  - colours tell the kinds apart: doors and the level loader yellow, wells pink, bird portals lavender, teleporters teal, path transitions white
  - hovering an object spotlights just its own arrows
- **Switch wiring** (off by default, or press **`w`**): what a lever actually does — green dotted lines from everything that writes a switch id (levers, buttons, work wheels, pressure plates, pull rings) to everything on the path answering that id (doors, drills, electric walls, trapdoors, bird portals, spawners, status lights), through the logic gates Exoddus wires between them and the hub doors Oddysee opens only when every zulag id they watch is set
  - hovering a wired object spotlights just its own wires, with arrowheads showing which way the signal runs, and the tooltip spells them out — `sets 66 → 5 objects`, or `answers 11 — set in P2` for a wire whose other end lives on another path of the level (switch state is level-wide in the engine, so those connections are real)
  - wires run between markers you can see: hide a category and its wires go with it (status lights and alarms sit in buckets that are off by default)
- **Enemy patrol pens** (off by default, or press **`p`**): the invisible posts that pen enemies in (Slig and Scrab bounds, enemy stoppers, moving-bomb stoppers) draw as dashed posts on the exact boundary the game enforces, whenever Enemies / spawners is on and whatever filter bucket they belong to; a foot at the base points into the pen where the type claims a side
  - hover a Slig (or a Slig spawner) and the span it patrols shades in, edge to edge between its own pair of posts — matched the way the game itself matches them, by the slig id both ends carry
- **Collision lines**: floors green, walls red/orange, ceilings blue, dashed = background layer
- **Background-plane objects**: objects placed on the half-scale background plane are drawn dimmed with a dashed outline, so foreground and background objects are tellable apart when reading a route
- **Foreground masks (FG1)**: highlights the scenery drawn in front of the player — every hideable/behind-walkable spot at a glance (pairs well with "Dim backgrounds")
- **Dim backgrounds**: fades the camera artwork to a third of its brightness, so markers and overlays stand out against it

### Measuring and routes

- the readout in the map's bottom corner follows the pointer: its world position, where it stands within its screen in grid squares, and the zoom
- **Ruler**: enable (or press **`m`**), then drag to measure — Δx × Δy, length in true world units and 25-unit grid squares (an Oddysee unit is one PS1 screen pixel; Exoddus screens are scaled artwork, and measurements account for that)
  - its ends snap to nearby object centers — and to collision-line ends while those are shown — so door-to-door distances come out exact; the radius is a few screen pixels, so zooming in shrinks it away
  - hovering a collision line shows its type and length the same way
  - moving on (switching path, following a door, changing game) clears the measurement
- **Route planner**: arm it (or press **`r`**), then click waypoints to plot a route — every leg is labelled with its length, and a bar at the top totals the distance in the same units
  - waypoints snap the way the ruler's ends do
  - **routes go through doors**: while the planner is armed, clicking a door, well, portal or teleporter closes the leg on it, rides it, and keeps plotting where you land — the line breaks at the seam, since the travel between the halves isn't walked, and the bar says how many paths the route crosses (hand stones only show a camera, so they stay plain waypoints)
  - **Backspace** (or the bar's undo button) removes the last waypoint — at a seam it takes the whole crossing back; clear starts over, and the browser back button brings a cleared route back
  - the route travels in the URL, so copying the link shares it exactly as plotted — it opens visible with the map fully browsable, no mode armed — and it appears in PNG exports
  - whoever you share it with can walk it: the route stays while you move among its own paths — path buttons, doors, the back button — and clears only when you wander somewhere it never visits (Back brings it back)
  - should a chat app or forum shorten the link, it opens with the waypoints that survived and says how many are missing

### By the numbers

- the **By the numbers** button under the Objects filters opens a small panel that counts object types you pick at every granularity at a glance: the screen under the view's center, the current path, the level, the whole game
- the numbers follow you as you browse: switch path, follow a door, even press shuffle, and the panel re-derives itself
- counting reads the data rather than the display (a type whose category filter is off still counts, the way search still finds it) and follows the demo-paths setting, noting below the table what the hidden demo copies hold
- click a type's name in the table to stop counting it

### Sharing and embedding

- the URL hash (`#GAME/LEVEL/path/x/y/zoom`, where x/y is the point in the middle of the view) always reflects the current view, including any plotted route
  - copy it to share an exact location, and it opens on that spot whatever the size of the window it lands in; the browser back button retraces follows
  - the chain button in the top-right corner copies the same link, for phones and installed-app mode where there may be no address bar
- **right-click** an object to copy a direct link to it — opening that link centers the object, holds a marker on it until you interact, and names what the marker is on at the bottom of the map
- add **`?embed=1`** to the URL for a view made for iframes on wikis and forums: the map fills the frame, fully interactive (hover, follow, the screen-list panel), with the sidebar starting closed but reachable through the menu button
  - a corner button opens the full site at the exact view
  - combine it with any permalink hash to embed an exact screen, e.g. `https://oddworldmap.com/?embed=1#AO/R1/15/…`
- **Export view as PNG** (the button under the Display toggles) saves what the canvas is showing — the visible area at the current zoom, with every overlay, marker and plotted route that is on — as `oddworld-ao-R1-P15.png`; zoom out until the area you want fits before exporting

### Settings

The gear button at the top of the sidebar opens them, in three groups. A setting you have changed from its default says so on its row, so "off by default" reads apart from "I turned this off".

- **Saved on this device**
  - "Remember display & object filters" (on by default) keeps the Display toggles and Objects filters across visits; turn it off to start from the defaults every time
  - "Remember last location" (off by default) reopens the map where you left off when the URL carries no permalink — a shared link always wins
  - "Keep the map on this device" (off by default) stores the app itself and every screen you visit — up to ~150 MB — so the map opens and works offline, the places you've browsed included; everything refreshes automatically while you're online, and switching it off frees the storage
- **Buttons and names**
  - "Show full names" (on by default) expands the game, level and path buttons into a list labelled with their full names ("MI — Necrum Mines"); turn it off for the bare short codes
  - "Show demo paths" (off by default) adds Exoddus' 25 demo areas to the path buttons, marked `[Demo]`; they are copies of real places that only the title-screen demos visit, so the map leaves them out of the buttons and out of search results, but a shared link to one still opens it and says what it is
- **Objects and fields**
  - "List a screen's objects on click" (on by default) opens the screen-inventory panel when a click/tap finds nothing to follow
  - "Show more object fields" (off by default) reveals a "Fields" panel in the sidebar where you pick, per object type, which of its fields show in tooltips and the screen list (the notable ones pre-checked) — a ⚙ next to an object in a screen's list opens that type's row in the panel; with it off, only the notable fields show and the panel stays hidden
  - "Show raw field values" (off by default) shows field values as the raw numbers the game stores (1/0, 15, …) instead of the translated text (left/right, patrol, true/false); search matches whichever representation you're viewing

## Rebuilding from a disc image

The site's generated data under `public/` (`cams/`, `map_data_ao.json`, `map_data_ae.json`) is produced by [tools/build_map.py](tools/build_map.py) from raw PS1 disc images (2352-byte sectors, e.g. the `.bin` of a `.cue/.bin` dump):

```bash
python3 tools/build_map.py --game AO --disc "/path/to/Abe's Oddysee.bin"
python3 tools/build_map.py --game AE --disc "/path/to/Exoddus (Disc 1).bin" "/path/to/Exoddus (Disc 2).bin"
python3 tools/build_map.py --levels R2,R6   # subset while iterating
```

`--disc` can be omitted if `$ODDWORLD_DISC_AO` / `$ODDWORLD_DISC_AE` point at the images; `$ODDWORLD_DISC_AE` holds both discs separated by `:` (the PATH separator):

```bash
export ODDWORLD_DISC_AO="$HOME/games/Abe's Oddysee.bin"
export ODDWORLD_DISC_AE="$HOME/games/Exoddus (Disc 1).bin:$HOME/games/Exoddus (Disc 2).bin"
```

The script needs Python 3.8 or newer, compiles `tools/cam2rgba` automatically on first run (needs a C++17 compiler) and requires [oxipng](https://github.com/oxipng/oxipng) — every emitted PNG is losslessly recompressed so rebuilds stay byte-identical to the committed images. Level/path table layouts are cached in [tools/data/pathdata_ao.json](tools/data/pathdata_ao.json); they only need regenerating (which requires an [alive_reversing](https://github.com/AliveTeam/alive_reversing) checkout as a sibling directory) if that cache is deleted.

A rebuild that changes any committed cam PNG also rewrites `CACHE_NAME` in [sw.js](public/sw.js), which the build summary prints — commit that line with the artwork. It is a content hash of the images, and visitors who opted into artwork caching serve cams cache-first from a service worker and never revalidate them, so it is what stops them keeping the old images indefinitely.

## How it works

- **Disc → files**: raw MODE2/FORM1 sectors are parsed as ISO9660; each level is a `.LVL` archive (32-byte header + 24-byte file records) containing the path data (`xxPATH.BND`) and one `.CAM` per camera.
- **Path chunks** hold, in order: the camera-name table (8 bytes/cell), collision lines (20 bytes, coordinates + type), and packed TLV object records (0x18-byte header in AO, 0x10 in AE, + type-specific payload) which the builder walks linearly and places by world coordinates.
  - Level/path tables and the AE type enum are parsed from the [alive_reversing](https://github.com/AliveTeam/alive_reversing) decompilation into `tools/data/` caches.
- **Camera backgrounds** are MDEC-compressed: 12 strips per screen, each a `u16 length` + standard PS1 BS v3 bitstream decoding to 32×240, assembled into 384×240 and written as PNG (368 visible columns + 16 columns of macroblock padding, cropped by the viewer).
  - The decoder (`tools/cam2rgba.cpp`) is built on `PSXMDECDecoder` from the [alive_reversing](https://github.com/AliveTeam/alive_reversing) project, patched for bounds-safe decoding of camera strip streams.
- **The viewer** is dependency-free vanilla JS with no build step: [index.html](public/index.html) plus [css/main.css](public/css/main.css) and the ES modules under [js/](public/js/) ([js/main.js](public/js/main.js) boots the app); `map_data_ao.json` / `map_data_ae.json` carry the level/path/TLV/collision data.
  - **Offline cache**: an optional service worker ([sw.js](public/sw.js), off by default — Settings → "Keep the map on this device") keeps the app and visited screen artwork cached on-device: repeat visits render instantly instead of re-downloading, and with no connection the map still opens and shows every place you've browsed.
  - **Checks**: `npm run lint` (ESLint) and `npm test` (`node --test` unit tests for the DOM-free logic) cover the viewer, and the builder is byte-compiled, linted with [ruff](https://docs.astral.sh/ruff/) and unit-tested with `python3 -m unittest discover -s tools/tests` (stdlib only, no disc image needed); CI runs all of it.
  - **Changelog**: the in-app What's New panel reads [changelog.json](public/changelog.json) (hand-curated, newest-first); [tools/changelog.py](tools/changelog.py) drafts candidate entries from the git log (dropping internal churn and printing each commit as context) to be curated in, but never writes the file itself.
- **Curated names**: [annotations.json](public/annotations.json) is hand-curated (never generated) — names and notes the discs don't provide: community names for 155 of the 173 paths the games leave nameless, plus notes on the places with something odd about them.
  - A path entry is a bare name string, or `{name?, note?, nickname?}` where there is more to say.
  - The note is a curiosity about that place, not the evidence behind the name, and it reads in the panel behind the map's place chip.
- **Nicknames**: a `nickname` is what players call a place, where the map has adopted their name for it — the [Oddworld Wiki](https://oddworld.fandom.com/wiki/SoulStorm_Brewery_(level))'s names for the Brewery's zulags, used as written where the shipped data confirms they fit, so zulag 3 answers to Industrial Machines and does hold more drills than anywhere else in the level.
  - It cannot be folded into the name, because every colon name in the Brewery marks a sub-path of a zulag that spans more than one path, so "Zulag 10: Slig High Security" would claim a division that isn't there.
  - It shows dimmed beside the name, never in its place, and each one is pinned in the tests against the fit it claims.
  - A name the map coins itself is not a nickname and goes in `name` instead.
- **The override rule**: a curated name deliberately overrides the in-game one where both exist, but must keep the in-game label visible within it ("Zulag 2 — Lobby", never a full erasure — the tests enforce this); the extracted map data itself is never altered.
  - A path's section is not a name and stands outside the rule: it says which half of the level the path belongs to, so it shows beside the curated name instead of having to be repeated inside it.
  - An adopted name stands outside it for the same reason — it is not the curated name, so it has nothing to refine.

Structure layouts (TLV types, path tables, collision records) come from the alive_reversing decompilation (commit `c1ba4c6c8` for AO, current sources for AE), which matches the PS1 data formats. Both games address cameras on a grid coarser than the screen: world units map 1:1 to PS1 screen pixels, and each camera shows a 368×240 window of them inside its cell. AO's cell is 1024×480, with the window centered at (cell·1024+440, cell·480+240); AE's is 375×260, with the window at the cell's corner. The map lays screens out edge to edge, folding away the slack the game never renders.

## Credits & licensing

- Game data formats reverse-engineered by the [AliveTeam / alive_reversing](https://github.com/AliveTeam/alive_reversing) project.
- Curated path names in [annotations.json](public/annotations.json) draw on Oddworld: New 'n' Tasty's official chapter names and on the [Barebones walkthrough](https://steamcommunity.com/sharedfiles/filedetails/?id=1812678216) on Steam, whose per-path titles most of the Oddysee names follow.
  - The Exoddus names are read off the game's own signage where it has any — the zulag, tunnel, block and terminal boards and the arches over them — and elsewhere from matching each path's contents against MCJohn117Chief's [GameFAQs walkthrough](https://gamefaqs.gamespot.com/pc/198221-oddworld-abes-exoddus/faqs/74324) and the [Oddworld Wiki](https://oddworld.fandom.com/wiki/SoulStorm_Brewery_(level)), with the demo paths and each level's entry path taken from the decompilation's own tables.
  - A curated name may refine the games' own coarse labels, but the extracted data is never altered.
- Nine of the Brewery's zulags additionally carry a nickname, the Oddworld Wiki's own name for that sector, adopted as written (minus its `#1`/`#2` numbering) where the shipped data confirms the name fits: Industrial Machines, Electrical Devices, Tear Gas, Blind Mudokon, Slog Warehouse, Slig High Security, Tear Extractors and the two Flying Sligs zulags.
  - Those are the wiki's coinages, not this project's, and the map shows them as such — beside each zulag's own number rather than in place of it.
- `tools/PSXMDECDecoder.{cpp,h}` are GPL-2.0 (see file headers; originally from libbs / psxdev). The rest of the tooling and the viewer were written for this project.
- Oddworld: Abe's Oddysee and Abe's Exoddus are © Oddworld Inhabitants. This project ships no game code and is intended for research, speedrunning and preservation; the extracted imagery remains the property of its copyright holders. The site says as much in the app, behind the sidebar's "About this map" link.
