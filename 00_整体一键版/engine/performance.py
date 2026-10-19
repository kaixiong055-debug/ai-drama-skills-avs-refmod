"""Render authored shot-level acting without changing speech, timing or blocking."""
import re
from .common import GateError

BASELINE = {
    'cn': '表演连续性：可见人物以轻微胸肩起伏保持安静呼吸，切镜延续呼吸和表情，不每次重新起拍。眼神目标遵守本镜站位与构图；按下列镜头表演，不强制每镜眨眼、不让多人同步眨眼。说话口型遵守原台词的发声语言与时间窗；听者不跟读。不可把呼吸变成新增喘息或叹气音效，不增加时长、位移或夸张脸部变形。',
    'en': 'Performance continuity: Visible characters retain subtle, quiet chest/shoulder breathing across cuts; do not restart breath or expression at each cut. Respect established eyelines and framing. Follow the shot-specific acting below; never force a blink in every shot or synchronize blinks across people. Lip movements follow the original dialogue language and timing windows; listeners do not mouth the lines. Breathing adds no audible gasp or sigh, extra duration, movement, or exaggerated facial deformation.'
}

def shot_performance(shot, lang):
    authored = shot.get('performance')
    if authored is not None:
        if not isinstance(authored, dict) or not all(isinstance(authored.get(k), str) and authored[k].strip() for k in ('cn', 'en')):
            raise GateError('SHOT_PERFORMANCE_BILINGUAL_REQUIRED:' + shot['shot_id'])
        return authored[lang]
    if shot.get('face_visible') is False:
        return None
    # Compatibility fallback supplies life, never invents a dramatic emotion or reaction.
    if shot['end_s'] - shot['start_s'] < 1:
        return ('延续前镜的眼神与表情张力；短切内不强制眨眼或安排完整呼吸周期。' if lang == 'cn' else
                'Carry forward the existing gaze and expression; do not force a blink or full breath cycle into this short cut.')
    if shot.get('shot_scale') in ('wide', 'extreme_wide', 'long', 'full'):
        return ('仅用可见胸肩的轻微呼吸避免站姿僵硬；保持原走位，不为面部细节改变远景构图。' if lang == 'cn' else
                'Use only subtle visible chest/shoulder breathing to avoid a rigid pose; preserve blocking and wide framing without adding facial close-ups.')
    return ('保持安静呼吸、自然眼睑张力和已建立的视线；停顿时可自然眨眼，不规定频率或新增情绪。嘴唇只随原台词活动，听者保持自然闭口。' if lang == 'cn' else
            'Maintain quiet breathing, natural eyelid tension and the established gaze. Allow an unforced blink in an existing pause, without a fixed cadence or invented emotion. Lips move only for scheduled lines; listeners keep a relaxed closed mouth.')

def apply_performance(raw, plans, lang, header_lang=None):
    from .validator import parse_md
    units = parse_md(raw, header_lang or lang)
    if not units:
        raise GateError('PERFORMANCE_UNITS_MISSING')
    by_id = {p['segment_id']: p for p in plans}
    prefix = raw[:raw.index(next(iter(units.values())))]
    result = []
    for uid, block in units.items():
        if uid.startswith('LOCK_'):
            result.append(block)
            continue
        if uid not in by_id:
            raise GateError('PERFORMANCE_PLAN_MISSING:' + uid)
        marker = 'shot_timeline:\n'
        if marker not in block:
            raise GateError('PERFORMANCE_TIMELINE_MISSING:' + uid)
        start = block.index(marker) + len(marker)
        ends = [block.find('\n' + key + ':\n', start) for key in ('detailed_description', 'dialogue_and_audio')]
        end = min(x for x in ends if x >= 0)
        timeline = block[start:end]
        shots = by_id[uid]['shots']
        headers = list(re.finditer(r'(?m)^\[Shot (\d+)\s*\|[^\n]*\][ \t]*$', timeline))
        if [int(m[1]) for m in headers] != list(range(1, len(shots) + 1)):
            raise GateError('PERFORMANCE_SHOT_MISMATCH:' + uid)
        # Work backwards so inserting one shot note cannot move the others' offsets.
        active = False
        for shot, match in reversed(list(zip(shots, headers))):
            note = shot_performance(shot, lang)
            if not note:
                continue
            active = True
            label = ('人物表演' if lang == 'cn' else 'Performance') + ' (' + shot['shot_id'] + '): '
            if re.search(r'(?m)^' + re.escape(label), timeline):
                continue
            timeline = timeline[:match.end()] + '\n' + label + note + timeline[match.end():]
        if active and BASELINE[lang] not in timeline:
            timeline = BASELINE[lang] + '\n' + timeline
        result.append(block[:start] + timeline + block[end:])
    return prefix + ''.join(result)
