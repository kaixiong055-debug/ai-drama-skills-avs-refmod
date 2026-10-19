"""Validate declared scale in a frozen input or a production pack."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine.common import load
from engine.measurement import validate_spatial_measurements

def main():
    p=argparse.ArgumentParser();p.add_argument('--input');p.add_argument('--project');a=p.parse_args()
    if bool(a.input)==bool(a.project):p.error('specify exactly one of --input / --project')
    try:
        r=load(a.input) if a.input else load(Path(a.project)/'01_story.json')
        errors=validate_spatial_measurements(r)
    except (ValueError,OSError,TypeError) as exc:errors=[str(exc)]
    print(json.dumps({'status':'FAIL' if errors else 'PASS','errors':errors},ensure_ascii=False,indent=2))
    return int(bool(errors))

if __name__=='__main__':raise SystemExit(main())
