"""Standard-library-only board integration. No MMIO, ACK or model inference."""
import math
from .prepare_features import convert, schema, BIT, HWH
from .contract import VERSION, PURPOSE

ADAPTER_VERSION = 'lab07-board-adapter-0.3'

def forward_u32(current, previous):
    delta = (current - previous) & 0xffffffff
    return 0 < delta < 0x80000000

class BoardAdapter:
    """Single reader/serial caller. start_session only after C verifies release/epoch."""
    def __init__(self, *, channels='both', max_age_s):
        self.schema_id, self.names = schema(channels)
        if type(max_age_s) not in (int, float) or not math.isfinite(max_age_s) or max_age_s <= 0:
            raise ValueError('max_age_s must be an explicit positive local integration limit')
        self.channels = channels
        self.max_age_s = max_age_s
        self.epoch = None
        self.last_seq = self.last_frame = None

    def start_session(self, release, epoch):
        # Fail closed: an unsuccessful reconfiguration must not retain the old session.
        self.epoch = None
        self.last_seq = self.last_frame = None
        expected = dict(abi='2.1', regmap_version=0x00020001, feature_capability=0x17f,
                        raw_capability=15, frame_samples=2048, sample_rate_nominal_hz=10000,
                        bit_sha256=BIT, hwh_sha256=HWH)
        if not isinstance(release, dict) or release.get('verified_by_reader') is not True:
            raise ValueError('RELEASE_NOT_VERIFIED')
        for key,value in expected.items():
            if type(release.get(key)) is not type(value) or release[key] != value:
                raise ValueError('RELEASE_MISMATCH: ' + key)
        if not isinstance(epoch, (list, tuple)) or len(epoch) != 3 or not all(isinstance(x,str) and x for x in epoch[:2]) or type(epoch[2]) is not int or not 0 <= epoch[2] < 2**32:
            raise ValueError('INVALID_EPOCH')
        self.epoch = tuple(epoch)

    def result(self, error):
        return dict(status='model_error', error_code=error, class_id=None, class_name=None,
                    confidence=None, confidence_type='unavailable', model_version=None,
                    label_map_version=None, feature_config_version=VERSION, purpose=PURPOSE,
                    adapter_version=ADAPTER_VERSION, schema_id=self.schema_id,
                    input_status='rejected', features=None, frame_identity=None)

    def process(self, snapshot, *, received_monotonic_s, now_monotonic_s, reader_eligible):
        result = self.result('MODEL_NOT_READY')
        if self.epoch is None:
            result.update(status='invalid_input', error_code='SESSION_NOT_READY')
            return result
        try:
            if reader_eligible is not True:
                raise ValueError('READER_REJECTED')
            if any(type(t) not in (int,float) or not math.isfinite(t) for t in (received_monotonic_s,now_monotonic_s)):
                raise ValueError('INVALID_AGE')
            age = now_monotonic_s - received_monotonic_s
            if age < 0 or age > self.max_age_s:
                raise ValueError('STALE_INPUT')
            if tuple(snapshot['session']['epoch']) != self.epoch:
                raise ValueError('EPOCH_MISMATCH')
            values, _, seq, quality = convert(snapshot, self.channels)
            frame = snapshot['frame_id']
            if self.last_seq is not None and not forward_u32(seq,self.last_seq):
                raise ValueError('DUPLICATE_OR_OUT_OF_ORDER_SEQUENCE')
            if self.last_frame is not None and not forward_u32(frame,self.last_frame):
                raise ValueError('DUPLICATE_OR_OUT_OF_ORDER_FRAME')
            self.last_seq, self.last_frame = seq, frame
            result.update(input_status='accepted', features=dict(zip(self.names,values)),
                          frame_identity=dict(epoch=list(self.epoch), frame_id=frame, snapshot_seq=seq),
                          quality=quality, age_s=age)
        except (KeyError,TypeError,ValueError,OverflowError) as exc:
            result.update(status='invalid_input', error_code='INVALID_SNAPSHOT', detail=str(exc))
        return result
