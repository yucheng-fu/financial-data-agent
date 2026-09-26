# Setting up infrastructure with Terraform
Terraform requires a backend to store the Terraform state file, so some initial setup is required before you can use Terraform to manage your IaC. 

## Terraform for Azure
1. Create a Service principal `sp-github-fda-<env>` in App registrations
2. Setup a federated credential for Github Actions using the entity type "Environment"
3. Create resource group `rg-fda-<env>`
4. In the resource group, create a storage account `stfda<env>` with the container `tfstate`
5. On the subscription level, assign the role "Contributor" to the Service principal
6. On storage acccount level, assign the role "Storage Blob Data Contributor" to the Service principal
7. On the subscription, register the resource providers `Microsoft.App` and `Microsoft.OperationalInsights`.
8. Create the environment in Github and `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, and `AZURE_SUBSCRIPTION_ID` as secrets. 