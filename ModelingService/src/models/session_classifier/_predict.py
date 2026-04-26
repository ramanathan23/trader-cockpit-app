from __future__ import annotations

import pandas as pd

from ._features import FEATURES, SESSION_CLASSES


def feature_frame(row: dict) -> pd.DataFrame:
    data = {name: row.get(name) for name in FEATURES}
    df = pd.DataFrame([data], columns=FEATURES)
    df["prev_bb_squeeze"] = df["prev_bb_squeeze"].fillna(False).astype(int)
    for col in FEATURES:
        if col != "prev_bb_squeeze":
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df.fillna(-999)


def predict_session(classifier, pullback_regressor, row: dict) -> dict:
    X = feature_frame(row)
    probs = classifier.predict_proba(X)[0]
    best_idx = int(probs.argmax())
    session_type = SESSION_CLASSES[best_idx]
    pullback = None
    if pullback_regressor is not None and session_type == "TREND_UP":
        pullback = float(pullback_regressor.predict(X)[0])
        pullback = max(0.0, min(1.0, pullback))
    prob_by_class = {label: float(probs[idx]) for idx, label in enumerate(SESSION_CLASSES)}
    return {
        "session_type_pred": session_type,
        "trend_up_prob": prob_by_class.get("TREND_UP", 0.0),
        "trend_down_prob": prob_by_class.get("TREND_DOWN", 0.0),
        "chop_prob": prob_by_class.get("CHOP", 0.0),
        "volatile_prob": prob_by_class.get("VOLATILE", 0.0),
        "pullback_depth_pred": pullback,
    }
