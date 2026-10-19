"""Explicit scale provenance; numerical layout coordinates never imply metres."""
from copy import deepcopy
import math
import re
from .common import bi, finite

MODES = ('RELATIVE', 'METRIC', 'UNKNOWN')
SOURCES = ('USER_SPECIFIED', 'DIMENSIONED_FLOORPLAN', 'BLENDER_3D', 'CAD',
           'VERIFIABLE_SCALE', 'CANONICAL_SCENE')
DEFAULT = {'measurement_mode': 'RELATIVE', 'confidence': 'UNKNOWN'}
METRES = re.compile(r'\d+(?:\.\d+)?\s*(?:米|m(?:eters?|etres?)?\b)', re.I)


def measurement_for(scene):
    """No inference from image/coordinate magnitude, including legacy x_m fields."""
    return deepcopy(scene.get('spatial_measurement', DEFAULT))


def prepare_measurements(request):
    r = deepcopy(request)
    for scene in r.get('scenes', []):
        scene.setdefault('spatial_measurement', deepcopy(DEFAULT))
    return r


def validate_spatial_measurements(request):
    from .spatial import GEOMETRY
    errors = []
    for scene in request.get('scenes', []):
        sid = scene.get('scene_id', '?')
        m = measurement_for(scene)
        if not isinstance(m, dict):
            errors.append(sid + ':SPATIAL_MEASUREMENT_INVALID'); continue
        mode = m.get('measurement_mode')
        if mode not in MODES: errors.append(sid + ':MEASUREMENT_MODE_INVALID')
        if m.get('confidence') not in ('HIGH', 'MEDIUM', 'LOW', 'UNKNOWN'):
            errors.append(sid + ':MEASUREMENT_CONFIDENCE_INVALID')
        if mode == 'METRIC':
            p = m.get('provenance', {})
            if not isinstance(p, dict) or p.get('source_type') not in SOURCES or any(
                    not isinstance(p.get(k), str) or not p[k].strip() for k in ('source_id', 'evidence')):
                errors.append(sid + ':METRIC_PROVENANCE_REQUIRED')
            if m.get('source_measurement_mode') in ('RELATIVE', 'UNKNOWN'):
                errors.append(sid + ':RELATIVE_TO_METRIC_FORBIDDEN')
        else:
            if m.get('constraints'):
                errors.append(sid + ':METRIC_CONSTRAINT_WITHOUT_METRIC_PROVENANCE')
            # Camera lens/height are authored camera settings, not measured scene scale.
            geometry = {k: scene.get('initial_state', {}).get(k, scene.get(k, {})) for k in GEOMETRY}
            def check(v):
                if isinstance(v, str) and METRES.search(v):
                    errors.append(sid + ':UNVERIFIED_METRIC_GEOMETRY')
                elif isinstance(v, dict):
                    for child in v.values(): check(child)
                elif isinstance(v, list):
                    for child in v: check(child)
            check(geometry)
            check(m.get('relative_descriptions', {}))
        positions = scene.get('initial_state', {}).get('character_positions', {})
        refs = set(positions)
        for key in GEOMETRY:
            refs.update(scene.get('initial_state', {}).get(key, scene.get(key, {})))
        constraint_pairs = {}
        for c in m.get('constraints', []):
            if (not isinstance(c, dict) or not finite(c.get('distance_m')) or c['distance_m'] < 0
                    or c.get('subject_id') not in refs or c.get('reference_id') not in refs):
                errors.append(sid + ':METRIC_CONSTRAINT_INVALID')
                continue
            pair=tuple(sorted([c['subject_id'],c['reference_id']]))
            if pair in constraint_pairs and not math.isclose(constraint_pairs[pair],c['distance_m'],abs_tol=.001):
                errors.append(sid + ':METRIC_CONSTRAINT_CONFLICT')
            constraint_pairs[pair]=c['distance_m']
            if all(ref in positions for ref in pair):
                a,b=(positions[ref] for ref in pair)
                if all(finite(p.get(k)) for p in [a,b] for k in ['x_m','y_m']):
                    actual=math.hypot(a['x_m']-b['x_m'],a['y_m']-b['y_m'])
                    if not math.isclose(actual,c['distance_m'],abs_tol=.001):
                        errors.append(sid + ':METRIC_COORDINATE_CONSTRAINT_CONFLICT')
        for plan in request.get('segments', []):
            if plan.get('scene_id') != sid: continue
            for event in plan.get('events', []) + plan.get('before_events', []):
                if 'spatial_measurement' in event or 'measurement_mode' in event:
                    errors.append(sid + ':EVENT_MEASUREMENT_OVERRIDE_FORBIDDEN')
    return list(dict.fromkeys(errors))


def relative_distance(a, b, positions, order, measurement):
    declared = measurement.get('relative_descriptions', {}).get(a + '|' + b)
    if declared is not None: return deepcopy(declared)
    adjacent = abs(order.index(a) - order.index(b)) == 1
    same_depth = positions[a]['depth'] == positions[b]['depth']
    if adjacent and same_depth:
        return bi('相邻，保持已建立的相对间隔；未提供米制尺度',
                  'Adjacent, maintaining the established relative spacing; metric scale is unspecified')
    return bi('保持已建立的横向与前后层次关系；未提供米制尺度',
              'Maintain the established lateral and depth relationship; metric scale is unspecified')
