# Vercel and Supabase infrastructure

Terraform roots, one per environment, for the Supabase project (`modules/supabase-postgres`) and the Vercel project with its environment variables (`modules/vercel-app`). State lives under `terraform/` in each Supabase project's `bucket-fda-<env>` bucket, next to the filings.

## Prerequisites

Once per environment (`test`, `prod`), by hand:

1. In the Supabase project, create the **private** Storage bucket `bucket-fda-<env>`. It holds the filings and the Terraform state. Neither Terraform provider can create buckets.
2. Under *Project Settings* → *Storage* → *S3 Connection*, enable S3 access and create an access key.
3. Under *Project Settings* → *API Keys*, create or reuse a **secret** key (`sb_secret_...`).
4. Create a Vercel token under *Account Settings* → *Tokens*. One token covers both environments.
5. Add the GitHub environment secrets and variable listed in [docs/deployment.md](../../docs/deployment.md#3-configuration).
6. If you created a Vercel project `fda-<env>` by hand, delete it, so Terraform can create it. One the pipeline created is already in Terraform's state; leave it.

## Adopt the existing Supabase project

The Supabase projects predate these roots, so each root imports its project with an `import` block keyed by `supabase_project_ref` in `terraform.tfvars`. Nothing is run by hand: the first CI apply imports the project, and the block is a no-op from then on. See [docs/deployment.md](../../docs/deployment.md#5-adopting-the-existing-projects).

Set `supabase_project_ref` in `<env>/terraform.tfvars` to the ref from the project's dashboard URL, `supabase.com/dashboard/project/<ref>`.

## Plan locally

With the same values the pipeline uses:

```bash
ENV=test
export AWS_ENDPOINT_URL_S3="https://<project_ref>.storage.supabase.co/storage/v1/s3"
export AWS_ACCESS_KEY_ID="<S3 access key ID>" AWS_SECRET_ACCESS_KEY="<S3 secret access key>"
export SUPABASE_ACCESS_TOKEN="..." VERCEL_API_TOKEN="..."
export TF_VAR_supabase_db_password="..." TF_VAR_llm_reader_db_password="..."
export TF_VAR_supabase_secret="..." TF_VAR_google_api_key="..."
terraform -chdir=iac/vercel-supabase/$ENV init -input=false
terraform -chdir=iac/vercel-supabase/$ENV plan
```

On the first run the plan shows `1 to import` for the Supabase project, plus an in-place update of its `database_password`, which the API never returns. Do not run `apply` locally while a deploy is running: the state has no lock.

## Further reading

[docs/deployment.md](../../docs/deployment.md) — configuration, the state backend, how the existing projects are adopted, and the pipeline.
