"""Fail-closed offline label rules and formal dataset readiness checks.

No physical thresholds are supplied by this module. Synthetic policies must
remain separate from physical policy approvals.
"""
import hashlib
import json
import math
from pathlib import Path

LABELS=('CLEAN','H3_DOMINANT','H5_DOMINANT','MIXED_ODD_HARMONICS')
ORDER=('H3_pct','H5_pct','H7_pct','H9_pct','THD_ODD_pct','Crest')
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def interval_label(lower,upper,policy):
    """Classify independently sourced intervals, not PL-generated truth."""
    if len(lower)!=4 or len(upper)!=4:raise ValueError('Four harmonic intervals required')
    tc=policy['clean_pct'];ta=policy['active_pct'];d=policy['dominance_ratio']
    if len(tc)!=4 or len(ta)!=4 or not math.isfinite(d) or d<=1:raise ValueError('Invalid policy')
    if any(not math.isfinite(v) for v in list(lower)+list(upper)+tc+ta):raise ValueError('Nonfinite policy/interval')
    if any(not 0<=c<a for c,a in zip(tc,ta)):raise ValueError('Invalid low/active gap')
    if any(not 0<=l<=u for l,u in zip(lower,upper)):raise ValueError('Invalid interval')
    low=[u<=c for u,c in zip(upper,tc)];active=[l>=a for l,a in zip(lower,ta)]
    if any(not (lo or ac) for lo,ac in zip(low,active)):return None,'BOUNDARY'
    if all(low):return LABELS[0],'CLASSIFIED'
    for i in (0,1):
        if active[i] and lower[i]>d*max(upper[j] for j in range(4) if j!=i):return LABELS[i+1],'CLASSIFIED'
    # To rule out dominance robustly, use upper of target versus lower competitors.
    non_dominant=[not active[i] or upper[i]<d*max(lower[j] for j in range(4) if j!=i) for i in (0,1)]
    if sum(active)>=2 and all(non_dominant):return LABELS[3],'CLASSIFIED'
    if sum(active)==1 and (active[2] or active[3]):return None,'OUT_OF_SCOPE'
    return None,'BOUNDARY'

def validate_features(x):
    return (len(x)==6 and all(isinstance(v,(int,float)) and math.isfinite(v) and v>=0 for v in x)
            and x[5]>=1)

