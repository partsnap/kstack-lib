"""KStack route type definitions."""

from enum import Enum


class KStackRoute(Enum):
    """
    KStack environment routes.

    Routes represent different deployment environments for the stack.
    Each route can run independently with its own set of services.
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    SCRATCH = "scratch"
    DATA_COLLECTION = "data-collection"

    @classmethod
    def from_string(cls, value: str) -> "KStackRoute":
        """
        Get route from string.

        Args:
        ----
            value: Route string (case-insensitive)

        Returns:
        -------
            Corresponding KStackRoute

        Raises:
        ------
            ValueError: If value doesn't match any route

        Example:
        -------
            >>> KStackRoute.from_string('development')
            <KStackRoute.DEVELOPMENT: 'development'>
            >>> KStackRoute.from_string('TESTING')
            <KStackRoute.TESTING: 'testing'>

        """
        value_lower = value.lower().strip()

        # Try to match enum value
        try:
            return cls(value_lower)
        except ValueError:
            pass

        # No match
        valid_routes = ", ".join(r.value for r in cls)
        raise ValueError(f"Invalid route: '{value}'. " f"Valid routes: {valid_routes}")

    @classmethod
    def all_routes(cls) -> list["KStackRoute"]:
        """Get list of all routes."""
        return list(cls)
