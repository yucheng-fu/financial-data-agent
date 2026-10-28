output "supabase_project_ref" {
  value = module.supabase_postgres.project_ref
}

output "vercel_project_name" {
  value = module.vercel_app.name
}

output "vercel_project_id" {
  value = module.vercel_app.project_id
}

# Read inside the deploy job with `terraform output -raw` and masked before use.
output "database_url" {
  value     = module.supabase_postgres.database_url
  sensitive = true
}

output "llm_reader_database_url" {
  value     = module.supabase_postgres.llm_reader_database_url
  sensitive = true
}
