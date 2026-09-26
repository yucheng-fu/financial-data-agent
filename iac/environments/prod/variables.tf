variable "resource_group_name" {
  type        = string
  description = "Existing resource group to deploy into"
}

variable "location" {
  type        = string
  description = "Region for the deployed resources, independent of the resource group's region"
}

variable "env" {
  type        = string
  description = "Environment name, e.g. dev, test, prod"
}

variable "storage_account_name" {
  type        = string
  description = "Existing storage account created by the Bicep bootstrap"
}

variable "filings_container_name" {
  type        = string
  description = "Blob container holding the downloaded SEC filings"
}

variable "container_registry_name" {
  type        = string
  description = "Registry name, alphanumeric only and globally unique across Azure"
}

variable "container_app_name" {
  type = string
}

variable "container_image" {
  type        = string
  description = "Public placeholder image used to create the app. The pipeline replaces it with the pushed image"
}

variable "container_target_port" {
  type = number
}
