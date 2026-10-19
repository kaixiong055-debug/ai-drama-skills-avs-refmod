"""Storyboard keyframe planning and reference authority; never synthesizes images."""
import copy
from pathlib import Path
from .common import GateError, bi, index

KEYFRAME_TYPES = {'SPATIAL_ANCHOR_KEYFRAME', 'SHOT_KEYFRAME', 'ACTION_KEYFRAME', 'END_STATE_KEYFRAME'}
KEYFRAME_POLICIES = {'AUTO', 'ALWAYS', 'NEVER'}
KEYFRAME_STATUSES = {'AVAILABLE', 'MISSING', 'NOT_REQUIRED'}
REFERENCE_AUTHORITY = {
    'controls': ['composition', 'current_blocking', 'shot_scale', 'spatial_relations'],
    'cannot_override': ['character_identity_master', 'current_wardrobe', 'scene_master_geometry'],
}


def _risk_reasons(segment, shot, scene, first_scene):
    reasons = []
    if len(segment.get('participants', [])) >= 3 and (shot.get('shot_scale') in {'wide', 'medium'} or segment.get('complex_composition') or scene.get('complex_scene')):
        reasons.append('COMPLEX_GROUP_COMPOSITION')
    if shot.get('special_camera') or shot.get('camera_movement') in {'tracking', 'pan'} or shot.get('camera_height_m', 1.5) > 3:
        reasons.append('SPECIAL_CAMERA')
    if segment.get('scene_geometry_risk') in {'MEDIUM', 'HIGH'} or scene.get('geometry_drift_risk') in {'MEDIUM', 'HIGH'}:
        reasons.append('SCENE_GEOMETRY_RISK')
    if segment.get('fixed_facility_interaction') or shot.get('fixed_prop_interaction') or segment.get('local_area_required'):
        reasons.append('FIXED_PROP_INTERACTION')
    history = segment.get('regression_history', []) + scene.get('regression_history', []) + segment.get('reject_reason', [])
    for label in ['POSITION_DRIFT', 'SCENE_GEOMETRY_DRIFT']:
        if label in history:
            reasons.append('HISTORY_' + label)
    if segment.get('review_drift') or segment.get('spatial_unreliable'):
        reasons.append('HISTORY_POSITION_DRIFT')
    if shot.get('special_action') or segment.get('mecha') or segment.get('weapon_action') or segment.get('special_action'):
        reasons.append('SPECIAL_ACTION')
    if first_scene and (scene.get('complex_scene') or len(segment.get('participants', [])) >= 4):
        reasons.append('FIRST_COMPLEX_SCENE')
    return list(dict.fromkeys(reasons))


def _safe_output(output):
    if not isinstance(output, str) or not output or Path(output).is_absolute() or '..' in Path(output).parts:
        raise GateError('KEYFRAME_OUTPUT_PATH_UNSAFE:' + str(output))
    if Path(output).suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}:
        raise GateError('KEYFRAME_OUTPUT_NOT_IMAGE:' + output)
    return output.replace('\\', '/')


def _existing_file(output, asset_root):
    if asset_root is None or not output:
        return False
    root = Path(asset_root).resolve()
    path = (root / output).resolve()
    if not path.is_relative_to(root):
        raise GateError('KEYFRAME_OUTPUT_PATH_UNSAFE:' + output)
    return path.is_file()


