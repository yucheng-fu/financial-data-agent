env = "test"

# Must match iac/environments/test so the moved state plans no changes: name and region
# force replacement of the project.
supabase_organization_id = "myzjsmnkyekmrupcbysz"
supabase_project_name    = "fda-test"
supabase_region          = "eu-north-1"

vercel_project_name = "fda-test"
filings_bucket      = "bucket-fda-test"
embedding_model     = "BAAI/bge-small-en-v1.5"
llm_model           = "gemini-3-flash"
