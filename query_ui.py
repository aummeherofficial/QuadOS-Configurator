import streamlit as st

from email_service import send_new_query_admin_email, send_query_reply_email

from query_database import (
    create_user_query,
    get_user_queries,
    get_query_details,
    get_query_messages,
    add_query_message,
    get_all_queries,
    update_query_status,
    delete_query,
)


def _set_query_flash(message):
    """Store a query success message so it survives st.rerun()."""
    st.session_state["query_flash_message"] = message


def _show_query_flash():
    message = st.session_state.pop("query_flash_message", None)
    if message:
        st.success(message)


def _query_status_counts(queries, status_index):
    """Count query statuses using the tuple layout returned by the caller."""
    pending = sum(1 for q in queries if len(q) > status_index and str(q[status_index] or "Pending") == "Pending")
    in_progress = sum(1 for q in queries if len(q) > status_index and str(q[status_index] or "") == "In Progress")
    resolved = sum(1 for q in queries if len(q) > status_index and str(q[status_index] or "") == "Resolved")
    return pending, in_progress, resolved


def _render_query_header(title, subtitle):
    st.markdown(
        f"""
        <div class="quados-query-header">
            <div class="quados-query-kicker">QuadOS Support</div>
            <div class="quados-query-title">{title}</div>
            <div class="quados-query-subtitle">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_user_help_queries(current_user):
    """Render the user-side support area."""

    _show_query_flash()

    user_id = current_user[0]
    user_name = current_user[1]
    user_email = current_user[2]

    st.markdown(
        """
        <style>
        .quados-query-header {
            padding: 22px 26px;
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(25,31,55,.97), rgba(55,42,75,.92));
            border: 1px solid rgba(255,255,255,.10);
            margin-bottom: 20px;
        }
        .quados-query-kicker {
            font-size: 11px;
            letter-spacing: .10em;
            text-transform: uppercase;
            opacity: .58;
        }
        .quados-query-title {
            font-size: 32px;
            font-weight: 800;
            margin-top: 3px;
        }
        .quados-query-subtitle {
            font-size: 14px;
            opacity: .70;
            margin-top: 5px;
        }
        .quados-query-card {
            padding: 18px 20px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,.10);
            background: rgba(255,255,255,.035);
            margin: 10px 0 16px 0;
            box-shadow: 0 10px 28px rgba(0,0,0,.10);
        }
        .quados-query-intro {
            padding: 14px 16px;
            border-radius: 13px;
            background: rgba(167,139,250,.08);
            border: 1px solid rgba(167,139,250,.16);
            font-size: 13px;
            line-height: 1.55;
            margin-bottom: 16px;
        }
        .quados-query-empty {
            padding: 28px 20px;
            text-align: center;
            border-radius: 16px;
            border: 1px dashed rgba(255,255,255,.14);
            background: rgba(255,255,255,.025);
        }
        .quados-query-meta {
            font-size: 12px;
            opacity: .62;
            margin-top: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _render_query_header(
        "Help & Queries",
        "Ask a question about your account, configuration or order and continue the conversation here.",
    )

    # New query first: the main action is immediately visible.
    st.markdown(
        """<div class="quados-query-intro"><b>Need help?</b> Start a conversation below. Use a short subject and describe the problem clearly. QuadOS support can reply here, so you do not need to leave the platform.</div>""",
        unsafe_allow_html=True,
    )
    st.subheader("Start a conversation")
    with st.form("new_help_query_form"):
        subject = st.text_input(
            "Subject",
            placeholder="e.g. Question about my order",
        )
        question = st.text_area(
            "Message",
            placeholder="Describe your question or problem clearly...",
            height=120,
        )
        submitted = st.form_submit_button(
            "Send Query",
            type="primary",
            use_container_width=True,
        )

        if submitted:
            if not subject.strip():
                st.error("Please enter a subject.")
            elif not question.strip():
                st.error("Please enter your message.")
            else:
                query_id = create_user_query(
                    user_id,
                    user_name,
                    user_email,
                    subject.strip(),
                    question.strip(),
                )
                email_ok, _ = send_new_query_admin_email(
                    query_id,
                    user_name,
                    user_email,
                    subject.strip(),
                    question.strip(),
                    __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                )
                _set_query_flash(
                    f"Query #{query_id} sent successfully."
                    + (" Support has been notified." if email_ok else "")
                )
                st.rerun()

    queries = get_user_queries(user_id)

    st.divider()
    st.subheader("My Conversations")

    if not queries:
        st.markdown(
            """<div class="quados-query-empty"><div style="font-size:28px;">💬</div><div style="font-size:17px;font-weight:750;margin-top:6px;">No conversations yet</div><div style="font-size:13px;opacity:.65;margin-top:4px;">Send a query above and your support conversation will appear here.</div></div>""",
            unsafe_allow_html=True,
        )
        return

    pending, in_progress, resolved = _query_status_counts(queries, 3)
    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.metric("Pending", pending)
    with m2:
        st.metric("In Progress", in_progress)
    with m3:
        st.metric("Resolved", resolved)

    query_options = {
        f"#{row[0]} — {row[1]} — {row[3]}": row[0]
        for row in queries
    }

    selected_label = st.selectbox(
        "Conversation",
        list(query_options.keys()),
        key="user_query_selector",
    )
    selected_query_id = query_options[selected_label]
    details = get_query_details(selected_query_id)

    if not details:
        st.error("Unable to load the selected query.")
        return

    status = details[7] or "Pending"
    st.markdown(
        f"""
        <div class="quados-query-card">
            <div style="font-size:20px;font-weight:750;">{details[4]}</div>
            <div class="quados-query-meta">Query #{details[0]} • {details[6]} • Status: <b>{status}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Conversation")
    messages = get_query_messages(selected_query_id)

    for message in messages:
        sender_type = message[1]
        sender_name = message[3]
        text = message[4]
        sent_at = message[5]
        with st.chat_message("user" if sender_type == "user" else "assistant"):
            st.markdown("**You**" if sender_type == "user" else "**QuadOS Admin**")
            st.write(text)
            st.caption(sent_at)

    if status != "Resolved":
        with st.form(f"user_query_reply_{selected_query_id}"):
            reply = st.text_area(
                "Reply",
                placeholder="Write your message to QuadOS support...",
                height=100,
            )
            send_reply = st.form_submit_button(
                "Send Reply",
                type="primary",
                use_container_width=True,
            )
            if send_reply:
                if not reply.strip():
                    st.error("Please enter a message.")
                else:
                    add_query_message(
                        selected_query_id,
                        "user",
                        user_id,
                        user_name,
                        reply.strip(),
                    )
                    _set_query_flash("Reply sent.")
                    st.rerun()
    else:
        st.success("This conversation is resolved. Start a new query if you need more help.")


@st.dialog("Delete Query")
def confirm_delete_query_dialog(query_id):
    st.warning(f"Delete Query #{query_id} permanently?")
    st.write("The query and its complete conversation will be deleted. This cannot be undone.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(
            "Delete",
            key=f"confirm_delete_query_{query_id}",
            type="primary",
            use_container_width=True,
        ):
            if delete_query(query_id):
                _set_query_flash(f"Query #{query_id} deleted successfully.")
                st.rerun()
            else:
                st.error("Unable to delete the selected query.")
    with col2:
        if st.button(
            "Cancel",
            key=f"cancel_delete_query_{query_id}",
            use_container_width=True,
        ):
            st.rerun()


def render_admin_queries(current_user):
    """Render a compact admin support inbox with two-way communication."""

    _show_query_flash()

    st.markdown(
        """
        <style>
        .quados-admin-query-card {
            padding: 18px 20px;
            border-radius: 16px;
            border: 1px solid rgba(255,255,255,.10);
            background: rgba(255,255,255,.035);
            margin: 10px 0 16px 0;
            box-shadow: 0 10px 28px rgba(0,0,0,.10);
        }
        .quados-admin-query-tip {
            padding: 12px 15px;
            border-radius: 12px;
            background: rgba(56,189,248,.07);
            border: 1px solid rgba(56,189,248,.14);
            font-size: 12px;
            line-height: 1.5;
            margin-bottom: 16px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    _render_query_header(
        "Support Queries",
        "Review customer questions, reply to users and keep each conversation up to date.",
    )

    st.markdown(
        """<div class="quados-admin-query-tip"><b>Support workflow:</b> select a conversation, read the full history, reply to the customer, and update the status when the issue is handled.</div>""",
        unsafe_allow_html=True,
    )

    queries = get_all_queries()

    if not queries:
        st.success("No support queries right now. You're all caught up.")
        return

    pending, in_progress, resolved = _query_status_counts(queries, 7)
    m1, m2, m3 = st.columns(3, gap="medium")
    with m1:
        st.metric("Pending", pending)
    with m2:
        st.metric("In Progress", in_progress)
    with m3:
        st.metric("Resolved", resolved)

    query_options = {
        f"#{query[0]} — {query[2]} — {query[4]}": query[0]
        for query in queries
    }

    st.write("")
    selected_label = st.selectbox(
        "Select Conversation",
        list(query_options.keys()),
        key="admin_query_selector",
    )
    selected_query_id = query_options[selected_label]
    details = get_query_details(selected_query_id)

    if not details:
        st.error("Unable to load this query.")
        return

    status = details[7] or "Pending"
    st.markdown(
        f"""
        <div class="quados-admin-query-card">
            <div style="font-size:21px;font-weight:800;">{details[4]}</div>
            <div style="font-size:13px;opacity:.68;margin-top:6px;">
                #{details[0]} • {details[2]} • {details[3]} • {details[6]}
            </div>
            <div style="font-size:13px;margin-top:8px;">Status: <b>{status}</b></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Conversation")
    messages = get_query_messages(selected_query_id)
    for message in messages:
        sender_type = message[1]
        sender_name = message[3]
        text = message[4]
        sent_at = message[5]
        with st.chat_message("user" if sender_type == "user" else "assistant"):
            st.markdown(
                f"**{sender_name}**" if sender_type == "user" else "**QuadOS Admin**"
            )
            st.write(text)
            st.caption(sent_at)

    if status != "Resolved":
        with st.form(f"admin_query_reply_{selected_query_id}"):
            reply = st.text_area(
                "Reply to User",
                placeholder="Write a clear response...",
                height=110,
            )
            send_reply = st.form_submit_button(
                "Send Reply",
                type="primary",
                use_container_width=True,
            )
            if send_reply:
                if not reply.strip():
                    st.error("Please enter a message.")
                else:
                    add_query_message(
                        selected_query_id,
                        "admin",
                        current_user[0],
                        current_user[1],
                        reply.strip(),
                    )
                    email_ok, email_message = send_query_reply_email(
                        details[3], details[2], selected_query_id, details[4], reply.strip()
                    )
                    _set_query_flash(
                        "Reply sent to user."
                        + (" Email notification sent." if email_ok else f" Email notification failed: {email_message}")
                    )
                    st.rerun()

    st.divider()
    st.subheader("Manage Conversation")

    status_options = ["Pending", "In Progress", "Resolved"]
    status_index = status_options.index(status) if status in status_options else 0

    status_col, update_col = st.columns([3, 1], gap="medium")
    with status_col:
        new_status = st.selectbox(
            "Status",
            status_options,
            index=status_index,
            key=f"admin_query_status_{selected_query_id}",
        )
    with update_col:
        st.write("")
        st.write("")
        if st.button(
            "Update Status",
            key=f"admin_update_query_{selected_query_id}",
            use_container_width=True,
        ):
            if update_query_status(selected_query_id, new_status):
                _set_query_flash("Query status updated.")
                st.rerun()
            else:
                st.error("Unable to update the query status.")

    with st.expander("Delete conversation"):
        st.warning("Deleting permanently removes this query and its complete conversation.")
        if st.button(
            f"Delete Query #{selected_query_id}",
            key=f"admin_delete_query_{selected_query_id}",
            type="secondary",
            use_container_width=True,
        ):
            confirm_delete_query_dialog(selected_query_id)
