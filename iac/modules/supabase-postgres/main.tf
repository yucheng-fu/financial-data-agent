# Required here, not just in the environment, because Terraform would otherwise infer
# the supabase_ prefix as hashicorp/supabase, which does not exist. The environment
# pins the exact version.
terraform {
  required_providers {
    supabase = {
      source  = "supabase/supabase"
      version = ">= 1.11.0"
    }
  }
}

resource "supabase_project" "this" {
  organization_id   = var.organization_id
  name              = var.project_name
  database_password = var.database_password
  region            = var.region
  instance_size     = var.instance_size

  timeouts {
    create = "30m"
  }
}

data "supabase_pooler" "this" {
  project_ref = supabase_project.this.id
}

locals {
  # Supavisor serves session mode on 5432 and transaction mode on 6543 of the same
  # host. Session mode is required because Alembic DDL uses prepared statements, and
  # the pooler is required at all because the direct host is IPv6 only on the free
  # tier while GitHub hosted runners are IPv4 only.
  session_pooler_url = data.supabase_pooler.this.url["session"]

  # psycopg needs the SQLAlchemy dialect prefix rather than the bare postgres://
  # scheme, and the Management API redacts the password in the connection string.
  sqlalchemy_url = replace(
    replace(local.session_pooler_url, "postgres://", "postgresql+psycopg://"),
    "[YOUR-PASSWORD]",
    var.database_password
  )

  database_url = "${local.sqlalchemy_url}?sslmode=require"
}
