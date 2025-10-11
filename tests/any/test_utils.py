"""Tests for kstack_lib.any.utils module."""

import subprocess
from unittest.mock import patch

import pytest

from kstack_lib.any.utils import run_command


class TestRunCommand:
    """Test run_command function."""

    def test_simple_command_success(self):
        """Test running a simple successful command."""
        result = run_command(["echo", "hello"])

        assert result.returncode == 0
        assert "hello" in result.stdout
        assert result.stderr == ""

    def test_command_with_arguments(self):
        """Test running a command with multiple arguments."""
        result = run_command(["echo", "-n", "test"])

        assert result.returncode == 0
        assert result.stdout == "test"

    def test_command_failure_with_check_true(self):
        """Test command failure raises CalledProcessError when check=True."""
        with pytest.raises(subprocess.CalledProcessError) as exc_info:
            run_command(["false"])

        assert exc_info.value.returncode != 0

    def test_command_failure_with_check_false(self):
        """Test command failure doesn't raise when check=False."""
        result = run_command(["false"], check=False)

        assert result.returncode != 0

    def test_capture_output_true(self):
        """Test capturing output when capture=True (default)."""
        result = run_command(["echo", "captured"])

        assert result.stdout == "captured\n"
        assert result.stderr == ""

    @patch("subprocess.run")
    def test_capture_output_false(self, mock_run):
        """Test not capturing output when capture=False."""
        mock_run.return_value = subprocess.CompletedProcess(
            args=["echo", "test"], returncode=0, stdout=None, stderr=None
        )

        run_command(["echo", "test"], capture=False)

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["capture_output"] is False

    def test_environment_variables(self):
        """Test passing custom environment variables."""
        result = run_command(["sh", "-c", "echo $TEST_VAR"], env={"TEST_VAR": "custom_value"})

        assert "custom_value" in result.stdout

    def test_environment_variables_merged_with_os_environ(self):
        """Test that custom env vars are merged with os.environ."""
        # PATH should still be available from os.environ
        result = run_command(["sh", "-c", "echo $PATH:$CUSTOM"], env={"CUSTOM": "added"})

        # Should have both PATH (from os.environ) and CUSTOM (from env param)
        assert ":" in result.stdout  # PATH separator
        assert "added" in result.stdout

    @patch("subprocess.run")
    def test_timeout_parameter(self, mock_run):
        """Test passing timeout parameter."""
        mock_run.return_value = subprocess.CompletedProcess(args=["sleep", "10"], returncode=0, stdout="", stderr="")

        run_command(["sleep", "10"], timeout=5)

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs["timeout"] == 5

    def test_timeout_expired_raises(self):
        """Test that timeout expiration raises TimeoutExpired."""
        with pytest.raises(subprocess.TimeoutExpired):
            run_command(["sleep", "10"], timeout=0.1)

    def test_returns_completed_process(self):
        """Test that function returns subprocess.CompletedProcess."""
        result = run_command(["echo", "test"])

        assert isinstance(result, subprocess.CompletedProcess)
        assert hasattr(result, "returncode")
        assert hasattr(result, "stdout")
        assert hasattr(result, "stderr")

    def test_text_mode_enabled(self):
        """Test that output is returned as text (not bytes)."""
        result = run_command(["echo", "test"])

        assert isinstance(result.stdout, str)
        assert isinstance(result.stderr, str)

    def test_command_with_special_characters(self):
        """Test running command with special characters in arguments."""
        result = run_command(["echo", "hello world", "foo&bar"])

        assert "hello world" in result.stdout
        assert "foo&bar" in result.stdout

    def test_stderr_capture(self):
        """Test capturing stderr output."""
        result = run_command(["sh", "-c", "echo error >&2"])

        assert result.returncode == 0
        assert result.stdout == ""
        assert "error" in result.stderr

    @patch("subprocess.run")
    def test_check_parameter_passed(self, mock_run):
        """Test that check parameter is passed to subprocess.run."""
        mock_run.return_value = subprocess.CompletedProcess(args=["test"], returncode=0, stdout="", stderr="")

        run_command(["test"], check=True)
        assert mock_run.call_args[1]["check"] is True

        run_command(["test"], check=False)
        assert mock_run.call_args[1]["check"] is False

    def test_no_environment_variables(self):
        """Test running command without custom environment variables."""
        result = run_command(["echo", "no env"])

        assert result.returncode == 0
        assert "no env" in result.stdout

    @patch("subprocess.run")
    def test_env_none_uses_os_environ(self, mock_run):
        """Test that env=None uses os.environ copy."""
        import os

        mock_run.return_value = subprocess.CompletedProcess(args=["test"], returncode=0, stdout="", stderr="")

        run_command(["test"], env=None)

        call_kwargs = mock_run.call_args[1]
        passed_env = call_kwargs["env"]

        # Should be a copy of os.environ
        assert "PATH" in passed_env
        assert len(passed_env) >= len(os.environ)

    def test_multiline_output(self):
        """Test handling multiline command output."""
        result = run_command(["sh", "-c", "echo line1; echo line2; echo line3"])

        assert "line1" in result.stdout
        assert "line2" in result.stdout
        assert "line3" in result.stdout
        assert result.stdout.count("\n") >= 3

    def test_empty_output(self):
        """Test command with no output."""
        result = run_command(["true"])

        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""

    def test_command_list_not_string(self):
        """Test that command must be a list."""
        # Should work with list
        result = run_command(["echo", "test"])
        assert result.returncode == 0

        # subprocess.run should handle string differently (shell mode)
        # Our function expects list format
