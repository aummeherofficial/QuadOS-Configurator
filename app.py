import streamlit as st
import base64
from pathlib import Path
from datetime import datetime
import pandas as pd
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


def go_to_page(page_name):
    st.session_state.user_navigation = page_name



# ============================================================
# LOGIN / REGISTER
# ============================================================

if not st.session_state.logged_in:

    st.title("QuadOS")

    st.subheader("Login to QuadOS")

    login_tab, register_tab = st.tabs(
        ["Login", "Create Account"]
    )


    # ========================================================
    # LOGIN
    # ========================================================

    with login_tab:

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
            use_container_width=True
        ):

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
    # REGISTER
    # ========================================================

    with register_tab:

        st.subheader("Create User Account")

        name = st.text_input(
            "Full Name"
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

        phone = st.text_input(
            "Phone"
        )

        address = st.text_area(
            "Address"
        )

        if st.button(
            "Create Account",
            use_container_width=True
        ):

            if (
                name == ""
                or email == ""
                or password == ""
            ):

                st.warning(
                    "Please fill all required fields."
                )

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
        "View all orders placed through QuadOS."
    )

    st.write("")

    orders = get_all_orders_with_users()

    if orders:

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

            with st.container(border=True):

                st.subheader(
                    f"Order #{order_id}"
                )

                col1, col2, col3 = st.columns(3)

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

                with col2:

                    st.write(
                        f"**Subtotal:** "
                        f"₹{subtotal:,.2f}"
                    )

                    st.write(
                        f"**Final Price:** "
                        f"₹{final_price:,.2f}"
                    )

                with col3:

                    st.write(
                        f"**Order Date:** "
                        f"{order_date}"
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

    st.divider()

    # ========================================================
    # PLATFORM
    # ========================================================

    pc_type = st.selectbox(
        "Select Platform",
        [
            "Windows PC",
            "macOS"
        ]
    )

    # ========================================================
    # WINDOWS PC
    # ========================================================

    if pc_type == "Windows PC":

        st.subheader("Windows PC")

        st.write(
            "Select the components for your custom Windows PC."
        )

        st.divider()

        # ----------------------------------------------------
        # PROCESSOR
        # ----------------------------------------------------

        cpu_display = st.selectbox(
            "Processor",
            show_options(CPU_OPTIONS)
        )

        cpu = cpu_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # MOTHERBOARD
        # ----------------------------------------------------

        motherboard_display = st.selectbox(
            "Motherboard",
            show_options(MOTHERBOARD_OPTIONS)
        )

        motherboard = motherboard_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # RAM
        # ----------------------------------------------------

        ram_display = st.selectbox(
            "RAM",
            show_options(RAM_OPTIONS)
        )

        ram = ram_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # GPU
        # ----------------------------------------------------

        gpu_display = st.selectbox(
            "Graphics Card",
            show_options(GPU_OPTIONS)
        )

        gpu = gpu_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # STORAGE
        # ----------------------------------------------------

        storage_display = st.selectbox(
            "Storage",
            show_options(STORAGE_OPTIONS)
        )

        storage = storage_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # POWER SUPPLY
        # ----------------------------------------------------

        power_supply_display = st.selectbox(
            "Power Supply",
            show_options(POWER_SUPPLY_OPTIONS)
        )

        power_supply = power_supply_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # COOLING
        # ----------------------------------------------------

        cooling_display = st.selectbox(
            "Cooling",
            show_options(COOLING_OPTIONS)
        )

        cooling = cooling_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # CABINET
        # ----------------------------------------------------

        cabinet_display = st.selectbox(
            "Cabinet",
            show_options(CABINET_OPTIONS)
        )

        cabinet = cabinet_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # MONITOR
        # ----------------------------------------------------

        monitor_display = st.selectbox(
            "Monitor",
            show_options(MONITOR_OPTIONS)
        )

        monitor = monitor_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # KEYBOARD
        # ----------------------------------------------------

        keyboard_display = st.selectbox(
            "Keyboard",
            show_options(KEYBOARD_OPTIONS)
        )

        keyboard = keyboard_display.split(" — ₹")[0]

        # ----------------------------------------------------
        # MOUSE
        # ----------------------------------------------------

        mouse_display = st.selectbox(
            "Mouse",
            show_options(MOUSE_OPTIONS)
        )

        mouse = mouse_display.split(" — ₹")[0]

        # ====================================================
        # CONFIGURATION
        # ====================================================

        configuration = {

            "CPU": CPU_OPTIONS[cpu],

            "Motherboard":
                MOTHERBOARD_OPTIONS[motherboard],

            "RAM":
                RAM_OPTIONS[ram],

            "GPU":
                GPU_OPTIONS[gpu],

            "Storage":
                STORAGE_OPTIONS[storage],

            "Power Supply":
                POWER_SUPPLY_OPTIONS[power_supply],

            "Cooling":
                COOLING_OPTIONS[cooling],

            "Cabinet":
                CABINET_OPTIONS[cabinet],

            "Monitor":
                MONITOR_OPTIONS[monitor],

            "Keyboard":
                KEYBOARD_OPTIONS[keyboard],

            "Mouse":
                MOUSE_OPTIONS[mouse]
        }



        # ====================================================
        # ACCESSORIES
        # ====================================================

        st.divider()

        st.subheader("Accessories")

        st.write(
            "Select any accessories you want to add."
        )

        selected_accessories = st.multiselect(
"Choose Accessories",
            show_options(ACCESSORY_OPTIONS)
        )


        # ====================================================
        # ACCESSORY PRICE
        # ====================================================

        accessory_names = [
            item.split(" — ₹")[0]
            for item in selected_accessories
        ]

        accessory_price = 0

        for accessory in accessory_names:

            accessory_price += ACCESSORY_OPTIONS[accessory]



        # ====================================================
        # PRICE
        # ====================================================
        # ====================================================
        # PRICE BREAKDOWN
        # ====================================================

        pc_price = calculate_pc_price(
            configuration
        )

        subtotal = pc_price + accessory_price


        # ====================================================
        # PRICE SUMMARY
        # ====================================================

        st.divider()

        st.subheader("Price Summary")

        col1, col2 = st.columns(2)

        with col1:

            st.write("**PC Components**")

            st.write("**Accessories**")

            st.write("**Final Price**")

        with col2:

            st.write(
                f"₹{pc_price:,.2f}"
            )

            st.write(
                f"₹{accessory_price:,.2f}"
            )

            st.write(
                f"₹{subtotal:,.2f}"
            )


        st.divider()

        st.metric(
            "Final Price",
            f"₹{subtotal:,.2f}"
        )


        # ====================================================
        # ORDER SUMMARY
        # ====================================================

        st.divider()

        st.subheader("Order Summary")

        st.write("**Platform:** Windows PC")

        st.write(
            f"**Processor:** {cpu}"
        )

        st.write(
            f"**Motherboard:** {motherboard}"
        )

        st.write(
            f"**RAM:** {ram}"
        )

        st.write(
            f"**Graphics Card:** {gpu}"
        )

        st.write(
            f"**Storage:** {storage}"
        )

        st.write(
            f"**Power Supply:** {power_supply}"
        )

        st.write(
            f"**Cooling:** {cooling}"
        )

        st.write(
            f"**Cabinet:** {cabinet}"
        )

        st.write(
            f"**Monitor:** {monitor}"
        )

        st.write(
            f"**Keyboard:** {keyboard}"
        )

        st.write(
            f"**Mouse:** {mouse}"
        )

        st.write("**Accessories:**")

        if accessory_names:

            for accessory in accessory_names:

                st.write(
                    f"- {accessory}"
                )

        else:

            st.write(
                "No accessories selected."
            )

        st.write("")

        st.write(
            f"**Final Price: ₹{subtotal:,.2f}**"
        )


        # ====================================================
        # PLACE ORDER
        # ====================================================

        if st.button(
            "Place Order",
            use_container_width=True
        ):

            configuration_text = f"""
CPU: {cpu}
Motherboard: {motherboard}
RAM: {ram}
GPU: {gpu}
Storage: {storage}
Power Supply: {power_supply}
Cooling: {cooling}
Cabinet: {cabinet}
Monitor: {monitor}
Keyboard: {keyboard}
Mouse: {mouse}
"""

            accessories_text = ", ".join(
                accessory_names
            )

            order_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            create_order(
                user_id=user_id,
                device_type="PC",
                operating_system="Windows",
                configuration=configuration_text,
                accessories=accessories_text,
                subtotal=subtotal,
                discount=0,
                final_price=subtotal,
                order_date=order_date
            )

            st.success(
                "Your order has been placed successfully."
            )



    # ========================================================
    # macOS CONFIGURATOR
    # ========================================================

    else:

        st.subheader("macOS")

        st.write(
            "Build your custom macOS system."
        )

        st.divider()

        # ----------------------------------------------------
        # PROCESSOR
        # ----------------------------------------------------

        mac_cpu_display = st.selectbox(
            "Apple Processor",
            show_options(
                MACOS_CPU_OPTIONS
            )
        )

        mac_cpu = mac_cpu_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # RAM
        # ----------------------------------------------------

        mac_ram_display = st.selectbox(
            "Memory",
            show_options(
                MACOS_RAM_OPTIONS
            )
        )

        mac_ram = mac_ram_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # STORAGE
        # ----------------------------------------------------

        mac_storage_display = st.selectbox(
            "Storage",
            show_options(
                MACOS_STORAGE_OPTIONS
            )
        )

        mac_storage = mac_storage_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # GPU
        # ----------------------------------------------------

        mac_gpu_display = st.selectbox(
            "Graphics",
            show_options(
                MACOS_GPU_OPTIONS
            )
        )

        mac_gpu = mac_gpu_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # DISPLAY
        # ----------------------------------------------------

        mac_display_display = st.selectbox(
            "Display",
            show_options(
                MACOS_DISPLAY_OPTIONS
            )
        )

        mac_display = mac_display_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # KEYBOARD
        # ----------------------------------------------------

        mac_keyboard_display = st.selectbox(
            "Keyboard",
            show_options(
                MACOS_KEYBOARD_OPTIONS
            )
        )

        mac_keyboard = mac_keyboard_display.split(
            " — ₹"
        )[0]


        # ----------------------------------------------------
        # MOUSE / TRACKPAD
        # ----------------------------------------------------

        mac_mouse_display = st.selectbox(
            "Mouse / Trackpad",
            show_options(
                MACOS_MOUSE_OPTIONS
            )
        )

        mac_mouse = mac_mouse_display.split(
            " — ₹"
        )[0]


        # ====================================================
        # ACCESSORIES
        # ====================================================

        st.divider()

        st.subheader("Accessories")

        st.write(
            "Select any accessories you want to add."
        )

        selected_mac_accessories = st.multiselect(
            "Choose Accessories",
            show_options(
                MACOS_ACCESSORY_OPTIONS
            )
        )

        mac_accessory_names = [
            item.split(" — ₹")[0]
            for item in selected_mac_accessories
        ]

        mac_accessory_price = 0

        for accessory in mac_accessory_names:
        
            mac_accessory_price += (
                MACOS_ACCESSORY_OPTIONS[accessory]
            )



        # ====================================================
        # CONFIGURATION
        # ====================================================

        mac_configuration = {

            "Processor":
                MACOS_CPU_OPTIONS[mac_cpu],

            "Memory":
                MACOS_RAM_OPTIONS[mac_ram],

            "Storage":
                MACOS_STORAGE_OPTIONS[mac_storage],

            "Graphics":
                MACOS_GPU_OPTIONS[mac_gpu],

            "Display":
                MACOS_DISPLAY_OPTIONS[mac_display],

            "Keyboard":
                MACOS_KEYBOARD_OPTIONS[mac_keyboard],

            "Mouse / Trackpad":
                MACOS_MOUSE_OPTIONS[mac_mouse]
        }


        # ====================================================
        # PRICE
        # ====================================================

        mac_price = sum(
            mac_configuration.values()
        )


        st.divider()


        st.subheader("Price Summary")

        st.write(
            f"**Processor:** ₹{MACOS_CPU_OPTIONS[mac_cpu]:,.2f}"
        )

        st.write(
            f"**Memory:** ₹{MACOS_RAM_OPTIONS[mac_ram]:,.2f}"
        )

        st.write(
            f"**Storage:** ₹{MACOS_STORAGE_OPTIONS[mac_storage]:,.2f}"
        )

        st.write(
            f"**Graphics:** ₹{MACOS_GPU_OPTIONS[mac_gpu]:,.2f}"
        )

        st.write(
            f"**Display:** ₹{MACOS_DISPLAY_OPTIONS[mac_display]:,.2f}"
        )

        st.write(
            f"**Keyboard:** ₹{MACOS_KEYBOARD_OPTIONS[mac_keyboard]:,.2f}"
        )

        st.write(
            f"**Mouse / Trackpad:** "
            f"₹{MACOS_MOUSE_OPTIONS[mac_mouse]:,.2f}"
        )

        st.write(
            f"**Accessories:** "
            f"₹{mac_accessory_price:,.2f}"
        )

        st.divider()

        st.metric(
            "Final Price",
            f"₹{mac_price:,.2f}"
        )




        # ====================================================
        # MACOS ORDER SUMMARY
        # ====================================================

        st.divider()

        st.subheader("Order Summary")

        st.write("**Platform:** macOS")

        st.write(
            f"**Processor:** {mac_cpu}"
        )

        st.write(
            f"**Memory:** {mac_ram}"
        )

        st.write(
            f"**Storage:** {mac_storage}"
        )

        st.write(
            f"**Graphics:** {mac_gpu}"
        )

        st.write(
            f"**Display:** {mac_display}"
        )

        st.write(
            f"**Keyboard:** {mac_keyboard}"
        )

        st.write(
            f"**Mouse / Trackpad:** {mac_mouse}"
        )

        st.write("**Accessories:**")

        if mac_accessory_names:
        
            for accessory in mac_accessory_names:
            
                st.write(
                    f"- {accessory}"
                )

        else:
        
            st.write(
                "No accessories selected."
            )

        st.write("")

        st.write( f"**Final Price: ₹{mac_price:,.2f}**"
        )



# ====================================================
# PLACE macOS ORDER
# ====================================================

        if st.button(
            "Place Order",
            use_container_width=True
        ):

            mac_configuration_text = f"""
        Processor: {mac_cpu}
        Memory: {mac_ram}
        Storage: {mac_storage}
        Graphics: {mac_gpu}
        Display: {mac_display}
        Keyboard: {mac_keyboard}
        Mouse / Trackpad: {mac_mouse}
        """

            mac_accessories_text = ", ".join(
                mac_accessory_names
            )

            order_date = datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )

            create_order(
                user_id=user_id,
                device_type="PC",
                operating_system="macOS",
                configuration=mac_configuration_text,
                accessories=mac_accessories_text,
                subtotal=mac_price,
                discount=0,
                final_price=mac_price,
                order_date=order_date
            )

            st.success(
                "Your macOS order has been placed successfully."
            )




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
        "View your orders placed through QuadOS."
    )

    st.divider()

    orders = get_user_orders(user_id)

    if orders:

        for order in orders:

            order_id = order[0]
            device_type = order[2]
            operating_system = order[3]
            configuration = order[4]
            accessories = order[5]
            subtotal = order[6]
            final_price = order[8]
            order_date = order[9]

            with st.container(border=True):

                st.subheader(
                    f"Order #{order_id}"
                )

                col1, col2 = st.columns(2)

                with col1:

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

                st.write(
                    "**Configuration**"
                )

                st.code(
                    configuration
                    if configuration
                    else "No configuration details"
                )

                st.write(
                    "**Accessories**"
                )

                if accessories:

                    st.write(
                        accessories
                    )

                else:

                    st.write(
                        "No accessories"
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