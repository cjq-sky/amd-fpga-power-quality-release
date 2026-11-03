"""Offline dataset workflow: import, review, freeze, audit and release.

Labels and split assignments are supplied by reviewers, never inferred from models.
"""
import argparse
import csv
import hashlib
import io
import json
import shutil
import tarfile
from pathlib import Path, PurePosixPath

from register import identifier
from vendor.prepare_features_v05 import convert, BIT, HWH
from vendor.readiness import formal_preflight, interval_label, LABELS, ORDER

VERSION = 'pq-data-manager-0.2.1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def safe_file(root, name):
    root = Path(root).resolve()
    p = (root / name).resolve()
    require(p.is_relative_to(root) and p.is_file(), 'Missing or unsafe evidence: ' + str(name))
    return p


def new_output(output, protected=()):
    output = Path(output).resolve()
    require(not output.exists(), 'Output exists')
    for root in protected:
        root = Path(root).resolve()
        require(not output.is_relative_to(root), 'Output must be outside input evidence')
    return output


def verify(rows, root):
    seen = set()
    cached = {}
    for r in rows:
        require(r['record_id'] not in seen, 'Duplicate record_id')
        seen.add(r['record_id'])
        require(bool(r.get('evidence_files')), 'No evidence')
        for ref in r['evidence_files']:
            p = safe_file(root, ref['path'])
            if p not in cached:
                cached[p] = sha(p)
            require(cached[p] == ref['sha256'], 'Evidence hash mismatch: ' + ref['path'])
    return cached


def preflight(rows, policy, approval, root):
    report = formal_preflight(rows, policy, approval, root)
    scope = policy.get('release_scope', 'TRAIN_VALIDATION_TEST')
    if scope == 'TRAINING_ONLY':
        # A scoped training release does not claim validation/test coverage.
        report['issues'] = [s for s in report['issues'] if s not in
            ('MISSING_CLASS_COVERAGE:validation', 'MISSING_CLASS_COVERAGE:test_internal')]
        if any(r['split_role'] != 'train' for r in rows):
            report['issues'].append('TRAINING_ONLY_REQUIRES_TRAIN_ROWS')
    elif scope != 'TRAIN_VALIDATION_TEST':
        report['issues'].append('UNKNOWN_RELEASE_SCOPE')
    report.update(release_scope=scope, formal_training_permitted=not report['issues'],
                  status='BLOCKED' if report['issues'] else 'READY',
                  independent_test_claim=scope == 'TRAIN_VALIDATION_TEST' and not report['issues'])
    return report


