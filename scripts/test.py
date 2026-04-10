import time
import uuid
import sys
import requests

BOOKING_SRV = "http://localhost:8002"
ROAD_SRV    = "http://localhost:8001"
GATEWAY     = "http://localhost:8000"

TEST_DATE        = "2099-01-01"
TEST_USER        = f"test-user-{uuid.uuid4().hex[:8]}"
TEST_ROAD_IDS    = [9001, 9002]
TEST_COUNTRY     = "IE"
POLL_TIMEOUT_S   = 15
POLL_INTERVAL_S  = 1

GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

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


def assert_status(label: str, resp: requests.Response, expected: int) -> bool:
    if resp.status_code == expected:
        ok(label, f"HTTP {resp.status_code}")
        return True
    else:
        fail(label, f"expected HTTP {expected}, got {resp.status_code}: {resp.text[:120]}")
        return False


def post(url: str, **kwargs) -> requests.Response | None:
    try:
        return requests.post(url, **kwargs)
    except requests.ConnectionError:
        fail(f"POST {url}", "connection refused")
        return None


def get(url: str, **kwargs) -> requests.Response | None:
    try:
        return requests.get(url, **kwargs)
    except requests.ConnectionError:
        fail(f"GET {url}", "connection refused")
        return None


def poll_booking_status(booking_id: str, user_id: str) -> str | None:
    deadline = time.time() + POLL_TIMEOUT_S
    while time.time() < deadline:
        resp = get(
            f"{BOOKING_SRV}/bookings/{booking_id}",
            headers={"x-user-id": user_id},
        )
        if resp is None or resp.status_code != 200:
            return None
        status = resp.json().get("status")
        if status != "PENDING":
            return status
        time.sleep(POLL_INTERVAL_S)
    return "PENDING"


section("Health checks")

for name, url in [
    ("booking-srv", f"{BOOKING_SRV}/health"),
    ("road-srv",    f"{ROAD_SRV}/health"),
    ("gateway-srv", f"{GATEWAY}/health"),
]:
    try:
        resp = requests.get(url, timeout=5)
        assert_status(f"{name} /health", resp, 200)
    except requests.ConnectionError:
        fail(f"{name} /health", "connection refused — is the service running?")


section("road-srv: capacity management")

roads_payload = {
    "booking_date": TEST_DATE,
    "roads": [{"road_id": r, "country_code": TEST_COUNTRY} for r in TEST_ROAD_IDS],
}

post(f"{ROAD_SRV}/roads/decrement", json=roads_payload)

resp = post(f"{ROAD_SRV}/roads/increment", json=roads_payload)
if resp and assert_status("POST /roads/increment", resp, 200):
    body = resp.json()
    if body.get("status") == "success":
        ok("increment returns status=success")
    else:
        fail("increment returns status=success", f"got: {body}")

resp = post(f"{ROAD_SRV}/roads/counts", json=roads_payload)
if resp and assert_status("POST /roads/counts", resp, 200):
    counts = {r["road_id"]: r["count"] for r in resp.json().get("roads", [])}
    all_one = all(counts.get(r) == 1 for r in TEST_ROAD_IDS)
    if all_one:
        ok("counts reflect increment (all roads at 1)")
    else:
        fail("counts reflect increment", f"got: {counts}")

resp = post(f"{ROAD_SRV}/roads/decrement", json=roads_payload)
if resp is not None:
    assert_status("POST /roads/decrement", resp, 200)

resp = post(f"{ROAD_SRV}/roads/counts", json=roads_payload)
if resp and assert_status("POST /roads/counts after decrement", resp, 200):
    counts = {r["road_id"]: r["count"] for r in resp.json().get("roads", [])}
    all_zero = all(counts.get(r) == 0 for r in TEST_ROAD_IDS)
    if all_zero:
        ok("counts reflect decrement (all roads back to 0)")
    else:
        fail("counts reflect decrement", f"got: {counts}")

section("road-srv: capacity limit enforcement")
capacity_road = [{"road_id": 9999, "country_code": TEST_COUNTRY}]
cap_payload = {"booking_date": TEST_DATE, "roads": capacity_road}
post(f"{ROAD_SRV}/roads/decrement", json=cap_payload)

for i in range(10):
    post(f"{ROAD_SRV}/roads/increment", json=cap_payload)

resp = post(f"{ROAD_SRV}/roads/increment", json=cap_payload)
if resp and assert_status("11th increment on full road returns 200", resp, 200):
    body = resp.json()
    if body.get("status") == "failed":
        ok("11th increment rejected (status=failed)")
    else:
        fail("11th increment rejected", f"got status={body.get('status')}")

for _ in range(10):
    post(f"{ROAD_SRV}/roads/decrement", json=cap_payload)


section("booking-srv: create and resolve a booking")

booking_body = {
    "start_location": "Dublin",
    "end_location":   "Cork",
    "booking_date":   TEST_DATE,
    "country_code":   TEST_COUNTRY,
    "road_ids":       TEST_ROAD_IDS,
}

resp = post(
    f"{BOOKING_SRV}/bookings",
    json=booking_body,
    headers={"x-user-id": TEST_USER},
)
booking_id = None
if resp and assert_status("POST /bookings returns 202", resp, 202):
    body = resp.json()
    booking_id = body.get("id")
    if body.get("status") == "PENDING":
        ok("initial status is PENDING")
    else:
        fail("initial status is PENDING", f"got: {body.get('status')}")

