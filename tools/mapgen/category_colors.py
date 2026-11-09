"""One RGB per marker category: the legend rows (generate_room_names.HELP_RGB) and the marker names (generate_item_labels)
both read it, so a row and its names can never differ. Name categories double as ItemLabel.cat in item_labels.h."""
KEY, LOCK, PUZZLE, DOCUMENT, COMMON, EVENT = range(6)  # ItemLabel.cat; re2_keymap.c LABEL_* use the same numbers
ROOMS = (240, 226, 190)
MONSTERS = (235, 60, 60)
OFF = (106, 106, 106)  # disabled legend rows, darker grey #6A6A6A (user 2026-11-08)
NAME_RGB = {
    KEY: (90, 220, 255),
    LOCK: (255, 205, 70),
    PUZZLE: (255, 150, 40),
    DOCUMENT: (255, 140, 210),  # documents and area maps ([4] legend row)
    COMMON: (184, 188, 196),    # cool grey #B8BCC4, user 2026-11-08 (RGB555 23,23,24); was lavender #B4A7D6
    EVENT: (176, 112, 255),     # event purple #B070FF as in the RE0 HD map mod
}
