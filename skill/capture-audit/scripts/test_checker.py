import hashlib,json,tempfile,unittest
from pathlib import Path
from check_capture import check
from register import register

class Checks(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  manifest=self.root/'manifest.json'
  manifest.write_text(json.dumps([dict(waveform_id='W',parameter_set_id='W',lineage_group_id='G',source_type='parametric_synthetic',source_sha256='a'*64,split_role='calibration_dev')]))
  self.run=register(manifest,'W',self.root/'runs','RUN','SESSION','DEVICE',write_markdown=False)
  self.m=json.loads((self.run/'metadata.json').read_text())
  self.m.update(firmware_bit_sha256='a'*64,firmware_hwh_sha256='b'*64,capture_status='CAPTURED',abi_version='2.1',adapter_version='fixture',association='offline_verified_same_frame')
  for k in ('awg_actual_settings','independent_output_verification','adc_actual_configuration','frame_association_evidence'):self.m[k]={'basis':'SOFTWARE_FIXTURE'}
  for role,field in [('raw','raw_files'),('feature','feature_files'),('reference','reference_files')]:
   f=self.run/role/'fixture';f.write_text(role)
   self.m[field]=[dict(path=role+'/fixture',sha256=hashlib.sha256(f.read_bytes()).hexdigest())]
 def tearDown(self):self.tmp.cleanup()
 def run_check(self):
  (self.run/'metadata.json').write_text(json.dumps(self.m));return check(self.run)
 def test_structure_not_approval(self):
  r=self.run_check();self.assertEqual(r['structural_status'],'STRUCTURALLY_COMPLETE');self.assertFalse(r['formal_training_eligible'])
 def test_tamper_preserves_original(self):
  q=self.run/'raw/fixture';q.write_text('changed');r=self.run_check();self.assertIn('HASH_MISMATCH',[i['code'] for i in r['issues']]);self.assertEqual(q.read_text(),'changed')
 def test_missing(self):
  (self.run/'feature/fixture').unlink();self.assertIn('FILE_READ',[i['code'] for i in self.run_check()['issues']])
 def test_path_escape(self):
  self.m['raw_files'][0]['path']='../outside';self.assertIn('UNSAFE_PATH',[i['code'] for i in self.run_check()['issues']])
 def test_unmatched(self):
  self.m['association']='unmatched';self.assertIn('ASSOCIATION',[i['code'] for i in self.run_check()['issues']])
 def test_malformed(self):
  (self.run/'metadata.json').write_text('[]');self.assertEqual(check(self.run)['structural_status'],'INCOMPLETE')

if __name__=='__main__':unittest.main()
