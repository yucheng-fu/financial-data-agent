resource_group_name     = "rg-fda-prod"
location                = "swedencentral"
env                     = "prod"
storage_account_name    = "stfdaprod"
filings_container_name  = "filings"
container_registry_name = "crfdaprod"
container_app_name      = "ca-fda-prod"
container_image         = "mcr.microsoft.com/k8se/quickstart:latest"
container_target_port   = 8000

# The organization slug is an identifier, not a credential. Replace it before the
# first apply, see iac/README.md.
supabase_organization_id = "REPLACE_WITH_SUPABASE_ORG_SLUG"
supabase_project_name    = "fda-prod"
supabase_region          = "eu-north-1"
