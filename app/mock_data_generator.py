"""Synthetic Chiller Dashboard Data Generator

Generates 1,000 rows of coherent synthetic chiller telemetry using
`nemo_platform` if available, otherwise falling back to pandas.

The simulation creates realistic base sensor signals first, then derives
lag, rolling, ratio, and proxy features from those signals.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    import nemo_platform as nemo_platform
except ImportError:  # pragma: no cover
    nemo_platform = None

RAW_COLUMNS = [
    "CHW_Return",
    "CHW_Supply",
    "RLA_L1",
    "RLA_L2",
    "RLA_L3",
    "RLA_Avg",
    "CW_Return",
    "CW_Supply",
    "PH1_FLOW",
    "PH2_FLOW",
    "FEEDBACK",
    "SIGNAL",
    "CURRENT_L2",
    "CURRENT_L3",
    "CURRENT_L1",
    "WET_BULB",
]

DERIVED_COLUMNS = [
    "CHW_delta",
    "CW_delta",
    "RLA_imbalance",
    "CHW_Return_d1",
    "CHW_Return_d2",
    "CHW_Supply_d1",
    "CHW_Supply_d2",
    "CW_Return_d1",
    "CW_Return_d2",
    "CW_Supply_d1",
    "CW_Supply_d2",
    "RLA_L1_d1",
    "RLA_L1_d2",
    "RLA_L2_d1",
    "RLA_L2_d2",
    "RLA_L3_d1",
    "RLA_L3_d2",
    "RLA_Avg_d1",
    "RLA_Avg_d2",
    "PH1_FLOW_d1",
    "PH1_FLOW_d2",
    "PH2_FLOW_d1",
    "PH2_FLOW_d2",
    "FEEDBACK_d1",
    "FEEDBACK_d2",
    "SIGNAL_d1",
    "SIGNAL_d2",
    "CURRENT_L1_d1",
    "CURRENT_L1_d2",
    "CURRENT_L2_d1",
    "CURRENT_L2_d2",
    "CURRENT_L3_d1",
    "CURRENT_L3_d2",
    "CHW_Return_rmean_2h",
    "CHW_Return_rstd_2h",
    "CHW_Return_rrange_2h",
    "CHW_Return_rmean_24h",
    "CHW_Return_rstd_24h",
    "CHW_Return_zscore_24h",
    "CHW_Supply_rmean_2h",
    "CHW_Supply_rstd_2h",
    "CHW_Supply_rrange_2h",
    "CHW_Supply_rmean_24h",
    "CHW_Supply_rstd_24h",
    "CHW_Supply_zscore_24h",
    "CW_Return_rmean_2h",
    "CW_Return_rstd_2h",
    "CW_Return_rrange_2h",
    "CW_Return_rmean_24h",
    "CW_Return_rstd_24h",
    "CW_Return_zscore_24h",
    "CW_Supply_rmean_2h",
    "CW_Supply_rstd_2h",
    "CW_Supply_rrange_2h",
    "CW_Supply_rmean_24h",
    "CW_Supply_rstd_24h",
    "CW_Supply_zscore_24h",
    "RLA_L1_rmean_2h",
    "RLA_L1_rstd_2h",
    "RLA_L1_rrange_2h",
    "RLA_L1_rmean_24h",
    "RLA_L1_rstd_24h",
    "RLA_L1_zscore_24h",
    "RLA_L2_rmean_2h",
    "RLA_L2_rstd_2h",
    "RLA_L2_rrange_2h",
    "RLA_L2_rmean_24h",
    "RLA_L2_rstd_24h",
    "RLA_L2_zscore_24h",
    "RLA_L3_rmean_2h",
    "RLA_L3_rstd_2h",
    "RLA_L3_rrange_2h",
    "RLA_L3_rmean_24h",
    "RLA_L3_rstd_24h",
    "RLA_L3_zscore_24h",
    "RLA_Avg_rmean_2h",
    "RLA_Avg_rstd_2h",
    "RLA_Avg_rrange_2h",
    "RLA_Avg_rmean_24h",
    "RLA_Avg_rstd_24h",
    "RLA_Avg_zscore_24h",
    "PH1_FLOW_rmean_2h",
    "PH1_FLOW_rstd_2h",
    "PH1_FLOW_rrange_2h",
    "PH1_FLOW_rmean_24h",
    "PH1_FLOW_rstd_24h",
    "PH1_FLOW_zscore_24h",
    "PH2_FLOW_rmean_2h",
    "PH2_FLOW_rstd_2h",
    "PH2_FLOW_rrange_2h",
    "PH2_FLOW_rmean_24h",
    "PH2_FLOW_rstd_24h",
    "PH2_FLOW_zscore_24h",
    "WET_BULB_zscore_24h",
    "FEEDBACK_rmean_2h",
    "FEEDBACK_rstd_2h",
    "FEEDBACK_rrange_2h",
    "FEEDBACK_rmean_24h",
    "FEEDBACK_rstd_24h",
    "FEEDBACK_zscore_24h",
    "SIGNAL_rmean_2h",
    "SIGNAL_rstd_2h",
    "SIGNAL_rrange_2h",
    "SIGNAL_rmean_24h",
    "SIGNAL_rstd_24h",
    "SIGNAL_zscore_24h",
    "CURRENT_L1_rmean_2h",
    "CURRENT_L1_rstd_2h",
    "CURRENT_L1_rrange_2h",
    "CURRENT_L1_rmean_24h",
    "CURRENT_L1_rstd_24h",
    "CURRENT_L1_zscore_24h",
    "CURRENT_L2_rmean_2h",
    "CURRENT_L2_rstd_2h",
    "CURRENT_L2_rrange_2h",
    "CURRENT_L2_rmean_24h",
    "CURRENT_L2_rstd_24h",
    "CURRENT_L2_zscore_24h",
    "CURRENT_L3_rmean_2h",
    "CURRENT_L3_rstd_2h",
    "CURRENT_L3_rrange_2h",
    "CURRENT_L3_rmean_24h",
    "CURRENT_L3_rstd_24h",
    "CURRENT_L3_zscore_24h",
    "CHW_delta_T",
    "CHW_delta_T_d1",
    "CHW_delta_T_d2",
    "CW_delta_T",
    "CW_delta_T_d1",
    "RLA_spread",
    "RLA_spread_d1",
    "RLA_avg_calc",
    "COP_proxy",
    "COP_proxy_d1",
    "Temp_ratio",
    "is_weekend",
    "is_business_hours",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
    "current_mean",
    "current_imbalance",
    "current_std_phases",
    "current_imbalance_d1",
    "RLA_cur_ratio_L1",
    "RLA_cur_ratio_L2",
    "RLA_cur_ratio_L3",
    "tower_tracking_error",
    "tower_tracking_error_abs",
    "tower_nonresponse_flag",
    "CW_approach_to_WB",
    "CW_sup_vs_expected",
    "total_flow",
    "flow_imbalance",
    "flow_imbalance_pct",
    "cooling_tons_proxy",
    "tons_per_RLA",
    "RLA_weather_norm",
    "RLA_EWMA_4h",
    "CHW_ret_EWMA_4h",
    "CW_ret_EWMA_4h",
    "RLA_high_persistence_4h",
    "RLA_high_persistence_8h",
    "COP_7d_mean",
    "COP_7d_drift",
    "COP_3d_slope",
    "CW_approach_7d_mean",
    "CW_approach_drift",
    "CW_approach_3d_slope",
    "CHW_dT_7d_mean",
    "CHW_dT_drift",
    "CHW_dT_3d_slope",
    "RLA_spread_7d_mean",
    "RLA_spread_drift",
    "RLA_spread_3d_slope",
    "tower_err_3d_mean",
    "tower_err_7d_mean",
    "tower_err_drift",
    "readings_since_start",
]


def _to_nemo_dataframe(df: pd.DataFrame) -> Any:
    if nemo_platform is None:
        return df

    if hasattr(nemo_platform, "DataFrame"):
        try:
            return nemo_platform.DataFrame(df)
        except Exception:
            pass

    if hasattr(nemo_platform, "from_pandas"):
        try:
            return nemo_platform.from_pandas(df)
        except Exception:
            pass

    return df


def _simulate_base_series(n_rows: int = 1000, freq_mins: int = 30, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    index = pd.date_range(start="2026-01-01T00:00:00", periods=n_rows, freq=f"{freq_mins}min")
    hour = index.hour + index.minute / 60.0
    day_of_year = index.dayofyear
    week_day = index.dayofweek
    month = index.month

    oscillation = np.sin(2 * np.pi * hour / 24)
    seasonal = 2.5 * np.sin(2 * np.pi * day_of_year / 365)

    wet_bulb = 65 + 8 * oscillation + 2.0 * np.sin(2 * np.pi * month / 12) + rng.normal(0, 0.8, n_rows)
    chw_return = 59 + 4.5 * oscillation - 0.8 * np.cos(2 * np.pi * day_of_year / 365) + rng.normal(0, 0.5, n_rows)
    chw_supply = chw_return - (5.5 + 0.5 * rng.normal(0, 1.0, n_rows))
    cw_return = 75 + 6.0 * oscillation + 1.0 * np.sin(2 * np.pi * day_of_year / 365) + rng.normal(0, 0.6, n_rows)
    cw_supply = cw_return - (8.3 + 0.6 * rng.normal(0, 1.0, n_rows))

    base_demand = 700 + 80 * np.sin(2 * np.pi * hour / 24) + 20 * np.cos(2 * np.pi * week_day / 7)
    ph1_flow = base_demand * (0.52 + rng.normal(0, 0.02, n_rows))
    ph2_flow = base_demand * (0.48 + rng.normal(0, 0.02, n_rows))
    total_flow = ph1_flow + ph2_flow

    current_base = 210 + 15 * np.sin(2 * np.pi * hour / 24) + rng.normal(0, 4.0, n_rows)
    current_l1 = current_base + rng.normal(0, 2.0, n_rows)
    current_l2 = current_base + rng.normal(0, 2.2, n_rows)
    current_l3 = current_base + rng.normal(0, 2.5, n_rows)

    rla_l1 = 62 + 14 * (total_flow / total_flow.max()) + rng.normal(0, 2.0, n_rows)
    rla_l2 = rla_l1 + rng.normal(0, 1.8, n_rows)
    rla_l3 = rla_l1 - rng.normal(0, 1.6, n_rows)
    rla_avg = np.minimum(100.0, np.maximum(0.0, (rla_l1 + rla_l2 + rla_l3) / 3))

    feedback = 50 + 15 * np.sin(2 * np.pi * hour / 24 + 0.6) + rng.normal(0, 2.0, n_rows)
    signal = feedback + rng.normal(0, 2.5, n_rows)

    return pd.DataFrame(
        {
            "CHW_Return": chw_return,
            "CHW_Supply": chw_supply,
            "RLA_L1": rla_l1,
            "RLA_L2": rla_l2,
            "RLA_L3": rla_l3,
            "RLA_Avg": rla_avg,
            "CW_Return": cw_return,
            "CW_Supply": cw_supply,
            "PH1_FLOW": ph1_flow,
            "PH2_FLOW": ph2_flow,
            "FEEDBACK": feedback,
            "SIGNAL": signal,
            "CURRENT_L1": current_l1,
            "CURRENT_L2": current_l2,
            "CURRENT_L3": current_l3,
            "WET_BULB": wet_bulb,
        },
        index=index,
    )


def _add_lags(df: pd.DataFrame, columns: list[str], lags: list[int]) -> pd.DataFrame:
    for column in columns:
        for lag in lags:
            df[f"{column}_d{lag}"] = df[column].shift(lag)
    return df


def _rolling_stats(df: pd.DataFrame, column: str, window: int, suffix: str) -> pd.Series:
    rolling = df[column].rolling(window=window, min_periods=1)
    if suffix == "mean":
        return rolling.mean()
    if suffix == "std":
        return rolling.std(ddof=0)
    if suffix == "range":
        return rolling.max() - rolling.min()
    raise ValueError(f"Unknown suffix {suffix}")


def _zscore_24h(series: pd.Series, window: int = 48) -> pd.Series:
    mean_24h = series.rolling(window=window, min_periods=1).mean()
    std_24h = series.rolling(window=window, min_periods=1).std(ddof=0)
    return (series - mean_24h) / (std_24h.replace(0, np.nan) + 1e-6)


def _slope(series: pd.Series, window: int) -> pd.Series:
    def slope_window(values: np.ndarray) -> float:
        x = np.arange(len(values))
        if len(values) < 2 or np.allclose(values, values[0]):
            return 0.0
        coef = np.polyfit(x, values, 1)
        return float(coef[0])

    return series.rolling(window=window, min_periods=2).apply(slope_window, raw=True)


def _derive_features(raw: pd.DataFrame) -> pd.DataFrame:
    df = raw.copy()
    df["CHW_delta"] = df["CHW_Return"] - df["CHW_Supply"]
    df["CW_delta"] = df["CW_Return"] - df["CW_Supply"]
    df["RLA_imbalance"] = df[["RLA_L1", "RLA_L2", "RLA_L3"]].max(axis=1) - df[["RLA_L1", "RLA_L2", "RLA_L3"]].min(axis=1)
    df["RLA_avg_calc"] = df[["RLA_L1", "RLA_L2", "RLA_L3"]].mean(axis=1)
    df["CHW_delta_T"] = df["CHW_delta"]
    df["CW_delta_T"] = df["CW_delta"]
    df["Temp_ratio"] = (df["CHW_Return"] - df["CW_Return"]) / (df["WET_BULB"] + 1)
    df["total_flow"] = df["PH1_FLOW"] + df["PH2_FLOW"]
    df["flow_imbalance"] = (df["PH1_FLOW"] - df["PH2_FLOW"]).abs()
    df["flow_imbalance_pct"] = df["flow_imbalance"] / (df["total_flow"] + 1e-6)
    df["current_mean"] = df[["CURRENT_L1", "CURRENT_L2", "CURRENT_L3"]].mean(axis=1)
    df["current_imbalance"] = df[["CURRENT_L1", "CURRENT_L2", "CURRENT_L3"]].max(axis=1) - df[["CURRENT_L1", "CURRENT_L2", "CURRENT_L3"]].min(axis=1)
    df["current_std_phases"] = df[["CURRENT_L1", "CURRENT_L2", "CURRENT_L3"]].std(axis=1, ddof=0)
    df["tower_tracking_error"] = df["FEEDBACK"] - df["SIGNAL"]
    df["tower_tracking_error_abs"] = df["tower_tracking_error"].abs()
    df["tower_nonresponse_flag"] = ((df["tower_tracking_error_abs"] < 1.2) & (df["SIGNAL"].diff().abs() < 0.2)).astype(int)
    df["CW_approach_to_WB"] = df["CW_Supply"] - df["WET_BULB"]
    df["CW_sup_vs_expected"] = df["CW_Supply"] - (df["WET_BULB"] + 10)
    df["cooling_tons_proxy"] = df["total_flow"] * df["CHW_delta"] / 24.0
    df["tons_per_RLA"] = df["cooling_tons_proxy"] / (df["RLA_Avg"] + 1.0)
    df["RLA_weather_norm"] = df["RLA_Avg"] - 0.12 * (df["WET_BULB"] - 70)
    df["RLA_spread"] = df["RLA_Avg"] - df[["RLA_L1", "RLA_L2", "RLA_L3"]].min(axis=1)

    df = _add_lags(df, RAW_COLUMNS + ["CHW_delta", "CW_delta", "CHW_delta_T", "CW_delta_T", "RLA_spread"], [1, 2])

    df["RLA_EWMA_4h"] = df["RLA_Avg"].ewm(span=8, adjust=False).mean()
    df["CHW_ret_EWMA_4h"] = df["CHW_Return"].ewm(span=8, adjust=False).mean()
    df["CW_ret_EWMA_4h"] = df["CW_Return"].ewm(span=8, adjust=False).mean()

    df["RLA_high_persistence_4h"] = (df["RLA_Avg"].rolling(window=8, min_periods=1).mean() > 85).astype(int)
    df["RLA_high_persistence_8h"] = (df["RLA_Avg"].rolling(window=16, min_periods=1).mean() > 80).astype(int)

    df["COP_proxy"] = df["cooling_tons_proxy"] / (df["RLA_Avg"] + 1.0)
    df["COP_proxy_d1"] = df["COP_proxy"].shift(1)

    df["is_weekend"] = df.index.dayofweek >= 5
    df["is_business_hours"] = ((df.index.hour >= 8) & (df.index.hour < 18))
    df["hour_sin"] = np.sin(2 * np.pi * df.index.hour / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df.index.hour / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df.index.dayofweek / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df.index.dayofweek / 7)
    df["month_sin"] = np.sin(2 * np.pi * df.index.month / 12)
    df["month_cos"] = np.cos(2 * np.pi * df.index.month / 12)

    for col in [
        "CHW_Return",
        "CHW_Supply",
        "CW_Return",
        "CW_Supply",
        "RLA_L1",
        "RLA_L2",
        "RLA_L3",
        "RLA_Avg",
        "PH1_FLOW",
        "PH2_FLOW",
        "FEEDBACK",
        "SIGNAL",
        "CURRENT_L1",
        "CURRENT_L2",
        "CURRENT_L3",
        "WET_BULB",
    ]:
        df[f"{col}_rmean_2h"] = df[col].rolling(window=4, min_periods=1).mean()
        df[f"{col}_rstd_2h"] = df[col].rolling(window=4, min_periods=1).std(ddof=0)
        df[f"{col}_rrange_2h"] = df[col].rolling(window=4, min_periods=1).max() - df[col].rolling(window=4, min_periods=1).min()
        df[f"{col}_rmean_24h"] = df[col].rolling(window=48, min_periods=1).mean()
        df[f"{col}_rstd_24h"] = df[col].rolling(window=48, min_periods=1).std(ddof=0)
        df[f"{col}_zscore_24h"] = _zscore_24h(df[col], window=48)

    df["CW_approach_7d_mean"] = df["CW_approach_to_WB"].rolling(window=336, min_periods=1).mean()
    df["CW_approach_drift"] = df["CW_approach_to_WB"] - df["CW_approach_7d_mean"]
    df["CW_approach_3d_slope"] = _slope(df["CW_approach_to_WB"], window=144)

    df["CHW_dT_7d_mean"] = df["CHW_delta_T"].rolling(window=336, min_periods=1).mean()
    df["CHW_dT_drift"] = df["CHW_delta_T"] - df["CHW_dT_7d_mean"]
    df["CHW_dT_3d_slope"] = _slope(df["CHW_delta_T"], window=144)

    df["RLA_spread_7d_mean"] = df["RLA_spread"].rolling(window=336, min_periods=1).mean()
    df["RLA_spread_drift"] = df["RLA_spread"] - df["RLA_spread_7d_mean"]
    df["RLA_spread_3d_slope"] = _slope(df["RLA_spread"], window=144)

    df["tower_err_3d_mean"] = df["tower_tracking_error"].rolling(window=144, min_periods=1).mean()
    df["tower_err_7d_mean"] = df["tower_tracking_error"].rolling(window=336, min_periods=1).mean()
    df["tower_err_drift"] = df["tower_tracking_error"] - df["tower_err_7d_mean"]

    df["COP_7d_mean"] = df["COP_proxy"].rolling(window=336, min_periods=1).mean()
    df["COP_7d_drift"] = df["COP_proxy"] - df["COP_7d_mean"]
    df["COP_3d_slope"] = _slope(df["COP_proxy"], window=144)

    df["readings_since_start"] = np.arange(len(df), dtype=int)

    df = df.ffill().fillna(0)
    return df


def build_synthetic_dataset(n_rows: int = 1000, seed: int = 42) -> Any:
    raw = _simulate_base_series(n_rows=n_rows, seed=seed)
    derived = _derive_features(raw)
    derived = derived[RAW_COLUMNS + [c for c in derived.columns if c not in RAW_COLUMNS]]
    return _to_nemo_dataframe(derived)


def save_synthetic_dataset(data: Any, path: str | Path = "synthetic_chiller_data.csv") -> None:
    if hasattr(data, "to_pandas"):
        data = data.to_pandas()
    if hasattr(data, "to_csv"):
        data.to_csv(path, index=True)
        return

    pd.DataFrame(data).to_csv(path, index=True)


def main(output_path: str = "synthetic_chiller_data.csv") -> None:
    dataset = build_synthetic_dataset(n_rows=1000)
    save_synthetic_dataset(dataset, output_path)
    print(f"Generated synthetic data for dashboard design: {output_path}")


if __name__ == "__main__":
    main()
