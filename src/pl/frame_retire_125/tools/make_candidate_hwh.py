"""Describe the actual own adapter, preserving public interfaces/address map.

The raw BD HWH describes a vendor peripheral before the explicit synthesis
binding override. Do not distribute it as though it described the new core.
"""
from pathlib import Path
import sys, json, hashlib, xml.etree.ElementTree as ET
source,target,report=map(Path,sys.argv[1:])
assert source.resolve()!=target.resolve() and not target.exists()
tree=ET.parse(source);root=tree.getroot()
modules=[m for m in root.findall('.//MODULE') if m.get('FULLNAME','').strip('/')=='video/axi_vdma']
assert len(modules)==1
m=modules[0];before=dict(m.attrib)
params=m.find('PARAMETERS');assert params is not None
original=next(x for x in params if x.get('NAME')=='C_PRMRY_IS_ACLK_ASYNC')
assert original.get('VALUE')=='1'
original.set('VALUE','0')
m.set('MODTYPE','lab08_vdma_frame_retire')
m.set('VLNV','user.org:user:lab08_vdma_frame_retire:1.0')
m.set('HWVERSION','1.0')
for key,value in {'C_FRAME_RETIRE_CAPABILITY':'0x46520101',
                  'C_FRAME_RETIRE_SESSION':'COLD_ARM_ONCE_PER_CONFIGURATION',
                  'C_FRAME_RETIRE_REGISTER_WINDOW':'0x100..0x1FC',
                  'C_CONTROL_BRIDGE':'REQUEST_ACK_SNAPSHOT',
                  'C_CONTROL_BRIDGE_SNAPSHOT_WIDTH':'34',
                  'C_EXTERNAL_CONTROL_CLOCK_HZ':'100000000',
                  'C_CORE_CONTROL_CLOCK_HZ':'142857132',
                  'C_CORE_CONTROL_CLOCK_SOURCE':'m_axi_mm2s_aclk',
                  'C_CORE_RESET_SOURCE':'bridge.m_resetn_out',
                  'C_VENDOR_REGIF_ASYNC_HARDCODED':'1_SAME_ACTUAL_CLOCK',
                  'C_IRQ_LEVEL_SYNC_STAGES':'2',
                  'C_MM2S_R_CHANNEL_SLICE':'ONE_ENTRY_ELASTIC',
                  'C_MM2S_R_SLICE_RESET':'SYNCHRONOUS_ACTIVE_LOW',
                  'C_MM2S_R_SLICE_CLOCK_SOURCE':'m_axi_mm2s_aclk'}.items():
 ET.SubElement(params,'PARAMETER',{'NAME':key,'VALUE':value})
# Ports and memory maps are inherited byte-semantically, not re-addressed.
ports_before=[dict(x.attrib) for x in m.findall('./PORTS/PORT')]
warm_module=next(x for x in root.findall('.//MODULE') if x.get('FULLNAME','').strip('/')=='video/hdmi_out/warm_reset')
reset_source_port=next(x for x in warm_module.findall('./PORTS/PORT') if x.get('NAME')=='unpack_resetn')
assert reset_source_port.get('SIGNAME')
ET.SubElement(m.find('PORTS'),'PORT',{'DIR':'I','NAME':'retire_video_resetn','SIGIS':'rst','SIGNAME':reset_source_port.get('SIGNAME')})
ET.SubElement(params,'PARAMETER',{'NAME':'C_RETIRE_RESET_CONNECTION','VALUE':'video/hdmi_out/warm_reset/unpack_resetn; candidate emitted HDL named-port binding'})
tree.write(target,encoding='utf-8',xml_declaration=True)
new=ET.parse(target).getroot()
nm=next(x for x in new.findall('.//MODULE') if x.get('FULLNAME','').strip('/')=='video/axi_vdma')
assert [dict(x.attrib) for x in nm.findall('./PORTS/PORT') if x.get('NAME')!='retire_video_resetn']==ports_before
assert len([x for x in nm.findall('./PORTS/PORT') if x.get('NAME')=='retire_video_resetn'])==1
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report.write_text(json.dumps({'status':'OWN_ADAPTER_METADATA_GENERATED',
 'raw_bd_hwh':str(source),'raw_sha256':sha(source),'candidate_hwh':str(target),'sha256':sha(target),
 'module_before':before,'module_after':dict(nm.attrib),
 'address_and_external_port_contract':'UNCHANGED',
 'core_async_parameter':0,
 'driver_binding':'CUSTOM_VLNV; no automatic old vendor driver binding claimed; PS integration review required',
 'provenance':'Raw generated BD HWH transformed to describe explicit own synthesis adapter; raw file preserved'},
 ensure_ascii=False,indent=2),encoding='utf-8')
print('OWN_ADAPTER_HWH_GENERATED; external address/port contract preserved; custom VLNV explicit')
