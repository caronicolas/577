variable "project_id" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "assemblee_api_base_url" {
  type = string
}

variable "gouv_api_base_url" {
  type = string
}

variable "scrutins_zip_key" {
  description = "Clé de l'objet ZIP de la fonction ingest-scrutins dans le bucket"
  type        = string
  default     = "ingest-scrutins.zip"
}

variable "deputes_zip_key" {
  description = "Clé de l'objet ZIP de la fonction ingest-deputes dans le bucket"
  type        = string
  default     = "ingest-deputes.zip"
}