def _sources(request, segment, shot, kind, wardrobe_state):
    cast = index(request['cast'], 'character_id')
    scenes = index(request['scenes'], 'scene_id')
    scene = scenes[segment['scene_id']]
    present = list(segment['participants'])
    clothes = copy.deepcopy(wardrobe_state)
    time = shot['end_s'] if kind == 'END_STATE_KEYFRAME' else shot['start_s']
    for event in sorted(segment.get('events', []), key=lambda e: e.get('at_s', 0)):
        if event.get('at_s', 0) > time:
            continue
        if event['op'] == 'appearance' and 'wardrobe' in event:
            clothes[event['character_id']] = event['wardrobe']
        if event['op'] == 'enter' and event['character_id'] not in present:
            present.append(event['character_id'])
            if event.get('wardrobe'): clothes[event['character_id']] = event['wardrobe']
        if event['op'] == 'exit' and event['character_id'] in present:
            present.remove(event['character_id'])
    source = [cast[c]['wardrobes'][clothes[c]]['runtime_asset_id'] for c in present]
    source.append(scene['master_asset_id'])
    source += segment.get('required_area_ids', [])
    active_props = set(scene['initial_state'].get('major_props', {}))
    for event in segment.get('before_events', []) + segment.get('events', []):
        if event.get('op') == 'prop' and event.get('prop_id'): active_props.add(event['prop_id'])
    source += [aid for pid, aid in scene.get('prop_asset_ids', {}).items() if pid in active_props]
    return list(dict.fromkeys(source))


