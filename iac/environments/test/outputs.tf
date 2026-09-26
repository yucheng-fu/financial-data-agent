output "resource_group_name" {
  value = data.azurerm_resource_group.this.name
}

output "container_registry_name" {
  value = module.container_registry.name
}

output "container_registry_login_server" {
  value = module.container_registry.login_server
}

output "container_app_name" {
  value = module.container_app.name
}

output "container_app_fqdn" {
  value = module.container_app.fqdn
}

output "filings_container_name" {
  value = azurerm_storage_container.filings.name
}
