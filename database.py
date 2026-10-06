import sqlite3
import hashlib
import hmac
import secrets
from datetime import datetime, timezone


# ============================================================
# DATABASE CONFIGURATION
# ============================================================

DATABASE_NAME = "quados.db"


# ============================================================
# DATABASE CONNECTION
# ============================================================

def get_connection():
    connection = sqlite3.connect(DATABASE_NAME)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


# ============================================================
# CREATE TABLES
# ============================================================

def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    # ========================================================
    # USERS TABLE
    # ========================================================

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

    # ========================================================
    # ORDERS TABLE
    # ========================================================

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

            status TEXT DEFAULT 'Placed',

            payment_status TEXT DEFAULT 'Pending',

            razorpay_order_id TEXT,

            razorpay_payment_link_id TEXT,

            razorpay_payment_id TEXT,

            payment_date TEXT,

            cancelled_date TEXT,

            refund_status TEXT DEFAULT 'Not Applicable',

            refund_amount REAL DEFAULT 0,

            refund_date TEXT,

            razorpay_refund_id TEXT,

            refund_type TEXT,

            cancellation_reason TEXT,

            cancellation_charge REAL DEFAULT 0,

            cancellation_requested_date TEXT,

            cancellation_status TEXT DEFAULT 'None',

            FOREIGN KEY (user_id)
            REFERENCES users(id)
        )
    """)

    # ========================================================
    # USER TABLE MIGRATION
    # ========================================================
    #
    # IMPORTANT:
    #
    # CREATE TABLE IF NOT EXISTS does NOT modify an existing
    # database table.
    #
    # Therefore, if an older QuadOS database already exists,
    # we check whether the "role" column exists.
    #
    # If it doesn't exist, we add it.
    # Existing users and orders are NOT deleted.
    # ========================================================

    cursor.execute("""
        PRAGMA table_info(users)
    """)

    user_columns = cursor.fetchall()

    user_column_names = [
        column[1]
        for column in user_columns
    ]

    # --------------------------------------------------------
    # ADD ROLE COLUMN IF MISSING
    # --------------------------------------------------------

    if "role" not in user_column_names:

        cursor.execute("""
            ALTER TABLE users
            ADD COLUMN role TEXT DEFAULT 'user'
        """)

    # ========================================================
    # ORDER PAYMENT COLUMN MIGRATION
    # ========================================================
    cursor.execute("PRAGMA table_info(orders)")
    order_columns = [column[1] for column in cursor.fetchall()]

    if "payment_status" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'Pending'")

    if "razorpay_order_id" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_order_id TEXT")

    if "razorpay_payment_link_id" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_payment_link_id TEXT")

    if "razorpay_payment_id" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_payment_id TEXT")

    if "payment_date" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_date TEXT")

    if "cancelled_date" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN cancelled_date TEXT")

    if "refund_status" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN refund_status TEXT DEFAULT 'Not Applicable'")

    if "refund_amount" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN refund_amount REAL DEFAULT 0")

    if "refund_date" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN refund_date TEXT")

    if "razorpay_refund_id" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_refund_id TEXT")

    if "refund_type" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN refund_type TEXT")

    if "cancellation_reason" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN cancellation_reason TEXT")

    if "cancellation_charge" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN cancellation_charge REAL DEFAULT 0")

    if "cancellation_requested_date" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN cancellation_requested_date TEXT")

    if "cancellation_status" not in order_columns:
        cursor.execute("ALTER TABLE orders ADD COLUMN cancellation_status TEXT DEFAULT 'None'")

    # Preserve the best available historical date for existing records.
    # Future payments/cancellations receive their real event timestamp.
    cursor.execute("""
        UPDATE orders
        SET payment_date = order_date
        WHERE LOWER(COALESCE(payment_status, 'Pending')) = 'paid'
          AND (payment_date IS NULL OR TRIM(payment_date) = '')
    """)
    cursor.execute("""
        UPDATE orders
        SET cancelled_date = order_date
        WHERE LOWER(COALESCE(status, 'Placed')) = 'cancelled'
          AND (cancelled_date IS NULL OR TRIM(cancelled_date) = '')
    """)

    # ========================================================
    # ENSURE EXISTING USERS HAVE USER ROLE
    # ========================================================

    cursor.execute("""
        UPDATE users
        SET role = 'user'
        WHERE role IS NULL
           OR TRIM(role) = ''
    """)

    # ========================================================
    # ENSURE ADMIN ACCOUNT
    # ========================================================

    cursor.execute("""
        SELECT id
        FROM users
        WHERE LOWER(email) = ?
    """, (
        "admin@quados.com",
    ))

    existing_admin = cursor.fetchone()

    if existing_admin is None:

        cursor.execute("""
            INSERT INTO users
            (
                name,
                email,
                password,
                phone,
                address,
                role
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "QuadOS Admin",
            "admin@quados.com",
            _hash_password("admin123"),
            "",
            "",
            "admin"
        ))

    else:

        # Make sure the existing admin account
        # has admin privileges.

        cursor.execute("""
            UPDATE users
            SET role = 'admin'
            WHERE LOWER(email) = ?
        """, ("admin@quados.com",))
        cursor.execute("SELECT id, password FROM users WHERE LOWER(email) = ?", ("admin@quados.com",))
        admin_row = cursor.fetchone()
        if admin_row and _needs_password_migration(admin_row[1]):
            _set_hashed_password(cursor, admin_row[0], admin_row[1])

    # ========================================================
    # ORDER TABLE MIGRATION
    # ========================================================

    cursor.execute("PRAGMA table_info(orders)")

    order_columns = cursor.fetchall()

    order_column_names = [
        column[1]
        for column in order_columns
    ]

    if "status" not in order_column_names:

        cursor.execute("""
            ALTER TABLE orders
            ADD COLUMN status TEXT DEFAULT 'Placed'
        """)

    # Existing orders are treated as placed orders.
    cursor.execute("""
        UPDATE orders
        SET status = 'Placed'
        WHERE status IS NULL
           OR TRIM(status) = ''
    """)

    # ========================================================
    # PAYMENT COLUMN MIGRATION
    # ========================================================

    if "payment_status" not in order_column_names:
        cursor.execute("ALTER TABLE orders ADD COLUMN payment_status TEXT DEFAULT 'Pending'")

    if "razorpay_payment_link_id" not in order_column_names:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_payment_link_id TEXT")

    if "razorpay_payment_id" not in order_column_names:
        cursor.execute("ALTER TABLE orders ADD COLUMN razorpay_payment_id TEXT")

    # ========================================================
    # COMMIT
    # ========================================================

    connection.commit()
    connection.close()


