"""Read-only Linux environment preflight; never imports the board runtime/PYNQ."""
from pathlib import Path
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect():
    profile = json.loads((ROOT / 'board/application.json').read_text(encoding='utf-8'))
    report = dict(image_version=profile['image_version'], platform=platform.system(),
                  machine=platform.machine(), kernel=platform.release(), python=platform.python_version(),
                  checks={}, warnings=[], hardware_access=False, bit_loaded=False)
    checks = report['checks']
    if not sys.platform.startswith('linux'):
        report.update(ready_for_original_startup=False, reason='BOARD_LINUX_REQUIRED')
        return report
    env = profile['environment']
    checks['architecture'] = platform.machine() == env['machine']
    checks['kernel_release'] = platform.release() == env['kernel']
    checks['python_series'] = list(sys.version_info[:2]) == env['python_series']
    observed_versions = {}
    packages = {}
    for module_name in ['pynq', 'numpy', 'PIL']:
        spec = importlib.util.find_spec(module_name)
        packages[module_name] = Path(spec.origin).parent if spec and spec.origin else None
        checks['package_present_' + module_name] = packages[module_name] is not None
    for distribution in ['pynq', 'numpy', 'Pillow']:
        try:
            observed_versions[distribution] = importlib.metadata.version(distribution)
        except importlib.metadata.PackageNotFoundError:
            observed_versions[distribution] = None
    report['distribution_versions'] = observed_versions
    # Distribution metadata is an early hint. The original platform_guard still
    # checks actual imported versions/native identity and remains unchanged.
    for name, expected in env['recorded_versions'].items():
        if observed_versions.get(name) != expected:
            report['warnings'].append('Distribution version differs or unavailable: ' + name)
    native = sorted((packages['numpy'] / 'core').glob('_multiarray_umath*.so')) if packages['numpy'] else []
    files = {'kernel_image':Path('/boot/image.ub'), 'kernel_notes':Path('/sys/kernel/notes'),
             'pynq_mmio':packages['pynq']/'mmio.py' if packages['pynq'] else None,
             'pynq_backend':packages['pynq']/'pl_server/embedded_device.py' if packages['pynq'] else None,
             'numpy_scalar':native[0] if len(native) == 1 else None}
    report['platform_file_hashes'] = {}
    for name, path in files.items():
        try:
            value = digest(path) if path and path.is_file() else None
        except OSError:
            value = None
        report['platform_file_hashes'][name] = value
        checks['identity_' + name] = value == env['platform_sha256'][name]
    font = Path(env['chinese_font'])
    checks['chinese_font_present'] = font.is_file()
    if not Path(env['latin_font_optional']).is_file():
        report['warnings'].append('Optional Latin font absent; original renderer falls back to Chinese font')
    model_dir = Path(profile['external_model_directory'])
    for name, expected in profile['model_sha256'].items():
        try:
            checks['installed_model_' + name] = digest(model_dir/name) == expected
        except OSError:
            checks['installed_model_' + name] = False
    try:
        output = subprocess.run(['ip','-j','address','show'], capture_output=True, text=True,
                                check=True, timeout=5)
        addresses = json.loads(output.stdout)
        checks['configured_http_address'] = any(info.get('local') == profile['http']['address']
            for adapter in addresses for info in adapter.get('addr_info',[]))
    except (OSError, ValueError, subprocess.SubprocessError):
        checks['configured_http_address'] = False
    occupied = False
    tcp_read = False
    for path in [Path('/proc/net/tcp'), Path('/proc/net/tcp6')]:
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding='utf-8').splitlines()[1:]
            tcp_read = True
            occupied |= any(len(parts) > 3 and parts[3] == '0A'
                and parts[1].split(':')[-1].upper() == f"{profile['http']['port']:04X}"
                for parts in (line.split() for line in lines))
        except OSError:
            pass
    checks['http_port_not_listening'] = tcp_read and not occupied
    runtime = ROOT / profile['runtime_directory']
    checks['runtime_directory_writable'] = os.access(runtime, os.W_OK)
    boot = Path('/proc/sys/kernel/random/boot_id').read_text(encoding='utf-8').strip()
    report['boot_id'] = boot
    checks['no_previous_loader_in_this_directory_this_boot'] = not (runtime/'results'/('load_identity_'+boot+'.jsonl')).exists()
    checks['no_previous_live_owner_in_this_directory_this_boot'] = not (runtime/'results'/('live_ui4_'+boot)).exists()
    import fcntl
    for name in profile['lock_names']:
        path = Path('/tmp') / (name + '.lock')
        okay = True
        if path.exists():
            try:
                with path.open('r', encoding='utf-8') as handle:
                    okay = not handle.read().strip()
                    fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(handle, fcntl.LOCK_UN)
            except (OSError, UnicodeError):
                okay = False
        checks['lease_available_' + name] = okay
    report['ready_for_original_startup'] = all(checks.values())
    report['cold_bus_history'] = 'Requires full power cycle and known operator history; OS checks alone do not prove DMA stopped'
    report['runtime_guard'] = 'Original platform/version, MMIO, owner, epoch, ACK and buffer checks remain in the original program'
    return report


def main():
    report = collect()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report['ready_for_original_startup']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
