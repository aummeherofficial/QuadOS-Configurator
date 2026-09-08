"""Razorpay Standard Checkout integration for QuadOS.

This module keeps Razorpay-specific API operations in one place.  QuadOS
creates a Razorpay Order on the server, opens Standard Checkout in the
browser using that order_id, and verifies the returned signature on the
server before treating the payment as successful.
"""

import html
import json

import razorpay


def get_client(key_id, key_secret):
    """Return an authenticated Razorpay client."""
    if not key_id or not key_secret:
        raise ValueError("Razorpay API keys are not configured.")
    return razorpay.Client(auth=(key_id, key_secret))


def create_razorpay_order(
    key_id,
    key_secret,
    amount_rupees,
    receipt,
    notes=None,
):
    """Create a Razorpay Order using the amount in INR.

    Razorpay expects the amount in the smallest currency unit (paise).
    The returned order must be passed to Standard Checkout.
    """
    amount_rupees = float(amount_rupees)
    if amount_rupees <= 0:
        raise ValueError("Payment amount must be greater than zero.")

    payload = {
        "amount": int(round(amount_rupees * 100)),
        "currency": "INR",
        "receipt": str(receipt),
    }

    if notes:
        payload["notes"] = {
            str(key): str(value)[:256]
            for key, value in dict(notes).items()
        }

    client = get_client(key_id, key_secret)
    return client.order.create(payload)


def verify_payment_signature(
    key_id,
    key_secret,
    razorpay_order_id,
    razorpay_payment_id,
    razorpay_signature,
):
    """Verify the Standard Checkout payment signature server-side.

    Returns True only when Razorpay's SDK accepts the signature.
    """
    if not all([
        razorpay_order_id,
        razorpay_payment_id,
        razorpay_signature,
    ]):
        return False

    client = get_client(key_id, key_secret)

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": str(razorpay_order_id),
            "razorpay_payment_id": str(razorpay_payment_id),
            "razorpay_signature": str(razorpay_signature),
        })
        return True
    except Exception:
        return False


def fetch_payment(key_id, key_secret, payment_id):
    """Fetch a Razorpay payment from the server."""
    client = get_client(key_id, key_secret)
    return client.payment.fetch(str(payment_id))


def is_payment_captured(payment):
    """Return True when Razorpay reports the payment as captured."""
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
    """Build the browser-side Razorpay Standard Checkout component.

    The checkout sends the successful response back to Streamlit through
    query parameters.  The secret key is never included in this HTML.
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
        "theme": {
            "color": "#ff4b4b",
        },
        "handler": "__QUADOS_PAYMENT_HANDLER__",
    }

    options_json = json.dumps(checkout_options, ensure_ascii=False)
    safe_options = html.escape(options_json, quote=False)

    return f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
</head>
<body>
<script>
const options = {safe_options};
options.handler = function (response) {{
    const params = new URLSearchParams({{
        razorpay_payment_id: response.razorpay_payment_id || "",
        razorpay_order_id: response.razorpay_order_id || "",
        razorpay_signature: response.razorpay_signature || ""
    }});
    window.parent.location.href = window.parent.location.pathname + "?" + params.toString();
}};

options.modal = {{
    ondismiss: function () {{
        window.parent.postMessage({{ type: "quados_razorpay_dismissed" }}, "*");
    }}
}};

const razorpay = new Razorpay(options);
razorpay.open();
</script>
</body>
</html>
"""
