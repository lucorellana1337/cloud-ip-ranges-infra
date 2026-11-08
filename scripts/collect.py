#!/usr/bin/env python3
"""Collect public IP ranges published by cloud/CDN providers.

Usage:
    python scripts/collect.py <provider>   # snapshot one provider
    python scripts/collect.py report       # rebuild REPORT.md

For each provider it writes:
    data/<provider>/cidrs.txt     sorted CIDR list (git diff shows real changes)
    data/<provider>/latest.json   summary of the latest snapshot
    data/<provider>/history.csv   one row per run (also records failures)
"""
from __future__ import annotations

import csv
import hashlib
import ipaddress
import json
import sys
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = {"User-Agent": "cloud-ip-ranges-infra/1.0 (+github actions)"}
NL = "\n"


def fetch_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def is_cidr(value) -> bool:
    try:
        ipaddress.ip_network(str(value), strict=False)
        return True
    except ValueError:
        return False


# Each parser returns a list of (cidr, group) tuples.
def aws():
    d = fetch_json("https://ip-ranges.amazonaws.com/ip-ranges.json")
    return [(p["ip_prefix"], p["region"]) for p in d["prefixes"]] + [
        (p["ipv6_prefix"], p["region"]) for p in d["ipv6_prefixes"]
    ]


def gcp():
    d = fetch_json("https://www.gstatic.com/ipranges/cloud.json")
    return [(p.get("ipv4Prefix") or p["ipv6Prefix"], p.get("scope", "global")) for p in d["prefixes"]]


def cloudflare():
    r = fetch_json("https://api.cloudflare.com/client/v4/ips")["result"]
    return [(c, "edge") for c in r["ipv4_cidrs"] + r["ipv6_cidrs"]]


def github():
    d = fetch_json("https://api.github.com/meta")  # also has ssh keys / domains: keep CIDRs only
    return [(c, k) for k, v in d.items() if isinstance(v, list) for c in v if is_cidr(c)]


def oracle():
    d = fetch_json("https://docs.oracle.com/en-us/iaas/tools/public_ip_ranges.json")
    return [(c["cidr"], r["region"]) for r in d["regions"] for c in r["cidrs"]]


def fastly():
    d = fetch_json("https://api.fastly.com/public-ip-list")
    return [(c, "edge") for c in d["addresses"] + d.get("ipv6_addresses", [])]


PROVIDERS = {"aws": aws, "gcp": gcp, "cloudflare": cloudflare, "github": github, "oracle": oracle, "fastly": fastly}
FIELDS = ["timestamp", "status", "ipv4_prefixes", "ipv6_prefixes", "ipv4_addresses", "added", "removed", "sha256"]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline=NL)


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def snapshot(name: str) -> None:
    out = DATA / name
    out.mkdir(parents=True, exist_ok=True)
    cidr_file, latest_file, hist_file = out / "cidrs.txt", out / "latest.json", out / "history.csv"
    row = {k: "" for k in FIELDS} | {"timestamp": now()}

    try:
        nets = {}
        for cidr, group in PROVIDERS[name]():
            nets.setdefault(ipaddress.ip_network(cidr.strip(), strict=False), group)
        v4 = sorted(n for n in nets if n.version == 4)
        v6 = sorted(n for n in nets if n.version == 6)
        cidrs = [str(n) for n in v4 + v6]

        old = set(read(cidr_file).split()) if cidr_file.exists() else set()
        new = set(cidrs)
        write(cidr_file, NL.join(cidrs) + NL)

        summary = {
            "provider": name,
            "checked_at": row["timestamp"],
            "status": "ok",
            "ipv4_prefixes": len(v4),
            "ipv6_prefixes": len(v6),
            "ipv4_addresses": sum(n.num_addresses for n in v4),
            "added": len(new - old) if old else 0,
            "removed": len(old - new) if old else 0,
            "sha256": hashlib.sha256(NL.join(cidrs).encode()).hexdigest()[:16],
            "top_groups": Counter(nets.values()).most_common(5),
        }
        row |= {k: summary[k] for k in FIELDS if k in summary}
    except Exception as exc:  # keep a record of outages / API changes
        print(f"::warning::{name}: {exc}")
        summary = json.loads(read(latest_file)) if latest_file.exists() else {"provider": name}
        summary |= {"status": f"error: {type(exc).__name__}", "checked_at": row["timestamp"]}
        row["status"] = "error"

    write(latest_file, json.dumps(summary, indent=2) + NL)
    new_file = not hist_file.exists()
    with hist_file.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, lineterminator=NL)
        if new_file:
            w.writeheader()
        w.writerow(row)
    print(f"{name}: {row['status']} v4={row['ipv4_prefixes']} v6={row['ipv6_prefixes']}")


def human(n) -> str:
    if not isinstance(n, int):
        return "-"
    if n < 1000:
        return str(n)
    for unit in ("K", "M", "B", "T"):
        n /= 1000
        if n < 1000:
            break
    return f"{n:.1f}{unit}"


def report() -> None:
    lines = [
        "# Cloud IP Ranges Report",
        "",
        f"_Last updated: {now()} (generated by `scripts/collect.py report`)_",
        "",
        "| Provider | Status | IPv4 prefixes | IPv6 prefixes | IPv4 addresses | Change last run | Checked at |",
        "|---|---|---:|---:|---:|---|---|",
    ]
    tops = []
    for name in PROVIDERS:
        f = DATA / name / "latest.json"
        if not f.exists():
            continue
        s = json.loads(read(f))
        lines.append(
            f"| {name} | {s.get('status', '-')} | {s.get('ipv4_prefixes', '-')} | {s.get('ipv6_prefixes', '-')} "
            f"| {human(s.get('ipv4_addresses'))} | +{s.get('added', 0)} / -{s.get('removed', 0)} "
            f"| {s.get('checked_at', '-')} |"
        )
        if s.get("top_groups"):
            tops.append(f"- **{name}**: " + ", ".join(f"{g} ({c})" for g, c in s["top_groups"]))
    lines += ["", "## Top groups (region / service) by prefix count", "", *tops]
    write(ROOT / "REPORT.md", NL.join(lines) + NL)
    print("REPORT.md updated")


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else ""
    if arg == "report":
        report()
    elif arg in PROVIDERS:
        snapshot(arg)
    else:
        sys.exit(f"usage: collect.py [{'|'.join(PROVIDERS)}|report]")
