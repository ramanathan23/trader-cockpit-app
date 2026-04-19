"""LightGBM training function."""

import logging
from typing import Tuple

import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

logger = logging.getLogger(__name__)


def train_lightgbm(
    X: pd.DataFrame,
    y: pd.Series,
    val_split: float = 0.2,
) -> Tuple[lgb.Booster, dict]:
    """Train LightGBM regression model."""
    logger.info(f"Training LightGBM on {len(X)} samples")

    split_idx = int(len(X) * (1 - val_split))
    X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]

    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)

    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'max_depth': 6,
        'learning_rate': 0.05,
        'feature_fraction': 0.8,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
    }

    model = lgb.train(
        params,
        train_data,
        num_boost_round=500,
        valid_sets=[train_data, val_data],
        valid_names=['train', 'val'],
        callbacks=[
            lgb.early_stopping(stopping_rounds=50, verbose=False),
            lgb.log_evaluation(period=0),
        ],
    )

    y_pred = model.predict(X_val)
    metrics = {
        'rmse': float(mean_squared_error(y_val, y_pred, squared=False)),
        'mae': float(mean_absolute_error(y_val, y_pred)),
        'r2': float(r2_score(y_val, y_pred)),
        'train_samples': len(X_train),
        'val_samples': len(X_val),
    }

    logger.info(f"Training complete. RMSE: {metrics['rmse']:.2f}, R2: {metrics['r2']:.3f}")
    return model, metrics
