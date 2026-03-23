"""Main FastAPI application with dynamic endpoint generation."""

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from config import settings
from api.endpoints import endpoint_generator
from db.connection import db_connection
from db.schema_inspector import schema_inspector


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title=settings.api_title,
        version=settings.api_version,
        description="Dynamically generated REST API from SQL Server schema",
    )

    @app.on_event("startup")
    async def startup_event():
        """Initialize database connection and generate endpoints on startup."""
        try:
            # Test database connection
            db_connection.connect()

            # Generate dynamic routers for all tables and views
            routers = endpoint_generator.generate_all_routers(settings.schema_list)

            # Include all generated routers
            for router in routers:
                app.include_router(router)

            print(f"Successfully generated {len(routers)} endpoints")

        except Exception as e:
            print(f"Error during startup: {str(e)}")
            raise

    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up database connection on shutdown."""
        db_connection.disconnect()

    @app.get("/")
    async def root():
        """Root endpoint with API information."""
        return {
            "message": "SQL Server API Accelerator",
            "version": settings.api_version,
            "docs": "/docs",
            "schemas": settings.schema_list,
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        try:
            conn = db_connection.connect()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            return {"status": "healthy", "database": "connected"}
        except Exception as e:
            return JSONResponse(
                status_code=503, content={"status": "unhealthy", "error": str(e)}
            )

    @app.get("/metadata")
    async def metadata():
        """Get metadata about all exposed tables and views."""
        tables = schema_inspector.get_tables_and_views(settings.schema_list)

        metadata = []
        for table in tables:
            table_meta = {
                "schema": table.schema,
                "name": table.name,
                "type": table.type,
                "full_name": table.full_name,
                "has_primary_key": table.has_primary_key,
                "primary_keys": table.primary_keys,
                "columns": [
                    {
                        "name": col.name,
                        "data_type": col.data_type,
                        "is_nullable": col.is_nullable,
                        "is_primary_key": col.is_primary_key,
                    }
                    for col in table.columns
                ],
                "endpoints": {
                    "get_all": f"/{table.schema}/{table.name}",
                    "get_by_pk": (
                        f"/{table.schema}/{table.name}/{{pk}}"
                        if table.has_primary_key
                        else None
                    ),
                },
            }
            metadata.append(table_meta)

        return metadata

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.api_host, port=settings.api_port, reload=True)
