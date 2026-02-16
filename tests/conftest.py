"""Pytest configuration and fixtures for router-backup tests."""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests."""
    temp = tempfile.mkdtemp(prefix="router_backup_test_")
    yield Path(temp)
    shutil.rmtree(temp, ignore_errors=True)


@pytest.fixture
def git_repo_path(temp_dir):
    """Provide a path for a git repository."""
    return temp_dir / "testrepo"


@pytest.fixture
def script_paths():
    """Provide paths to the storage scripts."""
    base = Path(__file__).parent.parent / "router_backup"
    return {
        "storage_git": base / "storage_git.py",
        "storage_pygit": base / "storage_pygit.py",
    }
