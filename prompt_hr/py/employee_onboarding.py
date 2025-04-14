import frappe

# ! prompt_hr.py.employee_onboarding.get_onboarding_details
# ? FETCH TEMPLATE ACTIVITIES FOR CHILD TABLE
@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
    return frappe.get_all(
        "Employee Boarding Activity",
        fields=["*"],
        filters={"parent": parent, "parenttype": parenttype},
        order_by="idx"
    )


# ? MAIN ON_UPDATE EVENT FUNCTION (No doc.save here!)
@frappe.whitelist()
def on_update(doc, method):
    print("Employee Onboarding Document Updated\n", doc.name)

    auto_fill_first_activity(doc)
    fill_missing_checklist_records(doc)
    rows_to_notify = get_pending_activity_rows(doc)

    notify_users_for_pending_actions(rows_to_notify)

    print("Notified Rows:", [
        {"user": row.user, "desc": row.custom_email_description}
        for row in rows_to_notify
    ])

    return "Emails enqueued successfully"


# ? FILL FIRST ROW USER AND CHECKLIST RECORD IF EMPTY
def auto_fill_first_activity(doc):
    if not doc.activities:
        return 

    first = doc.activities[0]

    if not first.user and not first.custom_checklist_record and doc.job_applicant:
        email = get_applicant_email(doc.job_applicant)
        checklist_record = get_checklist_record("New Joinee Checklist", doc.job_applicant)

        if email:
            first.user = email
            first.custom_checklist_record = checklist_record
            print("First row auto-filled from Job Applicant:", email)

            # ? ONLY SEND IF IS_RAISED IS ALREADY SET
            if first.custom_is_sent == 0:
                send_pending_action_email(first)
                first.custom_is_sent = 1
                print("Email sent immediately for first auto-filled row.")


# ? GET EMAIL FROM JOB APPLICANT
def get_applicant_email(job_applicant):
    return frappe.get_value("Job Applicant", job_applicant, "email_id")


# ? FETCH CHECKLIST RECORD BY DOCTYPE NAME AND JOB APPLICANT
def get_checklist_record(doctype_name, job_applicant):
    try:
        return frappe.get_value(doctype_name, {"job_applicant": job_applicant}, "name")
    except Exception as e:
        frappe.log_error(f"Error fetching checklist from {doctype_name}: {e}", "Checklist Fetch Error")
        return None


# ? FILL MISSING CHECKLIST RECORDS IN ACTIVITIES
def fill_missing_checklist_records(doc):
    for row in doc.activities:
        if not row.custom_checklist_record and row.custom_checklist_name and doc.job_applicant:
            checklist_record = get_checklist_record(row.custom_checklist_name, doc.job_applicant)
            if checklist_record:
                row.custom_checklist_record = checklist_record
                print(f"Filled checklist record for {row.custom_checklist_name}: {checklist_record}")


# ? GET FILTERED ROWS WHERE EMAIL SHOULD BE SENT
def get_pending_activity_rows(doc):
    return [
        row for row in doc.activities
        if row.user and row.custom_is_raised == 1 and row.custom_is_sent == 0
    ]


# ? SEND EMAIL TO USERS FOR PENDING CHECKLIST ACTIONS
def notify_users_for_pending_actions(rows):
    for row in rows:
        send_pending_action_email(row)
        row.custom_is_sent = 1  # Frappe will auto-save after hook


# ? COMPOSE + SEND EMAIL FOR A SINGLE ROW
def send_pending_action_email(row):
    doc_type = row.custom_checklist_name
    doc_name = row.custom_checklist_record
    recipient = row.user

    fallback_subject = "Pending Action Required"
    fallback_message = format_pending_action_message(
        row.custom_email_description, 
        row.custom_checklist_name, 
        row.custom_checklist_record
    )

    frappe.enqueue(
        method=send_notification_email,
        queue="short",
        timeout=300,
        doc_type=doc_type,
        doc_name=doc_name,
        recipient=recipient,
        fallback_subject=fallback_subject,
        fallback_message=fallback_message
    )


# ? FORMAT FALLBACK EMAIL
def format_pending_action_message(description, checklist_name, checklist_record):
    base_url = frappe.utils.get_url()
    checklist_path = checklist_name.lower().replace(" ", "-")
    record_link = f"{base_url}/app/{checklist_path}/{checklist_record}" if checklist_record else "#"

    return f"""
        <p>{description or ""}</p>
        <p><b>Checklist Record:</b> 
            <a href="{record_link}" target="_blank">{checklist_name} ({checklist_record})</a>
        </p>
    """


# ? BACKGROUND TASK: FETCH NOTIFICATION BY DOCTYPE & SEND EMAIL
def send_notification_email(doc_type, doc_name, recipient, fallback_subject, fallback_message):
    try:
        doc = frappe.get_doc(doc_type, doc_name)

        # ? Fetch first Notification matching doc_type
        notification = frappe.get_all("Notification", filters={"document_type": doc_type,"channel": "Email"}, limit=1)
        if not notification:
            raise Exception(f"No Notification template found for {doc_type}")
        
        notification = frappe.get_doc("Notification", notification[0].name)

        context = {
            "doc": doc,
            "user": recipient
        }

        subject = frappe.render_template(notification.subject, context)
        message = frappe.render_template(notification.message, context)

        # ? Append Checklist Link
        checklist_name = getattr(doc, "checklist_name", "") or doc_type
        checklist_path = checklist_name.lower().replace(" ", "-")
        base_url = frappe.utils.get_url()
        record_link = f"{base_url}/app/{checklist_path}/{doc.name}"

        message += f"""
            <hr>
            <p><b>Checklist Record:</b> 
            <a href="{record_link}" target="_blank">{checklist_name} ({doc.name})</a></p>
        """

    except Exception as e:
        frappe.log_error(f"Using fallback message due to: {e}", "Notification Template Error")
        subject = fallback_subject
        message = fallback_message

    frappe.sendmail(
        recipients=[recipient],
        subject=subject,
        message=message
    )

    print(f"✅ Sent '{subject}' to {recipient}")
