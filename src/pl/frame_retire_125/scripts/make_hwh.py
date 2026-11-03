"""Release-derived metadata generation for a NEW isolated build, not a frozen release overwrite."""
from pathlib import Path
import argparse, copy, hashlib, json, subprocess, sys
import xml.etree.ElementTree as ET
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p, data):
    Path(p).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')

def make_hwh():
    assert not HWH.exists()
    tree=ET.parse(RAW); root=tree.getroot()
    mods={m.get('FULLNAME'):m for m in root.findall('.//MODULE')}
    m=mods['/video/axi_vdma']; before=copy.deepcopy(m)
    ps={p.get('NAME'):p.get('VALUE') for p in mods['/ps7_0'].findall('./PARAMETERS/PARAMETER')}
    assert ps['PCW_CLK0_FREQ']=='100000000' and ps['PCW_CLK1_FREQ']=='125000000'
    assert float(ps['PCW_ACT_FPGA1_PERIPHERAL_FREQMHZ'])==125 and float(ps['PCW_S_AXI_HP0_FREQMHZ'])==125
    psports={p.get('NAME'):p for p in mods['/ps7_0'].findall('./PORTS/PORT')}
    assert psports['S_AXI_HP0_ACLK'].get('CLKFREQUENCY')=='125000000'
    assert psports['S_AXI_HP0_ACLK'].get('SIGNAME')==psports['FCLK_CLK1'].get('SIGNAME')
    # Reuse the reviewed own-wrapper transformation; correct its legacy fixed
    # clock annotation from the authenticated, genuine 125MHz PS7 metadata.
    adapter=(C/'tools/make_candidate_hwh.py').read_text(encoding='utf-8')
    assert adapter.count("'C_CORE_CONTROL_CLOCK_HZ':'142857132'")==1
    adapter=adapter.replace("'C_CORE_CONTROL_CLOCK_HZ':'142857132'", "'C_CORE_CONTROL_CLOCK_HZ':'125000000'")
    local=W/'make_release_hwh.py';local.write_text(adapter,encoding='utf-8')
    subprocess.run([sys.executable,str(local),str(RAW),str(HWH),str(E/'HWH_ADAPTER.json')],check=True)
    tree=ET.parse(HWH);root=tree.getroot()
    m=next(m for m in root.findall('.//MODULE') if m.get('FULLNAME')=='/video/axi_vdma')
    params=m.find('PARAMETERS')
    for k,v in {'C_RELEASE_ROUTED_DCP_SHA256':EXPECTED,'C_FRAME_RETIRE_DEADLINE_CYCLES':'125000000',
                'C_FRAME_RETIRE_QUEUE_DEPTH':'64','C_FRAME_RETIRE_BASELINE':'R6_WITH_R7A_HEAD_AND_TWO_STAGE_CONFIG',
                'C_VIDEO_WIDTH':'1280','C_VIDEO_HEIGHT':'720','C_VIDEO_STRIDE_BYTES':'3840','C_VIDEO_FORMAT':'BGR24'}.items():
        ET.SubElement(params,'PARAMETER',{'NAME':k,'VALUE':v})
    # Actual custom registers in frame_retire_registers.sv. Public address
    # windows and inherited vendor register descriptions remain unchanged.
    specs=[('FR_CAPABILITY',0x100,'read-only','Capability constant 0x46520101'),
           ('FR_STATUS',0x104,'read-only','Bits 0 enable, 1 started, 2 busy, 3 accepted, 4 retire_valid, 5 fault'),
           ('FR_ERROR',0x108,'read-only','Fence error, protocol error, and runtime-reset quarantine'),
           ('FR_SESSION',0x10c,'read-write','Write 1: cold arm once per configuration after legal generation and buffers'),
           ('FR_COMMIT_SEQ_LO',0x120,'read-write','COMMIT sequence low 32 bits'),
           ('FR_COMMIT_SEQ_HI',0x124,'read-write','COMMIT sequence high 32 bits'),
           ('FR_COMMIT_SLOT',0x128,'read-write','COMMIT slot 0..3'),
           ('FR_COMMIT',0x12c,'read-write','Write 1: generation-checked COMMIT request; read is backing register'),
           ('FR_ACCEPTED_SEQ_LO',0x140,'read-only','Accepted sequence low'),
           ('FR_ACCEPTED_SEQ_HI',0x144,'read-only','Accepted sequence high'),
           ('FR_RETIRE_SEQ_LO',0x148,'read-only','Retired sequence low'),
           ('FR_RETIRE_SEQ_HI',0x14c,'read-only','Retired sequence high'),
           ('FR_RETIRE_SLOT',0x150,'read-only','Retired slot'),
           ('FR_ACTIVE_SLOT',0x154,'read-only','Active slot'),
           ('FR_RETIRE_ACK_SEQ_LO',0x160,'read-write','RETIRE_ACK sequence low'),
           ('FR_RETIRE_ACK_SEQ_HI',0x164,'read-write','RETIRE_ACK sequence high'),
           ('FR_RETIRE_ACK',0x168,'read-write','Write 1: generation-checked RETIRE_ACK; read is backing register')]
    for i in range(4):
        specs += [(f'FR_GENERATION_{i}',0x110+4*i,'read-write','SESSION generation word; low word first'),
                  (f'FR_BUFFER_BASE_{i}',0x130+4*i,'read-write','4KiB aligned 2764800-byte frame buffer base'),
                  (f'FR_RETIRE_ACK_GENERATION_{i}',0x170+4*i,'read-write','RETIRE_ACK generation echo; low word first'),
                  (f'FR_COMMIT_GENERATION_{i}',0x180+4*i,'read-write','COMMIT generation echo; low word first')]
    block=m.find('./ADDRESSBLOCKS/ADDRESSBLOCK');assert block.get('RANGE')=='256'
    block.set('RANGE','512'); regs=block.find('REGISTERS')
    assert all(int(r.find("PROPERTY[@NAME='ADDRESS_OFFSET']").get('VALUE'),0)<0x100 for r in regs)
    for name,offset,access,desc in sorted(specs,key=lambda s:s[1]):
        reg=ET.SubElement(regs,'REGISTER',{'NAME':name})
        for k,v in [('DESCRIPTION',desc),('ADDRESS_OFFSET',hex(offset)),('SIZE','32'),('ACCESS',access),('IS_ENABLED','true')]:
            ET.SubElement(reg,'PROPERTY',{'NAME':k,'VALUE':v})
    tree.write(HWH,encoding='utf-8',xml_declaration=True)
    adapter_report=json.loads((E/'HWH_ADAPTER.json').read_text(encoding='utf-8'))
    adapter_report['adapter_step_sha256']=adapter_report['sha256']
    adapter_report['sha256']=sha(HWH)
    adapter_report['final_metadata_annotations']='125MHz source identity, routed DCP hash, actual Frame Retire register descriptions'
    save(E/'HWH_ADAPTER.json',adapter_report)
    newroot=ET.parse(HWH).getroot()
    assert '142857' not in HWH.read_text() and '142.857' not in HWH.read_text()
    assert [dict(x.attrib) for x in before.findall('./PORTS/PORT')]==[dict(x.attrib) for x in m.findall('./PORTS/PORT') if x.get('NAME')!='retire_video_resetn']
    assert [dict(x.attrib) for x in ET.parse(RAW).getroot().findall('.//MEMRANGE')]==[dict(x.attrib) for x in newroot.findall('.//MEMRANGE')]
    # Original validator's exact reset-sink test is for raw BD metadata; the
    # release adds the real custom input and must explicitly include it.
    verifier=(C/'tools/verify_hwh_integration.py').read_text(encoding='utf-8')
    assert verifier.count("assert connections==[(u,'ap_rst_n')],connections")==1
    verifier=verifier.replace("assert connections==[(u,'ap_rst_n')],connections", "assert sorted(connections)==sorted([(u,'ap_rst_n'),('/video/axi_vdma','retire_video_resetn')]),connections")
    local=W/'verify_release_hwh.py';local.write_text(verifier,encoding='utf-8')
    subprocess.run([sys.executable,str(local),str(HWH),str(E/'HWH_STATIC_CHECK.json')],check=True)
    save(R/'FRAME_RETIRE_REGISTERS.json',{'base':'0x43000000','rtl':str(C/'candidate/rtl/frame_retire_registers.sv'),
         'rtl_sha256':sha(C/'candidate/rtl/frame_retire_registers.sv'),
         'registers':[{'name':n,'offset':hex(o),'absolute_address':hex(0x43000000+o),'access':a,'description':d} for n,o,a,d in sorted(specs,key=lambda s:s[1])]})
    return hwh_binding_proof()

