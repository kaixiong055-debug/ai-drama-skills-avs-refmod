"""Evidence-backed H3 A/B/C registry. Empty registries never imply video success."""
import copy
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from .common import GateError, digest, finite, load, save

METRICS = ['identity_drift', 'position_drift', 'left_right_swap', 'axis_flip',
           'eyeline_error', 'scene_geometry_drift', 'prop_drift', 'end_frame_deformation']
METADATA = ['model', 'model_version', 'workflow', 'resolution', 'steps', 'seed',
            'prompt_version', 'hidden_lock', 'continuation', 'reference_assets',
            'runtime_seconds', 'output_file', 'scenario_signature']
CASE_NAMES = [
    ('双人连续3段对白', 'Two-person dialogue across three segments'),
    ('双人8轮对白', 'Two-person dialogue across eight exchanges'),
    ('三人对白插话', 'Three-person dialogue with an interruption'),
    ('四人客厅群聊', 'Four-person living-room conversation'),
    ('五人会议式小群戏', 'Five-person meeting scene'),
    ('角色进场', 'Character entrance'), ('角色退场', 'Character exit'),
    ('角色换位', 'Characters change positions'), ('门口对话', 'Doorway dialogue'),
    ('餐桌多人对话', 'Group dialogue around a dining table'),
    ('道具右手持续持有', 'Persistent prop held in the right hand'),
    ('门半开连续性', 'Continuity of a half-open door'),
    ('连续近景', 'Consecutive close-ups'),
    ('Hidden LOCK → 正式近景', 'Hidden LOCK followed by a formal close-up'),
    ('无 LOCK 对照组', 'No-LOCK control against locked variants'),
]
CASE_PROTOCOLS = [
    {'participants': 2, 'minimum_formal_segments': 3, 'procedure': 'Keep both characters in fixed positions for three consecutive 5-second dialogue segments; alternate speaking close-ups.', 'inspect': ['identity across cuts', 'screen side', 'eyelines', 'tail-22 handoff']},
    {'participants': 2, 'minimum_dialogue_exchanges': 8, 'procedure': 'Perform eight complete question-response exchanges across consecutive segments, preserving each speaker and occurrence.', 'inspect': ['long-chain identity/position drift', 'dialogue occurrence', 'accumulating end-frame deformation']},
    {'participants': 3, 'procedure': 'Establish a fixed triangular group; C interrupts an A/B exchange while all listeners remain present.', 'inspect': ['speaker/listener assignment', 'off-screen positions', 'gaze targets']},
    {'participants': 4, 'procedure': 'Keep four characters around the living-room seating; alternate close-ups and one motivated group reaction.', 'inspect': ['sofa/door geometry', 'group left-right order', 'off-screen persistence']},
    {'participants': 5, 'procedure': 'Use five stable seating positions in a meeting-style conversation; cover all speakers without moving their physical positions.', 'inspect': ['identity separation', 'foreground/midground/background', 'axis']},
    {'participants': 3, 'procedure': 'Begin with two characters, show a third entering through the known entrance along a readable path, then re-anchor before the next formal segment.', 'inspect': ['entry direction', 'existing-character persistence', 'LOCK invalidation']},
    {'participants': 3, 'procedure': 'One character exits through the known exit; retain the remaining two and re-anchor the changed layout before the next formal segment.', 'inspect': ['exit path', 'no respawn', 'group reconstruction']},
    {'participants': 2, 'procedure': 'Show an explicit authorized crossing or position exchange with a readable path; record new positions and rebuild the subsequent anchor.', 'inspect': ['no unmotivated swap', 'correct final positions', 'camera-side consistency']},
    {'participants': 2, 'procedure': 'Place two speakers on documented sides of one doorway, preserve the door frame/opening axis and inside/outside scene authorities.', 'inspect': ['door geometry', 'inside/outside direction', 'eyelines']},
    {'participants': 4, 'procedure': 'Use fixed seating around a dining table with foreground and background speakers; cut only when dialogue or reaction requires it.', 'inspect': ['table scale/geometry', 'depth order', 'seating persistence']},
    {'participants': 2, 'minimum_formal_segments': 3, 'procedure': 'The same character holds the same prop in the right hand across three segments; include a readable medium shot and close-ups.', 'inspect': ['right-hand holder', 'prop appearance', 'no swap/spawn/disappearance']},
    {'participants': 2, 'minimum_formal_segments': 3, 'procedure': 'Maintain a known half-open door through three dialogue segments without a door-change event.', 'inspect': ['door openness', 'hinge direction', 'unchanged fixed geometry']},
    {'participants': 2, 'minimum_formal_segments': 3, 'procedure': 'Render consecutive alternating close-ups without visible establishing shots or character move events.', 'inspect': ['camera crop versus blocking', 'off-screen listeners', 'screen direction']},
    {'participants': 3, 'procedure': 'For B/C render an independent 0.8–1.5-second hidden group anchor, feed its tail 22 frames, then start the full 5-second formal segment directly in close-up. A omits the anchor as the control.', 'inspect': ['tail-frame transfer', 'full formal duration', 'no visible LOCK in final']},
    {'participants': 3, 'minimum_formal_segments': 3, 'procedure': 'Repeat the same three-segment dialogue plan with A explicitly omitting LOCK and B/C enabling LOCK. Preserve all other controls.', 'inspect': ['difference attributable to LOCK/prompt family', 'position and geometry drift', 'end-frame deformation']},
]
VARIANTS = {'A': {'prompt_family': '5.0', 'hidden_lock': False},
            'B': {'prompt_family': '5.0', 'hidden_lock': True},
            'C': {'prompt_family': '5.1', 'hidden_lock': True}}


