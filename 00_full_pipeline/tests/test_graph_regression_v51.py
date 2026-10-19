import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from engine.common import GateError, load, save
from engine.pipeline_graph import load_graph, validate_pipeline_graph, execution_order
from engine.regression import new_manifest, validate_manifest, register_result, compare_results, METRICS, METADATA


class GraphRegressionTests(unittest.TestCase):
    def test_graph_respects_export_dependencies(self):
        self.assertEqual(validate_pipeline_graph(), [])
        order = execution_order()
        self.assertLess(order.index('spatial_lock'), order.index('binding'))
        self.assertLess(order.index('binding'), order.index('h3_export'))
        self.assertLess(order.index('qc'), order.index('assembly'))

    def test_graph_cycle_and_unproduced_artifact_rejected(self):
        graph = load_graph()
        graph['stages'][0]['depends_on'] = ['assembly']
        self.assertTrue(any('CYCLE' in e for e in validate_pipeline_graph(graph)))
        graph = load_graph()
        graph['stages'][0]['requires'].append('imaginary.json')
        self.assertTrue(any('INPUT_UNKNOWN' in e for e in validate_pipeline_graph(graph)))

    def test_graph_export_cannot_skip_binding(self):
        graph = load_graph()
        stage = next(s for s in graph['stages'] if s['id'] == 'h3_export')
        stage['depends_on'] = ['storyboard']
        self.assertTrue(any('REQUIRED_GATE_MISSING' in e for e in validate_pipeline_graph(graph)))

    def test_registry_has_45_unrun_variants_and_null_metrics(self):
        manifest = new_manifest()
        self.assertEqual(validate_manifest(manifest), [])
        self.assertEqual(len(manifest['cases']), 15)
        self.assertEqual(sum(len(c['variants']) for c in manifest['cases']), 45)
        self.assertEqual(compare_results(manifest)['status'], 'NOT_RUN')
        for case in manifest['cases']:
            for variant in case['variants'].values():
                self.assertTrue(all(v is None for v in variant['metrics'].values()))

    def test_unrun_zero_is_fabrication(self):
        manifest = new_manifest()
        manifest['cases'][0]['variants']['A']['metrics']['identity_drift'] = 0
        self.assertIn('REGRESSION_UNRUN_RESULT_FABRICATED', validate_manifest(manifest))

    def make_record(self, root, variant='C'):
        output = root / f'{variant}.mp4'
        # Unit-test stub only. Probe is mocked; no actual H3 video is generated.
        output.write_bytes(b'unit-test-video-probe-stub')
        version = '5.1' if variant == 'C' else '5.0'
        return {'case_id': 'R01', 'variant': variant, 'comparison_id': 'controlled-seed-17',
                'generation_id': 'GEN-' + variant, 'take_id': 'TAKE01', 'segment_id': 'SEG001',
                'model': 'H3', 'model_version': 'operator-supplied-version', 'workflow': 'workflow-hash',
                'resolution': [1280, 720], 'steps': 30, 'seed': 17,
                'prompt_version': version + ':prompt-hash', 'hidden_lock': variant != 'A',
                'continuation': None, 'reference_assets': ['CHAR_A', 'SCENE_MASTER'],
                'runtime_seconds': 90.5, 'output_file': str(output),
                'scenario_signature': 'a' * 64,
                'metrics': {k: 0.25 for k in METRICS},
                'evidence': {'reviewer': 'unit-test-fixture', 'method': 'mocked probe unit test',
                             'observations': {k: 'Fixture only; not a real H3 evaluation.' for k in METRICS}}}

    def create_files(self, root, records):
        manifest, ledger = root / 'manifest.json', root / 'ledger.json'
        save(manifest, new_manifest())
        save(ledger, {'takes': [{**r, 'status': 'GENERATED', 'output': r['output_file']} for r in records]})
        return manifest, ledger

    def test_real_registration_links_ledger_and_preserves_unknown_cases(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); record = self.make_record(root)
            manifest, ledger = self.create_files(root, [record])
            with patch('engine.regression._probe_video', return_value={'width': 1280, 'height': 720, 'duration_s': 5, 'probe': 'test-only'}):
                register_result(manifest, ledger, record)
                with self.assertRaisesRegex(GateError, 'DUPLICATE'):
                    register_result(manifest, ledger, record)
            result = load(manifest)
            self.assertEqual(result['status'], 'PARTIAL')
            self.assertEqual(result['cases'][1]['status'], 'NOT_RUN')
            self.assertEqual(validate_manifest(result), [])
            self.assertEqual(load(ledger)['takes'][0]['h3_regression'][0]['variant'], 'C')

    def test_registration_missing_video_or_ledger_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); record = self.make_record(root)
            manifest, ledger = self.create_files(root, [record])
            changed = copy.deepcopy(record); changed['seed'] += 1
            with self.assertRaisesRegex(GateError, 'METADATA_MISMATCH'):
                register_result(manifest, ledger, changed)
            Path(record['output_file']).unlink()
            with self.assertRaisesRegex(GateError, 'VIDEO_MISSING'):
                register_result(manifest, ledger, record)
            self.assertEqual(load(manifest)['status'], 'NOT_RUN')

    def test_registration_metrics_and_variants_not_guessed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); record = self.make_record(root)
            manifest, ledger = self.create_files(root, [record])
            record['metrics']['identity_drift'] = None
            with self.assertRaisesRegex(GateError, 'METRIC_VALUES'):
                register_result(manifest, ledger, record)
            record['metrics']['identity_drift'] = 0
            record['hidden_lock'] = False
            with self.assertRaisesRegex(GateError, 'LOCK_VARIANT'):
                register_result(manifest, ledger, record)

    def test_registry_tampered_metrics_and_probe_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); record = self.make_record(root)
            manifest, ledger = self.create_files(root, [record])
            with patch('engine.regression._probe_video', return_value={'width': 1280, 'height': 720, 'duration_s': 5, 'probe': 'test-only'}):
                register_result(manifest, ledger, record)
            data = load(manifest)
            variant = data['cases'][0]['variants']['C']
            variant['runs'][0]['metrics']['identity_drift'] = 7
            variant['metrics']['identity_drift'] = 7
            self.assertTrue(any('RUN_INVALID' in e for e in validate_manifest(data)))
            data = load(manifest)
            data['cases'][0]['variants']['C']['runs'][0]['video_probe']['duration_s'] = None
            self.assertIn('REGRESSION_VIDEO_PROBE_INVALID', validate_manifest(data))

    def test_english_runtime_jobs_can_record_a_take(self):
        from examples.fixtures import fixture, materialize
        from engine.pipeline import export_project
        from engine.generation import jobs, record_take
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); request = fixture(2, 1)
            assets = materialize(request, root / 'input')
            project = export_project(request, assets, root / 'production')
            job = next(j for j in jobs(project, 'en') if j['segment_id'] == 'SEG001')
            self.assertEqual(job['language'], 'en')
            self.assertNotIn('retention_analysis:', job['prompt'])
            output = root / 'synthetic.mp4'; output.write_bytes(b'UNIT TEST ONLY')
            job.update(generation_id='EN-GEN', output=str(output), status='GENERATED')
            ledger = record_take(project, job)
            self.assertEqual(ledger['takes'][0]['output_file'], str(output))
            self.assertIsNone(ledger['takes'][0]['model_version'])

    def test_controlled_abc_comparison_and_seed_confounds(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); records = [self.make_record(root, v) for v in 'ABC']
            manifest, ledger = self.create_files(root, records)
            with patch('engine.regression._probe_video', return_value={'width': 1280, 'height': 720, 'duration_s': 5, 'probe': 'test-only'}):
                for record in records:
                    register_result(manifest, ledger, record)
            data = load(manifest)
            comparison = compare_results(data)['comparisons'][0]
            self.assertEqual(comparison['status'], 'COMPARABLE')
            self.assertEqual(comparison['C_minus_B']['position_drift'], 0)
            data['cases'][0]['variants']['C']['runs'][0]['seed'] = 999
            comparison = compare_results(data)['comparisons'][0]
            self.assertEqual(comparison['status'], 'CONTROL_MISMATCH')
            self.assertIsNone(comparison['C_minus_B'])

    def test_different_story_or_output_duration_is_not_comparable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); records = [self.make_record(root, v) for v in 'ABC']
            manifest, ledger = self.create_files(root, records)
            with patch('engine.regression._probe_video', return_value={'width': 1280, 'height': 720, 'duration_s': 5, 'probe': 'test-only'}):
                for record in records:
                    register_result(manifest, ledger, record)
            data = load(manifest)
            run = data['cases'][0]['variants']['C']['runs'][0]
            run['scenario_signature'] = 'b' * 64
            self.assertIn('scenario_signature', compare_results(data)['comparisons'][0]['mismatched_controls'])
            run['scenario_signature'] = 'a' * 64
            run['video_probe']['duration_s'] = 5.917
            self.assertIn('output_duration_s', compare_results(data)['comparisons'][0]['mismatched_controls'])


if __name__ == '__main__':
    unittest.main()
