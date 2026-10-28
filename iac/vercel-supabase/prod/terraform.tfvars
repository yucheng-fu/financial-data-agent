env = "prod"

# The ref is an identifier, not a credential. Name and region must match the existing
# project: the provider cannot change the region, and a different name renames it.
supabase_organization_id = "myzjsmnkyekmrupcbysz"
supabase_project_name    = "fda-prod"
supabase_region          = "eu-north-1"

vercel_project_name = "fda-prod"
filings_bucket      = "bucket-fda-prod"
embedding_model     = "BAAI/bge-small-en-v1.5"
llm_model           = "gemini-3-flash"
