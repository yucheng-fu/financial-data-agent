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

  precondition {
    condition     = strcontains(local.database_url, ":5432/")
    error_message = "The composed URL is not on the session pooler port 5432, so Alembic DDL would fail. Inspect the pooler_urls output and adjust the port rewrite in main.tf."
  }

  precondition {
    condition     = startswith(local.database_url, "postgresql+psycopg://")
    error_message = "The composed URL does not name the psycopg dialect, so SQLAlchemy would fall back to psycopg2 and fail to import it. Inspect the pooler_urls output and adjust the scheme rewrite in main.tf."
  }
}

output "llm_reader_database_url" {
  value       = local.llm_reader_database_url
  description = "SQLAlchemy URL for the llm_reader role on the session pooler, used for model-generated SQL"
  sensitive   = true

  precondition {
    condition     = strcontains(local.llm_reader_database_url, "llm_reader.")
    error_message = "The pooler username was not postgres.<project_ref>, so llm_reader credentials were not substituted. Inspect the pooler_urls output and adjust the replacement in main.tf."
  }
}