def import_run(archive, binding, evidence_root, output):
    """Read C joint_cycle tar.gz, preserving original runtime association."""
    import numpy as np
    b = read(binding)
    for k in ('run_id', 'waveform_id', 'lineage_group_id'):
        identifier(b[k])
    require(b['origin_role'] in ('calibration_dev', 'prospective'), 'Explicit origin_role required')
    require(type(b['used_for_development']) is bool, 'Explicit historical use required')
    output = new_output(output, (evidence_root,))
    inputs = []
    for role in ('source', 'reference'):
        for ref in b.get(role + '_files', []):
            p = safe_file(evidence_root, ref['path'])
            require(sha(p) == ref['sha256'], 'Binding hash mismatch')
            inputs.append((role, p, ref['sha256']))
    require(any(role == 'source' for role, _, _ in inputs), 'Source evidence required')
    payload = {}
    with tarfile.open(archive, 'r:gz') as tar:
        for m in tar:
            name = PurePosixPath(m.name)
            require(not name.is_absolute() and '..' not in name.parts and ':' not in m.name
                    and '\\' not in m.name, 'Unsafe tar member')
            require(m.isdir() or m.isfile(), 'Links and special tar members rejected')
            if m.isfile():
                require(m.name not in payload, 'Duplicate tar member')
                require(m.size <= 64 * 1024 * 1024, 'Oversized run member')
                payload[m.name] = tar.extractfile(m).read()
    def unique(suffix):
        names = [n for n in payload if PurePosixPath(n).name == suffix]
        require(len(names) == 1, 'Missing/ambiguous ' + suffix)
        return names[0]
    log_name = unique('records.jsonl')
    summary = json.loads(payload[unique('summary.json')])
    release = summary['session_context']['release']
    require(release['bit_sha256'] == BIT and release['hwh_sha256'] == HWH,
            'Unsupported firmware release')
    require(release.get('verified_by_reader') is True, 'No historical reader release evidence')
    require(summary['feature_config_version'] == 'lab07-harmonic-6d-0.1', 'Feature version')
    records = []
    rejected = []
    last = None
    for line, text in enumerate(payload[log_name].decode('utf-8-sig').splitlines(), 1):
        r = json.loads(text)
        if r.get('record') != 'joint_cycle':
            continue
        if r.get('quarantined') is not False:
            rejected.append(dict(line=line, reason='QUARANTINED_OR_UNSPECIFIED'))
            continue
        try:
            values, epoch, seq, _ = convert(r['feature_snapshot'], 'CH1')
            raw = r['raw']; identity = r['pq']['frame_identity']
            require(r['pq']['adapter_version'] == 'lab07-harmonic-adapter-0.5', 'Adapter version')
            require(raw['frame_id'] == r['feature_snapshot']['frame_id'] == identity['frame_id'], 'Frame mismatch')
            require(raw['epoch'] == identity['epoch'] == json.loads(epoch)
                    == summary['session_context']['epoch'], 'Epoch mismatch')
            require(identity['snapshot_seq'] == seq, 'Snapshot identity mismatch')
            require(raw['ack_result'] == 1 and raw['owner_valid'] is True
                    and raw['frame_valid'] is True, 'Raw validity')
            require(last is None or (raw['frame_id'] == last[0] + 1 and raw['token'] == last[1] + 1
                    and seq > last[2] and raw['drop_diagnostics']['RAW_DROP_COUNT'] == last[3]), 'Continuity/drop mismatch')
            for live in (r['live_before'], r['live_after']):
                for key, value in live.items():
                    if key in ('ACQUISITION_FAULT', 'ACQUISITION_FAULT_CODE') or key.endswith(('_ERROR_STICKY', '_PROTOCOL_STICKY', '_TOKEN_EXHAUSTED_STICKY')):
                        require(value == 0, 'Acquisition fault: ' + key)
            name = unique(PurePosixPath(r['raw_file']).name)
            with np.load(io.BytesIO(payload[name]), allow_pickle=False) as a:
                words = a['words']
                require(words.dtype == np.dtype('uint32') and words.shape == (2048,), 'Raw words format')
                require(a['CH1'].dtype == a['CH2'].dtype == np.dtype('int16'), 'Raw channel dtype')
                require(np.array_equal((words & 65535).astype('uint16').view('int16'), a['CH1'])
                        and np.array_equal((words >> 16).astype('uint16').view('int16'), a['CH2']), 'Raw decode mismatch')
                require(json.loads(str(a['metadata'].item())) == raw, 'NPZ metadata mismatch')
            expected = [r['pq']['features'][k] for k in ('CH1_band_h3_pct', 'CH1_band_h5_pct',
                        'CH1_band_h7_pct', 'CH1_band_h9_pct', 'CH1_thd_odd_pct', 'CH1_crest')]
            require(values == expected, 'Stored six differs from actual v05 conversion')
            last = (raw['frame_id'], raw['token'], seq, raw['drop_diagnostics']['RAW_DROP_COUNT'])
            records.append(dict(record_id=b['run_id'] + ':' + str(raw['frame_id']), run_id=b['run_id'],
                waveform_id=b['waveform_id'], lineage_group_id=b['lineage_group_id'], features=values,
                intended_use=b.get('intended_use', 'historical_development'),
                epoch=raw['epoch'], frame_id=raw['frame_id'], snapshot_seq=seq,
                runtime_association=raw['association'], offline_pair_identity_verified=True,
                origin_role=b['origin_role'], split_role='calibration_dev', used_for_development=b['used_for_development'],
                source_type='awg_replay_parametric', source_sha256=b['source_files'][0]['sha256'],
                raw_sha256=hashlib.sha256(payload[name]).hexdigest(),
                feature_sha256=digest(r['feature_snapshot']), feature_log_line=line,
                session_id=epoch, device_id=b.get('device_id', 'unknown'), bit_sha256=BIT, hwh_sha256=HWH,
                feature_config_version='lab07-harmonic-6d-0.1', adapter_version='lab07-harmonic-adapter-0.5',
                source_label=None, label_status='UNRESOLVED', sample_status='DEVELOPMENT_ONLY', training_eligible=False))
        except (KeyError, ValueError, TypeError) as exc:
            rejected.append(dict(line=line, reason=str(exc)))
    require(records, 'No valid frames')
    output.mkdir(parents=True)
    refs = []
    for name, data in payload.items():
        target = output / 'originals' / name
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(data)
        refs.append(dict(path=target.relative_to(output).as_posix(), sha256=hashlib.sha256(data).hexdigest()))
    for index, (role, path, h) in enumerate(inputs):
        target = output / 'evidence' / (str(index) + '_' + path.name)
        target.parent.mkdir(exist_ok=True); shutil.copyfile(path, target)
        refs.append(dict(path=target.relative_to(output).as_posix(), sha256=h, role=role))
    save(output / 'binding.json', b)
    refs.append(dict(path='binding.json', sha256=sha(output / 'binding.json')))
    for row in records:
        row['evidence_files'] = refs
    save(output / 'manifest.json', records)
    report = dict(version=VERSION, accepted=len(records), rejected=rejected,
                  archive_sha256=sha(archive), adapter_sha256=sha(Path(__file__).parent / 'vendor/prepare_features_v05.py'),
                  formal_training_permitted=False, runtime_association_unchanged=True)
    save(output / 'import_report.json', report)
    verify(records, output)
    return report


