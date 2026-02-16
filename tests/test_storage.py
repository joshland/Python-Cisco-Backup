#!/usr/bin/env python3
"""
Comprehensive test suite for storage_git.py and storage_pygit.py

This script tests both storage implementations with:
- Repository initialization
- File write operations
- File update operations
- Version listing
- Diff generation and verification
- File content verification
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def extract_commit_hashes(output):
    """Extract commit hashes from versions command output.

    Looks for lines with 8-character hex hashes at the beginning.
    """
    hashes = []
    for line in output.split("\n"):
        line = line.strip()
        # Match lines starting with 8 hex characters
        match = re.match(r"^([a-f0-9]{8})\s", line)
        if match:
            hashes.append(match.group(1))
    return hashes


class TestStorageGit(unittest.TestCase):
    """Test cases for storage_git.py"""

    @classmethod
    def setUpClass(cls):
        cls.script_path = Path(__file__).parent.parent / "router_backup" / "storage_git.py"
        if not cls.script_path.exists():
            raise FileNotFoundError(f"storage_git.py not found at {cls.script_path}")

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_storage_git_")
        self.repo_path = Path(self.test_dir) / "testrepo"

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def run_command(self, args):
        """Run a storage_git.py command and return result"""
        cmd = [sys.executable, str(self.script_path)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_init_repository(self):
        """Test repository initialization"""
        result = self.run_command(["init", "-p", str(self.repo_path)])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Initialized", result.stdout)
        self.assertTrue((self.repo_path / ".git").exists())

    def test_init_already_exists(self):
        """Test that init on existing repo shows appropriate message"""
        self.run_command(["init", "-p", str(self.repo_path)])
        result = self.run_command(["init", "-p", str(self.repo_path)])
        self.assertEqual(result.returncode, 0)
        self.assertIn("already initialized", result.stdout)

    def test_write_file(self):
        """Test writing a file and committing"""
        self.run_command(["init", "-p", str(self.repo_path)])

        result = self.run_command(
            [
                "write",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Hello World",
                "-m",
                "Initial commit",
            ]
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Committed", result.stdout)

        # Verify file was created
        file_path = self.repo_path / "test.txt"
        self.assertTrue(file_path.exists())
        with open(file_path) as f:
            self.assertEqual(f.read(), "Hello World")

    def test_write_file_without_init(self):
        """Test that writing without init fails gracefully"""
        result = self.run_command(
            ["write", "-p", str(self.repo_path), "test.txt", "-c", "Hello World"]
        )
        self.assertIn("not initialized", result.stdout)

    def test_update_file(self):
        """Test updating a file creates a new commit"""
        self.run_command(["init", "-p", str(self.repo_path)])
        self.run_command(["write", "-p", str(self.repo_path), "test.txt", "-c", "Version 1"])

        result = self.run_command(
            [
                "update",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Version 2",
                "-m",
                "Second version",
            ]
        )
        self.assertEqual(result.returncode, 0)

        # Verify file content
        with open(self.repo_path / "test.txt") as f:
            self.assertEqual(f.read(), "Version 2")

    def test_list_versions(self):
        """Test listing versions of a file"""
        self.run_command(["init", "-p", str(self.repo_path)])

        # Create multiple versions
        for i in range(3):
            self.run_command(
                [
                    "update",
                    "-p",
                    str(self.repo_path),
                    "test.txt",
                    "-c",
                    f"Version {i + 1}",
                    "-m",
                    f"Commit {i + 1}",
                ]
            )

        result = self.run_command(["versions", "-p", str(self.repo_path), "test.txt"])
        self.assertEqual(result.returncode, 0)

        # Extract commit hashes from output
        hashes = extract_commit_hashes(result.stdout)
        self.assertEqual(len(hashes), 3, f"Expected 3 commits, got hashes: {hashes}")

    def test_status(self):
        """Test repository status command"""
        self.run_command(["init", "-p", str(self.repo_path)])
        result = self.run_command(["status", "-p", str(self.repo_path)])
        self.assertEqual(result.returncode, 0)
        # Clean repo should indicate working tree clean

    def test_diff_versions(self):
        """Test diff between versions"""
        self.run_command(["init", "-p", str(self.repo_path)])
        self.run_command(
            [
                "write",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Line 1\nLine 2\n",
                "-m",
                "Initial",
            ]
        )
        self.run_command(
            [
                "update",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Line 1\nModified Line 2\nLine 3\n",
                "-m",
                "Modified",
            ]
        )

        # Get commit hashes
        result = self.run_command(["versions", "-p", str(self.repo_path), "test.txt"])
        hashes = extract_commit_hashes(result.stdout)

        if len(hashes) >= 2:
            # Test diff between two commits
            result = self.run_command(
                [
                    "diff",
                    "-p",
                    str(self.repo_path),
                    "test.txt",
                    hashes[1],
                    hashes[0],
                ]
            )
            self.assertEqual(result.returncode, 0)

            # Verify diff contains expected changes
            diff_output = result.stdout
            self.assertTrue(
                "Modified" in diff_output or "diff --git" in diff_output or "@@" in diff_output,
                f"Diff should show changes: {diff_output[:200]}",
            )

    def test_nested_paths(self):
        """Test writing files in subdirectories"""
        self.run_command(["init", "-p", str(self.repo_path)])

        result = self.run_command(
            [
                "write",
                "-p",
                str(self.repo_path),
                "subdir/nested/file.txt",
                "-c",
                "Nested content",
            ]
        )
        self.assertEqual(result.returncode, 0)

        file_path = self.repo_path / "subdir" / "nested" / "file.txt"
        self.assertTrue(file_path.exists())
        with open(file_path) as f:
            self.assertEqual(f.read(), "Nested content")

    def test_multiple_files(self):
        """Test handling multiple files"""
        self.run_command(["init", "-p", str(self.repo_path)])

        files = {
            "file1.txt": "Content 1",
            "file2.txt": "Content 2",
            "file3.txt": "Content 3",
        }

        for filename, content in files.items():
            result = self.run_command(["write", "-p", str(self.repo_path), filename, "-c", content])
            self.assertEqual(result.returncode, 0)

        # Verify all files exist
        for filename, content in files.items():
            file_path = self.repo_path / filename
            self.assertTrue(file_path.exists())
            with open(file_path) as f:
                self.assertEqual(f.read(), content)

        # Check each has versions
        for filename in files:
            result = self.run_command(["versions", "-p", str(self.repo_path), filename])
            self.assertEqual(result.returncode, 0)
            hashes = extract_commit_hashes(result.stdout)
            self.assertEqual(len(hashes), 1, f"Expected 1 commit for {filename}")


class TestStoragePyGit(unittest.TestCase):
    """Test cases for storage_pygit.py"""

    @classmethod
    def setUpClass(cls):
        cls.script_path = Path(__file__).parent.parent / "router_backup" / "storage_pygit.py"
        if not cls.script_path.exists():
            raise unittest.SkipTest("storage_pygit.py not found")

        # Check if pygit2 is available
        try:
            import pygit2
        except ImportError:
            raise unittest.SkipTest("pygit2 not installed")

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_storage_pygit_")
        self.repo_path = Path(self.test_dir) / "testrepo"

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def run_command(self, args):
        """Run a storage_pygit.py command and return result"""
        cmd = [sys.executable, str(self.script_path)] + args
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result

    def test_init_repository(self):
        """Test repository initialization with pygit2"""
        result = self.run_command(["init", "-p", str(self.repo_path)])
        self.assertEqual(result.returncode, 0)
        self.assertIn("Initialized", result.stdout)
        self.assertTrue((self.repo_path / ".git").exists())

    def test_write_file(self):
        """Test writing a file with pygit2"""
        self.run_command(["init", "-p", str(self.repo_path)])

        result = self.run_command(
            [
                "write",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Hello World",
            ]
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Committed", result.stdout)

    def test_update_file(self):
        """Test updating a file with pygit2"""
        self.run_command(["init", "-p", str(self.repo_path)])
        self.run_command(["write", "-p", str(self.repo_path), "test.txt", "-c", "Version 1"])

        result = self.run_command(
            [
                "update",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Version 2",
            ]
        )
        self.assertEqual(result.returncode, 0)

    def test_list_versions(self):
        """Test listing versions with pygit2"""
        self.run_command(["init", "-p", str(self.repo_path)])

        for i in range(3):
            self.run_command(
                [
                    "update",
                    "-p",
                    str(self.repo_path),
                    "test.txt",
                    "-c",
                    f"Version {i + 1}",
                ]
            )

        result = self.run_command(["versions", "-p", str(self.repo_path), "test.txt"])
        self.assertEqual(result.returncode, 0)

        hashes = extract_commit_hashes(result.stdout)
        self.assertGreaterEqual(len(hashes), 1, f"Expected at least 1 commit, got: {hashes}")

    def test_diff_versions(self):
        """Test diff functionality with pygit2"""
        self.run_command(["init", "-p", str(self.repo_path)])
        self.run_command(
            [
                "write",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Original content",
            ]
        )
        self.run_command(
            [
                "update",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Modified content",
            ]
        )

        # Get versions
        result = self.run_command(["versions", "-p", str(self.repo_path), "test.txt"])
        hashes = extract_commit_hashes(result.stdout)

        if len(hashes) >= 2:
            result = self.run_command(
                [
                    "diff",
                    "-p",
                    str(self.repo_path),
                    "test.txt",
                    hashes[1],
                    hashes[0],
                ]
            )
            self.assertEqual(result.returncode, 0)


class TestBothImplementations(unittest.TestCase):
    """Tests that compare both implementations for consistency"""

    @classmethod
    def setUpClass(cls):
        cls.git_script = Path(__file__).parent.parent / "router_backup" / "storage_git.py"
        cls.pygit_script = Path(__file__).parent.parent / "router_backup" / "storage_pygit.py"

        if not cls.git_script.exists():
            raise FileNotFoundError("storage_git.py not found")
        if not cls.pygit_script.exists():
            raise unittest.SkipTest("storage_pygit.py not found")

        try:
            import pygit2
        except ImportError:
            raise unittest.SkipTest("pygit2 not installed")

    def run_git_cmd(self, args):
        cmd = [sys.executable, str(self.git_script)] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def run_pygit_cmd(self, args):
        cmd = [sys.executable, str(self.pygit_script)] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def test_parallel_operations(self):
        """Test that both implementations produce similar results"""
        import tempfile
        import shutil

        git_dir = tempfile.mkdtemp(prefix="test_git_")
        pygit_dir = tempfile.mkdtemp(prefix="test_pygit_")

        try:
            # Initialize both repos
            self.run_git_cmd(["init", "-p", git_dir])
            self.run_pygit_cmd(["init", "-p", pygit_dir])

            # Write same file to both
            self.run_git_cmd(["write", "-p", git_dir, "test.txt", "-c", "Hello World"])
            self.run_pygit_cmd(["write", "-p", pygit_dir, "test.txt", "-c", "Hello World"])

            # Update both
            self.run_git_cmd(["update", "-p", git_dir, "test.txt", "-c", "Updated"])
            self.run_pygit_cmd(["update", "-p", pygit_dir, "test.txt", "-c", "Updated"])

            # Check versions in both
            git_versions = self.run_git_cmd(["versions", "-p", git_dir, "test.txt"])
            pygit_versions = self.run_pygit_cmd(["versions", "-p", pygit_dir, "test.txt"])

            self.assertEqual(git_versions.returncode, 0)
            self.assertEqual(pygit_versions.returncode, 0)

            # Both should have similar number of version lines
            git_hashes = extract_commit_hashes(git_versions.stdout)
            pygit_hashes = extract_commit_hashes(pygit_versions.stdout)
            self.assertEqual(
                len(git_hashes),
                len(pygit_hashes),
                f"Git has {len(git_hashes)} commits, pygit has {len(pygit_hashes)}",
            )

        finally:
            shutil.rmtree(git_dir, ignore_errors=True)
            shutil.rmtree(pygit_dir, ignore_errors=True)


class TestDiffVerification(unittest.TestCase):
    """Detailed tests for diff functionality with content verification"""

    @classmethod
    def setUpClass(cls):
        cls.script_path = Path(__file__).parent.parent / "router_backup" / "storage_git.py"
        if not cls.script_path.exists():
            raise FileNotFoundError("storage_git.py not found")

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="test_diff_")
        self.repo_path = Path(self.test_dir) / "testrepo"
        self.run_cmd(["init", "-p", str(self.repo_path)])

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def run_cmd(self, args):
        cmd = [sys.executable, str(self.script_path)] + args
        return subprocess.run(cmd, capture_output=True, text=True)

    def get_commit_hashes(self, filepath):
        """Extract commit hashes from versions output"""
        result = self.run_cmd(["versions", "-p", str(self.repo_path), filepath])
        return extract_commit_hashes(result.stdout)

    def test_diff_content_verification(self):
        """Verify diff output contains actual changes"""
        # Create initial file
        self.run_cmd(
            [
                "write",
                "-p",
                str(self.repo_path),
                "data.txt",
                "-c",
                "Line 1\nLine 2\nLine 3\n",
                "-m",
                "v1",
            ]
        )

        # Update file
        self.run_cmd(
            [
                "update",
                "-p",
                str(self.repo_path),
                "data.txt",
                "-c",
                "Line 1\nModified Line 2\nLine 3\nAdded Line 4\n",
                "-m",
                "v2",
            ]
        )

        hashes = self.get_commit_hashes("data.txt")
        self.assertEqual(len(hashes), 2, f"Expected 2 commits, got: {hashes}")

        # Get diff between the two versions (older to newer)
        result = self.run_cmd(
            [
                "diff",
                "-p",
                str(self.repo_path),
                "data.txt",
                hashes[1],
                hashes[0],
            ]
        )

        self.assertEqual(result.returncode, 0)
        diff = result.stdout

        # Verify diff contains expected content
        self.assertTrue(
            "Modified" in diff or "@@" in diff or "diff --git" in diff,
            f"Diff should show changes, got: {diff[:500]}",
        )

    def test_diff_single_commit(self):
        """Test diff with single commit (compares to current)"""
        self.run_cmd(
            [
                "write",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Original",
                "-m",
                "v1",
            ]
        )

        hashes = self.get_commit_hashes("test.txt")
        self.assertEqual(len(hashes), 1)

        # Diff against commit
        result = self.run_cmd(["diff", "-p", str(self.repo_path), "test.txt", hashes[0]])

        self.assertEqual(result.returncode, 0)

    def test_diff_additions_only(self):
        """Test diff with only line additions"""
        self.run_cmd(
            [
                "write",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Line 1\n",
                "-m",
                "v1",
            ]
        )
        self.run_cmd(
            [
                "update",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Line 1\nLine 2\nLine 3\n",
                "-m",
                "v2",
            ]
        )

        hashes = self.get_commit_hashes("test.txt")
        result = self.run_cmd(
            [
                "diff",
                "-p",
                str(self.repo_path),
                "test.txt",
                hashes[1],
                hashes[0],
            ]
        )

        self.assertEqual(result.returncode, 0)
        diff = result.stdout
        self.assertTrue(
            "Line 2" in diff or "@@" in diff or "diff --git" in diff,
            f"Diff should show additions, got: {diff[:500]}",
        )

    def test_diff_deletions_only(self):
        """Test diff with only line deletions"""
        self.run_cmd(
            [
                "write",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Line 1\nLine 2\nLine 3\n",
                "-m",
                "v1",
            ]
        )
        self.run_cmd(
            [
                "update",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Line 1\n",
                "-m",
                "v2",
            ]
        )

        hashes = self.get_commit_hashes("test.txt")
        result = self.run_cmd(
            [
                "diff",
                "-p",
                str(self.repo_path),
                "test.txt",
                hashes[1],
                hashes[0],
            ]
        )

        self.assertEqual(result.returncode, 0)

    def test_diff_no_changes(self):
        """Test diff when no changes exist"""
        self.run_cmd(
            [
                "write",
                "-p",
                str(self.repo_path),
                "test.txt",
                "-c",
                "Content",
                "-m",
                "v1",
            ]
        )

        hashes = self.get_commit_hashes("test.txt")
        # Diff a commit against itself
        result = self.run_cmd(
            [
                "diff",
                "-p",
                str(self.repo_path),
                "test.txt",
                hashes[0],
                hashes[0],
            ]
        )

        self.assertEqual(result.returncode, 0)
        # Should indicate no differences or empty diff


def run_comprehensive_test():
    """Run all tests with detailed output"""
    print("=" * 70)
    print("COMPREHENSIVE STORAGE_GIT.PY AND STORAGE_PYGIT.PY TEST SUITE")
    print("=" * 70)
    print()

    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestStorageGit))
    suite.addTests(loader.loadTestsFromTestCase(TestStoragePyGit))
    suite.addTests(loader.loadTestsFromTestCase(TestBothImplementations))
    suite.addTests(loader.loadTestsFromTestCase(TestDiffVerification))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print()
    print("=" * 70)
    if result.wasSuccessful():
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED")
        print(f"Failures: {len(result.failures)}")
        print(f"Errors: {len(result.errors)}")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)
