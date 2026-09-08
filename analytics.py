import sqlite3
import pandas as pd

DATABASE_NAME = "quados.db"


def get_order_data():
    """Return the complete order history for analytics.

    Revenue is calculated separately from order activity, so cancelled,
    pending, and failed records remain visible without being counted as revenue.
    """
    connection = sqlite3.connect(DATABASE_NAME)
    query = """
        SELECT
            id, device_type, operating_system, subtotal, final_price,
            order_date, status, payment_status, payment_date, cancelled_date
        FROM orders
        ORDER BY order_date
    """
    data = pd.read_sql_query(query, connection)
    connection.close()
    return data


def orders_by_device(data):
    return data["device_type"].value_counts()


def revenue_by_device(data):
    paid = data[
        (data["payment_status"].fillna("Pending").str.lower() == "paid")
        & (data["status"].fillna("Placed").str.lower() != "cancelled")
    ]
    return paid.groupby("device_type")["final_price"].sum()
