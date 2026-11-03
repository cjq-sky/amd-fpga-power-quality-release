"""Prepare an isolated 125 MHz PL workspace without modifying source inputs."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def reconstruct_vdma(original, recipe):
    raw = original.read_bytes()
    if sha(raw) != recipe['base_sha256']:
        raise ValueError('Installed VDMA does not match the recorded Vivado 2018.2 source')
    lines = raw.decode('utf-8').replace('\r\n', '\n').splitlines(keepends=True)
    for change in reversed(recipe['changes']):
        lines[change['start']:change['end']] = change['insert'].splitlines(keepends=True)
    result = ''.join(lines).replace('\n', '\r\n').encode('utf-8')
    if sha(result) != recipe['result_sha256']:
        raise ValueError('VDMA reconstruction hash mismatch')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--vivado-home', type=Path,
                        default=Path(os.environ['XILINX_VIVADO']) if os.environ.get('XILINX_VIVADO') else None)
    parser.add_argument('--vdma-source', type=Path, help='Optional exact, lawfully installed vendor VDMA file')
    parser.add_argument('--vendor-source', type=Path, help='Optional matching PYNQ candidate/ip/vendor tree')
    parser.add_argument('--vivado-hls', default='vivado_hls')
    parser.add_argument('--prepare-only', action='store_true', help='Prepare files; do not execute Vivado/HLS')
    args = parser.parse_args()
    out = args.output.resolve()
    source = ROOT / 'src/pl/frame_retire_125'
    if out.exists() or out == ROOT or out.is_relative_to(source.resolve()) or source.resolve().is_relative_to(out):
        raise SystemExit('Choose a new, separate output directory; existing output is never overwritten')
    vendor = args.vdma_source
    if vendor is None:
        if args.vivado_home is None:
            raise SystemExit('Use the Vivado 2018.2 command environment or specify --vivado-home')
        vendor = args.vivado_home / 'data/ip/xilinx/axi_vdma_v6_3/hdl/axi_vdma_v6_3_rfs.vhd'
    recipe = json.loads((ROOT / 'build/dependencies/frame_retire_125/vdma_patch.json').read_text(encoding='utf-8'))
    vdma = reconstruct_vdma(vendor, recipe)
    lock = json.loads((ROOT / 'build/dependencies/frame_retire_125/pynq_dependencies.json').read_text(encoding='utf-8'))
    dependency_bytes = []
    for row in lock['files']:
        if args.vendor_source:
            rel = row['upstream_path'].removeprefix('boards/ip/')
            data = (args.vendor_source / rel).read_bytes()
        else:
            url = f"https://raw.githubusercontent.com/Xilinx/PYNQ/{lock['commit']}/{row['upstream_path']}"
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
            if blob != row['git_blob_sha']:
                raise ValueError('Upstream blob mismatch: ' + row['upstream_path'])
            if row['append_lf']:
                data += b'\n'
        if sha(data) != row['baseline_sha256']:
            raise ValueError('PYNQ input hash mismatch: ' + row['upstream_path'])
        dependency_bytes.append((row['destination'], data))
    # Create output only after all external input identities have passed.
    shutil.copytree(source, out)
    # Only relocate the same immutable ROM file; no arithmetic or RTL logic edit.
    top = out / 'candidate/rtl/unified_top.sv'
    text = top.read_text(encoding='utf-8')
    reference = '"fft_ip/hann_q17.hex"'
    if text.count(reference) != 1:
        raise ValueError('Expected one relocatable Hann ROM reference')
    text = text.replace(reference, '"' + (out / 'fft_ip/hann_q17.hex').as_posix() + '"', 1)
    top.write_text(text, encoding='utf-8', newline='\n')
    (out / 'reports/preparation').mkdir(parents=True)
    (out / 'output/checkpoints').mkdir(parents=True)
    (out / 'output/reports').mkdir(parents=True)
    (out / 'output/artifacts').mkdir(parents=True)
    target = out / 'candidate/vendor_vdma/axi_vdma_v6_3_rfs.vhd'
    target.parent.mkdir(parents=True)
    target.write_bytes(vdma)
    for name, data in dependency_bytes:
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    omitted = []
    for component in (out / 'candidate/ip/vendor').rglob('component.xml'):
        tree = ET.parse(component)
        changed = False
        for parent in tree.iter():
            for child in list(parent):
                if child.tag.rsplit('}', 1)[-1] != 'file':
                    continue
                names = [n.text for n in child if n.tag.rsplit('}', 1)[-1] == 'name']
                if any(n.lower().endswith('.pdf') and not (component.parent / n).is_file() for n in names):
                    parent.remove(child)
                    changed = True
                    omitted.extend(names)
        if changed:
            tree.write(component, encoding='utf-8', xml_declaration=True)
    for name, display, description in [
        ('pixel_unpack', 'Pixel Unpack', 'Pixel Unpacking from 32-bit to 24-bit'),
        ('color_convert', 'Color Convert', 'Color conversion for 24-bit AXI video stream'),
    ]:
        cpp = (out / f'candidate/ip/vendor/hls/{name}/{name}.cpp').as_posix()
        project = (out / f'candidate/ip/generated/{name}').as_posix()
        script = out / f'scripts/generate_{name}.tcl'
        script.write_text(
            f'open_project {{{project}}}\nset_top {name}\nadd_files {{{cpp}}}\n'
            'open_solution solution1\nset_part {xc7z020clg400-1} -tool vivado\n'
            'create_clock -period 7 -name default\ncreate_clock -period 10 -name control\n'
            f'csynth_design\nexport_design -format ip_catalog -description {{{description}}} '
            f'-display_name {{{display}}}\nexit\n', encoding='utf-8')
        if not args.prepare_only:
            subprocess.run([args.vivado_hls, '-f', str(script)], cwd=out, check=True)
    status = dict(pynq_commit=lock['commit'], vdma_sha256=sha(vdma),
                  hls_generated=not args.prepare_only, omitted_optional_documents=omitted,
                  vivado_implementation='NOT_RUN', board='NOT_RUN')
    (out / 'preparation.json').write_text(json.dumps(status, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(workspace=str(out), **status), indent=2))


if __name__ == '__main__':
    main()
