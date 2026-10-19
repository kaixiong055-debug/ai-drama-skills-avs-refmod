"""Cross-layer contracts, event replay, language parity and fail-closed Ready Gate."""
import copy
import hashlib
import re
from pathlib import Path
from .common import FILES, PROFILES, SECTIONS, GateError, digest, finite, index, load, text
from .spatial import GEOMETRY, apply_event, normalize, signature

HAN = re.compile(r'[\u3400-\u9fff]')
CAMERA_FIELDS = {'lens','lens_mm','shot_scale','camera_height','camera_height_m','camera_angle',
                 'camera_movement','camera_plan','screen_position','screen-left','screen-right','eyeline','composition'}
OPS = {'enter','exit','move','axis','group','area','appearance','prop','door','action','sound'}


def validate_request(r):
    errors=[]
    def need(ok, code):
        if not ok: errors.append(code)
    def bilingual(v, label):
        for lang in ['cn','en']:
            need(isinstance(v,dict) and isinstance(v.get(lang),str) and bool(v[lang].strip()),label+':BILINGUAL_TEXT_MISSING:'+lang)
        if isinstance(v,dict) and isinstance(v.get('en'),str): need(not HAN.search(v['en']),label+':ENGLISH_CONTAINS_CHINESE')
    if not isinstance(r,dict): return ['INPUT_NOT_OBJECT']
    for key in ['project','cast','scenes','assets','beats','segments']:
        need(key in r,'INPUT_MISSING:'+key)
    if errors:return errors
    if r.get('schema_version') not in ['5.0','5.1']: errors.append('INPUT_SCHEMA_VERSION_UNSUPPORTED')
    from .schema import validate_schema
    errors.extend(validate_schema(r, 'request.schema.json'))
    if errors:return errors
    from .measurement import validate_spatial_measurements
    errors.extend(validate_spatial_measurements(r))
    try:
        cast=index(r['cast'],'character_id'); scenes=index(r['scenes'],'scene_id')
        assets=index(r['assets'],'asset_id'); beats=index(r['beats'],'beat_id')
        segments=index(r['segments'],'segment_id')
    except (GateError,TypeError,AttributeError) as exc:return errors+[str(exc)]
    project=r['project']; profile=project.get('production_profile')
    need(profile in PROFILES,'PRODUCTION_PROFILE_INVALID')
    bilingual(project.get('title'),'PROJECT_TITLE'); bilingual(project.get('episode_name'),'EPISODE_NAME')
    bilingual(project.get('visual_style'),'VISUAL_STYLE')
    budget=project.get('runtime_budget',{})
    need(budget.get('profile') in ['BATCH_COMPACT','USER_DEFINED','CONFIRMED'],'RUNTIME_BUDGET_MISSING')
    need(finite(budget.get('max_seconds')) and budget['max_seconds']>=5*len(segments),'RUNTIME_BUDGET_EXCEEDED')
    if budget.get('profile')=='BATCH_COMPACT':
        need(budget.get('target_seconds')==180 and budget.get('max_seconds')==240,'DEFAULT_BUDGET_CHANGED')
    else: need(bool(budget.get('reason')),'RUNTIME_BUDGET_OVERRIDE_REASON_MISSING')
    for cid,c in cast.items():
        for key in ['name','identity','hairstyle']:bilingual(c.get(key),cid+':'+key)
        need(c.get('default_wardrobe') in c.get('wardrobes',{}),cid+':DEFAULT_WARDROBE_MISSING')
        for wid,w in c.get('wardrobes',{}).items():
            bilingual(w.get('description'),cid+':WARDROBE:'+wid)
            need(w.get('runtime_asset_id') in assets,cid+':RUNTIME_ASSET_UNKNOWN')
        # Design boards are registered independently and never substituted for runtime images.
        for k in ['master_asset_id','face4_asset_id','body_asset_id']:
            if c.get(k):need(c[k] in assets,cid+':DESIGN_ASSET_UNKNOWN:'+k)
    families={}
    filenames=[]
    for aid,a in assets.items():
        need(isinstance(a.get('file'),str) and bool(a['file']),aid+':ASSET_FILENAME_MISSING')
        if isinstance(a.get('file'),str):
            filenames.append(a['file']);need(not Path(a['file']).is_absolute() and '..' not in Path(a['file']).parts,aid+':ASSET_PATH_UNSAFE')
        bilingual(a.get('description'),aid+':DESCRIPTION')
        need(a.get('role') in ['MASTER','FACE4','BODY','WARDROBE','H3_RUNTIME','AREA','SHEET','PROP','TRANSITION','STORYBOARD'],aid+':ASSET_ROLE_INVALID')
        if a.get('scene_family_id') and a.get('role') in ['MASTER','AREA','SHEET','TRANSITION']:
            families.setdefault(a['scene_family_id'],set()).add(a.get('file'))
        if profile=='2D_COMIC':
            need(a.get('style_id')==project.get('style_id'),aid+':STYLE_ID_MISMATCH')
    need(len(filenames)==len(set(filenames)),'ASSET_FILENAME_AMBIGUOUS')
    for family,files in families.items():need(len(files)<=9,'SCENE_IMAGE_LIMIT_EXCEEDED:'+family)
    for sid,s in scenes.items():
        for k in ['name','time_of_day','soundscape']:bilingual(s.get(k),sid+':'+k)
        need(s.get('master_asset_id') in assets,sid+':SCENE_MASTER_MISSING')
        if s.get('master_asset_id') in assets:
            need(assets[s['master_asset_id']]['role']=='MASTER',sid+':SCENE_MASTER_ROLE_INVALID')
        for key in GEOMETRY:
            need(isinstance(s.get('initial_state',{}).get(key,s.get(key)),dict),sid+':GEOMETRY_MISSING:'+key)
        for c,p in s.get('initial_state',{}).get('character_positions',{}).items():
            need(c in cast,sid+':INITIAL_CHARACTER_UNKNOWN')
            need(finite(p.get('x_m')) and finite(p.get('y_m')),sid+':POSITION_COORDINATES_INVALID')
            need(p.get('depth') in ['foreground','midground','background'],sid+':POSITION_DEPTH_INVALID')
        for cid,cs in s['initial_state'].get('characters',{}).items():
            need(cid in cast,sid+':INITIAL_APPEARANCE_CHARACTER_UNKNOWN')
            if 'wardrobe' in cs and cid in cast:need(cs['wardrobe'] in cast[cid]['wardrobes'],sid+':INITIAL_WARDROBE_UNKNOWN')
            if 'hair_state' in cs:need(cs['hair_state'] in ['dry','wet'],sid+':HAIR_STATE_INVALID')
            for key in ['pose','clothing_state']:
                if key in cs:bilingual(cs[key],sid+':INITIAL:'+key)
    coverage=[]; global_shots=[]; occurrences=[]
    for bid,b in beats.items():
        need(b.get('scene_id') in scenes,bid+':SCENE_UNKNOWN')
        if b.get('speaker'):need(b['speaker'] in cast,bid+':SPEAKER_UNKNOWN')
        if b.get('dialogue'):need(b.get('speaker') in cast,bid+':DIALOGUE_SPEAKER_MISSING')
        bilingual(b.get('action'),bid+':ACTION')
        def scan(v):
            if isinstance(v,dict):
                for k,x in v.items():
                    if k in CAMERA_FIELDS:errors.append(bid+':SCRIPT_CAMERA_FIELD_FORBIDDEN:'+k)
                    scan(x)
            elif isinstance(v,list):
                for x in v:scan(x)
        scan(b)
    need(list(segments)==[f'SEG{n:03d}' for n in range(1,len(segments)+1)],'SEGMENT_IDS_NOT_CONSECUTIVE')
    for sid,p in segments.items():
        need(p.get('scene_id') in scenes,sid+':SCENE_UNKNOWN')
        participants=p.get('participants',[])
        need(0<=len(participants)<=5 and len(participants)==len(set(participants)),sid+':CAST_COUNT_INVALID')
        need(all(c in cast for c in participants),sid+':UNAUTHORIZED_CHARACTER')
        for k in ['title','summary','detailed_description']:bilingual(p.get(k),sid+':'+k)
        need(p.get('duration_s')==5,sid+':FORMAL_DURATION_NOT_5')
        need(all(b in beats for b in p.get('beat_ids',[])),sid+':BEAT_UNKNOWN')
        coverage+=p.get('beat_ids',[])
        if p.get('jump_risk')=='HIGH':need(bool(p.get('bridge_resolved')),sid+':UNRESOLVED_HIGH_CONTINUITY_JUMP')
        if p.get('screen_direction_unresolved'):errors.append(sid+':SCREEN_DIRECTION_UNRESOLVED')
        if p.get('anatomy_risk') in ['MEDIUM','HIGH']:
            need(bool(p.get('limb_contracts')),sid+':LIMB_ACTION_UNDERSPECIFIED')
            for contract in p.get('limb_contracts',[]):bilingual(contract,sid+':LIMB_CONTRACT')
        for aid in p.get('required_text_asset_ids',[]):
            need(aid in assets and aid in p.get('required_asset_ids',[]),sid+':TEXT_REFERENCE_ASSET_MISSING')
        if p.get('area_trigger')=='sound_only':need(not p.get('local_area_required'),sid+':AUDIO_ONLY_AREA_UNNECESSARY')
        if p.get('primary_listener') is not None:need(p['primary_listener'] in participants,sid+':LISTENER_NOT_PRESENT')
        for target in p.get('off_frame_targets',[]):
            need(target.get('screen_direction') in ['left','right','screen-left','screen-right'],sid+':OFF_FRAME_DIRECTION_INVALID')
        if p.get('text_reference_required'):need(bool(p.get('required_text_asset_ids')),sid+':TEXT_REFERENCE_ASSET_MISSING')
        for display in p.get('display_state_contract',[]):
            need(display.get('asset_id') in p.get('required_text_asset_ids',[]) and bool(display.get('value')),sid+':DISPLAY_STATE_REFERENCE_MISSING')
        for bid in p.get('beat_ids',[]):
            if bid in beats:
                need(beats[bid]['scene_id']==p['scene_id'],sid+':BEAT_SCENE_MISMATCH')
                if beats[bid].get('speaker'):need(beats[bid]['speaker'] in participants,sid+':SPEAKER_NOT_PRESENT')
        shots=p.get('shots',[]);prev=0.0;shot_beats=[]
        need(1<=len(shots)<=PROFILES.get(profile,3),sid+':SHOT_PROFILE_LIMIT')
        if p.get('multi_shot_required'):need(len(shots)>1,sid+':MULTI_SHOT_REQUIRED')
        for sh in shots:
            shid=sh.get('shot_id');global_shots.append(shid)
            need(isinstance(shid,str) and bool(re.fullmatch(r'SH\d{3,}',shid)),sid+':SHOT_ID_INVALID')
            start,end=sh.get('start_s'),sh.get('end_s')
            if not(finite(start) and finite(end)):errors.append(sid+':SHOT_TIME_INVALID');continue
            need(abs(start-prev)<1e-7 and .2<=end-start<=5,sid+':SHOT_GAP_OVERLAP_OR_DURATION')
            need(all(abs(t*1000-round(t*1000))<1e-7 for t in [start,end]),sid+':SHOT_TIME_NOT_MILLISECOND_ALIGNED')
            need(end<=5,sid+':SHOT_OVER_5_SECONDS');prev=end
            need(sh.get('shot_scale') in ['close_up','medium_close','medium','wide','extreme_close_up'],sid+':SHOT_SCALE_INVALID')
            need(finite(sh.get('lens_mm')) and 12<=sh['lens_mm']<=200,sid+':LENS_INVALID')
            need(finite(sh.get('camera_height_m')) and 0<sh['camera_height_m']<=10,sid+':CAMERA_HEIGHT_INVALID')
            need(sh.get('camera_movement') in ['locked_off','push_in','tracking','pan','pull_out'],sid+':MOVEMENT_INVALID')
            for k in ['camera_angle','composition','lighting','depth_of_field','action','cut_reason']:bilingual(sh.get(k),str(shid)+':'+k)
            for bid in sh.get('beat_ids',[]):
                shot_beats.append(bid)
                if bid in beats and beats[bid].get('dialogue'):
                    b=beats[bid];bs,be=b.get('start_s'),b.get('end_s')
                    need(finite(bs) and finite(be) and start<=bs<be<=end,str(shid)+':DIALOGUE_WINDOW_INVALID')
                    if finite(bs) and finite(be):
                        rate={'normal':3.5,'suspense':3,'fast':4}.get(b.get('pace','normal'),3.5)
                        count=len(HAN.findall(b['dialogue'])) if b.get('spoken_language','Chinese')=='Chinese' else len(b['dialogue'].split())*1.4
                        estimate=count/rate
                        need(estimate<=be-bs+.02 and estimate<=4.6,sid+':DIALOGUE_OVERTIME:'+bid)
                        if estimate>4.2:need(p.get('near_static') is True,sid+':DIALOGUE_REQUIRES_NEAR_STATIC')
                        occurrences.append((sid,bs,be,bid))
        need(abs(prev-5)<1e-7,sid+':TIMELINE_NOT_CLOSED')
        need(sorted(shot_beats)==sorted(p.get('beat_ids',[])),sid+':SHOT_BEAT_COVERAGE_MISMATCH')
        local=sorted((a,b,c) for x,a,b,c in occurrences if x==sid)
        need(all(local[i][0]>=local[i-1][1] for i in range(1,len(local))),sid+':DIALOGUE_OVERLAP')
        need(sum(b-a for a,b,c in local)<=4.6,sid+':DIALOGUE_CAPACITY_EXCEEDED')
        if len(local)>5:
            need(all(len(HAN.findall(beats[bid]['dialogue']))<=2 for a,b,bid in local),sid+':TOO_MANY_DIALOGUE_LINES')
        events=p.get('before_events',[])+p.get('events',[])
        for e in events:
            need(e.get('op') in OPS,sid+':EVENT_OP_UNKNOWN');bilingual(e.get('description'),sid+':EVENT_DESCRIPTION')
            if e in p.get('events',[]):need(finite(e.get('at_s')) and 0<=e['at_s']<=5,sid+':EVENT_TIME_INVALID')
            if e.get('op') in ['move','area']:need(bool(e.get('path')),sid+':MOVEMENT_PATH_MISSING')
            if e.get('op')=='sound':
                ws,we=e.get('window_start'),e.get('window_end');ct=e.get('count')
                need(isinstance(ct,int) and not isinstance(ct,bool) and ct>0,sid+':SOUND_COUNT_INVALID')
                need(finite(ws) and finite(we) and 0<=ws<we<=5,sid+':SOUND_WINDOW_INVALID')
                need(e.get('at_s')==we,sid+':SOUND_COMPLETION_TIME_MISMATCH')
                bilingual(e.get('termination'),sid+':SOUND_TERMINATION')
            if e.get('op')=='action':
                need(isinstance(e.get('count',1),int) and e.get('count',1)>0,sid+':ACTION_COUNT_INVALID')
                need(e.get('phase')!='prepare',sid+':PREPARE_ACTION_MUST_NOT_BE_COUNTED')
            if e.get('op')=='appearance':
                need(bool(e.get('cause')),sid+':APPEARANCE_CAUSE_MISSING')
    need(len(global_shots)==len(set(global_shots)),'GLOBAL_SHOT_ID_DUPLICATE')
    need(set(coverage)==set(beats),'BEAT_COVERAGE_INCOMPLETE')
    need(len(coverage)==len(set(coverage)),'BEAT_OCCURRENCE_REUSED')
    source_beats=r.get('source_beats',[])
    source_ids=set()
    for b in r['beats']:source_ids.update(b.get('source_beat_ids',[]))
    for sb in source_beats:
        if sb.get('preservation')=='EXACT':need(sb.get('beat_id') in source_ids,'PROTECTED_SOURCE_BEAT_UNCOVERED:'+str(sb.get('beat_id')))
        if sb.get('preservation')=='OMIT_OPTIONAL':need(bool(sb.get('reason')),'OPTIONAL_OMISSION_REASON_MISSING')
    if profile=='2D_COMIC':
        need(bool(project.get('style_id')),'STYLE_ID_MISSING')
        style=project.get('visual_style',{})
        for lang in ['cn','en']:
            s=style.get(lang,'');need(bool(re.search(r'2D|二维',s,re.I)),'2D_STYLE_MISSING')
            # Look at positive style declarations only, not negated terms or dialogue.
            need(not re.search(r'(?<!no )\b(?:photorealistic|live-action|Pixar)\b|真人摄影|三维渲染',s,re.I),'POSITIVE_2D_STYLE_CONFLICT')
    return list(dict.fromkeys(errors))


