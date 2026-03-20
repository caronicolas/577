terraform {
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.46"
    }
  }
}

resource "scaleway_container_namespace" "main" {
  name       = "an577-api"
  project_id = var.project_id
  region     = "fr-par"
}

resource "scaleway_container" "api" {
  name           = "api"
  namespace_id   = scaleway_container_namespace.main.id
  registry_image = "rg.fr-par.scw.cloud/an577/api:${var.image_tag}"
  port           = 8000
  cpu_limit      = 560
  memory_limit   = 256
  min_scale      = 0
  max_scale      = 5
  timeout        = 30
  privacy        = "public"

  environment_variables = {
    API_HOST = "0.0.0.0"
    API_PORT = "8000"
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}
