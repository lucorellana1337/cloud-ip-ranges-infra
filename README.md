# cloud-ip-ranges-infra

Tracks the public IP ranges published by major cloud and CDN providers, and turns them
into **Terraform-managed firewall allowlists** on AWS.

[![daily-ip-snapshot](../../actions/workflows/daily-snapshot.yml/badge.svg)](../../actions/workflows/daily-snapshot.yml)
[![terraform](../../actions/workflows/terraform.yml/badge.svg)](../../actions/workflows/terraform.yml)

## Why

Allowlists such as "only accept HTTPS from Cloudflare" or "only allow GitHub Actions runners"
break silently when a provider adds or removes ranges. This repo:

1. **Collects** the official range feeds every day (GitHub Actions, scheduled).
2. **Versions** them in git, so every change is a reviewable diff (`data/<provider>/cidrs.txt`).
3. **Applies** them with Terraform as AWS managed prefix lists referenced by security groups.

## Providers

| Provider   | Source feed |
|------------|-------------|
| AWS        | `ip-ranges.amazonaws.com/ip-ranges.json` |
| GCP        | `gstatic.com/ipranges/cloud.json` |
| Cloudflare | `api.cloudflare.com/client/v4/ips` |
| GitHub     | `api.github.com/meta` |
| Oracle OCI | `docs.oracle.com/.../public_ip_ranges.json` |
| Fastly     | `api.fastly.com/public-ip-list` |

Latest numbers: see [REPORT.md](REPORT.md).

## Layout

```
scripts/collect.py              # fetch + normalize + diff a provider feed, build REPORT.md
scripts/run_daily.sh            # daily job, one commit per provider snapshot
data/<provider>/cidrs.txt       # sorted CIDRs (source of truth for Terraform)
data/<provider>/history.csv     # time series: prefix counts, added/removed, status
terraform/modules/vpc           # VPC, public/private subnets across AZs, optional NAT
terraform/modules/provider-allowlist  # AWS managed prefix list from a CIDR file
terraform/examples/web-edge     # VPC + SG that only accepts 443 from Cloudflare
```

## Usage

```bash
python scripts/collect.py cloudflare   # snapshot one provider
python scripts/collect.py report       # rebuild REPORT.md

cd terraform/examples/web-edge
terraform init && terraform plan
```

## CI/CD

- `daily-ip-snapshot.yml`: scheduled job (cron) that snapshots providers and commits the changes.
- `terraform.yml`: `terraform fmt -check` + `validate` for every module on each change.

## Stack

Terraform · AWS (VPC, subnets, NAT, managed prefix lists, security groups) · GitHub Actions · Python
