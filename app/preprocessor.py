"""
BMS Chiller — Feature Engineering Preprocessor
===============================================
Reproduces exactly the 197-feature pipeline from the training notebook
(BMS_Chiller_Anomaly_Detection_With_Enhanced_Sensitivity v3.1).

The bridge calls ChillerPreprocessor.update(timestamp, raw) on every
new OPC-UA reading. Once the internal rolling buffer is warm enough,
get_feature_vector() returns the scaled 197-feature array ready for
the ONNX inference session.

Raw sensors required (16 values from OPC-UA, in any order via dict):
    CHW_Return, CHW_Supply, CW_Return, CW_Supply,
    RLA_L1, RLA_L2, RLA_L3, RLA_Avg,
    PH1_FLOW, PH2_FLOW, FEEDBACK, SIGNAL,
    CURRENT_L1, CURRENT_L2, CURRENT_L3, WET_BULB
"""

import numpy as np
import pandas as pd
import joblib
from pathlib import Path
from collections import deque
from datetime import datetime, timezone

# ── Training hyperparameters (must match CONFIG in notebook) ─────────────────
WIN_SHORT   = 4      # 4 × 30 min = 2 h  (roll_short)
WIN_LONG    = 48     # 48 × 30 min = 24 h (roll_long)
EWMA_SPAN   = 8      # ~4 h              (roll_ewma_span)
W3D         = 144    # 144 steps = 3 days
W7D         = 336    # 336 steps = 7 days
SMOOTH_WIN  = 5      # rolling-median noise smoothing window
RLA_ON_THR  = 5.0   # RLA_Avg > 5 % → chiller ON
STARTUP_WIN = 10     # readings after OFF→ON to suppress

