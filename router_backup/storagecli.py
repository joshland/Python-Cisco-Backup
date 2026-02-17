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
_dry_run: bool = False


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
    global _storage, _dry_run

    _storage = BackupStorage(
        storage_path=config.storage,
        storage_model=config.storage_model,
        hostname="storagecli",
        timestamp="",
        dry_run=_dry_run,
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
    dry_run: bool = typer.Option(
        False, "--dryrun", "-n", help="Simulate operations without writing files"
    ),
):
    """Storage CLI for managing configuration backups with version control."""
    global _config, _dry_run

    _dry_run = dry_run

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


def show_dry_run_summary():
    """Show dry-run summary if in dry-run mode."""
    global _storage
    if _storage and _storage.dry_run:
        summary = _storage.get_dry_run_summary()
        if summary:
            typer.echo(summary)


@app.command(name="init")
def init_repo(
    force: bool = typer.Option(False, "--force", "-f", help="Force reinitialize if already exists"),
):
    """Initialize the storage repository."""
    global _config, _dry_run

    if _config is None:
        _config = load_config()

    storage_path = Path(_config.storage)

    if _dry_run:
        typer.echo(f"[DRY-RUN] Would initialize {_config.storage_model} storage at {storage_path}")
        return

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

    # Show dry-run summary if applicable
    show_dry_run_summary()

    if not _storage.dry_run:
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

    # Show dry-run summary if applicable
    show_dry_run_summary()

    if not _storage.dry_run:
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


@app.command(name="list")
def list_configs(
    pattern: str = typer.Argument("*.txt", help="File pattern to match (default: *.txt)"),
):
    """List all configuration files in storage."""
    global _config

    if _config is None:
        _config = load_config()

    storage_path = Path(_config.storage)

    if not storage_path.exists():
        typer.echo(f"Storage directory not found: {storage_path}")
        raise typer.Exit(1)

    # Find all matching files
    files = list(storage_path.glob(pattern))

    if not files:
        typer.echo(f"No files matching '{pattern}' found in {storage_path}")
        return

    typer.echo(f"\nConfiguration files in {storage_path}:")
    typer.echo("-" * 80)

    total_size = 0
    for f in sorted(files):
        if f.is_file():
            size = f.stat().st_size
            total_size += size
            size_str = f"{size:,} bytes"
            typer.echo(f"  {f.name:<50} {size_str:>15}")

    typer.echo("-" * 80)
    typer.echo(f"Total: {len(files)} files, {total_size:,} bytes ({total_size / 1024:.2f} KB)")


@app.command(name="devices")
def list_devices():
    """List all devices (unique hostnames) that have been backed up."""
    global _config

    if _config is None:
        _config = load_config()

    storage_path = Path(_config.storage)

    if not storage_path.exists():
        typer.echo(f"Storage directory not found: {storage_path}")
        raise typer.Exit(1)

    # Find all .txt files and extract device names
    txt_files = list(storage_path.glob("*.txt"))

    if not txt_files:
        typer.echo(f"No backup files found in {storage_path}")
        return

    # Extract unique device names (everything before the timestamp)
    import re

    devices = {}

    # For git/pygit storage, get version counts from git history
    if _config.storage_model in ["git", "pygit"]:
        # Initialize storage to access git functions
        if _storage is None:
            init_storage(_config)

    for f in txt_files:
        if f.is_file():
            # Parse filename like: router1-config_02-15-2024_14-30.txt
            # or: router1_02-15-2024_14-30.txt (for txt storage)
            # or: router1-config.txt (for git storage)
            name = f.stem  # Get filename without extension

            # Pattern to match timestamp: _MM-DD-YYYY_HH-MM at the end
            timestamp_pattern = r"_(\d{2}-\d{2}-\d{4})_(\d{2}-\d{2})$"
            match = re.search(timestamp_pattern, name)

            if match:
                # Remove the timestamp from the end (txt storage)
                device_name = name[: match.start()]
            else:
                # No timestamp found, use whole name (git storage)
                device_name = name

            if device_name not in devices:
                devices[device_name] = {"count": 0, "files": [], "total_size": 0}

            size = f.stat().st_size
            devices[device_name]["files"].append(f.name)
            devices[device_name]["total_size"] += size

            # For git/pygit storage, count versions from git history
            if _config.storage_model in ["git", "pygit"] and _storage:
                versions = _storage.get_versions(device_name)
                devices[device_name]["count"] = len(versions) if versions else 1
            else:
                # For txt storage, count files
                devices[device_name]["count"] += 1

    if not devices:
        typer.echo("No devices found")
        return

    typer.echo(f"\nDevices backed up in {storage_path}:")
    typer.echo("-" * 80)
    typer.echo(f"{'Device Name':<30} {'Backups':<10} {'Total Size':<15}")
    typer.echo("-" * 80)

    total_backups = 0
    total_size = 0

    for device_name in sorted(devices.keys()):
        info = devices[device_name]
        count = info["count"]
        size = info["total_size"]
        total_backups += count
        total_size += size

        size_str = f"{size:,} bytes" if size < 1024 else f"{size / 1024:.2f} KB"
        typer.echo(f"{device_name:<30} {count:<10} {size_str:<15}")

    typer.echo("-" * 80)
    size_total_str = f"{total_size:,} bytes" if total_size < 1024 else f"{total_size / 1024:.2f} KB"
    typer.echo(f"Total: {len(devices)} devices, {total_backups} backups, {size_total_str}")


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
