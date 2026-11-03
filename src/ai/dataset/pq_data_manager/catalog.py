"""Unified evidence inventory. Not an approval or dataset splitter."""
import argparse,json,hashlib
from pathlib import Path
from summarize_runs import summarize

def build(data_root,capture_root=None):
    root=Path(data_root).resolve();records=[];issues=[]
    if not root.is_dir():raise ValueError('Historical data root missing')
    for directory in sorted(root.iterdir()):
        if not directory.is_dir():continue
        if directory.is_symlink() or not directory.resolve().is_relative_to(root):
            issues.append(dict(path=str(directory),reason='Unsafe directory link'));continue
        try:
            report_path=directory/'import_report.json'
            if not report_path.exists():
                if (directory/'inventory.json').exists():
                    records.append(dict(type='DOCUMENT_ARCHIVE',path=str(directory),sample_count=0,training_eligible=False))
                else:issues.append(dict(path=str(directory),reason='Unknown directory format'))
                continue
            report=json.loads(report_path.read_text(encoding='utf-8'))
            if report.get('module')=='h12-import-0.1':
                for case in report['cases']:
                    name=case['case']
                    if name not in ['CASE1','CASE2']:raise ValueError('Unknown H12 case')
                    p=directory/name/'terminal.log'
                    if hashlib.sha256(p.read_bytes()).hexdigest()!=case['log_sha256']:raise ValueError('H12 original log changed')
                    records.append(dict(type='FEATURE_ONLY',source='H12',case=name,frame_ids=case['selected_frames'],sample_count=len(case['selected_frames']),lineage_group_id=case['lineage_group_id'],training_eligible=False,path=str(directory/name)))
            elif report.get('status')=='SOURCE_HASH_AND_PAIR_CHECKS_PASS':
                pairs=json.loads((directory/'pairs.json').read_text(encoding='utf-8'))
                for pair in pairs:
                    records.append(dict(type='MATCHED_PAIR',source='H13',frame_ids=[pair['frame_id']],sample_count=1,lineage_group_id=pair['lineage_group_id'],training_eligible=False,path=str(directory)))
            else:raise ValueError('Unknown import report')
        except (OSError,ValueError,KeyError,TypeError) as e:issues.append(dict(path=str(directory),reason=str(e)))
    captures=summarize(capture_root) if capture_root else None
    return dict(module='unified-catalog-0.1',historical_records=records,historical_frame_count=sum(r['sample_count'] for r in records),historical_lineages=sorted({r['lineage_group_id'] for r in records if 'lineage_group_id' in r}),issues=issues,captures=captures,training_eligible=False,note='Catalog of prior import reports, not full source revalidation. Counts do not establish independent waveforms. H13 source checks remain in import_h13.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--data-root',type=Path,default=Path(__file__).parent/'data');p.add_argument('--capture-root',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    try:
        for root in [a.data_root,a.capture_root]:
            if root and a.output.resolve().is_relative_to(root.resolve()):raise ValueError('Save report outside evidence roots')
        r=build(a.data_root,a.capture_root)
        with a.output.open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
        print(f"Historical frames: {r['historical_frame_count']}; issues: {len(r['issues'])}")
    except (OSError,ValueError) as e:p.exit(2,str(e)+'\n')