# 197 features in exact training order
FEATURE_ORDER = [
    'CHW_Return','CHW_Supply','RLA_L1','RLA_L2','RLA_L3','RLA_Avg',
    'CW_Return','CW_Supply','PH1_FLOW','PH2_FLOW','FEEDBACK','SIGNAL',
    'CURRENT_L2','CURRENT_L3','CURRENT_L1','CHW_delta','CW_delta',
    'RLA_imbalance','CHW_Return_d1','CHW_Return_d2','CHW_Supply_d1',
    'CHW_Supply_d2','CW_Return_d1','CW_Return_d2','CW_Supply_d1',
    'CW_Supply_d2','RLA_L1_d1','RLA_L1_d2','RLA_L2_d1','RLA_L2_d2',
    'RLA_L3_d1','RLA_L3_d2','RLA_Avg_d1','RLA_Avg_d2','PH1_FLOW_d1',
    'PH1_FLOW_d2','PH2_FLOW_d1','PH2_FLOW_d2','FEEDBACK_d1','FEEDBACK_d2',
    'SIGNAL_d1','SIGNAL_d2','CURRENT_L1_d1','CURRENT_L1_d2',
    'CURRENT_L2_d1','CURRENT_L2_d2','CURRENT_L3_d1','CURRENT_L3_d2',
    'CHW_Return_rmean_2h','CHW_Return_rstd_2h','CHW_Return_rrange_2h',
    'CHW_Return_rmean_24h','CHW_Return_rstd_24h','CHW_Return_zscore_24h',
    'CHW_Supply_rmean_2h','CHW_Supply_rstd_2h','CHW_Supply_rrange_2h',
    'CHW_Supply_rmean_24h','CHW_Supply_rstd_24h','CHW_Supply_zscore_24h',
    'CW_Return_rmean_2h','CW_Return_rstd_2h','CW_Return_rrange_2h',
    'CW_Return_rmean_24h','CW_Return_rstd_24h','CW_Return_zscore_24h',
    'CW_Supply_rmean_2h','CW_Supply_rstd_2h','CW_Supply_rrange_2h',
    'CW_Supply_rmean_24h','CW_Supply_rstd_24h','CW_Supply_zscore_24h',
    'RLA_L1_rmean_2h','RLA_L1_rstd_2h','RLA_L1_rrange_2h',
    'RLA_L1_rmean_24h','RLA_L1_rstd_24h','RLA_L1_zscore_24h',
    'RLA_L2_rmean_2h','RLA_L2_rstd_2h','RLA_L2_rrange_2h',
    'RLA_L2_rmean_24h','RLA_L2_rstd_24h','RLA_L2_zscore_24h',
    'RLA_L3_rmean_2h','RLA_L3_rstd_2h','RLA_L3_rrange_2h',
    'RLA_L3_rmean_24h','RLA_L3_rstd_24h','RLA_L3_zscore_24h',
    'RLA_Avg_rmean_2h','RLA_Avg_rstd_2h','RLA_Avg_rrange_2h',
    'RLA_Avg_rmean_24h','RLA_Avg_rstd_24h','RLA_Avg_zscore_24h',
    'PH1_FLOW_rmean_2h','PH1_FLOW_rstd_2h','PH1_FLOW_rrange_2h',
    'PH1_FLOW_rmean_24h','PH1_FLOW_rstd_24h','PH1_FLOW_zscore_24h',
    'PH2_FLOW_rmean_2h','PH2_FLOW_rstd_2h','PH2_FLOW_rrange_2h',
    'PH2_FLOW_rmean_24h','PH2_FLOW_rstd_24h','PH2_FLOW_zscore_24h',
    'WET_BULB_zscore_24h',
    'FEEDBACK_rmean_2h','FEEDBACK_rstd_2h','FEEDBACK_rrange_2h',
    'FEEDBACK_rmean_24h','FEEDBACK_rstd_24h','FEEDBACK_zscore_24h',
    'SIGNAL_rmean_2h','SIGNAL_rstd_2h','SIGNAL_rrange_2h',
    'SIGNAL_rmean_24h','SIGNAL_rstd_24h','SIGNAL_zscore_24h',
    'CURRENT_L1_rmean_2h','CURRENT_L1_rstd_2h','CURRENT_L1_rrange_2h',
    'CURRENT_L1_rmean_24h','CURRENT_L1_rstd_24h','CURRENT_L1_zscore_24h',
    'CURRENT_L2_rmean_2h','CURRENT_L2_rstd_2h','CURRENT_L2_rrange_2h',
    'CURRENT_L2_rmean_24h','CURRENT_L2_rstd_24h','CURRENT_L2_zscore_24h',
    'CURRENT_L3_rmean_2h','CURRENT_L3_rstd_2h','CURRENT_L3_rrange_2h',
    'CURRENT_L3_rmean_24h','CURRENT_L3_rstd_24h','CURRENT_L3_zscore_24h',
    'CHW_delta_T','CHW_delta_T_d1','CHW_delta_T_d2',
    'CW_delta_T','CW_delta_T_d1',
    'RLA_spread','RLA_spread_d1','RLA_avg_calc',
    'COP_proxy','COP_proxy_d1','Temp_ratio',
    'is_weekend','is_business_hours',
    'hour_sin','hour_cos','dow_sin','dow_cos','month_sin','month_cos',
    'current_mean','current_imbalance','current_std_phases',
    'current_imbalance_d1',
    'RLA_cur_ratio_L1','RLA_cur_ratio_L2','RLA_cur_ratio_L3',
    'tower_tracking_error','tower_tracking_error_abs','tower_nonresponse_flag',
    'CW_approach_to_WB','CW_sup_vs_expected',
    'total_flow','flow_imbalance','flow_imbalance_pct',
    'cooling_tons_proxy','tons_per_RLA',
    'RLA_weather_norm',
    'RLA_EWMA_4h','CHW_ret_EWMA_4h','CW_ret_EWMA_4h',
    'RLA_high_persistence_4h','RLA_high_persistence_8h',
    'COP_7d_mean','COP_7d_drift','COP_3d_slope',
    'CW_approach_7d_mean','CW_approach_drift','CW_approach_3d_slope',
    'CHW_dT_7d_mean','CHW_dT_drift','CHW_dT_3d_slope',
    'RLA_spread_7d_mean','RLA_spread_drift','RLA_spread_3d_slope',
    'tower_err_3d_mean','tower_err_7d_mean','tower_err_drift',
    'readings_since_start',
]

