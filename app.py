import streamlit as st
import base64
from pathlib import Path
from datetime import datetime
import pandas as pd
import re
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
    get_user_orders,
    get_all_orders_with_users
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


# ============================================================
# DISPLAY OPTION WITH PRICE
# ============================================================

def show_options(options):

    return [
        f"{name} — ₹{price:,.0f}"
        for name, price in options.items()
    ]


def show_options_with_none(options):
    """Return options with a zero-price Not Selected choice first."""
    return ["Not Selected — ₹0"] + [
        f"{name} — ₹{price:,.0f}"
        for name, price in options.items()
    ]


# ============================================================
# DATABASE
# ============================================================

create_tables()
create_admin()


# ============================================================
# PAGE SETTINGS
# ============================================================

st.set_page_config(
    page_title="QuadOS",
    page_icon="Q",
    layout="wide"
)


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

def go_to_page(page_name):
    st.session_state.user_navigation = page_name



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
            options[selected_name],
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
                options[name],
                category=f"accessory:{name}"
            )


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
    if phone and not re.fullmatch(r"[0-9+()\- ]{7,20}", phone):
        return False, "Please enter a valid phone number."

    if len(address.strip()) > 250:
        return False, "Address must not exceed 250 characters."

    return True, ""


# ============================================================
# LOGIN / REGISTER
# ============================================================

if not st.session_state.logged_in:

    st.title("QuadOS")
    st.subheader("Secure Login")

    # CREATE THE TABS FIRST
    login_tab, register_tab = st.tabs(
        ["Login", "Create Account"]
    )

    # ========================================================
    # LOGIN
    # ========================================================

    with login_tab:

        st.write(
            "Use your registered email and password to continue."
        )

        email = st.text_input(
            "Email",
            key="login_email"
        )

        password = st.text_input(
            "Password",
            type="password",
            key="login_password"
        )

        if st.button(
            "Login",
            key="login_button",
            use_container_width=True
        ):

            # Do NOT use strict email validation here.
            # This allows existing QuadOS users to continue
            # using the identifier stored in the database.

            email = email.strip().lower()

            if email == "":
                st.warning(
                    "Please enter your email."
                )

            elif password == "":
                st.warning(
                    "Please enter your password."
                )

            else:

                user = login_user(
                    email,
                    password
                )

                if user:

                    st.session_state.logged_in = True
                    st.session_state.user = user

                    st.rerun()

                else:

                    st.error(
                        "Invalid email or password."
                    )


    # ========================================================
    # CREATE ACCOUNT
    # ========================================================

    with register_tab:

        st.write(
            "Create a new QuadOS user account."
        )

        name = st.text_input(
            "Full Name",
            key="register_name"
        )

        email = st.text_input(
            "Email",
            key="register_email"
        )

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

        phone = st.text_input(
            "Phone",
            key="register_phone"
        )

        address = st.text_area(
            "Address",
            key="register_address"
        )

        if st.button(
            "Create Account",
            key="create_account_button",
            use_container_width=True
        ):

            name = name.strip()
            email = email.strip().lower()
            phone = phone.strip()
            address = address.strip()

            # -----------------------------
            # REQUIRED FIELDS
            # -----------------------------

            if name == "":
                st.warning(
                    "Please enter your full name."
                )

            elif email == "":
                st.warning(
                    "Please enter your email."
                )

            elif password == "":
                st.warning(
                    "Please enter a password."
                )

            elif confirm_password == "":
                st.warning(
                    "Please confirm your password."
                )

            # -----------------------------
            # PASSWORD MATCH
            # -----------------------------

            elif password != confirm_password:

                st.error(
                    "Passwords do not match."
                )

            # -----------------------------
            # PASSWORD LENGTH
            # -----------------------------

            elif len(password) < 8:

                st.error(
                    "Password must contain at least 8 characters."
                )

            # -----------------------------
            # PASSWORD UPPERCASE
            # -----------------------------

            elif not any(
                character.isupper()
                for character in password
            ):

                st.error(
                    "Password must contain at least one uppercase letter."
                )

            # -----------------------------
            # PASSWORD LOWERCASE
            # -----------------------------

            elif not any(
                character.islower()
                for character in password
            ):

                st.error(
                    "Password must contain at least one lowercase letter."
                )

            # -----------------------------
            # PASSWORD NUMBER
            # -----------------------------

            elif not any(
                character.isdigit()
                for character in password
            ):

                st.error(
                    "Password must contain at least one number."
                )

            # -----------------------------
            # CREATE USER
            # -----------------------------

            else:

                success = create_user(
                    name,
                    email,
                    password,
                    phone,
                    address
                )

                if success:

                    st.success(
                        "Account created successfully. "
                        "You can now login."
                    )

                else:

                    st.error(
                        "This email is already registered."
                    )

    st.stop()

# ============================================================
# GET CURRENT USER
# ============================================================

current_user = st.session_state.user

