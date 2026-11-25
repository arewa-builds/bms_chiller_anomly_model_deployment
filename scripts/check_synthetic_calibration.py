"""Regression check: synthetic data must look normal to the LOF model, and injected faults must still be caught.

Run: python scripts/check_synthetic_calibration.py
Exits non-zero if the false-alarm rate on clean data exceeds MAX_CLEAN_RATE or a
gross fault is not detected. Subtle-fault sensitivity is printed for visibility only.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "app"))
import mock_data_generator as g  # noqa: E402
import preprocessor as p  # noqa: E402
import score_synthetic_data as s  # noqa: E402

MAX_CLEAN_RATE = 0.03
SEEDS = [1, 2, 3, 7, 42, 100, 2026]
FAULT_WINDOW = slice(600, 700)


def score(raw):
    raw = raw.copy()
    raw["_readings_since_start"] = 500 + np.arange(len(raw))
    feats = p.engineer_features(raw)
    cols = list(dict.fromkeys(p.RAW_SENSOR_COLS + p.FEATURE_ORDER))
    data = feats[cols].replace([np.inf, -np.inf], np.nan).fillna(0).reset_index(drop=True)
    return s.score_dataset(data)["is_anomaly"]


def scaled(cols, factor):
    def apply(raw):
        for c in cols:
            raw.iloc[FAULT_WINDOW, raw.columns.get_loc(c)] *= factor
        return raw
    return apply


def shifted(cols, delta):
    def apply(raw):
        for c in cols:
            raw.iloc[FAULT_WINDOW, raw.columns.get_loc(c)] += delta
        return raw
    return apply


GROSS_FAULTS = {  # must be detected in >= 50% of the fault window
    "PH1_FLOW x0.3 (severe flow restriction)": scaled(["PH1_FLOW"], 0.3),
    "CURRENT_L1 x0.4 (phase loss)": scaled(["CURRENT_L1"], 0.4),
}
SUBTLE_FAULTS = {  # informational: documents known model sensitivity limits
    "CW loop +6 F (condenser degradation)": shifted(["CW_Supply", "CW_Return"], 6),
    "CHW supply +3 F (setpoint drift)": shifted(["CHW_Supply", "CHW_Return"], 3),
    "PH1_FLOW x0.75 (mild flow restriction)": scaled(["PH1_FLOW"], 0.75),
}


def main():
    failed = False
    for seed in SEEDS:
        rate = score(g.simulate_raw(seed=seed)).iloc[s.WARMUP_ROWS if hasattr(s, "WARMUP_ROWS") else 48:].mean()
        ok = rate <= MAX_CLEAN_RATE
        failed |= not ok
        print(f"[{'PASS' if ok else 'FAIL'}] clean seed {seed:>4}: {rate:.1%} flagged")
    for name, fault in GROSS_FAULTS.items():
        rate = score(fault(g.simulate_raw(seed=42))).iloc[FAULT_WINDOW].mean()
        ok = rate >= 0.5
        failed |= not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {name}: {rate:.0%} of fault window flagged")
    for name, fault in SUBTLE_FAULTS.items():
        rate = score(fault(g.simulate_raw(seed=42))).iloc[FAULT_WINDOW].mean()
        print(f"[INFO] {name}: {rate:.0%} of fault window flagged")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
