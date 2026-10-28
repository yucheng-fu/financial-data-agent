# Required here, not just in the environment, because Terraform would otherwise infer
# the vercel_ prefix as hashicorp/vercel, which does not exist. The environment pins
# the exact version.
terraform {
  required_providers {
    vercel = {
      source  = "vercel/vercel"
      version = ">= 5.24.1"
    }
  }
}

# Not connected to Git, so only the pipeline deploys, and always after the migration.
# The framework and region live in vercel.json, which the CLI uploads with the source.
resource "vercel_project" "this" {
  name = var.name
}

resource "vercel_project_environment_variables" "this" {
  project_id = vercel_project.this.id

  variables = concat(
    [
      for key, value in var.env_vars : {
        key       = key
        value     = value
        target    = ["production"]
        sensitive = false
      }
    ],
    [
      for key, value in var.secret_env_vars : {
        key       = key
        value     = value
        target    = ["production"]
        sensitive = true
      }
    ],
  )
}
