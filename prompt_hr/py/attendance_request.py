import frappe
from frappe import _
from frappe import throw
from prompt_hr.py.utils import (
    send_notification_email,
    check_user_is_reporting_manager,
    fetch_company_name,
    get_employee_email
)


def is_valid_for_partial_day(doc, event):
    prompt_company_name = fetch_company_name(prompt=1)

    if not prompt_company_name.get("error") and doc.company == prompt_company_name.get(
        "company_id"
    ):

        partial_day_allowed_minutes = frappe.db.get_single_value(
            "HR Settings", "custom_partial_day_minutes_for_prompt"
        )

        if partial_day_allowed_minutes and doc.custom_partial_day_request_minutes:
            if partial_day_allowed_minutes < int(doc.custom_partial_day_request_minutes or 0):
                throw(
                    "Allowed Partial Day Minutes are {0}".format(
                        partial_day_allowed_minutes
                    )
                )

    elif prompt_company_name.get("error"):
        throw(prompt_company_name.get("message"))


def before_submit(doc, event):
    if not doc.custom_status:
        throw("Cannot Submit, Status not set")


def validate(doc, event):
    try:
        old_status = frappe.db.get_value(
            "Attendance Request", doc.name, "custom_status"
        )

        # Send additional notification only if status has changed
        if doc.custom_status != old_status and doc.custom_status in [
            "Approved",
            "Rejected",
        ]:
            employee_mail = get_employee_email(doc.employee)
            manager_id = get_employee_email(doc.custom_reporting_manager)
            if manager_id:
                cc = [manager_id]
            else:
                cc = []
            if not doc.is_new():
                auto_approve = frappe.db.get_value("Attendance Request", doc.name, "custom_auto_approve")
                if auto_approve:
                    is_email_sent_allowed = frappe.db.get_single_value("HR Settings", "custom_send_auto_approve_doc_emails") or 0
                    if not is_email_sent_allowed:
                        return
            if employee_mail:
                # FETCH MANAGER NAME IN PYTHON
                manager_name = frappe.db.get_value("Employee", {"user_id": frappe.session.user}, "name") or frappe.session.user

                # BUILD WEEKOFF LINK
                att_req_link = f"{frappe.utils.get_url()}/app/attendance-request/{doc.name}"

                # CREATE THE MESSAGE AS PYTHON F-STRING
                fallback_message = f"""
                    <p>Dear <b>{doc.employee}</b>,</p>

                    <p>
                        Your Attendance request has been {doc.workflow_state} by {manager_name}.<br>
                        Please find the details below:
                    </p>

                    <p><b>Request Summary:</b></p>
                    <ul>
                        <li><b>Employee:</b> {doc.employee}</li>
                        <li><b>Workflow State:</b> {doc.workflow_state}</li>
                        <li><b>Type:</b> {doc.reason}</li>
                        <li><b>View Request:</b> <a href="{att_req_link}">Click here</a></li>
                    </ul>
                    """

                send_notification_email(
                    recipients=[employee_mail],
                    notification_name="Attendance Request Status Changed",
                    doctype="Attendance Request",
                    docname=doc.name,
                    cc=cc,
                    send_link=False,
                    fallback_subject=f"Attendance Request: {doc.workflow_state} - {doc.employee}",
                    fallback_message=fallback_message,
                )
            else: #*Changed by Ayush
                frappe.msgprint(f"No Email Sent Because Employee {doc.employee} does not have a preferred email set.")                
    except Exception as e:
        frappe.log_error(
            f"Error while validating Attendance Request status change: {str(e)}",
            frappe.get_traceback(),
        )
        frappe.throw(str(e))


# * NOTIFYING EMPLOYEE'S REPORTING MANAGER WHEN A ATTENDANCE REQUEST IS CREATED
def notify_reporting_manager(doc, event):
    """Method to send email to employee's reporting manager when employee creates attendance request"""
    try:
        if doc.employee and doc.custom_status == "Pending":
            rh_emp = frappe.db.get_value("Employee", doc.employee, "reports_to")
            employee_id = get_employee_email(doc.employee)
            if not rh_emp:
                throw(f"No Reporting Head found for employee {doc.employee}")

            rh_user_id = get_employee_email(rh_emp)
            if not rh_user_id:
                throw(f"Reporting Head User ID not found from {rh_emp}")

            if event == "after_insert":
                if employee_id:
                    cc = [employee_id]
                else:
                    cc = []
                send_notification_email(
                    recipients=[rh_user_id],
                    notification_name="Attendance Request Creation",
                    doctype="Attendance Request",
                    cc = cc,
                    docname=doc.name,
                    send_link=False,
                    fallback_subject=f"Attendance Request Created",
                    fallback_message=f"<p>Dear Reporting Head,<br> An attendance request has been created—please review it at your convenience.</p>",
                )
            if event == "validate" and not doc.is_new():
                if doc.has_value_changed("custom_reason_for_rejection"):
                    try:
                        prev_reason = frappe.db.get_value("Attendance Request", doc.name, "custom_reason_for_rejection")
                    except:
                        prev_reason = None

                    if not prev_reason:
                        return

                if employee_id:
                    cc = [employee_id]
                else:
                    cc = []
                # Send generic update notification
                send_notification_email(
                    recipients=[rh_user_id],
                    notification_name="Attendance Request Updated",
                    doctype="Attendance Request",
                    docname=doc.name,
                    cc = cc,
                    send_link=False,
                    fallback_subject=f"Attendance Request Updated",
                    fallback_message=f"<p>Dear Reporting Head,<br> An attendance request has been updated—please review it at your convenience.</p>",
                )

    except Exception as e:
        frappe.log_error(
            f"Error while sending notification to reporting manager",
            frappe.get_traceback(),
        )
        frappe.throw(str(e))

def on_update(doc, method=None):
    
    share_leave_with_manager(doc)
    
    if doc.workflow_state == "Pending":
        manager_docname = frappe.db.get_value("Employee", doc.employee, "reports_to")
        if manager_docname:
            manager = frappe.db.get_value(
                "Employee",
                manager_docname,
                ["name", "employee_name"],
                as_dict=True
            )
            if manager:
                doc.db_set("custom_pending_approval_at", f"{manager.name} - {manager.employee_name}")
    else:
        doc.db_set("custom_pending_approval_at", "")
        
        
        
def share_leave_with_manager(leave_doc):
   
    # Get employee linked to this leave
    employee_id = leave_doc.employee
    
    if not employee_id:
        return

    # Get the manager linked in Employee's custom_dotted_line_manager field
    manager_id = frappe.db.get_value("Employee", employee_id, "custom_dotted_line_manager")
    
    if not manager_id:
        return

    # Get the manager's user ID (needed for sharing the document)
    manager_user_id = frappe.db.get_value("Employee", manager_id, "user_id")
    
    if not manager_user_id:
        return

    # Check if the Attendance Request is already shared with the manager
    existing_share = frappe.db.exists("DocShare", {
        "share_doctype": "Attendance Request",
        "share_name": leave_doc.name,
        "user": manager_user_id
    })

    if existing_share:
        return

    # Share the Attendance Request with manager (read-only)
    frappe.share.add_docshare(
        doctype="Attendance Request",
        name=leave_doc.name,
        user=manager_user_id,
        read=1,      # Read permission
        write=0,
        share=0,
        flags={"ignore_share_permission": True}
    )


    


