import os
import smtplib
import sqlite3
from email.message import EmailMessage
from html import escape

DATABASE_NAME = "quados.db"


def _setting(name, default=""):
    """Read a setting from Streamlit Secrets first, then environment variables."""
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
    """Render cart items with price below the item name."""
    if priced_items:
        rows = []
        for item in priced_items:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "Item"))
            price = item.get("price", 0)
            rows.append(
                '<div style="padding:13px 14px;border-bottom:1px solid #e5e7eb;">'
                f'<div style="font-size:14px;line-height:1.45;color:#202124;">{escape(name)}</div>'
                f'<div style="font-size:14px;font-weight:700;color:#111827;margin-top:4px;">{_money(price)}</div>'
                '</div>'
            )
        if rows:
            rows[-1] = rows[-1].replace(
                'border-bottom:1px solid #e5e7eb;',
                'border-bottom:0;'
            )
            return "".join(rows)

    if not text or not str(text).strip():
        return (
            f'<div style="padding:13px 14px;color:#6b7280;">'
            f'{escape(empty_text)}</div>'
        )

    items = [line.strip() for line in str(text).splitlines() if line.strip()]
    if len(items) == 1 and "," in items[0]:
        items = [x.strip() for x in items[0].split(",") if x.strip()]

    rows = []
    for index, item in enumerate(items):
        border = "" if index == len(items) - 1 else "border-bottom:1px solid #e5e7eb;"
        rows.append(
            f'<div style="padding:13px 14px;{border}">'
            f'<div style="font-size:14px;line-height:1.45;">{escape(item)}</div>'
            '</div>'
        )
    return "".join(rows)


def _notification_html(title, subtitle, content, footer="This is an automated email from QuadOS."):
    """Shared professional QuadOS email shell."""
    return f'''<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>QuadOS</title>
</head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#202124;">
<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="padding:30px 12px;background:#f4f6f8;">
<tr><td align="center">
<table role="presentation" width="680" cellspacing="0" cellpadding="0" style="max-width:680px;width:100%;background:#ffffff;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">
<tr><td style="background:#111827;padding:26px 32px;">
<div style="font-size:28px;font-weight:800;color:#ffffff;letter-spacing:.3px;">QuadOS</div>
<div style="font-size:13px;color:#d1d5db;margin-top:5px;">Your configuration. Your choice.</div>
</td></tr>
<tr><td style="padding:30px 32px 12px;">
<div style="font-size:24px;font-weight:800;color:#111827;">{escape(title)}</div>
<div style="font-size:14px;color:#6b7280;margin-top:7px;">{escape(subtitle)}</div>
</td></tr>
<tr><td style="padding:16px 32px 30px;">{content}</td></tr>
<tr><td style="padding:20px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;color:#9ca3af;font-size:12px;line-height:1.6;">{escape(footer)}</td></tr>
</table>
</td></tr></table>
</body>
</html>'''


def _smtp_send(msg):
    """Send one email and return (success, message)."""
    host = _setting("SMTP_HOST", "smtp.gmail.com")
    port = int(_setting("SMTP_PORT", "587"))
    username = _setting("SMTP_USERNAME")
    password = _setting("SMTP_PASSWORD")
    sender = _setting("EMAIL_FROM", username)

    if not username or not password or not sender:
        return False, "Email is not configured. Add SMTP_USERNAME, SMTP_PASSWORD and EMAIL_FROM to Streamlit secrets."

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(username, password)
            server.send_message(msg)
        return True, "Email sent successfully."
    except Exception as exc:
        return False, str(exc)


def _admin_email():
    return _setting("ADMIN_EMAIL", _setting("SMTP_USERNAME", ""))


def get_latest_order_id(user_id):
    """Return the newest order ID for a user."""
    connection = sqlite3.connect(DATABASE_NAME)
    cursor = connection.cursor()
    cursor.execute(
        "SELECT id FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (user_id,),
    )
    row = cursor.fetchone()
    connection.close()
    return row[0] if row else None


def _split_order_items(order_items):
    configuration_items = []
    accessory_items = []
    for item in order_items or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", ""))
        if name.lower().startswith("accessory -"):
            accessory_items.append(item)
        else:
            configuration_items.append(item)
    return configuration_items, accessory_items


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
    """Professional customer order confirmation template."""
    configuration_items, accessory_items = _split_order_items(order_items)
    discount_value = float(discount or 0)
    discount_text = f"-{_money(discount_value)}" if discount_value > 0 else "₹0.00"

    safe_name = escape(customer_name or "Customer")
    safe_device = escape(device_type or "Not specified")
    safe_os = escape(operating_system or "Not specified")
    safe_date = escape(str(order_date or ""))
    safe_order_id = escape(str(order_id))

    return f'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f4f6f8;font-family:Arial,Helvetica,sans-serif;color:#202124;">
