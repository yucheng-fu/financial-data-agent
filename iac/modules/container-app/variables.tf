variable "name" {
  type        = string
  description = "Container app name, also used to derive the environment and log workspace names"
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

variable "image" {
  type        = string
  description = "Container image, e.g. myregistry.azurecr.io/api:latest"
}

variable "target_port" {
  type        = number
  description = "Port the container listens on"
}

variable "cpu" {
  type    = number
  default = 0.25
}

variable "memory" {
  type    = string
  default = "0.5Gi"
}

variable "min_replicas" {
  type    = number
  default = 0
}

variable "max_replicas" {
  type    = number
  default = 1
}
