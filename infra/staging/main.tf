terraform {
  required_version = ">= 1.9"
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.46"
    }
  }
  backend "s3" {
    bucket                      = "an577-tfstate"
    key                         = "staging.tfstate"
    region                      = "fr-par"
    endpoint                    = "https://s3.fr-par.scw.cloud"
    skip_credentials_validation = true
    skip_region_validation      = true
    skip_requesting_account_id  = true
  }
}

provider "scaleway" {
  access_key = var.scw_access_key
  secret_key = var.scw_secret_key
  project_id = var.scw_project_id
  region     = "fr-par"
  zone       = "fr-par-1"
}

# ---------------------------------------------------------------------------
# Base de données staging — nouvelle DB sur l'instance RDB prod (pas de
# nouvelle instance → pas de surcoût)
# ---------------------------------------------------------------------------

data "scaleway_rdb_instance" "prod" {
  name = "an577-db"
}

resource "scaleway_rdb_database" "staging" {
  instance_id = data.scaleway_rdb_instance.prod.id
  name        = "an577_staging"
}

resource "scaleway_rdb_user" "staging" {
  instance_id = data.scaleway_rdb_instance.prod.id
  name        = "an577_staging"
  password    = var.db_staging_password
  is_admin    = false
}

resource "scaleway_rdb_privilege" "staging" {
  instance_id   = data.scaleway_rdb_instance.prod.id
  user_name     = scaleway_rdb_user.staging.name
  database_name = scaleway_rdb_database.staging.name
  permission    = "all"

  depends_on = [scaleway_rdb_database.staging, scaleway_rdb_user.staging]
}

# ---------------------------------------------------------------------------
# Container API staging — dans le namespace existant
# ---------------------------------------------------------------------------

data "scaleway_container_namespace" "main" {
  name = "an577-api"
}

data "scaleway_registry_namespace" "main" {
  name = "an577"
}

resource "scaleway_container" "staging" {
  name           = "api-staging"
  namespace_id   = data.scaleway_container_namespace.main.id
  registry_image = "${data.scaleway_registry_namespace.main.endpoint}/api:${var.api_image_tag}"
  port           = 8000
  cpu_limit      = 280
  memory_limit   = 512
  min_scale      = 0
  max_scale      = 2
  timeout        = 30
  privacy        = "public"
  deploy         = true

  environment_variables = {
    API_HOST = "0.0.0.0"
    API_PORT = "8000"
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url_staging
  }
}

# ---------------------------------------------------------------------------
# Frontend staging — bucket S3 dédié
# ---------------------------------------------------------------------------

resource "scaleway_object_bucket" "staging_frontend" {
  name          = "test.les577.fr"
  project_id    = var.scw_project_id
  region        = "fr-par"
  force_destroy = true

  tags = {
    project = "an577"
    env     = "staging"
  }
}

resource "scaleway_object_bucket_website_configuration" "staging_frontend" {
  bucket = scaleway_object_bucket.staging_frontend.name
  region = "fr-par"

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "scaleway_object_bucket_policy" "staging_frontend_public" {
  bucket = scaleway_object_bucket.staging_frontend.name
  region = "fr-par"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${scaleway_object_bucket.staging_frontend.name}/*"
      }
    ]
  })
}
