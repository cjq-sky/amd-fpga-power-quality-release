import hashlib,platform,sys
from pathlib import Path
def digest(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def qualify_explicit_platform():
    import pynq, numpy, importlib
    root = Path(pynq.__file__).parent
    native = Path(importlib.import_module('numpy.core._multiarray_umath').__file__)
    files = {'pynq_mmio': root / 'mmio.py', 'pynq_backend': root / 'pl_server/embedded_device.py', 'numpy_scalar': native, 'kernel_image': Path('/boot/image.ub'), 'kernel_notes': Path('/sys/kernel/notes')}
    observed = {k: digest(p) if p.is_file() else None for k, p in files.items()}
    wanted = {'pynq_mmio': 'c9827fa71513f5e9d58022801143ca59195b55a23e73ee98bce0b98458f3321b', 'pynq_backend': '124511991cb3c0d15842344efb8621a5dd15fc0e5d8eb70d29cbfa81f398a12f', 'numpy_scalar': 'd0a044512a374d93e52629c4c15c70590cb693ba99950d8c335a10f6034c362b', 'kernel_image': '8e380cb96c2803e1d5d1c46b1f2f8e505b4c31dcf24d68da4669be7502c6bbae', 'kernel_notes': 'e62bb66d336c448af5d4350464fdccb1535323efc7da223438907e1b8257d1e5'}
    ok = observed == wanted and pynq.__version__ == '3.1.1' and (numpy.__version__ == '1.21.5') and (sys.version_info[:2] == (3, 10)) and (platform.machine() == 'armv7l') and (platform.release() == '6.6.10-xilinx-v2024.1-g3c0eca68c652')
    return dict(scope='REVALIDATE_EXISTING_20261024_EXPLICIT_PATH_ONLY', source_hashes=observed, expected_hashes=wanted, pynq=pynq.__version__, numpy=numpy.__version__, kernel=platform.release(), machine=platform.machine(), explicit_platform_qualified=ok, limitation='No new PTE readback, DSB proof, SLVERR injection or mapped-copy acceptance')
