"""Pytest configuration and fixtures for kstack-lib tests."""

import shutil
import subprocess
import time
from collections.abc import Generator

import pytest


def is_docker_available() -> bool:
    """Check if Docker is available on the system."""
    return shutil.which("docker") is not None


def is_localstack_running() -> bool:
    """Check if localstack is already running on port 4566."""
    try:
        result = subprocess.run(
            ["curl", "-s", "http://localhost:4566/_localstack/health"],
            capture_output=True,
            timeout=2,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def localstack() -> Generator[None, None, None]:
    """Start localstack container for integration tests.

    Automatically starts localstack if Docker is available and it's not already running.
    Cleans up the container after tests complete.
    """
    if not is_docker_available():
        pytest.skip("Docker not available - skipping integration tests requiring localstack")

    # Check if localstack is already running
    already_running = is_localstack_running()

    container_name = "kstack-lib-test-localstack"
    container_id = None

    if not already_running:
        # Start localstack container
        try:
            result = subprocess.run(
                [
                    "docker",
                    "run",
                    "-d",
                    "--rm",
                    "--name",
                    container_name,
                    "-p",
                    "4566:4566",
                    "localstack/localstack:latest",
                ],
                capture_output=True,
                text=True,
                check=True,
            )
            container_id = result.stdout.strip()
            print(f"\n✓ Started localstack container: {container_id[:12]}")

            # Wait for localstack to be ready
            max_wait = 30
            for i in range(max_wait):
                if is_localstack_running():
                    print(f"✓ LocalStack ready after {i+1}s")
                    break
                time.sleep(1)
            else:
                raise TimeoutError(f"LocalStack failed to start within {max_wait}s")

        except subprocess.CalledProcessError as e:
            pytest.skip(f"Failed to start localstack container: {e.stderr}")
        except TimeoutError as e:
            # Clean up failed container
            if container_id:
                subprocess.run(["docker", "stop", container_name], capture_output=True)
            pytest.skip(str(e))

    try:
        yield
    finally:
        # Only stop container if we started it
        if not already_running and container_id:
            try:
                subprocess.run(
                    ["docker", "stop", container_name],
                    capture_output=True,
                    timeout=10,
                )
                print(f"\n✓ Stopped localstack container: {container_id[:12]}")
            except subprocess.TimeoutExpired:
                # Force kill if stop times out
                subprocess.run(["docker", "kill", container_name], capture_output=True)
