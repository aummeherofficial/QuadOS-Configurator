
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
from market_pricing import market_price, calculate_bundle_discount

from query_database import (
    create_query_table,
    create_user_query,
    get_all_queries,
    get_user_queries,
    update_query_status,
    get_query_count
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


def _fallback_bundle_discount(cart):
    """Defensive discount calculation for carts from older sessions/files.

    The cart can contain categories from older QuadOS versions, so this
    fallback uses the actual cart contents instead of relying only on exact
    category names. This guarantees that a real multi-item combination gets
    an offer even when an older market_pricing.py is still installed.
    """
    items = list(cart or [])
    if not items:
        return 0.0, ""

    def is_accessory(item):
        category = str(item.get("category", "")).lower()
        name = str(item.get("name", "")).lower()
        return (
            category.startswith("accessory:")
            or category.startswith("mobile_accessory:")
            or name.startswith("accessory - ")
        )

    accessories = [item for item in items if is_accessory(item)]
    core_items = [item for item in items if not is_accessory(item)]
    core_count = len(core_items)
    accessory_count = len(accessories)

    device_type = str(
        st.session_state.get("cart_device_type", "")
    ).strip()
    operating_system = str(
        st.session_state.get("cart_operating_system", "")
    ).strip()

    # Infer the device if an old session did not store cart_device_type.
    categories = [str(item.get("category", "")).lower() for item in items]
    if not device_type:
        if any(c.startswith(("iphone_", "android_", "mobile_accessory:")) for c in categories):
            device_type = "Mobile"
        else:
            device_type = "PC"

    offers = []

    if core_count == 0:
        if accessory_count >= 3:
            offers.append((8.0, "3+ accessories — 8% bundle discount"))
        elif accessory_count >= 2:
            offers.append((5.0, "2 accessories — 5% bundle discount"))

    elif device_type == "Mobile":
        if core_count >= 6 and accessory_count >= 2:
            offers.append((10.0, "Smartphone + 2 accessories — 10% bundle discount"))
        if core_count >= 6 and accessory_count >= 1:
            offers.append((8.0, "Complete smartphone + accessory — 8% bundle discount"))
        if core_count >= 6:
            offers.append((7.0, "Complete smartphone — 7% bundle discount"))
        if core_count >= 4:
            offers.append((6.0, "4+ smartphone components — 6% discount"))
        if core_count >= 3:
            offers.append((5.0, "3+ smartphone components — 5% discount"))
        if core_count >= 2:
            offers.append((3.0, "Smartphone component combo — 3% discount"))

    elif operating_system == "macOS":
        if core_count >= 6 and accessory_count >= 1:
            offers.append((10.0, "Complete Mac + peripherals — 10% bundle discount"))
        if core_count >= 6:
            offers.append((8.0, "Complete macOS setup — 8% bundle discount"))
        if core_count >= 4:
            offers.append((7.0, "4+ Mac components — 7% discount"))
        if core_count >= 3:
            offers.append((5.0, "3+ Mac components — 5% discount"))
        if core_count >= 2:
            offers.append((3.0, "Mac component combo — 3% discount"))

    else:
        # Windows PC
        if core_count >= 6 and accessory_count >= 1:
            offers.append((12.0, "Complete PC + accessory — 12% bundle discount"))
        if core_count >= 6:
            offers.append((10.0, "Complete Windows PC — 10% bundle discount"))
        if core_count >= 4:
            offers.append((7.0, "4+ PC components — 7% discount"))
        if core_count >= 3:
            offers.append((5.0, "3+ PC components — 5% discount"))
        if core_count >= 2:
            offers.append((3.0, "PC component combo — 3% discount"))

    # Accessory combinations can improve an already qualifying device offer.
    if accessory_count >= 2 and core_count >= 2:
        offers.append((8.0, "Device + 2 accessories — 8% bundle discount"))

    return max(offers, key=lambda x: x[0]) if offers else (0.0, "")


def get_discounted_cart_totals():
    subtotal = get_cart_total()

    # First use the normal pricing module. If it returns 0 for a cart that
    # clearly contains a combination, use the defensive calculation above.
    percent, offer = calculate_bundle_discount(st.session_state.cart)

    if percent <= 0 and len(st.session_state.cart) >= 2:
        percent, offer = _fallback_bundle_discount(st.session_state.cart)

    discount = subtotal * percent / 100.0
    final = max(subtotal - discount, 0.0)
    return subtotal, discount, final, percent, offer


# ============================================================
# DATABASE
# ============================================================

create_tables()
create_admin()
create_query_table()


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
        "All Orders",
        "Manage Orders",
        "Analytics",
        "Queries",
        "About",
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
            "pc_cpu": "Intel Core i5", "pc_motherboard": "Mid Range Motherboard",
            "pc_ram": "16 GB", "pc_gpu": "Integrated Graphics", "pc_storage": "1 TB SSD",
            "pc_power_supply": "650W", "pc_cooling": "Air Cooler", "pc_cabinet": "Mid Range Cabinet",
            "pc_monitor": "24 inch Full HD", "pc_keyboard": "Basic Keyboard", "pc_mouse": "Basic Mouse",
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
            "pc_cpu": "Intel Core i7", "pc_motherboard": "High End Motherboard",
            "pc_ram": "32 GB", "pc_gpu": "NVIDIA RTX 4060", "pc_storage": "1 TB SSD",
            "pc_power_supply": "750W", "pc_cooling": "Tower Cooler", "pc_cabinet": "Mid Range Cabinet",
            "pc_monitor": "27 inch 2K", "pc_keyboard": "Mechanical Keyboard", "pc_mouse": "Gaming Mouse",
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
            "pc_cpu": "Intel Core i5", "pc_motherboard": "Basic Motherboard",
            "pc_ram": "16 GB", "pc_gpu": "Integrated Graphics", "pc_storage": "512 GB SSD",
            "pc_power_supply": "550W", "pc_cooling": "Stock Air Cooling", "pc_cabinet": "Basic Cabinet",
            "pc_monitor": "24 inch Full HD", "pc_keyboard": "Basic Keyboard", "pc_mouse": "Basic Mouse",
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
            "pc_cpu": "AMD Ryzen 7", "pc_motherboard": "Mid Range Motherboard",
            "pc_ram": "32 GB", "pc_gpu": "Integrated Graphics", "pc_storage": "1 TB SSD",
            "pc_power_supply": "650W", "pc_cooling": "Air Cooler", "pc_cabinet": "Mid Range Cabinet",
            "pc_monitor": "27 inch 2K", "pc_keyboard": "Mechanical Keyboard", "pc_mouse": "Basic Mouse",
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
            "pc_cpu": "Intel Core i7", "pc_motherboard": "High End Motherboard",
            "pc_ram": "32 GB", "pc_gpu": "NVIDIA RTX 4060", "pc_storage": "2 TB SSD",
            "pc_power_supply": "750W", "pc_cooling": "Tower Cooler", "pc_cabinet": "Premium Cabinet",
            "pc_monitor": "27 inch 2K", "pc_keyboard": "Mechanical Keyboard", "pc_mouse": "Gaming Mouse",
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
            "pc_cpu": "AMD Ryzen 9", "pc_motherboard": "High End Motherboard",
            "pc_ram": "64 GB", "pc_gpu": "NVIDIA RTX 4070", "pc_storage": "2 TB SSD",
            "pc_power_supply": "850W", "pc_cooling": "Liquid Cooling", "pc_cabinet": "Premium Cabinet",
            "pc_monitor": "27 inch 2K", "pc_keyboard": "Mechanical Keyboard", "pc_mouse": "Premium Gaming Mouse",
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
            "pc_cpu": "Intel Core i7", "pc_motherboard": "High End Motherboard",
            "pc_ram": "32 GB", "pc_gpu": "NVIDIA RTX 4060", "pc_storage": "1 TB SSD",
            "pc_power_supply": "750W", "pc_cooling": "Tower Cooler", "pc_cabinet": "Premium Cabinet",
            "pc_monitor": "27 inch 2K", "pc_keyboard": "Mechanical Keyboard", "pc_mouse": "Premium Gaming Mouse",
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
            "pc_cpu": "Intel Core i5", "pc_motherboard": "Basic Motherboard",
            "pc_ram": "16 GB", "pc_gpu": "Integrated Graphics", "pc_storage": "1 TB SSD",
            "pc_power_supply": "550W", "pc_cooling": "Stock Air Cooling", "pc_cabinet": "Basic Cabinet",
            "pc_monitor": "24 inch Full HD", "pc_keyboard": "Basic Keyboard", "pc_mouse": "Basic Mouse",
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
            "pc_cpu": "Intel Core i5", "pc_motherboard": "Basic Motherboard",
            "pc_ram": "16 GB", "pc_gpu": "Integrated Graphics", "pc_storage": "512 GB SSD",
            "pc_power_supply": "550W", "pc_cooling": "Stock Air Cooling", "pc_cabinet": "Mid Range Cabinet",
            "pc_monitor": "24 inch Full HD", "pc_keyboard": "Basic Keyboard", "pc_mouse": "Basic Mouse",
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
            if name in options and name not in ("Integrated Graphics", "No Monitor", "No Keyboard", "No Mouse", "Stock Air Cooling"):
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
        if name in options and options[name] > 0:
            category, label = categories[key]
            add_to_cart(f"{label} - {name}", market_price(options[name]), category=category)

    _set_profile_accessories(accessory_key, accessory_options, config.get(accessory_key, []))
    for name in config.get(accessory_key, []):
        if name in accessory_options:
            add_to_cart("Accessory - " + name, market_price(accessory_options[name]), category=f"mobile_accessory:{name}")

def handle_pc_profile_change():
    apply_pc_profile()

def handle_mobile_profile_change():
    apply_mobile_profile()

def reset_profile_for_pc_platform():
    st.session_state.pc_profile = "Balanced / Everyday"
    handle_pc_platform_change()

def reset_profile_for_mobile_platform():
    st.session_state.mobile_profile = "Balanced / Everyday"
    handle_mobile_platform_change()


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

        # Apply a requested destination BEFORE the admin navigation
        # radio widget is created. This avoids:
        # StreamlitAPIException: st.session_state.admin_navigation
        # cannot be modified after the widget ... is instantiated.
        if "admin_navigation_target" in st.session_state:
            _admin_target = st.session_state.pop("admin_navigation_target")

            if _admin_target in {
                "Admin Dashboard",
                "All Users",
                "All Orders",
                "Manage Orders",
                "Analytics",
                "Queries",
                "About",
            }:
                st.session_state.admin_navigation = _admin_target

        page = st.radio(
            "Navigation",
          [
            "Admin Dashboard",
            "All Users",
            "All Orders",
            "Manage Orders",
            "Analytics",
            "Queries",
            "About"
          ],
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

    # ========================================================
    # ADMIN DASHBOARD HEADER
    # ========================================================

    st.markdown(
        f"""
        <div style="
            padding:24px 28px;
            border-radius:18px;
            background:linear-gradient(135deg, rgba(20,25,45,.96), rgba(42,42,58,.90));
            border:1px solid rgba(255,255,255,.10);
            margin-bottom:22px;
        ">
            <div style="font-size:13px;opacity:.65;">QuadOS 3.0 • Administration</div>
            <div style="font-size:34px;font-weight:800;margin-top:5px;">Admin Dashboard</div>
            <div style="font-size:15px;opacity:.72;margin-top:6px;">
                Welcome back, {user_name}. Here's the current platform overview.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

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
    # 3. BUSINESS HEALTH — MODERN, COMPACT ANALYTICS
    # ========================================================

    st.subheader("📊 Business Health")

    health1, health2, health3 = st.columns(3, gap="medium")

    with health1:
        st.metric("Active / Placed Orders", f"{active_orders:,}")

    with health2:
        st.metric("Cancelled Orders", f"{cancelled_orders:,}")

    with health3:
        st.metric("Average Order Value", f"₹{average_order_value:,.0f}")

    st.write("")

    # Keep only the two most useful charts:
    # 1. Orders by device = where demand is coming from
    # 2. Order status = current order health
    device_counts = {}

    for order in all_orders:
        device_name = str(order[3] or "Unknown")
        device_counts[device_name] = device_counts.get(device_name, 0) + 1

    if device_counts:
        chart_col1, chart_col2 = st.columns(2, gap="large")

        # ----------------------------------------------------
        # CHART 1 - ORDERS BY DEVICE
        # ----------------------------------------------------
        with chart_col1:
            st.markdown("#### Orders by Device")

            labels = list(device_counts.keys())
            values = list(device_counts.values())

            fig, ax = plt.subplots(figsize=(6.2, 3.5))

            # Modern QuadOS dark chart styling
            fig.patch.set_facecolor("#111318")
            ax.set_facecolor("#111318")

            bars = ax.barh(
                labels,
                values,
                height=0.52,
                color="#F4C430"
            )

            max_value = max(values) if values else 1
            ax.set_xlim(0, max_value * 1.22)

            ax.invert_yaxis()

            for bar, value in zip(bars, values):
                ax.text(
                    value + max_value * 0.03,
                    bar.get_y() + bar.get_height() / 2,
                    f"{value}",
                    va="center",
                    fontsize=10,
                    fontweight="bold",
                    color="#FFFFFF"
                )

            ax.set_xlabel("")
            ax.set_ylabel("")
            ax.tick_params(
                axis="both",
                colors="#D7D9DE",
                labelsize=9,
                length=0
            )

            ax.grid(
                axis="x",
                linestyle="--",
                linewidth=0.7,
                color="#FFFFFF",
                alpha=0.12
            )

            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_visible(False)
            ax.spines["bottom"].set_color("#3A3D45")

            ax.set_title(
                "Orders by Device",
                loc="left",
                fontsize=12,
                fontweight="bold",
                color="#FFFFFF",
                pad=12
            )

            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        # ----------------------------------------------------
        # CHART 2 - ORDER STATUS
        # ----------------------------------------------------
        with chart_col2:
            st.markdown("#### Order Status")

            status_labels = ["Active / Placed", "Cancelled"]
            status_values = [active_orders, cancelled_orders]

            # Remove zero-value slices so the chart stays clean.
            filtered = [
                (label, value)
                for label, value in zip(status_labels, status_values)
                if value > 0
            ]

            fig, ax = plt.subplots(figsize=(6.2, 3.5))

            fig.patch.set_facecolor("#111318")
            ax.set_facecolor("#111318")

            if filtered:
                filtered_labels = [item[0] for item in filtered]
                filtered_values = [item[1] for item in filtered]

                status_colors = [
                    "#22C55E" if label == "Active / Placed" else "#EF4444"
                    for label in filtered_labels
                ]

                wedges, _ = ax.pie(
                    filtered_values,
                    startangle=90,
                    counterclock=False,
                    colors=status_colors,
                    wedgeprops={
                        "width": 0.38,
                        "edgecolor": "#111318",
                        "linewidth": 3
                    }
                )

                total_status = sum(filtered_values)

                ax.text(
                    0,
                    0.08,
                    f"{total_status}",
                    ha="center",
                    va="center",
                    fontsize=22,
                    fontweight="bold",
                    color="#FFFFFF"
                )

                ax.text(
                    0,
                    -0.16,
                    "Total Orders",
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="#AEB3BE"
                )

                legend_labels = [
                    f"{label}  •  {value}"
                    for label, value in zip(filtered_labels, filtered_values)
                ]

                ax.legend(
                    wedges,
                    legend_labels,
                    loc="center left",
                    bbox_to_anchor=(0.98, 0.5),
                    frameon=False,
                    fontsize=9,
                    labelcolor="#D7D9DE"
                )
            else:
                ax.text(
                    0.5,
                    0.5,
                    "No order data",
                    transform=ax.transAxes,
                    ha="center",
                    va="center",
                    color="#AEB3BE",
                    fontsize=11
                )

            ax.set_title(
                "Order Status",
                loc="left",
                fontsize=12,
                fontweight="bold",
                color="#FFFFFF",
                pad=12
            )

            plt.tight_layout()
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

    else:
        st.info("Business activity will appear after orders are placed.")

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

    st.divider()

    # ========================================================
    # 6. QUICK ADMIN ACTIONS
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

    st.caption(
        "View, inspect and manage all customer orders from one place."
    )

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
        # DELETE ORDER
        # ----------------------------------------------------

        st.divider()

        delete_col, _ = st.columns([1, 3])

        with delete_col:

            if st.button(
                "Delete Order",
                type="primary",
                key=f"delete_admin_order_{order_id}",
                use_container_width=True
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
    st.write("A clear view of orders, revenue, customer buying patterns and trends.")
    st.divider()

    # ========================================================
    # GET DATA
    # ========================================================

    data = get_order_data()

    if data.empty:
        st.info("No order data available for analytics yet.")

    else:
        # ====================================================
        # PREPARE DATA
        # ====================================================

        data = data.copy()
        data["order_date"] = pd.to_datetime(data["order_date"], errors="coerce")
        data["final_price"] = pd.to_numeric(data["final_price"], errors="coerce").fillna(0)
        data["device_type"] = data["device_type"].fillna("Unknown").astype(str)
        data["operating_system"] = data["operating_system"].fillna("Unknown").astype(str)
        data = data.dropna(subset=["order_date"])
        data["date"] = data["order_date"].dt.normalize()

        total_orders = len(data)
        total_revenue = data["final_price"].sum()
        average_order_value = data["final_price"].mean() if total_orders else 0

        # ====================================================
        # SUMMARY CARDS
        # ====================================================

        col1, col2, col3, col4 = st.columns(4, gap="medium")

        with col1:
            st.metric("Total Orders", f"{total_orders:,}")

        with col2:
            st.metric("Total Revenue", f"₹{total_revenue:,.0f}")

        with col3:
            st.metric("Average Order Value", f"₹{average_order_value:,.0f}")

        with col4:
            highest_order = data["final_price"].max() if total_orders else 0
            st.metric("Highest Order", f"₹{highest_order:,.0f}")

        st.divider()

        # ====================================================
        # ANALYTICS CHART STYLE
        # ====================================================

        CHART_BG = "#111827"
        TEXT = "#E5E7EB"
        MUTED = "#9CA3AF"
        GRID = "#374151"
        BLUE = "#38BDF8"
        ORANGE = "#F59E0B"
        GREEN = "#34D399"
        PURPLE = "#A78BFA"
        RED = "#FB7185"
        TEAL = "#2DD4BF"

        def analytics_style(ax, title, ylabel=""):
            ax.set_title(
                title,
                fontsize=13,
                fontweight="bold",
                color=TEXT,
                loc="left",
                pad=12,
            )
            ax.set_ylabel(ylabel, color=MUTED, fontsize=9)
            ax.tick_params(axis="both", colors=MUTED, labelsize=9)
            ax.grid(axis="y", linestyle="--", linewidth=0.7, alpha=0.35, color=GRID)
            ax.set_axisbelow(True)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(GRID)
            ax.spines["bottom"].set_color(GRID)
            ax.set_facecolor(CHART_BG)

        def finish_chart(fig):
            fig.patch.set_facecolor(CHART_BG)
            plt.tight_layout(pad=1.5)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

        def rupee_short(value):
            value = float(value)
            if abs(value) >= 10_000_000:
                return f"₹{value / 10_000_000:.1f}Cr"
            if abs(value) >= 100_000:
                return f"₹{value / 100_000:.1f}L"
            if abs(value) >= 1_000:
                return f"₹{value / 1_000:.0f}K"
            return f"₹{value:.0f}"

        # ====================================================
        # ROW 1 — DEVICE PERFORMANCE
        # ====================================================

        st.subheader("📦 Device Performance")
        col1, col2 = st.columns(2, gap="large")

        # ----------------------------------------------------
        # CHART 1 - ORDERS BY DEVICE
        # ----------------------------------------------------

        with col1:
            device_orders = data["device_type"].value_counts().sort_values()

            fig, ax = plt.subplots(figsize=(7, 4))
            bars = ax.barh(
                device_orders.index,
                device_orders.values,
                color=BLUE,
                height=0.55,
            )

            ax.bar_label(
                bars,
                labels=[f"{int(v):,}" for v in device_orders.values],
                padding=5,
                fontsize=9,
                color=TEXT,
            )
            ax.set_xlabel("Number of orders", color=MUTED, fontsize=9)
            analytics_style(ax, "Orders by Device", "")
            ax.grid(axis="x", linestyle="--", linewidth=0.7, alpha=0.3, color=GRID)
            ax.grid(axis="y", visible=False)
            finish_chart(fig)

        # ----------------------------------------------------
        # CHART 2 - REVENUE BY DEVICE
        # ----------------------------------------------------

        with col2:
            device_revenue = (
                data.groupby("device_type")["final_price"]
                .sum()
                .sort_values()
            )

            fig, ax = plt.subplots(figsize=(7, 4))
            bars = ax.barh(
                device_revenue.index,
                device_revenue.values,
                color=ORANGE,
                height=0.55,
            )

            ax.bar_label(
                bars,
                labels=[rupee_short(v) for v in device_revenue.values],
                padding=5,
                fontsize=9,
                color=TEXT,
            )
            ax.set_xlabel("Revenue", color=MUTED, fontsize=9)
            analytics_style(ax, "Revenue by Device", "")
            ax.grid(axis="x", linestyle="--", linewidth=0.7, alpha=0.3, color=GRID)
            ax.grid(axis="y", visible=False)
            finish_chart(fig)

        st.divider()

        # ====================================================
        # ROW 2 — CUSTOMER CHOICES
        # ====================================================

        st.subheader("🧩 Customer Choices")
        col1, col2 = st.columns(2, gap="large")

        # ----------------------------------------------------
        # CHART 3 - ORDERS BY OPERATING SYSTEM
        # ----------------------------------------------------

        with col1:
            os_orders = data["operating_system"].value_counts().sort_values()

            fig, ax = plt.subplots(figsize=(7, 4))
            bars = ax.barh(
                os_orders.index,
                os_orders.values,
                color=GREEN,
                height=0.55,
            )

            ax.bar_label(
                bars,
                labels=[f"{int(v):,}" for v in os_orders.values],
                padding=5,
                fontsize=9,
                color=TEXT,
            )
            ax.set_xlabel("Number of orders", color=MUTED, fontsize=9)
            analytics_style(ax, "Orders by Operating System", "")
            ax.grid(axis="x", linestyle="--", linewidth=0.7, alpha=0.3, color=GRID)
            ax.grid(axis="y", visible=False)
            finish_chart(fig)

        # ----------------------------------------------------
        # CHART 4 - REVENUE SHARE BY OS
        # ----------------------------------------------------

        with col2:
            os_revenue = (
                data.groupby("operating_system")["final_price"]
                .sum()
                .sort_values(ascending=False)
            )

            fig, ax = plt.subplots(figsize=(7, 4))
            pie_colors = [BLUE, PURPLE, TEAL, ORANGE, RED, GREEN]

            wedges, _, autotexts = ax.pie(
                os_revenue.values,
                autopct=lambda p: f"{p:.0f}%" if p >= 4 else "",
                startangle=90,
                counterclock=False,
                colors=pie_colors[:len(os_revenue)],
                wedgeprops={"width": 0.42, "edgecolor": CHART_BG, "linewidth": 2},
                pctdistance=0.78,
            )

            for text in autotexts:
                text.set_color(TEXT)
                text.set_fontsize(9)
                text.set_fontweight("bold")

            legend_labels = [
                f"{name} — {rupee_short(value)}"
                for name, value in os_revenue.items()
            ]
            ax.legend(
                wedges,
                legend_labels,
                title="Revenue",
                loc="center left",
                bbox_to_anchor=(0.98, 0.5),
                fontsize=8,
                title_fontsize=9,
                frameon=False,
                labelcolor=TEXT,
            )
            ax.set_title(
                "Revenue Share by Operating System",
                fontsize=13,
                fontweight="bold",
                color=TEXT,
                loc="left",
                pad=12,
            )
            ax.set_facecolor(CHART_BG)
            finish_chart(fig)

        st.divider()

        # ====================================================
        # ROW 3 — BUSINESS TRENDS
        # ====================================================

        st.subheader("📈 Business Trends")
        col1, col2 = st.columns(2, gap="large")

        # ----------------------------------------------------
        # CHART 5 - ORDERS OVER TIME
        # ----------------------------------------------------

        with col1:
            orders_time = data.groupby("date").size().sort_index()

            fig, ax = plt.subplots(figsize=(7, 4))
            ax.plot(
                orders_time.index,
                orders_time.values,
                marker="o",
                markersize=5,
                linewidth=2.5,
                color=BLUE,
            )
            ax.fill_between(
                orders_time.index,
                orders_time.values,
                alpha=0.12,
                color=BLUE,
            )

            for date, value in orders_time.items():
                ax.annotate(
                    str(int(value)),
                    (date, value),
                    textcoords="offset points",
                    xytext=(0, 8),
                    ha="center",
                    fontsize=8,
                    color=TEXT,
                )

            analytics_style(ax, "Orders Over Time", "Orders")
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            ax.tick_params(axis="x", rotation=30)
            ax.grid(axis="x", visible=False)
            finish_chart(fig)

        # ----------------------------------------------------
        # CHART 6 - REVENUE OVER TIME
        # ----------------------------------------------------

        with col2:
            revenue_time = data.groupby("date")["final_price"].sum().sort_index()

            fig, ax = plt.subplots(figsize=(7, 4))
            ax.plot(
                revenue_time.index,
                revenue_time.values,
                marker="o",
                markersize=5,
                linewidth=2.5,
                color=ORANGE,
            )
            ax.fill_between(
                revenue_time.index,
                revenue_time.values,
                alpha=0.12,
                color=ORANGE,
            )

            analytics_style(ax, "Revenue Over Time", "Revenue")
            ax.xaxis.set_major_locator(mdates.AutoDateLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
            ax.tick_params(axis="x", rotation=30)
            ax.grid(axis="x", visible=False)
            ax.yaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, pos: rupee_short(x))
            )
            finish_chart(fig)

        st.divider()

        # ====================================================
        # ROW 4 — ORDER VALUE INSIGHTS
        # ====================================================

        st.subheader("💰 Order Value Insights")
        col1, col2 = st.columns(2, gap="large")

        # ----------------------------------------------------
        # CHART 7 - ORDER VALUE DISTRIBUTION
        # ----------------------------------------------------

        with col1:
            fig, ax = plt.subplots(figsize=(7, 4))
            ax.hist(
                data["final_price"],
                bins=min(10, max(4, total_orders)),
                color=PURPLE,
                alpha=0.85,
                edgecolor=CHART_BG,
                linewidth=1.2,
            )

            ax.axvline(
                average_order_value,
                color=ORANGE,
                linewidth=2,
                linestyle="--",
                label=f"Average: {rupee_short(average_order_value)}",
            )
            ax.legend(frameon=False, fontsize=9, labelcolor=TEXT)
            ax.xaxis.set_major_formatter(
                plt.FuncFormatter(lambda x, pos: rupee_short(x))
            )
            ax.set_xlabel("Order value", color=MUTED, fontsize=9)
            analytics_style(ax, "Order Value Distribution", "Number of Orders")
            finish_chart(fig)

        # ----------------------------------------------------
        # CHART 8 - AVERAGE ORDER VALUE BY DEVICE
        # ----------------------------------------------------

        with col2:
            average_device_price = (
                data.groupby("device_type")["final_price"]
                .mean()
                .sort_values()
            )

            fig, ax = plt.subplots(figsize=(7, 4))
            bars = ax.barh(
                average_device_price.index,
                average_device_price.values,
                color=PURPLE,
                height=0.55,
            )

            ax.bar_label(
                bars,
                labels=[rupee_short(v) for v in average_device_price.values],
                padding=5,
                fontsize=9,
                color=TEXT,
            )
            ax.set_xlabel("Average order value", color=MUTED, fontsize=9)
            analytics_style(ax, "Average Order Value by Device", "")
            ax.grid(axis="x", linestyle="--", linewidth=0.7, alpha=0.3, color=GRID)
            ax.grid(axis="y", visible=False)
            finish_chart(fig)

        st.caption(
            "Tip: horizontal bars make category comparisons easier, while the line charts show how orders and revenue change over time."
        )


# ============================================================
# USER HOME / DASHBOARD
# ============================================================


# ============================================================

elif page == "Home":

    render_offers_section()

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

    render_offers_section()

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
            on_change=reset_profile_for_pc_platform
        )

        if "pc_profile" not in st.session_state:
            st.session_state.pc_profile = "Balanced / Everyday"
            apply_pc_profile()

        st.selectbox(
            "Configuration Profile",
            PC_PROFILE_OPTIONS,
            key="pc_profile",
            on_change=handle_pc_profile_change,
            help="Choose a use-case and QuadOS will load a suitable starting configuration. You can change every component afterward."
        )

        st.caption("💡 Selecting a profile automatically fills suitable components. You can customize any selection afterward.")

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

                        cart_subtotal, cart_discount, cart_final, _, _ = get_discounted_cart_totals()

                        order_date = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        create_order(
                            user_id=user_id,
                            device_type="PC",
                            operating_system=cart_os,
                            configuration=configuration_text,
                            accessories=accessories_text,
                            subtotal=cart_subtotal,
                            discount=cart_discount,
                            final_price=cart_final,
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

    render_offers_section()

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
            on_change=reset_profile_for_mobile_platform
        )

        if "mobile_profile" not in st.session_state:
            st.session_state.mobile_profile = "Balanced / Everyday"
            apply_mobile_profile()

        st.selectbox(
            "Configuration Profile",
            MOBILE_PROFILE_OPTIONS,
            key="mobile_profile",
            on_change=handle_mobile_profile_change,
            help="Choose a use-case and QuadOS will load a suitable starting configuration. You can change every feature afterward."
        )

        st.caption("💡 Selecting a profile automatically fills suitable features. You can customize any selection afterward.")

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

                        mobile_cart_subtotal, mobile_cart_discount, mobile_cart_final, _, _ = get_discounted_cart_totals()

                        order_date = datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )

                        create_order(
                            user_id=user_id,
                            device_type="Mobile",
                            operating_system=mobile_cart_os,
                            configuration=configuration_text,
                            accessories=accessories_text,
                            subtotal=mobile_cart_subtotal,
                            discount=mobile_cart_discount,
                            final_price=mobile_cart_final,
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
    st.caption("Manage and review your QuadOS account information.")

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

elif page == "About":

    st.title("About QuadOS")
    st.write(
        "QuadOS is a custom device configuration platform for building, "
        "pricing and ordering personalized PCs and smartphones."
    )

    st.divider()

    # --------------------------------------------------------
    # FEATURES
    # --------------------------------------------------------
    st.subheader("Features")

    feature_col1, feature_col2 = st.columns(2)

    with feature_col1:
        st.markdown("""
        **🖥️ PC Configurator**  
        Build Windows and macOS PC combinations using configurable components.

        **📱 Mobile Configurator**  
        Configure iPhone and Android devices with supported hardware options.

        **🛒 Smart Cart**  
        Selected components and accessories are added directly to the cart.

        **📦 Order Management**  
        Users can view their orders and cancel eligible orders.
        """)

    with feature_col2:
        st.markdown("""
        **💰 Dynamic Pricing**  
        Component prices are combined to calculate the final order value.

        **🔐 Authentication**  
        User registration, login and password reset are supported.

        **📊 Analytics**  
        Admins can view order, revenue and device analytics.

        **👨‍💼 Admin Management**  
        Admins can manage users, orders and submitted queries.
        """)

    st.divider()

    # --------------------------------------------------------
    # HOW IT WORKS
    # --------------------------------------------------------
    st.subheader("How QuadOS Works")
    st.markdown("""
    **1. Create an account or log in**  
    **2. Choose PC or Mobile Configurator**  
    **3. Select a complete device combination**  
    **4. Add components/accessories to the cart**  
    **5. Review the cart and place the order**  
    **6. Track the order from My Orders**
    """)

    st.divider()

    # --------------------------------------------------------
    # SUPPORTED DEVICES
    # --------------------------------------------------------
    st.subheader("Supported Devices")
    supported_col1, supported_col2 = st.columns(2)

    with supported_col1:
        st.markdown("""
        ### 🖥️ PC
        - Windows PC
        - macOS PC
        - CPU / Processor
        - Motherboard
        - RAM
        - Storage
        - GPU
        - Cooling
        - Cabinet
        - Monitor and peripherals
        """)

    with supported_col2:
        st.markdown("""
        ### 📱 Mobile
        - iPhone
        - Android
        - Display
        - Battery
        - RAM
        - Storage
        - Processor
        - Camera
        - Connectivity
        - Build / Frame / Color
        """)

    st.divider()

    # --------------------------------------------------------
    # CONTACT
    # --------------------------------------------------------
    st.subheader("Contact & Support")
    st.write("Need help with QuadOS? Use the query form below and your question will be sent to the QuadOS support database.")

    contact_col1, contact_col2 = st.columns(2)

    with contact_col1:
        st.info("📧 Support: Submit a question through the Help & Query section below.")

    with contact_col2:
        st.info("🕐 Support Requests: Your submission is recorded with date and time for admin review.")

    st.divider()

    # --------------------------------------------------------
    # FAQ / HELP
    # --------------------------------------------------------
    st.subheader("Help & Frequently Asked Questions")

    with st.expander("Can I order only one PC component?"):
        st.write("No. A PC order must contain the required combination of components. Accessories can be ordered separately.")

    with st.expander("Can I order only an accessory?"):
        st.write("Yes. Accessory-only orders are allowed.")

    with st.expander("Can I cancel my order?"):
        st.write("Yes. Go to My Orders and select an eligible order to cancel it.")

    with st.expander("Where can I see my orders?"):
        st.write("Open My Orders from the user navigation menu.")

    with st.expander("What happens after I submit a question?"):
        st.write("Your question is stored in the separate QuadOS queries database and becomes visible to the admin in the Queries section.")

    st.divider()

    # --------------------------------------------------------
    # ASK A QUESTION
    # --------------------------------------------------------
    st.subheader("Ask a Question / Send a Help Query")
    st.write("Submit your question below. It will be saved in the QuadOS queries database for admin review.")

    with st.form("user_query_form", clear_on_submit=True):

        query_subject = st.text_input(
            "Subject",
            placeholder="Example: Login problem"
        )

        query_question = st.text_area(
            "Your Question",
            placeholder="Describe your question or problem...",
            height=150
        )

        submit_query = st.form_submit_button(
            "Send Question",
            type="primary",
            use_container_width=True
        )

        if submit_query:

            if not query_subject.strip():
                st.error("Please enter a subject.")

            elif not query_question.strip():
                st.error("Please enter your question.")

            else:
                submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                query_id = create_user_query(
                    user_id=user_id,
                    name=user_name,
                    email=user_email,
                    subject=query_subject,
                    question=query_question,
                    submitted_at=submitted_at
                )

                st.success(
                    f"Your question has been submitted successfully. Query ID: #{query_id}"
                )

    st.divider()

    # --------------------------------------------------------
    # FUTURE ROADMAP
    # --------------------------------------------------------
    st.subheader("Future Roadmap")
    st.markdown("""
    - 🤖 Machine Learning price prediction
    - 🧾 Invoice generation
    - 📈 Additional analytics and insights
    - 🔔 Improved order notifications
    - 💬 Enhanced customer support workflow
    """)
