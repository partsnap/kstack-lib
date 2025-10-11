"""Utility functions for kstack-lib."""

import subprocess

from partsnap_logger.logging import psnap_get_logger

LOGGER = psnap_get_logger("kstack_lib.utils")


def run_command(
    cmd: list[str],
    check: bool = True,
    capture: bool = True,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess:
    """
    Run a shell command with consistent handling.

    Args:
    ----
        cmd: Command and arguments as a list
        check: If True, raise CalledProcessError on non-zero exit
        capture: If True, capture stdout/stderr
        env: Optional environment variables (merged with os.environ)
        timeout: Optional timeout in seconds

    Returns:
    -------
        CompletedProcess instance with returncode, stdout, stderr

    Raises:
    ------
        subprocess.CalledProcessError: If check=True and command fails
        subprocess.TimeoutExpired: If timeout is exceeded

    Example:
    -------
        ```python
        from kstack_lib.utils import run_command

        # Simple command
        result = run_command(["kubectl", "get", "pods"])
        print(result.stdout)

        # With environment variables
        result = run_command(
            ["partsecrets", "reveal"],
            env={"PARTSECRETS_VAULT_PATH": "/path/to/vault"}
        )

        # Don't raise on failure
        result = run_command(["kubectl", "get", "nonexistent"], check=False)
        if result.returncode != 0:
            print(f"Command failed: {result.stderr}")
        ```

    """
    import os

    # Merge environment if provided
    command_env = os.environ.copy()
    if env:
        command_env.update(env)

    LOGGER.debug(f"Running command: {' '.join(cmd)}")

    return subprocess.run(
        cmd,
        capture_output=capture,
        text=True,
        check=check,
        env=command_env,
        timeout=timeout,
    )
