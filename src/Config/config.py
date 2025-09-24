import os
from pathlib import Path

from dotenv import load_dotenv, find_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

DEV_MODE = False


# PATH

def get_project_root() -> Path:
    current_file = Path(__file__).absolute()

    for parent in current_file.parents:
        if (parent / '.git').exists() or (parent / 'requirements.txt').exists():
            return parent

    return current_file.parents[2]


# FILES_PATH: Path = get_project_root() / "data/input_files"
# NOPASSED_PATH: Path = get_project_root() / "data/nopassed"
# RESPONSES_PATH: Path = get_project_root() / "data/responses"

FILES_PATH: Path = Path(r"D:\FTPFolder\input_files")
NOPASSED_PATH: Path = Path(r"D:\FTPFolder\nopassed")
RESPONSES_PATH: Path = Path(r"D:\FTPFolder\responses")

FILES_PATH.mkdir(parents=True, exist_ok=True)
NOPASSED_PATH.mkdir(parents=True, exist_ok=True)
RESPONSES_PATH.mkdir(parents=True, exist_ok=True)

# ENVIRONMENT

if DEV_MODE:
    ENV_PATH: str = ".env.dev"
else:
    ENV_PATH: str = os.getenv("ENV_PATH") or ".env"

PATH = find_dotenv(filename=ENV_PATH)

load_dotenv(dotenv_path=PATH)

# SERVER

HOST: str = os.getenv("HOST") or "0.0.0.0"
PORT: int = os.getenv("PORT") or 8000

# API

API_TITLE: str = os.getenv("API_TITLE") or "AI12 Claims Server"
API_DESCRIPTION: str = os.getenv("API_DESCRIPTION") or ""
API_VERSION: str = os.getenv("API_VERSION") or "0.0.1"
API_SWAGGER_URL: str = os.getenv("API_SWAGGER_URL") or "/api/docs"
API_REDOC_URL: str = os.getenv("API_REDOC_URL") or "/api/redoc"
API_ROOT_URL: str = os.getenv("API_ROOT_URL") or "/api/v1"

# CORS

CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "*").split(",")
CORS_CREDENTIALS: bool = os.getenv("CORS_CREDENTIALS") or True
CORS_METHODS: list = os.getenv("CORS_METHODS", "*").split(",")
CORS_HEADERS: list = os.getenv("CORS_HEADERS", "*").split(",")


# DATABASE

class DBSettings(BaseSettings):
    """
    ENVIRONMENT AUTO, NO PARAMS NEED
    """
    DB_USER: str = Field(default="")
    DB_PASSWORD: str = Field(default="")
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_NAME: str = Field(default="")

    # REDIS_HOST: str
    # REDIS_PORT: int

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
        return (f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@"
                f"{self.DB_HOST}:{self.DB_PORT}/{matches[0]}")

    # def get_reddis_url(self):
    #     return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}"


#  LOGS

LOGS_DIR = get_project_root() / 'Logs'
LOGS_DIR.mkdir(exist_ok=True, parents=True)
