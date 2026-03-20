output "bucket_name" {
  description = "Nom du bucket S3 créé pour le state Terraform"
  value       = scaleway_object_bucket.tfstate.name
}

output "bucket_endpoint" {
  description = "Endpoint S3 à renseigner dans backend.tfvars"
  value       = "https://s3.fr-par.scw.cloud"
}
