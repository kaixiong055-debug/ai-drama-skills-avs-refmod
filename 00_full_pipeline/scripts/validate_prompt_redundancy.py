"""Check one runtime MD or both runtime files in a production directory."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from engine.redundancy import budget_warnings,validate_prompt_redundancy


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path',type=Path)
    parser.add_argument('--language',choices=['cn','en'])
    args=parser.parse_args();errors=[];warnings=[]
    paths=[args.path/f'H3_RUNTIME_{lang}.md' for lang in ['CN','EN']] if args.path.is_dir() else [args.path]
    for path in paths:
        lang=args.language or ('cn' if path.stem.endswith('_CN') else 'en')
        try:data=path.read_text(encoding='utf-8-sig')
        except OSError as exc:errors.append(str(exc));continue
        errors.extend(validate_prompt_redundancy(data,lang));warnings.extend(budget_warnings(data,lang))
    print(json.dumps({'status':'FAIL' if errors else 'PASS','errors':errors,'warnings':warnings},ensure_ascii=False,indent=2))
    return bool(errors)


if __name__=='__main__':raise SystemExit(main())
