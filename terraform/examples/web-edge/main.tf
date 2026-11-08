# Example: VPC + security group that only accepts HTTPS from the Cloudflare edge.

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project   = "cloud-ip-ranges-infra"
      ManagedBy = "terraform"
    }
  }
}

module "vpc" {
  source = "../../modules/vpc"

  name     = var.name
  az_count = 2
}

module "cloudflare_v4" {
  source = "../../modules/provider-allowlist"

  name       = "${var.name}-cloudflare-v4"
  cidrs_file = "${path.module}/../../../data/cloudflare/cidrs.txt"
}

resource "aws_security_group" "web" {
  name        = "${var.name}-web"
  description = "HTTPS only from Cloudflare edge"
  vpc_id      = module.vpc.vpc_id

  ingress {
    description     = "HTTPS from Cloudflare"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    prefix_list_ids = [module.cloudflare_v4.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}
