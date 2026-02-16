#!/usr/bin/env python3
"""
storage_git.py - A file storage system backed by git version control.

Provides functionality to:
- Initialize git repositories
- Write and commit files
- Update files with version history
- List file versions
- Diff files across versions
"""

import subprocess
from pathlib import Path
from typing import List, Optional, Tuple


class StorageGit:
    """A storage system using git for version control."""

    def __init__(self, repo_path: str = "."):
        """Initialize StorageGit with a repository path."""
        self.repo_path = Path(repo_path).resolve()
        self.git_dir = self.repo_path / ".git"

    def _run_git(
        self, args: List[str], check: bool = True
    ) -> subprocess.CompletedProcess:
        """Run a git command in the repository."""
        cmd = ["git", "-C", str(self.repo_path)] + args
        result = subprocess.run(cmd, capture_output=True, text=True, check=check)
        return result

    def is_initialized(self) -> bool:
        """Check if the repository is initialized."""
        return self.git_dir.exists()

    def init(self) -> bool:
        """Initialize a new git repository."""
        if self.is_initialized():
            print(f"Repository already initialized at {self.repo_path}")
            return False

        self.repo_path.mkdir(parents=True, exist_ok=True)
        result = self._run_git(["init"])

        # Configure git user if not set
        self._run_git(["config", "user.email", "storage@git.local"], check=False)
        self._run_git(["config", "user.name", "StorageGit"], check=False)

        print(f"Initialized empty repository at {self.repo_path}")
        return result.returncode == 0

    def write_file(
        self, filepath: str, content: str, commit_msg: Optional[str] = None
    ) -> bool:
        """Write a file and commit it to the repository."""
        if not self.is_initialized():
            print("Repository not initialized. Run init() first.")
            return False

        full_path = self.repo_path / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with open(full_path, "w") as f:
            f.write(content)

        # Stage and commit
        self._run_git(["add", filepath])

        msg = commit_msg or f"Add {filepath}"
        result = self._run_git(["commit", "-m", msg], check=False)

        if result.returncode == 0:
            print(f"Committed {filepath}")
            return True
        else:
            # Check if it's a no-change commit
            if (
                "nothing to commit" in result.stdout
                or "nothing to commit" in result.stderr
            ):
                print(f"No changes to commit for {filepath}")
                return True
            print(f"Failed to commit: {result.stderr}")
            return False

    def update_file(
        self, filepath: str, content: str, commit_msg: Optional[str] = None
    ) -> bool:
        """Update a file and commit the changes."""
        return self.write_file(filepath, content, commit_msg or f"Update {filepath}")

    def list_versions(self, filepath: str) -> List[dict]:
        """List all versions of a file with their commit info."""
        if not self.is_initialized():
            print("Repository not initialized.")
            return []

        result = self._run_git(
            ["log", "--follow", "--format=%H|%ci|%s", "--", filepath], check=False
        )

        if result.returncode != 0:
            print(f"Error: {result.stderr}")
            return []

        versions = []
        for line in result.stdout.strip().split("\n"):
            if line and "|" in line:
                parts = line.split("|", 2)
                if len(parts) == 3:
                    commit_hash, date_str, message = parts
                    versions.append(
                        {
                            "hash": commit_hash[:8],
                            "full_hash": commit_hash,
                            "date": date_str.strip(),
                            "message": message,
                        }
                    )

        return versions

    def read_version(self, filepath: str, commit_hash: str) -> Optional[str]:
        """Read a specific version of a file."""
        if not self.is_initialized():
            print("Repository not initialized.")
            return None

        result = self._run_git(["show", f"{commit_hash}:{filepath}"], check=False)

        if result.returncode == 0:
            return result.stdout
        else:
            print(f"Error reading version: {result.stderr}")
            return None

    def diff_versions(
        self, filepath: str, commit1: str, commit2: Optional[str] = None
    ) -> str:
        """
        Show diff between two versions of a file.
        If commit2 is None, compares commit1 with current version.
        """
        if not self.is_initialized():
            return "Repository not initialized."

        if commit2:
            result = self._run_git(
                ["diff", commit1, commit2, "--", filepath], check=False
            )
        else:
            result = self._run_git(["diff", commit1, "--", filepath], check=False)

        if result.returncode == 0:
            return result.stdout if result.stdout else "No differences found."
        else:
            return f"Error: {result.stderr}"

    def diff_with_previous(self, filepath: str, commit_hash: str) -> str:
        """Show diff between a commit and its parent."""
        if not self.is_initialized():
            return "Repository not initialized."

        result = self._run_git(
            ["diff", f"{commit_hash}^..{commit_hash}", "--", filepath], check=False
        )

        if result.returncode == 0:
            return result.stdout if result.stdout else "No differences found."
        else:
            return f"Error: {result.stderr}"

    def status(self) -> str:
        """Show repository status."""
        if not self.is_initialized():
            return "Repository not initialized."

        result = self._run_git(["status"])
        return result.stdout


def main():
    """CLI interface for storage_git."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Git-backed file storage system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Init command
    init_parser = subparsers.add_parser("init", help="Initialize a new repository")
    init_parser.add_argument("--path", "-p", default=".", help="Repository path")

    # Write command
    write_parser = subparsers.add_parser("write", help="Write a file and commit it")
    write_parser.add_argument("filepath", help="Path to the file")
    write_parser.add_argument("--content", "-c", required=True, help="File content")
    write_parser.add_argument("--message", "-m", help="Commit message")
    write_parser.add_argument("--path", "-p", default=".", help="Repository path")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update a file")
    update_parser.add_argument("filepath", help="Path to the file")
    update_parser.add_argument("--content", "-c", required=True, help="New content")
    update_parser.add_argument("--message", "-m", help="Commit message")
    update_parser.add_argument("--path", "-p", default=".", help="Repository path")

    # List versions command
    versions_parser = subparsers.add_parser("versions", help="List file versions")
    versions_parser.add_argument("filepath", help="Path to the file")
    versions_parser.add_argument("--path", "-p", default=".", help="Repository path")

    # Diff command
    diff_parser = subparsers.add_parser("diff", help="Show diff between versions")
    diff_parser.add_argument("filepath", help="Path to the file")
    diff_parser.add_argument("commit1", help="First commit hash")
    diff_parser.add_argument("commit2", nargs="?", help="Second commit hash (optional)")
    diff_parser.add_argument("--path", "-p", default=".", help="Repository path")

    # Status command
    status_parser = subparsers.add_parser("status", help="Show repository status")
    status_parser.add_argument("--path", "-p", default=".", help="Repository path")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    storage = StorageGit(args.path)

    if args.command == "init":
        storage.init()

    elif args.command == "write":
        storage.write_file(args.filepath, args.content, args.message)

    elif args.command == "update":
        storage.update_file(args.filepath, args.content, args.message)

    elif args.command == "versions":
        versions = storage.list_versions(args.filepath)
        if versions:
            print(f"\nVersions of {args.filepath}:")
            print("-" * 80)
            for v in versions:
                print(f"  {v['hash']}  {v['date']}  {v['message']}")
        else:
            print(f"No versions found for {args.filepath}")

    elif args.command == "diff":
        diff = storage.diff_versions(args.filepath, args.commit1, args.commit2)
        print(diff)

    elif args.command == "status":
        print(storage.status())


if __name__ == "__main__":
    main()