def scenario_signature(project):
    """Hash frozen story and formal shots, independent of LOCK/prompt rendering."""
    project = Path(project)
    beats = load(project / '04_script.json')['beats']
    plans = load(project / '05_storyboard.json')['segments']
    fields = ['segment_id', 'scene_id', 'participants', 'shots', 'events', 'before_events']
    return digest({'beats': beats, 'segments': [{k: s[k] for k in fields if k in s} for s in plans]})


def new_manifest():
    cases = []
    for number, (cn, en) in enumerate(CASE_NAMES, 1):
        cases.append({'case_id': f'R{number:02}', 'name': {'cn': cn, 'en': en},
                      'protocol': copy.deepcopy(CASE_PROTOCOLS[number - 1]),
                      'scenario_review': 'NOT_RUN',
                      'status': 'NOT_RUN', 'metrics': {k: None for k in METRICS},
                      'variants': {key: {**spec, 'status': 'NOT_RUN', 'runs': [],
                                          'metrics': {k: None for k in METRICS}}
                                   for key, spec in VARIANTS.items()}})
    return {'schema_version': '5.1', 'status': 'NOT_RUN',
            'metric_definition': 'Observed error rates [0,1], lower is better; null means not evaluated.',
            'comparison_policy': 'Pair A/B/C by comparison_id; keep model, workflow, resolution, steps, seed, source, assets and durations constant. LOCK and prompt family are experimental variables.',
            'cases': cases}


