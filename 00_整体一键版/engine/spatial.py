"""Event-driven world state. Cropping never mutates a character position."""
from copy import deepcopy
from itertools import combinations
import math
from .common import GateError, bi, digest, finite
from .measurement import measurement_for, relative_distance

GEOMETRY = ['fixed_architecture', 'door_positions', 'window_positions', 'furniture_positions',
            'entrance_positions', 'exit_positions']


def initial_state(scene, cast, participants):
    seed = deepcopy(scene.get('initial_state', {}))
    positions = seed.setdefault('character_positions', {})
    for n, cid in enumerate(participants):
        if cid not in positions:raise GateError('INITIAL_POSITION_MISSING:'+scene['scene_id']+':'+cid)
    positions = {cid: positions[cid] for cid in participants}
    state = {'scene_id': scene['scene_id'], 'scene_variant': scene.get('scene_variant', 'MASTER'),
             'spatial_measurement': measurement_for(scene),
             'area': scene.get('area', 'MAIN'), 'character_positions': positions,
             'camera_side': seed.get('camera_side', 'south'),
             'dialogue_axis': seed.get('dialogue_axis', 'locked_east_west'),
             'dialogue_group': [c for c in seed.get('dialogue_group', participants[:2]) if c in participants],
             'major_props': deepcopy(seed.get('major_props', {})),
             'door_states': deepcopy(seed.get('door_states', {})),
             'characters': {}, 'completed_actions': [], 'completed_sounds': [],
             'valid_until_changed': True}
    for key in GEOMETRY:
        state[key] = deepcopy(seed.get(key, scene.get(key, {})))
    for cid in participants:
        char = cast[cid]
        state['characters'][cid] = {'wardrobe': char['default_wardrobe'],
                                    'hair_state': char.get('hair_state', 'dry'),
                                    'clothing_state': bi('干燥、完整', 'dry and intact'),
                                    'pose': bi('自然站立', 'standing naturally')}
        state['characters'][cid].update(copy_values(seed.get('characters',{}).get(cid,{})))
    return normalize(state)


def copy_values(value):
    return {k:deepcopy(v) for k,v in value.items() if k in ['wardrobe','hair_state','clothing_state','pose']}


def normalize(state):
    out = deepcopy(state)
    ps = out['character_positions']
    sign = -1 if out['camera_side'] in ['north','east'] else 1
    axis = 'y_m' if out['camera_side'] in ['east','west'] else 'x_m'
    out['left_to_right_order'] = sorted(ps, key=lambda c: (sign*ps[c][axis], c))
    names = {'foreground': 'foreground_characters', 'midground': 'midground_characters', 'background': 'background_characters'}
    for depth, key in names.items(): out[key] = [c for c in out['left_to_right_order'] if ps[c]['depth'] == depth]
    measurement = out.setdefault('spatial_measurement', measurement_for({}))
    metric = measurement['measurement_mode'] == 'METRIC'
    out['coordinate_unit'] = 'metres' if metric else 'relative_layout'
    out['distance_between_characters'] = {
        a + '|' + b: (round(math.hypot(ps[a]['x_m']-ps[b]['x_m'], ps[a]['y_m']-ps[b]['y_m']), 3)
                     if metric else relative_distance(a, b, ps, out['left_to_right_order'], measurement))
        for a, b in combinations(sorted(ps), 2)}
    out['facing'] = {c: v['facing'] for c, v in ps.items()}
    out['eyelines'] = {c: v['eyeline_target'] for c, v in ps.items()}
    count = len(ps)
    for n, cid in enumerate(out['left_to_right_order']):
        ps[cid]['screen_position'] = ('center' if count == 1 else 'left' if n == 0 else
                                      'right' if n == count-1 else f'center_{n+1}_of_{count}')
        # Body orientation is authored state. An eyeline toward another character
        # may involve the eyes/head only and must not silently rotate the body.
    out['facing'] = {c: v['facing'] for c, v in ps.items()}
    return out


def signature(state):
    # Wardrobe, props, breathing and individual eyelines do not invalidate geometry.
    keys = ['scene_id', 'scene_variant', 'area', 'character_positions', 'camera_side',
            'dialogue_axis', 'dialogue_group', 'spatial_measurement'] + GEOMETRY
    value = {k: state[k] for k in keys}
    value['character_positions'] = {c: {k: p[k] for k in ['x_m', 'y_m', 'depth']}
                                    for c, p in state['character_positions'].items()}
    return digest(value)