def hwh_binding_proof():
    return {'raw_hwh_sha256':sha(RAW),'original_adapter_sha256':sha(C/'tools/make_candidate_hwh.py'),
            'release_adapter_sha256':sha(W/'make_release_hwh.py'),'register_count_added':33,
            'public_addresses_and_existing_ports':'UNCHANGED','custom_reset_input':'retire_video_resetn',
            'custom_VLNV':'user.org:user:lab08_vdma_frame_retire:1.0',
            'metadata_only_changes':['core clock annotation derived from genuine 125MHz PS7','actual custom Frame Retire register descriptions',
                                     'local address block 0x200 bytes','routed DCP provenance and fixed design contract annotations']}

def main():
    global C, W, R, E, RAW, HWH, EXPECTED
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace', type=Path, required=True)
    a = p.parse_args()
    C = a.workspace.resolve()
    if not (C/'source_identity.json').is_file():
        raise SystemExit('Not a prepared workspace')
    R = C/'output/artifacts'
    W = C/'output/metadata'
    E = C/'output/reports'
    RAW = C/'candidate/p/u2/lab07_lab08_unified_2.srcs/sources_1/bd/base/hw_handoff/base.hwh'
    HWH = R/'rebuilt_frame_retire_fclk1_125.hwh'
    routed = C/'output/checkpoints/routed_startup.dcp'
    EXPECTED = sha(routed)
    if HWH.exists():
        raise SystemExit('Refuse to overwrite existing HWH')
    W.mkdir(parents=True, exist_ok=True)
    E.mkdir(parents=True, exist_ok=True)
    R.mkdir(parents=True, exist_ok=True)
    print(json.dumps(make_hwh(), indent=2))

if __name__ == '__main__':
    main()
