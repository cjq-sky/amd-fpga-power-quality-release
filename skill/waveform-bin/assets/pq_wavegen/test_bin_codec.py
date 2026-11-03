import unittest,tempfile,json,struct,subprocess,sys
from pathlib import Path
from bin_codec import encode,inspect,export_existing
from wavegen import generate

class BinTests(unittest.TestCase):
 def profile(self):return dict(status='VERIFIED',evidence_reference='SOFTWARE_TEST_FIXTURE_ONLY',header_hex='00'*48,verified_max_points=10000,code_center=10000,codes_per_relative_unit=4500,verified_code_min=5000,verified_code_max=15000)
 def test_roundtrip(self):
  y=[.123456,-.1]*8;b,r=encode(y,self.profile());self.assertLessEqual(r['max_quantization_error_relative'],r['half_lsb_relative']);self.assertFalse(r['hardware_verified']);self.assertEqual(struct.unpack_from('<I',b,12)[0],16)
 def test_corrupt(self):
  p=self.profile();b,_=encode([0]*16,p)
  for data in [b[:20],b[:-1],b+b'xx',bytes([1])+b[1:],b[:48]+b'\xff\xff'+b[50:]]:
   with self.assertRaises(ValueError):inspect(data,p)
 def test_source_mismatch(self):
  p=self.profile();b,_=encode([0]*16,p)
  with self.assertRaises(ValueError):inspect(b,p,[.1]*16)
 def test_bad_profile(self):
  for k,v in [('status','PENDING'),('verified_max_points',True),('codes_per_relative_unit',float('nan')),('verified_code_min',1.5)]:
   p=self.profile();p[k]=v
   with self.assertRaises(ValueError):encode([0]*16,p)
 def test_overflow(self):
  for value in [2,float('inf'),float('nan'),5000/4500+1e-6]:
   with self.assertRaises(ValueError):encode([value]*16,self.profile())
 def test_generate_export_and_tamper(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);cfg=dict(split_role='calibration_dev',sample_rate_hz=1000,duration_s=1,cases=[dict(id='T')])
   generate(cfg,root/'generated',self.profile());source=root/'generated/T'
   r=export_existing(source,root/'export',self.profile());self.assertEqual(r['whole_record_repeat_hz'],1)
   self.assertEqual((source/'T.bin').read_bytes(),(root/'export/waveform.bin').read_bytes())
   with self.assertRaises(ValueError):export_existing(source,root/'export',self.profile())
   (source/'source.csv').write_text('broken')
   with self.assertRaises(ValueError):export_existing(source,root/'bad',self.profile())

class CliTests(unittest.TestCase):
 profile=BinTests.profile
 def test_cli_modes(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);profile=root/'profile.json';profile.write_text(json.dumps(self.profile()))
   cfg=root/'config.json';cfg.write_text(json.dumps(dict(split_role='calibration_dev',sample_rate_hz=1000,duration_s=1,cases=[dict(id='CLI')])))
   cli=[sys.executable,str(Path(__file__).with_name('wavegen.py'))]
   def run(*args):
    return subprocess.run(cli+list(map(str,args)),capture_output=True,text=True)
   r=run('--config',cfg,'--output',root/'generated','--bin-profile',profile)
   self.assertEqual(r.returncode,0,r.stderr)
   source=root/'generated/CLI'
   r=run('--export-source',source,'--output',root/'export','--bin-profile',profile)
   self.assertEqual(r.returncode,0,r.stderr)
   r=run('--check-bin',root/'export/waveform.bin','--compare-source',source,'--bin-profile',profile,'--output',root/'check.json')
   self.assertEqual(r.returncode,0,r.stderr)
   report=json.loads((root/'check.json').read_text());self.assertTrue(report['source_compared']);self.assertFalse(report['training_eligible'])
   self.assertEqual((source/'CLI.bin').read_bytes(),(root/'export/waveform.bin').read_bytes())
   r=run('--check-bin',root/'export/waveform.bin','--bin-profile',profile,'--output',root/'check.json')
   self.assertEqual(r.returncode,2)
   data=bytearray((root/'export/waveform.bin').read_bytes());data[48]^=1;(root/'changed.bin').write_bytes(data)
   r=run('--check-bin',root/'changed.bin','--compare-source',source,'--bin-profile',profile)
   self.assertEqual(r.returncode,2);self.assertIn('does not match',r.stderr)

if __name__=='__main__':unittest.main()
