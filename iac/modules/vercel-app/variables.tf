variable "name" {
  type        = string
  description = "Vercel project name, also the subdomain of its production URL when available"
}

variable "env_vars" {
  type        = map(string)
  description = "Plain runtime environment variables for production deployments"
  default     = {}
}

variable "secret_env_vars" {
  type        = map(string)
  description = "Sensitive runtime environment variables for production deployments, unreadable after creation"
  default     = {}
  sensitive   = true
}