def plan_keyframes(request, asset_root=None):
    """Return normalized request with one planning record per shot (or authored types).

    AUTO recommendations remain optional MISSING work items. ALWAYS / an authored
    keyframe_required=true fails closed until an actual image is supplied. NEVER
    rejects required work instead of silently discarding it. An existing file is
    registered for the same image decoding and hashing gate as other Picture assets.
    """
    r = copy.deepcopy(request)
    project_policy = r.get('project', {}).get('keyframe_policy', r.get('keyframe_policy', 'AUTO'))
    if project_policy not in KEYFRAME_POLICIES:
        raise GateError('KEYFRAME_POLICY_INVALID')
    r['project']['keyframe_policy'] = project_policy
    assets = index(r['assets'], 'asset_id')
    cast = index(r['cast'], 'character_id')
    scenes = index(r['scenes'], 'scene_id')
    all_shots = {sh['shot_id'] for seg in r['segments'] for sh in seg['shots']}
    supplied = r.get('shot_keyframes', [])
    if not isinstance(supplied, list):
        raise GateError('SHOT_KEYFRAMES_MUST_BE_ARRAY')
    for row in supplied:
        if row.get('shot_id') not in all_shots:
            raise GateError('KEYFRAME_SHOT_UNKNOWN:' + str(row.get('shot_id')))
    rows_all, seen_scenes = [], set()
    clothes = {cid: c['default_wardrobe'] for cid, c in cast.items()}
    for segment in r['segments']:
        policy = segment.get('keyframe_policy', project_policy)
        if policy not in KEYFRAME_POLICIES:
            raise GateError('KEYFRAME_POLICY_INVALID:' + segment['segment_id'])
        scene = scenes[segment['scene_id']]
        first = segment['scene_id'] not in seen_scenes
        if first:
            for cid, state in scene['initial_state'].get('characters', {}).items():
                if cid not in {c for prior in r['segments'][:r['segments'].index(segment)] for c in prior['participants']}:
                    clothes[cid] = state.get('wardrobe', clothes[cid])
        for event in segment.get('before_events', []):
            if event['op'] in {'appearance', 'enter'} and 'wardrobe' in event:
                clothes[event['character_id']] = event['wardrobe']
        own = segment.get('shot_keyframes', [])
        if not isinstance(own, list):
            raise GateError('SHOT_KEYFRAMES_MUST_BE_ARRAY')
        seg_shots = {sh['shot_id'] for sh in segment['shots']}
        if any(row.get('shot_id') not in seg_shots for row in own):
            raise GateError('KEYFRAME_SEGMENT_SHOT_MISMATCH:' + segment['segment_id'])
        candidates = own + [row for row in supplied if row['shot_id'] in seg_shots]
        # A saved normalized request repeats records in the global index and owner
        # segment. These are read-only identical views, never competing authorities.
        dedup = {}
        for row in candidates:
            key = (row['shot_id'], row.get('keyframe_type', 'SHOT_KEYFRAME'))
            if key in dedup and dedup[key] != row:
                raise GateError('KEYFRAME_RECORD_CONFLICT:' + row['shot_id'])
            dedup[key] = row
        rows = []
        for shot in segment['shots']:
            reasons = _risk_reasons(segment, shot, scene, first)
            authored = [row for (sid, _), row in dedup.items() if sid == shot['shot_id']]
            if not authored:
                kind = 'ACTION_KEYFRAME' if 'SPECIAL_ACTION' in reasons else 'SHOT_KEYFRAME'
                authored = [{'shot_id': shot['shot_id'], 'keyframe_type': kind}]
            for raw in authored:
                row = copy.deepcopy(raw)
                kind = row.get('keyframe_type', 'SHOT_KEYFRAME')
                if kind == 'SHOT_REFERENCE': kind = 'SHOT_KEYFRAME'  # request example alias
                if kind not in KEYFRAME_TYPES:
                    raise GateError('KEYFRAME_TYPE_INVALID:' + str(kind))
                required = row.get('keyframe_required', False) or policy == 'ALWAYS'
                if not isinstance(required, bool):
                    raise GateError('KEYFRAME_REQUIRED_MUST_BE_BOOLEAN')
                if policy == 'NEVER' and required:
                    raise GateError('KEYFRAME_REQUIRED_CONFLICTS_NEVER:' + shot['shot_id'])
                if 'reference_authority' in row and row['reference_authority'] != REFERENCE_AUTHORITY:
                    raise GateError('KEYFRAME_AUTHORITY_OVERRIDE_FORBIDDEN:' + shot['shot_id'])
                expected = _sources(r, segment, shot, kind, clothes)
                source = row.get('source_assets', expected)
                if not isinstance(source, list) or any(aid not in assets for aid in source):
                    raise GateError('KEYFRAME_SOURCE_ASSET_UNKNOWN:' + shot['shot_id'])
                if set(expected) - set(source):
                    raise GateError('KEYFRAME_REQUIRED_SOURCE_MISSING:' + shot['shot_id'])
                for aid in source:
                    a = assets[aid]
                    if a.get('role') == 'H3_RUNTIME' and aid not in expected:
                        raise GateError('KEYFRAME_WRONG_RUNTIME_WARDROBE:' + shot['shot_id'] + ':' + aid)
                output = row.get('output')
                if output: output = _safe_output(output)
                existing_id = row.get('asset_id')
                if output and not existing_id:
                    matching = [aid for aid, asset in assets.items() if asset.get('file', '').replace('\\', '/') == output]
                    if len(matching) == 1:
                        existing_id = matching[0]
                if existing_id:
                    if existing_id not in assets or assets[existing_id].get('role') != 'STORYBOARD':
                        raise GateError('KEYFRAME_ASSET_ROLE_INVALID:' + str(existing_id))
                    output = output or _safe_output(assets[existing_id]['file'])
                    if output != assets[existing_id]['file'].replace('\\', '/'):
                        raise GateError('KEYFRAME_ASSET_FILE_CONFLICT:' + shot['shot_id'])
                available = bool(output and (_existing_file(output, asset_root) or (asset_root is None and (existing_id or row.get('status') in {'AVAILABLE', 'VALID'}))))
                recommended = bool(reasons) and policy != 'NEVER'
                if required and not available:
                    raise GateError('REQUIRED_KEYFRAME_MISSING:' + shot['shot_id'])
                if policy == 'NEVER':
                    available = False
                status = 'AVAILABLE' if available else 'MISSING' if required or recommended or output else 'NOT_REQUIRED'
                row.update(shot_id=shot['shot_id'], segment_id=segment['segment_id'], keyframe_type=kind,
                           keyframe_required=required, keyframe_recommended=recommended, source_assets=source,
                           output=output, status=status, reasons=reasons, reference_authority=copy.deepcopy(REFERENCE_AUTHORITY),
                           generation_status='NOT_RUN' if not available else 'EXISTING_ASSET')
                if available:
                    aid = existing_id or 'KF_' + shot['shot_id'] + '_' + kind
                    if aid not in assets:
                        asset = {'asset_id': aid, 'file': output, 'role': 'STORYBOARD', 'direct_bindable': True,
                                 'keyframe_type': kind, 'shot_id': shot['shot_id'], 'scene_id': segment['scene_id'],
                                 'description': bi('镜头构图、当前站位、景别和空间关系参考；人物身份、服装及场景结构仍由基础资产决定。',
                                                   'Reference for shot composition, current blocking, shot scale and spatial relations; base assets retain identity, wardrobe and scene-geometry authority.'),
                                 'reference_authority': copy.deepcopy(REFERENCE_AUTHORITY), 'derived_from': source,
                                 'source_versions': copy.deepcopy(row.get('source_versions', {})),
                                 'generated_from_version': copy.deepcopy(row.get('generated_from_version', row.get('source_versions', {}))),
                                 'version': row.get('version'), 'status': row.get('asset_status', 'UNVERIFIED')}
                        if r['project'].get('style_id'): asset['style_id'] = r['project']['style_id']
                        r['assets'].append(asset)
                        assets[aid] = asset
                    else:
                        asset = assets[aid]
                        if asset.get('reference_authority', REFERENCE_AUTHORITY) != REFERENCE_AUTHORITY:
                            raise GateError('KEYFRAME_AUTHORITY_OVERRIDE_FORBIDDEN:' + aid)
                        if asset.get('shot_id') not in {None, shot['shot_id']} or asset.get('keyframe_type') not in {None, kind}:
                            raise GateError('KEYFRAME_ASSET_SHOT_CONFLICT:' + aid)
                        if asset.get('derived_from') and set(asset['derived_from']) != set(source):
                            raise GateError('KEYFRAME_ASSET_SOURCE_CONFLICT:' + aid)
                        asset.setdefault('derived_from', source)
                        if not asset['derived_from']: asset['derived_from'] = source
                        if 'source_versions' in row:
                            if asset.get('source_versions') and asset['source_versions'] != row['source_versions']:
                                raise GateError('KEYFRAME_ASSET_SOURCE_VERSION_CONFLICT:' + aid)
                            asset['source_versions'] = copy.deepcopy(row['source_versions'])
                        asset.update(keyframe_type=kind, shot_id=shot['shot_id'], reference_authority=copy.deepcopy(REFERENCE_AUTHORITY))
                    row['asset_id'] = aid
                    segment.setdefault('required_asset_ids', [])
                    if aid not in segment['required_asset_ids']: segment['required_asset_ids'].append(aid)
                rows.append(row)
        segment['shot_keyframes'] = rows
        rows_all.extend(copy.deepcopy(rows))
        seen_scenes.add(segment['scene_id'])
        for event in sorted(segment.get('events', []), key=lambda e: e.get('at_s', 0)):
            if event['op'] in {'appearance', 'enter'} and 'wardrobe' in event:
                clothes[event['character_id']] = event['wardrobe']
    r['shot_keyframes'] = rows_all
    return r


