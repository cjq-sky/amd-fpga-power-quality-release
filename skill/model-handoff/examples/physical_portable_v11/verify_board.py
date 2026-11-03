"""Offline-only file/golden validation. Does not connect Reader, AWG or UI."""
import argparse
import hashlib
import json
import platform
import sys
import time
from pathlib import Path
from portable_model import PortableModel


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('Choose a new output file; existing results will not be overwritten')
    root = Path(__file__).resolve().parent
    report = dict(status='FAIL', environment=dict(python=sys.version, executable=sys.executable,
        architecture=platform.machine(), platform=platform.platform(),
        runtime_module=str(root / 'portable_model.py')), models={},
        scope='Offline TRAIN golden numerical replay; no independent classification score',
        live_service_tested=False, reader_ownership_tested=False, memory_tested=False)
    try:
        hashes = json.loads((root / 'sha256.json').read_text(encoding='utf-8'))
        for name, expected in hashes.items():
            target = (root / name).resolve()
            if not target.is_relative_to(root) or hashlib.sha256(target.read_bytes()).hexdigest() != expected:
                raise ValueError('Package file hash mismatch: ' + name)
        manifest = json.loads((root / 'deployment_manifest.json').read_text(encoding='utf-8'))
        raw = (root / 'golden.json').read_bytes()
        if hashlib.sha256(raw).hexdigest() != manifest['golden_sha256']:
            raise ValueError('Golden hash mismatch')
        golden = json.loads(raw)
        for name in ('logistic_regression', 'random_forest'):
            start = time.perf_counter()
            model = PortableModel(root, name)
            load_s = time.perf_counter() - start
            expected = golden['models'][name]
            mismatches = 0; difference = 0.0; durations = []
            if not len(golden['X']) == len(expected['predictions']) == len(expected['probabilities']) == 2496:
                raise ValueError('Golden row count mismatch')
            for x, label, probabilities in zip(golden['X'], expected['predictions'], expected['probabilities']):
                start = time.perf_counter(); actual = model.predict(x)
                durations.append(time.perf_counter() - start)
                if actual['input_status'] != 'ACCEPTED':
                    raise ValueError('Golden input rejected: ' + str(actual))
                mismatches += actual['class_id'] != label
                difference = max(difference, max(abs(a - b) for a, b in zip(actual['probabilities'], probabilities)))
            invalid = [[0] * 5, [0] * 12, [True, 0, 0, 0, 0, 1.4],
                       [float('nan'), 0, 0, 0, 0, 1.4], [float('inf'), 0, 0, 0, 0, 1.4],
                       [-1, 0, 0, 0, 0, 1.4], [0, 0, 0, 0, 0, .5], [1e300, 0, 0, 0, 0, 1.4]]
            rejected = all(model.predict(x)['input_status'] == 'REJECTED' for x in invalid)
            boundary = (model.predict(golden['X'][0], 'wrong')['input_status'] == 'REJECTED'
                        and model.predict_checked({'input_status': 'rejected'})['model_prediction'] is None)
            ordered = sorted(durations)
            report['models'][name] = dict(rows=len(durations), class_mismatches=mismatches,
                max_probability_abs_difference=difference, probability_tolerance=1e-6,
                invalid_input_checks_pass=rejected, input_boundary_checks_pass=boundary,
                load_seconds=load_s, predict_seconds_median=ordered[len(ordered)//2],
                predict_seconds_p95=ordered[int(.95*(len(ordered)-1))],
                predict_seconds_max=max(ordered), timing_scope='Python wrapper call only, not Reader/UI end-to-end',
                status='PASS' if mismatches == 0 and difference <= 1e-6 and rejected and boundary else 'FAIL')
        report['status'] = 'PASS' if all(r['status'] == 'PASS' for r in report['models'].values()) else 'FAIL'
    except Exception as exc:
        report['error'] = type(exc).__name__ + ': ' + str(exc)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['status'] == 'PASS' else 2


if __name__ == '__main__':
    sys.exit(main())
