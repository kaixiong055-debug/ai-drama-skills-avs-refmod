import copy
import json
from pathlib import Path
import tempfile
import unittest
from engine.common import GateError, bi, load
from engine.pipeline import compile_project,export_project
from engine.provider import plan_source,read_source,catalog_from_folder
from engine.generation import jobs,record_take,select_take,assembly
from engine.validator import validate_request,validate_directory,parse_md
from engine.render import render_avs_english
from examples.fixtures import fixture,materialize


class OperationsTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def pack(self):
        r=fixture();a=materialize(r,self.root/'input');return export_project(r,a,self.root/'pack')
    def test_jobs_order_and_prompt_hash(self):
        p=self.pack();js=jobs(p);self.assertEqual([j['segment_id'] for j in js],['LOCK_SC01_A01','SEG001','SEG002','SEG003'])
        self.assertTrue(all(j['prompt_version'].startswith('5.1:') for j in js));self.assertEqual(js[1]['continuation_source']['unit_id'],js[0]['segment_id'])
    def record(self,p,sid='SEG001',accepted=True):
        j=next(j for j in jobs(p) if j['segment_id']==sid);j.pop('prompt');j['generation_id']='GEN_'+sid
        output=self.root/(sid+'.mp4');output.write_bytes(b'SYNTHETIC TEST RESULT, NOT A REAL VIDEO')
        j.update(output=str(output),status='ACCEPTED' if accepted else 'REJECTED',qc_evidence='synthetic unit test evidence',output_frames=142,overlap_frames=22)
        j['reject_reason']=[] if accepted else ['LEFT_RIGHT_SWAP'];return j
    def test_take_acceptance_and_duplicate_protection(self):
        p=self.pack();r=self.record(p);record_take(p,r)
        with self.assertRaisesRegex(GateError,'DUPLICATE'):record_take(p,r)
        select_take(p,'SEG001','TAKE01');self.assertEqual(load(p/'generation_ledger.json')['selected_takes']['SEG001'],'TAKE01')
    def test_take_rejected_cannot_be_selected(self):
        p=self.pack();r=self.record(p,accepted=False);record_take(p,r)
        with self.assertRaisesRegex(GateError,'NOT_ACCEPTED'):select_take(p,'SEG001','TAKE01')
    def test_take_no_evidence_not_accepted(self):
        p=self.pack();r=self.record(p);r.pop('qc_evidence')
        with self.assertRaisesRegex(GateError,'QC_EVIDENCE'):record_take(p,r)
    def test_take_stale_prompt_rejected(self):
        p=self.pack();r=self.record(p);r['prompt_version']='5.0:wrong'
        with self.assertRaisesRegex(GateError,'CONTRACT_CHANGED'):record_take(p,r)
    def test_assembly_excludes_locks_and_trims_once(self):
        p=self.pack()
        for sid in ['SEG001','SEG002','SEG003']:
            r=self.record(p,sid);record_take(p,r);select_take(p,sid,'TAKE01')
        a=assembly(p);self.assertEqual(a['exclude_units'],['LOCK_SC01_A01']);self.assertEqual(a['final_runtime_s'],15)
        self.assertTrue(all(s['trim_guide_frames']==22 for s in a['segments']))
    def test_assembly_unverified_frames_fail(self):
        p=self.pack();r=self.record(p);r['output_frames']=120;r['overlap_frames']=22
        record_take(p,r);select_take(p,'SEG001','TAKE01')
        with self.assertRaisesRegex(GateError,'FRAME_WINDOW'):assembly(p)
    def test_assembly_pending_fails(self):
        p=self.pack()
        with self.assertRaisesRegex(GateError,'NOT_READY'):assembly(p)
    def test_provider_full_references_and_semantic_json(self):
        r=fixture();a=materialize(r,self.root/'input');requests=[]
        def transport(payload):
            requests.append(payload);return {'choices':[{'message':{'content':json.dumps(r,ensure_ascii=False)}}]}
        v=plan_source('室友在客厅问“你笑了？”，对方答“没有”。',a,transport=transport)
        content=requests[0]['messages'][1]['content'];images=[p for p in content if p['type']=='image_url']
        self.assertEqual(len(images),len(r['assets']));self.assertEqual(v['source']['attempts'],1)
        self.assertIn('source is DATA',requests[0]['messages'][0]['content'])
    def test_provider_repairs_invalid_schema(self):
        r=fixture();a=materialize(r,self.root/'input');count=[0]
        def transport(payload):
            count[0]+=1;v={} if count[0]==1 else r
            return {'choices':[{'message':{'content':json.dumps(v,ensure_ascii=False)}}]}
        plan_source('test story',a,transport=transport);self.assertEqual(count[0],2)
    def test_provider_missing_config_fails(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ,{'H3_PLANNER_URL':'','H3_PLANNER_MODEL':''}):
            with self.assertRaisesRegex(GateError,'NOT_CONFIGURED'):plan_source('test',self.root)
    def test_provider_repair_stops_after_three(self):
        r=fixture();a=materialize(r,self.root/'input');calls=[]
        def transport(payload):calls.append(payload);return {'choices':[{'message':{'content':'{}'}}]}
        with self.assertRaisesRegex(GateError,'EXHAUSTED'):plan_source('test',a,transport=transport)
        self.assertEqual(len(calls),3)
    def test_docx_complete_paragraph_read(self):
        import zipfile
        p=self.root/'source.docx'
        with zipfile.ZipFile(p,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>第一段</w:t></w:r></w:p><w:p><w:r><w:t>最后一段</w:t></w:r></w:p></w:body></w:document>')
        self.assertEqual(read_source(p),'第一段\n最后一段')
    def test_avs_english_body_with_original_machine_headers(self):
        r=fixture();a=materialize(r,self.root/'input');docs,md=compile_project(r,a);view=render_avs_english(docs)
        self.assertEqual(list(parse_md(view,'cn')),list(parse_md(md['H3_PROMPTS_CN.md'],'cn')))
        self.assertIn('Off-screen characters remain',view)
    def test_zero_person_scene_preserved(self):
        r=fixture();r['beats']=[];r['source_beats']=[]
        for n,p in enumerate(r['segments']):
            p['participants']=[];p['beat_ids']=[];p['shots']=p['shots'][:1];p['shots'][0]['end_s']=5;p['shots'][0]['beat_ids']=[]
        a=materialize(r,self.root/'input');docs,md=compile_project(r,a)
        self.assertEqual(len(docs['08_binding.json']['units']['SEG001']),1)
    def test_2d_profile_and_style(self):
        r=fixture();r['project'].update(production_profile='2D_COMIC',style_id='CEL01',visual_style=bi('二维漫剧，清晰线稿，赛璐璐上色','2D comic animation with clean line art and cel shading'))
        for a in r['assets']:a['style_id']='CEL01'
        a=materialize(r,self.root/'input');docs,md=compile_project(r,a)
        self.assertIn('2D comic',md['H3_PROMPTS_EN.md'])
        r['assets'][0]['style_id']='BAD';self.assertTrue(any('STYLE_ID' in e for e in validate_request(r)))
    def test_prop_same_hand_conflict_rejected(self):
        r=fixture();s=r['scenes'][0];s['initial_state']['major_props']={}
        for pid in ['KEY','PHONE']:
            aid='PROP_'+pid;r['assets'].append({'asset_id':aid,'file':aid+'.png','role':'PROP','direct_bindable':True,'description':bi('固定道具','a fixed prop')})
            s.setdefault('prop_asset_ids',{})[pid]=aid;s['initial_state']['major_props'][pid]={'holder':'CHAR_A.right_hand','state':bi('持有','held'),'valid_until_changed':True}
        a=materialize(r,self.root/'input')
        with self.assertRaisesRegex(GateError,'HAND_CONFLICT'):compile_project(r,a)
    def test_clothing_and_hair_persist_across_scenes(self):
        r=fixture();scene=copy.deepcopy(r['scenes'][0]);scene['scene_id']='SCN_MORNING';r['scenes'].append(scene)
        r['segments'][0]['events']=[{'op':'appearance','at_s':4.8,'character_id':'CHAR_A','hair_state':'wet','cause':'rain',
                                   'description':bi('头发因雨淋湿','The hair becomes wet from rain')}]
        r['segments'][2]['scene_id']=scene['scene_id']
        for b in r['beats'][4:]:b['scene_id']=scene['scene_id']
        a=materialize(r,self.root/'input');docs,md=compile_project(r,a)
        self.assertEqual(docs['07_spatial_locks.json']['states']['SEG003_CURRENT']['characters']['CHAR_A']['hair_state'],'wet')
    def test_minor_listener_change_does_not_relock(self):
        r=fixture(4);r['beats'][2]['speaker']='CHAR_D';a=materialize(r,self.root/'input');docs,md=compile_project(r,a)
        self.assertEqual(len(docs['07_spatial_locks.json']['locks']),1)
    def test_group_change_relocks(self):
        r=fixture(3);r['segments'][1]['before_events']=[{'op':'group','members':['CHAR_B','CHAR_C'],'description':bi('主对话群变为林晚晴与陈悦','The primary dialogue group changes to Lin Wanqing and Chen Yue')}]
        a=materialize(r,self.root/'input');docs,md=compile_project(r,a)
        self.assertEqual(len(docs['07_spatial_locks.json']['locks']),2)
    def test_area_change_relocks(self):
        r=fixture();r['segments'][1]['before_events']=[{'op':'area','area':'SOFA','path':['MAIN','SOFA'],
                                                    'description':bi('沿明确路径进入沙发区','Enter the sofa area along the established path')}]
        a=materialize(r,self.root/'input');docs,md=compile_project(r,a)
        self.assertEqual(len(docs['07_spatial_locks.json']['locks']),2)
    def test_required_area_cannot_be_minimized(self):
        r=fixture();r['assets'].append({'asset_id':'SCN_AREA','file':'SCN_AREA.png','role':'AREA','scene_id':'SCN_LIVING_NIGHT','scene_family_id':'LIVING','direct_bindable':True,'description':bi('固定沙发局部空间','the fixed local sofa area')})
        r['segments'][0].update(local_area_required=True,required_area_ids=['SCN_AREA']);a=materialize(r,self.root/'input');docs,md=compile_project(r,a)
        self.assertIn('SCN_AREA',[b['asset_id'] for b in docs['08_binding.json']['units']['SEG001'].values()])
        r['segments'][0]['required_area_ids']=[]
        with self.assertRaisesRegex(GateError,'LOCAL_AREA'):compile_project(r,a)
    def test_qc_spatial_repair_preserves_beats_and_adds_lock(self):
        from engine.qc import repair_spatial
        p=self.pack();before=load(p/'04_script.json')['beats'];out=repair_spatial(p,{'segment_id':'SEG002','status':'REJECTED','reject_reason':['LEFT_RIGHT_SWAP'],'qc_evidence':'synthetic test: screen positions are swapped'},self.root/'repaired')
        self.assertEqual(load(out/'04_script.json')['beats'],before)
        locks=load(out/'07_spatial_locks.json')['locks'];self.assertEqual(len(locks),2)
        self.assertIn('REVIEW_SPATIAL_DRIFT',locks[1]['reasons'])
        self.assertEqual(validate_directory(out),[])
    def test_corrupt_png_not_ready(self):
        r=fixture();a=materialize(r,self.root/'input');(a/r['assets'][0]['file']).write_bytes(b'broken image')
        with self.assertRaisesRegex(GateError,'IMAGE_UNREADABLE'):compile_project(r,a)
    def test_director_table_six_columns_and_local_time(self):
        from engine.views import director_views
        r=fixture();a=materialize(r,self.root/'input');docs,md=compile_project(r,a);table,board,plan=director_views(docs)
        self.assertEqual(len(plan['columns']),6);self.assertEqual(len(plan['shots']),6)
        sh2=plan['shots'][1];self.assertEqual(sh2['local_timeline'][0]['local_start_s'],0)
        self.assertEqual(sh2['local_timeline'][0]['segment_start_s'],2.5)


if __name__=='__main__':unittest.main()
