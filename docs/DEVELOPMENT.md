# Development and verification

This repository contains the RE2 annotated-map mod. The release ZIP installs `scripts/RE2.AnnotatedMap.asi` with its commented default INI and bundles Ultimate ASI Loader as `dsound.dll`; settings and the log are written beside the ASI. It does not contain game executables, RDT files, original item atlases, saves, Wine wrappers, translation patches, cutscene patches, or historical diagnostics.

## Build inputs

`src/re2_keymap.c` is the runtime source. The remaining headers are the pinned current generated map/label/icon data. The bilingual label texture headers contain text rasterized with the open-source Pretendard fonts in `fonts/` (Korean labels SemiBold, English labels and legend Medium); release builds must not use proprietary system fonts. No font is needed to compile. `data/room_names-*.json` and `data/room_shapes.json` document editable names and map geometry; editing these alone does not regenerate the pinned headers. The repository builds from pinned headers. Full extraction and text-label regeneration tools are not included.

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

## Icon editing

Prepared AI-assisted C-style sprites are in `assets/icons/`. The map icon and flat amber puzzle diamond are code-drawn in `assets/generate_overlay_icons.py`.

```sh
python -m pip install -r requirements-assets.txt
python assets/generate_atlas.py
python assets/generate_overlay_icons.py
cp assets/atlas.h assets/overlay_icons.h src/
python build.py --game-exe '/path/to/Resident Evil 2.exe'
```

Generated asset previews and temporary headers are ignored. Lock icons use visible-texel atlas bounds and scale their longest side to approximately 7.5px; ordinary pickups/maps render at7px. Furniture/documents render at8px, puzzles at6px. Map IDs200–205 are synthetic overlay identifiers and are never written into game inventory.

## Public scope and licensing

Project source is MIT-licensed; see LICENSE and NOTICE for the scope and third-party credits. Game assets and third-party components retain their own rights.
