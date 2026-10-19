import copy
import tempfile
import unittest
from pathlib import Path
from engine.common import GateError, bi
from engine.asset_dependencies import prepare_asset_dependencies, validate_asset_dependencies
from engine.binding import bind_unit, resolve_files
from engine.spatial import initial_state
from examples.fixtures import fixture, materialize


def versioned_request():
    r = fixture(2, 1)
    for c in r['cast']:
        cid = c['character_id']
        master, face, body, outfit = [cid + x for x in ['_MASTER', '_FACE4', '_BODY', '_WARDROBE_OFFICE']]
        c.update(master_asset_id=master, face4_asset_id=face, body_asset_id=body)
        c['wardrobes']['OFFICE']['wardrobe_asset_id'] = outfit
        for aid, role, parents in [(master, 'MASTER', []), (face, 'FACE4', [master]),
                                   (body, 'BODY', [face]), (outfit, 'WARDROBE', [body])]:
            asset = {'asset_id': aid, 'file': aid + '.png', 'role': role, 'character_id': cid,
                     'version': 3, 'derived_from': parents, 'source_versions': {p: 3 for p in parents},
                     'status': 'VALID', 'direct_bindable': False, 'description': bi('版本资产', 'A versioned asset')}
            if role == 'WARDROBE': asset['wardrobe'] = 'OFFICE'
            r['assets'].append(asset)
        runtime = next(a for a in r['assets'] if a['asset_id'] == c['wardrobes']['OFFICE']['runtime_asset_id'])
        runtime.update(version=3, derived_from=[master, outfit], source_versions={master: 3, outfit: 3}, status='VALID')
    scene_master = next(a for a in r['assets'] if a['asset_id'] == r['scenes'][0]['master_asset_id'])
    scene_master.update(version=3, derived_from=[], source_versions={}, status='VALID')
    return r


def bound_runtime(r):
    return {'SEG001': {'P1': {'asset_id': r['cast'][0]['wardrobes']['OFFICE']['runtime_asset_id']}}}


