import tempfile
import unittest
from pathlib import Path

from engine.common import GateError, load, save
from engine.delivery import export_delivery, export_user_project, resolve_project, english_with_chinese_metadata
from engine.validator import validate_directory, parse_md
from examples.fixtures import fixture, materialize


class UserDeliveryTests(unittest.TestCase):
    def test_ready_handoff_preserves_full_and_hides_engineering(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            request = fixture(2)
            assets = materialize(request, base / 'input')
            public = export_user_project(request, assets, base / 'delivery')
            internal = resolve_project(public)
            self.assertFalse(internal.is_relative_to(public))
            self.assertEqual([], validate_directory(internal, internal / 'assets'))
            self.assertEqual([], list(public.rglob('*.json')))
            self.assertEqual(6, len(list(public.glob('*.md'))))
            self.assertEqual(2, len(list(public.glob('*H3*.md'))))
            self.assertEqual((internal / 'H3_PROMPTS_FULL_CN.md').read_bytes(),
                             (public / '04_H3一键提示词_中文版.md').read_bytes())
            cn = parse_md((internal / 'H3_PROMPTS_FULL_CN.md').read_text('utf-8'), 'cn')
            en = parse_md((internal / 'H3_PROMPTS_FULL_EN.md').read_text('utf-8'), 'en')
            delivered = parse_md((public / '05_H3一键提示词_英文版.md').read_text('utf-8'), 'cn')
            self.assertEqual(list(cn), list(delivered))
            marker = 'subject_definitions:\n'
            for uid, block in delivered.items():
                self.assertEqual(cn[uid].split(marker, 1)[0], block.split(marker, 1)[0])
                self.assertEqual(en[uid].split(marker, 1)[1], block.split(marker, 1)[1])
            for row in load(internal / '08_binding.json')['asset_files'].values():
                self.assertEqual((internal / 'assets' / row['file']).read_bytes(),
                                 (public / 'assets' / row['file']).read_bytes())
            with self.assertRaises(GateError):
                export_delivery(internal, public)

    def test_blocked_project_requires_explicit_draft_and_retains_status(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            request = fixture(2)
            public = export_user_project(request, materialize(request, base / 'input'), base / 'delivery')
            internal = resolve_project(public)
            review = load(internal / 'production_review.json')
            review['status'] = 'BLOCKED_MISSING_IMAGES'
            save(internal / 'production_review.json', review)
            with self.assertRaises(GateError):
                export_delivery(internal, base / 'rejected')
            self.assertFalse((base / 'rejected').exists())
            draft = export_delivery(internal, base / 'draft', allow_draft=True)
            self.assertTrue((draft / '04_H3一键提示词_中文版_待出图.md').is_file())
            self.assertIn('尚未准备完成', (draft / '00_使用说明.md').read_text('utf-8'))
            self.assertEqual([], list(draft.rglob('*.json')))

    def test_incomplete_full_is_rejected_before_publication(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            request = fixture(2)
            public = export_user_project(request, materialize(request, base / 'input'), base / 'delivery')
            internal = resolve_project(public)
            review = load(internal / 'production_review.json')
            review['status'] = 'BLOCKED_MISSING_IMAGES'
            save(internal / 'production_review.json', review)
            prompt = internal / 'H3_PROMPTS_FULL_CN.md'
            prompt.write_text(prompt.read_text('utf-8').replace('negative_rules:\n', ''), 'utf-8')
            with self.assertRaisesRegex(GateError, 'ONE_CLICK_H3_FORMAT_INVALID'):
                export_delivery(internal, base / 'bad', allow_draft=True)
            self.assertFalse((base / 'bad').exists())

    def test_header_conversion_preserves_notice_bindings_and_chinese_dialogue(self):
        cn = ('制作状态：待出图。\n\n【视频片段 1｜5秒】\n'
              '【集数】EP01｜我的新室友，是个女生\n【连续性】独立生成\n'
              '【Picture绑定】P1=characters/CHAR_GYC_H3_OFFICE.png\n'
              '【Speaker绑定】S1=顾言川\n\nsubject_definitions:\n中文正文\n')
        en = ('Draft.\n\n[Video Segment 1 | 5s]\n[Speaker Binding] S1=Gu Yanchuan\n'
              'subject_definitions:\nEnglish body.\ndialogue_and_audio:\n顾言川：“晚上见。”\n')
        result = english_with_chinese_metadata(cn, en)
        expected = cn.split('subject_definitions:\n')[0] + en[en.index('subject_definitions:\n'):]
        self.assertEqual(expected, result)
        with self.assertRaisesRegex(GateError, 'DELIVERY_LANGUAGE_UNIT_MISMATCH'):
            english_with_chinese_metadata(cn, en.replace('Segment 1', 'Segment 2'))
        with self.assertRaisesRegex(GateError, 'ONE_CLICK_H3_FORMAT_INVALID'):
            english_with_chinese_metadata(cn, en.replace('subject_definitions:\n', ''))


if __name__ == '__main__':
    unittest.main()
