from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://perch:perch@localhost:5432/perch"
    redis_url: str = "redis://localhost:6379/0"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 7

    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    cookie_samesite: str = "lax"  # "none" when dashboard and API are cross-site (behind TLS)
    cookie_secure: bool = False

    model_config = {"env_prefix": "PERCH_"}


settings = Settings()