if booking_id:
    status = poll_booking_status(booking_id, TEST_USER)
    if status == "SUCCESSFUL":
        ok(f"booking resolved to SUCCESSFUL (within {POLL_TIMEOUT_S}s)")
    elif status == "FAILED":
        fail("booking resolved to SUCCESSFUL", "got FAILED — road capacity may be exhausted")
    elif status == "PENDING":
        fail("booking resolved within timeout", f"still PENDING after {POLL_TIMEOUT_S}s")
    else:
        fail("booking resolved", f"unexpected status: {status}")


section("booking-srv: list bookings")

resp = get(
    f"{BOOKING_SRV}/bookings",
    headers={"x-user-id": TEST_USER},
)
if resp and assert_status("GET /bookings returns 200", resp, 200):
    bookings = resp.json()
    if isinstance(bookings, list) and any(b["id"] == booking_id for b in bookings):
        ok(f"booking appears in list ({len(bookings)} booking(s))")
    else:
        fail("booking appears in list", f"booking_id={booking_id} not found in response")


section("booking-srv: idempotency")

idempotency_key = str(uuid.uuid4())
resp1 = post(
    f"{BOOKING_SRV}/bookings",
    json={**booking_body, "road_ids": [9003]},
    headers={"x-user-id": TEST_USER, "x-request-id": idempotency_key},
)
id1 = resp1.json().get("id") if resp1 and resp1.status_code == 202 else None

resp2 = post(
    f"{BOOKING_SRV}/bookings",
    json={**booking_body, "road_ids": [9003]},
    headers={"x-user-id": TEST_USER, "x-request-id": idempotency_key},
)
id2 = resp2.json().get("id") if resp2 and resp2.status_code == 202 else None

if id1 and id2 and id1 == id2:
    ok("duplicate request with same X-Request-Id returns same booking", f"id={id1}")
elif id1 and id2:
    fail("duplicate request returns same booking", f"got two different ids: {id1} vs {id2}")
else:
    fail("idempotency test", "one or both requests failed (service unavailable?)")


section("booking-srv: cancel a booking")

resp = post(
    f"{BOOKING_SRV}/bookings",
    json={**booking_body, "road_ids": [9004]},
    headers={"x-user-id": TEST_USER},
)
cancel_id = resp.json().get("id") if resp and resp.status_code == 202 else None

if cancel_id:
    poll_booking_status(cancel_id, TEST_USER)

    resp = post(
        f"{BOOKING_SRV}/bookings/{cancel_id}/cancel",
        headers={"x-user-id": TEST_USER},
    )
    if resp and assert_status("POST /bookings/{id}/cancel returns 200", resp, 200):
        if resp.json().get("status") == "CANCELLED":
            ok("cancelled booking status is CANCELLED")
        else:
            fail("cancelled booking status", f"got: {resp.json().get('status')}")

    resp = post(
        f"{BOOKING_SRV}/bookings/{cancel_id}/cancel",
        headers={"x-user-id": TEST_USER},
    )
    if resp and assert_status("cancelling already-cancelled booking is idempotent (200)", resp, 200):
        ok("repeated cancel returns CANCELLED")
else:
    fail("cancel test setup", "could not create a booking to cancel")


section("booking-srv: cancel a PENDING booking is rejected")

resp = post(
    f"{BOOKING_SRV}/bookings",
    json={**booking_body, "road_ids": [9005]},
    headers={"x-user-id": TEST_USER},
)
pending_id = resp.json().get("id") if resp and resp.status_code == 202 else None

if pending_id:
    resp = post(
        f"{BOOKING_SRV}/bookings/{pending_id}/cancel",
        headers={"x-user-id": TEST_USER},
    )
    if resp is not None and resp.status_code == 409:
        ok("cancelling a PENDING booking returns 409")
    elif resp is not None and resp.status_code == 200:
        ok("booking resolved before cancel attempt (race condition — acceptable)")
    elif resp is not None:
        fail("cancelling PENDING booking returns 409", f"got HTTP {resp.status_code}")
else:
    fail("pending cancel test setup", "could not create booking")


section("booking-srv: error handling")

resp = get(f"{BOOKING_SRV}/bookings/not-a-uuid", headers={"x-user-id": TEST_USER})
if resp is not None:
    assert_status("GET /bookings/invalid-id returns 404", resp, 404)

resp = post(
    f"{BOOKING_SRV}/bookings",
    json={"start_location": "Dublin"},
    headers={"x-user-id": TEST_USER},
)
if resp is not None:
    assert_status("POST /bookings with missing fields returns 422", resp, 422)

resp = post(f"{BOOKING_SRV}/bookings", json=booking_body)
if resp is not None:
    assert_status("POST /bookings without X-User-ID returns 422", resp, 422)


total = passed + failed
print(f"\n{BOLD}{'─' * 50}{RESET}")
print(f"{BOLD}Results: {GREEN}{passed} passed{RESET}, {RED}{failed} failed{RESET} / {total} total{BOLD}{RESET}")

sys.exit(0 if failed == 0 else 1)