# ============================================================
# PASSWORD HELPERS
# ============================================================

_PASSWORD_PREFIX = "pbkdf2_sha256$"
_PASSWORD_ITERATIONS = 260_000


def _hash_password(password):
    password = str(password)
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), _PASSWORD_ITERATIONS
    ).hex()
    return f"{_PASSWORD_PREFIX}{_PASSWORD_ITERATIONS}${salt}${digest}"


def _verify_password(password, stored_password):
    stored_password = str(stored_password or "")
    if not stored_password.startswith(_PASSWORD_PREFIX):
        return hmac.compare_digest(stored_password, str(password))

    try:
        _, iterations, salt, expected = stored_password.split("$", 3)
        digest = hashlib.pbkdf2_hmac(
            "sha256", str(password).encode("utf-8"), salt.encode("utf-8"), int(iterations)
        ).hex()
        return hmac.compare_digest(digest, expected)
    except (ValueError, TypeError):
        return False


def _needs_password_migration(stored_password):
    return not str(stored_password or "").startswith(_PASSWORD_PREFIX)


def _set_hashed_password(cursor, user_id, password):
    cursor.execute("UPDATE users SET password = ? WHERE id = ?", (_hash_password(password), user_id))


# ============================================================
# CREATE USER
# ============================================================

def create_user(name, email, password, phone, address):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (name, email, password, phone, address, role)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name.strip(), email.strip().lower(), _hash_password(password),
              phone.strip(), address.strip(), "user"))
        connection.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        connection.close()


# ============================================================
# LOGIN USER
# ============================================================

