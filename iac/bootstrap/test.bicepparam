using 'main.bicep'

param env = 'test'
param resourceGroupName = 'rg-fda-test'
param stateStorageAccountName = 'stfdatest'
param principalId = readEnvironmentVariable('PRINCIPAL_ID')
param adminPrincipalId = readEnvironmentVariable('ADMIN_PRINCIPAL_ID', '')
