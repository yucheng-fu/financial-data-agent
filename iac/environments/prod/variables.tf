variable "resource_group_name" {
  type        = string
  description = "Existing resource group to deploy into"
}

variable "env" {
  type        = string
  description = "Environment name, e.g. dev, test, prod"
}

variable "container_app_name" {
  type = string
}

variable "container_image" {
  type = string
}

variable "container_target_port" {
  type = number
}
