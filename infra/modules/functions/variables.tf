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
