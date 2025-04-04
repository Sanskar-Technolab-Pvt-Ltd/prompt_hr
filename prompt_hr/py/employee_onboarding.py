import frappe

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
    print("🔄 Employee Onboarding Document Updated\n", doc.name)

    # ? CHECK & PREFILL FIRST ACTIVITY IF NEEDED
    auto_fill_first_activity(doc)

    # ? FILTER ACTIVITIES WHERE EMAIL IS REQUIRED
    rows_to_notify = get_pending_activity_rows(doc)

    for row in rows_to_notify:
        send_pending_action_email(row)

        # ✅ MARK AS SENT (Frappe will auto-save after hook)
        row.custom_is_sent = 1

    print("✅ Notified Rows:", [
        {"user": row.user, "desc": row.custom_email_description}
        for row in rows_to_notify
    ])

    return "Emails enqueued successfully"


# ? FILL FIRST ROW USER + CHECKLIST RECORD IF EMPTY
def auto_fill_first_activity(doc):
    if not doc.activities:
        return

    first = doc.activities[0]
    if not first.user and not first.custom_checklist_record and doc.job_applicant:
        email = frappe.get_value("Job Applicant", doc.job_applicant, "email_id")
        if email:
            first.user = email
            first.custom_checklist_record = email  # ? Or use your own logic to assign this
            print("📝 First row auto-filled from Job Applicant:", email)


# ? GET FILTERED ROWS WHERE EMAIL SHOULD BE SENT
def get_pending_activity_rows(doc):
    return [
        row for row in doc.activities
        if row.user and row.custom_is_raised == 1 and row.custom_is_sent == 0
    ]


# ? COMPOSE + SEND EMAIL FOR A SINGLE ROW
def send_pending_action_email(row):
    subject = "Pending Action Required"
    checklist_path = frappe.scrub(row.custom_checklist_name)
    base_url = frappe.utils.get_url()
    record_link = f"{base_url}/app/{checklist_path}/{row.custom_checklist_record}" if row.custom_checklist_record else "#"

    # ? FORMAT EMAIL MESSAGE
    message = f"""
        <p>{row.custom_email_description}</p>
        <p><b>Checklist Record:</b> 
            <a href="{record_link}" target="_blank">{row.custom_checklist_name} ({row.custom_checklist_record})</a>
        </p>
    """

    # ? ENQUEUE EMAIL
    send_email(row.user, subject, message)


# ? ENQUEUE EMAIL BACKGROUND JOB
@frappe.whitelist()
def send_email(recipients, subject, message, attachments=None):
    frappe.enqueue(
        method=send_email_task,
        queue="short",
        timeout=300,
        recipients=recipients,
        subject=subject,
        message=message,
        attachments=attachments
    )


# ? ACTUAL BACKGROUND EMAIL TASK
def send_email_task(recipients, subject, message, attachments=None):
    if isinstance(recipients, str):
        recipients = [recipients]

    email_args = {
        "recipients": recipients,
        "subject": subject,
        "message": message
    }

    if attachments:
        email_args["attachments"] = frappe.parse_json(attachments)

    frappe.sendmail(**email_args)
