"""NDG observed format codec. Software checks never certify physical output."""
import hashlib,json,math,struct,csv
from pathlib import Path

def sha(b):return hashlib.sha256(b).hexdigest()
def profile_values(p):
    if p.get('status')!='VERIFIED' or not isinstance(p.get('evidence_reference'),str) or not p['evidence_reference'].strip():
        raise ValueError('Profile requires VERIFIED declaration and evidence_reference')
    h=bytes.fromhex(p['header_hex'])
    if len(h)!=48:raise ValueError('Expected 48-byte header')
    for key in ('verified_max_points','verified_code_min','verified_code_max'):
        if type(p[key]) is not int:raise ValueError(key+' must be integer')
    low,high=p['verified_code_min'],p['verified_code_max']
    if not 0<=low<high<=65535 or not 16<=p['verified_max_points']<=200000:raise ValueError('Invalid profile limits')
    center,scale=p['code_center'],p['codes_per_relative_unit']
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in (center,scale)) or scale<=0:raise ValueError('Invalid mapping')
    return h,center,scale,low,high

def inspect(data,p,values=None):
    h,center,scale,low,high=profile_values(p)
    if len(data)<48:raise ValueError('Truncated BIN header')
    n=struct.unpack_from('<I',data,12)[0]
    if not 16<=n<=p['verified_max_points'] or len(data)!=48+2*n:raise ValueError('Point count/file length mismatch')
    if data[:12]+data[16:48]!=h[:12]+h[16:48]:raise ValueError('Header differs from profile outside point count')
    codes=struct.unpack('<'+'H'*n,data[48:])
    if min(codes)<low or max(codes)>high:raise ValueError('BIN code outside verified range')
    report=dict(status='SOFTWARE_CHECK_PASS',bin_sha256=sha(data),points=n,bytes=len(data),code_min=min(codes),code_max=max(codes),
       margin_low_codes=min(codes)-low,margin_high_codes=high-max(codes),profile_sha256=sha(json.dumps(p,sort_keys=True).encode()),
       evidence_reference=p['evidence_reference'],profile_evidence_independently_verified=False,hardware_verified=False,
       source_compared=values is not None,automatic_normalization=False,automatic_clipping=False,
       first_code=codes[0],last_code=codes[-1],wrap_step_codes=codes[0]-codes[-1],seam_hardware_accepted=False,training_eligible=False)
    if values is not None:
        if len(values)!=n or any(not math.isfinite(v) for v in values):raise ValueError('Invalid source values')
        mapped=[center+scale*v for v in values]
        if any(not math.isfinite(v) or v<low or v>high for v in mapped):raise ValueError('Source exceeds mapping range before rounding')
        expected=[round(v) for v in mapped]
        if list(codes)!=expected:raise ValueError('BIN does not match source encoding')
        error=max(abs((c-center)/scale-v) for c,v in zip(codes,values))
        report.update(max_quantization_error_relative=error,half_lsb_relative=.5/scale)
    return report

def encode(values,p):
    h,center,scale,low,high=profile_values(p)
    if not 16<=len(values)<=p['verified_max_points']:raise ValueError('Unsupported points')
    mapped=[center+scale*v for v in values]
    if any(not math.isfinite(v) or v<low or v>high for v in mapped):raise ValueError('Code overflow: no clipping or normalization')
    header=bytearray(h);struct.pack_into('<I',header,12,len(values))
    data=bytes(header)+struct.pack('<'+'H'*len(values),*[round(v) for v in mapped])
    return data,inspect(data,p,values)

def load_source(source):
    """Validate the persisted CSV and its recorded identity before use."""
    source=Path(source)
    m=json.loads((source/'metadata.json').read_text(encoding='utf-8'))
    raw=(source/'source.csv').read_bytes()
    if sha(raw)!=m['source_sha256']:raise ValueError('Source CSV hash mismatch')
    rows=list(csv.DictReader(raw.decode('utf-8').splitlines()))
    if not rows or set(rows[0])!={'time_s','value_relative'}:raise ValueError('Expected generated CSV columns')
    values=[float(r['value_relative']) for r in rows];times=[float(r['time_s']) for r in rows]
    fs=m['sample_rate_hz']
    if not isinstance(fs,(int,float)) or isinstance(fs,bool) or not math.isfinite(fs) or fs<=0:raise ValueError('Invalid source rate')
    if len(values)!=m['n_points'] or any(not math.isfinite(t) or abs(t-i/fs)>1e-9/fs+1e-11 for i,t in enumerate(times)):raise ValueError('Source time grid mismatch')
    duration=m['duration_s']
    if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or abs(duration-len(values)/fs)>1e-10:raise ValueError('Source duration mismatch')
    return values,dict(source_sha256=sha(raw),source_metadata_sha256=sha((source/'metadata.json').read_bytes()),
       sample_rate_hz=fs,whole_record_repeat_hz=fs/len(values),fundamental_hz=m['fundamental_hz'],training_eligible=False)

def check_existing(path,p,source=None):
    values,identity=load_source(source) if source is not None else (None,{})
    report=inspect(Path(path).read_bytes(),p,values)
    report.update(identity)
    return report

def export_existing(source,output,p):
    output=Path(output)
    if output.exists():raise ValueError('Output exists')
    values,identity=load_source(source)
    data,report=encode(values,p)
    report.update(identity)
    output.mkdir(parents=True)
    target=output/'waveform.bin';target.write_bytes(data)
    inspect(target.read_bytes(),p,values)
    (output/'bin_check.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    (output/'encoding_profile.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
    return report