def login_user(identifier, password):
    connection = get_connection()
    cursor = connection.cursor()
    identifier = identifier.strip().lower()
    cursor.execute("""
        SELECT id, name, email, password, phone, address, role
        FROM users WHERE LOWER(email) = ?
    """, (identifier,))
    user = cursor.fetchone()
    if not user or not _verify_password(password, user[3]):
        connection.close()
        return None

    # Seamlessly migrate old plaintext passwords after a successful login.
    if _needs_password_migration(user[3]):
        _set_hashed_password(cursor, user[0], password)
        connection.commit()
        cursor.execute("""
            SELECT id, name, email, password, phone, address, role
            FROM users WHERE id = ?
        """, (user[0],))
        user = cursor.fetchone()
    connection.close()
    return user


# ============================================================
# GET USER BY EMAIL
# ============================================================

def get_user_by_email(email):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            name,
            email,
            password,
            phone,
            address,
            role
        FROM users
        WHERE LOWER(email) = ?
    """, (
        email.strip().lower(),
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
        WHERE LOWER(email) = ?
    """, (
        "admin@quados.com",
    ))

    existing_admin = cursor.fetchone()

    if existing_admin is None:

        cursor.execute("""
            INSERT INTO users
            (
                name,
                email,
                password,
                phone,
                address,
                role
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            "QuadOS Admin",
            "admin@quados.com",
            _hash_password("admin123"),
            "",
            "",
            "admin"
        ))

    else:

        cursor.execute("""
            UPDATE users
            SET role = 'admin'
            WHERE LOWER(email) = ?
        """, ("admin@quados.com",))
        cursor.execute("SELECT id, password FROM users WHERE LOWER(email) = ?", ("admin@quados.com",))
        admin_row = cursor.fetchone()
        if admin_row and _needs_password_migration(admin_row[1]):
            _set_hashed_password(cursor, admin_row[0], admin_row[1])

    connection.commit()
    connection.close()


# ============================================================
# USER ORDERS
# ============================================================

def get_user_orders(user_id):

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            user_id,
            device_type,
            operating_system,
            configuration,
            accessories,
            subtotal,
            discount,
            final_price,
            order_date,
            status,
            payment_status,
            payment_date,
            cancelled_date,
            refund_status,
            refund_amount,
            refund_date,
            razorpay_refund_id,
            refund_type,
            cancellation_reason,
            cancellation_charge,
            cancellation_requested_date,
            cancellation_status
        FROM orders
        WHERE user_id = ?
        ORDER BY id DESC
    """, (
        user_id,
    ))

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
        SELECT
            id,
            user_id,
            device_type,
            operating_system,
            configuration,
            accessories,
            subtotal,
            discount,
            final_price,
            order_date,
            status
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
    """, (
        order_id,
    ))

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
        WHERE LOWER(COALESCE(payment_status, 'Pending')) = 'paid'
        AND COALESCE(status, 'Placed') != 'Cancelled'
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
        SELECT COALESCE(SUM(final_price), 0)
        FROM orders
        WHERE LOWER(COALESCE(payment_status, 'Pending')) = 'paid'
        AND COALESCE(status, 'Placed') != 'Cancelled'
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
    """Return users for the admin table without exposing passwords."""

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
# DELETE USER
# ============================================================

def delete_user(user_id):
    """Permanently delete a normal user and their related orders."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()

    if not user or (user[0] or "user").lower() != "user":
        connection.close()
        return False

    # Orders reference users, so remove the user's orders first.
    cursor.execute("DELETE FROM orders WHERE user_id = ?", (user_id,))
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

    connection.commit()
    deleted = cursor.rowcount > 0
    connection.close()

    return deleted


# ============================================================
# PASSWORD RESET - VERIFY USER
# ============================================================

def verify_password_reset_user(email, phone):
    """Verify a user for the Forgot Password flow using email + phone."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, name, email
        FROM users
        WHERE LOWER(email) = ?
        AND phone = ?
        AND role = 'user'
    """, (
        email.strip().lower(),
        phone.strip()
    ))

    user = cursor.fetchone()

    connection.close()

    return user


# ============================================================
# PASSWORD RESET - UPDATE PASSWORD
# ============================================================

def reset_user_password(user_id, new_password):
    """Set a new password for a verified user."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET password = ?
        WHERE id = ?
        AND role = 'user'
    """, (_hash_password(new_password), user_id))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed


# ============================================================
# ADMIN - RESET USER PASSWORD
# ============================================================

