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
- **Leon B transport sequence**: checked against Brandon W. Dennis's Resident Evil 2 FAQ (1998),
  https://gamefaqs.gamespot.com/ps/198458-resident-evil-2/faqs/4110 . No FAQ text is included.
- **Monster icons**: pixel art drawn for this mod; Evil Resource (https://www.evilresource.com) Resident Evil 2 images
  were used as visual reference only. The site's images are not included.
- **Item, ammunition, recovery, Ink Ribbon, furniture and document sprites**: AI-assisted artwork prepared for this mod
  from game object identities and a retro pixel-art style. Provenance and extraction hashes are in
  `assets/artwork-provenance.json`. The folded map icon and amber puzzle diamond are code-drawn in
  `assets/generate_overlay_icons.py`.
- **Fonts**: map labels and the legend are rasterized with Pretendard (SIL Open Font License 1.1, Copyright (c) 2021
  Kil Hyung-jin, https://github.com/orioncactus/pretendard v1.3.9): SemiBold for Korean labels, Medium for English
  labels and the legend. The font files and license are in `fonts/` for regeneration; the release ZIP contains only
  rendered pixels, no font file.
- **Ultimate ASI Loader** v9.7.4 (MIT, Copyright (c) 2023 ThirteenAG): the release ZIP includes its unmodified x86
  `dinput8.dll` renamed to `dsound.dll`, with its license in `scripts/UltimateASILoader-LICENSE.txt`.
  https://github.com/ThirteenAG/Ultimate-ASI-Loader
- **Build and test tools**: Zig (via `ziglang`), Unicorn and Pillow are installed separately under their own licenses.
