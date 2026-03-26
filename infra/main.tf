terraform {
  required_version = ">= 1.9"
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.46"
    }
  }
  backend "s3" {
    # Scaleway Object Storage comme backend Terraform
    # Configurer via : terraform init -backend-config=backend.tfvars
    bucket                      = "an577-tfstate"
    key                         = "terraform.tfstate"
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

module "database" {
  source      = "./modules/database"
  project_id  = var.scw_project_id
  db_name     = var.db_name
  db_user     = var.db_user
  db_password = var.db_password
}

module "containers" {
  source       = "./modules/containers"
  project_id   = var.scw_project_id
  database_url = module.database.connection_url
  image_tag    = var.api_image_tag
}

module "functions" {
  source                 = "./modules/functions"
  project_id             = var.scw_project_id
  database_url           = module.database.connection_url
  assemblee_api_base_url = var.assemblee_api_base_url
  gouv_api_base_url      = var.gouv_api_base_url
}

module "frontend" {
  source     = "./modules/frontend"
  project_id = var.scw_project_id
}
