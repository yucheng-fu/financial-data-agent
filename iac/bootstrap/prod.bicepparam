using 'main.bicep'

param env = 'prod'
param stateResourceGroupName = 'rg-fda-prod'
param appResourceGroupName = 'rg-fda-app-prod'
param stateStorageAccountName = 'stfdaprod'
param principalId = readEnvironmentVariable('PRINCIPAL_ID')
