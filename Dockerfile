FROM python:3.12-slim

# Install minimal system deps
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 1. Copy only requirements first → pip install gets cached unless deps change
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2. Create data dir for persistence
RUN mkdir -p data

# 3. Copy the actual app code last (changes most often)
COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]