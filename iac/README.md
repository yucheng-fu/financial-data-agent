# Setting up infrastructure

Bicep (`bootstrap/`) creates the resource group, the Terraform state storage account and the service principal's role assignments. Terraform (`environments/`, `modules/`) creates everything else: the container registry, the app's identity, the `filings` container, the container app and the Supabase Postgres project.

Run the bootstrap once per environment, locally. CI runs Terraform on every push to `main`.

## 1. Manual steps (Azure portal and GitHub)

1. Create a service principal `sp-github-fda-<env>` in App registrations.
2. Set up a federated credential for GitHub Actions using the entity type "Environment".
3. Create the environment in GitHub with `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID` as secrets.
4. Create a Supabase organization, then mint a Personal Access Token under *Account preferences* → *Access Tokens*.
5. Add `SUPABASE_ACCESS_TOKEN` and `SUPABASE_DB_PASSWORD` to each GitHub environment.
6. Put the Supabase organization slug into `supabase_organization_id` in `environments/test/terraform.tfvars` and `environments/prod/terraform.tfvars`.

Both Supabase secrets have constraints that will fail the deploy if ignored — see [docs/infrastructure.md](../docs/infrastructure.md).

## 2. Bootstrap with Bicep

Run from the repository root, signed in as Owner or User Access Administrator on the subscription.

```powershell
az login
az account set --subscription <AZURE_SUBSCRIPTION_ID>

az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.ManagedIdentity --wait

$env:PRINCIPAL_ID = az ad sp show --id <AZURE_CLIENT_ID> --query id -o tsv
$env:ADMIN_PRINCIPAL_ID = az ad signed-in-user show --query id -o tsv

az deployment sub what-if --name bootstrap-test --location swedencentral --parameters iac/bootstrap/test.bicepparam

az deployment sub create --name bootstrap-test --location swedencentral --parameters iac/bootstrap/test.bicepparam
```

Repeat with `prod.bicepparam` and `--name bootstrap-prod` for production.

## 3. Terraform

CI runs `init`, `plan` and `apply` per environment. To run it locally, from `environments/<env>/`:

```powershell
terraform init
terraform plan
```

Reading the state locally requires a blob data role, which the bootstrap grants if you set `ADMIN_PRINCIPAL_ID`.

## Further reading

[docs/infrastructure.md](../docs/infrastructure.md) — the Bicep/Terraform split, the Supabase secret constraints, resource naming, the deployment pipeline, and which tool owns the image and the schema.
