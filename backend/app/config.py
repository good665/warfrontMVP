from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

DEV_JWT_SECRET = "dev-only-change-me"


class Settings(BaseSettings):
    database_url: str = "sqlite:///./warfront.db"
    allowed_origins: str = "http://localhost:3000"
    environment: Literal["dev", "prod"] = "dev"
    jwt_secret: str = DEV_JWT_SECRET
    jwt_expire_minutes: int = 60 * 24 * 30
    # 운영에서는 Alembic 마이그레이션을 쓰고 false 로 둔다.
    auto_create_tables: bool = True
    public_test_mode: bool = False
    test_access_key: str = ""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def _check_prod_secret(self) -> "Settings":
        placeholders = {DEV_JWT_SECRET, "change-me-to-a-long-random-string", "changeme"}
        if self.environment == "prod" and (self.jwt_secret in placeholders or len(self.jwt_secret.encode()) < 32):
            raise ValueError("JWT_SECRET must be a non-placeholder secret of at least 32 bytes in prod")
        if self.public_test_mode and (self.environment != "prod" or len(self.test_access_key.encode()) < 24):
            raise ValueError("PUBLIC_TEST_MODE requires ENVIRONMENT=prod and a TEST_ACCESS_KEY of at least 24 bytes")
        return self


settings = Settings()