RAW_SENSOR_COLS = [
    'CHW_Return','CHW_Supply','RLA_L1','RLA_L2','RLA_L3','RLA_Avg',
    'CW_Return','CW_Supply','PH1_FLOW','PH2_FLOW','FEEDBACK','SIGNAL',
    'CURRENT_L1','CURRENT_L2','CURRENT_L3','WET_BULB',
]


class ChillerPreprocessor:
    """
    Stateful rolling-window preprocessor.
    Call update() every 30 minutes with the latest OPC-UA reading.
    Call get_feature_vector() to get the 197-feature array for inference.
    """

    def __init__(self, scaler_path: str):
        self.scaler = joblib.load(scaler_path)
        # Rolling buffer — keep W7D + margin rows for long-window features
        self._buf: deque = deque(maxlen=W7D + 50)
        self._startup_cumsum = 0
        self._prev_rla_on = False
        self._readings_since_start = 0

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, timestamp: datetime, raw: dict) -> None:
        """
        Ingest one 30-min OPC-UA reading.

        Parameters
        ----------
        timestamp : datetime (timezone-aware UTC recommended)
        raw       : dict with keys matching RAW_SENSOR_COLS
        """
        row = {col: float(raw.get(col, np.nan)) for col in RAW_SENSOR_COLS}
        ts = pd.Timestamp(timestamp)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        row["_ts"] = ts

        # Startup counter (replaces CMD-based Group H)
        rla_on_now = row["RLA_Avg"] > RLA_ON_THR
        if rla_on_now and not self._prev_rla_on:
            # OFF → ON transition
            self._startup_cumsum += 1
            self._readings_since_start = 0
        elif rla_on_now:
            self._readings_since_start += 1
        else:
            self._readings_since_start = 0
        self._prev_rla_on = rla_on_now
        row["_readings_since_start"] = float(self._readings_since_start)

        self._buf.append(row)

    def is_warm(self) -> bool:
        """True once enough history exists for 24-hour rolling features."""
        return len(self._buf) >= WIN_LONG

    def get_feature_vector(self) -> np.ndarray:
        """
        Compute and return the scaled 197-feature vector for the latest reading.
        Returns None if the buffer is not yet warm.
        """
        if not self.is_warm():
            return None

        df = pd.DataFrame(list(self._buf)).set_index("_ts")

        # ── Step 1: rolling-median noise smoothing (Groups from notebook) ──
        sprint2_smooth = ["PH1_FLOW","PH2_FLOW","WET_BULB","FEEDBACK",
                          "SIGNAL","CURRENT_L1","CURRENT_L2","CURRENT_L3"]
        for col in sprint2_smooth:
            if col in df.columns:
                df[col] = df[col].rolling(
                    window=SMOOTH_WIN, center=True, min_periods=1
                ).median()

        # ── Group A: 1st and 2nd derivatives ────────────────────────────────
        deriv_cols = [c for c in RAW_SENSOR_COLS if c in df.columns and c != "WET_BULB"]
        for col in deriv_cols:
            df[f"{col}_d1"] = df[col].diff()
            df[f"{col}_d2"] = df[col].diff().diff()

        # ── Group B: rolling statistics ──────────────────────────────────────
        roll_cols = [c for c in RAW_SENSOR_COLS if c in df.columns]
        for col in roll_cols:
            roll_s = df[col].rolling(WIN_SHORT, min_periods=2)
            roll_l = df[col].rolling(WIN_LONG,  min_periods=12)
            df[f"{col}_rmean_2h"]   = roll_s.mean()
            df[f"{col}_rstd_2h"]    = roll_s.std()
            df[f"{col}_rrange_2h"]  = roll_s.max() - roll_s.min()
            df[f"{col}_rmean_24h"]  = roll_l.mean()
            df[f"{col}_rstd_24h"]   = roll_l.std()
            df[f"{col}_zscore_24h"] = (
                (df[col] - df[f"{col}_rmean_24h"]) /
                (df[f"{col}_rstd_24h"] + 1e-8)
            )

        # ── Group C: thermodynamic deltas ────────────────────────────────────
        df["CHW_delta_T"]    = df["CHW_Return"] - df["CHW_Supply"]
        df["CHW_delta_T_d1"] = df["CHW_delta_T"].diff()
        df["CHW_delta_T_d2"] = df["CHW_delta_T"].diff().diff()
        df["CW_delta_T"]     = df["CW_Return"]  - df["CW_Supply"]
        df["CW_delta_T_d1"]  = df["CW_delta_T"].diff()
        df["CHW_delta"]      = df["CHW_delta_T"]   # alias used in feature list
        df["CW_delta"]       = df["CW_delta_T"]    # alias used in feature list

        rla_phases = ["RLA_L1","RLA_L2","RLA_L3"]
        df["RLA_spread"]    = df[rla_phases].max(axis=1) - df[rla_phases].min(axis=1)
        df["RLA_spread_d1"] = df["RLA_spread"].diff()
        df["RLA_avg_calc"]  = df[rla_phases].mean(axis=1)
        df["RLA_imbalance"] = df["RLA_spread"]   # alias

        df["COP_proxy"]    = df["CHW_delta_T"] / (df["RLA_avg_calc"] / 100 + 1e-8)
        df["COP_proxy_d1"] = df["COP_proxy"].diff()
        df["Temp_ratio"]   = df["CHW_delta_T"] / (df["CW_delta_T"] + 1e-6)

        # ── Group D: cyclic time features ────────────────────────────────────
        df["hour"]              = df.index.hour
        df["day_of_week"]       = df.index.dayofweek
        df["month_num"]         = df.index.month
        df["is_weekend"]        = (df.index.dayofweek >= 5).astype(float)
        df["is_business_hours"] = (
            (df.index.hour >= 7) & (df.index.hour <= 19)
        ).astype(float)
        df["hour_sin"]  = np.sin(2 * np.pi * df["hour"]        / 24)
        df["hour_cos"]  = np.cos(2 * np.pi * df["hour"]        / 24)
        df["dow_sin"]   = np.sin(2 * np.pi * df["day_of_week"] /  7)
        df["dow_cos"]   = np.cos(2 * np.pi * df["day_of_week"] /  7)
        df["month_sin"] = np.sin(2 * np.pi * df["month_num"]   / 12)
        df["month_cos"] = np.cos(2 * np.pi * df["month_num"]   / 12)

        # ── Group E: current × RLA features ─────────────────────────────────
        cur_df   = df[["CURRENT_L1","CURRENT_L2","CURRENT_L3"]]
        cur_mean = cur_df.mean(axis=1)
        df["current_mean"]         = cur_mean
        df["current_imbalance"]    = (
            (cur_df.max(axis=1) - cur_df.min(axis=1)) / (cur_mean + 1e-8) * 100
        )
        df["current_std_phases"]   = cur_df.std(axis=1)
        df["current_imbalance_d1"] = df["current_imbalance"].diff()
        for rla_c, cur_c, tag in [
            ("RLA_L1","CURRENT_L1","L1"),
            ("RLA_L2","CURRENT_L2","L2"),
            ("RLA_L3","CURRENT_L3","L3"),
        ]:
            df[f"RLA_cur_ratio_{tag}"] = df[rla_c] / (df[cur_c] + 1e-8)

        # ── Group F: tower efficiency ─────────────────────────────────────────
        df["tower_tracking_error"]     = df["FEEDBACK"] - df["SIGNAL"]
        df["tower_tracking_error_abs"] = df["tower_tracking_error"].abs()
        df["tower_nonresponse_flag"]   = (
            (df["SIGNAL"] > 50) & (df["tower_tracking_error"] < -10)
        ).astype(float)

        # ── Group G (weather) + Group G (flow) ───────────────────────────────
        df["WB_roll_mean8"]     = df["WET_BULB"].rolling(8).mean()
        df["CW_approach_to_WB"] = df["CW_Supply"] - df["WET_BULB"]
        df["CW_sup_expected"]   = df["WB_roll_mean8"] + 6.0
        df["CW_sup_vs_expected"]= df["CW_Supply"] - df["CW_sup_expected"]

        df["total_flow"]         = df["PH1_FLOW"] + df["PH2_FLOW"]
        df["flow_imbalance"]     = (df["PH1_FLOW"] - df["PH2_FLOW"]).abs()
        df["flow_imbalance_pct"] = df["flow_imbalance"] / (df["total_flow"] + 1e-8) * 100
        df["cooling_tons_proxy"] = df["total_flow"] * df["CHW_delta_T"]
        df["tons_per_RLA"]       = df["cooling_tons_proxy"] / (df["RLA_Avg"] + 1e-8)

        # ── Group I: weather interaction ──────────────────────────────────────
        df["RLA_weather_norm"] = df["RLA_Avg"] / (df["WB_roll_mean8"] + 32 + 1e-8)

        # ── Group J: EWMA + persistence ──────────────────────────────────────
        df["RLA_EWMA_4h"]        = df["RLA_Avg"].ewm(span=EWMA_SPAN, adjust=False).mean()
        df["CHW_ret_EWMA_4h"]    = df["CHW_Return"].ewm(span=EWMA_SPAN, adjust=False).mean()
        df["CW_ret_EWMA_4h"]     = df["CW_Return"].ewm(span=EWMA_SPAN, adjust=False).mean()
        df["RLA_high_flag"]           = (df["RLA_Avg"] > 80).astype(float)
        df["RLA_high_persistence_4h"] = df["RLA_high_flag"].rolling(8).sum()
        df["RLA_high_persistence_8h"] = df["RLA_high_flag"].rolling(16).sum()

        # ── Group K: multi-day trend features ────────────────────────────────
        df["COP_7d_mean"]  = df["COP_proxy"].rolling(W7D, min_periods=48).mean()
        df["COP_7d_drift"] = df["COP_proxy"] - df["COP_7d_mean"]
        df["COP_3d_slope"] = (
            df["COP_proxy"].rolling(W3D, min_periods=24).mean() -
            df["COP_proxy"].rolling(W7D, min_periods=48).mean()
        )
        df["CW_approach_7d_mean"]  = df["CW_delta_T"].rolling(W7D, min_periods=48).mean()
        df["CW_approach_drift"]    = df["CW_delta_T"] - df["CW_approach_7d_mean"]
        df["CW_approach_3d_slope"] = (
            df["CW_delta_T"].rolling(W3D, min_periods=24).mean() -
            df["CW_delta_T"].rolling(W7D, min_periods=48).mean()
        )
        df["CHW_dT_7d_mean"]  = df["CHW_delta_T"].rolling(W7D, min_periods=48).mean()
        df["CHW_dT_drift"]    = df["CHW_delta_T"] - df["CHW_dT_7d_mean"]
        df["CHW_dT_3d_slope"] = (
            df["CHW_delta_T"].rolling(W3D, min_periods=24).mean() -
            df["CHW_delta_T"].rolling(W7D, min_periods=48).mean()
        )
        df["RLA_spread_7d_mean"]  = df["RLA_spread"].rolling(W7D, min_periods=48).mean()
        df["RLA_spread_drift"]    = df["RLA_spread"] - df["RLA_spread_7d_mean"]
        df["RLA_spread_3d_slope"] = (
            df["RLA_spread"].rolling(W3D, min_periods=24).mean() -
            df["RLA_spread"].rolling(W7D, min_periods=48).mean()
        )
        df["tower_err_3d_mean"] = df["tower_tracking_error_abs"].rolling(W3D, min_periods=24).mean()
        df["tower_err_7d_mean"] = df["tower_tracking_error_abs"].rolling(W7D, min_periods=48).mean()
        df["tower_err_drift"]   = df["tower_err_3d_mean"] - df["tower_err_7d_mean"]

        # Startup counter (stored per-row from update())
        df["readings_since_start"] = df["_readings_since_start"]

        # ── Extract latest row and build final feature vector ────────────────
        latest = df.iloc[-1]
        feat_vec = np.array(
            [latest.get(f, np.nan) for f in FEATURE_ORDER],
            dtype=np.float32
        )

        # Replace inf/-inf with nan then fill remaining NaN with 0
        feat_vec = np.where(np.isinf(feat_vec), np.nan, feat_vec)
        feat_vec = np.where(np.isnan(feat_vec), 0.0, feat_vec)

        # ── Scale using RobustScaler fitted on training data ─────────────────
        feat_scaled = self.scaler.transform(feat_vec.reshape(1, -1))
        return feat_scaled.astype(np.float32)
