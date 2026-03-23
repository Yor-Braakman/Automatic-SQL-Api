"""SQL Server connection management with Azure AD authentication."""
import pyodbc
import struct
from azure.identity import ClientSecretCredential
from config import settings
from typing import Optional


class SQLServerConnection:
    """Manage SQL Server connections with service principal authentication."""
    
    def __init__(self):
        self.connection: Optional[pyodbc.Connection] = None
        self._access_token = None
    
    def _get_access_token(self) -> str:
        """Get Azure AD access token using service principal credentials."""
        credential = ClientSecretCredential(
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret
        )
        
        # Get token for Azure SQL Database
        token = credential.get_token("https://database.windows.net/.default")
        return token.token
    
    def _build_token_struct(self, token: str) -> bytes:
        """Build SQL_COPT_SS_ACCESS_TOKEN structure for pyodbc."""
        token_bytes = token.encode("utf-16-le")
        token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
        return token_struct
    
    def connect(self) -> pyodbc.Connection:
        """Establish connection to SQL Server using service principal."""
        if self.connection is not None:
            try:
                # Test if connection is still alive
                self.connection.cursor().execute("SELECT 1")
                return self.connection
            except:
                self.connection = None
        
        # Get fresh access token
        access_token = self._get_access_token()
        token_struct = self._build_token_struct(access_token)
        
        # SQL_COPT_SS_ACCESS_TOKEN constant
        SQL_COPT_SS_ACCESS_TOKEN = 1256
        
        # Connect using access token
        conn_str = settings.connection_string
        self.connection = pyodbc.connect(
            conn_str,
            attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct}
        )
        
        return self.connection
    
    def disconnect(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None):
        """Execute a query and return results."""
        conn = self.connect()
        cursor = conn.cursor()
        
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        return cursor


# Global connection instance
db_connection = SQLServerConnection()


def get_connection():
    """Get the database connection instance."""
    return db_connection.connect()
