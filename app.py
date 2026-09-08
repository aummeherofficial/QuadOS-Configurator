
import streamlit as st
import base64
from pathlib import Path
from datetime import datetime
import pandas as pd
import re
import os
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from analytics import (
    get_order_data,
    orders_by_device,
    revenue_by_device
)

from database import (
    create_tables,
    create_admin,
    create_user,
    login_user,
    get_total_users,
    get_total_orders,
    get_total_revenue,
    get_recent_orders,
    get_all_users,
    get_all_orders,
    delete_order,
    get_user_order_count,
    create_order,
    cancel_order,
    get_user_orders,
    get_all_orders_with_users,
    update_order_status,
    verify_password_reset_user,
    reset_user_password,
    admin_reset_user_password,
    delete_user,
    update_order_payment,
    mark_order_paid,
    get_order_payment,
    get_order_by_id,
    get_order_by_razorpay_order_id
)

from config import (
    CPU_OPTIONS,
    MOTHERBOARD_OPTIONS,
    RAM_OPTIONS,
    GPU_OPTIONS,
    STORAGE_OPTIONS,
    POWER_SUPPLY_OPTIONS,
    COOLING_OPTIONS,
    CABINET_OPTIONS,
    MONITOR_OPTIONS,
    KEYBOARD_OPTIONS,
    MOUSE_OPTIONS,
    ACCESSORY_OPTIONS,

    MACOS_CPU_OPTIONS,
    MACOS_RAM_OPTIONS,
    MACOS_STORAGE_OPTIONS,
    MACOS_GPU_OPTIONS,
    MACOS_DISPLAY_OPTIONS,
    MACOS_KEYBOARD_OPTIONS,
    MACOS_MOUSE_OPTIONS,
    MACOS_ACCESSORY_OPTIONS,

    IPHONE_DISPLAY_OPTIONS,
    IPHONE_BATTERY_OPTIONS,
    IPHONE_CAMERA_OPTIONS,
    IPHONE_RAM_OPTIONS,
    IPHONE_STORAGE_OPTIONS,
    IPHONE_PROCESSOR_OPTIONS,
    IPHONE_CONNECTIVITY_OPTIONS,
    IPHONE_FRAME_OPTIONS,
    IPHONE_COLOR_OPTIONS,
    IPHONE_ACCESSORY_OPTIONS,

    ANDROID_DISPLAY_OPTIONS,
    ANDROID_BATTERY_OPTIONS,
    ANDROID_CAMERA_OPTIONS,
    ANDROID_RAM_OPTIONS,
    ANDROID_STORAGE_OPTIONS,
    ANDROID_PROCESSOR_OPTIONS,
    ANDROID_CONNECTIVITY_OPTIONS,
    ANDROID_BUILD_OPTIONS,
    ANDROID_COLOR_OPTIONS,
    ANDROID_ACCESSORY_OPTIONS
)



from pricing import calculate_pc_price
from market_pricing import market_price, calculate_bundle_discount
from payment_standard import (
    create_razorpay_order,
    verify_payment_signature,
    fetch_payment,
    fetch_order_payments,
    get_captured_payment_for_order,
    is_payment_captured,
    build_checkout_html,
)
from email_service import (
    send_order_confirmation_email,
    send_order_status_email,
    send_order_cancellation_emails,
    send_welcome_email,
    send_password_reset_email,
)

from query_database import (
    create_query_table,
    create_user_query,
    get_all_queries,
    get_user_queries,
    update_query_status,
    get_query_count,
    delete_user_queries
)

