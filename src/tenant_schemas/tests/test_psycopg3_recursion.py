from unittest.mock import patch, Mock
import django.db.utils

from django.db import connection
from django.test import override_settings
from tenant_schemas.tests.testcases import BaseTestCase
from tenant_schemas.tests.models import Tenant
from tenant_schemas.utils import get_public_schema_name
from tenant_schemas.postgresql_backend.base import _SETTING_SEARCH_PATH, DatabaseWrapper


class Psycopg3RecursionFixTest(BaseTestCase):
    """
    Tests for the psycopg3 recursion fix when DEBUG=True.

    The bug occurs when Django's SQL debug logging tries to format queries
    using psycopg3's mogrify, which opens a new cursor, causing recursion
    in our _cursor() method when setting search_path.
    """

    # Cache the original backend to avoid repeated loading in tests
    _original_backend = django.db.utils.load_backend("django.db.backends.postgresql")

    @classmethod
    @override_settings(
        SHARED_APPS=("tenant_schemas",),
        TENANT_APPS=(
            "dts_test_app",
            "django.contrib.contenttypes",
            "django.contrib.auth",
        ),
        INSTALLED_APPS=(
            "tenant_schemas",
            "dts_test_app",
            "django.contrib.contenttypes",
            "django.contrib.auth",
        ),
    )
    def setUpClass(cls):
        super().setUpClass()
        cls.sync_shared()
        Tenant(domain_url="test.com", schema_name=get_public_schema_name()).save(
            verbosity=cls.get_verbosity()
        )

    def setUp(self):
        super().setUp()
        # Create a mock tenant for unit tests - no DB operations needed
        test_name = self._testMethodName
        self.tenant = Mock()
        self.tenant.domain_url = f"{test_name}.test.com"
        self.tenant.schema_name = f"test_{test_name}"

    def _create_test_wrapper(self):
        """Create a test DatabaseWrapper with proper settings."""
        return DatabaseWrapper(
            {
                "ENGINE": "tenant_schemas.postgresql_backend",
                "NAME": "test_db",
                "HOST": "localhost",
                "PORT": 5432,
                "USER": "test",
                "PASSWORD": "test",
                "TIME_ZONE": "UTC",
                "CONN_MAX_AGE": 0,
                "CONN_HEALTH_CHECKS": False,
                "AUTOCOMMIT": True,
                "ATOMIC_REQUESTS": False,
                "OPTIONS": {},
                "TEST": {},
            }
        )

    def test_contextvar_prevents_recursion(self):
        """Test that ContextVar prevents recursion during search_path setting."""
        wrapper = self._create_test_wrapper()
        wrapper.set_tenant(self.tenant)

        # Simulate being already in the middle of setting search_path
        token = _SETTING_SEARCH_PATH.set(True)
        try:
            # Mock the super()._cursor() call and connection to avoid actual DB calls
            # Use the cached original backend DatabaseWrapper that our class inherits from
            with patch.object(
                self._original_backend.DatabaseWrapper, "_cursor"
            ) as mock_super_cursor, patch.object(wrapper, "connection") as mock_conn:
                mock_super_cursor.return_value = Mock()
                mock_conn.cursor.return_value = Mock()

                cursor = wrapper._cursor()
                self.assertIsNotNone(cursor)

                # Should have called super()._cursor() to get the cursor
                mock_super_cursor.assert_called_once()
                # But should NOT have called connection.cursor() due to ContextVar guard
                mock_conn.cursor.assert_not_called()
        finally:
            _SETTING_SEARCH_PATH.reset(token)

    def test_search_path_signature_caching(self):
        """Test that search_path signature caching works correctly."""
        wrapper = self._create_test_wrapper()
        wrapper.set_tenant(self.tenant)

        # Mock connection to count calls
        with patch.object(wrapper, "connection") as mock_conn:
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor

            # First call should set search_path
            cursor1 = wrapper._cursor()
            self.assertIsNotNone(cursor1)
            first_call_count = mock_cursor.execute.call_count

            # Second call with same tenant should use cache
            cursor2 = wrapper._cursor()
            self.assertIsNotNone(cursor2)
            second_call_count = mock_cursor.execute.call_count

            # Should not have called execute again (cached)
            self.assertEqual(first_call_count, second_call_count)

    def test_tenant_switch_clears_cache(self):
        """Test that switching tenants clears the path signature cache."""
        wrapper = self._create_test_wrapper()

        # Set initial tenant and cache a signature
        wrapper.set_tenant(self.tenant)
        wrapper._ts_last_path_sig = ("tenant1", "public")

        # Switch tenants - should clear cache
        wrapper.set_schema_to_public()
        self.assertIsNone(wrapper._ts_last_path_sig)

    def test_connection_close_clears_cache(self):
        """Test that closing connection clears the cache."""
        wrapper = self._create_test_wrapper()

        # Set cache
        wrapper._ts_last_path_sig = ("tenant1", "public")

        # Close should clear cache
        with patch.object(wrapper, "connection"):  # Mock to avoid real close
            wrapper.close()
        self.assertIsNone(wrapper._ts_last_path_sig)

    def test_rollback_clears_cache(self):
        """Test that rollback clears the cache."""
        wrapper = self._create_test_wrapper()

        # Set cache
        wrapper._ts_last_path_sig = ("tenant1", "public")

        # Rollback should clear cache
        # Use the cached original backend DatabaseWrapper that our class inherits from
        with patch.object(
            self._original_backend.DatabaseWrapper, "rollback"
        ):  # Mock parent rollback
            wrapper.rollback()
        self.assertIsNone(wrapper._ts_last_path_sig)

    def test_last_executed_query_optimization(self):
        """Test that last_executed_query skips mogrify for parameterless queries."""
        wrapper = self._create_test_wrapper()

        cursor = Mock()

        # Test with no parameters - should return SQL as-is
        result = wrapper.last_executed_query(cursor, "SELECT 1", None)
        self.assertEqual(result, "SELECT 1")

        result = wrapper.last_executed_query(cursor, "SELECT 1", [])
        self.assertEqual(result, "SELECT 1")

        # Test with parameters - should delegate to ops
        with patch.object(
            wrapper.ops, "last_executed_query", return_value="formatted"
        ) as mock_ops:
            result = wrapper.last_executed_query(cursor, "SELECT %s", ["test"])
            self.assertEqual(result, "formatted")
            mock_ops.assert_called_once_with(cursor, "SELECT %s", ["test"])

    @override_settings(DEBUG=True)
    def test_integration_with_real_connection(self):
        """Integration test with real database connection and DEBUG=True."""
        # Use existing public schema to avoid tenant creation complexity
        connection.set_schema_to_public()

        try:
            # This should work without recursion error even with DEBUG=True
            cursor = connection._cursor()
            self.assertIsNotNone(cursor)

            # Execute a simple query to verify everything works
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)

            # Verify we can switch search paths without issues
            # Create a mock tenant for search path testing
            mock_tenant = Mock()
            mock_tenant.schema_name = "public"  # Use public schema that exists

            connection.set_tenant(mock_tenant)
            cursor2 = connection._cursor()
            self.assertIsNotNone(cursor2)

            # Another simple query to ensure search_path changes work
            cursor2.execute("SELECT 2")
            result2 = cursor2.fetchone()
            self.assertEqual(result2[0], 2)

        finally:
            # Clean up any state changes
            connection.set_schema_to_public()