<table width="100%" cellspacing="0" cellpadding="0" style="background:#f4f6f8;padding:30px 12px;"><tr><td align="center">
<table width="680" cellspacing="0" cellpadding="0" style="max-width:680px;width:100%;background:#fff;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,.08);">
<tr><td style="background:#111827;padding:26px 32px;"><div style="font-size:28px;font-weight:800;color:#fff;">QuadOS</div><div style="font-size:13px;color:#d1d5db;margin-top:5px;">Your configuration. Your choice.</div></td></tr>
<tr><td style="padding:34px 32px 18px;"><div style="font-size:25px;font-weight:700;color:#111827;">Order Confirmed <span style="color:#16a34a;">✓</span></div><p style="font-size:15px;line-height:1.6;color:#4b5563;margin:10px 0 0;">Hello {safe_name}, your QuadOS order has been successfully placed.</p></td></tr>
<tr><td style="padding:10px 32px 24px;"><table width="100%" cellspacing="0" cellpadding="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;"><tr><td style="padding:16px 18px;"><div style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.7px;">Order ID</div><div style="font-size:17px;font-weight:700;margin-top:5px;">#{safe_order_id}</div></td><td style="padding:16px 18px;text-align:right;"><div style="font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:.7px;">Order Date</div><div style="font-size:14px;font-weight:600;margin-top:5px;">{safe_date}</div></td></tr></table></td></tr>
<tr><td style="padding:0 32px 26px;"><div style="font-size:17px;font-weight:700;margin-bottom:12px;">Order Details</div><table width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;"><tr><td style="padding:12px 15px;background:#f9fafb;color:#6b7280;width:35%;font-size:13px;">Device</td><td style="padding:12px 15px;font-weight:700;font-size:14px;">{safe_device}</td></tr><tr><td style="padding:12px 15px;background:#f9fafb;color:#6b7280;font-size:13px;">Operating System</td><td style="padding:12px 15px;font-weight:600;font-size:14px;">{safe_os}</td></tr></table></td></tr>
<tr><td style="padding:0 32px 26px;"><div style="font-size:17px;font-weight:700;margin-bottom:10px;">Configuration</div><div style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">{_rows(configuration, priced_items=configuration_items)}</div></td></tr>
<tr><td style="padding:0 32px 26px;"><div style="font-size:17px;font-weight:700;margin-bottom:10px;">Accessories</div><div style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">{_rows(accessories, "No accessories selected", priced_items=accessory_items)}</div></td></tr>
<tr><td style="padding:0 32px 30px;"><div style="font-size:17px;font-weight:700;margin-bottom:10px;">Payment Summary</div><table width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;"><tr><td style="padding:12px 16px;color:#6b7280;">Subtotal</td><td align="right" style="padding:12px 16px;font-weight:600;">{_money(subtotal)}</td></tr><tr><td style="padding:12px 16px;color:#6b7280;">Discount</td><td align="right" style="padding:12px 16px;color:#16a34a;font-weight:600;">{discount_text}</td></tr><tr><td style="padding:15px 16px;background:#111827;color:#fff;font-size:16px;font-weight:700;">Total Amount</td><td align="right" style="padding:15px 16px;background:#111827;color:#fff;font-size:19px;font-weight:800;">{_money(final_price)}</td></tr></table></td></tr>
<tr><td style="padding:22px 32px;background:#f9fafb;border-top:1px solid #e5e7eb;"><div style="font-size:14px;font-weight:700;">Need help?</div><div style="font-size:13px;line-height:1.6;color:#6b7280;margin-top:5px;">Use the <b>Help &amp; Queries</b> section in QuadOS if you have any questions about your order.</div></td></tr>
</table></td></tr></table></body></html>'''


def build_admin_order_email_html(
    customer_name,
    customer_email,
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
    """Admin version using the same QuadOS visual design as customer emails."""
    configuration_items, accessory_items = _split_order_items(order_items)
    body = f'''
