FROM nvcr.io/nvidia/pytorch:24.01-py3

WORKDIR /app

# Install ODBC drivers for MSSQL (updated for Ubuntu 22.04 per Microsoft docs)
RUN apt-get update && apt-get install -y curl gnupg unixodbc-dev \
    && curl -sSL -O https://packages.microsoft.com/config/ubuntu/22.04/packages-microsoft-prod.deb \
    && dpkg -i packages-microsoft-prod.deb \
    && rm packages-microsoft-prod.deb \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y msodbcsql18 mssql-tools18 \
    && echo 'export PATH="$PATH:/opt/mssql-tools18/bin"' >> ~/.bashrc

# Python deps (pyodbc for MSSQL connectivity)
RUN pip install --no-cache-dir crewai langchain langchain-community langchain-ollama pyodbc streamlit pandas matplotlib plotly

COPY multi_agent_db.py app.py ./

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]