# Builds an AWS managed prefix list from a CIDR file produced by scripts/collect.py
# (e.g. data/cloudflare/cidrs.txt), so firewall rules follow the published provider ranges.

locals {
  lines   = [for l in split("\n", file(var.cidrs_file)) : trimspace(l) if trimspace(l) != ""]
  is_ipv6 = var.address_family == "IPv6"
  cidrs   = [for c in local.lines : c if local.is_ipv6 == strcontains(c, ":")]
}

resource "aws_ec2_managed_prefix_list" "this" {
  name           = var.name
  address_family = var.address_family
  max_entries    = max(length(local.cidrs), 1)
  tags           = var.tags

  dynamic "entry" {
    for_each = local.cidrs
    content {
      cidr        = entry.value
      description = var.name
    }
  }
}