user_id = current_user[0]
user_name = current_user[1]
user_email = current_user[2]
user_role = current_user[3]


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.title("◈ QuadOS")

    st.caption("Custom Device Platform")

    st.divider()


    # ========================================================
    # ADMIN NAVIGATION
    # ========================================================

    if user_role == "admin":

        st.write("ADMIN")

        page = st.radio(
            "Navigation",
            [
                "Admin Dashboard",
                "All Users",
                "All Orders",
                "Manage Orders",
                "Analytics",
                "About"
            ]
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
                "About"
            ],
            key="user_navigation"
        )


    st.divider()

    st.caption(
        f"Logged in as: {user_name}"
    )

    st.caption(
        f"Role: {user_role}"
    )


    if st.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.logged_in = False

        st.session_state.user = None

        st.rerun()


    st.divider()

    st.caption("QuadOS 3.0")




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

    st.title("Admin Dashboard")

    st.write(
        f"Welcome, {user_name}"
    )

    st.write("")

    # --------------------------------------------------------
    # GET DATA
    # --------------------------------------------------------

    total_users = get_total_users()

    total_orders = get_total_orders()

    total_revenue = get_total_revenue()

    recent_orders = get_recent_orders()


    # --------------------------------------------------------
    # DASHBOARD CARDS
    # --------------------------------------------------------

    col1, col2, col3 = st.columns(3)

    with col1:

        st.metric(
            "Total Users",
            total_users
        )

    with col2:

        st.metric(
            "Total Orders",
            total_orders
        )

    with col3:

        st.metric(
            "Total Revenue",
            f"₹{total_revenue:,.2f}"
        )


    st.divider()


    # --------------------------------------------------------
    # RECENT ORDERS
    # --------------------------------------------------------

    st.subheader("Recent Orders")

    if recent_orders:

        for order in recent_orders:

            order_id = order[0]
            user_id = order[1]
            device = order[2]
            operating_system = order[3]
            final_price = order[4]
            order_date = order[5]

            st.write(
                f"Order #{order_id} | "
                f"User ID: {user_id} | "
                f"{device} | "
                f"{operating_system} | "
                f"₹{final_price:,.2f} | "
                f"{order_date}"
            )

    else:

        st.info(
            "No orders have been placed yet."
        )


# ============================================================
# ALL USERS
# ============================================================

elif page == "All Users":

    st.title("All Users")

    st.write(
        "View all registered QuadOS users."
    )

    st.write("")

    users = get_all_users()

    if users:

        for user in users:

            user_id = user[0]
            name = user[1]
            email = user[2]
            phone = user[3]
            address = user[4]
            role = user[5]

            with st.container(border=True):

                col1, col2, col3 = st.columns(3)

                with col1:

                    st.write(
                        f"**User ID:** {user_id}"
                    )

                    st.write(
                        f"**Name:** {name}"
                    )

                with col2:

                    st.write(
                        f"**Email:** {email}"
                    )

                    st.write(
                        f"**Phone:** {phone}"
                    )

                with col3:

                    st.write(
                        f"**Address:** {address}"
                    )

                    st.write(
                        f"**Role:** {role}"
                    )

    else:

        st.info(
            "No users found."
        )


# ============================================================
# ALL ORDERS
# ============================================================

