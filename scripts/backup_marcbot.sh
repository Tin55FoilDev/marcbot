#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="/srv/marcbot"
cd "${PROJECT_ROOT}"

APP_DIR="${PROJECT_ROOT}/app"
BACKUP_DIR="${PROJECT_ROOT}/backups"
TMP_DIR="${PROJECT_ROOT}/tmp"
LATEST_FILE="${BACKUP_DIR}/latest-backup.txt"

RETENTION_DAYS="${MARC_BACKUP_RETENTION_DAYS:-14}"

timestamp="$(date +%Y%m%d-%H%M%S)"
backup_name="marcbot-backup-${timestamp}.tar.gz"
backup_path="${BACKUP_DIR}/${backup_name}"
sha_path="${backup_path}.sha256"
tmp_path="${TMP_DIR}/${backup_name}.tmp"

mkdir -p "${BACKUP_DIR}" "${TMP_DIR}"

if [[ ! -d "${PROJECT_ROOT}" ]]; then
  echo "ERROR [MBOT-BACKUP-001]: project root not found: ${PROJECT_ROOT}" >&2
  exit 1
fi

if [[ ! -d "${APP_DIR}" ]]; then
  echo "ERROR [MBOT-BACKUP-002]: app directory not found: ${APP_DIR}" >&2
  exit 1
fi

if [[ ! -w "${BACKUP_DIR}" ]]; then
  echo "ERROR [MBOT-BACKUP-003]: backup directory is not writable: ${BACKUP_DIR}" >&2
  exit 1
fi

if [[ ! -w "${TMP_DIR}" ]]; then
  echo "ERROR [MBOT-BACKUP-004]: tmp directory is not writable: ${TMP_DIR}" >&2
  exit 1
fi

rm -f "${tmp_path}"

tar \
  --create \
  --gzip \
  --file "${tmp_path}" \
  --directory "/" \
  --exclude="srv/marcbot/app/.venv" \
  --exclude="srv/marcbot/backups" \
  --exclude="srv/marcbot/tmp" \
  "srv/marcbot/app" \
  "srv/marcbot/config" \
  "srv/marcbot/state" \
  "srv/marcbot/workspace" \
  "srv/marcbot/logs" \
  "srv/marcbot/memory"

mv "${tmp_path}" "${backup_path}"

sha256sum "${backup_path}" > "${sha_path}"

archive_size_bytes="$(stat -c '%s' "${backup_path}")"
created_epoch="$(date +%s)"
created_iso="$(date --iso-8601=seconds)"

cat > "${LATEST_FILE}" <<EOF
name=${backup_name}
path=${backup_path}
sha256_path=${sha_path}
created_iso=${created_iso}
created_epoch=${created_epoch}
size_bytes=${archive_size_bytes}
retention_days=${RETENTION_DAYS}
EOF

chmod 600 "${backup_path}" "${sha_path}" "${LATEST_FILE}"

# Remove old MarcBot app-level backups and checksum files.
# Keep this conservative: only files matching the exact script naming pattern.
find "${BACKUP_DIR}" \
  -maxdepth 1 \
  -type f \
  \( -name 'marcbot-backup-*.tar.gz' -o -name 'marcbot-backup-*.tar.gz.sha256' \) \
  -mtime "+${RETENTION_DAYS}" \
  -print \
  -delete

(
  cd "${APP_DIR}"
  "${APP_DIR}/.venv/bin/python" -m marcbot memory event add \
    --type backup_completed \
    --project marcbot-operations \
    --summary "MarcBot app-level backup completed." \
    --source marcbot_backup_script \
    --confidence high \
    --details "The MarcBot app-level backup script created a tar.gz archive, checksum file, and latest-backup marker." \
    --verification "Archive, checksum, and latest-backup marker were written successfully before this event was recorded." \
    --follow-up "Use /backup_status, /backup_list, or python -m marcbot memory search backup to inspect backup history." \
    --related-file "${backup_path}" \
    --related-file "${sha_path}" \
    --related-file "${LATEST_FILE}" \
    --related-command "systemctl start marcbot-backup.service"
)

echo "MarcBot backup created:"
echo "  archive: ${backup_path}"
echo "  sha256:  ${sha_path}"
echo "  latest:  ${LATEST_FILE}"
echo "  size:    ${archive_size_bytes} bytes"
echo "  memory:  backup_completed event recorded"
