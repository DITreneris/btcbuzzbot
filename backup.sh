#!/bin/bash
# BTCBuzzBot Database Backup Script

# Configuration
DB_PATH="/path/to/btcbuzzbot/btcbuzzbot.db"
BACKUP_DIR="/path/to/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=7
LOG_FILE="/var/log/btcbuzzbot/backup.log"
NOTIFICATION_EMAIL="admin@example.com"

# Timestamp for logs
LOG_TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")

# Check if the script is running as root or with appropriate permissions
if [[ $EUID -ne 0 ]] && [[ ! -w $(dirname "$LOG_FILE") ]]; then
    echo "[$LOG_TIMESTAMP] ERROR: This script must be run as root or with write access to $(dirname "$LOG_FILE")" >&2
    exit 1
fi

# Ensure backup directory exists
mkdir -p $BACKUP_DIR
if [ ! -d "$BACKUP_DIR" ]; then
    echo "[$LOG_TIMESTAMP] ERROR: Could not create backup directory $BACKUP_DIR" | tee -a $LOG_FILE
    exit 1
fi

# Log start of backup
echo "[$LOG_TIMESTAMP] Starting database backup" | tee -a $LOG_FILE

# Check if database file exists
if [ ! -f "$DB_PATH" ]; then
    echo "[$LOG_TIMESTAMP] ERROR: Database file not found at $DB_PATH" | tee -a $LOG_FILE
    echo "Database file not found at $DB_PATH" | mail -s "BTCBuzzBot Backup Failed" $NOTIFICATION_EMAIL
    exit 1
fi

# Create backup filename
BACKUP_FILE="$BACKUP_DIR/btcbuzzbot_$TIMESTAMP.db"

# Backup SQLite database
echo "[$LOG_TIMESTAMP] Creating backup at $BACKUP_FILE" | tee -a $LOG_FILE
sqlite3 $DB_PATH ".backup $BACKUP_FILE"
BACKUP_STATUS=$?

if [ $BACKUP_STATUS -ne 0 ]; then
    echo "[$LOG_TIMESTAMP] ERROR: Backup failed with status $BACKUP_STATUS" | tee -a $LOG_FILE
    echo "Database backup failed with status $BACKUP_STATUS" | mail -s "BTCBuzzBot Backup Failed" $NOTIFICATION_EMAIL
    exit 1
fi

# Compress backup
echo "[$LOG_TIMESTAMP] Compressing backup" | tee -a $LOG_FILE
gzip "$BACKUP_FILE"
COMPRESS_STATUS=$?

if [ $COMPRESS_STATUS -ne 0 ]; then
    echo "[$LOG_TIMESTAMP] ERROR: Compression failed with status $COMPRESS_STATUS" | tee -a $LOG_FILE
    echo "Database compression failed with status $COMPRESS_STATUS" | mail -s "BTCBuzzBot Backup Failed" $NOTIFICATION_EMAIL
    exit 1
fi

# Delete old backups
echo "[$LOG_TIMESTAMP] Cleaning up old backups (older than $RETENTION_DAYS days)" | tee -a $LOG_FILE
find $BACKUP_DIR -name "btcbuzzbot_*.db.gz" -type f -mtime +$RETENTION_DAYS -delete

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE.gz" | cut -f1)

# Log success
echo "[$LOG_TIMESTAMP] Backup completed successfully (Size: $BACKUP_SIZE)" | tee -a $LOG_FILE

# Optional: Copy backup to remote location
if [ ! -z "$REMOTE_BACKUP_PATH" ]; then
    echo "[$LOG_TIMESTAMP] Copying backup to remote location" | tee -a $LOG_FILE
    scp "$BACKUP_FILE.gz" $REMOTE_BACKUP_PATH
    SCP_STATUS=$?
    
    if [ $SCP_STATUS -ne 0 ]; then
        echo "[$LOG_TIMESTAMP] WARNING: Remote backup copy failed with status $SCP_STATUS" | tee -a $LOG_FILE
    else
        echo "[$LOG_TIMESTAMP] Remote backup completed successfully" | tee -a $LOG_FILE
    fi
fi

# List current backups
BACKUP_COUNT=$(find $BACKUP_DIR -name "btcbuzzbot_*.db.gz" -type f | wc -l)
TOTAL_SIZE=$(du -sh $BACKUP_DIR | cut -f1)

echo "[$LOG_TIMESTAMP] Summary: $BACKUP_COUNT backups in $BACKUP_DIR (Total size: $TOTAL_SIZE)" | tee -a $LOG_FILE

exit 0 