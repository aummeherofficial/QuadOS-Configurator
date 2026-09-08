import streamlit as st
import razorpay
import streamlit.components.v1 as components
from datetime import datetime

st.set_page_config(page_title="QuadOS Razorpay Test")

KEY_ID = st.secrets["RAZORPAY_KEY_ID"]
KEY_SECRET = st.secrets["RAZORPAY_KEY_SECRET"]

client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

st.title("QuadOS - Razorpay Checkout Test")

amount_rupees = 1
amount_paise = amount_rupees * 100

if st.button("Create ₹1 Test Payment", type="primary"):

    receipt = f"quados_payment_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        order = client.order.create(
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

        order_id = order["id"]

        st.success("✓ Razorpay Order Created")

        st.write(f"Order ID: `{order_id}`")
        st.write(f"Amount: ₹{amount_rupees:.2f}")

        checkout_html = f"""
        <script src="https://checkout.razorpay.com/v1/checkout.js"></script>

        <button
            id="rzp-button"
            style="
                background:#3399cc;
                color:white;
                border:none;
                padding:12px 24px;
                border-radius:6px;
                font-size:16px;
                cursor:pointer;
            ">
            Pay ₹1 with Razorpay
        </button>

        <script>
        document.getElementById('rzp-button').onclick = function(e) {{

            var options = {{
                "key": "{KEY_ID}",
                "amount": "{amount_paise}",
                "currency": "INR",
                "name": "QuadOS",
                "description": "QuadOS Test Payment",
                "order_id": "{order_id}",

                "handler": function(response) {{
                    document.body.innerHTML +=
                        "<p style='color:green;font-weight:bold;'>" +
                        "Payment successful!<br><br>" +
                        "Payment ID: " +
                        response.razorpay_payment_id +
                        "</p>";
                }},

                "prefill": {{
                    "name": "QuadOS Test User",
                    "email": "test@quados.com",
                    "contact": "9999999999"
                }},

                "theme": {{
                    "color": "#3399cc"
                }}
            }};

            var rzp = new Razorpay(options);

            rzp.on('payment.failed', function(response) {{
                document.body.innerHTML +=
                    "<p style='color:red;font-weight:bold;'>" +
                    "Payment failed<br><br>" +
                    response.error.description +
                    "</p>";
            }});

            rzp.open();

            e.preventDefault();
        }};
        </script>
        """

        components.html(checkout_html, height=350)

    except Exception as e:
        st.error("Failed to create Razorpay order.")
        st.code(str(e))