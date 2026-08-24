import os
import smtplib
import sqlite3
from email.message import EmailMessage
from html import escape

DATABASE_NAME = "quados.db"


def _setting(name, default=""):
    """Read SMTP settings from Streamlit secrets first, then environment variables."""
    try:
        import streamlit as st
        value = st.secrets.get(name, None)
        if value not in (None, ""):
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


def _money(value):
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "₹0.00"


def _rows(text, empty_text="Not specified", priced_items=None):
    # Preferred: render actual cart items with the price BELOW the item name.
    if priced_items:
        rows = []
        for item in priced_items:
            if isinstance(item, dict):
                name = str(item.get("name", "Item"))
                price = item.get("price", 0)
            else:
                name = str(item)
                price = 0

            rows.append(
                '<div style="padding:13px 14px;border-bottom:1px solid #e5e7eb;">'
                f'<div style="font-size:14px;line-height:1.45;color:#202124;">{escape(name)}</div>'
                f'<div style="font-size:14px;font-weight:700;color:#111827;margin-top:4px;">{_money(price)}</div>'
                '</div>'
            )

        if rows:
            rows[-1] = rows[-1].replace(
                'border-bottom:1px solid #e5e7eb;', 'border-bottom:0;'
            )
            return "".join(rows)

    # Fallback for old calls that do not pass priced cart items.
    if not text or not str(text).strip():
        return f'<div style="padding:13px 14px;color:#6b7280;">{escape(empty_text)}</div>'

    items = [line.strip() for line in str(text).splitlines() if line.strip()]
    if len(items) == 1 and "," in items[0]:
        items = [x.strip() for x in items[0].split(",") if x.strip()]

    return "".join(
        '<div style="padding:13px 14px;border-bottom:1px solid #e5e7eb;">'
        f'<div style="font-size:14px;line-height:1.45;">{escape(item)}</div>'
        '</div>'
        for item in items
    )


def build_order_email_html(
    customer_name,
    order_id,
    device_type,
    operating_system,
    configuration,
    accessories,
    subtotal,
    discount,
    final_price,
    order_date,
    order_items=None,
):
    discount_value = float(discount or 0)
    subtotal_value = float(subtotal or 0)
    final_value = float(final_price or 0)

    discount_text = (
        f"-{_money(discount_value)}"
        if discount_value > 0
        else "₹0.00"
    )

    safe_name = escape(customer_name or "Customer")
    safe_device = escape(device_type or "Device")
    safe_os = escape(operating_system or "Not specified")
    safe_date = escape(str(order_date or ""))
    safe_order_id = escape(str(order_id))

    # order_items comes directly from the cart. Keep configuration and accessories
    # separate so the email does not duplicate accessory lines.
    priced_configuration = []
    priced_accessories = []

    for item in (order_items or []):
        if not isinstance(item, dict):
            continue
        item_name = str(item.get("name", ""))
        if item_name.lower().startswith("accessory -"):
            priced_accessories.append(item)
        else:
            priced_configuration.append(item)

    return f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuadOS Order Confirmation</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#202124;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8;padding:30px 12px;">