def review_template(manifest, output):
    rows = read(manifest)
    save(output, dict(version=1, manifest_sha256=digest(rows), reviewer=None, decision_reference=None,
                     decisions=[dict(record_id=r['record_id'], source_label=None, sample_status='PENDING_REVIEW',
                     independent_label_evidence=[], lower_pct=None, upper_pct=None, source_identity_verified=False,
                     scope_verified=False, h1_reliability_verified=False) for r in rows]))


def collect(imports, output):
    """Combine validated run imports into one portable evidence root."""
    output = new_output(output, imports)
    rows = []; copies = []; identities = set(); raw_hashes = set()
    for index, directory in enumerate(imports):
        directory = Path(directory)
        rr = read(directory / 'manifest.json'); checked = verify(rr, directory)
        prefix = 'run_' + str(index)
        for r in rr:
            identity = (json.dumps(r['epoch']), r['frame_id'])
            require(identity not in identities and r['raw_sha256'] not in raw_hashes,
                    'Duplicate physical frame across imports')
            identities.add(identity); raw_hashes.add(r['raw_sha256'])
            refs = [dict(ref, path=prefix + '/' + ref['path']) for ref in r['evidence_files']]
            rows.append(dict(r, evidence_files=refs))
        copies.extend((p, prefix + '/' + p.relative_to(directory.resolve()).as_posix()) for p in checked)
    require(rows and len({r['record_id'] for r in rows}) == len(rows), 'Empty or duplicate record IDs')
    output.mkdir(parents=True)
    for source, relative in copies:
        target = output / relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    save(output / 'manifest.json', rows)
    report = dict(frames=len(rows), runs=len(imports), lineages=len({r['lineage_group_id'] for r in rows}),
                  unreviewed=sum(r['label_status'] != 'VERIFIED' for r in rows),
                  formal_training_permitted=False)
    save(output / 'collection_report.json', report); verify(rows, output)
    return report


def index_batch(package, output):
    """Check a v0.2.1 generator delivery and prepare explicit Run bindings."""
    package = Path(package).resolve(); output = new_output(output, (package,))
    rows = read(package / '采集清单.json'); seen = set(); bindings = []
    for r in rows:
        identifier(r['waveform_id']); identifier(r['lineage_group_id'])
        require(r['waveform_id'] not in seen, 'Duplicate waveform ID'); seen.add(r['waveform_id'])
        require(r['section'] in ('training_candidates', 'event_tests', 'boundary_scope_tests'), 'Unknown use')
        for field, hash_field in (('source_path', 'source_sha256'), ('bin_path', 'bin_sha256')):
            require(sha(safe_file(package, r[field])) == r[hash_field], 'Candidate hash mismatch')
        bindings.append(dict(run_id='FILL_ACTUAL_RUN_ID', waveform_id=r['waveform_id'],
            lineage_group_id=r['lineage_group_id'], origin_role='calibration_dev', used_for_development=True,
            device_id='unknown', intended_use=r['section'], source_files=[
                dict(path=r['source_path'], sha256=r['source_sha256']),
                dict(path=r['bin_path'], sha256=r['bin_sha256'])], reference_files=[]))
    require(bool(bindings), 'Empty batch')
    output.mkdir(parents=True)
    for b in bindings:
        save(output / (b['waveform_id'] + '_binding.json'), b)
    report = dict(waveforms=len(rows), source_and_bin_hash_checks='PASS', counts={
        role: sum(r['section'] == role for r in rows) for role in
        ('training_candidates', 'event_tests', 'boundary_scope_tests')}, formal_training_permitted=False)
    save(output / 'batch_report.json', report)
    return report