st.set_page_config(
    page_title="QuadOS.",
    page_icon="assets/quados_favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)



from query_ui import (
    render_user_help_queries,
    render_admin_queries
)

ORDER_STATUS_OPTIONS = [
    "Placed",
    "Confirmed",
    "In Progress",
    "Payment Pending",
    "Completed",
    "Cancelled",
]


@st.dialog("Confirm Delete User")
def confirm_delete_user_dialog(user_id, user_name):
    st.warning(
        f"Are you sure you want to permanently delete user **{user_name}** (ID #{user_id})?"
    )
    st.write("The user's account, orders, and support queries will be permanently deleted.")
    st.write("This action cannot be undone.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Yes, Delete",
            key=f"confirm_delete_user_{user_id}",
            type="primary",
            use_container_width=True
        ):
            # Remove support queries first, then the user and their orders.
            delete_user_queries(user_id)
            if delete_user(user_id):
                st.session_state["flash_success_message"] = (
                    f"User {user_name} (ID #{user_id}) deleted successfully."
                )
                st.rerun()
            else:
                st.error("Unable to delete the selected user.")

    with col2:
        if st.button(
            "Cancel",
            key=f"cancel_delete_user_{user_id}",
            use_container_width=True
        ):
            st.rerun()



# ============================================================
# DISPLAY OPTION WITH PRICE
# ============================================================

def show_options(options):
    return [
        f"{name} — ₹{market_price(price):,.0f}"
        for name, price in options.items()
    ]


def show_options_with_none(options):
    """Return options with a zero-price Not Selected choice first."""
    return ["Not Selected — ₹0"] + [
        f"{name} — ₹{market_price(price):,.0f}"
        for name, price in options.items()
    ]


def render_offers_section():
    st.markdown(
        """
        <div style="padding:16px 20px;border-radius:15px;margin:8px 0 22px 0;
        background:linear-gradient(135deg,rgba(70,58,0,.9),rgba(25,22,4,.9));
        border:1px solid rgba(255,210,0,.35);">
        <div style="font-size:23px;font-weight:800;">🔥 QuadOS Offers</div>
        <div style="font-size:13px;opacity:.75;margin-top:4px;">
        Buy qualifying combinations and the discount is applied automatically. No coupon code required.
        </div></div>
        """,
        unsafe_allow_html=True
    )
    cols = st.columns(4)
    offers = [
        ("🖥️ PC Combo", "3%–12%", "2+ components / complete PC"),
        ("🍎 Mac Combo", "3%–10%", "2+ components / peripherals"),
        ("📱 Smartphone Combo", "3%–10%", "2+ components / accessories"),
        ("🎁 Accessories", "5%–8%", "Buy 2 or more"),
    ]
    for col, (title, discount, detail) in zip(cols, offers):
        with col:
            st.markdown(
                f"""<div style="padding:12px;border:1px solid rgba(255,255,255,.12);
                border-radius:12px;min-height:92px;">
                <b>{title}</b><br><span style="font-size:19px;font-weight:800;">{discount} OFF</span><br>
                <small style="opacity:.65;">{detail}</small></div>""",
                unsafe_allow_html=True
            )


def get_discounted_cart_totals():
    """Return cart totals using market_pricing.py as the single discount source."""
    subtotal = get_cart_total()
    percent, offer = calculate_bundle_discount(st.session_state.cart)

    discount = subtotal * percent / 100.0
    final = max(subtotal - discount, 0.0)
    return subtotal, discount, final, percent, offer


def get_razorpay_credentials():
    """Read Razorpay credentials without hardcoding secrets in the app."""
    key_id = os.getenv("RAZORPAY_KEY_ID", "")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET", "")

    try:
        key_id = st.secrets.get("RAZORPAY_KEY_ID", key_id)
        key_secret = st.secrets.get("RAZORPAY_KEY_SECRET", key_secret)
    except Exception:
        pass

    return str(key_id).strip(), str(key_secret).strip()


def initiate_razorpay_payment(
    user_id, user_name, user_email, user_phone,
    device_type, operating_system, configuration, accessories,
    subtotal, discount, final_price, order_date, order_items
):
    """Create a local pending order and its Razorpay Standard Checkout order."""
    key_id, key_secret = get_razorpay_credentials()

    if not key_id or not key_secret:
        return False, "Razorpay Test API keys are not configured.", None

    local_order_id = create_order(
        user_id=user_id,
        device_type=device_type,
        operating_system=operating_system,
        configuration=configuration,
        accessories=accessories,
        subtotal=subtotal,
        discount=discount,
        final_price=final_price,
        order_date=order_date,
        status="Payment Pending"
    )

    try:
        razorpay_order = create_razorpay_order(
            key_id=key_id,
            key_secret=key_secret,
            amount_rupees=final_price,
            receipt=f"quados_{local_order_id}",
            notes={
                "quados_order_id": local_order_id,
                "device_type": device_type,
            },
        )

        razorpay_order_id = razorpay_order.get("id")
        if not razorpay_order_id:
            raise RuntimeError("Razorpay did not return a valid order ID.")

        update_order_payment(
            local_order_id,
            "Pending",
            razorpay_order_id=razorpay_order_id
        )

        st.session_state.pending_payment = {
            "order_id": local_order_id,
            "razorpay_order_id": razorpay_order_id,
            "device_type": device_type,
            "final_price": float(final_price),
            "customer_name": user_name,
            "customer_email": user_email,
            "customer_phone": user_phone,
            "operating_system": operating_system,
            "configuration": configuration,
            "accessories": accessories,
            "subtotal": float(subtotal),
            "discount": float(discount),
            "order_date": order_date,
            "order_items": [dict(item) for item in order_items],
        }

        return True, "Razorpay order created successfully.", local_order_id

    except Exception as exc:
        update_order_payment(local_order_id, "Failed")
        update_order_status(local_order_id, "Cancelled")
        return False, f"Could not create the Razorpay order: {exc}", local_order_id


def complete_paid_order(order_id, payment_id, razorpay_order_id):
    """Mark a verified/captured Razorpay payment as a QuadOS order."""
    order = get_order_by_id(order_id)
    if not order:
        return False, "QuadOS order was not found."

    if order[1] != user_id:
        return False, "This payment does not belong to the signed-in user."

    if str(order[12] or "") != str(razorpay_order_id):
        return False, "Razorpay order does not match the QuadOS order."

    if str(order[11] or "").lower() == "paid":
        return True, "Payment was already confirmed."

    if not mark_order_paid(order_id, payment_id, razorpay_order_id):
        return False, "Could not update the order payment status."

    updated_order = get_order_by_id(order_id)
    (
        _order_id, _user_id, device_type, operating_system, configuration,
        accessories, subtotal, discount, final_price, order_date, _status,
        _payment_status, _razorpay_order_id, _payment_link_id, _payment_id,
        _payment_date, _cancelled_date
    ) = updated_order

    customer_name = user_name
    email_items = st.session_state.get("pending_payment", {}).get("order_items", [])

    email_ok, email_message = send_order_confirmation_email(
        recipient_email=user_email,
        customer_name=customer_name,
        order_id=order_id,
        device_type=device_type,
        operating_system=operating_system,
        configuration=configuration,
        accessories=accessories,
        subtotal=subtotal,
        discount=discount,
        final_price=final_price,
        order_date=order_date,
        order_items=email_items
    )

    st.session_state.order_success_message = (
        f"Payment successful. Order #{order_id} has been placed successfully. "
        + ("Confirmation email sent to your registered email." if email_ok
           else "Your order is saved, but the confirmation email could not be sent.")
    )
    st.session_state.order_email_status = email_message
    st.session_state.pop("pending_payment", None)
    st.session_state.pop("pending_payment_callback_handled", None)
    clear_cart()
    # Always land on My Orders after a confirmed payment.
    st.session_state.user_navigation = "My Orders"

    return True, "Payment confirmed successfully."


def handle_standard_razorpay_callback():
    """Verify the Standard Checkout response before updating the local order."""
    params = st.query_params
    payment_id = params.get("razorpay_payment_id")
    razorpay_order_id = params.get("razorpay_order_id")
    signature = params.get("razorpay_signature")

    if not all([payment_id, razorpay_order_id, signature]):
        return

    signature_key = f"{razorpay_order_id}:{payment_id}:{signature}"
    if st.session_state.get("pending_payment_callback_handled") == signature_key:
        return

    pending = st.session_state.get("pending_payment")
    local_order = get_order_by_razorpay_order_id(razorpay_order_id)

    if not local_order:
        st.error("Payment verification failed. The Razorpay order is not linked to a QuadOS order.")
        st.session_state.pending_payment_callback_handled = signature_key
        return

    if local_order[1] != user_id:
        st.error("Payment verification failed. This payment does not belong to your account.")
        st.session_state.pending_payment_callback_handled = signature_key
        return

    if pending and str(pending.get("order_id")) != str(local_order[0]):
        st.error("Payment verification failed. The pending order does not match the payment.")
        st.session_state.pending_payment_callback_handled = signature_key
        return

    key_id, key_secret = get_razorpay_credentials()
    if not key_id or not key_secret:
        st.error("Razorpay payment received, but API credentials are not configured.")
        return

    if not verify_payment_signature(
        key_id, key_secret, razorpay_order_id, payment_id, signature
    ):
        st.session_state.pending_payment_callback_handled = signature_key
        st.error("Payment verification failed. The Razorpay signature could not be verified.")
        return

    try:
        payment = fetch_payment(key_id, key_secret, payment_id)
    except Exception as exc:
        st.error(f"Payment verification failed while checking Razorpay: {exc}")
        return

    expected_amount = round(float(local_order[2]), 2)
    actual_amount = round(float(payment.get("amount", 0)) / 100.0, 2)
    if actual_amount != expected_amount:
        st.session_state.pending_payment_callback_handled = signature_key
        st.error("Payment verification failed. The payment amount does not match the QuadOS order.")
        return

    if not is_payment_captured(payment):
        st.session_state.pending_payment_callback_handled = signature_key
        st.warning(
            f"Payment has not been captured yet. Razorpay status: "
            f"{payment.get('status', 'unknown')}."
        )
        return

    st.session_state.pending_payment_callback_handled = signature_key
    ok, message = complete_paid_order(local_order[0], payment_id, razorpay_order_id)
    st.query_params.clear()

    if ok:
        st.success(message)
        st.rerun()
    else:
        st.error(message)


@st.fragment(run_every="2s")
def monitor_pending_razorpay_payment():
    """Poll Razorpay from the server until the pending order is captured.

    This fixes the browser/iframe return problem: even if Razorpay's handler
    cannot navigate the Streamlit page, QuadOS can independently reconcile the
    exact Razorpay order using the authenticated Razorpay API.
    """
    pending = st.session_state.get("pending_payment")
    if not pending:
        return

    key_id, key_secret = get_razorpay_credentials()
    if not key_id or not key_secret:
        return

    try:
        payment = get_captured_payment_for_order(
            key_id,
            key_secret,
            pending["razorpay_order_id"],
            pending["final_price"],
        )
    except Exception:
        # Razorpay may briefly return a transient API/network error.
        # Keep the checkout visible and try again on the next fragment run.
        return

    if not payment:
        return

    payment_id = str(payment.get("id", "")).strip()
    razorpay_order_id = str(payment.get("order_id", "")).strip()
    if not payment_id or not razorpay_order_id:
        return

    # Reuse the same server-side completion path used by the signed handler.
    ok, message = complete_paid_order(
        pending["order_id"],
        payment_id,
        razorpay_order_id,
    )

    if ok:
        st.session_state.order_success_message = (
            f"Payment successful. Order #{pending['order_id']} has been placed successfully."
        )
        st.rerun()
    else:
        st.error(message)


def render_pending_payment(device_type):
    """Render Razorpay Standard Checkout in a centered payment card."""
    pending = st.session_state.get("pending_payment")
    if not pending or pending.get("device_type") != device_type:
        return

    key_id, _ = get_razorpay_credentials()
    if not key_id:
        st.error("Razorpay Test API key is not configured.")
        return

    st.markdown(
        """
        <style>
        .quados-payment-title {
            text-align: center;
            margin-top: 10px;
            margin-bottom: 6px;
        }
        .quados-payment-subtitle {
            text-align: center;
            opacity: 0.75;
            margin-bottom: 18px;
        }
        .quados-payment-card {
            border: 1px solid rgba(128,128,128,0.28);
            border-radius: 18px;
            padding: 24px 26px 18px 26px;
            box-shadow: 0 8px 28px rgba(0,0,0,0.08);
            margin: 8px auto 18px auto;
            max-width: 760px;
        }
        .quados-payment-amount {
            text-align: center;
            font-size: 30px;
            font-weight: 800;
            margin: 8px 0 2px 0;
        }
        .quados-payment-order {
            text-align: center;
            opacity: 0.72;
            margin-bottom: 14px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="quados-payment-title"><h2>💳 Complete Your Payment</h2></div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="quados-payment-subtitle">Your configuration is ready. Complete the secure Razorpay payment to place the order.</div>',
        unsafe_allow_html=True,
    )

    # The payment view is intentionally centered and shown instead of the
    # configurator/cart while a payment is pending.
    _, center_col, _ = st.columns([1, 2.2, 1], gap="large")

    with center_col:
        st.markdown(
            f"""
            <div class="quados-payment-card">
                <div class="quados-payment-order">Order #{pending['order_id']} • {device_type}</div>
                <div class="quados-payment-amount">₹{pending['final_price']:,.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        checkout_html = build_checkout_html(
            key_id=key_id,
            razorpay_order_id=pending["razorpay_order_id"],
            amount_rupees=pending["final_price"],
            customer_name=pending.get("customer_name", ""),
            customer_email=pending.get("customer_email", ""),
            customer_phone=pending.get("customer_phone", ""),
            description=f"QuadOS {device_type} Order #{pending['order_id']}",
        )

        # Keep the checkout UI interactive, but do not depend on its iframe
        # being able to navigate the parent Streamlit page after payment.
        st.components.v1.html(checkout_html, height=360, scrolling=False)

        monitor_pending_razorpay_payment()

        st.caption(
            "Secure payment powered by Razorpay. QuadOS verifies the payment signature, "
            "amount, and captured status before placing your order."
        )


# ============================================================
# DATABASE
# ============================================================

create_tables()
create_admin()
create_query_table()


# ============================================================
# BACKGROUND IMAGE
# ============================================================

def set_background():

    image_path = Path("assets/quados_background.png")

    if image_path.exists():

        with open(image_path, "rb") as image_file:

            image_data = base64.b64encode(
                image_file.read()
            ).decode()

        st.markdown(
            f"""
            <style>

            .stApp {{
                background-image:
                    linear-gradient(
                        rgba(0, 0, 0, 0.55),
                        rgba(0, 0, 0, 0.55)
                    ),
                    url("data:image/png;base64,{image_data}");

                background-size: cover;
                background-position: center;
                background-attachment: fixed;
            }}

            </style>
            """,
            unsafe_allow_html=True
        )


set_background()


# ============================================================
# UI STYLE
# ============================================================

st.markdown(
    """
    <style>

    section[data-testid="stSidebar"] {
        background-color: rgba(5, 8, 20, 0.95);
    }

    .main-title {
        font-size: 55px;
        font-weight: bold;
        color: white;
    }

    .subtitle {
        font-size: 22px;
        color: #dddddd;
    }

    .description {
        font-size: 17px;
        color: #cccccc;
        max-width: 700px;
    }

    .quados-sidebar-brand {
        font-size: 24px;
        font-weight: 800;
        line-height: 1.1;
        margin: 0 0 2px 0;
    }

    .quados-sidebar-subtitle {
        font-size: 12px;
        opacity: .58;
        margin-bottom: 4px;
    }

    section[data-testid="stSidebar"] > div {
        height: 100vh;
    }

    section[data-testid="stSidebar"] .block-container {
        padding-top: 14px;
        padding-bottom: 10px;
    }

    section[data-testid="stSidebar"] hr {
        margin: 8px 0;
        opacity: .35;
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] {
        gap: 2px;
    }

    section[data-testid="stSidebar"] [data-testid="stRadio"] label {
        margin-bottom: 0;
    }

    section[data-testid="stSidebar"] .stCaption {
        line-height: 1.25;
    }

    /* QUADOS MODERN UI — presentation only */
    .block-container { max-width: 1480px; padding-top: 2rem; padding-bottom: 3.5rem; }
    h1, h2, h3 { letter-spacing: -0.02em; }
    h1 { margin-bottom: .35rem; }
    h2, h3 { margin-top: .75rem; }
    [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 18px; border-color: rgba(255,255,255,.11);
        background: rgba(12,15,25,.48); box-shadow: 0 12px 30px rgba(0,0,0,.10);
    }
    [data-testid="stMetric"] {
        padding: 16px 18px; border: 1px solid rgba(255,255,255,.09);
        border-radius: 15px; background: rgba(255,255,255,.035); min-height: 92px;
    }
    [data-testid="stMetricLabel"] { font-size: .78rem; opacity: .70; }
    [data-testid="stMetricValue"] { font-weight: 800; letter-spacing: -.02em; }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, textarea { border-radius: 10px !important; }
    div[data-baseweb="input"] > div:focus-within, div[data-baseweb="select"] > div:focus-within, textarea:focus {
        box-shadow: 0 0 0 1px rgba(167,139,250,.65) !important;
    }
    .stButton > button { border-radius: 10px; min-height: 42px; font-weight: 650; transition: transform .12s ease, box-shadow .12s ease; }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(0,0,0,.16); }
    .quados-page-kicker { font-size: 11px; font-weight: 700; letter-spacing: .11em; text-transform: uppercase; opacity: .56; margin-bottom: 4px; }
    .quados-page-title { font-size: 36px; line-height: 1.1; font-weight: 850; letter-spacing: -.025em; }
    .quados-page-subtitle { margin-top: 7px; font-size: 14px; line-height: 1.55; opacity: .70; max-width: 850px; }
    .quados-hero { padding: 28px 32px; border-radius: 22px; background: linear-gradient(135deg, rgba(25,31,55,.97), rgba(55,42,75,.92)); border: 1px solid rgba(255,255,255,.11); box-shadow: 0 18px 45px rgba(0,0,0,.18); margin-bottom: 24px; }
    .quados-hero-title { font-size: clamp(30px, 4vw, 46px); font-weight: 850; line-height: 1.05; letter-spacing: -.035em; }
    .quados-hero-text { margin-top: 10px; max-width: 820px; font-size: 15px; line-height: 1.65; opacity: .76; }
    .quados-guide { display: grid; grid-template-columns: repeat(5,minmax(0,1fr)); gap: 8px; margin: 0 0 22px; }
    .quados-guide-step { padding: 11px 12px; border-radius: 12px; border: 1px solid rgba(255,255,255,.09); background: rgba(255,255,255,.035); font-size: 12px; line-height: 1.35; }
    .quados-guide-step b { display: block; font-size: 13px; margin-bottom: 2px; }
    .quados-sidebar-user { padding: 12px 13px; border-radius: 12px; background: rgba(255,255,255,.045); border: 1px solid rgba(255,255,255,.08); margin-top: 8px; }
    section[data-testid="stSidebar"] [data-testid="stRadio"] > div { gap: 4px; }
    section[data-testid="stSidebar"] [data-testid="stRadio"] label { padding: 5px 7px; border-radius: 8px; }
    [data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid rgba(255,255,255,.08); }
    [data-testid="stExpander"] { border-radius: 12px; border-color: rgba(255,255,255,.09); }
    [data-testid="stAlert"] { border-radius: 12px; }
    [data-testid="stTabs"] [role="tab"] { font-weight: 650; }
    div[data-testid="stForm"] { border-radius: 16px; border-color: rgba(255,255,255,.10); background: rgba(255,255,255,.018); padding: 6px; }
    @media (max-width: 900px) { .quados-guide { grid-template-columns: 1fr 1fr; } .block-container { padding-top: 1.2rem; } }

    </style>
    """,
    unsafe_allow_html=True
)



# ============================================================
# SESSION STATE
# ============================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user" not in st.session_state:
    st.session_state.user = None

# ============================================================
# CART
# ============================================================

if "cart" not in st.session_state:
    st.session_state.cart = []

# Reset old PC selections once when this cart version is first loaded.
# This ensures the configurator starts with every component deselected.
if "pc_cart_defaults_v3" not in st.session_state:
    _pc_reset_keys = [
        "pc_cpu", "pc_motherboard", "pc_ram", "pc_gpu",
        "pc_storage", "pc_power_supply", "pc_cooling",
        "pc_cabinet", "pc_monitor", "pc_keyboard", "pc_mouse",
        "mac_cpu", "mac_ram", "mac_storage", "mac_gpu",
        "mac_display", "mac_keyboard", "mac_mouse"
    ]
    for _key in _pc_reset_keys:
        st.session_state.pop(_key, None)
    st.session_state.pc_cart_defaults_v3 = True

# Reset mobile selections once so every smartphone option starts
# as Not Selected / ₹0.
if "mobile_cart_defaults_v1" not in st.session_state:
    _mobile_reset_keys = [
        "mobile_platform",
        "iphone_display", "iphone_battery", "iphone_camera",
        "iphone_ram", "iphone_storage", "iphone_processor",
        "iphone_connectivity", "iphone_frame", "iphone_color",
        "iphone_accessories",
        "android_display", "android_battery", "android_camera",
        "android_ram", "android_storage", "android_processor",
        "android_connectivity", "android_build", "android_color",
        "android_accessories"
    ]
    for _key in _mobile_reset_keys:
        st.session_state.pop(_key, None)
    st.session_state.mobile_cart_defaults_v1 = True

def go_to_page(page_name):
    st.session_state.user_navigation = page_name


def go_to_admin_page(page_name):
    """
    Request an admin navigation change safely.

    IMPORTANT:
    Do not modify st.session_state["admin_navigation"] after the
    radio widget with that key has been created. Store the requested
    destination separately and apply it on the next rerun BEFORE
    the radio widget is instantiated.
    """
    allowed_pages = {
        "Admin Dashboard",
        "All Users",
        "Manage Orders",
        "Analytics",
        "Queries",
    }

    if page_name in allowed_pages:
        st.session_state.admin_navigation_target = page_name




# ============================================================
# CONFIGURATION PROFILES
# ============================================================

PROFILE_OPTIONS = [
    "Balanced / Everyday",
    "Gaming",
    "Office & Productivity",
    "Coding & Development",
    "Multimedia & Streaming",
    "Photography",
    "Video Editing",
    "Creative Design",
    "Social Media & Content",
    "Battery Saver",
    "Business",
    "Student"
]

PC_PROFILE_OPTIONS = [
    "Custom Build (Start Empty)",
    "Balanced / Everyday",
    "Gaming",
    "Office & Productivity",
    "Coding & Development",
    "Multimedia & Streaming",
    "Video Editing",
    "Creative Design",
    "Business",
    "Student"
]

MOBILE_PROFILE_OPTIONS = [
    "Custom Build (Start Empty)",
    "Balanced / Everyday",
    "Gaming",
    "Multimedia & Streaming",
    "Photography",
    "Social Media & Content",
    "Battery Saver",
    "Student"
]

# Each profile contains option names from config.py.
PC_PROFILE_CONFIGS = {
    "Balanced / Everyday": {
        "Windows PC": {
            "pc_cpu": "Intel Core i5-12400F", "pc_motherboard": "MSI PRO B760M-A WIFI (Intel)",
            "pc_ram": "16 GB DDR4-3200", "pc_gpu": "Integrated Graphics", "pc_storage": "1 TB NVMe SSD",
            "pc_power_supply": "650W 80+ Bronze", "pc_cooling": "DeepCool AK400 Air Cooler", "pc_cabinet": "Ant Esports Crystal X7",
            "pc_monitor": "LG 24-inch FHD IPS", "pc_keyboard": "Basic USB Keyboard", "pc_mouse": "Logitech G102/G203",
            "pc_accessories": []
        },
        "macOS": {
            "mac_cpu": "Apple M4", "mac_ram": "16 GB", "mac_storage": "512 GB SSD",
            "mac_gpu": "Integrated Apple GPU", "mac_display": "24-inch Retina Display",
            "mac_keyboard": "Magic Keyboard", "mac_mouse": "No Mouse", "mac_accessories": []
        }
    },
    "Gaming": {
        "Windows PC": {
            "pc_cpu": "Intel Core i7-14700F", "pc_motherboard": "MSI MAG B760 TOMAHAWK WIFI (Intel)",
            "pc_ram": "32 GB DDR5-6000 (16GB x2)", "pc_gpu": "NVIDIA GeForce RTX 4060 8GB", "pc_storage": "1 TB NVMe SSD",
            "pc_power_supply": "750W 80+ Gold", "pc_cooling": "DeepCool AG620 Dual-Tower Cooler", "pc_cabinet": "MSI MAG Forge 320R",
            "pc_monitor": "MSI MAG 275QF 27-inch QHD 180Hz", "pc_keyboard": "Ant Esports Mechanical Keyboard", "pc_mouse": "Gaming Mouse",
            "pc_accessories": ["Headphones"]
        },
        "macOS": {
            "mac_cpu": "Apple M4 Max", "mac_ram": "64 GB", "mac_storage": "2 TB SSD",
            "mac_gpu": "30-Core GPU", "mac_display": "32-inch Retina Display",
            "mac_keyboard": "Magic Keyboard with Touch ID", "mac_mouse": "Magic Mouse",
            "mac_accessories": ["Wireless Earphones"]
        }
    },
    "Office & Productivity": {
        "Windows PC": {
            "pc_cpu": "Intel Core i5-12400F", "pc_motherboard": "MSI PRO H610M-E (Intel)",
            "pc_ram": "16 GB DDR4-3200", "pc_gpu": "Integrated Graphics", "pc_storage": "500 GB NVMe SSD",
            "pc_power_supply": "550W 80+ Bronze", "pc_cooling": "Stock Air Cooling", "pc_cabinet": "Ant Esports ICE-211TG",
            "pc_monitor": "LG 24-inch FHD IPS", "pc_keyboard": "Basic USB Keyboard", "pc_mouse": "Logitech G102/G203",
            "pc_accessories": []
        },
        "macOS": {
            "mac_cpu": "Apple M4", "mac_ram": "16 GB", "mac_storage": "512 GB SSD",
            "mac_gpu": "Integrated Apple GPU", "mac_display": "24-inch Retina Display",
            "mac_keyboard": "Magic Keyboard", "mac_mouse": "Magic Mouse",
            "mac_accessories": []
        }
    },
    "Coding & Development": {
        "Windows PC": {
            "pc_cpu": "AMD Ryzen 7 9800X3D", "pc_motherboard": "Gigabyte B650 Gaming X AX V2 (AMD AM5)",
            "pc_ram": "32 GB DDR5-5600 (16GB x2)", "pc_gpu": "Integrated Graphics", "pc_storage": "1 TB NVMe SSD",
            "pc_power_supply": "650W 80+ Bronze", "pc_cooling": "DeepCool AK400 Air Cooler", "pc_cabinet": "Ant Esports Crystal X7",
            "pc_monitor": "MSI MAG 275QF 27-inch QHD 180Hz", "pc_keyboard": "Ant Esports Mechanical Keyboard", "pc_mouse": "Logitech G102/G203",
            "pc_accessories": []
        },
        "macOS": {
            "mac_cpu": "Apple M4 Pro", "mac_ram": "32 GB", "mac_storage": "1 TB SSD",
            "mac_gpu": "16-Core GPU", "mac_display": "27-inch Retina Display",
            "mac_keyboard": "Magic Keyboard", "mac_mouse": "Magic Trackpad",
            "mac_accessories": []
        }
    },
    "Multimedia & Streaming": {
        "Windows PC": {
            "pc_cpu": "Intel Core i7-14700F", "pc_motherboard": "MSI MAG B760 TOMAHAWK WIFI (Intel)",
            "pc_ram": "32 GB DDR5-5600 (16GB x2)", "pc_gpu": "NVIDIA GeForce RTX 4060 8GB", "pc_storage": "2 TB NVMe SSD",
            "pc_power_supply": "750W 80+ Gold", "pc_cooling": "DeepCool AG620 Dual-Tower Cooler", "pc_cabinet": "Lian Li Lancool 216",
            "pc_monitor": "MSI MAG 275QF 27-inch QHD 180Hz", "pc_keyboard": "Ant Esports Mechanical Keyboard", "pc_mouse": "Gaming Mouse",
            "pc_accessories": ["Webcam", "Headphones"]
        },
        "macOS": {
            "mac_cpu": "Apple M4 Pro", "mac_ram": "24 GB", "mac_storage": "1 TB SSD",
            "mac_gpu": "16-Core GPU", "mac_display": "27-inch Retina Display",
            "mac_keyboard": "Magic Keyboard", "mac_mouse": "Magic Mouse",
            "mac_accessories": ["Webcam", "Wireless Earphones"]
        }
    },
    "Video Editing": {
        "Windows PC": {
            "pc_cpu": "AMD Ryzen 7 9800X3D", "pc_motherboard": "MSI MPG B650 Edge WIFI (AMD AM5)",
            "pc_ram": "64 GB DDR5-6000 (32GB x2)", "pc_gpu": "AMD Radeon RX 9070 XT 16GB", "pc_storage": "2 TB NVMe SSD",
            "pc_power_supply": "850W 80+ Gold", "pc_cooling": "DeepCool LE360 AIO", "pc_cabinet": "Lian Li Lancool 216",
            "pc_monitor": "MSI MAG 275QF 27-inch QHD 180Hz", "pc_keyboard": "Ant Esports Mechanical Keyboard", "pc_mouse": "Premium Gaming Mouse",
            "pc_accessories": ["Webcam"]
        },
        "macOS": {
            "mac_cpu": "Apple M4 Max", "mac_ram": "64 GB", "mac_storage": "2 TB SSD",
            "mac_gpu": "40-Core GPU", "mac_display": "32-inch Retina Display",
            "mac_keyboard": "Magic Keyboard with Touch ID", "mac_mouse": "Magic Trackpad",
            "mac_accessories": ["External SSD 2TB"]
        }
    },
    "Creative Design": {
        "Windows PC": {
            "pc_cpu": "Intel Core i7-14700F", "pc_motherboard": "MSI MAG B760 TOMAHAWK WIFI (Intel)",
            "pc_ram": "32 GB DDR5-6000 (16GB x2)", "pc_gpu": "NVIDIA GeForce RTX 4060 8GB", "pc_storage": "1 TB NVMe SSD",
            "pc_power_supply": "750W 80+ Gold", "pc_cooling": "DeepCool AG620 Dual-Tower Cooler", "pc_cabinet": "Lian Li Lancool 216",
            "pc_monitor": "MSI MAG 275QF 27-inch QHD 180Hz", "pc_keyboard": "Ant Esports Mechanical Keyboard", "pc_mouse": "Premium Gaming Mouse",
            "pc_accessories": []
        },
        "macOS": {
            "mac_cpu": "Apple M4 Pro", "mac_ram": "32 GB", "mac_storage": "1 TB SSD",
            "mac_gpu": "20-Core GPU", "mac_display": "27-inch Retina Display",
            "mac_keyboard": "Magic Keyboard with Touch ID", "mac_mouse": "Magic Trackpad",
            "mac_accessories": []
        }
    },
    "Business": {
        "Windows PC": {
            "pc_cpu": "Intel Core i5-12400F", "pc_motherboard": "MSI PRO H610M-E (Intel)",
            "pc_ram": "16 GB DDR4-3200", "pc_gpu": "Integrated Graphics", "pc_storage": "1 TB NVMe SSD",
            "pc_power_supply": "550W 80+ Bronze", "pc_cooling": "Stock Air Cooling", "pc_cabinet": "Ant Esports ICE-211TG",
            "pc_monitor": "LG 24-inch FHD IPS", "pc_keyboard": "Basic USB Keyboard", "pc_mouse": "Logitech G102/G203",
            "pc_accessories": ["Webcam"]
        },
        "macOS": {
            "mac_cpu": "Apple M4", "mac_ram": "16 GB", "mac_storage": "1 TB SSD",
            "mac_gpu": "Integrated Apple GPU", "mac_display": "24-inch Retina Display",
            "mac_keyboard": "Magic Keyboard with Touch ID", "mac_mouse": "Magic Mouse",
            "mac_accessories": []
        }
    },
    "Student": {
        "Windows PC": {
            "pc_cpu": "Intel Core i5-12400F", "pc_motherboard": "MSI PRO H610M-E (Intel)",
            "pc_ram": "16 GB DDR4-3200", "pc_gpu": "Integrated Graphics", "pc_storage": "500 GB NVMe SSD",
            "pc_power_supply": "550W 80+ Bronze", "pc_cooling": "Stock Air Cooling", "pc_cabinet": "MSI MAG Forge 320R",
            "pc_monitor": "LG 24-inch FHD IPS", "pc_keyboard": "Basic USB Keyboard", "pc_mouse": "Logitech G102/G203",
            "pc_accessories": ["Earphones"]
        },
        "macOS": {
            "mac_cpu": "Apple M4", "mac_ram": "16 GB", "mac_storage": "512 GB SSD",
            "mac_gpu": "Integrated Apple GPU", "mac_display": "24-inch Retina Display",
            "mac_keyboard": "Magic Keyboard", "mac_mouse": "No Mouse",
            "mac_accessories": []
        }
    }
}

MOBILE_PROFILE_CONFIGS = {
    "Balanced / Everyday": {
        "iPhone": {
            "iphone_display": "6.1-inch OLED", "iphone_battery": "4000 mAh",
            "iphone_camera": "48 MP Single Camera", "iphone_ram": "6 GB",
            "iphone_storage": "128 GB", "iphone_processor": "A16 Bionic",
            "iphone_connectivity": "5G", "iphone_frame": "Aluminium", "iphone_color": "Black",
            "iphone_accessories": []
        },
        "Android": {
            "android_display": "6.5-inch AMOLED", "android_battery": "5000 mAh",
            "android_camera": "50 MP Dual Camera", "android_ram": "8 GB",
            "android_storage": "256 GB", "android_processor": "Snapdragon 7 Series",
            "android_connectivity": "5G", "android_build": "Glass", "android_color": "Black",
            "android_accessories": []
        }
    },
    "Gaming": {
        "iPhone": {
            "iphone_display": "6.7-inch OLED", "iphone_battery": "4500 mAh",
            "iphone_camera": "48 MP Dual Camera", "iphone_ram": "12 GB",
            "iphone_storage": "512 GB", "iphone_processor": "A18 Pro",
            "iphone_connectivity": "5G", "iphone_frame": "Titanium", "iphone_color": "Natural Titanium",
            "iphone_accessories": ["AirPods Pro"]
        },
        "Android": {
            "android_display": "6.8-inch AMOLED", "android_battery": "5500 mAh",
            "android_camera": "108 MP Triple Camera", "android_ram": "16 GB",
            "android_storage": "512 GB", "android_processor": "Snapdragon 8 Elite",
            "android_connectivity": "5G", "android_build": "Aluminium", "android_color": "Black",
            "android_accessories": ["Wireless Earphones", "Fast Charger"]
        }
    },
    "Multimedia & Streaming": {
        "iPhone": {
            "iphone_display": "6.7-inch OLED", "iphone_battery": "4500 mAh",
            "iphone_camera": "48 MP Dual Camera", "iphone_ram": "8 GB",
            "iphone_storage": "512 GB", "iphone_processor": "A18",
            "iphone_connectivity": "5G", "iphone_frame": "Aluminium", "iphone_color": "Blue",
            "iphone_accessories": ["AirPods"]
        },
        "Android": {
            "android_display": "6.7-inch AMOLED", "android_battery": "5000 mAh",
            "android_camera": "50 MP Triple Camera", "android_ram": "12 GB",
            "android_storage": "512 GB", "android_processor": "Snapdragon 8 Gen 3",
            "android_connectivity": "5G", "android_build": "Glass", "android_color": "Blue",
            "android_accessories": ["Wireless Earphones"]
        }
    },
    "Photography": {
        "iPhone": {
            "iphone_display": "6.3-inch OLED", "iphone_battery": "4500 mAh",
            "iphone_camera": "48 MP + 48 MP + 48 MP Pro Camera", "iphone_ram": "12 GB",
            "iphone_storage": "1 TB", "iphone_processor": "A18 Pro",
            "iphone_connectivity": "5G", "iphone_frame": "Titanium", "iphone_color": "Natural Titanium",
            "iphone_accessories": ["USB-C Cable"]
        },
        "Android": {
            "android_display": "6.7-inch AMOLED", "android_battery": "5000 mAh",
            "android_camera": "200 MP Pro Camera", "android_ram": "16 GB",
            "android_storage": "1 TB", "android_processor": "Snapdragon 8 Elite",
            "android_connectivity": "5G", "android_build": "Titanium", "android_color": "Green",
            "android_accessories": ["Fast Charger"]
        }
    },
    "Social Media & Content": {
        "iPhone": {
            "iphone_display": "6.3-inch OLED", "iphone_battery": "4000 mAh",
            "iphone_camera": "48 MP Dual Camera", "iphone_ram": "8 GB",
            "iphone_storage": "256 GB", "iphone_processor": "A18",
            "iphone_connectivity": "5G", "iphone_frame": "Aluminium", "iphone_color": "Blue",
            "iphone_accessories": ["iPhone Case", "Screen Protector"]
        },
        "Android": {
            "android_display": "6.7-inch AMOLED", "android_battery": "5000 mAh",
            "android_camera": "108 MP Triple Camera", "android_ram": "12 GB",
            "android_storage": "256 GB", "android_processor": "Snapdragon 8 Gen 3",
            "android_connectivity": "5G", "android_build": "Glass", "android_color": "Purple",
            "android_accessories": ["Android Phone Case", "Screen Protector"]
        }
    },
    "Battery Saver": {
        "iPhone": {
            "iphone_display": "6.1-inch OLED", "iphone_battery": "5000 mAh",
            "iphone_camera": "12 MP Single Camera", "iphone_ram": "6 GB",
            "iphone_storage": "128 GB", "iphone_processor": "A15 Bionic",
            "iphone_connectivity": "4G", "iphone_frame": "Aluminium", "iphone_color": "Black",
            "iphone_accessories": []
        },
        "Android": {
            "android_display": "6.5-inch AMOLED", "android_battery": "6000 mAh",
            "android_camera": "50 MP Single Camera", "android_ram": "6 GB",
            "android_storage": "128 GB", "android_processor": "Snapdragon 7 Series",
            "android_connectivity": "4G", "android_build": "Plastic", "android_color": "Black",
            "android_accessories": []
        }
    },
    "Student": {
        "iPhone": {
            "iphone_display": "6.1-inch OLED", "iphone_battery": "4000 mAh",
            "iphone_camera": "12 MP Single Camera", "iphone_ram": "6 GB",
            "iphone_storage": "128 GB", "iphone_processor": "A15 Bionic",
            "iphone_connectivity": "5G", "iphone_frame": "Aluminium", "iphone_color": "White",
            "iphone_accessories": ["Screen Protector"]
        },
        "Android": {
            "android_display": "6.5-inch AMOLED", "android_battery": "5000 mAh",
            "android_camera": "50 MP Dual Camera", "android_ram": "8 GB",
            "android_storage": "256 GB", "android_processor": "Snapdragon 7 Series",
            "android_connectivity": "5G", "android_build": "Plastic", "android_color": "Blue",
            "android_accessories": ["Screen Protector"]
        }
    }
}

def _profile_display(options, name):
    if not name or name not in options:
        return "Not Selected — ₹0"
    return f"{name} — ₹{market_price(options[name]):,.0f}"

def _set_profile_value(key, options, name):
    st.session_state[key] = _profile_display(options, name)

def _set_profile_accessories(key, options, names):
    st.session_state[key] = [
        _profile_display(options, name)
        for name in names
        if name in options
    ]

def _reset_profile_cart(device_type, operating_system):
    st.session_state.cart = []
    st.session_state.cart_device_type = device_type
    st.session_state.cart_operating_system = operating_system

def apply_pc_profile():
    profile = st.session_state.get("pc_profile", "Balanced / Everyday")
    platform = st.session_state.get("pc_platform", "Windows PC")
    config = PC_PROFILE_CONFIGS.get(profile, {}).get(platform)
    if not config:
        return

    _reset_profile_cart("PC", "macOS" if platform == "macOS" else "Windows")

    if platform == "Windows PC":
        option_groups = {
            "pc_cpu": CPU_OPTIONS, "pc_motherboard": MOTHERBOARD_OPTIONS,
            "pc_ram": RAM_OPTIONS, "pc_gpu": GPU_OPTIONS, "pc_storage": STORAGE_OPTIONS,
            "pc_power_supply": POWER_SUPPLY_OPTIONS, "pc_cooling": COOLING_OPTIONS,
            "pc_cabinet": CABINET_OPTIONS, "pc_monitor": MONITOR_OPTIONS,
            "pc_keyboard": KEYBOARD_OPTIONS, "pc_mouse": MOUSE_OPTIONS
        }
        categories = {
            "pc_cpu": ("cpu", "CPU"), "pc_motherboard": ("motherboard", "Motherboard"),
            "pc_ram": ("ram", "RAM"), "pc_gpu": ("gpu", "GPU"), "pc_storage": ("storage", "Storage"),
            "pc_power_supply": ("power_supply", "Power Supply"), "pc_cooling": ("cooling", "Cooling"),
            "pc_cabinet": ("cabinet", "Cabinet"), "pc_monitor": ("monitor", "Monitor"),
            "pc_keyboard": ("keyboard", "Keyboard"), "pc_mouse": ("mouse", "Mouse")
        }
        for key, options in option_groups.items():
            name = config.get(key)
            _set_profile_value(key, options, name)
            if name in options and name not in ("Integrated Graphics", "No Monitor", "No Keyboard", "No Mouse"):
                category, label = categories[key]
                add_to_cart(f"{label} - {name}", market_price(options[name]), category=category)
            elif name in options and options[name] > 0:
                category, label = categories[key]
                add_to_cart(f"{label} - {name}", market_price(options[name]), category=category)
        _set_profile_accessories("pc_accessories", ACCESSORY_OPTIONS, config.get("pc_accessories", []))
        for name in config.get("pc_accessories", []):
            if name in ACCESSORY_OPTIONS:
                add_to_cart("Accessory - " + name, market_price(ACCESSORY_OPTIONS[name]), category=f"accessory:{name}")
    else:
        option_groups = {
            "mac_cpu": MACOS_CPU_OPTIONS, "mac_ram": MACOS_RAM_OPTIONS,
            "mac_storage": MACOS_STORAGE_OPTIONS, "mac_gpu": MACOS_GPU_OPTIONS,
            "mac_display": MACOS_DISPLAY_OPTIONS, "mac_keyboard": MACOS_KEYBOARD_OPTIONS,
            "mac_mouse": MACOS_MOUSE_OPTIONS
        }
        categories = {
            "mac_cpu": ("processor", "Processor"), "mac_ram": ("memory", "Memory"),
            "mac_storage": ("storage", "Storage"), "mac_gpu": ("graphics", "Graphics"),
            "mac_display": ("display", "Display"), "mac_keyboard": ("keyboard", "Keyboard"),
            "mac_mouse": ("mouse", "Mouse / Trackpad")
        }
        for key, options in option_groups.items():
            name = config.get(key)
            _set_profile_value(key, options, name)
            if name in options and options[name] > 0:
                category, label = categories[key]
                add_to_cart(f"{label} - {name}", market_price(options[name]), category=category)
        _set_profile_accessories("mac_accessories", MACOS_ACCESSORY_OPTIONS, config.get("mac_accessories", []))
        for name in config.get("mac_accessories", []):
            if name in MACOS_ACCESSORY_OPTIONS:
                add_to_cart("Accessory - " + name, market_price(MACOS_ACCESSORY_OPTIONS[name]), category=f"accessory:{name}")

def apply_mobile_profile():
    profile = st.session_state.get("mobile_profile", "Balanced / Everyday")
    platform = st.session_state.get("mobile_platform", "iPhone")
    config = MOBILE_PROFILE_CONFIGS.get(profile, {}).get(platform)
    if not config:
        return

    os_name = "iOS" if platform == "iPhone" else "Android"
    _reset_profile_cart("Mobile", os_name)

    if platform == "iPhone":
        option_groups = {
            "iphone_display": IPHONE_DISPLAY_OPTIONS, "iphone_battery": IPHONE_BATTERY_OPTIONS,
            "iphone_camera": IPHONE_CAMERA_OPTIONS, "iphone_ram": IPHONE_RAM_OPTIONS,
            "iphone_storage": IPHONE_STORAGE_OPTIONS, "iphone_processor": IPHONE_PROCESSOR_OPTIONS,
            "iphone_connectivity": IPHONE_CONNECTIVITY_OPTIONS, "iphone_frame": IPHONE_FRAME_OPTIONS,
            "iphone_color": IPHONE_COLOR_OPTIONS
        }
        categories = {
            "iphone_display": ("iphone_display", "Display"), "iphone_battery": ("iphone_battery", "Battery"),
            "iphone_camera": ("iphone_camera", "Camera"), "iphone_ram": ("iphone_ram", "RAM"),
            "iphone_storage": ("iphone_storage", "Storage"), "iphone_processor": ("iphone_processor", "Processor"),
            "iphone_connectivity": ("iphone_connectivity", "Connectivity"), "iphone_frame": ("iphone_frame", "Frame"),
            "iphone_color": ("iphone_color", "Color")
        }
        accessory_key, accessory_options = "iphone_accessories", IPHONE_ACCESSORY_OPTIONS
    else:
        option_groups = {
            "android_display": ANDROID_DISPLAY_OPTIONS, "android_battery": ANDROID_BATTERY_OPTIONS,
            "android_camera": ANDROID_CAMERA_OPTIONS, "android_ram": ANDROID_RAM_OPTIONS,
            "android_storage": ANDROID_STORAGE_OPTIONS, "android_processor": ANDROID_PROCESSOR_OPTIONS,
            "android_connectivity": ANDROID_CONNECTIVITY_OPTIONS, "android_build": ANDROID_BUILD_OPTIONS,
            "android_color": ANDROID_COLOR_OPTIONS
        }
        categories = {
            "android_display": ("android_display", "Display"), "android_battery": ("android_battery", "Battery"),
            "android_camera": ("android_camera", "Camera"), "android_ram": ("android_ram", "RAM"),
            "android_storage": ("android_storage", "Storage"), "android_processor": ("android_processor", "Processor"),
            "android_connectivity": ("android_connectivity", "Connectivity"), "android_build": ("android_build", "Build Material"),
            "android_color": ("android_color", "Color")
        }
        accessory_key, accessory_options = "android_accessories", ANDROID_ACCESSORY_OPTIONS

    for key, options in option_groups.items():
        name = config.get(key)
        _set_profile_value(key, options, name)
        if name in options:
            category, label = categories[key]
            add_to_cart(f"{label} - {name}", market_price(options[name]), category=category)

    _set_profile_accessories(accessory_key, accessory_options, config.get(accessory_key, []))
    for name in config.get(accessory_key, []):
        if name in accessory_options:
            add_to_cart("Accessory - " + name, market_price(accessory_options[name]), category=f"mobile_accessory:{name}")

def reset_pc_component_selections():
    keys = [
        "pc_cpu", "pc_motherboard", "pc_ram", "pc_gpu", "pc_storage",
        "pc_power_supply", "pc_cooling", "pc_cabinet", "pc_monitor",
        "pc_keyboard", "pc_mouse", "pc_accessories",
        "mac_cpu", "mac_ram", "mac_storage", "mac_gpu", "mac_display",
        "mac_keyboard", "mac_mouse", "mac_accessories"
    ]
    for key in keys:
        st.session_state.pop(key, None)

def reset_mobile_component_selections():
    keys = [
        "iphone_display", "iphone_battery", "iphone_camera", "iphone_ram",
        "iphone_storage", "iphone_processor", "iphone_connectivity",
        "iphone_frame", "iphone_color", "iphone_accessories",
        "android_display", "android_battery", "android_camera", "android_ram",
        "android_storage", "android_processor", "android_connectivity",
        "android_build", "android_color", "android_accessories"
    ]
    for key in keys:
        st.session_state.pop(key, None)

def handle_pc_profile_change():
    if st.session_state.get("pc_profile") == "Custom Build (Start Empty)":
        clear_cart()
        reset_pc_component_selections()
        st.session_state.cart_device_type = "PC"
        st.session_state.cart_operating_system = "Windows"
        return
    apply_pc_profile()

def handle_mobile_profile_change():
    if st.session_state.get("mobile_profile") == "Custom Build (Start Empty)":
        clear_cart()
        reset_mobile_component_selections()
        st.session_state.cart_device_type = "Mobile"
        st.session_state.cart_operating_system = "iOS" if st.session_state.get("mobile_platform", "iPhone") == "iPhone" else "Android"
        return
    apply_mobile_profile()

def reset_profile_for_pc_platform():
    st.session_state.pc_profile = "Custom Build (Start Empty)"
    clear_cart()
    reset_pc_component_selections()
    handle_pc_platform_change()

def reset_profile_for_mobile_platform():
    st.session_state.mobile_profile = "Custom Build (Start Empty)"
    clear_cart()
    reset_mobile_component_selections()
    handle_mobile_platform_change()


# ============================================================
# ORDER VALIDATION
# ============================================================

def validate_order_cart(cart, device_type, operating_system):
    """Validate that the cart is a complete and compatible device build."""
    if not cart:
        return False, "Your cart is empty. Select components before placing the order."

    non_accessories = [
        item for item in cart
        if not str(item.get("category", "")).startswith(("accessory:", "mobile_accessory:"))
    ]

    if not non_accessories:
        return False, "Please select the device components first. Accessories cannot be ordered without a device configuration."

    selected = {item.get("category") for item in non_accessories}

    if device_type == "PC" and operating_system == "Windows":
        required = {"cpu", "motherboard", "ram", "storage", "power_supply", "cabinet", "cooling"}
        missing = required - selected
        labels = {
            "cpu":"Processor", "motherboard":"Motherboard", "ram":"RAM",
            "storage":"Storage", "power_supply":"Power Supply",
            "cabinet":"Cabinet", "cooling":"Cooling"
        }
        if missing:
            return False, "Complete these required PC components: " + ", ".join(labels[x] for x in required if x in missing) + "."

        cpu = next((i["name"] for i in non_accessories if i.get("category") == "cpu"), "")
        board = next((i["name"] for i in non_accessories if i.get("category") == "motherboard"), "")
        gpu = next((i["name"] for i in non_accessories if i.get("category") == "gpu"), "")
        psu = next((i["name"] for i in non_accessories if i.get("category") == "power_supply"), "")

        cpu_is_intel = "Intel" in cpu
        cpu_is_am4 = any(x in cpu for x in ["Ryzen 5 5500"])
        cpu_is_am5 = any(x in cpu for x in ["7500F", "7600X", "7800X3D", "9800X3D"])
        board_is_intel = "(Intel)" in board
        board_is_am4 = "AM4" in board
        board_is_am5 = "AM5" in board

        if cpu_is_intel and not board_is_intel:
            return False, "Processor and motherboard are not compatible. Select an Intel motherboard for this Intel processor."
        if cpu_is_am4 and not board_is_am4:
            return False, "Processor and motherboard are not compatible. Ryzen 5 5500 requires an AM4 motherboard such as B550."
        if cpu_is_am5 and not board_is_am5:
            return False, "Processor and motherboard are not compatible. This Ryzen processor requires an AM5 motherboard such as B650/B850."

        gpu_watts = {
            "RTX 4060": 550, "RTX 5060": 550, "RX 9060 XT": 550,
            "RX 9070 16GB": 650, "RX 9070 XT": 750
        }
        required_watt = 0
        for gpu_name, watts in gpu_watts.items():
            if gpu_name in gpu:
                required_watt = watts
                break
        psu_watt = int(re.search(r"(\d+)W", psu).group(1)) if re.search(r"(\d+)W", psu) else 0
        if required_watt and psu_watt < required_watt:
            return False, f"The selected GPU needs at least about {required_watt}W PSU. Please choose a higher-wattage power supply."

    elif device_type == "PC" and operating_system == "macOS":
        required = {"processor", "memory", "storage", "display"}
        missing = required - selected
        if missing:
            labels = {"processor":"Apple Processor", "memory":"Memory", "storage":"Storage", "display":"Display"}
            return False, "Complete these required Mac components: " + ", ".join(labels[x] for x in required if x in missing) + "."

    elif device_type == "Mobile":
        if operating_system == "iOS":
            required = {"iphone_display", "iphone_battery", "iphone_camera", "iphone_ram", "iphone_storage", "iphone_processor", "iphone_connectivity", "iphone_frame", "iphone_color"}
            labels = {"iphone_display":"Display","iphone_battery":"Battery","iphone_camera":"Camera","iphone_ram":"RAM","iphone_storage":"Storage","iphone_processor":"Processor","iphone_connectivity":"Connectivity","iphone_frame":"Frame","iphone_color":"Color"}
        else:
            required = {"android_display", "android_battery", "android_camera", "android_ram", "android_storage", "android_processor", "android_connectivity", "android_build", "android_color"}
            labels = {"android_display":"Display","android_battery":"Battery","android_camera":"Camera","android_ram":"RAM","android_storage":"Storage","android_processor":"Processor","android_connectivity":"Connectivity","android_build":"Build Material","android_color":"Color"}
        missing = required - selected
        if missing:
            return False, "Complete these required smartphone components: " + ", ".join(labels[x] for x in required if x in missing) + "."

    return True, ""


# ============================================================
# CART FUNCTIONS
# ============================================================

def add_to_cart(name, price, category=None):
    """Add an item to the cart, replacing the same component."""
    item = {
        "name": name,
        "price": float(price)
    }

    if category:
        item["category"] = category

        st.session_state.cart = [
            existing
            for existing in st.session_state.cart
            if existing.get("category") != category
        ]

    st.session_state.cart.append(item)


def update_cart_item(category, name, price, operating_system):
    """Immediately synchronize one selected component with the cart."""
    st.session_state.cart_device_type = "PC"
    st.session_state.cart_operating_system = operating_system

    add_to_cart(
        name,
        price,
        category=category
    )


def sync_selectbox_to_cart(
    widget_key,
    options,
    category,
    label_prefix,
    operating_system
):
    """Read a changed selectbox and immediately put it in the cart."""
    selected_display = st.session_state.get(
        widget_key,
        ""
    )

    selected_name = selected_display.split(" — ₹")[0]

    # "Not Selected" means the component is deselected and
    # must not appear in the cart.
    if selected_name == "Not Selected":
        st.session_state.cart = [
            item
            for item in st.session_state.cart
            if item.get("category") != category
        ]
        return

    if selected_name in options:
        update_cart_item(
            category,
            f"{label_prefix} - {selected_name}",
            market_price(options[selected_name]),
            operating_system
        )


def sync_accessories(widget_key, options, operating_system):
    """Synchronize the selected accessories with the cart."""
    st.session_state.cart_device_type = "PC"
    st.session_state.cart_operating_system = operating_system

    selected_values = st.session_state.get(
        widget_key,
        []
    )

    # Remove all current accessory items.
    st.session_state.cart = [
        item
        for item in st.session_state.cart
        if not item.get("category", "").startswith(
            "accessory:"
        )
    ]

    # Add the currently selected accessories.
    for selected in selected_values:

        name = selected.split(" — ₹")[0]

        if name in options:
            add_to_cart(
                "Accessory - " + name,
                market_price(options[name]),
                category=f"accessory:{name}"
            )


def update_mobile_cart_item(category, name, price, operating_system):
    """Immediately synchronize one selected smartphone component with the cart."""
    st.session_state.cart_device_type = "Mobile"
    st.session_state.cart_operating_system = operating_system

    add_to_cart(
        name,
        price,
        category=category
    )


def sync_mobile_selectbox_to_cart(
    widget_key,
    options,
    category,
    label_prefix,
    operating_system
):
    """Immediately synchronize one iPhone/Android selection with the cart."""
    selected_display = st.session_state.get(
        widget_key,
        "Not Selected — ₹0"
    )

    selected_name = selected_display.split(" — ₹")[0]

    if selected_name == "Not Selected":
        st.session_state.cart = [
            item
            for item in st.session_state.cart
            if item.get("category") != category
        ]
        return

    if selected_name in options:
        update_mobile_cart_item(
            category,
            f"{label_prefix} - {selected_name}",
            market_price(options[selected_name]),
            operating_system
        )


def sync_mobile_accessories(widget_key, options, operating_system):
    """Synchronize selected smartphone accessories with the cart."""
    st.session_state.cart_device_type = "Mobile"
    st.session_state.cart_operating_system = operating_system

    selected_values = st.session_state.get(
        widget_key,
        []
    )

    st.session_state.cart = [
        item
        for item in st.session_state.cart
        if not item.get("category", "").startswith(
            "mobile_accessory:"
        )
    ]

    for selected in selected_values:
        name = selected.split(" — ₹")[0]

        if name in options:
            add_to_cart(
                "Accessory - " + name,
                market_price(options[name]),
                category=f"mobile_accessory:{name}"
            )


def handle_mobile_platform_change():
    """Start a fresh smartphone cart when switching iPhone/Android."""
    st.session_state.cart = []
    st.session_state.cart_device_type = "Mobile"

    mobile_keys = [
        "iphone_display", "iphone_battery", "iphone_camera",
        "iphone_ram", "iphone_storage", "iphone_processor",
        "iphone_connectivity", "iphone_frame", "iphone_color",
        "iphone_accessories",
        "android_display", "android_battery", "android_camera",
        "android_ram", "android_storage", "android_processor",
        "android_connectivity", "android_build", "android_color",
        "android_accessories"
    ]

    for key in mobile_keys:
        if key.endswith("accessories"):
            st.session_state[key] = []
        else:
            st.session_state[key] = "Not Selected — ₹0"

    if st.session_state.get("mobile_platform") == "iPhone":
        st.session_state.cart_operating_system = "iOS"
    else:
        st.session_state.cart_operating_system = "Android"


def selected_price(options, selected_name):
    """Return zero for Not Selected, otherwise return the option price."""
    return market_price(options.get(selected_name, 0))


def handle_pc_platform_change():
    """Start a fresh PC cart and reset component selections when OS changes."""
    st.session_state.cart = []

    windows_keys = [
        "pc_cpu", "pc_motherboard", "pc_ram", "pc_gpu",
        "pc_storage", "pc_power_supply", "pc_cooling",
        "pc_cabinet", "pc_monitor", "pc_keyboard", "pc_mouse",
        "pc_accessories"
    ]

    mac_keys = [
        "mac_cpu", "mac_ram", "mac_storage", "mac_gpu",
        "mac_display", "mac_keyboard", "mac_mouse",
        "mac_accessories"
    ]

    for key in windows_keys + mac_keys:
        if key in st.session_state:
            if key.endswith("accessories"):
                st.session_state[key] = []
            else:
                st.session_state[key] = "Not Selected — ₹0"

    if st.session_state.get("pc_platform") == "macOS":
        st.session_state.cart_operating_system = "macOS"
    else:
        st.session_state.cart_operating_system = "Windows"


def remove_from_cart(index):
    if 0 <= index < len(st.session_state.cart):
        st.session_state.cart.pop(index)


def clear_cart():
    st.session_state.cart = []


def get_cart_total():
    return sum(
        item["price"]
        for item in st.session_state.cart
    )



# ============================================================
# AUTHENTICATION VALIDATION
# ============================================================

EMAIL_PATTERN = re.compile(
    r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
)


def normalize_email(email):
    return email.strip().lower()


def validate_email(email):
    email = normalize_email(email)
    if not email:
        return False, "Email is required."
    if len(email) > 254:
        return False, "Email is too long."
    if not EMAIL_PATTERN.fullmatch(email):
        return False, "Please enter a valid email address."
    return True, ""


def validate_password(password):
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must contain at least 8 characters."
    if len(password) > 128:
        return False, "Password must not exceed 128 characters."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number."
    return True, ""


def validate_registration(name, email, password, confirm_password, phone, address):
    name = " ".join(name.strip().split())
    if not name:
        return False, "Full name is required."
    if len(name) < 2 or len(name) > 80:
        return False, "Full name must be between 2 and 80 characters."
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]*", name):
        return False, "Full name can contain letters, spaces, apostrophes and hyphens only."

    valid_email, email_message = validate_email(email)
    if not valid_email:
        return False, email_message

    valid_password, password_message = validate_password(password)
    if not valid_password:
        return False, password_message

    if password != confirm_password:
        return False, "Passwords do not match."

    phone = phone.strip()
    if not phone:
        return False, "Phone number is required."
    if not re.fullmatch(r"[0-9+()\- ]{7,20}", phone):
        return False, "Please enter a valid phone number."

    if len(address.strip()) > 250:
        return False, "Address must not exceed 250 characters."

    return True, ""


# ============================================================
# PASSWORD RESET VALIDATION
# ============================================================

def validate_new_password(password, confirm_password):
    valid, message = validate_password(password)
    if not valid:
        return False, message

    if password != confirm_password:
        return False, "Passwords do not match."

    return True, ""


# ============================================================
# LOGIN / REGISTER / FORGOT PASSWORD
# ============================================================

if not st.session_state.logged_in:

    st.markdown("""<div class="quados-hero"><div class="quados-page-kicker">QuadOS 3.0 • Custom Device Platform</div><div class="quados-hero-title">Build it your way.</div><div class="quados-hero-text">Configure supported PCs and mobile devices, review transparent pricing, pay securely, and track every order from one place.</div></div>""", unsafe_allow_html=True)
    st.subheader("Welcome back")

    login_tab, register_tab, forgot_tab = st.tabs(
        ["Login", "Create Account", "Forgot Password"]
    )

    # ========================================================
    # LOGIN
    # ========================================================

    with login_tab:

        st.write("Use your registered email and password to continue.")

        email = st.text_input(
            "Email",
            key="login_email"
        )

        show_password = st.checkbox(
            "Show password",
            key="show_login_password"
        )

        password = st.text_input(
            "Password",
            type="default" if show_password else "password",
            key="login_password"
        )

        if st.button(
            "Login",
            key="login_button",
            use_container_width=True
        ):

            email = email.strip()
            password = password.strip()

            if email == "":
                st.warning("Please enter your email.")

            elif password == "":
                st.warning("Please enter your password.")

            else:
                user = login_user(email, password)

                if user:
                    st.session_state.logged_in = True
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error("Invalid email or password.")

    # ========================================================
    # CREATE ACCOUNT
    # ========================================================

    with register_tab:

        st.write("Create a new QuadOS account.")

        name = st.text_input("Full Name", key="register_name")
        email = st.text_input("Email", key="register_email")
        password = st.text_input(
            "Password",
            type="password",
            key="register_password"
        )
        confirm_password = st.text_input(
            "Confirm Password",
            type="password",
            key="register_confirm_password"
        )
        phone = st.text_input("Phone (required)", key="register_phone")
        address = st.text_area("Address", key="register_address")

        if st.button(
            "Create Account",
            key="create_account_button",
            use_container_width=True
        ):

            valid, message = validate_registration(
                name, email, password, confirm_password, phone, address
            )

            if not valid:
                st.error(message)
            else:
                success = create_user(
                    name.strip(),
                    email.strip(),
                    password,
                    phone.strip(),
                    address.strip()
                )

                if success:
                    welcome_ok, welcome_message = send_welcome_email(
                        email.strip().lower(), name.strip()
                    )
                    st.success("Account created successfully.")
                    if welcome_ok:
                        st.info("A welcome email was sent to your registered email.")
                    else:
                        st.warning(f"Account created, but the welcome email could not be sent: {welcome_message}")
                    st.info("You can now login with your account.")
                else:
                    st.error("This email is already registered.")

    # ========================================================
    # FORGOT PASSWORD
    # ========================================================

    with forgot_tab:

        st.write("Reset your password using your registered email and phone number.")
        st.caption("For security, QuadOS does not display existing passwords.")

        reset_email = st.text_input(
            "Registered Email",
            key="reset_email"
        )

        reset_phone = st.text_input(
            "Registered Phone Number",
            key="reset_phone"
        )

        new_password = st.text_input(
            "New Password",
            type="password",
            key="reset_new_password"
        )

        confirm_new_password = st.text_input(
            "Confirm New Password",
            type="password",
            key="reset_confirm_password"
        )

        if st.button(
            "Reset Password",
            key="reset_password_button",
            use_container_width=True
        ):

            reset_email = reset_email.strip()
            reset_phone = reset_phone.strip()

            if not reset_email:
                st.warning("Please enter your registered email.")

            elif not reset_phone:
                st.warning("Please enter your registered phone number.")

            else:
                verified_user = verify_password_reset_user(
                    reset_email,
                    reset_phone
                )

                if not verified_user:
                    st.error("Email and phone number do not match a registered user.")
                else:
                    valid, message = validate_new_password(
                        new_password,
                        confirm_new_password
                    )

                    if not valid:
                        st.error(message)
                    else:
                        changed = reset_user_password(
                            verified_user[0],
                            new_password
                        )

                        if changed:
                            reset_email_ok, reset_email_message = send_password_reset_email(
                                verified_user[2] if len(verified_user) > 2 else reset_email,
                                verified_user[1] if len(verified_user) > 1 else "Customer"
                            )
                            st.success("Password reset successfully. You can now login.")
                            if not reset_email_ok:
                                st.warning(f"Password was reset, but the confirmation email could not be sent: {reset_email_message}")
                        else:
                            st.error("Password could not be reset. Please try again.")

    st.stop()

# ============================================================
# GET CURRENT USER
# ============================================================

current_user = st.session_state.user

user_id = current_user[0]
user_name = current_user[1]
user_email = current_user[2]
user_role = current_user[6]
user_phone = current_user[4] if len(current_user) > 4 else ""

# Razorpay Standard Checkout responses return to the same Streamlit app.
if user_role != "admin":
    handle_standard_razorpay_callback()


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.markdown(
        '<div class="quados-sidebar-brand"><span>◈</span> QuadOS</div>'
        '<div class="quados-sidebar-subtitle">Custom Device Platform</div>',
        unsafe_allow_html=True
    )

    st.divider()


    # ========================================================
    # ADMIN NAVIGATION
    # ========================================================

    if user_role == "admin":

        st.write("ADMIN")

        # Apply a requested destination BEFORE the admin navigation
        # radio widget is created. This avoids:
        # StreamlitAPIException: st.session_state.admin_navigation
        # cannot be modified after the widget ... is instantiated.
        if "admin_navigation_target" in st.session_state:
            _admin_target = st.session_state.pop("admin_navigation_target")

            if _admin_target in {
                "Admin Dashboard",
                "All Users",
                "Manage Orders",
                "Analytics",
                "Queries",
            }:
                st.session_state.admin_navigation = _admin_target

        admin_pages = [
            "Admin Dashboard",
            "All Users",
            "Manage Orders",
            "Analytics",
            "Queries"
        ]

        # Recover cleanly from an older session that still has the removed
        # admin About page selected.
        if st.session_state.get("admin_navigation") not in admin_pages:
            st.session_state.admin_navigation = "Admin Dashboard"

        page = st.radio(
            "Navigation",
            admin_pages,
            key="admin_navigation"
        )


    # ========================================================
    # USER NAVIGATION
    # ========================================================


    else:

        st.write("USER")

        if "user_navigation" not in st.session_state:
            st.session_state.user_navigation = "Home"

        page = st.radio(
            "Navigation",
           [
                "Home",
                "PC Configurator",
                "Mobile Configurator",
                "My Orders",
                "My Profile",
                "Help & Queries",
                "About"
            ],
            key="user_navigation"
        )

    # Reset configurator state only when entering a configurator page.
    # Normal widget reruns on the same page keep the current cart intact.
    _current_config_page = page if page in ("PC Configurator", "Mobile Configurator") else None
    _previous_config_page = st.session_state.get("last_configurator_page")
    if _current_config_page != _previous_config_page:
        if _current_config_page == "PC Configurator":
            clear_cart()
            reset_pc_component_selections()
            st.session_state.pc_profile = "Custom Build (Start Empty)"
            st.session_state.cart_device_type = "PC"
            st.session_state.cart_operating_system = "Windows"
        elif _current_config_page == "Mobile Configurator":
            clear_cart()
            reset_mobile_component_selections()
            st.session_state.mobile_profile = "Custom Build (Start Empty)"
            st.session_state.cart_device_type = "Mobile"
            st.session_state.cart_operating_system = "iOS" if st.session_state.get("mobile_platform", "iPhone") == "iPhone" else "Android"
        st.session_state.last_configurator_page = _current_config_page


    st.divider()

    st.markdown(
        f"""<div class="quados-sidebar-user"><div style="font-size:11px;opacity:.55;text-transform:uppercase;letter-spacing:.08em;">Signed in</div><div style="font-size:14px;font-weight:750;margin-top:3px;">{user_name}</div><div style="font-size:11px;opacity:.62;margin-top:2px;">{user_role.capitalize()}</div></div>""",
        unsafe_allow_html=True
    )
    st.write("")

    if st.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False

        st.session_state.user = None

        st.rerun()



# ============================================================
# MATPLOTLIB CHART STYLE
# ============================================================

def style_chart(ax, title, ylabel):

    ax.set_title(
        title,
        fontsize=11,
        fontweight="bold",
        pad=10
    )

    ax.set_xlabel("")

    ax.set_ylabel(
        ylabel,
        fontsize=9
    )

    ax.grid(
        axis="y",
        linestyle="--",
        alpha=0.25
    )

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.tick_params(
        axis="both",
        labelsize=8
    )

    ax.legend(
        fontsize=8,
        frameon=False
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

if page == "Admin Dashboard":

    # ========================================================
    # ADMIN DASHBOARD HEADER
    # ========================================================

    st.markdown(f"""<div class="quados-hero"><div class="quados-page-kicker">QuadOS 3.0 • Administration</div><div class="quados-hero-title">Admin Dashboard</div><div class="quados-hero-text">Welcome back, {user_name}. Monitor orders, payments, customers and support activity from one structured workspace.</div></div>""", unsafe_allow_html=True)

    # ========================================================
    # LOAD DATA ONCE
    # ========================================================

    total_users = get_total_users()
    total_orders = get_total_orders()
    total_revenue = get_total_revenue()
    recent_orders = get_recent_orders()
    all_orders = get_all_orders_with_users()
    all_queries = get_all_queries()

    pending_queries = [
        q for q in all_queries
        if str(q[7] or "Pending") == "Pending"
    ]

    in_progress_queries = [
        q for q in all_queries
        if str(q[7] or "") == "In Progress"
    ]

    resolved_queries = [
        q for q in all_queries
        if str(q[7] or "") == "Resolved"
    ]

    # Use ALL orders for accurate status statistics, not only the recent 10.
    cancelled_orders = sum(
        1
        for order in all_orders
        if len(order) > 10 and str(order[10] or "Placed") == "Cancelled"
    )

    active_orders = max(total_orders - cancelled_orders, 0)

    average_order_value = (
        total_revenue / total_orders
        if total_orders > 0
        else 0
    )

    # ========================================================
    # 1. CORE KPIs — EACH IMPORTANT VALUE APPEARS ONCE
    # ========================================================

    st.subheader("Overview")

    metric1, metric2, metric3, metric4 = st.columns(4, gap="medium")

    with metric1:
        st.metric("Registered Users", f"{total_users:,}")

    with metric2:
        st.metric("Total Orders", f"{total_orders:,}")

    with metric3:
        st.metric("Total Revenue", f"₹{total_revenue:,.0f}")

    with metric4:
        st.metric(
            "Pending Queries",
            f"{len(pending_queries):,}",
            delta="Action required" if pending_queries else "All clear",
            delta_color="inverse" if pending_queries else "normal"
        )

    st.divider()

    # ========================================================
    # 2. ATTENTION — ONLY ITEMS THAT NEED ADMIN ACTION
    # ========================================================

    st.subheader("🔔 Needs Your Attention")

    if pending_queries:

        for query in pending_queries[:5]:

            query_id = query[0]
            query_name = query[2]
            query_subject = query[4]
            query_date = query[6]

            with st.container(border=True):

                q_col1, q_col2 = st.columns([5, 1.2], gap="medium")

                with q_col1:
                    st.markdown(
                        f"**#{query_id} — {query_subject}**"
                    )
                    st.caption(
                        f"{query_name} • {query_date}"
                    )

                with q_col2:
                    if st.button(
                        "Open Chat",
                        key=f"dashboard_query_{query_id}",
                        use_container_width=True
                    ):
                        go_to_admin_page("Queries")
                        st.rerun()

        if len(pending_queries) > 5:
            st.caption(
                f"+ {len(pending_queries) - 5} more pending queries."
            )

    else:
        st.success("No pending queries. You're all caught up.")

    st.divider()

    # ========================================================
    # 3. BUSINESS HEALTH — COMPLETE ORDER & PAYMENT SUMMARY
    # ========================================================

    st.subheader("📊 Business Health")

    all_status_values = [
        str(order[10] or "Placed")
        for order in all_orders
    ]
    status_counts = {status_name: all_status_values.count(status_name) for status_name in ORDER_STATUS_OPTIONS}

    # Keep payment statistics independent from order status.
    payment_rows = []
    for order in all_orders:
        order_id = order[0]
        payment_row = get_order_payment(order_id)
        payment_status = str(payment_row[4] or "Pending") if payment_row else "Pending"
        payment_rows.append(payment_status.title())

    payment_counts = {
        "Paid": payment_rows.count("Paid"),
        "Pending": payment_rows.count("Pending"),
        "Failed": payment_rows.count("Failed"),
    }

    paid_non_cancelled = []
    for order in all_orders:
        payment_row = get_order_payment(order[0])
        payment_status = str(payment_row[4] or "Pending").lower() if payment_row else "pending"
        order_status = str(order[10] or "Placed")
        if payment_status == "paid" and order_status != "Cancelled":
            paid_non_cancelled.append(float(order[8] or 0))

    total_recorded_orders = len(all_orders)
    paid_orders = payment_counts["Paid"]
    pending_payments = payment_counts["Pending"]
    failed_payments = payment_counts["Failed"]
    cancelled_orders = status_counts["Cancelled"]
    total_revenue = sum(paid_non_cancelled)
    average_order_value = total_revenue / len(paid_non_cancelled) if paid_non_cancelled else 0
    highest_order = max(paid_non_cancelled) if paid_non_cancelled else 0

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    with k1:
        st.metric("Total Orders", f"{total_recorded_orders:,}")
    with k2:
        st.metric("Paid Orders", f"{paid_orders:,}")
    with k3:
        st.metric("Pending Payment", f"{pending_payments:,}")
    with k4:
        st.metric("Cancelled Orders", f"{cancelled_orders:,}")

    k5, k6, k7, k8 = st.columns(4, gap="medium")
    with k5:
        st.metric("Failed Payment", f"{failed_payments:,}")
    with k6:
        st.metric("Total Revenue", f"₹{total_revenue:,.0f}")
    with k7:
        st.metric("Average Paid Order", f"₹{average_order_value:,.0f}")
    with k8:
        st.metric("Highest Paid Order", f"₹{highest_order:,.0f}")

    st.caption("Order activity includes the complete recorded history. Revenue includes paid, non-cancelled orders only.")

    # Complete status view instead of a misleading Active/Cancelled donut.
    st.subheader("Order & Payment Status")
    status_col, payment_col = st.columns(2, gap="large")

    with status_col:
        status_items = [(name, value) for name, value in status_counts.items() if value > 0]
        if status_items:
            fig, ax = plt.subplots(figsize=(6.4, 3.7))
            labels = [x[0] for x in status_items]
            values = [x[1] for x in status_items]
            bars = ax.barh(labels[::-1], values[::-1], color="#A78BFA", height=0.52)
            ax.bar_label(bars, labels=[str(v) for v in values[::-1]], padding=5, color="#FFFFFF", fontsize=9)
            ax.set_xlabel("Orders")
            ax.set_title("Orders by Status", loc="left", fontsize=12, fontweight="bold", color="#FFFFFF")
            ax.set_xlim(0, max(values) * 1.2 if values else 1)
            ax.grid(axis="x", linestyle="--", alpha=0.2)
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.spines["left"].set_visible(False)
            fig.patch.set_facecolor("#111318"); ax.set_facecolor("#111318")
            ax.tick_params(colors="#D7D9DE", labelsize=9)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True); plt.close(fig)
        else:
            st.info("No order status data yet.")

    with payment_col:
        payment_items = [(name, value) for name, value in payment_counts.items() if value > 0]
        if payment_items:
            fig, ax = plt.subplots(figsize=(6.4, 3.7))
            labels = [x[0] for x in payment_items]
            values = [x[1] for x in payment_items]
            bars = ax.barh(labels[::-1], values[::-1], color="#38BDF8", height=0.52)
            ax.bar_label(bars, labels=[str(v) for v in values[::-1]], padding=5, color="#FFFFFF", fontsize=9)
            ax.set_xlabel("Orders")
            ax.set_title("Orders by Payment Status", loc="left", fontsize=12, fontweight="bold", color="#FFFFFF")
            ax.set_xlim(0, max(values) * 1.2 if values else 1)
            ax.grid(axis="x", linestyle="--", alpha=0.2)
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False); ax.spines["left"].set_visible(False)
            fig.patch.set_facecolor("#111318"); ax.set_facecolor("#111318")
            ax.tick_params(colors="#D7D9DE", labelsize=9)
            plt.tight_layout()
            st.pyplot(fig, use_container_width=True); plt.close(fig)
        else:
            st.info("No payment status data yet.")

    st.divider()

    # ========================================================
    # 4. SUPPORT STATUS — WORKFLOW COUNTS, NOT DUPLICATES
    # ========================================================

    st.subheader("💬 Support Status")

    support1, support2, support3 = st.columns(3, gap="medium")

    with support1:
        st.metric("Pending", len(pending_queries))

    with support2:
        st.metric("In Progress", len(in_progress_queries))

    with support3:
        st.metric("Resolved", len(resolved_queries))

    st.divider()

    # ========================================================
    # 5. RECENT ORDERS — SINGLE TABLE ON DASHBOARD
    # ========================================================

    st.subheader("🛒 Recent Orders")

    if recent_orders:

        recent_order_rows = []

        for order in recent_orders[:10]:

            order_id = order[0]
            customer_id = order[1]
            device = order[2]
            operating_system = order[3]
            final_price = order[4]
            order_date = order[5]

            # Status may not exist in older recent-order records.
            status = order[6] if len(order) > 6 else "Placed"

            recent_order_rows.append({
                "Order ID": f"#{order_id}",
                "User ID": customer_id,
                "Device": device,
                "OS": operating_system or "-",
                "Amount": f"₹{float(final_price or 0):,.0f}",
                "Status": status or "Placed",
                "Date": str(order_date)
            })

        st.dataframe(
            pd.DataFrame(recent_order_rows),
            use_container_width=True,
            hide_index=True,
            height=350
        )

    else:
        st.info("No orders have been placed yet.")

    # ========================================================
    # 6. QUICK ORDER STATUS
    # ========================================================
    st.divider()
    st.subheader("⚡ Quick Order Status")
    st.caption("Change an order status directly from the dashboard.")

    if all_orders:
        dashboard_order_options = [
            f"#{order[0]} — {order[1]} — {order[3]} — ₹{float(order[8] or 0):,.0f}"
            for order in all_orders
        ]

        quick_col1, quick_col2, quick_col3 = st.columns([4, 2, 1.2], gap="medium")

        with quick_col1:
            selected_dashboard_order = st.selectbox(
                "Order",
                dashboard_order_options,
                key="dashboard_quick_status_order",
            )

        selected_dashboard_index = dashboard_order_options.index(selected_dashboard_order)
        selected_dashboard_order_data = all_orders[selected_dashboard_index]

        quick_order_id = selected_dashboard_order_data[0]
        quick_customer_name = selected_dashboard_order_data[1]
        quick_customer_email = selected_dashboard_order_data[2]
        quick_device_type = selected_dashboard_order_data[3]
        quick_final_price = selected_dashboard_order_data[8]
        quick_current_status = selected_dashboard_order_data[10] or "Placed"
        if quick_current_status not in ORDER_STATUS_OPTIONS:
            quick_current_status = "Placed"

        with quick_col2:
            quick_new_status = st.selectbox(
                "New Status",
                ORDER_STATUS_OPTIONS,
                index=ORDER_STATUS_OPTIONS.index(quick_current_status),
                key=f"dashboard_quick_status_{quick_order_id}",
            )

        with quick_col3:
            st.write("")
            st.write("")
            quick_update = st.button(
                "Update",
                type="primary",
                key=f"dashboard_quick_update_{quick_order_id}",
                use_container_width=True,
            )

        if quick_update:
            if quick_new_status == quick_current_status:
                st.info(f"Order #{quick_order_id} is already marked as {quick_current_status}.")
            else:
                quick_updated = update_order_status(quick_order_id, quick_new_status)

                if quick_updated:
                    if quick_new_status == "Cancelled":
                        quick_email_ok, quick_email_message = send_order_cancellation_emails(
                            recipient_email=quick_customer_email,
                            customer_name=quick_customer_name,
                            order_id=quick_order_id,
                            device_type=quick_device_type,
                            final_price=quick_final_price,
                        )
                    else:
                        quick_email_ok, quick_email_message = send_order_status_email(
                            recipient_email=quick_customer_email,
                            customer_name=quick_customer_name,
                            order_id=quick_order_id,
                            status=quick_new_status,
                        )

                    st.session_state["flash_success_message"] = (
                        f"Order #{quick_order_id} status changed to {quick_new_status}."
                    )

                    if quick_email_ok:
                        st.session_state["order_status_email_message"] = (
                            f"Customer notification sent for Order #{quick_order_id}."
                        )
                    else:
                        st.session_state["order_status_email_message"] = (
                            f"Order status was updated, but the email could not be sent: {quick_email_message}"
                        )

                    st.rerun()
                else:
                    st.error("Unable to update the order status. Please refresh the dashboard and try again.")
    else:
        st.info("There are no orders available for a quick status update.")

    st.divider()

    # ========================================================
    # 7. QUICK ADMIN ACTIONS
    # ========================================================

    st.subheader("⚡ Quick Actions")

    quick1, quick2, quick3 = st.columns(3, gap="medium")

    with quick1:
        if st.button(
            "👥 View Users",
            key="dashboard_users",
            use_container_width=True
        ):
            go_to_admin_page("All Users")
            st.rerun()

    with quick2:
        if st.button(
            "📦 Manage Orders",
            key="dashboard_manage_orders",
            use_container_width=True
        ):
            go_to_admin_page("Manage Orders")
            st.rerun()

    with quick3:
        if st.button(
            "💬 Open Queries",
            key="dashboard_queries",
            use_container_width=True
        ):
            go_to_admin_page("Queries")
            st.rerun()


# ============================================================
# ALL USERS
# ============================================================

elif page == "All Users":

    st.markdown("""<div class="quados-page-kicker">Administration</div><div class="quados-page-title">All Users</div><div class="quados-page-subtitle">Review registered customer accounts and use the available account-management actions when required.</div>""", unsafe_allow_html=True)

    users = get_all_users()

    if users:

        user_rows = []

        for user in users:
            user_id = user[0]
            name = user[1]
            email = user[2]
            phone = user[3] or "-"
            address = user[4] or "-"
            role = user[5] or "user"

            user_rows.append({
                "User ID": user_id,
                "Name": name,
                "Email": email,
                "Phone": phone,
                "Address": address,
                "Role": role,
                "Password": "Protected"
            })

        users_df = pd.DataFrame(user_rows)

        st.dataframe(
            users_df,
            use_container_width=True,
            hide_index=True,
            height=450
        )

        st.caption(
            f"Total users: {len(users_df)} | Passwords are protected and are not displayed."
        )

        st.divider()
        st.subheader("Reset User Password")

        normal_users = [
            user for user in users
            if (user[5] or "user").lower() == "user"
        ]

        if normal_users:

            user_options = {
                f"{user[1]} — {user[2]}": user[0]
                for user in normal_users
            }

            selected_label = st.selectbox(
                "Select User",
                list(user_options.keys()),
                key="admin_reset_user_select"
            )

            selected_user_id = user_options[selected_label]

            admin_new_password = st.text_input(
                "New Password",
                type="password",
                key="admin_new_password"
            )

            admin_confirm_password = st.text_input(
                "Confirm New Password",
                type="password",
                key="admin_confirm_password"
            )

            if st.button(
                "Reset Selected User Password",
                key="admin_reset_password_button",
                type="primary",
                use_container_width=True
            ):

                valid, message = validate_new_password(
                    admin_new_password,
                    admin_confirm_password
                )

                if not valid:
                    st.error(message)
                else:
                    changed = admin_reset_user_password(
                        selected_user_id,
                        admin_new_password
                    )

                    if changed:
                        st.success(
                            "User password reset successfully."
                        )
                    else:
                        st.error(
                            "Password reset failed."
                        )
        else:
            st.info("There are no normal users available for password reset.")

    else:
        st.info("No users found.")

    if users:
        st.divider()
        st.subheader("Delete User")
        st.warning("Deleting a user permanently removes their account, orders, and support queries.")

        deletable_users = [
            user for user in users
            if (user[5] or "user").lower() == "user"
        ]

        if deletable_users:
            delete_user_options = {
                f"{user[1]} — {user[2]} (ID #{user[0]})": (user[0], user[1])
                for user in deletable_users
            }

            delete_user_label = st.selectbox(
                "Select User to Delete",
                list(delete_user_options.keys()),
                key="admin_delete_user_select"
            )

            delete_user_id, delete_user_name = delete_user_options[delete_user_label]

            if st.button(
                "Delete Selected User",
                key="admin_delete_user_button",
                type="primary",
                use_container_width=True
            ):
                confirm_delete_user_dialog(delete_user_id, delete_user_name)
        else:
            st.info("There are no normal users available to delete.")


# ============================================================
# MANAGE ORDERS
# ============================================================

elif page == "Manage Orders":

    st.markdown("""<div class="quados-page-kicker">Administration</div><div class="quados-page-title">Manage Orders</div><div class="quados-page-subtitle">Inspect customer configurations, reconcile payment status and update order progress from one workspace.</div>""", unsafe_allow_html=True)

    orders = get_all_orders_with_users()

    if not orders:

        st.info("There are no orders to manage.")

    else:

        # ----------------------------------------------------
        # ORDERS TABLE
        # ----------------------------------------------------

        table_rows = []

        for order in orders:

            order_id = order[0]
            customer_name = order[1]
            customer_email = order[2]
            device_type = order[3]
            operating_system = order[4]
            final_price = order[8]
            order_date = order[9]
            status = order[10] or "Placed"

            table_rows.append({
                "Order ID": f"#{order_id}",
                "Customer": customer_name,
                "Email": customer_email,
                "Device": device_type,
                "OS": operating_system or "-",
                "Amount": f"₹{float(final_price or 0):,.2f}",
                "Status": status,
                "Order Date": str(order_date)
            })

        st.dataframe(
            pd.DataFrame(table_rows),
            use_container_width=True,
            hide_index=True,
            height=450
        )

        st.divider()

        # ----------------------------------------------------
        # ORDER DETAILS / ACTIONS
        # ----------------------------------------------------

        st.subheader("Order Details")

        order_options = [
            f"#{order[0]} — {order[1]} — {order[3]} — ₹{float(order[8] or 0):,.2f}"
            for order in orders
        ]

        selected_order = st.selectbox(
            "Select an order to inspect",
            order_options,
            key="admin_manage_order_select"
        )

        selected_index = order_options.index(selected_order)
        order = orders[selected_index]

        order_id = order[0]
        customer_name = order[1]
        customer_email = order[2]
        device_type = order[3]
        operating_system = order[4]
        configuration = order[5]
        accessories = order[6]
        subtotal = order[7]
        final_price = order[8]
        order_date = order[9]
        status = order[10] or "Placed"

        detail1, detail2, detail3 = st.columns(3)

        with detail1:
            st.write(f"**Customer**")
            st.write(customer_name)
            st.write(f"**Email**")
            st.write(customer_email)

        with detail2:
            st.write(f"**Device**")
            st.write(device_type)
            st.write(f"**Operating System**")
            st.write(operating_system or "-")

        with detail3:
            st.write(f"**Order Date**")
            st.write(order_date)
            st.write(f"**Status**")
            st.write(status)

        price1, price2 = st.columns(2)

        with price1:
            st.metric(
                "Subtotal",
                f"₹{float(subtotal or 0):,.2f}"
            )

        with price2:
            st.metric(
                "Final Price",
                f"₹{float(final_price or 0):,.2f}"
            )

        st.write("**Configuration**")

        st.code(
            configuration
            if configuration
            else "No configuration details"
        )

        st.write("**Accessories**")

        st.code(
            accessories
            if accessories
            else "No accessories"
        )

        # ----------------------------------------------------
        # PAYMENT MANAGEMENT
        # ----------------------------------------------------

        payment_details = get_order_payment(order_id)
        current_payment_status = str(payment_details[4] or "Pending") if payment_details else "Pending"

        st.divider()
        st.subheader("Payment Management")
        st.caption("Use these actions for orders whose payment must be reconciled manually.")

        pay_col1, pay_col2, pay_col3 = st.columns(3, gap="medium")
        with pay_col1:
            st.metric("Payment Status", current_payment_status)
        with pay_col2:
            payment_date_value = "—"
            if payment_details:
                full_order = get_order_by_id(order_id)
                if full_order and len(full_order) > 15:
                    payment_date_value = full_order[15] or "—"
            st.metric("Payment Date", str(payment_date_value))
        with pay_col3:
            if current_payment_status.lower() == "paid":
                st.success("Payment confirmed")
            elif current_payment_status.lower() == "failed":
                st.error("Payment failed")
            else:
                st.warning("Payment pending")

        if current_payment_status.lower() != "paid" and status != "Cancelled":
            pay_action1, pay_action2 = st.columns(2, gap="medium")
            with pay_action1:
                if st.button("Mark as Paid", type="primary", key=f"manual_paid_{order_id}", use_container_width=True):
                    if mark_order_paid(order_id):
                        st.session_state["flash_success_message"] = f"Order #{order_id} marked as paid."
                        st.rerun()
                    else:
                        st.error("Could not mark this order as paid. Check that it is not cancelled or already paid.")
            with pay_action2:
                if st.button("Mark as Failed", key=f"manual_failed_{order_id}", use_container_width=True):
                    if update_order_payment(order_id, "Failed"):
                        st.session_state["flash_success_message"] = f"Payment for Order #{order_id} marked as failed."
                        st.rerun()
                    else:
                        st.error("Could not update the payment status.")
        elif current_payment_status.lower() == "paid":
            st.info("This payment is already confirmed. Paid orders cannot be changed back to Pending or Failed.")
        else:
            st.info("Cancelled orders cannot be marked as paid.")

        # ----------------------------------------------------
        # UPDATE ORDER STATUS
        # ----------------------------------------------------

        st.divider()
        st.subheader("Update Order Status")

        current_status = status if status in ORDER_STATUS_OPTIONS else "Placed"

        new_status = st.selectbox(
            "Order Status",
            ORDER_STATUS_OPTIONS,
            index=ORDER_STATUS_OPTIONS.index(current_status),
            key=f"admin_order_status_{order_id}",
        )

        if st.button(
            "Update Order Status",
            type="primary",
            key=f"update_admin_order_status_{order_id}",
            use_container_width=True,
        ):
            # Do not send duplicate notifications when the admin
            # saves the same status again.
            if new_status == current_status:
                st.info(f"Order #{order_id} is already marked as {current_status}.")
            else:
                updated = update_order_status(order_id, new_status)

                if updated:
                    # The database update is the source of truth.
                    # Email failure must never undo a successful status update.
                    if new_status == "Cancelled":
                        email_ok, email_message = send_order_cancellation_emails(
                            recipient_email=customer_email,
                            customer_name=customer_name,
                            order_id=order_id,
                            device_type=device_type,
                            final_price=final_price,
                        )
                    else:
                        email_ok, email_message = send_order_status_email(
                            recipient_email=customer_email,
                            customer_name=customer_name,
                            order_id=order_id,
                            status=new_status,
                        )

                    st.session_state["flash_success_message"] = (
                        f"Order #{order_id} status changed to {new_status}."
                    )

                    if email_ok:
                        st.session_state["order_status_email_message"] = (
                            f"Customer notification sent for Order #{order_id}."
                        )
                    else:
                        st.session_state["order_status_email_message"] = (
                            f"Order status was updated, but the email could not be sent: "
                            f"{email_message}"
                        )

                    st.rerun()
                else:
                    st.error(
                        "Unable to update the order status. "
                        "Please refresh the page and try again."
                    )

        # ----------------------------------------------------
        # DELETE ORDER

        st.divider()
        delete_col, _ = st.columns([1, 3])

        with delete_col:
            if st.button(
                "Delete Order",
                type="primary",
                key=f"delete_admin_order_{order_id}",
                use_container_width=True
            ):
                st.session_state["confirm_delete_order_id"] = order_id

        # ----------------------------------------------------
        # DELETE CONFIRMATION
        # ----------------------------------------------------

        if st.session_state.get("confirm_delete_order_id") == order_id:

            @st.dialog("Confirm Delete")
            def confirm_delete_order_dialog():
                confirm_id = st.session_state.get("confirm_delete_order_id")

                st.warning(
                    f"Are you sure you want to permanently delete Order #{confirm_id}?"
                )
                st.write("This action cannot be undone.")

                yes_col, cancel_col = st.columns(2)

                with yes_col:
                    if st.button(
                        "Yes, Delete",
                        type="primary",
                        use_container_width=True,
                        key=f"confirm_delete_{confirm_id}"
                    ):
                        delete_order(confirm_id)

                        st.session_state.pop("confirm_delete_order_id", None)

                        st.session_state["flash_success_message"] = (
                            f"Order #{confirm_id} deleted successfully."
                        )

                        st.rerun()

                with cancel_col:
                    if st.button(
                        "Cancel",
                        use_container_width=True,
                        key=f"cancel_delete_{confirm_id}"
                    ):
                        st.session_state.pop("confirm_delete_order_id", None)
                        st.rerun()

            confirm_delete_order_dialog()


# ============================================================
# ANALYTICS
# ============================================================

elif page == "Analytics":

    st.markdown("""<div class="quados-page-kicker">Administration</div><div class="quados-page-title">QuadOS Analytics</div><div class="quados-page-subtitle">Understand order activity, payment outcomes, device choices and business trends using recorded order history.</div>""", unsafe_allow_html=True)
    st.caption("Complete order, payment, revenue and exception history.")
    st.divider()

    data = get_order_data()

    if data.empty:
        st.info("No order data available for analytics yet.")
    else:
        data = data.copy()
        data["order_date"] = pd.to_datetime(data["order_date"], errors="coerce")
        data["payment_date"] = pd.to_datetime(data["payment_date"], errors="coerce")
        data["cancelled_date"] = pd.to_datetime(data["cancelled_date"], errors="coerce")
        data["final_price"] = pd.to_numeric(data["final_price"], errors="coerce").fillna(0)
        data["device_type"] = data["device_type"].fillna("Unknown").astype(str)
        data["operating_system"] = data["operating_system"].fillna("Unknown").astype(str)
        data["status"] = data["status"].fillna("Placed").astype(str)
        data["payment_status"] = data["payment_status"].fillna("Pending").astype(str)

        total_orders = len(data)
        paid = data["payment_status"].str.lower().eq("paid")
        cancelled = data["status"].str.lower().eq("cancelled")
        paid_active = paid & ~cancelled
        pending = data["payment_status"].str.lower().eq("pending")
        failed = data["payment_status"].str.lower().eq("failed")

        total_revenue = data.loc[paid_active, "final_price"].sum()
        paid_values = data.loc[paid_active, "final_price"]
        average_paid = paid_values.mean() if not paid_values.empty else 0
        highest_paid = paid_values.max() if not paid_values.empty else 0

        # ====================================================
        # COMPLETE SUMMARY
        # ====================================================
        st.subheader("📊 Complete Summary")
        cards = st.columns(4, gap="medium")
        metrics = [
            ("Total Orders", total_orders, None),
            ("Paid Orders", int(paid.sum()), None),
            ("Pending Payment", int(pending.sum()), None),
            ("Cancelled Orders", int(cancelled.sum()), None),
            ("Failed Payment", int(failed.sum()), None),
            ("Total Revenue", total_revenue, "₹"),
            ("Average Paid Order", average_paid, "₹"),
            ("Highest Paid Order", highest_paid, "₹"),
        ]
        for index, (label, value, prefix) in enumerate(metrics):
            with cards[index % 4]:
                if prefix:
                    st.metric(label, f"{prefix}{float(value):,.0f}")
                else:
                    st.metric(label, f"{int(value):,}")
            if index % 4 == 3 and index < len(metrics) - 1:
                cards = st.columns(4, gap="medium")

        st.caption("Order-volume metrics use the complete recorded history. Revenue metrics use paid, non-cancelled orders only.")
        st.divider()

        CHART_BG = "#111827"; TEXT = "#E5E7EB"; MUTED = "#9CA3AF"; GRID = "#374151"
        BLUE = "#38BDF8"; ORANGE = "#F59E0B"; GREEN = "#34D399"; PURPLE = "#A78BFA"; RED = "#FB7185"; TEAL = "#2DD4BF"

        def analytics_style(ax, title, ylabel=""):
            ax.set_title(title, fontsize=13, fontweight="bold", color=TEXT, loc="left", pad=12)
            ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
            ax.tick_params(axis="both", colors=MUTED, labelsize=9)
            ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35, color=GRID)
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(GRID); ax.spines["bottom"].set_color(GRID)
            ax.set_facecolor(CHART_BG)

        def finish_chart(fig):
            fig.patch.set_facecolor(CHART_BG)
            plt.tight_layout(pad=1.5)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        def rupee_short(value):
            value=float(value)
            if abs(value)>=10_000_000: return f"₹{value/10_000_000:.2f}Cr"
            if abs(value)>=100_000: return f"₹{value/100_000:.2f}L"
            if abs(value)>=1_000: return f"₹{value/1_000:.0f}K"
            return f"₹{value:.0f}"

        # ====================================================
        # ORDER & PAYMENT STATUS
        # ====================================================
        st.subheader("📦 Order & Payment Status")
        c1, c2 = st.columns(2, gap="large")

        with c1:
            status_counts = data["status"].value_counts().reindex(ORDER_STATUS_OPTIONS, fill_value=0)
            status_counts = status_counts[status_counts > 0]
            fig, ax = plt.subplots(figsize=(7, 4))
            bars=ax.barh(status_counts.index[::-1], status_counts.values[::-1], color=PURPLE, height=.55)
            ax.bar_label(bars, labels=[str(int(v)) for v in status_counts.values[::-1]], padding=5, color=TEXT, fontsize=9)
            ax.set_xlabel("Orders", color=MUTED, fontsize=9); analytics_style(ax,"Orders by Status","")
            ax.grid(axis="x", linestyle="--", linewidth=.7, alpha=.3, color=GRID); ax.grid(axis="y", visible=False)
            finish_chart(fig)

        with c2:
            payment_counts=data["payment_status"].str.title().value_counts().reindex(["Paid","Pending","Failed"],fill_value=0)
            payment_counts=payment_counts[payment_counts>0]
            fig, ax=plt.subplots(figsize=(7,4))
            bars=ax.barh(payment_counts.index[::-1],payment_counts.values[::-1],color=BLUE,height=.55)
            ax.bar_label(bars,labels=[str(int(v)) for v in payment_counts.values[::-1]],padding=5,color=TEXT,fontsize=9)
            ax.set_xlabel("Orders",color=MUTED,fontsize=9); analytics_style(ax,"Orders by Payment Status","")
            ax.grid(axis="x",linestyle="--",linewidth=.7,alpha=.3,color=GRID); ax.grid(axis="y",visible=False)
            finish_chart(fig)

        st.divider()

        # ====================================================
        # DEVICE PERFORMANCE
        # ====================================================
        st.subheader("🖥️ Device Performance")
        c1,c2=st.columns(2,gap="large")
        with c1:
            counts=data["device_type"].value_counts().sort_values()
            fig,ax=plt.subplots(figsize=(7,4)); bars=ax.barh(counts.index,counts.values,color=BLUE,height=.55)
            ax.bar_label(bars,labels=[str(int(v)) for v in counts.values],padding=5,color=TEXT,fontsize=9)
            ax.set_xlabel("Number of orders",color=MUTED,fontsize=9); analytics_style(ax,"All Orders by Device","")
            ax.grid(axis="x",linestyle="--",linewidth=.7,alpha=.3,color=GRID);ax.grid(axis="y",visible=False);finish_chart(fig)
        with c2:
            revenue=data.loc[paid_active].groupby("device_type")["final_price"].sum().sort_values()
            if revenue.empty: st.info("No paid revenue data yet.")
            else:
                fig,ax=plt.subplots(figsize=(7,4)); bars=ax.barh(revenue.index,revenue.values,color=ORANGE,height=.55)
                ax.bar_label(bars,labels=[rupee_short(v) for v in revenue.values],padding=5,color=TEXT,fontsize=9)
                ax.set_xlabel("Paid revenue",color=MUTED,fontsize=9);analytics_style(ax,"Paid Revenue by Device","")
                ax.grid(axis="x",linestyle="--",linewidth=.7,alpha=.3,color=GRID);ax.grid(axis="y",visible=False);finish_chart(fig)

        st.divider()

        # ====================================================
        # CUSTOMER CHOICES
        # ====================================================
        st.subheader("🧩 Customer Choices")
        c1,c2=st.columns(2,gap="large")
        with c1:
            os_orders=data["operating_system"].value_counts().sort_values()
            fig,ax=plt.subplots(figsize=(7,4)); bars=ax.barh(os_orders.index,os_orders.values,color=GREEN,height=.55)
            ax.bar_label(bars,labels=[str(int(v)) for v in os_orders.values],padding=5,color=TEXT,fontsize=9)
            ax.set_xlabel("Number of orders",color=MUTED,fontsize=9);analytics_style(ax,"All Orders by Operating System","")
            ax.grid(axis="x",linestyle="--",linewidth=.7,alpha=.3,color=GRID);ax.grid(axis="y",visible=False);finish_chart(fig)
        with c2:
            os_revenue=data.loc[paid_active].groupby("operating_system")["final_price"].sum().sort_values()
            if os_revenue.empty: st.info("No paid revenue data yet.")
            else:
                fig,ax=plt.subplots(figsize=(7,4));bars=ax.barh(os_revenue.index,os_revenue.values,color=TEAL,height=.55)
                ax.bar_label(bars,labels=[rupee_short(v) for v in os_revenue.values],padding=5,color=TEXT,fontsize=9)
                ax.set_xlabel("Paid revenue",color=MUTED,fontsize=9);analytics_style(ax,"Paid Revenue by Operating System","")
                ax.grid(axis="x",linestyle="--",linewidth=.7,alpha=.3,color=GRID);ax.grid(axis="y",visible=False);finish_chart(fig)

        st.divider()

        # ====================================================
        # BUSINESS TRENDS
        # ====================================================
        st.subheader("📈 Business Trends")
        c1,c2=st.columns(2,gap="large")
        with c1:
            trend=data.dropna(subset=["order_date"]).groupby(data["order_date"].dt.normalize()).size().sort_index()
            fig,ax=plt.subplots(figsize=(7,4)); ax.plot(trend.index,trend.values,marker="o",markersize=5,linewidth=2.5,color=BLUE)
            ax.fill_between(trend.index,trend.values,alpha=.12,color=BLUE)
            analytics_style(ax,"All Orders Over Time","Orders");ax.xaxis.set_major_locator(mdates.AutoDateLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"));ax.tick_params(axis="x",rotation=30);ax.grid(axis="x",visible=False);finish_chart(fig)
        with c2:
            revenue_data=data.loc[paid_active & data["payment_date"].notna()].copy()
            if revenue_data.empty: st.info("No paid revenue dates available yet.")
            else:
                trend=revenue_data.groupby(revenue_data["payment_date"].dt.normalize())["final_price"].sum().sort_index()
                fig,ax=plt.subplots(figsize=(7,4));ax.plot(trend.index,trend.values,marker="o",markersize=5,linewidth=2.5,color=ORANGE);ax.fill_between(trend.index,trend.values,alpha=.12,color=ORANGE)
                analytics_style(ax,"Paid Revenue Over Time","Revenue");ax.xaxis.set_major_locator(mdates.AutoDateLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"));ax.tick_params(axis="x",rotation=30);ax.grid(axis="x",visible=False);ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x,pos:rupee_short(x)));finish_chart(fig)

        st.divider()

        # ====================================================
        # EXCEPTIONS & RECOVERY
        # ====================================================
        st.subheader("⚠️ Order Exceptions & Recovery")
        c1,c2,c3=st.columns(3,gap="medium")
        with c1: st.metric("Cancelled",int(cancelled.sum()))
        with c2: st.metric("Payment Pending",int(pending.sum()))
        with c3: st.metric("Payment Failed",int(failed.sum()))

        exception_frames=[]
        for label,mask,date_col in [("Cancelled",cancelled,"cancelled_date"),("Payment Pending",pending,"order_date"),("Payment Failed",failed,"order_date")]:
            subset=data.loc[mask].copy()
            subset["event_date"]=pd.to_datetime(subset[date_col],errors="coerce")
            if not subset.empty:
                counts=subset.dropna(subset=["event_date"]).groupby(subset["event_date"].dt.normalize()).size()
                for dt,val in counts.items(): exception_frames.append({"date":dt,"type":label,"count":int(val)})
        if exception_frames:
            ex=pd.DataFrame(exception_frames)
            fig,ax=plt.subplots(figsize=(14,4.5))
            for label,color in [("Cancelled",RED),("Payment Pending",PURPLE),("Payment Failed",ORANGE)]:
                part=ex[ex["type"]==label].sort_values("date")
                if not part.empty: ax.plot(part["date"],part["count"],marker="o",linewidth=2,label=label,color=color)
            analytics_style(ax,"Cancelled, Pending and Failed Orders Over Time","Orders")
            ax.xaxis.set_major_locator(mdates.AutoDateLocator());ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"));ax.tick_params(axis="x",rotation=30);ax.grid(axis="x",visible=False);ax.legend(frameon=False,fontsize=9)
            finish_chart(fig)
        else:
            st.info("No cancelled, pending or failed order events to display.")

        st.divider()

        # ====================================================
        # ORDER VALUE INSIGHTS
        # ====================================================
        st.subheader("💰 Order Value Insights")
        c1,c2=st.columns(2,gap="large")
        with c1:
            if paid_values.empty: st.info("No paid order values available yet.")
            else:
                fig,ax=plt.subplots(figsize=(7,4));ax.hist(paid_values,bins=min(10,max(4,len(paid_values))),color=PURPLE,alpha=.85,edgecolor=CHART_BG,linewidth=1.2)
                ax.axvline(average_paid,color=ORANGE,linewidth=2,linestyle="--",label=f"Average: {rupee_short(average_paid)}");ax.legend(frameon=False,fontsize=9,labelcolor=TEXT);ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x,pos:rupee_short(x)));ax.set_xlabel("Paid order value",color=MUTED,fontsize=9);analytics_style(ax,"Paid Order Value Distribution","Number of Orders");finish_chart(fig)
        with c2:
            avg_device=data.loc[paid_active].groupby("device_type")["final_price"].mean().sort_values()
            if avg_device.empty: st.info("No paid order values available yet.")
            else:
                fig,ax=plt.subplots(figsize=(7,4));bars=ax.barh(avg_device.index,avg_device.values,color=PURPLE,height=.55);ax.bar_label(bars,labels=[rupee_short(v) for v in avg_device.values],padding=5,color=TEXT,fontsize=9);ax.set_xlabel("Average paid order value",color=MUTED,fontsize=9);analytics_style(ax,"Average Paid Order Value by Device","");ax.grid(axis="x",linestyle="--",linewidth=.7,alpha=.3,color=GRID);ax.grid(axis="y",visible=False);finish_chart(fig)

        st.caption("Order dates describe when orders were created. Revenue trends use the payment date. Cancelled trends use the cancellation date when available.")


