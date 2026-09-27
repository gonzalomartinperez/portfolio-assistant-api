#!/usr/bin/env bash
# Operator-only local VPS entry point. No workflow invokes this until separately approved.
set -euo pipefail
if [[ $# -ne 3 || "$1" != '--approved' ]]; then
  echo 'Usage: apply-release.sh --approved release.json /private/compose.env' >&2
  exit 2
fi
manifest_path=$2
compose_env=$3
python3 -m scripts.validate_release_file "$manifest_path"
mapfile -t release_fields < <(python3 - "$manifest_path" <<'PY'
import json, sys
value=json.load(open(sys.argv[1]))
print(value['api']['image'])
print(value['web']['image'])
PY
)
export API_IMAGE="${release_fields[0]}" WEB_IMAGE="${release_fields[1]}"
compose=(docker compose --env-file "$compose_env" -f deploy/compose.yaml)
# A reviewed backup/restore receipt and backward-compatible migration approval
# are release prerequisites. Application rollback never reverses migrations.
"${compose[@]}" pull api web
"${compose[@]}" --profile maintenance run --rm --no-deps migrate
"${compose[@]}" exec -T postgres sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < deploy/runtime-grants.sql
"${compose[@]}" up -d --wait api web
if [[ -n "$("${compose[@]}" --profile edge ps -q proxy)" ]]; then
  "${compose[@]}" --profile edge exec -T proxy nginx -s reload
else
  echo 'External shared ingress must be reloaded by its approved operator before public smoke.' >&2
  exit 3
fi
"${compose[@]}" exec -T api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health/ready', timeout=10)"
python3 -m scripts.deployment_smoke https://assistant.gonzalomartinperez.com
