"""Conservative runtime diagnostics. Never shorten by discarding unique facts."""
import re
from difflib import SequenceMatcher

RUNTIME_SECTIONS = ['subject_definitions', 'summary', 'spatial_state', 'continuity_state',
                    'camera_plan', 'shot_timeline', 'dialogue_and_audio', 'reference_map', 'negative_rules']
RUNTIME_PROMPT_BUDGET = {'cn': {'target_min': 2500, 'target_max': 5000, 'warning_chars': 10000},
                         'en': {'target_min': 3500, 'target_max': 8000, 'warning_chars': 15000},
                         'policy': 'SEMANTIC_COMPLETENESS_FIRST; no hard truncation'}


def sections(block):
    matches=list(re.finditer(r'^('+'|'.join(RUNTIME_SECTIONS)+r'):\s*$',block,re.M))
    return {m[1]:block[m.end():matches[i+1].start() if i+1<len(matches) else len(block)].strip()
            for i,m in enumerate(matches)}


def _normalize(line):
    return re.sub(r'[\s，。；：、,.!;:]+',' ',line.casefold()).strip()


def _sentences(value):
    # Keep decimals, filenames, and keyed records intact.
    return [s.strip() for s in re.split(r'\n+|(?<=[。!?])\s*|(?<=\.)\s+(?=[A-Z])',value) if s.strip()]


def semantic_deduplicate(document):
    """Remove exact repeated prose within an owner, protecting timed execution records.

    Similar sentences are reported, never deleted: a changed digit, name, negation,
    direction, or event scope may be essential. This is deliberately conservative.
    """
    result=[];seen=set();owner=None
    for line in document.splitlines():
        if line.rstrip(':') in RUNTIME_SECTIONS:
            owner=line.rstrip(':');seen=set()
        if re.match(r'^【(?:视频片段|空间预热)|^\[(?:Video Segment|Spatial Warm-up)',line):
            owner=None;seen=set()
        protected=owner in ['shot_timeline','dialogue_and_audio','continuity_state','reference_map']
        if owner=='summary' and not protected:
            unique=[]
            for sentence in _sentences(line):
                sentence_key=_normalize(sentence)
                if len(sentence_key)>=15 and sentence_key in seen:continue
                if sentence_key:seen.add(sentence_key)
                unique.append(sentence)
            line=' '.join(unique)
            if not line:continue
            # Its sentences were already entered into the summary seen set.
            result.append(line);continue
        key=_normalize(line)
        if not protected and len(key)>=15 and key in seen:continue
        if key:seen.add(key)
        result.append(line)
    return '\n'.join(result).rstrip()+'\n\n'


def _blocks(document,lang):
    from .validator import parse_md
    try:
        parsed=parse_md(document,lang or ('cn' if '【视频片段' in document or '【空间预热' in document else 'en'))
        return parsed or {'PROMPT':document}
    except ValueError:return {'PROMPT':document}


def _side(value):
    v=value.casefold().replace('screen ','').replace('screen-','').strip()
    return {'左':'left','左侧':'left','右':'right','右侧':'right','南侧':'south','北侧':'north',
            '东侧':'east','西侧':'west','前方':'forward'}.get(v,v)


