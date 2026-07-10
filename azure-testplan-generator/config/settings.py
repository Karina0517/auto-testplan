"""Application configuration and environment loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from dotenv import load_dotenv


class ConfigurationError(Exception):
    """Raised when required configuration is missing or invalid."""


@dataclass(slots=True, frozen=True)
class Settings:
    """Environment-backed app settings."""

    azure_organization: str
    azure_project: str
    azure_pat: str
    area_path: str
    base_iteration: str
    api_version: str
    request_timeout_seconds: int = 30

    @classmethod
    def from_env(cls, env_file: str = ".env") -> "Settings":
        """Load settings from .env file and environment variables."""
        load_dotenv(dotenv_path=Path(env_file))

        required_env = {
            "AZURE_ORGANIZATION": os.getenv("AZURE_ORGANIZATION", "").strip(),
            "AZURE_PROJECT": os.getenv("AZURE_PROJECT", "").strip(),
            "AZURE_PAT": os.getenv("AZURE_PAT", "").strip(),
            "AREA_PATH": os.getenv("AREA_PATH", "").strip(),
            "BASE_ITERATION": os.getenv("BASE_ITERATION", "").strip(),
            "API_VERSION": os.getenv("API_VERSION", "").strip(),
        }
        missing = [key for key, value in required_env.items() if not value]
        if missing:
            missing_vars = ", ".join(missing)
            raise ConfigurationError(
                f"Faltan variables obligatorias en .env: {missing_vars}"
            )

        return cls(
            azure_organization=required_env["AZURE_ORGANIZATION"],
            azure_project=required_env["AZURE_PROJECT"],
            azure_pat=required_env["AZURE_PAT"],
            area_path=required_env["AREA_PATH"],
            base_iteration=required_env["BASE_ITERATION"],
            api_version=required_env["API_VERSION"],
        )

