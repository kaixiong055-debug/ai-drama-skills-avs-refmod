"""Read the single published dependency graph; directory numbers are not a schedule."""
from pathlib import Path
from .common import GateError, load

GRAPH_PATH = Path(__file__).resolve().parent.parent / 'pipeline_graph.json'
REQUIRED_STAGES = {'story_adapter', 'character_bible', 'asset_bible', 'script',
                   'storyboard', 'production_state', 'spatial_lock', 'binding',
                   'h3_export', 'generation', 'qc', 'assembly'}


def load_graph():
    return load(GRAPH_PATH)


def validate_pipeline_graph(graph=None):
    graph = load_graph() if graph is None else graph
    errors = []
    if not isinstance(graph, dict):
        return ['PIPELINE_GRAPH_INVALID']
    if not isinstance(graph.get('external_inputs'), list) or any(not isinstance(x, str) for x in graph['external_inputs']):
        return ['PIPELINE_GRAPH_EXTERNAL_INPUTS_INVALID']
    stages = graph.get('stages', [])
    if not isinstance(stages, list) or not all(isinstance(s, dict) for s in stages):
        return ['PIPELINE_GRAPH_STAGES_INVALID']
    ids = [s.get('id') for s in stages]
    if any(not isinstance(i, str) or not i for i in ids) or len(ids) != len(set(ids)):
        return ['PIPELINE_GRAPH_STAGE_ID_INVALID']
    if set(ids) != REQUIRED_STAGES:
        errors.append('PIPELINE_GRAPH_STAGE_SET_INVALID')
    by_id = {s['id']: s for s in stages}
    producers = {}
    for s in stages:
        sid = s['id']
        for key in ('requires', 'produces', 'depends_on', 'blocking_failures'):
            values = s.get(key)
            if not isinstance(values, list) or any(not isinstance(v, str) or not v for v in values):
                errors.append('PIPELINE_GRAPH_CONTRACT_INVALID:' + sid + ':' + key)
        if not s.get('validator') or not isinstance(s.get('validator'), str):
            errors.append('PIPELINE_GRAPH_VALIDATOR_MISSING:' + sid)
        if not s.get('produces') or not s.get('blocking_failures'):
            errors.append('PIPELINE_GRAPH_CONTRACT_EMPTY:' + sid)
        for artifact in s.get('produces', []) if isinstance(s.get('produces'), list) else []:
            if not isinstance(artifact, str):
                continue
            if artifact in producers:
                errors.append('PIPELINE_GRAPH_MULTIPLE_PRODUCERS:' + artifact)
            producers[artifact] = sid
        for parent in s.get('depends_on', []) if isinstance(s.get('depends_on'), list) else []:
            if not isinstance(parent, str):
                continue
            if parent not in by_id:
                errors.append('PIPELINE_GRAPH_DEPENDENCY_UNKNOWN:' + sid + ':' + parent)
    if errors:
        return errors
    visiting, done, ancestors = set(), set(), {}

    def visit(sid):
        if sid in visiting:
            raise GateError('PIPELINE_GRAPH_CYCLE:' + sid)
        if sid in done:
            return ancestors[sid]
        visiting.add(sid)
        inherited = set()
        for dep in by_id[sid]['depends_on']:
            inherited.add(dep)
            inherited.update(visit(dep))
        visiting.remove(sid)
        done.add(sid)
        ancestors[sid] = inherited
        return inherited

    try:
        for sid in ids:
            visit(sid)
    except GateError as exc:
        return [str(exc)]
    external = set(graph.get('external_inputs', []))
    for s in stages:
        for artifact in s['requires']:
            owner = producers.get(artifact)
            if owner is None and artifact not in external:
                errors.append('PIPELINE_GRAPH_INPUT_UNKNOWN:' + s['id'] + ':' + artifact)
            elif owner is not None and owner not in ancestors[s['id']]:
                errors.append('PIPELINE_GRAPH_INPUT_NOT_DEPENDENCY:' + s['id'] + ':' + artifact)
    # These are safety invariants, not a second execution schedule.
    for stage, required in {'h3_export': {'binding', 'spatial_lock'},
                            'assembly': {'qc', 'generation'}}.items():
        if stage in ancestors and not required.issubset(ancestors[stage]):
            errors.append('PIPELINE_GRAPH_REQUIRED_GATE_MISSING:' + stage)
    return errors


def execution_order(graph=None):
    graph = load_graph() if graph is None else graph
    errors = validate_pipeline_graph(graph)
    if errors:
        raise GateError('\n'.join(errors))
    pending = list(graph['stages'])
    ordered = []
    while pending:
        ready = [s for s in pending if set(s['depends_on']).issubset(ordered)]
        for s in ready:
            ordered.append(s['id'])
            pending.remove(s)
    return ordered
