import streamlit as st
import razorpay

key_id = st.secrets["RAZORPAY_KEY_ID"]
key_secret = st.secrets["RAZORPAY_KEY_SECRET"]

client = razorpay.Client(auth=(key_id, key_secret))

st.title("Razorpay Connection Test")

try:
    client.order.all({"count": 1})
    st.success("✓ Razorpay connection successful!")
    st.write("Test API authentication is working.")
except Exception as e:
    st.error("✗ Razorpay connection failed.")
    st.code(str(e))