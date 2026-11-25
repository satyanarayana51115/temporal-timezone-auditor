from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="Temporal & Time-Zone Edge Case Billing API")

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc


class TransactionRequest(BaseModel):
    order_id: str
    amount: float
    coupon_expiry_utc: str  # ISO-8601 format expected (e.g., 2026-11-25T18:29:59Z)


@app.post("/naive-billing")
def process_naive_billing(payload: TransactionRequest):
    """
    VULNERABLE ENDPOINT:
    1. Uses timezone-naive datetime.now() (server local time drift).
    2. Returns naive timestamp without 'Z' or offset.
    3. Fails cleanly on midnight rollover & cross-timezone expiry checks.
    """
    server_now = datetime.now()  # Bug: Timezone-naive!
    # Bug: Stripping timezone info to compare naively
    expiry_naive = datetime.fromisoformat(payload.coupon_expiry_utc.replace("Z", ""))

    is_expired = server_now > expiry_naive
    final_amount = payload.amount if is_expired else round(payload.amount * 0.80, 2)

    return {
        "order_id": payload.order_id,
        "processed_at": server_now.strftime("%Y-%m-%d %H:%M:%S"),  # Bug: Missing TZ offset
        "billing_date": server_now.strftime("%Y-%m-%d"),
        "coupon_expired": is_expired,
        "final_amount": final_amount,
        "mode": "NAIVE_LOCAL"
    }


@app.post("/strict-utc-billing")
def process_strict_utc_billing(payload: TransactionRequest):
    """
    HARDENED ENDPOINT:
    1. Enforces strict timezone-aware UTC clock.
    2. Converts accurately to Asia/Kolkata (IST) for business ledger date.
    3. Outputs strict ISO-8601 timestamps with explicit offsets.
    """
    try:
        expiry_aware = datetime.fromisoformat(payload.coupon_expiry_utc.replace("Z", "+00:00"))
        if expiry_aware.tzinfo is None:
            raise ValueError("Timezone offset is mandatory.")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"Invalid Temporal Schema: {exc}")

    now_utc = datetime.now(UTC)
    now_ist = now_utc.astimezone(IST)

    is_expired = now_utc > expiry_aware.astimezone(UTC)
    final_amount = payload.amount if is_expired else round(payload.amount * 0.80, 2)

    return {
        "order_id": payload.order_id,
        "processed_at_utc": now_utc.isoformat(),
        "processed_at_ist": now_ist.isoformat(),
        "ist_ledger_date": now_ist.strftime("%Y-%m-%d"),
        "coupon_expired": is_expired,
        "final_amount": final_amount,
        "mode": "STRICT_TZ_AWARE"
    }