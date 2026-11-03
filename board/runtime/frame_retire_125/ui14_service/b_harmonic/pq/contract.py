"""Harmonic-only task. Label thresholds await joint review and real data."""
VERSION = 'lab07-harmonic-6d-0.1'
BASE_FEATURE_VERSION = 'lab07-candidate-1.1'
FEATURES = ['band_h3_pct', 'band_h5_pct', 'band_h7_pct', 'band_h9_pct', 'thd_odd_pct', 'crest']
LABELS = {0: 'CLEAN', 1: 'H3_DOMINANT', 2: 'H5_DOMINANT', 3: 'MIXED_ODD_HARMONICS'}
LABEL_VERSION = 'lab07-harmonic-four-class-proposal-0.1'
