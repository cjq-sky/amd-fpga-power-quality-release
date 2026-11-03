"""Versioned candidate contract: offline replay, not production approval."""
try:
    from .prepare_features import schema, BIT, HWH
except ImportError:
    from prepare_features import schema, BIT, HWH

PURPOSE = 'lab07_candidate_model_not_production_certified'
VERSION = 'lab07-candidate-1.1'

def configuration(channels='both'):
    sid, names = schema(channels)
    fields = []
    for i, name in enumerate(names):
        ch, suffix = name.split('_', 1)
        if suffix.startswith('band_'):
            order = suffix.split('_')[1].upper()
            formula, unit = f'100 * {ch}_{order} / {ch}_H1', '%'
        elif suffix == 'thd_odd_pct':
            formula, unit = f'100 * {ch}_THD_ODD_3_5_7_9 / 65536', '%'
        else:
            formula, unit = f'{ch}_CREST / 1024', 'ratio'
        fields.append(dict(index=i, name=name, channel=ch, use='USE', formula=formula, unit=unit))
    return dict(contract_id=VERSION, version=VERSION, status='candidate_offline_frozen_online_pending',
                purpose=PURPOSE, schema_id=sid, channels=channels, input_dtype='float32', shape=[len(names)],
                fields=fields, feature_names=names, abi='2.1', bit_sha256=BIT, hwh_sha256=HWH,
                feature_capability=0x17F, raw_capability=15, raw_required=False,
                preprocessing='none_after_adapter', h1_raw_min_exclusive=0,
                h1_threshold_scope='division_guard_only_not_production_SNR',
                missing_policy='reject', nonfinite_policy='reject', negative_policy='reject',
                clipping=False, imputation=False, formal_unknown_offline='ALLOW_NUMERIC_REPLAY',
                online_enabled=False, training_requires_real_labels=True,
                distribution_limits=None, label_map_version=None, model_version=None)
