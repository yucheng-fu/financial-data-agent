env = "prod"

# Must match iac/environments/prod so the moved state plans no changes: name and region
# force replacement of the project.
supabase_organization_id = "myzjsmnkyekmrupcbysz"
supabase_project_name    = "fda-prod"
supabase_region          = "eu-north-1"

vercel_project_name = "fda-prod"
filings_bucket      = "bucket-fda-prod"
embedding_model     = "BAAI/bge-small-en-v1.5"
llm_model           = "gemini-3-flash"
