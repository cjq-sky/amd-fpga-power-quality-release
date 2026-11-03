"""Read-only AI file, model-identity and contract checks; no training or hardware."""
from pathlib import Path
import ast
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
AI = ROOT / 'src/ai'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    expected = set()
    for line in (AI / 'sha256sums').read_text(encoding='utf-8').splitlines():
        value, name = line.split('  ', 1)
        path = (AI / name).resolve()
        if not path.is_relative_to(AI.resolve()) or not path.is_file() or digest(path) != value:
            raise SystemExit('AI file identity mismatch: ' + name)
        expected.add(name)
    actual = {p.relative_to(AI).as_posix() for p in AI.rglob('*') if p.is_file()
              and not any(n in p.relative_to(AI).parts for n in ['__pycache__', 'local_data', 'reports', 'outputs'])}
    if actual != expected | {'sha256sums'}:
        raise SystemExit('AI file coverage mismatch')
    count = 0
    for path in AI.rglob('*.py'):
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path), feature_version=(3, 10))
        count += 1
    for path in AI.rglob('*.json'):
        json.loads(path.read_text(encoding='utf-8-sig'))
    contract = json.loads((AI / 'preprocessing/feature_contract.json').read_text(encoding='utf-8'))
    deploy = AI / 'models/physical_portable_v11'
    manifest = json.loads((deploy / 'deployment_manifest.json').read_text(encoding='utf-8'))
    original = AI / 'models/original_training'
    original_manifest = json.loads((original / 'model_manifest.json').read_text(encoding='utf-8'))
    for name, entry in manifest['models'].items():
        model_path = deploy / entry['file']
        if digest(model_path) != entry['sha256']:
            raise SystemExit('Deployment model identity mismatch: ' + name)
        model = json.loads(model_path.read_text(encoding='utf-8'))
        if (model['feature_order'] != contract['feature_order'] or model['input_shape'] != contract['shape']
                or model['feature_config_version'] != contract['feature_config_version']
                or model['labels'] != [x['name'] for x in contract['labels']]):
            raise SystemExit('Feature/model contract mismatch: ' + name)
        if digest(original / (name + '.joblib')) != entry['original_model_sha256']:
            raise SystemExit('Original weight identity mismatch: ' + name)
        if original_manifest['models'][name] != entry['original_model_sha256']:
            raise SystemExit('Original model manifest mismatch: ' + name)
    board = ROOT / 'board/models/physical_portable_v11'
    mapping = {'portable_model.py': AI / 'inference/portable_model.py',
               **{n: deploy / n for n in ['deployment_manifest.json', 'logistic_regression.json', 'random_forest.json']}}
    for name, source in mapping.items():
        if digest(board / name) != digest(source):
            raise SystemExit('Board model payload mismatch: ' + name)
    print(json.dumps(dict(ai_files=len(actual), python_modules=count, file_identity='PASS',
        json_contracts='PASS', frozen_model_identity='PASS', board_payload_identity='PASS',
        training='NOT_RUN', inference='NOT_RUN', hardware='NOT_RUN',
        scope='AI_FILES_AND_CONTRACTS_ONLY_NOT_SYSTEM_ACCEPTANCE')))


if __name__ == '__main__':
    main()
