#!/bin/sh
set -eu
umask 077
# Run from deploy/. Keep backups encrypted/off-site; never in the GitHub repo.
DEST=${1:?Usage: sh backup.sh /private/backup-directory}
mkdir -p "$DEST"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
docker compose exec -T db pg_dump -U marketplace -Fc marketplace > "$DEST/database-$STAMP.dump"
docker compose exec -T web tar -C /data -czf - media > "$DEST/media-$STAMP.tar.gz"
printf 'Backup written to the specified private directory. Test restoration regularly.
'
