import inspect
import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv, find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# DEV_MODE: bool = os.getenv("DEV_MODE", "false").lower() in ("1", "true", "yes", "on", True)
DEV_MODE: bool = True


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
    CIRIUM_FILES_PATH: Path = EXCEL_FILES_PATH / "cirium"
    NOPASSED_PATH: Path = ROOT / "nopassed"
    RESPONSES_PATH: Path = ROOT / "responses"
    SUBSCRIPTION_FILE: Path = ROOT / "subscription_data.json"
    FLIGHT_RADAR_PATH: Path = ROOT / "flight_radar"
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
    CIRIUM_FILES_PATH: Path = EXCEL_FILES_PATH / "cirium"
    NOPASSED_PATH: Path = ROOT / "nopassed"
    RESPONSES_PATH: Path = ROOT / "responses"
    SUBSCRIPTION_FILE: Path = ROOT / "subscription_data.json"
    FLIGHT_RADAR_PATH: Path = ROOT / "flight_radar"


ROOT.mkdir(parents=True, exist_ok=True)
FILES_PATH.mkdir(parents=True, exist_ok=True)
EXCEL_FILES_PATH.mkdir(parents=True, exist_ok=True)
NOPASSED_PATH.mkdir(parents=True, exist_ok=True)
RESPONSES_PATH.mkdir(parents=True, exist_ok=True)
CIRIUM_FILES_PATH.mkdir(parents=True, exist_ok=True)
FLIGHT_RADAR_PATH.mkdir(parents=True, exist_ok=True)


def require_env(name: str, additional=None):
    value = os.getenv(name)
    if not value and additional or additional == "":
        return additional
    if not value and not additional:
        raise RuntimeError(f"{name} is required")
    return value


PATH = find_dotenv(filename=str(Path(ENV_PATH).absolute()))

load_dotenv(dotenv_path=PATH)

ENABLE_PERFORMANCE_LOGGER: bool = require_env("ENABLE_PERFORMANCE_LOGGER", False)

# SERVER

HOST: str = require_env("HOST", "0.0.0.0")
PORT: int = require_env("PORT", 8000)

SELF_HOST: str = require_env("SELF_HOST", "api.aixii.com")
SELF_PORT: int = require_env("SELF_PORT", 8000)

# API

API_TITLE: str = require_env("API_TITLE", "AIXII API Server")
API_DESCRIPTION: str = require_env("API_DESCRIPTION", "")
API_VERSION: str = require_env("API_VERSION", "0.3.9")
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
MS_WEBHOOK_LIFECYCLE_URL: str = require_env("MS_WEBHOOK_LIFECYCLE_URL",
                                            f"https://{SELF_HOST}/{API_ROOT_URL}/webhooks/microsoft/lifecycle")
MS_WEBHOOK_SECRET: str = require_env("MS_WEBHOOK_SECRET", "SuperSecret")

# DREMIO

DREMIO_HOST = require_env("DREMIO_HOST", "http://data.aixii.com")
DREMIO_PORT = require_env("DREMIO_PORT", "9047")
DREMIO_USER = require_env("DREMIO_USER", "dremio_user")
DREMIO_PASS = require_env("DREMIO_PASS", "dremio_pass")

# AIRLABS

AIRLABS_API_KEY: str = require_env("AIRLABS_API_KEY")
AIRLABS_API_URL: str = "https://airlabs.co/api/v9/"

#

PA_APP_URL = require_env("PA_APP_URL",
                         "https://apps.powerapps.com/play/e/default-7ed13fa4-3b96-4f55-8254-4902942ef466/a/e599ee0c-0b10-409b-bcc3-c0520ebfcf48?tenantId=7ed13fa4-3b96-4f55-8254-4902942ef466&hint=20e3f4e3-fad9-4b45-b069-78883539860f")
CUSTOM_EXCEL_LEASE_HEADERS_ORDER = [
    "lessee", "lessor", "aircraft_count", "aircraft_type", "msn", "aircraft_registration", "engines_count",
    "engines_manufacturer", "engines_models", "engine1_msn", "engine2_msn", "dated", "damage_proceeds_threshold",
    "aircraft_agreed_value", "aircraft_hull_all_risks", "min_liability_coverages", "all_risks_deductible", "currency",
    "id", "created_at", "updated_at"
]

# Flight Radar

FLIGHT_RADAR_URL: str = require_env("FLIGHT_RADAR_URL", "https://fr24api.flightradar24.com/api")
FLIGHT_RADAR_API_KEY: str = require_env("FLIGHT_RADAR_API_KEY")
FLIGHT_RADAR_SECONDS_BETWEEN_REQUESTS: float = require_env("FLIGHT_RADAR_SECONDS_BETWEEN_REQUESTS", 60 / 90)
FLIGHT_RADAR_RANGE_DAYS: int = require_env("FLIGHT_RADAR_RANGE_DAYS", 14)
FLIGHT_RADAR_MAX_REG_PER_BATCH: int = require_env("FLIGHT_RADAR_MAX_REG_PER_BATCH", 15)
FLIGHT_RADAR_HEADERS: dict = {
    "Authorization": f"Bearer {FLIGHT_RADAR_API_KEY}",
    "Accept-Version": "v1",
    "Accept": "application/json"
}

FLIGHT_RADAR_REDIS_POLLING_KEY: str = "flights:polling"
FLIGHT_RADAR_REDIS_META_KEY: str = "flights:meta"

FLIGHT_RADAR_CHECK_INTERVAL_MISS: int = require_env("FLIGHT_RADAR_CHECK_INTERVAL_MISS", 15 * 60)
FLIGHT_RADAR_CHECK_INTERVAL_FOUND: int = require_env("FLIGHT_RADAR_CHECK_INTERVAL_FOUND", 30 * 60)
FLIGHT_RADAR_REDIS_TTL_SECONDS: int = require_env("FLIGHT_RADAR_REDIS_TTL_SECONDS", 2 * 60 * 60)

# IMPORTS

_current_module = sys.modules[__name__]

__all__ = [
    name
    for name, obj in globals().items()
    if not name.startswith("__") and not name == "DEV_MODE" and not inspect.isfunction(obj)
]
