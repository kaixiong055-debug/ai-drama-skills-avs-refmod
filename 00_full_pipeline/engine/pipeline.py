import copy
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
from .common import FILES, VERSION, GateError, bi, digest, envelope, index, load, save
from .spatial import initial_state, apply_event, lock_reasons, signature
from .binding import resolve_files, bind_unit


def compile_project(request, asset_root):
    from .validator import validate_request, validate_pack
    issues = validate_request(request)
    if issues: raise GateError('\n'.join(issues))
    from .measurement import prepare_measurements
    from .keyframes import plan_keyframes
    from .asset_dependencies import prepare_asset_dependencies
    from .pipeline_graph import validate_pipeline_graph
    graph = load(Path(__file__).resolve().parent.parent/'pipeline_graph.json')
    graph_errors = validate_pipeline_graph(graph)
    if graph_errors: raise GateError('\n'.join(graph_errors))
    r = prepare_measurements(request)
    r['schema_version'] = VERSION
    r['project'].setdefault('allow_stale_asset', False)
    r['project'].setdefault('runtime_prompt_budget', {
        'cn': {'target_min':2500,'target_max':5000}, 'en': {'target_min':3500,'target_max':8000},
        'ordinary_two_person_warning':15000,'semantic_completeness_first':True})
    r = plan_keyframes(r, asset_root=asset_root)
    r, dependency_report = prepare_asset_dependencies(r)
    if dependency_report['errors']: raise GateError('\n'.join(dependency_report['errors']))
    issues = validate_request(r)
    if issues: raise GateError('\n'.join(issues))
    cast = index(r['cast'], 'character_id')
    scenes = index(r['scenes'], 'scene_id')
    assets = index(r['assets'], 'asset_id')
    beats = index(r['beats'], 'beat_id')
    file_map = resolve_files(r['assets'], asset_root)
    story = envelope('story', {'project': r['project'], 'scenes': r['scenes'],
                             'source': r.get('source', {}), 'source_beats': r.get('source_beats', [])},
                     {'source_request': r})
    cast_doc = envelope('cast', {'characters': r['cast']}, {'story': story})
    assets_doc = envelope('assets', {'assets': r['assets']}, {'story': story, 'cast': cast_doc})
    script = envelope('script', {'beats': r['beats']}, {'story': story, 'cast': cast_doc, 'assets': assets_doc})
    storyboard = envelope('storyboard', {'segments': r['segments'], 'shot_keyframes': r.get('shot_keyframes',[])}, {'script': script})
    units, states, locks, bindings = [], {}, [], {}
    last = None
    active_lock = None
    anchor_state = None
    scene_versions = {}
    scene_cache = {}
    history_actions, history_sounds = [], []
    previous_id = None
    for n, plan in enumerate(r['segments'], 1):
        sid = plan['segment_id']
        scene_id = plan['scene_id']
        if last is None or last['scene_id'] != scene_id:
            world = copy.deepcopy(scene_cache.get(scene_id)) if scene_id in scene_cache else initial_state(scenes[scene_id], cast, plan['participants'])
            world['completed_actions'] = list(history_actions)
            world['completed_sounds'] = list(history_sounds)
        else: world = copy.deepcopy(last)
        if last is not None and last['scene_id'] != scene_id:
            for cid in world['characters']:
                if cid in last['characters']: world['characters'][cid] = copy.deepcopy(last['characters'][cid])
            for pid,prop in last['major_props'].items():
                if prop['holder'].split('.')[0] in world['characters']:
                    world['major_props'][pid] = copy.deepcopy(prop)
        incoming = copy.deepcopy(world)
        for event in plan.get('before_events', []): world = apply_event(world, event, cast, scenes)
        if set(world['character_positions']) != set(plan['participants']): raise GateError('PARTICIPANT_STATE_MISMATCH:' + sid)
        reasons = lock_reasons(anchor_state, world, plan)
        if last is not None and last['scene_id'] != scene_id and 'NEW_SCENE' not in reasons: reasons.append('NEW_SCENE')
        if reasons:
            scene_versions[scene_id] = scene_versions.get(scene_id, 0) + 1
            v = scene_versions[scene_id]
            scene_num = list(scenes).index(scene_id) + 1
            active_lock = f'LOCK_SC{scene_num:02d}_A{v:02d}'
            world['anchor_version'] = f'A{v:02d}'
            state_id = active_lock + '_STATE'
            states[state_id] = copy.deepcopy(world)
            lock = {'unit_id': active_lock, 'lock_id': active_lock, 'scene_id': scene_id,
                    'before_segment_id': sid, 'duration_s': plan.get('lock_duration_s', 1.0),
                    'include_in_final': False, 'state_id': state_id, 'reasons': reasons,
                    'continuation_source': None, 'h3_mode': 'REF2VA'}
            locks.append(lock)
            bindings[active_lock] = bind_unit(world, scenes, cast, assets, file_map, plan,
                                              allow_stale_asset=r['project']['allow_stale_asset'], is_lock=True, character_binding_mode=r['project'].get('character_binding_mode','PICTURE'))
            anchor_state = copy.deepcopy(world)
            continuation = active_lock
        else:
            world['anchor_version'] = anchor_state['anchor_version']
            continuation = previous_id
        current = copy.deepcopy(world)
        snapshots = []
        for event in sorted(plan.get('events', []), key=lambda e: (e['at_s'], e.get('event_id', ''))):
            before = copy.deepcopy(world)
            world = apply_event(world, event, cast, scenes)
            eid = sid + '_T' + str(len(snapshots) + 1)
            states[eid + '_BEFORE'] = before
            states[eid + '_AFTER'] = copy.deepcopy(world)
            snapshots.append({'at_s': event['at_s'], 'event': event,
                              'before_state_id': eid+'_BEFORE', 'after_state_id': eid+'_AFTER'})
        end = copy.deepcopy(world)
        ids = {k: sid + '_' + k.upper() for k in ['incoming', 'current', 'end']}
        for k, val in [('incoming', incoming), ('current', current), ('end', end)]: states[ids[k]] = val
        unit = {'unit_id': sid, 'segment_id': sid, 'scene_id': scene_id, 'duration_s': 5.0,
                'include_in_final': True, 'spatial_anchor': active_lock, 'state_ids': ids,
                'continuation_source': {'unit_id': continuation, 'tail_frames': 22, 'fps': 24,
                                        'guide_frame_idx': 0, 'inherit_audio': False},
                'shot_ids': [s['shot_id'] for s in plan['shots']], 'events': snapshots,
                'active_speakers': list(dict.fromkeys(beats[b]['speaker'] for b in plan['beat_ids'] if beats[b].get('speaker'))),
                'primary_listener': plan.get('primary_listener', next((c for c in current['left_to_right_order']
                                                                  if c not in [beats[b].get('speaker') for b in plan['beat_ids']]), None)),
                'secondary_listeners': [], 'h3_mode': 'REF2VA'}
        unit['secondary_listeners'] = [c for c in current['left_to_right_order'] if c not in unit['active_speakers'] and c != unit['primary_listener']]
        units.append(unit)
        bindings[sid] = bind_unit(current, scenes, cast, assets, file_map, plan,
                                  allow_stale_asset=r['project']['allow_stale_asset'], character_binding_mode=r['project'].get('character_binding_mode','PICTURE'))
        # References introduced by wardrobe changes/entrances within the segment must also be available.
        for snap in snapshots:
            extra = bind_unit(states[snap['after_state_id']], scenes, cast, assets, file_map, plan,
                              allow_stale_asset=r['project']['allow_stale_asset'], character_binding_mode=r['project'].get('character_binding_mode','PICTURE'))
            for row in extra.values():
                if row['asset_id'] not in {v['asset_id'] for v in bindings[sid].values()}:
                    if len(bindings[sid]) == 9: raise GateError('PICTURE_LIMIT_EXCEEDED:' + sid)
                    bindings[sid][f'P{len(bindings[sid])+1}'] = row
        last, previous_id = end, sid
        history_actions, history_sounds = end['completed_actions'], end['completed_sounds']
        scene_cache[scene_id] = copy.deepcopy(end)
    production = envelope('production', {'units': units, 'production_profile': r['project']['production_profile'],
                                        'final_runtime_s': 5 * len(units), 'final_segment_count': len(units)},
                          {'storyboard': storyboard, 'assets': assets_doc})
    spatial = envelope('spatial_locks', {'locks': locks, 'states': states}, {'production': production})
    binding = envelope('binding', {'units': bindings, 'asset_files': file_map}, {'spatial_locks': spatial, 'assets': assets_doc})
    docs = dict(zip(FILES, [story, cast_doc, assets_doc, script, storyboard, production, spatial, binding]))
    from .render import render_pack
    md = render_pack(docs)
    md.update({f'H3_PROMPTS_FULL_{lang}.md':md[f'H3_PROMPTS_{lang}.md'] for lang in ['CN','EN']})
    from .runtime import render_runtime_pack
    md.update(render_runtime_pack(docs))
    errors = validate_pack(docs, md, asset_root)
    if errors: raise GateError('\n'.join(errors))
    return docs, md