<div style="font-size:13px;color:#6b7280;margin-bottom:14px;">A new order has been placed and requires admin review.</div>
<table width="100%" cellspacing="0" cellpadding="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;margin-bottom:24px;">
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;width:34%;">Order ID</td><td style="padding:12px;font-weight:800;">#{escape(str(order_id))}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Customer</td><td style="padding:12px;font-weight:600;">{escape(customer_name or "")}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Email</td><td style="padding:12px;font-weight:600;">{escape(customer_email or "")}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Device</td><td style="padding:12px;font-weight:800;">{escape(device_type or "Not specified")}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Operating System</td><td style="padding:12px;font-weight:600;">{escape(operating_system or "Not specified")}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Order Date</td><td style="padding:12px;">{escape(str(order_date or ""))}</td></tr>
</table>
<div style="font-size:17px;font-weight:700;margin-bottom:10px;">Configuration</div>
<div style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;margin-bottom:22px;">{_rows(configuration, priced_items=configuration_items)}</div>
<div style="font-size:17px;font-weight:700;margin-bottom:10px;">Accessories</div>
<div style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;margin-bottom:22px;">{_rows(accessories, "No accessories selected", priced_items=accessory_items)}</div>
<div style="font-size:17px;font-weight:700;margin-bottom:10px;">Payment Summary</div>
<table width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
<tr><td style="padding:12px;color:#6b7280;">Subtotal</td><td align="right" style="padding:12px;font-weight:600;">{_money(subtotal)}</td></tr>
<tr><td style="padding:12px;color:#6b7280;">Discount</td><td align="right" style="padding:12px;color:#16a34a;font-weight:700;">{_money(discount)}</td></tr>
<tr><td style="padding:15px;background:#111827;color:#fff;font-weight:800;">Total Amount</td><td align="right" style="padding:15px;background:#111827;color:#fff;font-size:19px;font-weight:800;">{_money(final_price)}</td></tr>
</table>'''
    return _notification_html(
        "New Order Received",
        f"Order #{order_id} • Admin notification",
        body,
        "QuadOS Admin Notification • Review this order in Admin → Manage Orders.",
    )


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
    """Send the professional order email to user and admin."""
    if not recipient_email or "@" not in str(recipient_email):
        return False, "No valid registered email address is available."

    customer_msg = EmailMessage()
    customer_msg["Subject"] = f"QuadOS Order Confirmation — Order #{order_id}"
    customer_msg["To"] = recipient_email
    customer_msg.set_content(
        f"Hello {customer_name},\n\n"
        f"Your QuadOS order #{order_id} has been successfully placed.\n\n"
        f"Device: {device_type}\n"
        f"Operating System: {operating_system}\n"
        f"Subtotal: {_money(subtotal)}\n"
        f"Discount: {_money(discount)}\n"
        f"Total: {_money(final_price)}\n"
    )
    customer_msg.add_alternative(
        build_order_email_html(
            customer_name, order_id, device_type, operating_system,
            configuration, accessories, subtotal, discount, final_price,
            order_date, order_items=order_items,
        ),
        subtype="html",
    )
    customer_ok, customer_message = _smtp_send(customer_msg)

    admin = _admin_email()
    admin_ok = True
    admin_message = ""
    if admin and "@" in admin:
        admin_msg = EmailMessage()
        admin_msg["Subject"] = f"🔔 New QuadOS Order — #{order_id}"
        admin_msg["To"] = admin
        admin_msg.set_content(
            f"New QuadOS order #{order_id}.\n"
            f"Customer: {customer_name}\nEmail: {recipient_email}\n"
            f"Device: {device_type}\nOperating System: {operating_system}\n"
            f"Total: {_money(final_price)}\n"
        )
        admin_msg.add_alternative(
            build_admin_order_email_html(
                customer_name, recipient_email, order_id, device_type,
                operating_system, configuration, accessories, subtotal,
                discount, final_price, order_date, order_items=order_items,
            ),
            subtype="html",
        )
        admin_ok, admin_message = _smtp_send(admin_msg)

    if customer_ok and admin_ok:
        return True, f"Confirmation email sent to {recipient_email} and order notification sent to admin."
    if customer_ok:
        return True, f"Confirmation email sent to {recipient_email}, but the admin notification could not be sent: {admin_message}"
    if admin_ok:
        return False, f"Order was saved, but the customer email could not be sent: {customer_message}. Admin was notified."
    return False, f"Order was saved, but email notifications could not be sent: {customer_message}"


def send_welcome_email(recipient_email, customer_name):
    if not recipient_email or "@" not in str(recipient_email):
        return False, "No valid email address is available."
    safe_name = escape(customer_name or "Customer")
    body = f'''
