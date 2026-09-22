terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.50"
    }
  }
}

provider "azurerm" {
  features {}
}
