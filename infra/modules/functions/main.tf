terraform {
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.46"
    }
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
  handler      = "scrutins.handle"
  privacy      = "private"
  timeout      = 900
  max_scale    = 1
  memory_limit = 1024
  zip_file     = "functions/scrutins.zip"
  zip_hash     = try(filesha256("functions/scrutins.zip"), "")
  deploy       = true

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

resource "scaleway_function" "ingest_organes" {
  name         = "ingest-organes"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "organes.handle"
  privacy      = "private"
  timeout      = 300
  max_scale    = 1
  memory_limit = 256
  zip_file     = "functions/organes.zip"
  zip_hash     = try(filesha256("functions/organes.zip"), "")
  deploy       = true

  environment_variables = {
    ASSEMBLEE_API_BASE_URL = var.assemblee_api_base_url
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}

resource "scaleway_function_cron" "organes_weekly" {
  function_id = scaleway_function.ingest_organes.id
  schedule    = "0 4 * * 0" # Dimanche 04:00 UTC (avant deputes lundi 05:00)
  args        = jsonencode({ type = "organes" })
}

resource "scaleway_function" "ingest_deputes" {
  name         = "ingest-deputes"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "deputes.handle"
  privacy      = "private"
  timeout      = 300
  max_scale    = 1
  memory_limit = 256
  zip_file     = "functions/deputes.zip"
  zip_hash     = try(filesha256("functions/deputes.zip"), "")
  deploy       = true

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

resource "scaleway_function" "ingest_agenda" {
  name         = "ingest-agenda"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "agenda.handle"
  privacy      = "private"
  timeout      = 900
  max_scale    = 1
  memory_limit = 512
  zip_file     = "functions/agenda.zip"
  zip_hash     = try(filesha256("functions/agenda.zip"), "")
  deploy       = true

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}

resource "scaleway_function_cron" "agenda_daily" {
  function_id = scaleway_function.ingest_agenda.id
  schedule    = "0 4 * * *" # 04:00 UTC chaque jour
  args        = jsonencode({ type = "agenda" })
}

resource "scaleway_function" "ingest_amendements" {
  name         = "ingest-amendements"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "amendements.handle"
  privacy      = "private"
  timeout      = 900
  max_scale    = 1
  memory_limit = 1024
  zip_file     = "functions/amendements.zip"
  zip_hash     = try(filesha256("functions/amendements.zip"), "")
  deploy       = true

  environment_variables = {
    ASSEMBLEE_API_BASE_URL = var.assemblee_api_base_url
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}

resource "scaleway_function_cron" "amendements_daily" {
  function_id = scaleway_function.ingest_amendements.id
  schedule    = "0 7 * * *" # 07:00 UTC chaque jour
  args        = jsonencode({ type = "amendements" })
}

resource "scaleway_function" "post_agenda_bluesky" {
  name         = "post-agenda-bluesky"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "post_agenda.handle"
  privacy      = "private"
  timeout      = 60
  max_scale    = 1
  memory_limit = 128
  zip_file     = "functions/post_agenda.zip"
  zip_hash     = try(filesha256("functions/post_agenda.zip"), "")
  deploy       = true

  secret_environment_variables = {
    DATABASE_URL      = var.database_url
    BSKY_IDENTIFIER   = var.bsky_identifier
    BSKY_APP_PASSWORD = var.bsky_app_password
  }
}

resource "scaleway_function_cron" "post_agenda_bluesky_daily" {
  function_id = scaleway_function.post_agenda_bluesky.id
  schedule    = "0 8 * * *" # 08:00 UTC (10h Paris) chaque jour
  args        = jsonencode({})
}

resource "scaleway_function" "ingest_datan" {
  name         = "ingest-datan"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "datan.handle"
  privacy      = "private"
  timeout      = 120
  max_scale    = 1
  memory_limit = 256
  zip_file     = "functions/datan.zip"
  zip_hash     = try(filesha256("functions/datan.zip"), "")
  deploy       = true

  environment_variables = {
    GOUV_API_BASE_URL = var.gouv_api_base_url
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}

resource "scaleway_function_cron" "datan_weekly" {
  function_id = scaleway_function.ingest_datan.id
  schedule    = "0 3 * * 2" # Mardi 03:00 UTC (datasets MAJ hebdo)
  args        = jsonencode({ type = "datan" })
}
