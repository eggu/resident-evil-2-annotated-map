# Rank and settings

[한국어](12-rank-settings.md) | [English](12-rank-settings.en.md) · [Index](README.en.md)

Enable the rank estimate with `Rank=1` under `[MapOverlay]` and restart the game. It changes with elapsed time, saves, First Aid Spray use and the infinite-weapon flag; it is not a guaranteed final result. It is hidden in Easy and bonus modes.

Score = time points + save points + spray points − infinite-weapon penalty, clamped at zero.

- Time: 100 through 2h30m, then minus 10 per started additional hour, minimum zero.
- Saves: `100−5×count` for 0–19; zero from 20. The new-game sentinel counts as zero saves.
- Sprays: `100−15×count` for 0–5; zero from 6.
- Subtract 50 when the infinite-weapon flag is set.

| Rank | Score |
| --- | --- |
| A | 269–300 |
| B | 199–268 |
| C | 144–198 |
| D | 99–143 |
| E | 0–98 |

## Settings

Settings are stored in `scripts/RE2.AnnotatedMap.ini`. In-game changes are saved automatically. Name size ranges from 50–150% and opacity from 10–100%, in 10% steps. Enlarged names may overlap on crowded maps.

[All defaults and controls](../../README.en.md)
