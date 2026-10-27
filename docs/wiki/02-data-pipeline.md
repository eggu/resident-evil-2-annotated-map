# 데이터 구성

[한국어](02-data-pipeline.md) | [English](02-data-pipeline.en.md) · [Index](README.md)

| 종류 | 파일 |
| --- | --- |
| 방 이름과 방 모양 | `data/room_names-*.json`, `data/room_shapes.json` |
| 잠긴 문 | `src/doors-all.h` |
| 아이템과 조건 | `src/items.h` |
| 문서·퍼즐·세이브 지점·잔여 아이템 | `src/overlay_data.h` |
| 몬스터 출현과 조건 | `src/monsters.h` |
| 한·영 이름과 렌더링 데이터 | `src/room_names-*.h`, `src/room_labels-*.h`, `src/item_labels-*.h` |
| 아이콘·방 채움·랭크 글자 | `src/atlas.h`, `src/overlay_icons.h`, `src/fill_masks.h`, `src/rank_glyphs.h` |

실행 중에는 캐릭터·게임 모드·현재 지도·방문 상태·획득/해제 플래그·조건식을 적용해 표시 여부를 결정합니다. A/B 시나리오 차이는 조건과 문 마스크에 반영됩니다.

빌드는 고정된 헤더를 컴파일합니다. JSON의 이름이나 좌표만 바꿔도 렌더링 헤더가 자동 갱신되지는 않습니다. 이 위키의 표는 `python3 tools/gen_wiki.py`로 해당 헤더에서 다시 생성합니다. 게임 파일은 필요하지 않습니다.

[빌드 안내](../DEVELOPMENT.md)
