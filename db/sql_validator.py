"""SQL validation utilities for preventing SQL injection."""
import re
import logging
from typing import Optional
from db.connection import db_connection

logger = logging.getLogger(__name__)


class SQLValidator:
    """Validate SQL identifiers and objects to prevent SQL injection."""
    
    @staticmethod
    def validate_identifier(name: str) -> bool:
        """
        Validate SQL identifier follows safe naming conventions.
        
        SQL Server identifiers must:
        - Start with letter, underscore, @, or #
        - Contain only letters, digits, @, $, #, _
        - Be 1-128 characters long
        
        Args:
            name: The identifier to validate
            
        Returns:
            True if valid, False otherwise
        """
        if not name or len(name) > 128:
            return False
        
        # SQL Server identifier pattern
        pattern = r'^[a-zA-Z_@#][a-zA-Z0-9_@#$]*$'
        return bool(re.match(pattern, name))
    
    @staticmethod
    def validate_schema_exists(schema_name: str) -> bool:
        """
        Verify that a schema exists in the database.
        
        Args:
            schema_name: The schema name to check
            
        Returns:
            True if schema exists, False otherwise
        """
        if not SQLValidator.validate_identifier(schema_name):
            logger.warning(f"Invalid schema name format: {schema_name}")
            return False
        
        try:
            query = "SELECT SCHEMA_ID(?) AS schema_id"
            cursor = db_connection.execute_query(query, (schema_name,))
            result = cursor.fetchone()
            
            if result and result.schema_id is not None:
                return True
            
            logger.warning(f"Schema does not exist: {schema_name}")
            return False
            
        except Exception as e:
            logger.error(f"Error validating schema: {e}", exc_info=True)
            return False
    
    @staticmethod
    def validate_table_exists(schema_name: str, table_name: str) -> bool:
        """
        Verify that a table or view exists in the specified schema.
        
        Args:
            schema_name: The schema name
            table_name: The table or view name
            
        Returns:
            True if table/view exists, False otherwise
        """
        if not SQLValidator.validate_identifier(schema_name):
            logger.warning(f"Invalid schema name format: {schema_name}")
            return False
        
        if not SQLValidator.validate_identifier(table_name):
            logger.warning(f"Invalid table name format: {table_name}")
            return False
        
        try:
            query = """
            SELECT OBJECT_ID(? + '.' + ?) AS object_id
            """
            cursor = db_connection.execute_query(query, (schema_name, table_name))
            result = cursor.fetchone()
            
            if result and result.object_id is not None:
                return True
            
            logger.warning(f"Table does not exist: {schema_name}.{table_name}")
            return False
            
        except Exception as e:
            logger.error(f"Error validating table: {e}", exc_info=True)
            return False
    
    @staticmethod
    def get_quoted_identifier(name: str) -> str:
        """
        Get SQL Server quoted identifier using QUOTENAME.
        
        This is safer than manual bracket escaping as QUOTENAME
        handles all edge cases properly.
        
        Args:
            name: The identifier to quote
            
        Returns:
            Quoted identifier safe for use in dynamic SQL
            
        Raises:
            ValueError: If identifier is invalid
        """
        if not SQLValidator.validate_identifier(name):
            raise ValueError(f"Invalid SQL identifier: {name}")
        
        try:
            query = "SELECT QUOTENAME(?) AS quoted_name"
            cursor = db_connection.execute_query(query, (name,))
            result = cursor.fetchone()
            
            if result and result.quoted_name:
                return result.quoted_name
            
            raise ValueError(f"Could not quote identifier: {name}")
            
        except Exception as e:
            logger.error(f"Error quoting identifier: {e}", exc_info=True)
            raise ValueError(f"Could not quote identifier: {name}") from e
    
    @staticmethod
    def build_safe_table_reference(schema_name: str, table_name: str) -> str:
        """
        Build a safe schema-qualified table reference.
        
        Args:
            schema_name: The schema name
            table_name: The table name
            
        Returns:
            Safe quoted reference like [schema].[table]
            
        Raises:
            ValueError: If names are invalid or objects don't exist
        """
        # Validate identifiers
        if not SQLValidator.validate_identifier(schema_name):
            raise ValueError(f"Invalid schema name: {schema_name}")
        
        if not SQLValidator.validate_identifier(table_name):
            raise ValueError(f"Invalid table name: {table_name}")
        
        # Verify objects exist
        if not SQLValidator.validate_schema_exists(schema_name):
            raise ValueError(f"Schema does not exist: {schema_name}")
        
        if not SQLValidator.validate_table_exists(schema_name, table_name):
            raise ValueError(f"Table does not exist: {schema_name}.{table_name}")
        
        # Use QUOTENAME for safe quoting
        quoted_schema = SQLValidator.get_quoted_identifier(schema_name)
        quoted_table = SQLValidator.get_quoted_identifier(table_name)
        
        return f"{quoted_schema}.{quoted_table}"


# Global validator instance
sql_validator = SQLValidator()
