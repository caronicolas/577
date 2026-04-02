variable "scw_access_key" {
  description = "Scaleway Access Key"
  type        = string
  sensitive   = true
}

variable "scw_secret_key" {
  description = "Scaleway Secret Key"
  type        = string
  sensitive   = true
}

variable "scw_project_id" {
  description = "Scaleway Project ID"
  type        = string
}

variable "db_name" {
  description = "Nom de la base PostgreSQL"
  type        = string
  default     = "an577"
}

variable "db_user" {
  description = "Utilisateur PostgreSQL"
  type        = string
  default     = "an577"
}

variable "db_password" {
  description = "Mot de passe PostgreSQL"
  type        = string
  sensitive   = true
}

variable "api_image_tag" {
  description = "Tag Docker de l'image API FastAPI"
  type        = string
  default     = "latest"
}

variable "assemblee_api_base_url" {
  description = "URL de base API Assemblée Nationale"
  type        = string
  default     = "https://data.assemblee-nationale.fr/api"
}

variable "gouv_api_base_url" {
  description = "URL de base data.gouv.fr"
  type        = string
  default     = "https://www.data.gouv.fr/api/1"
}

variable "bsky_identifier" {
  description = "Handle ou DID du compte Bluesky (ex : les577.fr)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "bsky_app_password" {
  description = "App password Bluesky"
  type        = string
  sensitive   = true
  default     = ""
}
