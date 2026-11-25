"""Score synthetic chiller data with the deployed LOF model.

Reads a synthetic dataset CSV, selects the required 197 features in the
training order, scales with the ONNX scaler, runs the LOF model, and writes
back anomaly predictions.
"""

from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as rt
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from preprocessor import FEATURE_ORDER, WIN_LONG  # noqa: E402  single source of truth

SCRIPT_DIR = Path(__file__).resolve().parent
MODEL_DIR = SCRIPT_DIR.parent / "model"
SCALER_ONNX_PATH = MODEL_DIR / "scaler_model.onnx"
LOF_ONNX_PATH = MODEL_DIR / "lof_chiller_model.onnx"


def load_synthetic_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    for col in ("Unnamed: 0", "timestamp"):
        if col in df.columns:
            df = df.drop(columns=[col])
    return df


def prepare_features(df: pd.DataFrame) -> np.ndarray:
    missing = [col for col in FEATURE_ORDER if col not in df.columns]
    if missing:
        # Fail loudly: silently zero-filling features hides pipeline drift.
        raise ValueError(
            f"{len(missing)} model features missing from input, e.g. {missing[:5]}. "
            "Regenerate the dataset with app/mock_data_generator.py."
        )
    X = df.loc[:, FEATURE_ORDER].to_numpy(dtype=np.float32)
    return np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)


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
    # The live preprocessor only scores once 24 h of history exist (WIN_LONG
    # readings). Mark the same warm-up rows so summaries can exclude them.
    scored_df["is_warmup"] = np.arange(len(scored_df)) < WIN_LONG
    return scored_df


def summarize(scored_df: pd.DataFrame) -> str:
    """One-line anomaly-rate summary, excluding warm-up rows."""
    live = scored_df[~scored_df["is_warmup"]]
    n_anom = int(live["is_anomaly"].sum())
    return (
        f"{n_anom} of {len(live)} post-warm-up rows flagged as anomalies "
        f"({n_anom / max(len(live), 1):.1%}); {int(scored_df['is_warmup'].sum())} warm-up rows excluded"
    )


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
    print(summarize(scored))


if __name__ == "__main__":
    main()
