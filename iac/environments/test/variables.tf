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

variable "supabase_organization_id" {
  type        = string
  description = "Supabase organization slug that owns the project"
}

variable "supabase_project_name" {
  type        = string
  description = "Supabase project name, unique within the organization"
}

variable "supabase_region" {
  type        = string
  description = "Supabase region, independent of the Azure location"
}

variable "supabase_instance_size" {
  type        = string
  description = "Paid plan instance size. Null leaves the plan default, which the free tier requires"
  default     = null
}

variable "supabase_db_password" {
  type        = string
  description = "Password for the Supabase project database, supplied as TF_VAR_supabase_db_password"
  sensitive   = true
}

variable "embedding_model" {
  type        = string
  description = "Embedding model the ingestion layer loads, read as EMBEDDING_MODEL"
}
