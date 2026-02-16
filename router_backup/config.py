"""Configuration management for router-backup."""

import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class Config:
    """Configuration class for router-backup."""

    device_file: str = "/etc/router-backup/devices.csv"
    storage: str = "/var/lib/router-backup"
    storage_model: str = "txt"  # txt, git, or pygit
    log_level: str = "INFO"
    log_file: Optional[str] = None

    @classmethod
    def from_file(cls, config_path: str) -> "Config":
        """Load configuration from YAML file."""
        path = Path(config_path)

        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {config_path}")

        with open(path, "r") as f:
            data = yaml.safe_load(f) or {}

        return cls(
            device_file=data.get("device_file", cls.device_file),
            storage=data.get("storage", cls.storage),
            storage_model=data.get("storage_model", cls.storage_model),
            log_level=data.get("log_level", cls.log_level),
            log_file=data.get("log_file", cls.log_file),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Config":
        """Create config from dictionary."""
        return cls(
            device_file=data.get("device_file", cls.device_file),
            storage=data.get("storage", cls.storage),
            storage_model=data.get("storage_model", cls.storage_model),
            log_level=data.get("log_level", cls.log_level),
            log_file=data.get("log_file", cls.log_file),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "device_file": self.device_file,
            "storage": self.storage,
            "storage_model": self.storage_model,
            "log_level": self.log_level,
            "log_file": self.log_file,
        }

    def ensure_directories(self):
        """Ensure required directories exist."""
        # Ensure storage directory exists
        storage_path = Path(self.storage)
        storage_path.mkdir(parents=True, exist_ok=True)

        # Ensure device file directory exists
        device_file_path = Path(self.device_file)
        device_file_path.parent.mkdir(parents=True, exist_ok=True)


def get_default_config_path() -> str:
    """Get the default configuration file path."""
    return "/etc/router-backup/config.yaml"


def create_default_config(path: str) -> Config:
    """Create a default configuration file."""
    config = Config()
    config_path = Path(path)
    config_path.parent.mkdir(parents=True, exist_ok=True)

    with open(config_path, "w") as f:
        yaml.dump(config.to_dict(), f, default_flow_style=False)

    return config
