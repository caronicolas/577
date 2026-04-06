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

resource "scaleway_registry_namespace" "main" {
  name       = "an577"
  project_id = var.project_id
  region     = "fr-par"
  is_public  = false
}

resource "scaleway_container" "api" {
  name           = "api"
  namespace_id   = scaleway_container_namespace.main.id
  registry_image = "${scaleway_registry_namespace.main.endpoint}/api:${var.image_tag}"
  port           = 8000
  cpu_limit      = 280
  memory_limit   = 512
  min_scale      = 0
  max_scale      = 5
  timeout        = 30
  privacy        = "public"
  deploy         = true

  environment_variables = {
    API_HOST = "0.0.0.0"
    API_PORT = "8000"
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}

resource "scaleway_container_domain" "api" {
  container_id = scaleway_container.api.id
  hostname     = "api.les577.fr"
}
