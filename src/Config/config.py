import inspect
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv, find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_MODE = os.getenv("DEV_MODE") or True


# PATH

def get_project_root() -> Path:
    current_file = Path(__file__).absolute()

    for parent in current_file.parents:
        if (parent / '.git').exists() or (parent / 'requirements.txt').exists():
            return parent

    return current_file.parents[2]

# ENVIRONMENT

if DEV_MODE:
    ENV_PATH: Path = os.getenv("ENV_DEV_PATH") or get_project_root() / ".env.dev"
    ROOT: Path = get_project_root() / "api_data"
    FILES_PATH: Path = ROOT / "input_files"
    EXCEL_FILES_PATH: Path = FILES_PATH / "excel_db"
    NOPASSED_PATH: Path = ROOT / "nopassed"
    RESPONSES_PATH: Path = ROOT / "responses"
    SUBSCRIPTION_FILE: Path = ROOT / "subscription_data.json"
    # FILES_PATH: Path = Path(r"D:\FTPFolder\input_files")
    # EXCEL_FILES_PATH: Path = FILES_PATH / "excel_files"
    # NOPASSED_PATH: Path = Path(r"D:\FTPFolder\nopassed")
    # RESPONSES_PATH: Path = Path(r"D:\FTPFolder\responses")
    # SUBSCRIPTION_FILE: Path = Path(r"D:\FTPFolder\subscription_data.json")
else:
    ENV_PATH: Path = os.getenv("ENV_PATH") or get_project_root() / ".env"
    ROOT: Path = get_project_root() / "api_data"
    FILES_PATH: Path = ROOT / "input_files"
    EXCEL_FILES_PATH: Path = FILES_PATH / "excel_db"
    NOPASSED_PATH: Path = ROOT / "nopassed"
    RESPONSES_PATH: Path = ROOT / "responses"
    SUBSCRIPTION_FILE: Path = ROOT / "subscription_data.json"

ROOT.mkdir(parents=True, exist_ok=True)
FILES_PATH.mkdir(parents=True, exist_ok=True)
EXCEL_FILES_PATH.mkdir(parents=True, exist_ok=True)
NOPASSED_PATH.mkdir(parents=True, exist_ok=True)
RESPONSES_PATH.mkdir(parents=True, exist_ok=True)


def require_env(name: str, additional=None):
    value = os.getenv(name)
    if not value and additional or additional == "":
        return additional
    if not value and not additional:
        raise RuntimeError(f"{name} is required")
    return value


PATH = find_dotenv(filename=str(Path(ENV_PATH).absolute()))

load_dotenv(dotenv_path=PATH)

# SERVER

HOST: str = require_env("HOST", "0.0.0.0")
PORT: int = require_env("PORT", 8000)

SELF_HOST: str = require_env("SELF_HOST", "api.aixii.com")
SELF_PORT: int = require_env("SELF_PORT", 8000)

# API

API_TITLE: str = require_env("API_TITLE", "AIXII API Server")
API_DESCRIPTION: str = require_env("API_DESCRIPTION", "")
API_VERSION: str = require_env("API_VERSION", "0.2.1")
API_SWAGGER_URL: str = require_env("API_SWAGGER_URL", "/api/docs")
API_REDOC_URL: str = require_env("API_REDOC_URL", "/api/redoc")
API_ROOT_URL: str = require_env("API_ROOT_URL", "/api/v1")

# CORS

CORS_ORIGINS: list = require_env("CORS_ORIGINS", "*").split(",")
CORS_CREDENTIALS: bool = require_env("CORS_CREDENTIALS", True)
CORS_METHODS: list = require_env("CORS_METHODS", "*").split(",")
CORS_HEADERS: list = require_env("CORS_HEADERS", "*").split(",")


# DATABASE

class DBSettings(BaseSettings):
    """
    ENVIRONMENT AUTO, NO PARAMS NEED
    """
    DB_USER: str = Field(default="")
    DB_PASSWORD: str = Field(default="")
    DB_HOST: str = Field(default=HOST)
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="")

    REDIS_USER: str = Field(default="")
    REDIS_USER_PASSWORD: str = Field(default="")
    REDIS_HOST: str = Field(default=HOST)
    REDIS_PORT: int = Field(default=6379)

    model_config = SettingsConfigDict(
        env_file=PATH, extra='ignore'
    )

    @property
    def db_list(self) -> list[str]:
        """Splits a string into a DB list"""
        return [db.strip() for db in self.DB_NAME.split(",") if db.strip()]

    def get_db_url(self, db_name: str) -> str:
        """Returns DSN for the best matching database (substring match)."""
        if self.DB_USER == "" or self.DB_PASSWORD == "":
            raise ValueError("Database credentials not provided")

        matches = [db for db in self.db_list if db_name.lower() in db.lower()]
        if not matches:
            raise ValueError(f"No database similar to '{db_name}' found in {self.db_list}")
        if len(matches) > 1:
            raise ValueError(f"Ambiguous name '{db_name}', matches: {matches}")
        return (f"postgresql+asyncpg://{self.DB_USER}:{quote_plus(self.DB_PASSWORD)}@"
                f"{self.DB_HOST}:{self.DB_PORT}/{matches[0]}")

    def get_reddis_credentials(self):
        return self.REDIS_USER, quote_plus(self.REDIS_USER_PASSWORD), self.REDIS_HOST, self.REDIS_PORT

#  LOGS

LOGS_DIR = get_project_root() / 'Logs'
LOGS_DIR.mkdir(exist_ok=True, parents=True)

#  Microsoft Graph

MS_TENANT_ID: str = require_env("MS_TENANT_ID")
MS_CLIENT_ID: str = require_env("MS_CLIENT_ID")
MS_CLIENT_SECRET: str = require_env("MS_CLIENT_SECRET")
MS_GRAPHSCOPES: list = [scope.strip() for scope
                        in require_env("MS_GRAPHSCOPES", "https://graph.microsoft.com/.default").split(",")
                        if scope.strip()]
MS_WEBHOOK_URL: str = require_env("MS_WEBHOOK_URL", f"https://{SELF_HOST}/{API_ROOT_URL}/webhooks/microsoft")
MS_WEBHOOK_LIFECYCLE_URL: str = require_env("MS_WEBHOOK_LIFECYCLE_URL", f"https://{SELF_HOST}/{API_ROOT_URL}/webhooks/microsoft/lifecycle")
MS_WEBHOOK_SECRET: str = require_env("MS_WEBHOOK_SECRET", "SuperSecret")

# DREMIO

DREMIO_HOST = require_env("DREMIO_HOST", "http://data.aixii.com")
DREMIO_PORT = require_env("DREMIO_PORT", "9047")
DREMIO_USER = require_env("DREMIO_USER", "dremio_user")
DREMIO_PASS = require_env("DREMIO_PASS", "dremio_pass")

#


# IMPORTS

_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if not name.startswith("__") and not name == "DEV_MODE" and not inspect.isfunction(obj)
]