def lock_reasons(old, new, flags):
    if old is None or old['scene_id'] != new['scene_id']: return ['NEW_SCENE']
    reasons = []
    a, b = set(old['character_positions']), set(new['character_positions'])
    if b-a: reasons.append('CHARACTER_ENTER')
    if a-b: reasons.append('CHARACTER_EXIT')
    for k, code in [('area', 'AREA_CHANGE'), ('camera_side', 'AXIS_CROSS'),
                    ('dialogue_axis', 'AXIS_CHANGE'), ('dialogue_group', 'DIALOGUE_GROUP_CHANGE'),
                    ('scene_variant', 'SCENE_VARIANT_CHANGE')]:
        if old[k] != new[k]: reasons.append(code)
    if any(old['character_positions'][c][k] != new['character_positions'][c][k]
           for c in a&b for k in ['x_m', 'y_m', 'depth']): reasons.append('POSITION_CHANGE')
    if any(old[k] != new[k] for k in GEOMETRY): reasons.append('GEOMETRY_CHANGE')
    if flags.get('spatial_unreliable'): reasons.append('CLOSEUP_INHERITANCE_UNRELIABLE')
    if flags.get('review_drift'): reasons.append('REVIEW_SPATIAL_DRIFT')
    return reasons


def apply_event(state, event, cast, scenes):
    out = deepcopy(state)
    op = event['op']
    cid = event.get('character_id')
    if op == 'enter':
        if cid not in cast or cid in out['character_positions']: raise GateError('ENTER_INVALID:' + str(cid))
        out['character_positions'][cid] = deepcopy(event['position'])
        out['characters'][cid] = {'wardrobe': event.get('wardrobe', cast[cid]['default_wardrobe']),
                                 'hair_state': event.get('hair_state', 'dry'),
                                 'clothing_state': bi('干燥、完整', 'dry and intact'),
                                 'pose': bi('自然站立', 'standing naturally')}
    elif op == 'exit':
        if cid not in out['character_positions']: raise GateError('EXIT_INVALID:' + str(cid))
        out['character_positions'].pop(cid); out['characters'].pop(cid)
        out['dialogue_group'] = [c for c in out['dialogue_group'] if c != cid]
        for p in out['character_positions'].values():
            if p['eyeline_target'] == cid: p['eyeline_target'] = event.get('exit_direction', 'forward')
    elif op == 'move':
        if not event.get('path'): raise GateError('MOVEMENT_PATH_MISSING')
        if cid not in out['character_positions']: raise GateError('MOVE_UNKNOWN_CHARACTER')
        out['character_positions'][cid].update(event['position'])
    elif op == 'axis':
        if not event.get('authorized'): raise GateError('UNAUTHORIZED_AXIS_CROSS')
        opposite={'north':'south','south':'north','east':'west','west':'east'}
        if opposite.get(out['camera_side'])==event['camera_side']:
            for position in out['character_positions'].values():
                position['facing']={'left':'right','right':'left','screen-left':'screen-right',
                                    'screen-right':'screen-left'}.get(position['facing'],position['facing'])
        out['camera_side'] = event['camera_side']
        # Planned new projection must be explicit; world coordinates remain stable.
        out['dialogue_axis'] = event.get('dialogue_axis', out['dialogue_axis'])
    elif op == 'group': out['dialogue_group'] = event['members']
    elif op == 'area':
        if not event.get('path'): raise GateError('AREA_PATH_MISSING')
        out['area'] = event['area']
    elif op == 'appearance':
        if cid not in out['characters']: raise GateError('APPEARANCE_UNKNOWN_CHARACTER')
        if not event.get('cause'): raise GateError('APPEARANCE_CAUSE_MISSING')
        if 'wardrobe' in event and not event.get('off_screen_window'):
            raise GateError('WARDROBE_CHANGE_NEEDS_OFF_SCREEN_WINDOW')
        for k in ['wardrobe', 'hair_state', 'clothing_state', 'pose']:
            if k in event: out['characters'][cid][k] = deepcopy(event[k])
    elif op == 'prop':
        pid = event['prop_id']
        if pid not in out['major_props'] and not event.get('authorized_spawn'): raise GateError('PROP_PROVENANCE_MISSING:' + pid)
        if pid in out['major_props'] and event.get('from_holder') != out['major_props'][pid]['holder']:
            raise GateError('PROP_HOLDER_HANDOFF_CONFLICT:' + pid)
        out['major_props'][pid] = {'holder': event['holder'], 'state': event['state'],
                                  'valid_until_changed': True}
    elif op == 'door':
        if event['door_id'] not in out['door_positions']: raise GateError('UNKNOWN_DOOR')
        out['door_states'][event['door_id']] = event['state']
    elif op == 'action':
        if event['event_id'] in out['completed_actions']: raise GateError('ACTION_REPEATED:' + event['event_id'])
        if event.get('phase') == 'prepare': raise GateError('PREPARE_ACTION_MUST_NOT_BE_COUNTED')
        out['completed_actions'].append(event['event_id'])
    elif op == 'sound':
        if event['event_id'] in out['completed_sounds']: raise GateError('SOUND_REPEATED:' + event['event_id'])
        out['completed_sounds'].append(event['event_id'])
    else: raise GateError('UNKNOWN_STATE_EVENT:' + op)
    return normalize(out)
