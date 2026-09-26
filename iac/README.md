# Setting up infrastructure

Infrastructure is split across two tools, because Terraform cannot create the storage account that holds its own state file:

- **Bicep** (`bootstrap/`) owns the pre-Terraform layer: the resource group, the state storage account with its `tfstate` container, and the role assignments for the service principal. Run once per environment, locally.
- **Terraform** (`environments/`, `modules/`) owns everything else — the container app, its environment and log analytics workspace. Run by CI on every push to `main`.

This is why `environments/<env>/main.tf` reads the resource group as a `data` source instead of creating it: Bicep already made it.

## 1. Manual steps (Azure portal and GitHub)

These involve Entra ID objects and GitHub settings, which are not expressible in Bicep.

1. Create a service principal `sp-github-fda-<env>` in App registrations.
2. Set up a federated credential for GitHub Actions using the entity type "Environment".
3. Create the environment in GitHub with `AZURE_CLIENT_ID`, `AZURE_TENANT_ID` and `AZURE_SUBSCRIPTION_ID` as secrets.

## 2. Bootstrap with Bicep

Run from the repository root, signed in with an account that can create role assignments on the subscription (Owner or User Access Administrator). The service principal cannot do this itself — an identity cannot grant itself Contributor.

```powershell
az login
az account set --subscription <AZURE_SUBSCRIPTION_ID>

az provider register --namespace Microsoft.App --wait
az provider register --namespace Microsoft.OperationalInsights --wait

$env:PRINCIPAL_ID = az ad sp show --id <AZURE_CLIENT_ID> --query id -o tsv
$env:ADMIN_PRINCIPAL_ID = az ad signed-in-user show --query id -o tsv

az deployment sub what-if --name bootstrap-test --location swedencentral --parameters iac/bootstrap/test.bicepparam

az deployment sub create --name bootstrap-test --location swedencentral --parameters iac/bootstrap/test.bicepparam
```

Repeat with `prod.bicepparam` and `--name bootstrap-prod` for production.

Notes:

- `PRINCIPAL_ID` is the service principal's **object ID**, not the client ID. The `az ad sp show --id <client-id>` call above converts one into the other, so there is nothing to copy by hand.
- `ADMIN_PRINCIPAL_ID` is your own user object ID. It grants you Storage Blob Data Owner across the subscription, so you can browse the state container in the portal and run Terraform locally. It is optional — leave it unset and the assignment is skipped.
- `--template-file` is omitted on purpose: `az` resolves it from the `using` directive in the `.bicepparam` file (requires az >= 2.53).
- The deployment is idempotent. Role assignment names are derived with `guid()`, so re-running it reports no changes rather than failing.
- Provider registration is a one-off per subscription, not per environment.

If a role assignment for the same principal, role and scope was already created by hand, the deployment fails with `RoleAssignmentExists`. Azure compares principal/role/scope, not the assignment's name, so Bicep's deterministic name does not match the portal's random one. Delete the manual assignment and re-run, after which Bicep owns it:

```powershell
az role assignment delete --assignee <object-id> --role "<role name>" --scope "/subscriptions/<AZURE_SUBSCRIPTION_ID>"
```

### Why the storage account is configured this way

`allowSharedKeyAccess: false` means the account has no usable access keys, so Terraform authenticates to the backend with Entra ID (`use_azuread_auth = true` in `backend.tf`) via its Storage Blob Data Contributor assignment. Access keys would otherwise be two long-lived secrets granting full access to the state file, which holds every resource attribute in plaintext.

A consequence: Owner and Contributor grant no blob data access, so browsing the container needs a data-plane role. That is what `ADMIN_PRINCIPAL_ID` is for. In the portal's container view, set **Authentication method** to "Microsoft Entra user account".

`isHnsEnabled: true` enables the hierarchical namespace. It can only be set at creation time — an account that already exists without it has to be deleted and recreated, which means migrating any state file it holds. Storage Blob Data **Owner** rather than Contributor is used for the admin grant because only Owner can manage POSIX ACLs, which exist on hierarchical-namespace accounts.

## 3. Terraform

CI runs `init`, `plan` and `apply` per environment — see `.github/workflows/azure-deployment-pipelines.yml`. To run it locally, from `environments/<env>/`:

```powershell
terraform init
terraform plan
```

Reading the state locally requires a blob data role, which the bootstrap grants if you set `ADMIN_PRINCIPAL_ID`.
