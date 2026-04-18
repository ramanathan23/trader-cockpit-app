"""Feature extraction for ComfortScorer model."""

import logging
from datetime import date
from typing import Optional, Dict, Any

import numpy as np
import pandas as pd
import asyncpg

logger = logging.getLogger(__name__)


class FeatureExtractor:
    """Extract features from daily_scores and symbol_metrics tables."""
    
    # Feature names (28 dimensions)
    FEATURE_NAMES = [
        # Scores (5)
        'total_score', 'momentum_score', 'trend_score', 'volatility_score', 'structure_score',
        # RSI/MACD/ROC (6)
        'rsi_14', 'macd_hist', 'roc_5', 'roc_20', 'roc_60', 'vol_ratio_20',
        # Trend indicators (4)
        'adx_14', 'plus_di', 'minus_di', 'weekly_bias_encoded',
        # Volatility (7)
        'bb_squeeze', 'squeeze_days', 'nr7', 'atr_ratio', 'atr_5', 'bb_width', 'kc_width',
        # Structure (1)
        'rs_vs_nifty',
        # Additional context (5)
        'price_52w_proximity', 'sector_encoded', 'market_cap_log', 
        'avg_volume_log', 'liquidity_score'
    ]
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool
    
    async def build_features(
        self, 
        symbol: str, 
        date: date,
        context: Optional[Dict[str, Any]] = None
    ) -> np.ndarray:
        """Build 28-dim feature vector for a symbol on given date."""
        async with self.db_pool.acquire() as conn:
            # Get daily scores
            score_row = await conn.fetchrow("""
                SELECT 
                    total_score, momentum_score, trend_score, 
                    volatility_score, structure_score
                FROM daily_scores
                WHERE symbol = $1 AND score_date = $2
            """, symbol, date)
            
            if not score_row:
                raise ValueError(f"No scores found for {symbol} on {date}")
            
            # Get symbol metrics (indicators)
            metrics_row = await conn.fetchrow("""
                SELECT 
                    rsi_14, macd_hist, roc_5, roc_20, roc_60, vol_ratio_20,
                    adx_14, plus_di, minus_di, weekly_bias,
                    bb_squeeze, squeeze_days, nr7, atr_ratio, atr_5, 
                    bb_width, kc_width, rs_vs_nifty
                FROM symbol_metrics
                WHERE symbol = $1
            """, symbol)
            
            if not metrics_row:
                raise ValueError(f"No metrics found for {symbol}")
            
            # Get price data for additional context
            price_row = await conn.fetchrow("""
                SELECT close, volume
                FROM price_data_daily
                WHERE symbol = $1 AND date <= $2
                ORDER BY date DESC
                LIMIT 1
            """, symbol, date)
            
            # Get 52-week high for proximity
            high_52w_row = await conn.fetchrow("""
                SELECT MAX(high) as high_52w
                FROM price_data_daily
                WHERE symbol = $1 AND date <= $2 
                  AND date >= $2 - INTERVAL '252 days'
            """, symbol, date)
            
            # Build feature vector
            features = []
            
            # Scores (5)
            features.extend([
                float(score_row['total_score']),
                float(score_row['momentum_score']),
                float(score_row['trend_score']),
                float(score_row['volatility_score']),
                float(score_row['structure_score']),
            ])
            
            # Indicators (6)
            features.extend([
                float(metrics_row['rsi_14'] or 50.0),
                float(metrics_row['macd_hist'] or 0.0),
                float(metrics_row['roc_5'] or 0.0),
                float(metrics_row['roc_20'] or 0.0),
                float(metrics_row['roc_60'] or 0.0),
                float(metrics_row['vol_ratio_20'] or 1.0),
            ])
            
            # Trend (4)
            features.extend([
                float(metrics_row['adx_14'] or 20.0),
                float(metrics_row['plus_di'] or 20.0),
                float(metrics_row['minus_di'] or 20.0),
                self._encode_weekly_bias(metrics_row['weekly_bias']),
            ])
            
            # Volatility (7)
            features.extend([
                float(metrics_row['bb_squeeze'] or False),
                float(metrics_row['squeeze_days'] or 0),
                float(metrics_row['nr7'] or False),
                float(metrics_row['atr_ratio'] or 1.0),
                float(metrics_row['atr_5'] or 0.0),
                float(metrics_row['bb_width'] or 0.0),
                float(metrics_row['kc_width'] or 0.0),
            ])
            
            # Structure (1)
            features.append(float(metrics_row['rs_vs_nifty'] or 0.0))
            
            # Additional context (5)
            price_52w_proximity = 0.5
            if price_row and high_52w_row and high_52w_row['high_52w']:
                price_52w_proximity = float(price_row['close']) / float(high_52w_row['high_52w'])
            
            features.extend([
                price_52w_proximity,
                0.0,  # sector_encoded (TODO)
                np.log1p(1e9),  # market_cap_log (TODO)
                np.log1p(float(price_row['volume']) if price_row else 1e6),
                50.0,  # liquidity_score (TODO)
            ])
            
            return np.array(features, dtype=np.float32)
    
    @staticmethod
    def _encode_weekly_bias(bias: Optional[str]) -> float:
        """Encode weekly bias: BULLISH=1, NEUTRAL=0, BEARISH=-1."""
        if bias == "BULLISH":
            return 1.0
        elif bias == "BEARISH":
            return -1.0
        else:
            return 0.0
