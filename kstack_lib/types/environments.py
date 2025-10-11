"""KStack environment type definitions."""

from enum import Enum


class KStackEnvironment(Enum):
    """
    KStack deployment environments.

    Environments represent different deployment contexts for the stack.
    Each environment can run independently with its own set of services.
    """

    DEVELOPMENT = "dev"
    TESTING = "test"
    STAGING = "staging"
    PRODUCTION = "prod"
    SCRATCH = "scratch"
    DATA_COLLECTION = "data-collection"

    @classmethod
    def from_string(cls, value: str) -> "KStackEnvironment":
        """
        Get environment from string.

        Args:
        ----
            value: Environment string (case-insensitive)

        Returns:
        -------
            Corresponding KStackEnvironment

        Raises:
        ------
            ValueError: If value doesn't match any environment

        Example:
        -------
            >>> KStackEnvironment.from_string('dev')
            <KStackEnvironment.DEVELOPMENT: 'dev'>
            >>> KStackEnvironment.from_string('TEST')
            <KStackEnvironment.TESTING: 'test'>

        """
        value_lower = value.lower().strip()

        # Try to match enum value
        try:
            return cls(value_lower)
        except ValueError:
            pass

        # No match
        valid_environments = ", ".join(e.value for e in cls)
        raise ValueError(f"Invalid environment: '{value}'. " f"Valid environments: {valid_environments}")

    @classmethod
    def all_environments(cls) -> list["KStackEnvironment"]:
        """Get list of all environments."""
        return list(cls)
