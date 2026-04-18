-- ModelingService Database Schema
-- Unified schema for all ML models with flexible JSONB storage

-- Model registry and versioning
CREATE TABLE IF NOT EXISTS model_registry (
    model_name TEXT,
    version TEXT,
    model_type TEXT,        -- 'regression', 'classification', 'clustering'
    framework TEXT,         -- 'lightgbm', 'sklearn', 'pytorch'
    trained_at TIMESTAMPTZ NOT NULL,
    is_active BOOLEAN DEFAULT FALSE,
    is_shadow BOOLEAN DEFAULT FALSE,
    file_path TEXT,
    feature_count INT,
    feature_names JSONB,    -- Array of feature names
    metadata JSONB,         -- Flexible storage for model-specific config
    PRIMARY KEY (model_name, version)
);

CREATE INDEX IF NOT EXISTS idx_model_registry_active 
    ON model_registry(model_name, is_active) WHERE is_active = TRUE;

-- Unified predictions table (all models)
CREATE TABLE IF NOT EXISTS model_predictions (
    id BIGSERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    symbol TEXT NOT NULL,
    prediction_date DATE NOT NULL,
    predictions JSONB NOT NULL,   -- Flexible: {comfort_score: 75.2}, {regime: "TRENDING_BULL"}, etc
    confidence REAL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (model_name, symbol, prediction_date)
);

CREATE INDEX IF NOT EXISTS idx_predictions_model 
    ON model_predictions(model_name, prediction_date DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_symbol 
    ON model_predictions(symbol, prediction_date DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_created 
    ON model_predictions(created_at DESC);

-- Feedback / actual outcomes (all models)
CREATE TABLE IF NOT EXISTS model_feedback (
    id BIGSERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    prediction_id BIGINT REFERENCES model_predictions(id),
    symbol TEXT NOT NULL,
    prediction_date DATE NOT NULL,
    outcome_date DATE NOT NULL,
    predicted_values JSONB NOT NULL,    -- What was predicted
    actual_values JSONB NOT NULL,       -- What actually happened
    prediction_error REAL,              -- Main error metric
    metrics JSONB,                      -- Model-specific metrics
    recorded_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_feedback_model 
    ON model_feedback(model_name, outcome_date DESC);
CREATE INDEX IF NOT EXISTS idx_feedback_prediction 
    ON model_feedback(prediction_id);

-- Performance tracking (all models)
CREATE TABLE IF NOT EXISTS model_performance (
    model_name TEXT,
    model_version TEXT,
    metric_date DATE,
    sample_count INT,
    metrics JSONB,          -- RMSE, MAE, R2, accuracy, precision, etc (model-specific)
    PRIMARY KEY (model_name, model_version, metric_date)
);

CREATE INDEX IF NOT EXISTS idx_performance_date 
    ON model_performance(model_name, metric_date DESC);

-- Retrain history
CREATE TABLE IF NOT EXISTS model_training_history (
    id BIGSERIAL PRIMARY KEY,
    model_name TEXT NOT NULL,
    version TEXT NOT NULL,
    trigger_reason TEXT,    -- 'drift', 'scheduled', 'manual', 'initial'
    train_start TIMESTAMPTZ,
    train_end TIMESTAMPTZ,
    train_samples INT,
    validation_metrics JSONB,
    status TEXT,            -- 'running', 'completed', 'failed'
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_training_history_model 
    ON model_training_history(model_name, created_at DESC);
