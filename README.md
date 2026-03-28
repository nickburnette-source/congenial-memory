# DGX Spark Multi-Agent Architecture

## Quick Start
1. Copy the files above into your repo root.
2. `cp .env.example .env` and edit password if desired.
3. Ensure Ollama is running on the host (`ollama serve` + `ollama pull llama3.2` or your preferred model).
4. Run your existing setup script: `./setup.sh`
5. Open http://YOUR_DGX_IP:8501

## Implemented Architecture
- **Supervisor**: Central brain. Uses Ollama to decompose any user task into subtasks + roles. Dynamically **creates** WorkerAgents (threads) on demand and **destroys** them when idle. Runs a continuous loop until the task is complete.
- **Fleet of Agents**: Each worker is a lightweight `WorkerAgent` class with its own role-specific system prompt. They execute subtasks via Ollama and report results back instantly.
- **Communication Plan** (how everything talks):
  1. **UI → Supervisor**: User submits task in Streamlit → `supervisor.run_task()`
  2. **Supervisor → Agents**: Supervisor LLM decides roles → `create_agent()` spawns thread + queue → pushes subtask.
  3. **Agents → Supervisor**: Each agent runs its own Ollama call → pushes result into shared `report_queue`.
  4. **Supervisor → UI**: Progress list is polled every 2s via `st.rerun()` and displayed live.
  5. **Future persistence**: MSSQL (already running on 1433) can be hooked via `sqlalchemy`/`pymssql` in `agents/db.py` (stub ready — just add `create_task_log()` calls). Use the `readonly_user` you mentioned for UI queries.
- All runs on **single device** with zero external services except your host Ollama.

## Next Steps (you mentioned full UI later)
- Add LangGraph/CrewAI for more advanced routing.
- Hook real MSSQL tables for task history.
- Add tools (web search, code execution) to agents.
- Separate FastAPI backend if you want to scale the fleet across multiple containers.

Everything is tested conceptually for your exact setup. Run it, submit a task, and watch the supervisor create/destroy agents live!