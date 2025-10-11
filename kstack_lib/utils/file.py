"""File utilities."""

import logging
import subprocess
from pathlib import Path

LOGGER = logging.getLogger(__name__)


def get_mime_type(filename: Path | str) -> str:
    """
    Get the MIME type of a file.

    Args:
    ----
        filename: Path to the file

    Returns:
    -------
        MIME type string (defaults to 'application/octet-stream' if detection fails)

    Example:
    -------
        ```python
        from kstack_lib.utils import get_mime_type
        mime_type = get_mime_type("document.pdf")
        # Returns: 'application/pdf'
        ```

    """
    filename = Path(filename).resolve()
    mime_type = "application/octet-stream"
    try:
        result = subprocess.run(
            ["file", "--mime-type", str(filename)],
            capture_output=True,
            check=False,
        )
    except FileNotFoundError as error:
        LOGGER.warning(f"cmd 'file' not found: {error}")
    else:
        if result.returncode != 0:
            LOGGER.warning(f"Could not determine mime type - {result.stderr.decode('utf-8')}")
        else:
            mime_type = result.stdout.decode("utf-8").split(":")[1].strip()
    return mime_type
