import secrets
import warnings
from typing import Annotated, Any, Literal

from pydantic import (
    AnyUrl,
    BeforeValidator,
    EmailStr,
    HttpUrl,
    PostgresDsn,
    computed_field,
    model_validator,
)
from pydantic_core import MultiHostUrl
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing_extensions import Self
import logging

logger = logging.getLogger(__name__)


def parse_cors(v: Any) -> list[str] | str:
    if isinstance(v, str) and not v.startswith("["):
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list | str):
        return v
    raise ValueError(v)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = secrets.token_urlsafe(32)
    # 60 minutes * 24 hours * 8 days = 8 days
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8
    REFRESH_TOKEN_EXPIRE_DAYS: int = 60  # 60 ngày
    FRONTEND_HOST: str = "https://startomation.com"
    ENVIRONMENT: Literal["local", "staging", "production"] = "local"

    BACKEND_CORS_ORIGINS: Annotated[list[AnyUrl] | str, BeforeValidator(parse_cors)] = (
        []
    )

    LEMON_SQUEEZY_API_KEY: str = ""
    LEMON_SQUEEZY_STORE_ID: str = ""
    LEMON_SQUEEZY_WEBHOOK_SECRET: str = ""

    # Secret key for automation engine
    SECRET_KEY_ENGINE: str = ""

    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB default
    ALLOWED_IMAGE_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
    ]
    ALLOWED_FILE_TYPES: list[str] = [
        "image/jpeg",
        "image/png",
        "image/webp",
        "image/gif",
        "application/pdf",
        "text/plain",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]
    LOCAL_UPLOAD_PATH: str = "public"

    # DigitalOcean Spaces settings
    DO_SPACES_KEY: str = "DO801E6P7WCHQNYL8ZCG"
    DO_SPACES_SECRET: str = "eDUYkieLNAqcvjW1q7XDsSabSXIny1HyC5EIvwb5KIs"
    DO_SPACES_BUCKET: str = "startomation"
    DO_SPACES_REGION: str = "sgp1"
    DO_SPACES_ENDPOINT: str = "https://sgp1.digitaloceanspaces.com"
    DO_SPACES_CDN_ENDPOINT: str = "https://sgp1.cdn.digitaloceanspaces.com"

    # Storage provider: "local" or "spaces"
    STORAGE_PROVIDER: Literal["local", "spaces"] = "local"

    # Image compression settings
    IMAGE_COMPRESSION_ENABLED: bool = True
    IMAGE_QUALITY: int = 85  # JPEG quality (1-100)
    IMAGE_MAX_WIDTH: int = 1920  # Max width in pixels
    IMAGE_MAX_HEIGHT: int = 1080  # Max height in pixels
    IMAGE_OPTIMIZE: bool = True  # Enable PIL optimization
    IMAGE_PROGRESSIVE: bool = True  # Progressive JPEG
    IMAGE_KEEP_EXIF: bool = False  # Keep EXIF data
    IMAGE_AUTO_ORIENT: bool = True  # Auto-orient based on EXIF

    @computed_field  # type: ignore[prop-decorator]
    @property
    def all_cors_origins(self) -> list[str]:
        # Allow all origins if "*" is present
        if "*" in self.BACKEND_CORS_ORIGINS:
            return ["*"]
        return [str(origin).rstrip("/") for origin in self.BACKEND_CORS_ORIGINS] + [
            self.FRONTEND_HOST
        ]

    PROJECT_NAME: str
    SENTRY_DSN: HttpUrl | None = None
    POSTGRES_SERVER: str
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SQLALCHEMY_DATABASE_URI(self) -> PostgresDsn:
        return MultiHostUrl.build(
            scheme="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            port=self.POSTGRES_PORT,
            path=self.POSTGRES_DB,
        )

    SMTP_TLS: bool = True
    SMTP_SSL: bool = False
    SMTP_PORT: int = 587
    SMTP_HOST: str | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    EMAILS_FROM_EMAIL: EmailStr | None = None
    EMAILS_FROM_NAME: str | None = None

    @model_validator(mode="after")
    def _set_default_emails_from(self) -> Self:
        if not self.EMAILS_FROM_NAME:
            self.EMAILS_FROM_NAME = self.PROJECT_NAME
        return self

    EMAIL_RESET_TOKEN_EXPIRE_HOURS: int = 48

    @computed_field  # type: ignore[prop-decorator]
    @property
    def emails_enabled(self) -> bool:
        logger.info(f"SMTP_HOST: {self.SMTP_HOST}")
        logger.info(f"EMAILS_FROM_EMAIL: {self.EMAILS_FROM_EMAIL}")
        return bool(self.SMTP_HOST and self.EMAILS_FROM_EMAIL)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def spaces_enabled(self) -> bool:
        return bool(
            self.DO_SPACES_KEY
            and self.DO_SPACES_SECRET
            and self.DO_SPACES_BUCKET
            and self.DO_SPACES_REGION
        )

    EMAIL_TEST_USER: EmailStr = "test@example.com"
    FIRST_SUPERUSER: EmailStr
    FIRST_SUPERUSER_PASSWORD: str

    # Firebase configuration for Phone OTP
    FIREBASE_SERVICE_ACCOUNT_FILE: str = "firebase-service-account.json"

    def _check_default_secret(self, var_name: str, value: str | None) -> None:
        if value == "changethis":
            message = (
                f'The value of {var_name} is "changethis", '
                "for security, please change it, at least for deployments."
            )
            if self.ENVIRONMENT == "local":
                warnings.warn(message, stacklevel=1)
            else:
                raise ValueError(message)

    @model_validator(mode="after")
    def _enforce_non_default_secrets(self) -> Self:
        self._check_default_secret("SECRET_KEY", self.SECRET_KEY)
        self._check_default_secret("POSTGRES_PASSWORD", self.POSTGRES_PASSWORD)
        self._check_default_secret(
            "FIRST_SUPERUSER_PASSWORD", self.FIRST_SUPERUSER_PASSWORD
        )

        return self


settings = Settings()  # type: ignore
