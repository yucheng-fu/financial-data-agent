terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "5.5.0"
    }
    supabase = {
      source  = "supabase/supabase"
      version = "1.11.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# access_token comes from SUPABASE_ACCESS_TOKEN, set per GitHub environment.
provider "supabase" {}
