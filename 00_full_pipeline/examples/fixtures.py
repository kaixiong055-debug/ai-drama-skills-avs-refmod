"""Small synthetic assets and complete requests for deterministic engineering tests."""
import struct
import zlib
import copy
from pathlib import Path
from engine.common import bi, save

def png_fixture():
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    raw=b''.join(b'\x00'+bytes([80,120,160])*32 for _ in range(32))
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',32,32,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
PNG=png_fixture()


def fixture(count=2, segments=3):
    ids=[f'CHAR_{chr(65+i)}' for i in range(count)]
    cast=[];assets=[]
    for i,cid in enumerate(ids):
        cn=['顾言川','林晚晴','陈悦','周明','苏岚'][i];en=['Gu Yanchuan','Lin Wanqing','Chen Yue','Zhou Ming','Su Lan'][i]
        cast.append({'character_id':cid,'name':bi(cn,en),'identity':bi('约28岁的成年人，保持原面部和身材比例','an adult approximately 28 years old with consistent facial features and body proportions'),
                     'hairstyle':bi('整齐的黑发','neatly styled black hair'),'default_wardrobe':'OFFICE','hair_state':'dry',
                     'wardrobes':{'OFFICE':{'description':bi('黑色通勤西装','a black office suit'),'runtime_asset_id':cid+'_H3_OFFICE'}}})
        assets.append({'asset_id':cid+'_H3_OFFICE','file':cid+'_H3_OFFICE.png','role':'H3_RUNTIME','character_id':cid,'wardrobe':'OFFICE','direct_bindable':True,
                       'description':bi(cn+'的身份与黑色通勤西装',en+"'s identity and black office suit")})
    assets += [{'asset_id':'SCN_LIVING_MASTER','file':'SCN_LIVING_MASTER.png','role':'MASTER','scene_id':'SCN_LIVING_NIGHT','scene_family_id':'LIVING','direct_bindable':True,
                'description':bi('客厅建筑、门窗、沙发、茶几及固定空间几何','the living-room architecture, doors, windows, sofa, coffee table, and fixed spatial geometry')}]
    scene={'scene_id':'SCN_LIVING_NIGHT','scene_variant':'MASTER','area':'MAIN','name':bi('夜晚客厅','the living room at night'),
           'time_of_day':bi('晚上','Night'),'soundscape':bi('低声室内环境底声和轻微呼吸','quiet indoor room tone and subtle breathing'),
           'master_asset_id':'SCN_LIVING_MASTER', 'initial_state':{
               'character_positions':{c:{'x_m':round(i*1.8,2),'y_m':0.0 if i<2 else .8 if i<4 else 1.6,
                                        'depth':'foreground' if i<2 else 'midground' if i<4 else 'background',
                                        'facing':'right' if i==0 else 'left','eyeline_target':ids[1] if i==0 and count>1 else ids[0] if i>0 else 'forward'} for i,c in enumerate(ids)},
               'fixed_architecture':{'walls':bi('矩形客厅；北墙固定','rectangular living room; fixed north wall')},
               'door_positions':{'ENTRY_DOOR':bi('后方左侧','rear left')},
               'window_positions':{'WINDOW':bi('后方右侧','rear right')},
               'furniture_positions':{'SOFA':bi('位于角色右侧后方','behind the characters on the right'),'TABLE':bi('前景中央','foreground center'),'CHAIR':bi('左侧中景','midground left')},
               'entrance_positions':{'ENTRY_DOOR':bi('后方左侧进场','enter from rear left')},
               'exit_positions':{'ENTRY_DOOR':bi('后方左侧离场','exit toward rear left')},
               'door_states':{'ENTRY_DOOR':'closed'}, 'major_props':{},'camera_side':'south','dialogue_axis':'locked_east_west','dialogue_group':ids[:2]}}
    r={'schema_version':'5.0','source':{'type':'confirmed_storyboard','description':'synthetic regression fixture; no actual video quality claim'},
       'project':{'title':bi('室友空间连续性示例','Roommate spatial continuity example'),'episode_id':'EP01','episode_name':bi('第一章','Chapter 1'),
                  'production_profile':'DRAMA_DIALOGUE','visual_style':bi('自然写实漫剧，稳定人物与室内光线','A natural cinematic drama with consistent characters and stable indoor lighting'),
                  'runtime_budget':{'profile':'BATCH_COMPACT','target_seconds':180,'max_seconds':240}},
       'cast':cast,'assets':assets,'scenes':[scene],'beats':[],'segments':[],'source_beats':[]}
    for n in range(1,segments+1):
        bs=[];shots=[]
        for k,cid in enumerate(ids[:2]):
            bid=f'B{(n-1)*2+k+1:03d}';bs.append(bid)
            r['beats'].append({'beat_id':bid,'scene_id':scene['scene_id'],'speaker':cid,
                               'dialogue':'你笑了？' if k==0 else '没有。','spoken_language':'Chinese',
                               'start_s':.2 if k==0 else 2.7,'end_s':2.2 if k==0 else 4.5,
                               'emotion':bi('克制、自然','restrained and natural'),
                               'action':bi('保持原位，说完短句','Remain in the established position and deliver the short line'),
                               'source_beat_ids':['SRC_'+bid]})
            r['source_beats'].append({'beat_id':'SRC_'+bid,'preservation':'EXACT'})
            shots.append({'shot_id':f'SH{(n-1)*2+k+1:03d}','start_s':k*2.5,'end_s':(k+1)*2.5,'beat_ids':[bid],
                          'shot_scale':'close_up','lens_mm':85,'camera_height_m':1.5,'camera_movement':'locked_off',
                          'camera_angle':bi('同轴线侧的侧前方反打','a three-quarter reverse angle on the same side of the dialogue axis'),
                          'composition':bi('当前说话人的面部与肩部可见，其他人仍在原位画外','Frame the current speaker’s face and shoulders; all others remain off-screen in their established positions'),
                          'lighting':bi('窗侧柔光，室内补光，方向保持稳定','soft window-side key light and consistent indoor fill'),
                          'depth_of_field':bi('浅景深但面部清晰','shallow depth of field with a clearly readable face'),
                          'action':bi('说话人轻微呼吸，视线保持指向听者','The speaker breathes subtly and keeps the eyeline toward the listener'),
                          'cut_reason':bi('呈现当前说话人的细微反应','show the current speaker’s subtle reaction')})
        if count==1:
            shots[0]['end_s']=5
        r['segments'].append({'segment_id':f'SEG{n:03d}','scene_id':scene['scene_id'],'duration_s':5,
                              'participants':ids[:],'beat_ids':bs,'shots':shots,
                              'title':bi('室友短句对白','A short exchange between roommates'),
                              'summary':bi('角色在固定客厅位置完成一问一答','The characters exchange a question and answer from their fixed living-room positions'),
                              'detailed_description':bi('表情自然克制，动作保持轻微；画外人物不移动。','Use natural, restrained expressions and subtle movements. Off-screen characters do not move.'),
                              'before_events':[],'events':[]})
    return r


def materialize(request, folder):
    folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
    assets=folder/'assets';assets.mkdir(exist_ok=True)
    for a in request['assets']:
        p=assets/a['file'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(PNG)
    save(folder/'project_input.json',request)
    return assets
