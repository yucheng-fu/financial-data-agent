# The project predates this root, so it is adopted rather than created. Once it is in
# state this is a no-op, and it re-adopts the project if the state is ever lost. The
# provider never reads the password back, so the first apply after an import sets it to
# var.supabase_db_password, the same value the connection strings are built from.
import {
  to = module.supabase_postgres.supabase_project.this
  id = var.supabase_project_ref
}

module "supabase_postgres" {
  source = "../../modules/supabase-postgres"

  organization_id     = var.supabase_organization_id
  project_name        = var.supabase_project_name
  region              = var.supabase_region
  instance_size       = var.supabase_instance_size
  database_password   = var.supabase_db_password
  llm_reader_password = var.llm_reader_db_password
}

module "vercel_app" {
  source = "../../modules/vercel-app"

  name = var.vercel_project_name

  # The function filesystem is read-only except /tmp, hence the cache directories.
  env_vars = {
    ENVIRONMENT                    = var.env
    EMBEDDING_MODEL                = var.embedding_model
    EMBEDDING_CACHE_DIR            = "/tmp/fastembed"
    EDGAR_LOCAL_DATA_DIR           = "/tmp/edgar"
    LLM_MODEL                      = var.llm_model
    SUPABASE_URL                   = "https://${module.supabase_postgres.project_ref}.supabase.co"
    FILINGS_BUCKET                 = var.filings_bucket
    VERCEL_SUPPORT_LARGE_FUNCTIONS = "1"
  }

  secret_env_vars = {
    DATABASE_URL            = module.supabase_postgres.database_url
    LLM_READER_DATABASE_URL = module.supabase_postgres.llm_reader_database_url
    SUPABASE_SECRET         = var.supabase_secret
    GOOGLE_API_KEY          = var.google_api_key
  }
}