def apply_review(manifest, review, policy, root, output):
    rows = read(manifest); rv = read(review); p = read(policy)
    output = new_output(output, (root,)); verify(rows, root)
    require(rv['manifest_sha256'] == digest(rows), 'Stale review: manifest changed')
    require(rv.get('reviewer') and rv.get('decision_reference') and type(rv.get('version')) is int
            and rv['version'] > 0, 'Review identity/version/provenance required')
    decisions = {d['record_id']: d for d in rv['decisions']}
    require(len(decisions) == len(rv['decisions']) and set(decisions) == {r['record_id'] for r in rows}, 'Review coverage differs')
    result = []
    for r in rows:
        d = decisions[r['record_id']]
        status = d['sample_status']
        require(status in ('PENDING_REVIEW', 'DEVELOPMENT_ONLY', 'ACCEPTED', 'BOUNDARY', 'OUT_OF_SCOPE', 'INVALID'), 'Sample status')
        accepted = status == 'ACCEPTED'
        if accepted:
            require(r.get('intended_use') not in ('event_tests', 'boundary_scope_tests'),
                    'Event/scope challenge records are excluded from four-class training')
            require(p.get('status') == 'APPROVED_PHYSICAL', 'Physical policy not approved')
            require(d['source_label'] in LABELS, 'Unknown label')
            label, state = interval_label(d['lower_pct'], d['upper_pct'], p)
            require(state == 'CLASSIFIED' and label == d['source_label'], 'Reference intervals disagree with label')
            require(all(d.get(k) is True for k in ('source_identity_verified', 'scope_verified', 'h1_reliability_verified')), 'Review qualification incomplete')
            evidence = {e['sha256'] for e in r['evidence_files'] if e.get('role') == 'reference'}
            require(bool(d['independent_label_evidence']) and set(d['independent_label_evidence']) <= evidence,
                    'Independent reference must name hashed reference evidence')
        result.append(dict(r, source_label=d['source_label'] if accepted else None,
            label_status='VERIFIED' if accepted else 'UNRESOLVED', sample_status=status, training_eligible=accepted,
            independent_label_evidence=d.get('independent_label_evidence', []),
            source_identity_verified=d.get('source_identity_verified') is True,
            scope_verified=d.get('scope_verified') is True, h1_reliability_verified=d.get('h1_reliability_verified') is True,
            label_spec_version=p.get('label_spec_version'), review_sha256=sha(review), policy_sha256=digest(p)))
        result[-1]['review_audit'] = dict(version=rv['version'], reviewer=rv['reviewer'],
            decision_reference=rv['decision_reference'], source_manifest_sha256=rv['manifest_sha256'], decision=d)
    output.mkdir(parents=True)
    save(output / 'reviewed_manifest.json', result)
    save(output / 'review_receipt.json', dict(review=rv, review_file_sha256=sha(review), policy=p,
                                           evidence_root=str(Path(root).resolve()), original_manifest_sha256=digest(rows)))
    return dict(rows=len(rows), accepted=sum(r['training_eligible'] for r in result))


def freeze(manifest, splits, policy, root, output):
    rows = read(manifest); allocations = read(splits); p = read(policy)
    output = new_output(output, (root,)); verify(rows, root)
    require(rows and all(r.get('training_eligible') is True for r in rows), 'Select reviewed ACCEPTED records before freeze')
    groups = {r['lineage_group_id'] for r in rows}
    require(set(allocations) == groups, 'Split map must cover exactly the selected lineages')
    require(set(allocations.values()) <= {'train', 'validation', 'test_internal'}, 'Unsupported split')
    frozen = [dict(r, split_role=allocations[r['lineage_group_id']]) for r in rows]
    require(all(r.get('policy_sha256') == digest(p) for r in frozen), 'Review policy changed')
    # Approval is supplied later, against this exact frozen manifest.
    report = preflight(frozen, p, None, root)
    output.mkdir(parents=True)
    save(output / 'manifest.json', frozen); save(output / 'policy.json', p)
    save(output / 'split_map.json', allocations); save(output / 'preflight.json', report)
    save(output / 'approval_template.json', dict(approved=False, policy_sha256=digest(p),
         manifest_sha256=digest(frozen), decision_reference=None))
    return report


