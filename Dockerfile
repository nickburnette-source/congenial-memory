FROM nvcr.io/nvidia/pytorch:24.01-py3

WORKDIR /app

# Install ODBC drivers for MSSQL
RUN apt-get update && apt-get install -y gnupg2 curl unixodbc-dev \
    && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
    && curl https://packages.microsoft.com/config/ubuntu/22.04/prod.list > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql17 mssql-tools18

# Python deps (replace mysql-connector with pyodbc)
RUN pip install --no-cache-dir crewai langchain langchain-community pyodbc streamlit pandas matplotlib plotly

COPY multi_agent_db.py app.py ./

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]