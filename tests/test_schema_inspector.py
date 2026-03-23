"""Tests for schema inspection functionality."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from db.schema_inspector import SchemaInspector, TableInfo, ColumnInfo


@pytest.fixture
def mock_cursor():
    """Create a mock database cursor."""
    cursor = Mock()
    return cursor


@pytest.fixture
def schema_inspector():
    """Create a SchemaInspector instance."""
    return SchemaInspector()


def test_column_info_creation():
    """Test ColumnInfo dataclass creation."""
    col = ColumnInfo(
        name="CustomerID",
        data_type="int",
        is_nullable=False,
        max_length=None,
        is_primary_key=True,
    )

    assert col.name == "CustomerID"
    assert col.data_type == "int"
    assert col.is_nullable is False
    assert col.is_primary_key is True


def test_table_info_full_name():
    """Test TableInfo full_name property."""
    table = TableInfo(
        schema="dbo",
        name="Customers",
        type="TABLE",
        columns=[],
        primary_keys=["CustomerID"],
    )

    assert table.full_name == "dbo.Customers"


def test_table_info_has_primary_key():
    """Test TableInfo has_primary_key property."""
    table_with_pk = TableInfo(
        schema="dbo",
        name="Customers",
        type="TABLE",
        columns=[],
        primary_keys=["CustomerID"],
    )

    table_without_pk = TableInfo(
        schema="dbo", name="CustomerView", type="VIEW", columns=[], primary_keys=[]
    )

    assert table_with_pk.has_primary_key is True
    assert table_without_pk.has_primary_key is False


@patch("db.schema_inspector.db_connection")
def test_get_primary_keys(mock_db_connection, schema_inspector):
    """Test primary key retrieval."""
    mock_cursor = Mock()
    mock_row = Mock()
    mock_row.column_name = "CustomerID"
    mock_cursor.fetchall.return_value = [mock_row]
    mock_db_connection.execute_query.return_value = mock_cursor

    pks = schema_inspector._get_primary_keys("dbo", "Customers")

    assert pks == ["CustomerID"]
    mock_db_connection.execute_query.assert_called_once()


@patch("db.schema_inspector.db_connection")
def test_get_columns(mock_db_connection, schema_inspector):
    """Test column retrieval."""
    mock_cursor = Mock()
    mock_row = Mock()
    mock_row.COLUMN_NAME = "CustomerID"
    mock_row.DATA_TYPE = "int"
    mock_row.IS_NULLABLE = "NO"
    mock_row.CHARACTER_MAXIMUM_LENGTH = None
    mock_cursor.fetchall.return_value = [mock_row]
    mock_db_connection.execute_query.return_value = mock_cursor

    columns = schema_inspector._get_columns("dbo", "Customers")

    assert len(columns) == 1
    assert columns[0].name == "CustomerID"
    assert columns[0].data_type == "int"
    assert columns[0].is_nullable is False
