FROM python:3.9-slim

WORKDIR /app

# Install lean CLI and dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Lean CLI
RUN pip install lean

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY mcp_server.py .

EXPOSE 8000

CMD ["python", "mcp_server.py"]