# ============================================================
# USER HOME / DASHBOARD
# ============================================================


# ============================================================

elif page == "Home":

    # ========================================================
    # WELCOME HERO
    # ========================================================
    st.markdown(f"""<div class="quados-hero"><div class="quados-page-kicker">QuadOS 3.0 • Customer Workspace</div><div class="quados-hero-title">Welcome, {user_name}</div><div class="quados-hero-text">Choose a builder below, select the components you need, review the cart summary, and complete payment when your configuration is ready.</div></div>""", unsafe_allow_html=True)

    # ========================================================
    # QUICK STATS
    # ========================================================
    order_count = get_user_order_count(user_id)
    cart_count = len(st.session_state.get("cart", []))

    stat1, stat2, stat3 = st.columns(3, gap="medium")
    with stat1:
        st.metric("My Orders", order_count)
    with stat2:
        st.metric("Cart Items", cart_count)
    with stat3:
        st.metric("Supported Devices", "PC + Mobile", help="PC and Mobile configurators")

    st.write("")

    # ========================================================
    # BUILDERS
    # ========================================================
    st.subheader("Start Building")
    st.caption("Choose a device and configure it to match your needs.")

    pc_col, mobile_col = st.columns(2, gap="large")

    with pc_col:
        st.markdown(
            """
            <div style="padding:24px;border:1px solid rgba(255,255,255,.12);border-radius:18px;
            min-height:185px;background:rgba(255,255,255,.035);">
                <div style="font-size:30px;">🖥️</div>
                <div style="font-size:24px;font-weight:750;margin-top:6px;">Custom PC</div>
                <div style="opacity:.72;margin-top:8px;line-height:1.5;">
                    Configure a Windows PC or macOS setup with supported processors, memory, storage, graphics, cooling and peripherals.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.write("")
        st.button(
            "Open PC Configurator →",
            key="home_pc_builder",
            use_container_width=True,
            on_click=go_to_page,
            args=("PC Configurator",)
        )

    with mobile_col:
        st.markdown(
            """
            <div style="padding:24px;border:1px solid rgba(255,255,255,.12);border-radius:18px;
            min-height:185px;background:rgba(255,255,255,.035);">
                <div style="font-size:30px;">📱</div>
                <div style="font-size:24px;font-weight:750;margin-top:6px;">Custom Mobile</div>
                <div style="opacity:.72;margin-top:8px;line-height:1.5;">
                    Configure a supported iPhone or Android combination with display, battery, camera, memory, storage and other options.
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
        st.write("")
        st.button(
            "Open Mobile Configurator →",
            key="home_mobile_builder",
            use_container_width=True,
            on_click=go_to_page,
            args=("Mobile Configurator",)
        )

    st.write("")

    # ========================================================
    # OFFERS
    # ========================================================
    render_offers_section()

    # ========================================================
    # HOW IT WORKS + SHORTCUTS
    # ========================================================
    left, right = st.columns([1.45, 1], gap="large")

    with left:
        st.subheader("How It Works")
        steps = [
            ("1", "Choose a builder", "Start with PC or Mobile Configurator."),
            ("2", "Select components", "Choose the supported options for your device."),
            ("3", "Review your cart", "Check selected items, pricing and applicable discounts."),
            ("4", "Place and track", "Complete payment and follow the order from My Orders."),
        ]
        for number, title, detail in steps:
            st.markdown(
                f"""
                <div style="display:flex;gap:14px;align-items:flex-start;margin:0 0 14px 0;">
                    <div style="min-width:30px;height:30px;border-radius:50%;border:1px solid rgba(255,255,255,.2);
                    display:flex;align-items:center;justify-content:center;font-weight:700;">{number}</div>
                    <div><b>{title}</b><div style="opacity:.68;font-size:13px;margin-top:2px;">{detail}</div></div>
                </div>
                """,
                unsafe_allow_html=True
            )

    with right:
        st.subheader("Quick Access")
        st.button(
            "🛒 View My Orders",
            key="home_orders",
            use_container_width=True,
            on_click=go_to_page,
            args=("My Orders",)
        )
        st.button(
            "👤 Open My Profile",
            key="home_profile",
            use_container_width=True,
            on_click=go_to_page,
            args=("My Profile",)
        )
        st.button(
            "💬 Help & Queries",
            key="home_help",
            use_container_width=True,
            on_click=go_to_page,
            args=("Help & Queries",)
        )

    st.write("")
    st.divider()
    st.caption("QuadOS helps you configure supported devices, review pricing, place orders and track them in one place.")


# ============================================================
# PC CONFIGURATOR
# ============================================================

elif page == "PC Configurator":

    if (
        st.session_state.get("pending_payment")
        and st.session_state["pending_payment"].get("device_type") == "PC"
    ):
        render_pending_payment("PC")
        st.stop()

    render_offers_section()

    st.title("PC Configurator")

    st.write("Build your custom PC by selecting each component.")
    st.markdown("""<div class="quados-guide"><div class="quados-guide-step"><b>1 · Platform</b>Windows or macOS</div><div class="quados-guide-step"><b>2 · Profile</b>Start with a ready setup</div><div class="quados-guide-step"><b>3 · Components</b>Choose required parts</div><div class="quados-guide-step"><b>4 · Accessories</b>Add extras if needed</div><div class="quados-guide-step"><b>5 · Review & Pay</b>Check the cart and place order</div></div>""", unsafe_allow_html=True)
    st.info("Choose a platform and profile first, complete the required components, add accessories if you want them, then review the Order Summary on the right. The Place Order button becomes available when the configuration is complete.")

    # ========================================================
    # PC CONFIGURATOR LAYOUT
    # ========================================================

    pc_left, pc_right = st.columns(
        [3, 1.25],
        gap="large"
    )

    # ========================================================
    # LEFT SIDE — PC CONFIGURATOR
    # ========================================================

    with pc_left:

        st.divider()

        pc_type = st.selectbox(
            "Select Platform",
            [
                "Windows PC",
                "macOS"
            ],
            key="pc_platform",
            on_change=reset_profile_for_pc_platform
        )

        if "pc_profile" not in st.session_state:
            st.session_state.pc_profile = "Custom Build (Start Empty)"

        st.selectbox(
            "Configuration Profile",
            PC_PROFILE_OPTIONS,
            key="pc_profile",
            on_change=handle_pc_profile_change,
            help="Choose a use-case and QuadOS will load a suitable starting configuration. You can change every component afterward."
        )

        st.caption("💡 Start from an empty cart, choose a profile to auto-build, or select components manually. The cart updates instantly.")

        # ====================================================
        # WINDOWS PC
        # ====================================================

        if pc_type == "Windows PC":

            st.subheader("Windows PC")

            st.write(
                "Select the components for your custom Windows PC."
            )

            st.divider()

            # ------------------------------------------------
            # PROCESSOR
            # ------------------------------------------------

            cpu_display = st.selectbox(
                "Processor",
                show_options_with_none(CPU_OPTIONS),
                key="pc_cpu",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_cpu",
                    CPU_OPTIONS,
                    "cpu",
                    "CPU",
                    "Windows"
                )
            )

            cpu = cpu_display.split(" — ₹")[0]

            # ------------------------------------------------
            # MOTHERBOARD
            # ------------------------------------------------

            motherboard_display = st.selectbox(
                "Motherboard",
                show_options_with_none(MOTHERBOARD_OPTIONS),
                key="pc_motherboard",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_motherboard",
                    MOTHERBOARD_OPTIONS,
                    "motherboard",
                    "Motherboard",
                    "Windows"
                )
            )

            motherboard = motherboard_display.split(" — ₹")[0]

            # ------------------------------------------------
            # RAM
            # ------------------------------------------------

            ram_display = st.selectbox(
                "RAM",
                show_options_with_none(RAM_OPTIONS),
                key="pc_ram",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_ram",
                    RAM_OPTIONS,
                    "ram",
                    "RAM",
                    "Windows"
                )
            )

            ram = ram_display.split(" — ₹")[0]

            # ------------------------------------------------
            # GPU
            # ------------------------------------------------

            gpu_display = st.selectbox(
                "Graphics Card",
                show_options_with_none(GPU_OPTIONS),
                key="pc_gpu",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_gpu",
                    GPU_OPTIONS,
                    "gpu",
                    "GPU",
                    "Windows"
                )
            )

            gpu = gpu_display.split(" — ₹")[0]

            # ------------------------------------------------
            # STORAGE
            # ------------------------------------------------

            storage_display = st.selectbox(
                "Storage",
                show_options_with_none(STORAGE_OPTIONS),
                key="pc_storage",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_storage",
                    STORAGE_OPTIONS,
                    "storage",
                    "Storage",
                    "Windows"
                )
            )

            storage = storage_display.split(" — ₹")[0]

            # ------------------------------------------------
            # POWER SUPPLY
            # ------------------------------------------------

            power_supply_display = st.selectbox(
                "Power Supply",
                show_options_with_none(POWER_SUPPLY_OPTIONS),
                key="pc_power_supply",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_power_supply",
                    POWER_SUPPLY_OPTIONS,
                    "power_supply",
                    "Power Supply",
                    "Windows"
                )
            )

            power_supply = power_supply_display.split(" — ₹")[0]

            # ------------------------------------------------
            # COOLING
            # ------------------------------------------------

            cooling_display = st.selectbox(
                "Cooling",
                show_options_with_none(COOLING_OPTIONS),
                key="pc_cooling",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_cooling",
                    COOLING_OPTIONS,
                    "cooling",
                    "Cooling",
                    "Windows"
                )
            )

            cooling = cooling_display.split(" — ₹")[0]

            # ------------------------------------------------
            # CABINET
            # ------------------------------------------------

            cabinet_display = st.selectbox(
                "Cabinet",
                show_options_with_none(CABINET_OPTIONS),
                key="pc_cabinet",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_cabinet",
                    CABINET_OPTIONS,
                    "cabinet",
                    "Cabinet",
                    "Windows"
                )
            )

            cabinet = cabinet_display.split(" — ₹")[0]

            # ------------------------------------------------
            # MONITOR
            # ------------------------------------------------

            monitor_display = st.selectbox(
                "Monitor",
                show_options_with_none(MONITOR_OPTIONS),
                key="pc_monitor",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_monitor",
                    MONITOR_OPTIONS,
                    "monitor",
                    "Monitor",
                    "Windows"
                )
            )

            monitor = monitor_display.split(" — ₹")[0]

            # ------------------------------------------------
            # KEYBOARD
            # ------------------------------------------------

            keyboard_display = st.selectbox(
                "Keyboard",
                show_options_with_none(KEYBOARD_OPTIONS),
                key="pc_keyboard",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_keyboard",
                    KEYBOARD_OPTIONS,
                    "keyboard",
                    "Keyboard",
                    "Windows"
                )
            )

            keyboard = keyboard_display.split(" — ₹")[0]

            # ------------------------------------------------
            # MOUSE
            # ------------------------------------------------

            mouse_display = st.selectbox(
                "Mouse",
                show_options_with_none(MOUSE_OPTIONS),
                key="pc_mouse",
                on_change=sync_selectbox_to_cart,
                args=(
                    "pc_mouse",
                    MOUSE_OPTIONS,
                    "mouse",
                    "Mouse",
                    "Windows"
                )
            )

            mouse = mouse_display.split(" — ₹")[0]

            # =================================================
            # CONFIGURATION
            # =================================================

            configuration = {
                "CPU": CPU_OPTIONS.get(cpu, 0),
                "Motherboard": MOTHERBOARD_OPTIONS.get(motherboard, 0),
                "RAM": RAM_OPTIONS.get(ram, 0),
                "GPU": GPU_OPTIONS.get(gpu, 0),
                "Storage": STORAGE_OPTIONS.get(storage, 0),
                "Power Supply": POWER_SUPPLY_OPTIONS.get(power_supply, 0),
                "Cooling": COOLING_OPTIONS.get(cooling, 0),
                "Cabinet": CABINET_OPTIONS.get(cabinet, 0),
                "Monitor": MONITOR_OPTIONS.get(monitor, 0),
                "Keyboard": KEYBOARD_OPTIONS.get(keyboard, 0),
                "Mouse": MOUSE_OPTIONS.get(mouse, 0)
            }

            # =================================================
            # ACCESSORIES
            # =================================================

            st.divider()

            st.subheader("Accessories")

            st.write(
                "Select any accessories you want to add."
            )

            selected_accessories = st.multiselect(
                "Choose Accessories",
                show_options(ACCESSORY_OPTIONS),
                key="pc_accessories",
                on_change=sync_accessories,
                args=(
                    "pc_accessories",
                    ACCESSORY_OPTIONS,
                    "Windows"
                )
            )

            accessory_names = [
                item.split(" — ₹")[0]
                for item in selected_accessories
            ]

            accessory_price = sum(
                ACCESSORY_OPTIONS[accessory]
                for accessory in accessory_names
            )

            # =================================================
            # PRICE
            # =================================================

            pc_price = calculate_pc_price(configuration)
            subtotal = pc_price + accessory_price


        # ====================================================
        # macOS CONFIGURATOR
        # ====================================================

        else:

            st.subheader("macOS")

            st.write(
                "Build your custom macOS system."
            )

            st.divider()

            # ------------------------------------------------
            # PROCESSOR
            # ------------------------------------------------

            mac_cpu_display = st.selectbox(
                "Apple Processor",
                show_options_with_none(MACOS_CPU_OPTIONS),
                key="mac_cpu",
                on_change=sync_selectbox_to_cart,
                args=(
                    "mac_cpu",
                    MACOS_CPU_OPTIONS,
                    "processor",
                    "Processor",
                    "macOS"
                )
            )

            mac_cpu = mac_cpu_display.split(" — ₹")[0]

            # ------------------------------------------------
            # RAM
            # ------------------------------------------------

            mac_ram_display = st.selectbox(
                "Memory",
                show_options_with_none(MACOS_RAM_OPTIONS),
                key="mac_ram",
                on_change=sync_selectbox_to_cart,
                args=(
                    "mac_ram",
                    MACOS_RAM_OPTIONS,
                    "memory",
                    "Memory",
                    "macOS"
                )
            )

            mac_ram = mac_ram_display.split(" — ₹")[0]

            # ------------------------------------------------
            # STORAGE
            # ------------------------------------------------

            mac_storage_display = st.selectbox(
                "Storage",
                show_options_with_none(MACOS_STORAGE_OPTIONS),
                key="mac_storage",
                on_change=sync_selectbox_to_cart,
                args=(
                    "mac_storage",
                    MACOS_STORAGE_OPTIONS,
                    "storage",
                    "Storage",
                    "macOS"
                )
            )

            mac_storage = mac_storage_display.split(" — ₹")[0]

            # ------------------------------------------------
            # GPU
            # ------------------------------------------------

            mac_gpu_display = st.selectbox(
                "Graphics",
                show_options_with_none(MACOS_GPU_OPTIONS),
                key="mac_gpu",
                on_change=sync_selectbox_to_cart,
                args=(
                    "mac_gpu",
                    MACOS_GPU_OPTIONS,
                    "graphics",
                    "Graphics",
                    "macOS"
                )
            )

            mac_gpu = mac_gpu_display.split(" — ₹")[0]

            # ------------------------------------------------
            # DISPLAY
            # ------------------------------------------------

            mac_display_display = st.selectbox(
                "Display",
                show_options_with_none(MACOS_DISPLAY_OPTIONS),
                key="mac_display",
                on_change=sync_selectbox_to_cart,
                args=(
                    "mac_display",
                    MACOS_DISPLAY_OPTIONS,
                    "display",
                    "Display",
                    "macOS"
                )
            )

            mac_display = mac_display_display.split(" — ₹")[0]

            # ------------------------------------------------
            # KEYBOARD
            # ------------------------------------------------

            mac_keyboard_display = st.selectbox(
                "Keyboard",
                show_options_with_none(MACOS_KEYBOARD_OPTIONS),
                key="mac_keyboard",
                on_change=sync_selectbox_to_cart,
                args=(
                    "mac_keyboard",
                    MACOS_KEYBOARD_OPTIONS,
                    "keyboard",
                    "Keyboard",
                    "macOS"
                )
            )

            mac_keyboard = mac_keyboard_display.split(" — ₹")[0]

            # ------------------------------------------------
            # MOUSE / TRACKPAD
            # ------------------------------------------------

            mac_mouse_display = st.selectbox(
                "Mouse / Trackpad",
                show_options_with_none(MACOS_MOUSE_OPTIONS),
                key="mac_mouse",
                on_change=sync_selectbox_to_cart,
                args=(
                    "mac_mouse",
                    MACOS_MOUSE_OPTIONS,
                    "mouse",
                    "Mouse / Trackpad",
                    "macOS"
                )
            )

            mac_mouse = mac_mouse_display.split(" — ₹")[0]

            # =================================================
            # ACCESSORIES
            # =================================================

            st.divider()

            st.subheader("Accessories")

            st.write(
                "Select any accessories you want to add."
            )

            selected_mac_accessories = st.multiselect(
                "Choose Accessories",
                show_options(MACOS_ACCESSORY_OPTIONS),
                key="mac_accessories",
                on_change=sync_accessories,
                args=(
                    "mac_accessories",
                    MACOS_ACCESSORY_OPTIONS,
                    "macOS"
                )
            )

            mac_accessory_names = [
                item.split(" — ₹")[0]
                for item in selected_mac_accessories
            ]

            mac_accessory_price = sum(
                MACOS_ACCESSORY_OPTIONS[accessory]
                for accessory in mac_accessory_names
            )

            # =================================================
            # CONFIGURATION
            # =================================================

            mac_configuration = {
                "Processor": MACOS_CPU_OPTIONS.get(mac_cpu, 0),
                "Memory": MACOS_RAM_OPTIONS.get(mac_ram, 0),
                "Storage": MACOS_STORAGE_OPTIONS.get(mac_storage, 0),
                "Graphics": MACOS_GPU_OPTIONS.get(mac_gpu, 0),
                "Display": MACOS_DISPLAY_OPTIONS.get(mac_display, 0),
                "Keyboard": MACOS_KEYBOARD_OPTIONS.get(mac_keyboard, 0),
                "Mouse / Trackpad": MACOS_MOUSE_OPTIONS.get(mac_mouse, 0)
            }

            # =================================================
            # PRICE
            # =================================================

            mac_component_price = sum(
                mac_configuration.values()
            )

            mac_price = mac_component_price + mac_accessory_price


    # ========================================================
    # RIGHT SIDE — CART
    # ========================================================

    with pc_right:

        with st.container(border=True):

            st.subheader("🛒 Order Summary")
            st.caption("Selected items, discounts and the final payable amount appear here.")

            if not st.session_state.cart:

                st.info(
                    "Select a component on the left "
                    "and it will appear here automatically."
                )

            else:

                for index, item in enumerate(
                    st.session_state.cart
                ):

                    item_col1, item_col2 = st.columns(
                        [4, 1.4],
                        vertical_alignment="center"
                    )

                    with item_col1:

                        st.markdown(
                            f"**{item['name']}**"
                        )

                        st.caption(
                            f"₹{item['price']:,.2f}"
                        )

                    with item_col2:

                        if st.button(
                            "✕",
                            key=f"remove_cart_item_{index}",
                            help=f"Remove {item['name']}",
                            use_container_width=True
                        ):

                            remove_from_cart(index)
                            st.rerun()

                    st.divider()

                st.write(
                    f"**Items: {len(st.session_state.cart)}**"
                )

                cart_subtotal, cart_discount, cart_final, cart_discount_percent, cart_offer = get_discounted_cart_totals()

                st.markdown(f"**Subtotal:** ₹{cart_subtotal:,.2f}")
                if cart_discount_percent > 0:
                    st.success(
                        f"🎉 {cart_offer} | You save ₹{cart_discount:,.2f}"
                    )
                    st.markdown(f"**Discount:** {cart_discount_percent:.0f}%")
                    st.markdown(f"### Final Price: ₹{cart_final:,.2f}")
                else:
                    st.info("Add another compatible component or accessory to unlock an automatic discount.")
                    st.markdown(f"### Total: ₹{cart_final:,.2f}")

                cart_os = st.session_state.get(
                    "cart_operating_system",
                    "Windows"
                )

                st.caption(
                    f"Platform: PC | OS: {cart_os}"
                )

                pc_cart_valid, pc_cart_message = validate_order_cart(
                    st.session_state.cart, "PC", cart_os
                )
                if pc_cart_valid:
                    st.success("✓ Configuration complete — your order is ready for payment.")
                else:
                    st.warning(pc_cart_message)

                if st.button(
                    "Place Order",
                    key="place_cart_order",
                    use_container_width=True,
                    type="primary",
                    disabled=(not pc_cart_valid) or ("pending_payment" in st.session_state)
                ):

                    valid_order, validation_message = validate_order_cart(
                        st.session_state.cart,
                        "PC",
                        cart_os
                    )

                    if not valid_order:

                        st.warning(validation_message)

                    else:

                        configuration_items = []
                        accessory_items = []

                        for item in st.session_state.cart:

                            if item["name"].startswith(
                                "Accessory - "
                            ):

                                accessory_items.append(
                                    item["name"].replace(
                                        "Accessory - ",
                                        ""
                                    )
                                )

                            else:

                                configuration_items.append(
                                    item["name"]
                                )

                        configuration_text = "\n".join(
                            configuration_items
                        )

                        accessories_text = ", ".join(
                            accessory_items
                        )

                        cart_subtotal, cart_discount, cart_final, _, _ = get_discounted_cart_totals()

                        order_date = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        # Snapshot cart items BEFORE creating the order or clearing the cart.
                        email_order_items = [dict(item) for item in st.session_state.cart]

                        payment_ok, payment_message, order_id = initiate_razorpay_payment(
                            user_id=user_id,
                            user_name=user_name,
                            user_email=user_email,
                            user_phone=user_phone,
                            device_type="PC",
                            operating_system=cart_os,
                            configuration=configuration_text,
                            accessories=accessories_text,
                            subtotal=cart_subtotal,
                            discount=cart_discount,
                            final_price=cart_final,
                            order_date=order_date,
                            order_items=email_order_items
                        )

                        if payment_ok:
                            st.success(
                                f"Order #{order_id} created. Complete the Razorpay payment below."
                            )
                            st.rerun()
                        else:
                            st.error(payment_message)

                        st.session_state.cart_operating_system = cart_os

                if st.button(
                    "Clear Cart",
                    key="clear_cart_button",
                    use_container_width=True
                ):

                    clear_cart()

                    st.session_state.cart_operating_system = (
                        "Windows"
                    )

                    st.rerun()



