"""Read-only skill structure, provenance and identity checks; no example execution."""
from pathlib import Path
import ast
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
SKILLS = ROOT / 'skill'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    files = {p.relative_to(SKILLS).as_posix(): p for p in SKILLS.rglob('*') if p.is_file()
             and '__pycache__' not in p.parts}
    hashes = json.loads((SKILLS / 'sha256.json').read_text(encoding='utf-8'))
    if set(hashes) != set(files) - {'sha256.json'}:
        raise SystemExit('Skill checksum coverage mismatch')
    for name, value in hashes.items():
        if sha(files[name]) != value:
            raise SystemExit('Skill file identity mismatch: ' + name)
    for path in SKILLS.rglob('*sha256.json'):
        for name, value in json.loads(path.read_text(encoding='utf-8')).items():
            target = (path.parent / name).resolve()
            if not target.is_relative_to(path.parent.resolve()) or sha(target) != value:
                raise SystemExit('Nested skill checksum mismatch: ' + str(path) + ':' + name)
    for name, path in files.items():
        if any(not re.fullmatch(r'[a-z0-9_.-]+', part) for part in Path(name).parts
               if part not in {'README.md', 'SKILL.md'}):
            raise SystemExit('Non-portable skill name: ' + name)
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path), feature_version=(3, 10))
        if path.suffix == '.json':
            json.loads(path.read_text(encoding='utf-8-sig'))
        if path.suffix == '.md':
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
                if target.startswith(('http:', 'https:', '#')):
                    continue
                if not (path.parent / target.split('#', 1)[0]).is_file():
                    raise SystemExit('Missing skill reference: ' + name + ':' + target)
    for name in ['waveform-bin', 'capture-audit', 'model-handoff']:
        entry = (SKILLS / name / 'SKILL.md').read_text(encoding='utf-8')
        if not entry.startswith('---\n') or f'name: {name}\n' not in entry or 'description:' not in entry:
            raise SystemExit('Skill frontmatter mismatch: ' + name)
        if not (SKILLS / name / 'README.md').is_file():
            raise SystemExit('Missing skill usage README: ' + name)
    example = SKILLS / 'model-handoff/examples/physical_portable_v11'
    deploy = json.loads((example / 'deployment_manifest.json').read_text(encoding='utf-8'))
    if sha(example / 'golden.json') != deploy['golden_sha256']:
        raise SystemExit('Golden identity mismatch')
    for entry in deploy['models'].values():
        if sha(example / entry['file']) != entry['sha256']:
            raise SystemExit('Example model identity mismatch')
        if sha(example / entry['file']) != sha(ROOT / 'src/ai/models/physical_portable_v11' / entry['file']):
            raise SystemExit('Skill/AI frozen model mismatch')
    if sha(example / 'portable_model.py') != sha(ROOT / 'src/ai/inference/portable_model.py'):
        raise SystemExit('Skill/AI inference code mismatch')
    print(json.dumps(dict(skills=3, skill_files=len(files), checksums='PASS', paths='PASS',
        references='PASS', python310_syntax='PASS', frozen_models_and_golden='PASS',
        examples='NOT_RUN', inference='NOT_RUN', unit_tests='NOT_RUN', hardware='NOT_RUN')))


if __name__ == '__main__':
    main()
