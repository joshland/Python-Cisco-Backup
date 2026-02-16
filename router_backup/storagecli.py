#!/usr/bin/env python3
"""
Unified storage CLI for router-backup.

Uses the configured storage adapter (txt/git/pygit) and locations
from the configuration file.
"""

import os
import sys
from pathlib import Path
from typing import Optional

import typer
from loguru import logger

from router_backup.config import Config, get_default_config_path, create_default_config
from router_backup.storage import BackupStorage, set_global_storage

# Configure logging
logger.remove()
logger.add(sys.stderr, format="{level}: {message}", level="INFO")

app = typer.Typer(help="Storage CLI for router-backup git storage")

# Global config and storage
_config: Optional[Config] = None
_storage: Optional[BackupStorage] = None


def load_config(config_file: Optional[str] = None) -> Config:
    """Load configuration from file."""
    global _config

    if config_file and os.path.exists(config_file):
        _config = Config.from_file(config_file)
        logger.debug(f"Loaded config from {config_file}")
    elif os.path.exists(get_default_config_path()):
        _config = Config.from_file(get_default_config_path())
        logger.debug(f"Loaded config from {get_default_config_path()}")
    else:
        _config = Config()
        logger.debug("Using default configuration")

    return _config


def init_storage(config: Config) -> BackupStorage:
    """Initialize storage backend."""
    global _storage

    _storage = BackupStorage(
        storage_path=config.storage,
        storage_model=config.storage_model,
        hostname="storagecli",
        timestamp="",
    )

    set_global_storage(_storage)
    logger.debug(f"Initialized {config.storage_model} storage at {config.storage}")
    return _storage


@app.callback()
def callback(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file (default: /etc/router-backup/config.yaml)",
    ),
    storage: Optional[str] = typer.Option(
        None, "--storage", "-s", help="Storage path (overrides config)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", "-m", help="Storage model: txt, git, or pygit (overrides config)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
):
    """Storage CLI for managing configuration backups with version control."""
    global _config

    # Setup logging
    if verbose:
        logger.remove()
        logger.add(sys.stderr, format="{level}: {message}", level="DEBUG")

    # Load configuration
    _config = load_config(config)

    # Override with CLI arguments
    if storage:
        _config.storage = storage
    if model:
        _config.storage_model = model


@app.command(name="init")
def init_repo(
    force: bool = typer.Option(False, "--force", "-f", help="Force reinitialize if already exists"),
):
    """Initialize the storage repository."""
    global _config

    if _config is None:
        _config = load_config()

    storage_path = Path(_config.storage)

    # Check if already initialized
    if _config.storage_model in ["git", "pygit"]:
        git_dir = storage_path / ".git"
        if git_dir.exists() and not force:
            typer.echo(f"Repository already initialized at {storage_path}")
            typer.echo("Use --force to reinitialize")
            raise typer.Exit(1)

    # Initialize storage
    init_storage(_config)

    typer.echo(f"Initialized {_config.storage_model} storage at {storage_path}")


@app.command(name="write")
def write_file(
    filepath: str = typer.Argument(..., help="Path to the file (relative to storage)"),
    content: Optional[str] = typer.Option(
        None, "--content", "-c", help="Content to write directly"
    ),
    file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Path to file containing content to write"
    ),
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="Commit message (for git/pygit storage)"
    ),
):
    """Write a file to storage. Content can be provided directly (-c) or read from a file (-f)."""
    global _config, _storage

    if _config is None:
        _config = load_config()

    if _storage is None:
        _storage = init_storage(_config)

    # Get content from either --content or --file
    if content and file:
        typer.echo("Error: Cannot use both --content and --file options")
        raise typer.Exit(1)
    elif content:
        file_content = content
    elif file:
        if not os.path.exists(file):
            typer.echo(f"Error: File not found: {file}")
            raise typer.Exit(1)
        with open(file, "r") as f:
            file_content = f.read()
    else:
        typer.echo("Error: Must provide either --content or --file option")
        raise typer.Exit(1)

    # Use provided message or default
    commit_msg = message or f"Add {filepath}"

    # Write the file
    _storage.write_backup(
        filename=filepath.replace(".txt", ""),  # Remove extension if provided
        content=file_content,
        device_ip=None,
    )

    typer.echo(f"Written {filepath}")


