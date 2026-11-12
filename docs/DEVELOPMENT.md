# Development and verification

This repository contains the RE2 annotated-map mod. The release ZIP installs `scripts/RE2.AnnotatedMap.asi` with its commented default INI and bundles Ultimate ASI Loader as `dsound.dll`; settings and the log are written beside the ASI. It does not contain game executables, RDT files, original item atlases, saves, Wine wrappers, translation patches, cutscene patches, or historical diagnostics.

## Build inputs

`src/re2_keymap.c` is the runtime source. The remaining headers are the pinned current generated map/label/icon data. The bilingual label texture headers contain text rasterized with the open-source Pretendard fonts in `fonts/` (Korean labels SemiBold, English labels and legend Medium); release builds must not use proprietary system fonts. No font is needed to compile. `data/room_names-*.json` hold the editable room names and `data/room_shapes.json` the map geometry. Editing them does not change a build until the headers are regenerated. The repository builds from the pinned headers, so an ordinary build needs neither the generator nor game files.

`requirements.txt` pins Zig 0.16.0 for cross-compilation. `build.py` never installs into the game and does not launch it. Output is ignored by Git. The workflow builds on Ubuntu and uploads a build artifact; releases are published manually.

## Native tests with a legally owned executable

Supported executable SHA256:

```text
21b2a647cbeddac1ec389be847f22a434a0264a18020589de91cb2824dcb1bf5
```

The runtime has version-specific address and instruction guards. Do not remove guards to force a different executable to load. A different game build needs separate address/ABI analysis and runtime verification.

```sh
python -m pip install -r requirements-test.txt
python build.py --game-exe '/path/to/Resident Evil 2.exe'
```

The EXE is read only and its digest is checked first. Unicorn tests execute the actual x86 draw/texture code and verify state, flags, scenario/character gates, map-only keys, bilingual labels, texture uploads, and buffer limits. Tests are copied into `build/` and write reports there. The game EXE is never copied into the repository or package. Tests do not establish GPU behavior or visual acceptance in a running game. Existing label collision counts are diagnostic, not a guarantee of no overlap on every map.

## Regenerating map data

`tools/mapgen/` regenerates every pinned header from a legally owned game install. It reads the EXE and RDT files, never modifies them, and keeps game-derived intermediates in `build/regen/`, which is ignored by Git. Do not commit that folder.

```sh
python -m pip install -r requirements-assets.txt -r requirements-test.txt
python tools/mapgen/regen.py --game '/path/to/Resident Evil 2'           # compare with src/ and tests/fixtures/
python tools/mapgen/regen.py --game '/path/to/Resident Evil 2' --write   # update them
python tools/gen_wiki.py
```

Without `--write`, the command exits non-zero when a generated file differs from the tracked one. Run it after changing a generator, a name or an icon, and review the reported files.

Inputs tracked in `tools/mapgen/`: `opcode-sizes.json` (script opcode lengths), `excluded-approved.json` (pickup rows reviewed and left out; the extractor stops on a new unexplained exclusion) and `area-maps.json` (area-map analysis, including short script records).

## Name placement rules

These follow the RE0 HD map mod's rules, which are the default for every map mod since 2026-11-07. Room names are placed when the headers are generated (`generate_room_names.py`) and never move at runtime. Key-item names are placed at runtime (`src/re2_keymap.c`).

Priority:

- Key-item stars and names are never covered. Common items and enemies may be covered or hidden.
- Room names avoid only each other and the legend/readout panels. They ignore markers, and nothing avoids them except that key-item names lean away from them.
- A marker touching the legend or the readout panel is not drawn (a key star takes its name with it).

Room names (`place_labels`):

- Tightest rooms choose first. A name stays inside its room when it fits on the room's own mask, checked at 2 px, 1 px and no wall margin, then at 80% size. Among the spots within 0.05 of the best coverage (or fully covered), the one nearest the mask's pole of inaccessibility wins (`pole`).
- Otherwise the name sits outside on an axis-aligned leader line that starts on a mask pixel of its own room: first the shortest line into free space (`near_spot`, at most 45 px), then a fallback outside the floor's bounding box, which may cross another room at a right angle.
- Leaders never share a line with a room outline (`along_outline`): they start at least 3 px from their own room's corners (narrow rooms use their centre), and no wall lies within 2 px beside them.
- Leaders never run through another room name, and outside names never overlap a room mask. The generator asserts these checks and stops on a violation.
- Multi-word names are wrapped between words only: when they do not fit, or when one line is wider than 150% of the room.
- The panels are reserved `PAN_MARGIN` px larger toward the map, since room names are in map space and panels on screen.

Marker names (`item_label_draw`):

