# RE2 Annotated Map Wiki

[한국어](README.md) | [English](README.en.md) · [Index](README.en.md)

Reference for the map features and data in the original Resident Evil 2 (1998) PC mod. Tables reveal progression information and unexplored locations. Use the default Visited scope in game if you prefer to avoid spoilers.

| Page | Contents |
| --- | --- |
| [Native map and visibility](01-native-map.en.md) | Native map and visibility |
| [Data pipeline](02-data-pipeline.en.md) | Data pipeline |
| [Rooms](03-rooms.en.md) | Rooms |
| [Locked doors and keys](04-locks-keys.en.md) | Locked doors and keys |
| [Key items](05-key-items.en.md) | Key items |
| [Puzzles and devices](06-puzzles.en.md) | Puzzles and devices |
| [Documents and maps](07-documents-maps.en.md) | Documents and maps |
| [Common items](08-common-items.en.md) | Common items |
| [Typewriters and item boxes](09-save-points.en.md) | Typewriters and item boxes |
| [Sources and licenses](10-sources.en.md) | Sources and licenses |
| [Monsters](11-monsters.en.md) | Monsters |
| [Rank and settings](12-rank-settings.en.md) | Rank and settings |

## Reading the tables

- Map IDs are the mod's indices 0–19, not floor names or display resolutions.
- `seen` is a room-visit flag index, separate from a room code. Unmapped slots retain their numeric identifier.
- Conditions `bank:bit=value` describe flag truth values. All conditions joined by `∧` must pass. Banks 130/131 compare SCD variables 0x1e/0x1f: `130:n=1` means equal to n, and `130:n=0` means unequal.
- A location may have multiple scenario, item or event variants. Row counts are not unique item counts or simultaneous marker counts.
- Coordinates are logical source-map coordinates before panning and marker-centre offsets, not PC output pixels.

[Installation and controls](../../README.en.md) · [Credits](../../NOTICE.md)
