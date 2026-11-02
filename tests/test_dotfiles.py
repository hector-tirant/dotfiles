import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "dotfiles"


class DotfilesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="dotfiles-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.repo = self.root / "repository with spaces"
        (self.repo / "scripts").mkdir(parents=True)
        self.script = self.repo / "scripts" / "dotfiles"
        shutil.copy2(SCRIPT, self.script)
        self.home = self.root / "home with spaces"
        self.home.mkdir()
        self.config = self.home / ".zshrc"
        self.managed = self.repo / "zsh" / ".zshrc"

    def run_command(self, *args, success=True, env=None):
        result = subprocess.run(
            [str(self.script), *map(str, args)],
            cwd=self.home,
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def prepare_managed(self, content="repository\n"):
        self.managed.parent.mkdir()
        self.managed.write_text(content)

    def failing_command_env(self, command):
        bin_dir = self.root / "bin"
        bin_dir.mkdir()
        stub = bin_dir / command
        stub.write_text("#!/bin/sh\nexit 1\n")
        stub.chmod(0o755)
        return dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"])

    def test_add_and_delete_preserve_content_and_permissions(self):
        self.config.write_text("original\n")
        self.config.chmod(0o600)
        self.run_command("--add", "--zsh", self.config)
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(self.config.resolve(), self.managed)
        self.assertEqual(self.managed.stat().st_mode & 0o777, 0o600)
        self.config.write_text("edited through link\n")
        self.assertEqual(self.managed.read_text(), "edited through link\n")
        self.run_command("--del", "--zsh", self.config)
        self.assertFalse(self.config.is_symlink())
        self.assertEqual(self.config.read_text(), "edited through link\n")
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertFalse(self.managed.exists())

    def test_git_detects_edits_through_link(self):
        self.config.write_text("original\n")
        self.run_command("--add", "--zsh", self.config)
        for args in (("init", "--quiet"), ("add", "zsh/.zshrc")):
            subprocess.run(["git", "-C", str(self.repo), *args], check=True)
        self.config.write_text("edited\n")
        result = subprocess.run(
            ["git", "-C", str(self.repo), "diff", "--name-only"],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.stdout.strip(), "zsh/.zshrc")

    def test_add_restores_local_file_when_link_creation_fails(self):
        self.config.write_text("local\n")
        self.run_command(
            "--add", "--zsh", self.config,
            success=False, env=self.failing_command_env("ln"),
        )
        self.assertFalse(self.config.is_symlink())
        self.assertEqual(self.config.read_text(), "local\n")
        self.assertFalse(self.managed.exists())

    def test_add_restores_backup_when_link_creation_fails(self):
        self.prepare_managed()
        self.config.write_text("local\n")
        self.run_command(
            "--add", "--zsh", self.config,
            success=False, env=self.failing_command_env("ln"),
        )
        self.assertFalse(self.config.is_symlink())
        self.assertEqual(self.config.read_text(), "local\n")
        self.assertEqual(self.managed.read_text(), "repository\n")

    def test_delete_recreates_link_when_move_fails(self):
        self.prepare_managed()
        self.config.symlink_to(self.managed)
        self.run_command(
            "--del", "--zsh", self.config,
            success=False, env=self.failing_command_env("mv"),
        )
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(self.config.resolve(), self.managed)
        self.assertEqual(self.managed.read_text(), "repository\n")

    def test_existing_repository_file_backs_up_local_file(self):
        self.prepare_managed()
        self.config.write_text("local\n")
        self.config.chmod(0o600)
        self.run_command("--zsh", "--add", self.config)
        backups = list(self.home.glob(".zshrc.dotfiles-backup.*"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "local\n")
        self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(self.config.read_text(), "repository\n")

    def test_existing_repository_file_can_be_linked_without_local_file(self):
        self.prepare_managed()
        self.run_command("--add", "--zsh", ".zshrc")
        self.assertEqual(self.config.resolve(), self.managed)

    def test_add_leaves_all_existing_links_unchanged(self):
        self.prepare_managed()
        for target in (str(self.managed), "missing", "other"):
            with self.subTest(target=target):
                self.config.symlink_to(target)
                result = self.run_command("--add", "--zsh", self.config)
                self.assertIn("Warning:", result.stderr)
                self.assertEqual(os.readlink(self.config), target)
                self.assertEqual(self.managed.read_text(), "repository\n")
                self.config.unlink()

    def test_delete_accepts_relative_link_to_managed_file(self):
        self.prepare_managed()
        self.config.symlink_to(os.path.relpath(self.managed, self.home))
        self.run_command("--del", "--zsh", self.config)
        self.assertFalse(self.config.is_symlink())
        self.assertEqual(self.config.read_text(), "repository\n")

    def test_delete_rejects_unmanaged_link(self):
        self.prepare_managed()
        other = self.home / "other"
        other.write_text("unmanaged\n")
        self.config.symlink_to(other)
        self.run_command("--del", "--zsh", self.config, success=False)
        self.assertTrue(self.config.is_symlink())
        self.assertEqual(other.read_text(), "unmanaged\n")
        self.assertTrue(self.managed.exists())

    def test_delete_rejects_regular_file_and_missing_repository_file(self):
        self.config.write_text("local\n")
        self.run_command("--del", "--zsh", self.config, success=False)
        self.assertEqual(self.config.read_text(), "local\n")
        self.config.unlink()
        self.config.symlink_to(self.managed)
        self.run_command("--del", "--zsh", self.config, success=False)
        self.assertTrue(self.config.is_symlink())

    def test_add_rejects_directories_missing_files_and_repository_paths(self):
        self.run_command("--add", "--zsh", self.config, success=False)
        self.config.mkdir()
        self.run_command("--add", "--zsh", self.config, success=False)
        self.assertTrue(self.config.is_dir())
        self.prepare_managed()
        self.run_command("--add", "--zsh", self.managed, success=False)
        self.assertEqual(self.managed.read_text(), "repository\n")

    def test_add_rejects_symlinked_repository_directory_or_file(self):
        self.config.write_text("local\n")
        (self.repo / "zsh").symlink_to(self.home, target_is_directory=True)
        self.run_command("--add", "--zsh", self.config, success=False)
        (self.repo / "zsh").unlink()
        self.managed.parent.mkdir()
        self.managed.symlink_to(self.config)
        self.run_command("--add", "--zsh", self.config, success=False)
        self.assertEqual(self.config.read_text(), "local\n")
        self.assertFalse(self.config.is_symlink())

    def test_invalid_arguments_do_not_modify_local_file(self):
        self.config.write_text("local\n")
        cases = [
            (),
            ("--add", self.config),
            ("--zsh", self.config),
            ("--add", "--del", "--zsh", self.config),
            ("--add", "--unknown", self.config),
            ("--add", "--zsh", self.config, self.config),
            ("--add", "--zsh", str(self.config) + "/"),
        ]
        for args in cases:
            with self.subTest(args=args):
                self.run_command(*args, success=False)
                self.assertEqual(self.config.read_text(), "local\n")
                self.assertFalse(self.config.is_symlink())


if __name__ == "__main__":
    unittest.main()
