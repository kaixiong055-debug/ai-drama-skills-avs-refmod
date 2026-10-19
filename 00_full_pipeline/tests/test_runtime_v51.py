import copy
from pathlib import Path
import tempfile
import unittest
from engine.common import bi
from engine.pipeline import compile_project
from engine.runtime import render_runtime_pack,validate_runtime_pack,runtime_budget_report
from engine.redundancy import RUNTIME_SECTIONS,sections,validate_prompt_redundancy,semantic_deduplicate,budget_warnings
from engine.validator import parse_md
from examples.fixtures import fixture,materialize


class RuntimeV51Tests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def compile(self,r=None):
        r=r or fixture();docs,full=compile_project(r,materialize(r,self.root))
        return docs,full,render_runtime_pack(docs)
    def test_runtime_bilingual_canonical_and_ownership(self):
        docs,full,md=self.compile();self.assertEqual(validate_runtime_pack(docs,md),[])
        cn=parse_md(md['H3_RUNTIME_CN.md'],'cn');en=parse_md(md['H3_RUNTIME_EN.md'],'en')
        self.assertEqual(list(cn),list(en))
        for block in en.values():
            self.assertEqual(list(sections(block)),RUNTIME_SECTIONS)
            self.assertEqual(block.count('camera_side='),1)
            self.assertEqual(block.count('dialogue_axis='),1)
            self.assertEqual(block.count('geometry.door_positions.ENTRY_DOOR='),1)
            self.assertNotIn('physical_continuity_locks:',block)
        self.assertLess(len(md['H3_RUNTIME_EN.md']),len(full['H3_PROMPTS_EN.md'])*.55)
    def test_any_segment_is_independent(self):
        docs,full,md=self.compile();block=parse_md(md['H3_RUNTIME_EN.md'],'en')['SEG003']
        for fact in ['Gu Yanchuan','Lin Wanqing','a black office suit','screen_position=screen left','screen_position=screen right','eyeline=',
                     'geometry.door_positions.ENTRY_DOOR','door_states:', 'Hidden LOCK: LOCK_SC01_A01','continuation_source=SEG002',
                     'tail_frames=22','AddGuide.frame_idx=0','<Picture 1>','<d>[Chinese] 你笑了？</d>','end_state: SEG003_END']:
            self.assertIn(fact,block)
        self.assertNotRegex(block,r'same as above|same as previous|参考前文|沿用上一段')
    def test_dialogue_only_in_audio_owner(self):
        _,_,md=self.compile();block=parse_md(md['H3_RUNTIME_EN.md'],'en')['SEG001'];parts=sections(block)
        self.assertEqual(block.count('<d>'),2)
        self.assertEqual(parts['dialogue_and_audio'].count('<d>'),2)
        self.assertNotIn('<d>',parts['shot_timeline'])
    def test_corrupted_translation_and_timing_rejected(self):
        docs,_,md=self.compile();bad=dict(md);bad['H3_RUNTIME_EN.md']=bad['H3_RUNTIME_EN.md'].replace('0.000–2.500s','0.000–2.600s',1)
        errors=validate_runtime_pack(docs,bad)
        self.assertTrue(any('BILINGUAL_TIMELINE' in e for e in errors))
        self.assertTrue(any('NOT_CANONICAL' in e for e in errors))
    def test_sound_count_window_once_and_completion_survives(self):
        r=fixture();r['segments'][0]['events']=[{'op':'sound','at_s':1.2,'event_id':'BELL01','count':3,'window_start':.2,'window_end':1.2,
            'description':bi('三声分离门铃','three separate bell rings'),'termination':bi('第三声后完全停止','stop completely after the third ring')}]
        _,_,md=self.compile(r);blocks=parse_md(md['H3_RUNTIME_EN.md'],'en');block=blocks['SEG001']
        self.assertEqual(block.count('three separate bell rings'),1)
        self.assertIn('count=3; window=0.200–1.200s',sections(block)['dialogue_and_audio'])
        self.assertIn('completed_sounds: BELL01',blocks['SEG002'])
    def test_prop_transfer_end_state_and_holder_preserved(self):
        r=fixture();r['assets'].append({'asset_id':'PROP_SHIRT','file':'PROP_SHIRT.png','role':'PROP','direct_bindable':True,'description':bi('白衬衫','white shirt')})
        r['scenes'][0]['prop_asset_ids']={'SHIRT':'PROP_SHIRT'}
        r['scenes'][0]['initial_state']['major_props']={'SHIRT':{'holder':'CHAR_A.right_hand','state':bi('握住','held'),'valid_until_changed':True}}
        r['segments'][0]['events']=[{'op':'prop','at_s':4.8,'prop_id':'SHIRT','from_holder':'CHAR_A.right_hand','holder':'CHAIR','state':bi('搭在椅背','draped on the chair'),
            'description':bi('用右手放到椅背','Place it on the chair using the right hand')}]
        docs,_,md=self.compile(r);self.assertEqual(validate_runtime_pack(docs,md),[])
        block=parse_md(md['H3_RUNTIME_EN.md'],'en')['SEG001']
        self.assertIn('holder=Gu Yanchuan right hand',block);self.assertIn('holder=CHAIR',block)
        self.assertEqual(block.count('Place it on the chair using the right hand'),1)
    def test_relative_no_fabricated_metric_full_or_runtime(self):
        _,full,md=self.compile()
        for doc in [full['H3_PROMPTS_EN.md'],md['H3_RUNTIME_EN.md']]:
            self.assertNotIn('meters apart',doc);self.assertNotIn('ground-plane position',doc)
            self.assertIn('RELATIVE',doc)
    def test_full_and_runtime_preserve_verified_metric(self):
        r=fixture();r['scenes'][0]['spatial_measurement']={'measurement_mode':'METRIC','confidence':'HIGH',
            'provenance':{'source_type':'USER_SPECIFIED','source_id':'TEST_DIMENSIONS','evidence':'User explicitly supplied all ground-plane coordinates'},
            'constraints':[{'subject_id':'CHAR_A','reference_id':'ENTRY_DOOR','distance_m':1.2}]}
        _,full,md=self.compile(r)
        self.assertIn('1.8 meters apart',full['H3_PROMPTS_EN.md']);self.assertIn('distance=1.8m',md['H3_RUNTIME_EN.md'])
        self.assertIn('1.2 meters from ENTRY_DOOR',md['H3_RUNTIME_EN.md'])
    def test_chinese_metric_provenance_is_auditable_without_english_leak(self):
        r=fixture();r['scenes'][0]['spatial_measurement']={'measurement_mode':'METRIC','confidence':'HIGH',
            'provenance':{'source_type':'USER_SPECIFIED','source_id':'用户尺寸表','evidence':'用户明确提供：两人相距1.8米。'}}
        docs,full,md=self.compile(r)
        self.assertIn('用户明确提供',full['H3_PROMPTS_CN.md'])
        self.assertNotIn('用户明确提供',full['H3_PROMPTS_EN.md']);self.assertNotIn('用户尺寸表',md['H3_RUNTIME_EN.md'])
        self.assertEqual(validate_runtime_pack(docs,md),[])
        bad=dict(md);bad['H3_RUNTIME_EN.md']=bad['H3_RUNTIME_EN.md'].replace('summary:\n','summary:\n错误的中文描述\n',1)
        self.assertTrue(any('ENGLISH_BODY_CONTAINS_CHINESE' in e for e in validate_runtime_pack(docs,bad)))
    def test_intermediate_moves_returning_to_baseline_are_preserved(self):
        r=fixture();r['segments'][0]['events']=[{'op':'move','at_s':at,'character_id':'CHAR_A','position':{'x_m':x},'path':path,
            'description':bi('按登记路径走动','Walk along the registered path')} for at,x,path in [(1.0,3.0,['LEFT','RIGHT']),(4.0,0.0,['RIGHT','LEFT'])]]
        _,_,md=self.compile(r);block=parse_md(md['H3_RUNTIME_EN.md'],'en')['SEG001']
        self.assertIn('intermediate_state @1.000s:',block)
        self.assertIn('Gu Yanchuan (CHAR_A): screen_position=screen right',sections(block)['continuity_state'])
        self.assertIn('At 5s there is no state change',block)
        self.assertIn('path=LEFT, RIGHT',block);self.assertIn('path=RIGHT, LEFT',block)
    def test_five_people_all_present_once(self):
        docs,_,md=self.compile(fixture(5));block=parse_md(md['H3_RUNTIME_EN.md'],'en')['SEG001']
        for cid in ['CHAR_A','CHAR_B','CHAR_C','CHAR_D','CHAR_E']:
            self.assertEqual(sections(block)['spatial_state'].count('('+cid+'): screen_position='),1)
        self.assertEqual(validate_runtime_pack(docs,md),[])
    def test_keyframe_is_picture_reference_not_new_entity_subject(self):
        from examples.fixtures import PNG
        r=fixture(2,1);a=materialize(r,self.root);(a/'SHOT_REF.png').write_bytes(PNG)
        r['segments'][0]['shot_keyframes']=[{'shot_id':'SH001','keyframe_type':'SHOT_KEYFRAME','output':'SHOT_REF.png'}]
        docs,full=compile_project(r,a);runtime=render_runtime_pack(docs)
        for rendered in [full['H3_PROMPTS_EN.md'],runtime['H3_RUNTIME_EN.md']]:
            block=parse_md(rendered,'en')['SEG001']
            definitions=block.split('subject_definitions:\n',1)[1].split('\n\nsummary:',1)[0]
            self.assertNotIn('<Subject 4>',definitions)
            self.assertIn('<Picture 4>',block)
            self.assertIn('must not override identity MASTER',block)
        self.assertEqual(validate_runtime_pack(docs,runtime),[])
    def test_duplicate_spatial_and_axis_fail(self):
        _,_,md=self.compile();block=parse_md(md['H3_RUNTIME_EN.md'],'en')['SEG001']
        duplicate='Gu Yanchuan (CHAR_A): screen_position=screen left; depth=foreground; facing=screen right; eyeline=Lin Wanqing.'
        block=block.replace('camera_plan:\n','camera_plan:\n'+duplicate+'\n')
        self.assertTrue(any('SPATIAL_REPEATED' in e for e in validate_prompt_redundancy(block)))
        block=block.replace('camera_plan:\n','camera_plan:\ndialogue_axis=locked east-west axis\n')
        self.assertTrue(any('AXIS_REDEFINED' in e for e in validate_prompt_redundancy(block)))
    def test_conflicting_position_facing_camera_geometry_fail(self):
        base='spatial_state:\nGu Yanchuan (CHAR_A): screen_position=screen left; facing=screen right; eyeline=Lin Wanqing.\ngeometry.door_positions.ENTRY_DOOR=rear left\ncamera_plan:\ncamera_side=south; dialogue_axis=locked east-west axis\n'
        edits=['Gu Yanchuan (CHAR_A): screen_position=screen right; facing=screen right; eyeline=Lin Wanqing.',
               'Gu Yanchuan (CHAR_A): screen_position=screen left; facing=screen left; eyeline=Lin Wanqing.',
               'camera_side=north','geometry.door_positions.ENTRY_DOOR=rear right']
        for edit in edits:self.assertTrue(any('FACT_CONFLICT' in e for e in validate_prompt_redundancy(base+edit)),edit)
    def test_negative_repetition_and_similar_spatial_repetition(self):
        self.assertIn('PROMPT:RUNTIME_NEGATIVE_REPEATED',validate_prompt_redundancy('negative_rules:\nDo not spawn props.\nDo not spawn props.'))
        block='spatial_state:\nGu Yanchuan stays at screen left, in the foreground, facing the listener.\ncamera_plan:\nGu Yanchuan stays at screen left, in the foreground, facing his listener.'
        self.assertTrue(any('SPATIAL_REPEATED' in e for e in validate_prompt_redundancy(block)))
    def test_soft_budget_warns_and_dedup_never_truncates_unique_state(self):
        r=fixture();r['segments'][0]['summary']=bi('维持客厅的原有空间关系。'*2000,'Keep the established living-room spatial arrangement. '*700)
        docs,_,md=self.compile(r);report=runtime_budget_report(docs,md)
        self.assertTrue(any('RUNTIME_PROMPT_OVERVERBOSE' in e for e in report['warnings']))
        self.assertGreater(report['units']['SEG001']['en_removed_repeated_characters'],20000)
        block=parse_md(md['H3_RUNTIME_EN.md'],'en')['SEG001']
        self.assertIn('geometry.furniture_positions.SOFA=',block);self.assertIn('<d>[Chinese] 你笑了？</d>',block)
        unique='summary:\n'+''.join('Unique specific fact '+str(i)+'. ' for i in range(2000))
        self.assertIn('Unique specific fact 1999.',semantic_deduplicate(unique))
    def test_budget_warning_does_not_fail_legitimate_complex_runtime(self):
        r=fixture();r['project']['runtime_prompt_budget']={'cn':{'target_min':2500,'target_max':5000},'en':{'target_min':3500,'target_max':8000,'warning_chars':100},'semantic_completeness_first':True}
        docs,_,md=self.compile(r);self.assertTrue(runtime_budget_report(docs,md)['warnings']);self.assertEqual(validate_runtime_pack(docs,md),[])


if __name__=='__main__':unittest.main()
