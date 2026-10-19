"""Validate the package's JSON Schemas using jsonschema; fail closed if unavailable."""
from pathlib import Path
from .common import load


def validate_schema(value, filename):
    try:
        from jsonschema import Draft202012Validator
    except ImportError:
        return ['DEPENDENCY_MISSING: run python -m pip install -r requirements.txt']
    schema=load(Path(__file__).resolve().parent.parent/'schemas'/filename)
    return ['SCHEMA:'+('/'.join(map(str,e.path)) or '/')+':'+e.message
            for e in Draft202012Validator(schema).iter_errors(value)]
