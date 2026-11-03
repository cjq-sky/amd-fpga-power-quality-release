"""Offline PQ source generator. Python 3.10+, standard library only."""
import argparse, hashlib, json, math, random, re, struct
from pathlib import Path

VERSION = '0.2.1'
# Works both as CLI and when loaded directly by the data manager.
import importlib.util
_spec=importlib.util.spec_from_file_location('pq_wavegen_events',Path(__file__).with_name('events.py'))
_events=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_events)
_bs=importlib.util.spec_from_file_location('pq_bin_codec',Path(__file__).with_name('bin_codec.py'))
_codec=importlib.util.module_from_spec(_bs);_bs.loader.exec_module(_codec)
def digest(b): return hashlib.sha256(b).hexdigest()
def finite(x): return isinstance(x,(int,float)) and not isinstance(x,bool) and math.isfinite(x)
def generate(cfg, output, profile=None):
    if output.exists(): raise ValueError('Output already exists; choose a new directory.')
    if cfg.get('split_role') != 'calibration_dev': raise ValueError('This release only produces calibration_dev candidates.')
    fs, duration = cfg['sample_rate_hz'], cfg['duration_s']
    if not finite(fs) or not finite(duration) or fs<=0 or duration<=0: raise ValueError('Invalid timing.')
    nf=fs*duration; n=round(nf)
    if abs(n-nf)>1e-8 or not 16<=n<=200000: raise ValueError('Point count must be integer, 16..200000.')
    plans=[]; names=set()
    for c in cfg['cases']:
        name=c['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+',name) or name in names: raise ValueError('Invalid/duplicate id.')
        names.add(name)
        f=c.get('fundamental_hz',cfg.get('fundamental_hz',50)); a=c.get('fundamental_peak_relative',1)
        if not finite(f) or not finite(a) or f<=0 or a<=0: raise ValueError('Invalid fundamental.')
        if abs(f*duration-round(f*duration))>1e-8: raise ValueError('Periodic mode requires integer fundamental cycles.')
        components=[(1,1.0,c.get('fundamental_phase_rad',0))]
        for order, spec in c.get('harmonics',{}).items():
            k=int(order)
            if str(k)!=order or k<2: raise ValueError('Harmonic order must be integer >=2.')
            components.append((k,spec['ratio'],spec.get('phase_rad',0)))
        for k,r,p in components:
            if not finite(r) or not finite(p) or r<0 or k*f>=fs/2: raise ValueError('Invalid harmonic or Nyquist violation.')
        noise=c.get('noise_rms_relative',0)
        if not finite(noise) or noise<0: raise ValueError('Invalid noise.')
        if noise and 'seed' not in c: raise ValueError('Noise requires explicit seed.')
        env,annotations,mode=_events.envelope(c,fs,n)
        dc=c.get('dc_offset_relative',0)
        if not finite(dc): raise ValueError('Invalid DC offset')
        rng=random.Random(c.get('seed',0))
        y=[a*sum(r*math.sin(2*math.pi*k*f*i/fs+p)*(env[i] if mode=='all_ac' or k==1 else 1) for k,r,p in components)+dc+(rng.gauss(0,noise*a) if noise else 0) for i in range(n)]
        if not all(math.isfinite(v) for v in y): raise ValueError('Nonfinite waveform.')
        measured={}
        for k in sorted({1,3,5,7,9}|{v[0] for v in components}):
            if k*f>=fs/2: continue
            co=sum(v*math.cos(2*math.pi*k*f*i/fs) for i,v in enumerate(y))*2/n
            si=sum(v*math.sin(2*math.pi*k*f*i/fs) for i,v in enumerate(y))*2/n
            measured[str(k)]=math.hypot(co,si)/a
        if not noise and not annotations:
            target={str(k):r for k,r,p in components}
            if any(abs(v-target.get(k,0))>1e-8 for k,v in measured.items()): raise ValueError('DFT verification failed.')
        encoded=None
        if profile is not None:
            encoded,_=_codec.encode(y,profile)
        plans.append((c,f,a,y,measured,encoded,env,annotations,mode))
    if not plans: raise ValueError('No cases.')
    output.mkdir(parents=True)
    (output/'config.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2),encoding='utf-8')
    if profile: (output/'encoding_profile.json').write_text(json.dumps(profile,indent=2),encoding='utf-8')
    manifest=[]
    for c,f,a,y,measured,encoded,env,annotations,mode in plans:
        name=c['id']; d=output/name; d.mkdir()
        data=('time_s,value_relative\n'+''.join(f'{i/fs:.17g},{v:.17g}\n' for i,v in enumerate(y))).encode()
        (d/'source.csv').write_bytes(data)
        numeric=struct.pack('<'+'d'*n,*y)
        meta=dict(generator_version=VERSION,waveform_id=name,parameter_set_id=name,lineage_group_id=c.get('lineage_group_id',name),source_type='parametric_synthetic',split_role='calibration_dev',label=None,label_status='LABEL_REVIEW',parameters=c,sample_rate_hz=fs,n_points=n,duration_s=duration,whole_record_repeat_hz=1/duration,fundamental_hz=f,whole_vpp_relative=max(y)-min(y),rms_relative=math.sqrt(sum(v*v for v in y)/n),source_sha256=digest(data),numeric_sha256=digest(numeric),dft_ratios=measured,periodic_extension='analytic_periodic' if not c.get('noise_rms_relative',0) else 'repeated_noise_record_boundary_requires_review',last_to_first_step=y[0]-y[-1],hardware_verified=False,bin_generated=encoded is not None)
        meta.update(events=annotations,event_scale_mode=mode,dc_offset_relative=c.get('dc_offset_relative',0),
            noise_placement='additive_after_envelope',source_label=None,training_eligible=False,
            spectral_diagnostic_scope='whole_record_relative_to_nominal_fundamental_peak_NOT_event_THD_or_label',
            playback='whole record repeats, including every event; single-shot requires hardware setup',
            bandwidth_warning='Envelope edges create broadband content; sinusoid Nyquist check does not certify event bandwidth',
            interruption_warning='Zero envelope does not imply zero output when DC/noise or unscaled harmonics exist')
        if annotations:
            meta['periodic_extension']='event_record_repeats_with_baseline_at_both_ends'
        envelope_data=('time_s,envelope_relative\n'+''.join(f'{i/fs:.17g},{v:.17g}\n' for i,v in enumerate(env))).encode()
        (d/'envelope.csv').write_bytes(envelope_data)
        meta['envelope_sha256']=digest(envelope_data)
        if encoded:
            (d/(name+'.bin')).write_bytes(encoded); meta['bin_sha256']=digest(encoded)
            check=_codec.inspect((d/(name+'.bin')).read_bytes(),profile,y)
            check.update(sample_rate_hz=fs,whole_record_repeat_hz=1/duration,source_sha256=digest(data),training_eligible=False)
            (d/'bin_check.json').write_text(json.dumps(check,indent=2),encoding='utf-8')
        (d/'metadata.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8'); manifest.append(meta)
        end=n if annotations else min(n,round(2*fs/f)+1); stride=max(1,end//1500); peak=max(abs(v) for v in y) or 1
        pts=' '.join(f'{40+720*i/max(1,end-1):.2f},{145-95*y[i]/peak:.2f}' for i in range(0,end,stride))
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="800" height="300"><rect width="800" height="300" fill="white"/><text x="30" y="25">{name}: {f} Hz, relative units; auto-scaled preview</text><path d="M40 145H760" stroke="gray"/><polyline points="{pts}" fill="none" stroke="#1768ac"/><text x="30" y="280">Source only, NOT measured output. Peak scale {peak:.5g}</text></svg>'
        (d/'preview.svg').write_text(svg,encoding='utf-8')
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    (output/'preview.html').write_text('<meta charset="utf-8"><h1>Candidate source previews</h1>'+''.join(f'<img src="{m["waveform_id"]}/preview.svg"><br>' for m in manifest),encoding='utf-8')
    report=dict(count=len(manifest),unique_numeric_waveforms=len({m['numeric_sha256'] for m in manifest}),software_validation='PASS',bin_generated=profile is not None,bin_software_validation='PASS' if profile is not None else 'NOT_EXECUTED',hardware_validation='NOT_EXECUTED',formal_training_ready=False)
    (output/'validation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--config',type=Path)
    group.add_argument('--export-source',type=Path,help='Generated source folder with CSV and metadata')
    group.add_argument('--check-bin',type=Path,help='Check existing BIN against encoding profile')
    p.add_argument('--output',type=Path);p.add_argument('--bin-profile',type=Path)
    p.add_argument('--compare-source',type=Path,help='Source directory for point-by-point BIN comparison (with --check-bin)')
    args=p.parse_args()
    try:
        if args.compare_source and not args.check_bin:raise ValueError('--compare-source requires --check-bin')
        profile=json.loads(args.bin_profile.read_text(encoding='utf-8-sig')) if args.bin_profile else None
        if args.check_bin:
            if profile is None:raise ValueError('--check-bin requires --bin-profile')
            report=_codec.check_existing(args.check_bin,profile,args.compare_source)
            if args.output:
                with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2)
        elif args.export_source:
            if profile is None or args.output is None:raise ValueError('Export requires --output and --bin-profile')
            report=_codec.export_existing(args.export_source,args.output,profile)
        else:
            if args.output is None:raise ValueError('Generation requires --output')
            report=generate(json.loads(args.config.read_text(encoding='utf-8-sig')),args.output,profile)
        print(json.dumps(report,indent=2))
    except (ValueError,KeyError,TypeError,OSError,struct.error,OverflowError) as e:p.exit(2,f'Configuration/file rejected: {e}\n')
