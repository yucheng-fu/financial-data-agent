variable "resource_group_name" {
  type = string
}

variable "location" {
  type    = string
  default = "West Europe"
}

variable "env" {
  type        = string
  description = "Environment name, e.g. dev, test, prod"
}