- Names of 8+ characters wrap at the space nearest their middle (`generate_item_labels.display_lines`); each line is its own raster, and the second line is the next `item_labels` entry of the same item. Korean `A의 B` names drop `의` unless the stem is one syllable or listed in `KEEP_UI`.
- Candidates touch the marker: right, left, below, above, then the four corners. The first spot with no overlap wins, else the least weighted overlap; only if that still overlaps, a second ring one name height further out is tried. Each reserved box carries its weight (`occupied_w`): stars, diamonds, panels and key names 8x, room names 4x, other names 2x, other markers 1x.
- `[H]` names every drawn marker that has a name (`draw_marker_names`, after all icons): locks (the key's name), puzzles, area maps, documents, then common items; documents and common items only take a spot covering nothing of weight >= 2. Document titles and puzzle names come from `data/marker_names.json` (below).
- Names and icons follow the map zoom: 143% at 2x (`ZOOM_GAIN`, the RE0 mod's 0.7 zoomed-out ratio), times the size settings.
- Lines align toward the star: left-aligned on the right, right-aligned on the left, centred above or below.
- A lower-priority icon overlapping a key star, key name or puzzle diamond is not drawn. An area map or lock centred on a star or diamond is drawn as a badge 3 px down and right instead.

`tests/test_label_priority.py` and `tests/test_map_geometry.py` check these rules. Translucent names render below every opaque quad, so draw order alone cannot put a name over an icon.

## SD mode

SD mode (no HD pack: `bio2hd.asi` not loaded, or `RetroMode`/`LowResEnable` on, or `DisplayMode=SD`) draws 1:1 sprites from `src/sd_assets.h`, built by two tools:

- `tools/mapgen/sd_layout.py [pl,floor ...]` places every room name outside its room on a leader (leader starts 3 px inside the room, names avoid every possible non-enemy marker, the native title, compass, arrows and the folded legend; fewest-spots-first, then a refinement pass for English) and writes `data/sd-layout.json`. About 8 minutes in parallel; rerun when room names, rooms or marker positions change.
- `tools/mapgen/build_sd.py` renders markers (`tools/mapgen/sd_icons.py`: the approved lock table, 9x9 markers), Galmuri9 names and the legend into `src/sd_assets.h` (5 RGB555 pages: markers, English names, Korean names, legend). Run it after `sd_layout.py`.

`tests/test_sd.py` checks the layout tables and an emulated draw with SD forced (`KeyMapTestSdMode`). Preview images: `local/sd-test/preview_sd.py` (untracked) draws shapes, markers and names for one screen.

## Document and puzzle names

`data/marker_names.json` is the only source of these names. Documents (item ids 106-126): the game's own file titles. They are bitmaps, page 2 of `Common/file/fileNN.bin` (Korean, from the installed HD patch) and `fileNNu.bin` (English), NN = item id - 104; `tools/mapgen/extract_file_titles.py` unpacks them with the EXE's own decompressor, and `regen.py` stops when a bitmap hash differs from the table. The titles were read from the bitmaps by eye; entries with `ko_reading_uncertain` are flagged for confirmation. Puzzles: one name per mechanism, keyed by room stem plus evidence (`i<id>` the key item an item-use AOT asks for, `sw<bit>` a switch event, `nl<bit>` a number lock). Every named evidence cites public pages in `puzzle_sources` (Evil Resource item pages, Raccoon Insider room pages that carry the game's room IDs and examine texts, the BDennis FAQ); Korean puzzle names are project translations (`ko_basis`). Evidence without a name sits in `unresolved` with its reason and the marker stays unnamed; `extract_overlay.py` stops on evidence that is in neither list. `tests/test_marker_names.py` checks that every document has a Korean and English title and that the generated labels equal the table.

## Settings and keys

`tests/test_settings.py` checks the INI handling with an in-memory file system: `Version=2` (an older file keeps its values and is rewritten once with the new keys), atomic save through `RE2.AnnotatedMap.ini.tmp`, value clamping, `Modifier=Shift|Ctrl` and the 350 ms rest period per key. `LockSide=1` uses each door AOT's own destination (Door_aot_se bytes 14..25) projected by the native map code (`project_all.py other_side`).

## Icon editing

Shared icon rules (style, sizes, references, review): `../../common/icon-style-guide.md` (workspace root).


Key items draw their own art: 37 sprites in `assets/icons/key-<id>.png` are packed 1:1 by `assets/generate_key_art.py` into `src/key_art.h` (a second texture page, because the lock-icon page is full); the lock-icon sprites of `atlas.h` are reused for the other key items; items without art keep the cyan star. The art's longest side fills the star box and its aspect is kept (at least 2 px thick), and the item name touches the drawn art.
Prepared AI-assisted C-style sprites are in `assets/icons/`, and `assets/key-layout.json` places the lock icons on the atlas. The map icon, puzzle diamond and key star are code-drawn in `assets/generate_overlay_icons.py`. After editing, regenerate as above.

Lock icons use visible-texel atlas bounds and scale their longest side to approximately 7.5px; ordinary pickups/maps render at7px. Furniture/documents render at8px, puzzles at6px; all of these scale with `IconSize`. Map IDs200–205 are synthetic overlay identifiers and are never written into game inventory.

## Public scope and licensing

Project source is MIT-licensed; see LICENSE and NOTICE for the scope and third-party credits. Game assets and third-party components retain their own rights.

`[6]` events show one marker per floor: the next pending scene, first by ascending FG_COMMON done flag (the flags follow play order), drawn right after the key stars so key names steer around it; it moves to a free neighbouring spot if a star sits on it. A scene whose flag is set is done and the next appears; a scene whose room is unvisited holds back the later ones.
