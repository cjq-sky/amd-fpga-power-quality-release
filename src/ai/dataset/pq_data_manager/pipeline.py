"""Local generator -> manager registration -> reviewed development catalog.

No instrument control, approval promotion, Markdown generation, or training.
"""
import argparse,hashlib,importlib.util,json
from pathlib import Path
from collections import defaultdict
from register import register,identifier
from check_capture import check
from group_conflicts import conflicts

VERSION='pq-preparation-pipeline-1.0'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def save(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()

def generate_and_register(config,output,session,device='unknown',wavegen_path=None):
 identifier(session);identifier(device);output=Path(output).resolve()
 if output.exists():raise ValueError('Choose a new output directory; no overwrite')
 cfg=read(config)
 # Validate all run IDs before creating output.
 for c in cfg['cases']:identifier('PLAN_'+c['id']);identifier(c.get('lineage_group_id',c['id']))
 path=Path(wavegen_path).resolve() if wavegen_path else Path(__file__).resolve().parents[1]/'pq_wavegen'/'wavegen.py'
 if not path.is_file():raise ValueError('Generator not found. Install pq_wavegen alongside pq_data_manager or pass --wavegen PATH_TO_wavegen.py. Manager import/review/export work independently.')
 sp=importlib.util.spec_from_file_location('local_wavegen',path);mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod)
 mod.generate(cfg,output/'sources')
 manifest=read(output/'sources'/'manifest.json');normal=[]
 for r in manifest:
  q=output/'sources'/r['waveform_id']/'source.csv'
  if not q.resolve().is_relative_to((output/'sources').resolve()) or sha(q)!=r['source_sha256']:raise ValueError('Source identity failed')
  normal.append(dict(r,waveform_sha256=r['source_sha256'],source_record_id=r['waveform_id'],source_label=None,
      original_label_status=r.get('label_status'),label_status='UNRESOLVED',sample_status='PENDING_REVIEW',training_eligible=False))
 save(output/'normalized_manifest.json',normal)
 results=[]
 for r in normal:
  run=register(output/'normalized_manifest.json',r['waveform_id'],output/'runs','PLAN_'+r['waveform_id'],session,device,write_markdown=False)
  m=read(run/'metadata.json');m.update(original_label_status=m['label_status'],label_status='UNRESOLVED',sample_status='PENDING_REVIEW',training_eligible=False,
      preparation_pipeline_version=VERSION,feature_config_version='lab07-harmonic-6d-0.1',source_csv_path=str(output/'sources'/r['waveform_id']/'source.csv'),
      h1_reliability_status='NOT_CALIBRATED',amplitude_range_status='NOT_CALIBRATED',frequency_range_status='NOT_CALIBRATED')
  save(run/'metadata.json',m);results.append(check(run))
 save(output/'registration_checks.json',results)
 summary=dict(version=VERSION,source_groups=len(normal),planned_runs=len(results),captured_runs=0,training_eligible=0,
      status='GENERATED_AND_REGISTERED_NOT_CAPTURED',generator_sha256=sha(path),config_sha256=sha(config),
      missing_capture_information_expected=True,formal_policy='No automatic source labels or eligibility promotion')
 save(output/'pipeline_result.json',summary);return summary

def review_existing(manifest,evidence_root,output):
 rows=read(manifest);base=Path(evidence_root).resolve();output=Path(output).resolve()
 if output.exists():raise ValueError('Choose a new output directory')
 if output.is_relative_to(base):raise ValueError('Review output must be outside evidence root')
 seen=set();groups=defaultdict(list);verified={};allissues=[]
 for r in rows:
  rid=r['record_id']
  if rid in seen:raise ValueError('Duplicate record '+rid)
  seen.add(rid)
  for ref in r['evidence_files']:
   p=(base/ref['path']).resolve()
   if not p.is_relative_to(base):raise ValueError('Evidence path escapes root')
   if p not in verified:verified[p]=sha(p)
   if verified[p]!=ref['sha256']:raise ValueError('Evidence hash mismatch '+str(p))
  groups[r['run_id']].append(r)
 output.mkdir(parents=True)
 run_rows=[];qualified_rows=[]
 for run,rr in sorted(groups.items()):
  first=rr[0];lineage=first['lineage_group_id']
  if any(r['lineage_group_id']!=lineage for r in rr):raise ValueError('Conflicting run lineage')
  if lineage=='S0_SINE':use='BACKGROUND_AND_DOMAIN_COMPARISON';candidate='CLEAN'
  elif 'H3' in lineage:use='H3_RESPONSE_AND_DOMINANCE_CANDIDATE';candidate='H3_DOMINANT'
  elif 'H5' in lineage:use='H5_RESPONSE_AND_DOMINANCE_CANDIDATE';candidate='H5_DOMINANT'
  else:use='H7_H9_RESPONSE_AND_SCOPE_CHALLENGE';candidate=None
  missing=['INDEPENDENT_LABEL_QUALIFICATION','PHYSICAL_THRESHOLDS_AND_INTERVALS']
  if first.get('device_id') in (None,'unknown'):missing.append('DEVICE_IDENTITY')
  run_rows.append(dict(run_path=run,run_id=run,record_id=run,waveform_id=lineage,parameter_set_id=lineage,lineage_group_id=lineage,
      source_sha256=first['source_sha256'],split_role='calibration_dev',collection_domain=first['collection_domain'],frames=len(rr),
      reusable_for=use,candidate_label=candidate,candidate_basis='Source lineage hint only; not threshold/label approval',
      source_label=None,label_status='UNRESOLVED',sample_status='DEVELOPMENT_ONLY',training_eligible=False,pending=missing))
  for r in rr:qualified_rows.append(dict(r,candidate_label=candidate,candidate_basis='Lineage only',source_label=None,label_status='UNRESOLVED',sample_status='DEVELOPMENT_ONLY',training_eligible=False))
 finding=conflicts(run_rows)
 save(output/'run_qualification.json',run_rows);save(output/'development_manifest.json',qualified_rows);save(output/'group_findings.json',finding)
 summary=dict(version=VERSION,verified_evidence_files=len(verified),frames=len(rows),runs=len(groups),lineages=len({r['lineage_group_id'] for r in rows}),
      reusable_development_frames=len(rows),formal_training_eligible=0,formal_split=None,source_manifest_sha256=sha(manifest),
      extra_C_P3=dict(frames=32,status='NOT_B_VERIFIED_EXCLUDED'),
      history_preserved=True,conflict_count=sum(f['severity']=='conflict' for f in finding),
      mixed_verified_runs=0,calibration_status='NOT_CALIBRATED',no_new_measurement_required_by_this_check=True)
 save(output/'qualification_summary.json',summary);return summary

if __name__=='__main__':
 p=argparse.ArgumentParser();sub=p.add_subparsers(dest='command',required=True)
 g=sub.add_parser('prepare');g.add_argument('--config',type=Path,required=True);g.add_argument('--output',type=Path,required=True);g.add_argument('--session',required=True);g.add_argument('--device',default='unknown');g.add_argument('--wavegen',type=Path,help='Optional explicit path to separately installed wavegen.py')
 g=sub.add_parser('review');g.add_argument('--manifest',type=Path,required=True);g.add_argument('--evidence-root',type=Path,required=True);g.add_argument('--output',type=Path,required=True)
 a=p.parse_args()
 result=generate_and_register(a.config,a.output,a.session,a.device,a.wavegen) if a.command=='prepare' else review_existing(a.manifest,a.evidence_root,a.output)
 print(json.dumps(result,ensure_ascii=False,indent=2))
