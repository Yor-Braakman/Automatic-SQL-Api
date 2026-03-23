"""Tests for SQL validation utilities."""

import pytest
from unittest.mock import Mock, patch
from db.sql_validator import SQLValidator, sql_validator


class TestSQLValidator:
    """Test suite for SQL identifier validation."""

    def test_validate_identifier_valid_names(self):
        """Test validation of valid SQL identifiers."""
        valid_names = [
            "dbo",
            "MyTable",
            "table_name",
            "_temp",
            "Table123",
            "@variable",
            "#temp_table",
            "schema$table",
        ]

        for name in valid_names:
            assert sql_validator.validate_identifier(
                name
            ), f"Should accept valid identifier: {name}"

    def test_validate_identifier_invalid_names(self):
        """Test rejection of invalid SQL identifiers."""
        invalid_names = [
            "",  # Empty
            "a" * 129,  # Too long (>128 chars)
            "table name",  # Space
            "table-name",  # Dash
            "table.name",  # Dot
            "'; DROP TABLE users--",  # SQL injection attempt
            "../etc/passwd",  # Path traversal
            "table' OR '1'='1",  # SQL injection
            "table;",  # Semicolon
            "table/**/name",  # SQL comment
        ]

        for name in invalid_names:
            assert not sql_validator.validate_identifier(
                name
            ), f"Should reject invalid identifier: {name}"

    @patch("db.sql_validator.db_connection")
    def test_validate_schema_exists_success(self, mock_db):
        """Test schema existence validation with existing schema."""
        mock_cursor = Mock()
        mock_row = Mock()
        mock_row.schema_id = 1
        mock_cursor.fetchone.return_value = mock_row
        mock_db.execute_query.return_value = mock_cursor

        result = sql_validator.validate_schema_exists("dbo")

        assert result is True
        mock_db.execute_query.assert_called_once()
        call_args = mock_db.execute_query.call_args
        assert "SCHEMA_ID" in call_args[0][0]
        assert call_args[0][1] == ("dbo",)

    @patch("db.sql_validator.db_connection")
    def test_validate_schema_exists_not_found(self, mock_db):
        """Test schema existence validation with non-existent schema."""
        mock_cursor = Mock()
        mock_row = Mock()
        mock_row.schema_id = None
        mock_cursor.fetchone.return_value = mock_row
        mock_db.execute_query.return_value = mock_cursor

        result = sql_validator.validate_schema_exists("fake_schema")

        assert result is False

    @patch("db.sql_validator.db_connection")
    def test_validate_schema_exists_invalid_name(self, mock_db):
        """Test schema existence with invalid identifier."""
        result = sql_validator.validate_schema_exists("'; DROP SCHEMA dbo--")

        assert result is False
        # Should not call database
        mock_db.execute_query.assert_not_called()

    @patch("db.sql_validator.db_connection")
    def test_validate_table_exists_success(self, mock_db):
        """Test table existence validation."""
        mock_cursor = Mock()
        mock_row = Mock()
        mock_row.object_id = 12345
        mock_cursor.fetchone.return_value = mock_row
        mock_db.execute_query.return_value = mock_cursor

        result = sql_validator.validate_table_exists("dbo", "Users")

        assert result is True
        mock_db.execute_query.assert_called_once()
        call_args = mock_db.execute_query.call_args
        assert "OBJECT_ID" in call_args[0][0]
        assert call_args[0][1] == ("dbo", "Users")

    @patch("db.sql_validator.db_connection")
    def test_validate_table_exists_not_found(self, mock_db):
        """Test table existence validation with non-existent table."""
        mock_cursor = Mock()
        mock_row = Mock()
        mock_row.object_id = None
        mock_cursor.fetchone.return_value = mock_row
        mock_db.execute_query.return_value = mock_cursor

        result = sql_validator.validate_table_exists("dbo", "FakeTable")

        assert result is False

    @patch("db.sql_validator.db_connection")
    def test_get_quoted_identifier_success(self, mock_db):
        """Test QUOTENAME usage for identifier quoting."""
        mock_cursor = Mock()
        mock_row = Mock()
        mock_row.quoted_name = "[MyTable]"
        mock_cursor.fetchone.return_value = mock_row
        mock_db.execute_query.return_value = mock_cursor

        result = sql_validator.get_quoted_identifier("MyTable")

        assert result == "[MyTable]"
        mock_db.execute_query.assert_called_once()
        call_args = mock_db.execute_query.call_args
        assert "QUOTENAME" in call_args[0][0]
        assert call_args[0][1] == ("MyTable",)

    @patch("db.sql_validator.db_connection")
    def test_get_quoted_identifier_invalid(self, mock_db):
        """Test QUOTENAME with invalid identifier."""
        with pytest.raises(ValueError, match="Invalid SQL identifier"):
            sql_validator.get_quoted_identifier("'; DROP TABLE--")

        # Should not call database
        mock_db.execute_query.assert_not_called()

    @patch("db.sql_validator.db_connection")
    def test_build_safe_table_reference_success(self, mock_db):
        """Test building safe table reference."""
        # Mock for schema exists check
        mock_cursor_schema = Mock()
        mock_row_schema = Mock()
        mock_row_schema.schema_id = 1
        mock_cursor_schema.fetchone.return_value = mock_row_schema

        # Mock for table exists check
        mock_cursor_table = Mock()
        mock_row_table = Mock()
        mock_row_table.object_id = 12345
        mock_cursor_table.fetchone.return_value = mock_row_table

        # Mock for QUOTENAME calls
        mock_cursor_quote1 = Mock()
        mock_row_quote1 = Mock()
        mock_row_quote1.quoted_name = "[dbo]"
        mock_cursor_quote1.fetchone.return_value = mock_row_quote1

        mock_cursor_quote2 = Mock()
        mock_row_quote2 = Mock()
        mock_row_quote2.quoted_name = "[Users]"
        mock_cursor_quote2.fetchone.return_value = mock_row_quote2

        mock_db.execute_query.side_effect = [
            mock_cursor_schema,
            mock_cursor_table,
            mock_cursor_quote1,
            mock_cursor_quote2,
        ]

        result = sql_validator.build_safe_table_reference("dbo", "Users")

        assert result == "[dbo].[Users]"
        assert mock_db.execute_query.call_count == 4

    @patch("db.sql_validator.db_connection")
    def test_build_safe_table_reference_invalid_schema(self, mock_db):
        """Test building reference with invalid schema."""
        with pytest.raises(ValueError, match="Invalid schema name"):
            sql_validator.build_safe_table_reference("'; DROP--", "Users")

    @patch("db.sql_validator.db_connection")
    def test_build_safe_table_reference_schema_not_exists(self, mock_db):
        """Test building reference with non-existent schema."""
        mock_cursor = Mock()
        mock_row = Mock()
        mock_row.schema_id = None
        mock_cursor.fetchone.return_value = mock_row
        mock_db.execute_query.return_value = mock_cursor

        with pytest.raises(ValueError, match="Schema does not exist"):
            sql_validator.build_safe_table_reference("fake_schema", "Users")

    def test_sql_injection_attempts(self):
        """Test various SQL injection attempts are blocked."""
        injection_attempts = [
            ("dbo'; DROP TABLE Users--", "Users"),
            ("dbo", "Users'; DELETE FROM Users--"),
            ("dbo' OR '1'='1", "Users"),
            ("dbo", "Users' UNION SELECT * FROM sys.tables--"),
            ("dbo/**/", "Users"),
            ("dbo", "Users; DROP SCHEMA dbo;"),
        ]

        for schema, table in injection_attempts:
            # Should fail identifier validation
            if not sql_validator.validate_identifier(schema):
                continue
            if not sql_validator.validate_identifier(table):
                continue

            # If somehow it passes validation, build should fail
            with pytest.raises(ValueError):
                sql_validator.build_safe_table_reference(schema, table)


class TestSQLValidatorIntegration:
    """Integration tests with real database (mark as integration)."""

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires database connection")
    def test_validate_schema_real_db(self):
        """Test with real database connection."""
        # This would run against a real database in CI/CD
        assert sql_validator.validate_schema_exists("dbo")
        assert not sql_validator.validate_schema_exists("nonexistent_schema")

    @pytest.mark.integration
    @pytest.mark.skipif(True, reason="Requires database connection")
    def test_quotename_real_db(self):
        """Test QUOTENAME with real database."""
        result = sql_validator.get_quoted_identifier("MyTable")
        assert result == "[MyTable]"
