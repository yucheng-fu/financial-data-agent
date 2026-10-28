# Vercel and Supabase infrastructure

Terraform roots, one per environment, for the Supabase project (`modules/supabase-postgres`) and the Vercel project with its environment variables (`modules/vercel-app`). State lives in each Supabase project's own `terraform-state` bucket.

## Prerequisites

Once per environment (`test`, `prod`), by hand:

1. In the Supabase project, create two **private** Storage buckets: `terraform-state` and `bucket-fda-<env>`. Neither Terraform provider can create buckets.
2. Under *Project Settings* → *Storage* → *S3 Connection*, enable S3 access and create an access key.
3. Under *Project Settings* → *API Keys*, create or reuse a **secret** key (`sb_secret_...`).
4. Create a Vercel token under *Account Settings* → *Tokens*. One token covers both environments.
5. Add the GitHub environment secrets and variable listed in [docs/deployment.md](../../docs/deployment.md#3-configuration).
6. If a Vercel project `fda-<env>` already exists, delete it, so Terraform can create it.

## Adopt the existing Supabase project (once per environment)

The project's state is moved from the retired Azure backend. Do not `import` it, see [docs/deployment.md](../../docs/deployment.md#5-adopting-the-existing-projects). Run this in Git Bash from the repository root: PowerShell 5.1's `>` writes UTF-16, which `terraform state push` rejects.

```bash
ENV=test
TMP="$(mktemp -d)"

az login
az account set --subscription <AZURE_SUBSCRIPTION_ID>
terraform -chdir=iac/environments/$ENV init -input=false
terraform -chdir=iac/environments/$ENV state pull > "$TMP/azure.tfstate"

(cd "$TMP" && terraform state mv -state=azure.tfstate -state-out=new.tfstate module.supabase_postgres module.supabase_postgres)

export AWS_ENDPOINT_URL_S3="https://<project_ref>.storage.supabase.co/storage/v1/s3"
export AWS_ACCESS_KEY_ID="<S3 access key ID>"
export AWS_SECRET_ACCESS_KEY="<S3 secret access key>"
terraform -chdir=iac/vercel-supabase/$ENV init -input=false
terraform -chdir=iac/vercel-supabase/$ENV state push "$TMP/new.tfstate"
```

Then plan, with the same values the pipeline uses:

```bash
export SUPABASE_ACCESS_TOKEN="..." VERCEL_API_TOKEN="..."
export TF_VAR_supabase_db_password="..." TF_VAR_llm_reader_db_password="..."
export TF_VAR_supabase_secret_key="..." TF_VAR_google_api_key="..."
terraform -chdir=iac/vercel-supabase/$ENV plan
```

The plan must show `2 to add, 0 to change, 0 to destroy`: the Vercel project and its environment variables. Then delete the temporary files, which contain the database passwords:

```bash
rm -r "$TMP"
```

Repeat with `ENV=prod`. After that, CI runs `init`, `plan` and `apply` on every push to `main`.

## Further reading

[docs/deployment.md](../../docs/deployment.md) — configuration, the state backend, why the state is moved rather than imported, and the pipeline.
