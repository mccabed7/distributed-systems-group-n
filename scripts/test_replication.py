import subprocess
import sys
import time
import uuid
import requests

BOOKING_SRV = "http://localhost:8002"
POLL_TIMEOUT = 15
POLL_INTERVAL = 1

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

passed = 0
failed = 0


def ok(label: str, detail: str = "") -> None:
    global passed
    passed += 1
    suffix = f"  {YELLOW}{detail}{RESET}" if detail else ""
    print(f"  {GREEN}✓{RESET} {label}{suffix}")


def fail(label: str, detail: str = "") -> None:
    global failed
    failed += 1
    suffix = f"  {YELLOW}{detail}{RESET}" if detail else ""
    print(f"  {RED}✗{RESET} {label}{suffix}")


def section(title: str) -> None:
    print(f"\n{BOLD}{title}{RESET}")


def docker_exec(container: str, *cmd: str) -> tuple[int, str]:
    result = subprocess.run(
        ["docker", "exec", container, *cmd],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def psql(container: str, query: str) -> tuple[int, str]:
    return docker_exec(
        container,
        "psql",
        "-U",
        "booking",
        "-d",
        "booking",
        "-t",
        "-c",
        query,
    )


def post(url: str, **kwargs) -> requests.Response | None:
    try:
        return requests.post(url, **kwargs)
    except requests.ConnectionError:
        fail(f"POST {url}", "connection refused")
        return None


def poll_booking_status(booking_id: str, user_id: str) -> str | None:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{BOOKING_SRV}/bookings/{booking_id}",
                headers={"x-user-id": user_id},
            )
            if resp.status_code == 200:
                status = resp.json().get("status")
                if status != "PENDING":
                    return status
        except requests.ConnectionError:
            pass
        time.sleep(POLL_INTERVAL)
    return "PENDING"


section("PostgreSQL: primary is in replication mode")

code, out = psql(
    "postgres", "SELECT setting FROM pg_settings WHERE name = 'wal_level';"
)
if code == 0 and "replica" in out:
    ok("wal_level=replica on primary")
else:
    fail("wal_level=replica on primary", out.strip())

code, out = psql("postgres", "SELECT count(*) FROM pg_stat_replication;")
if code == 0:
    count = out.strip()
    if count and int(count) >= 1:
        ok(f"primary has {count.strip()} active replication connection(s)")
    else:
        fail("primary has active replication connections", f"count={count.strip()}")
else:
    fail("pg_stat_replication query failed", out.strip())

section("PostgreSQL: replica is in standby mode")

code, out = psql("postgres-replica", "SELECT pg_is_in_recovery();")
if code == 0 and "t" in out:
    ok("replica is in recovery/standby mode")
else:
    fail("replica is in standby mode", out.strip())

section("PostgreSQL: writes on primary replicate to replica")

user_id = f"replication-test-{uuid.uuid4().hex[:8]}"
booking_id = None

resp = post(
    f"{BOOKING_SRV}/bookings",
    json={
        "start_location": "Dublin",
        "end_location": "Cork",
        "booking_date": "2099-02-01",
        "country_code": "IE",
        "road_ids": [8001],
    },
    headers={"x-user-id": user_id},
)

if resp is not None and resp.status_code == 202:
    booking_id = resp.json().get("id")
    ok("created test booking via booking-srv", f"id={booking_id}")
else:
    fail("create test booking", f"HTTP {resp.status_code if resp else 'no response'}")

if booking_id:
    status = poll_booking_status(booking_id, user_id)
    ok(f"booking resolved to {status}")

    time.sleep(1)

    code, out = psql(
        "postgres-replica",
        f"SELECT id, status FROM bookings WHERE id = '{booking_id}';",
    )
    if code == 0 and booking_id in out:
        status_on_replica = (
            "SUCCESSFUL"
            if "SUCCESSFUL" in out
            else (
                "FAILED"
                if "FAILED" in out
                else "PENDING" if "PENDING" in out else "unknown"
            )
        )
        ok("booking row is present on replica", f"status={status_on_replica}")
    else:
        fail("booking row present on replica", out.strip())

    code, out = psql(
        "postgres-replica",
        f"UPDATE bookings SET status = 'FAILED' WHERE id = '{booking_id}';",
    )
    if code != 0 and "read-only" in out.lower():
        ok("replica correctly rejects writes (read-only)")
    else:
        fail("replica rejects writes", out.strip())


section("Kafka: topic replication")

code, out = docker_exec(
    "kafka-1",
    "/opt/kafka/bin/kafka-topics.sh",
    "--describe",
    "--topic",
    "notifications",
    "--bootstrap-server",
    "kafka-1:9092",
)

if code != 0:
    fail("describe notifications topic", out.strip())
else:
    if "ReplicationFactor: 3" in out:
        ok("notifications topic has ReplicationFactor=3")
    else:
        rf = next(
            (line for line in out.splitlines() if "ReplicationFactor" in line), ""
        )
        fail("notifications topic has ReplicationFactor=3", rf.strip())

    lines = [line for line in out.splitlines() if "Isr:" in line]
    all_in_sync = all(
        len(line.split("Isr:")[1].strip().split(",")) == 3
        for line in lines
        if "Isr:" in line
    )
    if all_in_sync and lines:
        ok(f"all {len(lines)} partition(s) have 3 in-sync replicas (ISR=3)")
    elif lines:
        fail("all partitions have ISR=3", "\n    ".join(line.strip() for line in lines))
    else:
        fail("could not parse ISR from topic description", out[:200])

section("Kafka: broker count")

code, out = docker_exec(
    "kafka-1",
    "/opt/kafka/bin/kafka-broker-api-versions.sh",
    "--bootstrap-server",
    "kafka-1:9092,kafka-2:9092,kafka-3:9092",
)
brokers = [line for line in out.splitlines() if line.startswith("kafka-")]
if len(brokers) >= 3:
    ok(f"{len(brokers)} brokers reachable", ", ".join(b.split(" ")[0] for b in brokers))
else:
    fail("3 brokers reachable", f"found {len(brokers)}: {out[:200]}")


total = passed + failed
print(f"\n{BOLD}{'─' * 50}{RESET}")
print(
    f"{BOLD}Results: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET} / {total} total{RESET}"
)

sys.exit(0 if failed == 0 else 1)
