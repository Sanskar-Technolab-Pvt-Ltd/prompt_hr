import frappe
from prompt_hr.py.utils import send_notification_email

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

# ? AFTER INSERT EVENT
def after_insert(doc, method):
    # ? SET REQUIRED DOCUMENTS IN THE NEW JOINEE CHECKLIST
    # set_required_documents_in_new_joinee_checklist(doc)
    pass

# ? FUNCTION TO SET REQUIRED DOCUMENTS IN THE NEW JOINEE CHECKLIST
def set_required_documents_in_new_joinee_checklist(doc):
    if doc.job_applicant:
        # ? GET JOINING DOCUMENT CHECKLIST
        joining_document_checklist = frappe.get_value(
            "Joining Document Checklist",
            {"company": doc.company},
            "name"
        )

        # ? GET JOB APPLICANT'S REQUIRED DOCUMENTS
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

        


# ? MAIN ON_UPDATE EVENT FUNCTION
@frappe.whitelist()
def validate(doc, method):

    # auto_fill_first_activity(doc)
    fill_missing_checklist_records(doc)
    rows_to_notify = get_pending_activity_rows(doc)
    frappe.db.commit()

    notify_users_for_pending_actions(rows_to_notify, company=doc.company)

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

            # ? ONLY SEND IF IS_RAISED IS ALREADY SET
            if first.custom_is_sent == 0:
                send_pending_action_email(first, notification_name="Onboarding Activity Reminder")
                first.custom_is_sent = 1


# ? GET EMAIL FROM JOB APPLICANT
def get_applicant_email(job_applicant):
    return frappe.get_value("Job Applicant", job_applicant, "email_id")


# ? FETCH CHECKLIST RECORD BY DOCTYPE NAME AND JOB APPLICANT
def get_checklist_record(doctype_name, job_applicant):
    try:
        checklist_record_name = frappe.get_value(doctype_name, {"job_applicant": job_applicant}, "name")
        if not checklist_record_name:
            checklist_record = frappe.new_doc(doctype_name)
            checklist_record.job_applicant = job_applicant
            checklist_record.insert(ignore_permissions=True)
            checklist_record_name = checklist_record.name
        else:
            print(f"[DEBUG] Found existing checklist record: {checklist_record_name}")
        return checklist_record_name
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


# ? GET FILTERED ROWS WHERE EMAIL SHOULD BE SENT
def get_pending_activity_rows(doc):
    filtered = [
        row for row in doc.activities
        if (row.user or row.role) and row.custom_is_raised == 1 and row.custom_is_sent == 0
    ]

    return filtered


# ? SEND EMAIL TO USERS FOR PENDING CHECKLIST ACTIONS
def notify_users_for_pending_actions(rows, company):
    if not rows:
        return
    for row in rows:
        send_pending_action_email(row, notification_name="Reporting Manger Checklist", company=company)
        row.custom_is_sent = 1  

# ? FUNCTION TO COMPOSE + SEND EMAIL FOR A SINGLE ROW
def send_pending_action_email(row, notification_name, company):
    # ? FETCH DOCTYPE AND DOCNAME
    doc_type = row.custom_checklist_name
    doc_name = row.custom_checklist_record
    recipient = row.user

    # ? VALIDATE IF BOTH USER AND ROLE ARE SET
    if row.user and row.role:
        frappe.throw("Kindly Either Select User or Role, Not Both", title="Invalid Selection")

    # ? IF ROLE IS SELECTED
    if row.role:
        # ? GET USERS WITH THE SPECIFIED ROLE
        users = frappe.get_all(
            "Has Role",
            filters={"role": row.role},
            fields=["parent as user"],
            pluck="user"
        )

        if not users:
            frappe.throw(f"No users found with role {row.role}", title="No Users Found")

        # ? FILTER ACTIVE EMPLOYEES FROM THE USERS
        emp_wise_recipient = frappe.get_all(
            "Employee",
            filters={
                "user_id": ["in", users],
                "company": company,
                "status": "Active"
            },
            fields=["user_id"]
        )

        if not emp_wise_recipient:
            frappe.throw(f"No active employees found with role {row.role}", title="No Active Employees Found")

        # ? EXTRACT USER IDS
        user_ids = [emp.user_id for emp in emp_wise_recipient if emp.user_id]
        if not user_ids:
            frappe.throw(f"No valid user IDs found for employees with role {row.role}", title="No Valid Users")

        # ? GET EMAIL ADDRESSES OF VALID USERS
        recipients = frappe.get_all(
            "User",
            filters={
                "name": ["in", user_ids],
                "enabled": 1
            },
            fields=["email"],
            pluck="email"
        )

        # ? FILTER OUT EMPTY EMAILS
        recipients = [email for email in recipients if email]

        if not recipients:
            frappe.throw(f"No email addresses found for users with role {row.role}", title="No Email Addresses")

    # ? IF SINGLE USER IS SELECTED
    else:
        if not recipient:
            frappe.throw("No user or role specified", title="Missing Recipient")

        # ? GET EMAIL FOR SINGLE USER
        user_email = frappe.db.get_value("User", recipient, "email")
        if not user_email:
            frappe.throw(f"No email found for user {recipient}", title="No Email Found")

        recipients = [user_email]

    # ? SEND NOTIFICATION EMAIL
    send_notification_email(
        recipients=recipients,
        notification_name=notification_name,
        doctype=doc_type,
        docname=doc_name,
        button_label="View Details",
    )

    frappe.msgprint("Notification email sent successfully.")
