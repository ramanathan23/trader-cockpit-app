from __future__ import annotations

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_error
from sklearn.model_selection import GroupShuffleSplit

from ._features import CATEGORICAL, FEATURES, SESSION_CLASSES
from ._labels import CLASS_TO_ID


def train_session_classifier(sessions_df: pd.DataFrame):
    import lightgbm as lgb

    clean = sessions_df.dropna(subset=["session_type", "session_date"]).copy()
    clean = clean[clean["session_type"].isin(SESSION_CLASSES)]
    if len(clean) < 100:
        raise ValueError("Need at least 100 training sessions for session classifier")

    X = _feature_frame(clean)
    y = clean["session_type"].map(CLASS_TO_ID)
    train_idx, test_idx = _split(X, y, clean["session_date"])

    model = lgb.LGBMClassifier(
        objective="multiclass",
        num_class=len(SESSION_CLASSES),
        num_leaves=63,
        learning_rate=0.05,
        feature_fraction=0.8,
        bagging_fraction=0.8,
        bagging_freq=5,
        min_child_samples=30,
        n_estimators=500,
        verbosity=-1,
    )
    model.fit(
        X.iloc[train_idx],
        y.iloc[train_idx],
        eval_set=[(X.iloc[test_idx], y.iloc[test_idx])],
        categorical_feature=CATEGORICAL,
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(50)],
    )
    pred = model.predict(X.iloc[test_idx])
    return model, {
        "accuracy": round(float(accuracy_score(y.iloc[test_idx], pred)), 4),
        "class_report": classification_report(
            y.iloc[test_idx],
            pred,
            target_names=SESSION_CLASSES,
            output_dict=True,
            zero_division=0,
        ),
    }


def train_pullback_regressor(sessions_df: pd.DataFrame):
    import lightgbm as lgb

    up_days = sessions_df.dropna(subset=["pullback_depth", "session_date"]).copy()
    if len(up_days) < 50:
        raise ValueError("Need at least 50 up-day sessions for pullback regressor")

    X = _feature_frame(up_days)
    y = up_days["pullback_depth"].astype(float)
    train_idx, test_idx = _split(X, y, up_days["session_date"])

    model = lgb.LGBMRegressor(
        objective="regression",
        num_leaves=31,
        learning_rate=0.05,
        feature_fraction=0.8,
        min_child_samples=20,
        n_estimators=400,
        verbosity=-1,
    )
    model.fit(
        X.iloc[train_idx],
        y.iloc[train_idx],
        eval_set=[(X.iloc[test_idx], y.iloc[test_idx])],
        callbacks=[lgb.early_stopping(30, verbose=False)],
    )
    mae = mean_absolute_error(y.iloc[test_idx], model.predict(X.iloc[test_idx]))
    return model, {"mae": round(float(mae), 4)}


def _feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    X = df.reindex(columns=FEATURES).copy()
    X["prev_bb_squeeze"] = X["prev_bb_squeeze"].fillna(False).astype(int)
    for col in FEATURES:
        if col != "prev_bb_squeeze":
            X[col] = pd.to_numeric(X[col], errors="coerce")
    return X.fillna(-999)


def _split(X: pd.DataFrame, y, groups):
    splitter = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
    return next(splitter.split(X, y, groups))
