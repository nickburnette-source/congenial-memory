from crewai import Agent, Task, Crew, Process
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_ollama import ChatOllama
from langchain.tools import tool
import os

# Local LLM (uses env var for flexibility)
llm = ChatOllama(model="llama3.1:70b", base_url=os.getenv('OLLAMA_HOST'))

# MSSQL Connection (read-only user via env vars)
db_uri = f"mssql+pyodbc://{os.getenv('MSSQL_USER')}:{os.getenv('MSSQL_PASSWORD')}@{os.getenv('MSSQL_HOST')}/{os.getenv('MSSQL_DB')}?driver=ODBC+Driver+17+for+SQL+Server&encrypt=true&trustServerCertificate=false"
db = SQLDatabase.from_uri(db_uri)
sql_toolkit = SQLDatabaseToolkit(db=db, llm=llm)

# Custom Tool: Safe SQL Executor (blocks DML, supports T-SQL)
@tool
def execute_safe_sql(query: str) -> str:
    """Executes read-only SQL (T-SQL) and returns results as string."""
    forbidden_cmds = ["DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "CREATE", "EXEC", "TRUNCATE"]
    if any(cmd in query.upper() for cmd in forbidden_cmds):
        return "DML or DDL operations not allowed."
    try:
        return str(db.run(query))
    except Exception as e:
        return f"Execution error: {str(e)}"

# Agents (roles specialized for MSSQL/T-SQL)
supervisor = Agent(
    role="Supervisor",
    goal="Orchestrate team to answer user queries accurately and safely.",
    backstory="You are a project manager coordinating experts for DB queries.",
    llm=llm,
    verbose=True
)

sql_engineer = Agent(
    role="SQL DB Engineer",
    goal="Generate and execute optimal T-SQL for the query using schema knowledge.",
    backstory="You are an expert MS SQL engineer using T-SQL syntax (e.g., TOP for limits). Use tools to inspect schema and query DB.",
    tools=sql_toolkit.get_tools() + [execute_safe_sql],
    llm=llm,
    verbose=True
)

data_scientist = Agent(
    role="Data Scientist",
    goal="Analyze SQL results, compute stats, and generate visualizations.",
    backstory="You use Python/pandas for insights and plots from data.",
    tools=[tool(lambda code: exec(code) and "Executed")],  # Simplified REPL; use full sandbox in prod
    llm=llm,
    verbose=True
)

auditor = Agent(
    role="Auditor",
    goal="Review SQL for security, efficiency, and compliance before execution.",
    backstory="You check for injections, limits, and read-only ops in T-SQL.",
    llm=llm,
    verbose=True
)

# Tasks (dynamic based on user query; sequential flow)
def create_tasks(user_query):
    task1 = Task(
        description=f"Generate T-SQL for: {user_query}",
        agent=sql_engineer,
        expected_output="Valid T-SQL query"
    )
    task2 = Task(
        description="Audit the generated SQL for safety.",
        agent=auditor,
        expected_output="Approved SQL or revisions",
        context=[task1]
    )
    task3 = Task(
        description="Execute approved SQL and analyze results.",
        agent=data_scientist,
        expected_output="Insights and viz code",
        context=[task2]
    )
    return [task1, task2, task3]

# Run the Crew (entry point for UI)
def run_crew(user_query):
    tasks = create_tasks(user_query)
    crew = Crew(
        agents=[supervisor, sql_engineer, data_scientist, auditor],
        tasks=tasks,
        process=Process.sequential,
        manager_agent=supervisor
    )
    return crew.kickoff()

# Future Extension Example: Add DataQualityAgent for defect hunting
# data_quality_analyst = Agent(
#     role="Data Quality Analyst",
#     goal="Hunt for data defects (duplicates, nulls, anomalies) and suggest corrections.",
#     backstory="You run SQL checks and Python stats to identify issues.",
#     tools=[execute_safe_sql, tool for pandas analysis],
#     llm=llm
# )
# Then add to create_tasks for research workflows.