# ============================================================
# MOBILE CONFIGURATOR
# ============================================================

elif page == "Mobile Configurator":

    if (
        st.session_state.get("pending_payment")
        and st.session_state["pending_payment"].get("device_type") == "Mobile"
    ):
        render_pending_payment("Mobile")
        st.stop()

    render_offers_section()

    # A cart belongs to the currently active device builder.
    # Switching from PC to Mobile starts a fresh mobile cart.
    if st.session_state.get("cart_device_type") != "Mobile":
        st.session_state.cart = []
        st.session_state.cart_device_type = "Mobile"
        st.session_state.cart_operating_system = "iOS"

    st.title("Mobile Configurator")

    st.write("Create your custom smartphone.")
    st.markdown("""<div class="quados-guide"><div class="quados-guide-step"><b>1 · Platform</b>Choose iPhone or Android</div><div class="quados-guide-step"><b>2 · Profile</b>Start from a use case</div><div class="quados-guide-step"><b>3 · Components</b>Complete the device</div><div class="quados-guide-step"><b>4 · Accessories</b>Add useful extras</div><div class="quados-guide-step"><b>5 · Review & Pay</b>Check the cart and place order</div></div>""", unsafe_allow_html=True)
    st.info("Choose iPhone or Android, select a profile or build manually, complete the required components, and review the Order Summary before placing the order.")

    mobile_left, mobile_right = st.columns(
        [3, 1.25],
        gap="large"
    )

    with mobile_left:

        st.divider()

        mobile_type = st.selectbox(
            "Select Platform",
            [
                "iPhone",
                "Android"
            ],
            key="mobile_platform",
            on_change=reset_profile_for_mobile_platform
        )

        if "mobile_profile" not in st.session_state:
            st.session_state.mobile_profile = "Custom Build (Start Empty)"

        st.selectbox(
            "Configuration Profile",
            MOBILE_PROFILE_OPTIONS,
            key="mobile_profile",
            on_change=handle_mobile_profile_change,
            help="Choose a use-case and QuadOS will load a suitable starting configuration. You can change every feature afterward."
        )

        st.caption("💡 Start from an empty cart, choose a profile to auto-build, or select features manually. The cart updates instantly.")

        # ========================================================
        # iPHONE
        # ========================================================

        if mobile_type == "iPhone":

            st.subheader("Custom iPhone")

            st.write(
                "Build your iPhone by selecting individual features."
            )

            st.divider()

            iphone_display_display = st.selectbox(
                "Display",
                show_options_with_none(IPHONE_DISPLAY_OPTIONS),
                key="iphone_display",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_display",
                    IPHONE_DISPLAY_OPTIONS,
                    "iphone_display",
                    "Display",
                    "iOS"
                )
            )
            iphone_display = iphone_display_display.split(" — ₹")[0]

            iphone_battery_display = st.selectbox(
                "Battery Capacity",
                show_options_with_none(IPHONE_BATTERY_OPTIONS),
                key="iphone_battery",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_battery",
                    IPHONE_BATTERY_OPTIONS,
                    "iphone_battery",
                    "Battery",
                    "iOS"
                )
            )
            iphone_battery = iphone_battery_display.split(" — ₹")[0]

            iphone_camera_display = st.selectbox(
                "Camera",
                show_options_with_none(IPHONE_CAMERA_OPTIONS),
                key="iphone_camera",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_camera",
                    IPHONE_CAMERA_OPTIONS,
                    "iphone_camera",
                    "Camera",
                    "iOS"
                )
            )
            iphone_camera = iphone_camera_display.split(" — ₹")[0]

            iphone_ram_display = st.selectbox(
                "RAM",
                show_options_with_none(IPHONE_RAM_OPTIONS),
                key="iphone_ram",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_ram",
                    IPHONE_RAM_OPTIONS,
                    "iphone_ram",
                    "RAM",
                    "iOS"
                )
            )
            iphone_ram = iphone_ram_display.split(" — ₹")[0]

            iphone_storage_display = st.selectbox(
                "Storage",
                show_options_with_none(IPHONE_STORAGE_OPTIONS),
                key="iphone_storage",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_storage",
                    IPHONE_STORAGE_OPTIONS,
                    "iphone_storage",
                    "Storage",
                    "iOS"
                )
            )
            iphone_storage = iphone_storage_display.split(" — ₹")[0]

            iphone_processor_display = st.selectbox(
                "Processor",
                show_options_with_none(IPHONE_PROCESSOR_OPTIONS),
                key="iphone_processor",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_processor",
                    IPHONE_PROCESSOR_OPTIONS,
                    "iphone_processor",
                    "Processor",
                    "iOS"
                )
            )
            iphone_processor = iphone_processor_display.split(" — ₹")[0]

            iphone_connectivity_display = st.selectbox(
                "Connectivity",
                show_options_with_none(IPHONE_CONNECTIVITY_OPTIONS),
                key="iphone_connectivity",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_connectivity",
                    IPHONE_CONNECTIVITY_OPTIONS,
                    "iphone_connectivity",
                    "Connectivity",
                    "iOS"
                )
            )
            iphone_connectivity = iphone_connectivity_display.split(" — ₹")[0]

            iphone_frame_display = st.selectbox(
                "Frame Material",
                show_options_with_none(IPHONE_FRAME_OPTIONS),
                key="iphone_frame",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_frame",
                    IPHONE_FRAME_OPTIONS,
                    "iphone_frame",
                    "Frame",
                    "iOS"
                )
            )
            iphone_frame = iphone_frame_display.split(" — ₹")[0]

            iphone_color_display = st.selectbox(
                "Color",
                show_options_with_none(IPHONE_COLOR_OPTIONS),
                key="iphone_color",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "iphone_color",
                    IPHONE_COLOR_OPTIONS,
                    "iphone_color",
                    "Color",
                    "iOS"
                )
            )
            iphone_color = iphone_color_display.split(" — ₹")[0]

            iphone_configuration = {
                "Display": selected_price(IPHONE_DISPLAY_OPTIONS, iphone_display),
                "Battery": selected_price(IPHONE_BATTERY_OPTIONS, iphone_battery),
                "Camera": selected_price(IPHONE_CAMERA_OPTIONS, iphone_camera),
                "RAM": selected_price(IPHONE_RAM_OPTIONS, iphone_ram),
                "Storage": selected_price(IPHONE_STORAGE_OPTIONS, iphone_storage),
                "Processor": selected_price(IPHONE_PROCESSOR_OPTIONS, iphone_processor),
                "Connectivity": selected_price(IPHONE_CONNECTIVITY_OPTIONS, iphone_connectivity),
                "Frame": selected_price(IPHONE_FRAME_OPTIONS, iphone_frame),
                "Color": selected_price(IPHONE_COLOR_OPTIONS, iphone_color)
            }

            st.divider()
            st.subheader("Accessories")
            st.write("Select any accessories you want to add.")

            selected_iphone_accessories = st.multiselect(
                "Choose Accessories",
                show_options(IPHONE_ACCESSORY_OPTIONS),
                key="iphone_accessories",
                on_change=sync_mobile_accessories,
                args=(
                    "iphone_accessories",
                    IPHONE_ACCESSORY_OPTIONS,
                    "iOS"
                )
            )

            iphone_accessory_names = [
                item.split(" — ₹")[0]
                for item in selected_iphone_accessories
            ]

            iphone_accessory_price = sum(
                IPHONE_ACCESSORY_OPTIONS[name]
                for name in iphone_accessory_names
            )

            iphone_price = sum(iphone_configuration.values()) + iphone_accessory_price


        # ========================================================
        # ANDROID
        # ========================================================

        else:

            st.subheader("Custom Android")

            st.write(
                "Build your Android smartphone by selecting individual features."
            )

            st.divider()

            android_display_display = st.selectbox(
                "Display",
                show_options_with_none(ANDROID_DISPLAY_OPTIONS),
                key="android_display",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_display",
                    ANDROID_DISPLAY_OPTIONS,
                    "android_display",
                    "Display",
                    "Android"
                )
            )
            android_display = android_display_display.split(" — ₹")[0]

            android_battery_display = st.selectbox(
                "Battery Capacity",
                show_options_with_none(ANDROID_BATTERY_OPTIONS),
                key="android_battery",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_battery",
                    ANDROID_BATTERY_OPTIONS,
                    "android_battery",
                    "Battery",
                    "Android"
                )
            )
            android_battery = android_battery_display.split(" — ₹")[0]

            android_camera_display = st.selectbox(
                "Camera",
                show_options_with_none(ANDROID_CAMERA_OPTIONS),
                key="android_camera",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_camera",
                    ANDROID_CAMERA_OPTIONS,
                    "android_camera",
                    "Camera",
                    "Android"
                )
            )
            android_camera = android_camera_display.split(" — ₹")[0]

            android_ram_display = st.selectbox(
                "RAM",
                show_options_with_none(ANDROID_RAM_OPTIONS),
                key="android_ram",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_ram",
                    ANDROID_RAM_OPTIONS,
                    "android_ram",
                    "RAM",
                    "Android"
                )
            )
            android_ram = android_ram_display.split(" — ₹")[0]

            android_storage_display = st.selectbox(
                "Storage",
                show_options_with_none(ANDROID_STORAGE_OPTIONS),
                key="android_storage",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_storage",
                    ANDROID_STORAGE_OPTIONS,
                    "android_storage",
                    "Storage",
                    "Android"
                )
            )
            android_storage = android_storage_display.split(" — ₹")[0]

            android_processor_display = st.selectbox(
                "Processor",
                show_options_with_none(ANDROID_PROCESSOR_OPTIONS),
                key="android_processor",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_processor",
                    ANDROID_PROCESSOR_OPTIONS,
                    "android_processor",
                    "Processor",
                    "Android"
                )
            )
            android_processor = android_processor_display.split(" — ₹")[0]

            android_connectivity_display = st.selectbox(
                "Connectivity",
                show_options_with_none(ANDROID_CONNECTIVITY_OPTIONS),
                key="android_connectivity",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_connectivity",
                    ANDROID_CONNECTIVITY_OPTIONS,
                    "android_connectivity",
                    "Connectivity",
                    "Android"
                )
            )
            android_connectivity = android_connectivity_display.split(" — ₹")[0]

            android_build_display = st.selectbox(
                "Build Material",
                show_options_with_none(ANDROID_BUILD_OPTIONS),
                key="android_build",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_build",
                    ANDROID_BUILD_OPTIONS,
                    "android_build",
                    "Build Material",
                    "Android"
                )
            )
            android_build = android_build_display.split(" — ₹")[0]

            android_color_display = st.selectbox(
                "Color",
                show_options_with_none(ANDROID_COLOR_OPTIONS),
                key="android_color",
                on_change=sync_mobile_selectbox_to_cart,
                args=(
                    "android_color",
                    ANDROID_COLOR_OPTIONS,
                    "android_color",
                    "Color",
                    "Android"
                )
            )
            android_color = android_color_display.split(" — ₹")[0]

            android_configuration = {
                "Display": selected_price(ANDROID_DISPLAY_OPTIONS, android_display),
                "Battery": selected_price(ANDROID_BATTERY_OPTIONS, android_battery),
                "Camera": selected_price(ANDROID_CAMERA_OPTIONS, android_camera),
                "RAM": selected_price(ANDROID_RAM_OPTIONS, android_ram),
                "Storage": selected_price(ANDROID_STORAGE_OPTIONS, android_storage),
                "Processor": selected_price(ANDROID_PROCESSOR_OPTIONS, android_processor),
                "Connectivity": selected_price(ANDROID_CONNECTIVITY_OPTIONS, android_connectivity),
                "Build Material": selected_price(ANDROID_BUILD_OPTIONS, android_build),
                "Color": selected_price(ANDROID_COLOR_OPTIONS, android_color)
            }

            st.divider()
            st.subheader("Accessories")
            st.write("Select any accessories you want to add.")

            selected_android_accessories = st.multiselect(
                "Choose Accessories",
                show_options(ANDROID_ACCESSORY_OPTIONS),
                key="android_accessories",
                on_change=sync_mobile_accessories,
                args=(
                    "android_accessories",
                    ANDROID_ACCESSORY_OPTIONS,
                    "Android"
                )
            )

            android_accessory_names = [
                item.split(" — ₹")[0]
                for item in selected_android_accessories
            ]

            android_accessory_price = sum(
                ANDROID_ACCESSORY_OPTIONS[name]
                for name in android_accessory_names
            )

            android_price = sum(android_configuration.values()) + android_accessory_price

    # ========================================================
    # RIGHT SIDE — MOBILE CART
    # ========================================================

    with mobile_right:

        with st.container(border=True):

            st.subheader("🛒 Order Summary")
            st.caption("Selected items, discounts and the final payable amount appear here.")

            if not st.session_state.cart:

                st.info("Your cart is empty.")

            else:

                for index, item in enumerate(st.session_state.cart):

                    item_col1, item_col2 = st.columns(
                        [4, 1],
                        vertical_alignment="center"
                    )

                    with item_col1:
                        st.markdown(
                            f"**{item['name']}**"
                        )
                        st.caption(
                            f"₹{item['price']:,.2f}"
                        )

                    with item_col2:
                        if st.button(
                            "✕",
                            key=f"mobile_remove_cart_{index}",
                            help=f"Remove {item['name']}",
                            use_container_width=True
                        ):
                            remove_from_cart(index)
                            st.rerun()

                    st.divider()

                st.write(
                    f"**Items: {len(st.session_state.cart)}**"
                )

                mobile_cart_subtotal, mobile_cart_discount, mobile_cart_final, mobile_discount_percent, mobile_offer = get_discounted_cart_totals()

                st.markdown(f"**Subtotal:** ₹{mobile_cart_subtotal:,.2f}")
                if mobile_discount_percent > 0:
                    st.success(
                        f"🎉 {mobile_offer} | You save ₹{mobile_cart_discount:,.2f}"
                    )
                    st.markdown(f"**Discount:** {mobile_discount_percent:.0f}%")
                    st.markdown(f"### Final Price: ₹{mobile_cart_final:,.2f}")
                else:
                    st.info("Add another smartphone component or accessory to unlock an automatic discount.")
                    st.markdown(f"### Total: ₹{mobile_cart_final:,.2f}")

                mobile_cart_os = st.session_state.get(
                    "cart_operating_system",
                    "iOS" if mobile_type == "iPhone" else "Android"
                )

                st.caption(
                    f"Platform: Mobile | OS: {mobile_cart_os}"
                )

                mobile_cart_valid, mobile_cart_message = validate_order_cart(
                    st.session_state.cart, "Mobile", mobile_cart_os
                )
                if mobile_cart_valid:
                    st.success("✓ Configuration complete — your order is ready for payment.")
                else:
                    st.warning(mobile_cart_message)

                if st.button(
                    "Place Order",
                    key="mobile_cart_place_order",
                    use_container_width=True,
                    type="primary",
                    disabled=(not mobile_cart_valid) or ("pending_payment" in st.session_state)
                ):

                    valid_order, validation_message = validate_order_cart(
                        st.session_state.cart,
                        "Mobile",
                        mobile_cart_os
                    )

                    if not valid_order:

                        st.warning(validation_message)

                    else:

                        configuration_items = []
                        accessory_items = []

                        for item in st.session_state.cart:

                            if item.get("category", "").startswith(
                                "mobile_accessory:"
                            ):
                                accessory_items.append(
                                    item["name"].replace(
                                        "Accessory - ",
                                        ""
                                    )
                                )
                            else:
                                configuration_items.append(
                                    item["name"]
                                )

                        configuration_text = "\n".join(
                            configuration_items
                        )

                        accessories_text = ", ".join(
                            accessory_items
                        )

                        mobile_cart_subtotal, mobile_cart_discount, mobile_cart_final, _, _ = get_discounted_cart_totals()

                        order_date = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        # Snapshot cart items BEFORE creating the order or clearing the cart.
                        email_order_items = [dict(item) for item in st.session_state.cart]

                        payment_ok, payment_message, order_id = initiate_razorpay_payment(
                            user_id=user_id,
                            user_name=user_name,
                            user_email=user_email,
                            user_phone=user_phone,
                            device_type="Mobile",
                            operating_system=mobile_cart_os,
                            configuration=configuration_text,
                            accessories=accessories_text,
                            subtotal=mobile_cart_subtotal,
                            discount=mobile_cart_discount,
                            final_price=mobile_cart_final,
                            order_date=order_date,
                            order_items=email_order_items
                        )

                        if payment_ok:
                            st.success(
                                f"Order #{order_id} created. Complete the Razorpay payment below."
                            )
                            st.rerun()
                        else:
                            st.error(payment_message)

                if st.button(
                    "Clear Cart",
                    key="mobile_clear_cart_button",
                    use_container_width=True
                ):

                    clear_cart()
                    st.session_state.cart_device_type = "Mobile"
                    st.rerun()



