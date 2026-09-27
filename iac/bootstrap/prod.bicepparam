using 'main.bicep'

param env = 'prod'
param resourceGroupName = 'rg-fda-prod'
param stateStorageAccountName = 'stfdaprod'
param principalId = readEnvironmentVariable('PRINCIPAL_ID')
param adminPrincipalId = readEnvironmentVariable('ADMIN_PRINCIPAL_ID', '')
