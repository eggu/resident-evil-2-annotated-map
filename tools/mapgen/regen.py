#!/usr/bin/env python3
"""Regenerate the pinned map headers from a legally owned game install. Nothing is installed or launched.

  python tools/mapgen/regen.py --game '/path/to/Resident Evil 2'           # compare with src/ and tests/fixtures/
  python tools/mapgen/regen.py --game '/path/to/Resident Evil 2' --write   # and update them

Game-derived intermediates stay in build/regen/, which is ignored by Git."""
from pathlib import Path
import argparse, importlib, json, os, re, shutil, subprocess, sys

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / 'build/regen'
EN = WORK / 'english'
OUT = WORK / 'bilingual'
STEPS = ('decode_maps.py', 'extract_all.py', 'extract_items.py', 'extract_overlay.py', 'project_all.py', 'generate_overlay_icons.py',
         'generate_atlas.py', 'generate_key_art.py', 'generate_fill_masks.py', 'generate_rank_glyphs.py', 'extract_monsters.py')
HEADERS = ('atlas.h', 'key_art.h', 'items.h', 'doors-all.h', 'overlay_data.h', 'overlay_icons.h', 'fill_masks.h', 'rank_glyphs.h', 'monsters.h')
LABELS = (('room_names', {'RoomName': 'RoomName', 'room_names': 'room_names'}),
          ('room_labels', {'RoomLabel': 'RoomLabel', 'ROOM_LABEL_PAGE_COUNT': 'ROOM_LABEL_PAGE_COUNT', 'ROOM_LABEL_SCALE': 'ROOM_LABEL_SCALE',
                           'ROOM_LABEL_COUNT': 'ROOM_LABEL_COUNT', 'ROOM_HELP_LABEL_COUNT': 'ROOM_HELP_LABEL_COUNT', 'ROOM_READOUT_W': 'ROOM_READOUT_W', 'ROOM_HELP_LABEL': 'ROOM_HELP_LABEL',
                           'room_labels': 'room_labels', 'room_label_pixels': 'room_label_pixels', 'room_help_icon_x': 'room_help_icon_x', 'RE2_ROOM_LABELS_H': 'RE2_ROOM_LABELS_H'}),
          ('item_labels', {'ItemLabel': 'ItemLabel', 'ITEM_LABEL_PAGE_COUNT': 'ITEM_LABEL_PAGE_COUNT', 'ITEM_LABEL_COUNT': 'ITEM_LABEL_COUNT',
                           'item_labels': 'item_labels', 'item_label_pixels': 'item_label_pixels', 'RE2_ITEM_LABELS_H': 'RE2_ITEM_LABELS_H'}))


def prepare(game):
    shutil.rmtree(WORK, ignore_errors=True)
    EN.mkdir(parents=True); OUT.mkdir()
    for folder in (ROOT / 'tools/mapgen', ROOT / 'data'):
        for p in folder.iterdir():
            if p.is_file():
                shutil.copy2(p, WORK / p.name)
    for name in ('generate_atlas.py', 'generate_key_art.py', 'key-art-provenance.json', 'generate_overlay_icons.py', 'pixel_icons.py', 'key-layout.json'):
        shutil.copy2(ROOT / 'assets' / name, WORK / name)
    shutil.copytree(ROOT / 'assets/icons', WORK / 'icons')
    shutil.copytree(ROOT / 'fonts', WORK / 'fonts')
    shutil.copy2(WORK / 'room_names-en.json', EN / 'room_names-en.json')
    # decode_maps rebuilds room_shapes.json and takes each room's identity from the last provenance.
    shutil.copy2(ROOT / 'tests/fixtures/korean-assets/room_names-provenance.json', WORK / 'room_names-provenance.json')
    os.environ['RE2_GAME'] = str(game)
    sys.path.insert(0, str(WORK))


def renamed(path, out, suffix, mapping):
    text = path.read_text()
    for old in sorted(mapping, key=len, reverse=True):
        text = re.sub(r'\b' + old + r'\b', mapping[old] + '_' + suffix.upper(), text)
    out.write_text(text)


