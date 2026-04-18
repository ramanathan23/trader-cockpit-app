"""Training dataset builder and LightGBM trainer for ComfortScorer."""

import logging
from datetime import date, timedelta
from typing import Tuple

import numpy as np
import pandas as pd
import asyncpg
import lightgbm as lgb

logger = logging.getLogger(__name__)


class ComfortScorerTrainer:
    """Build training dataset and train LightGBM model."""
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def build_dataset(
        self, 
        start_date: date, 
        end_date: date
    ) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Build training dataset from historical scores + forward outcomes.
        
        For each (symbol, date) with a score:
        - Features: all score components + indicators
        - Target: comfort_score computed from next 5 trading days
        
        Args:
            start_date: Training data start
            end_date: Training data end (must be at least 7 days before today)
            
        Returns:
            (X_df, y_series) - features and targets
        """
        logger.info(f"Building training dataset: {start_date} to {end_date}")
        
        async with self.db_pool.acquire() as conn:
            # Get all scored symbols and dates in range
            rows = await conn.fetch("""
                SELECT 
                    ds.symbol,
                    ds.score_date,
                    ds.total_score, ds.momentum_score, ds.trend_score,
                    ds.volatility_score, ds.structure_score,
                    sm.rsi_14, sm.macd_hist, sm.roc_5, sm.roc_20, sm.roc_60,
                    sm.vol_ratio_20, sm.adx_14, sm.plus_di, sm.minus_di,
                    sm.weekly_bias, sm.bb_squeeze, sm.squeeze_days, sm.nr7,
                    sm.atr_ratio, sm.atr_5, sm.bb_width, sm.kc_width,
                    sm.rs_vs_nifty
                FROM daily_scores ds
                JOIN symbol_metrics sm ON ds.symbol = sm.symbol
                WHERE ds.score_date >= $1 
                  AND ds.score_date <= $2
                  AND ds.total_score > 50  -- Focus on higher scores
                ORDER BY ds.score_date, ds.symbol
            """, start_date, end_date)
        
        logger.info(f"Found {len(rows)} scored samples")
        
        # Build features and targets
        X_data = []
        y_data = []
        
        for row in rows:
            symbol = row['symbol']
            pred_date = row['score_date']
            
            # Compute target: forward 5-day comfort score
            comfort = await self._compute_forward_comfort(symbol, pred_date)
            
            if comfort is None:
                continue  # Skip if insufficient forward data
            
            # Build feature vector
            features = self._extract_features_from_row(row)
            
            X_data.append(features)
            y_data.append(comfort)
        
        logger.info(f"Built {len(X_data)} training samples")
        
        X_df = pd.DataFrame(X_data)
        y_series = pd.Series(y_data, name='comfort_score')
        
        return X_df, y_series
    
    async def _compute_forward_comfort(
        self, 
        symbol: str, 
        prediction_date: date
    ) -> float | None:
        """
        Compute comfort score from next 5 trading days.
        
        Comfort = weighted average of:
        - Return quality (40%)
        - Drawdown quality (30%)
        - Volatility quality (20%)
        - Momentum sustained (10%)
        """
        async with self.db_pool.acquire() as conn:
            # Get next 5 trading days OHLCV
            rows = await conn.fetch("""
                SELECT date, open, high, low, close, volume
                FROM price_data_daily
                WHERE symbol = $1 
                  AND date > $2
                ORDER BY date
                LIMIT 5
            """, symbol, prediction_date)
        
        if len(rows) < 5:
            return None  # Insufficient data
        
        df = pd.DataFrame(rows)
        
        # Compute metrics
        returns = df['close'].pct_change().dropna()
        total_return = (df['close'].iloc[-1] / df['close'].iloc[0] - 1) * 100
        
        # Max drawdown (intraday)
        max_dd = 0.0
        peak = df['close'].iloc[0]
        for _, row in df.iterrows():
            peak = max(peak, row['high'])
            dd = (row['low'] - peak) / peak * 100
            max_dd = min(max_dd, dd)
        
        # Volatility
        volatility = returns.std() * 100
        
        # Momentum sustained
        momentum_sustained = 1.0 if df['close'].iloc[-1] > df['close'].iloc[0] else 0.0
        
        # Normalize to 0-100 scales
        return_quality = self._normalize_return(total_return)
        drawdown_quality = self._normalize_drawdown(abs(max_dd))
        volatility_quality = self._normalize_volatility(volatility)
        
        # Weighted comfort score
        comfort = (
            0.40 * return_quality +
            0.30 * drawdown_quality +
            0.20 * volatility_quality +
            0.10 * momentum_sustained * 100
        )
        
        return round(float(comfort), 2)
    
    @staticmethod
    def _normalize_return(ret: float) -> float:
        """Map return % to 0-100 quality score."""
        if ret > 3.0:
            return 100.0
        elif ret > 0.0:
            return 50.0 + (ret / 3.0) * 50.0
        elif ret > -2.0:
            return 25.0 + (ret / -2.0) * 25.0
        else:
            return 0.0
    
    @staticmethod
    def _normalize_drawdown(dd_pct: float) -> float:
        """Map drawdown % to 0-100 quality score (lower DD = higher score)."""
        if dd_pct < 1.0:
            return 100.0
        elif dd_pct < 3.0:
            return 100.0 - (dd_pct - 1.0) / 2.0 * 30.0
        elif dd_pct < 5.0:
            return 70.0 - (dd_pct - 3.0) / 2.0 * 30.0
        else:
            return max(0.0, 40.0 - (dd_pct - 5.0) * 8.0)
    
    @staticmethod
    def _normalize_volatility(vol_pct: float) -> float:
        """Map daily volatility % to 0-100 quality score (lower vol = higher score)."""
        if vol_pct < 1.5:
            return 100.0
        elif vol_pct < 3.0:
            return 100.0 - (vol_pct - 1.5) / 1.5 * 50.0
        else:
            return max(0.0, 50.0 - (vol_pct - 3.0) * 16.0)
    
    @staticmethod
    def _extract_features_from_row(row) -> list:
        """Extract features from DB row (simplified, matches features.py order)."""
        return [
            # Scores (5)
            float(row['total_score']),
            float(row['momentum_score']),
            float(row['trend_score']),
            float(row['volatility_score']),
            float(row['structure_score']),
            # Indicators (6)
            float(row['rsi_14'] or 50.0),
            float(row['macd_hist'] or 0.0),
            float(row['roc_5'] or 0.0),
            float(row['roc_20'] or 0.0),
            float(row['roc_60'] or 0.0),
            float(row['vol_ratio_20'] or 1.0),
            # Trend (4)
            float(row['adx_14'] or 20.0),
            float(row['plus_di'] or 20.0),
            float(row['minus_di'] or 20.0),
            1.0 if row['weekly_bias'] == 'BULLISH' else (-1.0 if row['weekly_bias'] == 'BEARISH' else 0.0),
            # Volatility (7)
            float(row['bb_squeeze'] or False),
            float(row['squeeze_days'] or 0),
            float(row['nr7'] or False),
            float(row['atr_ratio'] or 1.0),
            float(row['atr_5'] or 0.0),
            float(row['bb_width'] or 0.0),
            float(row['kc_width'] or 0.0),
            # Structure (1)
            float(row['rs_vs_nifty'] or 0.0),
            # Context (5) - simplified for training
            0.8, 0.0, 20.0, 15.0, 50.0
        ]
    
    @staticmethod
    def train_lightgbm(
        X: pd.DataFrame, 
        y: pd.Series,
        val_split: float = 0.2
    ) -> Tuple[lgb.Booster, dict]:
        """
        Train LightGBM regression model.
        
        Args:
            X: Feature dataframe
            y: Target series
            val_split: Validation set fraction
            
        Returns:
            (trained_model, metrics_dict)
        """
        logger.info(f"Training LightGBM on {len(X)} samples")
        
        # Train/val split
        split_idx = int(len(X) * (1 - val_split))
        X_train, X_val = X.iloc[:split_idx], X.iloc[split_idx:]
        y_train, y_val = y.iloc[:split_idx], y.iloc[split_idx:]
        
        # Create datasets
        train_data = lgb.Dataset(X_train, label=y_train)
        val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
        
        # Parameters
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
        
        # Train
        model = lgb.train(
            params,
            train_data,
            num_boost_round=500,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'val'],
            callbacks=[
                lgb.early_stopping(stopping_rounds=50, verbose=False),
                lgb.log_evaluation(period=0),  # Disable verbose logging
            ],
        )
        
        # Compute metrics
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
        
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
