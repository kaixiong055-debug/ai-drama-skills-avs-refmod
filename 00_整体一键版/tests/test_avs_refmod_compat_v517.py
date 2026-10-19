import tempfile
import unittest
from pathlib import Path
from examples.fixtures import fixture, materialize
from engine.pipeline import compile_project

class AVSRefModCompatTests(unittest.TestCase):
    def test_characters_do_not_occupy_picture_slots(self):
        r=fixture(2,1)
        r['project']['character_binding_mode']='AVS_REFMOD'
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); assets=materialize(r,root)
            docs,md=compile_project(r,assets)
            binding=docs['08_binding.json']['units']['SEG001']
            self.assertTrue(binding)
            self.assertTrue(all('CHAR_' not in row['asset_id'] for row in binding.values()))
            prompt=md['H3_PROMPTS_EN.md']
            self.assertIn('Identity RefMod',prompt)
            self.assertIn('Clothing RefMod',prompt)
            self.assertIn('character_picture=NONE',prompt)
            self.assertNotIn('current wardrobe from <Picture',prompt)
            self.assertNotIn('current character runtime appearance',prompt)

    def test_legacy_picture_mode_remains_compatible(self):
        r=fixture(2,1)
        r['project']['character_binding_mode']='PICTURE'
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); assets=materialize(r,root)
            docs,md=compile_project(r,assets)
            self.assertTrue(any('CHAR_' in row['asset_id'] for row in docs['08_binding.json']['units']['SEG001'].values()))
            self.assertIn('current wardrobe from <Picture',md['H3_PROMPTS_EN.md'])

if __name__=='__main__':unittest.main()
