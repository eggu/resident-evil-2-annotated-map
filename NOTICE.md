# Notice

This project's source code is released under the [MIT License](LICENSE). It covers only this repository's own code,
data and documentation.

- **Resident Evil / Biohazard** and related names, characters, item designs and game data are trademarks and
  copyrighted works of Capcom Co., Ltd. This is an unofficial fan mod, not affiliated with or endorsed by Capcom, GOG or
  the Classic REbirth project. No game executable, room scripts, original textures, audio or proprietary font files are included.
  Map positions, room shapes, pickup/unlock flags and scenario facts were analyzed from a legally installed PC game;
  only derived overlay tables are included.
- **Room names**: reference retained from the original label tooling,
  https://coregamers.com/walkthrough/resident-evil-2-8 . The included English and Korean names were edited for this
  project.
- **Document titles** (`data/marker_names.json`): the titles of the game's own files, read from the installed game's file bitmaps (English original; Korean from the installed Korean HD patch). Only the derived title text and bitmap hashes are included.
- **Leon B transport sequence**: checked against Brandon W. Dennis's Resident Evil 2 FAQ (1998),
  https://gamefaqs.gamespot.com/ps/198458-resident-evil-2/faqs/4110 . No FAQ text is included.
- **Enemy icons**: AI-assisted pixel art prepared for this mod (ChatGPT image generation, then reduced to 16-colour
  sprites); Evil Resource (https://www.evilresource.com) Resident Evil 2 images were used as visual reference only. The site's images are not included.
- **Key-item sprites** (`assets/icons/key-<id>.png`, 37 items without lock-icon art): AI-assisted pixel art made for this mod with the
  Codex image tool (2026-11-09, third set; the text-only first set and the second set were superseded), reduced to at most 16 colours;
  prompts, processing and hashes are in `assets/key-art-provenance.json`. The game's own inventory images were looked at as
  references only and are not included or traced. No game or third-party image pixels are in the sprites.
- **Lock/key sprites** (items 31, 52, 62, 75, 88, 89, 90, 91, 92, 95, 98): redrawn on 2026-11-09 with the Codex image tool against the game's own
  inventory images (looked at as references only, never included or traced) and reduced to at most 16 colours; they replace the earlier
  October sprites drawn from item names. 64 px masters are in `assets/icons/masters/`; prompts and hashes are in the `redraws` section of
  `assets/artwork-provenance.json`.
- **Item, ammunition, recovery, Ink Ribbon, furniture and document sprites**: AI-assisted artwork prepared for this mod
  from game object identities and a retro pixel-art style. Provenance and extraction hashes are in
  `assets/artwork-provenance.json`. The folded map icon and amber puzzle diamond are code-drawn in
  `assets/generate_overlay_icons.py`.
- **Fonts**: map labels and the legend are rasterized with Pretendard (SIL Open Font License 1.1, Copyright (c) 2021
  Kil Hyung-jin, https://github.com/orioncactus/pretendard v1.3.9): SemiBold for Korean labels, Medium for English
  labels and the legend. The font files and license are in `fonts/` for regeneration; the release ZIP contains only
  rendered pixels, no font file.
  In SD mode (no HD pack) the labels use Galmuri9 by quiple (SIL Open Font License 1.1, https://github.com/quiple/galmuri);
  `fonts/Galmuri9.ttf` and `fonts/Galmuri-OFL.txt`; the ZIP again holds only rendered pixels.
- **Ultimate ASI Loader** v9.7.4 (MIT, Copyright (c) 2023 ThirteenAG): the release ZIP includes its unmodified x86
  `dinput8.dll` renamed to `dsound.dll`, with its license in `scripts/UltimateASILoader-LICENSE.txt`.
  https://github.com/ThirteenAG/Ultimate-ASI-Loader
- **Script opcode sizes** (`tools/mapgen/opcode-sizes.json`): from the constant table in [biohazard-utils](https://github.com/biorand/biohazard-utils) (MIT).
- **Build and test tools**: Zig (via `ziglang`), Unicorn and Pillow are installed separately under their own licenses.
