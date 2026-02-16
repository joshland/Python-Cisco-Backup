"""
Multi-vendor network device backup script with CLI and GUI support.

This module can be used both as a CLI tool (with typer) and as a library
for the GUI interface in gui.py.
"""

from csv import reader
from datetime import datetime
from ping3 import ping
from router_backup.vendor_backups import (
    cisco_ios,
    cisco_asa,
    fortinet,
    huawei,
    juniper,
    microtik,
    vyos,
)
from router_backup.config import Config, get_default_config_path
from router_backup.storage import BackupStorage, set_global_storage
import os
import sys
from typing import Optional
from loguru import logger
import typer

# Vendor mapping: key is the selection string, value is (module, needs_secret)
VENDOR_MAP = {
    "1": (cisco_ios, True),
    "2": (cisco_asa, True),
    "3": (juniper, False),
    "4": (vyos, False),
    "5": (huawei, False),
    "6": (fortinet, False),
    "7": (microtik, False),
}

# Vendor names for display
VENDOR_NAMES = {
    "1": "Cisco IOS",
    "2": "Cisco ASA",
    "3": "Juniper",
    "4": "VyOS",
    "5": "Huawei",
    "6": "Fortinet",
    "7": "Microtik",
}

# Global config and storage
_config: Optional[Config] = None
_storage: Optional[BackupStorage] = None
_dry_run: bool = False


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Configure loguru logging."""
    logger.remove()  # Remove default handler

    # Add stderr handler
    logger.add(sys.stderr, format="{level}: {message}", level=log_level)

    # Add file handler
    if log_file:
        logger.add(
            log_file,
            rotation="1 day",
            retention="7 days",
            format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
            level=log_level,
        )


def get_timestamp() -> str:
    """Get current timestamp formatted as MM-DD-YYYY_HH-MM."""
    now = datetime.now()
    return now.strftime("%m-%d-%Y_%H-%M")


def load_config(
    config_file: Optional[str] = None,
    devices_file: Optional[str] = None,
    storage_path: Optional[str] = None,
    storage_model: Optional[str] = None,
) -> Config:
    """Load configuration from file or create from parameters."""
    global _config

    # Try to load from config file
    if config_file and os.path.exists(config_file):
        _config = Config.from_file(config_file)
        logger.info(f"Loaded config from {config_file}")
    elif os.path.exists(get_default_config_path()):
        _config = Config.from_file(get_default_config_path())
        logger.info(f"Loaded config from {get_default_config_path()}")
    else:
        _config = Config()
        logger.info("Using default configuration")

    # Override with CLI arguments
    if devices_file:
        _config.device_file = devices_file
    if storage_path:
        _config.storage = storage_path
    if storage_model:
        _config.storage_model = storage_model

    return _config


def init_storage(config: Config, hostname: str = "backup") -> BackupStorage:
    """Initialize storage backend."""
    global _storage, _dry_run

    timestamp = get_timestamp()
    _storage = BackupStorage(
        storage_path=config.storage,
        storage_model=config.storage_model,
        hostname=hostname,
        timestamp=timestamp,
        dry_run=_dry_run,
    )

    # Set global storage for vendor modules
    set_global_storage(_storage)

    if _dry_run:
        logger.info(
            f"[DRY-RUN] Would initialize {config.storage_model} storage at {config.storage}"
        )
    else:
        logger.info(f"Initialized {config.storage_model} storage at {config.storage}")
    return _storage


def run_script(
    user_selection: str,
    config: Optional[Config] = None,
    devices_file: Optional[str] = None,
    interactive: bool = False,
) -> dict:
    """
    Main backup function that processes devices from CSV.

    Args:
        user_selection: Vendor selection ("1"-"7")
        config: Configuration object (loads default if not provided)
        devices_file: Path to CSV file (overrides config)
        interactive: Whether to show interactive prompts

    Returns:
        dict with results: {'success': int, 'failed': int, 'down': int, 'files': list}
    """
    global _config

    # Load config if not provided
    if config is None:
        config = _config if _config else Config()

    # Use devices file from CLI if provided, otherwise use config
    csv_path = devices_file if devices_file else config.device_file

    # Validate vendor selection first
    if user_selection not in VENDOR_MAP:
        logger.error(f"Invalid vendor selection: {user_selection}")
        raise ValueError(f"Invalid vendor selection: {user_selection}")

    # Initialize storage
    vendor_module_obj, needs_secret = VENDOR_MAP[user_selection]
    vendor_name = VENDOR_NAMES[user_selection]
    init_storage(config, hostname=vendor_name.lower().replace(" ", "_"))

    logger.info(f"Starting backup for {vendor_name} devices from {csv_path}")

    results = {"success": 0, "failed": 0, "down": 0, "files": [], "down_devices": []}

    try:
        with open(csv_path, "r") as read_obj:
            csv_reader = reader(read_obj)
            list_of_rows = list(csv_reader)

            # Skip header row if present
            if len(list_of_rows) > 0:
                # Check if first row contains headers (no IP address)
                first_row = list_of_rows[0]
                try:
                    # Try to parse first element as IP to detect if it's a header
                    import ipaddress

                    ipaddress.ip_address(first_row[0])
                    data_rows = list_of_rows
                except ValueError:
                    # First row is likely a header, skip it
                    data_rows = list_of_rows[1:] if len(list_of_rows) > 1 else []
            else:
                data_rows = []

            total_rows = len(data_rows)
            logger.info(f"Found {total_rows} devices to process")

            for row in data_rows:
                if len(row) < 3:
                    logger.warning(f"Skipping malformed row: {row}")
                    continue

                ip = row[0]
                username = row[1]
                password = row[2]
                secret = row[3] if len(row) > 3 and needs_secret else None

                # Ping the host
                ip_ping = ping(ip, timeout=2)

                if ip_ping is None or ip_ping is False:
                    # Device is down
                    logger.warning(f"Device {ip} is down")
                    results["down"] += 1
                    results["down_devices"].append(ip)

                    if interactive:
                        print(f"{ip} is down!")
                else:
                    # Device is up, attempt backup
                    try:
                        logger.info(f"Backing up {ip} ({vendor_name})")

                        if needs_secret and secret:
                            vendor_module_obj.backup(ip, username, password, secret)
                        else:
                            vendor_module_obj.backup(ip, username, password)

                        results["success"] += 1
                        logger.success(f"Successfully backed up {ip}")

                    except Exception as e:
                        results["failed"] += 1
                        logger.error(f"Failed to backup {ip}: {e}")

                        if interactive:
                            print(f"Error backing up {ip}: {e}")

    except FileNotFoundError:
        logger.error(f"CSV file not found: {csv_path}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during backup: {e}")
        raise

    logger.info(
        f"Backup complete: {results['success']} succeeded, "
        f"{results['failed']} failed, {results['down']} down"
    )

    return results


# Typer CLI app
app = typer.Typer(help="Multi-vendor network device backup tool")


@app.callback()
def main(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file (default: /etc/router-backup/config.yaml)",
    ),
    devices: Optional[str] = typer.Option(
        None, "--devices", "-d", help="Path to devices CSV file (overrides config)"
    ),
    storage: Optional[str] = typer.Option(
        None, "--storage", "-s", help="Storage model: txt, git, or pygit (overrides config)"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    dry_run: bool = typer.Option(
        False, "--dryrun", "-n", help="Simulate backup without writing files"
    ),
):
    """Network device backup tool supporting multiple vendors."""
    # Load configuration
    global _config, _dry_run
    _dry_run = dry_run
    _config = load_config(
        config_file=config,
        devices_file=devices,
        storage_model=storage,
    )

    # Setup logging
    log_level = "DEBUG" if verbose else _config.log_level
    log_file = _config.log_file or os.path.join(_config.storage, "backup.log")
    setup_logging(log_level, log_file)

    # Ensure directories exist (unless dry-run)
    if not _dry_run:
        _config.ensure_directories()

    if verbose:
        logger.debug("Verbose logging enabled")

    if _dry_run:
        logger.info("DRY-RUN MODE: No files will be written")


def show_dry_run_summary():
    """Show dry-run summary if in dry-run mode."""
    global _storage
    if _storage and _storage.dry_run:
        summary = _storage.get_dry_run_summary()
        if summary:
            typer.echo(summary)


@app.command(name="all")
def backup_all():
    """Backup all vendor types from the CSV."""
    global _config
    logger.info("Starting backup for all vendors")

    for selection in VENDOR_MAP.keys():
        try:
            results = run_script(selection, config=_config)
            logger.info(f"{VENDOR_NAMES[selection]}: {results['success']} succeeded")
        except Exception as e:
            logger.error(f"Error backing up {VENDOR_NAMES[selection]}: {e}")

    show_dry_run_summary()


@app.command(name="cisco-ios")
def backup_cisco_ios():
    """Backup Cisco IOS devices."""
    global _config
    results = run_script("1", config=_config, interactive=True)
    typer.echo(f"Cisco IOS backup complete: {results['success']} succeeded")
    show_dry_run_summary()


@app.command(name="cisco-asa")
def backup_cisco_asa():
    """Backup Cisco ASA devices."""
    global _config
    results = run_script("2", config=_config, interactive=True)
    typer.echo(f"Cisco ASA backup complete: {results['success']} succeeded")
    show_dry_run_summary()


@app.command(name="juniper")
def backup_juniper():
    """Backup Juniper devices."""
    global _config
    results = run_script("3", config=_config, interactive=True)
    typer.echo(f"Juniper backup complete: {results['success']} succeeded")
    show_dry_run_summary()


@app.command(name="vyos")
def backup_vyos():
    """Backup VyOS routers."""
    global _config
    results = run_script("4", config=_config, interactive=True)
    typer.echo(f"VyOS backup complete: {results['success']} succeeded")
    show_dry_run_summary()


@app.command(name="huawei")
def backup_huawei():
    """Backup Huawei devices."""
    global _config
    results = run_script("5", config=_config, interactive=True)
    typer.echo(f"Huawei backup complete: {results['success']} succeeded")
    show_dry_run_summary()


@app.command(name="fortinet")
def backup_fortinet():
    """Backup Fortinet devices."""
    global _config
    results = run_script("6", config=_config, interactive=True)
    typer.echo(f"Fortinet backup complete: {results['success']} succeeded")
    show_dry_run_summary()


@app.command(name="microtik")
def backup_microtik():
    """Backup Microtik devices."""
    global _config
    results = run_script("7", config=_config, interactive=True)
    typer.echo(f"Microtik backup complete: {results['success']} succeeded")
    show_dry_run_summary()


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
    from router_backup.config import create_default_config

    config_path = path or get_default_config_path()

    if os.path.exists(config_path):
        typer.echo(f"Config file already exists: {config_path}")
        raise typer.Exit(1)

    config = create_default_config(config_path)
    typer.echo(f"Created default config at: {config_path}")
    typer.echo(f"  Device file: {config.device_file}")
    typer.echo(f"  Storage: {config.storage}")
    typer.echo(f"  Storage model: {config.storage_model}")


# Interactive menu (for backward compatibility when run directly)
def interactive_menu():
    """Show interactive menu for vendor selection."""
    global _config, _dry_run

    # Ensure we have a config
    if _config is None:
        _config = load_config()
        setup_logging(_config.log_level, _config.log_file)
        if not _dry_run:
            _config.ensure_directories()

    print("\nMulti-Vendor Network Backup Tool")
    print("=" * 40)
    if _dry_run:
        print("*** DRY-RUN MODE: No files will be written ***")
    print(
        f"Config: device_file={_config.device_file}, storage={_config.storage}, model={_config.storage_model}"
    )
    print()

    for key, name in VENDOR_NAMES.items():
        print(f"{key}. Backup {name} devices")

    print()
    user_selection = input("Please pick an option: ")

    if user_selection in VENDOR_MAP:
        try:
            results = run_script(user_selection, config=_config, interactive=True)
            print(f"\nBackup complete!")
            print(f"  Success: {results['success']}")
            print(f"  Failed: {results['failed']}")
            print(f"  Down: {results['down']}")
            show_dry_run_summary()
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            print(f"Error: {e}")
    else:
        print("Invalid option selected")


if __name__ == "__main__":
    # Check if running with arguments (CLI mode) or without (interactive mode)
    if len(sys.argv) > 1:
        app()
    else:
        interactive_menu()
