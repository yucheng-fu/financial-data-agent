terraform {
  backend "azurerm" {
    resource_group_name  = "rg-fda-tfstate"
    storage_account_name = "stfdatfstate"
    container_name       = "tfstate"
    key                  = "prod.tfstate"
  }
}
