# API Accelerator - FastAPI SQL Server Dynamic REST API

A FastAPI application that dynamically generates REST endpoints from SQL Server database schema with Azure AD authentication.

## Features

- Dynamic REST endpoint generation from SQL Server tables and views
- Azure AD Service Principal authentication for SQL Server
- Automatic primary key detection and endpoint generation
- Schema filtering to expose only specific schemas
- FastAPI with automatic Swagger UI documentation
- Azure VM deployment with Bicep
- CI/CD pipeline support (GitHub Actions / Azure DevOps)

## Architecture

```
api-accelerator/
├── main.py                 # FastAPI application entry point
├── config.py              # Configuration management
├── requirements.txt       # Python dependencies
├── api/
│   ├── __init__.py
│   └── endpoints.py       # Dynamic endpoint generator
├── db/
│   ├── __init__.py
│   ├── connection.py      # SQL Server connection with Azure AD
│   └── schema_inspector.py # Schema introspection and PK detection
├── deploy/
│   ├── main.bicep         # Azure VM infrastructure
│   └── install.sh         # VM setup script
├── tests/
│   └── ...                # Test files
└── .env                   # Environment configuration
```

## Prerequisites

- Python 3.11+
- SQL Server with Azure AD authentication enabled
- Azure Service Principal with SQL Server access
- ODBC Driver 18 for SQL Server

## Local Development

1. Clone the repository
2. Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

3. Create and activate virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows
```

4. Install dependencies:

```bash
pip install -r requirements.txt
```

5. Run the application:

```bash
python main.py
```

6. Access Swagger UI at http://localhost:8000/docs

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| SQL_SERVER | SQL Server hostname | myserver.database.windows.net |
| SQL_DATABASE | Database name | MyDatabase |
| SQL_DRIVER | ODBC driver name | ODBC Driver 18 for SQL Server |
| AZURE_CLIENT_ID | Service Principal Client ID | xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| AZURE_CLIENT_SECRET | Service Principal Secret | your-secret |
| AZURE_TENANT_ID | Azure Tenant ID | xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx |
| SCHEMAS_TO_EXPOSE | Comma-separated schema list | dbo,sales,inventory |

### Service Principal Setup

1. Create a Service Principal:

```bash
az ad sp create-for-rbac --name api-accelerator-sp
```

2. Grant SQL Server access:

```sql
CREATE USER [api-accelerator-sp] FROM EXTERNAL PROVIDER;
ALTER ROLE db_datareader ADD MEMBER [api-accelerator-sp];
```

## Generated Endpoints

The API automatically generates the following endpoints for each table/view:

### Tables/Views WITHOUT Primary Key

- `GET /{schema}/{table}` - Get all records with pagination

### Tables WITH Primary Key

- `GET /{schema}/{table}` - Get all records with pagination
- `GET /{schema}/{table}/{pk}` - Get record by primary key
- For composite keys: `GET /{schema}/{table}/{pk1}/{pk2}`

### Metadata Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `GET /metadata` - Schema metadata and available endpoints
- `GET /docs` - Swagger UI documentation

## Azure Deployment

### Prerequisites

- Azure subscription
- Azure CLI or GitHub/Azure DevOps configured

### Deploy with Bicep

1. Set parameters in Bicep parameters file or pass as arguments

2. Deploy:

```bash
az deployment group create \
  --resource-group rg-api-accelerator \
  --template-file deploy/main.bicep \
  --parameters \
    vmName=api-vm \
    adminUsername=azureuser \
    adminPassword='YourSecurePassword!' \
    sqlClientId='your-client-id' \
    sqlClientSecret='your-client-secret' \
    sqlTenantId='your-tenant-id' \
    sqlServerName='myserver.database.windows.net' \
    sqlDatabaseName='MyDatabase'
```

### Deploy with GitHub Actions

1. Configure secrets in GitHub repository:
   - AZURE_CREDENTIALS
   - VM_ADMIN_USERNAME
   - VM_ADMIN_PASSWORD
   - VM_SSH_KEY
   - SQL_CLIENT_ID
   - SQL_CLIENT_SECRET
   - SQL_TENANT_ID
   - SQL_SERVER_NAME
   - SQL_DATABASE_NAME

2. Push to main branch to trigger deployment

### Deploy with Azure DevOps

1. Configure service connections and variables
2. Run the pipeline

## Usage Examples

### Get all customers

```bash
GET /dbo/Customers?limit=50&offset=0
```

### Get customer by ID

```bash
GET /dbo/Customers/12345
```

### Get metadata

```bash
GET /metadata
```

Response:
```json
[
  {
    "schema": "dbo",
    "name": "Customers",
    "type": "TABLE",
    "has_primary_key": true,
    "primary_keys": ["CustomerID"],
    "columns": [...],
    "endpoints": {
      "get_all": "/dbo/Customers",
      "get_by_pk": "/dbo/Customers/{pk}"
    }
  }
]
```

## Security Considerations

- Service Principal credentials are stored securely in Azure Key Vault (recommended)
- Environment variables are not committed to source control
- SQL Server connections use encrypted connections
- Network Security Groups restrict access to API port
- Consider adding API authentication/authorization for production use

## Monitoring

The application includes:
- Health check endpoint at `/health`
- Systemd service with automatic restart
- Logging to systemd journal

View logs on VM:
```bash
sudo journalctl -u api-accelerator.service -f
```

## Troubleshooting

### Connection Issues

Check service principal has SQL access:
```sql
SELECT name, type_desc FROM sys.database_principals WHERE name = 'your-sp-name';
```

### Service Status

```bash
sudo systemctl status api-accelerator.service
```

### View Logs

```bash
sudo journalctl -u api-accelerator.service -n 100
```

## License

MIT
