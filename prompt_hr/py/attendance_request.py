import frappe

from frappe import throw
from prompt_hr.py.utils import send_notification_email, check_user_is_reporting_manager




def before_submit(doc, event):
    if not doc.custom_status :
        throw("Cannot Submit, Status not set")



#* NOTIFYING EMPLOYEE'S REPORTING MANAGER WHEN A ATTENDANCE REQUEST IS CREATED
def notify_reporting_manager(doc, event):
    """Method to send email to employee's reporting manager when employee creates attendance request
    """
    try:
        if doc.employee and not doc.custom_status:
            rh_emp = frappe.db.get_value("Employee", doc.employee, "reports_to")
            if not rh_emp:
                throw(f"No Reporting Head found for employee {doc.employee}")
            
            rh_user_id = frappe.db.get_value("Employee", rh_emp, "user_id")
            if not rh_user_id:
                throw(f"Reporting Head User ID not found from {rh_emp}")
            
            if event == "after_insert":
                send_notification_email(
                    recipients=[rh_user_id],
                    notification_name="Attendance Request Creation",
                    doctype="Attendance Request",
                    docname=doc.name,
                    fallback_subject=f"Attendance Request Created",
                    fallback_message=f"<p>Dear Reporting Head,<br> An attendance request has been created—please review it at your convenience.</p>"
                )
            if event == "validate" and not doc.is_new():
                send_notification_email(
                    recipients=[rh_user_id],
                    notification_name="Attendance Request Updated",
                    doctype="Attendance Request",
                    docname=doc.name,
                    fallback_subject=f"Attendance Request Updated",
                    fallback_message=f"<p>Dear Reporting Head,<br> An attendance request has been updated—please review it at your convenience.</p>"
                )
    except Exception as e:
        frappe.log_error(f"Error while sending notification to reporting manager", frappe.get_traceback())
        frappe.throw(str(e))
        