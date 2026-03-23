"""Dynamic REST endpoint generator with SQL injection protection."""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Dict, Any, Optional
import logging
import pyodbc

from db.schema_inspector import schema_inspector, TableInfo
from db.connection import db_connection
from db.sql_validator import sql_validator

logger = logging.getLogger(__name__)


class EndpointGenerator:
    """Generate FastAPI endpoints dynamically based on database schema."""
    
    def __init__(self):
        self.routers: Dict[str, APIRouter] = {}
    
    def create_router(self, table_info: TableInfo) -> APIRouter:
        """
        Create a FastAPI router for a specific table or view.
        
        Args:
            table_info: TableInfo object with validated schema/table names
            
        Returns:
            Configured APIRouter
        """
        router = APIRouter(
            prefix=f"/{table_info.schema}/{table_info.name}",
            tags=[f"{table_info.schema}.{table_info.name}"]
        )
        
        # Add GET all endpoint
        self._add_get_all_endpoint(router, table_info)
        
        # Add GET by primary key endpoint if table has PK
        if table_info.has_primary_key:
            self._add_get_by_pk_endpoint(router, table_info)
        
        return router
    
    def _add_get_all_endpoint(self, router: APIRouter, table_info: TableInfo):
        """Add GET endpoint to retrieve all records with proper SQL safety."""
        
        @router.get("/", response_model=List[Dict[str, Any]])
        async def get_all(
            limit: Optional[int] = Query(default=100, le=1000, ge=1),
            offset: Optional[int] = Query(default=0, ge=0)
        ):
            """
            Retrieve all records from the table/view with pagination.
            
            Args:
                limit: Maximum number of records (1-1000)
                offset: Number of records to skip
                
            Returns:
                List of records as dictionaries
            """
            try:
                # Build safe table reference using QUOTENAME
                # This protects against SQL injection
                safe_table_ref = sql_validator.build_safe_table_reference(
                    table_info.schema, 
                    table_info.name
                )
                
                # Now we can safely use the quoted reference in dynamic SQL
                # The parameters (offset, limit) are still parameterized
                query = f"""
                SELECT * 
                FROM {safe_table_ref}
                ORDER BY (SELECT NULL)
                OFFSET ? ROWS
                FETCH NEXT ? ROWS ONLY
                """
                
                cursor = db_connection.execute_query(query, (offset, limit))
                columns = [column[0] for column in cursor.description]
                
                results = []
                for row in cursor.fetchall():
                    results.append(dict(zip(columns, row)))
                
                logger.info(
                    f"Retrieved {len(results)} records from {table_info.full_name}",
                    extra={"limit": limit, "offset": offset}
                )
                
                return results
                
            except ValueError as e:
                # Validation error (invalid schema/table)
                logger.error(f"Validation error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid table or schema name"
                )
            except pyodbc.Error as e:
                logger.error(
                    f"Database error querying {table_info.full_name}",
                    exc_info=True,
                    extra={"error_code": e.args[0] if e.args else None}
                )
                raise HTTPException(
                    status_code=500, 
                    detail="An error occurred processing your request"
                )
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="An unexpected error occurred"
                )
    
    def _add_get_by_pk_endpoint(self, router: APIRouter, table_info: TableInfo):
        """Add GET endpoint to retrieve record by primary key with SQL safety."""
        
        # Validate all PK column names
        for pk in table_info.primary_keys:
            if not sql_validator.validate_identifier(pk):
                logger.error(f"Invalid primary key name: {pk}")
                raise ValueError(f"Invalid primary key column name: {pk}")
        
        # Build primary key parameters dynamically
        pk_params = table_info.primary_keys
        
        # Create endpoint path with PK parameters
        if len(pk_params) == 1:
            endpoint_path = f"/{{{pk_params[0]}}}"
        else:
            endpoint_path = "/" + "/".join([f"{{{pk}}}" for pk in pk_params])
        
        @router.get(endpoint_path, response_model=Dict[str, Any])
        async def get_by_pk(**pk_values):
            """
            Retrieve a specific record by primary key.
            
            Args:
                **pk_values: Primary key values
                
            Returns:
                Single record as dictionary
                
            Raises:
                HTTPException: 404 if not found, 500 on error
            """
            try:
                # Build safe table reference
                safe_table_ref = sql_validator.build_safe_table_reference(
                    table_info.schema,
                    table_info.name
                )
                
                # Build WHERE clause with quoted column names
                where_conditions = []
                params = []
                
                for pk in pk_params:
                    # Quote each column name safely
                    quoted_pk = sql_validator.get_quoted_identifier(pk)
                    where_conditions.append(f"{quoted_pk} = ?")
                    params.append(pk_values[pk])
                
                where_clause = " AND ".join(where_conditions)
                
                query = f"""
                SELECT * 
                FROM {safe_table_ref}
                WHERE {where_clause}
                """
                
                cursor = db_connection.execute_query(query, tuple(params))
                columns = [column[0] for column in cursor.description]
                
                row = cursor.fetchone()
                if row is None:
                    logger.info(
                        f"Record not found in {table_info.full_name}",
                        extra={"pk_values": pk_values}
                    )
                    raise HTTPException(
                        status_code=404,
                        detail=f"Record not found"
                    )
                
                result = dict(zip(columns, row))
                logger.info(
                    f"Retrieved record from {table_info.full_name} by PK",
                    extra={"pk_values": pk_values}
                )
                
                return result
                
            except HTTPException:
                # Re-raise HTTPException (404)
                raise
            except ValueError as e:
                # Validation error
                logger.error(f"Validation error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=400,
                    detail="Invalid request parameters"
                )
            except pyodbc.Error as e:
                logger.error(
                    f"Database error querying {table_info.full_name}",
                    exc_info=True,
                    extra={"error_code": e.args[0] if e.args else None}
                )
                raise HTTPException(
                    status_code=500,
                    detail="An error occurred processing your request"
                )
            except Exception as e:
                logger.error(f"Unexpected error: {e}", exc_info=True)
                raise HTTPException(
                    status_code=500,
                    detail="An unexpected error occurred"
                )
    
    def generate_all_routers(self, schemas: List[str]) -> List[APIRouter]:
        """
        Generate routers for all tables and views in specified schemas.
        
        Args:
            schemas: List of schema names
            
        Returns:
            List of configured routers
        """
        # Validation happens in schema_inspector.get_tables_and_views
        tables = schema_inspector.get_tables_and_views(schemas)
        routers = []
        
        for table in tables:
            try:
                router = self.create_router(table)
                routers.append(router)
                self.routers[table.full_name] = router
            except Exception as e:
                logger.error(
                    f"Failed to create router for {table.full_name}: {e}",
                    exc_info=True
                )
                # Continue with other tables
                continue
        
        logger.info(f"Generated {len(routers)} routers from {len(tables)} tables")
        return routers


# Global endpoint generator
endpoint_generator = EndpointGenerator()