import json
import re
from .common import SECTIONS, bi, digest, index, text
from .speech import enforce_spoken_language

CLOSEUP = bi('镜头从群像切为单人近景时，仅改变摄影机裁切、焦距与构图；角色在真实场景中的物理位置不发生变化。画外人物仍保持上一空间锚点中的原位置。',
             "When cutting from a group shot to a character close-up, only the camera framing, focal length, and composition change. The character's physical position in the scene does not change. Off-screen characters remain in their previously established spatial positions.")
NEGATIVES = [
    bi('禁止人物换脸、改变年龄、身份或身体比例。', 'Do not change faces, apparent age, identity, or body proportions.'),
    bi('禁止无剧情原因换衣、改变发型、湿发或干发状态。', 'Do not change wardrobe, hairstyle, or wet/dry hair states without a scripted cause.'),
    bi('禁止随机交换人物左右位置、近景传送、将画外人物重新安排到新位置。', 'Do not randomly swap left/right positions, teleport characters in close-ups, or rearrange off-screen characters.'),
    bi('禁止随机越轴、镜像翻转、道路左右反转。', 'Do not cross the dialogue axis without authorization, mirror the image, or reverse left/right roads.'),
    bi('禁止移动门窗、添加新门、删除固定家具或重新设计场景。', 'Do not move doors or windows, add doors, remove fixed furniture, or redesign the location.'),
    bi('禁止道具凭空出现、消失、擅自换手或改变持有人。', 'Do not spawn or remove props, switch holding hands, or change holders without a scripted transfer.'),
    bi('禁止多手、额外手臂、肢体融合和手部变形；每人恰好两只手。', 'No extra hands or arms, fused limbs, or deformed hands; each person has exactly two hands.'),
    bi('禁止重复已完成动作或重新播放已结束的声音事件。', 'Do not repeat completed actions or retrigger completed sound events.'),
    bi('禁止最后一秒随机变形、过度运动模糊、文字、水印；剧情文字只能严格复制绑定素材。', 'No random deformation during the final second, excessive motion blur, added text, or watermarks; scripted readable text must match the bound asset exactly.'),
    bi('禁止自动加入背景音乐。', 'Do not automatically add background music.')]
NEGATIVES.append(bi('同一事件ID在不同栏目出现时指同一次事件，不得按描述次数重复执行。', 'Repeated descriptions of the same event ID refer to one event; do not execute it multiple times.'))
TERMS = {
    'left':bi('左侧','screen left'), 'right':bi('右侧','screen right'), 'center':bi('中央','center'),
    'foreground':bi('前景','foreground'), 'midground':bi('中景','midground'), 'background':bi('后景','background'),
    'south':bi('南侧','south'), 'north':bi('北侧','north'), 'east':bi('东侧','east'), 'west':bi('西侧','west'),
    'forward':bi('前方','forward'), 'dry':bi('干燥','dry'), 'wet':bi('湿润','wet'),
    'locked_east_west':bi('东西方向锁定轴线','locked east-west axis'),
    'closed':bi('关闭','closed'), 'open':bi('打开','open'), 'half_open':bi('半开','half open'),
    'close_up':bi('近景','close-up'), 'medium_close':bi('中近景','medium close-up'),
    'medium':bi('中景','medium shot'), 'wide':bi('全景','wide shot'), 'extreme_close_up':bi('特写','extreme close-up'),
    'locked_off':bi('固定摄影机','locked-off camera'), 'push_in':bi('缓慢推近','slow push-in'),
    'tracking':bi('跟随摄影','tracking camera'), 'pan':bi('轻摇','gentle pan'), 'pull_out':bi('缓慢拉远','slow pull-out'),
    'MAIN':bi('主区域','main area'), 'MASTER':bi('主场景','master location'),
    'H3_RUNTIME':bi('当前人物运行造型','current character runtime appearance'), 'AREA':bi('局部空间几何','local-area geometry'),
    'PROP':bi('道具外观','prop appearance'), 'TRANSITION':bi('门内外连接空间','inside/outside doorway transition'),
    'STORYBOARD':bi('构图与动作阶段；不控制人物身份','composition and action phase; does not control identity'),
    'SHEET':bi('空间理解参考','spatial understanding reference')}