def admin_reset_user_password(user_id, new_password):
    """Allow an admin to set a new password for a normal user."""

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE users
        SET password = ?
        WHERE id = ?
        AND role = 'user'
    """, (_hash_password(new_password), user_id))

    changed = cursor.rowcount > 0

    connection.commit()
    connection.close()

    return changed


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
    """, (
        user_id,
    ))

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
    order_date,
    status="Placed"
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
            order_date,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        device_type,
        operating_system,
        configuration,
        accessories,
        subtotal,
        discount,
        final_price,
        order_date,
        status
    ))

    connection.commit()
    order_id = cursor.lastrowid

    connection.close()

    return order_id


# ============================================================
# PAYMENT HELPERS
# ============================================================

def update_order_payment(
    order_id,
    payment_status,
    razorpay_order_id=None,
    razorpay_payment_link_id=None,
    razorpay_payment_id=None
):
    connection = get_connection()
    cursor = connection.cursor()

    normalized = str(payment_status or "Pending").strip().title()
    if normalized not in {"Pending", "Paid", "Failed"}:
        return False

    connection_check = get_connection()
    check_cursor = connection_check.cursor()
    check_cursor.execute(
        "SELECT status, payment_status FROM orders WHERE id = ?",
        (order_id,)
    )
    existing = check_cursor.fetchone()
    connection_check.close()

    if not existing:
        return False

    current_status, current_payment = existing
    current_payment = str(current_payment or "Pending").lower()
    if current_payment == "paid" and normalized.lower() != "paid":
        return False
    if str(current_status or "Placed").lower() == "cancelled" and normalized == "Paid":
        return False

    payment_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds") if normalized == "Paid" else None

    cursor.execute("""
        UPDATE orders
        SET payment_status = ?,
            payment_date = CASE
                WHEN ? IS NOT NULL THEN COALESCE(payment_date, ?)
                ELSE payment_date
            END,
            razorpay_order_id = COALESCE(?, razorpay_order_id),
            razorpay_payment_link_id = COALESCE(?, razorpay_payment_link_id),
            razorpay_payment_id = COALESCE(?, razorpay_payment_id)
        WHERE id = ?
    """, (
        normalized,
        payment_timestamp,
        payment_timestamp,
        razorpay_order_id,
        razorpay_payment_link_id,
        razorpay_payment_id,
        order_id
    ))

    connection.commit()
    updated = cursor.rowcount > 0
    connection.close()
    return updated


def mark_order_paid(order_id, razorpay_payment_id=None, razorpay_order_id=None):
    connection = get_connection()
    cursor = connection.cursor()

    payment_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")

    cursor.execute("""
        UPDATE orders
        SET payment_status = 'Paid',
            status = CASE
                WHEN COALESCE(status, 'Placed') = 'Payment Pending' THEN 'Placed'
                ELSE status
            END,
            payment_date = COALESCE(payment_date, ?),
            razorpay_order_id = COALESCE(?, razorpay_order_id),
            razorpay_payment_id = COALESCE(?, razorpay_payment_id)
        WHERE id = ?
          AND LOWER(COALESCE(status, 'Placed')) != 'cancelled'
          AND LOWER(COALESCE(payment_status, 'Pending')) != 'paid'
    """, (
        payment_timestamp,
        razorpay_order_id,
        razorpay_payment_id,
        order_id
    ))

    connection.commit()
    updated = cursor.rowcount > 0
    connection.close()
    return updated


def get_order_by_id(order_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, user_id, device_type, operating_system, configuration,
               accessories, subtotal, discount, final_price, order_date, status,
               payment_status, razorpay_order_id, razorpay_payment_link_id,
               razorpay_payment_id, payment_date, cancelled_date,
               refund_status, refund_amount, refund_date, razorpay_refund_id,
               refund_type, cancellation_reason, cancellation_charge,
               cancellation_requested_date, cancellation_status
        FROM orders
        WHERE id = ?
    """, (order_id,))

    row = cursor.fetchone()
    connection.close()
    return row


def get_order_by_razorpay_order_id(razorpay_order_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, user_id, final_price, status, payment_status,
               razorpay_order_id, razorpay_payment_id
        FROM orders
        WHERE razorpay_order_id = ?
    """, (str(razorpay_order_id),))

    row = cursor.fetchone()
    connection.close()
    return row


