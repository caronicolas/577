terraform {
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.46"
    }
  }
}

resource "scaleway_rdb_instance" "main" {
  name           = "an577-db"
  node_type      = "DB-DEV-S"
  engine         = "PostgreSQL-16"
  is_ha_cluster  = false
  disable_backup = false
  user_name      = var.db_user
  password       = var.db_password
  project_id     = var.project_id
  region         = "fr-par"

  tags = ["an577", "production"]
}

resource "scaleway_rdb_database" "main" {
  instance_id = scaleway_rdb_instance.main.id
  name        = var.db_name
}

resource "scaleway_rdb_privilege" "main" {
  instance_id   = scaleway_rdb_instance.main.id
  user_name     = var.db_user
  database_name = var.db_name
  permission    = "all"
}
