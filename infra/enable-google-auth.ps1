param(
  [string]$ResourceGroup = "pooprprod-rg",
  [string]$ContainerAppName = "pooprprod-web",
  [string]$BackendContainerAppName = "pooprprod-api",
  [string]$GoogleClientId = $env:GOOGLE_CLIENT_ID,
  [string]$GoogleClientSecret = $env:GOOGLE_CLIENT_SECRET,
  [switch]$PrintRedirectUriOnly,
  [string]$SessionSecret = $env:SESSION_SECRET
)

$ErrorActionPreference = "Stop"
$PSNativeCommandUseErrorActionPreference = $true

$frontendHost = az containerapp show `
  --resource-group $ResourceGroup `
  --name $ContainerAppName `
  --query properties.configuration.ingress.fqdn `
  -o tsv

if (-not $frontendHost) {
  throw "Could not resolve Container Apps frontend host for $ResourceGroup/$ContainerAppName."
}

$frontendUrl = "https://$frontendHost"
$redirectUri = "$frontendUrl/.auth/login/google/callback"

Write-Host "Google OAuth authorized redirect URI:"
Write-Host $redirectUri

if ($PrintRedirectUriOnly) {
  return
}

if (-not $GoogleClientId -or -not $GoogleClientSecret) {
  throw "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET, or pass -GoogleClientId and -GoogleClientSecret. Add the redirect URI above to the Google OAuth client first."
}

if (-not $SessionSecret) {
  $SessionSecret = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 48 | ForEach-Object { [char]$_ })
}

Write-Host "Disabling Container Apps built-in auth on $ContainerAppName"
az containerapp auth update `
  --resource-group $ResourceGroup `
  --name $ContainerAppName `
  --enabled false `
  --yes | Out-Null

Write-Host "Configuring backend-owned Google OAuth on $BackendContainerAppName"
az containerapp secret set `
  --resource-group $ResourceGroup `
  --name $BackendContainerAppName `
  --secrets "google-client-secret=$GoogleClientSecret" "session-secret=$SessionSecret" | Out-Null

az containerapp update `
  --resource-group $ResourceGroup `
  --name $BackendContainerAppName `
  --set-env-vars `
    "APP_BASE_URL=$frontendUrl" `
    "GOOGLE_CLIENT_ID=$GoogleClientId" `
    "GOOGLE_CLIENT_SECRET=secretref:google-client-secret" `
    "GOOGLE_REDIRECT_PATH=/.auth/login/google/callback" `
    "SESSION_SECRET=secretref:session-secret" | Out-Null

$latestRevision = az containerapp show `
  --resource-group $ResourceGroup `
  --name $BackendContainerAppName `
  --query properties.latestRevisionName `
  -o tsv

az containerapp revision restart `
  --resource-group $ResourceGroup `
  --name $BackendContainerAppName `
  --revision $latestRevision | Out-Null

Write-Host "Google sign-in is configured."
Write-Host "Frontend: $frontendUrl"
