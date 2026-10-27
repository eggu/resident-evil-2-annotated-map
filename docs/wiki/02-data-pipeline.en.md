# Data pipeline

[한국어](02-data-pipeline.md) | [English](02-data-pipeline.en.md) · [Index](README.en.md)

| Data | File |
| --- | --- |
| Room names and shapes | `data/room_names-*.json`, `data/room_shapes.json` |
| Locked doors | `src/doors-all.h` |
| Items and conditions | `src/items.h` |
| Documents, puzzles, save points and remaining pickups | `src/overlay_data.h` |
| Monster spawns and conditions | `src/monsters.h` |
| Bilingual labels and rendering data | `src/room_names-*.h`, `src/room_labels-*.h`, `src/item_labels-*.h` |
| Icons, room fills and rank glyphs | `src/atlas.h`, `src/overlay_icons.h`, `src/fill_masks.h`, `src/rank_glyphs.h` |

At runtime, character, game mode, current map, visit state, collection/unlock flags and guard conditions determine visibility. Scenario A/B differences are encoded in guards and door masks.

Builds compile pinned headers. Editing JSON names or coordinates alone does not regenerate the rendered headers. Regenerate these wiki tables from the headers with `python3 tools/gen_wiki.py`; no game files are needed.

[Build documentation](../DEVELOPMENT.md)