# ============================================================
# MY ORDERS
# ============================================================

elif page == "My Orders":

    st.markdown("""<div class="quados-page-kicker">Customer workspace</div><div class="quados-page-title">My Orders</div><div class="quados-page-subtitle">Track your configurations, payment status and order progress. Unpaid orders can be cancelled; paid orders are protected from accidental cancellation.</div>""", unsafe_allow_html=True)

    st.divider()

    orders = get_user_orders(user_id)

    if orders:

        order_rows = []

        for order in orders:

            order_id = order[0]
            device_type = order[2]
            operating_system = order[3]
            configuration = order[4]
            accessories = order[5]
            subtotal = order[6]
            final_price = order[8]
            order_date = order[9]
            status = order[10] or "Placed"

            order_rows.append({
                "Order ID": order_id,
                "Device": device_type,
                "Operating System": operating_system,
                "Configuration": (
                    configuration
                    if configuration
                    else "No configuration details"
                ),
                "Accessories": (
                    accessories
                    if accessories
                    else "No accessories"
                ),
                "Subtotal": f"₹{float(subtotal):,.2f}",
                "Final Price": f"₹{float(final_price):,.2f}",
                "Order Date": str(order_date),
                "Status": status
            })

        orders_df = pd.DataFrame(order_rows)

        st.dataframe(
            orders_df,
            use_container_width=True,
            hide_index=True,
            height=500
        )

        st.caption(
            f"Total orders displayed: {len(orders_df)}"
        )

        # ====================================================
        # CANCEL ORDER
        # ====================================================

        st.divider()
        st.subheader("Cancel an Order")

        cancellable_orders = [
            order
            for order in orders
            if (order[10] or "Placed") != "Cancelled"
        ]

        if cancellable_orders:

            cancel_options = {
                f"Order #{order[0]} | {order[2]} | {order[3]} | ₹{float(order[8]):,.2f}": order[0]
                for order in cancellable_orders
            }

            selected_cancel_label = st.selectbox(
                "Select an order to cancel",
                list(cancel_options.keys()),
                key="user_cancel_order_select"
            )

            selected_cancel_order_id = cancel_options[
                selected_cancel_label
            ]

            if st.button(
                "Cancel Order",
                key="user_cancel_order_button",
                type="primary",
                use_container_width=True
            ):

                cancelled = cancel_order(
                    user_id,
                    selected_cancel_order_id
                )

                if cancelled:

                    # The cancellation is saved first. Email failure must
                    # not roll back the customer's cancellation.
                    selected_cancel_order = next(
                        (
                            item
                            for item in cancellable_orders
                            if item[0] == selected_cancel_order_id
                        ),
                        None,
                    )

                    if selected_cancel_order:
                        cancel_email_ok, cancel_email_message = (
                            send_order_cancellation_emails(
                                recipient_email=user_email,
                                customer_name=user_name,
                                order_id=selected_cancel_order[0],
                                device_type=selected_cancel_order[2],
                                final_price=selected_cancel_order[8],
                            )
                        )

                        if cancel_email_ok:
                            st.session_state["order_status_email_message"] = (
                                f"Cancellation email sent for Order #{selected_cancel_order_id}."
                            )
                        else:
                            st.session_state["order_status_email_message"] = (
                                "Order was cancelled, but the cancellation email could "
                                f"not be sent: {cancel_email_message}"
                            )

                    st.session_state["flash_success_message"] = (
                        f"Order #{selected_cancel_order_id} has been cancelled successfully."
                    )

                    st.rerun()

                else:

                    st.error(
                        "The order could not be cancelled. It may already be cancelled or does not belong to your account."
                    )

        else:

            st.info("All your orders have already been cancelled.")

    else:

        st.info(
            "You have not placed any orders yet."
        )



