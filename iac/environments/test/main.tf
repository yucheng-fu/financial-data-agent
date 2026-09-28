data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

# Created by the Bicep bootstrap, so it is read rather than managed here.
data "azurerm_storage_account" "this" {
  name                = var.storage_account_name
  resource_group_name = data.azurerm_resource_group.this.name
}

resource "azurerm_storage_container" "filings" {
  name                  = var.filings_container_name
  storage_account_id    = data.azurerm_storage_account.this.id
  container_access_type = "private"
}

# User assigned rather than system assigned so the AcrPull grant below can be
# created before the container app that depends on it.
resource "azurerm_user_assigned_identity" "app" {
  name                = "id-${var.container_app_name}"
  resource_group_name = data.azurerm_resource_group.this.name
  location            = var.location

  tags = {
    env = var.env
  }
}

module "container_registry" {
  source = "../../modules/container-registry"

  name                = var.container_registry_name
  resource_group_name = data.azurerm_resource_group.this.name
  location            = var.location
  env                 = var.env
}

resource "azurerm_role_assignment" "acr_pull" {
  scope                            = module.container_registry.id
  role_definition_name             = "AcrPull"
  principal_id                     = azurerm_user_assigned_identity.app.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "filings_blob_contributor" {
  scope                            = azurerm_storage_container.filings.id
  role_definition_name             = "Storage Blob Data Contributor"
  principal_id                     = azurerm_user_assigned_identity.app.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

module "supabase_postgres" {
  source = "../../modules/supabase-postgres"

  organization_id   = var.supabase_organization_id
  project_name      = var.supabase_project_name
  region            = var.supabase_region
  instance_size     = var.supabase_instance_size
  database_password = var.supabase_db_password
}

module "container_app" {
  source = "../../modules/container-app"

  name                  = var.container_app_name
  resource_group_name   = data.azurerm_resource_group.this.name
  location              = var.location
  env                   = var.env
  image                 = var.container_image
  target_port           = var.container_target_port
  identity_id           = azurerm_user_assigned_identity.app.id
  registry_login_server = module.container_registry.login_server

  env_vars = {
    ENVIRONMENT          = var.env
    STORAGE_ACCOUNT_NAME = data.azurerm_storage_account.this.name
    FILINGS_CONTAINER    = azurerm_storage_container.filings.name
    AZURE_CLIENT_ID      = azurerm_user_assigned_identity.app.client_id
    EMBEDDING_MODEL      = var.embedding_model
  }

  secrets = {
    database-url = module.supabase_postgres.database_url
  }

  secret_env_vars = {
    DATABASE_URL = "database-url"
  }

  depends_on = [azurerm_role_assignment.acr_pull]
}
