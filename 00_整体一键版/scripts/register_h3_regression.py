"""Prepare, validate, register and compare real H3 regression evidence."""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import GateError, load, save
from engine.regression import new_manifest, register_result, compare_results, validate_manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init')
    init.add_argument('--output', required=True)
    validate = commands.add_parser('validate')
    validate.add_argument('--manifest', required=True)
    register = commands.add_parser('register')
    register.add_argument('--manifest', required=True)
    register.add_argument('--ledger', required=True)
    register.add_argument('--record', required=True)
    compare = commands.add_parser('compare')
    compare.add_argument('--manifest', required=True)
    compare.add_argument('--output')
    args = parser.parse_args()
    try:
        if args.command == 'init':
            if Path(args.output).exists():
                raise GateError('REGRESSION_MANIFEST_ALREADY_EXISTS')
            save(args.output, new_manifest())
            result = {'status': 'NOT_RUN', 'manifest': args.output}
        elif args.command == 'validate':
            errors = validate_manifest(load(args.manifest))
            if errors:
                raise GateError('\n'.join(errors))
            result = {'validation': 'PASS', 'real_h3_status': load(args.manifest)['status']}
        elif args.command == 'register':
            result = register_result(args.manifest, args.ledger, load(args.record))
        else:
            result = compare_results(load(args.manifest))
            if args.output:
                save(args.output, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (GateError, OSError, ValueError) as exc:
        print(json.dumps({'status': 'FAIL', 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
