# Python3 Multivendor Backup
[![published](https://static.production.devnetcloud.com/codeexchange/assets/images/devnet-published.svg)](https://developer.cisco.com/codeexchange/github/repo/AlexMunoz905/Python-Cisco-Backup)

Backup your network configuration of a supported vendor, with easy options for automation.

## Supported Vendors
* Cisco IOS & ASA
* Juniper
* VyOS
* Huawei
* Fortinet
* MicroTik

This is running on Python3 with Netmiko, ping3, Typer, and Loguru.
Version 3.0

## Example:
CLI

![Screenshot of manual option](https://i.imgur.com/46JnIdM.png)
GUI

![Screenshot of GUI option](https://i.imgur.com/bmbiNce.png)

## Installation

### Quick Install (Using UV - Recommended)

This project supports [uv](https://docs.astral.sh/uv/), an extremely fast Python package manager:

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
git clone https://github.com/AlexMunoz905/Python-Cisco-Backup.git
cd Python-Cisco-Backup
uv venv
source .venv/bin/activate
uv pip install -e ".[all]"
```

### Using pip (Alternative)

```bash
# Clone repository
git clone https://github.com/AlexMunoz905/Python-Cisco-Backup.git
cd Python-Cisco-Backup

# Install dependencies
pip install -r requirements.txt
# Or manually:
pip install netmiko ping3 typer loguru
```

### Requirements

- Python 3.9+
- Git (for storage_git.py)
- libgit2 (optional, for storage_pygit.py)

See [INSTALL.md](INSTALL.md) for detailed installation instructions including system dependencies.

## Usage

### Configuration

Router-backup uses a YAML configuration file to define storage settings and device lists.

#### Initialize Configuration

```bash
# Create default config at /etc/router-backup/config.yaml
router-backup init-config

# Create config at custom location
router-backup init-config -p /path/to/config.yaml
```

#### Configuration File Format

```yaml
# /etc/router-backup/config.yaml
device_file: /etc/router-backup/devices.csv
storage: /var/lib/router-backup
storage_model: txt  # Options: txt, git, pygit
```

### CLI (Command Line Interface)

The CLI uses [Typer](https://typer.tiangolo.com/) for a modern, user-friendly command line experience.

#### Global Options

```bash
# Specify config file (default: /etc/router-backup/config.yaml)
router-backup -c /path/to/config.yaml cisco-ios

# Specify devices CSV file (overrides config)
router-backup -d /path/to/devices.csv cisco-ios

# Specify storage model: txt, git, or pygit (overrides config)
router-backup -s git cisco-ios

# Enable verbose logging
router-backup -v cisco-ios

# Combine options
router-backup -c config.yaml -d devices.csv -s pygit cisco-ios
```

#### Vendor-Specific Commands

```bash
# Backup Cisco IOS devices
router-backup cisco-ios

# Backup Cisco ASA devices
router-backup cisco-asa

# Backup Juniper devices
router-backup juniper

# Backup VyOS routers
router-backup vyos

# Backup Huawei devices
router-backup huawei

# Backup Fortinet devices
router-backup fortinet

# Backup Microtik devices
router-backup microtik

# Backup all vendor types
router-backup all

# Interactive mode (no command specified)
router-backup
```

#### Storage Models

- **txt** (default): Plain text files - Simple, no dependencies
- **git**: Git version control - Requires git installed, tracks all changes
- **pygit**: Native git via pygit2 - Requires pygit2 library, faster than git CLI

```bash
# Use plain text files
router-backup -s txt cisco-ios

# Use git for version control
router-backup -s git cisco-ios

# Use pygit2 for version control
router-backup -s pygit cisco-ios
```

#### Dry-Run Mode

Use `--dryrun` or `-n` to simulate backup operations without writing files:

```bash
# Preview what would be backed up
router-backup --dryrun cisco-ios

# Show total size and files that would be created
router-backup -n -s git cisco-ios

# Combine with other options
router-backup -c config.yaml -d devices.csv -n all
```

In dry-run mode, the tool will:
- Log all operations that would be performed
- Show total number of files that would be created
- Show total size of data that would be written
- Not actually connect to devices or write files

#### Direct Script Usage

You can also run the scripts directly without installing:

```bash
# Show help
python router_backup/multivendor_run.py --help

# Run with options
python router_backup/multivendor_run.py -c config.yaml -d devices.csv cisco-ios

# Run interactive menu
python router_backup/multivendor_run.py
```

### CSV File Format

The CSV file should contain the following columns:

| Column | Description | Required |
|--------|-------------|----------|
| 1 | IP Address/Hostname | Yes |
| 2 | Username | Yes |
| 3 | Password | Yes |
| 4 | Enable Secret | Only for Cisco IOS/ASA |

**Example CSV (`backup_hosts.csv`):**

```csv
192.168.1.1,admin,password123,enable_secret
192.168.1.2,admin,password123
10.0.0.1,root,password456
```

**Note:** The script automatically detects and skips header rows.

### GUI (Graphical User Interface)

1. Download & run executable from GitHub releases tab (if available).
2. Or run the GUI directly (after installation):
   ```bash
   router-backup-gui
   
   # Or with uv
   uv run router-backup-gui
   ```
3. Select the vendor you want to copy the config of.
4. Select the CSV file from the popup window.
5. It'll give you a popup for each successful configuration copied, as well as for each down host, if any.

## Settings & Configuration

### Output Directory

Backups are saved to the `backup-config/` directory (created automatically if it doesn't exist).

### Logging

Logs are written to `backup-config/backup.log` with the following features:
- Daily log rotation
- 7-day retention
- Structured format: `YYYY-MM-DD HH:mm:ss | LEVEL | message`

**Log Levels:**
- `INFO` (default) - Standard operation messages
- `DEBUG` (with `--verbose` flag) - Detailed debug information

### Output Files

1. **Configuration backups**: `{hostname}_{MM-DD-YYYY_HH-MM}.txt`
   - Example: `router1_02-15-2026_14-30.txt`

2. **Down devices list**: `down_devices_{MM-DD-YYYY_HH-MM}.txt`
   - Contains IP addresses of unreachable devices

## Getting help

If you are having trouble or need help, create an issue [here](https://github.com/alexmunoz905/Python-Cisco-Backup/issues)

## Contributors
- [ste-giraldo](https://github.com/ste-giraldo) for adding a memory and CPU saving feature to grabbing the hostname, and suggesting the ping feature.

## Credits and references

- [Netmiko](https://github.com/ktbyers/netmiko) by Kirk Byers
- [Ping3](https://github.com/kyan001/ping3) by Kyan
- [Typer](https://github.com/tiangolo/typer) by Sebastián Ramírez
- [Loguru](https://github.com/Delgan/loguru) by Delgan

----

## Licensing info

This code is with the MIT license.