TERMS.update({'left_front':bi('左前方','front-left'), 'right_front':bi('右前方','front-right'),
              'rear_left':bi('左后方','rear-left'), 'rear_right':bi('右后方','rear-right')})
TERMS.update({'screen-left':TERMS['left'],'screen-right':TERMS['right']})


def term(value, lang):
    if isinstance(value, dict): return text(value,lang)
    if value in TERMS: return TERMS[value][lang]
    if str(value).startswith('center_'):
        n, count = str(value).split('_')[1], str(value).split('_')[-1]
        return f'中央第{n}/{count}位' if lang=='cn' else f'central position {n} of {count}'
    return str(value)


def metric_provenance_text(measurement,lang):
    """Do not turn an untranslated evidence quote into English prompt prose."""
    provenance=measurement.get('provenance',{})
    if lang=='cn':return '; '.join(str(k)+'='+str(v) for k,v in provenance.items())
    result='source_type='+provenance.get('source_type','UNKNOWN')
    source=provenance.get('source_id','')
    if source and not re.search(r'[\u3400-\u9fff]',source):result+='; source_id='+source
    return result+'; evidence_sha256='+digest(provenance)+'; full evidence is stored in canonical spatial_measurement.provenance'


def render_pack(docs):
    result = {}
    for lang, name in [('cn','H3_PROMPTS_CN.md'), ('en','H3_PROMPTS_EN.md')]:
        result[name] = render_document(docs,lang)
    return result


def render_avs_english(docs):
    """English prompt bodies with the original Chinese parser's machine metadata."""
    from .validator import parse_md
    cn=parse_md(render_document(docs,'cn'),'cn')
    en=parse_md(render_document(docs,'en'),'en')
    return ''.join(cn[uid].split('subject_definitions:\n',1)[0]+'subject_definitions:\n'+
                   en[uid].split('subject_definitions:\n',1)[1] for uid in cn)


