import streamlit as st
import razorpay
import streamlit.components.v1 as components
from datetime import datetime

st.set_page_config(page_title="QuadOS Razorpay Verification Test")

KEY_ID = st.secrets["RAZORPAY_KEY_ID"]
KEY_SECRET = st.secrets["RAZORPAY_KEY_SECRET"]

client = razorpay.Client(auth=(KEY_ID, KEY_SECRET))

st.title("QuadOS - Razorpay Payment Verification Test")

# ------------------------------------------------------------
# CREATE TEST ORDER
# ------------------------------------------------------------

if "razorpay_order_id" not in st.session_state:
    st.session_state.razorpay_order_id = None

if "razorpay_payment_id" not in st.session_state:
    st.session_state.razorpay_payment_id = None

st.subheader("1. Create Test Payment")

if st.button("Create ₹1 Test Payment", type="primary"):

    receipt = f"quados_verify_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    try:
        order = client.order.create(
            data={
                "amount": 100,
                "currency": "INR",
                "receipt": receipt,
                "notes": {
                    "project": "QuadOS",
                    "environment": "Test"
                }
            }
        )

        st.session_state.razorpay_order_id = order["id"]

        st.success("✓ Razorpay Order Created")

    except Exception as e:
        st.error("Failed to create Razorpay Order.")
        st.code(str(e))


# ------------------------------------------------------------
# CHECKOUT
# ------------------------------------------------------------

if st.session_state.razorpay_order_id:

    order_id = st.session_state.razorpay_order_id

    st.write("Razorpay Order ID:")
    st.code(order_id)

    st.subheader("2. Make Test Payment")

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

    <div id="result" style="margin-top:20px;"></div>

    <script>

    document.getElementById("rzp-button").onclick = function(e) {{

        var options = {{

            "key": "{KEY_ID}",

            "amount": "100",

            "currency": "INR",

            "name": "QuadOS",

            "description": "QuadOS Razorpay Verification Test",

            "order_id": "{order_id}",

            "handler": function(response) {{

                document.getElementById("result").innerHTML =
                    "<h3 style='color:green;'>Payment Successful</h3>" +

                    "<p><b>Payment ID:</b></p>" +
                    "<code>" +
                    response.razorpay_payment_id +
                    "</code>" +

                    "<p><b>Order ID:</b></p>" +
                    "<code>" +
                    response.razorpay_order_id +
                    "</code>" +

                    "<p><b>Signature:</b></p>" +
                    "<code style='word-break:break-all;'>" +
                    response.razorpay_signature +
                    "</code>" +

                    "<p style='margin-top:20px;'>" +
                    "Copy these three values into the verification form below." +
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

        rzp.on("payment.failed", function(response) {{

            document.getElementById("result").innerHTML =
                "<p style='color:red;'>" +
                "Payment failed: " +
                response.error.description +
                "</p>";

        }});

        rzp.open();

        e.preventDefault();

    }};

    </script>
    """

    components.html(checkout_html, height=500)


# ------------------------------------------------------------
# VERIFICATION FORM
# ------------------------------------------------------------

st.divider()

st.subheader("3. Verify Payment")

payment_id = st.text_input(
    "Razorpay Payment ID",
    placeholder="pay_..."
)

checkout_order_id = st.text_input(
    "Razorpay Order ID",
    value=st.session_state.razorpay_order_id or "",
    placeholder="order_..."
)

signature = st.text_input(
    "Razorpay Signature",
    placeholder="Paste the signature returned by Razorpay"
)

if st.button("Verify Payment", type="primary"):

    if not payment_id:
        st.error("Please enter the Razorpay Payment ID.")

    elif not checkout_order_id:
        st.error("Please enter the Razorpay Order ID.")

    elif not signature:
        st.error("Please enter the Razorpay Signature.")

    else:

        try:

            # IMPORTANT:
            # Razorpay SDK performs server-side signature verification.
            client.utility.verify_payment_signature({
                "razorpay_order_id": checkout_order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": signature
            })

            st.success("✓ PAYMENT SIGNATURE VERIFIED")

            st.write(
                "Razorpay has confirmed that the payment response "
                "is authentic."
            )

            # Fetch payment details from Razorpay
            payment = client.payment.fetch(payment_id)

            st.write("Payment Status:")

            if payment.get("status") == "captured":
                st.success("✓ Payment Captured")
            else:
                st.warning(
                    f"Payment status: {payment.get('status')}"
                )

            st.write("Payment ID:")
            st.code(payment_id)

            st.write("Order ID:")
            st.code(checkout_order_id)

        except Exception as e:

            st.error("✗ PAYMENT VERIFICATION FAILED")

            st.code(str(e))