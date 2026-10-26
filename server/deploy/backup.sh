#!/bin/sh
set -eu
umask 077
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# No silent service shutdown. Python command requires --maintenance-confirmed.
exec python3 "$HERE/../tools/backup.py" "$@"
