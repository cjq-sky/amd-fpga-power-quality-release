"""Harmonic task metadata around the unchanged v3 adapter. No trained model."""
from lab07.board_adapter import BoardAdapter
from .contract import VERSION, BASE_FEATURE_VERSION

class HarmonicAdapter:
    def __init__(self, *, channel, max_age_s):
        if channel not in ('CH1', 'CH2'):
            raise ValueError('explicit single channel CH1 or CH2 required')
        self.channel = channel
        self.guard = BoardAdapter(channels=channel, max_age_s=max_age_s)

    def start_session(self, release, epoch):
        self.guard.start_session(release, epoch)

    def process(self, snapshot, *, received_monotonic_s, now_monotonic_s, reader_eligible):
        result = self.guard.process(snapshot, received_monotonic_s=received_monotonic_s,
                                    now_monotonic_s=now_monotonic_s, reader_eligible=reader_eligible)
        result.update(feature_config_version=VERSION, base_feature_config_version=BASE_FEATURE_VERSION,
                      purpose='harmonic_classification_preparation_no_model',
                      adapter_version='lab07-harmonic-adapter-0.5',
                      task_id='harmonic_shape_four_class')
        # class_id, confidence, model_version and label_map_version remain null.
        return result
