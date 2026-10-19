import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine.common import load
from engine.pipeline_graph import load_graph, execution_order, validate_pipeline_graph

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('graph', nargs='?')
    a = p.parse_args()
    graph = load(a.graph) if a.graph else load_graph()
    errors = validate_pipeline_graph(graph)
    print(json.dumps({'status': 'FAIL' if errors else 'PASS', 'errors': errors,
                      'execution_order': [] if errors else execution_order(graph)}, ensure_ascii=False, indent=2))
    raise SystemExit(bool(errors))