def get_order_payment(order_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, user_id, final_price, status, payment_status,
               razorpay_order_id, razorpay_payment_link_id, razorpay_payment_id
        FROM orders
        WHERE id = ?
    """, (order_id,))

    row = cursor.fetchone()
    connection.close()
    return row


def get_order_by_payment_link(razorpay_payment_link_id):
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, user_id, final_price, status, payment_status,
               razorpay_order_id, razorpay_payment_link_id, razorpay_payment_id
        FROM orders
        WHERE razorpay_payment_link_id = ?
    """, (razorpay_payment_link_id,))

    row = cursor.fetchone()
    connection.close()
    return row


# ============================================================
# CANCEL USER ORDER
# ============================================================

def update_order_status(order_id, status):
    """Safely update an order status while respecting payment/state rules."""
    allowed = {"Placed", "Confirmed", "In Progress", "Completed", "Payment Pending", "Cancelled"}
    if status not in allowed:
        return False

    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT status, payment_status FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row:
            return False
        current_status, payment_status = row
        current_status = current_status or "Placed"
        payment_status = (payment_status or "Pending").lower()

        if current_status == "Cancelled":
            return False
        if status == "Payment Pending" and payment_status == "paid":
            return False
        if status in {"Confirmed", "In Progress", "Completed"} and payment_status != "paid":
            return False
        if status == "Cancelled" and payment_status == "paid":
            # No refund mechanism exists, so never create a paid+cancelled state.
            return False
        if current_status == "Completed" and status != "Completed":
            return False

        cancelled_timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds") if status == "Cancelled" else None
        cursor.execute("""
            UPDATE orders
            SET status = ?,
                cancelled_date = CASE
                    WHEN ? IS NOT NULL THEN COALESCE(cancelled_date, ?)
                    ELSE cancelled_date
                END
            WHERE id = ?
        """, (status, cancelled_timestamp, cancelled_timestamp, order_id))
        changed = cursor.rowcount > 0
        connection.commit()
        return changed
    except sqlite3.Error:
        connection.rollback()
        return False
    finally:
        connection.close()


def request_order_cancellation(user_id, order_id, cancellation_reason="Customer requested cancellation"):
    """Create a customer cancellation request. The customer never approves or chooses a refund."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cursor.execute("""
            SELECT status, payment_status, cancellation_status
            FROM orders WHERE id = ? AND user_id = ?
        """, (order_id, user_id))
        row = cursor.fetchone()
        if not row:
            return False, "Order not found or it does not belong to your account."
        status, payment_status, cancellation_status = row
        if str(status or "Placed").lower() == "cancelled":
            return False, "This order is already cancelled."
        if str(cancellation_status or "None").lower() == "requested":
            return False, "Cancellation has already been requested for this order."
        if str(status or "Placed").lower() == "completed":
            return False, "Completed orders cannot be cancelled."

        cursor.execute("""
            UPDATE orders
            SET cancellation_status = 'Requested',
                cancellation_reason = ?,
                cancellation_requested_date = ?,
                refund_status = CASE WHEN LOWER(COALESCE(payment_status, 'Pending')) = 'paid' THEN 'Awaiting Admin Approval' ELSE 'Not Applicable' END
            WHERE id = ? AND user_id = ?
        """, (cancellation_reason, timestamp, order_id, user_id))
        changed = cursor.rowcount > 0
        connection.commit()
        return changed, ("Cancellation request submitted. An administrator will review it and decide the refund amount." if changed else "Could not submit the cancellation request.")
    except sqlite3.Error:
        connection.rollback()
        return False, "Could not submit the cancellation request."
    finally:
        connection.close()


def cancel_order(user_id, order_id, cancellation_reason="Customer requested cancellation"):
    """Backward-compatible alias: customers now submit a cancellation request."""
    ok, _ = request_order_cancellation(user_id, order_id, cancellation_reason)
    return ok


def reject_cancellation(order_id):
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            UPDATE orders
            SET cancellation_status = 'Rejected',
                refund_status = CASE WHEN LOWER(COALESCE(payment_status, 'Pending')) = 'paid' THEN 'Not Applicable' ELSE refund_status END
            WHERE id = ? AND LOWER(COALESCE(cancellation_status, 'None')) = 'requested'
        """, (order_id,))
        changed = cursor.rowcount > 0
        connection.commit()
        return changed
    except sqlite3.Error:
        connection.rollback()
        return False
    finally:
        connection.close()


