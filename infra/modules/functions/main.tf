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

# ---------------------------------------------------------------------------
# Fonctions d'ingestion
# BUILD_HASH dans environment_variables déclenche une mise à jour in-place
# (re-upload du ZIP) quand le contenu du ZIP change, sans détruire la fonction.
# ---------------------------------------------------------------------------

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
  deploy       = true

  environment_variables = {
    ASSEMBLEE_API_BASE_URL = var.assemblee_api_base_url
    BUILD_HASH             = lookup(var.zip_hashes, "scrutins", "")
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

resource "scaleway_function_cron" "scrutins_session" {
  function_id = scaleway_function.ingest_scrutins.id
  schedule    = "0,30 13-21 * * 1-6" # Toutes les 30 min, 13h-21h UTC (15h-23h Paris), lun-sam
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
  deploy       = true

  environment_variables = {
    ASSEMBLEE_API_BASE_URL = var.assemblee_api_base_url
    BUILD_HASH             = lookup(var.zip_hashes, "organes", "")
  }

  secret_environment_variables = {
    DATABASE_URL = var.database_url
  }
}

resource "scaleway_function_cron" "organes_weekly" {
  function_id = scaleway_function.ingest_organes.id
  schedule    = "0 4 * * *" # Quotidien 04:00 UTC
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
  deploy       = true

  environment_variables = {
    ASSEMBLEE_API_BASE_URL = var.assemblee_api_base_url
    GOUV_API_BASE_URL      = var.gouv_api_base_url
    BUILD_HASH             = lookup(var.zip_hashes, "deputes", "")
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
  deploy       = true

  environment_variables = {
    BUILD_HASH = lookup(var.zip_hashes, "agenda", "")
  }

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
  deploy       = true

  environment_variables = {
    ASSEMBLEE_API_BASE_URL = var.assemblee_api_base_url
    BUILD_HASH             = lookup(var.zip_hashes, "amendements", "")
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

# ---------------------------------------------------------------------------
# Fonctions Bluesky
# ---------------------------------------------------------------------------

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
  deploy       = true

  environment_variables = {
    BUILD_HASH = lookup(var.zip_hashes, "post_agenda", "")
  }

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

resource "scaleway_function" "post_commissions_bluesky" {
  name         = "post-commissions-bluesky"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "post_commissions.handle"
  privacy      = "private"
  timeout      = 300
  max_scale    = 1
  memory_limit = 128
  zip_file     = "functions/post_commissions.zip"
  deploy       = true

  environment_variables = {
    BUILD_HASH = lookup(var.zip_hashes, "post_commissions", "")
  }

  secret_environment_variables = {
    DATABASE_URL      = var.database_url
    BSKY_IDENTIFIER   = var.bsky_identifier
    BSKY_APP_PASSWORD = var.bsky_app_password
  }
}

resource "scaleway_function_cron" "post_commissions_bluesky_quarter" {
  function_id = scaleway_function.post_commissions_bluesky.id
  schedule    = "*/15 8-22 * * *" # Toutes les 15 min, 8h-22h UTC (10h-00h Paris), tous les jours
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
  deploy       = true

  environment_variables = {
    GOUV_API_BASE_URL = var.gouv_api_base_url
    BUILD_HASH        = lookup(var.zip_hashes, "datan", "")
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

resource "scaleway_function" "post_scrutins_bluesky" {
  name         = "post-scrutins-bluesky"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "post_scrutins.handle"
  privacy      = "private"
  timeout      = 60
  max_scale    = 1
  memory_limit = 128
  zip_file     = "functions/post_scrutins.zip"
  deploy       = true

  environment_variables = {
    BUILD_HASH = lookup(var.zip_hashes, "post_scrutins", "")
  }

  secret_environment_variables = {
    DATABASE_URL      = var.database_url
    BSKY_IDENTIFIER   = var.bsky_identifier
    BSKY_APP_PASSWORD = var.bsky_app_password
  }
}

resource "scaleway_function_cron" "post_scrutins_bluesky_session" {
  function_id = scaleway_function.post_scrutins_bluesky.id
  schedule    = "10,40 13-21 * * 1-6" # 10 min après l'ingestion, 13h-21h UTC, lun-sam
  args        = jsonencode({})
}

resource "scaleway_function_cron" "post_scrutins_bluesky_morning" {
  function_id = scaleway_function.post_scrutins_bluesky.id
  schedule    = "10 6 * * *" # 06:10 UTC — rattrapage après ingestion matinale
  args        = jsonencode({})
}

resource "scaleway_function" "post_stats_hebdo_bluesky" {
  name         = "post-stats-hebdo-bluesky"
  namespace_id = scaleway_function_namespace.main.id
  runtime      = "python312"
  handler      = "post_stats_hebdo.handle"
  privacy      = "private"
  timeout      = 60
  max_scale    = 1
  memory_limit = 128
  zip_file     = "functions/post_stats_hebdo.zip"
  deploy       = true

  environment_variables = {
    BUILD_HASH = lookup(var.zip_hashes, "post_stats_hebdo", "")
  }

  secret_environment_variables = {
    DATABASE_URL      = var.database_url
    BSKY_IDENTIFIER   = var.bsky_identifier
    BSKY_APP_PASSWORD = var.bsky_app_password
  }
}

resource "scaleway_function_cron" "post_stats_hebdo_weekly" {
  function_id = scaleway_function.post_stats_hebdo_bluesky.id
  schedule    = "0 8 * * 1" # Lundi 08:00 UTC — stats de la semaine écoulée
  args        = jsonencode({})
}
