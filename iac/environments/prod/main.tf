data "azurerm_resource_group" "this" {
  name = var.resource_group_name
}

module "container_app" {
  source = "../../modules/container-app"

  name                = var.container_app_name
  resource_group_name = data.azurerm_resource_group.this.name
  location            = var.location
  env                 = var.env
  image               = var.container_image
  target_port         = var.container_target_port
}
