from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from tests.test_pipeline import ProductionTests
from tests.test_operations import OperationsTests
suite=unittest.TestSuite()
prefixes=['test_missing', 'test_ambiguous']
for cls in [ProductionTests,OperationsTests]:
    for name in unittest.defaultTestLoader.getTestCaseNames(cls):
        if any(name.startswith(p) for p in prefixes):suite.addTest(cls(name))
for pattern in ['test_assets_v51.py']:
    suite.addTests(unittest.defaultTestLoader.discover(str(Path(__file__).resolve().parents[2]/'tests'),pattern=pattern))
if __name__=='__main__':
    if not suite.countTestCases():raise SystemExit('No matching layer tests')
    raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
