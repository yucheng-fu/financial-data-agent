targetScope = 'subscription'

@description('Environment name, e.g. test, prod')
param env string

param location string = 'swedencentral'

@description('Resource group holding both the Terraform state and the application resources')
param resourceGroupName string

@description('Globally unique, 3-24 lowercase letters and numbers')
param stateStorageAccountName string

param stateContainerName string = 'tfstate'

@description('Object ID of the service principal that Terraform runs as')
param principalId string

@description('Object ID of a human administrator granted blob data access across the subscription. Empty skips the assignment.')
param adminPrincipalId string = ''

var contributorRoleId = 'b24988ac-6180-42a0-ab88-20f7382dd24c' // Contributor role
var storageBlobDataOwnerRoleId = 'b7e6dc6d-f1e8-4753-8033-0f276bb0955b' // Storage Blob Data Owner role

var tags = {
  env: env
}

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
  tags: tags
}

module stateStorage 'modules/state-storage.bicep' = {
  name: 'state-storage-${env}'
  scope: resourceGroup
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

resource adminBlobDataOwner 'Microsoft.Authorization/roleAssignments@2022-04-01' = if (!empty(adminPrincipalId)) {
  name: guid(subscription().id, adminPrincipalId, storageBlobDataOwnerRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      storageBlobDataOwnerRoleId
    )
    principalId: adminPrincipalId
    principalType: 'User'
  }
}
