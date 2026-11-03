"""Immutable copy of 14-version DisplayState.view(); no Reader/model/MMIO calls."""
from dataclasses import dataclass
import json
import math
import time

NAMES = ('CLEAN', 'H3_DOMINANT', 'H5_DOMINANT', 'MIXED')


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def model_allowed(s):
    h = s.get('harmonic') or {}
    m = h.get('physical_model') or {}
    identity = h.get('frame_identity')
    probabilities = m.get('probabilities')
    cid = m.get('class_id')
    age = h.get('display_age_s')
    return (s.get('status') == 'LIVE' and h.get('input_status') == 'accepted'
            and finite(age) and 0 <= age <= .5
            and isinstance(identity, dict) and identity == m.get('frame_identity')
            and identity.get('frame_id') == h.get('source_frame_id') == s.get('frame_id')
            and h.get('feature_config_version') == 'lab07-harmonic-6d-0.1'
            and m.get('input_status') == 'ACCEPTED' and type(cid) is int and 0 <= cid < 4
            and m.get('model_prediction') == NAMES[cid]
            and isinstance(probabilities, list) and len(probabilities) == 4
            and all(finite(v) and 0 <= v <= 1 for v in probabilities)
            and abs(sum(probabilities) - 1) <= 1e-6)


@dataclass(frozen=True)
class DisplaySnapshot:
    payload: str
    captured_at: float
    source_note: str

    @classmethod
    def capture(cls, view, *, now=None, source_note='实时快照'):
        now = time.monotonic() if now is None else now
        if not isinstance(view, dict) or not finite(now):
            raise ValueError('DisplayState.view() dict and finite monotonic time required')
        return cls(json.dumps(view, ensure_ascii=False, allow_nan=False), now, source_note)

    def view(self, *, now=None):
        now = time.monotonic() if now is None else now
        elapsed = now - self.captured_at
        if not finite(now) or elapsed < 0:
            raise ValueError('Invalid monotonic snapshot age')
        s = json.loads(self.payload)
        def expired(obj, key, limit):
            age = obj.get(key)
            if finite(age):
                obj[key] = age + elapsed
                return age < 0 or obj[key] > limit
            return True
        if expired(s, 'age_s', 3) or s.get('status') != 'LIVE':
            s['metrics'] = {}
            if s.get('status') == 'LIVE':
                s['status'] = 'STALE'
        wave = s.setdefault('waveform', {})
        if expired(wave, 'age_s', 3) or wave.get('status') != 'LIVE':
            wave.pop('CH1', None); wave.pop('CH2', None)
            if wave.get('status') == 'LIVE':
                wave['status'] = 'STALE'
        event = s.setdefault('event', {})
        if expired(event, 'age_s', 3):
            for item in [event, *event.get('channels', {}).values()]:
                item.update(status='ERROR' if item.get('status') == 'ERROR' else 'STALE', rms_pu=None, active=None)
        harmonic = s.setdefault('harmonic', {})
        if expired(harmonic, 'display_age_s', .5) or s.get('status') != 'LIVE':
            harmonic.update(input_status='rejected', features=None, error_code='STALE_INPUT')
        s['model_display_valid'] = bool(model_allowed(s))
        # Preserve raw/feature association and all original identities; never infer a match.
        s['snapshot_source_note'] = self.source_note
        return s
