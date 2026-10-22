param(
  [string]$AppName = "pooprprod",
  [string]$Location = "westus",
  [string]$GoogleClientId = $env:GOOGLE_CLIENT_ID,
  [string]$GoogleClientSecret = $env:GOOGLE_CLIENT_SECRET,
  [string]$SessionSecret = $env:SESSION_SECRET
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$account = az account show | ConvertFrom-Json
$suffix = $account.id.Substring(0, 8).ToLower()

$resourceGroup = "$AppName-rg"
$acrName = ("$AppName$suffix" -replace "[^a-zA-Z0-9]", "").ToLower()
$environmentName = "$AppName-env"
$postgresName = "$AppName-pg-$suffix"
$backendAppName = "$AppName-api"
$frontendAppName = "$AppName-web"
$postgresAdmin = "poopradmin"
$postgresPassword = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | ForEach-Object { [char]$_ })
if (-not $SessionSecret) {
  $SessionSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
}

Write-Host "Creating resource group $resourceGroup in $Location"
az group create --name $resourceGroup --location $Location | Out-Null

Write-Host "Creating Azure Container Registry $acrName"
az acr create --resource-group $resourceGroup --name $acrName --sku Basic --admin-enabled true | Out-Null

Write-Host "Creating Log Analytics workspace and Container Apps environment"
az monitor log-analytics workspace create --resource-group $resourceGroup --workspace-name "$AppName-logs" --location $Location | Out-Null
$workspaceId = az monitor log-analytics workspace show --resource-group $resourceGroup --workspace-name "$AppName-logs" --query customerId -o tsv
$workspaceKey = az monitor log-analytics workspace get-shared-keys --resource-group $resourceGroup --workspace-name "$AppName-logs" --query primarySharedKey -o tsv
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
$acrUser = az acr credential show --resource-group $resourceGroup --name $acrName --query username -o tsv
$acrPass = az acr credential show --resource-group $resourceGroup --name $acrName --query passwords[0].value -o tsv

Write-Host "Building backend image in ACR"
az acr build --registry $acrName --image "poopr-api:latest" ./backend --no-logs | Out-Null

$databaseUrl = "postgresql+psycopg://${postgresAdmin}:${postgresPassword}@${postgresName}.postgres.database.azure.com:5432/poopr?sslmode=require"

Write-Host "Creating internal backend Container App"
az containerapp create `
  --resource-group $resourceGroup `
  --name $backendAppName `
  --environment $environmentName `
  --image "$loginServer/poopr-api:latest" `
  --registry-server $loginServer `
  --registry-username $acrUser `
  --registry-password $acrPass `
  --target-port 8000 `
  --ingress internal `
  --min-replicas 1 `
  --max-replicas 3 `
  --secrets "database-url=$databaseUrl" `
  --env-vars "DATABASE_URL=secretref:database-url" "AUTH_MODE=easy_auth" "CORS_ORIGINS=https://localhost" | Out-Null

$backendOrigin = "https://" + (az containerapp show --resource-group $resourceGroup --name $backendAppName --query properties.configuration.ingress.fqdn -o tsv)

Write-Host "Building frontend image in ACR"
az acr build --registry $acrName --image "poopr-web:latest" --build-arg "VITE_API_BASE_URL=" --build-arg "VITE_AUTH_MODE=easy_auth" ./frontend --no-logs | Out-Null

Write-Host "Creating public frontend Container App"
az containerapp create `
  --resource-group $resourceGroup `
  --name $frontendAppName `
  --environment $environmentName `
  --image "$loginServer/poopr-web:latest" `
  --registry-server $loginServer `
  --registry-username $acrUser `
  --registry-password $acrPass `
  --target-port 80 `
  --ingress external `
  --min-replicas 1 `
  --max-replicas 3 `
  --env-vars "BACKEND_ORIGIN=$backendOrigin" | Out-Null

$frontendUrl = "https://" + (az containerapp show --resource-group $resourceGroup --name $frontendAppName --query properties.configuration.ingress.fqdn -o tsv)

Write-Host "Disabling Container Apps built-in authentication"
az containerapp auth update `
  --resource-group $resourceGroup `
  --name $frontendAppName `
  --enabled false `
  --yes | Out-Null

$redirectUri = "$frontendUrl/.auth/login/google/callback"
if ($GoogleClientId -and $GoogleClientSecret) {
  Write-Host "Configuring backend-owned Google OAuth"
  az containerapp secret set `
    --resource-group $resourceGroup `
    --name $backendAppName `
    --secrets "google-client-secret=$GoogleClientSecret" "session-secret=$SessionSecret" | Out-Null

  az containerapp update `
    --resource-group $resourceGroup `
    --name $backendAppName `
    --set-env-vars `
      "APP_BASE_URL=$frontendUrl" `
      "GOOGLE_CLIENT_ID=$GoogleClientId" `
      "GOOGLE_CLIENT_SECRET=secretref:google-client-secret" `
      "GOOGLE_REDIRECT_PATH=/.auth/login/google/callback" `
      "SESSION_SECRET=secretref:session-secret" | Out-Null
} else {
  Write-Warning "Google OAuth was not configured because GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET were not provided."
  Write-Host "Add this redirect URI to a Google OAuth web client, then run infra/enable-google-auth.ps1:"
  Write-Host $redirectUri
}

Write-Host ""
Write-Host "Production deployment complete."
Write-Host "Frontend: $frontendUrl"
Write-Host "Backend internal origin: $backendOrigin"
Write-Host "Resource group: $resourceGroup"
Write-Host "Google OAuth redirect URI: $redirectUri"

