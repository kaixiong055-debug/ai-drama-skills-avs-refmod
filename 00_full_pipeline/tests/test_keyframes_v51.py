import copy
import tempfile
import unittest
from pathlib import Path
from engine.common import GateError
from engine.keyframes import KEYFRAME_TYPES, REFERENCE_AUTHORITY, plan_keyframes, validate_keyframes
from engine.binding import bind_unit, resolve_files
from engine.spatial import initial_state
from examples.fixtures import fixture, materialize, PNG


class KeyframeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()

    def test_auto_simple_closeups_do_not_require_images(self):
        r = plan_keyframes(fixture(1, 1))
        self.assertEqual(r['shot_keyframes'][0]['status'], 'NOT_REQUIRED')
        self.assertFalse(r['shot_keyframes'][0]['keyframe_required'])
        self.assertEqual(validate_keyframes(r), [])

    def test_auto_complex_scene_is_honest_optional_missing_interface(self):
        r = plan_keyframes(fixture(5, 1))
        for row in r['shot_keyframes']:
            self.assertEqual(row['status'], 'MISSING')
            self.assertEqual(row['generation_status'], 'NOT_RUN')
            self.assertTrue(row['keyframe_recommended'])
            self.assertFalse(row['keyframe_required'])
            self.assertIsNone(row['output'])
        self.assertEqual(plan_keyframes(r), r)

    def test_all_auto_risk_conditions(self):
        flags = [({'scene_geometry_risk': 'HIGH'}, {}, 'SCENE_GEOMETRY_RISK'),
                 ({'fixed_facility_interaction': True}, {}, 'FIXED_PROP_INTERACTION'),
                 ({'regression_history': ['POSITION_DRIFT']}, {}, 'HISTORY_POSITION_DRIFT'),
                 ({'regression_history': ['SCENE_GEOMETRY_DRIFT']}, {}, 'HISTORY_SCENE_GEOMETRY_DRIFT'),
                 ({'weapon_action': True}, {}, 'SPECIAL_ACTION'),
                 ({}, {'special_camera': True}, 'SPECIAL_CAMERA')]
        for segment_flags, shot_flags, reason in flags:
            with self.subTest(reason=reason):
                r = fixture(2, 1); r['segments'][0].update(segment_flags); r['segments'][0]['shots'][0].update(shot_flags)
                self.assertIn(reason, plan_keyframes(r)['shot_keyframes'][0]['reasons'])

    def test_always_missing_blocks_ready_and_never_conflict_is_explicit(self):
        r = fixture(1, 1); r['project']['keyframe_policy'] = 'ALWAYS'
        with self.assertRaisesRegex(GateError, 'REQUIRED_KEYFRAME_MISSING'): plan_keyframes(r)
        r['project']['keyframe_policy'] = 'NEVER'
        r['segments'][0]['shot_keyframes'] = [{'shot_id': 'SH001', 'keyframe_required': True}]
        with self.assertRaisesRegex(GateError, 'CONFLICTS_NEVER'): plan_keyframes(r)

    def test_four_types_and_existing_images_are_references_with_authority(self):
        r = fixture(1, 1); a = materialize(r, self.root)
        r['segments'][0]['shot_keyframes'] = []
        for kind in sorted(KEYFRAME_TYPES):
            output = kind + '.png'; (a / output).write_bytes(PNG)
            r['segments'][0]['shot_keyframes'].append({'shot_id': 'SH001', 'keyframe_type': kind, 'output': output})
        normalized = plan_keyframes(r, a)
        self.assertTrue(all(row['status'] == 'AVAILABLE' for row in normalized['shot_keyframes']))
        self.assertTrue(all(row['reference_authority'] == REFERENCE_AUTHORITY for row in normalized['shot_keyframes']))
        cast = {c['character_id']: c for c in normalized['cast']}
        scenes = {s['scene_id']: s for s in normalized['scenes']}
        assets = {a['asset_id']: a for a in normalized['assets']}
        state = initial_state(normalized['scenes'][0], cast, normalized['segments'][0]['participants'])
        files = resolve_files(normalized['assets'], a)
        segment = normalized['segments'][0]
        pictures = bind_unit(state, scenes, cast, assets, files, segment)
        locked = bind_unit(state, scenes, cast, assets, files, segment, is_lock=True)
        self.assertEqual(len(pictures), 6)
        self.assertEqual(len(locked), 3)
        self.assertEqual(validate_keyframes(normalized, {'SEG001': pictures}), [])
        self.assertTrue(any('KEYFRAME_PICTURE_MISSING' in e for e in validate_keyframes(normalized, {'SEG001': locked})))

    def test_no_fabricated_available_image(self):
        r = fixture(1, 1); a = materialize(r, self.root)
        r['segments'][0]['shot_keyframes'] = [{'shot_id': 'SH001', 'output': 'missing.png', 'status': 'AVAILABLE'}]
        row = plan_keyframes(r, a)['shot_keyframes'][0]
        self.assertEqual(row['status'], 'MISSING')
        self.assertEqual(row['generation_status'], 'NOT_RUN')
        r['segments'][0]['shot_keyframes'][0]['keyframe_required'] = True
        with self.assertRaisesRegex(GateError, 'REQUIRED_KEYFRAME_MISSING'): plan_keyframes(r, a)

    def test_available_image_uses_actual_decoder(self):
        r = fixture(1, 1); a = materialize(r, self.root)
        (a / 'invalid.png').write_bytes(b'not an image')
        r['segments'][0]['shot_keyframes'] = [{'shot_id': 'SH001', 'output': 'invalid.png'}]
        normalized = plan_keyframes(r, a)
        with self.assertRaisesRegex(GateError, 'IMAGE_UNREADABLE'): resolve_files(normalized['assets'], a)

    def test_unknown_sources_and_authority_override_blocked(self):
        r = fixture(1, 1)
        r['segments'][0]['shot_keyframes'] = [{'shot_id': 'SH001', 'source_assets': ['MISSING']}]
        with self.assertRaisesRegex(GateError, 'SOURCE_ASSET_UNKNOWN'): plan_keyframes(r)
        r['segments'][0]['shot_keyframes'] = [{'shot_id': 'SH001', 'reference_authority': {'controls': ['identity']}}]
        with self.assertRaisesRegex(GateError, 'AUTHORITY_OVERRIDE'): plan_keyframes(r)

    def test_input_not_mutated_and_unknown_shot_rejected(self):
        r = fixture(2, 1); original = copy.deepcopy(r); plan_keyframes(r)
        self.assertEqual(r, original)
        r['shot_keyframes'] = [{'shot_id': 'SH999'}]
        with self.assertRaisesRegex(GateError, 'KEYFRAME_SHOT_UNKNOWN'): plan_keyframes(r)

    def test_segment_policy_override_is_executed(self):
        r = fixture(1, 1); r['segments'][0]['keyframe_policy'] = 'ALWAYS'
        with self.assertRaisesRegex(GateError, 'REQUIRED_KEYFRAME_MISSING'): plan_keyframes(r)
        r['project']['keyframe_policy'] = 'ALWAYS'; r['segments'][0]['keyframe_policy'] = 'NEVER'
        self.assertEqual(plan_keyframes(r)['shot_keyframes'][0]['status'], 'NOT_REQUIRED')

    def test_entry_wardrobe_is_used_by_keyframe_sources(self):
        from engine.common import bi
        r = fixture(1, 1)
        r['cast'][0]['wardrobes']['HOME'] = {'runtime_asset_id': 'CHAR_A_H3_HOME', 'description': bi('家居服', 'home clothes')}
        r['assets'].append({'asset_id': 'CHAR_A_H3_HOME', 'role': 'H3_RUNTIME', 'character_id': 'CHAR_A', 'wardrobe': 'HOME'})
        r['segments'][0]['before_events'] = [{'op': 'enter', 'character_id': 'CHAR_A', 'wardrobe': 'HOME'}]
        sources = plan_keyframes(r)['shot_keyframes'][0]['source_assets']
        self.assertIn('CHAR_A_H3_HOME', sources)
        self.assertNotIn('CHAR_A_H3_OFFICE', sources)

    def test_saved_plan_source_tampering_rejected(self):
        r = plan_keyframes(fixture(1, 1))
        r['segments'][0]['shot_keyframes'][0]['source_assets'] = ['SCN_LIVING_MASTER']
        r['shot_keyframes'] = copy.deepcopy(r['segments'][0]['shot_keyframes'])
        self.assertTrue(any('KEYFRAME_REQUIRED_SOURCE_MISSING' in e for e in validate_keyframes(r)))

    def test_integrated_keyframe_runtime_authority_and_separate_lock(self):
        from examples.fixtures_v51 import feature_fixture
        from engine.pipeline import compile_project
        r = feature_fixture(); a = materialize(r, self.root)
        docs, md = compile_project(r, a)
        bindings = docs['08_binding.json']['units']
        lock_types = {b.get('keyframe_type') for b in bindings['LOCK_SC01_A01'].values()}
        seg_types = {b.get('keyframe_type') for b in bindings['SEG001'].values()}
        self.assertIn('SPATIAL_ANCHOR_KEYFRAME', lock_types)
        self.assertNotIn('SHOT_KEYFRAME', lock_types)
        self.assertIn('SHOT_KEYFRAME', seg_types)
        self.assertIn('must not override identity MASTER', md['H3_RUNTIME_EN.md'])
        self.assertIn('KF_SH001_SHOT_KEYFRAME.png', md['H3_RUNTIME_CN.md'])
        self.assertEqual(docs['07_spatial_locks.json']['states']['SEG003_END']['major_props']['LUGGAGE']['holder'], 'CHAR_A.right_hand')

    def test_binding_keyframe_authority_metadata_tampering_rejected(self):
        from examples.fixtures_v51 import feature_fixture
        from engine.pipeline import compile_project
        r = feature_fixture(); a = materialize(r, self.root)
        docs, _ = compile_project(r, a)
        normalized = {'project': docs['01_story.json']['project'], 'scenes': docs['01_story.json']['scenes'],
                      'cast': docs['02_cast.json']['characters'], 'assets': docs['03_assets.json']['assets'],
                      'segments': docs['05_storyboard.json']['segments'], 'shot_keyframes': docs['05_storyboard.json']['shot_keyframes']}
        bindings = copy.deepcopy(docs['08_binding.json']['units'])
        row = next(v for v in bindings['SEG001'].values() if v.get('keyframe_type') == 'SHOT_KEYFRAME')
        row['reference_authority']['cannot_override'] = []
        self.assertTrue(any('KEYFRAME_BINDING_AUTHORITY_INVALID' in e for e in validate_keyframes(normalized, bindings)))
        bindings = copy.deepcopy(docs['08_binding.json']['units'])
        row = copy.deepcopy(next(v for v in bindings['SEG001'].values() if v.get('keyframe_type') == 'SHOT_KEYFRAME'))
        bindings['LOCK_SC01_A01']['P9'] = row
        self.assertTrue(any('FORMAL_KEYFRAME_BOUND_TO_LOCK' in e for e in validate_keyframes(normalized, bindings)))


if __name__ == '__main__': unittest.main()
