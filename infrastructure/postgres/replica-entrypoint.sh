#!/bin/bash
set -e

DATA_DIR="/var/lib/postgresql/data"

if [ ! -f "$DATA_DIR/PG_VERSION" ]; then
    echo "Running pg_basebackup from primary..."
    until PGPASSWORD=replicator pg_basebackup \
        -h postgres \
        -U replicator \
        -D "$DATA_DIR" \
        -Xs -P -R \
        --checkpoint=fast; do
        echo "Primary not ready, retrying in 2s..."
        sleep 2
    done
    echo "Base backup complete."
fi

exec /usr/local/bin/docker-entrypoint.sh postgres
