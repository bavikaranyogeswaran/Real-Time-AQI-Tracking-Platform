#!/usr/bin/env python3
"""End-to-end smoke test against the running Docker stack.

Usage:
    python scripts/smoke_test.py

Requires: Python 3.9+, requests (pip install requests), docker CLI on PATH.
Exits 0 on all-pass, 1 on any failure.
"""
import json
import subprocess
import sys
import textwrap

try:
    import requests
except ImportError:
    print("ERROR: 'requests' not installed. Run: pip install requests")
    sys.exit(1)

API = "http://localhost:8000"
FRONTEND = "http://localhost:5173"

PASS = 0
FAIL = 0
FAILURES: list[str] = []


def _color(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if sys.stdout.isatty() else text


def passed(label: str) -> None:
    global PASS
    print(f"  {_color('0;32', 'PASS')}  {label}")
    PASS += 1


def failed(label: str, detail: str = "") -> None:
    global FAIL
    msg = f"{label}" + (f" — {detail}" if detail else "")
    print(f"  {_color('0;31', 'FAIL')}  {msg}")
    FAILURES.append(msg)
    FAIL += 1


def section(title: str) -> None:
    print(f"\n{_color('1;33', '>> ' + title)}")


def check(label: str, url: str, *, expected: int = 200, body_check=None) -> requests.Response | None:
    """GET url, assert status, optionally call body_check(parsed_json) → bool."""
    try:
        r = requests.get(url, timeout=10)
    except requests.exceptions.ConnectionError as exc:
        failed(label, f"connection error: {exc}")
        return None

    if r.status_code != expected:
        short = textwrap.shorten(r.text, 120)
        failed(label, f"HTTP {r.status_code} (expected {expected}) — {short}")
        return r

    if body_check is not None:
        try:
            body = r.json()
        except ValueError:
            failed(label, "response is not JSON")
            return r
        if not body_check(body):
            short = textwrap.shorten(r.text, 120)
            failed(label, f"body check failed — {short}")
            return r

    passed(label)
    return r


def check_container(name: str) -> bool:
    """Return True if the container is running."""
    try:
        out = subprocess.check_output(
            ["docker", "inspect", "--format={{.State.Status}}", name],
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        out = "missing"
    if out == "running":
        passed(f"Container {name} is running")
        return True
    failed(f"Container {name}", f"status: {out}")
    return False


# ---------------------------------------------------------------------------
# 1. Container health
# ---------------------------------------------------------------------------
section("Container health")
check_container("aqi_backend")
check_container("aqi_db")
check_container("aqi_frontend")

# ---------------------------------------------------------------------------
# 2. Backend health
# ---------------------------------------------------------------------------
section("Health check")
check("GET /health — status ok", f"{API}/health",
      body_check=lambda b: b.get("status") == "ok")

# ---------------------------------------------------------------------------
# 3. Pick a live city for subsequent parameterised tests
# ---------------------------------------------------------------------------
section("Locations")
locs_resp = check("GET /api/locations — 200, non-empty list", f"{API}/api/locations",
                  body_check=lambda b: isinstance(b, list) and len(b) > 0)

if locs_resp is None or locs_resp.status_code != 200 or not locs_resp.json():
    print(f"\n{_color('0;31', 'ABORT')}  No location data — cannot continue.")
    sys.exit(1)

locations = locs_resp.json()
city = locations[0]["city"]
loc_id = locations[0]["location_id"]
print(f"  Using city: {city}")

# ---------------------------------------------------------------------------
# 4. AQI endpoints
# ---------------------------------------------------------------------------
section(f"AQI endpoints (city={city})")
check("GET /api/aqi/current        — 200, has aqi",
      f"{API}/api/aqi/current?city={city}",
      body_check=lambda b: isinstance(b.get("aqi"), int))

check("GET /api/aqi/current        — 404 unknown city",
      f"{API}/api/aqi/current?city=NoSuchCityXYZ",
      expected=404)

check("GET /api/aqi/history        — 200, list",
      f"{API}/api/aqi/history?city={city}",
      body_check=lambda b: isinstance(b, list))

check("GET /api/aqi/history days=1 — 200, list",
      f"{API}/api/aqi/history?city={city}&days=1",
      body_check=lambda b: isinstance(b, list))

check("GET /api/aqi/history days=0 — 422 validation",
      f"{API}/api/aqi/history?city={city}&days=0",
      expected=422)

check("GET /api/aqi/pollutants     — 200, has pm25",
      f"{API}/api/aqi/pollutants?city={city}",
      body_check=lambda b: "pm25" in b)

check("GET /api/aqi/forecast       — 200, list",
      f"{API}/api/aqi/forecast?city={city}",
      body_check=lambda b: isinstance(b, list))

# ---------------------------------------------------------------------------
# 5. Alert endpoints
# ---------------------------------------------------------------------------
section("Alert endpoints")
check("GET /api/alerts             — 200, list",
      f"{API}/api/alerts",
      body_check=lambda b: isinstance(b, list))

# POST a test rule then delete it
try:
    r = requests.post(
        f"{API}/api/alerts/rules",
        json={"location_id": loc_id, "alert_type": "smoke_test_rule", "threshold_value": 999},
        timeout=10,
    )
    if r.status_code == 201:
        rule_id = r.json().get("rule_id")
        passed("POST /api/alerts/rules     — 201, rule created")
        # Clean up: delete via psql inside the db container
        subprocess.run(
            ["docker", "exec", "aqi_db", "psql", "-U", "aqi_user", "-d", "aqi_db",
             "-c", f"DELETE FROM alert_rules WHERE rule_id = '{rule_id}';"],
            check=False, capture_output=True,
        )
    else:
        failed("POST /api/alerts/rules", f"HTTP {r.status_code}")
except requests.exceptions.ConnectionError as exc:
    failed("POST /api/alerts/rules", str(exc))

# ---------------------------------------------------------------------------
# 6. Analytics endpoints
# ---------------------------------------------------------------------------
section(f"Analytics endpoints (city={city})")
check("GET /api/analytics/city-comparison — 200, list",
      f"{API}/api/analytics/city-comparison",
      body_check=lambda b: isinstance(b, list))

check("GET /api/analytics/trends weekly   — 200, list",
      f"{API}/api/analytics/trends?city={city}&period=weekly",
      body_check=lambda b: isinstance(b, list))

check("GET /api/analytics/trends invalid  — 400",
      f"{API}/api/analytics/trends?city={city}&period=notaperiod",
      expected=400)

check("GET /api/analytics/peak-hours      — 200, list",
      f"{API}/api/analytics/peak-hours?city={city}",
      body_check=lambda b: isinstance(b, list))

check("GET /api/analytics/distribution   — 200, list",
      f"{API}/api/analytics/distribution?city={city}",
      body_check=lambda b: isinstance(b, list))

check("GET /api/analytics/gaps           — 200, list",
      f"{API}/api/analytics/gaps?city={city}",
      body_check=lambda b: isinstance(b, list))

# ---------------------------------------------------------------------------
# 7. OpenAPI docs
# ---------------------------------------------------------------------------
section("API docs")
check("GET /docs  — 200", f"{API}/docs")
check("GET /redoc — 200", f"{API}/redoc")

# ---------------------------------------------------------------------------
# 8. Frontend dev server
# ---------------------------------------------------------------------------
section("Frontend")
check("GET http://localhost:5173/ — 200, HTML", FRONTEND)  # HTML, no JSON check

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
total = PASS + FAIL
print("\n" + "-" * 45)
if FAIL == 0:
    print(_color("0;32", f"All {total} checks passed."))
else:
    print(_color("0;31", f"{FAIL} of {total} checks FAILED:"))
    for msg in FAILURES:
        print(f"  • {msg}")
    sys.exit(1)
