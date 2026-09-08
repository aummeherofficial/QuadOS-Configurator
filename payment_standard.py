"""Razorpay Standard Checkout integration for QuadOS."""

import html
import json

import razorpay


def get_client(key_id, key_secret):
    if not key_id or not key_secret:
        raise ValueError("Razorpay API keys are not configured.")
    return razorpay.Client(auth=(key_id, key_secret))


def create_razorpay_order(key_id, key_secret, amount_rupees, receipt, notes=None):
    amount_rupees = float(amount_rupees)
    if amount_rupees <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    payload = {
        "amount": int(round(amount_rupees * 100)),
        "currency": "INR",
        "receipt": str(receipt),
    }
    if notes:
        payload["notes"] = {str(k): str(v)[:256] for k, v in dict(notes).items()}

    return get_client(key_id, key_secret).order.create(payload)


def verify_payment_signature(key_id, key_secret, razorpay_order_id, razorpay_payment_id, razorpay_signature):
    if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
        return False
    try:
        get_client(key_id, key_secret).utility.verify_payment_signature({
            "razorpay_order_id": str(razorpay_order_id),
            "razorpay_payment_id": str(razorpay_payment_id),
            "razorpay_signature": str(razorpay_signature),
        })
        return True
    except Exception:
        return False


def fetch_payment(key_id, key_secret, payment_id):
    return get_client(key_id, key_secret).payment.fetch(str(payment_id))


def fetch_order_payments(key_id, key_secret, razorpay_order_id):
    """Fetch all Razorpay payments linked to a specific order."""
    response = get_client(key_id, key_secret).order.payments(str(razorpay_order_id))
    if isinstance(response, dict):
        return response.get("items", []) or []
    return []


def get_captured_payment_for_order(key_id, key_secret, razorpay_order_id, expected_amount_rupees):
    """Return a captured payment matching the QuadOS order amount, if one exists.

    This is a server-side reconciliation fallback for cases where the browser
    cannot navigate the Streamlit page after Razorpay Checkout closes.
    """
    expected_paise = int(round(float(expected_amount_rupees) * 100))
    payments = fetch_order_payments(key_id, key_secret, razorpay_order_id)

    for payment in payments:
        if not isinstance(payment, dict):
            continue
        payment_order_id = str(payment.get("order_id", ""))
        payment_amount = int(payment.get("amount", 0) or 0)
        status = str(payment.get("status", "")).lower()
        captured = bool(payment.get("captured", False)) or status == "captured"

        if (
            payment_order_id == str(razorpay_order_id)
            and payment_amount == expected_paise
            and captured
        ):
            return payment

    return None


def is_payment_captured(payment):
    return str((payment or {}).get("status", "")).lower() == "captured"


def build_checkout_html(
    key_id,
    razorpay_order_id,
    amount_rupees,
    customer_name="",
    customer_email="",
    customer_phone="",
    description="QuadOS Order",
):
    """Build a Standard Checkout iframe with an explicit Pay button.

    The explicit button is intentional: browsers can block an automatically
    opened payment modal when it is launched from an embedded iframe without
    a direct user gesture.
    """
    checkout_options = {
        "key": str(key_id),
        "amount": int(round(float(amount_rupees) * 100)),
        "currency": "INR",
        "name": "QuadOS",
        "description": str(description)[:255],
        "order_id": str(razorpay_order_id),
        "prefill": {
            "name": str(customer_name or ""),
            "email": str(customer_email or ""),
            "contact": str(customer_phone or ""),
        },
        "theme": {"color": "#ff4b4b"},
    }

    options_json = json.dumps(checkout_options, ensure_ascii=False)
    safe_options = html.escape(options_json, quote=False)
    amount_text = f"₹{float(amount_rupees):,.2f}"

    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
<style>
    * {{ box-sizing: border-box; }}
    body {{
        margin: 0;
        padding: 14px 4px 8px;
        font-family: Arial, Helvetica, sans-serif;
        background: transparent;
        text-align: center;
    }}
    .pay-box {{
        max-width: 620px;
        margin: 0 auto;
        padding: 22px 20px;
        border: 1px solid rgba(128,128,128,.28);
        border-radius: 14px;
        background: rgba(255,255,255,.035);
    }}
    .label {{
        font-size: 14px;
        opacity: .72;
        margin-bottom: 6px;
    }}
    .amount {{
        font-size: 27px;
        font-weight: 800;
        margin-bottom: 18px;
    }}
    #payButton {{
        width: 100%;
        border: 0;
        border-radius: 9px;
        padding: 14px 18px;
        background: #ff4b4b;
        color: white;
        font-size: 16px;
        font-weight: 700;
        cursor: pointer;
    }}
    #payButton:hover {{ opacity: .92; }}
    #payButton:disabled {{ opacity: .65; cursor: wait; }}
    #message {{
        min-height: 20px;
        margin-top: 12px;
        font-size: 13px;
        opacity: .72;
    }}
</style>
</head>
<body>
<div class="pay-box">
    <div class="label">Secure Razorpay Payment</div>
    <div class="amount">{html.escape(amount_text)}</div>
    <button id="payButton" type="button">Pay {html.escape(amount_text)} with Razorpay</button>
    <div id="message">Click the button above to open the secure payment window.</div>
</div>

<script>
(function () {{
    const options = {safe_options};
    const button = document.getElementById("payButton");
    const message = document.getElementById("message");

    function returnToQuadOS(response) {{
        const params = new URLSearchParams();
        params.set("razorpay_payment_id", response.razorpay_payment_id || "");
        params.set("razorpay_order_id", response.razorpay_order_id || "");
        params.set("razorpay_signature", response.razorpay_signature || "");

        const target = window.location.origin + window.location.pathname + "?" + params.toString();
        message.textContent = "Payment received. Returning to QuadOS...";

        // The checkout was opened from a real button click, so top navigation
        // is permitted in browsers that restrict automatic iframe navigation.
        try {{
            window.top.location.assign(target);
        }} catch (e) {{
            try {{
                window.parent.location.assign(target);
            }} catch (e2) {{
                message.textContent = "Payment received. Please return to the QuadOS tab to complete verification.";
            }}
        }}
    }}

    button.addEventListener("click", function () {{
        button.disabled = true;
        message.textContent = "Opening secure Razorpay Checkout...";

        options.handler = function (response) {{
            returnToQuadOS(response);
        }};

        options.modal = {{
            ondismiss: function () {{
                button.disabled = false;
                message.textContent = "Payment window closed. Click Pay again to retry.";
            }}
        }};

        try {{
            const razorpay = new Razorpay(options);
            razorpay.open();
        }} catch (error) {{
            button.disabled = false;
            message.textContent = "Unable to open Razorpay Checkout. Please refresh and try again.";
            console.error(error);
        }}
    }});
}})();
</script>
</body>
</html>
"""
