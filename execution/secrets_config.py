
from pydantic_settings import BaseSettings, SettingsConfigDict

class ExecutionSecrets(BaseSettings):
    """
    SECRETS ONLY for Execution Gateway.
    These should NEVER be loaded by Ingest/Scoring services.
    """
    BROKER_API_KEY: str = "restricted_key"
    BROKER_API_SECRET: str = "restricted_secret"
    
    # 2FA / Gating Secrets
    GATING_SECRET_KEY: str = "super_secret_gating_key_123"

    model_config = SettingsConfigDict(env_file=".secrets.env")
