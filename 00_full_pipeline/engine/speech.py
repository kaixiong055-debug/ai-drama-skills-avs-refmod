"""Keep prompt prose language separate from the language of performed dialogue."""
import re
from .common import GateError

MANDARIN_RULE = {
    'cn': '对白语言要求：标记为中文的原台词必须用普通话逐字说出，不翻译、不改写、不使用英文配音；口型对应中文发音，按原时间窗每句只说一次。人物名、时间码、语言标签及画面动作指令不得朗读，不新增旁白或对白。明确标记为其他语言的台词仍遵守各自语言。',
    'en': 'Spoken-language requirement: Speak every Chinese-tagged original line verbatim in Mandarin Chinese. Do not translate, paraphrase, or dub these lines in English. Match lip movements to Chinese speech; speak each line once within its scheduled window. Never read character names, timestamps, language tags, or scene/action instructions aloud. Add no narration or unscripted speech. Explicitly tagged other languages retain their own language.'
}

def enforce_spoken_language(raw, lang):
    """Upgrade each independent unit, including legacy exports; leave silent units intact."""
    if lang not in MANDARIN_RULE:
        raise GateError('PROMPT_LANGUAGE_UNSUPPORTED:' + lang)
    header = r'(?m)(?=^(?:【(?:视频片段|视频段|空间预热|隐藏空间预热|空间锁)\s|\[(?:Video Segment|Spatial Warm-up)\s))'
    parts = re.split(header, raw)
    marker = 'dialogue_and_audio:\n'
    for i, block in enumerate(parts):
        if not re.search(r'<d>\[(?:Chinese|Mandarin(?: Chinese)?|中文|普通话|zh(?:-CN)?)\]\s*\S[\s\S]*?</d>', block, re.I):
            continue
        if marker not in block:
            raise GateError('DIALOGUE_AUDIO_SECTION_MISSING')
        audio = block.split(marker, 1)[1].split('\n\n', 1)[0]
        if MANDARIN_RULE[lang] not in audio:
            parts[i] = block.replace(marker, marker + MANDARIN_RULE[lang] + '\n', 1)
    return ''.join(parts)
