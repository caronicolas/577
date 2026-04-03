output "api_url" {
  description = "URL publique du container API staging"
  value       = scaleway_container.staging.domain_name
}

output "frontend_bucket" {
  description = "Nom du bucket frontend staging"
  value       = scaleway_object_bucket.staging_frontend.name
}

output "frontend_website_endpoint" {
  description = "Endpoint website du bucket staging (à pointer via CNAME pour test.les577.fr)"
  value       = "an577-frontend-staging.s3-website.fr-par.scw.cloud"
}
