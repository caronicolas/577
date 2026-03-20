# ─── Bootstrap — création du bucket S3 pour le state Terraform ───────────────
#
# Ce module s'exécute UNE SEULE FOIS, en local, avant le reste de l'infra.
# Il crée le bucket Object Storage qui sert de backend au projet principal.
#
# Procédure :
#   cd infra/bootstrap
#   terraform init
#   terraform apply -var-file=../../infra/terraform.tfvars   (ou passer les vars)
#
# Après cette étape, revenir dans infra/ et lancer :
#   terraform init -backend-config=backend.tfvars

terraform {
  required_version = ">= 1.9"

  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.46"
    }
  }

  # Backend local intentionnel : ce module ne peut pas utiliser le backend
  # distant qu'il est justement chargé de créer.
  backend "local" {}
}

provider "scaleway" {
  access_key = var.scw_access_key
  secret_key = var.scw_secret_key
  project_id = var.scw_project_id
  region     = "fr-par"
  zone       = "fr-par-1"
}

resource "scaleway_object_bucket" "tfstate" {
  name       = "an577-tfstate"
  region     = "fr-par"
  project_id = var.scw_project_id

  versioning {
    enabled = true
  }

  tags = {
    project = "577"
    managed = "terraform-bootstrap"
  }
}
