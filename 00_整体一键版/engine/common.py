import hashlib
import json
import math
from pathlib import Path

VERSION = '5.1'
FILES = ['01_story.json', '02_cast.json', '03_assets.json', '04_script.json',
         '05_storyboard.json', '06_production.json', '07_spatial_locks.json', '08_binding.json']
SECTIONS = ['subject_definitions', 'summary', 'retention_analysis', 'spatial_state',
            'continuity_state', 'physical_continuity_locks', 'camera_plan', 'shot_timeline',
            'detailed_description', 'dialogue_and_audio', 'overall_soundscape',
            'non_diegetic_music', 'reference_map', 'negative_rules']
PROFILES = {'DRAMA_DIALOGUE': 3, 'ACTION': 2, 'TRANSFORMATION': 1,
            '2D_COMIC': 2, 'CINEMATIC_MULTI_SHOT': 3}
REJECT_REASONS = ['IDENTITY_DRIFT', 'FACE_DRIFT', 'COSTUME_DRIFT', 'POSITION_DRIFT',
                  'LEFT_RIGHT_SWAP', 'AXIS_FLIP', 'EYELINE_ERROR', 'SCENE_GEOMETRY_DRIFT',
                  'PROP_DISAPPEAR', 'PROP_SPAWN', 'HAND_DEFORMATION', 'EXTRA_LIMB',
                  'ACTION_NOT_COMPLETED', 'ACTION_REPEATED', 'SOUND_REPEATED',
                  'END_FRAME_DEFORMATION', 'MOTION_BLUR_EXCESSIVE']


class GateError(ValueError):
    pass


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def text(v, lang):
    if not isinstance(v, dict) or not isinstance(v.get(lang), str) or not v[lang].strip():
        raise GateError('BILINGUAL_TEXT_MISSING:' + lang)
    return v[lang]


def bi(cn, en):
    return {'cn': cn, 'en': en}


def finite(v):
    return isinstance(v, (float, int)) and not isinstance(v, bool) and math.isfinite(v)


def index(rows, key):
    out = {}
    for row in rows:
        ident = row.get(key)
        if not isinstance(ident, str) or not ident or ident in out:
            raise GateError('ID_MISSING_OR_DUPLICATE:' + key + ':' + str(ident))
        out[ident] = row
    return out


def envelope(kind, content, inputs):
    return {'schema_version': VERSION, 'kind': kind,
            'lineage': {k: digest(v) for k, v in inputs.items()}, **content}
