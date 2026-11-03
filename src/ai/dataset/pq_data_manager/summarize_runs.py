"""Scan immediate Run directories; output new reports outside evidence root."""
import argparse,json
from collections import Counter
from pathlib import Path
from check_capture import check
from group_conflicts import conflicts

def read_object(path,root):
    try:
        if not path.resolve().is_relative_to(root):return {}
        obj=json.loads(path.read_text(encoding='utf-8-sig'))
        return obj if isinstance(obj,dict) else {}
    except (OSError,ValueError):return {}

def summarize(root):
    root=Path(root).resolve()
    if not root.is_dir():raise ValueError('Capture root is not a directory.')
    records=[];checks=[];skipped=[]
    for run in sorted(root.iterdir()):
        if not run.is_dir():continue
        if run.is_symlink() or not run.resolve().is_relative_to(root):
            skipped.append(str(run));continue
        # Every immediate directory is a Run candidate; missing metadata is reported.
        m=read_object(run/'metadata.json',run.resolve());s=read_object(run/'source_record.json',run.resolve())
        try:r=check(run)
        except (OSError,ValueError,TypeError,KeyError) as e:
            r=dict(run=str(run),structural_status='INCOMPLETE',issues=[dict(code='CHECK_ERROR',field='run',message=str(e))],inventory=[])
        checks.append(r)
        row={k:m.get(k) for k in ['run_id','record_id','session_id','waveform_id','parameter_set_id','lineage_group_id','split_role','capture_status','waveform_sha256','source_type']}
        row.update(run_path=str(run),source_sha256=s.get('source_sha256'),numeric_sha256=s.get('numeric_sha256'),inventory=r['inventory'],structural_status=r['structural_status'],issue_count=len(r['issues']))
        records.append(row)
    def counts(k):return dict(Counter(str(r.get(k) or 'UNKNOWN') for r in records))
    findings=conflicts(records)
    return dict(module='run-summary-0.1',capture_root=str(root),run_count=len(records),sessions=counts('session_id'),waveforms=counts('waveform_id'),capture_states=counts('capture_status'),structural_states=counts('structural_status'),issue_codes=dict(Counter(i['code'] for c in checks for i in c['issues'])),skipped_links=skipped,records=records,run_checks=checks,group_findings=findings,formal_training_eligible=False,note='Metadata counts are not independent sample counts. No automatic splitting, approval, near-duplicate detection or physical verification.')

def save(report,out):
    out=Path(out).resolve();root=Path(report['capture_root'])
    if out.is_relative_to(root):raise ValueError('Report directory must be outside capture root.')
    out.mkdir(parents=True,exist_ok=False)
    (out/'summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 多 Run 汇总与分组检查','',f"候选Run目录数：{report['run_count']}",'','仅结构检查；不代表采集、标签或训练资格通过。','']
    for r in report['run_checks']:
        lines.extend([f"## {Path(r['run']).name}",f"状态：{r['structural_status']}"])
        lines.extend(f"- {i['code']} / {i['field']}：{i['message']}" for i in r['issues'])
    lines+=['','## 重复与分组提示']
    lines.extend(f"- {f['severity']}：{f['code']}，{f['key']}={f['value']}；Run：{', '.join(f['runs'])}" for f in report['group_findings'])
    lines+=['','## 跳过的目录链接']+report['skipped_links']
    (out/'汇总报告.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        r=summarize(a.root);save(r,a.output)
        print(f"Runs={r['run_count']}; findings={len(r['group_findings'])}; report={a.output}")
        raise SystemExit(1 if not r['run_count'] or r['issue_codes'] or r['skipped_links'] or any(f['severity']!='info' for f in r['group_findings']) else 0)
    except (ValueError,OSError) as e:p.exit(2,str(e)+'\n')
