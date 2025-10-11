"""Helper functions for vault operations."""

from pathlib import Path


def is_encrypted(file_path: Path) -> bool:
    """
    Check if a file is Age-encrypted.

    Args:
    ----
        file_path: Path to the file to check

    Returns:
    -------
        True if the file is Age-encrypted, False otherwise

    """
    if not file_path.exists():
        return False

    try:
        with open(file_path, "rb") as f:
            # Age encrypted files start with "age-encryption.org/v1"
            header = f.read(24)
            return header.startswith(b"age-encryption.org/v1")
    except (OSError, PermissionError):
        return False
