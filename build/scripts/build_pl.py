"""Build a prepared, isolated workspace; never replaces approved board firmware."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import subprocess
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True)
    parser.add_argument('--vivado', default='vivado')
    parser.add_argument('--plan', action='store_true', help='Show commands; do not execute tools')
    args = parser.parse_args()
    work = args.workspace.resolve()
    if not (work / 'source_identity.json').is_file():
        raise SystemExit('Not a prepared 125 MHz workspace')
    state = json.loads((work / 'preparation.json').read_text(encoding='utf-8'))
    commands = [
        [args.vivado, '-mode', 'batch', '-source', str(work / 'candidate/tcl/build_unified2.tcl'),
         '-log', str(work / 'output/prepare.log'), '-journal', str(work / 'output/prepare.jou')],
        [args.vivado, '-mode', 'batch', '-source', str(work / 'scripts/implement.tcl'),
         '-log', str(work / 'output/implement.log'), '-journal', str(work / 'output/implement.jou')],
        [sys.executable, '-B', str(work / 'scripts/make_hwh.py'), '--workspace', str(work)],
    ]
    if args.plan:
        print(json.dumps(dict(commands=commands, hls_ready=state['hls_generated'], execution='NOT_RUN'), indent=2))
        return
    if not state['hls_generated']:
        raise SystemExit('HLS not generated; prepare again into a NEW directory without --prepare-only')
    if (work / 'candidate/p').exists() or any((work / 'output').glob('*.log')):
        raise SystemExit('Workspace has previous build results; preserve them and use a new workspace')
    env = dict(os.environ, PQ_BUILD_PYTHON=sys.executable)
    for command in commands:
        subprocess.run(command, cwd=work, env=env, check=True)
    artifacts = work / 'output/artifacts'
    rows = [dict(path=p.name, sha256=hashlib.sha256(p.read_bytes()).hexdigest())
            for p in sorted(artifacts.glob('rebuilt_frame_retire_fclk1_125.*'))]
    if {r['path'].rsplit('.', 1)[-1] for r in rows} != {'bit', 'hwh'}:
        raise SystemExit('Missing rebuilt BIT/HWH')
    (artifacts / 'rebuilt_identity.json').write_text(json.dumps(dict(
        status='NEW_BUILD_REQUIRES_REVIEW_NOT_APPROVED_FOR_BOARD', files=rows,
        board='NOT_RUN', external_io_signoff='OPEN'), indent=2) + '\n', encoding='utf-8')
    print('New artifacts:', artifacts, '; board approval and interface review remain separate')


if __name__ == '__main__':
    main()
