import copy
import tempfile
import unittest
from pathlib import Path
from engine.common import bi
from engine.pipeline import compile_project
from engine.render import render_pack
from engine.validator import validate_pack
from examples.fixtures import fixture,materialize


class BindingReplayTests(unittest.TestCase):
    def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
    def tearDown(self):self.temp.cleanup()
    def test_valid_file_of_wrong_character_not_accepted(self):
        r=fixture();a=materialize(r,self.root);docs,md=compile_project(r,a)
        rows=docs['08_binding.json']['units']['SEG001']
        rows['P1']=copy.deepcopy(rows['P2'])
        errors=validate_pack(docs,render_pack(docs),a)
        self.assertTrue(any('BINDING_STATE_REPLAY_MISMATCH' in e for e in errors))
    def test_unbound_wardrobe_cannot_replace_current_wardrobe(self):
        r=fixture();r['cast'][0]['wardrobes']['HOME']={'description':bi('居家白衬衫','a white home shirt'),'runtime_asset_id':'CHAR_A_HOME'}
        r['assets'].append({'asset_id':'CHAR_A_HOME','file':'CHAR_A_HOME.png','role':'H3_RUNTIME','character_id':'CHAR_A',
                            'wardrobe':'HOME','direct_bindable':True,'description':bi('居家白衬衫造型','the home-shirt appearance')})
        a=materialize(r,self.root);docs,md=compile_project(r,a)
        replacement=copy.deepcopy(docs['08_binding.json']['asset_files']['CHAR_A_HOME'])
        replacement['asset_id']='CHAR_A_HOME';docs['08_binding.json']['units']['SEG001']['P1']=replacement
        errors=validate_pack(docs,render_pack(docs),a)
        self.assertTrue(any('BINDING_STATE_REPLAY_MISMATCH' in e for e in errors))

if __name__=='__main__':unittest.main()
