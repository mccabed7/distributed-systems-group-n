#!/usr/bin/env bash

set -e

echo "Waiting for Kafka ($KAFKA_BOOTSTRAP_SERVER) to become available..."

until kafka-topics.sh \
  --bootstrap-server $KAFKA_BOOTSTRAP_SERVER \
  --list > /dev/null 2>&1
do
  sleep 2
done

echo "Kafka ready. Creating topics..."

kafka-topics.sh \
  --create --if-not-exists \
  --topic notifications \
  --bootstrap-server $KAFKA_BOOTSTRAP_SERVER \
  --partitions 3 \
  --replication-factor 1

echo "Topic initialisation complete."