def validate_manifest(manifest):
    errors = []
    if not isinstance(manifest, dict):
        return ['REGRESSION_MANIFEST_INVALID']
    cases = manifest.get('cases', [])
    if not isinstance(cases, list) or any(not isinstance(c, dict) for c in cases):
        return ['REGRESSION_CASES_INVALID']
    if [c.get('case_id') for c in cases] != [f'R{i:02}' for i in range(1, 16)]:
        errors.append('REGRESSION_CASE_SET_INVALID')
    any_run = False
    all_complete = True
    for case in cases:
        if not isinstance(case.get('variants'), dict) or set(case['variants']) != set(VARIANTS):
            errors.append('REGRESSION_VARIANTS_INVALID:' + str(case.get('case_id')))
            continue
        count = 0
        for name, variant in case['variants'].items():
            if not isinstance(variant, dict):
                errors.append('REGRESSION_VARIANT_INVALID:' + name)
                continue
            spec = VARIANTS[name]
            if any(variant.get(k) != v for k, v in spec.items()):
                errors.append('REGRESSION_VARIANT_CONTRACT_CHANGED:' + name)
            runs = variant.get('runs', [])
            metrics = variant.get('metrics', {})
            if not isinstance(runs, list) or any(not isinstance(r, dict) for r in runs):
                errors.append('REGRESSION_RUNS_INVALID')
                continue
            if not isinstance(metrics, dict):
                errors.append('REGRESSION_METRIC_SET_INVALID')
                continue
            if set(metrics) != set(METRICS):
                errors.append('REGRESSION_METRIC_SET_INVALID')
            if not runs:
                if variant.get('status') != 'NOT_RUN' or any(v is not None for v in metrics.values()):
                    errors.append('REGRESSION_UNRUN_RESULT_FABRICATED')
            else:
                any_run = True
                count += 1
                if variant.get('status') != 'RECORDED':
                    errors.append('REGRESSION_RECORDED_STATUS_INVALID')
                for run in runs:
                    try:
                        _validate_record(run)
                    except (GateError, TypeError, ValueError) as exc:
                        errors.append('REGRESSION_RUN_INVALID:' + str(exc))
                    if not run.get('evidence') or not run.get('output_sha256') or not run.get('video_probe'):
                        errors.append('REGRESSION_EVIDENCE_MISSING')
                    video_hash = run.get('output_sha256')
                    if not isinstance(video_hash, str) or len(video_hash) != 64 or any(c not in '0123456789abcdef' for c in video_hash):
                        errors.append('REGRESSION_OUTPUT_HASH_INVALID')
                    probe = run.get('video_probe')
                    if not isinstance(probe, dict) or not finite(probe.get('duration_s')) or probe.get('duration_s', 0) <= 0 or any(type(probe.get(k)) is not int or probe[k] <= 0 for k in ['width', 'height']):
                        errors.append('REGRESSION_VIDEO_PROBE_INVALID')
                    elif run.get('resolution') != [probe['width'], probe['height']]:
                        errors.append('REGRESSION_VIDEO_RESOLUTION_MISMATCH')
                    if run.get('variant') != name or run.get('case_id') != case.get('case_id'):
                        errors.append('REGRESSION_RUN_PLACEMENT_INVALID')
                if metrics != runs[-1].get('metrics'):
                    errors.append('REGRESSION_LATEST_METRICS_MISMATCH')
        expected = 'NOT_RUN' if count == 0 else 'COMPLETED' if count == 3 else 'PARTIAL'
        if case.get('status') != expected:
            errors.append('REGRESSION_CASE_STATUS_INVALID')
        all_complete &= count == 3
        # No meaningless average across different experimental variants.
        if not isinstance(case.get('metrics'), dict) or set(case['metrics']) != set(METRICS):
            errors.append('REGRESSION_CASE_METRIC_SET_INVALID')
        elif any(v is not None for v in case['metrics'].values()):
            errors.append('REGRESSION_CASE_METRICS_MUST_USE_VARIANTS')
    expected = 'COMPLETED' if all_complete and cases else 'PARTIAL' if any_run else 'NOT_RUN'
    if manifest.get('status') != expected:
        errors.append('REGRESSION_STATUS_INVALID')
    return errors


def _probe_video(path):
    executable = shutil.which('ffprobe')
    if not executable:
        raise GateError('REGRESSION_VIDEO_PROBE_UNAVAILABLE: install ffprobe to register real video evidence')
    result = subprocess.run([executable, '-v', 'error', '-show_streams', '-show_format',
                             '-of', 'json', str(path)], capture_output=True, text=True,
                            encoding='utf-8', timeout=60)
    if result.returncode:
        raise GateError('REGRESSION_OUTPUT_NOT_READABLE_VIDEO')
    try:
        value = json.loads(result.stdout)
        streams = [s for s in value['streams'] if s.get('codec_type') == 'video']
        stream = streams[0]
        duration = float(stream.get('duration', value.get('format', {}).get('duration', 0)))
        if stream.get('width', 0) <= 0 or stream.get('height', 0) <= 0 or duration <= 0:
            raise ValueError('Missing video dimensions or duration')
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise GateError('REGRESSION_OUTPUT_NOT_READABLE_VIDEO') from exc
    return {'width': stream['width'], 'height': stream['height'], 'duration_s': duration,
            'codec': stream.get('codec_name'), 'probe': 'ffprobe'}