@app.command(name="update")
def update_file(
    filepath: str = typer.Argument(..., help="Path to the file (relative to storage)"),
    content: Optional[str] = typer.Option(
        None, "--content", "-c", help="New content to write directly"
    ),
    file: Optional[str] = typer.Option(
        None, "--file", "-f", help="Path to file containing new content"
    ),
    message: Optional[str] = typer.Option(
        None, "--message", "-m", help="Commit message (for git/pygit storage)"
    ),
):
    """Update an existing file in storage. Content can be provided directly (-c) or read from a file (-f)."""
    global _config, _storage

    if _config is None:
        _config = load_config()

    if _storage is None:
        _storage = init_storage(_config)

    # Get content from either --content or --file
    if content and file:
        typer.echo("Error: Cannot use both --content and --file options")
        raise typer.Exit(1)
    elif content:
        file_content = content
    elif file:
        if not os.path.exists(file):
            typer.echo(f"Error: File not found: {file}")
            raise typer.Exit(1)
        with open(file, "r") as f:
            file_content = f.read()
    else:
        typer.echo("Error: Must provide either --content or --file option")
        raise typer.Exit(1)

    # Use provided message or default
    commit_msg = message or f"Update {filepath}"

    # Update the file
    _storage.write_backup(
        filename=filepath.replace(".txt", ""), content=file_content, device_ip=None
    )

    typer.echo(f"Updated {filepath}")


@app.command(name="versions")
def list_versions(
    filepath: str = typer.Argument(..., help="Path to the file"),
):
    """List all versions of a file (git/pygit only)."""
    global _config, _storage

    if _config is None:
        _config = load_config()

    if _config.storage_model == "txt":
        typer.echo("Version control not available with txt storage model")
        typer.echo("Use --model git or --model pygit for version control")
        raise typer.Exit(1)

    if _storage is None:
        _storage = init_storage(_config)

    versions = _storage.get_versions(filepath.replace(".txt", ""))

    if not versions:
        typer.echo(f"No versions found for {filepath}")
        return

    typer.echo(f"\nVersions of {filepath}:")
    typer.echo("-" * 80)
    for v in versions:
        typer.echo(f"  {v['hash']}  {v['date']}  {v['message']}")


@app.command(name="diff")
def diff_versions(
    filepath: str = typer.Argument(..., help="Path to the file"),
    commit1: str = typer.Argument(..., help="First commit hash"),
    commit2: Optional[str] = typer.Argument(
        None, help="Second commit hash (optional - compares with current if omitted)"
    ),
):
    """Show diff between file versions (git/pygit only)."""
    global _config, _storage

    if _config is None:
        _config = load_config()

    if _config.storage_model == "txt":
        typer.echo("Version control not available with txt storage model")
        typer.echo("Use --model git or --model pygit for version control")
        raise typer.Exit(1)

    if _storage is None:
        _storage = init_storage(_config)

    diff_output = _storage.diff_versions(
        filename=filepath.replace(".txt", ""), commit1=commit1, commit2=commit2
    )

    typer.echo(diff_output)


@app.command(name="read")
def read_version(
    filepath: str = typer.Argument(..., help="Path to the file"),
    commit: str = typer.Argument(..., help="Commit hash to read"),
    output: Optional[str] = typer.Option(
        None, "--output", "-o", help="Output file (default: stdout)"
    ),
):
    """Read a specific version of a file (git/pygit only)."""
    global _config, _storage

    if _config is None:
        _config = load_config()

    if _config.storage_model == "txt":
        typer.echo("Version control not available with txt storage model")
        typer.echo("Use --model git or --model pygit for version control")
        raise typer.Exit(1)

    if _storage is None:
        _storage = init_storage(_config)

    content = _storage.get_version_content(
        filename=filepath.replace(".txt", ""), commit_hash=commit
    )

    if content is None:
        typer.echo(f"Version not found: {commit}")
        raise typer.Exit(1)

    if output:
        with open(output, "w") as f:
            f.write(content)
        typer.echo(f"Written to {output}")
    else:
        typer.echo(content)


@app.command(name="status")
def show_status():
    """Show repository status (git/pygit only)."""
    global _config

    if _config is None:
        _config = load_config()

    if _config.storage_model == "txt":
        typer.echo("Status not available with txt storage model")
        typer.echo("Use --model git or --model pygit for version control")
        raise typer.Exit(1)

    # For git storage, show status
    if _config.storage_model == "git":
        from router_backup.storage_git import StorageGit

        storage = StorageGit(_config.storage)
        status = storage.status()
        typer.echo(status)
    elif _config.storage_model == "pygit":
        from router_backup.storage_pygit import StoragePyGit

        storage = StoragePyGit(_config.storage)
        status = storage.status()
        typer.echo(status)


@app.command(name="init-config")
def init_config(
    path: Optional[str] = typer.Option(
        None,
        "--path",
        "-p",
        help="Path to create config file (default: /etc/router-backup/config.yaml)",
    ),
):
    """Initialize a default configuration file."""
    config_path = path or get_default_config_path()

    if os.path.exists(config_path):
        typer.echo(f"Config file already exists: {config_path}")
        raise typer.Exit(1)

    config = create_default_config(config_path)
    typer.echo(f"Created default config at: {config_path}")
    typer.echo(f"  Device file: {config.device_file}")
    typer.echo(f"  Storage: {config.storage}")
    typer.echo(f"  Storage model: {config.storage_model}")


def main():
    """Entry point for storagecli command."""
    app()


if __name__ == "__main__":
    main()