<div style="border:1px solid #e5e7eb;border-radius:12px;padding:22px;background:#f9fafb;">
<div style="font-size:20px;font-weight:800;color:#111827;">Welcome, {safe_name} 👋</div>
<p style="font-size:15px;line-height:1.7;color:#4b5563;">Your QuadOS account has been created successfully.</p>
<p style="font-size:14px;line-height:1.7;color:#4b5563;">You can now configure and order your custom PC or smartphone.</p>
</div>'''
    msg = EmailMessage()
    msg["Subject"] = "Welcome to QuadOS"
    msg["To"] = recipient_email
    msg.set_content(
        f"Hello {customer_name},\n\nWelcome to QuadOS! Your account has been created successfully.\n\nYou can now configure and order your custom PC or smartphone."
    )
    msg.add_alternative(
        _notification_html("Welcome to QuadOS", "Your account is ready to use.", body),
        subtype="html",
    )
    return _smtp_send(msg)


def send_new_query_admin_email(query_id, name, email, subject, question, submitted_at):
    admin = _admin_email()
    if not admin or "@" not in admin:
        return False, "ADMIN_EMAIL is not configured."

    body = f'''
<table width="100%" cellspacing="0" cellpadding="0" style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;margin-bottom:20px;">
<tr><td style="padding:12px;color:#6b7280;width:32%;">Query ID</td><td style="padding:12px;font-weight:800;">#{escape(str(query_id))}</td></tr>
<tr><td style="padding:12px;color:#6b7280;background:#fff;">Customer</td><td style="padding:12px;font-weight:600;background:#fff;">{escape(name)}</td></tr>
<tr><td style="padding:12px;color:#6b7280;">Email</td><td style="padding:12px;font-weight:600;">{escape(email)}</td></tr>
<tr><td style="padding:12px;color:#6b7280;background:#fff;">Submitted</td><td style="padding:12px;background:#fff;">{escape(str(submitted_at))}</td></tr>
</table>
<div style="font-size:18px;font-weight:800;margin-bottom:10px;">{escape(subject)}</div>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:18px;line-height:1.7;white-space:pre-wrap;">{escape(question)}</div>'''

    msg = EmailMessage()
    msg["Subject"] = f"🔔 New QuadOS Query — #{query_id}"
    msg["To"] = admin
    msg.set_content(
        f"New support query #{query_id}\nCustomer: {name}\nEmail: {email}\nSubject: {subject}\n\n{question}"
    )
    msg.add_alternative(
        _notification_html(
            "New Support Query",
            "A customer is waiting for a response.",
            body,
            "QuadOS Admin Notification • Open Admin → Queries to reply.",
        ),
        subtype="html",
    )
    return _smtp_send(msg)


def send_query_reply_email(recipient_email, customer_name, query_id, subject, reply):
    if not recipient_email or "@" not in str(recipient_email):
        return False, "No valid customer email is available."

    safe_name = escape(customer_name or "Customer")
    body = f'''
<div style="font-size:13px;color:#6b7280;margin-bottom:10px;">Query #{escape(str(query_id))}</div>
<div style="font-size:18px;font-weight:800;margin-bottom:12px;">{escape(subject or "Support Query")}</div>
<div style="background:#f9fafb;border:1px solid #e5e7eb;border-radius:10px;padding:18px;line-height:1.7;white-space:pre-wrap;">{escape(reply or "")}</div>
<p style="font-size:13px;color:#6b7280;margin-top:18px;">Open QuadOS → Help &amp; Queries to continue the conversation.</p>'''

    msg = EmailMessage()
    msg["Subject"] = f"QuadOS Support Reply — Query #{query_id}"
    msg["To"] = recipient_email
    msg.set_content(
        f"Hello {customer_name},\n\nQuadOS support has replied to Query #{query_id}.\n\nSubject: {subject}\n\n{reply}"
    )
    msg.add_alternative(
        _notification_html(
            "Support Reply",
            f"Hello {safe_name}, QuadOS support has replied to your query.",
            body,
            "QuadOS Support Notification • Open Help & Queries to continue.",
        ),
        subtype="html",
    )
    return _smtp_send(msg)


def send_order_status_email(recipient_email, customer_name, order_id, status):
    if not recipient_email or "@" not in str(recipient_email):
        return False, "No valid customer email is available."

    safe_status = escape(status or "Placed")
    body = f'''
<table width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;">
<tr><td style="padding:13px;background:#f9fafb;color:#6b7280;width:35%;">Order ID</td><td style="padding:13px;font-weight:800;">#{escape(str(order_id))}</td></tr>
<tr><td style="padding:13px;background:#f9fafb;color:#6b7280;">Customer</td><td style="padding:13px;font-weight:600;">{escape(customer_name or "Customer")}</td></tr>
<tr><td style="padding:13px;background:#f9fafb;color:#6b7280;">New Status</td><td style="padding:13px;font-size:18px;font-weight:800;">{safe_status}</td></tr>
</table>
<p style="font-size:14px;color:#4b5563;line-height:1.7;margin-top:18px;">Log in to QuadOS to view your complete order details.</p>'''

    msg = EmailMessage()
    msg["Subject"] = f"QuadOS Order #{order_id} — Status Updated"
    msg["To"] = recipient_email
    msg.set_content(
        f"Hello {customer_name},\n\nYour QuadOS order #{order_id} status is now: {status}.\n\nPlease log in to QuadOS to view your order."
    )
    msg.add_alternative(
        _notification_html(
            "Order Status Updated",
            "Your QuadOS order has been updated.",
            body,
            "QuadOS Order Notification.",
        ),
        subtype="html",
    )
    return _smtp_send(msg)