def formal_preflight(rows,policy,approval,base):
    """Checks a resolved manifest, never promotes source/sample statuses.

    Approvals are an audited project artifact, not a cryptographic signer.
    Label decisions must already have independent-source provenance.
    """
    issues=[];base=Path(base).resolve()
    if policy.get('status')!='APPROVED_PHYSICAL':issues.append('PHYSICAL_POLICY_NOT_APPROVED')
    required=['h1_min_code_rms','clean_pct','active_pct','dominance_ratio','reference_interval_method','clean_thd_gate','scope_policy','label_map_version','label_spec_version']
    for k in required:
        if policy.get(k) is None:issues.append('POLICY_UNRESOLVED:'+k)
    if policy.get('clean_pct') is not None and policy.get('active_pct') is not None and policy.get('dominance_ratio') is not None:
        try:interval_label([0]*4,[0]*4,policy)
        except (ValueError,TypeError):issues.append('INVALID_NUMERIC_POLICY')
    if not approval or approval.get('approved') is not True:issues.append('NO_RELEASE_APPROVAL')
    def digest_obj(obj):return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    if approval:
        if approval.get('policy_sha256')!=digest_obj(policy):issues.append('APPROVAL_POLICY_HASH_MISMATCH')
        if approval.get('manifest_sha256')!=digest_obj(rows):issues.append('APPROVAL_MANIFEST_HASH_MISMATCH')
        if not approval.get('decision_reference'):issues.append('NO_APPROVAL_PROVENANCE')
    h1=policy.get('h1_min_code_rms')
    if h1 is not None and (not isinstance(h1,(int,float)) or not math.isfinite(h1) or h1<=0):issues.append('INVALID_H1_MIN')
    if policy.get('clean_thd_gate') is not None:
        gate=policy['clean_thd_gate']
        if not isinstance(gate,dict) or gate.get('mode') not in ('ENABLED','DISABLED'):issues.append('INVALID_CLEAN_THD_GATE')
        elif gate['mode']=='ENABLED' and (not isinstance(gate.get('threshold_pct'),(int,float)) or not math.isfinite(gate['threshold_pct']) or gate['threshold_pct']<0):issues.append('INVALID_CLEAN_THD_THRESHOLD')
    if not rows:issues.append('NO_FORMAL_SAMPLES')
    groups={};source_groups={};counts={s:{c:0 for c in LABELS} for s in ('train','validation','test_internal')};ids=set()
    eligible=0
    for r in rows:
        rid=r.get('record_id');prefix=str(rid)+':'
        if not rid or rid in ids:issues.append(prefix+'MISSING_OR_DUPLICATE_ID')
        ids.add(rid)
        if r.get('source_label') not in LABELS or r.get('label_status')!='VERIFIED' or r.get('sample_status')!='ACCEPTED' or r.get('training_eligible') is not True:issues.append(prefix+'NOT_TRAINING_ELIGIBLE')
        else:eligible+=1
        role=r.get('split_role');gid=r.get('lineage_group_id')
        if role not in counts:issues.append(prefix+'NO_FORMAL_SPLIT')
        if not gid:issues.append(prefix+'MISSING_LINEAGE')
        groups.setdefault(gid,set()).add(role)
        if role in counts and r.get('source_label') in LABELS:counts[role][r['source_label']]+=1
        if role=='test_internal' and (r.get('used_for_development') is not False or r.get('origin_role')=='calibration_dev'):issues.append(prefix+'DEVELOPMENT_DATA_IN_FINAL_TEST')
        if r.get('source_type') not in ('physical','awg_replay_parametric'):issues.append(prefix+'NONPHYSICAL_FORMAL_PRIMARY_DATA')
        if r.get('feature_config_version')!='lab07-harmonic-6d-0.1' or r.get('adapter_version')!='lab07-harmonic-adapter-0.5':issues.append(prefix+'INPUT_VERSION_MISMATCH')
        if not validate_features(r.get('features',[])):issues.append(prefix+'INVALID_SIX_FEATURES')
        if r.get('label_spec_version')!=policy.get('label_spec_version'):issues.append(prefix+'LABEL_VERSION_MISMATCH')
        if not r.get('independent_label_evidence'):issues.append(prefix+'NO_INDEPENDENT_LABEL_EVIDENCE')
        for field in ('source_identity_verified','scope_verified','h1_reliability_verified'):
            if r.get(field) is not True:issues.append(prefix+'NOT_VERIFIED:'+field)
        for field in ('source_sha256','raw_sha256','feature_sha256','session_id','device_id','bit_sha256','hwh_sha256'):
            if not r.get(field) or r[field]=='unknown':issues.append(prefix+'MISSING:'+field)
        for field in ('source_sha256','raw_sha256'):
            if r.get(field):source_groups.setdefault((field,r[field]),set()).add(role)
        refs=r.get('evidence_files',[])
        if not refs:issues.append(prefix+'NO_HASHED_EVIDENCE_FILES')
        for ref in refs:
            q=(base/ref['path']).resolve()
            if not q.is_relative_to(base):issues.append(prefix+'UNSAFE_EVIDENCE_PATH');continue
            if not q.is_file() or sha(q)!=ref['sha256']:issues.append(prefix+'EVIDENCE_HASH_MISMATCH')
    if any(len(s)>1 for s in groups.values()):issues.append('LINEAGE_CROSSES_SPLITS')
    if any(len(s)>1 for s in source_groups.values()):issues.append('SAME_SOURCE_OR_RAW_CROSSES_SPLITS')
    for role,c in counts.items():
        if any(v==0 for v in c.values()):issues.append('MISSING_CLASS_COVERAGE:'+role)
    return dict(status='READY' if not issues else 'BLOCKED',formal_training_permitted=not issues,rows=len(rows),eligible_records=eligible,issues=sorted(set(issues)),class_counts=counts)

def write_locked_split(rows,seed=20261102):
    """No frames randomized across a lineage. Requires >=5 groups/class.

    This is a planning algorithm; output becomes a released split only after
    formal_preflight and approval. Mixed-label groups require manual allocation.
    """
    import random
    by={c:{} for c in LABELS};seen={}
    for r in rows:
        if r.get('label_status')!='VERIFIED' or r.get('sample_status')!='ACCEPTED' or not r.get('training_eligible'):raise ValueError('Unapproved record')
        g=r['lineage_group_id'];c=r['source_label']
        if g in seen and seen[g]!=c:raise ValueError('Multi-label lineage needs explicit allocation')
        seen[g]=c;by[c].setdefault(g,[]).append(r)
    result=[];rng=random.Random(seed)
    for c,groups in by.items():
        gs=sorted(groups)
        if len(gs)<5:raise ValueError('Insufficient independent groups for '+c)
        rng.shuffle(gs);n=len(gs);nval=max(1,int(n*.2));ntest=max(1,int(n*.2))
        # Development groups can train/validate after explicit promotion, never final test.
        candidates=[g for g in gs if all(r.get('used_for_development') is False and r.get('origin_role')!='calibration_dev' for r in groups[g])]
        if len(candidates)<ntest:raise ValueError('Insufficient untouched test lineages')
        tests=set(candidates[:ntest]);rest=[g for g in gs if g not in tests];vals=set(rest[:nval])
        for g in gs:
            role='test_internal' if g in tests else 'validation' if g in vals else 'train'
            result.extend(dict(r,split_role=role) for r in groups[g])
    return result
