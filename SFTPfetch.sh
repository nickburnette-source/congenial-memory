#!/bin/bash

set -e

# Create backups dir if needed
mkdir -p backups

# Prompt for SFTP details (securely)
read -p "SFTP Host: " SFTP_HOST
read -p "SFTP User: " SFTP_USER
read -s -p "SFTP Password: " SFTP_PASS
echo
read -p "Remote .bak Path (e.g., /path/to/backup.bak): " REMOTE_PATH
read -p "Local Filename (e.g., backup.bak): " LOCAL_FILE

# Fetch via SFTP (use sshpass for password auth; install if needed)
if ! command -v sshpass &> /dev/null; then
    sudo apt install -y sshpass
fi

sshpass -p "$SFTP_PASS" sftp $SFTP_USER@$SFTP_HOST << EOF
get $REMOTE_PATH backups/$LOCAL_FILE
EOF

echo ".bak fetched to backups/$LOCAL_FILE"