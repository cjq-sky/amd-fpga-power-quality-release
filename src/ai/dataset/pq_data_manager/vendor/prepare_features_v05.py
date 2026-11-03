"""Offline candidate adapter for the frozen Lab07 ABI 2.1 reader log."""
import argparse
import csv
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BIT = '085da4540128571075c287cf96e1265982d7180a219928d5995219b41e52971a'
HWH = 'e39c46c086b76020e44ce680104aa45dfc2ef747efbcb2de93dea910853cf291'
SUFFIXES = ['band_h3_pct', 'band_h5_pct', 'band_h7_pct', 'band_h9_pct', 'thd_odd_pct', 'crest']
META = ['schema_id', 'source_sha256', 'source_case', 'label', 'group_id', 'split',
        'epoch', 'frame_id', 'snapshot_seq', 'quality_json']

def require(condition, message):
    if not condition:
        raise ValueError(message)

def uint(value, bits=32):
    require(type(value) is int and 0 <= value < 2**bits, 'invalid unsigned integer')
    return value

def schema(channels):
    require(channels in ('CH1', 'CH2', 'both'), 'unknown channels')
    names = ['CH1', 'CH2'] if channels == 'both' else [channels]
    return 'lab07_band_shape_v1_candidate_' + '_'.join(names), [c + '_' + s for c in names for s in SUFFIXES]

