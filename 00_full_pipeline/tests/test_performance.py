import re
import tempfile
import unittest
from pathlib import Path

from engine.common import bi, GateError
from engine.pipeline import compile_project
from engine.runtime import render_runtime_pack
from engine.performance import apply_performance, shot_performance, BASELINE
from engine.validator import parse_md
from examples.fixtures import fixture, materialize


class PerformanceTests(unittest.TestCase):
    def test_authored_acting_survives_full_and_runtime_without_changing_dialogue(self):
        with tempfile.TemporaryDirectory() as td:
            request = fixture(2)
            note = bi('听完后眼尾放松，嘴角收住笑意；原停顿内轻眨一次眼。',
                      'After listening, soften the eye corners and contain the smile; blink once in the existing pause.')
            request['segments'][0]['shots'][0]['performance'] = note
            docs, full = compile_project(request, materialize(request, Path(td) / 'assets'))
            plans = docs['05_storyboard.json']['segments']
            self.assertEqual(note, plans[0]['shots'][0]['performance'])
            for pack in [full, render_runtime_pack(docs)]:
                for lang in ['cn', 'en']:
                    key = next(k for k in pack if k.endswith('_' + lang.upper() + '.md'))
                    raw = pack[key]
                    self.assertEqual(raw, apply_performance(raw, plans, lang))
                    units = parse_md(raw, lang)
                    self.assertIn(note[lang], units['SEG001'])
                    self.assertEqual(1, units['SEG001'].count(note[lang]))
                    for uid, block in units.items():
                        if uid.startswith('LOCK_'):
                            self.assertNotIn(BASELINE[lang], block)
                    lines = re.findall(r'<d>\[Chinese\]\s*(.*?)</d>', raw)
                    self.assertEqual([b['dialogue'] for b in request['beats'] if b.get('dialogue')], lines)

    def test_legacy_upgrade_preserves_original_sections_and_is_idempotent(self):
        raw = ('【视频片段 1｜5秒】\n【Picture绑定】P1=face.png\n'
               'shot_timeline:\n[Shot 1 | 0.000–5.000s]\nKeep this action.\n\n'
               'detailed_description:\nOriginal framing.\n\ndialogue_and_audio:\n'
               '<d>[Chinese] 晚上见。</d>\n\noverall_soundscape:\nQuiet.\n')
        plans = [{'segment_id': 'SEG001', 'shots': [{'shot_id': 'SH001', 'start_s': 0, 'end_s': 5,
                 'shot_scale': 'medium', 'performance': bi('眼神放松。', 'Soften the gaze.')}]}]
        fixed = apply_performance(raw, plans, 'en', 'cn')
        self.assertEqual(fixed, apply_performance(fixed, plans, 'en', 'cn'))
        restored = fixed.replace(BASELINE['en'] + '\n', '').replace('\nPerformance (SH001): Soften the gaze.', '')
        self.assertEqual(raw, restored)
        with self.assertRaisesRegex(GateError, 'PERFORMANCE_SHOT_MISMATCH'):
            apply_performance(raw.replace('[Shot 1 |', '[Shot 2 |'), plans, 'en', 'cn')

    def test_fallback_respects_short_cuts_inserts_and_bilingual_authorship(self):
        shot = {'shot_id': 'SH001', 'start_s': 0, 'end_s': .6, 'shot_scale': 'close_up'}
        self.assertIn('do not force a blink', shot_performance(shot, 'en'))
        shot['face_visible'] = False
        self.assertIsNone(shot_performance(shot, 'en'))
        shot['performance'] = {'cn': '保持静态。'}
        with self.assertRaisesRegex(GateError, 'SHOT_PERFORMANCE_BILINGUAL_REQUIRED'):
            shot_performance(shot, 'en')
