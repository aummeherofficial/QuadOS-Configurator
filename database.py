import sqlite3


DATABASE_NAME = "quados.db"


def get_connection():
    return sqlite3.connect(DATABASE_NAME)


# ============================================================
# CREATE TABLES
# ============================================================

def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    # USERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            phone TEXT,
            address TEXT,
            role TEXT DEFAULT 'user'
        )
    """)

    # ORDERS TABLE
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_type TEXT NOT NULL,
            operating_system TEXT,
            configuration TEXT,
            accessories TEXT,
            subtotal REAL,
            discount REAL,
            final_price REAL,
            order_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    connection.commit()
    connection.close()


# ============================================================
# CREATE USER
# ============================================================

def create_user(name, email, password, phone, address):

    connection = get_connection()
    cursor = connection.cursor()

    try:

        cursor.execute("""
            INSERT INTO users
            (name, email, password, phone, address, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            name,
            email,
            password,
            phone,
            address,
            "user"
        ))

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        connection.close()


# ============================================================
# LOGIN
# ============================================================

def login_user(email, password):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, email, role
        FROM users
        WHERE email = ? AND password = ?
    """, (
        email,
        password
    ))

    user = cursor.fetchone()

    connection.close()

    return user


# ============================================================
# CREATE ADMIN
# ============================================================

def create_admin():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id
        FROM users
        WHERE email = ?
    """, ("admin@quados.com",))

    existing_admin = cursor.fetchone()

    if existing_admin is None:

        cursor.execute("""
            INSERT INTO users
            (name, email, password, phone, address, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "QuadOS Admin",
            "admin@quados.com",
            "admin123",
            "",
            "",
            "admin"
        ))

        connection.commit()

    connection.close()


# ============================================================
# USER ORDERS
# ============================================================

def get_user_orders(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    orders = cursor.fetchall()

    connection.close()

    return orders


# ============================================================
# ALL ORDERS
# ============================================================

def get_all_orders():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT *
        FROM orders
        ORDER BY id DESC
    """)

    orders = cursor.fetchall()

    connection.close()

    return orders


# ============================================================
# DELETE ORDER
# ============================================================

def delete_order(order_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        DELETE FROM orders
        WHERE id = ?
    """, (order_id,))

    connection.commit()
    connection.close()



    # ============================================================
# ADMIN DASHBOARD - TOTAL USERS
# ============================================================

def get_total_users():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM users
        WHERE role = 'user'
    """)

    total = cursor.fetchone()[0]

    connection.close()

    return total


# ============================================================
# ADMIN DASHBOARD - TOTAL ORDERS
# ============================================================

def get_total_orders():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
    """)

    total = cursor.fetchone()[0]

    connection.close()

    return total


# ============================================================
# ADMIN DASHBOARD - TOTAL REVENUE
# ============================================================

def get_total_revenue():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT SUM(final_price)
        FROM orders
    """)

    total = cursor.fetchone()[0]

    connection.close()

    if total is None:
        return 0

    return total


# ============================================================
# ADMIN DASHBOARD - RECENT ORDERS
# ============================================================

def get_recent_orders():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            user_id,
            device_type,
            operating_system,
            final_price,
            order_date
        FROM orders
        ORDER BY id DESC
        LIMIT 10
    """)

    orders = cursor.fetchall()

    connection.close()

    return orders


    # ============================================================
# GET ALL USERS
# ============================================================

def get_all_users():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            phone,
            address,
            role
        FROM users
        ORDER BY id DESC
    """)

    users = cursor.fetchall()

    connection.close()

    return users


    # ============================================================
# USER - ORDER COUNT
# ============================================================

def get_user_order_count(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM orders
        WHERE user_id = ?
    """, (user_id,))

    total = cursor.fetchone()[0]

    connection.close()

    return total


# ============================================================
# CREATE ORDER
# ============================================================

def create_order(
    user_id,
    device_type,
    operating_system,
    configuration,
    accessories,
    subtotal,
    discount,
    final_price,
    order_date
):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO orders
        (
            user_id,
            device_type,
            operating_system,
            configuration,
            accessories,
            subtotal,
            discount,
            final_price,
            order_date
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        device_type,
        operating_system,
        configuration,
        accessories,
        subtotal,
        discount,
        final_price,
        order_date
    ))

    connection.commit()

    connection.close()



    # ============================================================
# ADMIN - ORDERS WITH USER DETAILS
# ============================================================

def get_all_orders_with_users():

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            orders.id,
            users.name,
            users.email,
            orders.device_type,
            orders.operating_system,
            orders.configuration,
            orders.accessories,
            orders.subtotal,
            orders.final_price,
            orders.order_date
        FROM orders
        JOIN users
        ON orders.user_id = users.id
        ORDER BY orders.id DESC
    """)

    orders = cursor.fetchall()

    connection.close()

    return orders