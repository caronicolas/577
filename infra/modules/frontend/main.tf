terraform {
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.46"
    }
  }
}

resource "scaleway_object_bucket" "frontend" {
  name       = "an577-frontend"
  project_id = var.project_id
  region     = "fr-par"

  tags = {
    project = "an577"
    env     = "production"
  }
}

resource "scaleway_object_bucket_website_configuration" "frontend" {
  bucket = scaleway_object_bucket.frontend.name
  region = "fr-par"

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

resource "scaleway_object_bucket_policy" "frontend_public" {
  bucket = scaleway_object_bucket.frontend.name
  region = "fr-par"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = "${scaleway_object_bucket.frontend.name}/*"
      }
    ]
  })
}