def export_project(request, asset_root, output):
    """Validate before committing a complete pack; never leave a half-ready export."""
    docs, md = compile_project(request, asset_root)
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()): raise GateError('OUTPUT_DIRECTORY_NOT_EMPTY:' + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = Path(tempfile.mkdtemp(prefix='.h3-v5-', dir=output.parent))
    try:
        for name, value in docs.items(): save(temp/name, value)
        for name, value in md.items(): (temp/name).write_text(value, encoding='utf-8')
        from .render import render_avs_english
        (temp/'H3_WORKBENCH_EN_AVS.md').write_text(render_avs_english(docs),encoding='utf-8')
        from .views import director_views
        for lang in ['cn','en']:
            table,board,view=director_views(docs,lang)
            (temp/f'STANDARD_SHOT_TABLE_{lang.upper()}.md').write_text(table,encoding='utf-8')
            (temp/f'TEXT_STORYBOARDS_{lang.upper()}.md').write_text(board,encoding='utf-8')
            save(temp/f'animation_plan_{lang}.view.json',view)
        root = Path(asset_root).resolve()
        for row in docs['08_binding.json']['asset_files'].values():
            dest = temp/'assets'/row['file']; dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(root/row['file'], dest)
        title = request['project']['title']['cn']
        safe_title = ''.join(c for c in title if c not in '<>:"/\\|?*').strip()[:80] or 'Project'
        shutil.copy2(temp/'H3_PROMPTS_FULL_CN.md', temp/(safe_title+'_H3一键导入_中文版.md'))
        shutil.copy2(temp/'H3_PROMPTS_FULL_EN.md', temp/(safe_title+'_H3_ONE_CLICK_ENGLISH.md'))
        from .asset_dependencies import validate_asset_dependencies
        dependency_report = validate_asset_dependencies(docs['03_assets.json']['assets'],docs['02_cast.json']['characters'],
            docs['01_story.json']['scenes'],docs['08_binding.json']['units'],
            allow_stale_asset=docs['01_story.json']['project'].get('allow_stale_asset',False))
        save(temp/'asset_dependency_report.json', dependency_report)
        from .runtime import runtime_budget_report
        budget_report = runtime_budget_report(docs,md)
        save(temp/'runtime_prompt_budget_report.json',budget_report)
        package_root=Path(__file__).resolve().parent.parent
        shutil.copy2(package_root/'pipeline_graph.json',temp/'pipeline_graph.json')
        from .regression import new_manifest
        save(temp/'h3_regression_manifest.json',new_manifest())
        shutil.copy2(package_root/'CHANGELOG_V5.1.md',temp/'CHANGELOG_V5.1.md')
        save(temp/'production_review.json', {'schema_version':VERSION, 'status':'READY', 'validation':'PASS',
                                            'errors': [], 'asset_content_review':'UNVERIFIED',
                                            'video_quality':'NOT_RUN', 'production_hash':digest(docs),
                                            'asset_dependency_status':dependency_report['status'],
                                            'asset_dependency_warnings':dependency_report.get('warnings',[]),
                                            'runtime_prompt_budget':budget_report,
                                            'keyframe_requests':docs['05_storyboard.json'].get('shot_keyframes',[]),
                                            'meaning':'Canonical prompts and local references validated; rendered video quality requires QC.'})
        save(temp/'generation_ledger.json', {'schema_version':VERSION, 'takes': [], 'selected_takes': {}})
        save(temp/'assembly_manifest.json', {'schema_version':VERSION, 'status':'PENDING_GENERATION',
                                           'exclude_units':[l['lock_id'] for l in docs['07_spatial_locks.json']['locks']],
                                           'segments':[{'segment_id':u['unit_id'], 'duration_s':5, 'selected_take':None,
                                                        'continuation_source':u['continuation_source'],
                                                        'trim_guide_frames':22, 'delivery_frames':120,
                                                        'required_generation_frames':142} for u in docs['06_production.json']['units']],
                                           'fps':24, 'final_runtime_s':docs['06_production.json']['final_runtime_s']})
        (temp/'README.md').write_text('本包 JSON 是生产权威；双语 MD 从同一数据渲染。\n'
                                    '最终一键复制给 H3：项目名_H3一键导入_中文版.md / 项目名_H3_ONE_CLICK_ENGLISH.md；两者使用 FULL 14 栏格式。\n'
                                    'H3_PROMPTS_FULL_CN.md / H3_PROMPTS_FULL_EN.md 为同源 FULL 正式提示词；H3_RUNTIME_CN.md / EN.md 仅作为精炼运行时视图。\n'
                                    '执行依赖以 pipeline_graph.json 为准，按 LOCK → SEG 链生成。\n'
                                    'LOCK 不进成片；AddGuide 使用尾22帧，禁止继承已经结束的尾音。\n'
                                    '每个正式段交付120帧；含引导的生成需142帧并裁22帧重叠，避免吃掉正式5秒。\n'
                                    '不要同时让工作台和装配器重复补偿或重复裁切；以实际生成帧数与帧窗口为准。\n'
                                    'READY 只代表提示词/数据/本地素材检查通过，视频仍需 Take/QC。\n'
                                    '无尺寸证据的空间为 RELATIVE；资产版本未登记为 UNVERIFIED，详见依赖报告。\n'
                                    'AUTO Keyframe 建议可保持 MISSING；显式 required / ALWAYS 缺失会阻止导出。\n'
                                    '真实 H3 Regression 全部 NOT_RUN，指标为 null；使用软件包的回归登记脚本登记真实结果。\n', encoding='utf-8')
        from .validator import validate_directory
        errors = validate_directory(temp, temp/'assets')
        if errors: raise GateError('\n'.join(errors))
        if output.exists(): output.rmdir()  # empty directory only
        os.replace(temp, output)
    finally:
        if temp.exists(): shutil.rmtree(temp)
    return output
