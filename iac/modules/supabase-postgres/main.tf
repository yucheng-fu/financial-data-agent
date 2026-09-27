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
  # The API returns only the project's configured pool mode, so this map has a single
  # entry, keyed "transaction" by default. Indexing by name is therefore not safe.
  # values() is ordered by key, so [0] picks "session" if a future project ever
  # reports both.
  raw_pooler_url = values(data.supabase_pooler.this.url)[0]

  # Supavisor serves both modes on the same host, session on 5432 and transaction on
  # 6543, so rewriting the port is what selects session mode. It is a no-op when the
  # URL is already a session one. Session mode is required because Alembic DDL uses
  # prepared statements, and the pooler is required at all because the direct host is
  # IPv6 only on the free tier while GitHub hosted runners are IPv4 only.
  session_pooler_url = replace(local.raw_pooler_url, ":6543/", ":5432/")

  # SQLAlchemy needs the psycopg dialect named explicitly: given a bare postgresql://
  # it loads psycopg2, which is not a dependency. The API returns postgresql://, but
  # replacing the scheme wholesale rather than matching a literal keeps this correct
  # whichever of postgres:// or postgresql:// it uses. Done before the password is
  # inserted so the password can never affect the split.
  dialect_url = "postgresql+psycopg://${split("://", local.session_pooler_url)[1]}"

  # The Management API redacts the password in the connection string.
  sqlalchemy_url = replace(local.dialect_url, "[YOUR-PASSWORD]", var.database_password)

  database_url = "${local.sqlalchemy_url}?sslmode=require"
}
