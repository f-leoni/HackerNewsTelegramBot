#!/usr/bin/env bash
# le-deploy-bookmark.sh
# Certbot deploy-hook per applicare gruppo/permessi ai certificati Let's Encrypt
# e riavviare (opzionalmente) il servizio dell'app bookmarks.
#
# Usage: certbot --deploy-hook /etc/letsencrypt/le-deploy-bookmark.sh
# Certbot sets environment variables like RENEWED_LINEAGE and RENEWED_DOMAINS.
# If you call the script manually, you may pass the domain as the first arg.

set -euo pipefail
IFS=$'\n\t'

# Configurabili dall'ambiente (es. export BOOKMARK_SERVICE=myapp.service)
BOOKMARK_SERVICE=${BOOKMARK_SERVICE:-bookmark.service}
CERT_GROUP=${CERT_GROUP:-ssl-cert}
DRY_RUN=${DRY_RUN:-}

log() {
  echo "[le-deploy-bookmark] $*"
  logger -t le-deploy-bookmark "$*" || true
}

# Determine the live path and domain
if [[ -n "${RENEWED_LINEAGE:-}" ]]; then
  LIVE_DIR="$RENEWED_LINEAGE"
  DOMAIN_NAME=$(basename "$RENEWED_LINEAGE")
elif [[ $# -ge 1 ]]; then
  DOMAIN_NAME="$1"
  LIVE_DIR="/etc/letsencrypt/live/$DOMAIN_NAME"
else
  log "ERROR: RENEWED_LINEAGE not set and no domain argument provided. Exiting."
  exit 1
fi

ARCH_DIR="/etc/letsencrypt/archive/$DOMAIN_NAME"

log "Applying permissions for domain: $DOMAIN_NAME"
log "Live dir: $LIVE_DIR"
log "Archive dir: $ARCH_DIR"

# Ensure cert group exists (create if missing)
if ! getent group "$CERT_GROUP" >/dev/null; then
  log "Group '$CERT_GROUP' does not exist. Creating it."
  if [[ -x "$(command -v groupadd)" ]]; then
    groupadd --system "$CERT_GROUP" || true
  else
    log "Warning: groupadd not found; cannot create group. Continuing..."
  fi
fi

# Helper to run commands optionally in dry-run
run_cmd() {
  if [[ -n "$DRY_RUN" ]]; then
    log "DRY RUN: $*"
  else
    eval "$@"
  fi
}

# Apply to live symlinks (these are symlinks to archive files)
if [[ -f "$LIVE_DIR/privkey.pem" ]]; then
  run_cmd "chgrp $CERT_GROUP \"$LIVE_DIR/privkey.pem\""
  run_cmd "chmod 640 \"$LIVE_DIR/privkey.pem\""
else
  log "Warning: $LIVE_DIR/privkey.pem not found"
fi

if [[ -f "$LIVE_DIR/fullchain.pem" ]]; then
  run_cmd "chgrp $CERT_GROUP \"$LIVE_DIR/fullchain.pem\""
  run_cmd "chmod 644 \"$LIVE_DIR/fullchain.pem\""
else
  log "Warning: $LIVE_DIR/fullchain.pem not found"
fi

# Apply to real files in archive (robust with -print0 + xargs -0)
if [[ -d "$ARCH_DIR" ]]; then
  # privkey files
  if find "$ARCH_DIR" -type f -name 'privkey*.pem' -print0 | xargs -0 -r echo >/dev/null 2>&1; then
    run_cmd "find \"$ARCH_DIR\" -type f -name 'privkey*.pem' -print0 | xargs -0 -r chgrp $CERT_GROUP"
    run_cmd "find \"$ARCH_DIR\" -type f -name 'privkey*.pem' -print0 | xargs -0 -r chmod 640"
  else
    log "No privkey files found in archive or xargs -r not supported. Trying fallback."
    while IFS= read -r -d '' f; do
      run_cmd "chgrp $CERT_GROUP \"$f\""
      run_cmd "chmod 640 \"$f\""
    done < <(find "$ARCH_DIR" -type f -name 'privkey*.pem' -print0)
  fi

  # fullchain files
  if find "$ARCH_DIR" -type f -name 'fullchain*.pem' -print0 | xargs -0 -r echo >/dev/null 2>&1; then
    run_cmd "find \"$ARCH_DIR\" -type f -name 'fullchain*.pem' -print0 | xargs -0 -r chgrp $CERT_GROUP"
    run_cmd "find \"$ARCH_DIR\" -type f -name 'fullchain*.pem' -print0 | xargs -0 -r chmod 644"
  else
    log "No fullchain files found in archive or xargs -r not supported. Trying fallback."
    while IFS= read -r -d '' f; do
      run_cmd "chgrp $CERT_GROUP \"$f\""
      run_cmd "chmod 644 \"$f\""
    done < <(find "$ARCH_DIR" -type f -name 'fullchain*.pem' -print0)
  fi
else
  log "Warning: archive directory $ARCH_DIR not found"
fi

# Optionally restart the bookmark service if it exists
if [[ -n "$BOOKMARK_SERVICE" ]]; then
  if systemctl list-units --full -all | grep -Fq "$BOOKMARK_SERVICE"; then
    log "Restarting service: $BOOKMARK_SERVICE"
    if [[ -n "$DRY_RUN" ]]; then
      log "DRY RUN: systemctl restart $BOOKMARK_SERVICE"
    else
      systemctl try-restart "$BOOKMARK_SERVICE" || systemctl restart "$BOOKMARK_SERVICE" || true
    fi
  else
    log "Service $BOOKMARK_SERVICE not found; skipping restart"
  fi
fi

log "Done."
exit 0