elif page == "All Orders":

    st.title("All Orders")

    st.write(
        "View all orders placed through QuadOS in a tabular format."
    )

    st.write("")

    orders = get_all_orders_with_users()

    if orders:

        order_rows = []

        for order in orders:

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

            order_rows.append({
                "Order ID": order_id,
                "Customer": customer_name,
                "Email": customer_email,
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
                "Order Date": str(order_date)
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

    else:

        st.info(
            "No orders have been placed yet."
        )


# ============================================================
# MANAGE ORDERS
# ============================================================

elif page == "Manage Orders":

    st.title("Manage Orders")

    st.write(
        "View and manage QuadOS orders."
    )

    st.write("")

    orders = get_all_orders_with_users()

    if not orders:

        st.info(
            "There are no orders to manage."
        )

    else:

        # ----------------------------------------------------
        # CREATE ORDER LIST
        # ----------------------------------------------------

        order_options = []

        for order in orders:

            order_id = order[0]
            customer_name = order[1]
            customer_email = order[2]
            device_type = order[3]
            final_price = order[8]

            order_options.append(
                f"Order #{order_id} | "
                f"{customer_name} | "
                f"{device_type} | "
                f"₹{final_price:,.2f}"
            )


        # ----------------------------------------------------
        # SELECT ORDER
        # ----------------------------------------------------

        selected_order = st.selectbox(
            "Select Order",
            order_options
        )


        # ----------------------------------------------------
        # GET SELECTED ORDER ID
        # ----------------------------------------------------

        selected_index = order_options.index(
            selected_order
        )

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


        st.write(
            f"**Customer:** {customer_name}"
            )

        st.write(
            f"**Email:** {customer_email}"
            )


        # ----------------------------------------------------
        # DISPLAY ORDER
        # ----------------------------------------------------

        st.divider()

        st.subheader(
            f"Order #{order_id}"
        )

        col1, col2 = st.columns(2)

        with col1:
        
            st.write(
                f"**Customer:** {customer_name}"
            )
        
            st.write(
                f"**Email:** {customer_email}"
            )
        
            st.write(
                f"**Device:** {device_type}"
            )
        
            st.write(
                f"**Operating System:** "
                f"{operating_system}"
            )
        
            st.write(
                f"**Order Date:** "
                f"{order_date}"
            )

            st.write(
                f"**User ID:** {user_id}"
            )

            st.write(
                f"**Device:** {device_type}"
            )

            st.write(
                f"**Operating System:** "
                f"{operating_system}"
            )

            st.write(
                f"**Order Date:** "
                f"{order_date}"
            )

        with col2:

            st.write(
                f"**Subtotal:** "
                f"₹{subtotal:,.2f}"
            )

            st.write(
                f"**Final Price:** "
                f"₹{final_price:,.2f}"
            )


        st.write("")

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
        # DELETE ORDER
        # ----------------------------------------------------

        st.divider()

        if st.button(
            "Delete Order",
            type="primary"
        ):

            delete_order(order_id)

            st.success(
                f"Order #{order_id} deleted successfully."
            )

            st.rerun()



# ============================================================
# ANALYTICS
# ============================================================


elif page == "Analytics":

    st.title("QuadOS Analytics")

    st.write(
        "Overview of QuadOS orders, revenue and pricing."
    )

    st.divider()

    # ========================================================
    # GET DATA
    # ========================================================

    data = get_order_data()

    if data.empty:

        st.info(
            "No order data available for analytics yet."
        )

    else:

        # ====================================================
        # PREPARE DATA
        # ====================================================

        data["order_date"] = pd.to_datetime(
            data["order_date"]
        )

        data["date"] = data["order_date"].dt.normalize()

        data["final_price"] = pd.to_numeric(
            data["final_price"]
        )

        # ====================================================
        # SUMMARY CARDS
        # ====================================================

        total_orders = len(data)

        total_revenue = data[
            "final_price"
        ].sum()

        average_order_value = data[
            "final_price"
        ].mean()


        col1, col2, col3 = st.columns(3)

        with col1:

            st.metric(
                "Total Orders",
                total_orders
            )

        with col2:

            st.metric(
                "Total Revenue",
                f"₹{total_revenue:,.0f}"
            )

        with col3:

            st.metric(
                "Average Order Value",
                f"₹{average_order_value:,.0f}"
            )


        st.divider()


        # ====================================================
        # ROW 1
        # ====================================================

        col1, col2, col3 = st.columns(3)


        # ----------------------------------------------------
        # CHART 1 - ORDERS BY DEVICE
        # ----------------------------------------------------

        with col1:

            st.subheader(
                "Orders by Device"
            )

            device_orders = (
                data["device_type"]
                .value_counts()
            )
            
            fig, ax = plt.subplots(figsize=(4, 2.8))
            
            bars = ax.bar(
                device_orders.index,
                device_orders.values,
                label="Orders"
            )
            
            ax.bar_label(
                bars,
                padding=3,
                fontsize=8
            )
            
            style_chart(
                ax,
                "Orders by Device",
                "Number of Orders"
            )
            
            plt.tight_layout()
            
            st.pyplot(
                fig,
                use_container_width=True
            )
            
            plt.close(fig)

        # ----------------------------------------------------
        # CHART 2 - REVENUE BY DEVICE
        # ----------------------------------------------------

        with col2:

            st.subheader(
                "Revenue by Device"
            )

            device_revenue = (
                data.groupby(
                    "device_type"
                )["final_price"]
                .sum()
            )

            fig, ax = plt.subplots(
                figsize=(4, 2.5)
            )



            device_revenue = (
                data.groupby("device_type")["final_price"]
                .sum()
            )

            fig, ax = plt.subplots(figsize=(4, 2.8))

            bars = ax.bar(
                device_revenue.index,
                device_revenue.values,
                label="Revenue"
            )

            ax.bar_label(
                bars,
                labels=[
                    f"₹{value:,.0f}"
                    for value in device_revenue.values
                ],
                padding=3,
                fontsize=7
            )

            style_chart(
                ax,
                "Revenue by Device",
                "Revenue (₹)"
            )

            plt.tight_layout()

            st.pyplot(
                fig,
                use_container_width=True
            )

            plt.close(fig)



        # ----------------------------------------------------
        # CHART 3 - ORDERS BY OPERATING SYSTEM
        # ----------------------------------------------------

        with col3:

            st.subheader(
                "Orders by OS"
            )

            os_orders = (
                data["operating_system"]
                .value_counts()
            )

            fig, ax = plt.subplots(figsize=(4, 2.8))

            wedges, texts, autotexts = ax.pie(
                os_orders.values,
                autopct="%1.0f%%",
                startangle=90
            )

            ax.legend(
                wedges,
                os_orders.index,
                title="Operating System",
                loc="center left",
                bbox_to_anchor=(1, 0.5),
                fontsize=7,
                frameon=False
            )

            ax.set_title(
                "Orders by Operating System",
                fontsize=11,
                fontweight="bold",
                pad=10
            )

            plt.tight_layout()

            st.pyplot(
                fig,
                use_container_width=True
            )

            plt.close(fig)

        # ====================================================
        # ROW 2
        # ====================================================

        col1, col2, col3 = st.columns(3)


        # ----------------------------------------------------
        # CHART 4 - REVENUE BY OS
        # ----------------------------------------------------

        with col1:

            st.subheader(
                "Revenue by OS"
            )

            os_revenue = (
                data.groupby("operating_system")["final_price"]
                .sum()
            )
            
            fig, ax = plt.subplots(figsize=(4, 2.8))
            
            bars = ax.bar(
                os_revenue.index,
                os_revenue.values,
                label="Revenue"
            )
            
            ax.bar_label(
                bars,
                labels=[
                    f"₹{value:,.0f}"
                    for value in os_revenue.values
                ],
                padding=3,
                fontsize=7
            )
            
            style_chart(
                ax,
                "Revenue by Operating System",
                "Revenue (₹)"
            )
            
            ax.tick_params(
                axis="x",
                rotation=20
            )
            
            plt.tight_layout()
            
            st.pyplot(
                fig,
                use_container_width=True
            )
            
            plt.close(fig)

            # ----------------------------------------------------
            # CHART 5 - ORDERS OVER TIME
            # ----------------------------------------------------
            
            with col2:
            
                st.subheader("Orders Over Time")
            
                orders_time = (
                    data.groupby("date")
                    .size()
                    .sort_index()
                )
            
                # Convert dates to simple strings
                date_labels = [
                    date.strftime("%d %b")
                    for date in orders_time.index
                ]
            
                fig, ax = plt.subplots(
                    figsize=(4, 2.5)
                )
            
                ax.plot(
                    date_labels,
                    orders_time.values,
                    marker="o",
                    linewidth=2,
                    label="Orders"
                )
            
                # Show values above points
                for i, value in enumerate(orders_time.values):
                
                    ax.text(
                        i,
                        value,
                        str(value),
                        ha="center",
                        va="bottom",
                        fontsize=8
                    )
            
                style_chart(
                    ax,
                    "Orders Over Time",
                    "Number of Orders"
                )
            
                ax.tick_params(
                    axis="x",
                    rotation=0
                )
            
                plt.tight_layout()
            
                st.pyplot(
                    fig,
                    use_container_width=True
                )
            
                plt.close(fig)


            # ----------------------------------------------------
            # CHART 6 - REVENUE OVER TIME
            # ----------------------------------------------------
            
            with col3:
            
                st.subheader("Revenue Over Time")
            
                revenue_time = (
                    data.groupby("date")["final_price"]
                    .sum()
                    .sort_index()
                )
            
                # Convert dates to simple strings
                date_labels = [
                    date.strftime("%d %b")
                    for date in revenue_time.index
                ]
            
                fig, ax = plt.subplots(
                    figsize=(4, 2.5)
                )
            
                ax.plot(
                    date_labels,
                    revenue_time.values,
                    marker="o",
                    linewidth=2,
                    label="Revenue"
                )
            
                # Show revenue values above points
                for i, value in enumerate(revenue_time.values):
                
                    ax.text(
                        i,
                        value,
                        f"₹{value:,.0f}",
                        ha="center",
                        va="bottom",
                        fontsize=7
                    )
            
                style_chart(
                    ax,
                    "Revenue Over Time",
                    "Revenue (₹)"
                )
            
                ax.tick_params(
                    axis="x",
                    rotation=0
                )
            
                plt.tight_layout()
            
                st.pyplot(
                    fig,
                    use_container_width=True
                )
            
                plt.close(fig)

        # ====================================================
        # ROW 3
        # ====================================================

        col1, col2, col3 = st.columns(3)


        # ----------------------------------------------------
        # CHART 7 - ORDER PRICE DISTRIBUTION
        # ----------------------------------------------------

        with col1:

            st.subheader(
                "Order Price Distribution"
            )


            fig, ax = plt.subplots(figsize=(4, 2.8))

            ax.hist(
                data["final_price"],
                bins=8,
                alpha=0.8,
                label="Orders"
            )

            style_chart(
                ax,
                "Order Price Distribution",
                "Number of Orders"
            )

            ax.set_xlabel(
                "Order Price (₹)",
                fontsize=9
            )

            plt.tight_layout()

            st.pyplot(
                fig,
                use_container_width=True
            )

            plt.close(fig)


        # ----------------------------------------------------
        # CHART 8 - AVERAGE PRICE BY DEVICE
        # ----------------------------------------------------

        with col2:

            st.subheader(
                "Average Price by Device"
            )


            average_device_price = (
                data.groupby("device_type")["final_price"]
                .mean()
            )

            fig, ax = plt.subplots(figsize=(4, 2.8))

            bars = ax.bar(
                average_device_price.index,
                average_device_price.values,
                label="Average Price"
            )

            ax.bar_label(
                bars,
                labels=[
                    f"₹{value:,.0f}"
                    for value in average_device_price.values
                ],
                padding=3,
                fontsize=7
            )

            style_chart(
                ax,
                "Average Price by Device",
                "Average Price (₹)"
            )

            plt.tight_layout()

            st.pyplot(
                fig,
                use_container_width=True
            )

            plt.close(fig)



        # ----------------------------------------------------
        # CHART 9 - AVERAGE PRICE BY OS
        # ----------------------------------------------------

        with col3:

            st.subheader(
                "Average Price by OS"
            )



            average_os_price = (
                data.groupby("operating_system")["final_price"]
                .mean()
            )

            fig, ax = plt.subplots(figsize=(4, 2.8))

            bars = ax.bar(
                average_os_price.index,
                average_os_price.values,
                label="Average Price"
            )

            ax.bar_label(
                bars,
                labels=[
                    f"₹{value:,.0f}"
                    for value in average_os_price.values
                ],
                padding=3,
                fontsize=7
            )

            style_chart(
                ax,
                "Average Price by Operating System",
                "Average Price (₹)"
            )

            ax.tick_params(
                axis="x",
                rotation=20
            )

            plt.tight_layout()

            st.pyplot(
                fig,
                use_container_width=True
            )

            plt.close(fig)



# ============================================================
# USER HOME / DASHBOARD
# ============================================================

elif page == "Home":

    st.markdown(
        f"""
        <div class="main-title">
            Welcome, {user_name}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(
        """
        <div class="subtitle">
            Build your own custom device with QuadOS Configurator
        </div>
        """,
        unsafe_allow_html=True
    )

    st.write("")

    st.write(
        "Choose a device category to start building."
    )

    st.write("")


    # ========================================================
    # ORDER COUNT
    # ========================================================

    order_count = get_user_order_count(user_id)

    st.metric(
        "My Orders",
        order_count
    )

    st.write("")

    st.subheader("Build Your Device")

    st.write("")



    # ========================================================
    # DEVICE OPTIONS
    # ========================================================
    
    col1, col2 = st.columns(2)
    
    
    # ========================================================
    # PC CARD
    # ========================================================
    
    with col1:
    
        pc_card = st.container(border=True)
    
        with pc_card:
        
            st.subheader("Custom PC")
    
            st.write(
                "Build a custom Windows or macOS computer "
                "using your preferred components."
            )
    
            st.write("")
    

            if st.button(
                "Start PC Builder",
                key="home_pc_builder",
                use_container_width=True,
                on_click=go_to_page,
                args=("PC Configurator",)
            ):
                pass

    
    # ========================================================
    # MOBILE CARD
    # ========================================================
    
    with col2:
    
        mobile_card = st.container(border=True)
    
        with mobile_card:
        
            st.subheader("Custom Mobile")
    
            st.write(
                "Configure an iPhone or Android device "
                "with your preferred features."
            )
    
            st.write("")
    

            if st.button(
                "Start Mobile Builder",
                key="home_mobile_builder",
                use_container_width=True,
                on_click=go_to_page,
                args=("Mobile Configurator",)
            ):
                pass


    
    st.write("")
    st.divider()




    st.subheader("QuadOS")

    st.write(
        """
        QuadOS focuses primarily on custom PC configuration,
        especially Windows and macOS systems.

        Mobile configuration for iPhone and Android is
        included as an additional part of the platform.
        """
    )


# ============================================================
# PC CONFIGURATOR
# ============================================================

elif page == "PC Configurator":

    st.title("PC Configurator")

    st.write(
        "Build your custom PC by selecting each component."
    )

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
            on_change=handle_pc_platform_change
        )

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

            # =================================================
            # PRICE SUMMARY
            # =================================================

            st.divider()

            st.subheader("Price Summary")

            price_col1, price_col2 = st.columns(2)

            with price_col1:
                st.write("**PC Components**")
                st.write("**Accessories**")
                st.write("**Final Price**")

            with price_col2:
                st.write(f"₹{pc_price:,.2f}")
                st.write(f"₹{accessory_price:,.2f}")
                st.write(f"₹{subtotal:,.2f}")

            st.divider()

            st.metric(
                "Final Price",
                f"₹{subtotal:,.2f}"
            )

            # =================================================
            # ORDER SUMMARY
            # =================================================

            st.divider()

            st.subheader("Order Summary")

            st.write("**Platform:** Windows PC")
            st.write(f"**Processor:** {cpu}")
            st.write(f"**Motherboard:** {motherboard}")
            st.write(f"**RAM:** {ram}")
            st.write(f"**Graphics Card:** {gpu}")
            st.write(f"**Storage:** {storage}")
            st.write(f"**Power Supply:** {power_supply}")
            st.write(f"**Cooling:** {cooling}")
            st.write(f"**Cabinet:** {cabinet}")
            st.write(f"**Monitor:** {monitor}")
            st.write(f"**Keyboard:** {keyboard}")
            st.write(f"**Mouse:** {mouse}")

            st.write("**Accessories:**")

            if accessory_names:
                for accessory in accessory_names:
                    st.write(f"- {accessory}")
            else:
                st.write("No accessories selected.")

            st.write("")
            st.write(f"**Final Price: ₹{subtotal:,.2f}**")

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

            # =================================================
            # PRICE SUMMARY
            # =================================================

            st.divider()

            st.subheader("Price Summary")

            st.write(
                f"**Processor:** ₹{MACOS_CPU_OPTIONS.get(mac_cpu, 0):,.2f}"
            )
            st.write(
                f"**Memory:** ₹{MACOS_RAM_OPTIONS.get(mac_ram, 0):,.2f}"
            )
            st.write(
                f"**Storage:** ₹{MACOS_STORAGE_OPTIONS.get(mac_storage, 0):,.2f}"
            )
            st.write(
                f"**Graphics:** ₹{MACOS_GPU_OPTIONS.get(mac_gpu, 0):,.2f}"
            )
            st.write(
                f"**Display:** ₹{MACOS_DISPLAY_OPTIONS.get(mac_display, 0):,.2f}"
            )
            st.write(
                f"**Keyboard:** ₹{MACOS_KEYBOARD_OPTIONS.get(mac_keyboard, 0):,.2f}"
            )
            st.write(
                f"**Mouse / Trackpad:** "
                f"₹{MACOS_MOUSE_OPTIONS.get(mac_mouse, 0):,.2f}"
            )
            st.write(
                f"**Accessories:** ₹{mac_accessory_price:,.2f}"
            )

            st.divider()

            st.metric(
                "Final Price",
                f"₹{mac_price:,.2f}"
            )

            # =================================================
            # MACOS ORDER SUMMARY
            # =================================================

            st.divider()

            st.subheader("Order Summary")

            st.write("**Platform:** macOS")
            st.write(f"**Processor:** {mac_cpu}")
            st.write(f"**Memory:** {mac_ram}")
            st.write(f"**Storage:** {mac_storage}")
            st.write(f"**Graphics:** {mac_gpu}")
            st.write(f"**Display:** {mac_display}")
            st.write(f"**Keyboard:** {mac_keyboard}")
            st.write(f"**Mouse / Trackpad:** {mac_mouse}")

            st.write("**Accessories:**")

            if mac_accessory_names:
                for accessory in mac_accessory_names:
                    st.write(f"- {accessory}")
            else:
                st.write("No accessories selected.")

            st.write("")
            st.write(f"**Final Price: ₹{mac_price:,.2f}**")

    # ========================================================
    # RIGHT SIDE — CART
    # ========================================================

    with pc_right:

        with st.container(border=True):

            st.subheader("🛒 Your Cart")

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

                st.markdown(
                    f"### Total: ₹{get_cart_total():,.2f}"
                )

                cart_os = st.session_state.get(
                    "cart_operating_system",
                    "Windows"
                )

                st.caption(
                    f"Platform: PC | OS: {cart_os}"
                )

                if st.button(
                    "Place Order",
                    key="place_cart_order",
                    use_container_width=True,
                    type="primary"
                ):

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

                    cart_total = get_cart_total()

                    order_date = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    create_order(
                        user_id=user_id,
                        device_type="PC",
                        operating_system=cart_os,
                        configuration=configuration_text,
                        accessories=accessories_text,
                        subtotal=cart_total,
                        discount=0,
                        final_price=cart_total,
                        order_date=order_date
                    )

                    st.success(
                        "Your order has been placed successfully."
                    )

                    clear_cart()

                    st.session_state.cart_operating_system = (
                        "Windows"
                    )

                    st.rerun()

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

    st.title("Mobile Configurator")

    st.write(
        "Create your custom smartphone."
    )

    mobile_type = st.selectbox(
        "Select Platform",
        [
            "iPhone",
            "Android"
        ]
    )

    # ========================================================
    # iPHONE
    # ========================================================

    if mobile_type == "iPhone":

        st.subheader("Custom iPhone")

        st.write(
            "Build your iPhone by selecting individual features."
        )

        st.divider()

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        iphone_display_display = st.selectbox(
            "Display",
            show_options(
                IPHONE_DISPLAY_OPTIONS
            )
        )

        iphone_display = iphone_display_display.split(
            " — ₹"
        )[0]

        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        iphone_battery_display = st.selectbox(
            "Battery Capacity",
            show_options(
                IPHONE_BATTERY_OPTIONS
            )
        )

        iphone_battery = iphone_battery_display.split(
            " — ₹"
        )[0]

        # ----------------------------------------------------
        # CAMERA
        # ----------------------------------------------------

        iphone_camera_display = st.selectbox(
            "Camera",
            show_options(
                IPHONE_CAMERA_OPTIONS
            )
        )

        iphone_camera = iphone_camera_display.split(
            " — ₹"
        )[0]

        # ----------------------------------------------------
        # RAM
        # ----------------------------------------------------

        iphone_ram_display = st.selectbox(
            "RAM",
            show_options(
                IPHONE_RAM_OPTIONS
            )
        )

        iphone_ram = iphone_ram_display.split(
            " — ₹"
        )[0]

        # ----------------------------------------------------
        # STORAGE
        # ----------------------------------------------------

        iphone_storage_display = st.selectbox(
            "Storage",
            show_options(
                IPHONE_STORAGE_OPTIONS
            )
        )

        iphone_storage = iphone_storage_display.split(
            " — ₹"
        )[0]

        # ----------------------------------------------------
        # PROCESSOR
        # ----------------------------------------------------

        iphone_processor_display = st.selectbox(
            "Processor",
            show_options(
                IPHONE_PROCESSOR_OPTIONS
            )
        )

        iphone_processor = iphone_processor_display.split(
            " — ₹"
        )[0]

        # ----------------------------------------------------
        # CONNECTIVITY
        # ----------------------------------------------------

        iphone_connectivity_display = st.selectbox(
            "Connectivity",
            show_options(
                IPHONE_CONNECTIVITY_OPTIONS
            )
        )

        iphone_connectivity = iphone_connectivity_display.split(
            " — ₹"
        )[0]

        # ----------------------------------------------------
        # FRAME
        # ----------------------------------------------------

        iphone_frame_display = st.selectbox(
            "Frame Material",
            show_options(
                IPHONE_FRAME_OPTIONS
            )
        )

        iphone_frame = iphone_frame_display.split(
            " — ₹"
        )[0]

        # ----------------------------------------------------
        # COLOR
        # ----------------------------------------------------

        iphone_color_display = st.selectbox(
            "Color",
            show_options(
                IPHONE_COLOR_OPTIONS
            )
        )

        iphone_color = iphone_color_display.split(
            " — ₹"
        )[0]

        # ====================================================
        # PRICE CALCULATION
        # ====================================================

        iphone_configuration = {

            "Display":
                IPHONE_DISPLAY_OPTIONS[
                    iphone_display
                ],

            "Battery":
                IPHONE_BATTERY_OPTIONS[
                    iphone_battery
                ],

            "Camera":
                IPHONE_CAMERA_OPTIONS[
                    iphone_camera
                ],

            "RAM":
                IPHONE_RAM_OPTIONS[
                    iphone_ram
                ],

            "Storage":
                IPHONE_STORAGE_OPTIONS[
                    iphone_storage
                ],

            "Processor":
                IPHONE_PROCESSOR_OPTIONS[
                    iphone_processor
                ],

            "Connectivity":
                IPHONE_CONNECTIVITY_OPTIONS[
                    iphone_connectivity
                ],

            "Frame":
                IPHONE_FRAME_OPTIONS[
                    iphone_frame
                ],

            "Color":
                IPHONE_COLOR_OPTIONS[
                    iphone_color
                ]
        }

        iphone_price = sum(iphone_configuration.values()
        )


        # ====================================================
        # ACCESSORIES
        # ====================================================

        st.divider()

        st.subheader("Accessories")

        st.write(
            "Select any accessories you want to add."
        )

        selected_iphone_accessories = st.multiselect(
            "Choose Accessories",
            show_options(
                IPHONE_ACCESSORY_OPTIONS
            )
        )

        iphone_accessory_names = [
            item.split(" — ₹")[0]
            for item in selected_iphone_accessories
        ]

        iphone_accessory_price = 0

        for accessory in iphone_accessory_names:
        
            iphone_accessory_price += (
                IPHONE_ACCESSORY_OPTIONS[accessory]
            )


        # ====================================================
        # FINAL PRICE
        # ====================================================

        iphone_price = (
            iphone_price
            + iphone_accessory_price
        )



        # ====================================================
        # PRICE SUMMARY
        # ====================================================

        st.divider()

        st.subheader("Price Summary")

        st.write(
            f"**Display:** "
            f"₹{IPHONE_DISPLAY_OPTIONS[iphone_display]:,.2f}"
        )

        st.write(
            f"**Battery:** "
            f"₹{IPHONE_BATTERY_OPTIONS[iphone_battery]:,.2f}"
        )

        st.write(
            f"**Camera:** "
            f"₹{IPHONE_CAMERA_OPTIONS[iphone_camera]:,.2f}"
        )

        st.write(
            f"**RAM:** "
            f"₹{IPHONE_RAM_OPTIONS[iphone_ram]:,.2f}"
        )

        st.write(
            f"**Storage:** "
            f"₹{IPHONE_STORAGE_OPTIONS[iphone_storage]:,.2f}"
        )

        st.write(
            f"**Processor:** "
            f"₹{IPHONE_PROCESSOR_OPTIONS[iphone_processor]:,.2f}"
        )

        st.write(
            f"**Connectivity:** "
            f"₹{IPHONE_CONNECTIVITY_OPTIONS[iphone_connectivity]:,.2f}"
        )

        st.write(
            f"**Frame:** "
            f"₹{IPHONE_FRAME_OPTIONS[iphone_frame]:,.2f}"
        )

        st.write(
            f"**Color:** "
            f"₹{IPHONE_COLOR_OPTIONS[iphone_color]:,.2f}"
        )

        st.write(
            f"**Accessories:** "
            f"₹{iphone_accessory_price:,.2f}"
)

        st.divider()

        st.metric(
            "Final Price",
            f"₹{iphone_price:,.2f}"
        )


        # ====================================================
        # iPHONE ORDER SUMMARY
        # ====================================================

        st.divider()

        st.subheader("Order Summary")

        st.write("**Device:** iPhone")

        st.write(
            f"**Display:** {iphone_display}"
        )

        st.write(
            f"**Battery:** {iphone_battery}"
        )

        st.write(
            f"**Camera:** {iphone_camera}"
        )

        st.write(
            f"**RAM:** {iphone_ram}"
        )

        st.write(
            f"**Storage:** {iphone_storage}"
        )

        st.write(
            f"**Processor:** {iphone_processor}"
        )

        st.write(
            f"**Connectivity:** {iphone_connectivity}"
        )

        st.write(
            f"**Frame:** {iphone_frame}"
        )

        st.write(
            f"**Color:** {iphone_color}"
        )

        st.write("**Accessories:**")

        if iphone_accessory_names:
        
            for accessory in iphone_accessory_names:
            
                st.write(
                    f"- {accessory}"
                )

        else:
        
            st.write(
                "No accessories selected."
            )

        st.write("")

        st.write(
            f"**Final Price: ₹{iphone_price:,.2f}**"
        )



        # ====================================================
        # PLACE iPHONE ORDER
        # ====================================================

        if st.button(
            "Place Order",
            use_container_width=True
        ):

            iphone_configuration_text = f"""
        Display: {iphone_display}
        Battery: {iphone_battery}
        Camera: {iphone_camera}
        RAM: {iphone_ram}
        Storage: {iphone_storage}
        Processor: {iphone_processor}
        Connectivity: {iphone_connectivity}
        Frame: {iphone_frame}
        Color: {iphone_color}
        """

            iphone_accessories_text = ", ".join(
                iphone_accessory_names
            )

            order_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            create_order(
                user_id=user_id,
                device_type="Mobile",
                operating_system="iOS",
                configuration=iphone_configuration_text,
                accessories=iphone_accessories_text,
                subtotal=iphone_price,
                discount=0,
                final_price=iphone_price,
                order_date=order_date
            )

            st.success(
                "Your iPhone order has been placed successfully."
            )



    # ========================================================
    # ANDROID
    # ========================================================

    else:

        st.subheader("Custom Android")

        st.write(
            "Build your Android smartphone by selecting individual features."
        )

        st.divider()

        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        android_display_display = st.selectbox(
            "Display",
            show_options(
                ANDROID_DISPLAY_OPTIONS
            )
        )

        android_display = android_display_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # BATTERY
        # ----------------------------------------------------

        android_battery_display = st.selectbox(
            "Battery Capacity",
            show_options(
                ANDROID_BATTERY_OPTIONS
            )
        )

        android_battery = android_battery_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # CAMERA
        # ----------------------------------------------------

        android_camera_display = st.selectbox(
            "Camera",
            show_options(
                ANDROID_CAMERA_OPTIONS
            )
        )

        android_camera = android_camera_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # RAM
        # ----------------------------------------------------

        android_ram_display = st.selectbox(
            "RAM",
            show_options(
                ANDROID_RAM_OPTIONS
            )
        )

        android_ram = android_ram_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # STORAGE
        # ----------------------------------------------------

        android_storage_display = st.selectbox(
            "Storage",
            show_options(
                ANDROID_STORAGE_OPTIONS
            )
        )

        android_storage = android_storage_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # PROCESSOR
        # ----------------------------------------------------

        android_processor_display = st.selectbox(
            "Processor",
            show_options(
                ANDROID_PROCESSOR_OPTIONS
            )
        )

        android_processor = android_processor_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # CONNECTIVITY
        # ----------------------------------------------------

        android_connectivity_display = st.selectbox(
            "Connectivity",
            show_options(
                ANDROID_CONNECTIVITY_OPTIONS
            )
        )

        android_connectivity = android_connectivity_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # BUILD MATERIAL
        # ----------------------------------------------------

        android_build_display = st.selectbox(
            "Build Material",
            show_options(
                ANDROID_BUILD_OPTIONS
            )
        )

        android_build = android_build_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # COLOR
        # ----------------------------------------------------

        android_color_display = st.selectbox(
            "Color",
            show_options(
                ANDROID_COLOR_OPTIONS
            )
        )

        android_color = android_color_display.split(
            " — ₹"
        )[0]


        # ====================================================
        # PRICE CALCULATION
        # ====================================================

        android_configuration = {

            "Display":
                ANDROID_DISPLAY_OPTIONS[
                    android_display
                ],

            "Battery":
                ANDROID_BATTERY_OPTIONS[
                    android_battery
                ],

            "Camera":
                ANDROID_CAMERA_OPTIONS[
                    android_camera
                ],

            "RAM":
                ANDROID_RAM_OPTIONS[
                    android_ram
                ],

            "Storage":
                ANDROID_STORAGE_OPTIONS[
                    android_storage
                ],

            "Processor":
                ANDROID_PROCESSOR_OPTIONS[
                    android_processor
                ],

            "Connectivity":
                ANDROID_CONNECTIVITY_OPTIONS[
                    android_connectivity
                ],

            "Build":
                ANDROID_BUILD_OPTIONS[
                    android_build
                ],

            "Color":
                ANDROID_COLOR_OPTIONS[
                    android_color
                ]
        }


        android_price = sum(
            android_configuration.values()
        )


        # ====================================================
        # ACCESSORIES
        # ====================================================

        st.divider()

        st.subheader("Accessories")

        st.write(
            "Select any accessories you want to add."
        )

        selected_android_accessories = st.multiselect(
            "Choose Accessories",
            show_options(
                ANDROID_ACCESSORY_OPTIONS
            )
        )

        android_accessory_names = [
            item.split(" — ₹")[0]
            for item in selected_android_accessories
        ]

        android_accessory_price = 0

        for accessory in android_accessory_names:
        
            android_accessory_price += (
                ANDROID_ACCESSORY_OPTIONS[accessory]
            )


        # ====================================================
        # FINAL PRICE
        # ====================================================

        android_price = (
            android_price
            + android_accessory_price
        )



        # ====================================================
        # PRICE SUMMARY
        # ====================================================

        st.divider()

        st.subheader("Price Summary")

        st.write(
            f"**Display:** "
            f"₹{ANDROID_DISPLAY_OPTIONS[android_display]:,.2f}"
        )

        st.write(
            f"**Battery:** "
            f"₹{ANDROID_BATTERY_OPTIONS[android_battery]:,.2f}"
        )

        st.write(
            f"**Camera:** "
            f"₹{ANDROID_CAMERA_OPTIONS[android_camera]:,.2f}"
        )

        st.write(
            f"**RAM:** "
            f"₹{ANDROID_RAM_OPTIONS[android_ram]:,.2f}"
        )

        st.write(
            f"**Storage:** "
            f"₹{ANDROID_STORAGE_OPTIONS[android_storage]:,.2f}"
        )

        st.write(
            f"**Processor:** "
            f"₹{ANDROID_PROCESSOR_OPTIONS[android_processor]:,.2f}"
        )

        st.write(
            f"**Connectivity:** "
            f"₹{ANDROID_CONNECTIVITY_OPTIONS[android_connectivity]:,.2f}"
        )

        st.write(
            f"**Build Material:** "
            f"₹{ANDROID_BUILD_OPTIONS[android_build]:,.2f}"
        )

        st.write(
            f"**Color:** "
            f"₹{ANDROID_COLOR_OPTIONS[android_color]:,.2f}"
        )

        st.divider()

        st.metric(
            "Final Price",
            f"₹{android_price:,.2f}"
        )

        st.write(
            f"**Accessories:** "
            f"₹{android_accessory_price:,.2f}"
        )


        # ====================================================
        # ANDROID ORDER SUMMARY
        # ====================================================

        st.divider()

        st.subheader("Order Summary")

        st.write("**Device:** Android")

        st.write(
            f"**Display:** {android_display}"
        )

        st.write(
            f"**Battery:** {android_battery}"
        )

        st.write(
            f"**Camera:** {android_camera}"
        )

        st.write(
            f"**RAM:** {android_ram}"
        )

        st.write(
            f"**Storage:** {android_storage}"
        )

        st.write(
            f"**Processor:** {android_processor}"
        )

        st.write(
            f"**Connectivity:** {android_connectivity}"
        )

        st.write(
            f"**Build Material:** {android_build}"
        )

        st.write(
            f"**Color:** {android_color}"
        )

        st.write("**Accessories:**")

        if android_accessory_names:
        
            for accessory in android_accessory_names:
            
                st.write(
                    f"- {accessory}"
                )

        else:
        
            st.write(
                "No accessories selected."
            )

        st.write("")

        st.write(
            f"**Final Price: ₹{android_price:,.2f}**"
        )



        # ====================================================
        # PLACE ANDROID ORDER
        # ====================================================

        if st.button(
            "Place Order",
            use_container_width=True
        ):

            android_configuration_text = f"""
        Display: {android_display}
        Battery: {android_battery}
        Camera: {android_camera}
        RAM: {android_ram}
        Storage: {android_storage}
        Processor: {android_processor}
        Connectivity: {android_connectivity}
        Build Material: {android_build}
        Color: {android_color}
        """

            android_accessories_text = ", ".join(
                android_accessory_names
            )

            order_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            create_order(
                user_id=user_id,
                device_type="Mobile",
                operating_system="Android",
                configuration=android_configuration_text,
                accessories=android_accessories_text,
                subtotal=android_price,
                discount=0,
                final_price=android_price,
                order_date=order_date
            )

            st.success(
                "Your Android order has been placed successfully."
            )



# ============================================================
# MY ORDERS
# ============================================================

elif page == "My Orders":

    st.title("My Orders")

    st.write(
        "View all your orders in a simple tabular format."
    )

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
                "Order Date": str(order_date)
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

    else:

        st.info(
            "You have not placed any orders yet."
        )



# ============================================================
# MY PROFILE
# ============================================================

elif page == "My Profile":

    st.title("My Profile")

    st.write(
        f"Name: {user_name}"
    )

    st.write(
        f"Email: {user_email}"
    )


# ============================================================
# ABOUT
# ============================================================

elif page == "About":

    st.title("About QuadOS")

    st.write(
        """
        QuadOS is a custom device configuration platform.

        The main focus of QuadOS is custom PC building,
        especially Windows and macOS systems.

        iPhone and Android customization are included
        as additional device categories.

        QuadOS supports dynamic configuration,
        pricing, accessories, discounts, orders
        and analytics.
        """
    )