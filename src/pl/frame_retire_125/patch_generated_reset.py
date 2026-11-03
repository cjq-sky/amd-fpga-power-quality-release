from pathlib import Path
import sys,re,json
root=Path(sys.argv[1]).resolve()
assert root.name=='u2' and (root.parents[2]/'source_identity.json').is_file(), 'Not an isolated candidate'
paths=list(root.rglob('synth/base.v'))+list(root.rglob('sim/base.v'))
assert len(paths)==2,paths
out=[]
for p in paths:
 s=p.read_text();pat=r'(base_axi_vdma_0\s+axi_vdma\s*\()'
 inst=re.search(pat,s);assert inst
 scope=s[s.rfind('module ',0,inst.start()):s.find('endmodule',inst.start())]
 assert re.search(r'output\s+retire_video_resetn\s*;',scope), 'Reset export missing from actual VDMA enclosing module'
 s,n=re.subn(pat,lambda m:m.group(1)+'.retire_video_resetn(retire_video_resetn),\n',s)
 assert n==1,(p,n)
 assert re.search(r'output\s+retire_video_resetn\s*;',s), 'Missing generated reset export'
 p.write_text(s,encoding='utf-8');out.append(str(p))
print(json.dumps({'candidate_generated_reset_connections':out}))
