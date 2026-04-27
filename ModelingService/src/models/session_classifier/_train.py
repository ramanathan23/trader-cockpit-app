from __future__ import annotations

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, mean_absolute_error

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
    sample_weight = _balanced_weights(y.iloc[train_idx])

    model = lgb.LGBMClassifier(
        objective="multiclass",
        num_class=len(SESSION_CLASSES),
        num_leaves=31,
        max_depth=8,
        learning_rate=0.05,
        feature_fraction=0.8,
        bagging_fraction=0.8,
        bagging_freq=5,
        min_child_samples=150,
        reg_alpha=0.05,
        reg_lambda=0.25,
        n_estimators=800,
        verbosity=-1,
    )
    model.fit(
        X.iloc[train_idx],
        y.iloc[train_idx],
        sample_weight=sample_weight,
        eval_set=[(X.iloc[test_idx], y.iloc[test_idx])],
        categorical_feature=CATEGORICAL,
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(50)],
    )
    pred = model.predict(X.iloc[test_idx])
    labels = list(range(len(SESSION_CLASSES)))
    predicted_distribution = pd.Series(pred).value_counts().reindex(labels, fill_value=0)
    return model, {
        "accuracy": round(float(accuracy_score(y.iloc[test_idx], pred)), 4),
        "predicted_distribution": {
            SESSION_CLASSES[idx]: int(predicted_distribution[idx])
            for idx in labels
        },
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


def evaluate_session_models(classifier, pullback_regressor, sessions_df: pd.DataFrame) -> dict:
    clean = sessions_df.dropna(subset=["session_type", "session_date"]).copy()
    clean = clean[clean["session_type"].isin(SESSION_CLASSES)]
    if len(clean) < 100:
        raise ValueError("Need at least 100 training sessions for session classifier evaluation")

    X = _feature_frame(clean)
    y = clean["session_type"].map(CLASS_TO_ID)
    _, test_idx = _split(X, y, clean["session_date"])
    y_test = y.iloc[test_idx]
    pred = classifier.predict(X.iloc[test_idx])

    labels = list(range(len(SESSION_CLASSES)))
    matrix = confusion_matrix(y_test, pred, labels=labels)
    distribution = clean["session_type"].value_counts().reindex(SESSION_CLASSES, fill_value=0)
    predicted_distribution = pd.Series(pred).value_counts().reindex(labels, fill_value=0)

    result = {
        "samples": int(len(clean)),
        "test_samples": int(len(test_idx)),
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "label_distribution": {label: int(distribution[label]) for label in SESSION_CLASSES},
        "predicted_distribution": {
            SESSION_CLASSES[idx]: int(predicted_distribution[idx])
            for idx in labels
        },
        "confusion_matrix": {
            "labels": SESSION_CLASSES,
            "matrix": matrix.astype(int).tolist(),
        },
        "class_report": classification_report(
            y_test,
            pred,
            target_names=SESSION_CLASSES,
            output_dict=True,
            zero_division=0,
        ),
    }

    if pullback_regressor is not None:
        up_days = sessions_df.dropna(subset=["pullback_depth", "session_date"]).copy()
        if len(up_days) >= 50:
            X_pb = _feature_frame(up_days)
            y_pb = up_days["pullback_depth"].astype(float)
            _, pb_test_idx = _split(X_pb, y_pb, up_days["session_date"])
            pb_pred = pullback_regressor.predict(X_pb.iloc[pb_test_idx])
            result["pullback"] = {
                "samples": int(len(up_days)),
                "test_samples": int(len(pb_test_idx)),
                "mae": round(float(mean_absolute_error(y_pb.iloc[pb_test_idx], pb_pred)), 4),
            }

    return result


def _feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    X = df.reindex(columns=FEATURES).copy()
    X["prev_bb_squeeze"] = X["prev_bb_squeeze"].fillna(False).astype(int)
    for col in FEATURES:
        if col != "prev_bb_squeeze":
            X[col] = pd.to_numeric(X[col], errors="coerce")
    return X.fillna(-999)


def _split(X: pd.DataFrame, y, groups):
    dates = pd.Series(pd.to_datetime(groups).dt.date.unique()).sort_values().tolist()
    if len(dates) < 5:
        split_at = max(1, int(len(X) * 0.8))
        return list(range(split_at)), list(range(split_at, len(X)))

    cutoff = dates[max(1, int(len(dates) * 0.8)) - 1]
    group_dates = pd.Series(pd.to_datetime(groups).dt.date.to_numpy())
    train_idx = group_dates[group_dates <= cutoff].index.tolist()
    test_idx = group_dates[group_dates > cutoff].index.tolist()
    if not train_idx or not test_idx:
        split_at = max(1, int(len(X) * 0.8))
        return list(range(split_at)), list(range(split_at, len(X)))
    return train_idx, test_idx


def _balanced_weights(y: pd.Series) -> pd.Series:
    counts = y.value_counts()
    total = float(len(y))
    class_count = float(len(counts))
    weights = y.map(lambda cls: total / (class_count * float(counts[cls])))
    return weights.clip(lower=0.55, upper=3.0)
