import copy,json,unittest
from pathlib import Path
from compare_replay import compare
class ReplayTests(unittest.TestCase):
 def setUp(self):
  root=Path(__file__).resolve().parent.parent/'examples'
  self.c=json.loads((root/'contract.json').read_text());self.e=json.loads((root/'expected.json').read_text());self.a=copy.deepcopy(self.e)
 def test_pass(self):self.assertEqual(compare(self.c,self.e,self.a)['status'],'PASS')
 def test_wrong_class(self):
  self.a['rows'][0]['label']='CLASS_B';self.assertEqual(compare(self.c,self.e,self.a)['status'],'FAIL')
 def test_missing_and_duplicate(self):
  self.a['rows'].pop();self.a['rows'].append(copy.deepcopy(self.a['rows'][0]));self.assertEqual(compare(self.c,self.e,self.a)['status'],'FAIL')
 def test_hash_and_order(self):
  self.a['model_sha256']='b'*64;self.a['feature_order'].reverse();self.assertEqual(compare(self.c,self.e,self.a)['status'],'FAIL')
 def test_nonfinite(self):
  self.a['rows'][0]['probabilities'][0]=float('nan');self.assertEqual(compare(self.c,self.e,self.a)['status'],'FAIL')
 def test_rejected_prediction(self):
  self.a['rows'][1]['label']='CLASS_A';self.assertEqual(compare(self.c,self.e,self.a)['status'],'FAIL')
 def test_changed_input(self):
  self.a['rows'][0]['input'][0]=0.3;self.assertEqual(compare(self.c,self.e,self.a)['status'],'FAIL')
 def test_tolerance(self):
  self.a['rows'][0]['probabilities']=[0.74,0.26];self.assertEqual(compare(self.c,self.e,self.a)['status'],'FAIL')
if __name__=='__main__':unittest.main()
