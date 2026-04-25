FROM python:3.11-slim

WORKDIR /app

# Python deps
COPY mcp-servers/system-addons/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# sql-memory CRUD functions (shared library — accessed via SQL_MEMORY_ROOT)
COPY sql-memory/memory_mcp ./sql-memory/memory_mcp

# Application code
COPY mcp-servers/system-addons/system_addons_mcp ./system_addons_mcp
COPY mcp-servers/system-addons/docker-entrypoint.sh /usr/local/bin/system-addons-entrypoint

RUN mkdir -p /app/data \
    && chmod +x /usr/local/bin/system-addons-entrypoint

ENV LOG_LEVEL=INFO
ENV SQL_MEMORY_ROOT=/app/sql-memory
ENV SQL_MEMORY_DB_PATH=/data/memory.db
ENV HOME=/tmp
ENV XDG_DATA_HOME=/tmp/xdg-data

EXPOSE 8090

ENTRYPOINT ["system-addons-entrypoint"]
CMD ["python", "-m", "system_addons_mcp.server"]
