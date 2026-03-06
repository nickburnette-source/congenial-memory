# congenial-memory
Maximally self contained agent hierarchy reporting to supervisory llm for defect hunting.

# Multi-Agent NL-to-SQL Setup for DGX Spark

This repo automates a containerized multi-agent system (CrewAI + Ollama) for querying a sensitive MS SQL database via natural language. Runs fully offline on NVIDIA DGX Spark.

## Prerequisites
- Fresh DGX Spark with Ubuntu (e.g., 22.04+).
- SSH access.
- SFTP credentials for the remote file share (host, user, pass, path to .bak).
- Git installed (`sudo apt install git` if needed).

## Quick Start
1. Clone: `git clone <repo-url> && cd multi-agent-db-repo`
2. Make executable: `chmod +x setup.sh sftp_fetch.sh`
3. Run: `./setup.sh`
   - This updates OS, installs Docker/NVIDIA toolkit, fetches .bak via SFTP (prompts for creds), and starts Docker Compose.
4. Access UI: `http://<spark-ip>:8501` (chat with DB via agents).

## Customization
- Edit `docker-compose.yml` env vars for secrets (e.g., MSSQL_PASSWORD).
- For future UI: Extend `app.py` (e.g., add Streamlit tabs for data defect hunting).

## Troubleshooting
- Logs: `docker compose logs -f`
- MSSQL Restore: Check mssql container logs for errors.