def _validate_record(record):
    for key in ['case_id', 'variant', 'comparison_id', 'generation_id', 'take_id',
                'segment_id', 'metrics', 'evidence', *METADATA]:
        if key not in record:
            raise GateError('REGRESSION_RECORD_INCOMPLETE:' + key)
    if record['case_id'] not in [f'R{i:02}' for i in range(1, 16)] or record['variant'] not in VARIANTS:
        raise GateError('REGRESSION_CASE_OR_VARIANT_UNKNOWN')
    for key in ['comparison_id', 'generation_id', 'take_id', 'segment_id', 'model',
                'model_version', 'workflow', 'prompt_version', 'output_file']:
        if not isinstance(record[key], str) or not record[key].strip():
            raise GateError('REGRESSION_METADATA_INVALID:' + key)
    resolution = record['resolution']
    if not isinstance(resolution, list) or len(resolution) != 2 or any(type(x) is not int or x <= 0 for x in resolution):
        raise GateError('REGRESSION_RESOLUTION_INVALID')
    if type(record['steps']) is not int or record['steps'] <= 0 or type(record['seed']) is not int:
        raise GateError('REGRESSION_STEPS_OR_SEED_INVALID')
    if not finite(record['runtime_seconds']) or record['runtime_seconds'] <= 0:
        raise GateError('REGRESSION_RUNTIME_INVALID')
    spec = VARIANTS[record['variant']]
    if type(record['hidden_lock']) is not bool or record['hidden_lock'] != spec['hidden_lock']:
        raise GateError('REGRESSION_LOCK_VARIANT_MISMATCH')
    if record['prompt_version'].split(':')[0] != spec['prompt_family']:
        raise GateError('REGRESSION_PROMPT_VARIANT_MISMATCH')
    if not isinstance(record['reference_assets'], list) or not record['reference_assets']:
        raise GateError('REGRESSION_REFERENCE_ASSETS_MISSING')
    signature = record['scenario_signature']
    if not isinstance(signature, str) or len(signature) != 64 or any(c not in '0123456789abcdef' for c in signature):
        raise GateError('REGRESSION_SCENARIO_SIGNATURE_INVALID')
    if record['continuation'] is not None and not isinstance(record['continuation'], dict):
        raise GateError('REGRESSION_CONTINUATION_INVALID')
    if not isinstance(record['metrics'], dict) or set(record['metrics']) != set(METRICS) or any(not finite(v) or not 0 <= v <= 1 for v in record['metrics'].values()):
        raise GateError('REGRESSION_METRIC_VALUES_INVALID')
    evidence = record['evidence']
    if not isinstance(evidence, dict) or not evidence.get('reviewer') or not evidence.get('method'):
        raise GateError('REGRESSION_REVIEW_EVIDENCE_MISSING')
    if not isinstance(evidence.get('observations'), dict) or any(not evidence['observations'].get(k) for k in METRICS):
        raise GateError('REGRESSION_METRIC_EVIDENCE_MISSING')


