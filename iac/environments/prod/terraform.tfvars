resource_group_name     = "rg-fda-prod"
location                = "swedencentral"
env                     = "prod"
storage_account_name    = "stfdaprod"
filings_container_name  = "filings"
container_registry_name = "crfdaprod"
container_app_name      = "ca-fda-prod"
container_image         = "mcr.microsoft.com/k8se/quickstart:latest"
container_target_port   = 8000
embedding_model         = "BAAI/bge-small-en-v1.5"

# The organization slug is an identifier, not a credential. Replace it before the
# first apply, see iac/README.md.
supabase_organization_id = "myzjsmnkyekmrupcbysz"
supabase_project_name    = "fda-prod"
supabase_region          = "eu-north-1"
