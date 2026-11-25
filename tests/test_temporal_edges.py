from fastapi.testclient import TestClient
from app.billing_time_api import app
from engine.time_travel_clock import TemporalAuditorEngine

client = TestClient(app)
auditor = TemporalAuditorEngine()


def test_01_naive_endpoint_exposes_timezone_drift_bug():
    """
    AUDIT CHECK 1 (Expected Failure on Naive Endpoint):
    Demonstrates that /naive-billing emits timezone-naive timestamps without offset,
    causing cross-region ledger drift.
    """
    with auditor.travel_to("2026-11-25T18:29:59Z"):  # 23:59:59 IST
        response = client.post(
            "/naive-billing",
            json={
                "order_id": "ORD-NAIVE-001",
                "amount": 1000.0,
                "coupon_expiry_utc": "2026-11-25T18:30:00Z",
            },
        )
        data = response.json()
        assert auditor.has_valid_tz_offset(data["processed_at"]), (
            f"TEMPORAL DRIFT DETECTED: Naive timestamp '{data['processed_at']}' lacks UTC/offset!"
        )


def test_02_strict_endpoint_ist_midnight_rollover_boundary():
    """
    AUDIT CHECK 2 (IST Midnight Boundary 23:59:59 -> 00:00:01):
    Verifies that 18:29:59 UTC maps to 23:59:59 IST (same day) and
    18:30:01 UTC rolls over cleanly to 00:00:01 IST (next day).
    """
    # 1 second before IST midnight (2026-11-25 23:59:59 IST)
    with auditor.travel_to("2026-11-25T18:29:59Z"):
        res_before = client.post(
            "/strict-utc-billing",
            json={
                "order_id": "ORD-IST-BEFORE",
                "amount": 1000.0,
                "coupon_expiry_utc": "2026-11-25T19:00:00Z",
            },
        ).json()
        assert res_before["ist_ledger_date"] == "2026-11-25"
        assert auditor.has_valid_tz_offset(res_before["processed_at_utc"])
        assert auditor.has_valid_tz_offset(res_before["processed_at_ist"])

    # 1 second after IST midnight (2026-11-26 00:00:01 IST)
    with auditor.travel_to("2026-11-25T18:30:01Z"):
        res_after = client.post(
            "/strict-utc-billing",
            json={
                "order_id": "ORD-IST-AFTER",
                "amount": 1000.0,
                "coupon_expiry_utc": "2026-11-25T19:00:00Z",
            },
        ).json()
        assert res_after["ist_ledger_date"] == "2026-11-26"


def test_03_coupon_expiry_exact_second_cutoff():
    """
    AUDIT CHECK 3 (Exact Second Expiry Boundary):
    Validates discount applies at 23:59:59Z and expires immediately at 00:00:01Z.
    """
    expiry = "2026-11-25T23:59:59Z"

    with auditor.travel_to("2026-11-25T23:59:59Z"):
        valid_res = client.post(
            "/strict-utc-billing",
            json={"order_id": "ORD-EXP-OK", "amount": 1000.0, "coupon_expiry_utc": expiry},
        ).json()
        assert valid_res["coupon_expired"] is False
        assert valid_res["final_amount"] == 800.0

    with auditor.travel_to("2026-11-26T00:00:01Z"):
        expired_res = client.post(
            "/strict-utc-billing",
            json={"order_id": "ORD-EXP-LATE", "amount": 1000.0, "coupon_expiry_utc": expiry},
        ).json()
        assert expired_res["coupon_expired"] is True
        assert expired_res["final_amount"] == 1000.0


def test_04_leap_year_feb_29_resilience():
    """
    AUDIT CHECK 4 (Leap Year Feb 29 Boundary):
    Ensures billing engine processes 2028-02-29T23:59:59Z without date overflow errors.
    """
    with auditor.travel_to("2028-02-29T23:59:59Z"):
        res = client.post(
            "/strict-utc-billing",
            json={
                "order_id": "ORD-LEAP-2028",
                "amount": 500.0,
                "coupon_expiry_utc": "2028-03-01T00:00:00Z",
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["coupon_expired"] is False
        assert body["processed_at_utc"].startswith("2028-02-29T23:59:59")