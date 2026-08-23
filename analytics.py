import sqlite3
import pandas as pd
import matplotlib.pyplot as plt


DATABASE_NAME = "quados.db"


# ============================================================
# GET ORDER DATA
# ============================================================

def get_order_data():

    connection = sqlite3.connect(
        DATABASE_NAME
    )

    query = """
        SELECT
            device_type,
            operating_system,
            subtotal,
            final_price,
            order_date
        FROM orders
    """

    data = pd.read_sql_query(
        query,
        connection
    )

    connection.close()

    return data


# ============================================================
# ORDERS BY DEVICE
# ============================================================

def orders_by_device(data):

    return data["device_type"].value_counts()


# ============================================================
# REVENUE BY DEVICE
# ============================================================

def revenue_by_device(data):

    return data.groupby(
        "device_type"
    )["final_price"].sum()