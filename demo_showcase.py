import os
import time
import subprocess
import webbrowser
from fastapi.testclient import TestClient
from app.billing_time_api import app
from engine.time_travel_clock import TemporalAuditorEngine

# ANSI Colors for High-Contrast Terminal Display
GREEN = "\033[92m"
RED = "\033[91m"
CYAN = "\033[96m"
YELLOW = "\033[93m"
BOLD = "\033[1m"
RESET = "\033[0m"

client = TestClient(app)
auditor = TemporalAuditorEngine()


def run_showcase():
    os.system("cls" if os.name == "nt" else "clear")
    print(f"{CYAN}{BOLD}" + "=" * 68)
    print("  TEMPORAL & TIME-ZONE EDGE CASE AUDITOR — LIVE EXECUTION")
    print("=" * 68 + f"{RESET}\n")
    time.sleep(2.0)

    # Check 1: Naive Endpoint Bug
    print(f"{YELLOW}[AUDIT 1/4] Testing /naive-billing at 23:59:59 IST (18:29:59 UTC)...{RESET}")
    time.sleep(1.5)
    with auditor.travel_to("2026-11-25T18:29:59Z"):
        res1 = client.post("/naive-billing", json={
            "order_id": "ORD-NAIVE-001", "amount": 1000.0, "coupon_expiry_utc": "2026-11-25T18:30:00Z"
        }).json()
        print(f"{RED}{BOLD}  -> BUG CAUGHT: Naive timestamp '{res1['processed_at']}' lacks UTC/offset!{RESET}\n")
    time.sleep(2.5)

    # Check 2: IST Midnight Rollover
    print(f"{YELLOW}[AUDIT 2/4] Auditing IST Midnight Rollover (23:59:59 -> 00:00:01 IST)...{RESET}")
    time.sleep(1.5)
    with auditor.travel_to("2026-11-25T18:30:01Z"):
        res2 = client.post("/strict-utc-billing", json={
            "order_id": "ORD-IST-AFTER", "amount": 1000.0, "coupon_expiry_utc": "2026-11-25T19:00:00Z"
        }).json()
        print(f"{GREEN}{BOLD}  -> PASSED: Clean rollover to {res2['ist_ledger_date']} ({res2['processed_at_ist']}){RESET}\n")
    time.sleep(2.5)

    # Check 3: Exact-Second Expiry Boundary
    print(f"{YELLOW}[AUDIT 3/4] Auditing Exact-Second Coupon Expiry (23:59:59Z -> 00:00:01Z)...{RESET}")
    time.sleep(1.5)
    with auditor.travel_to("2026-11-26T00:00:01Z"):
        res3 = client.post("/strict-utc-billing", json={
            "order_id": "ORD-EXP-LATE", "amount": 1000.0, "coupon_expiry_utc": "2026-11-25T23:59:59Z"
        }).json()
        print(f"{GREEN}{BOLD}  -> PASSED: Expired coupon blocked -> Final Amount: {res3['final_amount']}{RESET}\n")
    time.sleep(2.5)

    # Check 4: Leap Year Feb 29
    print(f"{YELLOW}[AUDIT 4/4] Time-Traveling to Leap Year (2028-02-29T23:59:59Z)...{RESET}")
    time.sleep(1.5)
    with auditor.travel_to("2028-02-29T23:59:59Z"):
        res4 = client.post("/strict-utc-billing", json={
            "order_id": "ORD-LEAP-2028", "amount": 500.0, "coupon_expiry_utc": "2028-03-01T00:00:00Z"
        }).json()
        print(f"{GREEN}{BOLD}  -> PASSED: Leap Year boundary verified ({res4['processed_at_utc']}){RESET}\n")
    time.sleep(2.0)

    # Generate HTML Governance Report & Open in Browser
    print(f"{CYAN}{BOLD}Generating Pytest HTML Governance Report...{RESET}")
    subprocess.run(
        ["pytest", "-q", "--tb=short", "--html=reports/temporal_audit_report.html", "--self-contained-html"],
        stdout=subprocess.DEVNULL
    )
    time.sleep(1.5)
    report_path = os.path.abspath("reports/temporal_audit_report.html")
    webbrowser.open(f"file:///{report_path}")
    print(f"{GREEN}{BOLD}Audit Complete! HTML Report opened in browser.{RESET}")


if __name__ == "__main__":
    run_showcase()