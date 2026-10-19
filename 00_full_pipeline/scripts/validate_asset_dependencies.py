"""Validate a canonical request or an exported Production Pack dependency graph."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import load, save
from engine.asset_dependencies import validate_asset_dependencies


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path, help='project_input.json or production pack directory')
    parser.add_argument('--output', type=Path, help='save the complete JSON report')
    args = parser.parse_args()
    try:
        if args.input.is_dir():
            story = load(args.input / '01_story.json')
            assets = load(args.input / '03_assets.json')['assets']
            cast = load(args.input / '02_cast.json')['characters']
            bindings = load(args.input / '08_binding.json')['units']
            scenes, project = story['scenes'], story['project']
        else:
            r = load(args.input)
            assets, cast, scenes, project = r['assets'], r['cast'], r['scenes'], r['project']
            bindings = r.get('bindings')
        report = validate_asset_dependencies(assets, cast, scenes, bindings,
                                              allow_stale_asset=project.get('allow_stale_asset', False))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report = {'status': 'FAIL', 'errors': ['ASSET_DEPENDENCY_INPUT_INVALID:' + str(exc)], 'warnings': []}
    if args.output: save(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report['errors'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
