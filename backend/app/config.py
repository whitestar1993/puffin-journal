"""Runtime configuration, read from environment variables (see .env.example)."""

from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    app_username: str = "me"
    # Either a plain password (hashed in memory at startup) ...
    app_password: str = ""
    # ... or an argon2 hash from `python -m app.cli hash-password` (wins if both set).
    app_password_hash: str = ""
    # Optional; auto-generated into DATA_DIR/secret_key when empty.
    secret_key: str = ""

    tz: str = Field(default="UTC", alias="TZ")
    data_dir: Path = Path("/data")
    database_url: str | None = None
    static_dir: Path = Path(__file__).resolve().parent.parent / "static"

    cookie_secure: bool = True
    session_days: int = 30

    login_max_failures: int = 5
    login_window_seconds: int = 15 * 60

    @property
    def zone(self) -> ZoneInfo:
        return ZoneInfo(self.tz)

    @property
    def db_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{self.data_dir / 'journal.db'}"


@lru_cache
def get_settings() -> Settings:
    return Settings()