def export_dataset(manifest, policy, approval, root, output):
    rows = read(manifest); p = read(policy); a = read(approval)
    output = new_output(output, (root,)); verify(rows, root)
    require(all(r.get('policy_sha256') == digest(p) for r in rows), 'Review policy changed')
    report = preflight(rows, p, a, root)
    require(report['formal_training_permitted'], 'Release blocked: ' + '; '.join(report['issues']))
    output.mkdir(parents=True)
    copied = set()
    for row in rows:
        for ref in row['evidence_files']:
            if ref['path'] in copied:
                continue
            source = safe_file(root, ref['path']); target = output / 'evidence' / ref['path']
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(source, target)
            copied.add(ref['path'])
    save(output / 'manifest.json', rows); save(output / 'policy.json', p); save(output / 'approval.json', a)
    save(output / 'review_audit.json', [dict(record_id=r['record_id'], review_sha256=r.get('review_sha256'),
         audit=r.get('review_audit')) for r in rows])
    save(output / 'preflight.json', report)
    with (output / 'features.csv').open('x', encoding='utf-8-sig', newline='') as stream:
        w = csv.writer(stream); w.writerow(['record_id', 'lineage_group_id', 'split_role', 'source_label'] + list(ORDER))
        for r in rows:
            w.writerow([r[k] for k in ('record_id', 'lineage_group_id', 'split_role', 'source_label')] + r['features'])
    # Features are unscaled. The training program fits preprocessing on train only.
    save(output / 'dataset_contract.json', dict(version=VERSION, feature_order=ORDER,
         labels=LABELS, preprocessing='unscaled; fit on train only', evidence_root='evidence',
         manifest_sha256=digest(rows), policy_sha256=digest(p), golden_rows=rows[:min(32, len(rows))]))
    verify(rows, output / 'evidence')
    save(output / 'SHA256.json', {f.relative_to(output).as_posix(): sha(f)
                               for f in sorted(output.rglob('*')) if f.is_file()})
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('index-batch', 'import-run', 'collect', 'review-template', 'review', 'freeze', 'export'):
        p = sub.add_parser(name); p.add_argument('--output', type=Path, required=True)
        if name == 'index-batch':
            p.add_argument('--package', type=Path, required=True)
        elif name == 'collect':
            p.add_argument('--imports', type=Path, nargs='+', required=True)
        elif name == 'import-run':
            p.add_argument('--archive', type=Path, required=True); p.add_argument('--binding', type=Path, required=True)
        else:
            p.add_argument('--manifest', type=Path, required=True)
        if name in ('import-run', 'review', 'freeze', 'export'):
            p.add_argument('--evidence-root', type=Path, required=True)
        if name in ('review', 'freeze', 'export'):
            p.add_argument('--policy', type=Path, required=True)
        if name == 'review': p.add_argument('--review', type=Path, required=True)
        if name == 'freeze': p.add_argument('--splits', type=Path, required=True)
        if name == 'export': p.add_argument('--approval', type=Path, required=True)
    a = parser.parse_args()
    try:
        if a.command == 'import-run': result = import_run(a.archive, a.binding, a.evidence_root, a.output)
        elif a.command == 'index-batch': result = index_batch(a.package, a.output)
        elif a.command == 'collect': result = collect(a.imports, a.output)
        elif a.command == 'review-template': result = review_template(a.manifest, a.output)
        elif a.command == 'review': result = apply_review(a.manifest, a.review, a.policy, a.evidence_root, a.output)
        elif a.command == 'freeze': result = freeze(a.manifest, a.splits, a.policy, a.evidence_root, a.output)
        else: result = export_dataset(a.manifest, a.policy, a.approval, a.evidence_root, a.output)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError) as exc:
        parser.exit(2, str(exc) + '\n')


if __name__ == '__main__':
    main()
