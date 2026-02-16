# Storage Git - File Version Control System

Two Python scripts that provide git-backed file storage with version control capabilities.

- `storage_git.py` - Uses shell commands to interact with git
- `storage_pygit.py` - Uses the pygit2 library for direct git operations

Both scripts provide identical functionality and CLI interfaces.

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

Both scripts share the same CLI interface:

```bash
# Initialize a new repository
./storage_git.py init -p ./myrepo
# or
./storage_pygit.py init -p ./myrepo

# Write a file
./storage_git.py write -p ./myrepo data.txt -c "Hello World" -m "Initial commit"

# Update a file
./storage_git.py update -p ./myrepo data.txt -c "Hello World Updated" -m "Fixed typo"

# List all versions of a file
./storage_git.py versions -p ./myrepo data.txt

# Show diff between current and a specific version
./storage_git.py diff -p ./myrepo data.txt abc1234

# Show diff between two versions
./storage_git.py diff -p ./myrepo data.txt abc1234 def5678

# Check repository status
./storage_git.py status -p ./myrepo
```

---

## Commands

### `init`
Initialize a new git repository.

**Options:**
- `-p, --path PATH` - Repository path (default: current directory)

```bash
./storage_git.py init -p ./myrepo
```

---

### `write`
Write a file and commit it to the repository.

**Arguments:**
- `filepath` - Path to the file (relative to repo root)

**Options:**
- `-c, --content TEXT` - File content (required)
- `-m, --message TEXT` - Commit message (optional, defaults to "Add {filepath}")
- `-p, --path PATH` - Repository path (default: current directory)

```bash
./storage_git.py write data.txt -c "Hello World" -m "Initial content"
```

---

### `update`
Update a file and commit the changes.

**Arguments:**
- `filepath` - Path to the file (relative to repo root)

**Options:**
- `-c, --content TEXT` - New content (required)
- `-m, --message TEXT` - Commit message (optional, defaults to "Update {filepath}")
- `-p, --path PATH` - Repository path (default: current directory)

```bash
./storage_git.py update data.txt -c "Updated content" -m "Fixed typo"
```

---

### `versions`
List all versions of a file with commit info.

**Arguments:**
- `filepath` - Path to the file

**Options:**
- `-p, --path PATH` - Repository path (default: current directory)

**Output:**
```
Versions of data.txt:
--------------------------------------------------------------------------------
  a1b2c3d4  2024-01-15 10:30:00  Update data.txt
  e5f6g7h8  2024-01-15 10:25:00  Fixed typo
  i9j0k1l2  2024-01-15 10:20:00  Add data.txt
```

```bash
./storage_git.py versions data.txt
```

---

### `diff`
Show differences between file versions.

**Arguments:**
- `filepath` - Path to the file
- `commit1` - First commit hash (8 chars or full hash)
- `commit2` - Second commit hash (optional - if omitted, compares commit1 with current)

**Options:**
- `-p, --path PATH` - Repository path (default: current directory)

```bash
# Diff current vs older version
./storage_git.py diff data.txt a1b2c3d4

# Diff two specific versions
./storage_git.py diff data.txt a1b2c3d4 e5f6g7h8
```

---

### `status`
Show repository status (modified, staged, untracked files).

**Options:**
- `-p, --path PATH` - Repository path (default: current directory)

```bash
./storage_git.py status -p ./myrepo
```

---

## Python API

Both classes can be used programmatically:

```python
from storage_git import StorageGit
# or
from storage_pygit import StoragePyGit

# Initialize
storage = StorageGit("./myrepo")  # or StoragePyGit
storage.init()

# Write file
storage.write_file("data.txt", "Hello World", "Initial commit")

# Update file
storage.update_file("data.txt", "Hello World Updated", "Fixed typo")

# List versions
versions = storage.list_versions("data.txt")
for v in versions:
    print(f"{v['hash']} - {v['message']}")

# Read specific version
content = storage.read_version("data.txt", "a1b2c3d4")

# Show diff
diff = storage.diff_versions("data.txt", "a1b2c3d4")
print(diff)

# Check status
print(storage.status())
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
# Create a repo and add some files
./storage_git.py init -p ./project
./storage_git.py write -p ./project config.json -c '{"version": 1}' -m "Initial config"
./storage_git.py write -p ./project README.md -c "# My Project" -m "Add readme"

# Make updates
./storage_git.py update -p ./project config.json -c '{"version": 2}' -m "Bump version"

# View history
./storage_git.py versions -p ./project config.json

# See what changed
./storage_git.py diff -p ./project config.json HEAD~1
```

### Programmatic Usage

```python
from storage_pygit import StoragePyGit

# Create a versioned document store
store = StoragePyGit("/var/docs")
store.init()

# Save document versions
doc_id = "report_2024"
for i, content in enumerate(["Draft", "Reviewed", "Final"]):
    store.write_file(f"{doc_id}.txt", content, f"Version {i+1}")

# Get all versions
versions = store.list_versions(f"{doc_id}.txt")
print(f"Document has {len(versions)} versions")

# Restore old version
old_content = store.read_version(f"{doc_id}.txt", versions[-1]['full_hash'])
```

---

## Troubleshooting

### storage_git.py
- **"git: command not found"** - Install git on your system
- **"Repository not initialized"** - Run `init` command first
- **Permission denied** - Make script executable: `chmod +x storage_git.py`

### storage_pygit.py
- **"No module named 'pygit2'"** - Run `uv pip install pygit2` or `pip install pygit2`
- **"libgit2 not found"** - Install libgit2 system library
- **Import errors on macOS** - May need to set DYLD_LIBRARY_PATH

---

## License

These scripts are provided as-is for educational and utility purposes.