def approve_unpaid_cancellation(order_id):
    """Admin-only database operation for cancelling an unpaid requested order."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cursor.execute("""
            UPDATE orders
            SET status = 'Cancelled',
                cancelled_date = COALESCE(cancelled_date, ?),
                cancellation_status = 'Approved',
                refund_status = 'Not Applicable',
                refund_amount = 0,
                refund_type = 'None',
                cancellation_charge = 0
            WHERE id = ?
              AND LOWER(COALESCE(status, 'Placed')) != 'Cancelled'
              AND LOWER(COALESCE(payment_status, 'Pending')) != 'paid'
              AND LOWER(COALESCE(cancellation_status, 'None')) = 'requested'
        """, (timestamp, order_id))
        changed = cursor.rowcount > 0
        connection.commit()
        return changed
    except sqlite3.Error:
        connection.rollback(); return False
    finally:
        connection.close()


def start_order_refund(user_id, order_id, refund_amount, refund_type, cancellation_reason, cancellation_charge):
    """Record that a paid-order refund has been requested before calling Razorpay."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cursor.execute("""
            SELECT user_id, final_price, status, payment_status, refund_status
            FROM orders WHERE id = ?
        """, (order_id,))
        row = cursor.fetchone()
        if not row or row[0] != user_id:
            return False, "Order does not belong to the signed-in user."
        final_price = float(row[1] or 0)
        if str(row[2] or "Placed").lower() == "cancelled":
            return False, "This order is already cancelled."
        if str(row[3] or "Pending").lower() != "paid":
            return False, "Only paid orders can be refunded."
        if str(row[4] or "Not Applicable").lower() in {"pending", "processed"}:
            return False, "A refund has already been requested for this order."
        amount = round(float(refund_amount), 2)
        if amount <= 0 or amount > final_price:
            return False, "Refund amount must be greater than zero and cannot exceed the paid amount."
        cursor.execute("""
            UPDATE orders
            SET refund_status = 'Pending', refund_amount = ?, refund_type = ?,
                cancellation_reason = ?, cancellation_charge = ?,
                cancellation_requested_date = ?
            WHERE id = ? AND user_id = ?
        """, (amount, refund_type, cancellation_reason, round(float(cancellation_charge),2), timestamp, order_id, user_id))
        connection.commit()
        return cursor.rowcount > 0, "Refund request recorded."
    except (sqlite3.Error, ValueError, TypeError):
        connection.rollback()
        return False, "Could not record the refund request."
    finally:
        connection.close()


def complete_order_refund(user_id, order_id, refund_amount, refund_status, razorpay_refund_id=None):
    """Finalize cancellation/refund after Razorpay responds."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
        cursor.execute("SELECT user_id, final_price, refund_amount FROM orders WHERE id = ?", (order_id,))
        row = cursor.fetchone()
        if not row or row[0] != user_id:
            return False
        final_price = float(row[1] or 0)
        amount = round(float(refund_amount), 2)
        if amount <= 0 or amount > final_price:
            return False
        normalized = str(refund_status or "Pending").strip().title()
        if normalized not in {"Pending", "Processed", "Failed"}:
            return False
        new_order_status = "Cancelled" if normalized in {"Pending", "Processed"} else "Placed"
        refund_date = timestamp if normalized == "Processed" else None
        cursor.execute("""
            UPDATE orders
            SET status = ?,
                cancelled_date = CASE WHEN ? = 'Cancelled' THEN COALESCE(cancelled_date, ?) ELSE cancelled_date END,
                refund_status = ?,
                refund_amount = ?,
                refund_date = CASE WHEN ? IS NOT NULL THEN COALESCE(refund_date, ?) ELSE refund_date END,
                razorpay_refund_id = COALESCE(?, razorpay_refund_id),
                cancellation_status = 'Approved'
            WHERE id = ? AND user_id = ?
        """, (new_order_status, new_order_status, timestamp, normalized, amount, refund_date, refund_date, razorpay_refund_id, order_id, user_id))
        connection.commit()
        return cursor.rowcount > 0
    except (sqlite3.Error, ValueError, TypeError):
        connection.rollback()
        return False
    finally:
        connection.close()


