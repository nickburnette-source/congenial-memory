#!/bin/bash

set -e  # Exit on error

echo "Starting full setup on DGX Spark..."

# Step 1: Update OS and install basics
sudo apt update && sudo apt upgrade -y
# sudo apt install -y curl git openssh-client  # For SFTP (sshpass if needed for non-key auth)

# Step 2: Install Docker + NVIDIA Container Toolkit (idempotent)
if ! command -v docker &> /dev/null; then
    sudo apt install -y docker.io nvidia-container-toolkit
    sudo systemctl start docker && sudo systemctl enable docker
    sudo nvidia-ctk runtime configure --runtime=docker
    sudo systemctl restart docker
fi

# Step 4: Start Docker Compose (builds if needed)
docker compose up -d --build

echo "Setup complete! Access UI at http://$(hostname -I | awk '{print $1}'):8501"
echo "MSSQL ready at port 1433 (use readonly_user for queries)."
echo "IMPORTANT: Create .env file for docker compose!"