def validate_prompt_redundancy(document,lang=None,negative_repeat_threshold=1):
    """Return fatal duplicate/conflict diagnostics; soft length warnings are separate.

    Dynamic state changes in continuity/timeline are not mistaken for conflicting
    *current* declarations. Canonical-render equality independently guards changes.
    """
    errors=[]
    for uid,block in _blocks(document,lang).items():
        data=sections(block);spatial=[];facts={};axis=[]
        for owner,body in data.items():
            for sentence in _sentences(body):
                if re.search(r'(?i)(?:screen[- ](?:left|right)|left.to.right|facing\s*[=:]|faces\b|camera.side\s*[=:]|dialogue.axis\s*[=:]|geometry\.|位于|朝向|从左到右|摄影机侧|对话轴[：:])',sentence):
                    if owner not in ['continuity_state','shot_timeline','negative_rules','reference_map']:
                        spatial.append((owner,sentence))
            if owner in ['continuity_state','shot_timeline','negative_rules','reference_map']:continue
            for line in body.splitlines():
                # Renderer emits explicit per-character ownership records.
                char=re.search(r'\((CHAR_[^)]+)\):',line)
                if char:
                    for key in ['screen_position','facing','eyeline']:
                        m=re.search(r'\b'+key+r'=([^;；\n]+)',line)
                        if m: facts.setdefault((char[1],key),[]).append(_side(m[1]))
                for key in ['camera_side','dialogue_axis']:
                    for m in re.finditer(r'(?i)\b'+key.replace('_',r'[_ ]')+r'\s*[=:]\s*([^;；\n.]+)',line):
                        facts.setdefault(('scene',key),[]).append(_side(m[1]))
                        if key=='dialogue_axis':axis.append(m[1])
                geo=re.match(r'\s*(geometry\.[^=]+)=([^\n]+)',line)
                if geo:facts.setdefault(('geometry',geo[1]),[]).append(_normalize(geo[2]))
                # Also inspect natural edits pasted into the runtime prompt.
                for m in re.finditer(r'([A-Z][\w]*(?: [A-Z][\w]*){0,3}) (?:stays at|is at|is on|stands on|stands at|is) (?:the )?(screen[ -](?:left|right))',line):
                    facts.setdefault((m[1],'screen_position'),[]).append(_side(m[2]))
                for m in re.finditer(r'([A-Z][\w]*(?: [A-Z][\w]*){0,3}) faces (?:screen[ -])?(left|right)',line):
                    facts.setdefault((m[1],'facing'),[]).append(_side(m[2]))
                for m in re.finditer(r'([\u3400-\u9fff]{2,8})(?:位于|在)(?:画面)?(左侧|右侧)',line):
                    facts.setdefault((m[1],'screen_position'),[]).append(_side(m[2]))
                for m in re.finditer(r'([\u3400-\u9fff]{2,8})(?:面向|朝向)(左侧|右侧|左|右)',line):
                    facts.setdefault((m[1],'facing'),[]).append(_side(m[2]))
        for key,values in facts.items():
            if len(set(values))>1:errors.append(uid+':RUNTIME_FACT_CONFLICT:'+':'.join(key))
            elif key[0]=='geometry' and len(values)>1:errors.append(uid+':RUNTIME_GEOMETRY_REPEATED:'+key[1])
        if len(axis)>1:errors.append(uid+':RUNTIME_AXIS_REDEFINED')
        for i,(owner,sentence) in enumerate(spatial):
            normalized=_normalize(sentence)
            if len(normalized)<24:continue
            for previous_owner,previous in spatial[:i]:
                other=_normalize(previous)
                # Ratio alone cannot authorize deletion; it only raises a review error.
                same_entities=set(re.findall(r'CHAR_[\w]+',sentence))==set(re.findall(r'CHAR_[\w]+',previous))
                if normalized==other or ((previous_owner!=owner or same_entities) and min(len(normalized),len(other))>=45 and same_entities and SequenceMatcher(None,normalized,other).ratio()>=.94):
                    errors.append(uid+':RUNTIME_SPATIAL_REPEATED:'+previous_owner+':'+owner);break
        negatives=[_normalize(v) for v in _sentences(data.get('negative_rules','')) if len(_normalize(v))>8]
        repeats=sum(negatives.count(v)-1 for v in set(negatives))
        if repeats>=negative_repeat_threshold:errors.append(uid+':RUNTIME_NEGATIVE_REPEATED')
    return list(dict.fromkeys(errors))


def budget_warnings(document,lang='en',budget=None):
    settings=(budget or RUNTIME_PROMPT_BUDGET).get(lang,RUNTIME_PROMPT_BUDGET[lang])
    warning=settings.get('warning_chars',(budget or {}).get('ordinary_two_person_warning',RUNTIME_PROMPT_BUDGET[lang]['warning_chars']) if lang=='en' else RUNTIME_PROMPT_BUDGET[lang]['warning_chars'])
    return [uid+':RUNTIME_PROMPT_OVERVERBOSE:'+str(len(block)) for uid,block in _blocks(document,lang).items()
            if uid.startswith('SEG') and len(block)>warning]
