variable "scw_access_key" {
  type      = string
  sensitive = true
}

variable "scw_secret_key" {
  type      = string
  sensitive = true
}

variable "scw_project_id" {
  type = string
}

variable "db_staging_password" {
  description = "Mot de passe de l'utilisateur an577_staging"
  type        = string
  sensitive   = true
}

variable "database_url_staging" {
  description = "URL de connexion PostgreSQL complète pour le container staging"
  type        = string
  sensitive   = true
}

variable "api_image_tag" {
  description = "Tag Docker de l'image API (ex: sha court du commit)"
  type        = string
  default     = "latest"
}
