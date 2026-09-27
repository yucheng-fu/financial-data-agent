variable "name" {
  type        = string
  description = "Registry name, alphanumeric only and globally unique across Azure"
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "env" {
  type        = string
  description = "Environment name, e.g. dev, test, prod"
}

variable "sku" {
  type        = string
  description = "Registry SKU, one of Basic, Standard or Premium"
  default     = "Basic"
}
