#!/usr/bin/env python3
import argparse
import json
from pathlib import Path
import sys
from engine.common import GateError, load, save
from engine.pipeline import export_project
from engine.delivery import export_user_project, export_delivery, resolve_project, internal_project


def main(argv=None):
    p=argparse.ArgumentParser(description='AI漫剧 V5.1 双语 H3 一键生产包')
    sub=p.add_subparsers(dest='command',required=True)
    exp=sub.add_parser('export');exp.add_argument('--input',required=True);exp.add_argument('--asset-root',required=True);exp.add_argument('--output',required=True)
    src=sub.add_parser('source');src.add_argument('--source',required=True);src.add_argument('--asset-root',required=True);src.add_argument('--catalog');src.add_argument('--config');src.add_argument('--output',required=True)
    handoff=sub.add_parser('delivery');handoff.add_argument('--project',required=True);handoff.add_argument('--output',required=True);handoff.add_argument('--draft',action='store_true')
    val=sub.add_parser('validate');val.add_argument('--project',required=True);val.add_argument('--asset-root')
    test=sub.add_parser('selftest');test.add_argument('--report')
    sample=sub.add_parser('example');sample.add_argument('--output',required=True);sample.add_argument('--people',type=int,default=2,choices=range(1,6))
    job=sub.add_parser('jobs');job.add_argument('--project',required=True);job.add_argument('--language',choices=['cn','en'],default='cn');job.add_argument('--output',required=True)
    take=sub.add_parser('record-take');take.add_argument('--project',required=True);take.add_argument('--record',required=True)
    select=sub.add_parser('select-take');select.add_argument('--project',required=True);select.add_argument('--unit',required=True);select.add_argument('--take',required=True)
    asm=sub.add_parser('assembly');asm.add_argument('--project',required=True)
    repair=sub.add_parser('repair-spatial');repair.add_argument('--project',required=True);repair.add_argument('--reject',required=True);repair.add_argument('--output',required=True)
    a=p.parse_args(argv)
    try:
        if a.command=='export':out=export_user_project(load(a.input),a.asset_root,a.output);print('READY: '+str(out))
        elif a.command=='source':
            from engine.provider import read_source,plan_source
            catalog=load(a.catalog) if a.catalog else None
            if isinstance(catalog,dict):catalog=catalog.get('assets',catalog)
            request=plan_source(read_source(a.source),a.asset_root,catalog,load(a.config) if a.config else None)
            out=export_user_project(request,a.asset_root,a.output)
            # Provenance is not an additional authoritative state file.
            save(resolve_project(out)/'source_request.provenance.json',request);print('READY: '+str(out))
        elif a.command=='delivery':
            out=export_delivery(resolve_project(a.project),a.output,allow_draft=a.draft)
            print('USER DELIVERY: '+str(out))
        elif a.command=='validate':
            from engine.validator import validate_directory
            errors=validate_directory(resolve_project(a.project),a.asset_root);print(json.dumps({'status':'FAIL' if errors else 'PASS','errors':errors},ensure_ascii=False,indent=2));return int(bool(errors))
        elif a.command=='selftest':
            import unittest
            suite=unittest.defaultTestLoader.discover(str(Path(__file__).parent/'tests'))
            result=unittest.TextTestRunner(verbosity=2).run(suite)
            report={'status':'PASS' if result.wasSuccessful() else 'FAIL','tests':result.testsRun,
                    'failures':[{'test':str(t),'trace':e} for t,e in result.failures+result.errors]}
            if a.report:save(a.report,report)
            return int(not result.wasSuccessful())
        elif a.command=='example':
            from examples.fixtures import fixture,materialize
            r=fixture(a.people);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
            assets=materialize(r,out/'input');export_project(r,assets,out/'production');print('READY: '+str(out/'production'))
        elif a.command=='jobs':
            from engine.generation import jobs
            save(a.output,{'jobs':jobs(resolve_project(a.project),a.language)});print('Jobs exported; no video task submitted.')
        elif a.command=='record-take':
            from engine.generation import record_take
            record_take(resolve_project(a.project),load(a.record));print('Take recorded.')
        elif a.command=='select-take':
            from engine.generation import select_take
            select_take(resolve_project(a.project),a.unit,a.take);print('Accepted take selected.')
        elif a.command=='assembly':
            from engine.generation import assembly
            print(json.dumps(assembly(resolve_project(a.project)),ensure_ascii=False,indent=2))
        elif a.command=='repair-spatial':
            from engine.qc import repair_spatial
            internal=repair_spatial(resolve_project(a.project),load(a.reject),internal_project(a.output))
            print('READY: '+str(export_delivery(internal,a.output)))
        return 0
    except (GateError,OSError,ValueError,KeyError,TypeError) as exc:
        print('FAIL: '+str(exc),file=sys.stderr);return 1


if __name__=='__main__':raise SystemExit(main())
