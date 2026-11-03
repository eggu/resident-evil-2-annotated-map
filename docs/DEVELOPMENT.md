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

Room names are placed when the headers are generated (`generate_room_names.py`) and never move at runtime. Key-item names are placed at runtime (`src/re2_keymap.c`).

Priority:

- Key-item stars and names are never covered. Common items and enemies may be covered or hidden.
- Room names never overlap key items or markers: save points, item boxes, documents, area maps, locks and puzzles. They may cover common items and enemies.

Room names (`place_labels`):

- Tightest rooms choose first. A name stays inside its room when it fits on the room's own mask, checked at 2 px, 1 px and no wall margin, then at 80% size.
- Otherwise the name sits outside on an axis-aligned leader line that starts on a mask pixel of its own room: first the shortest line into free space (`near_spot`), then a fallback outside the floor's bounding box, which may cross another room at a right angle.
- Leaders never share a line with a room outline (`along_outline`): they start at least 3 px from their own room's corners (narrow rooms use their centre), and no wall lies within 2 px beside them.
- Leaders never run through another room name, and outside names never overlap a room mask. The generator asserts these checks and stops on a violation.
- Multi-word names that do not fit are wrapped between words only.

Key-item names (`item_label_draw`, `place_at`):

- A name touches its star with no gap: right, left, below, above, then below or above running from the star's edge. The candidate with the least weighted overlap wins: stars, diamonds and the legend count 8x, room names 4x, other markers 1x.
- A lower-priority icon overlapping a key star, key name or puzzle diamond is not drawn. An area map or lock centred on a star or diamond is drawn as a badge 3 px down and right instead.

`tests/test_label_priority.py` and `tests/test_map_geometry.py` check these rules. Translucent names render below every opaque quad, so draw order alone cannot put a name over an icon.

## Icon editing

Prepared AI-assisted C-style sprites are in `assets/icons/`, and `assets/key-layout.json` places the lock icons on the atlas. The map icon, puzzle diamond and key star are code-drawn in `assets/generate_overlay_icons.py`. After editing, regenerate as above.

Lock icons use visible-texel atlas bounds and scale their longest side to approximately 7.5px; ordinary pickups/maps render at7px. Furniture/documents render at8px, puzzles at6px. Map IDs200–205 are synthetic overlay identifiers and are never written into game inventory.

## Public scope and licensing

Project source is MIT-licensed; see LICENSE and NOTICE for the scope and third-party credits. Game assets and third-party components retain their own rights.
