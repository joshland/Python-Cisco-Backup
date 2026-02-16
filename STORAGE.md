# Storage Git - File Version Control System

Router-backup includes a flexible storage system supporting plain text files, git repositories, and pygit2 for version-controlled configuration backups.

## Quick Start with Router-Backup

The easiest way to use storage is through the main router-backup CLI:

```bash
# Use plain text files (default)
router-backup -s txt cisco-ios

# Use git for version control
router-backup -s git cisco-ios

# Use pygit2 for version control
router-backup -s pygit cisco-ios
```

### Configuration

Add storage settings to your config file:

```yaml
# /etc/router-backup/config.yaml
device_file: /etc/router-backup/devices.csv
storage: /var/lib/router-backup
storage_model: git  # Options: txt, git, pygit
```

---

## Storage CLI

A unified storage CLI is available as `storagecli`:

```bash
# Initialize storage
storagecli init

# Write files
storagecli write config.txt -c "interface eth0" -m "Initial config"

# Update files
storagecli update config.txt -c "interface eth0\n  ip address 10.0.0.1/24" -m "Add IP"

# List versions
storagecli versions config.txt

# Show diff between versions
storagecli diff config.txt abc1234 def5678

# Read specific version
storagecli read config.txt abc1234

# Check repository status
storagecli status
```

### Storage CLI Options

```bash
# Use specific config file
storagecli -c /path/to/config.yaml init

# Override storage path
storagecli -s /var/backups/storage write config.txt -c "hostname router1"

# Override storage model
storagecli -m pygit init

# Combine options
storagecli -c config.yaml -m git -s /var/backups versions config.txt
```

---

## Installation

### storage_git.py
No additional dependencies required. Just needs git installed on your system.

```bash
# Check git is installed
git --version
```

### storage_pygit.py
Requires the pygit2 library and libgit2 system library.

#### Using UV (Recommended)
```bash
# Install pygit2
uv pip install pygit2

# On Ubuntu/Debian, you may need:
sudo apt-get install libgit2-dev

# On macOS with Homebrew:
brew install libgit2
```

#### Using pip
```bash
# Install pygit2
pip install pygit2

# On Ubuntu/Debian, you may need:
sudo apt-get install libgit2-dev

# On macOS with Homebrew:
brew install libgit2
```

---

## Usage

The unified `storagecli` command provides all storage functionality:

```bash
# Initialize storage (uses config file for settings)
storagecli init

# Write a file
storagecli write data.txt -c "Hello World" -m "Initial commit"

# Update a file
storagecli update data.txt -c "Hello World Updated" -m "Fixed typo"

# List all versions of a file (git/pygit only)
storagecli versions data.txt

# Show diff between versions (git/pygit only)
storagecli diff data.txt abc1234 def5678

# Read a specific version (git/pygit only)
storagecli read data.txt abc1234

# Check repository status (git/pygit only)
storagecli status
```

### Global Options

```bash
# Use specific config file
storagecli -c /etc/router-backup/config.yaml init

# Override storage path
storagecli -s /var/backups/storage write data.txt -c "content"

# Override storage model
storagecli -m pygit init

# Enable verbose output
storagecli -v versions data.txt
```

---

## Commands

### `init`
Initialize the storage repository.

**Options:**
- `--force, -f` - Force reinitialize if already exists

```bash
# Initialize with config defaults
storagecli init

# Force reinitialize
storagecli init --force

# Initialize with specific model
storagecli -m git init
```

---

### `write`
Write a file to storage.

**Arguments:**
- `filepath` - Path to the file (relative to storage)

**Options:**
- `-c, --content TEXT` - File content (required)
- `-m, --message TEXT` - Commit message (optional, for git/pygit)

```bash
storagecli write config.txt -c "hostname router1" -m "Initial config"
```

---

### `update`
Update an existing file in storage.

**Arguments:**
- `filepath` - Path to the file (relative to storage)

**Options:**
- `-c, --content TEXT` - New content (required)
- `-m, --message TEXT` - Commit message (optional, for git/pygit)

```bash
storagecli update config.txt -c "hostname router2" -m "Changed hostname"
```

---

### `versions`
List all versions of a file with commit info (git/pygit only).

**Arguments:**
- `filepath` - Path to the file

**Output:**
```
Versions of data.txt:
--------------------------------------------------------------------------------
  a1b2c3d4  2024-01-15 10:30:00  Update data.txt
  e5f6g7h8  2024-01-15 10:25:00  Fixed typo
  i9j0k1l2  2024-01-15 10:20:00  Add data.txt
```

```bash
storagecli versions config.txt
```

---

### `diff`
Show differences between file versions (git/pygit only).

**Arguments:**
- `filepath` - Path to the file
- `commit1` - First commit hash (8 chars or full hash)
- `commit2` - Second commit hash (optional - if omitted, compares commit1 with current)

```bash
# Diff current vs older version
storagecli diff config.txt a1b2c3d4

# Diff two specific versions
storagecli diff config.txt a1b2c3d4 e5f6g7h8
```

---

### `read`
Read a specific version of a file (git/pygit only).

**Arguments:**
- `filepath` - Path to the file
- `commit` - Commit hash to read

**Options:**
- `-o, --output TEXT` - Output file (default: stdout)

