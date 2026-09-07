import streamlit as st

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


def render_user_help_queries(current_user):
    """Separate user-side help/query chat."""

    _show_query_flash()

    user_id = current_user[0]
    user_name = current_user[1]
    user_email = current_user[2]

    st.title("Help & Queries")
    st.write("Chat with QuadOS support for help with your account, configuration or orders.")

    st.subheader("Create New Query")

    with st.form("new_help_query_form"):
        subject = st.text_input(
            "Subject",
            placeholder="Example: Problem with my order"
        )

        question = st.text_area(
            "Question",
            placeholder="Describe your question or problem..."
        )

        submitted = st.form_submit_button(
            "Send Query",
            type="primary",
            use_container_width=True
        )

        if submitted:
            if not subject.strip():
                st.error("Please enter a subject.")
            elif not question.strip():
                st.error("Please enter your question.")
            else:
                query_id = create_user_query(
                    user_id,
                    user_name,
                    user_email,
                    subject,
                    question
                )
                _set_query_flash(
                    f"Query #{query_id} sent successfully."
                )
                st.rerun()

    st.divider()
    st.subheader("My Conversations")

    queries = get_user_queries(user_id)

    if not queries:
        st.info("You have not submitted any queries yet.")
        return

    query_options = {
        f"#{row[0]} — {row[1]} — {row[3]}": row[0]
        for row in queries
    }

    selected_label = st.selectbox(
        "Select Query",
        list(query_options.keys()),
        key="user_query_selector"
    )

    selected_query_id = query_options[selected_label]
    details = get_query_details(selected_query_id)

    if not details:
        st.error("Unable to load the selected query.")
        return

    st.markdown(f"### {details[4]}")
    st.caption(
        f"Query #{details[0]} • {details[6]} • Status: {details[7]}"
    )

    st.markdown("#### Conversation")

    messages = get_query_messages(selected_query_id)

    for message in messages:
        sender_type = message[1]
        sender_name = message[3]
        text = message[4]
        sent_at = message[5]

        with st.chat_message("user" if sender_type == "user" else "assistant"):
            st.markdown(
                "**You**" if sender_type == "user" else "**QuadOS Admin**"
            )
            st.write(text)
            st.caption(sent_at)

    if details[7] != "Resolved":
        with st.form(f"user_query_reply_{selected_query_id}"):
            reply = st.text_area(
                "Reply",
                placeholder="Write your message to QuadOS Admin..."
            )

            send_reply = st.form_submit_button(
                "Send Reply",
                type="primary",
                use_container_width=True
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
                        reply
                    )
                    _set_query_flash("Reply sent.")
                    st.rerun()
    else:
        st.info("This query is resolved. Create a new query if you need more help.")


@st.dialog("Confirm Delete Query")
def confirm_delete_query_dialog(query_id):
    st.warning(f"Are you sure you want to permanently delete Query #{query_id}?")
    st.write("The query and its complete conversation will be permanently deleted.")
    st.write("This action cannot be undone.")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Yes, Delete",
            key=f"confirm_delete_query_{query_id}",
            type="primary",
            use_container_width=True
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
            use_container_width=True
        ):
            st.rerun()


def render_admin_queries(current_user):
    """Admin-side query table and two-way communication."""

    _show_query_flash()

    st.title("Queries")
    st.write("Communicate directly with QuadOS users.")

    queries = get_all_queries()

    if not queries:
        st.info("No user queries have been submitted yet.")
        return

    rows = []

    for query in queries:
        rows.append({
            "Query ID": query[0],
            "User ID": query[1] if query[1] is not None else "Guest",
            "Name": query[2],
            "Email": query[3],
            "Subject": query[4],
            "Created": query[6],
            "Status": query[7]
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
        height=350
    )

    st.divider()

    query_options = {
        f"#{query[0]} — {query[2]} — {query[4]} — {query[7]}": query[0]
        for query in queries
    }

    selected_label = st.selectbox(
        "Select Conversation",
        list(query_options.keys()),
        key="admin_query_selector"
    )

    selected_query_id = query_options[selected_label]
    details = get_query_details(selected_query_id)

    if not details:
        st.error("Unable to load this query.")
        return

    st.subheader(f"Query #{details[0]}")
    st.write(f"**User:** {details[2]}")
    st.write(f"**Email:** {details[3]}")
    st.write(f"**Subject:** {details[4]}")
    st.write(f"**Created:** {details[6]}")
    st.write(f"**Status:** {details[7]}")

    st.divider()
    st.subheader("Conversation")

    messages = get_query_messages(selected_query_id)

    for message in messages:
        sender_type = message[1]
        sender_name = message[3]
        text = message[4]
        sent_at = message[5]

        with st.chat_message("user" if sender_type == "user" else "assistant"):
            st.markdown(
                f"**{sender_name}**"
                if sender_type == "user"
                else "**QuadOS Admin**"
            )
            st.write(text)
            st.caption(sent_at)

    if details[7] != "Resolved":
        with st.form(f"admin_query_reply_{selected_query_id}"):
            reply = st.text_area(
                "Reply to User",
                placeholder="Write your response..."
            )

            send_reply = st.form_submit_button(
                "Send Reply",
                type="primary",
                use_container_width=True
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
                        reply
                    )
                    _set_query_flash("Reply sent to user.")
                    st.rerun()

    st.divider()

    st.subheader("Update Status")

    status_options = ["Pending", "In Progress", "Resolved"]

    current_status = details[7]
    status_index = (
        status_options.index(current_status)
        if current_status in status_options
        else 0
    )

    new_status = st.selectbox(
        "Status",
        status_options,
        index=status_index,
        key=f"admin_query_status_{selected_query_id}"
    )

    if st.button(
        "Update Query Status",
        key=f"admin_update_query_{selected_query_id}",
        use_container_width=True
    ):
        if update_query_status(selected_query_id, new_status):
            _set_query_flash("Query status updated.")
            st.rerun()
        else:
            st.error("Unable to update the query status.")

    st.divider()

    st.subheader("Delete Query")
    st.warning("Deleting this query permanently removes the query and its entire conversation.")

    if st.button(
        f"Delete Query #{selected_query_id}",
        key=f"admin_delete_query_{selected_query_id}",
        type="primary",
        use_container_width=True
    ):
        confirm_delete_query_dialog(selected_query_id)
