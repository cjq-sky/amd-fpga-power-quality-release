"""CH1 six-feature LR/RF inference. Python 3.10+, standard library only."""
import hashlib
import json
import math
import struct
from pathlib import Path

VERSION = 'physical-portable-1.1'
FEATURE_VERSION = 'lab07-harmonic-6d-0.1'
KEYS = ['CH1_band_h3_pct', 'CH1_band_h5_pct', 'CH1_band_h7_pct',
        'CH1_band_h9_pct', 'CH1_thd_odd_pct', 'CH1_crest']


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


class PortableModel:
    def __init__(self, directory, algorithm):
        root = Path(directory)
        manifest = json.loads((root / 'deployment_manifest.json').read_text(encoding='utf-8'))
        if algorithm not in ('logistic_regression', 'random_forest'):
            raise ValueError('Unknown algorithm')
        entry = manifest['models'][algorithm]
        raw = (root / entry['file']).read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry['sha256']:
            raise ValueError('Deployment model hash mismatch')
        m = json.loads(raw)
        if (m['algorithm'] != algorithm or m['input_shape'] != [6]
                or m['feature_config_version'] != FEATURE_VERSION
                or m['classes'] != [0, 1, 2, 3]):
            raise ValueError('Model contract mismatch')
        self.model = m
        self.algorithm = algorithm
        self.model_hash = entry['sha256']

    def predict(self, features, feature_config_version=FEATURE_VERSION):
        result = dict(algorithm=self.algorithm, model_version=self.model['model_version'],
                      deployment_version=VERSION, deployment_sha256=self.model_hash,
                      input_status='REJECTED', class_id=None, model_prediction=None,
                      probabilities=None, error=None, release_scope='TRAINING_ONLY')
        if feature_config_version != FEATURE_VERSION:
            result['error'] = 'INPUT_VERSION_MISMATCH'; return result
        if not isinstance(features, (list, tuple)) or len(features) != 6:
            result['error'] = 'EXPECTED_SIX_FEATURES'; return result
        if any(type(v) not in (int, float) or not math.isfinite(v) for v in features):
            result['error'] = 'NONFINITE_OR_NONNUMERIC'; return result
        try:
            x = [f32(v) for v in features]
            if not all(math.isfinite(v) for v in x):
                raise ValueError('FLOAT32_OVERFLOW')
            if any(v < 0 for v in x) or x[-1] < 1:
                raise ValueError('INVALID_FEATURE_RANGE')
            m = self.model
            if self.algorithm == 'logistic_regression':
                # Match sklearn float32 StandardScaler in-place subtract/divide.
                z = [f32(f32(v - mean) / scale)
                     for v, mean, scale in zip(x, m['mean'], m['scale'])]
                if not all(math.isfinite(v) for v in z):
                    raise ValueError('PREPROCESS_OVERFLOW')
                logits = [sum(a * b for a, b in zip(row, z)) + bias
                          for row, bias in zip(m['coef'], m['intercept'])]
                e = [math.exp(v - max(logits)) for v in logits]
                probs = [v / sum(e) for v in e]
            else:
                probs = [0.0] * 4
                for tree in m['trees']:
                    node = 0
                    while tree['left'][node] != -1:
                        node = (tree['left'][node] if x[tree['feature'][node]] <= tree['threshold'][node]
                                else tree['right'][node])
                    values = tree['value'][node]
                    total = sum(values)
                    if total <= 0:
                        raise ValueError('INVALID_LEAF')
                    for k in range(4):
                        probs[k] += values[k] / total
                probs = [v / len(m['trees']) for v in probs]
            if not all(math.isfinite(v) and 0 <= v <= 1 for v in probs):
                raise ValueError('INVALID_PROBABILITY')
            k = max(range(4), key=probs.__getitem__)
            result.update(input_status='ACCEPTED', class_id=k,
                          model_prediction=m['labels'][k], probabilities=probs)
        except (ValueError, OverflowError, struct.error) as exc:
            result['error'] = str(exc)
        return result

    def predict_checked(self, checked):
        """Read an already checked Adapter result; never changes Reader/session state."""
        if checked.get('input_status') != 'accepted':
            return dict(input_status='REJECTED', model_prediction=None, error='ADAPTER_REJECTED')
        if checked.get('schema_id') != 'lab07_band_shape_v1_candidate_CH1':
            return dict(input_status='REJECTED', model_prediction=None, error='SCHEMA_MISMATCH')
        if not checked.get('frame_identity'):
            return dict(input_status='REJECTED', model_prediction=None, error='MISSING_FRAME_IDENTITY')
        try:
            values = [checked['features'][k] for k in KEYS]
        except (KeyError, TypeError):
            return dict(input_status='REJECTED', model_prediction=None, error='MISSING_FEATURE')
        result = self.predict(values, checked.get('feature_config_version'))
        result['frame_identity'] = checked['frame_identity']
        return result