def new_output(kind):
    path = ROOT / 'outputs' / (kind + '_' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ'))
    path.mkdir(parents=True, exist_ok=False)
    return path

def convert(snapshot, channels='both'):
    s = snapshot
    require(s['status'] == 'CONSISTENT' and s['snapshot_valid'] is True
            and s['consistent'] is True and s['stale'] is False and s['reasons'] == [], 'snapshot rejected')
    seq = uint(s['seq_before'])
    require(seq == uint(s['seq_after']), 'torn snapshot')
    elapsed = s['elapsed_s']
    require(type(elapsed) in (int, float) and math.isfinite(elapsed) and 0 <= elapsed < 1, 'unsafe read duration')
    epoch = s['session']['epoch']
    require(isinstance(epoch, list) and len(epoch) == 3 and all(isinstance(v, str) and v for v in epoch[:2]), 'invalid epoch')
    uint(epoch[2])
    raw = s['raw']
    require(uint(raw['FRAME_ID']) == uint(s['frame_id']), 'frame mismatch')
    require(uint(raw['SNAPSHOT_VALID']) == 1 and uint(raw['FEATURE_ACQUISITION_VALID']) == 1, 'acquisition invalid')
    mask = uint(raw['FEATURE_VALID_MASK'], 9)
    numeric = uint(raw['SPECTRAL_NUMERIC_STATUS'])
    formal = uint(raw['SPECTRAL_STATUS'])
    identity = uint(raw['FORMAL_IDENTITY'], 4)
    values = []
    selected = ['CH1', 'CH2'] if channels == 'both' else [channels]
    schema(channels)
    for channel in selected:
        i = int(channel[-1]) - 1
        info = s['channels'][channel]
        status = (numeric >> (16*i)) & 65535
        require(not status & 16 and info['boundary_warning'] is False, channel + ': REVIEW_REQUIRED boundary')
        require(status == 1 and uint(info['numeric_status'], 16) == status and info['numeric_valid'] is True
                and info['consumable'] is True and info['protocol_errors'] == [] and info['numeric_reasons'] == [], channel + ': numeric invalid')
        require(mask & (1 << (7+i)) and mask & (1 << (4+i)), channel + ': validity mask')
        crest = s['basic'][channel + '_CREST']
        crest_raw = uint(raw[channel + '_CREST'], 16)
        require(crest['valid'] is True and uint(crest['raw'], 16) == crest_raw, channel + ': crest invalid')
        h1 = uint(raw[channel + '_H1'])
        require(h1 > 0, channel + ': H1 zero')
        values.extend(100.0 * uint(raw[channel + '_H' + str(n)]) / h1 for n in (3, 5, 7, 9))
        values.extend([100.0 * uint(raw[channel + '_THD_ODD_3_5_7_9']) / 65536, crest_raw / 1024])
    require(all(math.isfinite(v) for v in values), 'nonfinite feature')
    return values, json.dumps(epoch, separators=(',', ':')), seq, {
        'numeric_status': numeric, 'formal_status': formal, 'formal_identity': identity,
        'feature_valid_mask': mask, 'channels': s['channels'], 'basic': s['basic'],
        'note': 'numeric feature readiness is not load identity or physical accuracy certification'}

def read_records(path):
    records = []
    for number, line in enumerate(path.read_text(encoding='utf-8-sig').splitlines(), 1):
        if not line.lstrip().startswith(('{', '[')):
            continue
        try:
            record = json.loads(line)
        except ValueError as exc:
            raise ValueError(f'malformed JSON line {number}') from exc
        require(isinstance(record, dict), f'non-object JSON line {number}')
        records.append((number, record))
    return records

def prepare(path, channels='both', output=None):
    path = Path(path)
    records = read_records(path)
    pre = [r for _, r in records if r.get('phase') == 'A_RELEASE_PREFLIGHT']
    abi = [r for _, r in records if r.get('phase') == 'D_ABI_CAPABILITY']
    require(len(pre) == len(abi) == 1, 'need exactly one release preflight and ABI record per log')
    require(pre[0]['audit']['bit_sha256'] == BIT and pre[0]['audit']['hwh_sha256'] == HWH, 'release identity mismatch')
    info = abi[0]['info']
    require((info['major'], info['minor']) == (2, 1) and info['mode'] == 'SUPPORTED'
            and info['feature']['raw'] == 0x17F and info['raw']['raw'] == 15, 'ABI/capability mismatch')
    schema_id, names = schema(channels)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    accepted, rejected, seen = [], [], set()
    last_seq = {}
    for line, record in records:
        if 'feature' not in record:
            continue
        try:
            values, epoch, seq, quality = convert(record['feature'], channels)
            key = (epoch, seq)
            require(key not in seen, 'duplicate epoch/sequence')
            require(epoch not in last_seq or seq > last_seq[epoch], 'non-increasing sequence; split reset/wrap into a new managed epoch')
            seen.add(key)
            last_seq[epoch] = seq
            row = dict(zip(names, values))
            row.update(schema_id=schema_id, source_sha256=digest, source_case=record.get('case', ''),
                       label='', group_id='', split='', epoch=epoch, frame_id=record['feature']['frame_id'],
                       snapshot_seq=seq, quality_json=json.dumps(quality, ensure_ascii=False, separators=(',', ':')))
            accepted.append(row)
        except (KeyError, TypeError, ValueError) as exc:
            rejected.append({'line': line, 'reason': str(exc)})
    require(accepted or rejected, 'no feature records')
    output = Path(output) if output else new_output('prepare')
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'features.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=META + names)
        writer.writeheader()
        writer.writerows(accepted)
    report = dict(schema_id=schema_id, feature_names=names, source_sha256=digest,
                  accepted=len(accepted), rejected=len(rejected), rejections=rejected,
                  model_trained=False, labels_inferred=False, physical_accuracy_certified=False,
                  bit_sha256=BIT, hwh_sha256=HWH,
                  limitations=['candidate schema', 'H1>0 is only a zero guard, not an SNR threshold',
                               'offline reader log; no new board run or raw-frame association claimed'])
    (output / 'prepare_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report, output

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--log', type=Path, default=ROOT / 'data' / 'combined_terminal.log')
    parser.add_argument('--channels', choices=['CH1', 'CH2', 'both'], default='both')
    args = parser.parse_args()
    try:
        report, output = prepare(args.log, args.channels)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print('Output:', output)
        return 0 if report['accepted'] and not report['rejected'] else 2
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print('ERROR:', exc)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())

