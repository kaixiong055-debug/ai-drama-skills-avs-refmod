import re
import tempfile
import unittest
from pathlib import Path

from engine.common import GateError, load, save
from engine.delivery import export_user_project, export_delivery, resolve_project
from engine.speech import enforce_spoken_language, MANDARIN_RULE
from engine.validator import parse_md
from examples.fixtures import fixture, materialize


class SpokenLanguageTests(unittest.TestCase):
    def test_selective_verbatim_idempotent_and_explicit_other_language(self):
        silent = '【空间预热 LOCK_SC01_A01｜1秒】\nsubject_definitions:\nA room.\ndialogue_and_audio:\nNo dialogue.\n\n'
        chinese = '【视频片段 1｜5秒】\nsubject_definitions:\nA person.\ndetailed_description:\nGu: <d>[Chinese] 晚上见，室友。</d>\n\ndialogue_and_audio:\nB001; 1.0–2.5s; once.\n\n'
        english = '【视频片段 2｜5秒】\nsubject_definitions:\nA person.\ndetailed_description:\nGu: <d>[English] See you.</d>\n\ndialogue_and_audio:\nB002; 1.0–2.5s; once.\n'
        raw = silent + chinese + english
        for lang in ['cn', 'en']:
            fixed = enforce_spoken_language(raw, lang)
            self.assertEqual(fixed, enforce_spoken_language(fixed, lang))
            self.assertEqual(raw, fixed.replace(MANDARIN_RULE[lang] + '\n', ''))
            units = parse_md(fixed, 'cn')
            self.assertEqual(silent, units['LOCK_SC01_A01'])
            self.assertEqual(english, units['SEG002'])
            self.assertEqual(re.findall(r'<d>.*?</d>', raw), re.findall(r'<d>.*?</d>', fixed))
            self.assertIn(MANDARIN_RULE[lang], units['SEG001'].split('dialogue_and_audio:\n')[1])
        with self.assertRaisesRegex(GateError, 'DIALOGUE_AUDIO_SECTION_MISSING'):
            enforce_spoken_language(chinese.replace('dialogue_and_audio:\n', ''), 'en')

    def test_new_exports_full_runtime_and_legacy_draft(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            request = fixture(2)
            public = export_user_project(request, materialize(request, base / 'input'), base / 'public')
            internal = resolve_project(public)
            for lang in ['cn', 'en']:
                for prefix in ['H3_PROMPTS_FULL_', 'H3_RUNTIME_']:
                    raw = (internal / (prefix + lang.upper() + '.md')).read_text('utf-8')
                    units = parse_md(raw, lang)
                    self.assertTrue(units)
                    for uid, block in units.items():
                        if '<d>[Chinese]' in block:
                            self.assertIn(MANDARIN_RULE[lang], block)
                        else:
                            self.assertNotIn(MANDARIN_RULE[lang], block)
                # Simulate an existing project compiled before this fix.
                path = internal / ('H3_PROMPTS_FULL_' + lang.upper() + '.md')
                path.write_text(path.read_text('utf-8').replace(MANDARIN_RULE[lang] + '\n', ''), encoding='utf-8')
            review = load(internal / 'production_review.json')
            review['status'] = 'BLOCKED_MISSING_IMAGES'
            save(internal / 'production_review.json', review)
            draft = export_delivery(internal, base / 'legacy', allow_draft=True)
            for n, label, lang in [('04', '中文版', 'cn'), ('05', '英文版', 'en')]:
                text = (draft / f'{n}_H3一键提示词_{label}_待出图.md').read_text('utf-8')
                units = parse_md(text, 'cn')
                self.assertTrue(units)
                for block in units.values():
                    if '<d>[Chinese]' in block:
                        self.assertIn(MANDARIN_RULE[lang], block)
                original = (internal / ('H3_PROMPTS_FULL_' + lang.upper() + '.md')).read_text('utf-8')
                self.assertEqual(re.findall(r'<d>.*?</d>', original), re.findall(r'<d>.*?</d>', text))
            self.assertEqual(6, len(list(draft.glob('*.md'))))
            self.assertFalse(list(draft.rglob('*.json')))
