import unittest,tempfile,json,copy,struct
from pathlib import Path
from wavegen import generate
from events import envelope

class Tests(unittest.TestCase):
 def cfg(self):return dict(split_role='calibration_dev',sample_rate_hz=1000,duration_s=1,fundamental_hz=50,cases=[dict(id='TEST',events=[dict(kind='sag',start_s=.2,duration_s=.2,level=.5)])])
 def run_case(self,c,profile=None):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'out';generate(c,p,profile)
   m=json.loads((p/'TEST/metadata.json').read_text());y=[float(s.split(',')[1]) for s in (p/'TEST/source.csv').read_text().splitlines()[1:]]
   return m,y
 def test_sag_ratio_and_baseline(self):
  m,y=self.run_case(self.cfg());self.assertAlmostEqual(y[205]/y[105],.5);self.assertAlmostEqual(y[405]/y[105],1);self.assertFalse(m['training_eligible'])
 def test_interrupt_zero_and_residual(self):
  c=self.cfg();c['cases'][0]['events'][0].update(kind='interruption',level=0)
  _,y=self.run_case(c);self.assertTrue(all(v==0 for v in y[200:400]))
  c['cases'][0]['dc_offset_relative']=.1;_,y=self.run_case(c);self.assertTrue(all(v==.1 for v in y[200:400]))
 def test_harmonics_scaling_modes(self):
  c=self.cfg();c['cases'][0]['harmonics']={'3':{'ratio':.1}}
  _,y=self.run_case(c);self.assertAlmostEqual(y[205]/y[105],.5)
  c['cases'][0]['event_scale_mode']='fundamental_only';_,y=self.run_case(c);self.assertAlmostEqual(y[205],.4)
 def test_ramps(self):
  c=self.cfg()['cases'][0];c['events'][0].update(ramp_in_s=.01,ramp_out_s=.02)
  e,a,_=envelope(c,1000,1000);self.assertEqual(e[200],1);self.assertEqual(e[210],.5);self.assertAlmostEqual(e[390],.75);self.assertEqual(e[400],1)
 def test_bad_timing(self):
  for change in [dict(start_s=0),dict(start_s=.2001),dict(duration_s=.8),dict(ramp_in_s=.2),dict(level=-1),dict(kind='unknown')]:
   c=self.cfg();c['cases'][0]['events'][0].update(change)
   with self.assertRaises(ValueError):self.run_case(c)
 def test_overlap(self):
  c=self.cfg();c['cases'][0]['events']*=2
  with self.assertRaises(ValueError):self.run_case(c)
 def test_swell_bin_overflow(self):
  c=self.cfg();c['cases'][0]['events'][0].update(kind='swell',level=2)
  profile=dict(status='VERIFIED',evidence_reference='TEST_FIXTURE_NOT_HARDWARE',header_hex='00'*48,verified_max_points=1000,code_center=10000,codes_per_relative_unit=4500,verified_code_min=5000,verified_code_max=15000)
  with self.assertRaises(ValueError):self.run_case(c,profile)
 def test_seed_and_no_overwrite(self):
  c=self.cfg();c['cases'][0].update(noise_rms_relative=.01,seed=77)
  self.assertEqual(self.run_case(c)[1],self.run_case(c)[1])
  with tempfile.TemporaryDirectory() as t:
   with self.assertRaises(ValueError):generate(c,Path(t))
 def test_steady(self):
  c=self.cfg();c['cases'][0].pop('events');m,y=self.run_case(c);self.assertAlmostEqual(m['dft_ratios']['1'],1);self.assertEqual(m['events'],[])
 def test_multiple(self):
  c=self.cfg();c['cases'][0]['events'].append(dict(kind='swell',start_s=.6,duration_s=.2,level=1.2));m,y=self.run_case(c);self.assertEqual(len(m['events']),2);self.assertAlmostEqual(y[605]/y[105],1.2)

if __name__=='__main__':unittest.main()
