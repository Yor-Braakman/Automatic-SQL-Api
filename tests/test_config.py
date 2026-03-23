"""Tests for configuration management."""

import pytest
from unittest.mock import patch
from config import Settings


def test_settings_schema_list():
    """Test schema list parsing from comma-separated string."""
    with patch.dict(
        "os.environ",
        {
            "SQL_SERVER": "test.database.windows.net",
            "SQL_DATABASE": "testdb",
            "AZURE_CLIENT_ID": "test-client-id",
            "AZURE_CLIENT_SECRET": "test-secret",
            "AZURE_TENANT_ID": "test-tenant-id",
            "SCHEMAS_TO_EXPOSE": "dbo,sales,inventory",
        },
    ):
        settings = Settings()
        assert settings.schema_list == ["dbo", "sales", "inventory"]


def test_settings_connection_string():
    """Test connection string building."""
    with patch.dict(
        "os.environ",
        {
            "SQL_SERVER": "test.database.windows.net",
            "SQL_DATABASE": "testdb",
            "SQL_DRIVER": "ODBC Driver 18 for SQL Server",
            "AZURE_CLIENT_ID": "test-client-id",
            "AZURE_CLIENT_SECRET": "test-secret",
            "AZURE_TENANT_ID": "test-tenant-id",
        },
    ):
        settings = Settings()
        conn_str = settings.connection_string

        assert "Driver={ODBC Driver 18 for SQL Server}" in conn_str
        assert "Server=tcp:test.database.windows.net,1433" in conn_str
        assert "Database=testdb" in conn_str
        assert "Encrypt=yes" in conn_str


def test_settings_defaults():
    """Test default configuration values."""
    with patch.dict(
        "os.environ",
        {
            "SQL_SERVER": "test.database.windows.net",
            "SQL_DATABASE": "testdb",
            "AZURE_CLIENT_ID": "test-client-id",
            "AZURE_CLIENT_SECRET": "test-secret",
            "AZURE_TENANT_ID": "test-tenant-id",
        },
    ):
        settings = Settings()

        assert settings.api_title == "SQL Server API Accelerator"
        assert settings.api_version == "1.0.0"
        assert settings.api_host == "0.0.0.0"
        assert settings.api_port == 8000
        assert settings.schemas_to_expose == "dbo"
