# Native map and visibility

[한국어](01-native-map.md) | [English](01-native-map.en.md) · [Index](README.en.md)

Press `8` to cycle Visited → Revealed → All. Revealed requires the acquired floor-map flag and the room's scenario visibility mask. All removes the room-visit gate; it does not restore collected items or completed events.

On the status-screen map, left/right selects an area and up/down selects a floor. Only visited floors are selectable, without wraparound. All scope does not add unvisited floors to the selection list.

| Area | Map IDs, top to bottom |
| --- | --- |
| City | 0, 1 |
| Police station | 4, 3, 2, 5, 6 |
| Sewers | 7, 8 |
| Factory | 9, 10, 11, 12 |
| Laboratory | 13, 14, 15, 16, 17 |
| Train | 18, 19 |

| Character | Map ID | Resource | Room slots |
| --- | --- | --- | --- |
| Leon | 0 | map00 | 8 |
| Leon | 1 | map01 | 4 |
| Leon | 2 | map10 | 18 |
| Leon | 3 | map02 | 15 |
| Leon | 4 | map03 | 3 |
| Leon | 5 | map11 | 11 |
| Leon | 6 | map20 | 11 |
| Leon | 7 | map30 | 6 |
| Leon | 8 | map31 | 13 |
| Leon | 9 | map40 | 4 |
| Leon | 10 | map41 | 3 |
| Leon | 11 | map42 | 3 |
| Leon | 12 | map43 | 2 |
| Leon | 13 | map50 | 6 |
| Leon | 14 | map51 | 1 |
| Leon | 15 | map52 | 1 |
| Leon | 16 | map53 | 13 |
| Leon | 17 | map54 | 7 |
| Leon | 18 | map60 | 6 |
| Leon | 19 | map61 | 2 |
| Claire | 0 | map00 | 8 |
| Claire | 1 | map01 | 4 |
| Claire | 2 | map10 | 18 |
| Claire | 3 | map02 | 15 |
| Claire | 4 | map03 | 3 |
| Claire | 5 | map11 | 11 |
| Claire | 6 | map20 | 11 |
| Claire | 7 | map30 | 6 |
| Claire | 8 | map31 | 13 |
| Claire | 9 | map40 | 4 |
| Claire | 10 | map41 | 3 |
| Claire | 11 | map42 | 3 |
| Claire | 12 | map43 | 2 |
| Claire | 13 | map50 | 6 |
| Claire | 14 | map51 | 1 |
| Claire | 15 | map52 | 1 |
| Claire | 16 | map53 | 13 |
| Claire | 17 | map54 | 7 |
| Claire | 18 | map60 | 6 |
| Claire | 19 | map61 | 2 |

Names and markers are overlaid on the native map. Rooms with remaining items receive an orange tint. Name/leader opacity is independent of icons, legend and rank.

## Native data reference

Addresses refer to the supported PC executable. Display resolution is separate from logical map coordinates.

| Address | Meaning |
| --- | --- |
| `0x691f7a` | Displayed map ID |
| `0x691fb8 / 0x691fba` | Map pan x/y (signed short) |
| `0x98ec00` | Visited-floor bits |
| `0x98ec04` | Room-visit bits |
| `0x98ec1c` | Acquired floor-map bits |
| `0x98ed2c` | Door-unlock bits |
| `0x53eaf8 / 0x53eb98` | Leon/Claire floor tables |
| `0x53b218` | SCD flag-bank pointer table |
