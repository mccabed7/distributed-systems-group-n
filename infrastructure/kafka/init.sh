#!/usr/bin/env bash

set -e

echo "Creating topics..."

/opt/kafka/bin/kafka-topics.sh \
  --create --if-not-exists \
  --topic notifications \
  --bootstrap-server $KAFKA_BOOTSTRAP_SERVER \
  --partitions 3 \
  --replication-factor 3

echo "Topic initialisation complete."
