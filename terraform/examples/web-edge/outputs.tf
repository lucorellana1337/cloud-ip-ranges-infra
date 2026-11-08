output "vpc_id" {
  value = module.vpc.vpc_id
}

output "security_group_id" {
  value = aws_security_group.web.id
}

output "cloudflare_prefixes" {
  value = module.cloudflare_v4.cidr_count
}
