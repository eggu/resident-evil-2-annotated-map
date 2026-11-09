"""Names of document and puzzle markers, from data/marker_names.json (documents: the game's own file titles, see
extract_file_titles.py; puzzles: one name per mechanism, see the table's basis)."""
from pathlib import Path
import json

_HERE = Path(__file__).resolve().parent
_TABLE = next(p for p in (_HERE / 'marker_names.json', _HERE.parents[1] / 'data/marker_names.json') if p.is_file())
TABLE = json.loads(_TABLE.read_text())
DOCUMENTS = {int(i): (d['en'], d['ko']) for i, d in TABLE['documents'].items()}
ITEMS_KO = {int(i): d['ko'] for i, d in TABLE['item_names_ko'].items()}  # the game's own Korean item names (korean_hd.bin)
PUZZLES = {int(i): (p['en'], p['ko']) for i, p in TABLE['puzzle_names'].items()}
RULES = {tuple(k.split(':')): int(v) for k, v in TABLE['puzzle_rules'].items()}
UNRESOLVED = {tuple(k.split(':')): reason for k, reason in TABLE['unresolved'].items()}


def puzzle_name_id(evidence):
    """evidence: {(room stem, token)} of every AOT drawn at one marker; the name id, or 0 unless all of it agrees."""
    ids = {RULES.get(e, 0) for e in evidence}
    return ids.pop() if len(ids) == 1 else 0