def validate_pack(docs, md, asset_root):
    errors=[]
    def need(ok,code):
        if not ok:errors.append(code)
    try:
        story,cast_doc,assets_doc,script,board,production,spatial,binding=[docs[n] for n in FILES]
        from .schema import validate_schema
        for doc in [story,cast_doc,assets_doc,script,board,production,spatial,binding]:
            errors.extend(validate_schema(doc,doc['kind']+'.schema.json'))
        if errors:return errors
        request={'schema_version':story['schema_version'],'project':story['project'],'scenes':story['scenes'],
                 'cast':cast_doc['characters'],'assets':assets_doc['assets'],'beats':script['beats'],
                 'segments':board['segments'],'source_beats':story.get('source_beats',[])}
        errors.extend(validate_request(request))
        scenes=index(story['scenes'],'scene_id');cast=index(cast_doc['characters'],'character_id')
        assets=index(assets_doc['assets'],'asset_id');plans=index(board['segments'],'segment_id')
        units=production['units'];states=spatial['states'];locks=index(spatial['locks'],'lock_id')
        need(len(units)==len(plans)==production['final_segment_count'],'PRODUCTION_COUNT_MISMATCH')
        need(production['final_runtime_s']==len(units)*5,'PRODUCTION_RUNTIME_MISMATCH')
        # Each derivative has a content hash of each immediate authoritative parent.
        for doc,parents in [(cast_doc,{'story':story}), (assets_doc,{'story':story,'cast':cast_doc}),
                            (script,{'story':story,'cast':cast_doc,'assets':assets_doc}), (board,{'script':script}),
                            (production,{'storyboard':board,'assets':assets_doc}), (spatial,{'production':production}),
                            (binding,{'spatial_locks':spatial,'assets':assets_doc})]:
            need(doc.get('schema_version')==story['schema_version'],'SCHEMA_VERSION_MISMATCH')
            need(doc.get('lineage')=={k:digest(v) for k,v in parents.items()},'CANONICAL_LINEAGE_MISMATCH:'+doc.get('kind','?'))
        prior=None; prior_unit=None;active_lock=None;anchor_sig=None
        for u in units:
            sid=u['unit_id'];p=plans[sid]
            incoming=states[u['state_ids']['incoming']];current=states[u['state_ids']['current']];end=states[u['state_ids']['end']]
            from .measurement import measurement_for
            for state in [incoming,current,end]:
                need(state.get('spatial_measurement')==measurement_for(scenes[state['scene_id']]),sid+':MEASUREMENT_PROVENANCE_CHANGED')
            need(u['include_in_final'] is True and u['duration_s']==5,sid+':FORMAL_UNIT_INVALID')
            need(u['shot_ids']==[s['shot_id'] for s in p['shots']],sid+':SHOT_IDS_MISMATCH')
            if prior and prior['scene_id']==incoming['scene_id']:need(prior==incoming,sid+':INCOMING_STATE_BREAK')
            check_current=copy.deepcopy(incoming)
            for event in p.get('before_events',[]):check_current=apply_event(check_current,event,cast,scenes)
            check_current['anchor_version']=current['anchor_version']
            need(check_current==current,sid+':CURRENT_STATE_EVENT_REPLAY_MISMATCH')
            if u['spatial_anchor'] not in locks:errors.append(sid+':HIDDEN_LOCK_MISSING');continue
            lock=locks[u['spatial_anchor']];anchor=states[lock['state_id']]
            if lock['before_segment_id']==sid:
                need(lock['include_in_final'] is False and .8<=lock['duration_s']<=1.5,sid+':LOCK_INVALID')
                need(lock['scene_id']==u['scene_id'] and signature(anchor)==signature(current),sid+':LOCK_STATE_MISMATCH')
                need(u['continuation_source']['unit_id']==lock['lock_id'],sid+':FIRST_SEGMENT_NOT_CONTINUING_LOCK')
                need(lock['lock_id']!=active_lock,sid+':LOCK_ID_REUSED')
                active_lock=lock['lock_id'];anchor_sig=signature(anchor)
            else:
                need(active_lock==u['spatial_anchor'],sid+':STALE_LOCK_REFERENCE')
                need(signature(current)==anchor_sig,sid+':LOCK_REQUIRED_AFTER_SPATIAL_CHANGE')
                need(u['continuation_source']['unit_id']==prior_unit,sid+':CONTINUATION_SOURCE_INVALID')
            src=u['continuation_source'];need(src['tail_frames']==22 and src['fps']==24 and src['inherit_audio'] is False,sid+':ADDGUIDE_INVALID')
            replay=copy.deepcopy(current)
            for snap in u['events']:
                need(states[snap['before_state_id']]==replay,sid+':EVENT_INCOMING_MISMATCH')
                replay=apply_event(replay,snap['event'],cast,scenes)
                need(states[snap['after_state_id']]==replay,sid+':EVENT_END_MISMATCH')
            need(replay==end,sid+':END_STATE_REPLAY_MISMATCH')
            for s in [incoming,current,end]:
                need(normalize(s)==s,sid+':SPATIAL_DERIVED_FIELDS_CONFLICT')
                need(set(s['characters'])==set(s['character_positions']),sid+':CHARACTER_STATE_CONFLICT')
                occupied=[]
                for pid, prop in s['major_props'].items():
                    holder=prop.get('holder','')
                    if holder.endswith(('.right_hand','.left_hand')):
                        occupied.append(holder)
                        need(holder.split('.')[0] in s['characters'],sid+':PROP_HOLDER_UNKNOWN')
                    else:
                        fixtures=set().union(*(set(s[k]) for k in GEOMETRY))
                        need(holder in fixtures or holder in s['major_props'] or holder in ['floor','ground'],sid+':PROP_HOLDER_LOCATION_UNKNOWN')
                    need(prop.get('valid_until_changed') is True,sid+':PROP_PERSISTENCE_MISSING')
                need(len(occupied)==len(set(occupied)),sid+':PROP_HOLDER_HAND_CONFLICT')
                for cid,cs in s['characters'].items():need(cs['wardrobe'] in cast[cid]['wardrobes'],sid+':CLOTHING_STATE_CONFLICT')
                need(set(s['dialogue_group']).issubset(s['characters']),sid+':DIALOGUE_GROUP_UNAUTHORIZED')
                for cid,pstate in s['character_positions'].items():
                    target=pstate['eyeline_target']
                    need(target in s['characters'] or target in ['forward','left','right','left_front','right_front','rear_left','rear_right'],sid+':EYELINE_TARGET_UNKNOWN')
            prior,prior_unit=end,sid
        expected_units=set(plans)|set(locks)
        need(set(binding['units'])==expected_units,'BINDING_UNIT_SET_MISMATCH')
        root=Path(asset_root)
        from .binding import resolve_files,bind_unit
        verified_files=resolve_files(assets_doc['assets'],root)
        need(binding['asset_files']==verified_files,'ASSET_FILE_MAP_NOT_CANONICAL')
        allow_stale=story['project'].get('allow_stale_asset',False)
        character_binding_mode=story['project'].get('character_binding_mode','PICTURE')
        for lock in locks.values():
            expected=bind_unit(states[lock['state_id']],scenes,cast,assets,verified_files,
                               plans[lock['before_segment_id']],allow_stale_asset=allow_stale,is_lock=True,character_binding_mode=character_binding_mode)
            need(binding['units'].get(lock['lock_id'])==expected,lock['lock_id']+':BINDING_STATE_REPLAY_MISMATCH')
        for unit in units:
            uid=unit['unit_id'];plan=plans[uid]
            expected=bind_unit(states[unit['state_ids']['current']],scenes,cast,assets,verified_files,plan,
                               allow_stale_asset=allow_stale,character_binding_mode=character_binding_mode)
            for snap in unit['events']:
                extra=bind_unit(states[snap['after_state_id']],scenes,cast,assets,verified_files,plan,
                                allow_stale_asset=allow_stale,character_binding_mode=character_binding_mode)
                for row in extra.values():
                    if row['asset_id'] not in {v['asset_id'] for v in expected.values()}:
                        expected[f'P{len(expected)+1}']=row
            need(binding['units'].get(uid)==expected,uid+':BINDING_STATE_REPLAY_MISMATCH')
        for uid,pictures in binding['units'].items():
            need(list(pictures)==[f'P{n}' for n in range(1,len(pictures)+1)] and len(pictures)<=9,uid+':PICTURE_SLOTS_INVALID')
            for slot,b in pictures.items():
                need(b['asset_id'] in assets,uid+':ASSET_UNKNOWN')
                path=(root/b['file']).resolve()
                need(path.is_relative_to(root.resolve()),uid+':ASSET_PATH_ESCAPE')
                if path.is_file():need(hashlib.sha256(path.read_bytes()).hexdigest()==b['sha256'],uid+':ASSET_HASH_CHANGED')
                else:errors.append(uid+':ASSET_FILE_MISSING:'+b['file'])
        errors+=validate_bilingual(docs,md)
        if story['schema_version']=='5.1':
            from .keyframes import validate_keyframes
            request['shot_keyframes']=board.get('shot_keyframes',[])
            errors.extend(validate_keyframes(request,binding['units']))
            from .asset_dependencies import validate_asset_dependencies
            report=validate_asset_dependencies(assets_doc['assets'],cast_doc['characters'],story['scenes'],binding['units'],
                                               allow_stale_asset=story['project'].get('allow_stale_asset',False))
            errors.extend(report['errors'])
            from .runtime import validate_runtime_pack
            if any(k.startswith('H3_RUNTIME_') for k in md):errors.extend(validate_runtime_pack(docs,md))
    except (KeyError,TypeError,ValueError,AttributeError,OSError) as exc:errors.append('INVALID_PRODUCTION_PACK:'+str(exc))
    return list(dict.fromkeys(errors))


