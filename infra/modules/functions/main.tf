terraform {
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.46"
    }
  }
}

# Bucket Object Storage pour stocker les ZIPs des fonctions
resource "scaleway_object_bucket" "functions_zips" {
  name       = "an577-functions-zips"
  project_id = var.project_id
  region     = "fr-par"

  tags = {
    project = "an577"
    env     = "production"
  }
}

resource "scaleway_function_namespace" "main" {
  name       = "an577-ingestion"
  project_id = var.project_id
  region     = "fr-par"
}

resource "scaleway_function" "ingest_scrutins" {
  name         = "ingest-scrutins"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "handler.handle"
  privacy      = "private"
  timeout      = 300
  max_scale    = 1
  memory_limit = 256

  s3_zip {
    bucket = scaleway_object_bucket.functions_zips.name
    key    = var.scrutins_zip_key
    region = "fr-par"
  }

  environment_variables = {
    ASSEMBLEE_API_BASE_URL = var.assemblee_api_base_url
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}

resource "scaleway_function_cron" "scrutins_daily" {
  function_id = scaleway_function.ingest_scrutins.id
  schedule    = "0 6 * * *" # 06:00 UTC chaque jour
  args        = jsonencode({ type = "scrutins" })
}

resource "scaleway_function" "ingest_deputes" {
  name         = "ingest-deputes"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "handler.handle"
  privacy      = "private"
  timeout      = 300
  max_scale    = 1
  memory_limit = 256

  s3_zip {
    bucket = scaleway_object_bucket.functions_zips.name
    key    = var.deputes_zip_key
    region = "fr-par"
  }

  environment_variables = {
    ASSEMBLEE_API_BASE_URL = var.assemblee_api_base_url
    GOUV_API_BASE_URL      = var.gouv_api_base_url
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}

resource "scaleway_function_cron" "deputes_weekly" {
  function_id = scaleway_function.ingest_deputes.id
  schedule    = "0 5 * * 1" # Lundi 05:00 UTC
  args        = jsonencode({ type = "deputes" })
}