# ============================================================
# MY PROFILE
# ============================================================

elif page == "My Profile":

    st.markdown("""<div class="quados-page-kicker">Account</div><div class="quados-page-title">My Profile</div><div class="quados-page-subtitle">Review your account details, order activity and support history in one place.</div>""", unsafe_allow_html=True)

    # --------------------------------------------------------
    # PROFILE HEADER
    # --------------------------------------------------------

    initials = "".join(
        part[0].upper()
        for part in str(user_name).split()
        if part
    )[:2] or "U"

    st.markdown(
        f"""
        <div style="
            padding:24px;
            border-radius:18px;
            background:linear-gradient(
                135deg,
                rgba(20,25,45,.95),
                rgba(45,45,65,.88)
            );
            border:1px solid rgba(255,255,255,.10);
            margin-bottom:20px;
        ">
            <div style="
                width:64px;
                height:64px;
                border-radius:50%;
                display:flex;
                align-items:center;
                justify-content:center;
                font-size:24px;
                font-weight:800;
                background:rgba(255,255,255,.12);
                border:1px solid rgba(255,255,255,.18);
                margin-bottom:14px;
            ">
                {initials}
            </div>
            <div style="font-size:28px;font-weight:800;">
                {user_name}
            </div>
            <div style="opacity:.70;margin-top:4px;">
                {user_email}
            </div>
            <div style="margin-top:12px;">
                <span style="
                    padding:5px 11px;
                    border-radius:20px;
                    background:rgba(255,255,255,.10);
                    font-size:12px;
                ">
                    {user_role.upper()}
                </span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # --------------------------------------------------------
    # PROFILE STATISTICS
    # --------------------------------------------------------

    profile_orders = get_user_orders(user_id)
    profile_order_count = len(profile_orders)

    profile_total_spend = 0

    for order in profile_orders:
        try:
            profile_total_spend += float(order[8] or 0)
        except (TypeError, ValueError, IndexError):
            pass

    profile_queries = get_user_queries(user_id)
    profile_query_count = len(profile_queries)

    stat1, stat2, stat3 = st.columns(3)

    with stat1:
        st.metric("My Orders", profile_order_count)

    with stat2:
        st.metric("Total Spent", f"₹{profile_total_spend:,.0f}")

    with stat3:
        st.metric("Support Queries", profile_query_count)

    st.divider()

    # --------------------------------------------------------
    # ACCOUNT INFORMATION
    # --------------------------------------------------------

    st.subheader("👤 Account Information")

    info_col1, info_col2 = st.columns(2, gap="large")

    with info_col1:

        st.text_input(
            "Full Name",
            value=str(current_user[1] or ""),
            disabled=True,
            key="profile_display_name"
        )

        st.text_input(
            "Email",
            value=str(current_user[2] or ""),
            disabled=True,
            key="profile_display_email"
        )

        st.text_input(
            "Phone",
            value=str(current_user[4] or "Not provided"),
            disabled=True,
            key="profile_display_phone"
        )

    with info_col2:

        st.text_area(
            "Address",
            value=str(current_user[5] or "Not provided"),
            disabled=True,
            height=120,
            key="profile_display_address"
        )

        st.text_input(
            "Account Role",
            value=str(current_user[6] or "user").capitalize(),
            disabled=True,
            key="profile_display_role"
        )

    st.caption(
        "Your profile information is currently displayed in read-only mode."
    )

    st.divider()

    # --------------------------------------------------------
    # ORDER SUMMARY
    # --------------------------------------------------------

    st.subheader("📦 Account Activity")

    activity_col1, activity_col2 = st.columns(2, gap="large")

    with activity_col1:

        if profile_orders:

            placed_count = sum(
                1
                for order in profile_orders
                if (order[10] or "Placed") != "Cancelled"
            )

            cancelled_count = sum(
                1
                for order in profile_orders
                if (order[10] or "Placed") == "Cancelled"
            )

            st.markdown(
                f"""
                <div style="padding:20px;border-radius:15px;
                            background:rgba(255,255,255,.045);
                            border:1px solid rgba(255,255,255,.08);">
                    <div style="font-size:14px;opacity:.65;">
                        Order Status
                    </div>
                    <div style="font-size:18px;margin-top:10px;">
                        🟢 Active / Placed: <b>{placed_count}</b>
                    </div>
                    <div style="font-size:18px;margin-top:8px;">
                        🔴 Cancelled: <b>{cancelled_count}</b>
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )

        else:
            st.info("You have not placed any orders yet.")

    with activity_col2:

        pending_user_queries = sum(
            1
            for query in profile_queries
            if str(query[3] or "") == "Pending"
        )

        resolved_user_queries = sum(
            1
            for query in profile_queries
            if str(query[3] or "") == "Resolved"
        )

        st.markdown(
            f"""
            <div style="padding:20px;border-radius:15px;
                        background:rgba(255,255,255,.045);
                        border:1px solid rgba(255,255,255,.08);">
                <div style="font-size:14px;opacity:.65;">
                    Support Activity
                </div>
                <div style="font-size:18px;margin-top:10px;">
                    🟠 Pending: <b>{pending_user_queries}</b>
                </div>
                <div style="font-size:18px;margin-top:8px;">
                    🟢 Resolved: <b>{resolved_user_queries}</b>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

    st.divider()

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    st.subheader("🔐 Account Security")

    st.info(
        "Your password is protected and is not displayed in your profile. "
        "If you need to change it, use the Forgot Password option on the login screen."
    )


# ============================================================
# ADMIN QUERIES / SUPPORT CHAT
# ============================================================

elif page == "Queries":

    render_admin_queries(current_user)


# ============================================================
# USER HELP & QUERIES
# ============================================================

elif page == "Help & Queries":

    render_user_help_queries(current_user)


# ============================================================
# ABOUT
# ============================================================

elif page == "About" and user_role != "admin":

    st.markdown(
        """
        <div style="padding:24px 28px;border-radius:18px;
        background:linear-gradient(135deg, rgba(25,31,55,.97), rgba(55,42,75,.92));
        border:1px solid rgba(255,255,255,.10);margin-bottom:20px;">
            <div style="font-size:12px;opacity:.58;letter-spacing:.10em;text-transform:uppercase;">QuadOS 3.0</div>
            <div style="font-size:32px;font-weight:800;margin-top:4px;">About QuadOS</div>
            <div style="font-size:14px;opacity:.72;margin-top:6px;">A simple platform for configuring supported devices and managing orders.</div>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.subheader("What QuadOS Does")
    st.write(
        "QuadOS lets users configure supported PC and mobile devices, review prices and applicable bundle discounts, pay securely through the integrated Razorpay checkout, and manage their orders."
    )

    info1, info2 = st.columns(2, gap="large")

    with info1:
        st.markdown(
            """
            **🖥️ PC Configurator**  
            Build supported Windows PC or macOS configurations.

            **📱 Mobile Configurator**  
            Configure supported iPhone or Android options.

            **🛒 Cart & Pricing**  
            Review selections, accessories and automatic bundle discounts before ordering.
            """
        )

    with info2:
        st.markdown(
            """
            **💳 Razorpay Payments**  
            Complete orders through the integrated Razorpay checkout.

            **📦 My Orders**  
            View your orders and their current status.

            **💬 Help & Queries**  
            Contact QuadOS support and continue your conversations.
            """
        )

    st.divider()
    st.caption("For account details, open My Profile. For support, use Help & Queries.")
