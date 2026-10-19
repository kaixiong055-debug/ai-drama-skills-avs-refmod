from pathlib import Path
from .common import FILES, GateError, load, save
from .pipeline import export_project
from .validator import validate_directory

SPATIAL_REJECTS={'POSITION_DRIFT','LEFT_RIGHT_SWAP','AXIS_FLIP','EYELINE_ERROR','SCENE_GEOMETRY_DRIFT'}


def repair_spatial(project, rejection, output):
    """Freeze original beats/cameras, rebuild invalid spatial anchors in a new pack."""
    project=Path(project)
    errors=validate_directory(project)
    if errors:raise GateError('\n'.join(errors))
    if rejection.get('status')!='REJECTED' or not SPATIAL_REJECTS.intersection(rejection.get('reject_reason',[])):
        raise GateError('SPATIAL_REPAIR_REQUIRES_STRUCTURED_REJECTION')
    if not rejection.get('qc_evidence'):raise GateError('QC_REPAIR_EVIDENCE_MISSING')
    docs={n:load(project/n) for n in FILES}
    r={'schema_version':'5.0','project':docs['01_story.json']['project'],'scenes':docs['01_story.json']['scenes'],
       'source':docs['01_story.json'].get('source',{}),'source_beats':docs['01_story.json'].get('source_beats',[]),
       'cast':docs['02_cast.json']['characters'],'assets':docs['03_assets.json']['assets'],
       'beats':docs['04_script.json']['beats'],'segments':docs['05_storyboard.json']['segments']}
    target=next((s for s in r['segments'] if s['segment_id']==rejection['segment_id']),None)
    if target is None:raise GateError('QC_REPAIR_SEGMENT_UNKNOWN')
    target['review_drift']=True
    target['review_evidence']=rejection['qc_evidence']
    out=export_project(r,project/'assets',output)
    save(out/'qc_repair_provenance.json',{'previous_pack':str(project.resolve()),'rejection':rejection,
                                         'old_generation_ledger':load(project/'generation_ledger.json'),
                                         'note':'Original takes preserved as provenance. New prompt versions need generation and QC.'})
    return out
