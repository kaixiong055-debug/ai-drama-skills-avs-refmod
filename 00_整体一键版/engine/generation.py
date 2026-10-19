import copy
from pathlib import Path
from .common import FILES, REJECT_REASONS, VERSION, GateError, digest, index, load, save
from .validator import validate_directory
from .runtime import render_runtime_document


def jobs(project, language='cn', model='H3'):
    project=Path(project)
    errors=validate_directory(project)
    if errors:raise GateError('\n'.join(errors))
    docs={n:load(project/n) for n in FILES}
    from .validator import parse_md
    blocks=parse_md(render_runtime_document(docs,language),language)
    from .regression import scenario_signature
    scenario=scenario_signature(project)
    units=docs['06_production.json']['units'];locks=docs['07_spatial_locks.json']['locks']
    ordered=[];before={l['before_segment_id']:l for l in locks}
    for unit in units:
        if unit['unit_id'] in before:ordered.append(before[unit['unit_id']])
        ordered.append(unit)
    return [{'generation_id':None,'segment_id':u['unit_id'],'shot_id':None,'shot_ids':u.get('shot_ids',[]),
             'take_id':'TAKE01','language':language,'prompt_version':VERSION+':'+digest(blocks[u['unit_id']]),'model':model,'mode':'REF2VA',
             'model_version':None,'workflow':None,'resolution':None,'steps':None,'seed':None,
             'hidden_lock':bool(u.get('spatial_anchor') or not u['include_in_final']),
             'continuation':u.get('continuation_source'),
             'reference_assets':[b['asset_id'] for b in docs['08_binding.json']['units'][u['unit_id']].values()],
             'runtime_seconds':None,'output_file':None,
             'scenario_signature':scenario,
             'picture_bindings':docs['08_binding.json']['units'][u['unit_id']],
             'spatial_anchor':u.get('spatial_anchor',u['unit_id']),
             'continuation_source':u.get('continuation_source'),'output':None,'status':'PENDING',
             'reject_reason':[],'include_in_final':u['include_in_final'],
             'requested_frames':142 if u['include_in_final'] else max(22,round(u['duration_s']*24)),
             'delivery_frames':120 if u['include_in_final'] else 0,
             'prompt':blocks[u['unit_id']]} for u in ordered]


def record_take(project, record):
    project=Path(project)
    errors=validate_directory(project)
    if errors:raise GateError('\n'.join(errors))
    required=['generation_id','segment_id','shot_id','take_id','prompt_version','model','mode',
              'picture_bindings','spatial_anchor','continuation_source','output','status','reject_reason']
    if any(k not in record for k in required):raise GateError('TAKE_RECORD_INCOMPLETE')
    from .schema import validate_schema
    schema_errors=validate_schema(record,'generation_take.schema.json')
    if schema_errors:raise GateError('\n'.join(schema_errors))
    if record['status'] not in ['GENERATED','ACCEPTED','REJECTED','FAILED']:raise GateError('TAKE_STATUS_INVALID')
    import re
    if not re.fullmatch(r'TAKE\d{2,}',record['take_id']):raise GateError('TAKE_ID_INVALID')
    if not record['generation_id']:raise GateError('GENERATION_ID_MISSING')
    if not isinstance(record['reject_reason'],list) or any(r not in REJECT_REASONS for r in record['reject_reason']):raise GateError('REJECT_REASON_INVALID')
    if record['status']=='REJECTED' and not record['reject_reason']:raise GateError('REJECT_REASON_MISSING')
    if record['status']=='ACCEPTED' and (record['reject_reason'] or not record.get('qc_evidence')):raise GateError('ACCEPTED_TAKE_REQUIRES_QC_EVIDENCE')
    language=record.get('language','cn')
    by_id=index(jobs(project,language,record['model']),'segment_id')
    expected=by_id.get(record['segment_id'])
    if expected is None:raise GateError('TAKE_UNIT_UNKNOWN')
    for k in ['prompt_version','mode','picture_bindings','spatial_anchor','continuation_source']:
        if record[k]!=expected[k]:raise GateError('TAKE_CANONICAL_CONTRACT_CHANGED:'+k)
    if record['shot_id'] is not None and record['shot_id'] not in expected['shot_ids']:raise GateError('TAKE_SHOT_UNKNOWN')
    if record['status'] in ['GENERATED','ACCEPTED'] and not Path(record['output']).is_file():raise GateError('TAKE_OUTPUT_MISSING')
    ledger=load(project/'generation_ledger.json')
    if any(t['generation_id']==record['generation_id'] or (t['segment_id'],t['take_id'])==(record['segment_id'],record['take_id']) for t in ledger['takes']):raise GateError('TAKE_ID_OR_GENERATION_ID_DUPLICATE')
    stored=copy.deepcopy(record)
    for key in ['model_version','workflow','resolution','steps','seed','runtime_seconds']:
        stored.setdefault(key,None)
    for key in ['hidden_lock','continuation','reference_assets','scenario_signature']:
        stored.setdefault(key,copy.deepcopy(expected[key]))
        if stored[key]!=expected[key]:raise GateError('TAKE_CANONICAL_CONTRACT_CHANGED:'+key)
    if stored.get('output_file') is not None and stored['output_file']!=stored['output']:
        raise GateError('TAKE_OUTPUT_FILE_ALIAS_MISMATCH')
    stored['output_file']=stored['output']
    ledger['takes'].append(stored);save(project/'generation_ledger.json',ledger)
    return ledger


def select_take(project, unit_id, take_id):
    project=Path(project);ledger=load(project/'generation_ledger.json')
    matches=[t for t in ledger['takes'] if t['segment_id']==unit_id and t['take_id']==take_id and t['status']=='ACCEPTED']
    if len(matches)!=1:raise GateError('SELECTED_TAKE_NOT_ACCEPTED')
    # Composite H3 SEG output only; an isolated shot is not a full 5-second segment.
    if matches[0]['shot_id'] is not None:raise GateError('ASSEMBLY_NEEDS_COMPLETE_SEGMENT_TAKE')
    ledger['selected_takes'][unit_id]=take_id;save(project/'generation_ledger.json',ledger)


def assembly(project):
    project=Path(project)
    errors=validate_directory(project)
    if errors:raise GateError('\n'.join(errors))
    ledger=load(project/'generation_ledger.json');manifest=load(project/'assembly_manifest.json')
    for row in manifest['segments']:
        sid=row['segment_id'];take_id=ledger['selected_takes'].get(sid)
        found=[t for t in ledger['takes'] if t['segment_id']==sid and t['take_id']==take_id and t['status']=='ACCEPTED']
        if len(found)!=1:raise GateError('ASSEMBLY_TAKE_NOT_READY:'+sid)
        t=found[0]
        if not Path(t['output']).is_file():raise GateError('ASSEMBLY_OUTPUT_MISSING:'+sid)
        frames=t.get('output_frames');guide=t.get('overlap_frames')
        if frames not in [120,142] or guide!=(22 if frames==142 else 0):raise GateError('ASSEMBLY_FRAME_WINDOW_UNVERIFIED:'+sid)
        row.update(selected_take=take_id,output=t['output'],trim_guide_frames=guide,delivery_frames=120)
    manifest['status']='READY_TO_ASSEMBLE';save(project/'assembly_manifest.json',manifest)
    return manifest
