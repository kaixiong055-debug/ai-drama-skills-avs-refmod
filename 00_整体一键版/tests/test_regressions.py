import copy
import tempfile
import unittest
from pathlib import Path
from engine.common import GateError,bi
from engine.pipeline import compile_project
from engine.validator import validate_request
from examples.fixtures import fixture,materialize


class FineGrainedRegressions(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def compile(self,r):return compile_project(r,materialize(r,self.root))
    def test_initial_seated_pose_preserved(self):
        r=fixture();r['scenes'][0]['initial_state']['characters']={'CHAR_A':{'pose':bi('坐在固定沙发左端','seated at the left end of the fixed sofa')}}
        docs,md=self.compile(r);self.assertIn('seated at the left',md['H3_PROMPTS_EN.md'])
    def test_missing_position_not_guessed(self):
        r=fixture();r['scenes'][0]['initial_state']['character_positions'].pop('CHAR_B')
        with self.assertRaisesRegex(GateError,'INITIAL_POSITION_MISSING'):self.compile(r)
    def test_runtime_cannot_be_replaced_by_face_board(self):
        r=fixture();r['assets'][0]['role']='FACE4'
        with self.assertRaisesRegex(GateError,'WARDROBE_RUNTIME_BINDING_CONFLICT'):self.compile(r)
    def test_wardrobe_change_without_window_rejected(self):
        r=fixture();r['segments'][0]['events']=[{'op':'appearance','at_s':4.7,'character_id':'CHAR_A','cause':'changing','wardrobe':'OFFICE',
                                               'description':bi('换衣','Change clothing')}]
        with self.assertRaisesRegex(GateError,'OFF_SCREEN_WINDOW'):self.compile(r)
    def test_subject_identity_groups_multiple_runtime_outfits(self):
        r=fixture();r['cast'][0]['wardrobes']['HOME']={'description':bi('白色居家衬衫','a white home shirt'),'runtime_asset_id':'CHAR_A_H3_HOME'}
        r['assets'].append({'asset_id':'CHAR_A_H3_HOME','file':'CHAR_A_H3_HOME.png','role':'H3_RUNTIME','character_id':'CHAR_A','wardrobe':'HOME','direct_bindable':True,'description':bi('顾言川的白色居家衬衫造型',"Gu Yanchuan's white home-shirt appearance")})
        r['segments'][0]['events']=[{'op':'appearance','at_s':4.9,'character_id':'CHAR_A','cause':'changing before next beat','wardrobe':'HOME','off_screen_window':'4.5–4.9 seconds after an already established long off-screen time bridge',
                                               'description':bi('明确画外时间桥接后换成居家衬衫','Change into the home shirt after an explicitly established off-screen time bridge')}]
        docs,md=self.compile(r)
        block=md['H3_PROMPTS_EN.md'].split('[Video Segment 1',1)[1].split('[Video Segment 2',1)[0]
        definitions=block.split('subject_definitions:\n',1)[1].split('\n\nsummary:',1)[0]
        self.assertEqual(definitions.count('is Gu Yanchuan'),1)
        self.assertIn('<Picture 4>',definitions)
    def test_source_exact_beat_cannot_be_omitted(self):
        r=fixture();r['source_beats'].append({'beat_id':'SRC_LOST','preservation':'EXACT'})
        self.assertIn('PROTECTED_SOURCE_BEAT_UNCOVERED:SRC_LOST',validate_request(r))
    def test_text_reference_gate(self):
        r=fixture();r['segments'][0]['text_reference_required']=True
        self.assertTrue(any('TEXT_REFERENCE_ASSET_MISSING' in e for e in validate_request(r)))
    def test_scene_budget_limit(self):
        r=fixture()
        for n in range(9):r['assets'].append({'asset_id':f'SCN_AREA{n}','file':f'SCN_AREA{n}.png','role':'AREA','scene_id':'SCN_LIVING_NIGHT','scene_family_id':'LIVING','direct_bindable':True,'description':bi('局部空间','a local area')})
        self.assertTrue(any('SCENE_IMAGE_LIMIT_EXCEEDED' in e for e in validate_request(r)))
    def test_unauthorized_axis_cross_rejected(self):
        r=fixture();r['segments'][1]['before_events']=[{'op':'axis','camera_side':'north','authorized':False,'description':bi('越轴','Cross the axis')}]
        self.assertTrue(validate_request(r))
    def test_transformation_profile_requires_single_continuous_shot(self):
        r=fixture();r['project']['production_profile']='TRANSFORMATION'
        self.assertTrue(any('SHOT_PROFILE_LIMIT' in e for e in validate_request(r)))


if __name__=='__main__':unittest.main()
