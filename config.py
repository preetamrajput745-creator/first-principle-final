from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # --- Infrastructure ---
    # S3 / MinIO
    S3_ENDPOINT_URL: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_TICKS: str = "data"  # Root bucket, paths will be ticks/...
    S3_BUCKET_FEATURES: str = "data"
    S3_BUCKET_BOOKS: str = "data"
    
    # Redis (Event Bus)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    
    # Postgres (Metadata DB)
    # DB_HOST: str = "localhost"
    # DB_PORT: int = 5432
    # DB_USER: str = "postgres"
    # DB_PASSWORD: str = "postgres"
    # DB_NAME: str = "false_breakout"
    
    # SQLite (Local Demo)
    # SQLite (Local Demo)
    DATABASE_URL: str = "sqlite:///./sql_app.db"

    # --- Automation Config ---
    PAPER_MODE: bool = True
    SYMBOLS: list[str] = ["NIFTY_FUT", "BANKNIFTY_FUT", "BTCUSDT"]
    
    # Scoring Parameters
    WICK_RATIO_THRESHOLD: float = 0.7
    VOL_RATIO_THRESHOLD: float = 0.6
    POKE_TICK_BUFFER: float = 0.05 # % of ATR or fixed ticks, logic to be defined
    
    # Weights
    WEIGHT_WICK: int = 30
    WEIGHT_VOL: int = 20
    WEIGHT_POKE: int = 10
    WEIGHT_BOOK_CHURN: int = 20
    WEIGHT_DELTA: int = 20
    
    TRIGGER_SCORE: int = 70
    
    # Simulation / Safety
    SLIPPAGE_BASE: float = 0.0002
    SLIPPAGE_VOL_COEFF: float = 1.0
    HEARTBEAT_INTERVAL_MS: int = 5000
    
    # Circuit Breaker
    MAX_DAILY_LOSS: float = 1000.0
    MAX_SIGNALS_PER_HOUR: int = 10

    # PHASE A - RELEASE FLAGS
    EXECUTION_MODE: str = "SIMULATION" # Default safe
    ALLOW_BROKER_KEYS: bool = False
    HUMAN_GATING_COUNT: int = 5
    REQUIRE_2FA_FOR_LIVE: bool = False
    MAX_RISK_PER_TRADE: float = 0.005
    CANARY_SYMBOLS: list[str] = []
    SNAPSHOT_RETENTION_HOT_DAYS: int = 30
    TIME_DRIFT_THRESHOLD_MS: int = 500
    SLIPPAGE_BASELINE_COEFF: float = 0.0002

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
