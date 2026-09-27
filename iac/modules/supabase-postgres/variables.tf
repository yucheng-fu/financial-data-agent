variable "organization_id" {
  type        = string
  description = "Supabase organization slug, found in the dashboard URL or organization settings"
}

variable "project_name" {
  type        = string
  description = "Supabase project name, unique within the organization"
}

variable "database_password" {
  type        = string
  description = "Password for the project database. Changing this updates or replaces the project"
  sensitive   = true
}

variable "region" {
  type        = string
  description = "Supabase region, e.g. eu-north-1. Independent of the Azure location"
}

variable "instance_size" {
  type        = string
  description = "Paid plan instance size, e.g. micro. Null leaves the plan default, which is what the free tier requires"
  default     = null
}
