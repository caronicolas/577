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

variable "bsky_identifier" {
  type      = string
  sensitive = true
}

variable "bsky_app_password" {
  type      = string
  sensitive = true
}

variable "zip_hashes" {
  description = "SHA-256 de chaque ZIP de fonction, calculé depuis le module racine"
  type        = map(string)
  default     = {}
}

