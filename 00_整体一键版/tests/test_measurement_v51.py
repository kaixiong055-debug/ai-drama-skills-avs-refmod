import copy
import re
import tempfile
import unittest
from pathlib import Path
from engine.common import GateError,bi
from engine.measurement import prepare_measurements,validate_spatial_measurements
from engine.pipeline import compile_project,export_project
from engine.validator import validate_request,validate_pack,validate_directory
from examples.fixtures import fixture,materialize


class MeasurementTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def compile(self,r):return compile_project(r,materialize(r,self.root/'input'))
    def metric(self,r):
        r['scenes'][0]['spatial_measurement']={'measurement_mode':'METRIC','confidence':'HIGH',
            'provenance':{'source_type':'USER_SPECIFIED','source_id':'user_dimensions_001',
                          'evidence':'The user explicitly supplied the scene coordinates and a 1.2 m door distance.'},
            'constraints':[{'subject_id':'CHAR_A','reference_id':'ENTRY_DOOR','distance_m':1.2}]}
        return r
    def test_legacy_image_layout_defaults_relative_no_fake_metres(self):
        docs,md=self.compile(fixture());s=docs['07_spatial_locks.json']['states']['SEG001_CURRENT']
        self.assertEqual(s['spatial_measurement']['measurement_mode'],'RELATIVE')
        self.assertEqual(s['coordinate_unit'],'relative_layout')
        self.assertIsInstance(s['distance_between_characters']['CHAR_A|CHAR_B'],dict)
        for name in ['H3_RUNTIME_CN.md','H3_RUNTIME_EN.md','H3_PROMPTS_FULL_CN.md','H3_PROMPTS_FULL_EN.md']:
            self.assertNotRegex(md[name],r'1\.8\s*(?:m\b|米)')
    def test_metric_preserves_user_distance(self):
        docs,md=self.compile(self.metric(fixture()))
        self.assertEqual(docs['07_spatial_locks.json']['states']['SEG001_CURRENT']['distance_between_characters']['CHAR_A|CHAR_B'],1.8)
        for name in ['H3_RUNTIME_EN.md','H3_PROMPTS_FULL_EN.md']:
            self.assertRegex(md[name],r'1\.2\s*m')
    def test_metric_without_evidence_blocks(self):
        r=fixture();r['scenes'][0]['spatial_measurement']={'measurement_mode':'METRIC','confidence':'HIGH'}
        self.assertTrue(validate_request(r))
        with self.assertRaises(GateError):self.compile(r)
    def test_photo_inference_not_metric_source(self):
        r=self.metric(fixture());r['scenes'][0]['spatial_measurement']['provenance']['source_type']='PHOTO_INFERENCE'
        self.assertTrue(validate_request(r))
    def test_relative_cannot_be_promoted(self):
        r=self.metric(fixture());r['scenes'][0]['spatial_measurement']['source_measurement_mode']='RELATIVE'
        self.assertIn('SCN_LIVING_NIGHT:RELATIVE_TO_METRIC_FORBIDDEN',validate_spatial_measurements(r))
    def test_unknown_remains_unknown(self):
        r=fixture();r['scenes'][0]['spatial_measurement']={'measurement_mode':'UNKNOWN','confidence':'LOW'}
        docs,md=self.compile(r)
        self.assertEqual(docs['07_spatial_locks.json']['states']['SEG003_END']['spatial_measurement']['measurement_mode'],'UNKNOWN')
    def test_layout_magnitude_does_not_create_metric(self):
        r=fixture();r['scenes'][0]['initial_state']['character_positions']['CHAR_B']['x_m']=1234
        docs,md=self.compile(r);self.assertNotIn('1234 m',md['H3_RUNTIME_EN.md'])
        self.assertEqual(docs['01_story.json']['scenes'][0]['spatial_measurement']['measurement_mode'],'RELATIVE')
    def test_fake_metric_geometry_rejected(self):
        r=fixture();r['scenes'][0]['initial_state']['door_positions']['ENTRY_DOOR']=bi('距离顾言川1.2米','1.2m from Gu Yanchuan')
        self.assertTrue(any('UNVERIFIED_METRIC' in e for e in validate_request(r)))
    def test_state_cannot_override_scale(self):
        docs,md=self.compile(fixture());docs['07_spatial_locks.json']['states']['SEG001_CURRENT']['spatial_measurement']=self.metric(fixture())['scenes'][0]['spatial_measurement']
        self.assertTrue(any('MEASUREMENT_PROVENANCE_CHANGED' in e for e in validate_pack(docs,md,self.root/'input/assets')))
    def test_new_version_request_and_pack_artifacts(self):
        r=fixture();r['schema_version']='5.1';out=export_project(r,materialize(r,self.root/'input'),self.root/'pack')
        required=['pipeline_graph.json','asset_dependency_report.json','h3_regression_manifest.json','runtime_prompt_budget_report.json',
            'H3_RUNTIME_CN.md','H3_RUNTIME_EN.md','H3_PROMPTS_FULL_CN.md','H3_PROMPTS_FULL_EN.md','CHANGELOG_V5.1.md']
        self.assertTrue(all((out/n).is_file() for n in required));self.assertEqual(validate_directory(out),[])
        (out/'H3_RUNTIME_CN.md').write_text('bad prompt',encoding='utf-8')
        self.assertTrue(validate_directory(out))
    def test_metric_contradictory_constraints_rejected(self):
        r=self.metric(fixture());m=r['scenes'][0]['spatial_measurement']
        m['constraints'].append({'subject_id':'CHAR_A','reference_id':'CHAR_B','distance_m':1.2})
        self.assertTrue(any('COORDINATE_CONSTRAINT_CONFLICT' in e for e in validate_request(r)))
        m['constraints']=[{'subject_id':'CHAR_A','reference_id':'ENTRY_DOOR','distance_m':1.2},
                          {'subject_id':'ENTRY_DOOR','reference_id':'CHAR_A','distance_m':2.0}]
        self.assertTrue(any('METRIC_CONSTRAINT_CONFLICT' in e for e in validate_request(r)))
    def test_body_facing_not_overwritten_by_eyeline(self):
        r=fixture();r['scenes'][0]['initial_state']['character_positions']['CHAR_A']['facing']='forward'
        docs,md=self.compile(r)
        p=docs['07_spatial_locks.json']['states']['SEG001_CURRENT']['character_positions']['CHAR_A']
        self.assertEqual(p['facing'],'forward');self.assertEqual(p['eyeline_target'],'CHAR_B')

if __name__=='__main__':unittest.main()