def parse_md(data, lang):
    pattern = (r'^【(?:视频片段\s+(\d+)|空间预热\s+(LOCK_[^｜]+))[^\n]*】$' if lang=='cn'
               else r'^\[(?:Video Segment\s+(\d+)|Spatial Warm-up\s+(LOCK_[^ |]+))[^\n]*\]$')
    matches=list(re.finditer(pattern,data,re.M));units={}
    for i,m in enumerate(matches):
        uid=f'SEG{int(m[1]):03d}' if m[1] else m[2]
        if uid in units:raise GateError('MD_DUPLICATE_UNIT:'+uid)
        block=data[m.start():matches[i+1].start() if i+1<len(matches) else len(data)]
        units[uid]=block
    return units


def validate_bilingual(docs,md):
    from .render import render_pack
    errors=[]
    expected=render_pack(docs)
    cn=parse_md(md.get('H3_PROMPTS_CN.md',''),'cn');en=parse_md(md.get('H3_PROMPTS_EN.md',''),'en')
    if list(cn)!=list(en):errors.append('BILINGUAL_UNIT_ORDER_OR_COUNT_MISMATCH')
    binding=docs['08_binding.json']['units']
    for lang,units,filename in [('cn',cn,'H3_PROMPTS_CN.md'),('en',en,'H3_PROMPTS_EN.md')]:
        if set(units)!=set(binding):errors.append(lang+':MD_UNIT_SET_MISMATCH')
        if md.get(filename)!=expected[filename]:errors.append(lang+':MD_NOT_CANONICAL_RENDER')
        for uid,block in units.items():
            headers=re.findall(r'^([a-z_]+):\s*$',block,re.M)
            top=[h for h in headers if h not in ['incoming_state','current_state','end_state','from_previous','to_next']]
            if top!=SECTIONS:errors.append(uid+':H3_SECTIONS_INVALID:'+lang)
            pics=set(re.findall(r'<Picture\s+(\d+)>',block))
            if pics!={k[1:] for k in binding.get(uid,{})}:errors.append(uid+':PICTURE_REFERENCE_INCOMPLETE')
            definitions=block.split('subject_definitions:\n',1)[-1].split('\n\nsummary:',1)[0]
            defined=set(re.findall(r'<Subject (\d+)>',definitions))
            if not defined or defined!={str(i) for i in range(1,len(defined)+1)}:
                errors.append(uid+':SUBJECT_COVERAGE_INCOMPLETE')
            if re.search(r'同上|沿用上一段|参考上一段|same as above|same setting|continue previous',block,re.I):errors.append(uid+':PROMPT_SHORTHAND_FORBIDDEN')
            if '\nnon_diegetic_music:\nN/A\n' not in block:errors.append(uid+':MUSIC_NOT_DISABLED')
            if lang=='en':
                body=block.split('subject_definitions:\n',1)[-1]
                body=re.sub(r'<d>.*?</d>','',body,flags=re.S)
                # Real filenames and identifiers are shared and can legitimately contain Han characters.
                for b in binding.get(uid,{}).values():body=body.replace(b['file'],'').replace(b['asset_id'],'')
                if HAN.search(body):errors.append(uid+':ENGLISH_BODY_CONTAINS_CHINESE')
    for uid in cn.keys()&en.keys():
        ctimes=re.findall(r'\[Shot (\d+) \| ([^\]]+)\]',cn[uid]);etimes=re.findall(r'\[Shot (\d+) \| ([^\]]+)\]',en[uid])
        if ctimes!=etimes:errors.append(uid+':BILINGUAL_TIMELINE_MISMATCH')
        cb=re.findall(r'P\d+=[^；;\n]+',cn[uid]);eb=re.findall(r'P\d+=[^；;\n]+',en[uid])
        if cb!=eb:errors.append(uid+':BILINGUAL_PICTURE_BINDING_MISMATCH')
        if re.findall(r'<d>(.*?)</d>',cn[uid],re.S)!=re.findall(r'<d>(.*?)</d>',en[uid],re.S):errors.append(uid+':BILINGUAL_DIALOGUE_MISMATCH')
    return errors