<tr><td align="center">
<table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">
<tr>
<td style="background:#111827;padding:26px 32px;">
<div style="font-size:28px;font-weight:800;color:#ffffff;letter-spacing:.3px;">QuadOS</div>
<div style="font-size:13px;color:#d1d5db;margin-top:5px;">Your configuration. Your choice.</div>
</td>
</tr>
<tr>
<td style="padding:34px 32px 18px;">
<div style="font-size:25px;font-weight:700;color:#111827;">Order Confirmed <span style="color:#16a34a;">✓</span></div>
<p style="font-size:15px;line-height:1.6;color:#4b5563;margin:10px 0 0;">Hello {safe_name}, your QuadOS order has been successfully placed.</p>
</td>
</tr>
<tr>
<td style="padding:10px 32px 24px;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;">
<tr>
<td style="padding:16px 18px;"><div style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.7px;">Order ID</div><div style="font-size:17px;font-weight:700;margin-top:5px;">#{safe_order_id}</div></td>
<td style="padding:16px 18px;text-align:right;"><div style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.7px;">Order Date</div><div style="font-size:14px;font-weight:600;margin-top:5px;">{safe_date}</div></td>
</tr>
</table>
</td>
</tr>
<tr>
<td style="padding:0 32px 26px;">
<div style="font-size:17px;font-weight:700;margin-bottom:12px;">Order Details</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
<tr><td style="padding:12px 15px;background:#f9fafb;color:#6b7280;width:35%;font-size:13px;">Device</td><td style="padding:12px 15px;font-weight:600;font-size:14px;">{safe_device}</td></tr>
<tr><td style="padding:12px 15px;background:#f9fafb;color:#6b7280;font-size:13px;">Operating System</td><td style="padding:12px 15px;font-weight:600;font-size:14px;">{safe_os}</td></tr>
</table>
</td>
</tr>
<tr>
<td style="padding:0 32px 26px;">
<div style="font-size:17px;font-weight:700;margin-bottom:10px;">Configuration</div>
<div style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;background:#ffffff;">{_rows(configuration, priced_items=priced_configuration)}</div>
</td>
</tr>
<tr>
<td style="padding:0 32px 26px;">
<div style="font-size:17px;font-weight:700;margin-bottom:10px;">Accessories</div>
<div style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;background:#ffffff;">{_rows(accessories, "No accessories selected", priced_items=priced_accessories)}</div>
</td>
</tr>
<tr>
<td style="padding:0 32px 30px;">
<div style="font-size:17px;font-weight:700;margin-bottom:10px;">Payment Summary</div>
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
<tr><td style="padding:12px 16px;color:#6b7280;">Subtotal</td><td align="right" style="padding:12px 16px;font-weight:600;">{_money(subtotal_value)}</td></tr>
<tr><td style="padding:12px 16px;color:#6b7280;">Discount</td><td align="right" style="padding:12px 16px;color:#16a34a;font-weight:600;">{discount_text}</td></tr>
<tr><td style="padding:15px 16px;background:#111827;color:#ffffff;font-size:16px;font-weight:700;">Total Amount</td><td align="right" style="padding:15px 16px;background:#111827;color:#ffffff;font-size:19px;font-weight:800;">{_money(final_value)}</td></tr>
</table>
</td>
</tr>
<tr>
<td style="padding:22px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;">
<div style="font-size:14px;font-weight:700;color:#111827;">Need help?</div>
<div style="font-size:13px;line-height:1.6;color:#6b7280;margin-top:5px;">Use the <b>Help &amp; Queries</b> section in QuadOS if you have any questions about your order.</div>
<div style="font-size:12px;line-height:1.6;color:#9ca3af;margin-top:16px;">This is an automated order confirmation from QuadOS. Please do not reply directly to this email.</div>
</td>
</tr>
</table>
</td></tr></table>
</body>
</html>"""


def get_latest_order_id(user_id):
    """Return the newest order ID for a user. Used immediately after order creation."""
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    row = cursor.fetchone()
    connection.close()
    return row[0] if row else None


def send_order_confirmation_email(
    recipient_email,
    customer_name,
    order_id,
    device_type,
    operating_system,
    configuration,
    accessories,
    subtotal,
    discount,
    final_price,
    order_date,
    order_items=None,
):
    """Send a professional HTML order confirmation email. Returns (success, message)."""
    if not recipient_email or "@" not in str(recipient_email):
        return False, "No valid registered email address is available."

    host = _setting("SMTP_HOST", "smtp.gmail.com")
    port = int(_setting("SMTP_PORT", "587"))
    username = _setting("SMTP_USERNAME")
    password = _setting("SMTP_PASSWORD")
    sender = _setting("EMAIL_FROM", username)

    if not username or not password or not sender:
        return False, "Email is not configured. Add SMTP_USERNAME, SMTP_PASSWORD and EMAIL_FROM to Streamlit secrets."

    msg = EmailMessage()
    msg["Subject"] = f"QuadOS Order Confirmation — Order #{order_id}"
    msg["From"] = sender
    msg["To"] = recipient_email
    msg.set_content(
        f"Hello {customer_name},\n\n"
        f"Your QuadOS order #{order_id} has been successfully placed.\n\n"
        f"Device: {device_type}\n"
        f"Operating System: {operating_system}\n"
        "Items:\n"
        + (
            "".join(
                f"  - {item.get('name', 'Item')}: {_money(item.get('price', 0))}\n"
                for item in (order_items or [])
                if isinstance(item, dict)
            )
            if order_items
            else ""
        )
        + f"\nSubtotal: {_money(subtotal)}\n"
        + f"Discount: {_money(discount)}\n"
        + f"Total: {_money(final_price)}\n\n"
        + "Thank you for choosing QuadOS."
    )
    msg.add_alternative(
        build_order_email_html(
            customer_name,
            order_id,
            device_type,
            operating_system,
            configuration,
            accessories,
            subtotal,
            discount,
            final_price,
            order_date,
            order_items=order_items,
        ),
        subtype="html",
    )

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.send_message(msg)
        return True, f"Confirmation email sent to {recipient_email}."
    except Exception as exc:
        return False, f"Order was saved, but the confirmation email could not be sent: {exc}"