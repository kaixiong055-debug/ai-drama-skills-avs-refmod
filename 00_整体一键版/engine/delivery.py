"""Allowlisted user handoff. Canonical JSON and execution records remain internal."""
import os
from pathlib import Path
import shutil
import tempfile
from .common import GateError, load, save, SECTIONS
from .speech import enforce_spoken_language
from .performance import apply_performance


def internal_project(output):
    output = Path(output).resolve()
    return output.parent / '.ai_drama_internal' / output.name / 'production'


def resolve_project(path):
    path = Path(path).resolve()
    if (path / '01_story.json').is_file():
        return path
    internal = internal_project(path)
    if (internal / '01_story.json').is_file():
        return internal
    raise GateError('INTERNAL_PROJECT_NOT_FOUND:' + str(path))


def _first(project, names):
    return next((project / n for n in names if (project / n).is_file()), None)


def _text(value, lang):
    return value.get(lang, '') if isinstance(value, dict) else str(value or '')


def english_with_chinese_metadata(cn_text, en_text):
    """Keep Chinese import headers and the exact English FULL bodies, including dialogue."""
    from .validator import parse_md
    cn = parse_md(cn_text, 'cn')
    en = parse_md(en_text, 'en')
    if not cn or list(cn) != list(en):
        raise GateError('DELIVERY_LANGUAGE_UNIT_MISMATCH')
    marker = 'subject_definitions:\n'
    if any(marker not in block for units in (cn, en) for block in units.values()):
        raise GateError('ONE_CLICK_H3_FORMAT_INVALID:SUBJECT_DEFINITIONS')
    # Retain the Chinese review/draft notice before the first unit as well.
    prefix = cn_text[:cn_text.index(next(iter(cn.values())))]
    return prefix + ''.join(cn[uid].split(marker, 1)[0] + marker +
                            en[uid].split(marker, 1)[1] for uid in cn)


def _asset_prompts(project, lang):
    existing = _first(project, [f'人物场景道具_出图提示词_{lang.upper()}.md'])
    if existing:
        return existing.read_text(encoding='utf-8')
    tasks = load(project / 'asset_generation_tasks.json') if (project / 'asset_generation_tasks.json').is_file() else []
    if isinstance(tasks, dict):
        tasks = tasks.get('tasks', tasks.get('assets', []))
    by_id = {a['asset_id']: a for a in tasks}
    data = load(project / '03_assets.json')['assets']
    title = '# 人物、场景与道具设计\n\n' if lang == 'cn' else '# Character, location and prop designs\n\n'
    parts = [title]
    for a in data:
        task = by_id.get(a['asset_id'], {})
        prompt = task.get('prompt_' + lang) or _text(a.get('generation_prompt'), lang) or _text(a.get('description'), lang)
        parts.append(f'## {a["asset_id"]}\n\n目标文件 / Target file: `{a["file"]}`\n\n{prompt}\n\n')
    return ''.join(parts)


def _shot_table(project):
    existing = project / '分镜执行表_中文.md'
    if existing.is_file():
        return existing.read_text(encoding='utf-8')
    cast = {c['character_id']: _text(c['name'], 'cn') for c in load(project / '02_cast.json')['characters']}
    beats = {b['beat_id']: b for b in load(project / '04_script.json')['beats']}
    plans = load(project / '05_storyboard.json')['segments']
    parts = ['# 分镜执行表\n\n每段正式时长5秒；隐藏LOCK不进入成片。重复提及同一动作仅执行一次。\n\n']
    for p in plans:
        parts.append(f'## {p["segment_id"]} · {_text(p["title"], "cn")}\n\n')
        if p.get('bridge_description'):
            parts.append('时间桥接：' + _text(p['bridge_description'], 'cn') + '\n\n')
        for sh in p['shots']:
            parts.append(f'**{sh["shot_id"]}｜{sh["start_s"]:.3f}—{sh["end_s"]:.3f}秒｜{sh["shot_scale"]}｜{sh["lens_mm"]}mm**\n\n')
            parts.append('画面：' + _text(sh['composition'], 'cn') + '\n\n动作：' + _text(sh['action'], 'cn') + '\n\n')
            for bid in sh['beat_ids']:
                b = beats[bid]
                if b.get('dialogue'):
                    parts.append(f'{cast[b["speaker"]]}：{b["dialogue"]}\n\n')
            parts.append('切镜理由：' + _text(sh['cut_reason'], 'cn') + '\n\n')
    return ''.join(parts)


