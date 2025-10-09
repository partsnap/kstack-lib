"""Tests for KStack custom exceptions."""

import pytest

from kstack_lib.exceptions import (
    ConfigurationError,
    KStackError,
    LayerAccessError,
    RouteError,
    ServiceNotFoundError,
)


class TestExceptionHierarchy:
    """Test exception inheritance hierarchy."""

    def test_all_exceptions_inherit_from_kstack_error(self):
        """Test that all custom exceptions inherit from KStackError."""
        assert issubclass(LayerAccessError, KStackError)
        assert issubclass(ServiceNotFoundError, KStackError)
        assert issubclass(ConfigurationError, KStackError)
        assert issubclass(RouteError, KStackError)

    def test_kstack_error_inherits_from_exception(self):
        """Test that KStackError inherits from built-in Exception."""
        assert issubclass(KStackError, Exception)

    def test_can_raise_and_catch_kstack_error(self):
        """Test that KStackError can be raised and caught."""
        with pytest.raises(KStackError):
            raise KStackError("Test error")

    def test_can_raise_and_catch_layer_access_error(self):
        """Test that LayerAccessError can be raised and caught."""
        with pytest.raises(LayerAccessError):
            raise LayerAccessError("Layer access denied")

    def test_can_raise_and_catch_service_not_found_error(self):
        """Test that ServiceNotFoundError can be raised and caught."""
        with pytest.raises(ServiceNotFoundError):
            raise ServiceNotFoundError("Service not found")

    def test_can_raise_and_catch_configuration_error(self):
        """Test that ConfigurationError can be raised and caught."""
        with pytest.raises(ConfigurationError):
            raise ConfigurationError("Configuration error")

    def test_can_raise_and_catch_route_error(self):
        """Test that RouteError can be raised and caught."""
        with pytest.raises(RouteError):
            raise RouteError("Route error")

    def test_can_catch_specific_error_with_base_class(self):
        """Test that specific errors can be caught with KStackError base class."""
        with pytest.raises(KStackError):
            raise LayerAccessError("Layer access denied")

        with pytest.raises(KStackError):
            raise ServiceNotFoundError("Service not found")

    def test_error_message_is_preserved(self):
        """Test that error messages are preserved when raised."""
        error_message = "Redis databases are only available in Layer 3"

        with pytest.raises(LayerAccessError, match=error_message):
            raise LayerAccessError(error_message)

    def test_cannot_catch_kstack_error_with_builtin_valueerror(self):
        """Test that KStack errors don't get caught by built-in ValueError."""
        # This is the key benefit - KStack errors won't mask Python errors
        with pytest.raises(LayerAccessError):
            try:
                raise LayerAccessError("Layer access denied")
            except ValueError:
                # Should NOT catch KStack errors
                pytest.fail("KStack error should not be caught by ValueError")