def generate(game):
    for step in STEPS:
        subprocess.run([sys.executable, '-B', step], cwd=WORK, check=True, stdout=subprocess.DEVNULL)
    subprocess.run([sys.executable, '-B', 'extract_file_titles.py'], cwd=WORK, check=True)  # document titles still match the game files
    subprocess.run([sys.executable, '-B', 'extract_doc_names.py'], cwd=WORK, check=True)  # document names still match the EXE item-name table
    subprocess.run([sys.executable, '-B', 'extract_ko_doc_names.py'], cwd=WORK, check=True)  # Korean names still match korean_hd.bin
    shutil.copy2(WORK / 'items.h', EN / 'items.h')
    shutil.copy2(WORK / 'overlay_data.h', EN / 'overlay_data.h')
    shutil.copy2(WORK / 'doors-all.h', EN / 'doors-all.h')
    shutil.copy2(WORK / 'room_shapes.json', EN / 'room_shapes.json')
    rooms = importlib.import_module('generate_room_names')
    for folder, language, names, px, stroke, font in ((WORK, 'Korean', 'room_names-ko.json', 24, 3, rooms.FONT_KO), (EN, 'English', 'room_names-en.json', 20, 2, rooms.FONT_EN)):
        rooms.R, rooms.G, rooms.LANGUAGE, rooms.ROOM_NAMES_FILE = folder, game, language, names
        rooms.FONT_PX, rooms.STROKE, rooms.FONT = px, stroke, font
        rooms.generate()
    items = importlib.import_module('generate_item_labels')
    items.R, items.NAMES = WORK, importlib.import_module('extract_items').NAMES
    items.generate()
    items.R, items.NAMES = EN, importlib.import_module('item_names_en').ITEM_EN
    items.FONT, items.FONT_PX = rooms.FONT_EN, rooms.FONT_PX
    items.LANG = 'en'
    items.generate()
    includes = []
    for stem, mapping in LABELS:
        for suffix, folder in (('ko', WORK), ('en', EN)):
            renamed(folder / f'{stem}.h', OUT / f'{stem}-{suffix}.h', suffix, mapping)
            includes.append(f'#include "{stem}-{suffix}.h"')
    (OUT / 'bilingual_assets.h').write_text('\n'.join(includes) + '\n')
    for name in HEADERS:
        shutil.copy2(WORK / name, OUT / name)


def targets():
    """generated file -> tracked file"""
    pairs = {OUT / p.name: p for p in (ROOT / 'src').iterdir() if (OUT / p.name).exists()}
    pairs[WORK / 'room_shapes.json'] = ROOT / 'data/room_shapes.json'
    pairs[WORK / 'events-report.json'] = ROOT / 'data/events_report.json'
    for name in ('room_names.h', 'room_labels.h', 'item_labels.h', 'room_names-provenance.json'):
        pairs[EN / name] = ROOT / 'tests/fixtures' / name
        pairs[WORK / name] = ROOT / 'tests/fixtures/korean-assets' / name
    return pairs


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--game', type=Path, required=True, help='Folder holding Resident Evil 2.exe and Pl0/Pl1')
    parser.add_argument('--write', action='store_true', help='Update src/ and tests/fixtures/ with the generated files')
    args = parser.parse_args()
    game = args.game.resolve()
    if not (game / 'Resident Evil 2.exe').is_file():
        parser.error(f'Resident Evil 2.exe not found in {game}')
    prepare(game)
    generate(game)
    pairs = targets()
    changed = [dst for src, dst in pairs.items() if src.read_bytes() != dst.read_bytes()]
    for dst in changed:
        print('changed:', dst.relative_to(ROOT))
    print(f'{len(pairs) - len(changed)} of {len(pairs)} files identical')
    if args.write:
        for src, dst in pairs.items():
            shutil.copy2(src, dst)
    elif changed:
        sys.exit(1)


if __name__ == '__main__':
    main()
