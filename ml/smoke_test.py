"""
Pre-demo smoke test for the SIH26001 landslide risk API.

Run this the night before (and again 30 min before) your demo:

    python src/generate_synthetic_data.py   # only if data/raw is empty
    python src/train.py                      # only if models/ is empty
    uvicorn api.main:app --host 0.0.0.0 --port 8000 &
    python smoke_test.py

It does NOT judge model quality (that's what train.py's printed metrics are for).
It only catches "the demo is about to break" issues: server won't start, an
endpoint 500s, responses are missing fields the frontend expects, or a
known-risky input pattern silently produces a nonsensical answer.

Exit code 0 = safe to demo. Non-zero = fix it first.
"""
import sys
import time
import requests

BASE_URL = "http://localhost:8000"
TIMEOUT = 10

PASS, FAIL = [], []


def check(name, condition, detail=""):
    if condition:
        PASS.append(name)
        print(f"  OK   {name}")
    else:
        FAIL.append((name, detail))
        print(f"  FAIL {name}  -- {detail}")


def wait_for_server(retries=10, delay=1):
    for _ in range(retries):
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
            if r.status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(delay)
    return False


LOW_RISK_CELL = {
    "lat": 24.0, "lon": 92.0,
    "slope_deg": 5, "elevation_m": 100, "aspect_deg": 180, "ndvi": 0.8,
    "rain_24h_mm": 2, "rain_3d_mm": 5, "rain_7d_mm": 10, "rain_30d_mm": 40,
    "soil_saturation_proxy": 5,
}

HIGH_RISK_CELL = {
    "lat": 24.1, "lon": 92.1,
    "slope_deg": 55, "elevation_m": 1500, "aspect_deg": 10, "ndvi": 0.05,
    "rain_24h_mm": 180, "rain_3d_mm": 380, "rain_7d_mm": 620, "rain_30d_mm": 1400,
    "soil_saturation_proxy": 95,
}

INVALID_CELL = {**LOW_RISK_CELL, "slope_deg": 150}  # out of allowed range


def main():
    print(f"Checking server at {BASE_URL} ...")
    if not wait_for_server():
        print(f"\nServer never came up at {BASE_URL}. Is uvicorn running?")
        sys.exit(1)

    print("\n[1] Health & root")
    r = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
    check("GET /health returns 200", r.status_code == 200, r.text)
    check("model_loaded is true", r.json().get("model_loaded") is True, r.text)

    print("\n[2] Single prediction - low risk profile")
    r = requests.post(f"{BASE_URL}/predict", json=LOW_RISK_CELL, timeout=TIMEOUT)
    check("POST /predict returns 200", r.status_code == 200, r.text)
    body = r.json() if r.status_code == 200 else {}
    for field in ("risk_score", "risk_level", "model_version", "confidence", "top_contributing_factors"):
        check(f"response has '{field}'", field in body, str(body)[:200])
    if "risk_score" in body:
        check("risk_score in [0,1]", 0.0 <= body["risk_score"] <= 1.0, body["risk_score"])
        check("low-risk profile scores as Low or Moderate (not Severe)",
              body.get("risk_level") in ("Low", "Moderate"),
              f"got {body.get('risk_level')} for a mild slope/low rainfall/high vegetation input")

    print("\n[3] Single prediction - high risk profile")
    r = requests.post(f"{BASE_URL}/predict", json=HIGH_RISK_CELL, timeout=TIMEOUT)
    check("POST /predict returns 200 (high-risk input)", r.status_code == 200, r.text)
    hbody = r.json() if r.status_code == 200 else {}
    if "risk_score" in hbody:
        check("high-risk profile scores meaningfully above low-risk profile",
              hbody["risk_score"] > body.get("risk_score", 1.0),
              f"high={hbody.get('risk_score')} low={body.get('risk_score')}")

    print("\n[4] Sub-daily rainfall fallback consistency")
    # Same daily/weekly totals, once with sub-daily fields omitted and once with
    # consistent sub-daily fields supplied -- these should now match (regression
    # check for the rain_1h/6h/12h/14d silently-defaulting-to-zero bug).
    omitted = {k: v for k, v in HIGH_RISK_CELL.items()}
    explicit = {
        **HIGH_RISK_CELL,
        "rain_1h_mm": HIGH_RISK_CELL["rain_24h_mm"] / 24.0,
        "rain_6h_mm": HIGH_RISK_CELL["rain_24h_mm"] / 4.0,
        "rain_12h_mm": HIGH_RISK_CELL["rain_24h_mm"] / 2.0,
        "rain_14d_mm": HIGH_RISK_CELL["rain_7d_mm"] * 1.7,
    }
    r1 = requests.post(f"{BASE_URL}/predict", json=omitted, timeout=TIMEOUT)
    r2 = requests.post(f"{BASE_URL}/predict", json=explicit, timeout=TIMEOUT)
    if r1.status_code == 200 and r2.status_code == 200:
        s1, s2 = r1.json()["risk_score"], r2.json()["risk_score"]
        check("omitted vs. explicit sub-daily rain give matching risk_score",
              abs(s1 - s2) < 1e-6, f"omitted={s1} explicit={s2}")
    else:
        check("sub-daily rainfall consistency check ran", False,
              f"status codes: {r1.status_code}, {r2.status_code}")

    print("\n[5] Input validation")
    r = requests.post(f"{BASE_URL}/predict", json=INVALID_CELL, timeout=TIMEOUT)
    check("out-of-range slope_deg is rejected with 422", r.status_code == 422, r.text)

    print("\n[6] Batch endpoint with mixed missing fields across cells")
    r = requests.post(f"{BASE_URL}/predict/batch",
                       json={"cells": [LOW_RISK_CELL, HIGH_RISK_CELL]}, timeout=TIMEOUT)
    check("POST /predict/batch returns 200", r.status_code == 200, r.text)
    bbody = r.json() if r.status_code == 200 else {}
    check("batch returns 2 results", bbody.get("total_cells") == 2, bbody)
    check("batch risk_counts present", "risk_counts" in bbody, bbody)

    print("\n[7] Risk map (GeoJSON for the dashboard)")
    r = requests.get(f"{BASE_URL}/risk-map", timeout=30)
    check("GET /risk-map returns 200", r.status_code == 200, r.text[:200])
    if r.status_code == 200:
        gj = r.json()
        check("risk-map is a FeatureCollection", gj.get("type") == "FeatureCollection", gj.get("type"))
        check("risk-map has features", len(gj.get("features", [])) > 0, "0 features")
        if gj.get("features"):
            feat = gj["features"][0]
            check("feature has Point geometry", feat["geometry"]["type"] == "Point", feat)
            check("feature has risk_level property", "risk_level" in feat["properties"], feat)

    print("\n[8] Alerts endpoint")
    r = requests.post(f"{BASE_URL}/alerts/evaluate",
                       json={"cells": [LOW_RISK_CELL, HIGH_RISK_CELL]}, timeout=TIMEOUT)
    check("POST /alerts/evaluate returns 200", r.status_code == 200, r.text)
    abody = r.json() if r.status_code == 200 else {}
    check("alerts response has alert_count", "alert_count" in abody, abody)

    print(f"\n{'='*50}\n{len(PASS)} passed, {len(FAIL)} failed\n{'='*50}")
    if FAIL:
        print("\nFailures (fix before demo):")
        for name, detail in FAIL:
            print(f"  - {name}: {detail}")
        sys.exit(1)
    print("All checks passed. Safe to demo.")
    sys.exit(0)


if __name__ == "__main__":
    main()
