@description('Object ID of the service principal that Terraform runs as')
param principalId string

var rbacAdministratorRoleId = 'f58310d9-a9f6-439a-9e8d-f62e7b41a168' // Role Based Access Control Administrator role

resource rbacAdministrator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(resourceGroup().id, principalId, rbacAdministratorRoleId)
  properties: {
    roleDefinitionId: subscriptionResourceId(
      'Microsoft.Authorization/roleDefinitions',
      rbacAdministratorRoleId
    )
    principalId: principalId
    principalType: 'ServicePrincipal'
  }
}
