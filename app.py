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
    cancel_order,
    get_user_orders,
    get_all_orders_with_users,
    verify_password_reset_user,
    reset_user_password,
    admin_reset_user_password
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

st.set_page_config(
    page_title="QuadOS.",
    page_icon="assets/quados_favicon.ico",
    layout="wide",
    initial_sidebar_state="expanded"
)


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



# ============================================================
# ORDER VALIDATION
# ============================================================

def validate_order_cart(cart, device_type, operating_system):
    """
    Validate that a device order contains enough core components
    to represent a usable PC/mobile configuration.

    Accessories are allowed to be ordered by themselves.
    A single non-accessory component is not allowed.
    """

    if not cart:
        return False, "Your cart is empty."

    # Accessories are optional and may be ordered alone.
    non_accessories = [
        item for item in cart
        if not str(item.get("category", "")).startswith(
            ("accessory:", "mobile_accessory:")
        )
    ]

    if not non_accessories:
        return True, ""

    selected_categories = {
        item.get("category")
        for item in non_accessories
    }

    # --------------------------------------------------------
    # WINDOWS PC
    # --------------------------------------------------------
    if device_type == "PC" and operating_system == "Windows":

        required = {
            "cpu",
            "motherboard",
            "ram",
            "storage",
            "power_supply",
            "cabinet"
        }

        missing = required - selected_categories

        if missing:
            labels = {
                "cpu": "Processor",
                "motherboard": "Motherboard",
                "ram": "RAM",
                "storage": "Storage",
                "power_supply": "Power Supply",
                "cabinet": "Cabinet"
            }

            missing_names = [
                labels[item]
                for item in required
                if item in missing
            ]

            return (
                False,
                "A Windows PC order must contain the core components: "
                + ", ".join(missing_names)
                + ". You can add GPU, cooling, monitor, keyboard, mouse and accessories optionally."
            )

    # --------------------------------------------------------
    # macOS
    # --------------------------------------------------------
    elif device_type == "PC" and operating_system == "macOS":

        required = {
            "processor",
            "memory",
            "storage",
            "display"
        }

        missing = required - selected_categories

        if missing:
            labels = {
                "processor": "Apple Processor",
                "memory": "Memory",
                "storage": "Storage",
                "display": "Display"
            }

            missing_names = [
                labels[item]
                for item in required
                if item in missing
            ]

            return (
                False,
                "A macOS order must contain the core components: "
                + ", ".join(missing_names)
                + ". Keyboard, mouse, graphics and accessories are optional."
            )

    # --------------------------------------------------------
    # MOBILE
    # --------------------------------------------------------
    elif device_type == "Mobile":

        if operating_system == "iOS":

            required = {
                "iphone_display",
                "iphone_battery",
                "iphone_ram",
                "iphone_storage",
                "iphone_processor",
                "iphone_connectivity"
            }

            labels = {
                "iphone_display": "Display",
                "iphone_battery": "Battery",
                "iphone_ram": "RAM",
                "iphone_storage": "Storage",
                "iphone_processor": "Processor",
                "iphone_connectivity": "Connectivity"
            }

        else:

            required = {
                "android_display",
                "android_battery",
                "android_ram",
                "android_storage",
                "android_processor",
                "android_connectivity"
            }

            labels = {
                "android_display": "Display",
                "android_battery": "Battery",
                "android_ram": "RAM",
                "android_storage": "Storage",
                "android_processor": "Processor",
                "android_connectivity": "Connectivity"
            }

        missing = required - selected_categories

        if missing:
            missing_names = [
                labels[item]
                for item in required
                if item in missing
            ]

            return (
                False,
                "A smartphone order must contain the core components: "
                + ", ".join(missing_names)
                + ". Camera, build/frame, color and accessories are optional."
            )

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------
    if len(non_accessories) == 1:
        return (
            False,
            "A single device component cannot be ordered by itself. Please build a complete device configuration. Accessories can be ordered separately."
        )

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
            options[selected_name],
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
                options[name],
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
    return float(options.get(selected_name, 0))


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

    st.title("QuadOS")
    st.subheader("Secure Login")

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
        phone = st.text_input("Phone", key="register_phone")
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
                    st.success("Account created successfully.")
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
                            st.success("Password reset successfully. You can now login.")
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


# ============================================================
# ORDER SUCCESS MESSAGE
# ============================================================

order_success_message = st.session_state.pop(
    "order_success_message",
    None
)

if order_success_message:
    st.success(order_success_message)


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

    st.write("View all registered QuadOS users in a table.")

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
            status = order[10]

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
        status = order[10] or "Placed"


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
                f"**Status:** {status}"
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

                        st.session_state.order_success_message = (
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

    # A cart belongs to the currently active device builder.
    # Switching from PC to Mobile starts a fresh mobile cart.
    if st.session_state.get("cart_device_type") != "Mobile":
        st.session_state.cart = []
        st.session_state.cart_device_type = "Mobile"
        st.session_state.cart_operating_system = "iOS"

    st.title("Mobile Configurator")

    st.write(
        "Create your custom smartphone."
    )

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
            on_change=handle_mobile_platform_change
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

            st.subheader("🛒 Your Cart")

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

                mobile_cart_total = get_cart_total()

                st.markdown(
                    f"### Total: ₹{mobile_cart_total:,.2f}"
                )

                mobile_cart_os = st.session_state.get(
                    "cart_operating_system",
                    "iOS" if mobile_type == "iPhone" else "Android"
                )

                st.caption(
                    f"Platform: Mobile | OS: {mobile_cart_os}"
                )

                if st.button(
                    "Place Order",
                    key="mobile_cart_place_order",
                    use_container_width=True,
                    type="primary"
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

                        mobile_cart_total = get_cart_total()

                        order_date = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        create_order(
                            user_id=user_id,
                            device_type="Mobile",
                            operating_system=mobile_cart_os,
                            configuration=configuration_text,
                            accessories=accessories_text,
                            subtotal=mobile_cart_total,
                            discount=0,
                            final_price=mobile_cart_total,
                            order_date=order_date
                        )

                        st.session_state.order_success_message = (
                            "Your mobile order has been placed successfully."
                        )

                        clear_cart()
                        st.session_state.cart_device_type = "Mobile"
                        st.rerun()

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

    st.title("My Orders")

    st.write(
        "View your orders and cancel an order when needed."
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

                    st.success(
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