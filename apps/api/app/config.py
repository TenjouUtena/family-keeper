from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Family Keeper API"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://familykeeper:familykeeper@localhost:5433/familykeeper"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Auth
    SECRET_KEY: str = "change-me-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "family-keeper"
    R2_PUBLIC_URL: str = ""  # optional custom domain

    # AI (Phase 5)
    ANTHROPIC_API_KEY: str = ""
    AI_RATE_LIMIT_PER_HOUR: int = 10

    # Google Calendar (Phase 5)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/v1/calendar/auth/google/callback"
    GOOGLE_AUTH_REDIRECT_URI: str = "http://localhost:8000/v1/auth/google/callback"
    FERNET_KEY: str = ""
    FRONTEND_URL: str = "http://localhost:3000"

    # Observability
    SENTRY_DSN: str = ""
    ENVIRONMENT: str = "development"

    # CORS
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