def export_delivery(project, output, *, allow_draft=False):
    """Copy only presentation files; never zip/copy the engineering directory."""
    project = Path(project).resolve()
    output = Path(output).resolve()
    if project == output or project.is_relative_to(output) or output.is_relative_to(project):
        raise GateError('DELIVERY_MUST_BE_SEPARATE_FROM_INTERNAL_PROJECT')
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise GateError('OUTPUT_DIRECTORY_NOT_EMPTY:' + str(output))
    review = load(project / 'production_review.json')
    draft = review.get('status') != 'READY'
    if draft and not allow_draft:
        raise GateError('DELIVERY_NOT_READY:' + str(review.get('status')))
    if not draft:
        from .validator import validate_directory
        errors = validate_directory(project, project / 'assets')
        if errors:
            raise GateError('\n'.join(errors))
    from .validator import parse_md
    prompts = {}
    for lang in ['CN', 'EN']:
        path = _first(project, [f'H3_PROMPTS_FULL_{lang}.md', f'H3_PROMPTS_FULL_{lang}_待出图.md'])
        if path is None:
            raise GateError('FULL_PROMPT_MISSING:' + lang)
        raw = path.read_text(encoding='utf-8')
        units = parse_md(raw, lang.lower())
        if not units or any(field + ':\n' not in unit for unit in units.values() for field in SECTIONS):
            raise GateError('ONE_CLICK_H3_FORMAT_INVALID:' + lang)
        prompts[lang] = (path, units)
    if list(prompts['CN'][1]) != list(prompts['EN'][1]):
        raise GateError('DELIVERY_LANGUAGE_UNIT_MISMATCH')
    production = load(project / '06_production.json')
    spatial = load(project / '07_spatial_locks.json')
    expected = {u['unit_id'] for u in production['units']} | {l['lock_id'] for l in spatial['locks']}
    if set(prompts['CN'][1]) != expected:
        raise GateError('DELIVERY_CANONICAL_UNIT_MISMATCH')
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix='.user-delivery-', dir=output.parent))
    try:
        for lang, label, number in [('CN', '中文版', '04'), ('EN', '英文版', '05')]:
            suffix = '_待出图' if draft else ''
            target = staging / f'{number}_H3一键提示词_{label}{suffix}.md'
            if lang == 'CN':
                content = prompts[lang][0].read_text(encoding='utf-8')
            else:
                content = english_with_chinese_metadata(
                    prompts['CN'][0].read_text(encoding='utf-8'),
                    prompts['EN'][0].read_text(encoding='utf-8'))
            plans = load(project / '05_storyboard.json')['segments']
            updated = enforce_spoken_language(apply_performance(content, plans, lang.lower(), 'cn'), lang.lower())
            if lang == 'CN' and updated == content:
                shutil.copy2(prompts[lang][0], target)
            else:
                target.write_text(updated, encoding='utf-8', newline='\n')
        (staging / '01_人物场景道具提示词_中文版.md').write_text(_asset_prompts(project, 'cn'), encoding='utf-8')
        (staging / '02_人物场景道具提示词_英文版.md').write_text(_asset_prompts(project, 'en'), encoding='utf-8')
        (staging / '03_分镜执行表.md').write_text(_shot_table(project), encoding='utf-8')
        status = ('当前图片尚未准备完成，H3提示词是待出图审阅稿；完成素材并重新验证后再运行。'
                  if draft else '提示词与本地素材结构检查已通过；视频效果仍需生成后检查。')
        missing = [a for a in load(project / '03_assets.json')['assets'] if a.get('status') == 'MISSING']
        guide = ('# 使用说明\n\n' + status + '\n\n'
                 '1. 按01或02制作人物、场景和道具图片；两份分别是中文、英文版本。\n'
                 '2. 用03查看剧情、动作、对白与切镜。\n'
                 '3. 生成视频时选04中文或05英文提示词使用，二者对应同一套剧情，不需要都提交。\n\n'
                 f'正式视频计划：{production["final_segment_count"]}段，共{production["final_runtime_s"]}秒。隐藏LOCK不进入成片。\n\n'
                 '每种语言只交付一份FULL 14栏H3提示词。英文版保留中文段头和导入字段，正文为英文，原中文对白不翻译；固定标识与素材路径保持原样。\n')
        if missing:
            guide += '\n待制作素材：\n\n' + ''.join(f'- {a["asset_id"]} → `{a["file"]}`\n' for a in missing)
        (staging / '00_使用说明.md').write_text(guide, encoding='utf-8')
        # Copy only real registered images. Missing references never become placeholder files.
        files = load(project / '08_binding.json').get('asset_files', {})
        for row in files.values():
            rel = Path(row['file'])
            if rel.is_absolute() or '..' in rel.parts or rel.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp', '.bmp'}:
                raise GateError('DELIVERY_ASSET_PATH_INVALID:' + str(rel))
            src = (project / 'assets' / rel).resolve()
            if not src.is_relative_to((project / 'assets').resolve()) or not src.is_file():
                raise GateError('DELIVERY_ASSET_FILE_MISSING:' + str(rel))
            target = staging / 'assets' / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, target)
        # Stage is validated before the public directory becomes visible.
        if list(staging.rglob('*.json')) or len(list(staging.glob('*.md'))) != 6:
            raise GateError('USER_DELIVERY_CONTENT_INVALID')
        if output.exists():
            output.rmdir()  # Verified empty above; never recursive removal.
        os.replace(staging, output)
    finally:
        # This is the exact temporary directory created above, never a user-selected tree.
        if staging.exists():
            shutil.rmtree(staging)
    save(project / 'user_delivery.internal.json', {'public_output': str(output), 'draft': draft,
         'files': [p.relative_to(output).as_posix() for p in sorted(output.rglob('*')) if p.is_file()]})
    return output


def export_user_project(request, asset_root, output):
    """CLI/GUI entry: internal build first, then the allowlisted user handoff."""
    from .pipeline import export_project
    output = Path(output).resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise GateError('OUTPUT_DIRECTORY_NOT_EMPTY:' + str(output))
    internal = internal_project(output)
    export_project(request, asset_root, internal)
    return export_delivery(internal, output)
