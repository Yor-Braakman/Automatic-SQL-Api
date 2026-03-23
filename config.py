"""Configuration management for the API Accelerator with improved settings."""

from pydantic_settings import BaseSettings
from typing import List
import logging


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # SQL Server settings
    sql_server: str
    sql_database: str
    sql_driver: str = "ODBC Driver 18 for SQL Server"

    # Azure Service Principal
    azure_client_id: str
    azure_client_secret: str
    azure_tenant_id: str

    # Schema configuration
    schemas_to_expose: str = "dbo"

    # API configuration
    api_title: str = "SQL Server API Accelerator"
    api_version: str = "1.0.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Logging configuration
    log_level: str = "INFO"
    log_format: str = "json"  # json or text

    # Security settings (for future implementation)
    enable_api_key_auth: bool = False
    api_keys: str = ""

    # Performance settings
    query_timeout: int = 30  # seconds
    max_page_size: int = 1000
    default_page_size: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def schema_list(self) -> List[str]:
        """Return schemas as a list."""
        return [s.strip() for s in self.schemas_to_expose.split(",") if s.strip()]

    @property
    def connection_string(self) -> str:
        """Build the connection string for SQL Server."""
        return (
            f"Driver={{{self.sql_driver}}};"
            f"Server=tcp:{self.sql_server},1433;"
            f"Database={self.sql_database};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
            "Connection Timeout=30;"
        )

    def configure_logging(self):
        """Configure application logging."""
        log_level = getattr(logging, self.log_level.upper(), logging.INFO)

        if self.log_format == "json":
            # JSON logging for production
            import sys

            logging.basicConfig(
                level=log_level,
                format="%(message)s",
                handlers=[logging.StreamHandler(sys.stdout)],
            )
        else:
            # Text logging for development
            logging.basicConfig(
                level=log_level,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )


settings = Settings()
