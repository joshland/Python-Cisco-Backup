# Installation Guide

This project supports both `pip` and `uv` for package management.

## Using UV (Recommended)

[uv](https://docs.astral.sh/uv/) is an extremely fast Python package installer and resolver written in Rust.

### Install uv

```bash
# On macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Or with pip
pip install uv
```

### Install the project

```bash
# Clone the repository
git clone https://github.com/AlexMunoz905/Python-Cisco-Backup.git
cd Python-Cisco-Backup

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### Using uv for development

```bash
# Sync dependencies from pyproject.toml
uv pip sync pyproject.toml

# Install with all optional dependencies
uv pip install -e ".[all]"

# Run tests
uv run pytest tests/ -v

# Run CLI commands
uv run router-backup --help
uv run storage-git --help
```

## Using pip (Alternative)

If you prefer traditional pip:

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install from requirements.txt
pip install -r requirements.txt

# Or install the package
pip install -e ".[dev]"
```

## System Dependencies (pygit2)

If using `storagecli` with pygit model, you need libgit2:

### Ubuntu/Debian
```bash
sudo apt-get install libgit2-dev
```

### macOS
```bash
brew install libgit2
```

### Then install pygit2
```bash
# Using uv
uv pip install pygit2

# Using pip
pip install pygit2
```

## Running Tests

```bash
# Using uv
uv run pytest tests/ -v

# Or directly
python tests/test_storage.py
```

## CLI Commands After Installation

```bash
# CLI backup tool
router-backup --help

# GUI backup tool
router-backup-gui

# Storage CLI (unified - supports txt/git/pygit)
storagecli --help
storagecli init
storagecli write config.txt -c "content"
storagecli versions config.txt

# Run with uv
uv run router-backup --help
uv run storagecli --help
```
