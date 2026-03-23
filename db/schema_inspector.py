"""Schema introspection and metadata extraction from SQL Server."""
from typing import List, Optional
from dataclasses import dataclass
import logging
from db.connection import db_connection
from db.sql_validator import sql_validator

logger = logging.getLogger(__name__)


@dataclass
class ColumnInfo:
    """Information about a database column."""
    name: str
    data_type: str
    is_nullable: bool
    max_length: Optional[int]
    is_primary_key: bool = False


@dataclass
class TableInfo:
    """Information about a database table or view."""
    schema: str
    name: str
    type: str  # 'TABLE' or 'VIEW'
    columns: List[ColumnInfo]
    primary_keys: List[str]
    
    @property
    def full_name(self) -> str:
        """Return schema-qualified table name."""
        return f"{self.schema}.{self.name}"
    
    @property
    def has_primary_key(self) -> bool:
        """Check if table has a primary key."""
        return len(self.primary_keys) > 0
    
    @property
    def safe_reference(self) -> str:
        """Return safe quoted table reference for use in SQL."""
        return sql_validator.build_safe_table_reference(self.schema, self.name)


class SchemaInspector:
    """Inspect SQL Server schema and extract metadata."""
    
    def get_tables_and_views(self, schemas: List[str]) -> List[TableInfo]:
        """
        Get all tables and views from specified schemas.
        
        Args:
            schemas: List of schema names to inspect
            
        Returns:
            List of TableInfo objects
            
        Raises:
            ValueError: If any schema name is invalid
        """
        # Validate all schema names first
        for schema in schemas:
            if not sql_validator.validate_identifier(schema):
                raise ValueError(f"Invalid schema name: {schema}")
            if not sql_validator.validate_schema_exists(schema):
                logger.warning(f"Schema does not exist: {schema}")
        
        # Use parameterized query with IN clause
        # Build placeholders for each schema
        placeholders = ','.join(['?' for _ in schemas])
        
        query = f"""
        SELECT 
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE
        FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_SCHEMA IN ({placeholders})
        ORDER BY TABLE_SCHEMA, TABLE_NAME
        """
        
        try:
            cursor = db_connection.execute_query(query, tuple(schemas))
            tables = []
            
            for row in cursor.fetchall():
                schema = row.TABLE_SCHEMA
                name = row.TABLE_NAME
                table_type = 'TABLE' if row.TABLE_TYPE == 'BASE TABLE' else 'VIEW'
                
                # Get columns and primary keys
                columns = self._get_columns(schema, name)
                primary_keys = self._get_primary_keys(schema, name)
                
                # Mark primary key columns
                for col in columns:
                    if col.name in primary_keys:
                        col.is_primary_key = True
                
                table_info = TableInfo(
                    schema=schema,
                    name=name,
                    type=table_type,
                    columns=columns,
                    primary_keys=primary_keys
                )
                
                tables.append(table_info)
            
            logger.info(f"Retrieved {len(tables)} tables/views from schemas: {schemas}")
            return tables
            
        except Exception as e:
            logger.error(f"Error retrieving tables: {e}", exc_info=True)
            raise
    
    def _get_columns(self, schema: str, table: str) -> List[ColumnInfo]:
        """
        Get column information for a specific table.
        
        Uses parameterized queries for safety.
        """
        query = """
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
        ORDER BY ORDINAL_POSITION
        """
        
        try:
            cursor = db_connection.execute_query(query, (schema, table))
            columns = []
            
            for row in cursor.fetchall():
                col = ColumnInfo(
                    name=row.COLUMN_NAME,
                    data_type=row.DATA_TYPE,
                    is_nullable=row.IS_NULLABLE == 'YES',
                    max_length=row.CHARACTER_MAXIMUM_LENGTH
                )
                columns.append(col)
            
            return columns
            
        except Exception as e:
            logger.error(f"Error retrieving columns for {schema}.{table}: {e}", exc_info=True)
            raise
    
    def _get_primary_keys(self, schema: str, table: str) -> List[str]:
        """
        Get primary key columns using system views with parameterized queries.
        
        This is safe as we're using parameterized queries for schema/table names.
        """
        query = """
        SELECT 
            COL_NAME(ic.object_id, ic.column_id) AS column_name
        FROM 
            sys.indexes AS i
        INNER JOIN 
            sys.index_columns AS ic 
            ON i.object_id = ic.object_id 
            AND i.index_id = ic.index_id
        INNER JOIN 
            sys.tables AS t 
            ON i.object_id = t.object_id
        INNER JOIN 
            sys.schemas AS s 
            ON t.schema_id = s.schema_id
        WHERE 
            i.is_primary_key = 1
            AND s.name = ?
            AND t.name = ?
        ORDER BY 
            ic.key_ordinal
        """
        
        try:
            cursor = db_connection.execute_query(query, (schema, table))
            return [row.column_name for row in cursor.fetchall()]
            
        except Exception as e:
            logger.error(f"Error retrieving primary keys for {schema}.{table}: {e}", exc_info=True)
            return []
    
    def get_table_by_name(self, schema: str, table: str) -> Optional[TableInfo]:
        """
        Get information for a specific table.
        
        Args:
            schema: Schema name
            table: Table name
            
        Returns:
            TableInfo if found, None otherwise
        """
        # Validate first
        if not sql_validator.validate_identifier(schema):
            logger.warning(f"Invalid schema name: {schema}")
            return None
        
        if not sql_validator.validate_identifier(table):
            logger.warning(f"Invalid table name: {table}")
            return None
        
        if not sql_validator.validate_table_exists(schema, table):
            return None
        
        tables = self.get_tables_and_views([schema])
        for t in tables:
            if t.name == table:
                return t
        return None


# Global inspector instance
schema_inspector = SchemaInspector()
