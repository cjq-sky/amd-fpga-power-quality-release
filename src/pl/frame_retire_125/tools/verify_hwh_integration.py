from pathlib import Path
import hashlib,json,sys,xml.etree.ElementTree as ET
source,output=map(Path,sys.argv[1:3])
root=ET.parse(source).getroot()
mods={m.get('FULLNAME'):m for m in root.findall('.//MODULE')}
ports=lambda n:{p.get('NAME'):p for p in mods[n].findall('./PORTS/PORT')}
sig=lambda n,p:ports(n)[p].get('SIGNAME')
expected={'/lab07_mmio':(0x43c00000,0x1000),'/lab07_raw':(0x43c10000,0x2000),
 '/video/hdmi_out/frontend/hdmi_out_hpd_video':(0x41230000,0x10000),'/system_interrupts':(0x41800000,0x10000),
 '/video/axi_vdma':(0x43000000,0x10000),'/video/hdmi_out/frontend/vtc_out':(0x43c20000,0x10000),
 '/video/hdmi_out/frontend/axi_dynclk':(0x43c30000,0x10000),'/video/hdmi_out/warm_reset':(0x43c40000,0x10000),
 '/video/hdmi_out/color_convert':(0x43c60000,0x10000),'/video/hdmi_out/pixel_unpack':(0x43c70000,0x10000)}
byinst={m.get('INSTANCE'):m for m in mods.values()}
rows=[]
for m in mods.values():
 for a in m.findall('./MEMORYMAP/MEMRANGE'):
  leaf=byinst[a.get('INSTANCE')]
  rows.append({'master':m.get('FULLNAME'),'ip':leaf.get('FULLNAME'),'vlnv':leaf.get('VLNV'),**a.attrib})
regs=[x for x in rows if x['MEMTYPE']=='REGISTER']
assert len(regs)==10
for row in regs:
 lo,span=expected[row['ip']]
 assert int(row['BASEVALUE'],0)==lo and int(row['HIGHVALUE'],0)==lo+span-1,row
ranges=sorted((int(x['BASEVALUE'],0),int(x['HIGHVALUE'],0)) for x in regs)
assert all(a[1]<b[0] for a,b in zip(ranges,ranges[1:]))
wr='/video/hdmi_out/warm_reset';u='/video/hdmi_out/pixel_unpack'
assert mods[wr].get('VLNV')=='pq.local:user:lab08_warm_reset_ctrl:1.0'
params={p.get('NAME'):p.get('VALUE') for p in mods[wr].findall('./PARAMETERS/PARAMETER')}
assert int(params['MIN_RESET_CYCLES'],0)==32
assert sig(wr,'unpack_resetn')==sig(u,'ap_rst_n')
assert sig(wr,'stream_resetn')==sig(u,'ap_rst_n_control')
for n,p in [('/video/hdmi_out/color_convert','ap_rst_n'),('/video/hdmi_out/axis_register_slice_0','aresetn'),('/video/hdmi_out/frontend/v_axi4s_vid_out_0','aresetn')]:
 assert sig(n,p)==sig(wr,'stream_resetn'),(n,p)
assert sig(wr,'stream_clk')==sig(u,'ap_clk')==sig('/video/axi_vdma','m_axis_mm2s_aclk')
assert sig(wr,'s_axi_aclk')==sig('/ps7_0','FCLK_CLK0')
assert sig(wr,'s_axi_aresetn')==sig('/rst_ps7_0_fclk0','peripheral_aresetn')
assert sig(wr,'stream_clk')==sig('/ps7_0','FCLK_CLK1')
assert sig(wr,'video_locked')==sig('/video/hdmi_out/frontend/v_axi4s_vid_out_0','locked')
connections=[]
for n,m in mods.items():
 for p in m.findall('./PORTS/PORT'):
  if p.get('SIGNAME')==sig(wr,'unpack_resetn') and p.get('DIR')=='I':connections.append((n,p.get('NAME')))
assert connections==[(u,'ap_rst_n')],connections
for n in ['/lab07_mmio','/lab07_raw']:
 assert sig(n,'s_axi_aclk')!=sig(wr,'stream_clk')
 assert sig(n,'s_axi_aresetn')!=sig(wr,'unpack_resetn')
psparams={p.get('NAME'):p.get('VALUE') for p in mods['/ps7_0'].findall('./PARAMETERS/PARAMETER')}
result={'status':'PASS_TEN_ADDRESSES_AND_RESET_ISOLATION','hwh':str(source),
 'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'addresses':rows,'warm_reset_parameters':params,
 'unpack_reset_sinks':connections,'ps_clock_parameters':{k:v for k,v in psparams.items() if 'FCLK' in k or 'PERIPHERAL_FREQMHZ' in k},
 'important_ports':{n:{p:q.attrib for p,q in ports(n).items() if p in ['s_axi_aclk','s_axi_aresetn','stream_clk','stream_resetn','unpack_resetn','video_locked','ap_rst_n','ap_rst_n_control','ap_clk','FCLK_CLK0','FCLK_CLK1']} for n in [wr,u,'/lab07_mmio','/lab07_raw','/ps7_0']}}
output.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(result['status'])
