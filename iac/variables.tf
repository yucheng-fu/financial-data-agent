variable "resource_group_name" {
  type = string
}

variable "location" {
  type    = string
  default = "Sweden Central"
}

variable "env" {
  type        = string
  description = "Environment name, test or prod"
}