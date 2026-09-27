output "project_ref" {
  value       = supabase_project.this.id
  description = "Project reference used in the dashboard URL and the pooler username"
}

output "pooler_urls" {
  value       = data.supabase_pooler.this.url
  description = "Pooler mode to connection string, for inspecting the available modes during bring up"
  sensitive   = true
}

output "database_url" {
  value       = local.database_url
  description = "SQLAlchemy URL for the session pooler, consumed by the app and by Alembic"
  sensitive   = true

  precondition {
    condition     = !strcontains(local.database_url, "YOUR-PASSWORD")
    error_message = "The pooler connection string did not contain the [YOUR-PASSWORD] placeholder, so no password was substituted. Inspect the pooler_urls output and adjust the substitution in main.tf."
  }
}