def register_result(manifest_path, ledger_path, record):
    """Register reviewed video and link an existing real take; never generate a PASS label."""
    _validate_record(record)
    manifest = load(manifest_path)
    errors = validate_manifest(manifest)
    if errors:
        raise GateError('\n'.join(errors))
    ledger = load(ledger_path)
    matches = [t for t in ledger.get('takes', []) if
               (t.get('generation_id'), t.get('take_id'), t.get('segment_id')) ==
               (record['generation_id'], record['take_id'], record['segment_id'])]
    if len(matches) != 1 or matches[0].get('status') not in {'GENERATED', 'ACCEPTED', 'REJECTED'}:
        raise GateError('REGRESSION_LEDGER_TAKE_MISSING')
    take = matches[0]
    for key in METADATA:
        value = take.get(key, take.get('output') if key == 'output_file' else None)
        if value != record[key]:
            raise GateError('REGRESSION_LEDGER_METADATA_MISMATCH:' + key)
    output = Path(record['output_file'])
    if not output.is_absolute():
        output = Path(ledger_path).resolve().parent / output
    if not output.is_file() or output.stat().st_size == 0:
        raise GateError('REGRESSION_VIDEO_MISSING')
    probe = _probe_video(output)
    if record['resolution'] != [probe['width'], probe['height']]:
        raise GateError('REGRESSION_VIDEO_RESOLUTION_MISMATCH')
    case = next(c for c in manifest['cases'] if c['case_id'] == record['case_id'])
    variant = case['variants'][record['variant']]
    if any(r['comparison_id'] == record['comparison_id'] for r in variant['runs']):
        raise GateError('REGRESSION_COMPARISON_RUN_DUPLICATE')
    run = copy.deepcopy(record)
    run.update(recorded_at=datetime.now(timezone.utc).isoformat(),
               output_sha256=hashlib.sha256(output.read_bytes()).hexdigest(), video_probe=probe,
               ledger_file=str(Path(ledger_path).resolve()))
    variant['runs'].append(run)
    variant.update(status='RECORDED', metrics=copy.deepcopy(record['metrics']))
    case['status'] = 'COMPLETED' if all(v['runs'] for v in case['variants'].values()) else 'PARTIAL'
    manifest['status'] = 'COMPLETED' if all(c['status'] == 'COMPLETED' for c in manifest['cases']) else 'PARTIAL'
    take.setdefault('h3_regression', []).append({'case_id': record['case_id'], 'variant': record['variant'],
                                               'comparison_id': record['comparison_id'],
                                               'manifest': str(Path(manifest_path).resolve()),
                                               'output_sha256': run['output_sha256']})
    # Restore ledger if committing the registry fails; a rejected record mutates neither file.
    previous = Path(ledger_path).read_bytes()
    save(ledger_path, ledger)
    try:
        save(manifest_path, manifest)
    except Exception:
        Path(ledger_path).write_bytes(previous)
        raise
    return run


def compare_results(manifest):
    errors = validate_manifest(manifest)
    if errors:
        raise GateError('\n'.join(errors))
    comparisons = []
    controls = ['model', 'model_version', 'workflow', 'resolution', 'steps', 'seed', 'reference_assets', 'scenario_signature']
    for case in manifest['cases']:
        groups = {}
        for variant, spec in case['variants'].items():
            for run in spec['runs']:
                groups.setdefault(run['comparison_id'], {})[variant] = run
        for ident, runs in groups.items():
            missing = [v for v in VARIANTS if v not in runs]
            mismatches = []
            if not missing:
                for key in controls:
                    if any(runs[v][key] != runs['A'][key] for v in ['B', 'C']):
                        mismatches.append(key)
                if any(abs(runs[v]['video_probe']['duration_s'] - runs['A']['video_probe']['duration_s']) > 0.001 for v in ['B', 'C']):
                    mismatches.append('output_duration_s')
            comparable = not missing and not mismatches
            comparisons.append({'case_id': case['case_id'], 'comparison_id': ident,
                                'status': 'COMPARABLE' if comparable else 'INCOMPLETE' if missing else 'CONTROL_MISMATCH',
                                'missing_variants': missing, 'mismatched_controls': mismatches,
                                'metrics': {v: r['metrics'] for v, r in runs.items()},
                                'C_minus_B': {k: runs['C']['metrics'][k] - runs['B']['metrics'][k]
                                              for k in METRICS} if comparable else None,
                                'B_minus_A': {k: runs['B']['metrics'][k] - runs['A']['metrics'][k]
                                              for k in METRICS} if comparable else None})
    return {'status': 'NOT_RUN' if not comparisons else 'RECORDED', 'comparisons': comparisons,
            'note': 'No automatic claim of model quality or statistical significance. Negative deltas mean fewer observed errors.'}
