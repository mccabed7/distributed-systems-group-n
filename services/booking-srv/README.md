# booking-srv

Central coordinator service for the distributed traffic booking system. Accepts booking requests, persists them, and asynchronously validates road capacity before notifying users of the outcome.

## Responsibilities

1. Accept a booking request and immediately return `202 Accepted` with a `PENDING` status
2. Deduplicate retries using the `X-Request-Id` idempotency key
3. Optionally resolve road IDs from a journey service (if `JOURNEY_SRV_URL` is configured)
4. In the background, atomically reserve road capacity via `road-srv`
5. Transition the booking to `SUCCESSFUL` or `FAILED`
6. Publish an outcome event to Kafka for the notification service to consume

## API

### `POST /bookings`

Create a new booking. Requires the `x-user-id` header (injected by gateway-srv after authentication).

**Request headers:**

| Header | Required | Description |
|---|---|---|
| `X-User-ID` | Yes | Injected by gateway-srv after authentication |
| `X-Request-Id` | No | Client-supplied idempotency key. If a booking already exists for this key and user, it is returned without creating a new one. |

**Request body:**
```json
{
  "start_location": "Dublin",
  "end_location": "Cork",
  "booking_date": "2026-05-01",
  "country_code": "IE",
  "road_ids": [1, 2, 3]
}
```

- `road_ids` is optional. If omitted and `JOURNEY_SRV_URL` is set, road IDs are resolved via journey-srv. If omitted and no journey service is configured, the booking is marked `SUCCESSFUL` immediately.

**Response `202 Accepted`:**
```json
{
  "id": "8708aad5-0bde-4d5a-ab79-0da307a05025",
  "status": "PENDING"
}
```

On an idempotent retry (same `X-Request-Id` and `X-User-ID`), the same response is returned with the current status of the original booking (`PENDING`, `SUCCESSFUL`, or `FAILED`).

---

### `GET /bookings/{booking_id}`

Retrieve a booking by ID. Poll this endpoint to check for the final status after receiving a `PENDING` response.

**Response `200 OK`:**
```json
{
  "id": "8708aad5-0bde-4d5a-ab79-0da307a05025",
  "user_id": "user-123",
  "status": "SUCCESSFUL",
  "start_location": "Dublin",
  "end_location": "Cork",
  "booking_date": "2026-05-01",
  "country_code": "IE",
  "road_ids": [1, 2, 3],
  "created_at": "2026-05-01T10:00:00+00:00"
}
```

Possible `status` values: `PENDING`, `SUCCESSFUL`, `FAILED`.

---

### `GET /health`

Returns `200 OK` if the service and database are healthy.

```json
{"status": "ok"}
```

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://booking:booking@localhost:5432/booking` | PostgreSQL connection string |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker address |
| `KAFKA_NOTIFICATIONS_TOPIC` | `notifications` | Topic to publish outcome events to |
| `ROAD_SRV_URL` | `http://road-srv:8000` | Base URL of road-srv |
| `JOURNEY_SRV_URL` | _(empty)_ | Base URL of journey-srv. Leave empty to disable journey resolution |

## Booking flow

```
POST /bookings
    │
    ├─ (if X-Request-Id) SELECT bookings WHERE request_id + user_id
    │     └─ found  →  202 with existing booking (idempotent return)
    │
    ├─ (optional) POST journey-srv /journeys  →  resolve road_ids
    │
    ├─ INSERT bookings (status=PENDING, request_id stored)
    │
    └─ 202 Accepted
         │
         └─ background task
               │
               ├─ POST road-srv /roads/increment
               │     ├─ success  →  UPDATE status=SUCCESSFUL
               │     └─ failed   →  UPDATE status=FAILED
               │
               └─ publish to Kafka topic: notifications
```

## Kafka event format

Published to the `notifications` topic after every booking outcome:

```json
{
  "delivery_type": "PUSH",
  "user_id": "user-123",
  "message_id": "f8f80d3e-7be8-47be-b964-6a0fef1c02be",
  "content": "Your booking 8708aad5-... is SUCCESSFUL."
}
```

## Running locally (via Docker Compose)

```bash
# From the repo root
cd infrastructure
docker compose up --build -d
```

The service will be available at `http://localhost:8002`.

## Testing

```bash
# Health check
curl http://localhost:8002/health

# Create a booking (bypass gateway — x-user-id normally injected by gateway-srv)
curl -s -X POST http://localhost:8002/bookings \
  -H "Content-Type: application/json" \
  -H "x-user-id: user-123" \
  -H "x-request-id: my-unique-request-id" \
  -d '{"start_location":"Dublin","end_location":"Cork","booking_date":"2026-05-01","country_code":"IE","road_ids":[1,2]}' \
  | jq

# Retry with the same x-request-id — returns the original booking instead of creating a new one
curl -s -X POST http://localhost:8002/bookings \
  -H "Content-Type: application/json" \
  -H "x-user-id: user-123" \
  -H "x-request-id: my-unique-request-id" \
  -d '{"start_location":"Dublin","end_location":"Cork","booking_date":"2026-05-01","country_code":"IE","road_ids":[1,2]}' \
  | jq

# Poll for final status
curl -s http://localhost:8002/bookings/<id> | jq .status
```

## Tech stack

- Python 3.13 / FastAPI / Uvicorn
- PostgreSQL (via asyncpg)
- Apache Kafka (via aiokafka)
- httpx (async HTTP client for road-srv and journey-srv calls)
