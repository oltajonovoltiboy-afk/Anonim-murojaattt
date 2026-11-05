#!/usr/bin/env bash
# ===================================================================
# Urganch davlat akademik litseyi — PostgreSQL Avtomatik Zaxira Skripti
# ===================================================================

set -e

BACKUP_DIR="/var/backups/urganch_murojaat"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/murojaat_db_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=14

# Zaxira papkasini yaratish
mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Ma'lumotlar bazasi zaxira nusxasi yaratilmoqda..."

# Docker container orqali PostgreSQL bazasini dump qilish
docker exec -t urganch_murojaat_postgres pg_dump -U murojaat_user -d murojaat_db | gzip > "${BACKUP_FILE}"

echo "[$(date)] Zaxira muvaffaqiyatli saqlandi: ${BACKUP_FILE}"

# 14 kundan oshgan eski nusxalarni o'chirish
find "${BACKUP_DIR}" -type f -name "murojaat_db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] ${RETENTION_DAYS} kundan eski zaxira nusxalari tozalandi."