def fail_order_refund(user_id, order_id):
    connection = get_connection(); cursor = connection.cursor()
    try:
        cursor.execute("UPDATE orders SET refund_status = 'Failed' WHERE id = ? AND user_id = ?", (order_id, user_id))
        connection.commit(); return cursor.rowcount > 0
    except sqlite3.Error:
        connection.rollback(); return False
    finally:
        connection.close()


def get_pending_refund_orders(user_id=None):
    """Return paid QuadOS orders whose refund still needs Razorpay reconciliation."""
    connection = get_connection()
    cursor = connection.cursor()
    try:
        query = """
            SELECT id, user_id, razorpay_payment_id, refund_amount,
                   refund_status, razorpay_refund_id
            FROM orders
            WHERE LOWER(COALESCE(payment_status, 'Pending')) = 'paid'
              AND LOWER(COALESCE(refund_status, 'Not Applicable')) IN ('pending', 'awaiting admin approval')
              AND LOWER(COALESCE(cancellation_status, 'None')) = 'approved'
        """
        params = []
        if user_id is not None:
            query += " AND user_id = ?"
            params.append(user_id)
        query += " ORDER BY id DESC"
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        connection.close()


def sync_order_refund_status(user_id, order_id, refund_status, amount_refunded=0.0):
    """Synchronize a QuadOS refund from the state reported by Razorpay.

    Razorpay reports payment refund state using refund_status/amount_refunded.
    QuadOS marks the refund Processed only when Razorpay confirms that the
    requested refund amount has actually been refunded.
    """
    connection = get_connection()
    cursor = connection.cursor()
    try:
        cursor.execute("""
            SELECT user_id, refund_amount, refund_status
            FROM orders
            WHERE id = ?
        """, (order_id,))
        row = cursor.fetchone()
        if not row or row[0] != user_id:
            return False

        requested_amount = round(float(row[1] or 0), 2)
        refunded_amount = round(float(amount_refunded or 0), 2)
        normalized = str(refund_status or '').strip().lower()

        # A partial refund is also considered complete when Razorpay has
        # refunded the exact amount QuadOS promised the customer.
        is_processed = normalized == 'full' or (
            normalized == 'partial' and refunded_amount + 0.01 >= requested_amount and requested_amount > 0
        )

        if is_processed:
            timestamp = datetime.now(timezone.utc).isoformat(timespec='seconds')
            cursor.execute("""
                UPDATE orders
                SET status = 'Cancelled',
                    cancelled_date = COALESCE(cancelled_date, ?),
                    refund_status = 'Processed',
                    refund_date = COALESCE(refund_date, ?),
                    refund_amount = CASE
                        WHEN ? > 0 THEN ?
                        ELSE refund_amount
                    END,
                    cancellation_status = 'Approved'
                WHERE id = ? AND user_id = ?
            """, (
                timestamp, timestamp, refunded_amount, refunded_amount, order_id, user_id
            ))
        else:
            # Do not mark a Razorpay refund as Failed merely because it is
            # still pending. Razorpay may take time to finish a normal refund.
            cursor.execute("""
                UPDATE orders
                SET status = 'Cancelled',
                    cancelled_date = COALESCE(cancelled_date, ?),
                    refund_status = 'Pending',
                    cancellation_status = 'Approved'
                WHERE id = ? AND user_id = ?
            """, (datetime.now(timezone.utc).isoformat(timespec='seconds'), order_id, user_id))

        connection.commit()
        return cursor.rowcount > 0
    except (sqlite3.Error, ValueError, TypeError):
        connection.rollback()
        return False
    finally:
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
            orders.order_date,
            orders.status,
            orders.payment_status,
            orders.refund_status,
            orders.refund_amount,
            orders.cancellation_charge,
            orders.cancellation_status
        FROM orders
        JOIN users
        ON orders.user_id = users.id
        ORDER BY orders.id DESC
    """)

    orders = cursor.fetchall()

    connection.close()

    return orders


# ============================================================
# INITIALIZE DATABASE
# ============================================================

create_tables()
