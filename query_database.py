import sqlite3
from datetime import datetime

QUERY_DATABASE_NAME = "quados_queries.db"


def get_query_connection():
    connection = sqlite3.connect(QUERY_DATABASE_NAME)
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def create_query_table():
    connection = get_query_connection()
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_queries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            subject TEXT NOT NULL,
            question TEXT NOT NULL,
            submitted_at TEXT NOT NULL,
            status TEXT DEFAULT 'Pending'
        )
    """)

    # Separate message table for two-way user/admin communication.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query_id INTEGER NOT NULL,
            sender_type TEXT NOT NULL,
            sender_id INTEGER,
            sender_name TEXT NOT NULL,
            message TEXT NOT NULL,
            sent_at TEXT NOT NULL,
            FOREIGN KEY (query_id) REFERENCES user_queries(id) ON DELETE CASCADE
        )
    """)

    connection.commit()

    # Migrate old queries: the original question becomes the first chat message.
    cursor.execute("""
        SELECT q.id, q.user_id, q.name, q.question, q.submitted_at
        FROM user_queries q
        LEFT JOIN query_messages m
            ON m.query_id = q.id
        WHERE m.id IS NULL
    """)
    old_queries = cursor.fetchall()

    for query_id, user_id, name, question, submitted_at in old_queries:
        cursor.execute("""
            INSERT INTO query_messages
            (query_id, sender_type, sender_id, sender_name, message, sent_at)
            VALUES (?, 'user', ?, ?, ?, ?)
        """, (
            query_id,
            user_id,
            name,
            question,
            submitted_at
        ))

    connection.commit()
    connection.close()


def create_user_query(user_id, name, email, subject, question, submitted_at=None):
    """Create a query and its first user message."""
    if submitted_at is None:
        submitted_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    connection = get_query_connection()
    cursor = connection.cursor()

    cursor.execute("""
        INSERT INTO user_queries
        (user_id, name, email, subject, question, submitted_at, status)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending')
    """, (
        user_id,
        name.strip(),
        email.strip(),
        subject.strip(),
        question.strip(),
        submitted_at
    ))

    query_id = cursor.lastrowid

    cursor.execute("""
        INSERT INTO query_messages
        (query_id, sender_type, sender_id, sender_name, message, sent_at)
        VALUES (?, 'user', ?, ?, ?, ?)
    """, (
        query_id,
        user_id,
        name.strip(),
        question.strip(),
        submitted_at
    ))

    connection.commit()
    connection.close()
    return query_id


def get_all_queries():
    connection = get_query_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id,
            user_id,
            name,
            email,
            subject,
            question,
            submitted_at,
            status
        FROM user_queries
        ORDER BY id DESC
    """)

    queries = cursor.fetchall()
    connection.close()
    return queries


def get_user_queries(user_id):
    connection = get_query_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT id, subject, submitted_at, status
        FROM user_queries
        WHERE user_id = ?
        ORDER BY id DESC
    """, (user_id,))

    rows = cursor.fetchall()
    connection.close()
    return rows


def get_query_details(query_id):
    connection = get_query_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id, user_id, name, email, subject,
            question, submitted_at, status
        FROM user_queries
        WHERE id = ?
    """, (query_id,))

    row = cursor.fetchone()
    connection.close()
    return row


def get_query_messages(query_id):
    connection = get_query_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT
            id, sender_type, sender_id, sender_name,
            message, sent_at
        FROM query_messages
        WHERE query_id = ?
        ORDER BY id ASC
    """, (query_id,))

    rows = cursor.fetchall()
    connection.close()
    return rows


def add_query_message(query_id, sender_type, sender_id, sender_name, message):
    message = message.strip()

    if not message:
        return False

    if sender_type not in ("user", "admin"):
        return False

    connection = get_query_connection()
    cursor = connection.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
        INSERT INTO query_messages
        (query_id, sender_type, sender_id, sender_name, message, sent_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        query_id,
        sender_type,
        sender_id,
        sender_name.strip(),
        message,
        now
    ))

    # A user reply requires admin attention.
    # An admin reply moves the query into active handling.
    new_status = "Pending" if sender_type == "user" else "In Progress"

    cursor.execute("""
        UPDATE user_queries
        SET status = ?
        WHERE id = ?
    """, (new_status, query_id))

    changed = cursor.rowcount > 0
    connection.commit()
    connection.close()

    return changed


def update_query_status(query_id, status):
    allowed = {"Pending", "In Progress", "Resolved"}

    if status not in allowed:
        return False

    connection = get_query_connection()
    cursor = connection.cursor()

    cursor.execute("""
        UPDATE user_queries
        SET status = ?
        WHERE id = ?
    """, (status, query_id))

    connection.commit()
    changed = cursor.rowcount > 0
    connection.close()

    return changed


def get_query_count():
    connection = get_query_connection()
    cursor = connection.cursor()

    cursor.execute("""
        SELECT COUNT(*)
        FROM user_queries
        WHERE status = 'Pending'
    """)

    count = cursor.fetchone()[0]
    connection.close()
    return count


create_query_table()