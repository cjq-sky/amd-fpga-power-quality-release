"""Consume exactly one existing service result; no Reader/MMIO imports."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time

PINS = {
 'portable_model.py':'c77263ec7dbca537d4eac1a84e012b73854c9ae66fb2ff4518e7264e0e11b323',
 'deployment_manifest.json':'5516b50719be3a0e0cc170a96d72f2e7498686477fdf32a0297a9dcf38003928',
}

def load_portable(directory, algorithm):
    root = Path(directory).resolve()
    for name, expected in PINS.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest() != expected:
            raise ValueError('PORTABLE_RELEASE_HASH_MISMATCH: '+name)
    spec = importlib.util.spec_from_file_location('c_physical_portable_v11',root/'portable_model.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    model = module.PortableModel(root,algorithm)
    model.original_hash = json.loads((root/'deployment_manifest.json').read_text())['models'][algorithm]['original_model_sha256']
    return model


def predict_result(checked, model):
    result = dict(input_status='REJECTED',class_id=None,model_prediction=None,
        probabilities=None,error='ADAPTER_REJECTED',algorithm=model.algorithm,
        deployment_version='physical-portable-1.1',deployment_sha256=model.model_hash,
        original_model_sha256=model.original_hash,
        model_version='limited-scope-physical-v1-20261102',release_scope='TRAINING_ONLY',
        formal_decision=None,frame_identity=checked.get('frame_identity'))
    started = time.perf_counter()
    if checked.get('input_status') == 'accepted':
        try:
            result.update(model.predict_checked(checked))
        except Exception as exc:
            result.update(input_status='MODEL_CALL_FAILED',class_id=None,
                model_prediction=None,probabilities=None,error=type(exc).__name__+': '+str(exc))
    result['model_call_seconds'] = time.perf_counter()-started
    return dict(checked,physical_model=result)
