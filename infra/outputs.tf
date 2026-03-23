output "api_url" {
  description = "URL publique de l'API FastAPI"
  value       = module.containers.api_url
}

output "db_endpoint" {
  description = "Endpoint PostgreSQL managé"
  value       = module.database.host
  sensitive   = true
}
