import frappe
from prompt_hr.py.utils import send_notification_email

# ! prompt_hr.py.employee_onboarding.get_onboarding_details
# ? FETCH TEMPLATE ACTIVITIES FOR CHILD TABLE
@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
    print(f"[DEBUG] Fetching onboarding details for: {parent} ({parenttype})")
    return frappe.get_all(
        "Employee Boarding Activity",
        fields=["*"],
        filters={"parent": parent, "parenttype": parenttype},
        order_by="idx"
    )

# ? AFTER INSERT EVENT
def after_insert(doc, method):
    print(f"[DEBUG] after_insert called for: {doc.name}")
    set_required_documents_in_new_joinee_checklist(doc)

# ? FUNCTION TO SET REQUIRED DOCUMENTS IN THE NEW JOINEE CHECKLIST
def set_required_documents_in_new_joinee_checklist(doc):
    print(f"[DEBUG] Setting required documents for job_applicant: {doc.job_applicant}")
    if doc.job_applicant:
        joining_document_checklist = frappe.get_value(
            "Joining Document Checklist",
            {"company": doc.company},
            "name"
        )
        print(f"[DEBUG] Found checklist: {joining_document_checklist}")

        documents = frappe.get_all(
            "Joining Document",
            filters={
                "parent": joining_document_checklist,
                "document_collection_stage": "Employee Onboarding"
            },
            fields=["required_document", "document_collection_stage"]
        )
        print(f"[DEBUG] Documents to insert: {documents}")

        new_joinee_checklist = frappe.get_doc("New Joinee Checklist", {"job_applicant": doc.job_applicant})
        if not new_joinee_checklist:
            print("[DEBUG] New Joinee Checklist not found.")
            return

        for doc_item in documents:
            print(f"[DEBUG] Appending required document: {doc_item.required_document}")
            new_joinee_checklist.append("required_documents", {
                "required_document": doc_item.required_document,
                "collection_stage": doc_item.document_collection_stage
            })

        new_joinee_checklist.save(ignore_permissions=True)
        frappe.db.commit()
        print("[DEBUG] Required documents saved to New Joinee Checklist.")

# ? MAIN ON_UPDATE EVENT FUNCTION
@frappe.whitelist()
def validate(doc, method):
    print(f"[DEBUG] validate called on: {doc.name}")

    auto_fill_first_activity(doc)
    fill_missing_checklist_records(doc)
    rows_to_notify = get_pending_activity_rows(doc)

    print(f"[DEBUG] Rows eligible for notification: {[r.user for r in rows_to_notify]}")
    frappe.db.commit()

    notify_users_for_pending_actions(rows_to_notify)

    print("[DEBUG] Emails enqueued successfully")
    return "Emails enqueued successfully"

# ? FILL FIRST ROW USER AND CHECKLIST RECORD IF EMPTY
def auto_fill_first_activity(doc):
    if not doc.activities:
        print("[DEBUG] No activities found.")
        return 

    first = doc.activities[0]
    print(f"[DEBUG] First activity: {first}")

    if not first.user and not first.custom_checklist_record and doc.job_applicant:
        email = get_applicant_email(doc.job_applicant)
        checklist_record = get_checklist_record("New Joinee Checklist", doc.job_applicant)

        print(f"[DEBUG] First activity user auto-fill: {email}")
        print(f"[DEBUG] First activity checklist auto-fill: {checklist_record}")

        if email:
            first.user = email
            first.custom_checklist_record = checklist_record

            if first.custom_is_sent == 0:
                send_pending_action_email(first, notification_name="Onboarding Activity Reminder")
                first.custom_is_sent = 1
                print("[DEBUG] Email sent immediately for first row.")

# ? GET EMAIL FROM JOB APPLICANT
def get_applicant_email(job_applicant):
    email = frappe.get_value("Job Applicant", job_applicant, "email_id")
    print(f"[DEBUG] Retrieved applicant email: {email}")
    return email

# ? FETCH CHECKLIST RECORD BY DOCTYPE NAME AND JOB APPLICANT
def get_checklist_record(doctype_name, job_applicant):
    try:
        checklist_record_name = frappe.get_value(doctype_name, {"job_applicant": job_applicant}, "name")
        if not checklist_record_name:
            print(f"[DEBUG] Creating new checklist record for: {job_applicant}")
            checklist_record = frappe.new_doc(doctype_name)
            checklist_record.job_applicant = job_applicant
            checklist_record.insert(ignore_permissions=True)
            checklist_record_name = checklist_record.name
        else:
            print(f"[DEBUG] Found existing checklist record: {checklist_record_name}")
        return checklist_record_name
    except Exception as e:
        frappe.log_error(f"Error fetching checklist from {doctype_name}: {e}", "Checklist Fetch Error")
        print(f"[ERROR] Failed to get checklist record: {e}")
        return None

# ? FILL MISSING CHECKLIST RECORDS IN ACTIVITIES
def fill_missing_checklist_records(doc):
    for row in doc.activities:
        if not row.custom_checklist_record and row.custom_checklist_name and doc.job_applicant:
            print(f"[DEBUG] Filling missing checklist for: {row.custom_checklist_name}")
            checklist_record = get_checklist_record(row.custom_checklist_name, doc.job_applicant)
            if checklist_record:
                row.custom_checklist_record = checklist_record
                print(f"[DEBUG] Updated checklist record: {checklist_record}")

# ? GET FILTERED ROWS WHERE EMAIL SHOULD BE SENT
def get_pending_activity_rows(doc):
    filtered = [
        row for row in doc.activities
        if row.user and row.custom_is_raised == 1 and row.custom_is_sent == 0
    ]
    print(f"[DEBUG] Filtered rows for notification: {len(filtered)}")
    return filtered

# ? SEND EMAIL TO USERS FOR PENDING CHECKLIST ACTIONS
def notify_users_for_pending_actions(rows):
    for row in rows:
        print(f"[DEBUG] Sending email to: {row.user}")
        send_pending_action_email(row, notification_name="Reporting Manger Checklist")
        row.custom_is_sent = 1

# ? COMPOSE + SEND EMAIL FOR A SINGLE ROW
def send_pending_action_email(row, notification_name):
    doc_type = row.custom_checklist_name
    doc_name = row.custom_checklist_record
    recipient = row.user

    print(f"[DEBUG] Composing email for: {recipient}, Doctype: {doc_type}, Docname: {doc_name}")
    send_notification_email(
        recipients=[recipient],
        notification_name=notification_name,
        doctype=doc_type,
        docname=doc_name,
        button_label="View Details",
    )
    print(f"[DEBUG] Email sent to: {recipient}")
