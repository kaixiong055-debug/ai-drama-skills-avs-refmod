"""Deterministic H3 execution view of the same eight canonical documents as FULL.

The current state is emitted once, in its owning section. Incoming/end states are
lossless deltas from that explicit local baseline, never references to another SEG.
"""
import re
from .common import bi, index, text
from .render import CLOSEUP, NEGATIVES, metric_provenance_text, term
from .spatial import GEOMETRY
from .redundancy import (RUNTIME_SECTIONS, RUNTIME_PROMPT_BUDGET, budget_warnings,
                         semantic_deduplicate, sections, validate_prompt_redundancy)


def render_runtime_pack(docs):
    return {f'H3_RUNTIME_{lang.upper()}.md':render_runtime_document(docs,lang) for lang in ['cn','en']}


def render_runtime_document(docs,lang,compress=True):
    cast=index(docs['02_cast.json']['characters'],'character_id')
    scenes=index(docs['01_story.json']['scenes'],'scene_id')
    assets=index(docs['03_assets.json']['assets'],'asset_id')
    beats=index(docs['04_script.json']['beats'],'beat_id')
    board=docs['05_storyboard.json'];plans=index(board['segments'],'segment_id')
    states=docs['07_spatial_locks.json']['states']
    locks={v['before_segment_id']:v for v in docs['07_spatial_locks.json']['locks']}
    units=docs['06_production.json']['units'];project=docs['01_story.json']['project']
    avs_refmod = project.get('character_binding_mode','PICTURE') == 'AVS_REFMOD'
    def say(cn,en):return cn if lang=='cn' else en
    def name(cid):return text(cast[cid]['name'],lang) if cid in cast else term(cid,lang)
    def names(ids):return say('、',', ').join(name(cid) for cid in ids) or say('无','none')
    def value(v):
        if isinstance(v,dict):
            if 'cn' in v and 'en' in v:return text(v,lang)
            return '; '.join(str(k)+'='+value(w) for k,w in v.items())
        if isinstance(v,list):return ', '.join(value(w) for w in v) or say('无','none')
        if isinstance(v,bool):return str(v).lower()
        return name(v) if isinstance(v,str) else str(v)
    def holder(v):
        cid,sep,hand=v.partition('.')
        return name(cid)+(say('的右手',' right hand') if hand=='right_hand' else say('的左手',' left hand') if hand=='left_hand' else sep+hand)
    def pos(cid,p,metric=False):
        result=f'{name(cid)} ({cid}): screen_position={term(p["screen_position"],lang)}; depth={term(p["depth"],lang)}; facing={term(p["facing"],lang)}; eyeline={name(p["eyeline_target"])}'
        if metric:result+=f'; x={p["x_m"]}m, y={p["y_m"]}m'
        return result+'.'
    def prop(pid,p):return f'{pid}: holder={holder(p["holder"])}; state={value(p["state"])}; valid_until_changed={str(p.get("valid_until_changed",True)).lower()}.'
    def deltas(base,target):
        """Only changed fields, including removals; all unchanged facts stay local."""
        result=[];metric=target.get('spatial_measurement',{}).get('measurement_mode')=='METRIC'
        for key in ['scene_id','scene_variant','area','camera_side','dialogue_axis','dialogue_group']:
            if base.get(key)!=target.get(key):result.append(key+'='+value(target.get(key)))
        for cid in sorted(set(base['characters'])|set(target['characters'])):
            if cid not in target['characters']:result.append(name(cid)+say('已离场。',' is absent.'));continue
            if cid not in base['characters']:result.append(name(cid)+say('已进入当前场景。',' is now present.'))
            for k,v in target['characters'][cid].items():
                if v!=base.get('characters',{}).get(cid,{}).get(k):
                    desc=text(cast[cid]['wardrobes'][v]['description'],lang) if k=='wardrobe' else value(v)
                    result.append(name(cid)+': '+k+'='+desc)
            if target['character_positions'][cid]!=base['character_positions'].get(cid):result.append(pos(cid,target['character_positions'][cid],metric))
        for key in GEOMETRY:
            for ident in sorted(set(base.get(key,{}))|set(target.get(key,{}))):
                if base.get(key,{}).get(ident)!=target.get(key,{}).get(ident):
                    result.append('geometry.'+key+'.'+ident+'='+value(target[key][ident]) if ident in target.get(key,{}) else 'geometry.'+key+'.'+ident+say('已移除',' removed'))
        for pid in sorted(set(base['major_props'])|set(target['major_props'])):
            if base['major_props'].get(pid)!=target['major_props'].get(pid):result.append(prop(pid,target['major_props'][pid]) if pid in target['major_props'] else pid+say('已移除。',' is removed.'))
        for door in sorted(set(base['door_states'])|set(target['door_states'])):
            if base['door_states'].get(door)!=target['door_states'].get(door):result.append('door.'+door+'='+value(target['door_states'].get(door,say('不存在','absent'))))
        for key in ['completed_actions','completed_sounds']:
            added=[v for v in target[key] if v not in base[key]];removed=[v for v in base[key] if v not in target[key]]
            if added:result.append(key+say('新增=',' added=')+', '.join(added))
            if removed:result.append(key+say('尚未发生=',' not yet completed=')+', '.join(removed))
        return result
    def render_unit(unit,hidden=False,next_id=None):
        uid=unit['unit_id'];plan=plans[unit['before_segment_id'] if hidden else uid]
        scene=scenes[unit['scene_id']];state=states[unit['state_id'] if hidden else unit['state_ids']['current']]
        binding=docs['08_binding.json']['units'][uid]
        anchor=uid if hidden else unit['spatial_anchor'];duration=unit['duration_s']
        title=say('隐藏空间预热','Hidden spatial warm-up') if hidden else text(plan['title'],lang)
        # Runtime metadata deliberately contains no second Picture/state definition.
        if lang=='cn':
            header=[f'【空间预热 {uid}｜{duration:g}秒｜{title}】' if hidden else f'【视频片段 {int(uid[3:])}｜5秒｜{text(scene["time_of_day"],lang)}｜{title}】',
                    '【Scene】'+unit['scene_id']+'｜'+text(scene['name'],lang),
                    '【集数】'+project.get('episode_id','EP01')+'｜'+text(project['episode_name'],lang),
                    '【H3模式】REF2VA', '【最终成片】'+('否' if hidden else '是'), '【连续性】'+('独立生成' if hidden else '续写')]
        else:
            header=[f'[Spatial Warm-up {uid} | {duration:g}s | {title}]' if hidden else f'[Video Segment {int(uid[3:])} | 5s | {text(scene["time_of_day"],lang)} | {title}]',
                    '[Scene] '+unit['scene_id']+' | '+text(scene['name'],lang),
                    '[Episode] '+project.get('episode_id','EP01')+' | '+text(project['episode_name'],lang),
                    '[H3 Mode] REF2VA', '[Include In Final] '+('NO' if hidden else 'YES'), '[Continuity] '+('INDEPENDENT' if hidden else 'CONTINUATION')]
        out={k:[] for k in RUNTIME_SECTIONS};registry={};char_assets={};env_assets=[]
        if avs_refmod:
            for cid in state['left_to_right_order']:
                registry['character:'+cid]=len(registry)+1
                sub=f'<Subject {registry["character:"+cid]}>'
                current=state['characters'][cid]
                desc=sub+say(' 是',' is ')+name(cid)+f' ({cid}); '+text(cast[cid]['identity'],lang)
                desc+='; '+say('发型=','hairstyle=')+text(cast[cid]['hairstyle'],lang)
                desc+='; wardrobe='+say('AI-Video-Studio本段选择的Clothing RefMod','AI-Video-Studio shot-selected Clothing RefMod')
                desc+='; hair_state='+term(current['hair_state'],lang)+'; clothing_state='+value(current['clothing_state'])+'; pose='+value(current['pose'])+'.'
                desc+=say(' 身份由Identity RefMod控制；人物不占Picture槽位。',' Identity is controlled by Identity RefMod; the character occupies no Picture slot.')
                out['subject_definitions'].append(desc)
                out['reference_map'].append('RefMod → '+sub+'; identity=AI-Video-Studio Identity RefMod; wardrobe=shot-selected Clothing RefMod; character_picture=NONE.')
        for slot,b in binding.items():
            a=assets[b['asset_id']];role=a['role']
            if role in ['STORYBOARD','KEYFRAME','SHOT_KEYFRAME','SPATIAL_ANCHOR_KEYFRAME','ACTION_KEYFRAME','END_STATE_KEYFRAME'] or a.get('keyframe_type'):
                picture=f'<Picture {int(slot[1:])}>'
                authority=say('纯构图参考，不定义新Subject；控制对应镜头构图、当前站位、景别及空间关系；不得覆盖人物身份MASTER、当前服装或Scene MASTER真实几何。','Composition reference only; does not define a new Subject. Controls the assigned shot’s composition, current blocking, shot scale and spatial relationships; must not override identity MASTER, current wardrobe or Scene MASTER geometry.')
                out['reference_map'].append(f'{slot}={b["file"]}; {picture}; asset_id={a["asset_id"]}; shot_id='+a.get('shot_id','')+'; '+text(a['description'],lang)+'; '+authority)
                continue
            entity='character:'+a['character_id'] if role=='H3_RUNTIME' else 'environment' if role in ['MASTER','AREA','SHEET','TRANSITION'] else a['asset_id']
            if entity not in registry:registry[entity]=len(registry)+1
            sub=f'<Subject {registry[entity]}>';picture=f'<Picture {int(slot[1:])}>'
            if role=='H3_RUNTIME':
                char_assets.setdefault(a['character_id'],[]).append((a,sub))
                authority=say('只控制该人物身份、面部、年龄感、身体比例、发型及指定服装；不控制站位或摄影机。','Controls this character’s identity, face, apparent age, proportions, hairstyle and specified wardrobe; does not control blocking or camera.')
                authority+=' wardrobe='+a['wardrobe']
            elif role in ['MASTER','AREA','SHEET','TRANSITION']:
                env_assets.append(a)
                authority=say('控制固定建筑、门窗、家具与真实空间几何；不锁原图机位，剧情灯光/昼夜/天气优先。','Controls fixed architecture, doors, windows, furniture and real scene geometry; does not lock the source camera; story lighting, time and weather take precedence.')
                if role=='AREA':authority+=say(' 局部服从当前Scene MASTER。',' The local area remains subordinate to the current Scene MASTER.')
            else:
                authority=term(role,lang);out['subject_definitions'].append(sub+': '+text(a['description'],lang))
            out['reference_map'].append(f'{slot}={b["file"]}; {picture} → {sub}; asset_id={a["asset_id"]}; '+authority)
        for cid,refs in char_assets.items():
            current=state['characters'].get(cid)
            if current is None:
                current=next((states[snap['after_state_id']]['characters'][cid] for snap in unit.get('events',[]) if cid in states[snap['after_state_id']]['characters']),{'wardrobe':refs[0][0]['wardrobe'],'hair_state':'dry','clothing_state':bi('按明确入场事件','as declared by the entrance event'),'pose':bi('按明确入场事件','as declared by the entrance event')})
            desc=refs[0][1]+say(' 是',' is ')+name(cid)+f' ({cid}); '+text(cast[cid]['identity'],lang)
            desc+='; '+say('发型=','hairstyle=')+text(cast[cid]['hairstyle'],lang)+'; wardrobe='+text(cast[cid]['wardrobes'][current['wardrobe']]['description'],lang)
            desc+='; hair_state='+term(current['hair_state'],lang)+'; clothing_state='+value(current['clothing_state'])+'; pose='+value(current['pose'])+'.'
            if cid not in state['characters']:desc+=say(' 此人物只在时间轴登记的入场时出现。',' This character appears only at the scheduled entrance.')
            out['subject_definitions'].append(desc)
        if env_assets:
            out['subject_definitions'].append(f'<Subject {registry["environment"]}>: '+text(scene['name'],lang)+'; '+say('场景参考属于同一环境主体。','All scene references describe one environment subject.'))
        out['summary']=[text(project['visual_style'],lang),say('建立空间锚点，不执行正式剧情。','Establish a spatial anchor without executing the formal story.') if hidden else text(plan['summary'],lang)]
        measurement=state.get('spatial_measurement',{'measurement_mode':'RELATIVE','confidence':'UNKNOWN'})
        metric=measurement['measurement_mode']=='METRIC'
        out['spatial_state'].append('spatial_measurement: '+measurement['measurement_mode']+'; confidence='+measurement.get('confidence','UNKNOWN'))
        out['spatial_state'].append('area='+term(state['area'],lang)+'; scene_variant='+term(state['scene_variant'],lang)+'; '+say('在场人数=','present_count=')+str(len(state['characters'])))
        for cid in state['left_to_right_order']:out['spatial_state'].append(pos(cid,state['character_positions'][cid],metric))
        for pair,distance in state['distance_between_characters'].items():
            a,b=pair.split('|')
            if metric:out['spatial_state'].append(names([a,b])+f': distance={distance}m.')
            elif isinstance(distance,dict):out['spatial_state'].append(names([a,b])+': '+value(distance))
        if not metric and not state['distance_between_characters']:
            out['spatial_state'].append(say('相对布局，不声明未测量的米数。','Relative layout; no unmeasured metric distances are asserted.'))
        if metric:
            out['spatial_state'].append('metric_provenance: '+metric_provenance_text(measurement,lang))
            for c in measurement.get('constraints',[]):
                out['spatial_state'].append((name(c['subject_id'])+'距离'+name(c['reference_id'])+'为'+str(c['distance_m'])+'米。') if lang=='cn' else (name(c['subject_id'])+' is '+str(c['distance_m'])+' meters from '+name(c['reference_id'])+'.'))
        for key in GEOMETRY:
            for ident,v in state.get(key,{}).items():out['spatial_state'].append('geometry.'+key+'.'+ident+'='+value(v))
        for target in plan.get('off_frame_targets',[]):out['spatial_state'].append('off_frame_target.'+target['target']+'='+term(target['screen_direction'],lang))
        out['spatial_state'].append('dialogue_group='+names(state['dialogue_group']))
        if not hidden:out['spatial_state'].append('primary_listener='+names([unit['primary_listener']] if unit['primary_listener'] else [])+'; secondary_listeners='+names(unit['secondary_listeners']))
        # All current physical state has exactly one owner, with persistence explicit.
        current_lines=['valid_until_changed=true; '+say('以下基线在无明确事件时持续至5秒末。','The declared baseline persists to the end unless an explicit event changes it.')]
        current_lines.extend(prop(pid,p) for pid,p in state['major_props'].items())
        if not state['major_props']:current_lines.append(say('当前无持有或登记道具。','No props are currently held or registered.'))
        current_lines.append('door_states: '+value(state['door_states']))
        for key in ['completed_actions','completed_sounds']:current_lines.append(key+': '+value(state[key]))
        for display in plan.get('display_state_contract',[]):current_lines.append('display.'+display['object']+'='+str(display['value'])+'; '+say('只复制绑定素材准确文字。','Copy the exact text from the bound asset only.'))
        for carry in plan.get('critical_carry_states',[]):current_lines.append('carry_state: '+value(carry))
        if hidden:
            out['continuity_state']=['incoming_state: '+say('独立初始化当前声明的场景。','Initialize the declared scene independently.'),
                                     'current_state:\n'+'\n'.join(current_lines),
                                     'end_state: '+say('保持基线，结束于稳定姿态；不完成任何剧情动作或声音事件。','Hold the baseline and finish in a stable pose; complete no story action or sound event.'),
                                     'from_previous: '+say('无外部动态输入。','No dynamic input.'), 'to_next: '+unit['before_segment_id']]
        else:
            incoming=deltas(state,states[unit['state_ids']['incoming']]);ending=deltas(state,states[unit['state_ids']['end']])
            out['continuity_state']=['incoming_state: '+unit['state_ids']['incoming']+'\n'+('\n'.join(incoming) if incoming else say('入态与本段声明的当前基线一致；无待补的状态变更。','The entry state equals this segment’s declared baseline; no additional state transition is pending.')),
                                     'current_state: '+unit['state_ids']['current']+'\n'+'\n'.join(current_lines),
                                     'end_state: '+unit['state_ids']['end']+'\n'+('\n'.join(ending) if ending else say('5秒末无状态变更，当前基线的全部字段继续有效。','At 5s there is no state change; every field of the current baseline remains valid.')),
                                     'from_previous: '+say('只接续视觉运动，不继承已经结束的尾音。','Continue visual motion only; do not inherit completed audio tails.'),
                                     'to_next: '+(next_id+say(' 接收本段末态；空间失效时先重建LOCK。',' receives this segment’s end state; rebuild a LOCK if the spatial anchor is invalidated.') if next_id else say('本段收尾。','This segment closes the project.'))]
            for event in plan.get('before_events',[]):out['continuity_state'].append(say('已在段前完成：','Completed before this segment: ')+text(event['description'],lang))
            # End-only deltas cannot describe two moves that return to the baseline.
            # Preserve each intermediate physical transition once, with timed scope.
            for snap in unit['events'][:-1]:
                intermediate=[v for v in deltas(states[snap['before_state_id']],states[snap['after_state_id']])
                              if not v.startswith(('completed_actions','completed_sounds'))]
                if intermediate:out['continuity_state'].append(f'intermediate_state @{snap["at_s"]:.3f}s:\n'+'\n'.join(intermediate))
        out['camera_plan'].append('camera_side='+term(state['camera_side'],lang)+'; dialogue_axis='+term(state['dialogue_axis'],lang))
        if len(state['characters'])>=2:out['camera_plan'].append(text(CLOSEUP,lang))
        if hidden:
            out['camera_plan'].append(say('稳定全景；固定摄影机；所有在场人物和关键固定结构可见。','Stable wide shot; locked-off camera; show all present characters and key fixed structures.'))
            out['shot_timeline'].append(f'[Shot 1 | 0.000–{duration:.3f}s]\n'+say('仅自然呼吸和微小头部动作；不走位、不交叉、不换边、不执行复杂动作；结束于清晰稳定末帧。','Only natural breathing and tiny head movements; no walking, crossing, swaps or complex actions; finish on a clean stable frame.'))
            out['dialogue_and_audio'].append(say('无对白或关键声音事件。','No dialogue or key sound events.'))
        else:
            camera_keys=['shot_scale','lens_mm','camera_height_m','camera_movement','camera_angle','composition','lighting','depth_of_field']
            common={k:plan['shots'][0][k] for k in camera_keys if all(shot[k]==plan['shots'][0][k] for shot in plan['shots'])}
            def camera_field(k,v):
                if k=='lens_mm':return f'lens={v}mm'
                if k=='camera_height_m':return say('规划摄影机高度=','planned camera height=')+str(v)+'m'
                return k+'='+value(v)
            if common:out['camera_plan'].append(say('全段镜头共同设置：','Settings shared by all shots: ')+'; '.join(camera_field(k,v) for k,v in common.items()))
            for n,shot in enumerate(plan['shots'],1):
                custom=[camera_field(k,shot[k]) for k in camera_keys if k not in common]
                out['camera_plan'].append(f'Shot {n} ({shot["shot_id"]}): '+('; '.join(custom) if custom else say('应用本段共同镜头设置。','Apply the shared shot settings declared in this segment.'))+' '+say('剪切目的：','Cut purpose: ')+text(shot['cut_reason'],lang))
                line=f'[Shot {n} | {shot["start_s"]:.3f}–{shot["end_s"]:.3f}s]\n'+shot['shot_id']+': '+text(shot['action'],lang)
                assigned=[beats[bid] for bid in shot['beat_ids']]
                if assigned:line+='\n'+say('执行节拍：','Perform beats: ')+', '.join(b['beat_id']+' ('+name(b['speaker'])+')' if b.get('speaker') else b['beat_id'] for b in assigned)
                performed={text(shot['action'],lang)}
                for beat in assigned:
                    action=text(beat['action'],lang)
                    if action not in performed:
                        line+='\n'+beat['beat_id']+': '+action;performed.add(action)
                for snap in unit['events']:
                    if (shot['start_s']<snap['at_s']<=shot['end_s']) or (shot['start_s']==snap['at_s']==0):
                        event=snap['event']
                        if event['op']=='sound':continue
                        line+=f'\n{snap["at_s"]:.3f}s '+event.get('event_id',event['op'])+': '+text(event['description'],lang)
                        if event['op']=='action':line+=f'; count={event["count"]}; phase={event.get("phase","complete")}'
                        if event.get('path'):line+='; path='+value(event['path'])
                        if event.get('off_screen_window'):line+='; off_screen_window='+str(event['off_screen_window'])
                out['shot_timeline'].append(line)
                for beat in assigned:
                    if beat.get('dialogue'):out['dialogue_and_audio'].append(f'{beat["beat_id"]} | {beat["start_s"]:.3f}–{beat["end_s"]:.3f}s | '+name(beat['speaker'])+' | '+text(beat['emotion'],lang)+f': <d>[{beat.get("spoken_language","Chinese")}] {beat["dialogue"]}</d>')
            out['shot_timeline'].append(text(plan['detailed_description'],lang))
            for contract in plan.get('limb_contracts',[]):out['shot_timeline'].append(text(contract,lang))
            for item in plan.get('counted_action_sequence',[]):out['shot_timeline'].append('counted_action: '+value(item))
            for snap in unit['events']:
                e=snap['event']
                if e['op']=='sound':out['dialogue_and_audio'].append(f'{e["event_id"]}: '+text(e['description'],lang)+f'; count={e["count"]}; window={e["window_start"]:.3f}–{e["window_end"]:.3f}s; termination='+text(e['termination'],lang)+'; '+say('清晰分离；结束后不重播。','Clearly separated occurrences; no retrigger after completion.'))
            if not out['dialogue_and_audio']:out['dialogue_and_audio'].append(say('无对白、无离散声音事件。','No dialogue or discrete sound events.'))
        out['dialogue_and_audio'].append(say('环境声：','Ambience: ')+text(scene['soundscape'],lang))
        out['dialogue_and_audio'].append('non_diegetic_music=N/A')
        out['reference_map'].append('Hidden LOCK: '+anchor+'; '+say('提供稳定空间锚点，绝不计入正式5秒或最终成片。','Provides the spatial anchor and is excluded from the formal 5s and final assembly.'))
        if hidden:out['reference_map'].append('continuation_source=NONE; '+say('输出尾22帧供下一正式段AddGuide。','Supply the last 22 frames to AddGuide for the following formal segment.'))
        else:
            c=unit['continuation_source']
            out['reference_map'].append('continuation_source='+c['unit_id']+f'; tail_frames={c["tail_frames"]}; fps={c["fps"]}; AddGuide.frame_idx={c["guide_frame_idx"]}; inherit_audio=false; '+say('正式内容仍为完整5秒；生成142帧仅裁22帧重叠。','Deliver a full 5s of formal content; generate 142 frames and trim only the 22-frame overlap.'))
        for keyframe in board.get('shot_keyframes',[]):
            if keyframe.get('shot_id') not in {shot['shot_id'] for shot in plan['shots']}:continue
            if keyframe.get('status') in ['VALID','AVAILABLE'] and keyframe.get('output'):
                # Picture binding is authoritative; never invent a usable pending image.
                slots=[slot for slot,b in binding.items() if b.get('asset_id')==keyframe.get('asset_id') or b.get('file')==keyframe['output']]
                if slots:out['reference_map'].append('keyframe.'+keyframe['shot_id']+'='+','.join(slots)+'; type='+keyframe['keyframe_type'])
        out['negative_rules']=[text(v,lang) for v in NEGATIVES[:-1]]
        for forbidden in plan.get('forbidden_invented_objects',[]):out['negative_rules'].append(say('禁止新增：','Do not add: ')+value(forbidden))
        for forbidden in plan.get('forbidden_retrigger_events',[]):out['negative_rules'].append(say('本段不得重新触发：','Do not retrigger in this segment: ')+value(forbidden))
        block='\n'.join(header)+'\n\n'+'\n\n'.join(key+':\n'+'\n'.join(out[key]) for key in RUNTIME_SECTIONS)+'\n\n'
        return semantic_deduplicate(block) if compress else block
    chunks=[]
    for i,unit in enumerate(units):
        if unit['unit_id'] in locks:chunks.append(render_unit(locks[unit['unit_id']],True))
        chunks.append(render_unit(unit,next_id=units[i+1]['unit_id'] if i+1<len(units) else None))
    from .speech import enforce_spoken_language
    from .performance import apply_performance
    return enforce_spoken_language(apply_performance(''.join(chunks), list(plans.values()), lang), lang)


