"""Tests for API endpoint generation."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from api.endpoints import EndpointGenerator
from db.schema_inspector import TableInfo, ColumnInfo


@pytest.fixture
def endpoint_generator():
    """Create an EndpointGenerator instance."""
    return EndpointGenerator()


@pytest.fixture
def sample_table_with_pk():
    """Create a sample table with primary key."""
    columns = [
        ColumnInfo("CustomerID", "int", False, None, True),
        ColumnInfo("Name", "varchar", False, 100, False),
        ColumnInfo("Email", "varchar", True, 255, False),
    ]

    return TableInfo(
        schema="dbo",
        name="Customers",
        type="TABLE",
        columns=columns,
        primary_keys=["CustomerID"],
    )


@pytest.fixture
def sample_table_without_pk():
    """Create a sample table without primary key."""
    columns = [
        ColumnInfo("CustomerName", "varchar", False, 100, False),
        ColumnInfo("OrderCount", "int", False, None, False),
    ]

    return TableInfo(
        schema="dbo", name="CustomerView", type="VIEW", columns=columns, primary_keys=[]
    )


def test_create_router_with_pk(endpoint_generator, sample_table_with_pk):
    """Test router creation for table with primary key."""
    router = endpoint_generator.create_router(sample_table_with_pk)

    assert router.prefix == "/dbo/Customers"
    assert "dbo.Customers" in router.tags

    # Check routes exist
    routes = [route.path for route in router.routes]
    assert "/dbo/Customers/" in routes
    assert "/dbo/Customers/{CustomerID}" in routes


def test_create_router_without_pk(endpoint_generator, sample_table_without_pk):
    """Test router creation for table without primary key."""
    router = endpoint_generator.create_router(sample_table_without_pk)

    assert router.prefix == "/dbo/CustomerView"

    # Check only get_all route exists
    routes = [route.path for route in router.routes]
    assert "/dbo/CustomerView/" in routes
    # Should not have PK route
    pk_routes = [r for r in routes if "{" in r and "}" in r]
    assert len(pk_routes) == 0


@patch("api.endpoints.schema_inspector")
def test_generate_all_routers(mock_inspector, endpoint_generator, sample_table_with_pk):
    """Test generation of all routers."""
    mock_inspector.get_tables_and_views.return_value = [sample_table_with_pk]

    routers = endpoint_generator.generate_all_routers(["dbo"])

    assert len(routers) == 1
    assert "dbo.Customers" in endpoint_generator.routers
    mock_inspector.get_tables_and_views.assert_called_once_with(["dbo"])