def validate_directory(directory, asset_root=None):
    directory=Path(directory)
    try:
        docs={n:load(directory/n) for n in FILES}
        md={n:(directory/n).read_text(encoding='utf-8') for n in ['H3_PROMPTS_CN.md','H3_PROMPTS_EN.md']}
        if docs['01_story.json']['schema_version']=='5.1':
            for n in ['H3_PROMPTS_FULL_CN.md','H3_PROMPTS_FULL_EN.md','H3_RUNTIME_CN.md','H3_RUNTIME_EN.md']:
                md[n]=(directory/n).read_text(encoding='utf-8')
        errors=validate_pack(docs,md,asset_root or directory/'assets')
        if docs['01_story.json']['schema_version']=='5.1':
            for lang in ['CN','EN']:
                if md[f'H3_PROMPTS_FULL_{lang}.md']!=md[f'H3_PROMPTS_{lang}.md']:
                    errors.append('FULL_ALIAS_NOT_CANONICAL:'+lang)
            from .asset_dependencies import validate_asset_dependencies
            dependency_report=validate_asset_dependencies(docs['03_assets.json']['assets'],docs['02_cast.json']['characters'],
                docs['01_story.json']['scenes'],docs['08_binding.json']['units'],
                allow_stale_asset=docs['01_story.json']['project'].get('allow_stale_asset',False))
            if load(directory/'asset_dependency_report.json')!=dependency_report:
                errors.append('ASSET_DEPENDENCY_REPORT_STALE')
            from .pipeline_graph import validate_pipeline_graph,load_graph
            graph=load(directory/'pipeline_graph.json')
            errors.extend(validate_pipeline_graph(graph))
            if graph!=load_graph():errors.append('PIPELINE_GRAPH_NOT_CANONICAL')
            from .regression import validate_manifest
            errors.extend(validate_manifest(load(directory/'h3_regression_manifest.json')))
            from .runtime import runtime_budget_report
            if load(directory/'runtime_prompt_budget_report.json')!=runtime_budget_report(docs,md):
                errors.append('RUNTIME_BUDGET_REPORT_STALE')
            for n in ['generation_ledger.json','assembly_manifest.json','README.md','CHANGELOG_V5.1.md','production_review.json']:
                if not (directory/n).is_file():errors.append('REQUIRED_PACK_FILE_MISSING:'+n)
        compatible=directory/'H3_WORKBENCH_EN_AVS.md'
        if compatible.exists():
            from .render import render_avs_english
            if compatible.read_text(encoding='utf-8')!=render_avs_english(docs):errors.append('AVS_ENGLISH_VIEW_NOT_CANONICAL')
        from .views import director_views
        for lang in ['cn','en']:
            table,board,view=director_views(docs,lang)
            for filename,expected in [(f'STANDARD_SHOT_TABLE_{lang.upper()}.md',table),(f'TEXT_STORYBOARDS_{lang.upper()}.md',board)]:
                p=directory/filename
                if p.exists() and p.read_text(encoding='utf-8')!=expected:errors.append('DIRECTOR_VIEW_NOT_CANONICAL:'+filename)
            p=directory/f'animation_plan_{lang}.view.json'
            if p.exists() and load(p)!=view:errors.append('DIRECTOR_JSON_VIEW_NOT_CANONICAL')
        review=directory/'production_review.json'
        if review.exists():
            v=load(review)
            if v.get('production_hash')!=digest(docs):errors.append('PRODUCTION_REVIEW_STALE')
            if docs['01_story.json']['schema_version']=='5.1':
                if v.get('asset_dependency_status')!=dependency_report['status']:errors.append('DEPENDENCY_REVIEW_STALE')
                if v.get('runtime_prompt_budget')!=runtime_budget_report(docs,md):errors.append('BUDGET_REVIEW_STALE')
            if v.get('status')=='READY' and errors:errors.append('READY_WITH_VALIDATION_FAILURE')
        return errors
    except (OSError,ValueError) as exc:return ['PACK_LOAD_FAILED:'+str(exc)]