def runtime_budget_report(docs,md=None):
    from .validator import parse_md
    md=md or render_runtime_pack(docs)
    configured=docs['01_story.json']['project'].get('runtime_prompt_budget',RUNTIME_PROMPT_BUDGET)
    report={'runtime_prompt_budget':configured,'compression':'OWNERSHIP_AND_EXACT_DEDUPLICATION; NO_TRUNCATION','warnings':[],'units':{}}
    for lang in ['cn','en']:
        data=md[f'H3_RUNTIME_{lang.upper()}.md']
        raw=render_runtime_document(docs,lang,compress=False)
        report['warnings'].extend(budget_warnings(raw,lang,configured))
        before=parse_md(raw,lang)
        for uid,block in parse_md(data,lang).items():
            report['units'].setdefault(uid,{})[lang+'_characters']=len(block)
            report['units'][uid][lang+'_before_dedup_characters']=len(before[uid])
            report['units'][uid][lang+'_removed_repeated_characters']=len(before[uid])-len(block)
    report['warnings']=list(dict.fromkeys(report['warnings']))
    return report


def validate_runtime_pack(docs,md):
    from .validator import parse_md
    errors=[];expected=render_runtime_pack(docs);parsed={}
    for lang in ['cn','en']:
        filename=f'H3_RUNTIME_{lang.upper()}.md';data=md.get(filename,'')
        try:blocks=parse_md(data,lang)
        except ValueError as exc:errors.append(str(exc));continue
        parsed[lang]=blocks
        if data!=expected[filename]:errors.append(lang+':RUNTIME_NOT_CANONICAL_RENDER')
        if set(blocks)!=set(docs['08_binding.json']['units']):errors.append(lang+':RUNTIME_UNIT_SET_MISMATCH')
        errors.extend(validate_prompt_redundancy(data,lang))
        for uid,block in blocks.items():
            if list(sections(block))!=RUNTIME_SECTIONS:errors.append(uid+':RUNTIME_SECTIONS_INVALID')
            if re.search(r'同上|沿用上一段|参考前文|参考上一段|same as above|same as previous',block,re.I):errors.append(uid+':RUNTIME_SHORTHAND_FORBIDDEN')
            pictures=set(re.findall(r'<Picture (\d+)>',block))
            if pictures!={k[1:] for k in docs['08_binding.json']['units'].get(uid,{})}:errors.append(uid+':RUNTIME_PICTURE_INCOMPLETE')
            if 'non_diegetic_music=N/A' not in block:errors.append(uid+':RUNTIME_MUSIC_NOT_DISABLED')
            if lang=='en':
                body=block.split('subject_definitions:\n',1)[-1]
                body=re.sub(r'<d>.*?</d>','',body,flags=re.S)
                for row in docs['08_binding.json']['units'].get(uid,{}).values():
                    body=body.replace(row['file'],'').replace(row['asset_id'],'')
                if re.search(r'[\u3400-\u9fff]',body):errors.append(uid+':RUNTIME_ENGLISH_BODY_CONTAINS_CHINESE')
    cn=parsed.get('cn',{});en=parsed.get('en',{})
    if list(cn)!=list(en):errors.append('RUNTIME_BILINGUAL_UNIT_ORDER_OR_COUNT_MISMATCH')
    for uid in cn.keys()&en.keys():
        for label,pattern in [('TIMELINE',r'\[Shot (\d+) \| ([^\]]+)\]'),('PICTURE',r'P\d+=[^;\n]+'),
                              ('DIALOGUE',r'<d>(.*?)</d>'),('LOCK',r'Hidden LOCK: (\S+)'),
                              ('CONTINUATION',r'continuation_source=([^;\n]+)'),('STATE_IDS',r'(?:incoming_state|current_state|end_state): (SEG\w+)')]:
            if re.findall(pattern,cn[uid],re.S)!=re.findall(pattern,en[uid],re.S):errors.append(uid+':RUNTIME_BILINGUAL_'+label+'_MISMATCH')
    return list(dict.fromkeys(errors))
