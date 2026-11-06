#!/bin/sh
set -eu
deploy_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
exec docker compose --env-file "$deploy_dir/.env" -f "$deploy_dir/compose.yml" \
    run --rm --no-deps maintenance backup "${WARFRONT_BACKUP_DB:-/data/warfront.db}" --output-dir /backups
