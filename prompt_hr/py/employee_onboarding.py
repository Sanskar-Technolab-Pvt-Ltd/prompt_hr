import frappe
from prompt_hr.py.utils import send_notification_email

# ! prompt_hr.py.employee_onboarding.get_onboarding_details
# ? FETCH TEMPLATE ACTIVITIES FOR CHILD TABLE
@frappe.whitelist()
def get_onboarding_details(parent, parenttype):
    try:
        return frappe.get_all(
            "Employee Boarding Activity",
            fields=["*"],
            filters={"parent": parent, "parenttype": parenttype},
            order_by="idx"
        )
    except Exception as e:
        frappe.log_error(f"Error in get_onboarding_details: {e}", "Onboarding Details Fetch Error")
        raise

# ? AFTER INSERT EVENT
def after_insert(doc, method):
    try:
        set_required_documents_in_new_joinee_checklist(doc)
    except Exception as e:
        frappe.log_error(f"Error in after_insert: {e}", "After Insert Error")

# ? FUNCTION TO SET REQUIRED DOCUMENTS IN THE NEW JOINEE CHECKLIST
def set_required_documents_in_new_joinee_checklist(doc):
    try:
        if doc.job_applicant:
            joining_document_checklist = frappe.get_value(
                "Joining Document Checklist",
                {"company": doc.company},
                "name"
            )

            documents = frappe.get_all(
                "Joining Document",
                filters={
                    "parent": joining_document_checklist,
                    "document_collection_stage": "Employee Onboarding"
                },
                fields=["required_document", "document_collection_stage"]
            )

            new_joinee_checklist = frappe.get_doc("New Joinee Checklist", {"job_applicant": doc.job_applicant})
            if not new_joinee_checklist:
                return

            for doc_item in documents:
                new_joinee_checklist.append("required_documents", {
                    "required_document": doc_item.required_document,
                    "collection_stage": doc_item.document_collection_stage
                })

            new_joinee_checklist.save(ignore_permissions=True)
            frappe.db.commit()
    except Exception as e:
        frappe.log_error(f"Error in set_required_documents_in_new_joinee_checklist: {e}", "Checklist Setup Error")

# ? MAIN ON_UPDATE EVENT FUNCTION
@frappe.whitelist()
def validate(doc, method):
    try:
        auto_fill_first_activity(doc)
        fill_missing_checklist_records(doc)
        rows_to_notify = get_pending_activity_rows(doc)
        frappe.db.commit()
        notify_users_for_pending_actions(rows_to_notify)
        return "Emails enqueued successfully"
    except Exception as e:
        frappe.log_error(f"Error in validate: {e}", "Validation Error")
        return "Failed to enqueue emails"

# ? FILL FIRST ROW USER AND CHECKLIST RECORD IF EMPTY
def auto_fill_first_activity(doc):
    try:
        if not doc.activities:
            return

        first = doc.activities[0]

        if not first.user and not first.custom_checklist_record and doc.job_applicant:
            email = get_applicant_email(doc.job_applicant)
            checklist_record = get_checklist_record("New Joinee Checklist", doc.job_applicant)

            if email:
                first.user = email
                first.custom_checklist_record = checklist_record

                if first.custom_is_sent == 0:
                    send_pending_action_email(first, notification_name="Onboarding Activity Reminder")
                    first.custom_is_sent = 1
    except Exception as e:
        frappe.log_error(f"Error in auto_fill_first_activity: {e}", "Auto Fill Error")

# ? GET EMAIL FROM JOB APPLICANT
def get_applicant_email(job_applicant):
    try:
        return frappe.get_value("Job Applicant", job_applicant, "email_id")
    except Exception as e:
        frappe.log_error(f"Error in get_applicant_email: {e}", "Email Fetch Error")
        return None

# ? FETCH CHECKLIST RECORD BY DOCTYPE NAME AND JOB APPLICANT
def get_checklist_record(doctype_name, job_applicant):
    try:
        checklist_record_name = frappe.get_value(doctype_name, {"job_applicant": job_applicant}, "name")
        if not checklist_record_name:
            checklist_record = frappe.new_doc(doctype_name)
            checklist_record.job_applicant = job_applicant
            checklist_record.insert(ignore_permissions=True)
            checklist_record_name = checklist_record.name
        return checklist_record_name
    except Exception as e:
        frappe.log_error(f"Error fetching checklist from {doctype_name}: {e}", "Checklist Fetch Error")
        return None

# ? FILL MISSING CHECKLIST RECORDS IN ACTIVITIES
def fill_missing_checklist_records(doc):
    try:
        for row in doc.activities:
            if not row.custom_checklist_record and row.custom_checklist_name and doc.job_applicant:
                checklist_record = get_checklist_record(row.custom_checklist_name, doc.job_applicant)
                if checklist_record:
                    row.custom_checklist_record = checklist_record
    except Exception as e:
        frappe.log_error(f"Error in fill_missing_checklist_records: {e}", "Checklist Record Fill Error")

# ? GET FILTERED ROWS WHERE EMAIL SHOULD BE SENT
def get_pending_activity_rows(doc):
    return [
        row for row in doc.activities
        if row.user and row.custom_is_raised == 1 and row.custom_is_sent == 0
    ]

# ? SEND EMAIL TO USERS FOR PENDING CHECKLIST ACTIONS
def notify_users_for_pending_actions(rows):
    try:
        for row in rows:
            send_pending_action_email(row, notification_name="Reporting Manger Checklist")
            row.custom_is_sent = 1
    except Exception as e:
        frappe.log_error(f"Error in notify_users_for_pending_actions: {e}", "Notify Users Error")

# ? COMPOSE + SEND EMAIL FOR A SINGLE ROW
def send_pending_action_email(row, notification_name):
    try:
        send_notification_email(
            recipients=[row.user],
            notification_name=notification_name,
            doctype=row.custom_checklist_name,
            docname=row.custom_checklist_record,
            button_label="View Details",
        )
    except Exception as e:
        frappe.log_error(f"Error sending email to {row.user}: {e}", "Email Send Error")