```bash
# Print to stdout
storagecli read config.txt a1b2c3d4

# Save to file
storagecli read config.txt a1b2c3d4 -o old-config.txt
```

---

### `status`
Show repository status (git/pygit only).

```bash
storagecli status
```

---

## Python API

Use the unified `BackupStorage` class:

```python
from router_backup.storage import BackupStorage

# Initialize storage with desired model
storage = BackupStorage(
    storage_path="/var/lib/router-backup",
    storage_model="git",  # Options: "txt", "git", "pygit"
    hostname="storagecli",
    timestamp="2024-01-15_10-30"
)

# Write file (automatically commits for git/pygit)
storage.write_backup(
    filename="config",
    content="hostname router1",
    device_ip="192.168.1.1"  # Optional, used in commit message
)

# Update file
storage.write_backup(
    filename="config",
    content="hostname router1\ninterface eth0",
    device_ip="192.168.1.1"
)

# List versions (git/pygit only)
versions = storage.get_versions("config")
for v in versions:
    print(f"{v['hash']} - {v['message']}")

# Read specific version (git/pygit only)
content = storage.get_version_content("config", "a1b2c3d4")

# Show diff (git/pygit only)
diff = storage.diff_versions("config", "a1b2c3d4", "e5f6g7h8")
print(diff)
```

### Direct Storage Classes

For lower-level access, you can use the storage classes directly:

```python
from router_backup.storage_git import StorageGit
from router_backup.storage_pygit import StoragePyGit

# Git storage (uses git CLI)
storage = StorageGit("/var/backups")
storage.init()
storage.write_file("config.txt", "content", "commit message")

# Pygit2 storage (uses libgit2)
storage = StoragePyGit("/var/backups")
storage.init()
storage.write_file("config.txt", "content", "commit message")
```

---

## Choosing Between storage_git.py and storage_pygit.py

| Feature | storage_git.py | storage_pygit.py |
|---------|---------------|------------------|
| Dependencies | Git CLI only | pygit2 + libgit2 |
| Performance | Slower (subprocess) | Faster (native) |
| Portability | Requires git installed | Self-contained binary |
| Error Handling | Exit codes | Python exceptions |
| Memory Usage | Lower | Higher |

**Use storage_git.py when:**
- You want simplicity with no extra Python dependencies
- Git is already installed on your system
- You're doing simple operations

**Use storage_pygit.py when:**
- Performance matters (no shell overhead)
- You need programmatic control with exceptions
- You're building an application that bundles dependencies
- You want to avoid shell injection risks

---

## Examples

### Basic Workflow

```bash
# Initialize storage (reads from config file)
storagecli init

# Add files
storagecli write config.json -c '{"version": 1}' -m "Initial config"
storagecli write README.md -c "# My Project" -m "Add readme"

# Make updates
storagecli update config.json -c '{"version": 2}' -m "Bump version"

# View history (git/pygit only)
storagecli versions config.json

# See what changed (git/pygit only)
storagecli diff config.json HEAD~1
```

### Router-Backup Integration

When using git or pygit storage with router-backup, each device backup is automatically committed:

```bash
# Run backup with git storage
router-backup -s git -c config.yaml cisco-ios

# View backup history
storagecli versions router1_02-15-2025_14-30.txt

# Compare versions
storagecli diff router1_02-15-2025_14-30.txt abc1234 def5678

# Restore old version
storagecli read router1.txt abc1234 -o old_config.txt
```

### Programmatic Usage

```python
from router_backup.storage import BackupStorage

# Create storage instance
storage = BackupStorage(
    storage_path="/var/lib/router-backup",
    storage_model="git",
    hostname="router1",
    timestamp="02-15-2025_14-30"
)

# Write backup with automatic git commit
storage.write_backup(
    filename="router1_02-15-2025_14-30",
    content="interface configuration...",
    device_ip="192.168.1.1"
)

# Get version history
versions = storage.get_versions("router1_02-15-2025_14-30")
for v in versions:
    print(f"{v['hash']}: {v['message']}")

# View diffs
storage.diff_versions("router1_02-15-2025_14-30", "abc1234", "def5678")
```

---

## Troubleshooting

### storagecli

#### General Issues
- **"Config file not found"** - Run `storagecli init-config` to create default config
- **"Storage not initialized"** - Run `storagecli init` before other commands
- **"Version control not available with txt storage model"** - Use `-m git` or `-m pygit` for version control features

#### Git Storage Issues
- **"git: command not found"** - Install git on your system
- **"Repository not initialized"** - Run `storagecli init` with `-m git`

#### Pygit2 Storage Issues
- **"No module named 'pygit2'"** - Run `uv pip install pygit2` or `pip install pygit2`
- **"libgit2 not found"** - Install libgit2 system library
- **Import errors on macOS** - May need to set DYLD_LIBRARY_PATH

### Legacy Scripts
The individual `storage_git.py` and `storage_pygit.py` scripts are still available for backward compatibility:

```bash
# Direct script usage (deprecated, use storagecli instead)
python router_backup/storage_git.py init -p ./repo
python router_backup/storage_pygit.py init -p ./repo
```

---

## License

These scripts are provided as-is for educational and utility purposes.
