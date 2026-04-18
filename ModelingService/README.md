# ModelingService

ML model hosting and management service for trader-cockpit.

## Purpose

Centralized service for all ML models used in trading system:
- **ComfortScorer**: Predicts hold comfort score (0-100) for stocks
- **RegimeClassifier**: Detects market regime (trending/ranging/volatile)
- **PatternDetector**: Identifies chart patterns (flags, head-shoulders, etc)
- **PricePredictor**: (Future) LSTM-based price prediction

## Architecture

```
ModelingService/
├── core/              # Base classes, registry, feature store
├── models/            # Individual model implementations
│   ├── comfort_scorer/
│   ├── regime_classifier/
│   └── pattern_detector/
├── services/          # Shared services (training, monitoring)
├── repositories/      # DB access
└── api/               # REST endpoints
```

## Key Features

- **Model Registry**: Pluggable architecture for easy model addition
- **Versioning**: Multiple versions per model with champion/shadow modes
- **A/B Testing**: Shadow mode for new models before promotion
- **Drift Monitoring**: Automatic performance tracking and retrain triggers
- **Feedback Loops**: Capture actual outcomes for continuous improvement

## API Endpoints

### Prediction
```bash
POST /api/v1/models/{model_name}/predict
{
  "symbols": ["RELIANCE", "TCS"],
  "date": "2026-04-18"
}
```

### Training
```bash
POST /api/v1/models/{model_name}/retrain
{
  "start_date": "2023-01-01",
  "end_date": "2026-04-01",
  "reason": "drift_detected"
}
```

### Monitoring
```bash
GET /api/v1/models/{model_name}/metrics?days=30
```

### Management
```bash
GET /api/v1/models                        # List all models
POST /api/v1/models/{name}/promote        # Promote shadow to champion
POST /api/v1/models/{name}/rollback       # Rollback to previous version
```

## Model Storage

Models stored in Docker volume `/models`:
```
/models/
├── comfort_scorer/
│   ├── v1/
│   ├── v2/
│   └── active -> v1
├── regime_classifier/
│   └── v1/
└── pattern_detector/
    └── v1/
```

## Development

```bash
# Run tests
pytest tests/

# Start service locally
uvicorn src.main:app --reload --port 8004
```

## Environment Variables

See `config.py` for full list. Key vars:
- `MODEL_BASE_PATH`: Model storage location (default: /models)
- `AUTO_RETRAIN_ENABLED`: Enable automatic retraining (default: true)
- `MAX_MODEL_AGE_DAYS`: Force retrain after N days (default: 90)
