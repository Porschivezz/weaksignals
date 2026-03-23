from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://weaksignals:weaksignals@db:5432/weaksignals"
    SYNC_DATABASE_URL: str = "postgresql://weaksignals:weaksignals@db:5432/weaksignals"
    REDIS_URL: str = "redis://redis:6379/0"
    NEO4J_URI: str = "bolt://neo4j:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"
    ANTHROPIC_API_KEY: str = ""
    COHERE_API_KEY: str = ""
    JWT_SECRET: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION: int = 3600

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
