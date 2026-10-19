import json
import tempfile
import unittest
from pathlib import Path
from engine.provider import plan_source
from examples.fixtures import fixture,materialize


class PlannerAuthorityTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_model_cannot_authorize_stale_assets(self):
        r=fixture();r['project']['allow_stale_asset']=True
        a=materialize(r,self.root)
        result=plan_source('A short scene.',a,transport=lambda payload:{'choices':[{'message':{'content':json.dumps(r)}}]})
        self.assertFalse(result['project']['allow_stale_asset'])
    def test_model_cannot_fabricate_asset_versions(self):
        r=fixture();a=materialize(r,self.root)
        for asset in r['assets']:asset.update(version=77,status='VALID')
        result=plan_source('A short scene.',a,transport=lambda payload:{'choices':[{'message':{'content':json.dumps(r)}}]})
        self.assertTrue(all('version' not in asset and asset['status']=='UNVERIFIED' for asset in result['assets']))
    def test_explicit_operator_config_preserved(self):
        r=fixture();a=materialize(r,self.root)
        result=plan_source('A short scene.',a,config={'allow_stale_asset':True},transport=lambda payload:{'choices':[{'message':{'content':json.dumps(r)}}]})
        self.assertTrue(result['project']['allow_stale_asset'])

if __name__=='__main__':unittest.main()
