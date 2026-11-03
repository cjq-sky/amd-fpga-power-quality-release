"""Read-only PL source/contract checks; never runs Vivado, HLS or board code."""
from pathlib import Path
import ast
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
PL=ROOT/'src/pl/frame_retire_125'
DEPENDENCIES=ROOT/'build/dependencies/frame_retire_125'
MANIFEST=ROOT/'build/manifests/frame_retire_125_sources.json'
SUMS=ROOT/'build/manifests/frame_retire_125_sha256sums'
PAIR={'bit':'45197bb23c05e8f8c73e4cbbced7c12ce66599a4b54a407d77fefd94a08820f4',
      'hwh':'54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f'}
DCP='51034a1528d12ee76214c58f53b33089fb280d0da81908ca9221e15c4ea22df0'
SUPPORT=['build/scripts/prepare_pl.py','build/scripts/build_pl.py','build/scripts/check_pl.py',
         'build/manifests/frame_retire_125_sources.json','docs/reproducibility/pl_source_binding.md']

def digest(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def inside(name):
    path=(ROOT/name).resolve()
    if not path.is_relative_to(ROOT.resolve()):
        raise ValueError('PL path escapes repository: '+name)
    return path

def file_set(base):
    return {p.relative_to(ROOT).as_posix() for p in base.rglob('*') if p.is_file()
            and '__pycache__' not in p.relative_to(base).parts}

def main():
    listed=set()
    for line in SUMS.read_text(encoding='utf-8').splitlines():
        value,name=line.split('  ',1)
        if name in listed:
            raise ValueError('Duplicate PL checksum path: '+name)
        listed.add(name)
        path=inside(name)
        if not path.is_file() or digest(path)!=value:
            raise ValueError('PL file identity mismatch: '+name)
    actual=file_set(PL)|file_set(DEPENDENCIES)|set(SUPPORT)
    if actual!=listed:
        raise ValueError('PL source/dependency file coverage mismatch')
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    originals=manifest['original_source_records']
    if len(originals)!=72:
        raise ValueError('Frozen original source input count mismatch')
    for row in originals:
        if digest(inside(row['path']))!=row['sha256']:
            raise ValueError('Original PL source record mismatch: '+row['path'])
    if sum(not row['derived'] for row in originals)!=67:
        raise ValueError('Original unchanged/derived source count mismatch')
    for row in manifest['integration_files']:
        if digest(inside(row['path']))!=row['sha256']:
            raise ValueError('Integrated PL support identity mismatch: '+row['path'])
    identity=json.loads((PL/'source_identity.json').read_text(encoding='utf-8'))
    profile=json.loads((ROOT/'board/application.json').read_text(encoding='utf-8'))
    for ext,value in PAIR.items():
        if identity['approved_'+ext+'_sha256']!=value or profile['pair_sha256'][ext]!=value:
            raise ValueError('PL input/approved board pair binding mismatch: '+ext)
        if digest(ROOT/('board/runtime/frame_retire_125/final_frame_retire_fclk1_125.'+ext))!=value:
            raise ValueError('Approved board file changed: '+ext)
    wanted={'fclk0_hz':100000000,'fclk1_hz':125000000,'independent_h16_hz':125000000,
            'deadline_cycles':125000000,'queue_depth':64,'approved_routed_dcp_sha256':DCP}
    if any(identity.get(k)!=v for k,v in wanted.items()):
        raise ValueError('PL clock/deadline/queue/DCP identity mismatch')
    for path in [*(PL.rglob('*.py')),*(ROOT/p for p in SUPPORT if p.endswith('.py'))]:
        ast.parse(path.read_text(encoding='utf-8-sig'),filename=str(path),feature_version=(3,10))
    references=0
    for component in PL.rglob('component.xml'):
        for node in ET.parse(component).getroot().iter():
            if node.tag.rsplit('}',1)[-1]=='name' and node.text:
                name=node.text
                if '/' in name and name.endswith(('.sv','.v','.vhd','.tcl','.xdc')):
                    if not (component.parent/name).is_file():
                        raise ValueError('Missing own IP reference: '+str(component)+':'+name)
                    references+=1
    main_sources=(PL/'lab07_scripts/main_sources_unified2.tcl').read_text(encoding='utf-8')
    lab07=re.findall(r'\[file join \$frLab07Root \{([^}]+)\}\]',main_sources)
    if len(lab07)!=27 or len(set(lab07))!=27:
        raise ValueError('Expected 27 unique direct Lab07 design sources')
    if any(not (PL/'lab07_snapshot'/name).is_file() for name in lab07):
        raise ValueError('Missing direct Lab07 design source')
    top=(PL/'candidate/rtl/unified_top.sv').read_text(encoding='utf-8')
    if top.count('"fft_ip/hann_q17.hex"')!=1:
        raise ValueError('Relocatable same-byte Hann ROM reference mismatch')
    if digest(PL/'fft_ip/hann_q17.hex')!='b0b24e611fee2b737c4e3e7436bac04501eddb63488297748c8e7e434458231e':
        raise ValueError('Hann ROM changed')
    recipe=json.loads((DEPENDENCIES/'vdma_patch.json').read_text(encoding='utf-8'))
    if recipe['base_sha256']!='a180b97756081106fc48be6531d78d044268ab9e3cb34dcc556e3f8e9ce3745a' or recipe['result_sha256']!='1d8c313b9a9e2dae981230ffbf033ef4fa7d2f30252827652d1bedb478722c08':
        raise ValueError('VDMA dependency recipe identity mismatch')
    lock=json.loads((DEPENDENCIES/'pynq_dependencies.json').read_text(encoding='utf-8'))
    if lock['commit']!='d9c752164644ebdbf7f96e4cd7d96661d1276a34' or len(lock['files'])!=25:
        raise ValueError('PYNQ dependency lock mismatch')
    forbidden={'.bit','.hwh','.dcp','.xpr','.log','.jou','.zip','.wdb'}
    if any(p.suffix.lower() in forbidden for p in PL.rglob('*') if p.is_file()):
        raise ValueError('Generated/release artifact in PL source tree')
    if (ROOT/'src/pl/unified2').exists() or (ROOT/'tools/prepare_build.py').exists() or (ROOT/'tools/build_fpga.py').exists():
        raise ValueError('Retired old PL entry still present in current source tree')
    print(json.dumps(dict(pl_files=len(actual),source_records=72,unchanged_original_sources=67,
        derived_original_sources=5,lab07_direct_sources=27,own_ip_references=references,
        checksums='PASS',source_binding='PASS',pair_binding='PASS',python310_syntax='PASS',
        dependency_recipes='PASS',vivado='NOT_RUN',hls='NOT_RUN',hardware='NOT_RUN'),ensure_ascii=False))

if __name__=='__main__':
    main()
