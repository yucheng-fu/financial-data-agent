variable "storage_account_name" {
  type        = string
  description = "Globally unique name, 3-24 lowercase letters and numbers"
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
