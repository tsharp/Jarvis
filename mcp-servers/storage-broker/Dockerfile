FROM python:3.11-slim

WORKDIR /app

# util-linux → lsblk, findmnt; procps → df; coreutils → realpath
RUN apt-get update && apt-get install -y --no-install-recommends \
    util-linux \
    procps \
    e2fsprogs \
    xfsprogs \
    dosfstools \
    btrfs-progs \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY storage_broker_mcp ./storage_broker_mcp
COPY docker-entrypoint.sh /usr/local/bin/storage-broker-entrypoint

# Data directory (mounted as named volume in production)
RUN mkdir -p /app/data \
    && chmod +x /usr/local/bin/storage-broker-entrypoint

ENV LOG_LEVEL=INFO
ENV STORAGE_BROKER_DB=/app/data/storage_broker.db
ENV STORAGE_POLICY_PATH=/app/data/storage_policy.json
ENV STORAGE_MANAGED_BASES=""
ENV ADMIN_API_URL=http://jarvis-admin-api:8200

EXPOSE 8089

ENTRYPOINT ["storage-broker-entrypoint"]
CMD ["python", "-m", "storage_broker_mcp.server"]
