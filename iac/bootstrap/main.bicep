targetScope = 'subscription'

@description('Environment name, e.g. test, prod')
param env string

param location string = 'westeurope'

param stateResourceGroupName string

param appResourceGroupName string

@description('Globally unique, 3-24 lowercase letters and numbers')
param stateStorageAccountName string

param stateContainerName string = 'tfstate'

@description('Object ID of the service principal that Terraform runs as')
param principalId string

var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c'

var tags = {
  env: env
}

resource stateResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: stateResourceGroupName
  location: location
  tags: tags
}

resource appResourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: appResourceGroupName
  location: location
  tags: tags
}

module stateStorage 'modules/state-storage.bicep' = {
  name: 'state-storage-${env}'
  scope: stateResourceGroup
  params: {
    location: location
    storageAccountName: stateStorageAccountName
    containerName: stateContainerName
    principalId: principalId
    tags: tags
  }
}

resource subscriptionContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(subscription().id, principalId, contributorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', contributorRoleId)
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
