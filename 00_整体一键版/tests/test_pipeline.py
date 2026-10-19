import copy
import tempfile
import unittest
from pathlib import Path
from engine.common import GateError, bi
from engine.pipeline import compile_project, export_project
from engine.validator import validate_pack, validate_request, validate_directory
from engine.spatial import normalize
from examples.fixtures import fixture, materialize


class ProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def compile(self,r):return compile_project(r,materialize(r,self.root/'input'))
    def lock_count(self,r):return len(self.compile(r)[0]['07_spatial_locks.json']['locks'])
    def add_character(self,r):
        extra=fixture(3,1)
        r['cast']=extra['cast'];r['assets']=extra['assets']
        return {'op':'enter','character_id':'CHAR_C','position':extra['scenes'][0]['initial_state']['character_positions']['CHAR_C'],
                'description':bi('陈悦从已登记门口走入，在右后方停下','Chen Yue enters through the registered doorway and stops behind the group on the right')}
    def test_TEST01_two_person_multiround(self):
        docs,md=self.compile(fixture(2,3));self.assertEqual(len(docs['06_production.json']['units']),3)
        self.assertIn('Off-screen characters remain',md['H3_PROMPTS_EN.md'])
    def test_TEST02_three_person_interruption(self):
        r=fixture(3,3);r['beats'][2]['speaker']='CHAR_C';docs,md=self.compile(r)
        self.assertEqual(docs['06_production.json']['units'][1]['active_speakers'],['CHAR_C','CHAR_B'])
        self.assertEqual(len(docs['07_spatial_locks.json']['locks']),1)
    def test_TEST03_four_person(self):self.assertEqual(self.lock_count(fixture(4)),1)
    def test_TEST04_five_person(self):
        docs,md=self.compile(fixture(5));self.assertEqual(len(docs['08_binding.json']['units']['SEG001']),6)
        self.assertIn('Su Lan',md['H3_PROMPTS_EN.md'])
    def test_TEST05_entry_relocks(self):
        r=fixture(2);e=self.add_character(r);r['segments'][1]['before_events']=[e]
        for p in r['segments'][1:]:p['participants'].append('CHAR_C')
        self.assertEqual(self.lock_count(r),2)
    def test_TEST06_exit_relocks(self):
        r=fixture(3);r['segments'][1]['before_events']=[{'op':'exit','character_id':'CHAR_C','exit_direction':'left',
                 'description':bi('陈悦经已登记门口离场','Chen Yue exits through the registered doorway')}]
        for p in r['segments'][1:]:p['participants'].remove('CHAR_C')
        self.assertEqual(self.lock_count(r),2)
    def test_TEST07_swap_A02(self):
        r=fixture();r['segments'][1]['before_events']=[{'op':'move','character_id':c,'position':{'x_m':x},'path':['LEFT','RIGHT'],
                  'description':bi('角色沿清晰路径交换站位，已在段间完成','The character follows a visible path to swap positions, completed at the segment boundary')}
                 for c,x in [('CHAR_A',1.8),('CHAR_B',0)]]
        docs,md=self.compile(r);locks=docs['07_spatial_locks.json']['locks'];self.assertEqual(locks[1]['lock_id'],'LOCK_SC01_A02')
    def test_TEST08_three_segments_no_redundant_lock(self):self.assertEqual(self.lock_count(fixture(2,3)),1)
    def test_TEST09_right_hand_to_chair(self):
        r=fixture();r['assets'].append({'asset_id':'PROP_SHIRT','file':'PROP_SHIRT.png','role':'PROP','direct_bindable':True,
                                      'description':bi('白衬衫布料外观','the white shirt fabric appearance')})
        s=r['scenes'][0];s['prop_asset_ids']={'SHIRT':'PROP_SHIRT'}
        s['initial_state']['major_props']={'SHIRT':{'holder':'CHAR_A.right_hand','state':bi('右手松散持有','held loosely in the right hand'),'valid_until_changed':True}}
        r['segments'][0]['events']=[{'op':'prop','at_s':4.8,'prop_id':'SHIRT','from_holder':'CHAR_A.right_hand','holder':'CHAIR',
                                    'state':bi('搭在椅背','draped over the chair back'),
                                    'description':bi('顾言川用右手把衬衫放在椅背上','Gu Yanchuan places the shirt on the chair back with his right hand')}]
        docs,md=self.compile(r);ss=docs['07_spatial_locks.json']['states']['SEG002_CURRENT'];self.assertEqual(ss['major_props']['SHIRT']['holder'],'CHAIR')
    def test_TEST10_doorbell_three_once(self):
        r=fixture();e={'op':'sound','at_s':1.2,'event_id':'BELL01','count':3,'window_start':.2,'window_end':1.2,
                       'description':bi('三声分离门铃','three distinctly separated doorbell rings'),
                       'termination':bi('第三声后完全结束，无持续尾音','stop completely after the third ring with no sustained tail')}
        r['segments'][0]['events']=[e];docs,md=self.compile(r)
        self.assertEqual(docs['07_spatial_locks.json']['states']['SEG002_CURRENT']['completed_sounds'],['BELL01'])
        r['segments'][1]['events']=[copy.deepcopy(e)]
        with self.assertRaisesRegex(GateError,'SOUND_REPEATED'):self.compile(r)
    def test_TEST11_night_to_morning_scene(self):
        r=fixture();scene=copy.deepcopy(r['scenes'][0]);scene['scene_id']='SCN_LIVING_MORNING';scene['time_of_day']=bi('清晨','Morning');r['scenes'].append(scene)
        r['segments'][2]['scene_id']=scene['scene_id']
        for b in r['beats'][4:]:b['scene_id']=scene['scene_id']
        self.assertEqual(self.lock_count(r),2)
    def test_TEST12_bilingual_parity_and_export(self):
        r=fixture();a=materialize(r,self.root/'input');out=export_project(r,a,self.root/'output')
        self.assertEqual(validate_directory(out),[])
        docs={n:__import__('engine.common',fromlist=['load']).load(out/n) for n in __import__('engine.common',fromlist=['FILES']).FILES}
        md={n:(out/n).read_text(encoding='utf-8') for n in ['H3_PROMPTS_CN.md','H3_PROMPTS_EN.md']}
        md['H3_PROMPTS_EN.md']=md['H3_PROMPTS_EN.md'].replace('0.000–2.500s','0.000–2.600s',1)
        self.assertTrue(any('BILINGUAL_TIMELINE_MISMATCH' in e for e in validate_pack(docs,md,out/'assets')))
    def test_script_cannot_contain_camera(self):
        r=fixture();r['beats'][0]['lens_mm']=85;self.assertTrue(any('SCRIPT_CAMERA' in e for e in validate_request(r)))
    def test_dialogue_overtime(self):
        r=fixture();r['beats'][0]['dialogue']='这是一段非常长的对白绝对无法在规定时间内说完请不要直接输出';self.assertTrue(any('DIALOGUE_OVERTIME' in e for e in validate_request(r)))
    def test_missing_asset_is_not_ready(self):
        r=fixture();a=materialize(r,self.root/'input');(a/r['assets'][0]['file']).unlink()
        with self.assertRaisesRegex(GateError,'ASSET_FILE_MISSING'):compile_project(r,a)
    def test_ambiguous_asset_is_not_ready(self):
        r=fixture();a=materialize(r,self.root/'input');f=a/r['assets'][0]['file'];p=a/'one'/f.name;p.parent.mkdir();f.rename(p)
        q=a/'two'/f.name;q.parent.mkdir();q.write_bytes(p.read_bytes())
        with self.assertRaisesRegex(GateError,'ASSET_AMBIGUOUS'):compile_project(r,a)
    def test_state_tampering_rejected(self):
        docs,md=self.compile(fixture());s=docs['07_spatial_locks.json']['states']['SEG002_CURRENT'];s['character_positions']['CHAR_A']['x_m']=9
        self.assertTrue(any('LOCK_REQUIRED' in e or 'SPATIAL_DERIVED' in e for e in validate_pack(docs,md,self.root/'input/assets')))
    def test_duplicate_shot_and_gap(self):
        r=fixture();r['segments'][1]['shots'][0]['shot_id']='SH001';r['segments'][0]['shots'][1]['start_s']=2.7
        errors=validate_request(r);self.assertIn('GLOBAL_SHOT_ID_DUPLICATE',errors);self.assertTrue(any('SHOT_GAP' in e for e in errors))
    def test_axis_change_relocks(self):
        r=fixture();r['segments'][1]['before_events']=[{'op':'axis','camera_side':'north','authorized':True,
                                                     'description':bi('经明确空间建立后换到轴线另一侧','Cross to the other side of the axis after an explicit spatial establishment')}]
        self.assertEqual(self.lock_count(r),2)
    def test_unreliable_closeups_relock(self):
        r=fixture();r['segments'][1]['spatial_unreliable']=True;self.assertEqual(self.lock_count(r),2)
    def test_review_drift_relocks(self):
        r=fixture();r['segments'][1]['review_drift']=True;self.assertEqual(self.lock_count(r),2)
    def test_action_event_cannot_repeat(self):
        r=fixture();e={'op':'action','at_s':4.7,'event_id':'TOUCH01','count':1,'phase':'complete','description':bi('完成一次轻触','Complete one gentle touch')}
        r['segments'][0]['events']=[e];r['segments'][1]['events']=[e]
        with self.assertRaisesRegex(GateError,'ACTION_REPEATED'):self.compile(r)
    def test_atomic_export_rejects_without_partial_pack(self):
        r=fixture();r['segments'][0]['shots'][0]['end_s']=2.7;a=materialize(r,self.root/'input');out=self.root/'bad'
        with self.assertRaises(GateError):export_project(r,a,out)
        self.assertFalse(out.exists())


if __name__=='__main__':unittest.main()
