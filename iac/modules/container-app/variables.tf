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
  description = "Image used to create the app, e.g. myregistry.azurecr.io/api:latest. Only applied on creation; later changes are ignored because the pipeline owns the tag"
}

variable "identity_id" {
  type        = string
  description = "Resource ID of the user assigned identity the app runs as and pulls images with"
}

variable "registry_login_server" {
  type        = string
  description = "Login server of the registry to pull from, e.g. myregistry.azurecr.io"
}

variable "env_vars" {
  type        = map(string)
  description = "Plain environment variables set on the container"
  default     = {}
}

variable "target_port" {
  type        = number
  description = "Port the container listens on"
}

variable "cpu" {
  type        = number
  description = "Must pair with memory against an allowed Container Apps combination"
  default     = 0.5
}

variable "memory" {
  type    = string
  default = "1Gi"
}

variable "min_replicas" {
  type    = number
  default = 0
}

variable "max_replicas" {
  type    = number
  default = 1
}
