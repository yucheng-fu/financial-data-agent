resource_group_name     = "rg-fda-test"
location                = "swedencentral"
env                     = "test"
storage_account_name    = "stfdatest"
filings_container_name  = "filings"
container_registry_name = "crfdatest"
container_app_name      = "ca-fda-test"
container_image         = "mcr.microsoft.com/k8se/quickstart:latest"
container_target_port   = 8000

# The organization slug is an identifier, not a credential. Replace it before the
# first apply, see iac/README.md.
supabase_organization_id = "REPLACE_WITH_SUPABASE_ORG_SLUG"
supabase_project_name    = "fda-test"
supabase_region          = "eu-north-1"
