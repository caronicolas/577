output "bucket_name" {
  value = scaleway_object_bucket.frontend.name
}

output "website_url" {
  description = "URL publique du site statique frontend"
  value       = scaleway_object_bucket_website_configuration.frontend.website_endpoint
}