def send_order_cancellation_emails(recipient_email, customer_name, order_id, device_type, final_price):
    """Notify both customer and admin using the same professional design."""
    user_ok, user_message = send_order_status_email(
        recipient_email, customer_name, order_id, "Cancelled"
    )

    admin = _admin_email()
    admin_ok = True
    admin_message = ""

    if admin and "@" in admin:
        body = f'''
<table width="100%" cellspacing="0" cellpadding="0" style="border:1px solid #e5e7eb;border-radius:10px;overflow:hidden;margin-bottom:20px;">
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;width:34%;">Order ID</td><td style="padding:12px;font-weight:800;">#{escape(str(order_id))}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Customer</td><td style="padding:12px;font-weight:600;">{escape(customer_name or "")}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Email</td><td style="padding:12px;font-weight:600;">{escape(recipient_email or "")}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Device</td><td style="padding:12px;font-weight:700;">{escape(device_type or "Not specified")}</td></tr>
<tr><td style="padding:12px;background:#f9fafb;color:#6b7280;">Order Value</td><td style="padding:12px;font-weight:700;">{_money(final_price)}</td></tr>
<tr><td style="padding:12px;background:#fef2f2;color:#b91c1c;">Status</td><td style="padding:12px;background:#fef2f2;color:#b91c1c;font-weight:800;">Cancelled</td></tr>
</table>
<div style="background:#fff7ed;border:1px solid #fed7aa;border-radius:10px;padding:15px;color:#9a3412;font-size:13px;line-height:1.6;">Action: review the cancellation in Admin → Manage Orders.</div>'''

        msg = EmailMessage()
        msg["Subject"] = f"🔴 QuadOS Order Cancelled — #{order_id}"
        msg["To"] = admin
        msg.set_content(
            f"Order #{order_id} cancelled.\nCustomer: {customer_name}\n"
            f"Email: {recipient_email}\nDevice: {device_type}\n"
            f"Order Value: {_money(final_price)}"
        )
        msg.add_alternative(
            _notification_html(
                "Order Cancelled",
                "A customer order has been cancelled.",
                body,
                "QuadOS Admin Notification • Review the order in Admin → Manage Orders.",
            ),
            subtype="html",
        )
        admin_ok, admin_message = _smtp_send(msg)

    if user_ok and admin_ok:
        return True, "Cancellation notifications sent to customer and admin."
    if user_ok:
        return True, f"Customer notified, but the admin email failed: {admin_message}"
    if admin_ok:
        return False, f"Admin notified, but the customer email failed: {user_message}"
    return False, f"Cancellation emails could not be sent: {user_message}"


def send_password_reset_email(recipient_email, customer_name):
    """Send a confirmation after a password has been successfully reset."""
    if not recipient_email or "@" not in str(recipient_email):
        return False, "No valid customer email is available."

    body = f'''
<div style="border:1px solid #bbf7d0;background:#f0fdf4;border-radius:12px;padding:20px;">
<div style="font-size:18px;font-weight:800;color:#166534;">Password changed successfully ✓</div>
<p style="font-size:14px;line-height:1.7;color:#365314;">Hello {escape(customer_name or "Customer")}, your QuadOS password was successfully reset.</p>
<p style="font-size:13px;line-height:1.6;color:#6b7280;">For security, your password is never included in email.</p>
</div>'''

    msg = EmailMessage()
    msg["Subject"] = "QuadOS — Password Reset Successful"
    msg["To"] = recipient_email
    msg.set_content(
        f"Hello {customer_name},\n\nYour QuadOS password was successfully reset.\n\nFor security, your password is never included in email."
    )
    msg.add_alternative(
        _notification_html(
            "Password Reset Successful",
            "Your QuadOS account security has been updated.",
            body,
            "If you did not perform this action, contact QuadOS support.",
        ),
        subtype="html",
    )
    return _smtp_send(msg)
