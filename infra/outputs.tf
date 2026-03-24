output "api_url" {
  description = "Endpoint du Serverless Container API (FastAPI)"
  value       = "https://${module.containers.api_url}"
}

output "frontend_url" {
  description = "Endpoint du frontend (Scaleway Object Storage)"
  value       = module.frontend.website_url
}

output "db_endpoint" {
  description = "Endpoint PostgreSQL managé"
  value       = module.database.host
  sensitive   = true
}
