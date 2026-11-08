#!/usr/bin/env bash
# Daily job: snapshot a random subset of providers (one commit each) and refresh the report.
# Produces between 3 and 7 commits per run.
set -euo pipefail
cd "$(dirname "$0")/.."

providers=(aws gcp cloudflare github oracle fastly)
total=$(( RANDOM % 5 + 3 ))            # 3..7 commits in total
mapfile -t picked < <(printf '%s\n' "${providers[@]}" | shuf -n $(( total - 1 )))
today=$(date -u +%F)

for p in "${picked[@]}"; do
  python scripts/collect.py "$p"
  git add "data/$p"
  status=$(python -c "import json;print(json.load(open('data/$p/latest.json'))['status'])")
  if [[ "$status" == ok ]]; then
    msg="data($p): snapshot $today"
  else
    msg="data($p): record fetch failure $today"
  fi
  git diff --cached --quiet || git commit -q -m "$msg"
done

python scripts/collect.py report
git add REPORT.md
git diff --cached --quiet || git commit -q -m "docs(report): refresh summary $today"

echo "commits today: $(git rev-list --count --since=midnight HEAD)"
