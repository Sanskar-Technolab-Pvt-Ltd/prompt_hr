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

            # Optional: only send if is_raised is already set
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
    subject = "Pending Action Required"
    custom_checklist_name = row.custom_checklist_name
    checklist_path = custom_checklist_name.lower().replace(" ", "-")
    base_url = frappe.utils.get_url()
    record_link = f"{base_url}/app/{checklist_path}/{row.custom_checklist_record}" if row.custom_checklist_record else "#"

    message = format_pending_action_message(row.custom_email_description, row.custom_checklist_name, row.custom_checklist_record, record_link)

    send_email(row.user, subject, message)


# ? FORMAT EMAIL BODY
def format_pending_action_message(description, checklist_name, checklist_record, link):
    return f"""
        <p>{description or ""}</p>
        <p><b>Checklist Record:</b> 
            <a href="{link}" target="_blank">{checklist_name} ({checklist_record})</a>
        </p>
    """


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
