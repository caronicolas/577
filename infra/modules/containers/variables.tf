variable "project_id" {
  type = string
}

variable "database_url" {
  type      = string
  sensitive = true
}

variable "image_tag" {
  type    = string
  default = "latest"
}
