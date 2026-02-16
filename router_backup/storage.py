"""Unified storage interface for router-backup."""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal
from loguru import logger

from router_backup.storage_git import StorageGit
from router_backup.storage_pygit import StoragePyGit


StorageModel = Literal["txt", "git", "pygit"]


class BackupStorage:
    """Unified storage interface supporting txt, git, and pygit backends."""

    def __init__(
        self,
        storage_path: str,
        storage_model: str = "txt",
        hostname: Optional[str] = None,
        timestamp: Optional[str] = None,
    ):
        """
        Initialize backup storage.

        Args:
            storage_path: Path to storage directory
            storage_model: Storage model - 'txt', 'git', or 'pygit'
            hostname: Device hostname (for git commit messages)
            timestamp: Timestamp string (for git commit messages)
        """
        self.storage_path = Path(storage_path)
        self.storage_model = storage_model
        self.hostname = hostname or "unknown"
        self.timestamp = timestamp or datetime.now().strftime("%Y-%m-%d_%H-%M")

        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)

        # Initialize git storage if needed
        self._git_storage = None
        self._pygit_storage = None

        if storage_model == "git":
            self._init_git_storage()
        elif storage_model == "pygit":
            self._init_pygit_storage()

    def _init_git_storage(self):
        """Initialize git storage backend."""
        self._git_storage = StorageGit(str(self.storage_path))
        if not self._git_storage.is_initialized():
            self._git_storage.init()
            logger.info(f"Initialized git repository at {self.storage_path}")

    def _init_pygit_storage(self):
        """Initialize pygit2 storage backend."""
        try:
            self._pygit_storage = StoragePyGit(str(self.storage_path))
            if not self._pygit_storage.is_initialized():
                self._pygit_storage.init()
                logger.info(f"Initialized pygit2 repository at {self.storage_path}")
        except ImportError:
            logger.error("pygit2 not installed, falling back to txt storage")
            self.storage_model = "txt"
        except Exception as e:
            logger.error(f"Failed to initialize pygit2 storage: {e}")
            self.storage_model = "txt"

    def write_backup(self, filename: str, content: str, device_ip: Optional[str] = None):
        """
        Write backup content using the configured storage model.

        Args:
            filename: Base filename (without extension)
            content: Configuration content to store
            device_ip: Device IP address (optional, for commit messages)
        """
        if self.storage_model == "txt":
            self._write_txt(filename, content)
        elif self.storage_model == "git":
            self._write_git(filename, content, device_ip)
        elif self.storage_model == "pygit":
            self._write_pygit(filename, content, device_ip)
        else:
            raise ValueError(f"Unknown storage model: {self.storage_model}")

    def _write_txt(self, filename: str, content: str):
        """Write backup as plain text file."""
        dt_string = datetime.now().strftime("%m-%d-%Y_%H-%M")

        filepath = self.storage_path / f"{filename}_{dt_string}.txt"
        with open(filepath, "w") as f:
            f.write(content)

        logger.info(f"Written {len(content)} bytes to {filepath}")
        print(f"Outputted {len(content)} bytes to {filepath}")

    def _write_git(self, filename: str, content: str, device_ip: Optional[str] = None):
        """Write backup to git repository."""
        filepath = f"{filename}.txt"

        # Create commit message
        ip_str = f" ({device_ip})" if device_ip else ""
        commit_msg = f"Backup {self.hostname}{ip_str} at {self.timestamp}"

        # Write file and commit
        if self._git_storage:
            self._git_storage.write_file(filepath, content, commit_msg)
            logger.info(f"Committed backup to git: {filepath}")
            print(f"Committed {len(content)} bytes to git: {filepath}")
        else:
            logger.error("Git storage not initialized")
            raise RuntimeError("Git storage not initialized")

    def _write_pygit(self, filename: str, content: str, device_ip: Optional[str] = None):
        """Write backup to pygit2 repository."""
        filepath = f"{filename}.txt"

        # Create commit message
        ip_str = f" ({device_ip})" if device_ip else ""
        commit_msg = f"Backup {self.hostname}{ip_str} at {self.timestamp}"

        # Write file and commit
        self._pygit_storage.write_file(filepath, content, commit_msg)

        logger.info(f"Committed backup to pygit2: {filepath}")
        print(f"Committed {len(content)} bytes to pygit2: {filepath}")

    def get_versions(self, filename: str) -> list:
        """Get version history for a file (git/pygit only)."""
        if self.storage_model == "git":
            return self._git_storage.list_versions(f"{filename}.txt")
        elif self.storage_model == "pygit":
            return self._pygit_storage.list_versions(f"{filename}.txt")
        else:
            return []

    def get_version_content(self, filename: str, commit_hash: str) -> Optional[str]:
        """Get content of a specific version (git/pygit only)."""
        if self.storage_model == "git":
            return self._git_storage.read_version(f"{filename}.txt", commit_hash)
        elif self.storage_model == "pygit":
            return self._pygit_storage.read_version(f"{filename}.txt", commit_hash)
        else:
            return None

    def diff_versions(self, filename: str, commit1: str, commit2: Optional[str] = None) -> str:
        """Show diff between versions (git/pygit only)."""
        if self.storage_model == "git":
            return self._git_storage.diff_versions(f"{filename}.txt", commit1, commit2)
        elif self.storage_model == "pygit":
            return self._pygit_storage.diff_versions(f"{filename}.txt", commit1, commit2)
        else:
            return "Version control not available with txt storage model"


# Global storage instance for vendor backup modules
_global_storage: Optional[BackupStorage] = None


def set_global_storage(storage: BackupStorage):
    """Set the global storage instance."""
    global _global_storage
    _global_storage = storage


def get_global_storage() -> Optional[BackupStorage]:
    """Get the global storage instance."""
    return _global_storage


def write_backup(filename: str, content: str, device_ip: Optional[str] = None):
    """
    Write backup using global storage instance.
    Falls back to legacy backup-config directory if no storage configured.

    Args:
        filename: Base filename (without extension)
        content: Configuration content to store
        device_ip: Device IP address (optional, for commit messages in git storage)
    """
    global _global_storage

    if _global_storage is not None:
        _global_storage.write_backup(filename, content, device_ip)
    else:
        # Fallback to legacy behavior
        backup_file = os.path.join("backup-config", f"{filename}.txt")
        os.makedirs("backup-config", exist_ok=True)
        with open(backup_file, "w") as f:
            f.write(content)
        print(f"Outputted {len(content)} bytes to {backup_file}")
