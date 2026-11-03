"""Call B's unchanged v05 input adapter; no model weights or extra reader."""
import copy
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).with_name('b_harmonic')))
from pq.adapter import HarmonicAdapter


class HarmonicMonitor:
    def __init__(self, release, epoch, model=None):
        self.model = model
        self.adapter = HarmonicAdapter(channel='CH1', max_age_s=.5)
        self.adapter.start_session(release, epoch)
        self.epoch = list(epoch)

    def process(self, snapshot, received, now):
        data = copy.deepcopy(snapshot)
        session = data.get('session', {})
        if isinstance(session.get('epoch'), tuple):
            session['epoch'] = list(session['epoch'])
        observed = session.get('observed_at')
        eligible = (data.get('status') == 'CONSISTENT' and data.get('consistent') is True
            and data.get('snapshot_valid') is True and data.get('stale') is False
            and session.get('epoch') == self.epoch
            and type(observed) in (int, float) and math.isfinite(observed)
            and 0 <= now - observed <= .5)
        result = self.adapter.process(data, received_monotonic_s=received,
            now_monotonic_s=now, reader_eligible=eligible)
        result['source_frame_id'] = data.get('frame_id')
        result['scope'] = 'CH1 six-dimensional Adapter; candidate model result stored separately'
        if self.model is not None:
            from ui_physical import predict_result
            result = predict_result(result, self.model)
        return result
