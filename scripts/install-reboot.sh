#!/bin/sh
# Survive a host reboot without sudo.
# Primary: compose `restart: unless-stopped` (Docker starts the containers).
# Extra: @reboot crontab if crontab(1) exists. systemctl --user needs linger (sudo).

set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
LINE="@reboot sleep 20 && cd \"$ROOT\" && docker compose --profile minio up -d"

if command -v crontab >/dev/null 2>&1; then
  tmp=$(mktemp)
  crontab -l 2>/dev/null | grep -v 'docker compose --profile minio up -d' >"$tmp" || true
  echo "$LINE" >>"$tmp"
  crontab "$tmp"
  rm -f "$tmp"
  echo "installed crontab: $LINE"
else
  echo "crontab not available; relying on Docker restart: unless-stopped"
fi
echo "volumes that survive reboot (not make down -v): pgdata-lms coll gold gl archive, minio"
echo "make down wipes those volumes. instance termination destroys them."