class AssetDependencyTests(unittest.TestCase):
    def report(self, r, bindings=None, allow=False):
        return validate_asset_dependencies(r['assets'], r['cast'], r['scenes'], bindings, allow)

    def test_legacy_no_fake_versions_or_validity(self):
        original = fixture()
        normalized, report = prepare_asset_dependencies(original)
        self.assertEqual(report['errors'], [])
        self.assertEqual(set(a['status'] for a in normalized['assets']), {'UNVERIFIED'})
        self.assertTrue(all(a['version'] is None for a in normalized['assets']))
        self.assertNotIn('status', original['assets'][0])

    def test_declared_family_valid_and_idempotent(self):
        r, report = prepare_asset_dependencies(versioned_request())
        self.assertEqual(report['errors'], [])
        self.assertEqual(set(a['status'] for a in r['assets']), {'VALID'})
        again, _ = prepare_asset_dependencies(r)
        self.assertEqual(r, again)

    def test_master_update_invalidates_all_descendants(self):
        r = versioned_request()
        next(a for a in r['assets'] if a['asset_id'] == 'CHAR_A_MASTER')['version'] = 4
        report = self.report(r, bound_runtime(r))
        rows = {a['asset_id']: a for a in report['assets']}
        for suffix in ['FACE4', 'BODY', 'WARDROBE_OFFICE', 'H3_OFFICE']:
            self.assertEqual(rows['CHAR_A_' + suffix]['status'], 'STALE')
        self.assertIn('STALE_ASSET_BOUND:CHAR_A_H3_OFFICE', report['errors'])
        self.assertEqual(rows['CHAR_B_H3_OFFICE']['status'], 'VALID')

    def test_explicit_stale_exception_only(self):
        r = versioned_request()
        r['assets'][0]['status'] = 'STALE'
        self.assertTrue(self.report(r, bound_runtime(r))['errors'])
        report = self.report(r, bound_runtime(r), True)
        self.assertEqual(report['errors'], [])
        self.assertIn('STALE_ASSET_EXPLICITLY_ALLOWED:CHAR_A_H3_OFFICE', report['warnings'])
        self.assertIn('ALLOW_STALE_ASSET_MUST_BE_BOOLEAN', self.report(r, bound_runtime(r), 'true')['errors'])

    def test_missing_cannot_be_overridden(self):
        r = versioned_request(); r['assets'][0]['status'] = 'MISSING'
        self.assertIn('MISSING_ASSET_BOUND:CHAR_A_H3_OFFICE', self.report(r, bound_runtime(r), True)['errors'])

    def test_missing_parent_and_cycle_rejected(self):
        r = versioned_request(); r['assets'][0]['derived_from'].append('ABSENT')
        self.assertTrue(any('ASSET_DEPENDENCY_MISSING' in e for e in self.report(r)['errors']))
        r = versioned_request()
        master = next(a for a in r['assets'] if a['asset_id'] == 'CHAR_A_MASTER')
        master.update(derived_from=['CHAR_A_FACE4'], source_versions={'CHAR_A_FACE4': 3})
        self.assertTrue(any('ASSET_DEPENDENCY_CYCLE' in e for e in self.report(r)['errors']))

    def test_current_wardrobe_dependency_must_match(self):
        r = versioned_request(); runtime = r['assets'][0]
        runtime['derived_from'] = ['CHAR_A_MASTER', 'CHAR_B_WARDROBE_OFFICE']
        runtime['source_versions'] = {p: 3 for p in runtime['derived_from']}
        errors = self.report(r)['errors']
        self.assertTrue(any('RUNTIME_WARDROBE_DEPENDENCY_INVALID' in e for e in errors))
        self.assertTrue(any('RUNTIME_WRONG_WARDROBE_DEPENDENCY' in e for e in errors))

    def test_missing_runtime_master_cannot_silently_validate(self):
        r = versioned_request(); runtime = r['assets'][0]
        runtime.update(derived_from=[], source_versions={})
        self.assertTrue(any('CHARACTER_MASTER_DEPENDENCY_INVALID' in e for e in self.report(r)['errors']))

    def test_scene_area_and_prop_variant_stale(self):
        r = versioned_request()
        for aid, role, extra, parent in [
            ('AREA_ENTRY', 'AREA', {'scene_id': 'SCN_LIVING_NIGHT'}, 'SCN_LIVING_MASTER'),
            ('CASE_CLOSED', 'PROP', {'variant': 'CLOSED', 'master_asset_id': 'CASE_MASTER'}, 'CASE_MASTER')]:
            r['assets'].append({'asset_id': aid, 'role': role, 'version': 1, 'derived_from': [parent],
                                'source_versions': {parent: 3}, 'status': 'VALID', **extra})
        r['assets'].append({'asset_id': 'CASE_MASTER', 'role': 'PROP', 'version': 4, 'status': 'VALID'})
        next(a for a in r['assets'] if a['asset_id'] == 'SCN_LIVING_MASTER')['version'] = 4
        rows = {a['asset_id']: a for a in self.report(r)['assets']}
        self.assertEqual(rows['AREA_ENTRY']['status'], 'STALE')
        self.assertEqual(rows['CASE_CLOSED']['status'], 'STALE')

    def test_source_version_alias_and_generation_mismatch(self):
        r = versioned_request(); face = next(a for a in r['assets'] if a['role'] == 'FACE4')
        face.pop('source_versions'); face['source_version'] = 3
        self.assertEqual(self.report(r)['errors'], [])
        face['generated_from_version'] = 2
        self.assertTrue(any('ASSET_GENERATION_VERSION_CONFLICT' in e for e in self.report(r)['errors']))

    def test_legacy_marker_cannot_hide_new_metadata(self):
        r = versioned_request(); runtime = r['assets'][0]
        runtime.update(dependency_metadata_origin='LEGACY_UNVERIFIED', derived_from=[], source_versions={})
        self.assertTrue(any('CHARACTER_MASTER_DEPENDENCY_INVALID' in e for e in self.report(r)['errors']))

    def test_real_binding_blocks_stale_and_missing_without_exceptions(self):
        r = versioned_request(); r['assets'][0]['status'] = 'STALE'; r, _ = prepare_asset_dependencies(r)
        with tempfile.TemporaryDirectory() as td:
            assets_path = materialize(r, td)
            files = resolve_files(r['assets'], assets_path)
            cast = {c['character_id']: c for c in r['cast']}; scenes = {s['scene_id']: s for s in r['scenes']}
            assets = {a['asset_id']: a for a in r['assets']}
            state = initial_state(r['scenes'][0], cast, r['segments'][0]['participants'])
            with self.assertRaisesRegex(GateError, 'STALE_ASSET_BOUND'):
                bind_unit(state, scenes, cast, assets, files, r['segments'][0])
            pictures = bind_unit(state, scenes, cast, assets, files, r['segments'][0], allow_stale_asset=True)
            self.assertEqual(len(pictures), 3)
            assets['CHAR_A_H3_OFFICE']['status'] = 'MISSING'
            with self.assertRaisesRegex(GateError, 'MISSING_ASSET_BOUND'):
                bind_unit(state, scenes, cast, assets, files, r['segments'][0], allow_stale_asset=True)

    def test_integrated_ready_gate_blocks_changed_master(self):
        from examples.fixtures_v51 import versioned_fixture
        from engine.pipeline import compile_project
        r = versioned_fixture(2, 1)
        next(a for a in r['assets'] if a['asset_id'] == 'CHAR_A_MASTER')['version'] = 4
        with tempfile.TemporaryDirectory() as td:
            a = materialize(r, td)
            with self.assertRaisesRegex(GateError, 'STALE_ASSET_BOUND'): compile_project(r, a)
            r['project']['allow_stale_asset'] = True
            docs, _ = compile_project(r, a)
            runtime = next(a for a in docs['03_assets.json']['assets'] if a['asset_id'] == 'CHAR_A_H3_OFFICE')
            self.assertEqual(runtime['status'], 'STALE')


if __name__ == '__main__': unittest.main()
