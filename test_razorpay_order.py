import streamlit as st
import razorpay
from datetime import datetime

# Load Razorpay credentials
key_id = st.secrets["RAZORPAY_KEY_ID"]
key_secret = st.secrets["RAZORPAY_KEY_SECRET"]

# Create Razorpay client
client = razorpay.Client(auth=(key_id, key_secret))

st.title("QuadOS - Razorpay Test Order")

# Test amount: ₹1
amount_rupees = 1
amount_paise = amount_rupees * 100

receipt = f"quados_test_{datetime.now().strftime('%Y%m%d%H%M%S')}"

try:
    razorpay_order = client.order.create(
        data={
            "amount": amount_paise,
            "currency": "INR",
            "receipt": receipt,
            "notes": {
                "project": "QuadOS",
                "environment": "Test"
            }
        }
    )

    st.success("✓ Razorpay Test Order Created")

    st.write("Razorpay Order ID:")
    st.code(razorpay_order["id"])

    st.write("Amount:")
    st.write(f"₹{amount_rupees:.2f}")

    st.write("Currency:")
    st.write(razorpay_order["currency"])

    st.write("Status:")
    st.write(razorpay_order["status"])

except Exception as e:
    st.error("✗ Failed to create Razorpay Order")
    st.code(str(e))