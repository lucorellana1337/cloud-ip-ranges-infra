output "id" {
  value = aws_ec2_managed_prefix_list.this.id
}

output "cidr_count" {
  value = length(local.cidrs)
}
