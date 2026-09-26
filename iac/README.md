# Setting up infrastructure

Infrastructure is split across two tools, because Terraform cannot create the storage account that holds its own state file:

- **Bicep** (`bootstrap/`) owns the pre-Terraform layer: the resource group, the state storage account with its `tfstate` container, and the role assignments for the service principal. Run once per environment, locally.
- **Terraform** (`environments/`, `modules/`) owns everything else — the container registry, the user assigned identity the app runs as, its role assignments, the `filings` blob container, and the container app with its environment and log analytics workspace. Run by CI on every push to `main`.

This is why `environments/<env>/main.tf` reads the resource group as a `data` source instead of creating it: Bicep already made it. The storage account is read the same way, because the `filings` container is added to the account Bicep created for the state file.

Terraform does not own the container image. It creates the container app on a public placeholder image and then ignores the image field (`lifecycle.ignore_changes` in `modules/container-app`); the pipeline builds the real image and points the app at it with `az containerapp update`. See "Who owns the image" below.

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
az provider register --namespace Microsoft.ContainerRegistry --wait
az provider register --namespace Microsoft.ManagedIdentity --wait

$env:PRINCIPAL_ID = az ad sp show --id <AZURE_CLIENT_ID> --query id -o tsv
$env:ADMIN_PRINCIPAL_ID = az ad signed-in-user show --query id -o tsv

az deployment sub what-if --name bootstrap-test --location swedencentral --parameters iac/bootstrap/test.bicepparam

az deployment sub create --name bootstrap-test --location swedencentral --parameters iac/bootstrap/test.bicepparam
```

Repeat with `prod.bicepparam` and `--name bootstrap-prod` for production.

Notes:

- The bootstrap grants the service principal **Role Based Access Control Administrator** on the resource group (`modules/app-rbac.bicep`). Terraform needs it to create the `AcrPull` and `Storage Blob Data Contributor` assignments for the container app's identity, which Contributor alone cannot do. If you bootstrapped an environment before this module existed, re-run the deployment for that environment — otherwise `terraform apply` fails with `AuthorizationFailed` on the role assignments.
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

## 4. Who owns the image

Terraform and the pipeline deliberately own different halves of the container app:

| | Terraform | Pipeline (`az`) |
| --- | --- | --- |
| Container app, ingress, scaling, env vars | yes | no |
| Registry, identity, role assignments, `filings` container | yes | no |
| Container image tag | only at creation | yes, every push |

`modules/container-app` declares `lifecycle { ignore_changes = [template[0].container[0].image] }`, so after the app exists Terraform stops tracking the image and the pipeline's `az containerapp update --image <registry>/<image>:<sha>` is the only thing that moves it. Each push produces a new revision tagged with the commit SHA.

The `container_image` in `terraform.tfvars` is therefore a **public placeholder** (`mcr.microsoft.com/k8se/quickstart:latest`) that only matters on the very first apply of an environment. It is public on purpose: the app cannot pull from the registry until its `AcrPull` assignment exists, so creating it on a private image would deadlock. This mirrors Microsoft's documented flow for identity-based pulls — create on a public image, then update to the private one.

One consequence, expected and harmless: on the first apply of a new environment the app runs the placeholder, which listens on port 80 while ingress targets 8000, so that first revision is unhealthy. The `Deploy app` job that follows replaces it within a minute.

The pipeline runs these as four jobs. `Deploy iac (test)` runs first; `Deploy app (test)` and `Deploy iac (prod)` both fan out from it and run in parallel, and `Deploy app (prod)` follows the prod iac job:

```text
checks ── iac (test) ─┬─ app (test)
                      └─ iac (prod) ── app (prod)
```

Each iac job publishes its registry, app and FQDN names as job outputs, which the matching app job consumes; the app jobs need no Terraform state access of their own. What holds prod back is the `prod` GitHub environment's approval, not the test smoke check — the two branches are independent once test's infrastructure applies cleanly.

The pull identity is **user assigned** rather than system assigned. With a system assigned identity, the role assignment's `principal_id` depends on the container app, so the app can never `depends_on` the grant — a dependency cycle. A user assigned identity is created first, granted `AcrPull`, and only then attached, so the grant always exists before anything tries to pull.

### Naming

| Resource | Pattern | test |
| --- | --- | --- |
| Resource group | `rg-fda-<env>` | `rg-fda-test` |
| State + filings storage | `stfda<env>` | `stfdatest` |
| Container registry | `crfda<env>` | `crfdatest` |
| Container app | `ca-fda-<env>` | `ca-fda-test` |
| App identity | `id-ca-fda-<env>` | `id-ca-fda-test` |

Storage account and registry names are globally unique across Azure, so `stfda<env>` and `crfda<env>` may be taken in another tenant. Change `storage_account_name` / `container_registry_name` in `terraform.tfvars` (and the matching `.bicepparam`) if a create fails on name availability.
