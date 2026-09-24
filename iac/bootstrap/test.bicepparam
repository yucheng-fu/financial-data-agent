using 'main.bicep'

param env = 'test'
param stateResourceGroupName = 'rg-fda-test'
param appResourceGroupName = 'rg-fda-app-test'
param stateStorageAccountName = 'stfdatest'
param principalId = readEnvironmentVariable('PRINCIPAL_ID')
