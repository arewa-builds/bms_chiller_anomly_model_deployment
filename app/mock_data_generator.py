"""Synthetic Chiller Data Generator (training-calibrated).

Generates coherent synthetic chiller telemetry that sits inside the operating
envelope the LOF model was trained on, then derives all 197 features with the
production pipeline (``preprocessor.engineer_features``).

Why this design
---------------
An earlier version re-implemented feature engineering locally. It drifted
from the production preprocessor (for example ``*_d1``/``*_d2`` were lags
instead of differences) and used sensor levels far from the training data,
so the LOF model flagged 999 of 1,000 "normal" rows as anomalies. Reusing
``engineer_features`` removes that class of offline/live drift.

Calibration
-----------
Sensor levels, load sensitivity, residual noise, and autocorrelation below
were estimated from the 2,754 training rows embedded in
``model/lof_chiller_model.onnx`` (unscaled with ``model/scaler_model.onnx``).
Supply-side sensors are modelled as ``a + b * load + AR(1) residual`` where
``load`` is the chiller RLA (rated load amps, percent) following a daily
profile. Return temperatures are supply plus a load-dependent delta-T, and
phase currents follow RLA with fixed per-phase offsets.

Notes
-----
* WET_BULB was effectively constant (about -71.02) in the training data,
  which suggests a faulty or unconverted sensor at the training site. The
  generator reproduces it so features stay in distribution; treat it as a
  data-quality finding, not a physical value.
* Training covered January to March, so timestamps start on 2026-02-02.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preprocessor import FEATURE_ORDER, RAW_SENSOR_COLS, engineer_features  # noqa: E402

# Hourly load profile (RLA_Avg %, training mean by hour of day).
LOAD_BY_HOUR = np.array([
    46.3, 45.8, 45.7, 45.4, 45.2, 45.0, 45.1, 45.0, 46.6, 47.7, 49.8, 49.5,
    49.7, 49.8, 50.8, 50.8, 50.1, 48.9, 48.1, 47.4, 47.3, 47.0, 46.8, 46.3,
])
LOAD_SD = 9.0      # training RLA_Avg standard deviation is about 9.2
LOAD_AR1 = 0.95

# sensor: (intercept a, load slope b, residual sd, residual AR(1))
SENSOR_MODEL = {
    "CHW_Supply": (43.581, -0.005, 0.510, 0.68),
    "CW_Supply":  (60.652, 0.259, 2.112, 0.93),
    "PH1_FLOW":   (1689.869, 4.353, 84.578, 0.95),
    "PH2_FLOW":   (36.980, 4.995, 58.671, 0.91),
    "SIGNAL":     (-18.982, 1.986, 21.220, 0.90),
}
RLA_PHASE_MODEL = {  # phase = a + b * load + AR(1) residual
    "RLA_L1": (-0.225, 0.971, 0.611, 0.44),
    "RLA_L2": (-0.418, 1.017, 0.585, 0.32),
    "RLA_L3": (0.834, 1.008, 0.692, 0.54),
}
# Return temperatures are modelled as supply + delta-T so the loop stays coherent.
# delta: (intercept a, load slope b, residual sd, residual AR(1))
DELTA_T_MODEL = {
    "CHW_Return": ("CHW_Supply", (-0.3216, 0.1102, 0.694, 0.84)),
    "CW_Return":  ("CW_Supply",  (-3.2769, 0.1443, 0.482, 0.66)),
}
RLA_PER_AMP = 0.228          # training median RLA / phase current
PHASE_CURRENT_OFFSET = {"L1": -6.88, "L2": 1.62, "L3": 5.26}   # A, vs phase mean
PHASE_CURRENT_SD = 2.1
TRACKING_ERROR_SD = 8.0      # FEEDBACK minus SIGNAL residual
WET_BULB_TRAINING = -71.02


def _ar1(rng: np.random.Generator, n: int, sd: float, phi: float) -> np.ndarray:
    """Stationary AR(1) noise with marginal standard deviation ``sd``."""
    eps = rng.normal(0.0, sd * np.sqrt(1.0 - phi**2), n)
    out = np.empty(n)
    out[0] = rng.normal(0.0, sd)
    for i in range(1, n):
        out[i] = phi * out[i - 1] + eps[i]
    return out


def simulate_raw(n_rows: int = 1000, seed: int = 42,
                 start: str = "2026-02-02T00:00:00Z") -> pd.DataFrame:
    """Simulate the 16 raw OPC UA sensors at a 30-minute cadence."""
    rng = np.random.default_rng(seed)
    index = pd.date_range(start=start, periods=n_rows, freq="30min")
    hour = index.hour.to_numpy()

    load = np.clip(LOAD_BY_HOUR[hour] + _ar1(rng, n_rows, LOAD_SD, LOAD_AR1), 10, 95)

    raw: dict[str, np.ndarray] = {}
    for name, (a, b, sd, phi) in SENSOR_MODEL.items():
        raw[name] = a + b * load + _ar1(rng, n_rows, sd, phi)
    for name, (a, b, sd, phi) in RLA_PHASE_MODEL.items():
        raw[name] = np.round(a + b * load + _ar1(rng, n_rows, sd, phi))
    raw["RLA_Avg"] = (raw["RLA_L1"] + raw["RLA_L2"] + raw["RLA_L3"]) / 3.0

    for name, (supply, (a, b, sd, phi)) in DELTA_T_MODEL.items():
        raw[name] = raw[supply] + a + b * load + _ar1(rng, n_rows, sd, phi)

    ratio = RLA_PER_AMP * (1.0 + _ar1(rng, n_rows, 0.06, 0.9))
    current_mean = raw["RLA_Avg"] / ratio
    for phase, offset in PHASE_CURRENT_OFFSET.items():
        raw[f"CURRENT_{phase}"] = current_mean + offset + rng.normal(0.0, PHASE_CURRENT_SD, n_rows)

    raw["SIGNAL"] = np.clip(raw["SIGNAL"], 0.0, 100.0)
    raw["FEEDBACK"] = np.clip(
        raw["SIGNAL"] + 3.0 + _ar1(rng, n_rows, TRACKING_ERROR_SD, 0.85), 0.0, 100.0
    )
    raw["WET_BULB"] = WET_BULB_TRAINING + rng.normal(0.0, 0.03, n_rows)

    df = pd.DataFrame({c: raw[c] for c in RAW_SENSOR_COLS}, index=index)
    df.index.name = "_ts"
    return df


def build_synthetic_dataset(n_rows: int = 1000, seed: int = 42,
                            readings_offset: int = 500) -> pd.DataFrame:
    """Raw sensors plus all FEATURE_ORDER columns, computed by production code.

    ``readings_offset`` places the chiller mid-run (the training data never
    shows a cold start), matching how ``ChillerPreprocessor.update`` counts.
    """
    raw = simulate_raw(n_rows=n_rows, seed=seed)
    raw["_readings_since_start"] = readings_offset + np.arange(n_rows, dtype=float)
    features = engineer_features(raw)
    cols = list(dict.fromkeys(RAW_SENSOR_COLS + FEATURE_ORDER))
    out = features[cols].replace([np.inf, -np.inf], np.nan).fillna(0.0)
    out.index = out.index.tz_localize(None) if out.index.tz is not None else out.index
    return out


def save_synthetic_dataset(data: pd.DataFrame,
                           path: str | Path = "synthetic_chiller_data.csv") -> None:
    data.to_csv(path, index=True, index_label="timestamp")


REPO_ROOT = Path(__file__).resolve().parent.parent


def main(output_path: str | Path = REPO_ROOT / "synthetic_chiller_data.csv") -> None:
    dataset = build_synthetic_dataset(n_rows=1000)
    save_synthetic_dataset(dataset, output_path)
    print(f"Generated {len(dataset)} rows of training-calibrated synthetic data: {output_path}")


if __name__ == "__main__":
    main()
