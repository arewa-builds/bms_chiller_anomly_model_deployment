"""Score synthetic chiller data with the deployed LOF model.

Reads a synthetic dataset CSV, selects the required 197 features in the
training order, scales with the ONNX scaler, runs the LOF model, and writes
back anomaly predictions.
"""

from __future__ import annotations

from argparse import ArgumentParser
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as rt
import pandas as pd

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
    'WET_BULB_zscore_24h','FEEDBACK_rmean_2h','FEEDBACK_rstd_2h',
    'FEEDBACK_rrange_2h','FEEDBACK_rmean_24h','FEEDBACK_rstd_24h',
    'FEEDBACK_zscore_24h','SIGNAL_rmean_2h','SIGNAL_rstd_2h',
    'SIGNAL_rrange_2h','SIGNAL_rmean_24h','SIGNAL_rstd_24h',
    'SIGNAL_zscore_24h','CURRENT_L1_rmean_2h','CURRENT_L1_rstd_2h',
    'CURRENT_L1_rrange_2h','CURRENT_L1_rmean_24h','CURRENT_L1_rstd_24h',
    'CURRENT_L1_zscore_24h','CURRENT_L2_rmean_2h','CURRENT_L2_rstd_2h',
    'CURRENT_L2_rrange_2h','CURRENT_L2_rmean_24h','CURRENT_L2_rstd_24h',
    'CURRENT_L2_zscore_24h','CURRENT_L3_rmean_2h','CURRENT_L3_rstd_2h',
    'CURRENT_L3_rrange_2h','CURRENT_L3_rmean_24h','CURRENT_L3_rstd_24h',
    'CURRENT_L3_zscore_24h','CHW_delta_T','CHW_delta_T_d1','CHW_delta_T_d2',
    'CW_delta_T','CW_delta_T_d1','RLA_spread','RLA_spread_d1',
    'RLA_avg_calc','COP_proxy','COP_proxy_d1','Temp_ratio','is_weekend',
    'is_business_hours','hour_sin','hour_cos','dow_sin','dow_cos',
    'month_sin','month_cos','current_mean','current_imbalance',
    'current_std_phases','current_imbalance_d1','RLA_cur_ratio_L1',
    'RLA_cur_ratio_L2','RLA_cur_ratio_L3','tower_tracking_error',
    'tower_tracking_error_abs','tower_nonresponse_flag','CW_approach_to_WB',
    'CW_sup_vs_expected','total_flow','flow_imbalance','flow_imbalance_pct',
    'cooling_tons_proxy','tons_per_RLA','RLA_weather_norm','RLA_EWMA_4h',
    'CHW_ret_EWMA_4h','CW_ret_EWMA_4h','RLA_high_persistence_4h',
    'RLA_high_persistence_8h','COP_7d_mean','COP_7d_drift','COP_3d_slope',
    'CW_approach_7d_mean','CW_approach_drift','CW_approach_3d_slope',
    'CHW_dT_7d_mean','CHW_dT_drift','CHW_dT_3d_slope',
    'RLA_spread_7d_mean','RLA_spread_drift','RLA_spread_3d_slope',
    'tower_err_3d_mean','tower_err_7d_mean','tower_err_drift',
    'readings_since_start',
]

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_DIR = SCRIPT_DIR.parent / "model"
SCALER_ONNX_PATH = MODEL_DIR / "scaler_model.onnx"
LOF_ONNX_PATH = MODEL_DIR / "lof_chiller_model.onnx"


def load_synthetic_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    if "Unnamed: 0" in df.columns:
        df = df.drop(columns=["Unnamed: 0"])
    return df


def _add_missing_engineered_features(df: pd.DataFrame) -> pd.DataFrame:
    enriched = df.copy()

    if "current_imbalance_d1" not in enriched.columns:
        if "current_imbalance" in enriched.columns:
            enriched["current_imbalance_d1"] = enriched["current_imbalance"].diff()
        else:
            enriched["current_imbalance_d1"] = 0.0

    for tag, rla_col, cur_col in [
        ("L1", "RLA_L1", "CURRENT_L1"),
        ("L2", "RLA_L2", "CURRENT_L2"),
        ("L3", "RLA_L3", "CURRENT_L3"),
    ]:
        target_col = f"RLA_cur_ratio_{tag}"
        if target_col not in enriched.columns:
            if rla_col in enriched.columns and cur_col in enriched.columns:
                enriched[target_col] = enriched[rla_col] / (enriched[cur_col] + 1e-8)
            else:
                enriched[target_col] = 0.0

    return enriched


def prepare_features(df: pd.DataFrame) -> np.ndarray:
    enriched_df = _add_missing_engineered_features(df)

    missing = [col for col in FEATURE_ORDER if col not in enriched_df.columns]
    for col in missing:
        enriched_df[col] = 0.0

    X = enriched_df.loc[:, FEATURE_ORDER].to_numpy(dtype=np.float32)
    return X


def run_onnx_session(session: rt.InferenceSession, input_array: np.ndarray) -> list[Any]:
    input_name = session.get_inputs()[0].name
    return session.run(None, {input_name: input_array.astype(np.float32)})


def score_dataset(
    synthetic_df: pd.DataFrame,
    scaler_path: Path = SCALER_ONNX_PATH,
    model_path: Path = LOF_ONNX_PATH,
) -> pd.DataFrame:
    X = prepare_features(synthetic_df)

    scaler_session = rt.InferenceSession(str(scaler_path))
    scaler_output = run_onnx_session(scaler_session, X)
    X_scaled = np.asarray(scaler_output[0], dtype=np.float32)

    model_session = rt.InferenceSession(str(model_path))
    outputs = run_onnx_session(model_session, X_scaled)

    # ONNX session order is typically [label, scores, score_samples]
    labels = np.asarray(outputs[0]).flatten()
    scores = np.asarray(outputs[1]).flatten()

    scored_df = synthetic_df.copy()
    scored_df["decision_score"] = scores
    scored_df["label"] = labels.astype(int)
    scored_df["is_anomaly"] = scored_df["label"] == -1
    return scored_df


def parse_args() -> Any:
    parser = ArgumentParser(
        description="Score synthetic chiller dataset with the LOF model."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=SCRIPT_DIR.parent / "synthetic_chiller_data.csv",
        help="Path to the synthetic dataset CSV.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=SCRIPT_DIR.parent / "synthetic_chiller_data_scored.csv",
        help="Path for the scored output CSV.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    synthetic_path = args.input.resolve()
    output_path = args.output.resolve()

    if not synthetic_path.exists():
        raise FileNotFoundError(f"Synthetic dataset not found: {synthetic_path}")

    df = load_synthetic_csv(synthetic_path)
    scored = score_dataset(df)
    scored.to_csv(output_path, index=False)
    print(f"Wrote scored dataset with anomaly labels: {output_path}")


if __name__ == "__main__":
    main()
