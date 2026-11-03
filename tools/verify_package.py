"""Offline identity/contract validation; no PYNQ import, MMIO or model execution."""
from pathlib import Path
import ast
import contextlib
import hashlib
import io
import json
import runpy
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PAIR = {'bit': '45197bb23c05e8f8c73e4cbbced7c12ce66599a4b54a407d77fefd94a08820f4',
        'hwh': '54980f765756f8dc64ade54af7969c7b96054c816a31d88ab9d2c07fbce05b6f'}
PAYLOAD_SHA = '8f771391a2f2099ffdc1359d54bd7d31b7488d1768a7b994531cf0a7f7a6ffd9'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inside(base, name):
    path = (base / name).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError('Identity path escapes its package: ' + name)
    return path


def verify_runtime():
    runtime = ROOT / 'board/runtime/frame_retire_125'
    profile = json.loads((ROOT / 'board/application.json').read_text(encoding='utf-8'))
    if profile['mode'] != 'REALTIME_FRAME_RETIRE_125' or profile['pair_sha256'] != PAIR:
        raise ValueError('Current application/frozen-pair identity mismatch')
    for extension, value in PAIR.items():
        if digest(runtime / ('final_frame_retire_fclk1_125.' + extension)) != value:
            raise ValueError('Frozen 125 MHz pair changed: ' + extension)
    payload_file = runtime / '11_payload_sha256.json'
    if digest(payload_file) != PAYLOAD_SHA or profile['payload_manifest_sha256'] != PAYLOAD_SHA:
        raise ValueError('Runtime payload manifest changed')
    payload = json.loads(payload_file.read_text(encoding='utf-8'))
    if len(payload) != 59:
        raise ValueError('Runtime payload closure mismatch')
    for name, value in payload.items():
        if digest(inside(runtime, name)) != value:
            raise ValueError('Runtime file changed: ' + name)
    deployment = json.loads((runtime / 'DEPLOYMENT_SHA256.json').read_text(encoding='utf-8'))
    actual_runtime = {p.relative_to(runtime).as_posix() for p in runtime.rglob('*') if p.is_file()
                      and not any(n in p.relative_to(runtime).parts for n in ['__pycache__','results'])}
    if len(deployment) != 64 or actual_runtime != set(deployment) | {'DEPLOYMENT_SHA256.json'}:
        raise ValueError('Frozen deployment closure mismatch')
    for name, value in deployment.items():
        if digest(inside(runtime, name)) != value:
            raise ValueError('Deployment identity mismatch: ' + name)
    for path, relative_to in [(runtime/'01_load_identity.py', runtime),
                              (runtime/'ui14_service/b_harmonic/lab07/prepare_features.py', runtime)]:
        tree = ast.parse(path.read_text(encoding='utf-8-sig'))
        observed = {}
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in {'PAIR', 'BIT', 'HWH'}:
                        observed[target.id] = ast.literal_eval(node.value)
        if path.name == '01_load_identity.py':
            if observed.get('PAIR') != PAIR:
                raise ValueError('Loader pair contract mismatch')
        elif observed.get('BIT') != PAIR['bit'] or observed.get('HWH') != PAIR['hwh']:
            raise ValueError('Online feature adapter pair mismatch')
    root = ET.parse(runtime / 'final_frame_retire_fclk1_125.hwh').getroot()
    modules = {m.get('FULLNAME'): m for m in root.findall('.//MODULE')}
    ps = {p.get('NAME'):p.get('VALUE') for p in modules['/ps7_0'].findall('./PARAMETERS/PARAMETER')}
    if ps['PCW_CLK0_FREQ'] != '100000000' or ps['PCW_CLK1_FREQ'] != '125000000':
        raise ValueError('HWH PS7 clock identity mismatch')
    if modules['/video/axi_vdma'].get('VLNV') != 'user.org:user:lab08_vdma_frame_retire:1.0':
        raise ValueError('Custom Frame Retire metadata identity mismatch')
    by_instance = {m.get('INSTANCE'):m for m in modules.values()}
    registers = [(by_instance[r.get('INSTANCE')].get('FULLNAME'), int(r.get('BASEVALUE'),0), int(r.get('HIGHVALUE'),0))
                 for m in modules.values() for r in m.findall('./MEMORYMAP/MEMRANGE') if r.get('MEMTYPE') == 'REGISTER']
    expected = {'/lab07_mmio':(0x43c00000,0x1000), '/lab07_raw':(0x43c10000,0x2000),
        '/video/axi_vdma':(0x43000000,0x10000), '/system_interrupts':(0x41800000,0x10000),
        '/video/hdmi_out/frontend/hdmi_out_hpd_video':(0x41230000,0x10000),
        '/video/hdmi_out/frontend/vtc_out':(0x43c20000,0x10000),
        '/video/hdmi_out/frontend/axi_dynclk':(0x43c30000,0x10000),
        '/video/hdmi_out/warm_reset':(0x43c40000,0x10000),
        '/video/hdmi_out/color_convert':(0x43c60000,0x10000),
        '/video/hdmi_out/pixel_unpack':(0x43c70000,0x10000)}
    if len(registers) != 10 or any(expected.get(name) != (base, high-base+1) for name,base,high in registers):
        raise ValueError('Ten public HWH register windows mismatch')
    return dict(payload_files=59, deployment_files=len(deployment), register_windows=10,
                pair='PASS', loader_and_online_adapter='PASS', hwh='PASS')


def main():
    listed = set()
    for line in (ROOT / 'SHA256SUMS').read_text(encoding='utf-8').splitlines():
        value, name = line.split('  ', 1)
        if name in listed:
            raise ValueError('Duplicate global identity path: ' + name)
        listed.add(name)
        path = inside(ROOT, name)
        if not path.is_file() or digest(path) != value:
            raise SystemExit('Global file identity mismatch: ' + name)
    actual = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('*') if p.is_file()
              and not any(n in p.relative_to(ROOT).parts for n in ['.git','.build','.venv','__pycache__'])
              and not p.relative_to(ROOT).as_posix().startswith(
                  ('board/runtime/frame_retire_125/results/','board/runtime/results/','board/runtime/board_results/'))}
    if actual != listed | {'SHA256SUMS'}:
        raise ValueError('Global file coverage mismatch')
    runtime = verify_runtime()
    python_files = 0
    for path in ROOT.rglob('*.py'):
        if any(part in path.relative_to(ROOT).parts for part in ['.git','.build','.venv','__pycache__','results','board_results']):
            continue
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path), feature_version=(3,10))
        python_files += 1
    modules = {}
    for name, script in [('ai','check_ai.py'), ('skill','check_skill.py'), ('pl','check_pl.py')]:
        namespace = runpy.run_path(str(ROOT / 'build/scripts' / script), run_name='offline_module_check')
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            namespace['main']()
        modules[name] = json.loads(buffer.getvalue())
    print(json.dumps(dict(global_file_identity='PASS', file_coverage='PASS', python310_syntax='PASS',
        python_files=python_files, mode='REALTIME_FRAME_RETIRE_125', application_entry='run.py',
        runtime=runtime, modules=modules, hardware='NOT_RUN', inference='NOT_RUN',
        fpga_build='NOT_RUN'), ensure_ascii=False))


if __name__ == '__main__':
    main()
