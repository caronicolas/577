output "host" {
  value     = try(scaleway_rdb_instance.main.load_balancer[0].ip, null)
  sensitive = true
}

output "port" {
  value = try(scaleway_rdb_instance.main.load_balancer[0].port, null)
}

output "name" {
  value = var.db_name
}

output "user" {
  value = var.db_user
}

output "password" {
  value     = var.db_password
  sensitive = true
}

output "connection_url" {
  value = try(
    format(
      "postgresql+asyncpg://%s:%s@%s:%s/%s",
      var.db_user,
      var.db_password,
      scaleway_rdb_instance.main.load_balancer[0].ip,
      scaleway_rdb_instance.main.load_balancer[0].port,
      var.db_name
    ),
    null
  )
  sensitive = true
}
