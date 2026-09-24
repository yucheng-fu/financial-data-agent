terraform {
  backend "azurerm" {
    resource_group_name  = "rg-fda-prod"
    storage_account_name = "stfdaprod"
    container_name       = "tfstate"
    key                  = "prod.tfstate"
    use_oidc             = true
    use_azuread_auth     = true
  }
}
