"""UI adapter for the unchanged, previously accepted CH1 EventDetector."""
from dataclasses import asdict
import copy
from lab07_event_live import EventDetector, check_live, check_drop_change


class ChannelEventMonitor:
    def __init__(self, baseline, emit=lambda record: None):
        if baseline['channel'] not in ('CH1','CH2'):
            raise ValueError('Unsupported event channel')
        self.channel = baseline['channel']
        self.detector = EventDetector(baseline['nominal_rms_code'], baseline['fs_hz'], baseline['f0_hz'])
        self.baseline_id = baseline['baseline_id']
        self.emit, self.records, self.previous_live = emit, [], None
        self.error, self.frame_id = None, None

    def _record(self, records):
        for r in records:
            r = dict(r, channel=self.channel)
            self.emit(r)
            self.records.append(r)
        self.records = self.records[-20:]

    def stop(self, reason):
        if self.error is None:
            self.error = str(reason)
            self._record(self.detector.gap(self.error))

    def push(self, frame, before, after):
        if self.error is not None:
            return
        try:
            check_live(before); check_live(after)
            if self.previous_live is not None:
                check_drop_change(self.previous_live, before)
            check_drop_change(before, frame.drop_diagnostics)
            check_drop_change(frame.drop_diagnostics, after)
            meta = dict(epoch=frame.epoch, **asdict(frame.descriptor),
                ack_result=frame.ack_result, owner_valid=True, frame_valid=True,
                drop_diagnostics=frame.drop_diagnostics)
            records = self.detector.push(getattr(frame, self.channel), meta)
            self._record(records)
            if any(r['record']=='DATA_GAP' for r in records):
                self.error = 'Raw continuity lost; restart required, no automatic event recovery'
            self.previous_live = dict(after)
            self.frame_id = frame.descriptor.frame_id
        except Exception as exc:
            self.stop(str(exc))

    def snapshot(self):
        return copy.deepcopy(dict(status='ERROR' if self.error else self.detector.state or 'WARMUP',
            reason=self.error or '', rms_pu=None if self.error else self.detector.last_rms_pu,
            active=None if self.error or self.detector.active is None else dict(self.detector.active,channel=self.channel), frame_id=self.frame_id,
            baseline_id=self.baseline_id, nominal_rms_code=self.detector.nominal,
            records=self.records, channel=self.channel,scope=self.channel+' controlled ADC-code baseline; not calibrated voltage'))

    def finish(self):
        self._record(self.detector.finish())


class EventMonitor:
    """Two independent detectors consuming the same existing ACKed Raw copy.

    Top-level fields remain the CH1 API; channel results are in channels.
    """
    def __init__(self, baseline, emit=lambda record: None, baseline_ch2=None):
        if baseline.get('channel') != 'CH1':
            raise ValueError('Primary baseline must be CH1')
        if baseline_ch2 is not None and baseline_ch2.get('channel') != 'CH2':
            raise ValueError('Secondary baseline must be CH2')
        self.monitors = {'CH1':ChannelEventMonitor(baseline,emit)}
        if baseline_ch2 is not None:
            self.monitors['CH2'] = ChannelEventMonitor(baseline_ch2,emit)

    @property
    def error(self):
        return '; '.join(ch+': '+m.error for ch,m in self.monitors.items() if m.error) or None

    def push(self, frame, before, after):
        for monitor in self.monitors.values():
            monitor.push(frame,before,after)

    def stop(self, reason):
        for monitor in self.monitors.values():
            monitor.stop(reason)

    def snapshot(self):
        channels = {ch:m.snapshot() for ch,m in self.monitors.items()}
        channels.setdefault('CH2',dict(status='DISABLED',reason='CH2 reference not configured',rms_pu=None,active=None,records=[]))
        return dict(channels['CH1'],channels=channels)

    def finish(self):
        for monitor in self.monitors.values():
            monitor.finish()