def render_document(docs, lang):
    story = docs['01_story.json']; project=story['project']
    avs_refmod = project.get('character_binding_mode','PICTURE') == 'AVS_REFMOD'
    cast = index(docs['02_cast.json']['characters'],'character_id')
    scenes = index(story['scenes'],'scene_id')
    assets = index(docs['03_assets.json']['assets'],'asset_id')
    beats = index(docs['04_script.json']['beats'],'beat_id')
    plans = index(docs['05_storyboard.json']['segments'],'segment_id')
    spatial=docs['07_spatial_locks.json']; states=spatial['states']
    locks={l['before_segment_id']:l for l in spatial['locks']}
    units=docs['06_production.json']['units']
    def name(cid): return text(cast[cid]['name'],lang) if cid in cast else term(cid,lang)
    def names(ids): return ('、' if lang=='cn' else ', ').join(name(c) for c in ids) or ('无' if lang=='cn' else 'none')
    def describe_value(v):
        if isinstance(v,dict) and set(v)=={'cn','en'}: return text(v,lang)
        if isinstance(v,dict): return ('；' if lang=='cn' else '; ').join(k+'='+describe_value(x) for k,x in v.items())
        if isinstance(v,list): return names(v)
        if isinstance(v,bool): return ('是' if v else '否') if lang=='cn' else str(v).lower()
        return name(v) if isinstance(v,str) else str(v)
    def state_lines(s):
        lines=[]
        measurement=s.get('spatial_measurement',{'measurement_mode':'RELATIVE','confidence':'UNKNOWN'})
        metric=measurement.get('measurement_mode')=='METRIC'
        lines.append('spatial_measurement: '+measurement.get('measurement_mode','RELATIVE')+'; confidence='+measurement.get('confidence','UNKNOWN'))
        if lang=='cn': lines += [f"场景：{s['scene_id']}；区域：{term(s['area'],lang)}；空间锚点版本：{s.get('anchor_version','初始')}。",
                                 '从左到右：'+names(s['left_to_right_order'])+'。']
        else: lines += [f"Scene: {s['scene_id']}; area: {term(s['area'],lang)}; spatial anchor version: {s.get('anchor_version','initial')}.",
                        'Left-to-right order: '+names(s['left_to_right_order'])+'.']
        for cid in s['left_to_right_order']:
            p=s['character_positions'][cid]
            if lang=='cn': lines.append(f"{name(cid)}位于{term(p['screen_position'],lang)}、{term(p['depth'],lang)}；"+(f"坐标({p['x_m']},{p['y_m']})米；" if metric else '')+f"身体朝向{term(p['facing'],lang)}；视线指向{name(p['eyeline_target'])}。")
            else: lines.append(f"{name(cid)} stays at {term(p['screen_position'],lang)}, in the {p['depth']}; "+(f"ground-plane position ({p['x_m']}, {p['y_m']}) meters; " if metric else '')+f"faces {term(p['facing'],lang)}; eyeline toward {name(p['eyeline_target'])}.")
        for pair, distance in s['distance_between_characters'].items():
            a,b=pair.split('|')
            if metric:lines.append(f'{name(a)}与{name(b)}相距{distance}米。' if lang=='cn' else f'{name(a)} and {name(b)} are {distance} meters apart.')
            elif isinstance(distance,dict):lines.append(names([a,b])+': '+text(distance,lang))
        if metric:
            lines.append('metric_provenance: '+metric_provenance_text(measurement,lang))
            for constraint in measurement.get('constraints',[]):
                lines.append((f'{name(constraint["subject_id"])}距离{name(constraint["reference_id"])}为{constraint["distance_m"]}米。' if lang=='cn' else f'{name(constraint["subject_id"])} is {constraint["distance_m"]} meters from {name(constraint["reference_id"])}.'))
        labels={'fixed_architecture':bi('固定建筑','Fixed architecture'), 'door_positions':bi('门的位置','Door positions'),
                'window_positions':bi('窗的位置','Window positions'), 'furniture_positions':bi('家具位置','Furniture positions'),
                'entrance_positions':bi('进场位置','Entrance positions'), 'exit_positions':bi('离场位置','Exit positions')}
        for key,label in labels.items(): lines.append(text(label,lang)+': '+(describe_value(s[key]) or ('无' if lang=='cn' else 'none'))+'.')
        lines.append((f"摄影机保持在{term(s['camera_side'],lang)}；对话轴：{term(s['dialogue_axis'],lang)}。" if lang=='cn'
                      else f"Camera side: {term(s['camera_side'],lang)}; dialogue axis: {term(s['dialogue_axis'],lang)}.") )
        lines.append('状态持续有效，直到明确事件改变；裁切不改变真实站位。' if lang=='cn' else 'These states remain valid until an explicit event changes them; cropping does not change physical positions.')
        return '\n'.join(lines)
    def physical(s):
        lines=[]
        for cid,cs in s['characters'].items():
            outfit=cast[cid]['wardrobes'][cs['wardrobe']]
            if avs_refmod:
                wardrobe_text=('AI-Video-Studio当前选择的Clothing RefMod（剧情期望造型ID='+str(cs['wardrobe'])+'）' if lang=='cn' else 'AI-Video-Studio selected Clothing RefMod (story wardrobe id='+str(cs['wardrobe'])+')')
            else:
                wardrobe_text=text(outfit['description'],lang)
            if lang=='cn': lines.append(f"{name(cid)}：身份={text(cast[cid]['identity'],lang)}；服装={wardrobe_text}；发型={text(cast[cid]['hairstyle'],lang)}；头发状态={term(cs['hair_state'],lang)}；衣服状态={text(cs['clothing_state'],lang)}；姿态={text(cs['pose'],lang)}。")
            else: lines.append(f"{name(cid)}: identity={text(cast[cid]['identity'],lang)}; wardrobe={wardrobe_text}; hairstyle={text(cast[cid]['hairstyle'],lang)}; hair condition={term(cs['hair_state'],lang)}; clothing condition={text(cs['clothing_state'],lang)}; pose={text(cs['pose'],lang)}.")
        lines.append(('在场人物数量：' if lang=='cn' else 'Number of present characters: ')+str(len(s['characters'])))
        for pid,p in s['major_props'].items():
            holder=p['holder'].split('.')
            h=name(holder[0]) + (('的右手' if holder[-1]=='right_hand' else '的左手') if lang=='cn' and len(holder)>1 else ('.'+holder[-1] if len(holder)>1 else ''))
            lines.append(f'道具{pid}由{h}持有/承载；状态：{describe_value(p["state"])}；持续有效直到明确转移。' if lang=='cn' else f'Prop {pid}: holder={h}; state={describe_value(p["state"])}; persists until an explicit transfer.')
        if not s['major_props']: lines.append('无手持道具；禁止新增。' if lang=='cn' else 'No held props; do not introduce any.')
        lines.append(('门状态：' if lang=='cn' else 'Door states: ')+(describe_value(s['door_states']) or ('无' if lang=='cn' else 'none')))
        lines.append(('禁止再次执行已完成动作：' if lang=='cn' else 'Do not repeat completed actions: ')+(', '.join(s['completed_actions']) or ('无' if lang=='cn' else 'none')))
        lines.append(('禁止再次播放已结束声音：' if lang=='cn' else 'Do not retrigger completed sounds: ')+(', '.join(s['completed_sounds']) or ('无' if lang=='cn' else 'none')))
        return '\n'.join(lines)
    def render_unit(unit,plan,hidden=False):
        uid=unit['unit_id']; scene=scenes[unit['scene_id']]
        s=states[unit['state_id']] if hidden else states[unit['state_ids']['current']]
        binding=docs['08_binding.json']['units'][uid]
        anchor=uid if hidden else unit['spatial_anchor']
        continuation=None if hidden else unit['continuation_source']['unit_id']
        t=bi('隐藏空间预热','Hidden spatial warm-up') if hidden else plan['title']
        d=unit['duration_s']
        if lang=='cn':
            head=[f'【空间预热 {uid}｜{d:g}秒｜{text(t,lang)}】' if hidden else f'【视频片段 {int(uid[3:])}｜5秒｜{text(scene["time_of_day"],lang)}｜{text(t,lang)}】',
                  '【集数】'+project.get('episode_id','EP01')+'｜'+text(project['episode_name'],lang),
                  '【Scene】'+unit['scene_id'], '【场景】'+text(scene['name'],lang),
                  '【段类型】'+('隐藏空间预热' if hidden else '正式视频段'),
                  '【成片】'+('否' if hidden else '是'), '【最终成片】'+('否' if hidden else '是'),
                  '【H3模式】REF2VA', '【连续性】'+('独立生成' if hidden else '续写上一段'),
                  '【Hidden LOCK】'+anchor, '【空间锁ID】'+anchor if hidden else '【空间锁来源】'+anchor,
                  '【续写来源】'+('无' if hidden else continuation+' 尾部22帧'),
                  '【继承尾音】否', '【生成模式】单张生成',
                  '【Picture绑定】'+'；'.join(k+'='+v['file'] for k,v in binding.items()),
                  '【Speaker绑定】'+('无' if hidden else ('；'.join(f'S{n}={name(c)}' for n,c in enumerate(unit['active_speakers'],1)) or '无'))]
        else:
            head=[f'[Spatial Warm-up {uid} | {d:g}s | {text(t,lang)}]' if hidden else f'[Video Segment {int(uid[3:])} | 5s | {text(scene["time_of_day"],lang)} | {text(t,lang)}]',
                  '[Episode] '+project.get('episode_id','EP01')+' | '+text(project['episode_name'],lang),
                  '[Scene] '+unit['scene_id'], '[Location] '+text(scene['name'],lang),
                  '[Unit Type] '+('HIDDEN_SPATIAL_LOCK' if hidden else 'FORMAL_SEGMENT'),
                  '[Include In Final] '+('NO' if hidden else 'YES'), '[H3 Mode] REF2VA',
                  '[Continuity] '+('INDEPENDENT' if hidden else 'CONTINUATION'),
                  '[Hidden LOCK] '+anchor, '[Spatial Anchor] '+anchor,
                  '[Continuation Source] '+('none' if hidden else 'Last 22 frames of '+continuation),
                  '[Inherit Audio] NO', '[Generation Mode] Single image',
                  '[Picture Bindings] '+';'.join(k+'='+v['file'] for k,v in binding.items()),
                  '[Speaker Bindings] '+('none' if hidden else (';'.join(f'S{n}={name(c)}' for n,c in enumerate(unit['active_speakers'],1)) or 'none'))]
        sections={k:[] for k in SECTIONS}
        subjects=[]
        registry={};definitions={};retentions={}
        # In AVS_REFMOD mode characters are real Subjects but never Picture assets.
        # Identity is injected by AI-Video-Studio Identity RefMod; wardrobe is injected
        # by the shot-selected Clothing RefMod. Scene/prop/keyframe Pictures remain normal.
        if avs_refmod:
            shots='[Shot 1]' if hidden else ', '.join('[Shot '+str(i)+']' for i in range(1,len(plan['shots'])+1))
            for cid in s['left_to_right_order']:
                entity='character:'+cid
                registry[entity]=len(registry)+1
                sub=f'<Subject {registry[entity]}>'
                subjects.append(sub)
                if lang=='cn':
                    definitions[sub]=(f"{sub}是{name(cid)}，{text(cast[cid]['identity'],lang)}，发型为{text(cast[cid]['hairstyle'],lang)}。"
                                      f"身份、面部、年龄感、身体比例与发型由AI-Video-Studio人物Identity RefMod控制；当前服装由本段选择的Clothing RefMod控制。"
                                      f"人物不占用Picture槽位；禁止把人物头像、身份板、服装板或RefMod来源图复刻成背景、海报、分屏或额外人物。")
                    retentions[sub]=f'{sub}（出现于{shots}）：fully_preserved - 保持{name(cid)}身份、面部、发型、年龄感与身体比例；当前服装严格服从AI-Video-Studio本段选择的Clothing RefMod。'
                    sections['reference_map'].append(f'RefMod: {sub}={name(cid)}；identity=AI-Video-Studio Identity RefMod；wardrobe=本段选择的Clothing RefMod；character_picture=NONE。')
                else:
                    definitions[sub]=(f"{sub} is {name(cid)}, {text(cast[cid]['identity'],lang)}, with {text(cast[cid]['hairstyle'],lang)}. "
                                      f"Identity, face, apparent age, body proportions and hairstyle are controlled by the AI-Video-Studio Identity RefMod; the current wardrobe is controlled by the Clothing RefMod selected for this shot. "
                                      f"The character occupies no Picture slot. Do not reproduce any portrait, identity sheet, wardrobe sheet or RefMod source image as a background, poster, split-screen, or extra person.")
                    retentions[sub]=f'{sub} (appears in {shots}): fully_preserved - preserve {name(cid)} identity, face, hairstyle, apparent age and body proportions; current wardrobe must follow the AI-Video-Studio Clothing RefMod selected for this shot.'
                    sections['reference_map'].append(f'RefMod: {sub}={name(cid)}; identity=AI-Video-Studio Identity RefMod; wardrobe=shot-selected Clothing RefMod; character_picture=NONE.')
        for slot,b in binding.items():
            a=assets[b['asset_id']];role=a['role']
            if role=='STORYBOARD' or a.get('keyframe_type'):
                pic=f'<Picture {int(slot[1:])}>'
                sections['reference_map'].append(f'Picture {int(slot[1:])}: {b["file"]} → {pic}; '+
                    text(a['description'],lang)+'; keyframe_type='+a.get('keyframe_type','SHOT_KEYFRAME')+'; shot_id='+a.get('shot_id','')+'; '+
                    bi('纯构图参考，不定义新Subject。控制对应镜头构图、当前站位、景别及空间关系；不得覆盖人物身份MASTER、当前服装或Scene MASTER真实几何。',
                       'Composition reference only; does not define a new Subject. Controls the assigned shot composition, current blocking, shot scale and spatial relationships; must not override identity MASTER, current wardrobe or Scene MASTER geometry.')[lang])
                continue
            entity=('character:'+a['character_id'] if role=='H3_RUNTIME' else 'environment:'+unit['scene_id'] if role in ['MASTER','AREA','SHEET'] else b['asset_id'])
            if entity not in registry: registry[entity]=len(registry)+1
            n=registry[entity];pic=f'<Picture {int(slot[1:])}>'; sub=f'<Subject {n}>'
            if sub not in subjects:subjects.append(sub)
            if role=='H3_RUNTIME':
                cid=a['character_id']; outfit=cast[cid]['wardrobes'][a['wardrobe']]
                desc=(f"{sub}是{name(cid)}，{text(cast[cid]['identity'],lang)}，发型为{text(cast[cid]['hairstyle'],lang)}，服装为{text(outfit['description'],lang)}。严格继承{pic}中的身份、面部、发型、年龄感、身体比例与当前服装。参考仅控制身份和服装，不得覆盖站位、景别或摄影机设计。" if lang=='cn' else
                      f"{sub} is {name(cid)}, {text(cast[cid]['identity'],lang)}, with {text(cast[cid]['hairstyle'],lang)}, wearing {text(outfit['description'],lang)}. Strictly preserve identity, face, hairstyle, apparent age, body proportions, and current wardrobe from {pic}. The reference controls identity and wardrobe only; it must not override spatial placement, framing, or camera design.")
            elif role in ['MASTER','AREA','TRANSITION','SHEET']:
                desc=(f'{sub}是{pic}中的{text(a["description"],lang)}。固定建筑、门窗、家具和空间几何严格保留；昼夜、灯光、天气及已授权临时道具以当前剧情为准。参考构图不得锁死摄影机。' if lang=='cn' else
                      f'{sub} is {text(a["description"],lang)} from {pic}. Preserve fixed architecture, doors, windows, furniture, and spatial geometry. Time of day, lighting, weather, and authorized temporary props follow the current story; reference composition must not constrain the camera.')
            else:
                desc=f'{sub}由{pic}控制{term(role,lang)}：{text(a["description"],lang)}。' if lang=='cn' else f'{sub} is controlled by {pic} for {term(role,lang)}: {text(a["description"],lang)}.'
            if sub in definitions:
                extra=(f'附加参考{pic}控制同一主体的{term(role,lang)}：{text(a["description"],lang)}；服装只按明确事件切换，不生成第二个人。' if lang=='cn' else
                       f'Additional reference {pic} controls the same subject for {term(role,lang)}: {text(a["description"],lang)}. Apply it within its declared reference role; do not duplicate the subject.')
                definitions[sub]+='\n'+extra
            else:definitions[sub]=desc
            shots= '[Shot 1]' if hidden else ', '.join('[Shot '+str(i)+']' for i in range(1,len(plan['shots'])+1))
            if sub not in retentions:retentions[sub]=(f'{sub}（出现于{shots}）：fully_preserved - ' if lang=='cn' else f'{sub} (appears in {shots}): fully_preserved - ')+text(a['description'],lang)
            else:retentions[sub]+='; '+text(a['description'],lang)
            sections['reference_map'].append(f'Picture {int(slot[1:])}: {b["file"]} → {sub}；{term(role,lang)}；{text(a["description"],lang)}' if lang=='cn' else f'Picture {int(slot[1:])}: {b["file"]} → {sub}; {term(role,lang)}; {text(a["description"],lang)}')
        sections['subject_definitions']=list(definitions.values())
        sections['retention_analysis']=list(retentions.values())
        sections['summary'].append((f'建立{text(scene["name"],lang)}的隐藏空间锚点。' if lang=='cn' else f'Establish a hidden spatial anchor at {text(scene["name"],lang)}.') if hidden else text(plan['summary'],lang))
        sections['spatial_state']=[('当前空间锚点：' if lang=='cn' else 'Current spatial anchor: ')+anchor+'.',state_lines(s)]
        if not hidden:
            sections['spatial_state'] += [('当前说话人：' if lang=='cn' else 'Active speakers: ')+names(unit['active_speakers']),
                                          ('主要听者：' if lang=='cn' else 'Primary listener: ')+names([unit['primary_listener']] if unit['primary_listener'] else []),
                                          ('其他听者：' if lang=='cn' else 'Secondary listeners: ')+names(unit['secondary_listeners'])]
        if len(s['characters'])>=2: sections['spatial_state'].append(text(CLOSEUP,lang))
        sections['physical_continuity_locks']=[state_lines(s),physical(s)]
        if hidden:
            sections['continuity_state']=['incoming_state:\n'+state_lines(s)+'\n'+physical(s), 'current_state:\n'+state_lines(s),
                                         'end_state:\n'+state_lines(s)+'\n'+physical(s),
                                         'from_previous:\n'+('独立初始化空间；不执行剧情。' if lang=='cn' else 'Independent spatial initialization; no story action.'),
                                         'to_next:\n'+('将尾22帧传给'+unit['before_segment_id'] if lang=='cn' else 'Pass the last 22 frames to '+unit['before_segment_id'])]
            body=(f'[Shot 1 | 0.0–{d:.1f}s]\n' + ('稳定群像全景，所有当场人物可见；固定摄影机，不走位、不交叉、不换边、不说关键对白、不做复杂动作、不越轴。仅允许自然呼吸、微小头部动作和自然视线，结束于稳定姿态。' if lang=='cn' else 'A stable wide group shot showing all present characters. Keep the camera locked off. No walking, crossing, swaps, key dialogue, complex actions, or axis crossing. Allow only natural breathing, tiny head movements, and natural eyelines; finish in a clean stable pose.'))
            sections['camera_plan']=[bi('全景；35毫米；摄影机高度1.5米；固定摄影机。','Wide shot; 35 mm; camera height 1.5 meters; locked-off camera.')[lang]]
            sections['shot_timeline']=[body]
            sections['detailed_description']=[text(project['visual_style'],lang),body,' '.join(subjects),state_lines(s)]
            sections['dialogue_and_audio']=[bi('无对白、无关键声音事件；仅自然环境底声。','No dialogue or key sound events; natural ambient room tone only.')[lang]]
        else:
            for key in ['incoming','current','end']:
                ss=states[unit['state_ids'][key]]
                sections['continuity_state'].append(key+'_state:\n'+state_lines(ss)+'\n'+physical(ss))
            sections['continuity_state'].append('from_previous:\n'+(f'动态引导来自{continuation}尾22帧；继承身份、服装、道具、轴线和空间状态；不继承已结束尾音。' if lang=='cn' else f'Dynamic guide: last 22 frames of {continuation}. Preserve identity, wardrobe, props, axis, and spatial states; do not inherit completed audio tails.'))
            next_id=next((units[i+1]['unit_id'] for i,u in enumerate(units[:-1]) if u['unit_id']==uid),None)
            for e in plan.get('before_events',[]):
                sections['continuity_state'].append(text(e['description'],lang))
            sections['continuity_state'].append('to_next:\n'+(f'交付本段尾22帧及明确末态给{next_id}；换场或失效时先建立新LOCK。' if lang=='cn' else f'Pass the last 22 frames and explicit end state to {next_id}; establish a new LOCK on a scene change or invalidated geometry.') if next_id else 'to_next:\n'+('本段是项目收尾。' if lang=='cn' else 'This segment closes the project.'))
            for shotnum,shot in enumerate(plan['shots'],1):
                sections['camera_plan'].append(f'Shot {shotnum}: '+term(shot['shot_scale'],lang)+f'; {shot["lens_mm"]}mm; '+(f'摄影机高{shot["camera_height_m"]}米；' if lang=='cn' else f'camera height {shot["camera_height_m"]} m; ')+term(shot['camera_movement'],lang)+'; '+text(shot['camera_angle'],lang)+'; '+text(shot['composition'],lang)+'; '+text(shot['lighting'],lang)+'; '+text(shot['depth_of_field'],lang))
                shot_state=s
                for snap in unit['events']:
                    if snap['at_s']<=shot['start_s']: shot_state=states[snap['after_state_id']]
                body=f'[Shot {shotnum} | {shot["start_s"]:.3f}–{shot["end_s"]:.3f}s]\n'+text(shot['action'],lang)+'\n'+text(shot['composition'],lang)+'\n'+state_lines(shot_state)+'\n'+physical(shot_state)
                for snap in unit['events']:
                    if shot['start_s']<snap['at_s']<=shot['end_s']:
                        body+='\n'+f'{snap["at_s"]:.3f}s: '+text(snap['event']['description'],lang)+'\n'+state_lines(states[snap['after_state_id']])+'\n'+physical(states[snap['after_state_id']])
                if len(s['characters'])>=2: body+='\n'+text(CLOSEUP,lang)
                for bid in shot['beat_ids']:
                    beat=beats[bid]
                    if beat.get('dialogue'):
                        body+='\n'+name(beat['speaker'])+f' [{beat["start_s"]:.3f}–{beat["end_s"]:.3f}s]: <d>[{beat.get("spoken_language","Chinese")}] {beat["dialogue"]}</d>'
                        sections['dialogue_and_audio'].append(f'{bid}: '+name(beat['speaker'])+f'; {beat["start_s"]:.3f}–{beat["end_s"]:.3f}s; '+('对白仅在对应镜头执行一次。' if lang=='cn' else 'Perform the dialogue once in its assigned shot.'))
                sections['shot_timeline'].append(body)
            sections['detailed_description']=[text(project['visual_style'],lang), text(plan['summary'],lang),
                                              ' '.join(subjects),text(plan['detailed_description'],lang)]
            if plan.get('anatomy_risk') in ['MEDIUM','HIGH']:
                for hand in plan.get('limb_contracts',[]): sections['physical_continuity_locks'].append(text(hand,lang))
            for target in plan.get('off_frame_targets',[]):
                sections['spatial_state'].append(('画外固定目标：' if lang=='cn' else 'Off-screen fixed target: ')+target['target']+'; '+term(target['screen_direction'],lang))
            for display in plan.get('display_state_contract',[]):
                sections['physical_continuity_locks'].append((f'固定显示值：{display["object"]}={display["value"]}；只复制绑定素材中的准确文字。' if lang=='cn' else f'Locked display value: {display["object"]}={display["value"]}; copy the exact text from the bound reference only.'))
            for forbidden in plan.get('forbidden_invented_objects',[]):
                sections['negative_rules'].append(('禁止新增：' if lang=='cn' else 'Do not add: ')+term(forbidden,lang))
            for snap in unit['events']:
                e=snap['event']; sections['detailed_description'].append(f'{snap["at_s"]:.3f}s: '+text(e['description'],lang))
                sections['physical_continuity_locks'].append(f'{snap["at_s"]:.3f}s: '+text(e['description'],lang)+'\n'+state_lines(states[snap['after_state_id']])+'\n'+physical(states[snap['after_state_id']]))
                if e['op']=='sound':
                    sections['dialogue_and_audio'].append((f'声音事件{e["event_id"]}：{text(e["description"],lang)}；共{e["count"]}次；时间窗{e["window_start"]:.3f}–{e["window_end"]:.3f}秒；结束条件：{text(e["termination"],lang)}；结束后不重播。' if lang=='cn' else f'Sound event {e["event_id"]}: {text(e["description"],lang)}; exactly {e["count"]} occurrences within {e["window_start"]:.3f}–{e["window_end"]:.3f}s; termination: {text(e["termination"],lang)}; never retrigger after completion.'))
            if not sections['dialogue_and_audio']: sections['dialogue_and_audio']=[bi('无对白、无离散声音事件。','No dialogue or discrete sound events.')[lang]]
        sections['overall_soundscape']=[text(scene['soundscape'],lang),bi('保留已安排的对白、环境声、脚步、门铃、风雨、接触声、呼吸及必要动作声；禁止新增或重播离散事件。','Retain scheduled dialogue, ambience, footsteps, doorbells, wind, rain, contact sounds, breathing, and necessary action sounds. Do not add or retrigger discrete events.')[lang]]
        sections['non_diegetic_music']=['N/A']
        sections['reference_map'].append('Hidden LOCK: '+anchor+'; '+bi('控制左右顺序、前后关系、距离、朝向、视线及对话轴。','Controls left-to-right order, depth, spacing, facing, eyelines, and dialogue axis.')[lang])
        if continuation: sections['reference_map'].append('Previous segment: '+continuation+'; '+bi('尾22帧负责动态连续性；已结束声音不得重播。','The last 22 frames control dynamic continuity; completed sounds must not replay.')[lang])
        sections['negative_rules']=[text(v,lang) for v in NEGATIVES]+sections['negative_rules']
        return '\n'.join(head)+'\n\n'+'\n\n'.join(k+':\n'+'\n'.join(sections[k]) for k in SECTIONS)+'\n\n'
    chunks=[]
    for unit in units:
        if unit['unit_id'] in locks: chunks.append(render_unit(locks[unit['unit_id']], plans[unit['unit_id']], True))
        chunks.append(render_unit(unit, plans[unit['unit_id']]))
    from .performance import apply_performance
    return enforce_spoken_language(apply_performance(''.join(chunks), list(plans.values()), lang), lang)
