import copy,unittest
from score_paired import paired

class PairedTests(unittest.TestCase):
    def setUp(self):
        self.c={'labels':['A','B'],'feature_order':['x'],'rows':[{'id':str(i),'run_id':'R'+str(i//2),'input':[i],'eligible':True,'source_label':'A' if i<2 else 'B'} for i in range(4)]}
        self.p={'labels':['A','B'],'feature_order':['x'],'model_sha256':'a'*64,'rows':[{'id':r['id'],'input':r['input'],'status':'ACCEPTED','label':r['source_label'],'probabilities':[1,0] if r['source_label']=='A' else [0,1]} for r in self.c['rows']]}
    def test_identical(self):
        r=paired(self.c,self.p,self.p);self.assertEqual(r['left']['service_accuracy'],1);self.assertEqual(r['disagreements'],[])
    def test_missing_and_rejected_stay_in_denominator(self):
        q=copy.deepcopy(self.p);q['rows'].pop();q['rows'][0].update(status='REJECTED',label=None,probabilities=None)
        r=paired(self.c,self.p,q)['right'];self.assertEqual((r['total'],r['correct'],r['failed_outputs']),(4,2,2));self.assertEqual(r['service_accuracy'],.5);self.assertEqual(r['conditional_accuracy'],1)
    def test_input_mismatch(self):
        q=copy.deepcopy(self.p);q['rows'][0]['input']=[99]
        with self.assertRaises(ValueError):paired(self.c,self.p,q)
    def test_duplicate(self):
        q=copy.deepcopy(self.p);q['rows'].append(q['rows'][0])
        with self.assertRaises(ValueError):paired(self.c,self.p,q)
    def test_unapproved_labels(self):
        self.c['rows'][0]['eligible']=False
        with self.assertRaises(ValueError):paired(self.c,self.p,self.p)
    def test_failed_old_prediction(self):
        q=copy.deepcopy(self.p);q['rows'][0]['status']='ERROR'
        with self.assertRaises(ValueError):paired(self.c,self.p,q)

if __name__=='__main__':unittest.main()
