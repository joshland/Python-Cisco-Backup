#!/usr/bin/env python3
"""
storage_pygit.py - A file storage system backed by git using pygit2.

Uses pygit2 library instead of shell commands for better performance
and more control over git operations.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict

import pygit2


class StoragePyGit:
    """A storage system using pygit2 for version control."""

    def __init__(self, repo_path: str = "."):
        """Initialize StoragePyGit with a repository path."""
        self.repo_path = Path(repo_path).resolve()
        self.git_dir = self.repo_path / ".git"
        self.repo: Optional[pygit2.Repository] = None

        # Try to open repo if it exists
        if self.git_dir.exists():
            try:
                self.repo = pygit2.Repository(str(self.repo_path))
            except pygit2.GitError:
                pass

    def is_initialized(self) -> bool:
        """Check if the repository is initialized."""
        return self.repo is not None

    def init(self) -> bool:
        """Initialize a new git repository."""
        if self.is_initialized():
            print(f"Repository already initialized at {self.repo_path}")
            return False

        self.repo_path.mkdir(parents=True, exist_ok=True)

        try:
            self.repo = pygit2.init_repository(str(self.repo_path))

            # Configure git user if not set
            config = self.repo.config
            try:
                config["user.email"]
            except KeyError:
                config["user.email"] = "storage@git.local"
            try:
                config["user.name"]
            except KeyError:
                config["user.name"] = "StoragePyGit"

            print(f"Initialized empty repository at {self.repo_path}")
            return True
        except pygit2.GitError as e:
            print(f"Error initializing repository: {e}")
            return False

    def _create_signature(self) -> pygit2.Signature:
        """Create a git signature for commits."""
        config = self.repo.config
        try:
            email = config["user.email"]
        except KeyError:
            email = "storage@git.local"
        try:
            name = config["user.name"]
        except KeyError:
            name = "StoragePyGit"

        return pygit2.Signature(name, email, int(datetime.now().timestamp()))

    def write_file(self, filepath: str, content: str, commit_msg: Optional[str] = None) -> bool:
        """Write a file and commit it to the repository."""
        if not self.is_initialized():
            print("Repository not initialized. Run init() first.")
            return False

        full_path = self.repo_path / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)

        # Write content to file
        with open(full_path, "w") as f:
            f.write(content)

        # Get file status
        status = self.repo.status()

        # Check if file has changes
        file_status = status.get(filepath)
        if not file_status:
            # File may be untracked
            pass
        elif file_status == pygit2.GIT_STATUS_CURRENT:
            print(f"No changes to commit for {filepath}")
            return True

        # Stage the file
        self.repo.index.add(filepath)
        self.repo.index.write()

        # Create commit
        msg = commit_msg or f"Add {filepath}"
        tree = self.repo.index.write_tree()
        author = self._create_signature()
        committer = author

        # Get parent commit (if any)
        parents = []
        try:
            head = self.repo.head
            parents.append(head.target)
        except pygit2.GitError:
            # No HEAD yet (first commit)
            pass

        try:
            # Determine reference to update
            if not parents:
                # First commit - create master branch
                ref = "refs/heads/master"
            else:
                # Subsequent commits - update current branch
                ref = "HEAD"

            self.repo.create_commit(
                ref,
                author,
                committer,
                msg,
                tree,
                parents,
            )
            print(f"Committed {filepath}")
            return True
        except pygit2.GitError as e:
            print(f"Failed to commit: {e}")
            return False

    def update_file(self, filepath: str, content: str, commit_msg: Optional[str] = None) -> bool:
        """Update a file and commit the changes."""
        return self.write_file(filepath, content, commit_msg or f"Update {filepath}")

    def _resolve_hash(self, short_hash: str) -> Optional[str]:
        """Resolve a short hash to a full hash by searching commits."""
        if not self.is_initialized():
            return None

        try:
            # If it's already a full hash (40 chars), return it
            if len(short_hash) == 40:
                return short_hash

            # Walk through all commits to find matching short hash
            for commit in self.repo.walk(self.repo.head.target, pygit2.GIT_SORT_TIME):
                full_hash = str(commit.id)
                if full_hash.startswith(short_hash):
                    return full_hash
        except pygit2.GitError:
            pass

        return None

    def list_versions(self, filepath: str) -> List[Dict]:
        """List all versions of a file with their commit info."""
        if not self.is_initialized():
            print("Repository not initialized.")
            return []

        versions = []

        try:
            # Walk through commits
            for commit in self.repo.walk(self.repo.head.target, pygit2.GIT_SORT_TIME):
                # Check if file was modified in this commit
                if len(commit.parents) == 0:
                    # Initial commit - check if file exists in tree
                    try:
                        commit.tree / filepath
                        versions.append(
                            {
                                "hash": str(commit.id)[:8],
                                "full_hash": str(commit.id),
                                "date": datetime.fromtimestamp(commit.commit_time).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "message": commit.message.strip(),
                            }
                        )
                    except KeyError:
                        pass
                else:
                    # Compare with parent
                    parent = commit.parents[0]
                    diff = self.repo.diff(parent, commit)

                    for delta in diff.deltas:
                        if delta.new_file.path == filepath or delta.old_file.path == filepath:
                            versions.append(
                                {
                                    "hash": str(commit.id)[:8],
                                    "full_hash": str(commit.id),
                                    "date": datetime.fromtimestamp(commit.commit_time).strftime(
                                        "%Y-%m-%d %H:%M:%S"
                                    ),
                                    "message": commit.message.strip(),
                                }
                            )
                            break
        except pygit2.GitError as e:
            print(f"Error: {e}")

        return versions

    def read_version(self, filepath: str, commit_hash: str) -> Optional[str]:
        """Read a specific version of a file."""
        if not self.is_initialized():
            print("Repository not initialized.")
            return None

        try:
            # Resolve short hash to full hash
            full_hash = self._resolve_hash(commit_hash)
            if full_hash is None:
                print(f"Commit {commit_hash} not found")
                return None

            commit = self.repo.get(pygit2.Oid(hex=full_hash))
            if commit is None:
                print(f"Commit {commit_hash} not found")
                return None

            tree = commit.tree
            blob = tree / filepath
            return blob.data.decode("utf-8")
        except pygit2.GitError as e:
            print(f"Error reading version: {e}")
            return None

    def diff_versions(self, filepath: str, commit1: str, commit2: Optional[str] = None) -> str:
        """
        Show diff between two versions of a file.
        If commit2 is None, compares commit1 with current version.
        """
        if not self.is_initialized():
            return "Repository not initialized."

        try:
            # Resolve short hashes to full hashes
            full_hash1 = self._resolve_hash(commit1)
            if full_hash1 is None:
                return f"Commit {commit1} not found"

            c1 = self.repo.get(pygit2.Oid(hex=full_hash1))
            if c1 is None:
                return f"Commit {commit1} not found"

            if commit2:
                full_hash2 = self._resolve_hash(commit2)
                if full_hash2 is None:
                    return f"Commit {commit2} not found"
                c2 = self.repo.get(pygit2.Oid(hex=full_hash2))
                if c2 is None:
                    return f"Commit {commit2} not found"
                diff = self.repo.diff(c1, c2)
            else:
                # Diff commit1 with current working directory
                diff = self.repo.diff(c1)

            # Filter for our file and return patch text
            patch_output = []
            for delta in diff.deltas:
                if delta.new_file.path == filepath or delta.old_file.path == filepath:
                    # Get the patch text from the diff's patch property
                    # which returns the full unified diff format
                    if diff.patch:
                        patch_output.append(diff.patch)
                        break

            return "\n".join(patch_output) if patch_output else "No differences found."
        except pygit2.GitError as e:
            return f"Error: {e}"

    def diff_with_previous(self, filepath: str, commit_hash: str) -> str:
        """Show diff between a commit and its parent."""
        if not self.is_initialized():
            return "Repository not initialized."

        try:
            # Resolve short hash to full hash
            full_hash = self._resolve_hash(commit_hash)
            if full_hash is None:
                return f"Commit {commit_hash} not found"

            commit = self.repo.get(pygit2.Oid(hex=full_hash))
            if commit is None:
                return f"Commit {commit_hash} not found"

            if len(commit.parents) == 0:
                return "No parent commit (this is the initial commit)"

            parent = commit.parents[0]
            return self.diff_versions(filepath, str(parent.id), commit_hash)
        except pygit2.GitError as e:
            return f"Error: {e}"

    def status(self) -> str:
        """Show repository status."""
        if not self.is_initialized():
            return "Repository not initialized."

        output = []
        status = self.repo.status()

        status_map = {
            pygit2.GIT_STATUS_CURRENT: "current",
            pygit2.GIT_STATUS_INDEX_NEW: "staged (new)",
            pygit2.GIT_STATUS_INDEX_MODIFIED: "staged (modified)",
            pygit2.GIT_STATUS_INDEX_DELETED: "staged (deleted)",
            pygit2.GIT_STATUS_WT_NEW: "untracked",
            pygit2.GIT_STATUS_WT_MODIFIED: "modified",
            pygit2.GIT_STATUS_WT_DELETED: "deleted",
        }

        for filepath, flags in status.items():
            status_str = status_map.get(flags, f"unknown ({flags})")
            output.append(f"  {filepath}: {status_str}")

        if not output:
            return "Working tree clean"

        return "Repository status:\n" + "\n".join(output)


def main():
    """CLI interface for storage_pygit."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Git-backed file storage system using pygit2",
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

    storage = StoragePyGit(args.path)

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
