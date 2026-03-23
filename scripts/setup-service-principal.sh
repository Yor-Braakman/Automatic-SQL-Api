#!/bin/bash
# Script to set up Azure Service Principal for SQL Server authentication

set -e

echo "Setting up Service Principal for SQL Server API Accelerator"
echo "==========================================================="

# Variables
SP_NAME="api-accelerator-sp"
SQL_SERVER=""
SQL_DATABASE=""

# Parse arguments
while getopts "s:d:" opt; do
  case $opt in
    s) SQL_SERVER="$OPTARG"
    ;;
    d) SQL_DATABASE="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    exit 1
    ;;
  esac
done

if [ -z "$SQL_SERVER" ] || [ -z "$SQL_DATABASE" ]; then
    echo "Usage: $0 -s <sql-server> -d <sql-database>"
    echo "Example: $0 -s myserver.database.windows.net -d mydatabase"
    exit 1
fi

# Check if logged in to Azure
if ! az account show > /dev/null 2>&1; then
    echo "Please log in to Azure first:"
    echo "  az login"
    exit 1
fi

# Create Service Principal
echo ""
echo "Creating Service Principal..."
SP_OUTPUT=$(az ad sp create-for-rbac --name "$SP_NAME" --skip-assignment --output json)

CLIENT_ID=$(echo $SP_OUTPUT | jq -r '.appId')
CLIENT_SECRET=$(echo $SP_OUTPUT | jq -r '.password')
TENANT_ID=$(echo $SP_OUTPUT | jq -r '.tenant')

echo "Service Principal created:"
echo "  Client ID: $CLIENT_ID"
echo "  Client Secret: $CLIENT_SECRET"
echo "  Tenant ID: $TENANT_ID"

# Wait for replication
echo ""
echo "Waiting for Azure AD replication (30 seconds)..."
sleep 30

# Generate SQL script for database access
SQL_SCRIPT=$(cat <<EOF
-- Execute this script on your SQL Server database: $SQL_DATABASE
-- Make sure Azure AD authentication is enabled on your SQL Server

-- Create user from service principal
CREATE USER [$SP_NAME] FROM EXTERNAL PROVIDER;

-- Grant read permissions
ALTER ROLE db_datareader ADD MEMBER [$SP_NAME];

-- Optional: Grant additional permissions if needed
-- ALTER ROLE db_datawriter ADD MEMBER [$SP_NAME];
-- ALTER ROLE db_owner ADD MEMBER [$SP_NAME];

-- Verify the user was created
SELECT name, type_desc, authentication_type_desc 
FROM sys.database_principals 
WHERE name = '$SP_NAME';
EOF
)

echo ""
echo "==========================================================="
echo "Service Principal Setup Complete!"
echo "==========================================================="
echo ""
echo "SAVE THESE CREDENTIALS SECURELY:"
echo "  AZURE_CLIENT_ID=$CLIENT_ID"
echo "  AZURE_CLIENT_SECRET=$CLIENT_SECRET"
echo "  AZURE_TENANT_ID=$TENANT_ID"
echo ""
echo "Next Steps:""
echo "1. Update your .env file with the credentials above"
echo ""
echo "2. Execute the following SQL script on your database:"
echo "   Server: $SQL_SERVER"
echo "   Database: $SQL_DATABASE"
echo ""
echo "$SQL_SCRIPT" | tee setup-sql-access.sql
echo ""
echo "SQL script has been saved to: setup-sql-access.sql"
echo ""
echo "3. You can execute it using:"
echo "   sqlcmd -S $SQL_SERVER -d $SQL_DATABASE -G -i setup-sql-access.sql"
echo "   Or use Azure Data Studio / SQL Server Management Studio"
echo ""
