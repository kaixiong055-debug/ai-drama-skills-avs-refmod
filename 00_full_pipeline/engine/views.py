"""Read-only director views. No additional editable production authority."""
from .common import digest,index,text
from .render import term

COLUMNS=['Shot ID & Duration','Continuity Handoff','Reference Anchors (Spatial + Identity)',
         'Hook Type','Shot Description (Per-Second Directives)','Audio & Dialogue Track']


def director_views(docs,lang='cn'):
    units=index(docs['06_production.json']['units'],'unit_id')
    beats=index(docs['04_script.json']['beats'],'beat_id')
    rows=[];sections=[];json_rows=[]
    def cell(v):return str(v).replace('|',' / ').replace('\n','<br>')
    for p in docs['05_storyboard.json']['segments']:
        u=units[p['segment_id']];sid=u['unit_id']
        for sh in p['shots']:
            duration=sh['end_s']-sh['start_s'];local=0.;directives=[]
            while local<duration-1e-7:
                end=min(local+1.,duration)
                events=[e for e in p.get('events',[]) if sh['start_s']+local<e['at_s']<=sh['start_s']+end]
                audio=[b for b in sh['beat_ids'] if beats[b].get('dialogue') and
                       beats[b]['start_s']<sh['start_s']+end and beats[b]['end_s']>sh['start_s']+local]
                directives.append({'local_start_s':local,'local_end_s':end,
                                   'segment_start_s':sh['start_s']+local,'segment_end_s':sh['start_s']+end,
                                   'action':text(sh['action'],lang),'camera':text(sh['composition'],lang),
                                   'spatial_anchor':u['spatial_anchor'],'state_ids':u['state_ids'],
                                   'audio_beat_ids':audio,'state_events':events})
                local=end
            handoff=f'{sid} / {sh["start_s"]:.3f}–{sh["end_s"]:.3f}s; '+str(u['state_ids'])
            anchors='; '.join(k+'='+b['file'] for k,b in docs['08_binding.json']['units'][sid].items())+'; '+u['spatial_anchor']
            descriptions='; '.join(f'{d["local_start_s"]:.3f}–{d["local_end_s"]:.3f}s: {d["action"]}; {d["camera"]}; '+
                                  ','.join(e.get('event_id',e['op']) for e in d['state_events']) for d in directives)
            audio='; '.join(bid+f': {beats[bid].get("start_s",0):.3f}–{beats[bid].get("end_s",5):.3f}s' for bid in sh['beat_ids']) or ('仅环境声' if lang=='cn' else 'Ambient sound only')
            row=[sh['shot_id']+f' / {duration:g}s',handoff,anchors,p.get('shot_function','DRAMA'),descriptions,audio]
            rows.append('| '+' | '.join(cell(c) for c in row)+' |')
            sections.append('## '+sh['shot_id']+'\n\n'+handoff+'\n\nPose + Expression:\n'+text(sh['action'],lang)+
                            '\n\nCamera:\n'+term(sh['shot_scale'],lang)+f'; {sh["lens_mm"]}mm; '+text(sh['camera_angle'],lang)+'; '+text(sh['lighting'],lang)+
                            '\n\nAudio + Anchor:\n'+audio+'\n'+anchors+'\n\nContinuity:\n'+str(u['state_ids'])+'\n\n'+
                            '\n'.join(f'{d["local_start_s"]:.3f}–{d["local_end_s"]:.3f}s: '+d['action']+'; '+d['camera'] for d in directives))
            json_rows.append({'shot_id':sh['shot_id'],'segment_id':sid,'duration_s':duration,'segment_start_s':sh['start_s'],
                              'segment_end_s':sh['end_s'],'local_timeline':directives,'camera_contract':sh})
    table='| '+' | '.join(COLUMNS)+' |\n| '+' | '.join('---' for _ in COLUMNS)+' |\n'+'\n'.join(rows)+'\n'
    plan={'schema_version':docs['01_story.json']['schema_version'],'read_only':True,'view_of':'05_storyboard.json + 06_production.json + 07_spatial_locks.json + 08_binding.json',
          'canonical_hash':digest(docs),'columns':COLUMNS,'shots':json_rows}
    return table,'\n\n'.join(sections)+'\n',plan
