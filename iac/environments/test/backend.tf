terraform {
  backend "azurerm" {
    resource_group_name  = "rg-fda-test"
    storage_account_name = "stfdatest"
    container_name       = "tfstate"
    key                  = "test.tfstate"
    use_oidc             = true
  }
}
