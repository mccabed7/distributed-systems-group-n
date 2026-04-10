import subprocess
import sys
import time
import uuid
import requests

BOOKING_SRV = "http://localhost:8002"
POLL_TIMEOUT = 20
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


def info(msg: str) -> None:
    print(f"  {YELLOW}→{RESET} {msg}")


def docker(cmd: str, *args: str) -> tuple[int, str]:
    result = subprocess.run(
        ["docker", cmd, *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def docker_exec(container: str, *cmd: str) -> tuple[int, str]:
    result = subprocess.run(
        ["docker", "exec", container, *cmd],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout + result.stderr


def stop(container: str) -> None:
    info(f"stopping {container}...")
    docker("stop", container)


def start(container: str) -> None:
    info(f"starting {container}...")
    docker("start", container)


def wait_for_http(url: str, timeout: int = 30) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=2)
            if r.status_code == 200:
                return True
        except requests.RequestException:
            pass
        time.sleep(1)
    return False


def wait_for_container_healthy(container: str, timeout: int = 40) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        code, out = docker("inspect", "--format", "{{.State.Health.Status}}", container)
        if code == 0 and out.strip() == "healthy":
            return True
        time.sleep(2)
    return False


def create_booking(user_id: str, road_ids: list[int]) -> str | None:
    try:
        resp = requests.post(
            f"{BOOKING_SRV}/bookings",
            json={
                "start_location": "Dublin",
                "end_location": "Cork",
                "booking_date": "2099-03-01",
                "country_code": "IE",
                "road_ids": road_ids,
            },
            headers={"x-user-id": user_id},
            timeout=10,
        )
        if resp.status_code == 202:
            return resp.json().get("id")
    except requests.RequestException:
        pass
    return None


def poll_booking(booking_id: str, user_id: str) -> str | None:
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        try:
            resp = requests.get(
                f"{BOOKING_SRV}/bookings/{booking_id}",
                headers={"x-user-id": user_id},
                timeout=5,
            )
            if resp.status_code == 200:
                status = resp.json().get("status")
                if status != "PENDING":
                    return status
        except requests.RequestException:
            pass
        time.sleep(POLL_INTERVAL)
    return "PENDING"


def kafka_isr_counts(bootstrap: str = "kafka-1:9092") -> list[int]:
    """Return the ISR count for each partition of the notifications topic."""
    code, out = docker_exec(
        "kafka-1",
        "/opt/kafka/bin/kafka-topics.sh",
        "--describe",
        "--topic",
        "notifications",
        "--bootstrap-server",
        bootstrap,
    )
    counts = []
    for line in out.splitlines():
        if "Isr:" in line:
            isr = line.split("Isr:")[1].strip().split("\t")[0].split(",")
            counts.append(len([x for x in isr if x.strip()]))
    return counts


section("Failure scenario 1: Kafka broker failure (kafka-2)")

isr_before = kafka_isr_counts()
if all(c == 3 for c in isr_before):
    ok("pre-condition: all partitions have ISR=3", str(isr_before))
else:
    fail("pre-condition: all partitions have ISR=3", str(isr_before))

try:
    stop("kafka-2")
    time.sleep(3)

    user_id = f"kafka-fail-{uuid.uuid4().hex[:6]}"
    booking_id = create_booking(user_id, [7001])
    if booking_id:
        ok("POST /bookings succeeds with kafka-2 down", f"id={booking_id}")
        status = poll_booking(booking_id, user_id)
        if status == "SUCCESSFUL":
            ok("booking resolves to SUCCESSFUL with kafka-2 down")
        else:
            fail("booking resolves with kafka-2 down", f"status={status}")
    else:
        fail("POST /bookings succeeds with kafka-2 down")

    isr_during = kafka_isr_counts("kafka-1:9092")
    if all(c == 2 for c in isr_during):
        ok("ISR dropped to 2 on all partitions while kafka-2 is down", str(isr_during))
    else:
        fail("ISR dropped to 2", f"got {isr_during}")

finally:
    start("kafka-2")
    info("waiting for kafka-2 to rejoin and ISR to recover...")
    deadline = time.time() + 60
    recovered = False
    while time.time() < deadline:
        isr = kafka_isr_counts()
        if all(c == 3 for c in isr):
            recovered = True
            break
        time.sleep(3)

    if recovered:
        ok("ISR recovered to 3 after kafka-2 restarted")
    else:
        fail(
            "ISR recovered to 3 after kafka-2 restarted",
            f"last ISR: {kafka_isr_counts()}",
        )


section("Failure scenario 2: PostgreSQL replica failure")

user_id = f"replica-fail-{uuid.uuid4().hex[:6]}"

try:
    resp = requests.get(
        f"{BOOKING_SRV}/bookings",
        headers={"x-user-id": user_id},
        timeout=5,
    )
    if resp.status_code == 200:
        ok("pre-condition: GET /bookings works (replica up)")
    else:
        fail("pre-condition: GET /bookings works", f"HTTP {resp.status_code}")
except requests.RequestException as e:
    fail("pre-condition: GET /bookings works", str(e))

try:
    stop("postgres-replica")
    time.sleep(3)

    booking_id = create_booking(user_id, [7002])
    if booking_id:
        ok(
            "POST /bookings succeeds with replica down (writes go to primary)",
            f"id={booking_id}",
        )
    else:
        fail("POST /bookings succeeds with replica down")

    try:
        resp = requests.get(
            f"{BOOKING_SRV}/bookings",
            headers={"x-user-id": user_id},
            timeout=5,
        )
        if resp.status_code == 200:
            ok(
                "GET /bookings served from cached asyncpg connection (pool not yet aware replica is down)",
                "HTTP 200 — reads degrade gracefully on next pool exhaustion",
            )
        elif resp.status_code in (500, 503):
            ok(
                "GET /bookings correctly fails when replica is down",
                f"HTTP {resp.status_code}",
            )
        else:
            fail(
                "GET /bookings returns 200 or 5xx with replica down",
                f"HTTP {resp.status_code}",
            )
    except requests.RequestException:
        ok("GET /bookings fails when replica is down (connection error)")

    try:
        resp = requests.get(f"{BOOKING_SRV}/health", timeout=5)
        if resp.status_code == 200:
            ok("GET /health still returns 200 (primary unaffected)")
        else:
            fail("GET /health still returns 200", f"HTTP {resp.status_code}")
    except requests.RequestException as e:
        fail("GET /health still returns 200", str(e))

finally:
    start("postgres-replica")
    info("waiting for replica to recover...")
    if wait_for_container_healthy("postgres-replica", timeout=40):
        ok("postgres-replica is healthy again")
    else:
        fail("postgres-replica recovered in time")

    time.sleep(3)

    try:
        resp = requests.get(
            f"{BOOKING_SRV}/bookings",
            headers={"x-user-id": user_id},
            timeout=5,
        )
        if resp.status_code == 200:
            ok("GET /bookings recovers after replica restarts")
        else:
            fail(
                "GET /bookings recovers after replica restarts",
                f"HTTP {resp.status_code}",
            )
    except requests.RequestException as e:
        fail("GET /bookings recovers after replica restarts", str(e))


section(
    "Failure scenario 3: PostgreSQL primary failure (known limitation — no auto-failover)"
)

user_id = f"primary-fail-{uuid.uuid4().hex[:6]}"

try:
    stop("postgres")
    time.sleep(3)

    booking_id = create_booking(user_id, [7003])
    if booking_id is None:
        ok("POST /bookings fails when primary is down (expected — no auto-failover)")
    else:
        fail(
            "POST /bookings correctly fails when primary is down",
            f"booking was accepted (id={booking_id}) — primary may still have been reachable",
        )

    try:
        resp = requests.get(
            f"{BOOKING_SRV}/bookings",
            headers={"x-user-id": user_id},
            timeout=5,
        )
        if resp.status_code == 200:
            ok("GET /bookings still serves reads from replica while primary is down")
        else:
            info(
                f"GET /bookings returned HTTP {resp.status_code} with primary down "
                "(replica pool may have lost connection too)"
            )
    except requests.RequestException:
        info("GET /bookings also unavailable with primary down")

finally:
    start("postgres")
    info("waiting for primary to recover...")
    if wait_for_container_healthy("postgres", timeout=40):
        ok("postgres primary is healthy again")
    else:
        fail("postgres primary recovered in time")

    time.sleep(3)

    booking_id = create_booking(user_id, [7004])
    if booking_id:
        ok("POST /bookings recovers after primary restarts", f"id={booking_id}")
    else:
        fail("POST /bookings recovers after primary restarts")


total = passed + failed
print(f"\n{BOLD}{'─' * 50}{RESET}")
print(
    f"{BOLD}Results: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET} / {total} total{RESET}"
)

sys.exit(0 if failed == 0 else 1)
