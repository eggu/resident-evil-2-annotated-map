"""Document and puzzle marker names, stdlib only; run from the repository root. Game-dependent checks live in
tools/mapgen: extract_file_titles.py (title bitmaps match the game files) and extract_overlay.py (every puzzle
evidence is named or listed as unresolved), both run by regen.py."""
import json, re, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TABLE = json.loads((ROOT / 'data/marker_names.json').read_text())


def rows(text, name):
    body = text.split(name + '[] = {', 1)[1].split('};', 1)[0]
    return [tuple(int(v) for v in r.split(',')) for r in re.findall(r'^\{([^}]*)\},', body, re.M)]


def labels(lang):
    out = {}
    for item, text in re.findall(r'\{(\d+),[^}]+\}, /\* \S+ (.*?) \*/', (ROOT / f'src/item_labels-{lang}.h').read_text()):
        out.setdefault(int(item), []).append(text)
    return out


def unresolved_reasons():
    return TABLE['unresolved'].values()


def korean_display(name, official=False):  # generate_item_labels.display_lines: 'A의 B' drops the particle after a 2+ syllable stem,
    return name if official else re.sub(r'(\S{2,})의 ', r'\1 ', name)  # except in official document names


class MarkerNames(unittest.TestCase):
    overlay = (ROOT / 'src/overlay_data.h').read_text()

    def test_every_document_has_ko_and_en_title(self):
        self.assertEqual(sorted(map(int, TABLE['documents'])), list(range(106, 127)))
        for i, d in TABLE['documents'].items():
            self.assertTrue(d['en'] and d['ko'] and d['file'] == f'file{int(i) - 104:02x}', i)
            self.assertEqual(set(d['bitmap']), {'ko', 'en'})
            self.assertTrue(all(len(b['sha256']) == 64 for b in d['bitmap'].values()))
            self.assertEqual(bool(d.get('ko_flag')), d['ko_reading_uncertain'], i)

    def test_document_names_come_from_the_game_not_the_page_titles(self):
        """The Files-list name differs from the first-page title (user 2026-11-07): the game's EXE item-name table gives
        the English name, the Korean HD patch's name table (korean_hd.bin) the Korean one."""
        confirmed = {'119': '경비원의 일기', '124': '백신 합성 기록'}
        for i, d in TABLE['documents'].items():
            self.assertEqual(d['en_source']['file'], 'Resident Evil 2.exe')
            self.assertRegex(d['en_source']['offset'], r'^0x12[ef][0-9a-f]{3}$', i)
            self.assertEqual(len(d['en_source']['sha256']), 64)
            self.assertTrue(d['en_title'] and d['ko_title'], i)
            self.assertEqual(d['ko_source']['file'], 'korean_hd.bin')
            self.assertEqual(len(d['ko_source']['sha256']), 64)
            self.assertFalse(d['ko_reading_uncertain'], i)
            if i in confirmed: self.assertEqual(d['ko'], confirmed[i])
        glyphs = TABLE['ko_glyphs']  # every Hangul of a document name is a recorded cell reading
        for i, d in TABLE['documents'].items():
            hangul = [c for c in d['ko'] if '가' <= c <= '힣']
            cells = [g for k, g in glyphs.items() if g['first_seen'] == int(i)]
            self.assertTrue(set(hangul) >= {g['syl'] for g in cells}, i)
        self.assertEqual({g['basis'] for g in glyphs.values()}, {'patch G table', 'user-confirmed name', 'read by eye', 'read by eye (checked against the item name)'})
        self.assertEqual(TABLE['documents']['119']['en'], "Watchman's diary")
        self.assertEqual(TABLE['documents']['124']['en'], 'Vaccine synthesis')

    def test_item_labels_use_the_games_korean_item_names(self):
        """Full-data check (user 2026-11-08): every item with a name in the Korean HD patch's table is labelled with that name
        (not the project's translation), and the table rows carry their record offset and SHA-256."""
        got = labels('ko')
        self.assertTrue(len(TABLE['item_names_ko']) >= 70)
        for i, d in TABLE['item_names_ko'].items():
            self.assertEqual(d['source']['file'], 'korean_hd.bin'); self.assertEqual(len(d['source']['sha256']), 64)
            if int(i) in got:
                tag = '[Z] ' if d['ko_project'].startswith('[Z] ') else ''
                text = ' '.join(got[int(i)])  # a lock key has a second (lock-colour) copy of its name
                self.assertIn(text, (tag + d['ko'], tag + d['ko'] + ' ' + tag + d['ko']), (i, d['ko'], got[int(i)]))
        self.assertEqual(TABLE['item_names_ko']['38']['ko'], '초록 허브')  # the reported mismatch: not '허브 (녹색)'
        self.assertEqual(TABLE['item_names_ko']['39']['ko'], '빨간 허브')
        self.assertEqual(TABLE['item_names_ko']['40']['ko'], '파란 허브')

    def test_official_document_names_keep_the_particle(self):
        """Document names are official game names: the Korean '의' removal (puzzle/item names) must not touch them."""
        self.assertEqual(TABLE['documents']['119']['ko'], '경비원의 일기')
        self.assertEqual(' '.join(labels('ko')[119]), '경비원의 일기')
        self.assertEqual(' '.join(labels('ko')[121]), '하수도 관리자의 일기')
        self.assertEqual(korean_display('경비원의 일기'), '경비원 일기')  # the rule still applies to other names
        self.assertEqual(korean_display('경비원의 일기', official=True), '경비원의 일기')

    def test_flagged_puzzles_cite_game_data_and_map_room_names(self):
        """Low-confidence and unresolved puzzles are reported by the room names the map draws (user cannot read room
        numbers), each with what the RDT scripts prove."""
        ko = json.loads((ROOT / 'data/room_names-ko.json').read_text()); en = json.loads((ROOT / 'data/room_names-en.json').read_text())
        for group in ('low_confidence', 'unresolved_game_data'):
            for evidence, row in TABLE[group].items():
                room = evidence.split(':')[0]
                self.assertEqual((row['room_ko'], row['room_en']), (ko[room], en[room]), evidence)
                self.assertTrue(len(row['game_data']) > 40, evidence)
        self.assertEqual(set(TABLE['unresolved_game_data']), set(TABLE['unresolved']))
        self.assertTrue(set(TABLE['low_confidence']) <= set(TABLE['puzzle_rules']))

    def test_drawn_documents_and_puzzles_are_labelled_from_the_table(self):
        docs = {r[4] for r in rows(self.overlay, 'map_documents')}
        named = {r[8] for r in rows(self.overlay, 'map_interactions') if r[8]}
        self.assertTrue(docs and named)
        for lang, col in (('en', 'en'), ('ko', 'ko')):
            got = labels(lang)
            for i in docs:
                title = TABLE['documents'][str(i)][col]
                self.assertEqual(' '.join(got[i]), title, (lang, i))  # official names: no '의' removal
            for i in named:
                title = TABLE['puzzle_names'][str(i)][col]
                self.assertEqual(' '.join(got[i]), korean_display(title) if lang == 'ko' else title, (lang, i))

    def test_puzzle_rules_and_unresolved_list_are_consistent(self):
        rules, unresolved = set(TABLE['puzzle_rules']), set(TABLE['unresolved'])
        self.assertFalse(rules & unresolved)
        self.assertTrue(all(str(v) in TABLE['puzzle_names'] for v in TABLE['puzzle_rules'].values()))
        self.assertTrue(all(p['basis'] and p['en'] and p['ko'] for p in TABLE['puzzle_names'].values()))
        self.assertTrue(all(p['ko_basis'] == 'project translation' for p in TABLE['puzzle_names'].values()))
        self.assertEqual(set(TABLE['puzzle_sources']), rules)  # every named evidence cites at least one public page
        self.assertTrue(all(urls and all(u.startswith('https://') for u in urls) for urls in TABLE['puzzle_sources'].values()))
        self.assertTrue(all(len(reason) > 20 for reason in unresolved_reasons()))
        used = {str(r[8]) for r in rows(self.overlay, 'map_interactions') if r[8]}
        self.assertEqual(used, set(TABLE['puzzle_names']))  # no name without a drawn marker

    def test_source_is_recorded(self):
        src = TABLE['documents_source']
        self.assertEqual(len(src['exe_sha256']), 64)
        self.assertTrue(src['extracted'] and src['method'])
        self.assertEqual(len(src['files']), 42)


if __name__ == '__main__':
    unittest.main()