def validate_keyframes(request, bindings=None):
    """Check saved planning records and mandatory reference authority in a pack."""
    errors = []
    policy = request.get('project', {}).get('keyframe_policy', 'AUTO')
    if policy not in KEYFRAME_POLICIES: errors.append('KEYFRAME_POLICY_INVALID')
    assets = {a['asset_id']: a for a in request.get('assets', [])}
    records = []
    for segment in request.get('segments', []):
        effective_policy = segment.get('keyframe_policy', policy)
        if effective_policy not in KEYFRAME_POLICIES: errors.append('KEYFRAME_POLICY_INVALID:' + segment['segment_id'])
        rows = segment.get('shot_keyframes', [])
        records.extend(rows)
        shots = {s['shot_id'] for s in segment['shots']}
        if effective_policy == 'ALWAYS' and not rows:
            errors.append('REQUIRED_KEYFRAME_MISSING:' + segment['segment_id'])
        if rows and {row.get('shot_id') for row in rows} != shots:
            errors.append('KEYFRAME_SHOT_COVERAGE_INVALID:' + segment['segment_id'])
        seen = set()
        for row in rows:
            key = (row.get('shot_id'), row.get('keyframe_type'))
            if key in seen: errors.append('KEYFRAME_DUPLICATE:' + str(key))
            seen.add(key)
            if row.get('shot_id') not in shots: errors.append('KEYFRAME_SHOT_UNKNOWN:' + str(row.get('shot_id')))
            if row.get('keyframe_type') not in KEYFRAME_TYPES: errors.append('KEYFRAME_TYPE_INVALID')
            if row.get('status') not in KEYFRAME_STATUSES: errors.append('KEYFRAME_STATUS_INVALID')
            if row.get('reference_authority') != REFERENCE_AUTHORITY: errors.append('KEYFRAME_AUTHORITY_OVERRIDE_FORBIDDEN')
            if (row.get('keyframe_required') or effective_policy == 'ALWAYS') and row.get('status') != 'AVAILABLE':
                errors.append('REQUIRED_KEYFRAME_MISSING:' + str(row.get('shot_id')))
            if row.get('status') == 'AVAILABLE':
                aid = row.get('asset_id')
                if aid not in assets: errors.append('KEYFRAME_ASSET_MISSING:' + str(aid))
                elif assets[aid].get('role') != 'STORYBOARD' or assets[aid].get('reference_authority') != REFERENCE_AUTHORITY:
                    errors.append('KEYFRAME_ASSET_AUTHORITY_INVALID:' + str(aid))
                if bindings is not None:
                    units = bindings.get('units', bindings)
                    matching = [b for b in units.get(segment['segment_id'], {}).values() if b['asset_id'] == aid]
                    if not matching:
                        errors.append('KEYFRAME_PICTURE_MISSING:' + str(aid))
                    for bound in matching:
                        if (bound.get('shot_id') != row['shot_id'] or bound.get('keyframe_type') != row['keyframe_type']
                                or bound.get('reference_authority') != REFERENCE_AUTHORITY):
                            errors.append('KEYFRAME_BINDING_AUTHORITY_INVALID:' + str(aid))
    if 'shot_keyframes' in request and request['shot_keyframes'] != records:
        errors.append('KEYFRAME_GLOBAL_VIEW_MISMATCH')
    if bindings is not None:
        units = bindings.get('units', bindings)
        for uid, pictures in units.items():
            for bound in pictures.values():
                asset = assets.get(bound.get('asset_id'), {})
                if asset.get('keyframe_type'):
                    if (bound.get('reference_authority') != REFERENCE_AUTHORITY
                            or bound.get('shot_id') != asset.get('shot_id')
                            or bound.get('keyframe_type') != asset.get('keyframe_type')):
                        errors.append('KEYFRAME_BINDING_AUTHORITY_INVALID:' + str(bound.get('asset_id')))
                    if uid.startswith('LOCK_') and asset.get('keyframe_type') != 'SPATIAL_ANCHOR_KEYFRAME':
                        errors.append('FORMAL_KEYFRAME_BOUND_TO_LOCK:' + str(bound.get('asset_id')))
    if records:
        try:
            normalized = plan_keyframes(request)
            if normalized['shot_keyframes'] != records:
                errors.append('KEYFRAME_PLAN_NOT_CANONICAL')
        except (GateError, KeyError, TypeError, ValueError) as exc:
            errors.append('KEYFRAME_PLAN_INVALID:' + str(exc))
    return list(dict.fromkeys(errors))
