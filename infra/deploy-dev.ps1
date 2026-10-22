param(
  [string]$AppName = "poopr",
  [string]$Location = "westus2"
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$accountId = az account show --query id -o tsv
$suffix = $accountId.Substring(0, 8).ToLower()
$resourceGroup = "$AppName-dev-rg"
$acrName = ("$AppName$suffix" -replace "[^a-zA-Z0-9]", "").ToLower()
$environmentName = "$AppName-dev-env"
$postgresName = "$AppName-dev-pg-$suffix"
$backendAppName = "$AppName-api"
$frontendAppName = "$AppName-web"
$postgresAdmin = "poopradmin"
$postgresPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })

Write-Host "Creating resource group $resourceGroup in $Location"
az group create --name $resourceGroup --location $Location | Out-Null

Write-Host "Creating Azure Container Registry $acrName"
az acr create --resource-group $resourceGroup --name $acrName --sku Basic --admin-enabled true | Out-Null

Write-Host "Creating Log Analytics workspace and Container Apps environment"
az monitor log-analytics workspace create --resource-group $resourceGroup --workspace-name "$AppName-dev-logs" --location $Location | Out-Null
$workspaceId = az monitor log-analytics workspace show --resource-group $resourceGroup --workspace-name "$AppName-dev-logs" --query customerId -o tsv
$workspaceKey = az monitor log-analytics workspace get-shared-keys --resource-group $resourceGroup --workspace-name "$AppName-dev-logs" --query primarySharedKey -o tsv
az containerapp env create --resource-group $resourceGroup --name $environmentName --location $Location --logs-workspace-id $workspaceId --logs-workspace-key $workspaceKey | Out-Null

Write-Host "Creating PostgreSQL Flexible Server $postgresName"
az postgres flexible-server create `
  --resource-group $resourceGroup `
  --name $postgresName `
  --location $Location `
  --admin-user $postgresAdmin `
  --admin-password $postgresPassword `
  --sku-name Standard_B1ms `
  --tier Burstable `
  --storage-size 32 `
  --version 16 `
  --public-access 0.0.0.0 `
  --yes | Out-Null

az postgres flexible-server db create --resource-group $resourceGroup --server-name $postgresName --database-name poopr | Out-Null
az postgres flexible-server firewall-rule create --resource-group $resourceGroup --name $postgresName --rule-name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0 | Out-Null

$loginServer = az acr show --resource-group $resourceGroup --name $acrName --query loginServer -o tsv
$backendImage = "$loginServer/poopr-api:latest"
$frontendImage = "$loginServer/poopr-web:latest"

Write-Host "Building backend image in ACR"
az acr build --registry $acrName --image "poopr-api:latest" ./backend | Out-Null

$databaseUrl = "postgresql+psycopg://${postgresAdmin}:${postgresPassword}@${postgresName}.postgres.database.azure.com:5432/poopr?sslmode=require"

Write-Host "Creating backend Container App"
az containerapp create `
  --resource-group $resourceGroup `
  --name $backendAppName `
  --environment $environmentName `
  --image $backendImage `
  --registry-server $loginServer `
  --target-port 8000 `
  --ingress external `
  --min-replicas 1 `
  --max-replicas 3 `
  --secrets "database-url=$databaseUrl" `
  --env-vars "DATABASE_URL=secretref:database-url" "CORS_ORIGINS=*" | Out-Null

$backendUrl = "https://" + (az containerapp show --resource-group $resourceGroup --name $backendAppName --query properties.configuration.ingress.fqdn -o tsv)

Write-Host "Building frontend image in ACR with API URL $backendUrl"
az acr build --registry $acrName --image "poopr-web:latest" --build-arg "VITE_API_BASE_URL=$backendUrl" ./frontend | Out-Null

Write-Host "Creating frontend Container App"
az containerapp create `
  --resource-group $resourceGroup `
  --name $frontendAppName `
  --environment $environmentName `
  --image $frontendImage `
  --registry-server $loginServer `
  --target-port 80 `
  --ingress external `
  --min-replicas 1 `
  --max-replicas 3 | Out-Null

$frontendUrl = "https://" + (az containerapp show --resource-group $resourceGroup --name $frontendAppName --query properties.configuration.ingress.fqdn -o tsv)

Write-Host "Updating backend CORS origin to $frontendUrl"
az containerapp update --resource-group $resourceGroup --name $backendAppName --set-env-vars "CORS_ORIGINS=$frontendUrl" | Out-Null

Write-Host ""
Write-Host "Deployment complete."
Write-Host "Frontend: $frontendUrl"
Write-Host "Backend:  $backendUrl"
Write-Host "Resource group: $resourceGroup"

