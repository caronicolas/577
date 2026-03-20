output "endpoint" {
  value     = scaleway_rdb_instance.main.endpoint_ip
  sensitive = true
}

output "connection_url" {
  value = format(
    "postgresql+asyncpg://%s:%s@%s:%s/%s",
    var.db_user,
    var.db_password,
    scaleway_rdb_instance.main.endpoint_ip,
    scaleway_rdb_instance.main.endpoint_port,
    var.db_name
  )
  sensitive = true
}
