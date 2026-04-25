FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    util-linux \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (Docker layer caching)
COPY adapters/admin-api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy shared code from project root
COPY core /app/core
COPY maintenance /app/maintenance
COPY utils /app/utils
COPY mcp /app/mcp
COPY config /app/config
COPY CIM-skill_rag /app/CIM-skill_rag
COPY intelligence_modules /app/intelligence_modules

# Copy lobechat adapter (needed for chat endpoint)
COPY adapters/lobechat /app/adapters/lobechat
COPY adapters/runtime-hardware /app/adapters/runtime-hardware
COPY adapters/base.py /app/adapters/base.py
COPY adapters/__init__.py /app/adapters/__init__.py

# Copy application last
# Container Commander module
COPY container_commander /app/container_commander
COPY adapters/admin-api/commander_api /app/commander_api
COPY adapters/admin-api/docker-entrypoint.sh /usr/local/bin/jarvis-admin-api-entrypoint
COPY adapters/admin-api/*.py ./

RUN mkdir -p /app/data \
    && chmod +x /usr/local/bin/jarvis-admin-api-entrypoint

EXPOSE 8200

ENTRYPOINT ["jarvis-admin-api-entrypoint"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8200", "--log-level", "info"]
