output "resource_group_name" {
  value = data.azurerm_resource_group.this.name
}

output "container_registry_name" {
  value = module.container_registry.name
}

output "container_registry_login_server" {
  value = module.container_registry.login_server
}

output "container_app_name" {
  value = module.container_app.name
}

output "container_app_fqdn" {
  value = module.container_app.fqdn
}

output "filings_container_name" {
  value = azurerm_storage_container.filings.name
}

output "supabase_project_ref" {
  value = module.supabase_postgres.project_ref
}

output "pooler_urls" {
  value     = module.supabase_postgres.pooler_urls
  sensitive = true
}

# Read inside the migration job with `terraform output -raw`. Deliberately not
# promoted to a workflow job output, which would not be masked.
output "database_url" {
  value     = module.supabase_postgres.database_url
  sensitive = true
}

# Read inside the migration job like database_url, for the same reason.
output "llm_reader_database_url" {
  value     = module.supabase_postgres.llm_reader_database_url
  sensitive = true
}
